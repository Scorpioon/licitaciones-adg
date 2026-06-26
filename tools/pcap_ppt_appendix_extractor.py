#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCAP/PPT Appendix Extractor  (ADG OPS / p199 / v0.6.53)

Reads the p198b feed_xml attachment probe manifest (schema feedxml_probe/1) plus
its extracted plain-text files, and produces a conservative, evidence-backed
Appendix layer (schema appendix_pcap_ppt/1) for PCAP / PPT pliegos.

Design principles (operator requirement: HONEST FALLBACKS):
  - Never fabricate a value. Every non-null field carries at least one evidence
    object pointing at the exact document, page and capped excerpt it came from.
  - Every missing / unparsed field exposes a display-ready fallback so a future
    UI can offer "open source document", "manual review", "OCR needed", etc.
  - Source URLs (url / final_url) are always preserved for the "open document"
    fallback.
  - Low-coverage / image-like documents are flagged ocr_needed, not failed and
    not silently dropped.

Scope guardrails (p199):
  - stdlib only. No network. No downloads. No PDF/DOCX parsing. No OCR.
  - Reads text already extracted by p198b under _tmp/feedxml_probe/text/.
  - production_write_performed is always False; never writes data/licitaciones.json.
  - Output paths must resolve under _tmp/ or data/fetcher2/.

CLI:
  python tools/pcap_ppt_appendix_extractor.py \
      --input  _tmp/feedxml_probe/feedxml_probe_manifest_p198b.json \
      --out    _tmp/appendix/appendix_manifest_pcap_ppt_p199.json \
      --report _tmp/appendix/appendix_pcap_ppt_report_p199.md \
      --samples _tmp/appendix/appendix_pcap_ppt_samples_p199.json \
      --excerpt-chars 500 --window-chars 4000
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import unicodedata

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

SCHEMA = "appendix_pcap_ppt/1"
SCHEMA_VERSION = "0.1-prototype"
GENERATED_BY_PROMPT = "p199"
TARGET_VERSION = "v0.6.53"
INPUT_SCHEMA = "feedxml_probe/1"
EXTRACTOR_NAME = "pcap_ppt_appendix_extractor"

ALLOWED_ROLES = ("pcap", "ppt")

# Where outputs are permitted to land.
ALLOWED_OUTPUT_ROOTS = ("_tmp", os.path.join("data", "fetcher2"))
# Where input text files are permitted to come from.
ALLOWED_TEXT_ROOT = os.path.join("_tmp", "feedxml_probe", "text")

VALUE_CAP_CHARS = 2500          # max stored field value length in the manifest
PAGE_MARKER_RE = re.compile(r"^---\s*PAGE\s+(\d+)\s*---\s*$", re.IGNORECASE)

DISPLAY_LABELS = {
    "pcap": "PCAP / Pliego administrativo",
    "ppt": "PPT / Pliego técnico",
}

# --------------------------------------------------------------------------- #
# Heading / keyword variants per field (normalized: lowercase, accents stripped)
# Spanish + Galician (several records are in Galician) variants are included.
# These are *conservative* anchors; windows are evidence, never invention.
# --------------------------------------------------------------------------- #

FIELD_VARIANTS = {
    # --- Core deep fields (mostly PCAP) ---
    "solvencia_economica": [
        "solvencia economica", "solvencia economica y financiera",
        "capacidad economica", "volumen anual de negocios",
    ],
    "solvencia_tecnica": [
        "solvencia tecnica", "solvencia profesional",
        "solvencia tecnica o profesional", "solvencia tecnica e profesional",
        "relacion de servicios", "relacion de los principales servicios",
    ],
    "clasificacion_empresarial": [
        "clasificacion empresarial", "clasificacion del contratista",
        "clasificacion exigible", "habilitacion empresarial",
        "clasificacion del empresario",
    ],
    "criterios_adjudicacion": [
        "criterios de adjudicacion", "criterios de adxudicacion",
        "criterios evaluables", "criterios de valoracion",
    ],
    "criterios_precio": [
        "criterios automaticos", "criterios cuantificables mediante formulas",
        "criterios evaluables mediante formulas", "oferta economica",
        "puntuacion economica", "criterios objetivos",
    ],
    "criterios_tecnicos": [
        "juicio de valor", "criterios sujetos a juicio de valor",
        "criterios cualitativos", "criterios tecnicos",
    ],
    "formulas": [
        "formula", "puntuacion de la oferta economica",
        "puntuacion economica", "metodo de valoracion",
    ],
    "documentacion_exigida": [
        "documentacion a presentar", "documentacion administrativa",
        "documentacion exigida", "archivo electronico",
        "declaracion responsable", "sobre a", "sobre b", "sobre c",
        "sobre numero", "sobre nº",
    ],
    "garantia_provisional": ["garantia provisional"],
    "garantia_definitiva": ["garantia definitiva", "garantias"],
    "duracion_contrato": [
        "duracion del contrato", "prazo de duracion", "plazo de duracion",
        "duracion del sistema", "prazo de vixencia", "plazo de vigencia",
    ],
    "plazo_presentacion": [
        "plazo de presentacion", "prazo de presentacion",
        "presentacion de ofertas", "presentacion de las ofertas",
        "presentacion das ofertas", "presentacion de proposiciones",
    ],
    "plazo_ejecucion": [
        "plazo de ejecucion", "prazo de execucion",
        "plazo de ejecucion total", "plazo de duracion y prorroga",
    ],
    "penalidades": [
        "penalidades", "regimen de penalidades", "penalidades por demora",
        "causas de resolucion del contrato y penalidades",
    ],
    "obligaciones_principales": [
        "obligaciones del contratista", "obligaciones principales",
        "condiciones especiales de ejecucion", "obrigas do contratista",
    ],
    "subrogacion_personal": [
        "subrogacion", "subrogacion del personal", "subrogacion de personal",
    ],
    "lotes": ["division en lotes", "lotes", "division por lotes"],
    "variantes": ["variantes", "mejoras", "admision de variantes"],
    "presupuesto_base": [
        "presupuesto base", "presupuesto base de licitacion",
        "orzamento base", "orzamento maximo", "orzamento base de licitacion",
    ],
    "valor_estimado": ["valor estimado", "valor estimado del contrato"],
    "cpv": ["cpv"],
    "objeto": [
        "objeto del contrato", "objeto y alcance", "definicion del objeto",
        "definicion do obxecto", "obxecto do sistema", "obxecto",
        "objeto del sistema",
    ],
    # --- PPT-specific fields ---
    "alcance_tecnico": [
        "alcance del servicio", "alcance del contrato", "alcance tecnico",
        "alcance de los trabajos", "alcance",
    ],
    "prescripciones_tecnicas": [
        "prescripciones tecnicas", "prescricions tecnicas",
        "prescripciones tecnicas generales",
    ],
    "entregables": ["entregables", "productos entregables"],
    "medios_materiales": [
        "medios y materiales", "medios materiales",
        "medios personales y materiales", "adscripcion de medios",
        "medios materiales y personales",
    ],
    "perfiles_equipo": [
        "perfiles", "equipo de trabajo", "medios personales",
        "personal adscrito", "perfiles del equipo",
    ],
    "condiciones_servicio": [
        "condiciones del servicio", "condiciones de prestacion del servicio",
        "condiciones de prestacion",
    ],
    "niveles_servicio": [
        "niveles de servicio", "acuerdo de nivel de servicio",
        "acuerdos de nivel de servicio",
    ],
    "mantenimiento_soporte": [
        "mantenimiento y soporte", "mantenimiento", "soporte tecnico",
    ],
}

# Fields searched on PCAP documents.
PCAP_FIELDS = [
    "solvencia_economica", "solvencia_tecnica", "clasificacion_empresarial",
    "criterios_adjudicacion", "criterios_precio", "criterios_tecnicos",
    "formulas", "documentacion_exigida", "garantia_provisional",
    "garantia_definitiva", "duracion_contrato", "plazo_presentacion",
    "plazo_ejecucion", "penalidades", "obligaciones_principales",
    "subrogacion_personal", "lotes", "variantes", "presupuesto_base",
    "valor_estimado", "cpv", "objeto",
]

# Fields searched on PPT documents.
PPT_FIELDS = [
    "objeto", "alcance_tecnico", "prescripciones_tecnicas", "entregables",
    "medios_materiales", "perfiles_equipo", "condiciones_servicio",
    "niveles_servicio", "mantenimiento_soporte", "plazo_ejecucion", "cpv",
]

# Union, stable ordering, for the per-record fields object.
ALL_FIELDS = []
for _f in PCAP_FIELDS + PPT_FIELDS:
    if _f not in ALL_FIELDS:
        ALL_FIELDS.append(_f)

# "Core" fields that matter for the parsed/partial decision.
CORE_FIELDS = [
    "objeto", "solvencia_economica", "solvencia_tecnica",
    "criterios_adjudicacion", "garantia_definitiva", "plazo_ejecucion",
    "presupuesto_base", "valor_estimado",
]

CPV_RE = re.compile(r"\bcpv\b[:\s]*([0-9]{6,8}(?:-[0-9])?)", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# Text utilities
# --------------------------------------------------------------------------- #

def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace - for matching only."""
    return re.sub(r"\s+", " ", strip_accents(text).lower()).strip()


def is_toc_line(line: str) -> bool:
    """Table-of-contents / index line: dotted leaders or trailing page no."""
    if re.search(r"\.{4,}", line):
        return True
    if re.search(r"\.{2,}\s*\d{1,4}\s*$", line.strip()):
        return True
    return False


def hit_is_toc(lines, i):
    """A heading hit is a TOC entry if the line - or the next real line - is a
    dotted leader (covers 'ANEXO V ...\\nREALIZADOS ........ 70')."""
    if is_toc_line(lines[i]):
        return True
    j = i + 1
    while j < len(lines) and (not lines[j].strip() or PAGE_MARKER_RE.match(lines[j].strip())):
        j += 1
    if j < len(lines) and is_toc_line(lines[j]):
        return True
    return False


def is_pointer_window(win: str) -> bool:
    """Window with little real prose (mostly dotted leaders / page numbers)."""
    if not win:
        return True
    alpha = sum(1 for c in win if c.isalpha())
    if win.count(".") >= 20 and alpha < 0.45 * len(win):
        return True
    return alpha < 25


_NUM_HEADING_RE = re.compile(r"^\s*\d{1,2}(?:\.\d{1,2})*\s*[.\-)]?\s+\S")
_LETTER_HEADING_RE = re.compile(r"^[A-Z]\.?\s*\d{0,2}\.?\s+[A-ZÁÉÍÓÚÑ]")
# Single-letter clause headings like "C) Solvencia técnica" / "A. Datos".
_LETTER_PAREN_HEADING_RE = re.compile(r"^[A-Z][).]\s+\S")


def is_heading_line(line: str) -> bool:
    """Heuristic: does this line *start* a new section (a window boundary)?"""
    stripped = line.strip()
    if not stripped or len(stripped) > 130:
        return False
    if _NUM_HEADING_RE.match(line):
        return True
    if _LETTER_HEADING_RE.match(stripped):
        return True
    if _LETTER_PAREN_HEADING_RE.match(stripped):
        return True
    # Mostly-uppercase short line -> likely a heading.
    letters = [c for c in stripped if c.isalpha()]
    if len(letters) >= 4:
        upper = sum(1 for c in letters if c.upper() == c)
        if upper / len(letters) >= 0.7:
            return True
    return False


def build_page_index(lines):
    """Return a list 'page_of[i]' giving the active page number for each line."""
    page_of = []
    current = 0
    for ln in lines:
        m = PAGE_MARKER_RE.match(ln.strip())
        if m:
            current = int(m.group(1))
        page_of.append(current if current > 0 else 1)
    return page_of


# --------------------------------------------------------------------------- #
# Path safety
# --------------------------------------------------------------------------- #

def _norm_rel(path: str) -> str:
    return os.path.normpath(path.replace("\\", os.sep).replace("/", os.sep))


def assert_output_path_safe(path: str, repo_root: str) -> None:
    """Output must resolve under _tmp/ or data/fetcher2/ inside the repo."""
    abs = os.path.normpath(os.path.join(repo_root, path)) if not os.path.isabs(path) else os.path.normpath(path)
    rel = os.path.relpath(abs, repo_root)
    if rel.startswith(".."):
        raise SystemExit(f"[FATAL] output path escapes repo root: {path}")
    ok = any(rel == root or rel.startswith(root + os.sep) for root in ALLOWED_OUTPUT_ROOTS)
    if not ok:
        raise SystemExit(
            f"[FATAL] output path must be under {ALLOWED_OUTPUT_ROOTS}: {path}"
        )
    # Hard stop: never the production data file.
    if _norm_rel(rel) == _norm_rel(os.path.join("data", "licitaciones.json")):
        raise SystemExit("[FATAL] refusing to write data/licitaciones.json")


def resolve_text_path(text_location: str, repo_root: str) -> str:
    """Resolve a manifest text_location and confirm it is under the allowed root."""
    rel = _norm_rel(text_location)
    abs_path = rel if os.path.isabs(rel) else os.path.normpath(os.path.join(repo_root, rel))
    rel_to_root = os.path.relpath(abs_path, repo_root)
    if not (rel_to_root == ALLOWED_TEXT_ROOT or rel_to_root.startswith(ALLOWED_TEXT_ROOT + os.sep)):
        raise ValueError(f"text_location outside allowed root: {text_location}")
    return abs_path


# --------------------------------------------------------------------------- #
# Text quality classification
# --------------------------------------------------------------------------- #

def classify_text_quality(chars: int, pages: int, text_present: bool):
    pages = pages or 0
    chars = chars or 0
    cpp = round(chars / pages, 1) if pages else float(chars)
    if not text_present:
        return {
            "status": "missing", "chars": chars, "pages": pages,
            "chars_per_page": cpp, "ocr_needed": False,
            "reason": "text file referenced by manifest not found",
        }
    if chars == 0:
        return {
            "status": "empty", "chars": chars, "pages": pages,
            "chars_per_page": cpp, "ocr_needed": True,
            "reason": "no extractable text; document is likely image-based",
        }
    low_coverage = (pages >= 10 and cpp < 150) or (chars < 1500 and pages >= 10)
    if low_coverage:
        return {
            "status": "low_coverage", "chars": chars, "pages": pages,
            "chars_per_page": cpp, "ocr_needed": True,
            "reason": (
                f"very low text density ({cpp} chars/page over {pages} pages); "
                "document appears scanned/image-based, OCR needed"
            ),
        }
    return {
        "status": "usable", "chars": chars, "pages": pages,
        "chars_per_page": cpp, "ocr_needed": False,
        "reason": "sufficient extractable text",
    }


# --------------------------------------------------------------------------- #
# Window extraction
# --------------------------------------------------------------------------- #

def find_field_window(field, doc, lines, norm_lines, page_of, window_chars):
    """
    Search a single document's text for a field's heading variants and return the
    best evidence window, or None.

    Returns dict: {value, excerpt, page, heading, method, confidence,
                   only_pointer, raw_window_truncated} or None.
    """
    variants = FIELD_VARIANTS[field]
    hits = []  # (line_idx, is_toc, is_heading, matched_variant)
    for i, nline in enumerate(norm_lines):
        if not nline:
            continue
        for v in variants:
            # word-ish containment: variant surrounded by start/space/punct.
            idx = nline.find(v)
            if idx == -1:
                continue
            # avoid matching inside a longer word at the boundaries
            before_ok = idx == 0 or not nline[idx - 1].isalnum()
            end = idx + len(v)
            after_ok = end >= len(nline) or not nline[end].isalnum()
            if before_ok and after_ok:
                hits.append((i, hit_is_toc(lines, i), is_heading_line(lines[i]), v))
                break
    if not hits:
        return None

    content_hits = [h for h in hits if not h[1]]
    if not content_hits:
        # Only a TOC / pointer reference exists -> honest "pointer found".
        i, _toc, _head, v = hits[0]
        ptr = lines[i].strip()
        ptr = re.sub(r"\.{2,}.*$", "", ptr).strip()  # drop dotted leader+page no
        return {
            "value": ptr[:VALUE_CAP_CHARS],
            "excerpt": ptr,
            "page": page_of[i],
            "heading": ptr[:120],
            "method": "heading_window",
            "confidence": "low",
            "only_pointer": True,
            "raw_window_truncated": False,
        }

    # Prefer a hit that is itself a heading line; among those, the richest window.
    def window_for(start_idx):
        buf = []
        total = 0
        truncated = False
        j = start_idx + 1
        while j < len(lines):
            ln = lines[j]
            if PAGE_MARKER_RE.match(ln.strip()):
                j += 1
                continue
            if is_heading_line(ln) and ln.strip():
                break
            if total + len(ln) + 1 > window_chars:
                room = max(0, window_chars - total)
                if room:
                    buf.append(ln[:room])
                truncated = True
                break
            buf.append(ln)
            total += len(ln) + 1
            j += 1
        head_line = lines[start_idx].strip()
        body = "\n".join(buf).strip()
        full = (head_line + "\n" + body).strip() if body else head_line
        return full, truncated

    scored = []
    for (i, _toc, is_head, v) in content_hits:
        win, trunc = window_for(i)
        dots = win.count(".")
        richness = len(win) - dots  # penalize dotted/sparse windows
        # A real heading earns a bonus, but a rich descriptive window can still
        # win over a bare heading (e.g. an ANEXO form template with no body).
        score = richness + (400 if is_head else 0)
        scored.append((score, is_head, i, v, win, trunc))
    scored.sort(key=lambda t: t[0], reverse=True)
    _score, is_head, i, v, win, trunc = scored[0]

    # Guard: if the best window is just a dotted pointer (no real prose), do not
    # pass it off as an extracted value - demote to an honest pointer.
    if is_pointer_window(win):
        ptr = lines[i].strip()
        ptr = re.sub(r"\.{2,}.*$", "", ptr).strip()
        return {
            "value": ptr[:VALUE_CAP_CHARS],
            "excerpt": ptr,
            "page": page_of[i],
            "heading": ptr[:120],
            "method": "heading_window",
            "confidence": "low",
            "only_pointer": True,
            "raw_window_truncated": False,
        }

    method = "heading_window" if is_head else "keyword_window"
    confidence = "high" if is_head and len(win) > 200 else ("medium" if len(win) > 120 else "low")
    return {
        "value": win[:VALUE_CAP_CHARS],
        "excerpt": win,
        "page": page_of[i],
        "heading": lines[i].strip()[:120],
        "method": method,
        "confidence": confidence,
        "only_pointer": False,
        "raw_window_truncated": trunc or len(win) > VALUE_CAP_CHARS,
    }


def find_cpv(doc, full_text):
    m = CPV_RE.search(full_text)
    if not m:
        return None
    line = ""
    for ln in full_text.splitlines():
        if m.group(0).lower() in ln.lower() or m.group(1) in ln:
            line = ln.strip()
            break
    return {
        "value": m.group(1),
        "excerpt": line or m.group(0),
        "page": 1,
        "heading": "CPV",
        "method": "regex",
        "confidence": "medium",
        "only_pointer": False,
        "raw_window_truncated": False,
    }


# --------------------------------------------------------------------------- #
# Record processing
# --------------------------------------------------------------------------- #

def make_evidence(doc, win, excerpt_chars):
    excerpt = win["excerpt"][:excerpt_chars]
    return {
        "doc_sha256": doc["sha256"],
        "notice_id": doc["_notice_id"],
        "canonical_key": doc["_canonical_key"],
        "role": doc["inferred_role"],
        "display_label": doc.get("display_label") or DISPLAY_LABELS.get(doc["inferred_role"], ""),
        "source_url": doc.get("url", ""),
        "final_url": doc.get("final_url", ""),
        "page": win["page"],
        "excerpt": excerpt,
        "extractor": EXTRACTOR_NAME,
        "confidence": win["confidence"],
        "extraction_method": win["method"],
        "heading": win["heading"],
    }


def best_source_link(docs, role_preference):
    """Pick a (source_url, final_url, label) for a fallback, preferring a role."""
    ordered = sorted(docs, key=lambda d: 0 if d["inferred_role"] == role_preference else 1)
    for d in ordered:
        if d.get("url") or d.get("final_url"):
            return d.get("url", ""), d.get("final_url", ""), \
                d.get("display_label") or DISPLAY_LABELS.get(d["inferred_role"], "")
    return "", "", ""


def missing_field_object(field, docs, any_ocr_needed, all_low_text):
    """Build an honest display-ready fallback for a field with no evidence."""
    pref = "ppt" if field in PPT_FIELDS and field not in PCAP_FIELDS else "pcap"
    src, fin, label = best_source_link(docs, pref)
    if all_low_text:
        status = "ocr_needed"
        mode = "ocr_needed"
        reason = "source text too sparse to locate this field; OCR needed first"
    elif any_ocr_needed:
        status = "manual_review_recommended"
        mode = "manual_review"
        reason = "field not located in parsed text; one document needs OCR, manual review recommended"
    else:
        status = "not_found"
        mode = "open_source_document"
        reason = "field not found in parsed text with conservative rules; open source document to verify"
    return {
        "value": None,
        "field_status": status,
        "confidence": "none",
        "evidence": [],
        "display_fallback": {
            "mode": mode,
            "label": label or "Documento del expediente",
            "source_url": src,
            "final_url": fin,
            "reason": reason,
        },
    }


def process_record(rec, repo_root, excerpt_chars, window_chars, debug):
    notice_id = rec.get("notice_id", "")
    canonical_key = rec.get("canonical_key", "")
    docs_out = []
    doc_runtime = []  # parsed doc dicts with text loaded

    for doc in rec.get("documents", []):
        role = doc.get("inferred_role")
        if role not in ALLOWED_ROLES:
            docs_out.append({
                "sha256": doc.get("sha256", ""),
                "role": role,
                "warning": f"ignored: role '{role}' not in {ALLOWED_ROLES}",
                "source_url": doc.get("url", ""),
                "final_url": doc.get("final_url", ""),
            })
            continue

        doc["_notice_id"] = notice_id
        doc["_canonical_key"] = canonical_key

        text = ""
        text_present = False
        text_err = None
        loc = doc.get("text_location", "")
        if doc.get("extraction_status") == "extracted" and loc:
            try:
                p = resolve_text_path(loc, repo_root)
                if os.path.isfile(p):
                    with open(p, "r", encoding="utf-8", errors="replace") as fh:
                        text = fh.read()
                    text_present = True
                else:
                    text_err = "text file not found"
            except ValueError as exc:
                text_err = str(exc)

        tq = classify_text_quality(doc.get("chars", 0), doc.get("pages", 0), text_present)
        if text_err:
            tq["reason"] = f"{tq['reason']} ({text_err})"

        doc_record = {
            "sha256": doc.get("sha256", ""),
            "role": role,
            "display_label": doc.get("display_label") or DISPLAY_LABELS.get(role, ""),
            "source_url": doc.get("url", ""),
            "final_url": doc.get("final_url", ""),
            "pages": doc.get("pages", 0),
            "chars": doc.get("chars", 0),
            "endpoint_family": doc.get("endpoint_family", ""),
            "extraction_status": doc.get("extraction_status", ""),
            "text_quality": tq,
        }
        docs_out.append(doc_record)

        doc_runtime.append({
            "doc": doc,
            "role": role,
            "text": text,
            "text_present": text_present,
            "tq": tq,
        })

    # Aggregate flags.
    usable_docs = [d for d in doc_runtime if d["tq"]["status"] == "usable"]
    any_ocr_needed = any(d["tq"]["ocr_needed"] for d in doc_runtime)
    all_low_text = bool(doc_runtime) and not usable_docs

    # Field extraction across the record's documents.
    fields = {}
    fields_extracted = 0
    fields_missing = 0

    for field in ALL_FIELDS:
        # Which docs are eligible for this field, by role.
        eligible = []
        for d in usable_docs:
            if d["role"] == "pcap" and field in PCAP_FIELDS:
                eligible.append(d)
            elif d["role"] == "ppt" and field in PPT_FIELDS:
                eligible.append(d)

        best = None
        best_doc = None
        for d in eligible:
            lines = d["text"].splitlines()
            norm_lines = [normalize(x) for x in lines]
            page_of = build_page_index(lines)
            if field == "cpv":
                win = find_cpv(d["doc"], d["text"])
            else:
                win = find_field_window(field, d["doc"], lines, norm_lines, page_of, window_chars)
            if not win:
                continue
            rank = {"high": 3, "medium": 2, "low": 1}
            if best is None or rank[win["confidence"]] > rank[best["confidence"]]:
                best = win
                best_doc = d["doc"]

        if best is None:
            fields[field] = missing_field_object(field, [r["doc"] for r in doc_runtime] or
                                                 [{"inferred_role": "pcap", "url": "", "final_url": "",
                                                   "display_label": ""}],
                                                 any_ocr_needed, all_low_text)
            fields_missing += 1
            continue

        evidence = [make_evidence(best_doc, best, excerpt_chars)]
        if best.get("only_pointer"):
            field_status = "evidence_only"
        elif best["confidence"] == "high":
            field_status = "extracted"
        else:
            field_status = "partial"
        fields[field] = {
            "value": best["value"],
            "field_status": field_status,
            "confidence": best["confidence"],
            "evidence": evidence,
            "raw_window_truncated": best.get("raw_window_truncated", False),
        }
        fields_extracted += 1

    # Risk / warning flags.
    risk_warnings = []
    if any_ocr_needed:
        risk_warnings.append("ocr_needed")
    if all_low_text:
        risk_warnings.append("text_low_coverage")
    if fields_extracted == 0:
        risk_warnings.append("field_not_found")
        risk_warnings.append("manual_review_recommended")
    if any(f.get("field_status") == "evidence_only" for f in fields.values()):
        risk_warnings.append("only_pointer_found")

    # Record status.
    extracted_core = sum(
        1 for cf in CORE_FIELDS
        if fields.get(cf, {}).get("field_status") in ("extracted", "partial")
    )
    if all_low_text or not doc_runtime:
        if any(d["text_present"] for d in doc_runtime):
            record_status = "ocr_needed"
        else:
            record_status = "failed"
    elif fields_extracted == 0:
        record_status = "source_link_only"
    elif extracted_core >= 4 and not any_ocr_needed:
        record_status = "parsed"
    else:
        record_status = "partial"

    # Display options / honest badge.
    display_options = build_display_options(
        record_status, fields_extracted, any_ocr_needed, all_low_text, doc_runtime
    )

    return {
        "notice_id": notice_id,
        "canonical_key": canonical_key,
        "titol": rec.get("titol", ""),
        "year": rec.get("year", ""),
        "record_status": record_status,
        "documents": docs_out,
        "fields": fields,
        "risk_warnings": sorted(set(risk_warnings)),
        "display_options": display_options,
        "_counts": {
            "fields_extracted": fields_extracted,
            "fields_missing": fields_missing,
        },
    }


def build_display_options(record_status, fields_extracted, any_ocr_needed,
                          all_low_text, doc_runtime):
    can_show_fields = fields_extracted > 0
    if record_status == "parsed":
        badge = "parsed"
        msg = "Structured fields extracted from the pliegos with supporting evidence."
    elif record_status == "ocr_needed":
        badge = "ocr_needed"
        msg = "Document appears image-based; OCR needed before reliable extraction."
    elif record_status == "source_link_only":
        badge = "source_link_only"
        msg = ("Could not parse structured fields from this document. "
               "Source document link is available.")
    elif record_status == "failed":
        badge = "source_link_only"
        msg = "No extractable text available; open the source document."
    else:  # partial
        badge = "partial"
        if any_ocr_needed:
            msg = ("Some fields parsed. One document has low text coverage; "
                   "open source document or run OCR later.")
        else:
            msg = "Some fields parsed; important fields missing. Manual review recommended."
    return {
        "summary_ready": False,
        "can_show_extracted_fields": can_show_fields,
        "can_show_source_links": True,
        "manual_review_recommended": record_status in ("partial", "source_link_only", "failed"),
        "ocr_needed": bool(any_ocr_needed or all_low_text),
        "primary_status_badge": badge,
        "fallback_message": msg,
    }


# --------------------------------------------------------------------------- #
# Manifest / report / samples
# --------------------------------------------------------------------------- #

def build_counts(records):
    roles = {}
    statuses = {}
    documents = 0
    fields_extracted = 0
    fields_missing = 0
    ocr_docs = 0
    source_link_only = 0
    for rec in records:
        statuses[rec["record_status"]] = statuses.get(rec["record_status"], 0) + 1
        if rec["record_status"] == "source_link_only":
            source_link_only += 1
        fields_extracted += rec["_counts"]["fields_extracted"]
        fields_missing += rec["_counts"]["fields_missing"]
        for d in rec["documents"]:
            documents += 1
            r = d.get("role")
            if r:
                roles[r] = roles.get(r, 0) + 1
            if d.get("text_quality", {}).get("ocr_needed"):
                ocr_docs += 1
    return {
        "records": len(records),
        "documents": documents,
        "roles": roles,
        "statuses": statuses,
        "fields_extracted": fields_extracted,
        "fields_missing": fields_missing,
        "ocr_needed_documents": ocr_docs,
        "source_link_only_records": source_link_only,
    }


def build_manifest(records, limits):
    counts = build_counts(records)
    # Strip private _counts before emission.
    clean = []
    for rec in records:
        rec = dict(rec)
        rec.pop("_counts", None)
        clean.append(rec)
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generated_by_prompt": GENERATED_BY_PROMPT,
        "target_version": TARGET_VERSION,
        "production_write_performed": False,
        "input_schema": INPUT_SCHEMA,
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "limits": limits,
        "counts": counts,
        "records": clean,
    }


def render_report(manifest):
    c = manifest["counts"]
    lines = []
    add = lines.append
    add("# PCAP/PPT Appendix Extractor Report (p199 / v0.6.53)")
    add("")
    add("## STATE")
    add(f"- schema: `{manifest['schema']}` ({manifest['schema_version']})")
    add(f"- generated_at_utc: {manifest['generated_at_utc']}")
    add(f"- production_write_performed: {manifest['production_write_performed']}")
    add(f"- input_schema: `{manifest['input_schema']}`")
    add("")
    add("## INPUTS ANALYZED")
    add(f"- records: {c['records']}")
    add(f"- documents: {c['documents']}")
    add(f"- roles: {c['roles']}")
    add(f"- record statuses: {c['statuses']}")
    add("")
    add("## TEXT QUALITY")
    add("| record | role | pages | chars | chars/page | status | ocr |")
    add("|---|---|---|---|---|---|---|")
    for rec in manifest["records"]:
        for d in rec["documents"]:
            tq = d.get("text_quality", {})
            add(f"| {rec['canonical_key']} | {d.get('role','')} | "
                f"{tq.get('pages','')} | {tq.get('chars','')} | "
                f"{tq.get('chars_per_page','')} | {tq.get('status','')} | "
                f"{tq.get('ocr_needed','')} |")
    add("")
    add("## FIELDS EXTRACTED / MISSING")
    add(f"- fields_extracted (non-null): {c['fields_extracted']}")
    add(f"- fields_missing (null+fallback): {c['fields_missing']}")
    add("")
    add("### Extracted field categories by record")
    for rec in manifest["records"]:
        got = [k for k, v in rec["fields"].items() if v.get("value") is not None]
        add(f"- **{rec['canonical_key']}** ({rec['record_status']}): "
            f"{', '.join(got) if got else '(none)'}")
    add("")
    add("### Missing field categories by record")
    for rec in manifest["records"]:
        miss = [k for k, v in rec["fields"].items() if v.get("value") is None]
        add(f"- **{rec['canonical_key']}**: {', '.join(miss) if miss else '(none)'}")
    add("")
    add("## OCR-NEEDED DOCUMENTS")
    add(f"- ocr_needed_documents: {c['ocr_needed_documents']}")
    for rec in manifest["records"]:
        for d in rec["documents"]:
            if d.get("text_quality", {}).get("ocr_needed"):
                add(f"  - {rec['canonical_key']} / {d.get('role','')} "
                    f"(sha {d.get('sha256','')[:12]}): {d['text_quality']['reason']}")
    add("")
    add("## SOURCE-LINK-ONLY FALLBACK CASES")
    add(f"- source_link_only_records: {c['source_link_only_records']}")
    for rec in manifest["records"]:
        if rec["record_status"] == "source_link_only":
            add(f"  - {rec['canonical_key']}: {rec['display_options']['fallback_message']}")
    add("")
    add("## SAMPLE EVIDENCE (capped)")
    shown = 0
    for rec in manifest["records"]:
        for k, v in rec["fields"].items():
            if v.get("value") is not None and v.get("evidence"):
                ev = v["evidence"][0]
                snippet = ev["excerpt"][:200].replace("\n", " ")
                add(f"- **{rec['canonical_key']} / {k}** "
                    f"({v['field_status']}, {v['confidence']}, p{ev['page']}): {snippet}")
                shown += 1
                break
        if shown >= 6:
            break
    add("")
    add("## RECOMMENDATION FOR NEXT STEP")
    add(_recommendation(manifest))
    add("")
    add("## NO-TOUCH SAFETY")
    add("- production_write_performed=false")
    add("- no downloads, no OCR, no PDF/DOCX parsing")
    add("- outputs under _tmp/appendix/ only")
    add("- data/licitaciones.json and runtime/UI untouched")
    add("")
    return "\n".join(lines)


def _recommendation(manifest):
    c = manifest["counts"]
    parsed = c["statuses"].get("parsed", 0)
    partial = c["statuses"].get("partial", 0)
    if c["fields_extracted"] >= c["records"] * 3 and (parsed + partial) >= c["records"] * 0.6:
        return ("- Extraction yields useful structured fields. Proceed to p200 "
                "(JSON sharding + progressive loader) or p201 (UI DocIntel) per "
                "operator priority. OCR remains future debt for low-coverage PPTs.")
    return ("- Source links are solid but structured extraction is uneven; consider "
            "p199b extraction-rule hardening before UI work. OCR remains future debt.")


def build_samples(records, excerpt_chars):
    samples = []
    # Prefer a spread: a parsed/partial, a source_link_only, an ocr case.
    chosen = []
    for status in ("parsed", "partial", "ocr_needed", "source_link_only", "failed"):
        for rec in records:
            if rec["record_status"] == status and rec not in chosen:
                chosen.append(rec)
                break
    for rec in records:
        if len(chosen) >= 5:
            break
        if rec not in chosen:
            chosen.append(rec)
    chosen = chosen[:5]

    for rec in chosen:
        extracted = {}
        missing_examples = {}
        for k, v in rec["fields"].items():
            if v.get("value") is not None and len(extracted) < 5:
                ev = dict(v["evidence"][0])
                ev["excerpt"] = ev["excerpt"][:excerpt_chars]
                extracted[k] = {
                    "field_status": v["field_status"],
                    "confidence": v["confidence"],
                    "value_preview": v["value"][:300],
                    "evidence": ev,
                }
            elif v.get("value") is None and len(missing_examples) < 4:
                missing_examples[k] = {
                    "field_status": v["field_status"],
                    "display_fallback": v["display_fallback"],
                }
        samples.append({
            "canonical_key": rec["canonical_key"],
            "record_status": rec["record_status"],
            "display_options": rec["display_options"],
            "documents": [
                {"role": d.get("role"), "source_url": d.get("source_url", ""),
                 "final_url": d.get("final_url", ""),
                 "text_quality": d.get("text_quality", {})}
                for d in rec["documents"]
            ],
            "extracted_fields": extracted,
            "missing_field_fallbacks": missing_examples,
        })
    return {
        "schema": "appendix_pcap_ppt_samples/1",
        "generated_by_prompt": GENERATED_BY_PROMPT,
        "production_write_performed": False,
        "sample_count": len(samples),
        "samples": samples,
    }


# --------------------------------------------------------------------------- #
# Validation (inline assertions)
# --------------------------------------------------------------------------- #

def validate_manifest(manifest, excerpt_chars):
    errs = []
    if manifest["schema"] != SCHEMA:
        errs.append("schema mismatch")
    if manifest["production_write_performed"] is not False:
        errs.append("production_write_performed must be False")
    if manifest["counts"]["records"] <= 0:
        errs.append("records must be > 0")
    if manifest["counts"]["documents"] <= 0:
        errs.append("documents must be > 0")
    for rec in manifest["records"]:
        for d in rec["documents"]:
            if not (d.get("source_url") or d.get("final_url")):
                errs.append(f"{rec['canonical_key']}: document missing source/final url")
        for k, v in rec["fields"].items():
            if v.get("value") is not None:
                if not v.get("evidence"):
                    errs.append(f"{rec['canonical_key']}/{k}: non-null field without evidence")
                for ev in v.get("evidence", []):
                    if len(ev.get("excerpt", "")) > excerpt_chars:
                        errs.append(f"{rec['canonical_key']}/{k}: excerpt exceeds cap")
                    if len(ev.get("excerpt", "")) > 100000:
                        errs.append(f"{rec['canonical_key']}/{k}: huge raw body in evidence")
                if len(v.get("value", "")) > VALUE_CAP_CHARS:
                    errs.append(f"{rec['canonical_key']}/{k}: value exceeds cap")
            else:
                fb = v.get("display_fallback")
                if not fb or "mode" not in fb or "reason" not in fb:
                    errs.append(f"{rec['canonical_key']}/{k}: missing display_fallback mode/reason")
        # ocr consistency
        doc_ocr = any(d.get("text_quality", {}).get("ocr_needed") for d in rec["documents"])
        if doc_ocr and not rec["display_options"]["ocr_needed"]:
            errs.append(f"{rec['canonical_key']}: ocr doc not surfaced in display_options")
    return errs


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def parse_args(argv):
    ap = argparse.ArgumentParser(description="PCAP/PPT Appendix extractor (p199)")
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--samples", required=True)
    ap.add_argument("--excerpt-chars", type=int, default=500)
    ap.add_argument("--window-chars", type=int, default=4000)
    ap.add_argument("--max-records", type=int, default=0)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--strict-evidence", dest="strict_evidence",
                    action="store_true", default=True)
    ap.add_argument("--no-strict-evidence", dest="strict_evidence",
                    action="store_false")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    repo_root = os.getcwd()

    # Output safety up front.
    for p in (args.out, args.report, args.samples):
        assert_output_path_safe(p, repo_root)

    # Load + validate input.
    with open(args.input, "r", encoding="utf-8") as fh:
        src = json.load(fh)
    if src.get("schema") != INPUT_SCHEMA:
        raise SystemExit(f"[FATAL] input schema != {INPUT_SCHEMA}: {src.get('schema')}")
    if src.get("production_write_performed") is not False:
        raise SystemExit("[FATAL] input production_write_performed must be False")

    records_in = src.get("records", [])
    if args.max_records and args.max_records > 0:
        records_in = records_in[:args.max_records]

    out_records = []
    for rec in records_in:
        out_records.append(
            process_record(rec, repo_root, args.excerpt_chars,
                           args.window_chars, args.debug)
        )

    limits = {
        "excerpt_chars": args.excerpt_chars,
        "window_chars": args.window_chars,
        "value_cap_chars": VALUE_CAP_CHARS,
        "max_records": args.max_records,
        "strict_evidence": args.strict_evidence,
        "source_input": _norm_rel(args.input),
    }
    manifest = build_manifest(out_records, limits)

    errs = validate_manifest(manifest, args.excerpt_chars)
    if errs:
        for e in errs:
            sys.stderr.write(f"[VALIDATION] {e}\n")
        raise SystemExit(f"[FATAL] {len(errs)} validation error(s); refusing to write")

    # Ensure output dirs exist (under _tmp/).
    for p in (args.out, args.report, args.samples):
        d = os.path.dirname(os.path.join(repo_root, p))
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    with open(args.report, "w", encoding="utf-8") as fh:
        fh.write(render_report(manifest))
    with open(args.samples, "w", encoding="utf-8") as fh:
        json.dump(build_samples(out_records, args.excerpt_chars), fh,
                  ensure_ascii=False, indent=2)

    c = manifest["counts"]
    print(f"[OK] wrote {args.out}")
    print(f"     records={c['records']} documents={c['documents']} "
          f"roles={c['roles']}")
    print(f"     statuses={c['statuses']}")
    print(f"     fields_extracted={c['fields_extracted']} "
          f"fields_missing={c['fields_missing']} "
          f"ocr_docs={c['ocr_needed_documents']} "
          f"source_link_only={c['source_link_only_records']}")
    print(f"[OK] wrote {args.report}")
    print(f"[OK] wrote {args.samples}")
    print("[SAFE] production_write_performed=false; no downloads; no OCR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
