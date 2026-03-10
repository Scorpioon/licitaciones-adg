#!/usr/bin/env python3
"""
fetch_licitaciones.py — ADG Licitaciones v1.6
Fetcher para licitaciones públicas relevantes al diseño gráfico y comunicación visual.

ARQUITECTURA (leer antes de modificar):
  El feed PLACSP sindicacion_643 es el feed de "perfiles de contratante completo".
  Devuelve licitaciones de organismos que tienen CPVs de diseño en su PERFIL,
  no necesariamente de contratos de diseño. Por eso hay falsos positivos.

  Solución implementada:
  1. Hard gate: el TÍTULO debe contener al menos 1 keyword de diseño.
     Sin eso, el item se descarta sin importar CPV ni descripción.
  2. CPV como bonus (+20), no como requisito autónomo.
  3. Lista de exclusión agresiva aplicada sobre el título.
  4. Scoring separado: título pesa 2x más que descripción.
  5. --enrich: para adjudicatarios, scraping del HTML de detalle (lento, manual).

  v1.6 cambios (2026-03-10):
  - Paginación real con rel="next" según spec PLACSP v1.3 (RFC 5005).
    Antes: solo una página con ?numItems=N. Ahora: sigue links rel="next"
    hasta --pages páginas. Esto permite acceder al histórico completo.
  - Budget regex ampliado: captura formato PLACSP summary "Importe:NNNNEUR"
  - extract_estat_xml(): usa ContractFolderStatusCode (ADJ/PUB/RES/DES/EV)
    en lugar de solo regex sobre texto libre. Más fiable para feed 1044.
  - extract_org_xml(): añadida ruta LocatedContractingParty según spec §4.17.

Dependencias: pip install requests
"""

import argparse, hashlib, html as html_mod, json, re, sys, time, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    sys.exit("Instala requests:  python -m pip install requests")

# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────
OUTPUT_FILE = Path("data.json")
MIN_SCORE   = 20          # Mínimo para incluir un item. Ver DD-001 en BUGTRACKER.
MAX_ITEMS   = 500
TIMEOUT     = 45
ENRICH_DELAY = 0.8        # segundos entre requests al scraping de detalle

HEADERS = {
    "User-Agent": "ADG-Licitaciones/1.5 (+https://adg-fad.org)",
    "Accept":     "application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
}

SOURCES = [
    {
        "name": "PLACSP-643",
        "ccaa": None,
        # Feed de perfiles de contratante completo — licitaciones recientes de
        # organismos con CPVs de diseño en su perfil. ~100 items/page.
        "url":  "https://contrataciondelestado.es/sindicacion/sindicacion_643/"
                "licitacionesPerfilesContratanteCompleto3.atom",
    },
    {
        "name": "PLACSP-1044",
        "ccaa": None,
        # Feed de plataformas agregadas sin contratos menores — incluye CODICE/UBL
        # XML estructurado con WinningParty, importes y fechas como elementos XML.
        # Recomendado para datos históricos y adjudicatarios.
        "url":  "https://contrataciondelsectorpublico.gob.es/sindicacion/"
                "sindicacion_1044/PlataformasAgregadasSinMenores.atom",
    },
]

NS_ATOM  = "http://www.w3.org/2005/Atom"

# UBL/CODICE namespaces used by PLACSP in structured XML entries (feed 1044)
# cac: CommonAggregateComponents, cbc: CommonBasicComponents
NS_UBL = {
    "cac":  "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc":  "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "can":  "urn:dgpe:names:draft:codice:schema:xsd:ContractAwardNotice-2",
    "cn":   "urn:dgpe:names:draft:codice:schema:xsd:ContractNotice-2",
    # Also seen without full URI — just local name matching
}
# All possible URIs for cac: and cbc: in PLACSP feeds
NS_CAC_URIS = {
    "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2",
}
NS_CBC_URIS = {
    "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2",
}

# ── KEYWORDS ──────────────────────────────────────────────────────────────
# Palabras que EXCLUYEN un item del título — descarte inmediato sin importar nada más.
# IMPORTANTE: estas palabras deben ser muy específicas para no descartar diseño+X.
TITLE_EXCLUDE = [
    # Construcción e infraestructura
    "obra civil", "obras de", "reforma de", "instalación de", "instalaciones de",
    "suministro de energía", "suministro e instalación", "suministro y montaje",
    "suministro de módulos", "módulos sanitarios", "módulos prefabricados",
    "suministro de agua", "suministro de gas", "suministro de combustible",
    "mantenimiento de edificio", "mantenimiento del edificio", "mantenimiento y reparación",
    "mantenimiento preventivo", "mantenimiento correctivo",
    "limpieza de", "servicio de limpieza", "servicios de limpieza",
    "seguridad privada", "vigilancia", "control de accesos",
    # Residuos y medio ambiente
    "recogida de residuos", "gestión de residuos", "tratamiento de residuos",
    "basuras", "reciclaje", "compostaje", "planta de tratamiento",
    # Transporte y logística
    "transporte de viajeros", "transporte escolar", "servicio de transporte",
    "contratación de vuelos", "arrendamiento de vehículos",
    # Sanitario (no relacionado con diseño)
    "asistencia sanitaria", "atención sanitaria", "servicio médico",
    "material sanitario", "material clínico", "equipamiento médico",
    "bombas de agua", "grupo de bombeo", "sistema de bombeo",
    # Alimentación y catering
    "catering", "servicio de comedor", "servicio de cafetería", "suministro de alimentos",
    # Otros no relacionados
    "seguridad informática", "ciberseguridad", "consultoría jurídica",
    "asesoría fiscal", "auditoría de cuentas", "préstamo", "arrendamiento financiero",
    "póliza de seguros", "seguro de", "suministro de uniformes",
    "mantenimiento de parques", "mantenimiento de jardines", "mantenimiento de carreteras",
    "señalización vial", "señalización horizontal", "señalización vertical",
    "pintura de", "pintura vial",
    "alquiler de", "arrendamiento de",
    "suministro de mobiliario", "suministro de material de oficina",
    "suministro de equipamiento", "adquisición de equipamiento",
    "adquisición de vehículos", "adquisición de maquinaria",
]

# Keywords que acreditan que es diseño/comunicación — SOLO en título (hard gate).
TITLE_DESIGN_KW = [
    # Diseño gráfico
    "diseño gráfico", "disseny gràfic", "diseño y maquetación",
    "identidad corporativa", "identitat corporativa", "imagen corporativa", "imatge corporativa",
    "manual de identidad", "manual de marca", "manual corporativo",
    "comunicación visual", "comunicació visual", "comunicación gráfica",
    "diseño editorial", "disseny editorial",
    "maquetación", "maquetació", "autoedición",
    "infografía", "infografia",
    "cartelería", "cartelleria", "diseño de cartel", "diseño de carteles",
    "ilustración", "il·lustració",
    "tipografía",
    "logotipo", "logotip", "logomarca",
    "branding",
    # Publicidad y comunicación
    "campaña publicitaria", "campanya publicitària", "campaña de comunicación",
    "campaña de publicidad", "spot publicitario",
    "material promocional", "material divulgativo", "material divulgatiu",
    "material de comunicación", "material comunicatiu",
    "folletos", "fullets", "dípticos", "trípticos",
    "producción gráfica",
    "artes gráficas", "arts gràfiques",
    "rotulación", "retolació",
    # Web y digital
    "diseño web", "disseny web",
    "diseño de página web", "diseño de portal",
    "diseño ux", "diseño ui", "ux/ui", "experiencia de usuario",
    # Señalética y exposición
    "señalética", "senyalètica", "señalización corporativa", "sistema de señalización",
    "museografía", "museografia", "diseño de exposición", "diseño museográfico",
    # Audiovisual
    "producción audiovisual", "producció audiovisual",
    "motion graphics", "animación gráfica",
    "vídeo corporativo", "video corporativo",
    # Fotografía profesional
    "fotografía corporativa", "fotografía de producto", "reportaje fotográfico",
    # Impresión editorial
    "artes finales", "impresión de", "servicios de impresión",
    # Multiservicio comunicación
    "servicios de comunicación", "serveis de comunicació",
    "servicios de diseño", "serveis de disseny",
    "relaciones públicas", "relacions públiques",
    "estrategia de comunicación", "pla de comunicació",
    "plan de comunicación",
]

# Keywords fuertes en descripción (tienen que ver con diseño pero no como título)
STRONG_DESC_KW = [
    "diseño gráfico", "disseny gràfic", "identidad corporativa", "imagen corporativa",
    "manual de marca", "comunicación visual", "maquetación", "infografía",
    "cartelería", "producción gráfica", "artes gráficas", "branding",
    "campaña publicitaria", "material promocional", "señalética", "museografía",
    "producción audiovisual", "motion graphics",
]

# Keywords medias en descripción
MEDIUM_DESC_KW = [
    "diseño", "disseny", "comunicación", "comunicació", "publicidad", "publicitat",
    "marca", "marketing", "edición", "editorial", "fotografía", "fotografia",
    "ilustración", "impresión", "audiovisual", "animación", "exposición",
]

# Keywords de disciplina para clasificar
DISC_KW = {
    "branding":    ["branding","identidad corporativa","identitat corporativa","logotipo","logotip",
                    "logo","manual de marca","manual de identidad","imagen corporativa"],
    "editorial":   ["editorial","maquetación","maquetació","revista","catálogo","catàleg",
                    "folleto","fullet","cartel","cartell","infografía","memoria anual",
                    "publicación","publicació","díptico","tríptico"],
    "web":         ["diseño web","disseny web","página web","pàgina web","sitio web","portal web",
                    "wordpress","diseño digital"],
    "uxui":        ["ux","ui","experiencia de usuario","usabilidad","interfaz","app","aplicación",
                    "ux/ui","experiència d'usuari"],
    "publicitat":  ["publicidad","publicitat","campaña publicitaria","campanya publicitària",
                    "marketing","màrqueting","promoción","spot publicitario"],
    "senyaletica": ["señalética","senyalètica","rotulación","retolació","señalización corporativa",
                    "museografía","diseño de exposición","expositores","señales"],
    "fotografia":  ["fotografía corporativa","fotografía de producto","reportaje fotográfico",
                    "fotografía profesional"],
    "audiovisual": ["producción audiovisual","producció audiovisual","vídeo corporativo",
                    "motion graphics","animación gráfica","spot","multimedia"],
    "illustracio": ["ilustración","il·lustració","ilustración editorial"],
    "impressio":   ["impresión","impressió","artes gráficas","arts gràfiques","offset","serigrafía"],
}

CCAA_KW = {
    "CT":["cataluña","catalunya","barcelona","girona","lleida","tarragona","generalitat de catalunya",
          "diputació de barcelona","ajuntament de"],
    "MD":["madrid","comunidad de madrid","ayuntamiento de madrid","comunitat de madrid"],
    "AN":["andalucía","andalucia","sevilla","málaga","granada","córdoba","junta de andalucía"],
    "PV":["país vasco","pais vasco","euskadi","bilbao","donostia","vitoria","gobierno vasco",
          "diputación foral"],
    "VC":["comunitat valenciana","comunidad valenciana","valencia","alicante","castellón",
          "generalitat valenciana"],
    "GA":["galicia","xunta de galicia","vigo","a coruña","santiago","pontevedra"],
    "AR":["aragón","aragon","zaragoza","gobierno de aragón"],
    "CM":["castilla-la mancha","toledo","albacete","ciudad real"],
    "CL":["castilla y león","valladolid","burgos","salamanca","junta de castilla y león"],
    "MU":["región de murcia","murcia"],"NA":["navarra","pamplona","gobierno de navarra"],
    "IB":["baleares","illes balears","mallorca","ibiza"],
    "CN":["canarias","tenerife","las palmas","gobierno de canarias"],
    "EX":["extremadura","badajoz","cáceres"],"AS":["asturias","oviedo","principado de asturias"],
    "CB":["cantabria","santander"],"RI":["la rioja","gobierno de la rioja"],
    "ES":["ministerio","gobierno de españa","administración general del estado",
          "agencia estatal","organismo autónomo"],
}

TERR = {
    "AN":"Andalucía","AR":"Aragón","AS":"Asturias","IB":"Baleares","CN":"Canarias",
    "CB":"Cantabria","CM":"Castilla-La Mancha","CL":"Castilla y León","CT":"Catalunya",
    "EX":"Extremadura","GA":"Galicia","RI":"La Rioja","MD":"Madrid","MU":"Murcia",
    "NA":"Navarra","PV":"País Vasco","VC":"C. Valenciana","ES":"Estatal",
}


# ── SESSION ───────────────────────────────────────────────────────────────
def build_session():
    retry = Retry(total=3, connect=3, read=3, backoff_factor=1.0,
                  status_forcelist=(429,500,502,503,504),
                  allowed_methods=("HEAD","GET","OPTIONS"))
    s = requests.Session()
    s.headers.update(HEADERS)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://",  HTTPAdapter(max_retries=retry))
    return s


# ── TEXT UTILS ────────────────────────────────────────────────────────────
def strip_html(raw):
    t = html_mod.unescape(raw or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def norm(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()

def kw_in(text, kw):
    """Check if keyword appears as whole-word in normalized text."""
    t, k = norm(text), norm(kw)
    if not t or not k: return False
    if len(k) <= 3 and " " not in k:
        return bool(re.search(rf"\b{re.escape(k)}\b", t))
    return k in t


# ── HARD GATE: TITLE FILTER ───────────────────────────────────────────────
def title_passes_gate(titulo: str) -> bool:
    """
    Returns True only if:
    1. Title does NOT contain any exclusion keyword
    2. Title DOES contain at least one design keyword

    This is the primary false-positive defense. (See BUG-001, DD-001)
    """
    t = norm(titulo)
    # Exclusion: discard if title contains any exclusion phrase
    for ex in TITLE_EXCLUDE:
        if ex in t:
            return False
    # Inclusion: must have at least one design keyword
    for kw in TITLE_DESIGN_KW:
        if kw in t:
            return True
    return False


# ── SCORING ───────────────────────────────────────────────────────────────
def score_item(titulo: str, desc: str, cpv_codes: list) -> tuple:
    """
    Returns (score 0-100, disciplines list, keywords list).
    Title is the primary signal. Description adds bonus.
    CPV is a bonus ONLY when title already passes gate.
    """
    title_norm = norm(titulo)
    desc_norm  = norm(desc)
    score      = 0
    discs      = set()
    kws        = set()

    # ── Title keywords (2x weight) ──────────────────────────────────────
    for kw in TITLE_DESIGN_KW:
        if kw in title_norm:
            score += 15
            kws.add(kw)
            break  # one strong title match is enough, don't stack

    # Multiple title design keywords get diminishing bonus
    extra_title_matches = sum(1 for kw in TITLE_DESIGN_KW if kw in title_norm) - 1
    score += min(extra_title_matches * 5, 15)

    # ── Description keywords ────────────────────────────────────────────
    desc_strong_hits = 0
    for kw in STRONG_DESC_KW:
        if kw in desc_norm:
            score += 6
            kws.add(kw)
            desc_strong_hits += 1

    desc_medium_hits = 0
    for kw in MEDIUM_DESC_KW:
        if kw in desc_norm and kw not in kws:
            score += 2
            kws.add(kw)
            desc_medium_hits += 1

    # ── CPV bonus (only if title already proved design-relevance) ───────
    # See DD-002: CPV alone cannot qualify an item
    CPV_VALID_STARTS = {"79", "22", "92"}  # design/print/AV — removed "72" (too broad)
    design_cpvs = [c for c in cpv_codes if c[:2] in CPV_VALID_STARTS]
    if design_cpvs and score > 0:
        score += 20
        kws.update(f"CPV:{c}" for c in design_cpvs[:2])

    # ── Discipline classification ────────────────────────────────────────
    full = f"{title_norm} {desc_norm}"
    for disc, keys in DISC_KW.items():
        if any(kw_in(full, k) for k in keys):
            discs.add(disc)

    # Default discipline if none matched but title clearly is design
    if not discs and score >= MIN_SCORE:
        discs.add("branding")  # fallback

    score = max(0, min(100, score))
    return score, sorted(discs), list(kws)[:12]


# ── UBL/CODICE XML FIELD EXTRACTION ──────────────────────────────────────
# Used by feed 1044 (PlataformasAgregadas) which embeds CODICE XML directly.
# The user confirmed this structure:
#   <cac:WinningParty>
#     <cac:PartyName><cbc:Name>COMPANY NAME</cbc:Name></cac:PartyName>
#   </cac:WinningParty>

def _local(tag: str) -> str:
    """Strip namespace URI, return local element name."""
    return tag.split('}')[-1] if '}' in tag else tag

def ubl_find_text(entry, *local_path: str) -> str:
    """
    Find a value in UBL XML by traversing local element names.
    Example: ubl_find_text(entry, 'WinningParty', 'PartyName', 'Name')
    Works regardless of namespace URI prefix differences.
    """
    def _walk(el, path, depth=0):
        if depth >= len(path): return (el.text or "").strip()
        target = path[depth].lower()
        for child in el:
            if _local(child.tag).lower() == target:
                result = _walk(child, path, depth + 1)
                if result: return result
        return ""
    return _walk(entry, [p.lower() for p in local_path])

def ubl_find_all_text(entry, *local_path: str) -> list:
    """Find ALL values for a given path (for multi-value fields like TenderResult)."""
    results = []
    def _walk(el, path, depth):
        if depth >= len(path):
            v = (el.text or "").strip()
            if v: results.append(v)
            return
        target = path[depth].lower()
        for child in el:
            if _local(child.tag).lower() == target:
                _walk(child, path, depth + 1)
    _walk(entry, [p.lower() for p in local_path], 0)
    return results

def extract_winning_party_xml(entry) -> str:
    """
    Extract winning party from CODICE/UBL XML structure.
    Handles both ContractAwardNotice and ContractNotice formats.

    Primary path: WinningParty/PartyName/Name
    Fallback path: TenderResult/WinningParty/PartyName/Name
    """
    # Try direct WinningParty
    name = ubl_find_text(entry, "WinningParty", "PartyName", "Name")
    if not name:
        # Try nested in TenderResult
        name = ubl_find_text(entry, "TenderResult", "WinningParty", "PartyName", "Name")
    if not name:
        # Try AwardedTenderedProject path
        name = ubl_find_text(entry, "AwardedTenderedProject", "WinningParty", "PartyName", "Name")

    if name and len(name) >= 3 and not _NUTS_RE.match(name):
        return name[:120]
    return ""

def extract_budget_xml(entry) -> float | None:
    """
    Extract budget from UBL XML elements.
    Priority: BudgetAmount/TaxExclusiveAmount > EstimatedOverallContractAmount > LineExtensionAmount
    """
    def parse_amount(text):
        if not text: return None
        try:
            v = float(re.sub(r'[^\d.]', '', text.replace(',', '.')))
            return v if 100 < v < 50_000_000 else None
        except Exception: return None

    for path in [
        ("BudgetAmount", "TaxExclusiveAmount"),
        ("BudgetAmount", "TaxInclusiveAmount"),
        ("EstimatedOverallContractAmount",),
        ("LineExtensionAmount",),
        ("TaxableAmount",),
    ]:
        v = parse_amount(ubl_find_text(entry, *path))
        if v: return v
    return None

def extract_deadline_xml(entry) -> str:
    """Extract tender deadline from UBL XML date/time elements."""
    def clean_date(s):
        if not s: return ""
        m = re.search(r'(\d{4}-\d{2}-\d{2})', s)
        return m.group(1) if m else ""

    for path in [
        ("TenderSubmissionDeadlinePeriod", "EndDate"),
        ("TenderingProcess", "TenderSubmissionDeadlinePeriod", "EndDate"),
        ("ContractingParty", "Party", "EndDate"),
        ("EndDate",),
    ]:
        d = clean_date(ubl_find_text(entry, *path))
        if d: return d
    return ""

def extract_org_xml(entry) -> str:
    """Extract contracting body name from UBL XML.
    See spec §4.17: LocatedContractingParty/Party/PartyName/Name
    Also tries ContractingParty paths for direct PLACSP entries.
    """
    for path in [
        # spec §4.17 — primary path for aggregated platforms (feed 1044)
        ("LocatedContractingParty", "Party", "PartyName", "Name"),
        ("LocatedContractingParty", "PartyName", "Name"),
        # UBL standard paths (feed 643 / full CODICE)
        ("ContractingParty", "Party", "PartyName", "Name"),
        ("ContractingParty", "PartyName", "Name"),
        ("AccountingSupplierParty", "Party", "PartyName", "Name"),
        ("BuyerCustomerParty", "Party", "PartyName", "Name"),
    ]:
        name = ubl_find_text(entry, *path)
        if name and len(name) >= 4:
            return name[:150]
    return ""

def extract_cpv_xml(entry) -> list:
    """Extract CPV codes from UBL XML ItemClassificationCode elements."""
    codes = []
    for el in entry.iter():
        local = _local(el.tag)
        if local in ("ItemClassificationCode", "ClassificationCode", "CommodityCode"):
            text = (el.text or "").strip()
            if re.fullmatch(r"[1-9]\d{7}", text):
                codes.append(text)
    return list(dict.fromkeys(codes))


# Map ContractFolderStatusCode values to our internal estat labels.
# Source: spec §4.1 + SyndicationContractFolderStatusCode-2.07.gc
_STATUS_CODES = {
    "PUB":  "Vigente",   # Publicada / en plazo
    "PRE":  "Vigente",   # Publicada en preparación
    "EV":   "Vigente",   # En evaluación de ofertas
    "ADJ":  "Adjudicado",
    "RES":  "Adjudicado",  # Resuelta
    "FOR":  "Adjudicado",  # Formalizada
    "ANU":  "Desierta",    # Anulada
    "DES":  "Desierta",    # Desierta
    "SUS":  "Desierta",    # Suspendida
    "ANUL": "Desierta",
}

def extract_estat_xml(entry) -> str:
    """
    Extract tender status from ContractFolderStatusCode XML element.
    See spec §4.1 — more reliable than text regex for feed 1044.
    Returns 'Adjudicado' | 'Desierta' | 'Vigente' | '' (empty = use text fallback).
    """
    for el in entry.iter():
        if _local(el.tag) == "ContractFolderStatusCode":
            code = (el.text or "").strip().upper()
            if code in _STATUS_CODES:
                return _STATUS_CODES[code]
    return ""

def parse_atom_entries(root):
    entries = root.findall(f"{{{NS_ATOM}}}entry")
    if entries: return entries
    return [e for e in root.iter() if str(e.tag).endswith("entry")]

def get_entry_text(entry, tag):
    el = entry.find(f"{{{NS_ATOM}}}{tag}")
    if el is None: return ""
    return " ".join(p.strip() for p in el.itertext() if p and p.strip()).strip()

def get_entry_content(entry) -> str:
    """Get the main text content of an entry, stripped of HTML."""
    raw = get_entry_text(entry, "content") or get_entry_text(entry, "summary")
    return strip_html(raw)

def extract_link(entry) -> str:
    for child in entry.iter():
        if str(child.tag).endswith("link") and child.get("href") and child.get("rel") == "alternate":
            return child.get("href","").strip()
    for child in entry.iter():
        if str(child.tag).endswith("link") and child.get("href"):
            return child.get("href","").strip()
    return ""

def extract_cpv_from_categories(entry) -> list:
    """
    Extract CPV codes ONLY from <category> elements (not from all text).
    See BUG-001: category elements in PLACSP Atom are the contratante's profile CPVs.
    We still collect them but only use as bonus when title already passes.
    """
    codes = []
    for child in entry.iter():
        if str(child.tag).endswith("category"):
            term = child.get("term", "")
            if re.fullmatch(r"[1-9]\d{7}", term):
                codes.append(term)
    return list(dict.fromkeys(codes))


# ── FIELD EXTRACTION ──────────────────────────────────────────────────────
def extract_org(content: str, titulo: str) -> str:
    """Extract contracting body from content field."""
    text = f"{content} {titulo}"
    patterns = [
        r"(?:órgano de contratación|organo de contratacion)\s*[:\-]\s*([^|\n.;]{4,140})",
        r"(?:entidad adjudicadora|poder adjudicador)\s*[:\-]\s*([^|\n.;]{4,140})",
        r"(?:autoridad portuaria de [^|\n.;]{2,80})",
        r"(?:ayuntamiento de [^|\n.;]{2,80})",
        r"(?:ajuntament de [^|\n.;]{2,80})",
        r"(?:diputaci[oó]n de [^|\n.;]{2,80})",
        r"(?:diputaci[oó] de [^|\n.;]{2,80})",
        r"(?:cabildo (?:insular )?de [^|\n.;]{2,80})",
        r"(?:universidad de [^|\n.;]{2,80})",
        r"(?:universitat de [^|\n.;]{2,80})",
        r"(?:ministerio de [^|\n.;]{2,80})",
        r"(?:conseller[ií]a de [^|\n.;]{2,80})",
        r"(?:consejería de [^|\n.;]{2,80})",
        r"(?:mancomunidad de [^|\n.;]{2,80})",
        r"(?:consorcio de [^|\n.;]{2,80})",
        r"(?:patronato de [^|\n.;]{2,80})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            cand = m.group(1) if m.groups() else m.group(0)
            cand = re.sub(r"\s+", " ", cand).strip(" -:;,.|")
            if len(cand) >= 4:
                return cand[:150]
    return ""


def extract_budget(content: str):
    """
    Extract budget from content field.
    PLACSP format: "Presupuesto base de licitación sin impuestos: 25.000,00"
    See BUG-002: must handle Spanish number format (. thousands, , decimal).
    """
    def parse_es_number(s: str):
        """Parse Spanish number format: 1.234.567,89 → 1234567.89"""
        s = s.strip()
        # Remove thousand separators (dots when followed by 3 digits)
        s = re.sub(r'\.(?=\d{3})', '', s)
        # Replace decimal comma with dot
        s = s.replace(',', '.')
        try:
            v = float(re.sub(r'[^\d.]', '', s))
            return v if v > 100 else None
        except Exception:
            return None

    patterns = [
        # Most specific first — labeled amounts
        r"presupuesto base de licitaci[oó]n[^:]*:\s*([\d\.,]+)",
        r"valor estimado del contrato[^:]*:\s*([\d\.,]+)",
        r"importe de licitaci[oó]n[^:]*:\s*([\d\.,]+)",
        r"importe total[^:]*:\s*([\d\.,]+)",
        r"presupuesto[^:]*:\s*([\d\.,]+)\s*(?:€|euros|eur)",
        # PLACSP summary format: "Importe:5000000,00EUR" or "Importe: 200.000 EUR"
        # See spec §3.1.1 — summary pattern: Importe:N; Estado:X
        r"[Ii]mporte\s*:?\s*([\d\.,]+)\s*(?:EUR|€|euros|eur)\b",
        r"[Ii]mporte\s*:?\s*([\d\.,]+)EUR",   # no space variant
        r"([\d\.,]+)\s*(?:€|euros)\b",
    ]
    for pat in patterns:
        m = re.search(pat, content, re.I)
        if m:
            v = parse_es_number(m.group(1))
            if v and 100 < v < 50_000_000:  # sanity range
                return v
    return None


def extract_deadline(content: str) -> str:
    """Extract tender submission deadline date."""
    def norm_date(s):
        s = s.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s): return s
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", s):
            return f"{s[6:]}-{s[3:5]}-{s[:2]}"
        return ""

    patterns = [
        r"fecha l[íi]mite de presentaci[oó]n[^:]*:\s*(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})",
        r"plazo de presentaci[oó]n[^:]*:\s*(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})",
        r"presentaci[oó]n de ofertas[^:]*:\s*(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})",
        r"termini[^:]*:\s*(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, content, re.I)
        if m:
            d = norm_date(m.group(1))
            if d: return d
    return ""


def extract_estat(content: str) -> str:
    """Detect tender status from content."""
    b = norm(content)
    if re.search(r"\b(?:adjudica(?:do|da|t|da)|resuelt[ao]|formalizado)\b", b):
        return "Adjudicado"
    if any(w in b for w in ["desierta","deserta","sin adjudicar","sense adjudicació",
                              "declarada desierta","sin licitadores"]):
        return "Desierta"
    return "Vigente"


def detect_ccaa(src_ccaa, organisme: str, content: str) -> str:
    if src_ccaa: return src_ccaa
    text = norm(f"{organisme} {content[:500]}")
    for code, kws in CCAA_KW.items():
        if any(kw_in(text, k) for k in kws):
            return code
    return "ES"


# ── ADJUDICATARI — DETAIL PAGE SCRAPING ──────────────────────────────────
# See BUG-003: adjudicatari is NOT in the Atom feed.
# Only available in the HTML detail page. Only used with --enrich flag.

_NUTS_RE         = re.compile(r'^ES[\s\-]?\d', re.I)
_BOILERPLATE_FRAGS = [
    "presentará una declaración","declaración responsable","volumen anual de negocios",
    "objeto del contrato","plazo de ejecución","criterios de adjudicación",
]

def scrape_adj_from_detail_page(session, url: str) -> str:
    if not url or '/plataforma' in url: return ""
    try:
        r = session.get(url, timeout=12)
        if not r.ok: return ""
        html_text = r.text
        # Pattern from actual PLACSP HTML:
        # <span title="Winning party" ...>Winning party</span>
        # <span title="COMPANY NAME" ...>COMPANY NAME</span>
        m = re.search(
            r'title=["\']Winning party["\'][^>]*>[^<]*</span>\s*'
            r'<span[^>]+title=["\']([^"\'<>]{4,130})["\']',
            html_text, re.I | re.S
        )
        if m:
            cand = m.group(1).strip()
            if (cand and cand.lower() not in ('winning party','—','-','')
                    and not _NUTS_RE.match(cand) and len(cand.split()) >= 2
                    and not any(f in cand.lower() for f in _BOILERPLATE_FRAGS)):
                return cand[:120]
    except Exception as e:
        print(f"      [!] detail fetch: {e}")
    return ""


def enrich_adjudicataris(items: list, session) -> list:
    to_enrich = [i for i in items if i.get("estat")=="Adjudicado" and not i.get("adjudicatari")]
    if not to_enrich:
        print("  ℹ No hay adjudicados sin adjudicatario para enriquecer."); return items
    print(f"  🔍 Enriqueciendo {len(to_enrich)} adjudicatarios…")
    enriched = 0
    for item in to_enrich:
        adj = scrape_adj_from_detail_page(session, item.get("url",""))
        if adj:
            item["adjudicatari"] = adj
            for h in (item.get("historial") or []):
                if h.get("estat")=="Adjudicado" and "Adjudicado a" not in h.get("nota",""):
                    h["nota"] = f"Adjudicado a {adj}"
            enriched += 1
            print(f"      ✓ {item['titol'][:50]}… → {adj[:40]}")
        else:
            print(f"      – {item['titol'][:50]}…")
        time.sleep(ENRICH_DELAY)
    print(f"  → {enriched}/{len(to_enrich)} enriquecidos")
    return items


# ── STATE MERGE ───────────────────────────────────────────────────────────
def load_previous(path: Path) -> dict:
    if not path.exists(): return {}
    try:
        with open(path, encoding="utf-8") as f: raw = json.load(f)
        items = raw if isinstance(raw, list) else raw.get("data", [])
        return {item["id"]: item for item in items if "id" in item}
    except Exception: return {}


def merge_with_previous(new_items: list, previous: dict, today: str) -> list:
    result = []
    for item in new_items:
        iid  = item["id"]
        prev = previous.get(iid)
        item["historial"] = []
        if prev:
            item["historial"] = prev.get("historial", [])
            if not item.get("adjudicatari") and prev.get("adjudicatari"):
                item["adjudicatari"] = prev["adjudicatari"]
            prev_estat = prev.get("estat","Vigente")
            new_estat  = item.get("estat","Vigente")
            if new_estat != prev_estat:
                nota = f"Adjudicado a {item['adjudicatari']}" if (new_estat=="Adjudicado" and item.get("adjudicatari")) else f"Cambio: {prev_estat} → {new_estat}"
                item["historial"].append({"data":today,"estat":new_estat,"nota":nota})
        else:
            item["historial"] = [{
                "data":  item.get("data_pub", today),
                "estat": item.get("estat","Vigente"),
                "nota":  "Publicación",
            }]
        result.append(item)
    return result


# ── ATOM FETCHER ──────────────────────────────────────────────────────────
def _get_next_url(root) -> str:
    """
    Extract rel="next" pagination link from Atom feed root.
    See spec §3.2 (RFC 5005 Paged Feeds).
    Returns empty string if no next page.
    """
    for child in root:
        tag = _local(child.tag)
        if tag == "link" and child.get("rel") == "next":
            href = child.get("href", "").strip()
            if href:
                return href
    return ""


def fetch_source(session, source: dict, max_pages: int = 1) -> list:
    """
    Fetch a PLACSP Atom source, following rel="next" pagination links.

    v1.6: Each page is ~100 items. --pages N fetches up to N pages total,
    traversing backwards in time via rel="next". This is the correct way
    to access historical data per spec §3.2 (RFC 5005 Paged Feeds).

    Previously (v1.5): only one request with ?numItems=N×100.
    """
    name     = source["name"]
    src_ccaa = source.get("ccaa")
    base_url = source["url"]

    print(f"  ↓ {name}  [hasta {max_pages} página(s) × ~100 items]")

    all_results   = []
    seen_ids      = set()
    url           = base_url
    pages_done    = 0
    today         = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    while url and pages_done < max_pages:
        page_label = f"p{pages_done+1}" if max_pages > 1 else ""
        print(f"    {url[:90]}{'…' if len(url)>90 else ''} {page_label}")

        try:
            r = session.get(url, timeout=TIMEOUT)
            r.raise_for_status()
        except Exception as e:
            print(f"    [!] {e}"); break

        head = r.content[:3000].lower()
        if b"<feed" not in head and b"<entry" not in head:
            print(f"    [!] Respuesta no parece Atom"); break

        try:
            root = ET.fromstring(r.content)
        except ET.ParseError as e:
            print(f"    [!] XML parse error: {e}"); break

        entries = parse_atom_entries(root)
        print(f"    → {len(entries)} entries")

        discarded = {"no_title": 0, "title_gate": 0, "low_score": 0, "dup": 0}
        page_results = []

        for entry in entries:
            try:
                titulo = get_entry_text(entry, "title")
                if not titulo:
                    discarded["no_title"] += 1; continue

                # ── HARD GATE ──────────────────────────────────────────────
                if not title_passes_gate(titulo):
                    discarded["title_gate"] += 1; continue

                content  = get_entry_content(entry)
                url_item = extract_link(entry)
                item_id  = (get_entry_text(entry, "id") or url_item
                            or hashlib.md5(titulo.encode()).hexdigest())

                # Dedup across pages
                if item_id in seen_ids:
                    discarded["dup"] += 1; continue
                seen_ids.add(item_id)

                fecha_pub = (get_entry_text(entry, "published") or
                             get_entry_text(entry, "updated") or today)[:10]

                # ── CPV: XML first, fallback category ──────────────────────
                cpv_codes = extract_cpv_xml(entry) or extract_cpv_from_categories(entry)

                # ── Fields: XML first, fallback text regex ──────────────────
                organisme   = extract_org_xml(entry)  or extract_org(content, titulo)
                pressupost  = extract_budget_xml(entry) or extract_budget(content)
                fecha_limit = extract_deadline_xml(entry) or extract_deadline(content)

                # ── Status: XML code first (§4.1), fallback text regex ──────
                estat = extract_estat_xml(entry) or extract_estat(content)

                # ── WinningParty from UBL XML ───────────────────────────────
                adjudicatari = ""
                if estat == "Adjudicado":
                    adjudicatari = extract_winning_party_xml(entry)

                score, discs, kws = score_item(titulo, content, cpv_codes)
                if score < MIN_SCORE:
                    discarded["low_score"] += 1; continue

                item_ccaa = detect_ccaa(src_ccaa, organisme, content)
                lloc  = TERR.get(item_ccaa, "")
                tipus = "Suministros" if re.search(r"\bsuministro\b|\bsubministrament\b", norm(titulo)) else "Servicios"

                page_results.append({
                    "id":           item_id[:80],
                    "titol":        titulo[:200],
                    "organisme":    organisme[:150],
                    "adjudicatari": adjudicatari[:120],
                    "tipus":        tipus,
                    "pressupost":   pressupost,
                    "disciplines":  discs,
                    "ccaa":         item_ccaa,
                    "lloc":         lloc,
                    "data_pub":     fecha_pub,
                    "data_limit":   fecha_limit,
                    "estat":        estat,
                    "rellevancia":  score,
                    "url":          url_item[:300],
                    "font":         name,
                    "kw":           kws,
                    "cpv":          ", ".join(cpv_codes[:3]),
                    "historial":    [],
                })
            except Exception as e:
                print(f"    [!] entry error: {e}")

        dup_info = f" dup={discarded['dup']}" if discarded['dup'] else ""
        print(f"    → {len(page_results)} relevantes | "
              f"gate={discarded['title_gate']} score={discarded['low_score']} "
              f"notitle={discarded['no_title']}{dup_info}")

        all_results.extend(page_results)
        pages_done += 1

        # Follow rel="next" for older pages (historical data)
        url = _get_next_url(root)
        if url and pages_done < max_pages:
            time.sleep(0.4)  # polite delay between pages

    if pages_done > 1:
        print(f"    ── {pages_done} páginas, {len(all_results)} relevantes en total")
    return all_results


# Keep old name as alias for any callers
def fetch_atom(session, source: dict, num_items: int = 100) -> list:
    pages = max(1, num_items // 100)
    return fetch_source(session, source, max_pages=pages)


# ── MAIN ──────────────────────────────────────────────────────────────────
def main():
    global MIN_SCORE

    ap = argparse.ArgumentParser(description="ADG Licitaciones Fetcher v1.5.3")
    ap.add_argument("--output",    default=str(OUTPUT_FILE),
                    help=f"Archivo de salida (default: {OUTPUT_FILE})")
    ap.add_argument("--min-score", type=int, default=MIN_SCORE,
                    help=f"Puntuación mínima (default: {MIN_SCORE})")
    ap.add_argument("--pages",     type=int, default=1,
                    help="Páginas a recorrer por feed siguiendo rel='next' (~100 items/página). "
                         "Usa --pages 10 para backfill histórico 2024–2026. "
                         "Cada página extra = ~1s de espera. Default: 1")
    ap.add_argument("--source",    choices=["all","643","1044"], default="all",
                    help="Feed a usar: 643 (perfiles), 1044 (agregadas, incluye WinningParty XML), all (ambos). Default: all")
    ap.add_argument("--enrich",    action="store_true",
                    help="Scrape páginas de detalle para adjudicatarios sin WinningParty XML. Lento.")
    ap.add_argument("--stats",     action="store_true",
                    help="Solo mostrar estadísticas, no guardar")
    ap.add_argument("--dry-run",   action="store_true",
                    help="Mostrar items relevantes sin guardar")
    args = ap.parse_args()
    MIN_SCORE = args.min_score

    today   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_path = Path(args.output)

    print(f"\n{'═'*60}")
    print(f"  ADG Licitaciones Fetcher v1.6")
    print(f"  {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"  Min score:  {MIN_SCORE}  |  Páginas: {args.pages} × ~100 items/feed")
    print(f"  Enrich:     {'SÍ (lento)' if args.enrich else 'NO'}")
    print(f"  Output:     {out_path}")
    print(f"{'═'*60}\n")

    previous = load_previous(out_path)
    print(f"  Datos anteriores cargados: {len(previous)} items\n")

    session   = build_session()
    all_items = []
    # Filter sources based on --source flag
    active_sources = SOURCES if args.source == "all" else [
        s for s in SOURCES if args.source in s["name"]
    ]
    for src in active_sources:
        all_items.extend(fetch_source(session, src, max_pages=args.pages))
        print()

    # Dedup (keep highest score per id)
    seen = {}
    for item in all_items:
        key = item["id"]
        if key not in seen or item["rellevancia"] > seen[key]["rellevancia"]:
            seen[key] = item

    unique = sorted(seen.values(),
                    key=lambda x: (-x["rellevancia"], -(x["pressupost"] or 0)))[:MAX_ITEMS]

    # Merge with previous run
    unique = merge_with_previous(unique, previous, today)

    # Carry forward adjudicados/desiertas from previous runs (they may fall off the feed)
    prev_ids = {item["id"] for item in unique}
    carried  = [p for pid,p in previous.items()
                if pid not in prev_ids and p.get("estat") in ("Adjudicado","Desierta")]
    combined = (unique + sorted(carried, key=lambda x:(-x.get("rellevancia",0))))[:MAX_ITEMS]

    # Optional: enrich adjudicatarios via detail page scraping
    if args.enrich:
        print("\n  ── Enriqueciendo adjudicatarios (--enrich) ──")
        combined = enrich_adjudicataris(combined, session)

    # ── Stats summary ──────────────────────────────────────────────────
    vigentes = sum(1 for x in combined if x.get("estat")=="Vigente")
    adjudicados = sum(1 for x in combined if x.get("estat")=="Adjudicado")
    con_ppto = sum(1 for x in combined if x.get("pressupost"))
    vol_total = sum(x.get("pressupost",0) or 0 for x in combined)
    vol_medio = vol_total/con_ppto if con_ppto else 0

    print(f"\n{'─'*50}")
    print(f"  Items finales:      {len(combined)}")
    print(f"  Vigentes:           {vigentes}")
    print(f"  Adjudicados:        {adjudicados}")
    print(f"  Con presupuesto:    {con_ppto} ({100*con_ppto//max(len(combined),1)}%)")
    print(f"  Volumen total:      {vol_total:,.0f} €")
    print(f"  Presupuesto medio:  {vol_medio:,.0f} €")
    print(f"  Con adjudicatario:  {sum(1 for x in combined if x.get('adjudicatari'))}")

    # Discipline breakdown
    from collections import Counter
    disc_counter = Counter()
    for x in combined:
        for d in x.get("disciplines",[]):
            disc_counter[d] += 1
    if disc_counter:
        print(f"  Disciplinas: " + " | ".join(f"{k}:{v}" for k,v in disc_counter.most_common(6)))
    print(f"{'─'*50}\n")

    if args.stats or args.dry_run:
        if args.dry_run:
            for x in combined[:20]:
                print(f"  [{x['rellevancia']:3d}] {x['titol'][:75]}")
        print("  (--stats/--dry-run: no se guarda)")
        return

    # ── Save ──────────────────────────────────────────────────────────
    envelope = {
        "generated_at": now_iso,
        "count":        len(combined),
        "fetcher_version": "1.6",
        "data": combined,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Guardado en {out_path} ({out_path.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
