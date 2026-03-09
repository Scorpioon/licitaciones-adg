#!/usr/bin/env python3
"""
fetch_licitaciones.py — ADG Licitaciones v1.3
Solo Atom de PLACSP. Mantiene intacto el esquema de salida que consume index.html.

Cambios v1.3:
- Sigue usando solo Atom de PLACSP.
- Mantiene exactamente las mismas claves de salida JSON.
- Endurece el scoring para reducir falsos positivos con términos demasiado genéricos.
- Intenta extraer mejor organismo, presupuesto y fecha límite desde el payload completo del entry.

Cambios v1.3:
- Match CPV por prefijo de familia (5 dígitos) — captura subcódigos de la misma familia.
- Filtro CPV_VALID_STARTS — elimina falsos positivos de IDs de URL que coincidían con el regex.
- Resultado esperado: más licitaciones relevantes, menos ruido.
"""

import argparse
import hashlib
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    sys.exit("Instala requests: python -m pip install requests")

OUTPUT_FILE = Path("data.json")
MIN_SCORE = 15
MAX_ITEMS = 500
TIMEOUT = 45
HEADERS = {
    "User-Agent": "ADG-Licitaciones/1.3 (+https://adg-fad.org)",
    "Accept": "application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
}

SOURCES = [
    {
        "name": "PLACSP",
        "ccaa": None,
        "kind": "atom",
        "url": "https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom",
    }
]

CPV = {
    "79930000","79931000","79932000","79933000","79935000",
    "79340000","79341000","79341100","79341200","79341400","79342000","79342200",
    "79416000","79416100","79416200",
    "79800000","79810000","79811000","79812000","79820000","79821000","79822000","79823000",
    "22000000","22100000","22140000","22150000","22160000","22462000","22900000",
    "34928470","34928471",
    "79961000","79961100","79961200","79961300",
    "92111000","92111200","92111210","92111300",
    "72413000","72415000","72420000",
    "79950000","79952000","79956000",
}

KW_EXCLUDE = [
    "obra civil","construcción de edificio","suministro de energía","limpieza de edificios",
    "seguridad privada","catering","residuos","transporte de viajeros","asistencia sanitaria",
]

# Señales fuertes: cuando aparecen suelen apuntar claramente a diseño/comunicación.
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
    "logotipo","logotip"
]

# Señales medias: útiles, pero pueden colar ruido si van solas.
MEDIUM_KW = [
    "branding","marca","editorial","carteles","folletos","fullets","publicidad","publicitat",
    "marketing","impresión","impressió","vídeo","video","fotografía","fotografia",
    "animación","animació","multimedia","exposición","exposició","stand"
]

# Señales genéricas: solo suman si aparecen acompañadas por otras pistas.
GENERIC_KW = [
    "web","portal web","sitio web","contenidos digitales","redes sociales","xarxes socials",
    "digital","interfaz","app","aplicación","promoción"
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
    "NA":"Navarra","PV":"País Vasco","VC":"C. Valenciana","CE":"Ceuta","ML":"Melilla","ES":"Estatal",
}

# Prefijos de familia CPV (5 dígitos) para match más amplio
CPV_PREFIXES = {c[:5] for c in CPV}

# Prefijos de 2 dígitos que corresponden a categorías reales de diseño/comunicación
CPV_VALID_STARTS = {
    '79','22','34','72','92','55','71','73','75','85','90','98','39','32','48'
}

NS_ATOM = "http://www.w3.org/2005/Atom"


def build_session():
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("HEAD", "GET", "OPTIONS"),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.headers.update(HEADERS)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def strip_html(raw):
    text = html.unescape(raw or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def keyword_match(text, kw):
    text = normalize_text(text)
    kw = normalize_text(kw)
    if not text or not kw:
        return False
    if kw in {"ux", "ui"}:
        return bool(re.search(rf"(?<![a-záéíóúüñ]){re.escape(kw)}(?![a-záéíóúüñ])", text))
    if len(kw) <= 3 and " " not in kw:
        return bool(re.search(rf"\b{re.escape(kw)}\b", text))
    return kw in text


def score_item(titulo, desc, cpv_codes):
    title_text = normalize_text(titulo)
    desc_text = normalize_text(desc)
    full_text = f"{title_text} {desc_text}".strip()

    score = 0
    discs = set()
    kws = set()
    strong_hits = 0
    medium_hits = 0
    generic_hits = 0

    if any(c[:5] in CPV_PREFIXES for c in cpv_codes):
        score += 35
        kws.add("CPV:diseño")
        strong_hits += 1

    for kw in KW_EXCLUDE:
        if keyword_match(full_text, kw):
            score -= 25
            break

    for kw in STRONG_KW:
        if keyword_match(title_text, kw):
            score += 12
            kws.add(kw)
            strong_hits += 1
        elif keyword_match(desc_text, kw):
            score += 7
            kws.add(kw)
            strong_hits += 1

    for kw in MEDIUM_KW:
        if keyword_match(title_text, kw):
            score += 6
            kws.add(kw)
            medium_hits += 1
        elif keyword_match(desc_text, kw):
            score += 3
            kws.add(kw)
            medium_hits += 1

    for kw in GENERIC_KW:
        if keyword_match(title_text, kw):
            score += 2
            kws.add(kw)
            generic_hits += 1
        elif keyword_match(desc_text, kw):
            score += 1
            kws.add(kw)
            generic_hits += 1

    for disc, keys in DISC_KW.items():
        if any(keyword_match(full_text, k) for k in keys):
            discs.add(disc)

    # Penaliza resultados que entran solo por señales flojitas / genéricas.
    evidence = strong_hits + medium_hits
    if evidence == 0 and generic_hits > 0 and not cpv_codes:
        score -= 10
    if evidence == 1 and generic_hits > 1 and not cpv_codes:
        score -= 5

    return max(0, min(100, score)), sorted(discs), list(kws)[:12]


def detect_ccaa(src_ccaa, organisme, lloc):
    if src_ccaa:
        return src_ccaa
    text = normalize_text(f"{organisme} {lloc}")
    for code, kws in CCAA_KW.items():
        if any(keyword_match(text, k) for k in kws):
            return code
    return "ES"


def parse_budget(text):
    if not text:
        return None
    clean = re.sub(r"[^\d,.-]", "", str(text)).replace(".", "").replace(",", ".")
    try:
        value = float(clean)
        return value if value > 100 else None
    except Exception:
        return None


def ensure_feed_content(content):
    head = content[:3000].lower()
    return (b"<feed" in head) or (b"<entry" in head)


def get_entry_text(entry, tag):
    el = entry.find(f"{{{NS_ATOM}}}{tag}")
    if el is None:
        return ""
    return " ".join(part.strip() for part in el.itertext() if part and part.strip()).strip()


def parse_atom_entries(root):
    entries = root.findall(f"{{{NS_ATOM}}}entry")
    if entries:
        return entries
    return [el for el in root.iter() if str(el.tag).endswith("entry")]


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
    for elem in entry.iter():
        if elem.text and elem.text.strip():
            parts.append(elem.text.strip())
        if elem.tail and elem.tail.strip():
            parts.append(elem.tail.strip())
        for attr in ("term", "label", "title", "href"):
            val = elem.get(attr)
            if val:
                parts.append(val.strip())
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
    patterns = [
        r"(?:presupuesto base de licitación|presupuesto base de licitacion)[^\d]{0,50}(\d[\d\.,]+)\s*€?",
        r"(?:importe de licitación|importe de licitacion|importe total|valor estimado)[^\d]{0,50}(\d[\d\.,]+)\s*€?",
        r"(?:presupuesto|importe)[^\d]{0,40}(\d[\d\.,]+)\s*€",
        r"(\d[\d\.,]+)\s*€",
    ]
    for pat in patterns:
        m = re.search(pat, blob, re.I)
        if m:
            value = parse_budget(m.group(1))
            if value:
                return value
    return None


def normalize_date_token(token):
    token = token.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
        return token
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", token):
        return f"{token[6:]}-{token[3:5]}-{token[:2]}"
    return ""


def extract_deadline(blob):
    patterns = [
        r"(?:fecha límite|fecha limite|plazo de presentación|plazo presentación|presentación de ofertas|presentacion de ofertas|termini)[^\d]{0,40}(\d{4}-\d{2}-\d{2})",
        r"(?:fecha límite|fecha limite|plazo de presentación|plazo presentación|presentación de ofertas|presentacion de ofertas|termini)[^\d]{0,40}(\d{2}/\d{2}/\d{4})",
    ]
    for pat in patterns:
        m = re.search(pat, blob, re.I)
        if m:
            return normalize_date_token(m.group(1))
    return ""


def fetch_atom(session, source):
    name, ccaa, url = source["name"], source.get("ccaa"), source["url"]
    print(f"  ↓ {name}: {url[:72]}…")
    try:
        r = session.get(url, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        print(f"    [!] {e}")
        return []

    if not ensure_feed_content(r.content):
        print(f"    [!] respuesta no parece Atom/XML ({r.headers.get('content-type','?')})")
        return []

    try:
        root = ET.fromstring(r.content)
    except ET.ParseError as e:
        print(f"    [!] XML: {e}")
        return []

    entries = parse_atom_entries(root)
    print(f"    → {len(entries)} entries")
    results = []

    for entry in entries:
        try:
            titulo = get_entry_text(entry, "title")
            if not titulo:
                continue

            url_item = extract_link(entry)
            item_id = (get_entry_text(entry, "id") or url_item or hashlib.md5(titulo.encode("utf-8")).hexdigest())
            fecha_pub = (get_entry_text(entry, "published") or get_entry_text(entry, "updated"))[:10]
            raw = get_entry_text(entry, "content") or get_entry_text(entry, "summary")
            desc = strip_html(raw)[:1000]
            blob = gather_entry_blob(entry)

            # Extraer solo CPVs reales (no IDs de URL): 8 dígitos con prefijo de categoría válida
            cpv_raw = re.findall(r"\b([1-9]\d{7})\b", f"{blob} {titulo}")
            cpv_codes = list(dict.fromkeys(
                c for c in cpv_raw if c[:2] in CPV_VALID_STARTS
            ))
            organisme = extract_org(blob, desc, titulo)
            pressupost = extract_budget(blob)
            fecha_limite = extract_deadline(blob)

            score, discs, kws = score_item(titulo, blob or desc, cpv_codes)
            if score < MIN_SCORE:
                continue

            item_ccaa = detect_ccaa(ccaa, organisme, blob)
            lloc = TERR.get(item_ccaa, "")
            tipus = "Servicios"
            low = normalize_text(f"{titulo} {blob}")
            if "suministro" in low or "subministrament" in low:
                tipus = "Suministros"

            results.append({
                "id": item_id[:80],
                "titol": titulo[:200],
                "organisme": organisme[:150],
                "tipus": tipus,
                "pressupost": pressupost,
                "disciplines": discs,
                "ccaa": item_ccaa,
                "lloc": lloc,
                "data_pub": fecha_pub,
                "data_limit": fecha_limite,
                "estat": "Vigente",
                "rellevancia": score,
                "url": url_item[:300],
                "font": name,
                "kw": kws,
                "cpv": ", ".join(cpv_codes[:3]),
            })
        except Exception as e:
            print(f"    [!] entry: {e}")

    print(f"    → {len(results)} relevantes")
    return results


def main():
    global MIN_SCORE

    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--output", default=str(OUTPUT_FILE))
    ap.add_argument("--min-score", type=int, default=MIN_SCORE)
    args = ap.parse_args()
    MIN_SCORE = args.min_score

    print(f"\n{'═'*55}\n  ADG Licitaciones Fetcher v1.3\n  {datetime.now():%Y-%m-%d %H:%M}\n  Fuentes: solo Atom PLACSP\n  Min score: {MIN_SCORE}\n{'═'*55}\n")

    session = build_session()
    all_items = []
    for src in SOURCES:
        all_items.extend(fetch_atom(session, src))
        print()

    seen = {}
    for item in all_items:
        key = item["id"] or item["url"] or hashlib.md5(item["titol"].encode("utf-8")).hexdigest()
        if key not in seen or item["rellevancia"] > seen[key]["rellevancia"]:
            seen[key] = item

    unique = sorted(
        seen.values(),
        key=lambda x: (-x["rellevancia"], -(x["pressupost"] or 0), x.get("data_limit") or "9999-99-99"),
    )[:MAX_ITEMS]

    print(f"{'─'*40}")
    print(f"  Total único:   {len(unique)}")
    print(f"  Con ppto:      {sum(1 for x in unique if x['pressupost'])}")
    print(f"  Alta rel (≥70):{sum(1 for x in unique if x['rellevancia'] >= 70)}")
    print("  Fuentes:")
    for s, n in Counter(x["font"] for x in unique).most_common():
        print(f"    {s:<20} {n}")
    print("  CCAA:")
    for c, n in Counter(x["ccaa"] for x in unique).most_common(8):
        print(f"    {TERR.get(c, c):<25} {n}")

    if args.stats:
        print("\n  (--stats: no guardado)")
        return

    out = Path(args.output)
    out.write_text(json.dumps(unique, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ {out.resolve()} ({out.stat().st_size//1024}KB) — {len(unique)} licitaciones\n")


if __name__ == "__main__":
    main()
