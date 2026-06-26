#!/usr/bin/env python3
"""
tools/document_source_targeting.py — Document Source Targeting + Labels (v0.6.51 / p198)

Local-only, read-only audit + labeling layer that sits one step above DocReader
(docread/1) and the Appendix extractor (appendix/1).

Background (established by p195/p196/p197):
  * DocReader downloads the *confirmed* `f2b_resolver` PDF links and extracts text.
  * For active SDA / open-procedure records those confirmed links resolve to two
    PLACSP machine-generated wrappers: the "Anuncio de licitación" notice and the
    "Documento de Pliegos" index page.
  * The "Documento de Pliegos" page is an INDEX: it lists the real attachment
    *filenames* (Pliego Cláusulas Administrativas = PCAP, Pliego Prescripciones
    Técnicas = PPT, ANEXO*.docx, Modelo de oferta*.xlsx, ...) but NOT their text
    and NOT an inline download URL.

What this tool answers (no network, no parsing of PDFs/DOCX):
  1. Which sampled documents are `documento_pliegos`?
  2. What attachment filenames / types do those index pages reference?
  3. Are those referenced files already represented in production `documents[]`?
  4. Do those production entries carry a resolvable URL, or only a role slot?
  5. What exact fetch-path gap remains?
  6. Produce reliable, user-facing labels for every known document (so the UI
     never has to show the generic "Documento pdf"), without mutating production
     data.

Hard guarantees:
  * Reads data/licitaciones.json strictly read-only.
  * Never mutates any production / runtime file.
  * Never invents URLs — a referenced attachment only carries a URL if it was
    matched to a real production `documents[]` entry that already had one.
  * All output resolves under _tmp/ or data/fetcher2/ (default _tmp/document_targeting/).
  * No PDF / DOCX / raw full-text is written; only short capped evidence excerpts.

Python standard library only.
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter, OrderedDict
from datetime import datetime, timezone

VERSION = "v0.6.51"
SCHEMA = "document_targeting/1"
SCHEMA_VERSION = "0.1-prototype"
GENERATED_BY_PROMPT = "p198"

# --------------------------------------------------------------------------- #
# Safe output guard — output may only land under these local, gitignored roots.
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

# --------------------------------------------------------------------------- #
# Role / label policy (shared, consistent with p197 role vocabulary).
# --------------------------------------------------------------------------- #
# Content roles assigned by DocReader/Appendix from the PDF text itself.
ROLE_LABELS = OrderedDict([
    ("anuncio_placsp", "Anuncio de licitación"),
    ("anuncio_previo", "Anuncio previo"),
    ("documento_pliegos", "Índice de pliegos"),
    ("pcap", "PCAP / Pliego administrativo"),
    ("ppt", "PPT / Pliego técnico"),
    ("anexo", "Anexo"),
    ("modelo", "Modelo / Plantilla"),
    ("oferta", "Modelo de oferta"),
    ("declaracion", "Declaración"),
    ("acta", "Acta"),
    ("ACTA_ADJ", "Acta de adjudicación"),
    ("ACTA_FORM", "Formalización"),
])

# feed_xml source_section -> (inferred role, display label, confidence).
SECTION_ROLE = OrderedDict([
    ("legaldocumentreference", ("pcap", "PCAP / Pliego administrativo", "medium")),
    ("technicaldocumentreference", ("ppt", "PPT / Pliego técnico", "medium")),
    ("additionalpublicationdocumentreference",
     ("additional", "Documentación adicional", "low")),
])

# Referenced-attachment inferred role -> the production feed_xml source_section
# that would carry that attachment.
ROLE_TO_SECTION = {
    "pcap": "legaldocumentreference",
    "ppt": "technicaldocumentreference",
    "anexo": "additionalpublicationdocumentreference",
    "modelo": "additionalpublicationdocumentreference",
    "oferta": "additionalpublicationdocumentreference",
    "declaracion": "additionalpublicationdocumentreference",
    "other": "additionalpublicationdocumentreference",
}

GENERIC_BAD_LABEL = "Documento pdf"
UNCLASSIFIED_LABEL = "Documento sin clasificar"

_EXT_RE = re.compile(r"\.(docx|doc|pdf|xlsx|xls|zip)\b", re.IGNORECASE)
_CPV_CODE_RE = re.compile(r"^\s*\d{6,8}\s*[-–]")
_LEAD_NUM_RE = re.compile(r"^(?:\d+\s+){1,4}")

# Signal tokens (accent-folded, lowercase) that mark a line as a referenced
# attachment inside the index window.
_ATTACH_SIGNALS = (
    "pliego",
    "prescripciones",
    "clausulas administrativ",
    "anexo",
    "annex",
    "modelo",
    "oferta",
    "declaracion",
)


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


def _ensure_safe_dir(path, label):
    ok, norm = _is_safe_output(path)
    if not ok:
        sys.stderr.write(
            "[doctargeting] REFUSED unsafe output path for %s: %s\n"
            "               allowed roots: %s\n"
            % (label, norm, ", ".join(_SAFE_PREFIXES))
        )
        sys.exit(2)
    os.makedirs(path, exist_ok=True)
    return norm


def _ensure_safe_file(path, label):
    ok, norm = _is_safe_output(path)
    if not ok:
        sys.stderr.write(
            "[doctargeting] REFUSED unsafe output path for %s: %s\n"
            "               allowed roots: %s\n"
            % (label, norm, ", ".join(_SAFE_PREFIXES))
        )
        sys.exit(2)
    parent = os.path.dirname(path)
    if parent:
        _ensure_safe_dir(parent, label + " (parent dir)")
    return norm


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
def _fold(s):
    """Lowercase + strip accents for robust matching."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _load_json(path, label):
    if not os.path.isfile(path):
        sys.stderr.write("[doctargeting] %s not found: %s\n" % (label, path))
        sys.exit(2)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _page1(text):
    """Return the text of page 1 (between '--- PAGE 1 ---' and '--- PAGE 2 ---')."""
    if "--- PAGE 1 ---" in text:
        after = text.split("--- PAGE 1 ---", 1)[1]
        return after.split("--- PAGE 2 ---", 1)[0]
    return text


# --------------------------------------------------------------------------- #
# Referenced-attachment extraction (from documento_pliegos index pages)
# --------------------------------------------------------------------------- #
def _infer_extension(label):
    m = _EXT_RE.search(label)
    if not m:
        return None
    ext = m.group(1).lower()
    return ext


def _infer_role_from_label(label):
    f = _fold(label)
    if "prescripciones" in f and ("tecnic" in f or "tecn" in f):
        return "ppt"
    if "pliego" in f and "tecnic" in f:
        return "ppt"
    if "clausulas administrativ" in f or ("pliego" in f and "administrativ" in f):
        return "pcap"
    if "declaracion" in f:
        return "declaracion"
    if "modelo" in f:
        return "modelo"
    if "oferta" in f:
        return "oferta"
    if "anexo" in f or "annex" in f:
        return "anexo"
    if "pliego" in f:
        # Bare "Pliego ..." with no admin/tecnic qualifier — keep as other.
        return "other"
    return "other"


def _normalize_label(label):
    """Strip PLACSP leading section numbers ('4 1 ANEXO I.docx' -> 'ANEXO I.docx'),
    collapse whitespace, and tidy the space before a file extension."""
    s = re.sub(r"\s+", " ", str(label or "").strip())
    s = _LEAD_NUM_RE.sub("", s).strip()
    # 'economica .xlsx' -> 'economica.xlsx'
    s = re.sub(r"\s+(\.[A-Za-z0-9]+)$", r"\1", s)
    return s


def _looks_like_attachment(line):
    f = _fold(line)
    if _EXT_RE.search(line):
        return True
    for sig in _ATTACH_SIGNALS:
        if sig in f:
            return True
    return False


def extract_referenced_attachments(text, doc_sha, excerpt_chars):
    """Extract referenced attachment filenames from a documento_pliegos page-1
    index window (the block between the CPV header and 'Proceso de Licitación').

    Returns a list of attachment dicts. Never fabricates URLs.
    """
    page1 = _page1(text)
    lines = [ln.rstrip() for ln in page1.splitlines()]

    cpv_idx = None
    proceso_idx = None
    for i, ln in enumerate(lines):
        f = _fold(ln)
        if cpv_idx is None and (
            f.startswith("categorias/cpv")
            or f.startswith("clasificacion cpv")
            or f == "cpv"
        ):
            cpv_idx = i
        if proceso_idx is None and f.startswith("proceso de licitacion"):
            proceso_idx = i

    # Primary: tight window between CPV header and 'Proceso de Licitación'.
    if cpv_idx is not None and proceso_idx is not None and proceso_idx > cpv_idx:
        window = lines[cpv_idx + 1:proceso_idx]
    else:
        # Fallback: scan the whole page for attachment-signal lines.
        window = lines

    attachments = []
    for ln in window:
        raw = ln.strip()
        if not raw:
            continue
        if _CPV_CODE_RE.match(raw):
            continue
        if not _looks_like_attachment(raw):
            continue
        role = _infer_role_from_label(raw)
        ext = _infer_extension(raw)
        excerpt = raw[:excerpt_chars]
        attachments.append(OrderedDict([
            ("raw_label", raw),
            ("normalized_label", _normalize_label(raw)),
            ("inferred_role", role),
            ("extension", ext),
            ("source_doc_sha256", doc_sha),
            ("source_role", "documento_pliegos"),
            ("page", 1),
            ("evidence_excerpt", excerpt),
            ("resolution_status", "filename_only"),
            ("needs_fetch_path", True),
        ]))
    return attachments


# --------------------------------------------------------------------------- #
# Production document matching
# --------------------------------------------------------------------------- #
def match_reference_to_production(ref, prod_docs):
    """Match a referenced attachment to a production documents[] entry for the
    same record, by inferred-role -> feed_xml source_section.

    A 'resolvable' match requires the corresponding feed_xml slot to carry a
    non-empty URL (true for PCAP/PPT legal/technical refs). Anexos map to
    additionalpublicationdocumentreference slots which carry no URL -> gap.
    """
    role = ref.get("inferred_role")
    section = ROLE_TO_SECTION.get(role)
    result = OrderedDict([
        ("matched_existing_document", False),
        ("match_confidence", "none"),
        ("matched_document_url", None),
        ("matched_document_provenance", None),
        ("matched_source_section", None),
        ("match_reason", None),
        ("fetch_gap", None),
        ("resolvable", False),
    ])
    if not section:
        result["match_reason"] = "no_role_to_section_mapping"
        result["fetch_gap"] = "referenced_in_documento_pliegos_but_not_present_as_resolved_document"
        return result

    # feed_xml entries in this record whose source_section matches.
    candidates = [
        d for d in prod_docs
        if d.get("provenance") == "feed_xml"
        and d.get("source_section") == section
    ]
    if not candidates:
        result["match_reason"] = "no_feed_xml_slot_for_section:%s" % section
        result["fetch_gap"] = "referenced_in_documento_pliegos_but_not_present_as_resolved_document"
        return result

    with_url = [d for d in candidates if str(d.get("url") or "").strip()]
    result["matched_source_section"] = section
    result["matched_document_provenance"] = "feed_xml"

    if with_url and role in ("pcap", "ppt") and len(with_url) == 1:
        # 1:1 legal/technical reference carrying a real URL -> resolvable.
        result["matched_existing_document"] = True
        result["match_confidence"] = "high"
        result["matched_document_url"] = with_url[0].get("url")
        result["resolvable"] = True
        result["match_reason"] = (
            "inferred_role->source_section (%s->%s); single feed_xml entry with url"
            % (role, section)
        )
        result["fetch_gap"] = "url_present_in_feed_xml_but_not_yet_resolved_by_f2b"
    elif with_url:
        result["matched_existing_document"] = True
        result["match_confidence"] = "medium"
        result["matched_document_url"] = with_url[0].get("url")
        result["resolvable"] = True
        result["match_reason"] = (
            "inferred_role->source_section (%s->%s); feed_xml entry with url "
            "(ambiguous among %d)" % (role, section, len(with_url))
        )
        result["fetch_gap"] = "url_present_in_feed_xml_but_not_yet_resolved_by_f2b"
    else:
        # Slot exists (e.g. additionalpublicationdocumentreference) but no URL.
        result["matched_existing_document"] = False
        result["match_confidence"] = "low"
        result["match_reason"] = (
            "role maps to %s feed_xml slot(s) (%d) but none carry a url/title"
            % (section, len(candidates))
        )
        result["fetch_gap"] = "referenced_filename_only_no_resolvable_url_in_feed_xml"
    return result


# --------------------------------------------------------------------------- #
# Document labeling
# --------------------------------------------------------------------------- #
def label_docread_document(doc, role):
    """Label a DocReader document using its content role from the appendix layer."""
    if role and role in ROLE_LABELS:
        return OrderedDict([
            ("display_label", ROLE_LABELS[role]),
            ("display_role", role),
            ("confidence", "high"),
            ("source", "content_role"),
            ("do_not_show_as", GENERIC_BAD_LABEL),
        ])
    return OrderedDict([
        ("display_label", UNCLASSIFIED_LABEL),
        ("display_role", "unknown"),
        ("confidence", "low"),
        ("source", "fallback"),
        ("do_not_show_as", GENERIC_BAD_LABEL),
    ])


def label_production_document(doc, url_to_role):
    """Label a production documents[] entry without mutating it.

    f2b_resolver PDFs (title 'Documento pdf') inherit the DocReader content role
    when their URL matches a read document; feed_xml entries are labeled from
    their source_section.
    """
    prov = doc.get("provenance")
    section = doc.get("source_section")
    url = str(doc.get("url") or "").strip()

    if prov == "feed_xml" and section in SECTION_ROLE:
        role, label, conf = SECTION_ROLE[section]
        return OrderedDict([
            ("display_label", label),
            ("display_role", role),
            ("confidence", conf),
            ("source", "source_section"),
            ("do_not_show_as", GENERIC_BAD_LABEL),
        ])

    if prov == "f2b_resolver":
        role = url_to_role.get(url)
        if role and role in ROLE_LABELS:
            return OrderedDict([
                ("display_label", ROLE_LABELS[role]),
                ("display_role", role),
                ("confidence", "high"),
                ("source", "content_role"),
                ("do_not_show_as", GENERIC_BAD_LABEL),
            ])
        return OrderedDict([
            ("display_label", UNCLASSIFIED_LABEL),
            ("display_role", "unknown"),
            ("confidence", "low"),
            ("source", "fallback"),
            ("do_not_show_as", GENERIC_BAD_LABEL),
        ])

    # Unknown provenance / section.
    return OrderedDict([
        ("display_label", UNCLASSIFIED_LABEL),
        ("display_role", "unknown"),
        ("confidence", "low"),
        ("source", "fallback"),
        ("do_not_show_as", GENERIC_BAD_LABEL),
    ])


def reference_display_label(ref):
    """Build a combined label for a referenced attachment, e.g.
    'PPT / Pliego técnico — Pliego Prescripciones Técnicas'."""
    role = ref.get("inferred_role")
    base = ROLE_LABELS.get(role)
    name = ref.get("normalized_label")
    if base and name:
        return "%s — %s" % (base, name)
    if base:
        return base
    return name or UNCLASSIFIED_LABEL


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build_argparser():
    p = argparse.ArgumentParser(
        prog="document_source_targeting",
        description="Document Source Targeting + Labels — local-only audit (p198).",
    )
    p.add_argument("--data", default=os.path.join("data", "licitaciones.json"))
    p.add_argument("--docread", required=True)
    p.add_argument("--appendix", required=True)
    p.add_argument("--text-root", default=os.path.join("_tmp", "docreader", "text"))
    p.add_argument("--out", default=os.path.join(
        "_tmp", "document_targeting", "document_role_index_p198.json"))
    p.add_argument("--report", default=os.path.join(
        "_tmp", "document_targeting", "document_source_targeting_report_p198.md"))
    p.add_argument("--samples", default=os.path.join(
        "_tmp", "document_targeting", "document_label_samples_p198.json"))
    p.add_argument("--excerpt-chars", type=int, default=300)
    p.add_argument("--max-records", type=int, default=None)
    p.add_argument("--debug", action="store_true", default=False)
    return p


def main(argv=None):
    args = build_argparser().parse_args(argv)

    out_norm = _ensure_safe_file(args.out, "--out")
    report_norm = _ensure_safe_file(args.report, "--report")
    samples_norm = _ensure_safe_file(args.samples, "--samples")

    docread = _load_json(args.docread, "--docread manifest")
    appendix = _load_json(args.appendix, "--appendix manifest")

    # --- input validation -------------------------------------------------- #
    if docread.get("schema") != "docread/1":
        sys.stderr.write("[doctargeting] docread schema mismatch: %r\n"
                         % docread.get("schema"))
        sys.exit(2)
    if appendix.get("schema") != "appendix/1":
        sys.stderr.write("[doctargeting] appendix schema mismatch: %r\n"
                         % appendix.get("schema"))
        sys.exit(2)
    if docread.get("production_write_performed") is not False:
        sys.stderr.write("[doctargeting] docread.production_write_performed must be false\n")
        sys.exit(2)
    if appendix.get("production_write_performed") is not False:
        sys.stderr.write("[doctargeting] appendix.production_write_performed must be false\n")
        sys.exit(2)

    if not os.path.isfile(args.data):
        sys.stderr.write("[doctargeting] --data not found: %s\n" % args.data)
        sys.exit(2)
    with open(args.data, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    prod_records = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(prod_records, list):
        sys.stderr.write("[doctargeting] unexpected --data shape; expected dict.data[]\n")
        sys.exit(2)

    # Index production records by (notice_id, canonical_key) preferring records
    # that actually carry documents (some duplicate ids carry an empty list).
    prod_index = {}
    for r in prod_records:
        key = (r.get("id"), r.get("canonical_key"))
        docs = r.get("documents") or []
        if key not in prod_index or (docs and not (prod_index[key].get("documents"))):
            prod_index[key] = r

    # Index appendix roles by doc_sha256.
    appendix_role_by_sha = {}
    for arec in (appendix.get("records") or []):
        for dr in (arec.get("document_roles") or []):
            sha = dr.get("doc_sha256")
            if sha:
                appendix_role_by_sha[sha] = dr.get("role")

    docread_records = docread.get("records") or []
    if args.max_records is not None:
        docread_records = docread_records[:args.max_records]

    counts_roles = Counter()
    out_records = []
    text_root = args.text_root

    total_docread_docs = 0
    total_prod_docs = 0
    total_refs = 0
    total_matched = 0
    total_unresolved = 0
    missing_text_files = []

    for drec in docread_records:
        notice_id = drec.get("notice_id")
        canonical_key = drec.get("canonical_key")

        # Resolve the production record + its documents[] (read-only).
        prod_rec = prod_index.get((notice_id, canonical_key))
        prod_docs = (prod_rec.get("documents") or []) if prod_rec else []

        # Map confirmed f2b URLs -> content role (from appendix) for label reuse.
        url_to_role = {}

        # 1) Label DocReader documents and detect documento_pliegos text.
        doc_labels = []
        referenced_attachments = []
        for d in (drec.get("documents") or []):
            sha = d.get("doc_sha256")
            url = str(d.get("url") or "").strip()
            role = appendix_role_by_sha.get(sha)
            if url and role:
                url_to_role[url] = role
            total_docread_docs += 1

            label = label_docread_document(d, role)
            counts_roles[label["display_role"]] += 1
            doc_labels.append(OrderedDict([
                ("doc_sha256", sha),
                ("provenance", d.get("provenance")),
                ("source_section", d.get("source_section")),
                ("origin", "docread"),
                ("role", role),
                ("label", label),
            ]))

            # Extract referenced attachments from documento_pliegos index pages.
            if role == "documento_pliegos":
                text_path = os.path.join(text_root, "%s.txt" % sha) if sha else None
                manifest_loc = d.get("text_location")
                if (not text_path or not os.path.isfile(text_path)) and manifest_loc:
                    text_path = manifest_loc
                if text_path and os.path.isfile(text_path):
                    with open(text_path, "r", encoding="utf-8") as tf:
                        text = tf.read()
                    refs = extract_referenced_attachments(
                        text, sha, args.excerpt_chars)
                    referenced_attachments.extend(refs)
                else:
                    missing_text_files.append(sha)
                    if args.debug:
                        sys.stderr.write(
                            "[doctargeting] missing text for documento_pliegos sha=%s\n"
                            % sha)

        # 2) Label production documents[] for the same record (read-only).
        prod_doc_labels = []
        for pd in prod_docs:
            total_prod_docs += 1
            label = label_production_document(pd, url_to_role)
            counts_roles[label["display_role"]] += 1
            prod_doc_labels.append(OrderedDict([
                ("provenance", pd.get("provenance")),
                ("source_section", pd.get("source_section")),
                ("original_title", pd.get("title")),
                ("has_url", bool(str(pd.get("url") or "").strip())),
                ("origin", "production"),
                ("label", label),
            ]))

        # 3) Match each referenced attachment against production documents[].
        for ref in referenced_attachments:
            total_refs += 1
            match = match_reference_to_production(ref, prod_docs)
            ref["match"] = match
            ref["reference_display_label"] = reference_display_label(ref)
            if match["matched_existing_document"]:
                total_matched += 1
            else:
                total_unresolved += 1

        # 4) Per-record fetch-path assessment.
        legal_url = any(
            d.get("provenance") == "feed_xml"
            and d.get("source_section") == "legaldocumentreference"
            and str(d.get("url") or "").strip()
            for d in prod_docs)
        technical_url = any(
            d.get("provenance") == "feed_xml"
            and d.get("source_section") == "technicaldocumentreference"
            and str(d.get("url") or "").strip()
            for d in prod_docs)
        has_index = any(dl.get("role") == "documento_pliegos" for dl in doc_labels)
        resolvable_roles = sorted({
            r["inferred_role"] for r in referenced_attachments
            if r["match"]["resolvable"]})
        unresolvable_roles = sorted({
            r["inferred_role"] for r in referenced_attachments
            if not r["match"]["resolvable"]})

        if not has_index:
            assessment = "no_documento_pliegos_in_sample"
        elif legal_url or technical_url:
            assessment = (
                "PCAP/PPT URLs present in feed_xml legal/technical refs "
                "(resolvable, not yet fetched by f2b); anexos filename-only (gap)")
        else:
            assessment = "documento_pliegos present but no resolvable feed_xml urls"

        fetch_path_assessment = OrderedDict([
            ("has_documento_pliegos", has_index),
            ("referenced_attachment_count", len(referenced_attachments)),
            ("feed_xml_legal_url_present", legal_url),
            ("feed_xml_technical_url_present", technical_url),
            ("resolvable_roles", resolvable_roles),
            ("unresolvable_roles", unresolvable_roles),
            ("assessment", assessment),
        ])

        out_records.append(OrderedDict([
            ("notice_id", notice_id),
            ("canonical_key", canonical_key),
            ("titol", drec.get("titol")),
            ("documents", doc_labels + prod_doc_labels),
            ("referenced_attachments", referenced_attachments),
            ("fetch_path_assessment", fetch_path_assessment),
        ]))

    counts = OrderedDict([
        ("records", len(out_records)),
        ("docread_documents", total_docread_docs),
        ("production_documents_sampled", total_prod_docs),
        ("roles", OrderedDict(sorted(counts_roles.items()))),
        ("referenced_attachments", total_refs),
        ("matched_references", total_matched),
        ("unresolved_references", total_unresolved),
        ("missing_text_files", len(missing_text_files)),
    ])

    manifest = OrderedDict([
        ("schema", SCHEMA),
        ("schema_version", SCHEMA_VERSION),
        ("generated_by_prompt", GENERATED_BY_PROMPT),
        ("target_version", VERSION),
        ("production_write_performed", False),
        ("inputs", OrderedDict([
            ("data", os.path.normpath(args.data)),
            ("docread", os.path.normpath(args.docread)),
            ("appendix", os.path.normpath(args.appendix)),
            ("text_root", os.path.normpath(args.text_root)),
            ("excerpt_chars", args.excerpt_chars),
            ("max_records", args.max_records),
        ])),
        ("generated_at_utc", datetime.now(timezone.utc).isoformat()),
        ("counts", counts),
        ("records", out_records),
    ])

    # --- inline assertions -------------------------------------------------- #
    assert manifest["schema"] == "document_targeting/1"
    assert manifest["production_write_performed"] is False
    n_index = sum(1 for r in out_records if r["fetch_path_assessment"]["has_documento_pliegos"])
    assert n_index >= 1, "expected at least one documento_pliegos analyzed"
    assert total_refs > 0, "expected referenced attachments from index pages"
    for r in out_records:
        for ref in r["referenced_attachments"]:
            assert len(ref["evidence_excerpt"]) <= args.excerpt_chars, \
                "evidence excerpt exceeds excerpt_chars"
            assert ref["match"]["matched_document_url"] is None or \
                str(ref["match"]["matched_document_url"]).startswith("http"), \
                "matched url must come from production data, never invented"
    for r in out_records:
        for d in r["documents"]:
            dl = d["label"]["display_label"]
            if d["label"]["display_role"] not in ("unknown",):
                assert dl != GENERIC_BAD_LABEL, \
                    "classified document must not carry generic 'Documento pdf' label"

    # --- write outputs ------------------------------------------------------ #
    _ensure_safe_file(args.out, "--out")
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    samples = _build_samples(out_records)
    _ensure_safe_file(args.samples, "--samples")
    with open(args.samples, "w", encoding="utf-8") as fh:
        json.dump(samples, fh, ensure_ascii=False, indent=2)

    report = _build_report(manifest, missing_text_files)
    _ensure_safe_file(args.report, "--report")
    with open(args.report, "w", encoding="utf-8") as fh:
        fh.write(report)

    print("[doctargeting] %s %s" % (SCHEMA, VERSION))
    print("[doctargeting] records=%d docread_docs=%d prod_docs=%d refs=%d matched=%d unresolved=%d"
          % (counts["records"], counts["docread_documents"],
             counts["production_documents_sampled"], counts["referenced_attachments"],
             counts["matched_references"], counts["unresolved_references"]))
    print("[doctargeting] manifest -> %s" % out_norm)
    print("[doctargeting] report   -> %s" % report_norm)
    print("[doctargeting] samples  -> %s" % samples_norm)
    print("[doctargeting] production_write_performed=false")
    if missing_text_files:
        print("[doctargeting] WARNING missing text files: %d" % len(missing_text_files))
    return 0


def _build_samples(out_records):
    sample_labels = []
    sample_refs = []
    for r in out_records:
        for d in r["documents"]:
            if len(sample_labels) < 5:
                sample_labels.append(OrderedDict([
                    ("notice_canonical_key", r["canonical_key"]),
                    ("origin", d["origin"]),
                    ("provenance", d.get("provenance")),
                    ("source_section", d.get("source_section")),
                    ("label", d["label"]),
                ]))
        for ref in r["referenced_attachments"]:
            if len(sample_refs) < 10:
                sample_refs.append(OrderedDict([
                    ("notice_canonical_key", r["canonical_key"]),
                    ("raw_label", ref["raw_label"]),
                    ("normalized_label", ref["normalized_label"]),
                    ("inferred_role", ref["inferred_role"]),
                    ("extension", ref["extension"]),
                    ("reference_display_label", ref["reference_display_label"]),
                    ("match_confidence", ref["match"]["match_confidence"]),
                    ("resolvable", ref["match"]["resolvable"]),
                    ("fetch_gap", ref["match"]["fetch_gap"]),
                    ("evidence_excerpt", ref["evidence_excerpt"]),
                ]))
    return OrderedDict([
        ("schema", "document_targeting_samples/1"),
        ("generated_by_prompt", GENERATED_BY_PROMPT),
        ("production_write_performed", False),
        ("sample_document_labels", sample_labels),
        ("sample_referenced_attachments", sample_refs),
    ])


def _build_report(manifest, missing_text_files):
    counts = manifest["counts"]
    lines = []
    a = lines.append
    a("# Document Source Targeting Report — p198 (v0.6.51)\n")
    a("## STATE")
    a("- schema: `%s` (%s)" % (manifest["schema"], manifest["schema_version"]))
    a("- generated_at_utc: %s" % manifest["generated_at_utc"])
    a("- production_write_performed: **%s**" % manifest["production_write_performed"])
    a("- inputs:")
    for k, v in manifest["inputs"].items():
        a("  - %s: `%s`" % (k, v))
    a("")
    a("## INPUTS ANALYZED")
    a("- records: %d" % counts["records"])
    a("- docread documents: %d" % counts["docread_documents"])
    a("- production documents sampled: %d" % counts["production_documents_sampled"])
    a("- referenced attachments: %d" % counts["referenced_attachments"])
    a("- matched references: %d" % counts["matched_references"])
    a("- unresolved references: %d" % counts["unresolved_references"])
    a("- role label distribution: %s" % json.dumps(counts["roles"], ensure_ascii=False))
    a("")
    a("## DOCUMENTO_PLIEGOS FINDINGS")
    n_index = sum(1 for r in manifest["records"]
                  if r["fetch_path_assessment"]["has_documento_pliegos"])
    a("- documento_pliegos index pages analyzed: %d" % n_index)
    a("- These pages are PLACSP machine-generated indexes. They list referenced")
    a("  attachment **filenames only** (PCAP, PPT, ANEXO*.docx, Modelo*.xlsx).")
    a("- No inline download URL / document id / hash is present for those filenames.")
    a("- No real PCAP/PPT body text is present in the sampled documents.")
    a("")
    a("## REFERENCED FILENAMES / TYPES")
    a("| record | raw_label | role | ext | match | resolvable | fetch_gap |")
    a("| --- | --- | --- | --- | --- | --- | --- |")
    for r in manifest["records"]:
        for ref in r["referenced_attachments"]:
            m = ref["match"]
            a("| %s | %s | %s | %s | %s | %s | %s |" % (
                r["canonical_key"], ref["normalized_label"], ref["inferred_role"],
                ref["extension"] or "-", m["match_confidence"],
                m["resolvable"], m["fetch_gap"] or "-"))
    a("")
    a("## MATCHING ATTEMPTS vs PRODUCTION documents[]")
    a("- PCAP referenced filename -> `feed_xml` `legaldocumentreference` entry.")
    a("- PPT referenced filename  -> `feed_xml` `technicaldocumentreference` entry.")
    a("- ANEXO/Modelo filenames   -> `feed_xml` `additionalpublicationdocumentreference`.")
    a("- Key evidence: legal/technical feed_xml entries carry a real")
    a("  `GetDocumentByIdServlet` URL; additionalpublication entries carry no URL.")
    a("- The f2b_resolver PDFs DocReader actually read are the *notice* and the")
    a("  *index* pages (titled generic 'Documento pdf' in production), NOT the PCAP/PPT.")
    a("")
    a("## DOCUMENT LABEL TAXONOMY")
    for role, label in ROLE_LABELS.items():
        a("- `%s` -> %s" % (role, label))
    a("- feed_xml legaldocumentreference -> PCAP / Pliego administrativo")
    a("- feed_xml technicaldocumentreference -> PPT / Pliego técnico")
    a("- feed_xml additionalpublicationdocumentreference -> Documentación adicional")
    a("- generic / unmatched -> %s (never '%s')" % (UNCLASSIFIED_LABEL, GENERIC_BAD_LABEL))
    a("")
    a("## FETCH-PATH GAP")
    a("- **PCAP & PPT are reachable without new discovery**: their URLs already")
    a("  exist in production `documents[]` as feed_xml legal/technical references,")
    a("  but were never fetched because the DocReader/f2b eligibility predicate")
    a("  only accepts `provenance == 'f2b_resolver'` and those feed_xml entries are")
    a("  unverified (empty mime_hint/http_status).")
    a("- **ANEXOs are a true gap**: referenced by filename in the index page, but the")
    a("  corresponding additionalpublication feed_xml entries carry no URL, so they")
    a("  cannot be targeted with current data.")
    if missing_text_files:
        a("- WARNING: %d documento_pliegos text file(s) missing." % len(missing_text_files))
    a("")
    a("## CAN PCAP/PPT PARSING START YET?")
    a("- **No.** No real PCAP/PPT body text was captured in the sample. The next step")
    a("  is a *targeted attachment resolver* that fetches the feed_xml legal/technical")
    a("  URLs (bounded), determines their real format (PDF vs DOCX), and only then can")
    a("  a PCAP/PPT extractor run.")
    a("")
    a("## RECOMMENDED NEXT STEP")
    a("- **A) targeted attachment resolver / fetch-path implementation** (p198b or new")
    a("  p199 candidate): bounded fetch of feed_xml legaldocumentreference /")
    a("  technicaldocumentreference URLs for active records, with format detection.")
    a("- Do NOT start (D) PCAP/PPT extractor yet — no real PCAP/PPT text exists.")
    a("")
    a("## NO-TOUCH SAFETY")
    a("- production_write_performed=false")
    a("- data/licitaciones.json read-only; no production/runtime file modified")
    a("- no PDF/DOCX/raw full text written; only short capped evidence excerpts")
    a("- all outputs under _tmp/document_targeting/")
    a("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
