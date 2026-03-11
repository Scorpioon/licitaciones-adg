#!/usr/bin/env python3
"""
fetch_licitaciones.py — ADG Licitaciones v1.6
Histórico acumulativo + soporte .zip/.atom local + enrich opcional
"""

import argparse
import hashlib
import html as html_mod
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    sys.exit("Instala requests: K:\\PYTHON\\python.exe -m pip install requests")

OUTPUT_FILE = Path("data.json")
MIN_SCORE_DEFAULT = 20
MAX_ITEMS_DEFAULT = 3000
TIMEOUT = 45
ENRICH_DELAY = 0.8

HEADERS = {
    "User-Agent": "ADG-Licitaciones/1.6 (+https://adg-fad.org)",
    "Accept": "application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
}

SOURCES = [
    {
        "name": "PLACSP-643",
        "ccaa": None,
        "url": "https://contrataciondelestado.es/sindicacion/sindicacion_643/"
               "licitacionesPerfilesContratanteCompleto3.atom",
    },
    {
        "name": "PLACSP-1044",
        "ccaa": None,
        "url": "https://contrataciondelsectorpublico.gob.es/sindicacion/"
               "sindicacion_1044/PlataformasAgregadasSinMenores.atom",
    },
]

NS_ATOM = "http://www.w3.org/2005/Atom"

TITLE_EXCLUDE = [
    "obra civil", "obras de", "reforma de", "instalación de", "instalaciones de",
    "suministro de energía", "suministro e instalación", "suministro y montaje",
    "suministro de módulos", "módulos sanitarios", "módulos prefabricados",
    "suministro de agua", "suministro de gas", "suministro de combustible",
    "mantenimiento de edificio", "mantenimiento del edificio", "mantenimiento y reparación",
    "mantenimiento preventivo", "mantenimiento correctivo", "limpieza de", "servicio de limpieza",
    "servicios de limpieza", "seguridad privada", "vigilancia", "control de accesos",
    "recogida de residuos", "gestión de residuos", "tratamiento de residuos", "basuras",
    "reciclaje", "compostaje", "planta de tratamiento", "transporte de viajeros",
    "transporte escolar", "servicio de transporte", "contratación de vuelos",
    "arrendamiento de vehículos", "asistencia sanitaria", "atención sanitaria",
    "servicio médico", "material sanitario", "material clínico", "equipamiento médico",
    "bombas de agua", "grupo de bombeo", "sistema de bombeo", "catering",
    "servicio de comedor", "servicio de cafetería", "suministro de alimentos",
    "seguridad informática", "ciberseguridad", "consultoría jurídica", "asesoría fiscal",
    "auditoría de cuentas", "préstamo", "arrendamiento financiero", "póliza de seguros",
    "seguro de", "suministro de uniformes", "mantenimiento de parques",
    "mantenimiento de jardines", "mantenimiento de carreteras", "señalización vial",
    "señalización horizontal", "señalización vertical", "pintura de", "pintura vial",
    "alquiler de", "arrendamiento de", "suministro de mobiliario",
    "suministro de material de oficina", "suministro de equipamiento",
    "adquisición de equipamiento", "adquisición de vehículos", "adquisición de maquinaria",
]

TITLE_DESIGN_KW = [
    "diseño gráfico", "disseny gràfic", "diseño y maquetación",
    "identidad corporativa", "identitat corporativa", "imagen corporativa", "imatge corporativa",
    "manual de identidad", "manual de marca", "manual corporativo", "comunicación visual",
    "comunicació visual", "comunicación gráfica", "diseño editorial", "disseny editorial",
    "maquetación", "maquetació", "autoedición", "infografía", "infografia", "cartelería",
    "cartelleria", "diseño de cartel", "diseño de carteles", "ilustración", "il·lustració",
    "tipografía", "logotipo", "logotip", "logomarca", "branding", "campaña publicitaria",
    "campanya publicitària", "campaña de comunicación", "campaña de publicidad",
    "spot publicitario", "material promocional", "material divulgativo", "material divulgatiu",
    "material de comunicación", "material comunicatiu", "folletos", "fullets", "dípticos",
    "trípticos", "producción gráfica", "artes gráficas", "arts gràfiques", "rotulación",
    "retolació", "diseño web", "disseny web", "diseño de página web", "diseño de portal",
    "diseño ux", "diseño ui", "ux/ui", "experiencia de usuario", "señalética", "senyalètica",
    "señalización corporativa", "sistema de señalización", "museografía", "museografia",
    "diseño de exposición", "diseño museográfico", "producción audiovisual",
    "producció audiovisual", "motion graphics", "animación gráfica", "vídeo corporativo",
    "video corporativo", "fotografía corporativa", "fotografía de producto",
    "reportaje fotográfico", "artes finales", "impresión de", "servicios de impresión",
    "servicios de comunicación", "serveis de comunicació", "servicios de diseño",
    "serveis de disseny", "relaciones públicas", "relacions públiques",
    "estrategia de comunicación", "pla de comunicació", "plan de comunicación",
]

STRONG_DESC_KW = [
    "diseño gráfico", "disseny gràfic", "identidad corporativa", "imagen corporativa",
    "manual de marca", "comunicación visual", "maquetación", "infografía", "cartelería",
    "producción gráfica", "artes gráficas", "branding", "campaña publicitaria",
    "material promocional", "señalética", "museografía", "producción audiovisual",
    "motion graphics",
]

MEDIUM_DESC_KW = [
    "diseño", "disseny", "comunicación", "comunicació", "publicidad", "publicitat",
    "marca", "marketing", "edición", "editorial", "fotografía", "fotografia",
    "ilustración", "impresión", "audiovisual", "animación", "exposición",
]

DISC_KW = {
    "branding": ["branding", "identidad corporativa", "identitat corporativa", "logotipo", "logotip",
                 "logo", "manual de marca", "manual de identidad", "imagen corporativa"],
    "editorial": ["editorial", "maquetación", "maquetació", "revista", "catálogo", "catàleg",
                  "folleto", "fullet", "cartel", "cartell", "infografía", "memoria anual",
                  "publicación", "publicació", "díptico", "tríptico"],
    "web": ["diseño web", "disseny web", "página web", "pàgina web", "sitio web", "portal web",
            "wordpress", "diseño digital"],
    "uxui": ["ux", "ui", "experiencia de usuario", "usabilidad", "interfaz", "app", "aplicación",
             "ux/ui", "experiència d'usuari"],
    "publicitat": ["publicidad", "publicitat", "campaña publicitaria", "campanya publicitària",
                   "marketing", "màrqueting", "promoción", "spot publicitario"],
    "senyaletica": ["señalética", "senyalètica", "rotulación", "retolació", "señalización corporativa",
                    "museografía", "diseño de exposición", "expositores", "señales"],
    "fotografia": ["fotografía corporativa", "fotografía de producto", "reportaje fotográfico",
                   "fotografía profesional"],
    "audiovisual": ["producción audiovisual", "producció audiovisual", "vídeo corporativo",
                    "motion graphics", "animación gráfica", "spot", "multimedia"],
    "illustracio": ["ilustración", "il·lustració", "ilustración editorial"],
    "impressio": ["impresión", "impressió", "artes gráficas", "arts gràfiques", "offset", "serigrafía"],
}

CCAA_KW = {
    "CT": ["cataluña", "catalunya", "barcelona", "girona", "lleida", "tarragona",
           "generalitat de catalunya", "diputació de barcelona", "ajuntament de barcelona",
           "ajuntament de girona", "ajuntament de lleida", "ajuntament de tarragona"],
    "MD": ["madrid", "comunidad de madrid", "ayuntamiento de madrid", "comunitat de madrid"],
    "AN": ["andalucía", "andalucia", "sevilla", "málaga", "granada", "córdoba", "junta de andalucía"],
    "PV": ["país vasco", "pais vasco", "euskadi", "bilbao", "donostia", "vitoria",
           "gobierno vasco", "diputación foral"],
    "VC": ["comunitat valenciana", "comunidad valenciana", "valencia", "valència",
           "alicante", "alacant", "castellón", "castelló", "generalitat valenciana",
           "ajuntament de valència", "ajuntament d'alacant", "ajuntament de castelló"],
    "GA": ["galicia", "xunta de galicia", "vigo", "a coruña", "santiago", "pontevedra"],
    "AR": ["aragón", "aragon", "zaragoza", "gobierno de aragón"],
    "CM": ["castilla-la mancha", "toledo", "albacete", "ciudad real"],
    "CL": ["castilla y león", "valladolid", "burgos", "salamanca", "junta de castilla y león"],
    "MU": ["región de murcia", "murcia"],
    "NA": ["navarra", "pamplona", "gobierno de navarra"],
    "IB": ["baleares", "illes balears", "mallorca", "ibiza", "calvià", "calvia", "palma"],
    "CN": ["canarias", "tenerife", "las palmas", "gobierno de canarias"],
    "EX": ["extremadura", "badajoz", "cáceres"],
    "AS": ["asturias", "oviedo", "principado de asturias"],
    "CB": ["cantabria", "santander"],
    "RI": ["la rioja", "gobierno de la rioja"],
    "ES": ["ministerio", "gobierno de españa", "administración general del estado",
           "agencia estatal", "organismo autónomo"],
}

TERR = {
    "AN": "Andalucía", "AR": "Aragón", "AS": "Asturias", "IB": "Baleares", "CN": "Canarias",
    "CB": "Cantabria", "CM": "Castilla-La Mancha", "CL": "Castilla y León", "CT": "Catalunya",
    "EX": "Extremadura", "GA": "Galicia", "RI": "La Rioja", "MD": "Madrid", "MU": "Murcia",
    "NA": "Navarra", "PV": "País Vasco", "VC": "C. Valenciana", "ES": "Estatal",
}

_NUTS_RE = re.compile(r'^ES[\s\-]?\d', re.I)
_BOILERPLATE_FRAGS = [
    "presentará una declaración", "declaración responsable", "volumen anual de negocios",
    "objeto del contrato", "plazo de ejecución", "criterios de adjudicación",
]


def build_session():
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("HEAD", "GET", "OPTIONS"),
    )
    s = requests.Session()
    s.headers.update(HEADERS)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def strip_html(raw):
    t = html_mod.unescape(raw or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def kw_in(text, kw):
    t, k = norm(text), norm(kw)
    if not t or not k:
        return False
    if len(k) <= 3 and " " not in k:
        return bool(re.search(rf"\b{re.escape(k)}\b", t))
    return k in t


def title_passes_gate(titulo: str) -> bool:
    t = norm(titulo)
    for ex in TITLE_EXCLUDE:
        if ex in t:
            return False
    for kw in TITLE_DESIGN_KW:
        if kw in t:
            return True
    return False


def score_item(titulo: str, desc: str, cpv_codes: list, min_score: int) -> tuple:
    title_norm = norm(titulo)
    desc_norm = norm(desc)
    score = 0
    discs = set()
    kws = set()

    for kw in TITLE_DESIGN_KW:
        if kw in title_norm:
            score += 15
            kws.add(kw)
            break

    extra_title_matches = sum(1 for kw in TITLE_DESIGN_KW if kw in title_norm) - 1
    score += min(extra_title_matches * 5, 15)

    for kw in STRONG_DESC_KW:
        if kw in desc_norm:
            score += 6
            kws.add(kw)

    for kw in MEDIUM_DESC_KW:
        if kw in desc_norm and kw not in kws:
            score += 2
            kws.add(kw)

    CPV_VALID_STARTS = {"79", "22", "92"}
    design_cpvs = [c for c in cpv_codes if c[:2] in CPV_VALID_STARTS]
    if design_cpvs and score > 0:
        score += 20
        kws.update(f"CPV:{c}" for c in design_cpvs[:2])

    full = f"{title_norm} {desc_norm}"
    for disc, keys in DISC_KW.items():
        if any(kw_in(full, k) for k in keys):
            discs.add(disc)

    # No mostrar "otros" aún; si no hay disciplina clara, dejamos lista vacía.
    # El item puede seguir siendo útil por score/keywords.
    score = max(0, min(100, score))
    return score, sorted(discs), list(kws)[:12]


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def ubl_find_text(entry, *local_path: str) -> str:
    def _walk(el, path, depth=0):
        if depth >= len(path):
            return (el.text or "").strip()
        target = path[depth].lower()
        for child in el:
            if _local(child.tag).lower() == target:
                result = _walk(child, path, depth + 1)
                if result:
                    return result
        return ""
    return _walk(entry, [p.lower() for p in local_path])


def extract_winning_party_xml(entry) -> str:
    name = ubl_find_text(entry, "WinningParty", "PartyName", "Name")
    if not name:
        name = ubl_find_text(entry, "TenderResult", "WinningParty", "PartyName", "Name")
    if not name:
        name = ubl_find_text(entry, "AwardedTenderedProject", "WinningParty", "PartyName", "Name")
    if name and len(name) >= 3 and not _NUTS_RE.match(name):
        return name[:120]
    return ""


def extract_budget_xml(entry):
    def parse_amount(text):
        if not text:
            return None
        try:
            v = float(re.sub(r"[^\d.]", "", text.replace(",", ".")))
            return v if 100 < v < 50_000_000 else None
        except Exception:
            return None

    for path in [
        ("BudgetAmount", "TaxExclusiveAmount"),
        ("BudgetAmount", "TaxInclusiveAmount"),
        ("EstimatedOverallContractAmount",),
        ("LineExtensionAmount",),
        ("TaxableAmount",),
    ]:
        v = parse_amount(ubl_find_text(entry, *path))
        if v:
            return v
    return None


def extract_deadline_xml(entry) -> str:
    def clean_date(s):
        if not s:
            return ""
        m = re.search(r"(\d{4}-\d{2}-\d{2})", s)
        return m.group(1) if m else ""

    for path in [
        ("TenderSubmissionDeadlinePeriod", "EndDate"),
        ("TenderingProcess", "TenderSubmissionDeadlinePeriod", "EndDate"),
        ("ContractingParty", "Party", "EndDate"),
        ("EndDate",),
    ]:
        d = clean_date(ubl_find_text(entry, *path))
        if d:
            return d
    return ""


def extract_org_xml(entry) -> str:
    for path in [
        ("LocatedContractingParty", "Party", "PartyName", "Name"),
        ("LocatedContractingParty", "PartyName", "Name"),
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
    codes = []
    for el in entry.iter():
        local = _local(el.tag)
        if local in ("ItemClassificationCode", "ClassificationCode", "CommodityCode"):
            text = (el.text or "").strip()
            if re.fullmatch(r"[1-9]\d{7}", text):
                codes.append(text)
    return list(dict.fromkeys(codes))


_STATUS_CODES = {
    "PUB": "Vigente", "PRE": "Vigente", "EV": "Vigente",
    "ADJ": "Adjudicado", "RES": "Adjudicado", "FOR": "Adjudicado",
    "ANU": "Desierta", "DES": "Desierta", "SUS": "Desierta", "ANUL": "Desierta",
}


def extract_estat_xml(entry) -> str:
    for el in entry.iter():
        if _local(el.tag) == "ContractFolderStatusCode":
            code = (el.text or "").strip().upper()
            if code in _STATUS_CODES:
                return _STATUS_CODES[code]
    return ""


def parse_atom_entries(root):
    entries = root.findall(f"{{{NS_ATOM}}}entry")
    if entries:
        return entries
    return [e for e in root.iter() if str(e.tag).endswith("entry")]


def get_entry_text(entry, tag):
    el = entry.find(f"{{{NS_ATOM}}}{tag}")
    if el is None:
        return ""
    return " ".join(p.strip() for p in el.itertext() if p and p.strip()).strip()


def get_entry_content(entry) -> str:
    raw = get_entry_text(entry, "content") or get_entry_text(entry, "summary")
    return strip_html(raw)


def extract_link(entry) -> str:
    for child in entry.iter():
        if str(child.tag).endswith("link") and child.get("href") and child.get("rel") == "alternate":
            return child.get("href", "").strip()
    for child in entry.iter():
        if str(child.tag).endswith("link") and child.get("href"):
            return child.get("href", "").strip()
    return ""


def extract_cpv_from_categories(entry) -> list:
    codes = []
    for child in entry.iter():
        if str(child.tag).endswith("category"):
            term = child.get("term", "")
            if re.fullmatch(r"[1-9]\d{7}", term):
                codes.append(term)
    return list(dict.fromkeys(codes))


def extract_org(content: str, titulo: str) -> str:
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
    def parse_es_number(s: str):
        s = s.strip()
        s = re.sub(r"\.(?=\d{3})", "", s)
        s = s.replace(",", ".")
        try:
            v = float(re.sub(r"[^\d.]", "", s))
            return v if v > 100 else None
        except Exception:
            return None

    patterns = [
        r"presupuesto base de licitaci[oó]n[^:]*:\s*([\d\.,]+)",
        r"valor estimado del contrato[^:]*:\s*([\d\.,]+)",
        r"importe de licitaci[oó]n[^:]*:\s*([\d\.,]+)",
        r"importe total[^:]*:\s*([\d\.,]+)",
        r"presupuesto[^:]*:\s*([\d\.,]+)\s*(?:€|euros|eur)",
        r"[Ii]mporte\s*:?\s*([\d\.,]+)\s*(?:EUR|€|euros|eur)\b",
        r"[Ii]mporte\s*:?\s*([\d\.,]+)EUR",
        r"([\d\.,]+)\s*(?:€|euros)\b",
    ]
    for pat in patterns:
        m = re.search(pat, content, re.I)
        if m:
            v = parse_es_number(m.group(1))
            if v and 100 < v < 50_000_000:
                return v
    return None


def extract_deadline(content: str) -> str:
    def norm_date(s):
        s = s.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return s
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
            if d:
                return d
    return ""


def extract_estat(content: str) -> str:
    b = norm(content)
    if re.search(r"\b(?:adjudica(?:do|da|t)|resuelt[ao]|formalizado)\b", b):
        return "Adjudicado"
    if any(w in b for w in ["desierta", "deserta", "sin adjudicar", "sense adjudicació", "declarada desierta", "sin licitadores"]):
        return "Desierta"
    return "Vigente"


def detect_ccaa(src_ccaa, organisme: str, content: str) -> str:
    if src_ccaa:
        return src_ccaa
    text = norm(f"{organisme} {content[:700]}")
    for code, kws in CCAA_KW.items():
        if any(kw_in(text, k) for k in kws):
            return code
    return "ES"


def scrape_adj_from_detail_page(session, url: str) -> str:
    if not url or "/plataforma" in url:
        return ""
    try:
        r = session.get(url, timeout=12)
        if not r.ok:
            return ""
        html_text = r.text
        m = re.search(
            r'title=["\']Winning party["\'][^>]*>[^<]*</span>\s*<span[^>]+title=["\']([^"\'<>]{4,130})["\']',
            html_text,
            re.I | re.S
        )
        if m:
            cand = m.group(1).strip()
            if (
                cand
                and cand.lower() not in ("winning party", "—", "-", "")
                and not _NUTS_RE.match(cand)
                and len(cand.split()) >= 2
                and not any(f in cand.lower() for f in _BOILERPLATE_FRAGS)
            ):
                return cand[:120]
    except Exception as e:
        print(f"      [!] detail fetch: {e}")
    return ""


def enrich_adjudicataris(items: list, session) -> list:
    to_enrich = [i for i in items if i.get("estat") == "Adjudicado" and not i.get("adjudicatari")]
    if not to_enrich:
        print("  ℹ No hay adjudicados sin adjudicatario para enriquecer.")
        return items

    print(f"  🔍 Enriqueciendo {len(to_enrich)} adjudicatarios…")
    enriched = 0
    for item in to_enrich:
        adj = scrape_adj_from_detail_page(session, item.get("url", ""))
        if adj:
            item["adjudicatari"] = adj
            for h in (item.get("historial") or []):
                if h.get("estat") == "Adjudicado" and "Adjudicado a" not in h.get("nota", ""):
                    h["nota"] = f"Adjudicado a {adj}"
            enriched += 1
            print(f"      ✓ {item['titol'][:50]}… → {adj[:40]}")
        else:
            print(f"      – {item['titol'][:50]}…")
        time.sleep(ENRICH_DELAY)

    print(f"  → {enriched}/{len(to_enrich)} enriquecidos")
    return items


def load_previous(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        items = raw if isinstance(raw, list) else raw.get("data", [])
        return {item["id"]: item for item in items if "id" in item}
    except Exception:
        return {}


def make_history_entry(date_str: str, estat: str, nota: str) -> dict:
    return {"data": date_str, "estat": estat, "nota": nota}


def merge_master(new_items: list, previous: dict, today: str) -> list:
    """
    Maestro acumulativo por id:
    - conserva todo lo anterior
    - actualiza con lo nuevo
    - mantiene historial
    - no borra automáticamente vigentes viejos
    """
    merged = dict(previous)

    for item in new_items:
        iid = item["id"]
        prev = merged.get(iid)

        if prev:
            historial = list(prev.get("historial", []))
            prev_estat = prev.get("estat", "Vigente")
            new_estat = item.get("estat", "Vigente")

            # arrastre de campos valiosos si lo nuevo viene vacío
            if not item.get("adjudicatari") and prev.get("adjudicatari"):
                item["adjudicatari"] = prev["adjudicatari"]
            if not item.get("pressupost") and prev.get("pressupost"):
                item["pressupost"] = prev["pressupost"]
            if not item.get("organisme") and prev.get("organisme"):
                item["organisme"] = prev["organisme"]
            if not item.get("data_limit") and prev.get("data_limit"):
                item["data_limit"] = prev["data_limit"]
            if not item.get("url") and prev.get("url"):
                item["url"] = prev["url"]

            # conservar disciplinas/kw si lo nuevo viene pobre
            if not item.get("disciplines") and prev.get("disciplines"):
                item["disciplines"] = prev["disciplines"]
            if not item.get("kw") and prev.get("kw"):
                item["kw"] = prev["kw"]

            # historial
            if new_estat != prev_estat:
                nota = (
                    f"Adjudicado a {item['adjudicatari']}"
                    if (new_estat == "Adjudicado" and item.get("adjudicatari"))
                    else f"Cambio: {prev_estat} → {new_estat}"
                )
                historial.append(make_history_entry(today, new_estat, nota))
            elif not historial:
                historial.append(make_history_entry(item.get("data_pub", today), new_estat, "Publicación"))

            item["historial"] = historial
            merged[iid] = item
        else:
            item["historial"] = [
                make_history_entry(item.get("data_pub", today), item.get("estat", "Vigente"), "Publicación")
            ]
            merged[iid] = item

    return list(merged.values())


def _get_next_url(root) -> str:
    for child in root:
        tag = _local(child.tag)
        if tag == "link" and child.get("rel") == "next":
            href = child.get("href", "").strip()
            if href:
                return href
    return ""


def _process_entries(entries, src_ccaa, source_name, seen_ids, today, min_score):
    discarded = {"no_title": 0, "title_gate": 0, "low_score": 0, "dup": 0}
    page_results = []

    for entry in entries:
        try:
            titulo = get_entry_text(entry, "title")
            if not titulo:
                discarded["no_title"] += 1
                continue

            if not title_passes_gate(titulo):
                discarded["title_gate"] += 1
                continue

            content = get_entry_content(entry)
            url_item = extract_link(entry)
            item_id = (get_entry_text(entry, "id") or url_item or hashlib.md5(titulo.encode()).hexdigest())

            if item_id in seen_ids:
                discarded["dup"] += 1
                continue
            seen_ids.add(item_id)

            fecha_pub = (get_entry_text(entry, "published") or get_entry_text(entry, "updated") or today)[:10]
            cpv_codes = extract_cpv_xml(entry) or extract_cpv_from_categories(entry)
            organisme = extract_org_xml(entry) or extract_org(content, titulo)
            pressupost = extract_budget_xml(entry) or extract_budget(content)
            fecha_limit = extract_deadline_xml(entry) or extract_deadline(content)
            estat = extract_estat_xml(entry) or extract_estat(content)
            adjudicatari = extract_winning_party_xml(entry) if estat == "Adjudicado" else ""

            score, discs, kws = score_item(titulo, content, cpv_codes, min_score)
            if score < min_score:
                discarded["low_score"] += 1
                continue

            item_ccaa = detect_ccaa(src_ccaa, organisme, content)
            lloc = TERR.get(item_ccaa, "")
            tipus = "Suministros" if re.search(r"\bsuministro\b|\bsubministrament\b", norm(titulo)) else "Servicios"

            page_results.append({
                "id": item_id[:120],
                "titol": titulo[:220],
                "organisme": organisme[:150],
                "adjudicatari": adjudicatari[:120],
                "tipus": tipus,
                "pressupost": pressupost,
                "disciplines": discs,
                "ccaa": item_ccaa,
                "lloc": lloc,
                "data_pub": fecha_pub,
                "data_limit": fecha_limit,
                "estat": estat,
                "rellevancia": score,
                "url": url_item[:300],
                "font": source_name,
                "kw": kws,
                "cpv": ", ".join(cpv_codes[:3]),
                "historial": [],
            })
        except Exception as e:
            print(f"    [!] entry error: {e}")

    return page_results, discarded


def fetch_source(session, source: dict, max_pages: int, min_score: int) -> list:
    name = source["name"]
    src_ccaa = source.get("ccaa")
    base_url = source["url"]

    print(f"  ↓ {name}  [hasta {max_pages} página(s) × ~100 items]")
    all_results = []
    seen_ids = set()
    url = base_url
    pages_done = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    while url and pages_done < max_pages:
        page_label = f"p{pages_done + 1}" if max_pages > 1 else ""
        print(f"    {url[:90]}{'…' if len(url) > 90 else ''} {page_label}")

        try:
            r = session.get(url, timeout=TIMEOUT)
            r.raise_for_status()
        except Exception as e:
            print(f"    [!] {e}")
            break

        head = r.content[:3000].lower()
        if b"<feed" not in head and b"<entry" not in head:
            print("    [!] Respuesta no parece Atom")
            break

        try:
            root = ET.fromstring(r.content)
        except ET.ParseError as e:
            print(f"    [!] XML parse error: {e}")
            break

        entries = parse_atom_entries(root)
        print(f"    → {len(entries)} entries")

        page_results, discarded = _process_entries(entries, src_ccaa, name, seen_ids, today, min_score)
        dup_info = f" dup={discarded['dup']}" if discarded["dup"] else ""
        print(
            f"    → {len(page_results)} relevantes | "
            f"gate={discarded['title_gate']} score={discarded['low_score']} "
            f"notitle={discarded['no_title']}{dup_info}"
        )

        all_results.extend(page_results)
        pages_done += 1
        url = _get_next_url(root)

        if url and pages_done < max_pages:
            time.sleep(0.4)

    if pages_done > 1:
        print(f"    ── {pages_done} páginas, {len(all_results)} relevantes en total")

    return all_results


def fetch_local_dir(local_dir: Path, min_score: int) -> list:
    print(f"  ↓ LOCAL  [{local_dir}]")
    if not local_dir.exists():
        print("    [!] La carpeta no existe")
        return []

    atom_files = sorted(local_dir.rglob("*.atom"))
    zip_files = sorted(local_dir.rglob("*.zip"))
    print(f"    → detectados {len(atom_files)} .atom y {len(zip_files)} .zip")

    all_results = []
    seen_ids = set()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    processed_atom = 0
    processed_zip_members = 0

    for atom_file in atom_files:
        try:
            root = ET.parse(atom_file).getroot()
            entries = parse_atom_entries(root)
            page_results, _discarded = _process_entries(entries, None, "LOCAL", seen_ids, today, min_score)
            all_results.extend(page_results)
            processed_atom += 1

            if processed_atom % 200 == 0:
                print(f"    … {processed_atom} .atom procesados | {len(all_results)} relevantes acumulados")

        except ET.ParseError as e:
            print(f"    [!] XML parse error en {atom_file.name}: {e}")
        except Exception as e:
            print(f"    [!] error en {atom_file.name}: {e}")

    for zip_path in zip_files:
        try:
            with zipfile.ZipFile(zip_path) as zf:
                atom_names = [n for n in zf.namelist() if n.lower().endswith(".atom")]
                print(f"    → {zip_path.name}: {len(atom_names)} .atom internos detectados")

                zip_relevant_before = len(all_results)

                for i, member in enumerate(atom_names, start=1):
                    try:
                        with zf.open(member) as fh:
                            root = ET.parse(BytesIO(fh.read())).getroot()

                        entries = parse_atom_entries(root)
                        page_results, _discarded = _process_entries(entries, None, "LOCAL-ZIP", seen_ids, today, min_score)
                        all_results.extend(page_results)
                        processed_zip_members += 1

                        if i % 10 == 0 or i == len(atom_names):
                            encontrados = len(all_results) - zip_relevant_before
                            print(f"      … {i}/{len(atom_names)} .atom | {encontrados} relevantes en este zip")

                    except ET.ParseError as e:
                        print(f"    [!] XML parse error en {zip_path.name}::{Path(member).name}: {e}")
                    except Exception as e:
                        print(f"    [!] error en {zip_path.name}::{Path(member).name}: {e}")

            total_zip = len(all_results) - zip_relevant_before
            print(f"    ✓ {zip_path.name}: {len(atom_names)} .atom internos procesados | {total_zip} relevantes")

        except Exception as e:
            print(f"    [!] No se pudo abrir {zip_path.name}: {e}")

    print(f"    ── local: {processed_atom} .atom sueltos + {processed_zip_members} .atom dentro de zip")
    print(f"    ── local: {len(all_results)} relevantes en total")
    return all_results


def sort_master_items(items: list) -> list:
    def _sort_key(x):
        data_pub = x.get("data_pub") or ""
        rel = x.get("rellevancia") or 0
        ppto = x.get("pressupost") or 0
        return (data_pub, rel, ppto)
    return sorted(items, key=_sort_key, reverse=True)


def main():
    ap = argparse.ArgumentParser(description="ADG Licitaciones Fetcher v1.6")
    ap.add_argument("--output", default=str(OUTPUT_FILE), help=f"Archivo de salida (default: {OUTPUT_FILE})")
    ap.add_argument("--min-score", type=int, default=MIN_SCORE_DEFAULT, help=f"Puntuación mínima (default: {MIN_SCORE_DEFAULT})")
    ap.add_argument("--pages", type=int, default=1, help="Páginas a recorrer por feed siguiendo rel='next' (~100 items/página).")
    ap.add_argument("--source", choices=["all", "643", "1044"], default="all", help="Feed a usar: 643, 1044 o all.")
    ap.add_argument("--local-dir", help="Procesa .atom y/o .zip locales recursivamente desde esta carpeta. Cuando se usa, NO hace fetch online en esta ejecución.")
    ap.add_argument("--enrich", action="store_true", help="Scrape páginas de detalle para adjudicatarios sin WinningParty XML. Lento.")
    ap.add_argument("--stats", action="store_true", help="Solo mostrar estadísticas, no guardar")
    ap.add_argument("--dry-run", action="store_true", help="Mostrar resumen sin guardar")
    ap.add_argument("--max-items", type=int, default=MAX_ITEMS_DEFAULT, help=f"Cap de seguridad del maestro (default: {MAX_ITEMS_DEFAULT})")
    args = ap.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_path = Path(args.output)

    print(f"\n{'═' * 60}")
    print(f"  ADG Licitaciones Fetcher v1.6")
    print(f"  {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"  Min score:  {args.min_score}  |  Páginas: {args.pages} × ~100 items/feed")
    print(f"  Enrich:     {'SÍ (lento)' if args.enrich else 'NO'}")
    print(f"  Local dir:  {args.local_dir if args.local_dir else 'NO'}")
    print(f"  Max items:  {args.max_items}")
    print(f"  Output:     {out_path}")
    print(f"{'═' * 60}\n")

    previous = load_previous(out_path)
    print(f"  Datos anteriores cargados: {len(previous)} items\n")

    all_new_items = []

    if args.local_dir:
        all_new_items.extend(fetch_local_dir(Path(args.local_dir), args.min_score))
        print()
        session = build_session() if args.enrich else None
    else:
        session = build_session()
        active_sources = SOURCES if args.source == "all" else [s for s in SOURCES if args.source in s["name"]]
        for src in active_sources:
            all_new_items.extend(fetch_source(session, src, args.pages, args.min_score))
            print()

    # dedup dentro de la corrida actual por id + relevancia
    dedup_new = {}
    for item in all_new_items:
        key = item["id"]
        if key not in dedup_new or item["rellevancia"] > dedup_new[key]["rellevancia"]:
            dedup_new[key] = item

    merged = merge_master(list(dedup_new.values()), previous, today)

    if args.enrich:
        print("\n  ── Enriqueciendo adjudicatarios (--enrich) ──")
        merged = enrich_adjudicataris(merged, session or build_session())

    merged = sort_master_items(merged)

    # cap de seguridad, pero ahora alto y sobre maestro acumulativo
    if args.max_items and len(merged) > args.max_items:
        merged = merged[:args.max_items]

    vigentes = sum(1 for x in merged if x.get("estat") == "Vigente")
    adjudicados = sum(1 for x in merged if x.get("estat") == "Adjudicado")
    con_ppto = sum(1 for x in merged if x.get("pressupost"))
    vol_total = sum(x.get("pressupost", 0) or 0 for x in merged)
    vol_medio = vol_total / con_ppto if con_ppto else 0

    print(f"\n{'─' * 50}")
    print(f"  Items finales:      {len(merged)}")
    print(f"  Vigentes:           {vigentes}")
    print(f"  Adjudicados:        {adjudicados}")
    print(f"  Con presupuesto:    {con_ppto} ({100 * con_ppto // max(len(merged), 1)}%)")
    print(f"  Volumen total:      {vol_total:,.0f} €")
    print(f"  Presupuesto medio:  {vol_medio:,.0f} €")
    print(f"  Con adjudicatario:  {sum(1 for x in merged if x.get('adjudicatari'))}")

    disc_counter = Counter()
    for x in merged:
        for d in x.get("disciplines", []):
            if d != "otros":
                disc_counter[d] += 1
    if disc_counter:
        print("  Disciplinas: " + " | ".join(f"{k}:{v}" for k, v in disc_counter.most_common(8)))

    years = sorted({(x.get("data_pub") or "")[:4] for x in merged if x.get("data_pub")})
    if years:
        print(f"  Rango años:         {years[0]}–{years[-1]}")

    print(f"{'─' * 50}\n")

    if args.stats or args.dry_run:
        if args.dry_run:
            for x in merged[:20]:
                print(f"  [{x['rellevancia']:3d}] {x['titol'][:90]}")
        print("  (--stats/--dry-run: no se guarda)")
        return

    envelope = {
        "generated_at": now_iso,
        "count": len(merged),
        "fetcher_version": "1.6",
        "data": merged,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)

    print(f"  ✅ Guardado en {out_path} ({out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()