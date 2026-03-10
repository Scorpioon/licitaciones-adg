#!/usr/bin/env python3
"""
fetch_licitaciones.py — ADG Licitaciones v1.4
Solo Atom de PLACSP. Mantiene intacto el esquema de salida que consume index.html.

Novedades v1.4:
- Salida en formato envelope: {"data": [...], "generated_at": "ISO 8601"}
  → index.html v1.4 muestra la fecha real de la última actualización.
- Campo `adjudicatari`: extrae el adjudicatario del blob XML cuando aparece.
- Campo `historial`: array de {data, estat, nota} que crece en cada ejecución.
  → Cuando una licitación cambia de Vigente → Adjudicado/Desierta, se registra.
- Detección de estado: intenta extraer "Adjudicado"/"Desierta" del contenido del entry.
- Merge con data.json existente: preserva historial y adjudicatari conocidos.
- Resto de lógica idéntica a v1.3 (CPV prefix, CPV_VALID_STARTS, scoring).
"""

import argparse
import hashlib
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    sys.exit("Instala requests:  python -m pip install requests")

OUTPUT_FILE = Path("data.json")
MIN_SCORE   = 15
MAX_ITEMS   = 500
TIMEOUT     = 45
HEADERS     = {
    "User-Agent": "ADG-Licitaciones/1.4 (+https://adg-fad.org)",
    "Accept":     "application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
}

SOURCES = [
    {
        "name": "PLACSP",
        "ccaa": None,
        "kind": "atom",
        "url":  "https://contrataciondelestado.es/sindicacion/sindicacion_643/"
                "licitacionesPerfilesContratanteCompleto3.atom",
    }
]

CPV = {
    "79930000","79931000","79932000","79933000","79935000",
    "79340000","79341000","79341100","79341200","79341400","79342000","79342200",
    "79416000","79416100","79416200",
    "79800000","79810000","79811000","79812000","79820000","79821000","79822000","79823000",
    "22000000","22100000","22140000","22150000","22160000","22462000","22900000",
    "79961000","79961100","79961200","79961300",
    "92111000","92111200","92111210","92111300",
    "72413000","72415000","72420000",
    "79950000","79952000","79956000",
}

KW_EXCLUDE = [
    "obra civil","construcción de edificio","suministro de energía","limpieza de edificios",
    "seguridad privada","catering","residuos","transporte de viajeros","asistencia sanitaria",
]

STRONG_KW = [
    "diseño gráfico","disseny gràfic","identidad corporativa","identitat corporativa",
    "imagen corporativa","imatge corporativa","manual de identidad","manual de marca",
    "comunicación visual","comunicació visual","diseño editorial","disseny editorial",
    "maquetación","maquetació","infografía","infografia","campaña publicitaria",
    "campanya publicitària","material promocional","material divulgativo","material divulgatiu",
    "cartelería","cartelleria","dípticos","trípticos","diseño web","disseny web",
    "página web","pàgina web","artes gráficas","arts gràfiques","producción gráfica",
    "rotulación","retolació","señalética","senyalètica","producción audiovisual",
    "producció audiovisual","motion graphics","comunicación institucional",
    "comunicación corporativa","relaciones públicas","museografía","museografia",
    "dirección de arte","direcció d'art","ilustración","il·lustració","tipografía",
    "logotipo","logotip",
]

MEDIUM_KW = [
    "branding","marca","editorial","carteles","folletos","fullets","publicidad","publicitat",
    "marketing","impresión","impressió","vídeo","video","fotografía","fotografia",
    "animación","animació","multimedia","exposición","exposició","stand",
]

GENERIC_KW = [
    "web","portal web","sitio web","contenidos digitales","redes sociales","xarxes socials",
    "digital","interfaz","app","aplicación","promoción",
]

DISC_KW = {
    "branding":    ["branding","identidad corporativa","identitat corporativa","logotipo","logotip","logo","manual de marca","manual de identidad"],
    "editorial":   ["editorial","maquetación","maquetació","revista","catálogo","catàleg","folleto","fullet","cartel","cartell","infografía"],
    "web":         ["web","página web","pàgina web","sitio web","portal web","diseño web","disseny web","wordpress"],
    "uxui":        ["ux","ui","experiencia de usuario","usabilidad","interfaz","app","aplicación"],
    "publicitat":  ["publicidad","publicitat","campaña","campanya","marketing","màrqueting","promoción"],
    "senyaletica": ["señalética","senyalètica","rotulación","retolació","señalización","stand","expositor","museografía"],
    "fotografia":  ["fotografía","fotografia","fotográfico","reportaje"],
    "audiovisual": ["audiovisual","vídeo","video","motion","animación","animació","multimedia"],
    "illustracio": ["ilustración","il·lustració","dibujo"],
    "impressio":   ["impresión","impressió","artes gráficas","arts gràfiques","offset","serigrafía"],
}

CCAA_KW = {
    "CT":["cataluña","catalunya","barcelona","girona","lleida","tarragona","generalitat de catalunya"],
    "MD":["madrid","comunidad de madrid","ayuntamiento de madrid"],
    "AN":["andalucía","andalucia","sevilla","málaga","granada","córdoba","junta de andalucía"],
    "PV":["país vasco","pais vasco","euskadi","bilbao","donostia","vitoria","gobierno vasco"],
    "VC":["comunitat valenciana","comunidad valenciana","valencia","alicante","generalitat valenciana"],
    "GA":["galicia","xunta de galicia","vigo","a coruña","santiago"],
    "AR":["aragón","aragon","zaragoza"],"CM":["castilla-la mancha","toledo","albacete"],
    "CL":["castilla y león","valladolid","burgos","salamanca"],"MU":["murcia"],
    "NA":["navarra","pamplona"],"IB":["baleares","illes balears","mallorca"],
    "CN":["canarias","tenerife","las palmas"],"EX":["extremadura","badajoz"],
    "AS":["asturias","oviedo"],"CB":["cantabria","santander"],"RI":["la rioja"],
    "ES":["ministerio","gobierno de españa","estado"],
}

TERR = {
    "AN":"Andalucía","AR":"Aragón","AS":"Asturias","IB":"Baleares","CN":"Canarias",
    "CB":"Cantabria","CM":"Castilla-La Mancha","CL":"Castilla y León","CT":"Catalunya",
    "EX":"Extremadura","GA":"Galicia","RI":"La Rioja","MD":"Madrid","MU":"Murcia",
    "NA":"Navarra","PV":"País Vasco","VC":"C. Valenciana","CE":"Ceuta","ML":"Melilla",
    "ES":"Estatal",
}

CPV_PREFIXES    = {c[:5] for c in CPV}
# Only accept 8-digit numbers from categories genuinely related to design/communication.
# 79=business/advertising/design services, 22=printed matter, 72=IT/web, 92=AV/recreation
# Removed broad categories (34,55,71,73,75,85,90,98,39,32,48) that caused false positives.
CPV_VALID_STARTS = {"79","22","72","92"}
NS_ATOM = "http://www.w3.org/2005/Atom"


# ── SESSION ───────────────────────────────────────────────────────────────
def build_session():
    retry = Retry(
        total=3, connect=3, read=3, status=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("HEAD", "GET", "OPTIONS"),
    )
    s = requests.Session()
    s.headers.update(HEADERS)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://",  HTTPAdapter(max_retries=retry))
    return s


# ── TEXT UTILS ────────────────────────────────────────────────────────────
def strip_html(raw):
    text = html.unescape(raw or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def norm(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()

def kw_match(text, kw):
    text, kw = norm(text), norm(kw)
    if not text or not kw:
        return False
    if kw in {"ux", "ui"}:
        return bool(re.search(rf"(?<![a-záéíóúüñ]){re.escape(kw)}(?![a-záéíóúüñ])", text))
    if len(kw) <= 3 and " " not in kw:
        return bool(re.search(rf"\b{re.escape(kw)}\b", text))
    return kw in text


# ── SCORING ───────────────────────────────────────────────────────────────
def score_item(titulo, desc, cpv_codes):
    title_text = norm(titulo)
    desc_text  = norm(desc)
    full_text  = f"{title_text} {desc_text}".strip()

    score = 0; discs = set(); kws = set()
    strong_hits = medium_hits = generic_hits = 0

    if any(c[:5] in CPV_PREFIXES for c in cpv_codes):
        score += 35; kws.add("CPV:diseño"); strong_hits += 1

    if any(kw_match(full_text, kw) for kw in KW_EXCLUDE):
        score -= 25

    for kw in STRONG_KW:
        if kw_match(title_text, kw):
            score += 12; kws.add(kw); strong_hits += 1
        elif kw_match(desc_text, kw):
            score += 7;  kws.add(kw); strong_hits += 1

    for kw in MEDIUM_KW:
        if kw_match(title_text, kw):
            score += 6; kws.add(kw); medium_hits += 1
        elif kw_match(desc_text, kw):
            score += 3; kws.add(kw); medium_hits += 1

    for kw in GENERIC_KW:
        if kw_match(title_text, kw):
            score += 2; kws.add(kw); generic_hits += 1
        elif kw_match(desc_text, kw):
            score += 1; kws.add(kw); generic_hits += 1

    for disc, keys in DISC_KW.items():
        if any(kw_match(full_text, k) for k in keys):
            discs.add(disc)

    evidence = strong_hits + medium_hits
    if evidence == 0 and generic_hits > 0 and not cpv_codes:
        score -= 10
    if evidence == 1 and generic_hits > 1 and not cpv_codes:
        score -= 5

    return max(0, min(100, score)), sorted(discs), list(kws)[:12]


# ── FIELD EXTRACTION ──────────────────────────────────────────────────────
def detect_ccaa(src_ccaa, organisme, lloc):
    if src_ccaa:
        return src_ccaa
    text = norm(f"{organisme} {lloc}")
    for code, kws in CCAA_KW.items():
        if any(kw_match(text, k) for k in kws):
            return code
    return "ES"

def parse_budget(text):
    if not text:
        return None
    clean = re.sub(r"[^\d,.-]", "", str(text)).replace(".", "").replace(",", ".")
    try:
        v = float(clean)
        return v if v > 100 else None
    except Exception:
        return None

def ensure_feed_content(content):
    head = content[:3000].lower()
    return (b"<feed" in head) or (b"<entry" in head)

def get_entry_text(entry, tag):
    el = entry.find(f"{{{NS_ATOM}}}{tag}")
    if el is None:
        return ""
    return " ".join(p.strip() for p in el.itertext() if p and p.strip()).strip()

def parse_atom_entries(root):
    entries = root.findall(f"{{{NS_ATOM}}}entry")
    if entries:
        return entries
    return [e for e in root.iter() if str(e.tag).endswith("entry")]

def extract_link(entry):
    for child in entry.iter():
        if str(child.tag).endswith("link") and child.get("href") and child.get("rel") == "alternate":
            return child.get("href", "").strip()
    for child in entry.iter():
        if str(child.tag).endswith("link") and child.get("href"):
            return child.get("href", "").strip()
    return ""

def gather_entry_blob(entry):
    parts = []
    for el in entry.iter():
        if el.text  and el.text.strip():  parts.append(el.text.strip())
        if el.tail  and el.tail.strip():  parts.append(el.tail.strip())
        for attr in ("term","label","title","href"):
            val = el.get(attr)
            if val: parts.append(val.strip())
    return strip_html(" ".join(parts))

def extract_org(blob, desc, title):
    text = f"{blob} || {desc} || {title}"
    patterns = [
        r"(?:órgano de contratación|organo de contratacion)\s*[:\-]\s*([^|.;]{4,140})",
        r"(?:entidad adjudicadora|poder adjudicador)\s*[:\-]\s*([^|.;]{4,140})",
        r"(?:autoridad portuaria de [^|.;]{2,80})",
        r"(?:ayuntamiento de [^|.;]{2,80})",
        r"(?:diputación de [^|.;]{2,80})",
        r"(?:diputacio[nó] de [^|.;]{2,80})",
        r"(?:cabildo de [^|.;]{2,80})",
        r"(?:universidad de [^|.;]{2,80})",
        r"(?:ministerio de [^|.;]{2,80})",
        r"(?:consorcio de [^|.;]{2,80})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            candidate = m.group(1) if m.groups() else m.group(0)
            candidate = re.sub(r"\s+", " ", candidate).strip(" -:;,.|")
            if len(candidate) >= 4:
                return candidate[:150]
    return ""

def extract_budget(blob):
    for pat in [
        r"(?:presupuesto base de licitaci[oó]n)[^\d]{0,50}(\d[\d\.,]+)\s*€?",
        r"(?:importe de licitaci[oó]n|importe total|valor estimado)[^\d]{0,50}(\d[\d\.,]+)\s*€?",
        r"(?:presupuesto|importe)[^\d]{0,40}(\d[\d\.,]+)\s*€",
        r"(\d[\d\.,]+)\s*€",
    ]:
        m = re.search(pat, blob, re.I)
        if m:
            v = parse_budget(m.group(1))
            if v: return v
    return None

def normalize_date_token(token):
    token = token.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
        return token
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", token):
        return f"{token[6:]}-{token[3:5]}-{token[:2]}"
    return ""

def extract_deadline(blob):
    for pat in [
        r"(?:fecha l[íi]mite|plazo de presentaci[oó]n|plazo presentaci[oó]n|presentaci[oó]n de ofertas|termini)[^\d]{0,40}(\d{4}-\d{2}-\d{2})",
        r"(?:fecha l[íi]mite|plazo de presentaci[oó]n|plazo presentaci[oó]n|presentaci[oó]n de ofertas|termini)[^\d]{0,40}(\d{2}/\d{2}/\d{4})",
    ]:
        m = re.search(pat, blob, re.I)
        if m:
            return normalize_date_token(m.group(1))
    return ""

# ── v1.4.2: extract adjudicatari (ultra-conservative) ────────────────────
#
# APPROACH: PLACSP Atom feeds are messy. False positives (NUTS codes,
# contracting-body names, boilerplate text) are more harmful than missing data.
# Strategy: ONLY extract if there is an EXPLICIT label ("Empresa adjudicataria:",
# "Adjudicatario:", "Winning party:") immediately followed by a plausible name.
# If no explicit label → return "" (no guessing from company suffixes alone,
# since contracting bodies also end in S.L., S.A.U., etc.).
#
_NUTS_RE = re.compile(r'^ES[\s\-]?\d', re.I)

# Phrases that indicate we're reading about the contracting BODY, not the winner
_CONTRACTING_BODY_RE = re.compile(
    r'\b(?:órgano de contrataci[oó]n|entidad adjudicadora|poder adjudicador|'
    r'administraci[oó]n|ayuntamiento|diputaci[oó]n|consell|generalitat|'
    r'mancomunidad|ministerio|subsecretar[ií]a|direcci[oó]n general|'
    r'autoridad portuaria|universidad|cabildo|consorcio)\b',
    re.I
)

# Boilerplate strings found in PLACSP that are NOT company names
_BOILERPLATE_FRAGMENTS = [
    "presentará una declaración",
    "declaración responsable",
    "volumen anual de negocios",
    "importe de adjudicación",
    "objeto del contrato",
    "plazo de ejecución",
    "criterios de adjudicación",
    "tipo de procedimiento",
]

# Explicit winning-party labels ONLY (not "empresa" alone, which can be contracting body)
_WINNER_LABEL_RE = re.compile(
    r"(?:empresa adjudicataria|licitador adjudicatario|adjudicatario\s*[:\-]|"
    r"adjudicado a\s*[:\-]|licitador seleccionado|licitador ganador|"
    r"winning party|empresa contratista|contratista adjudicatario)"
    r"\s*[:\-]?\s*"
    r"([A-Za-záéíóúäëïöüàèìòùÁÉÍÓÚÜÑñçÇÀÈÌÒÙ][^\n\r|<>{}\[\]]{4,120}?)(?=\s*(?:\n|\r|$|NIF\b|CIF\b|\b\d{8}[A-Z]\b|\bES\s*\d))",
    re.I
)


def extract_adjudicatari(blob: str) -> str:
    """
    Extrae el nombre del adjudicatario SOLO cuando hay una etiqueta explícita.
    Es conservador a propósito: mejor no extraer que extraer mal.
    """
    m = _WINNER_LABEL_RE.search(blob)
    if not m:
        return ""

    raw = re.sub(r"\s+", " ", m.group(1)).strip(" -:;,.|\"'")

    # Reject if too short
    if len(raw) < 5:
        return ""
    # Reject NUTS codes
    if _NUTS_RE.match(raw):
        return ""
    # Reject if starts with digit
    if raw[0].isdigit():
        return ""
    # Reject if it's a contracting body, not a winning company
    if _CONTRACTING_BODY_RE.search(raw):
        return ""
    # Reject known PLACSP boilerplate fragments
    raw_low = raw.lower()
    if any(frag in raw_low for frag in _BOILERPLATE_FRAGMENTS):
        return ""
    # Must have at least 2 words
    if len(raw.split()) < 2:
        return ""
    # Reject if all-caps-code-like tokens (e.g. "ES MALAGA 29016")
    tokens = raw.split()
    if all(re.match(r'^[A-Z0-9\-]{2,}$', tok) for tok in tokens[:3]):
        return ""

    return raw[:120]


# ── NEW v1.4: detect estat ───────────────────────────────────────────────
def extract_estat(blob):
    """
    Detecta si el entry indica que la licitación está Adjudicada o Desierta.
    Por defecto devuelve Vigente.
    """
    b = norm(blob)
    if re.search(r"\badjudica(?:do|da|t|ción)\b", b):
        return "Adjudicado"
    if any(w in b for w in ["desierta","deserta","sin adjudicar","sense adjudicació"]):
        return "Desierta"
    return "Vigente"

# ── NEW v1.4: load previous data for merge ───────────────────────────────
def load_previous(path: Path) -> dict:
    """
    Carga data.json existente y devuelve un dict {item_id: item}.
    Soporta tanto el formato antiguo (array) como el nuevo envelope.
    """
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw.get("data", raw) if isinstance(raw, dict) else raw
        if not isinstance(items, list):
            return {}
        return {item["id"]: item for item in items if "id" in item}
    except Exception as e:
        print(f"  [!] No se pudo leer data.json anterior: {e}")
        return {}

# ── NEW v1.4: merge historial + adjudicatari ──────────────────────────────
def merge_with_previous(new_items: list, previous: dict, today: str) -> list:
    """
    Para cada item nuevo:
    - Si ya existía: preserva historial, detecta cambios de estado, actualiza adjudicatari.
    - Si es nuevo: añade entrada inicial al historial.
    """
    result = []
    for item in new_items:
        prev = previous.get(item["id"])
        if prev:
            # Preserve historial from previous run
            item["historial"] = prev.get("historial", [])
            # Preserve adjudicatari if we found a better one now
            if not item.get("adjudicatari") and prev.get("adjudicatari"):
                item["adjudicatari"] = prev["adjudicatari"]
            # Detect state change
            prev_estat = prev.get("estat", "Vigente")
            new_estat  = item.get("estat", "Vigente")
            if new_estat != prev_estat:
                entry = {
                    "data":  today,
                    "estat": new_estat,
                    "nota":  f"Cambio de estado: {prev_estat} → {new_estat}",
                }
                if item.get("adjudicatari") and new_estat == "Adjudicado":
                    entry["nota"] = f"Adjudicado a {item['adjudicatari']}"
                item["historial"].append(entry)
        else:
            # Brand new item — create initial historial entry
            item["historial"] = [{
                "data":  item.get("data_pub", today),
                "estat": item.get("estat", "Vigente"),
                "nota":  "Publicación",
            }]
        result.append(item)
    return result


# ── ATOM FETCHER ─────────────────────────────────────────────────────────
def fetch_atom(session, source):
    name, ccaa, url = source["name"], source.get("ccaa"), source["url"]
    print(f"  ↓ {name}: {url[:72]}…")
    try:
        r = session.get(url, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        print(f"    [!] {e}"); return []

    if not ensure_feed_content(r.content):
        print(f"    [!] respuesta no parece Atom/XML ({r.headers.get('content-type','?')})"); return []

    try:
        root = ET.fromstring(r.content)
    except ET.ParseError as e:
        print(f"    [!] XML: {e}"); return []

    entries  = parse_atom_entries(root)
    print(f"    → {len(entries)} entries")
    results  = []
    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for entry in entries:
        try:
            titulo = get_entry_text(entry, "title")
            if not titulo:
                continue

            url_item  = extract_link(entry)
            item_id   = (get_entry_text(entry, "id") or url_item
                         or hashlib.md5(titulo.encode("utf-8")).hexdigest())
            fecha_pub = (get_entry_text(entry, "published") or get_entry_text(entry, "updated") or today)[:10]
            raw       = get_entry_text(entry, "content") or get_entry_text(entry, "summary")
            desc      = strip_html(raw)[:1000]
            blob      = gather_entry_blob(entry)

            # CPV: only real codes (8 digits, valid category prefix)
            cpv_raw   = re.findall(r"\b([1-9]\d{7})\b", f"{blob} {titulo}")
            cpv_codes = list(dict.fromkeys(c for c in cpv_raw if c[:2] in CPV_VALID_STARTS))

            organisme   = extract_org(blob, desc, titulo)
            pressupost  = extract_budget(blob)
            fecha_limit = extract_deadline(blob)
            estat       = extract_estat(blob)
            adjudicatari = extract_adjudicatari(blob) if estat == "Adjudicado" else ""

            score, discs, kws = score_item(titulo, blob or desc, cpv_codes)
            if score < MIN_SCORE:
                continue

            item_ccaa = detect_ccaa(ccaa, organisme, blob)
            lloc  = TERR.get(item_ccaa, "")
            tipus = "Servicios"
            low   = norm(f"{titulo} {blob}")
            if "suministro" in low or "subministrament" in low:
                tipus = "Suministros"

            results.append({
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
                "historial":    [],   # filled by merge_with_previous
            })
        except Exception as e:
            print(f"    [!] entry: {e}")

    print(f"    → {len(results)} relevantes")
    return results


# ── MAIN ─────────────────────────────────────────────────────────────────
def main():
    global MIN_SCORE

    ap = argparse.ArgumentParser(description="ADG Licitaciones Fetcher v1.4.2")
    ap.add_argument("--stats",     action="store_true", help="Solo mostrar stats, no guardar")
    ap.add_argument("--output",    default=str(OUTPUT_FILE))
    ap.add_argument("--min-score", type=int, default=MIN_SCORE)
    ap.add_argument("--pages",     type=int, default=1,
                    help="Número de páginas a fetchear (cada página ~100 items). Útil para backfill histórico.")
    args     = ap.parse_args()
    MIN_SCORE = args.min_score

    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_path = Path(args.output)

    print(f"\n{'═'*55}")
    print(f"  ADG Licitaciones Fetcher v1.4.2")
    print(f"  {datetime.now():%Y-%m-%d %H:%M}")
    print(f"  Fuentes: Atom PLACSP | páginas: {args.pages}")
    print(f"  Min score: {MIN_SCORE}")
    print(f"{'═'*55}\n")

    # Load previous data for merge
    previous = load_previous(out_path)
    print(f"  Datos anteriores: {len(previous)} items\n")

    # Expand SOURCES with pagination (numItems = pages * 100)
    session   = build_session()
    all_items = []
    for src in SOURCES:
        paginated_src = dict(src)
        if args.pages > 1:
            num_items = min(args.pages * 100, 500)  # PLACSP max ~500
            sep = "&" if "?" in paginated_src["url"] else "?"
            paginated_src["url"] = f"{paginated_src['url']}{sep}numItems={num_items}"
            print(f"  📄 Modo histórico: solicitando {num_items} items")
        all_items.extend(fetch_atom(session, paginated_src))
        print()

    # Dedup (keep highest score per id)
    seen = {}
    for item in all_items:
        key = item["id"] or item["url"] or hashlib.md5(item["titol"].encode()).hexdigest()
        if key not in seen or item["rellevancia"] > seen[key]["rellevancia"]:
            seen[key] = item

    unique = sorted(
        seen.values(),
        key=lambda x: (-x["rellevancia"], -(x["pressupost"] or 0), x.get("data_limit") or "9999-99-99"),
    )[:MAX_ITEMS]

    # Merge historial + adjudicatari with previous run
    unique = merge_with_previous(unique, previous, today)

    # Also carry forward items from previous run that weren't in this fetch
    # (e.g. Adjudicados that fall off the feed but we want to keep in history)
    prev_ids      = {item["id"] for item in unique}
    carried_over  = []
    for pid, pitem in previous.items():
        if pid not in prev_ids:
            carried_over.append(pitem)
    # Keep carried-over items sorted after fresh ones, up to MAX_ITEMS total
    combined = unique + sorted(
        carried_over,
        key=lambda x: (-x.get("rellevancia",0), x.get("data_limit") or "9999")
    )
    combined = combined[:MAX_ITEMS]

    # ── Stats ────────────────────────────────────────────────────────────
    adj_count   = sum(1 for x in combined if x.get("estat") == "Adjudicado")
    new_today   = sum(1 for x in combined if x.get("data_pub","") == today)

    print(f"{'─'*40}")
    print(f"  Total único:       {len(combined)}")
    print(f"  Con ppto:          {sum(1 for x in combined if x.get('pressupost'))}")
    print(f"  Alta rel (≥70):    {sum(1 for x in combined if x.get('rellevancia',0) >= 70)}")
    print(f"  Adjudicados:       {adj_count}")
    print(f"  Nuevos hoy:        {new_today}")
    print(f"  Carried-over:      {len(carried_over)}")
    print("  Fuentes:")
    for s, n in Counter(x["font"] for x in combined).most_common():
        print(f"    {s:<20} {n}")
    print("  CCAA:")
    for c, n in Counter(x["ccaa"] for x in combined).most_common(8):
        print(f"    {TERR.get(c, c):<25} {n}")

    if args.stats:
        print("\n  (--stats: no guardado)")
        return

    # ── Write envelope ───────────────────────────────────────────────────
    envelope = {
        "generated_at": now_iso,
        "count":        len(combined),
        "data":         combined,
    }
    out_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n✅ {out_path.resolve()} ({out_path.stat().st_size // 1024}KB)")
    print(f"   {len(combined)} licitaciones · generated_at: {now_iso}\n")


if __name__ == "__main__":
    main()
