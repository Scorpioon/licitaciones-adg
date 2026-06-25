#!/usr/bin/env python3
"""
tools/docreader.py — DocReader prototype (v0.6.48 / p195)

DocReader is the first prototype of the document *content* extraction layer.
The inventory layer (DocIndexer -> LinkResolver -> DocEvidenceChain) already
populates production `documents[]` with confirmed, resolver-verified PDF links.
What is missing is reading those PDFs and extracting their text.

This tool, strictly local-only and read-only with respect to production data:

  1. Reads confirmed `documents[]` links from data/licitaciones.json (read-only).
  2. Selects a small, bounded, deterministic pilot of active-opportunity records.
  3. Optionally downloads each PDF to a temp file (streamed, byte-capped).
  4. Extracts per-page text with pdfplumber (primary) / pdfminer.six (fallback).
  5. Writes full extracted text only to gitignored _tmp paths.
  6. Emits a local-only `docread/1` manifest carrying metadata + short excerpts.

Hard guarantees:
  * Never mutates data/licitaciones.json or any production / runtime file.
  * Never commits PDF binaries or raw full text (all under gitignored _tmp/).
  * Output is refused unless it resolves under an allowed local root.
  * Caps on records / pdfs / per-record docs / bytes are always enforced.
  * PDFs are deleted after extraction unless --cache is explicitly set.

Stdlib + requests + pdfplumber + pdfminer.six only. No production write.
"""

import argparse
import hashlib
import io
import json
import os
import sys
import tempfile
import time
from collections import Counter, OrderedDict
from datetime import datetime, date, timezone

import requests

VERSION = "v0.6.48"
SCHEMA = "docread/1"
SCHEMA_VERSION = "1.0"
GENERATED_BY_PROMPT = "p195"
MODE = "DOCREADER_PROTOTYPE"

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

# Document types that are awards / formalizations — excluded by operator lock.
_EXCLUDED_DOC_TYPES = {"ACTA_ADJ", "ACTA_FORM"}

# Recognised failure / outcome modes (also drives the counts block).
_FAILURE_MODES = [
    "no_documents",
    "unsupported_type",
    "download_skipped",
    "download_failed",
    "parse_failed",
    "text_empty",
    "partial_parse",
    "extracted",
    "duplicate_doc",
    "too_large",
    "timeout",
]


# --------------------------------------------------------------------------- #
# Path safety
# --------------------------------------------------------------------------- #
def _is_safe_output(path):
    """Return (ok, resolved_relpath). Output must resolve under a safe root and
    must not be a forbidden production/runtime file."""
    repo_root = os.getcwd()
    abspath = os.path.abspath(path)
    try:
        rel = os.path.relpath(abspath, repo_root)
    except ValueError:
        return False, abspath
    norm = os.path.normpath(rel)
    # Reject anything that escapes the repo root.
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
            "[docreader] REFUSED unsafe output path for %s: %s\n"
            "            allowed roots: %s\n"
            % (label, norm, ", ".join(_SAFE_PREFIXES))
        )
        sys.exit(2)
    os.makedirs(path, exist_ok=True)
    return norm


def _ensure_safe_file(path, label):
    ok, norm = _is_safe_output(path)
    if not ok:
        sys.stderr.write(
            "[docreader] REFUSED unsafe output path for %s: %s\n"
            "            allowed roots: %s\n"
            % (label, norm, ", ".join(_SAFE_PREFIXES))
        )
        sys.exit(2)
    parent = os.path.dirname(path)
    if parent:
        _ensure_safe_dir(parent, label + " (parent dir)")
    return norm


# --------------------------------------------------------------------------- #
# Selection helpers
# --------------------------------------------------------------------------- #
def _year_of(value):
    s = str(value or "").strip()
    if len(s) >= 4 and s[:4].isdigit():
        return int(s[:4])
    return None


def _parse_iso_date(value):
    s = str(value or "").strip()
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            y, m, d = s.split("-")
            return date(int(y), int(m), int(d))
        except (ValueError, TypeError):
            return None
    return None


def _has_award_winner(rec):
    for award in (rec.get("award_results") or []):
        if str(award.get("winning_party_name") or "").strip():
            return True
    return False


def _record_eligible(rec):
    """Operator-lock record predicate.

    Include:
      - data_pub year == 2026, OR
      - data_pub year == 2025 AND active_opportunity_eligible AND no award evidence
    Plus, in all cases: active_opportunity_eligible is true and no award evidence
    (adjudicatari blank, no winning_party_name, winner_provenance blank).
    """
    year = _year_of(rec.get("data_pub"))
    if year not in (2025, 2026):
        return False
    if not rec.get("active_opportunity_eligible"):
        return False
    if str(rec.get("adjudicatari") or "").strip():
        return False
    if _has_award_winner(rec):
        return False
    if str(rec.get("winner_provenance") or "").strip():
        return False
    return True


def _document_eligible(doc):
    """Operator-lock document predicate."""
    if doc.get("provenance") != "f2b_resolver":
        return False
    if doc.get("mime_hint") != "application/pdf":
        return False
    if not str(doc.get("url") or "").strip():
        return False
    hs = doc.get("http_status")
    if hs is not None and hs != 200:
        return False
    if str(doc.get("document_type") or "") in _EXCLUDED_DOC_TYPES:
        return False
    return True


def _deadline_valid(rec, today):
    dl = _parse_iso_date(rec.get("data_limit"))
    return bool(dl and dl >= today)


def select_pilot(records, today, max_records, max_pdfs, docs_per_record):
    """Deterministic, bounded selection.

    Tier 1 fills from deadline_valid=true records first; Tier 2 falls back to the
    broader strict-temporal eligible set. Within each tier we prefer records with
    fewer eligible docs and spread across organisme / ccaa via round-robin.
    Returns (selected_record_views, eligible_record_count, eligible_doc_count).
    """
    eligible = []  # list of (rec, eligible_docs, deadline_valid)
    eligible_doc_count = 0
    for rec in records:
        if not _record_eligible(rec):
            continue
        docs = [d for d in (rec.get("documents") or []) if _document_eligible(d)]
        if not docs:
            continue
        eligible.append((rec, docs, _deadline_valid(rec, today)))
        eligible_doc_count += len(docs)

    tier1 = [e for e in eligible if e[2]]
    tier2 = [e for e in eligible if not e[2]]

    def order_tier(tier):
        # Stable, deterministic: fewer eligible docs first, then a diversity
        # round-robin across (organisme, ccaa) groups.
        groups = OrderedDict()
        for rec, docs, dv in sorted(
            tier,
            key=lambda e: (
                len(e[1]),
                str(e[0].get("organisme") or ""),
                str(e[0].get("ccaa") or ""),
                str(e[0].get("id") or ""),
            ),
        ):
            key = (str(rec.get("organisme") or ""), str(rec.get("ccaa") or ""))
            groups.setdefault(key, []).append((rec, docs, dv))
        ordered = []
        while groups:
            for key in list(groups.keys()):
                bucket = groups[key]
                ordered.append(bucket.pop(0))
                if not bucket:
                    del groups[key]
        return ordered

    ordered = order_tier(tier1) + order_tier(tier2)

    selected = []
    total_docs = 0
    for rec, docs, dv in ordered:
        if len(selected) >= max_records:
            break
        if total_docs >= max_pdfs:
            break
        take = docs[:docs_per_record]
        remaining = max_pdfs - total_docs
        if remaining <= 0:
            break
        take = take[:remaining]
        if not take:
            continue
        selected.append({
            "rec": rec,
            "docs": take,
            "deadline_valid": dv,
            "selection_tier": "deadline_valid" if dv else "strict_temporal_fallback",
        })
        total_docs += len(take)

    return selected, len(eligible), eligible_doc_count


def _record_attributes(rec, today):
    return {
        "published_year": _year_of(rec.get("data_pub")),
        "active_opportunity_eligible": bool(rec.get("active_opportunity_eligible")),
        "has_adjudicatari": bool(str(rec.get("adjudicatari") or "").strip()),
        "has_award_winner": _has_award_winner(rec),
        "has_winner_provenance": bool(str(rec.get("winner_provenance") or "").strip()),
        "deadline_valid": _deadline_valid(rec, today),
        "data_limit": rec.get("data_limit"),
    }


# --------------------------------------------------------------------------- #
# Download + extraction
# --------------------------------------------------------------------------- #
def _stream_download(url, dest_path, max_bytes, timeout, session):
    """Stream a URL to dest_path, aborting if it exceeds max_bytes.

    Returns dict: {ok, status, http_status, final_url, downloaded_bytes,
    error_class, error_message}. status is one of: ok, too_large, timeout,
    download_failed."""
    out = {
        "ok": False,
        "status": "download_failed",
        "http_status": None,
        "final_url": None,
        "downloaded_bytes": 0,
        "error_class": None,
        "error_message": None,
    }
    try:
        resp = session.get(
            url, stream=True, timeout=timeout, allow_redirects=True,
            headers={"User-Agent": "ADGOPS-DocReader/%s (prototype)" % VERSION},
        )
        out["http_status"] = resp.status_code
        out["final_url"] = resp.url
        if resp.status_code != 200:
            out["status"] = "download_failed"
            out["error_class"] = "http_status"
            out["error_message"] = "HTTP %s" % resp.status_code
            resp.close()
            return out
        downloaded = 0
        with open(dest_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > max_bytes:
                    out["downloaded_bytes"] = downloaded
                    out["status"] = "too_large"
                    out["error_class"] = "too_large"
                    out["error_message"] = (
                        "exceeded %d bytes cap" % max_bytes
                    )
                    resp.close()
                    return out
                fh.write(chunk)
        out["downloaded_bytes"] = downloaded
        out["ok"] = True
        out["status"] = "ok"
        resp.close()
        return out
    except requests.exceptions.Timeout as exc:
        out["status"] = "timeout"
        out["error_class"] = "timeout"
        out["error_message"] = str(exc)[:300]
        return out
    except requests.exceptions.RequestException as exc:
        out["status"] = "download_failed"
        out["error_class"] = exc.__class__.__name__
        out["error_message"] = str(exc)[:300]
        return out


def _extract_pdfplumber(pdf_path):
    """Return (pages:list[str], page_count:int) or raise."""
    import pdfplumber
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return pages, len(pages)


def _extract_pdfminer(pdf_path):
    """Return (pages:list[str], page_count:int) or raise."""
    from pdfminer.high_level import extract_text
    from pdfminer.pdfpage import PDFPage
    with open(pdf_path, "rb") as fh:
        page_count = sum(1 for _ in PDFPage.get_pages(fh))
    pages = []
    for i in range(page_count):
        txt = extract_text(pdf_path, page_numbers=[i]) or ""
        pages.append(txt)
    if not pages:
        whole = extract_text(pdf_path) or ""
        pages = [whole]
        page_count = 1
    return pages, page_count


def _render_full_text(pages):
    parts = []
    for idx, txt in enumerate(pages, start=1):
        parts.append("--- PAGE %d ---" % idx)
        parts.append(txt if txt is not None else "")
    return "\n".join(parts)


def extract_pdf(pdf_path):
    """Run pdfplumber primary, pdfminer fallback.

    Returns dict: {pages, chars, extractor, extraction_status, error_class,
    error_message, full_text}.
    extraction_status in: extracted, partial_parse, text_empty, parse_failed."""
    result = {
        "pages": None,
        "chars": 0,
        "extractor": None,
        "extraction_status": "parse_failed",
        "error_class": None,
        "error_message": None,
        "full_text": "",
    }
    plumber_err = None
    pages = None
    page_count = 0
    extractor = None
    try:
        pages, page_count = _extract_pdfplumber(pdf_path)
        extractor = "pdfplumber"
    except Exception as exc:  # noqa: BLE001 - want broad fallback
        plumber_err = (exc.__class__.__name__, str(exc)[:300])
        pages = None

    text_chars = sum(len((p or "").strip()) for p in pages) if pages else 0

    if not pages or text_chars == 0:
        # pdfplumber failed or produced no usable text -> pdfminer fallback.
        try:
            pages, page_count = _extract_pdfminer(pdf_path)
            extractor = "pdfminer"
            text_chars = sum(len((p or "").strip()) for p in pages)
        except Exception as exc:  # noqa: BLE001
            result["extractor"] = "pdfminer"
            result["extraction_status"] = "parse_failed"
            result["error_class"] = exc.__class__.__name__
            result["error_message"] = str(exc)[:300]
            if plumber_err:
                result["error_message"] = (
                    "pdfplumber=%s:%s ; pdfminer=%s"
                    % (plumber_err[0], plumber_err[1], result["error_message"])
                )
            return result

    full_text = _render_full_text(pages)
    result["pages"] = page_count
    result["chars"] = sum(len(p or "") for p in pages)
    result["extractor"] = extractor
    result["full_text"] = full_text

    if text_chars == 0:
        result["extraction_status"] = "text_empty"
    elif any((p or "").strip() == "" for p in pages):
        # At least one page yielded text, but at least one page was empty.
        result["extraction_status"] = "partial_parse"
    else:
        result["extraction_status"] = "extracted"

    if plumber_err and extractor == "pdfminer":
        result["error_class"] = plumber_err[0]
        result["error_message"] = "pdfplumber fallback: %s" % plumber_err[1]

    return result


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build_argparser():
    p = argparse.ArgumentParser(
        prog="docreader",
        description="DocReader prototype — local-only PDF content extraction (p195).",
    )
    p.add_argument("--input", default=os.path.join("data", "licitaciones.json"))
    p.add_argument("--out", default=os.path.join("_tmp", "docreader", "manifest_docread1.json"))
    p.add_argument("--text-dir", default=os.path.join("_tmp", "docreader", "text"))
    p.add_argument("--cache-dir", default=os.path.join("_tmp", "docreader", "cache"))
    p.add_argument("--cache", action="store_true", default=False,
                   help="Persist downloaded PDFs under cache-dir instead of deleting them.")
    p.add_argument("--dry-run-select", action="store_true", default=False,
                   help="Select and write manifest without downloading/extracting.")
    p.add_argument("--max-records", type=int, default=40)
    p.add_argument("--max-pdfs", type=int, default=80)
    p.add_argument("--docs-per-record", type=int, default=2)
    p.add_argument("--max-mb", type=float, default=25.0)
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--sleep", type=float, default=1.0)
    p.add_argument("--excerpt-chars", type=int, default=1200)
    p.add_argument("--include-robustness-sample", action="store_true", default=False,
                   help="(reserved) include a tiny explicit robustness sample. Not implemented; no-op.")
    p.add_argument("--verbose", action="store_true", default=False)
    return p


def main(argv=None):
    args = build_argparser().parse_args(argv)

    # Validate output targets up front (also enforced again before each write).
    out_norm = _ensure_safe_file(args.out, "--out manifest")
    text_dir_norm = _ensure_safe_dir(args.text_dir, "--text-dir")
    cache_dir_norm = None
    if args.cache:
        cache_dir_norm = _ensure_safe_dir(args.cache_dir, "--cache-dir")

    if not os.path.isfile(args.input):
        sys.stderr.write("[docreader] input not found: %s\n" % args.input)
        return 2

    with open(args.input, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    records = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        sys.stderr.write("[docreader] unexpected input shape; expected dict.data[] list\n")
        return 2

    today = datetime.now().date()
    max_bytes = int(args.max_mb * 1024 * 1024)

    selected, eligible_rec, eligible_doc = select_pilot(
        records, today, args.max_records, args.max_pdfs, args.docs_per_record
    )

    print("[docreader] %s %s  mode=%s" % (SCHEMA, VERSION,
          "DRY_RUN_SELECT" if args.dry_run_select else MODE))
    print("[docreader] eligible records=%d eligible docs=%d" % (eligible_rec, eligible_doc))
    print("[docreader] selected records=%d selected docs=%d (caps: rec<=%d pdfs<=%d dpr<=%d)"
          % (len(selected), sum(len(s["docs"]) for s in selected),
             args.max_records, args.max_pdfs, args.docs_per_record))

    counts = Counter()
    seen_sha = {}
    out_records = []
    session = None if args.dry_run_select else requests.Session()

    for sel in selected:
        rec = sel["rec"]
        attrs = _record_attributes(rec, today)
        rec_view = OrderedDict()
        rec_view["notice_id"] = rec.get("id")
        rec_view["canonical_key"] = rec.get("canonical_key")
        rec_view["titol"] = rec.get("titol")
        rec_view["organisme"] = rec.get("organisme")
        rec_view["ccaa"] = rec.get("ccaa")
        rec_view["data_pub"] = rec.get("data_pub")
        rec_view["published_year"] = attrs["published_year"]
        rec_view["data_limit"] = attrs["data_limit"]
        rec_view["deadline_valid"] = attrs["deadline_valid"]
        rec_view["active_opportunity_eligible"] = attrs["active_opportunity_eligible"]
        rec_view["has_adjudicatari"] = attrs["has_adjudicatari"]
        rec_view["has_award_winner"] = attrs["has_award_winner"]
        rec_view["has_winner_provenance"] = attrs["has_winner_provenance"]
        rec_view["selection_tier"] = sel["selection_tier"]
        rec_view["documents"] = []

        for doc in sel["docs"]:
            dv = OrderedDict()
            url = str(doc.get("url") or "").strip()
            dv["url"] = url
            dv["final_url"] = None
            dv["provenance"] = doc.get("provenance")
            dv["source_section"] = doc.get("source_section")
            dv["document_type"] = doc.get("document_type")
            dv["mime"] = doc.get("mime_hint")
            dv["http_status"] = doc.get("http_status")
            dv["doc_sha256"] = None
            dv["downloaded_bytes"] = None
            dv["pages"] = None
            dv["chars"] = None
            dv["extractor"] = None
            dv["extraction_status"] = None
            dv["error_class"] = None
            dv["error_message"] = None
            dv["text_location"] = None
            dv["cache_location"] = None
            dv["excerpt"] = None
            rec_view["documents"].append(dv)

            if args.dry_run_select:
                dv["extraction_status"] = "download_skipped"
                counts["download_skipped"] += 1
                continue

            # --- real download ---
            if args.sleep > 0:
                time.sleep(args.sleep)
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf", prefix="docreader_")
            os.close(tmp_fd)
            keep_pdf = False
            try:
                dl = _stream_download(url, tmp_path, max_bytes, args.timeout, session)
                dv["final_url"] = dl["final_url"]
                if dl["http_status"] is not None:
                    dv["http_status"] = dl["http_status"]
                dv["downloaded_bytes"] = dl["downloaded_bytes"]

                if not dl["ok"]:
                    dv["extraction_status"] = dl["status"]
                    dv["error_class"] = dl["error_class"]
                    dv["error_message"] = dl["error_message"]
                    counts[dl["status"]] += 1
                    if args.verbose:
                        print("  doc FAIL %s %s" % (dl["status"], url[:90]))
                    continue

                # sha256 of the downloaded bytes
                sha = hashlib.sha256()
                with open(tmp_path, "rb") as fh:
                    for blk in iter(lambda: fh.read(65536), b""):
                        sha.update(blk)
                sha_hex = sha.hexdigest()
                dv["doc_sha256"] = sha_hex

                if sha_hex in seen_sha:
                    dv["extraction_status"] = "duplicate_doc"
                    dv["text_location"] = seen_sha[sha_hex].get("text_location")
                    dv["pages"] = seen_sha[sha_hex].get("pages")
                    dv["chars"] = seen_sha[sha_hex].get("chars")
                    dv["extractor"] = seen_sha[sha_hex].get("extractor")
                    dv["excerpt"] = seen_sha[sha_hex].get("excerpt")
                    counts["duplicate_doc"] += 1
                    if args.verbose:
                        print("  doc DUP  %s" % sha_hex[:16])
                    continue

                ext = extract_pdf(tmp_path)
                dv["pages"] = ext["pages"]
                dv["chars"] = ext["chars"]
                dv["extractor"] = ext["extractor"]
                dv["extraction_status"] = ext["extraction_status"]
                dv["error_class"] = ext["error_class"]
                dv["error_message"] = ext["error_message"]

                if ext["extraction_status"] in ("extracted", "partial_parse", "text_empty"):
                    text_path = os.path.join(args.text_dir, "%s.txt" % sha_hex)
                    _ensure_safe_file(text_path, "text output")
                    with open(text_path, "w", encoding="utf-8") as tf:
                        tf.write(ext["full_text"])
                    dv["text_location"] = os.path.normpath(text_path)
                    excerpt = ext["full_text"][:args.excerpt_chars]
                    dv["excerpt"] = excerpt

                counts[ext["extraction_status"]] += 1

                if args.cache:
                    cache_path = os.path.join(args.cache_dir, "%s.pdf" % sha_hex)
                    _ensure_safe_file(cache_path, "cache pdf")
                    with open(tmp_path, "rb") as src, open(cache_path, "wb") as dst:
                        dst.write(src.read())
                    dv["cache_location"] = os.path.normpath(cache_path)

                seen_sha[sha_hex] = dv
                if args.verbose:
                    print("  doc OK   %s pages=%s chars=%s ext=%s"
                          % (ext["extraction_status"], ext["pages"], ext["chars"],
                             ext["extractor"]))
            finally:
                # Temp PDF is always removed; cache copy (if any) already written.
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except OSError:
                    pass

        if not rec_view["documents"]:
            counts["no_documents"] += 1
        out_records.append(rec_view)

    selection_summary = OrderedDict([
        ("eligible_records", eligible_rec),
        ("eligible_documents", eligible_doc),
        ("selected_records", len(selected)),
        ("selected_documents", sum(len(s["docs"]) for s in selected)),
        ("deadline_valid_selected", sum(1 for s in selected if s["deadline_valid"])),
        ("strict_temporal_fallback_selected",
         sum(1 for s in selected if not s["deadline_valid"])),
    ])

    counts_block = OrderedDict()
    for mode in _FAILURE_MODES:
        counts_block[mode] = counts.get(mode, 0)

    manifest = OrderedDict([
        ("schema", SCHEMA),
        ("schema_version", SCHEMA_VERSION),
        ("generated_by_prompt", GENERATED_BY_PROMPT),
        ("target_version", VERSION),
        ("mode", "DRY_RUN_SELECT" if args.dry_run_select else MODE),
        ("production_write_performed", False),
        ("input", os.path.normpath(args.input)),
        ("generated_at_utc", datetime.now(timezone.utc).isoformat()),
        ("limits", OrderedDict([
            ("max_records", args.max_records),
            ("max_pdfs", args.max_pdfs),
            ("docs_per_record", args.docs_per_record),
            ("max_mb", args.max_mb),
            ("timeout", args.timeout),
            ("sleep", args.sleep),
            ("excerpt_chars", args.excerpt_chars),
            ("cache", bool(args.cache)),
            ("dry_run_select", bool(args.dry_run_select)),
        ])),
        ("selection_summary", selection_summary),
        ("counts", counts_block),
        ("records", out_records),
    ])

    _ensure_safe_file(args.out, "--out manifest")
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    print("[docreader] counts: %s"
          % " ".join("%s=%d" % (k, counts_block[k]) for k in _FAILURE_MODES
                     if counts_block[k]))
    print("[docreader] manifest -> %s" % out_norm)
    print("[docreader] text-dir -> %s" % text_dir_norm)
    if cache_dir_norm:
        print("[docreader] cache-dir -> %s" % cache_dir_norm)
    print("[docreader] production_write_performed=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
