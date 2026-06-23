#!/usr/bin/env python3
# ADG Plataforma Digital -- fetch_licitaciones.py
# 0.4.5z -- May 2026
# Role: PLACSP ATOM fetcher -- scoring, classification, incremental merge,
#       adjudicatario enrichment. Writes data/licitaciones.json.
#
# CHANGELOG (newest first)
# 0.4.5z May 2026  Bugfix: seen_ids.add deferred after score gate; observed/candidate/accepted accounting.
# 0.4.5f May 2026  Add merge_master_v2: ContractFolderID-aware merge; canonical_key dedup path.
# 0.4.4o May 2026  Per-page retry/backoff for transient SSL/network failures in fetch_source().
# 0.4.4n May 2026  Live fetch reliability metadata, partial-run detection, and production write guard.
# 0.4.4i May 2026  Add estat_raw provenance field preserving raw ContractFolderStatusCode for future status semantics.
# 0.4.4h May 2026  (status/date semantics audit only -- no code changes).
# 0.4.4g May 2026  UBL extractor fix: ubl_find_text() resolves ContractFolderStatus root; TypeCode -> tipus.
# 0.4.4f May 2026  (audit + diagnostic only -- no code changes).
# 0.4.4e May 2026  Smoke controls: --max-local-atoms early parser cap; compact \r bar (≤74 chars); --no-progress blank-line fix.
# 0.4.4d May 2026  Progress telemetry: ETA, rejected counts per source, merge new/updated/preserved stats, --quiet/--no-progress flags.
# 0.4.4c May 2026  load_previous() hard-fail safety fix: abort on corrupt output JSON instead of returning empty dict.
# b4.0  Mar 2026  Header updated. Fetch path bug fix and multi-stage
#                 pipeline pending (Phase 7).
# v2.0  Mar 2026  Incremental merge, ZIP support, enrichment, progress bar.
# v1.x  Ene-Feb   Initial ATOM fetcher.

import argparse
import hashlib
import html as html_mod
import json
import random
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
    sys.exit("Instala requests: pip install requests --break-system-packages")

OUTPUT_FILE       = Path("data.json")
MIN_SCORE_DEFAULT = 20
MAX_ITEMS_DEFAULT = 0        # 0 = sin límite
TIMEOUT           = 45
ENRICH_DELAY      = 0.8
_PRODUCTION_PATH  = Path("data/licitaciones.json")

HEADERS = {
    "User-Agent": "ADG-Licitaciones/2.0 (+https://adg-fad.org)",
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
    "branding":    ["branding", "identidad corporativa", "identitat corporativa", "logotipo", "logotip",
                    "logo", "manual de marca", "manual de identidad", "imagen corporativa"],
    "editorial":   ["editorial", "maquetación", "maquetació", "revista", "catálogo", "catàleg",
                    "folleto", "fullet", "cartel", "cartell", "infografía", "memoria anual",
                    "publicación", "publicació", "díptico", "tríptico"],
    "web":         ["diseño web", "disseny web", "página web", "pàgina web", "sitio web", "portal web",
                    "wordpress", "diseño digital"],
    "uxui":        ["ux", "ui", "experiencia de usuario", "usabilidad", "interfaz", "app", "aplicación",
                    "ux/ui", "experiència d'usuari"],
    "publicitat":  ["publicidad", "publicitat", "campaña publicitaria", "campanya publicitària",
                    "marketing", "màrqueting", "promoción", "spot publicitario"],
    "senyaletica": ["señalética", "senyalètica", "rotulación", "retolació", "señalización corporativa",
                    "museografía", "diseño de exposición", "expositores", "señales"],
    "fotografia":  ["fotografía corporativa", "fotografía de producto", "reportaje fotográfico",
                    "fotografía profesional"],
    "audiovisual": ["producción audiovisual", "producció audiovisual", "vídeo corporativo",
                    "motion graphics", "animación gráfica", "spot", "multimedia"],
    "illustracio": ["ilustración", "il·lustració", "ilustración editorial"],
    "impressio":   ["impresión", "impressió", "artes gráficas", "arts gràfiques", "offset", "serigrafía"],
}

CCAA_KW = {
    "CT": ["cataluña", "catalunya", "barcelona", "girona", "lleida", "tarragona",
           "generalitat de catalunya", "diputació de barcelona", "ajuntament de barcelona",
           "ajuntament de girona", "ajuntament de lleida", "ajuntament de tarragona"],
    "MD": ["madrid", "comunidad de madrid", "ayuntamiento de madrid"],
    "AN": ["andalucía", "andalucia", "sevilla", "málaga", "granada", "córdoba", "junta de andalucía"],
    "PV": ["país vasco", "pais vasco", "euskadi", "bilbao", "donostia", "vitoria",
           "gobierno vasco", "diputación foral"],
    "VC": ["comunitat valenciana", "comunidad valenciana", "valencia", "valència",
           "alicante", "alacant", "castellón", "castelló", "generalitat valenciana"],
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

_QUIET = False        # set by --quiet in main()
_NO_PROGRESS = False  # set by --no-progress in main()

# ─────────────────────────────────────────────────────────────────────────────
# PROGRESS HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def pprint(msg: str = "", end: str = "\n"):
    """Print con flush automático para PowerShell."""
    print(msg, end=end, flush=True)


def progress_bar(current: int, total: int, width: int = 30, prefix: str = "") -> str:
    """Genera una barra de progreso ASCII."""
    if total == 0:
        return f"{prefix}[{'─'*width}] 0/0"
    pct = current / total
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"{prefix}[{bar}] {current}/{total} ({pct*100:.0f}%)"


def elapsed(start: float) -> str:
    s = time.time() - start
    if s < 60:
        return f"{s:.1f}s"
    return f"{int(s//60)}m {int(s%60)}s"


def eta(current: int, total: int, start: float) -> str:
    """Estimated time remaining, or '—' when total unknown or no progress yet."""
    if current <= 0 or total <= 0 or current >= total:
        return "—"
    elapsed_s = time.time() - start
    rate = current / elapsed_s if elapsed_s > 0 else 0
    if rate <= 0:
        return "—"
    remaining = (total - current) / rate
    if remaining < 60:
        return f"{remaining:.0f}s"
    return f"{int(remaining//60)}m {int(remaining%60)}s"


# ─────────────────────────────────────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────────────────────────────────────

def build_session():
    retry = Retry(
        total=3, connect=3, read=3, backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("HEAD", "GET", "OPTIONS"),
    )
    s = requests.Session()
    s.headers.update(HEADERS)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


# ─────────────────────────────────────────────────────────────────────────────
# TEXT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────────────────────────

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

    score = max(0, min(100, score))
    return score, sorted(discs), list(kws)[:12]


# ─────────────────────────────────────────────────────────────────────────────
# XML EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def localname_lower(tag: str) -> str:
    return _local(tag).lower()


def ubl_find_text(entry, *local_path: str) -> str:
    ubl_root = entry
    for child in entry:
        if "contractfolderstatus" in _local(child.tag).lower():
            ubl_root = child
            break

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
    return _walk(ubl_root, [p.lower() for p in local_path])


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

    amounts = []
    for path in [
        ("BudgetAmount", "TaxExclusiveAmount"),
        ("BudgetAmount", "TaxInclusiveAmount"),
        ("EstimatedOverallContractAmount",),
        ("LineExtensionAmount",),
        ("TaxableAmount",),
    ]:
        v = parse_amount(ubl_find_text(entry, *path))
        if v:
            amounts.append(v)
    return max(amounts) if amounts else None


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

# v0.4.5b — ContractFolderID extraction model constants
STATUS_CODE_TO_NOTICE_TYPE = {
    "PUB": "PUB",
    "EV": "EV",
    "PRE": "PRE",
    "ADJ": "AWARD",
    "RES": "RES",
    "FOR": "FORMALIZATION",
    "DEL": "CANCELLED",
}

STATUS_RANK = {
    "FORMALIZATION": 10,
    "CONTRACT_MODIFICATION": 9,
    "AWARD": 8,
    "ADJ": 8,
    "RES": 7,
    "EV": 4,
    "PRE": 3,
    "PUB": 2,
    "PRIOR": 1,
    "CANCELLED": 0,
    "UNKNOWN": 0,
}

OPEN_NOTICE_TYPES = {"PUB", "EV", "PRE", "PRIOR", "UNKNOWN"}

_CONTRACT_TYPES = {"1": "Suministros", "2": "Servicios", "3": "Obras"}


def extract_estat_xml(entry) -> str:
    for el in entry.iter():
        if _local(el.tag) == "ContractFolderStatusCode":
            code = (el.text or "").strip().upper()
            if code in _STATUS_CODES:
                return _STATUS_CODES[code]
    # Fallback: check for TenderResult/WinningParty presence
    for child in entry.iter():
        if _local(child.tag) == 'TenderResult':
            for sub in child.iter():
                if _local(sub.tag) in ('WinningParty', 'AwardedTenderedProject'):
                    return 'Adjudicado'
    return ""


def extract_estat_raw_xml(entry) -> str:
    for el in entry.iter():
        if _local(el.tag) == "ContractFolderStatusCode":
            return (el.text or "").strip().upper()
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


# ─────────────────────────────────────────────────────────────────────────────
# v0.4.5b — ContractFolderID extraction helpers
# All use entry.iter() BFS — do NOT use ubl_find_text() for ContractFolderID
# because ubl_find_text() re-roots at ContractFolderStatus and can miss the
# top-level ContractFolderID element.
# ─────────────────────────────────────────────────────────────────────────────

def extract_contract_folder_id_xml(entry) -> str:
    for el in entry.iter():
        if localname_lower(el.tag) == "contractfolderid":
            return (el.text or "").strip()
    return ""


def extract_notice_type_code_xml(entry) -> str:
    for el in entry.iter():
        if localname_lower(el.tag) == "noticetypecode":
            return (el.text or "").strip()
    return ""


def extract_notice_type_xml(entry, status_code_raw=None) -> str:
    raw = status_code_raw or extract_estat_raw_xml(entry)
    # CONTRACT_MODIFICATION takes precedence when the element is present
    for el in entry.iter():
        if localname_lower(el.tag) == "contractmodification":
            return "CONTRACT_MODIFICATION"
    return STATUS_CODE_TO_NOTICE_TYPE.get(raw, "UNKNOWN")


def extract_related_contract_ids_xml(entry) -> list:
    TARGET_TAGS = frozenset({"contractid", "contractidentifier"})
    ids = []
    for el in entry.iter():
        if localname_lower(el.tag) in TARGET_TAGS:
            v = (el.text or "").strip()
            if v and v not in ids:
                ids.append(v)
    return ids


def extract_winning_party_nif_xml(entry) -> str:
    _NIF_RE = re.compile(r"[A-Z][0-9A-Z]{7,8}")
    for el in entry.iter():
        if localname_lower(el.tag) == "winningparty":
            for child in el.iter():
                if localname_lower(child.tag) == "companyid":
                    v = (child.text or "").strip()
                    if _NIF_RE.match(v):
                        return v
    return ""


def extract_formalization_date_xml(entry, status_code_raw: str, issue_date: str) -> str:
    FORM_TAGS = frozenset({"formalizationdate", "signingdate", "contractdate"})
    for el in entry.iter():
        if localname_lower(el.tag) in FORM_TAGS:
            v = (el.text or "").strip()
            if v:
                m = re.search(r"(\d{4}-\d{2}-\d{2})", v)
                return m.group(1) if m else v[:10]
    if status_code_raw == "FOR" and issue_date:
        return issue_date[:10]
    return ""


def extract_award_results_xml(entry, notice_id: str, notice_type: str,
                               status_code_raw: str = "", issue_date: str = "") -> list:
    results = []
    for tr in entry.iter():
        if localname_lower(tr.tag) != "tenderresult":
            continue
        r = {
            "notice_id": notice_id,
            "notice_type": notice_type,
            "result_code": "",
            "winning_party_name": "",
            "winning_party_nif": "",
            "award_amount_tax_excl": None,
            "award_amount_tax_incl": None,
            "lot_id": None,
            "lot_title": None,
            "contract_id": None,
            "award_date": "",
            "formalization_date": extract_formalization_date_xml(entry, status_code_raw, issue_date),
            "modification_date": "",
            "provenance": "feed_xml",
        }
        for el in tr.iter():
            ln = localname_lower(el.tag)
            v = (el.text or "").strip()
            if ln == "resultcode" and not r["result_code"]:
                r["result_code"] = v
            elif ln == "awarddate" and not r["award_date"]:
                r["award_date"] = v[:10] if v else ""
            elif ln == "payableamount" and r["award_amount_tax_incl"] is None:
                try:
                    r["award_amount_tax_incl"] = float(v.replace(",", "."))
                except ValueError:
                    pass
            elif ln == "taxexclusiveamount" and r["award_amount_tax_excl"] is None:
                try:
                    r["award_amount_tax_excl"] = float(v.replace(",", "."))
                except ValueError:
                    pass
            elif ln in ("partyname", "name") and not r["winning_party_name"]:
                if len(v) >= 3 and not _NUTS_RE.match(v):
                    r["winning_party_name"] = v[:120]
            elif ln == "companyid" and not r["winning_party_nif"]:
                if re.match(r"[A-Z][0-9A-Z]{7,8}", v):
                    r["winning_party_nif"] = v
            elif ln == "lotid" and r["lot_id"] is None:
                r["lot_id"] = v
            elif ln == "contractid" and r["contract_id"] is None:
                r["contract_id"] = v
        results.append(r)
    return results


def extract_document_catalogue_xml(entry, notice_id: str, notice_type: str) -> list:
    # Live PLACSP Atom feed tags (confirmed v0.4.5a2) + fixture/full-CODICE tags
    DOC_TAGS = frozenset({
        "legaldocumentreference",
        "technicaldocumentreference",
        "additionalpublicationdocumentreference",
        "templatedocumentreference",
        "attachmentdocumentreference",
        "documentreference",
        "additionalattachment",
    })
    _MIME = {"pdf": "application/pdf", "zip": "application/zip",
             "doc": "application/msword",
             "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    docs = []
    for el in entry.iter():
        if localname_lower(el.tag) not in DOC_TAGS:
            continue
        doc = {
            "notice_id": notice_id,
            "notice_type": notice_type,
            "document_type": "",
            "source_section": localname_lower(el.tag),
            "title": "",
            "url": "",
            "mime_hint": "",
            "format_hint": "",
            "published_at": "",
            "provenance": "feed_xml",
        }
        for child in el.iter():
            ln = localname_lower(child.tag)
            v = (child.text or "").strip()
            if ln == "documenttypecode" and not doc["document_type"]:
                doc["document_type"] = v
            elif ln in ("uri", "url") and not doc["url"]:
                doc["url"] = v[:500]
            elif ln in ("filename", "title", "documentdescription", "name") and not doc["title"]:
                doc["title"] = v[:200]
            elif ln == "issuedate" and not doc["published_at"]:
                doc["published_at"] = v[:10]
        if doc["url"]:
            ext = doc["url"].rsplit(".", 1)[-1].lower().split("?")[0][:8]
            doc["mime_hint"] = _MIME.get(ext, "")
            doc["format_hint"] = ext.upper() if ext else ""
        docs.append(doc)
    return docs


# ─────────────────────────────────────────────────────────────────────────────
# TEXT-BASED EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# ENRICH
# ─────────────────────────────────────────────────────────────────────────────

def scrape_adj_from_detail_page(session, url: str) -> str:
    if not url or "/plataforma" in url:
        return ""
    try:
        r = session.get(url, timeout=12)
        if not r.ok:
            return ""
        m = re.search(
            r'title=["\']Winning party["\'][^>]*>[^<]*</span>\s*<span[^>]+title=["\']([^"\'<>]{4,130})["\']',
            r.text, re.I | re.S
        )
        if m:
            cand = m.group(1).strip()
            if (cand and cand.lower() not in ("winning party", "—", "-", "")
                    and not _NUTS_RE.match(cand) and len(cand.split()) >= 2
                    and not any(f in cand.lower() for f in _BOILERPLATE_FRAGS)):
                return cand[:120]
    except Exception as e:
        pprint(f"      [!] detail fetch: {e}")
    return ""


def enrich_adjudicataris(items: list, session) -> list:
    to_enrich = [i for i in items if i.get("estat") == "Adjudicado" and not i.get("adjudicatari")]
    if not to_enrich:
        pprint("  ℹ No hay adjudicados sin adjudicatario para enriquecer.")
        return items

    pprint(f"  🔍 Enriqueciendo {len(to_enrich)} adjudicatarios…")
    enriched = 0
    for idx, item in enumerate(to_enrich, 1):
        pprint(progress_bar(idx, len(to_enrich), prefix="  "), end="\r")
        adj = scrape_adj_from_detail_page(session, item.get("url", ""))
        if adj:
            item["adjudicatari"] = adj
            for h in (item.get("historial") or []):
                if h.get("estat") == "Adjudicado" and "Adjudicado a" not in h.get("nota", ""):
                    h["nota"] = f"Adjudicado a {adj}"
            enriched += 1
        time.sleep(ENRICH_DELAY)

    pprint("")  # newline after progress bar
    pprint(f"  → {enriched}/{len(to_enrich)} enriquecidos")
    return items


# ─────────────────────────────────────────────────────────────────────────────
# PERSISTENCE
# ─────────────────────────────────────────────────────────────────────────────

def load_previous(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        items = raw if isinstance(raw, list) else raw.get("data", [])
        return {item["id"]: item for item in items if "id" in item}
    except Exception as e:
        sys.exit(f"[FATAL] No se puede leer {path}: {e}\nHaz backup y verifica el JSON antes de continuar.")


def make_history_entry(date_str: str, estat: str, nota: str) -> dict:
    return {"data": date_str, "estat": estat, "nota": nota}


def merge_master(new_items: list, previous: dict, today: str) -> tuple:
    merged = dict(previous)
    new_count = 0
    updated_count = 0

    for item in new_items:
        iid = item["id"]
        prev = merged.get(iid)

        if prev:
            historial = list(prev.get("historial", []))
            prev_estat = prev.get("estat", "Vigente")
            new_estat = item.get("estat", "Vigente")

            # Arrastrar campos valiosos si lo nuevo viene vacío
            for field in ("adjudicatari", "pressupost", "organisme", "data_limit", "url",
                          "disciplines", "kw"):
                if not item.get(field) and prev.get(field):
                    item[field] = prev[field]

            # Historial de cambios de estado
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
            updated_count += 1
        else:
            item["historial"] = [
                make_history_entry(item.get("data_pub", today), item.get("estat", "Vigente"), "Publicación")
            ]
            merged[iid] = item
            new_count += 1

    preserved_count = len(previous) - updated_count
    stats = {"new": new_count, "updated": updated_count, "preserved": preserved_count}
    return list(merged.values()), stats


def merge_master_v2(new_items: list, previous: dict, today: str) -> tuple:
    """ContractFolderID-aware incremental merge (v0.4.5f).

    Merge key: canonical_key = contract_folder_id if present, else item["id"].
    Higher STATUS_RANK always wins; lower rank never downgrades a record.
    Union semantics for notice_history, award_results, documents,
    related_contract_ids, cpv, historial.
    previous dict may be keyed by old item["id"] strings (pre-CFID baseline) —
    those records are preserved unchanged under their original keys.
    """
    # Build a lookup from canonical_key -> record for previous data.
    # previous may be keyed by item["id"] (old records without CFID).
    prev_by_ckey: dict = {}
    for rec in previous.values():
        ckey = rec.get("canonical_key") or rec.get("contract_folder_id") or rec["id"]
        prev_by_ckey[ckey] = rec

    merged: dict = {}
    # Preserve all previous records under their canonical keys.
    for rec in previous.values():
        ckey = rec.get("canonical_key") or rec.get("contract_folder_id") or rec["id"]
        merged[ckey] = rec

    new_count = 0
    updated_count = 0

    def _union_list(base: list, incoming: list, key_fn) -> list:
        seen = {key_fn(x) for x in base}
        result = list(base)
        for x in incoming:
            k = key_fn(x)
            if k not in seen:
                result.append(x)
                seen.add(k)
        return result

    def _award_key(a: dict) -> tuple:
        return (
            a.get("notice_id", ""),
            a.get("winning_party_name", ""),
            a.get("winning_party_nif", ""),
            str(a.get("award_amount_tax_excl", "")),
            a.get("contract_id", ""),
            a.get("lot_id", ""),
        )

    def _doc_key(d: dict) -> tuple:
        return (d.get("title", ""), d.get("url", ""), d.get("document_type", ""), d.get("notice_id", ""))

    def _hist_key(h: dict) -> tuple:
        return (h.get("notice_id", ""), h.get("notice_type", ""), h.get("issue_date", ""))

    def _earliest_date(a: str, b: str) -> str:
        if not a:
            return b
        if not b:
            return a
        return a if a <= b else b

    def _latest_date(a: str, b: str) -> str:
        if not a:
            return b
        if not b:
            return a
        return a if a >= b else b

    def _estat_from_notice_type(notice_type: str, rank: int) -> str:
        if notice_type == "CANCELLED":
            return "Desierta"
        if rank >= 8 or notice_type in {"AWARD", "FORMALIZATION", "ADJ", "RES"}:
            return "Adjudicado"
        return "Vigente"

    for item in new_items:
        ckey = item.get("canonical_key") or item.get("contract_folder_id") or item["id"]
        item_rank = STATUS_RANK.get(item.get("notice_type", "UNKNOWN"), 0)
        prev = merged.get(ckey)

        if prev is None:
            # Genuinely new canonical procurement.
            if not item.get("historial"):
                item["historial"] = [
                    make_history_entry(item.get("data_pub", today), item.get("estat", "Vigente"), "Publicación")
                ]
            merged[ckey] = item
            new_count += 1
            continue

        # Existing record — decide winner by status rank.
        prev_rank = STATUS_RANK.get(prev.get("notice_type", "UNKNOWN"), 0)
        rank_wins = item_rank > prev_rank

        # Base record: start from the higher-rank source.
        if rank_wins:
            base = dict(item)
            other = prev
        else:
            base = dict(prev)
            other = item

        # --- Union / append fields ---

        # notice_history: union by (notice_id, notice_type, issue_date)
        base["notice_history"] = _union_list(
            list(base.get("notice_history") or []),
            list(other.get("notice_history") or []),
            _hist_key,
        )

        # award_results: union by stable tuple
        base["award_results"] = _union_list(
            list(base.get("award_results") or []),
            list(other.get("award_results") or []),
            _award_key,
        )

        # documents
        base["documents"] = _union_list(
            list(base.get("documents") or []),
            list(other.get("documents") or []),
            _doc_key,
        )

        # related_contract_ids: union by exact string
        rci_set = set(base.get("related_contract_ids") or [])
        for r in (other.get("related_contract_ids") or []):
            rci_set.add(r)
        base["related_contract_ids"] = sorted(rci_set)

        # cpv: union comma-joined sets
        cpv_set = set(x.strip() for x in (base.get("cpv") or "").split(",") if x.strip())
        for c in (other.get("cpv") or "").split(","):
            c = c.strip()
            if c:
                cpv_set.add(c)
        base["cpv"] = ",".join(sorted(cpv_set))

        # historial: prefer base; append entries from other that aren't duplicates
        base_historial = list(base.get("historial") or [])
        other_historial = list(other.get("historial") or [])
        hist_keys = {(h.get("data", ""), h.get("estat", ""), h.get("nota", "")) for h in base_historial}
        for h in other_historial:
            k = (h.get("data", ""), h.get("estat", ""), h.get("nota", ""))
            if k not in hist_keys:
                base_historial.append(h)
                hist_keys.add(k)
        if rank_wins:
            new_estat = _estat_from_notice_type(item.get("notice_type", "UNKNOWN"), item_rank)
            prev_estat_val = prev.get("estat") or "Vigente"
            if new_estat != prev_estat_val:
                nota = (
                    f"Adjudicado a {item.get('adjudicatari')}"
                    if (new_estat == "Adjudicado" and item.get("adjudicatari"))
                    else f"Cambio: {prev_estat_val} → {new_estat}"
                )
                base_historial.append(make_history_entry(today, new_estat, nota))
        elif not base_historial:
            base_historial.append(
                make_history_entry(base.get("data_pub", today), base.get("estat", "Vigente"), "Publicación")
            )
        base["historial"] = base_historial

        # --- Scalar fields: keep non-empty / winning-rank values ---

        # id: preserve the existing id (may be the original Atom entry URL)
        base["id"] = prev.get("id") or item.get("id")

        # canonical_key / contract_folder_id: keep truthy value
        base["canonical_key"] = (
            prev.get("canonical_key") or prev.get("contract_folder_id")
            or item.get("canonical_key") or item.get("contract_folder_id")
            or ckey
        )
        base["contract_folder_id"] = (
            prev.get("contract_folder_id") or item.get("contract_folder_id") or ""
        )

        # data_limit: keep non-empty tender-stage deadline; don't overwrite with blank from award notices
        base["data_limit"] = prev.get("data_limit") or item.get("data_limit") or ""

        # first_pub_date: earliest publication date
        base["first_pub_date"] = _earliest_date(
            prev.get("first_pub_date") or "", item.get("first_pub_date") or ""
        )

        # last_notice_date: latest known notice date
        base["last_notice_date"] = _latest_date(
            prev.get("last_notice_date") or "", item.get("last_notice_date") or ""
        )

        # data_pub: keep; prefer winner's value but fall back to other
        if not base.get("data_pub"):
            base["data_pub"] = other.get("data_pub") or ""

        # estat / estat_raw: derive from winning rank
        new_notice_type = base.get("notice_type", "UNKNOWN")
        winning_rank = max(item_rank, prev_rank)
        base["estat"] = _estat_from_notice_type(new_notice_type, winning_rank)
        # estat_raw: keep prev's raw code if new winner has none
        if not base.get("estat_raw"):
            base["estat_raw"] = other.get("estat_raw") or ""

        # adjudicatari: never blank a non-empty value; fill from award_results if empty
        if not base.get("adjudicatari"):
            base["adjudicatari"] = other.get("adjudicatari") or ""
        if not base.get("adjudicatari") and base["award_results"]:
            best = max(
                base["award_results"],
                key=lambda a: STATUS_RANK.get(a.get("notice_type", "UNKNOWN"), 0),
            )
            winner_name = best.get("winning_party_name") or ""
            if winner_name:
                base["adjudicatari"] = winner_name
                base["winner_provenance"] = "feed_xml"

        # Carry forward enrichment fields if winner doesn't have them
        for field in ("pressupost", "organisme", "url", "font", "disciplines", "kw",
                      "enrichment_version", "tipus", "ambit"):
            if not base.get(field) and other.get(field):
                base[field] = other[field]

        # sources_seen: union
        s_set = set(base.get("sources_seen") or [])
        s_set.update(other.get("sources_seen") or [])
        if s_set:
            base["sources_seen"] = sorted(s_set)

        if rank_wins:
            updated_count += 1
        else:
            # Not a rank win but still absorbed union data — count as updated
            updated_count += 1

        merged[ckey] = base

    preserved_count = len(previous) - updated_count
    stats = {"new": new_count, "updated": updated_count, "preserved": preserved_count}
    return list(merged.values()), stats


# ─────────────────────────────────────────────────────────────────────────────
# PROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def _get_next_url(root) -> str:
    for child in root:
        tag = _local(child.tag)
        if tag == "link" and child.get("rel") == "next":
            href = child.get("href", "").strip()
            if href:
                return href
    return ""


def _process_entries(entries, src_ccaa, source_name, seen_ids, today, min_score,
                     discard_evidence=None, max_discard_evidence=500):
    _evidence = discard_evidence if discard_evidence is not None else []
    discarded = {
        "no_title": 0, "title_gate": 0, "low_score": 0, "dup": 0,
        "observed_entries_count": 0, "candidate_id_count": 0,
        "low_score_by_score": {},
    }
    page_results = []

    for entry in entries:
        try:
            discarded["observed_entries_count"] += 1
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
            discarded["candidate_id_count"] += 1

            if item_id in seen_ids:
                discarded["dup"] += 1
                continue
            # seen_ids.add deferred — only accepted records block re-evaluation (v0.4.5z)

            fecha_pub = (get_entry_text(entry, "published") or get_entry_text(entry, "updated") or today)[:10]
            cpv_codes = extract_cpv_xml(entry) or extract_cpv_from_categories(entry)
            organisme = extract_org_xml(entry) or extract_org(content, titulo)
            pressupost = extract_budget_xml(entry) or extract_budget(content)
            fecha_limit = extract_deadline_xml(entry) or extract_deadline(content)
            estat = extract_estat_xml(entry) or extract_estat(content)
            estat_raw = extract_estat_raw_xml(entry)
            adjudicatari = extract_winning_party_xml(entry) if estat == "Adjudicado" else ""

            score, discs, kws = score_item(titulo, content, cpv_codes, min_score)
            if score < min_score:
                discarded["low_score"] += 1
                sk = str(score)
                discarded["low_score_by_score"][sk] = discarded["low_score_by_score"].get(sk, 0) + 1
                if len(_evidence) < max_discard_evidence:
                    _evidence.append({
                        "id": item_id[:80], "score": score,
                        "titulo": titulo[:120], "kws": kws, "discs": discs,
                        "source": source_name,
                    })
                continue

            item_ccaa = detect_ccaa(src_ccaa, organisme, content)
            lloc = TERR.get(item_ccaa, "")
            _tc = ubl_find_text(entry, "ProcurementProject", "TypeCode")
            tipus = _CONTRACT_TYPES.get(_tc) or (
                "Suministros" if re.search(r"\bsuministro\b|\bsubministrament\b", norm(titulo)) else "Servicios"
            )

            # v0.4.5b — ContractFolderID extraction (additive fields; does not affect merge yet)
            cfid = extract_contract_folder_id_xml(entry)
            canonical_key = cfid if cfid else item_id[:120]
            notice_type = extract_notice_type_xml(entry, estat_raw)
            notice_type_code = extract_notice_type_code_xml(entry)
            status_rank = STATUS_RANK.get(notice_type, 0)
            award_results = extract_award_results_xml(entry, item_id[:80], notice_type, estat_raw, fecha_pub)
            related_contract_ids = extract_related_contract_ids_xml(entry)
            documents = extract_document_catalogue_xml(entry, item_id[:80], notice_type)
            # Backward-compat: fill adjudicatari from award_results if currently empty
            if not adjudicatari and award_results:
                for ar in award_results:
                    if ar.get("winning_party_name"):
                        adjudicatari = ar["winning_party_name"]
                        break
            winner_provenance = "feed_xml" if adjudicatari else ""

            seen_ids.add(item_id)  # v0.4.5z: moved after score gate — accepted records only
            page_results.append({
                "id": item_id[:120],
                "titol": titulo[:400],
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
                "estat_raw": estat_raw,
                "rellevancia": score,
                "url": url_item[:300],
                "font": source_name,
                "kw": kws,
                "cpv": ", ".join(cpv_codes[:3]),
                "historial": [],
                # v0.4.5b additive fields
                "contract_folder_id": cfid,
                "canonical_key": canonical_key,
                "notice_type": notice_type,
                "notice_type_code": notice_type_code,
                "status_rank": status_rank,
                "first_pub_date": fecha_pub if notice_type in {"PUB", "PRIOR"} else "",
                "last_notice_date": fecha_pub,
                "status_provenance": item_id[:80],
                "winner_provenance": winner_provenance,
                "award_results": award_results,
                "related_contract_ids": related_contract_ids,
                "notice_history": [{
                    "notice_id": item_id[:80],
                    "notice_type": notice_type,
                    "status_key": notice_type,
                    "status_code_raw": estat_raw,
                    "issue_date": fecha_pub,
                    "url": url_item[:300],
                    "source": source_name,
                }],
                "documents": documents,
            })
        except Exception as e:
            pprint(f"    [!] entry error: {e}")

    return page_results, discarded


# ─────────────────────────────────────────────────────────────────────────────
# FETCH: ONLINE
# ─────────────────────────────────────────────────────────────────────────────

def is_retryable_fetch_error(exc) -> bool:
    """True for transient SSL/network errors that warrant per-page retry."""
    return isinstance(exc, (
        requests.exceptions.SSLError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.ChunkedEncodingError,
    ))


def retry_sleep(attempt: int, retry_delay: float, retry_backoff: float) -> float:
    """Exponential backoff with ±20% jitter. attempt starts at 1 for first retry."""
    base = retry_delay * (retry_backoff ** (attempt - 1))
    return base * random.uniform(0.8, 1.2)


def _sanitize_snippet(raw_bytes: bytes, encoding: str = None, limit: int = 160) -> str:
    """Single-line, length-capped, printable-only snippet of response bytes.

    Used only for non-Atom diagnostics — never dumps full HTML or binary noise.
    Collapses all whitespace to single spaces and drops control characters.
    """
    try:
        text = raw_bytes[:600].decode(encoding or "utf-8", errors="replace")
    except (LookupError, TypeError):
        text = raw_bytes[:600].decode("utf-8", errors="replace")
    text = re.sub(r"\s+", " ", text)                      # newlines/tabs/spaces -> single space
    text = "".join(ch for ch in text if ch >= " " and ch != "\x7f")  # drop control / binary noise
    text = text.strip()
    if len(text) > limit:
        text = text[:limit - 1].rstrip() + "…"
    return text


def _describe_non_atom_response(resp) -> str:
    """Enriched non-Atom diagnostic string: status, content-type, final URL, snippet.

    Shape: non-Atom response status=503 content-type=text/html final_url=https://... snippet="..."
    Does not change retry/outcome semantics — only the recorded error text.
    """
    status = getattr(resp, "status_code", "?")
    headers = getattr(resp, "headers", None)
    ctype = (headers.get("Content-Type", "") if headers else "").split(";")[0].strip() or "?"
    final_url = getattr(resp, "url", "") or "?"
    snippet = _sanitize_snippet(getattr(resp, "content", b"") or b"", getattr(resp, "encoding", None))
    return (
        f"non-Atom response status={status} content-type={ctype} "
        f'final_url={final_url} snippet="{snippet}"'
    )


def fetch_source(session, source: dict, max_pages: int, min_score: int,
                 retries: int = 3, retry_delay: float = 2.0, retry_backoff: float = 2.0) -> dict:
    """Returns dict: {results, pages_done, had_error, error_msg, retry_count, retried_pages, retry_errors}.
    had_error is True only after all retry attempts are exhausted on an actual failure."""
    name = source["name"]
    src_ccaa = source.get("ccaa")
    url = source["url"]

    pprint(f"  ↓ {name}  [hasta {max_pages} página(s) × ~100 items]")
    all_results = []
    seen_ids = set()
    pages_done = 0
    had_error = False
    error_msg = None
    retry_count = 0
    retried_pages = []
    retry_errors = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    while url and pages_done < max_pages:
        page_num = pages_done + 1
        page_label_str = f"p{page_num}"
        if not _QUIET:
            page_label = page_label_str if max_pages > 1 else ""
            pprint(f"    {url[:90]}{'…' if len(url) > 90 else ''} {page_label}")

        page_retry_errs = []
        root = None
        hard_fail = False

        for attempt in range(retries + 1):
            if attempt > 0:
                secs = retry_sleep(attempt, retry_delay, retry_backoff)
                pprint(f"    [retry {attempt}/{retries} in {secs:.1f}s] {page_retry_errs[-1]}")
                time.sleep(secs)
                retry_count += 1
                if page_num not in retried_pages:
                    retried_pages.append(page_num)

            try:
                r = session.get(url, timeout=TIMEOUT)
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code < 500 and e.response.status_code != 429:
                    pprint(f"    [!] {e}")
                    had_error = True
                    error_msg = f"{page_label_str}: {e}"
                    hard_fail = True
                    break
                page_retry_errs.append(str(e))
            except Exception as e:
                if is_retryable_fetch_error(e):
                    page_retry_errs.append(str(e))
                else:
                    pprint(f"    [!] {e}")
                    had_error = True
                    error_msg = f"{page_label_str}: {e}"
                    hard_fail = True
                    break
            else:
                head = r.content[:3000].lower()
                if b"<feed" not in head and b"<entry" not in head:
                    page_retry_errs.append(_describe_non_atom_response(r))
                else:
                    try:
                        root = ET.fromstring(r.content)
                    except ET.ParseError as e:
                        page_retry_errs.append(f"XML parse error: {e}")
                    else:
                        if page_retry_errs:
                            pprint(f"    [retry OK {page_label_str} after {attempt} attempt(s)]")
                            retry_errors.extend(f"{page_label_str}: {err}" for err in page_retry_errs)
                        break  # success

            if attempt == retries:
                last_err = page_retry_errs[-1] if page_retry_errs else "unknown error"
                pprint(f"    [!] {page_label_str} failed after {retries} retries: {last_err}")
                had_error = True
                error_msg = f"{page_label_str}: {last_err}"
                retry_errors.extend(f"{page_label_str}: {err}" for err in page_retry_errs)
                hard_fail = True
                break

        if hard_fail:
            break

        entries = parse_atom_entries(root)
        if not _QUIET:
            pprint(f"    → {len(entries)} entries")

        page_results, discarded = _process_entries(entries, src_ccaa, name, seen_ids, today, min_score)
        if not _QUIET:
            dup_info = f" dup={discarded['dup']}" if discarded["dup"] else ""
            pprint(
                f"    → {len(page_results)} relevantes | "
                f"gate={discarded['title_gate']} score={discarded['low_score']} "
                f"notitle={discarded['no_title']}{dup_info}"
            )

        all_results.extend(page_results)
        pages_done += 1
        url = _get_next_url(root)

        if url and pages_done < max_pages:
            time.sleep(0.4)

    if pages_done > 1 or _QUIET:
        pprint(f"    ── {pages_done} página(s), {len(all_results)} relevantes en total")

    return {
        "results": all_results,
        "pages_done": pages_done,
        "had_error": had_error,
        "error_msg": error_msg,
        "retry_count": retry_count,
        "retried_pages": retried_pages,
        "retry_errors": retry_errors,
    }


def _merge_discarded(total: dict, delta: dict) -> None:
    """Accumulate integer counters and low_score_by_score dict from delta into total."""
    for k in ("no_title", "title_gate", "low_score", "dup",
              "observed_entries_count", "candidate_id_count"):
        total[k] = total.get(k, 0) + delta.get(k, 0)
    for sk, cnt in delta.get("low_score_by_score", {}).items():
        total["low_score_by_score"][sk] = total["low_score_by_score"].get(sk, 0) + cnt


# ─────────────────────────────────────────────────────────────────────────────
# FETCH: LOCAL (atoms sueltos + ZIPs)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_local_dir(local_dir: Path, min_score: int, t_start: float,
                    max_local_atoms: int = 0):
    pprint(f"  ↓ LOCAL  [{local_dir}]")
    if not local_dir.exists():
        pprint("    [!] La carpeta no existe")
        return []

    atom_files = sorted(local_dir.rglob("*.atom"))
    zip_files  = sorted(local_dir.rglob("*.zip"))
    pprint(f"    → detectados {len(atom_files)} .atom sueltos y {len(zip_files)} .zip")

    all_results = []
    seen_ids    = set()
    today       = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    processed_atom = 0
    processed_zip_members = 0
    total_rejected = {
        "no_title": 0, "title_gate": 0, "low_score": 0, "dup": 0,
        "observed_entries_count": 0, "candidate_id_count": 0,
        "low_score_by_score": {},
    }
    total_discard_evidence = []
    atoms_done  = 0
    cap_reached = False

    # ── .atom sueltos ──────────────────────────────────────────────────────
    if atom_files:
        pprint(f"    Procesando {len(atom_files)} .atom sueltos…")
        for i, atom_file in enumerate(atom_files, 1):
            try:
                root = ET.parse(atom_file).getroot()
                entries = parse_atom_entries(root)
                page_results, discarded = _process_entries(
                    entries, None, "LOCAL", seen_ids, today, min_score,
                    discard_evidence=total_discard_evidence)
                all_results.extend(page_results)
                _merge_discarded(total_rejected, discarded)
                processed_atom += 1
            except ET.ParseError as e:
                pprint(f"    [!] XML parse error en {atom_file.name}: {e}")
            except Exception as e:
                pprint(f"    [!] error en {atom_file.name}: {e}")

            atoms_done += 1
            if not _QUIET and (i % 100 == 0 or i == len(atom_files)):
                bar = progress_bar(i, len(atom_files), prefix="    .atom: ")
                pprint(f"{bar}  [{elapsed(t_start)}/ETA {eta(i, len(atom_files), t_start)}]")

            if max_local_atoms > 0 and atoms_done >= max_local_atoms:
                cap_reached = True
                break

    # ── ZIPs ───────────────────────────────────────────────────────────────
    if not cap_reached:
        for zip_idx, zip_path in enumerate(zip_files, 1):
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    atom_names = [n for n in zf.namelist() if n.lower().endswith(".atom")]
                    pprint(f"\n    [{zip_idx}/{len(zip_files)}] {zip_path.name}: {len(atom_names)} .atom")

                    zip_relevant_before = len(all_results)
                    zip_rejected = {
                        "no_title": 0, "title_gate": 0, "low_score": 0, "dup": 0,
                        "observed_entries_count": 0, "candidate_id_count": 0,
                        "low_score_by_score": {},
                    }

                    for i, member in enumerate(atom_names, 1):
                        try:
                            with zf.open(member) as fh:
                                root = ET.parse(BytesIO(fh.read())).getroot()
                            entries = parse_atom_entries(root)
                            page_results, discarded = _process_entries(
                                entries, None, "LOCAL-ZIP", seen_ids, today, min_score,
                                discard_evidence=total_discard_evidence)
                            all_results.extend(page_results)
                            processed_zip_members += 1
                            _merge_discarded(zip_rejected, discarded)
                            _merge_discarded(total_rejected, discarded)
                        except ET.ParseError:
                            pass
                        except Exception as e:
                            pprint(f"    [!] {Path(member).name}: {e}")

                        atoms_done += 1

                        if not _QUIET and (i % 10 == 0 or i == len(atom_names)):
                            encontrados = len(all_results) - zip_relevant_before
                            gate = zip_rejected["title_gate"]
                            score = zip_rejected["low_score"]
                            pct = int(100 * i / len(atom_names)) if atom_names else 0
                            filled = int(16 * i / len(atom_names)) if atom_names else 0
                            bar_str = "█" * filled + "░" * (16 - filled)
                            line = (f"    [{bar_str}] {pct}%"
                                    f"  rel={encontrados} gt={gate} sc={score}"
                                    f"  [{elapsed(t_start)}/ETA {eta(i, len(atom_names), t_start)}]")
                            if _NO_PROGRESS:
                                pprint(line)
                            else:
                                pprint(line, end="\r")

                        if max_local_atoms > 0 and atoms_done >= max_local_atoms:
                            cap_reached = True
                            break  # inner member loop; cap message printed in final summary

                    if not _QUIET and not _NO_PROGRESS:
                        pprint("")  # newline after \r bar
                    zip_relevant = len(all_results) - zip_relevant_before
                    gate = zip_rejected["title_gate"]
                    score = zip_rejected["low_score"]
                    notitle = zip_rejected["no_title"]
                    pprint(f"    ✓ {zip_path.name}: {zip_relevant} relevantes | "
                           f"gate={gate} score={score} notitle={notitle}  [{elapsed(t_start)}]")

                    if cap_reached:
                        break  # outer ZIP loop; cap message printed in final summary

            except Exception as e:
                pprint(f"    [!] No se pudo abrir {zip_path.name}: {e}")

    gate_t    = total_rejected["title_gate"]
    score_t   = total_rejected["low_score"]
    notitle_t = total_rejected["no_title"]
    dup_t     = total_rejected["dup"]
    pprint(f"\n    ── local: {processed_atom} .atom sueltos + {processed_zip_members} .atom en ZIP")
    pprint(f"    ── local: {len(all_results)} relevantes  [{elapsed(t_start)}]")
    pprint(f"    ── rechazados: gate={gate_t} score={score_t} notitle={notitle_t} dup={dup_t}")
    if cap_reached:
        pprint(f"    [cap] Detenido tras {atoms_done} .atom (--max-local-atoms {max_local_atoms})")

    accepted_count  = len(all_results)
    discarded_count = gate_t + score_t + notitle_t + dup_t
    local_stats = {
        "observed_entries_count": total_rejected["observed_entries_count"],
        "candidate_id_count": total_rejected["candidate_id_count"],
        "accepted_count": accepted_count,
        "discarded_count": discarded_count,
        "discard_reason_distribution": {
            "no_title": notitle_t,
            "title_gate": gate_t,
            "low_score": score_t,
            "dup": dup_t,
        },
        "low_score_by_score": total_rejected["low_score_by_score"],
    }
    return all_results, local_stats


# ─────────────────────────────────────────────────────────────────────────────
# SORT
# ─────────────────────────────────────────────────────────────────────────────

def sort_master_items(items: list) -> list:
    def _sort_key(x):
        return (x.get("data_pub") or "", x.get("rellevancia") or 0, x.get("pressupost") or 0)
    return sorted(items, key=_sort_key, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="ADG Licitaciones Fetcher v2.0")
    ap.add_argument("--output",    default=str(OUTPUT_FILE), help=f"Archivo de salida (default: {OUTPUT_FILE})")
    ap.add_argument("--min-score", type=int, default=MIN_SCORE_DEFAULT, help=f"Puntuación mínima (default: {MIN_SCORE_DEFAULT})")
    ap.add_argument("--pages",     type=int, default=1,   help="Páginas online por feed (rel=next, ~100 items/página).")
    ap.add_argument("--source",    choices=["all", "643", "1044"], default="all", help="Feed online: 643, 1044 o all.")
    ap.add_argument("--local-dir", help="Procesa .atom y .zip recursivamente desde esta carpeta (no hace fetch online).")
    ap.add_argument("--enrich",    action="store_true", help="Scraping de páginas de detalle para adjudicatarios. Lento.")
    ap.add_argument("--dry-run",   action="store_true", help="Mostrar resumen sin guardar.")
    ap.add_argument("--stats",     action="store_true", help="Solo estadísticas, no guardar.")
    ap.add_argument("--max-items", type=int, default=MAX_ITEMS_DEFAULT,
                    help="Límite del maestro (0 = sin límite, default: 0).")
    ap.add_argument("--quiet",            action="store_true", help="Minimal output: phase labels + final stats only.")
    ap.add_argument("--no-progress",      action="store_true", help="No \\r bars; plain log output for CI/pipe.")
    ap.add_argument("--max-local-atoms",  type=int, default=0,
                    help="Stop local .atom processing after N files (smoke test only, 0 = no cap).")
    ap.add_argument("--allow-partial-production-write", action="store_true",
                    help="Allow writing a partial live run result to the production path. Use with caution.")
    ap.add_argument("--retries",       type=int,   default=3,   help="Per-page retry attempts after first failure (default: 3).")
    ap.add_argument("--retry-delay",   type=float, default=2.0, help="Initial retry delay in seconds (default: 2.0).")
    ap.add_argument("--retry-backoff", type=float, default=2.0, help="Exponential backoff multiplier (default: 2.0).")
    args = ap.parse_args()

    global _QUIET, _NO_PROGRESS
    _QUIET = args.quiet
    _NO_PROGRESS = args.no_progress

    t_start = time.time()
    today   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_path = Path(args.output)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    mode = "ZIP_BACKFILL" if args.local_dir else "LIVE_FEED"

    pprint(f"\n{'═'*60}")
    pprint(f"  ADG Licitaciones Fetcher v2.0  [run: {run_id}]")
    pprint(f"  Mode: {mode}")
    pprint(f"  {datetime.now():%Y-%m-%d %H:%M:%S}")
    pprint(f"  Min score:  {args.min_score}  |  Páginas: {args.pages}")
    if not args.local_dir:
        pprint(f"  Retries:    {args.retries} (delay={args.retry_delay}s, backoff={args.retry_backoff}×)")
    pprint(f"  Enrich:     {'SÍ (lento)' if args.enrich else 'NO'}")
    pprint(f"  Local dir:  {args.local_dir or 'NO'}")
    pprint(f"  Max items:  {'sin límite' if not args.max_items else args.max_items}")
    if args.max_local_atoms:
        pprint(f"  Atom cap:   {args.max_local_atoms} .atom (smoke, --max-local-atoms)")
    pprint(f"  Output:     {out_path}")
    pprint(f"{'═'*60}\n")

    previous = load_previous(out_path)
    pprint(f"  Datos anteriores cargados: {len(previous)} items\n")

    all_new_items = []
    _local_stats = None

    # Run-level tracking (live mode only)
    completed_pages_by_source: dict = {}
    failed_pages_by_source: dict = {}
    source_errors: dict = {}
    failed_sources: list = []
    completed_sources: list = []
    requested_sources: list = []
    retry_counts_by_source: dict = {}
    retried_pages_by_source: dict = {}
    retry_errors_by_source: dict = {}

    if args.local_dir:
        _local_items, _local_stats = fetch_local_dir(Path(args.local_dir), args.min_score, t_start,
                                                      max_local_atoms=args.max_local_atoms)
        all_new_items.extend(_local_items)
        pprint("")
        session = build_session() if args.enrich else None
    else:
        session = build_session()
        active_sources = SOURCES if args.source == "all" else [s for s in SOURCES if args.source in s["name"]]
        requested_sources = [s["name"] for s in active_sources]
        for src in active_sources:
            src_result = fetch_source(session, src, args.pages, args.min_score,
                                      retries=args.retries, retry_delay=args.retry_delay,
                                      retry_backoff=args.retry_backoff)
            all_new_items.extend(src_result["results"])
            sname = src["name"]
            completed_pages_by_source[sname] = src_result["pages_done"]
            retry_counts_by_source[sname] = src_result["retry_count"]
            if src_result["retried_pages"]:
                retried_pages_by_source[sname] = src_result["retried_pages"]
            if src_result["retry_errors"]:
                retry_errors_by_source[sname] = src_result["retry_errors"]
            if src_result["had_error"]:
                failed_pages_by_source[sname] = 1
                source_errors[sname] = src_result["error_msg"]
                failed_sources.append(sname)
            else:
                failed_pages_by_source[sname] = 0
                completed_sources.append(sname)
            pprint("")

    # Dedup dentro de la corrida actual (status_rank primero, rellevancia como desempate)
    dedup_new: dict = {}
    for item in all_new_items:
        key = item.get("canonical_key") or item.get("id")
        if key not in dedup_new:
            dedup_new[key] = item
        else:
            existing = dedup_new[key]
            item_rank = STATUS_RANK.get(item.get("notice_type", "UNKNOWN"), 0)
            exist_rank = STATUS_RANK.get(existing.get("notice_type", "UNKNOWN"), 0)
            if item_rank > exist_rank or (
                item_rank == exist_rank and item.get("rellevancia", 0) > existing.get("rellevancia", 0)
            ):
                dedup_new[key] = item
    dedup_removed = len(all_new_items) - len(dedup_new)
    if dedup_removed:
        pprint(f"  → {dedup_removed} duplicados eliminados en esta corrida → {len(dedup_new)} únicos")

    merged, merge_stats = merge_master_v2(list(dedup_new.values()), previous, today)

    if args.enrich:
        pprint("\n  ── Enriqueciendo adjudicatarios (--enrich) ──")
        merged = enrich_adjudicataris(merged, session or build_session())

    merged = sort_master_items(merged)

    # Cap opcional (0 = sin límite)
    if args.max_items and args.max_items > 0 and len(merged) > args.max_items:
        pprint(f"  ⚠ Cap aplicado: {len(merged)} → {args.max_items} items")
        merged = merged[:args.max_items]

    # ── Estadísticas finales ───────────────────────────────────────────────
    vigentes    = sum(1 for x in merged if x.get("estat") == "Vigente")
    adjudicados = sum(1 for x in merged if x.get("estat") == "Adjudicado")
    con_ppto    = sum(1 for x in merged if x.get("pressupost"))
    vol_total   = sum(x.get("pressupost", 0) or 0 for x in merged)
    vol_medio   = vol_total / con_ppto if con_ppto else 0

    pprint(f"\n{'─'*50}")
    pprint(f"  Items finales:      {len(merged)}")
    pprint(f"  Nuevos:             {merge_stats['new']}")
    pprint(f"  Actualizados:       {merge_stats['updated']}")
    pprint(f"  Preservados:        {merge_stats['preserved']}")
    pprint(f"  Vigentes:           {vigentes}")
    pprint(f"  Adjudicados:        {adjudicados}")
    pprint(f"  Con presupuesto:    {con_ppto} ({100 * con_ppto // max(len(merged), 1)}%)")
    pprint(f"  Volumen total:      {vol_total:,.0f} €")
    pprint(f"  Presupuesto medio:  {vol_medio:,.0f} €")
    pprint(f"  Con adjudicatario:  {sum(1 for x in merged if x.get('adjudicatari'))}")

    disc_counter = Counter()
    for x in merged:
        for d in x.get("disciplines", []):
            disc_counter[d] += 1
    if disc_counter:
        pprint("  Disciplinas: " + " | ".join(f"{k}:{v}" for k, v in disc_counter.most_common(10)))

    years = sorted({(x.get("data_pub") or "")[:4] for x in merged if x.get("data_pub")})
    if years:
        pprint(f"  Rango años:         {years[0]}–{years[-1]}")

    pprint(f"  Tiempo total:       {elapsed(t_start)}")
    pprint(f"{'─'*50}\n")

    # ── Run status (live mode only; local mode is always FULL_SUCCESS) ────────
    is_partial = False
    run_status = "FULL_SUCCESS"
    operator_warning = None

    if not args.local_dir:
        is_partial = len(failed_sources) > 0
        if failed_sources:
            run_status = "PARTIAL_SUCCESS" if all_new_items else "EMPTY_FAILURE"
            operator_warning = (
                f"PARTIAL RUN — failed sources: {', '.join(failed_sources)}. "
                "Do not promote to production without --allow-partial-production-write."
            )
            pprint(f"\n  [PARTIAL RUN] failed_sources: {failed_sources}")
            if source_errors:
                for sname, err in source_errors.items():
                    pprint(f"    {sname}: {err}")
        elif not all_new_items:
            run_status = "EMPTY_SUCCESS"

    if args.stats or args.dry_run:
        if args.dry_run:
            for x in merged[:20]:
                pprint(f"  [{x['rellevancia']:3d}] {x['titol'][:90]}")
        pprint("  (--stats/--dry-run: no se guarda)")
        return

    # ── Production guard ──────────────────────────────────────────────────────
    if not args.local_dir and is_partial:
        try:
            is_prod = out_path.resolve() == _PRODUCTION_PATH.resolve()
        except OSError:
            is_prod = out_path == _PRODUCTION_PATH
        if is_prod and not args.allow_partial_production_write:
            pprint(f"\n  [BLOCKED] Partial live run refused for production path: {out_path}")
            pprint(f"  failed_sources: {failed_sources}")
            pprint("  Use --allow-partial-production-write to override.")
            sys.exit(1)
        elif is_prod:
            pprint("  [WARNING] --allow-partial-production-write active. Writing partial run to production.")

    # ── Build envelope ────────────────────────────────────────────────────────
    envelope = {
        "generated_at":    now_iso,
        "count":           len(merged),
        "fetcher_version": "2.0",
        "run_status":      run_status,
        "run_mode":        "ZIP_BACKFILL" if args.local_dir else "LIVE_FEED",
        "is_partial":      is_partial,
    }

    if not args.local_dir:
        envelope["requested_sources"]         = requested_sources
        envelope["completed_sources"]         = completed_sources
        envelope["failed_sources"]            = failed_sources
        envelope["requested_pages"]           = args.pages
        envelope["completed_pages_by_source"] = completed_pages_by_source
        envelope["failed_pages_by_source"]    = failed_pages_by_source
        envelope["source_errors"]             = source_errors
        envelope["operator_warning"]          = operator_warning
        envelope["retry_policy"]              = {"retries": args.retries, "delay": args.retry_delay, "backoff": args.retry_backoff}
        envelope["retry_counts_by_source"]    = retry_counts_by_source
        envelope["retried_pages_by_source"]   = retried_pages_by_source
        envelope["retry_errors_by_source"]    = retry_errors_by_source

    if _local_stats is not None:
        envelope["observed_entries_count"]    = _local_stats["observed_entries_count"]
        envelope["candidate_id_count"]        = _local_stats["candidate_id_count"]
        envelope["accepted_count"]            = _local_stats["accepted_count"]
        envelope["discarded_count"]           = _local_stats["discarded_count"]
        envelope["discard_reason_distribution"] = _local_stats["discard_reason_distribution"]
        envelope["low_score_by_score"]        = _local_stats["low_score_by_score"]

    envelope["data"] = merged

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)

    size_kb = out_path.stat().st_size // 1024
    pprint(f"  ✅ Guardado en {out_path} ({size_kb} KB)  [{elapsed(t_start)}]")
    if is_partial:
        pprint(f"  ⚠  is_partial=true — output contains partial run results.")


if __name__ == "__main__":
    main()