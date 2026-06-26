#!/usr/bin/env python3
"""
tools/appendix_extractor.py — Appendix extractor (v0.6.50 / p197)

The Appendix layer is the first *document-intelligence* pass built ON TOP of the
DocReader (`docread/1`) extracted text. It is strictly additive / downstream:

  1. Reads a local-only `docread/1` manifest + the gitignored extracted text
     files it points at (`_tmp/docreader/text/<sha>.txt`).
  2. Classifies each document's role from text content (anuncio_placsp / pcap /
     ppt / acta / unknown) using conservative fingerprints.
  3. For the `anuncio_placsp` role only (Stage A scope), extracts conservative,
     evidence-backed header fields (objeto, cpv, valor_estimado, presupuesto,
     duracion, lotes, plazos, criterios, contract_meta, opportunity_flags).
  4. Captures solvencia as EVIDENCE-ONLY (never asserts a value sourced from a
     "Se describe en el pliego" / "Ver apartado del PCAP" pointer).
  5. Defers deep pliego fields (formulas, documentacion_exigida, garantia,
     riesgos) that are not present in the notice.
  6. Emits a local-only `appendix/1` manifest under `_tmp/appendix/`.

Hard guarantees (mirror DocReader's discipline):
  * Pure Python stdlib. No network. No PDF reading. No new downloads. No installs.
  * Never mutates data/licitaciones.json or any production / runtime file.
  * Output is refused unless it resolves under an allowed local root
    (`_tmp/` or `data/fetcher2/`); default `_tmp/appendix/`.
  * Never writes a tracked manifest. production_write_performed is always false.
  * No field value is asserted without >=1 evidence object citing verbatim text.
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter, OrderedDict
from datetime import datetime, timezone

VERSION = "v0.6.50"
SCHEMA = "appendix/1"
SCHEMA_VERSION = "0.1-prototype"
GENERATED_BY_PROMPT = "p197"
SOURCE_SCHEMA = "docread/1"

# --------------------------------------------------------------------------- #
# Safe output guard — output may only land under these local, gitignored roots.
# (Pattern mirrored from tools/docreader.py _is_safe_output.)
# --------------------------------------------------------------------------- #
_SAFE_PREFIXES = [
    os.path.normpath("_tmp"),
    os.path.normpath(os.path.join("data", "fetcher2")),
]
_FORBIDDEN = {
    os.path.normpath(os.path.join("data", "licitaciones.json")),
    os.path.normpath("fetch_licitaciones.py"),
    os.path.normpath(os.path.join("tools", "scheduled_fetch_merge.py")),
    os.path.normpath(os.path.join("tools", "scheduled_run_classify.py")),
    os.path.normpath("app.js"),
    os.path.normpath("shared.js"),
    os.path.normpath("estadisticas.js"),
}

# Fields the v1 extractor attempts for the anuncio_placsp role.
_EXTRACTABLE_V1 = [
    "objeto", "cpv", "valor_estimado", "presupuesto_base", "duracion", "lotes",
    "plazos", "criterios_adjudicacion", "criterios_precio", "criterios_tecnicos",
    "contract_meta", "opportunity_flags",
]
# Deep pliego fields not present in notices — deferred until PCAP/PPT captured.
_DEFERRED_V1 = ["formulas", "documentacion_exigida", "garantia", "riesgos"]
# Evidence-only fields: window captured, value never asserted in v1.
_EVIDENCE_ONLY_V1 = ["solvencia_economica", "solvencia_tecnica"]

_CONF_RANK = {"low": 0, "medium": 1, "high": 2}

# Phrases proving a field only *points at* the pliego, not the value itself.
_POINTER_PHRASES = [
    "se describe en el pliego",
    "ver apartado",
    "ver apartados",
    "ver pcap",
    "conforme pliego",
    "conforme apartado",
    "conforme ccp",
    "del pcap",
    "el pcap",
    "del ccp",
    "error plataforma",
    "no hacer nada",
    "que rige la contratacion",
]


# --------------------------------------------------------------------------- #
# Path safety
# --------------------------------------------------------------------------- #
def _is_safe_output(path):
    repo_root = os.getcwd()
    abspath = os.path.abspath(path)
    try:
        rel = os.path.relpath(abspath, repo_root)
    except ValueError:
        return False, abspath
    norm = os.path.normpath(rel)
    if norm.startswith(".." + os.sep) or norm == "..":
        return False, norm
    if norm in _FORBIDDEN:
        return False, norm
    for prefix in _SAFE_PREFIXES:
        if norm == prefix or norm.startswith(prefix + os.sep):
            return True, norm
    return False, norm


def _ensure_safe_file(path, label):
    ok, norm = _is_safe_output(path)
    if not ok:
        sys.stderr.write(
            "[appendix] REFUSED unsafe output path for %s: %s\n"
            "           allowed roots: %s\n"
            % (label, norm, ", ".join(_SAFE_PREFIXES))
        )
        sys.exit(2)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return norm


# --------------------------------------------------------------------------- #
# Text normalisation helpers
# --------------------------------------------------------------------------- #
def _fold_char(c):
    """Accent-fold a single char, preserving string length where possible so
    spans computed on folded text align with the original text."""
    decomposed = unicodedata.normalize("NFKD", c)
    base = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    if len(base) == 1:
        return base.lower()
    return c.lower() if len(c) == 1 else c


def fold(s):
    """Lowercase, accent-stripped copy of s (length-preserving for Spanish)."""
    return "".join(_fold_char(c) for c in s)


def _clean(s):
    """Strip pdfplumber glyph artifacts and collapse whitespace."""
    s = re.sub(r"\(cid:\d+\)", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def parse_amount(raw):
    """Parse a Spanish-format amount string (e.g. '2.080.000', '145.200', '0')."""
    s = raw.strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def iso_date(dmy):
    """'09/05/2025' -> '2025-05-09' (returns None on malformed input)."""
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", dmy.strip())
    if not m:
        return None
    d, mo, y = m.groups()
    return "%s-%s-%s" % (y, mo, d)


_PAGE_RE = re.compile(r"^---\s*PAGE\s+(\d+)\s*---\s*$")


class DocText:
    """Parsed text of a single extracted document, split into pages/lines."""

    def __init__(self, full_text):
        self.full_text = full_text
        self.lines = []  # list of {page, raw, fold}
        self.page_count = 0
        cur_page = 1
        for raw in full_text.splitlines():
            m = _PAGE_RE.match(raw.strip())
            if m:
                cur_page = int(m.group(1))
                self.page_count = max(self.page_count, cur_page)
                continue
            if raw.strip() == "":
                continue
            self.lines.append({"page": cur_page, "raw": raw, "fold": fold(raw)})
        if self.page_count == 0 and self.lines:
            self.page_count = 1

    @property
    def folded_full(self):
        return fold(self.full_text)


# --------------------------------------------------------------------------- #
# Evidence / field object builders
# --------------------------------------------------------------------------- #
class Ctx:
    """Per-document context carried into every evidence object."""

    def __init__(self, sha, notice_id, key, role, extractor, excerpt_chars):
        self.sha = sha
        self.notice_id = notice_id
        self.key = key
        self.role = role
        self.extractor = extractor
        self.excerpt_chars = excerpt_chars

    def evidence(self, page, excerpt, method, confidence):
        return OrderedDict([
            ("doc_sha256", self.sha),
            ("notice_id", self.notice_id),
            ("canonical_key", self.key),
            ("role", self.role),
            ("page", page),
            ("excerpt", _clean(excerpt)[: self.excerpt_chars]),
            ("extractor", self.extractor),
            ("confidence", confidence),
            ("extraction_method", method),
        ])


def field(value, confidence, method, evidence, status):
    return OrderedDict([
        ("value", value),
        ("confidence", confidence),
        ("extraction_method", method),
        ("field_status", status),
        ("evidence", evidence),
    ])


def null_field(status, method="manual_later"):
    return field(None, None, method, [], status)


# --------------------------------------------------------------------------- #
# Role classifier (content-based, conservative)
# --------------------------------------------------------------------------- #
def classify_role(doc):
    """Return (role, confidence, evidence_snippet). Content fingerprints only.

    Roles: anuncio_placsp (full PLACSP notice) | documento_pliegos (PLACSP pliego
    *index* page that merely lists the PCAP/PPT/ANEXO filenames, NOT their text) |
    anuncio_previo (prior-information notice) | pcap | ppt | acta | unknown.
    Only anuncio_placsp drives field extraction in v1."""
    f = doc.folded_full
    header = " ".join(ln["fold"] for ln in doc.lines[:3])

    # documento_pliegos: PLACSP machine index page. Its header is "Documento de
    # Pliegos"; it enumerates pliego filenames but is NOT the pliego content.
    # Check before anuncio_placsp (it shares the expediente/platform fingerprint).
    if header.startswith("documento de pliegos") or "documento de pliegos" in header:
        return "documento_pliegos", "high", _first_line_with(doc, "documento de pliegos")

    # anuncio_previo: prior-information notice variant ("Anuncio previo").
    if header.startswith("anuncio previo"):
        return "anuncio_previo", "high", _first_line_with(doc, "anuncio previo")

    # anuncio_placsp: the PLACSP machine notice. Most specific — check first.
    has_anuncio = ("anuncio de licitacion" in f)
    has_expediente = ("numero de expediente" in f)
    has_platform = ("plataforma de contratacion" in f) or ("sello de tiempo" in f)
    if has_anuncio and has_expediente and has_platform:
        snippet = ""
        for ln in doc.lines[:6]:
            snippet += ln["raw"] + "\n"
        return "anuncio_placsp", "high", snippet

    # pcap: require the full pliego title as a heading, not a body reference.
    if "pliego de clausulas administrativas particulares" in f:
        return "pcap", "high", _first_line_with(doc, "pliego de clausulas administrativas")
    # ppt
    if "pliego de prescripciones tecnicas" in f:
        return "ppt", "high", _first_line_with(doc, "pliego de prescripciones tecnicas")
    # acta (award / formalization minutes)
    if ("acta de adjudicacion" in f or "acta de formalizacion" in f
            or "formalizacion del contrato" in f):
        role = "acta"
        return role, "medium", _first_line_with(doc, "acta")

    return "unknown", "low", (doc.lines[0]["raw"] if doc.lines else "")


def _first_line_with(doc, needle):
    for ln in doc.lines:
        if needle in ln["fold"]:
            return ln["raw"]
    return ""


# --------------------------------------------------------------------------- #
# anuncio_placsp field extractors
# --------------------------------------------------------------------------- #
_KNOWN_HEADINGS_FOLD = (
    "descripcion del procedimiento", "valor estimado del contrato",
    "presupuesto base de licitacion", "categorias/cpv", "clasificacion cpv",
    "plazo de ejecucion", "lugar de ejecucion",
)


def extract_objeto(doc, ctx):
    # Primary: "Objeto del Contrato:" heading window.
    for i, ln in enumerate(doc.lines):
        if ln["fold"].startswith("objeto del contrato:"):
            page = ln["page"]
            head = ln["raw"].split(":", 1)[1].strip()
            parts = [head] if head else []
            for nxt in doc.lines[i + 1:i + 5]:
                nf = nxt["fold"]
                if any(nf.startswith(h) for h in _KNOWN_HEADINGS_FOLD):
                    break
                parts.append(nxt["raw"].strip())
            value = _clean(" ".join(parts))
            if value:
                exc = "Objeto del Contrato: " + value
                return field(value, "high", "heading_window",
                             [ctx.evidence(page, exc, "heading_window", "high")],
                             "extracted")
    # Fallback: page-1 title between the "Publicado ..." line and the
    # "Contrato Sujeto a regulacion armonizada" line.
    start = None
    for i, ln in enumerate(doc.lines):
        if ln["fold"].startswith("publicado en la plataforma"):
            start = i + 1
            break
    if start is not None:
        parts = []
        page = doc.lines[start]["page"] if start < len(doc.lines) else 1
        for ln in doc.lines[start:start + 5]:
            if ln["fold"].startswith("contrato sujeto a regulacion"):
                break
            parts.append(ln["raw"].strip())
        value = _clean(" ".join(parts))
        if value:
            return field(value, "medium", "heading_window",
                         [ctx.evidence(page, value, "heading_window", "medium")],
                         "partial")
    return null_field("absent", "heading_window")


def extract_cpv(doc, ctx):
    anchors = ("categorias/cpv", "clasificacion cpv")
    code_re = re.compile(r"^(\d{8})\s*-\s*(.+?)\.?\s*$")
    seen = OrderedDict()
    page = None
    ev_lines = []
    for i, ln in enumerate(doc.lines):
        if ln["fold"] in anchors or any(ln["fold"].startswith(a) for a in anchors):
            if page is None:
                page = ln["page"]
            for nxt in doc.lines[i + 1:i + 12]:
                m = code_re.match(nxt["raw"].strip())
                if m:
                    code, label = m.group(1), _clean(m.group(2))
                    if code not in seen:
                        seen[code] = label
                        ev_lines.append(nxt["raw"].strip())
                elif nxt["raw"].strip() and not nxt["raw"].strip()[0].isdigit():
                    break
    if seen:
        value = [{"code": c, "label": l} for c, l in seen.items()]
        exc = "Categorias/CPV\n" + "\n".join(ev_lines[:6])
        return field(value, "high", "keyword_window",
                     [ctx.evidence(page or 1, exc, "keyword_window", "high")],
                     "extracted")
    return null_field("absent", "keyword_window")


def extract_valor_estimado(doc, ctx):
    pat = re.compile(r"valor estimado del contrato\s+([\d.,]+)\s*eur")
    for ln in doc.lines:
        m = pat.search(ln["fold"])
        if m:
            amt = parse_amount(m.group(1))
            if amt is not None:
                return field({"amount": amt, "currency": "EUR"}, "high", "regex",
                             [ctx.evidence(ln["page"], ln["raw"], "regex", "high")],
                             "extracted")
    return null_field("absent", "regex")


def extract_presupuesto(doc, ctx):
    for i, ln in enumerate(doc.lines):
        if ln["fold"].startswith("presupuesto base de licitacion"):
            page = ln["page"]
            con = sin = None
            ev = [ln["raw"]]
            for nxt in doc.lines[i + 1:i + 5]:
                nf = nxt["fold"]
                ms = re.search(r"importe\s*\(sin impuestos\)\s+([\d.,]+)\s*eur", nf)
                if ms:
                    sin = parse_amount(ms.group(1))
                    ev.append(nxt["raw"].strip())
                    continue
                mc = re.search(r"importe\s+([\d.,]+)\s*eur", nf)
                if mc and "sin impuestos" not in nf:
                    con = parse_amount(mc.group(1))
                    ev.append(nxt["raw"].strip())
                    continue
                if any(nf.startswith(h) for h in _KNOWN_HEADINGS_FOLD):
                    break
            if con is not None or sin is not None:
                value = {"importe_con_impuestos": con,
                         "importe_sin_impuestos": sin, "currency": "EUR"}
                exc = "\n".join(ev[:4])
                # SDA notices legitimately carry 0 EUR base budgets.
                conf = "medium"
                return field(value, conf, "keyword_window",
                             [ctx.evidence(page, exc, "keyword_window", conf)],
                             "partial")
    return null_field("absent", "keyword_window")


def extract_duracion(doc, ctx):
    del_re = re.compile(r"del\s+(\d{2}/\d{2}/\d{4})\s+al\s+(\d{2}/\d{2}/\d{4})")
    for i, ln in enumerate(doc.lines):
        if "plazo de ejecucion" in ln["fold"]:
            page = ln["page"]
            window = doc.lines[i:i + 4]
            for j, wln in enumerate(window):
                m = del_re.search(wln["fold"])
                if m:
                    desde = iso_date(m.group(1))
                    hasta = iso_date(m.group(2))
                    obs = None
                    ev = [ln["raw"], wln["raw"].strip()]
                    for oln in doc.lines[i + j + 1:i + j + 4]:
                        if oln["fold"].startswith("observaciones:"):
                            obs = _clean(oln["raw"].split(":", 1)[1])
                            ev.append(oln["raw"].strip())
                            break
                        if any(oln["fold"].startswith(h)
                               for h in _KNOWN_HEADINGS_FOLD):
                            break
                    value = {"desde": desde, "hasta": hasta, "observaciones": obs}
                    exc = "\n".join(ev)
                    return field(value, "high", "keyword_window",
                                 [ctx.evidence(page, exc, "keyword_window", "high")],
                                 "extracted")
    return null_field("absent", "keyword_window")


_PLAZO_HEADINGS = [
    ("plazo de presentacion de oferta", "presentacion_oferta"),
    ("plazo de recepcion de solicitudes de", "recepcion_solicitudes_participacion"),
    ("plazo de obtencion de pliegos", "obtencion_pliegos"),
    ("periodo de vigencia del sistema dinamico", "vigencia_sistema_dinamico"),
    ("plazo de presentacion", "presentacion_recursos"),
]


def extract_plazos(doc, ctx):
    hasta_re = re.compile(r"hasta el\s+(\d{2}/\d{2}/\d{4})\s+a las\s+(\d{2}:\d{2})")
    out = []
    ev_lines = []
    seen = set()
    for i, ln in enumerate(doc.lines):
        tipo = None
        for prefix, t in _PLAZO_HEADINGS:
            if ln["fold"].startswith(prefix):
                tipo = t
                break
        if not tipo:
            continue
        for nxt in doc.lines[i:i + 4]:
            m = hasta_re.search(nxt["fold"])
            if m:
                fecha = iso_date(m.group(1))
                hora = m.group(2)
                key = (tipo, fecha, hora)
                if key not in seen:
                    seen.add(key)
                    out.append({"tipo": tipo, "fecha_limite": fecha, "hora": hora})
                    ev_lines.append("%s -> %s" % (ln["raw"].strip(),
                                                  nxt["raw"].strip()))
                break
    # Validez de la oferta (non-date duration, e.g. "36 Mes(es)").
    for i, ln in enumerate(doc.lines):
        if ln["fold"].startswith("plazo de validez de la oferta"):
            for nxt in doc.lines[i + 1:i + 3]:
                mv = re.match(r"^(\d+)\s*mes", nxt["fold"])
                if mv:
                    out.append({"tipo": "validez_oferta", "fecha_limite": None,
                                "hora": None, "raw": _clean(nxt["raw"])})
                    ev_lines.append("%s -> %s" % (ln["raw"].strip(),
                                                  nxt["raw"].strip()))
                    break
    if out:
        page = doc.lines[0]["page"]
        exc = "\n".join(ev_lines[:6])
        return field(out, "medium", "keyword_window",
                     [ctx.evidence(page, exc, "keyword_window", "medium")],
                     "extracted")
    return null_field("absent", "keyword_window")


def extract_lotes(doc, ctx):
    count = None
    count_ev = None
    count_page = None
    for ln in doc.lines:
        m = re.search(r"de lotes:\s*(\d+)", ln["fold"])
        if m:
            count = int(m.group(1))
            count_ev = ln["raw"].strip()
            count_page = ln["page"]
            break
    items = []
    val_re = re.compile(r"valor estimado del contrato\s+([\d.,]+)\s*eur")
    lote_re = re.compile(r"^lote\s+(\d+):\s*(.+)$")
    for i, ln in enumerate(doc.lines):
        m = lote_re.match(ln["fold"])
        if m:
            num = int(m.group(1))
            desc = _clean(ln["raw"].split(":", 1)[1])
            valor = None
            for nxt in doc.lines[i + 1:i + 8]:
                mv = val_re.search(nxt["fold"])
                if mv:
                    valor = parse_amount(mv.group(1))
                    break
                if lote_re.match(nxt["fold"]):
                    break
            items.append({"num": num, "descripcion": desc,
                          "valor_estimado": valor})
    if items:
        ev = []
        if count_ev:
            ev.append(count_ev)
        for it in items[:4]:
            ev.append("Lote %s: %s" % (it["num"], it["descripcion"][:60]))
        page = count_page or (items and 1)
        return field(items, "medium", "keyword_window",
                     [ctx.evidence(page or 1, "\n".join(ev), "keyword_window",
                                   "medium")],
                     "partial")
    if count is not None:
        return field(None, "low", "regex",
                     [ctx.evidence(count_page or 1, count_ev or "", "regex",
                                   "low")],
                     "partial")
    return null_field("absent", "keyword_window")


_CRIT_SKIP = ("subtipo criterio", "ponderacion", "cantidad minima",
              "cantidad maxima", "criterios de adjudicacion",
              "criterios evaluables", "condiciones de adjudicacion")


def _criterion_name(doc, idx, subtipo):
    """Nearest preceding meaningful line as the criterion name."""
    for k in range(idx - 1, max(idx - 4, -1), -1):
        ln = doc.lines[k]
        nf = ln["fold"]
        if not nf:
            continue
        if any(nf.startswith(s) for s in _CRIT_SKIP):
            continue
        if "no tiene criterios" in nf:
            continue
        return _clean(ln["raw"])
    return "Precio" if subtipo == "Precio" else None


def extract_criterios(doc, ctx):
    sub_re = re.compile(r"^subtipo criterio\s*:\s*(precio|otros)")
    pond_re = re.compile(r"ponderacion\s*:\s*(\d+)")
    crits = []
    ev_lines = []
    page = None
    for i, ln in enumerate(doc.lines):
        m = sub_re.match(ln["fold"])
        if not m:
            continue
        subtipo = "Precio" if m.group(1) == "precio" else "Otros"
        pond = None
        for nxt in doc.lines[i + 1:i + 3]:
            mp = pond_re.search(nxt["fold"])
            if mp:
                pond = int(mp.group(1))
                break
        nombre = _criterion_name(doc, i, subtipo)
        crits.append({"nombre": nombre, "subtipo": subtipo, "ponderacion": pond})
        if page is None:
            page = ln["page"]
        ev_lines.append("%s / Subtipo: %s / Ponderacion: %s"
                        % (nombre, subtipo, pond))

    adj = precio = tec = null_field("absent", "keyword_window")
    if crits:
        exc = "\n".join(ev_lines[:6])
        adj = field(crits, "medium", "keyword_window",
                    [ctx.evidence(page, exc, "keyword_window", "medium")],
                    "extracted")
        precio_entries = [c for c in crits if c["subtipo"] == "Precio"]
        if precio_entries:
            precio = field({"ponderacion": precio_entries[0]["ponderacion"]},
                           "medium", "keyword_window",
                           [ctx.evidence(page, exc, "keyword_window", "medium")],
                           "extracted")
        tec_entries = [{"nombre": c["nombre"], "ponderacion": c["ponderacion"]}
                       for c in crits if c["subtipo"] == "Otros" and c["nombre"]]
        if tec_entries:
            tec = field(tec_entries, "low", "keyword_window",
                        [ctx.evidence(page, exc, "keyword_window", "low")],
                        "partial")
    return adj, precio, tec


def extract_contract_meta(doc, ctx):
    value = {}
    ev_lines = []
    page = 1

    def grab(prefix):
        for ln in doc.lines:
            if ln["fold"].startswith(prefix):
                return ln
        return None

    ln = grab("numero de expediente")
    if ln:
        value["num_expediente"] = _clean(ln["raw"].split(None, 3)[-1]) \
            if len(ln["raw"].split(None, 3)) >= 4 else None
        # "Número de Expediente 2025 11" -> everything after the label.
        val = re.sub(r"(?i)^n[uú]mero de expediente\s+", "", ln["raw"]).strip()
        value["num_expediente"] = _clean(val)
        ev_lines.append(ln["raw"].strip())
        page = ln["page"]

    for fold_prefix, key in (("procedimiento ", "procedimiento"),
                             ("tramitacion ", "tramitacion"),
                             ("sistema de contratacion ", "sistema_contratacion"),
                             ("presentacion de la oferta ", "presentacion")):
        l2 = grab(fold_prefix)
        if l2:
            val = l2["raw"].split(None, 1)
            # Strip the label words, keep the value remainder.
            raw = l2["raw"]
            cut = len(fold_prefix.rstrip())
            value[key] = _clean(raw[cut:]) if len(raw) > cut else None
            ev_lines.append(l2["raw"].strip())

    mdir = re.search(r"directiva\s+(20\d{2}/\d+/[a-z]+)", doc.folded_full)
    if mdir:
        value["directiva"] = mdir.group(1).upper()

    if value:
        exc = "\n".join(ev_lines[:6])
        return field(value, "high", "regex",
                     [ctx.evidence(page, exc, "regex", "high")], "extracted")
    return null_field("absent", "regex")


def extract_solvencia(doc, ctx, anchor, label):
    for i, ln in enumerate(doc.lines):
        if ln["fold"].startswith(anchor):
            page = ln["page"]
            window = [ln["raw"].strip()]
            for nxt in doc.lines[i + 1:i + 3]:
                if nxt["fold"].startswith("criterio de solvencia"):
                    break
                if nxt["fold"].startswith("preparacion de oferta"):
                    break
                window.append(nxt["raw"].strip())
            wtext = " ".join(window)
            wfold = fold(wtext)
            is_pointer = any(p in wfold for p in _POINTER_PHRASES)
            status = "deferred_to_pcap" if is_pointer else "evidence_only"
            ev = [ctx.evidence(page, wtext, "keyword_window", "low")]
            # Value is NEVER asserted for solvencia in v1 (pointer-prone).
            return field(None, "low", "keyword_window", ev, status)
    return null_field("absent", "keyword_window")


def extract_opportunity_flags(doc, ctx, contract_meta_val, lotes_val,
                              deadline_valid):
    f = doc.folded_full
    flags = {}
    flags["es_sda"] = "sistema dinamico de adquisicion" in f
    proc = (contract_meta_val or {}).get("procedimiento") or ""
    flags["procedimiento_restringido"] = "restringido" in fold(proc)
    mra = re.search(r"contrato sujeto a regulacion armonizada\s+(si|no)", f)
    flags["sujeto_regulacion_armonizada"] = bool(mra and mra.group(1) == "si")
    if "no hay financiacion con fondos de la ue" in f:
        flags["fondos_ue"] = False
    elif "fondos de la ue" in f or "fondos ue" in f:
        flags["fondos_ue"] = True
    else:
        flags["fondos_ue"] = None
    if isinstance(lotes_val, list) and lotes_val:
        flags["num_lotes"] = len(lotes_val)
    else:
        ml = re.search(r"de lotes:\s*(\d+)", f)
        flags["num_lotes"] = int(ml.group(1)) if ml else None
    flags["deadline_valid"] = bool(deadline_valid)

    page = 1
    exc_parts = []
    for ln in doc.lines[:30]:
        if ("regulacion armonizada" in ln["fold"]
                or "sistema de contratacion" in ln["fold"]
                or "procedimiento" == ln["fold"][:12]):
            exc_parts.append(ln["raw"].strip())
    exc = "\n".join(exc_parts[:4]) or (doc.lines[0]["raw"] if doc.lines else "")
    return field(flags, "high", "derived",
                 [ctx.evidence(page, exc, "derived", "high")], "extracted")


# --------------------------------------------------------------------------- #
# Per-record assembly
# --------------------------------------------------------------------------- #
def _load_doc_text(doc_meta, text_root):
    sha = doc_meta.get("doc_sha256")
    candidates = []
    if sha:
        candidates.append(os.path.join(text_root, "%s.txt" % sha))
    tl = doc_meta.get("text_location")
    if tl:
        candidates.append(tl)
    for path in candidates:
        if path and os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                return path, fh.read()
    return None, None


def build_field_map(doc, ctx, deadline_valid):
    fields = OrderedDict()
    fields["objeto"] = extract_objeto(doc, ctx)
    fields["cpv"] = extract_cpv(doc, ctx)
    fields["valor_estimado"] = extract_valor_estimado(doc, ctx)
    fields["presupuesto_base"] = extract_presupuesto(doc, ctx)
    fields["duracion"] = extract_duracion(doc, ctx)
    fields["lotes"] = extract_lotes(doc, ctx)
    fields["plazos"] = extract_plazos(doc, ctx)
    adj, precio, tec = extract_criterios(doc, ctx)
    fields["criterios_adjudicacion"] = adj
    fields["criterios_precio"] = precio
    fields["criterios_tecnicos"] = tec
    fields["contract_meta"] = extract_contract_meta(doc, ctx)
    fields["solvencia_economica"] = extract_solvencia(
        doc, ctx, "criterio de solvencia economica", "economica")
    fields["solvencia_tecnica"] = extract_solvencia(
        doc, ctx, "criterio de solvencia tecnica", "tecnica")
    flags = extract_opportunity_flags(
        doc, ctx, fields["contract_meta"]["value"], fields["lotes"]["value"],
        deadline_valid)
    fields["opportunity_flags"] = flags
    # Deep pliego fields: deferred (absent from notice).
    for k in _DEFERRED_V1:
        fields[k] = null_field("deferred")
    return fields


def compute_status(fields, has_text, role):
    if not has_text:
        return "insufficient_text"
    if role != "anuncio_placsp":
        return "insufficient_text"
    core = ["objeto", "cpv", "valor_estimado", "presupuesto_base", "duracion",
            "criterios_adjudicacion"]
    present = [k for k in core if fields.get(k, {}).get("value") is not None]
    objeto_ok = fields.get("objeto", {}).get("value") is not None
    cpv_ok = fields.get("cpv", {}).get("value") is not None
    budget_or_date = any(
        fields.get(k, {}).get("value") is not None
        for k in ("valor_estimado", "presupuesto_base", "duracion",
                  "criterios_adjudicacion"))
    core_ok = objeto_ok and cpv_ok and budget_or_date
    if core_ok:
        # Deep pliego fields are deferred for notices -> partial, not ready.
        deep_deferred = any(
            fields.get(k, {}).get("field_status") in
            ("deferred", "deferred_to_pcap", "evidence_only")
            for k in (_DEFERRED_V1 + _EVIDENCE_ONLY_V1))
        return "partial" if deep_deferred else "ready"
    if present:
        return "partial"
    return "insufficient_text"


def field_coverage(fields):
    denom = _EXTRACTABLE_V1
    non_null = sum(1 for k in denom if fields.get(k, {}).get("value") is not None)
    return round(non_null / float(len(denom)), 3) if denom else 0.0


def process_record(rec, text_root, excerpt_chars, debug):
    notice_id = rec.get("notice_id")
    key = rec.get("canonical_key")
    deadline_valid = rec.get("deadline_valid")
    document_roles = []
    primary = None  # (doc, ctx, doc_meta)
    docs_read = pages_read = chars_read = 0
    warnings = []
    failed = False

    for doc_meta in (rec.get("documents") or []):
        status = doc_meta.get("extraction_status")
        sha = doc_meta.get("doc_sha256")
        if status not in ("extracted", "partial_parse"):
            document_roles.append(OrderedDict([
                ("doc_sha256", sha), ("role", "unknown"),
                ("role_confidence", "low"),
                ("role_evidence", {"note": "extraction_status=%s" % status})]))
            continue
        path, text = _load_doc_text(doc_meta, text_root)
        if not text:
            warnings.append("missing text file for doc %s" % (sha or "")[:16])
            document_roles.append(OrderedDict([
                ("doc_sha256", sha), ("role", "unknown"),
                ("role_confidence", "low"),
                ("role_evidence", {"note": "text_location missing"})]))
            continue
        try:
            doc = DocText(text)
            role, role_conf, role_snip = classify_role(doc)
        except Exception as exc:  # noqa: BLE001
            failed = True
            warnings.append("parse error doc %s: %s"
                            % ((sha or "")[:16], exc.__class__.__name__))
            continue
        docs_read += 1
        pages_read += doc.page_count
        chars_read += len(text)
        document_roles.append(OrderedDict([
            ("doc_sha256", sha),
            ("role", role),
            ("role_confidence", role_conf),
            ("role_evidence", {"page": 1, "excerpt": _clean(role_snip)[:excerpt_chars],
                               "extraction_method": "heading_window"})]))
        if role == "anuncio_placsp" and primary is None:
            extractor = doc_meta.get("extractor") or "pdfplumber"
            ctx = Ctx(sha, notice_id, key, role, extractor, excerpt_chars)
            primary = (doc, ctx, doc_meta)

    if failed and primary is None:
        return _record_obj(notice_id, key, "failed", document_roles, {},
                           docs_read, pages_read, chars_read, warnings), "failed"

    if primary is None:
        roles_found = sorted({r["role"] for r in document_roles})
        warnings.append("no anuncio_placsp document; roles=%s"
                        % ",".join(roles_found))
        empty_fields = _empty_fields()
        status = "insufficient_text"
        return _record_obj(notice_id, key, status, document_roles, empty_fields,
                           docs_read, pages_read, chars_read, warnings), status

    doc, ctx, doc_meta = primary
    fields = build_field_map(doc, ctx, deadline_valid)

    # Notice-specific warnings.
    warnings.append("primary document is anuncio_placsp notice, not PCAP/PPT")
    if fields["solvencia_economica"]["field_status"] == "deferred_to_pcap" or \
            fields["solvencia_tecnica"]["field_status"] == "deferred_to_pcap":
        warnings.append("solvencia captured as evidence-only/deferred_to_pcap, "
                        "not asserted")
    if "(cid:" in doc.full_text:
        warnings.append("pdfplumber glyph artifacts (cid:NN) present; cleaned")
    pb = fields["presupuesto_base"]["value"]
    if pb and (pb.get("importe_con_impuestos") == 0
               or pb.get("importe_sin_impuestos") == 0):
        warnings.append("presupuesto_base 0 EUR (legitimate for SDA notices)")

    status = compute_status(fields, has_text=True, role="anuncio_placsp")
    record = _record_obj(notice_id, key, status, document_roles, fields,
                         docs_read, pages_read, chars_read, warnings)
    return record, status


def _empty_fields():
    fields = OrderedDict()
    for k in _EXTRACTABLE_V1:
        fields[k] = null_field("insufficient_text", "keyword_window")
    for k in _EVIDENCE_ONLY_V1:
        fields[k] = null_field("insufficient_text", "keyword_window")
    for k in _DEFERRED_V1:
        fields[k] = null_field("deferred")
    return fields


def _record_obj(notice_id, key, status, document_roles, fields, docs_read,
                pages_read, chars_read, warnings):
    return OrderedDict([
        ("notice_id", notice_id),
        ("canonical_key", key),
        ("appendix_status", status),
        ("document_roles", document_roles),
        ("fields", fields),
        ("opportunity_flags", fields.get("opportunity_flags")),
        ("quality", OrderedDict([
            ("documents_read", docs_read),
            ("pages_read", pages_read),
            ("chars_read", chars_read),
            ("field_coverage", field_coverage(fields) if fields else 0.0),
            ("warnings", warnings),
        ])),
    ])


# --------------------------------------------------------------------------- #
# Strict-evidence / min-confidence post-processing
# --------------------------------------------------------------------------- #
def enforce_evidence(fields, min_conf, strict_evidence, warnings):
    if not fields:
        return
    for name, fobj in fields.items():
        if not isinstance(fobj, dict):
            continue
        val = fobj.get("value")
        status = fobj.get("field_status")
        if val is None:
            continue
        # strict-evidence: any asserted value must carry >=1 evidence object.
        if strict_evidence and status in ("extracted", "partial") \
                and not fobj.get("evidence"):
            fobj["value"] = None
            fobj["field_status"] = "insufficient_evidence"
            warnings.append("dropped %s (no evidence under strict-evidence)" % name)
            continue
        # min-confidence: demote values below the floor (solvencia excluded —
        # already value-null evidence-only).
        conf = fobj.get("confidence")
        if status in ("extracted", "partial") and conf in _CONF_RANK \
                and _CONF_RANK[conf] < _CONF_RANK.get(min_conf, 0):
            fobj["value"] = None
            fobj["field_status"] = "below_min_confidence"
            warnings.append("demoted %s (confidence=%s < %s)"
                            % (name, conf, min_conf))


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #
def validate_input(manifest, text_root):
    problems = []
    if manifest.get("schema") != SOURCE_SCHEMA:
        problems.append("input schema is %r, expected %r"
                        % (manifest.get("schema"), SOURCE_SCHEMA))
    if manifest.get("production_write_performed") is not False:
        problems.append("input production_write_performed != false (%r)"
                        % manifest.get("production_write_performed"))
    records = manifest.get("records")
    if not isinstance(records, list):
        problems.append("input has no records[] list")
        records = []
    # text_location presence for extracted docs.
    missing_text = 0
    for rec in records:
        for doc in (rec.get("documents") or []):
            if doc.get("extraction_status") == "extracted":
                path, text = _load_doc_text(doc, text_root)
                if not text:
                    missing_text += 1
    if missing_text:
        problems.append("%d extracted document(s) have no readable text file"
                        % missing_text)
    return problems


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build_argparser():
    p = argparse.ArgumentParser(
        prog="appendix_extractor",
        description="Appendix extractor — local-only doc-intelligence over "
                    "docread/1 text (p197).")
    p.add_argument("--input", required=True,
                   help="docread/1 manifest JSON (local-only).")
    p.add_argument("--out",
                   default=os.path.join("_tmp", "appendix",
                                        "appendix_manifest_v1.json"))
    p.add_argument("--text-root", default=os.path.join("_tmp", "docreader", "text"))
    p.add_argument("--schema-draft",
                   default=os.path.join("_tmp", "appendix_scouting",
                                        "appendix_schema_v1_draft.json"))
    p.add_argument("--excerpt-chars", type=int, default=350)
    p.add_argument("--strict-evidence", dest="strict_evidence",
                   action="store_true", default=True)
    p.add_argument("--no-strict-evidence", dest="strict_evidence",
                   action="store_false")
    p.add_argument("--min-confidence", choices=["medium", "low"], default="low")
    p.add_argument("--max-records", type=int, default=None)
    p.add_argument("--debug", action="store_true", default=False)
    return p


def main(argv=None):
    args = build_argparser().parse_args(argv)

    out_norm = _ensure_safe_file(args.out, "--out manifest")

    if not os.path.isfile(args.input):
        sys.stderr.write("[appendix] input not found: %s\n" % args.input)
        return 2
    with open(args.input, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    problems = validate_input(manifest, args.text_root)
    if problems:
        sys.stderr.write("[appendix] INPUT VALIDATION FAILED:\n")
        for pb in problems:
            sys.stderr.write("           - %s\n" % pb)
        return 2

    schema_draft_exists = os.path.isfile(args.schema_draft)

    src_records = manifest.get("records") or []
    if args.max_records is not None:
        src_records = src_records[:args.max_records]

    out_records = []
    role_counter = Counter()
    status_counter = Counter()
    doc_total = 0

    for rec in src_records:
        record, status = process_record(rec, args.text_root, args.excerpt_chars,
                                         args.debug)
        enforce_evidence(record.get("fields"), args.min_confidence,
                         args.strict_evidence, record["quality"]["warnings"])
        # Recompute status only if evidence enforcement nulled core fields.
        if status in ("ready", "partial"):
            status = compute_status(record["fields"], has_text=True,
                                    role="anuncio_placsp")
            record["appendix_status"] = status
        status_counter[status] += 1
        for dr in record.get("document_roles", []):
            role_counter[dr.get("role", "unknown")] += 1
            doc_total += 1
        out_records.append(record)
        if args.debug:
            print("[appendix] %s status=%s roles=%s coverage=%s"
                  % (rec.get("canonical_key"), status,
                     [d["role"] for d in record["document_roles"]],
                     record["quality"]["field_coverage"]))

    counts = OrderedDict([
        ("records", len(out_records)),
        ("documents", doc_total),
        ("roles", OrderedDict(sorted(role_counter.items()))),
        ("ready", status_counter.get("ready", 0)),
        ("partial", status_counter.get("partial", 0)),
        ("insufficient_text", status_counter.get("insufficient_text", 0)),
        ("failed", status_counter.get("failed", 0)),
    ])

    out = OrderedDict([
        ("schema", SCHEMA),
        ("schema_version", SCHEMA_VERSION),
        ("generated_by_prompt", GENERATED_BY_PROMPT),
        ("target_version", VERSION),
        ("source_schema", SOURCE_SCHEMA),
        ("production_write_performed", False),
        ("input", os.path.normpath(args.input)),
        ("schema_draft", os.path.normpath(args.schema_draft)
            if schema_draft_exists else None),
        ("generated_at_utc", datetime.now(timezone.utc).isoformat()),
        ("limits", OrderedDict([
            ("excerpt_chars", args.excerpt_chars),
            ("strict_evidence", bool(args.strict_evidence)),
            ("min_confidence", args.min_confidence),
            ("max_records", args.max_records),
        ])),
        ("source_counts", manifest.get("counts")),
        ("source_selection_summary", manifest.get("selection_summary")),
        ("counts", counts),
        ("records", out_records),
    ])

    _ensure_safe_file(args.out, "--out manifest")
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    print("[appendix] %s %s  source=%s" % (SCHEMA, VERSION, SOURCE_SCHEMA))
    print("[appendix] records=%d documents=%d roles=%s"
          % (counts["records"], counts["documents"], dict(counts["roles"])))
    print("[appendix] statuses: ready=%d partial=%d insufficient_text=%d failed=%d"
          % (counts["ready"], counts["partial"], counts["insufficient_text"],
             counts["failed"]))
    print("[appendix] manifest -> %s" % out_norm)
    print("[appendix] production_write_performed=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
