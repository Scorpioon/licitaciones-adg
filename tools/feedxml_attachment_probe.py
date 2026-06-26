#!/usr/bin/env python3
"""
tools/feedxml_attachment_probe.py — Targeted feed_xml Attachment Probe (v0.6.52 / p198b)

Local-only, bounded probe that answers the practical question left open by p198:
  * p198 proved many real PCAP/PPT URLs already live in production `documents[]`
    as feed_xml `legaldocumentreference` (PCAP) / `technicaldocumentreference`
    (PPT) entries that were never fetched (the f2b/DocReader predicate only
    accepts `provenance == 'f2b_resolver'`).
  * This tool selects a SMALL bounded set of those feed_xml legal/technical URLs,
    fetches them safely, detects the real content type by headers + magic bytes
    (not by URL), extracts text if PDF or DOCX, and writes a manifest + report.

It exists to decide the next roadmap step (p199):
  * If real PCAP/PPT text is extracted -> p199 = PCAP/PPT Appendix extractor.
  * If endpoints are reachable but yield no text -> p199 = feed_xml resolver
    hardening.

Hard guarantees:
  * Reads data/licitaciones.json strictly read-only; never mutates production.
  * No mass download — bounded by --max-records / --max-urls / --docs-per-record.
  * Streams downloads with a hard byte cap (--max-mb); deletes binaries unless
    --cache is explicitly passed.
  * Saves full extracted text ONLY under the (gitignored) --text-dir.
  * All outputs resolve under _tmp/ or data/fetcher2/ (default _tmp/feedxml_probe/).
  * Never writes a tracked output manifest; never writes data/licitaciones.json.
  * production_write_performed is always false.

Dependencies: stdlib + requests + pdfplumber (with pdfminer.six fallback).
DOCX extraction is stdlib-only (zipfile + xml.etree.ElementTree). No installs.
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import requests

VERSION = "v0.6.52"
SCHEMA = "feedxml_probe/1"
SCHEMA_VERSION = "0.1-prototype"
GENERATED_BY_PROMPT = "p198b"

LEGAL_SECTION = "legaldocumentreference"
TECH_SECTION = "technicaldocumentreference"

# source_section -> (inferred role, display label)
SECTION_ROLE = OrderedDict([
    (LEGAL_SECTION, ("pcap", "PCAP / Pliego administrativo")),
    (TECH_SECTION, ("ppt", "PPT / Pliego técnico")),
])

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

_USER_AGENT = (
    "adg-ops-feedxml-probe/0.1 (+local bounded probe; respects robots via "
    "manual bounded selection)"
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
            "[feedxml-probe] REFUSED unsafe output path for %s: %s\n"
            "                allowed roots: %s\n"
            % (label, norm, ", ".join(_SAFE_PREFIXES))
        )
        sys.exit(2)
    os.makedirs(path, exist_ok=True)
    return norm


def _ensure_safe_file(path, label):
    ok, norm = _is_safe_output(path)
    if not ok:
        sys.stderr.write(
            "[feedxml-probe] REFUSED unsafe output path for %s: %s\n"
            "                allowed roots: %s\n"
            % (label, norm, ", ".join(_SAFE_PREFIXES))
        )
        sys.exit(2)
    parent = os.path.dirname(path)
    if parent:
        _ensure_safe_dir(parent, label + " (parent dir)")
    return norm


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
def _load_json(path, label, required=True):
    if not os.path.isfile(path):
        if required:
            sys.stderr.write("[feedxml-probe] %s not found: %s\n" % (label, path))
            sys.exit(2)
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _record_year(rec):
    dp = str(rec.get("data_pub") or rec.get("first_pub_date") or "")
    return dp[:4] if dp[:4].isdigit() else ""


def _endpoint_family(url):
    if "GetDocumentByIdServlet" in url:
        return "servlet_direct"
    if "docAccCmpnt" in url or "GetDocumentsById" in url:
        return "docAccCmpnt_wrapper"
    return "other"


# --------------------------------------------------------------------------- #
# Selection (no network)
# --------------------------------------------------------------------------- #
def select_targets(records, sampled_keys, max_records, max_urls, docs_per_record):
    """Select a bounded set of feed_xml legal/technical references carrying http
    URLs. Returns a list of per-record selection dicts.

    Priority:
      1. records present in the p198 targeting sample (if any),
      2. publication year (2026 then 2025 then newest),
      3. active/no-award records (estat == 'Vigente') before awarded,
    Within a record: prefer one legal (PCAP) + one technical (PPT) pair.
    Global URL de-duplication across the whole selection.
    """
    def rank(rec):
        key = (rec.get("id"), rec.get("canonical_key"))
        in_sample = 0 if key in sampled_keys else 1  # sampled first
        year = _record_year(rec)
        # newest first -> negative int; unknown years sort last
        year_rank = -(int(year)) if year.isdigit() else 1
        estat = str(rec.get("estat") or "")
        active_rank = 0 if estat == "Vigente" else 1
        return (in_sample, active_rank, year_rank, str(rec.get("canonical_key") or ""))

    # Candidate records: those carrying >=1 feed_xml legal/tech doc with http url.
    candidates = []
    for rec in records:
        legal, tech = [], []
        for d in (rec.get("documents") or []):
            if d.get("provenance") != "feed_xml":
                continue
            sec = d.get("source_section")
            if sec not in SECTION_ROLE:
                continue
            url = str(d.get("url") or "").strip()
            if not url or not url.lower().startswith("http"):
                continue
            (legal if sec == LEGAL_SECTION else tech).append(d)
        if legal or tech:
            candidates.append((rec, legal, tech))

    candidates.sort(key=lambda t: rank(t[0]))

    selected = []
    seen_urls = set()
    total_urls = 0

    for rec, legal, tech in candidates:
        if len(selected) >= max_records or total_urls >= max_urls:
            break
        # Interleave legal/technical to get a PCAP+PPT pair first.
        ordered = []
        li = ti = 0
        while (li < len(legal) or ti < len(tech)) and len(ordered) < docs_per_record:
            if li < len(legal):
                ordered.append(legal[li]); li += 1
            if len(ordered) >= docs_per_record:
                break
            if ti < len(tech):
                ordered.append(tech[ti]); ti += 1

        picked = []
        for d in ordered:
            if total_urls >= max_urls:
                break
            url = str(d.get("url") or "").strip()
            if url in seen_urls:
                continue
            seen_urls.add(url)
            total_urls += 1
            sec = d.get("source_section")
            role, label = SECTION_ROLE[sec]
            picked.append(OrderedDict([
                ("source_section", sec),
                ("inferred_role", role),
                ("display_label", label),
                ("url", url),
                ("endpoint_family", _endpoint_family(url)),
                ("original_title", d.get("title") or ""),
                ("mime_hint", d.get("mime_hint") or ""),
                ("format_hint", d.get("format_hint") or ""),
                ("published_at", d.get("published_at") or ""),
            ]))
        if not picked:
            continue
        selected.append(OrderedDict([
            ("notice_id", rec.get("id")),
            ("canonical_key", rec.get("canonical_key")),
            ("titol", (rec.get("titol") or "")[:200]),
            ("estat", rec.get("estat")),
            ("year", _record_year(rec)),
            ("in_p198_sample", (rec.get("id"), rec.get("canonical_key")) in sampled_keys),
            ("documents", picked),
        ]))

    return selected


# --------------------------------------------------------------------------- #
# Download (network) — bounded, streamed, capped
# --------------------------------------------------------------------------- #
def fetch_bounded(url, timeout, max_bytes, session):
    """Stream a URL with a hard byte cap. Returns (info, data_or_None).

    info always carries: http_status, header_content_type, content_length_header,
    final_url, downloaded_bytes, network_status, warnings.
    """
    info = OrderedDict([
        ("http_status", None),
        ("header_content_type", None),
        ("content_length_header", None),
        ("final_url", None),
        ("downloaded_bytes", 0),
        ("network_status", None),
        ("warnings", []),
    ])
    try:
        resp = session.get(url, stream=True, timeout=timeout, allow_redirects=True)
    except requests.exceptions.Timeout:
        info["network_status"] = "timeout"
        return info, None
    except requests.exceptions.RequestException as exc:
        info["network_status"] = "download_failed"
        info["warnings"].append("request_exception:%s" % type(exc).__name__)
        return info, None

    with resp:
        info["http_status"] = resp.status_code
        info["final_url"] = resp.url
        info["header_content_type"] = resp.headers.get("Content-Type")
        clen = resp.headers.get("Content-Length")
        info["content_length_header"] = int(clen) if (clen and clen.isdigit()) else None

        if resp.status_code != 200:
            info["network_status"] = "download_failed"
            info["warnings"].append("http_status_%s" % resp.status_code)
            return info, None

        if info["content_length_header"] and info["content_length_header"] > max_bytes:
            info["network_status"] = "too_large"
            info["warnings"].append(
                "content_length_%d_gt_max_%d" % (info["content_length_header"], max_bytes))
            return info, None

        buf = io.BytesIO()
        too_large = False
        try:
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                buf.write(chunk)
                if buf.tell() > max_bytes:
                    too_large = True
                    break
        except requests.exceptions.Timeout:
            info["network_status"] = "timeout"
            info["downloaded_bytes"] = buf.tell()
            return info, None
        except requests.exceptions.RequestException as exc:
            info["network_status"] = "download_failed"
            info["warnings"].append("stream_exception:%s" % type(exc).__name__)
            info["downloaded_bytes"] = buf.tell()
            return info, None

        info["downloaded_bytes"] = buf.tell()
        if too_large:
            info["network_status"] = "too_large"
            info["warnings"].append("stream_exceeded_max_%d" % max_bytes)
            return info, None

        info["network_status"] = "ok"
        return info, buf.getvalue()


# --------------------------------------------------------------------------- #
# Type detection (headers + magic bytes, not URL)
# --------------------------------------------------------------------------- #
def detect_type(data, header_content_type):
    ct = (header_content_type or "").lower()
    head = data[:8] if data else b""

    if head.startswith(b"%PDF"):
        return "pdf"
    if head[:2] == b"PK":
        # zip container — DOCX if it has word/document.xml
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = set(zf.namelist())
            if "word/document.xml" in names:
                return "docx"
            return "zip_other"
        except zipfile.BadZipFile:
            return "unknown"

    lead = data[:512].lstrip().lower() if data else b""
    if lead.startswith(b"<!doctype html") or lead.startswith(b"<html") or "text/html" in ct:
        return "html"
    if lead.startswith(b"<?xml") or "xml" in ct:
        return "xml"
    if "text/plain" in ct:
        return "text"

    # Heuristic: printable text fallback.
    if data:
        sample = data[:1024]
        printable = sum(1 for b in sample if 9 <= b <= 13 or 32 <= b <= 126 or b >= 160)
        if printable / max(1, len(sample)) > 0.90:
            return "text"
    return "unknown"


# --------------------------------------------------------------------------- #
# Text extraction
# --------------------------------------------------------------------------- #
def extract_pdf_text(data):
    """Extract PDF text. pdfplumber first, pdfminer.six fallback.
    Returns (text, pages, extractor, status, warnings)."""
    warnings = []
    # pdfplumber
    try:
        import pdfplumber
        parts = []
        pages = 0
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                pages += 1
                t = page.extract_text() or ""
                parts.append("--- PAGE %d ---\n%s" % (i, t))
        text = "\n".join(parts).strip()
        if text:
            return text, pages, "pdfplumber", "extracted", warnings
        warnings.append("pdfplumber_empty")
    except Exception as exc:  # noqa: BLE001 — fall back to pdfminer
        warnings.append("pdfplumber_error:%s" % type(exc).__name__)

    # pdfminer.six fallback
    try:
        from pdfminer.high_level import extract_text as miner_extract
        text = (miner_extract(io.BytesIO(data)) or "").strip()
        if text:
            return text, None, "pdfminer", "extracted", warnings
        warnings.append("pdfminer_empty")
        return "", None, "pdfminer", "text_empty", warnings
    except Exception as exc:  # noqa: BLE001
        warnings.append("pdfminer_error:%s" % type(exc).__name__)
        return "", None, "pdfminer", "parse_failed", warnings


_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_docx_text(data):
    """Extract DOCX text using stdlib zipfile + ElementTree (no external pkgs).
    Preserves rough paragraph boundaries. Returns (text, extractor, status, warnings)."""
    warnings = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml = zf.read("word/document.xml")
    except Exception as exc:  # noqa: BLE001
        warnings.append("docx_zip_error:%s" % type(exc).__name__)
        return "", "zipfile+et", "parse_failed", warnings

    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        warnings.append("docx_xml_parse_error:%s" % exc)
        return "", "zipfile+et", "parse_failed", warnings

    paras = []
    for p in root.iter("%sp" % _W_NS):
        runs = []
        for node in p.iter():
            if node.tag == "%st" % _W_NS and node.text:
                runs.append(node.text)
            elif node.tag in ("%stab" % _W_NS,):
                runs.append("\t")
            elif node.tag in ("%sbr" % _W_NS, "%scr" % _W_NS):
                runs.append("\n")
        line = "".join(runs).strip()
        if line:
            paras.append(line)
    text = "\n".join(paras).strip()
    if text:
        return text, "zipfile+et", "extracted", warnings
    return "", "zipfile+et", "text_empty", warnings


def safe_text_diagnostic(data, limit=2000):
    """For HTML/XML/text: return a short, plainly-readable diagnostic snippet
    (NOT a full scraper). Decoded leniently."""
    try:
        s = data[:limit].decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""
    return s


# --------------------------------------------------------------------------- #
# Per-document probe
# --------------------------------------------------------------------------- #
def probe_document(doc, args, session, text_dir_norm):
    """Fetch + detect + extract a single selected document. Returns an entry dict."""
    url = doc["url"]
    entry = OrderedDict([
        ("source_section", doc["source_section"]),
        ("inferred_role", doc["inferred_role"]),
        ("display_label", doc["display_label"]),
        ("url", url),
        ("final_url", None),
        ("endpoint_family", doc["endpoint_family"]),
        ("original_title", doc.get("original_title") or ""),
        ("mime_hint", doc.get("mime_hint") or ""),
        ("http_status", None),
        ("header_content_type", None),
        ("detected_type", None),
        ("downloaded_bytes", 0),
        ("sha256", None),
        ("pages", None),
        ("chars", 0),
        ("extractor", None),
        ("extraction_status", "selected_only"),
        ("text_location", None),
        ("excerpt", ""),
        ("warnings", []),
    ])

    info, data = fetch_bounded(url, args.timeout, args.max_mb * 1024 * 1024, session)
    entry["http_status"] = info["http_status"]
    entry["final_url"] = info["final_url"]
    entry["header_content_type"] = info["header_content_type"]
    entry["downloaded_bytes"] = info["downloaded_bytes"]
    entry["warnings"].extend(info["warnings"])

    net = info["network_status"]
    if net != "ok" or data is None:
        # map network failure to extraction_status
        entry["extraction_status"] = net if net in (
            "too_large", "timeout", "download_failed") else "download_failed"
        return entry

    entry["sha256"] = hashlib.sha256(data).hexdigest()
    detected = detect_type(data, info["header_content_type"])
    entry["detected_type"] = detected

    # Optional cache (only when explicitly requested)
    if args.cache:
        cache_dir_norm = _ensure_safe_dir(args.cache_dir, "--cache-dir")
        ext = {"pdf": ".pdf", "docx": ".docx", "zip_other": ".zip",
               "html": ".html", "xml": ".xml", "text": ".txt"}.get(detected, ".bin")
        cache_path = os.path.join(args.cache_dir, "%s%s" % (entry["sha256"][:16], ext))
        with open(cache_path, "wb") as fh:
            fh.write(data)
        entry["warnings"].append("cached:%s" % os.path.normpath(cache_path))

    text = ""
    if detected == "pdf":
        text, pages, extractor, status, w = extract_pdf_text(data)
        entry["pages"] = pages
        entry["extractor"] = extractor
        entry["extraction_status"] = status
        entry["warnings"].extend(w)
    elif detected == "docx":
        text, extractor, status, w = extract_docx_text(data)
        entry["extractor"] = extractor
        entry["extraction_status"] = status
        entry["warnings"].extend(w)
    elif detected in ("html", "xml", "text"):
        diag = safe_text_diagnostic(data)
        entry["extractor"] = "diagnostic"
        entry["extraction_status"] = "unsupported_type"
        entry["excerpt"] = diag[:args.excerpt_chars]
        entry["warnings"].append("diagnostic_only_%s" % detected)
        return entry
    else:
        entry["extraction_status"] = "unsupported_type"
        entry["warnings"].append("undetected_or_unsupported:%s" % detected)
        return entry

    if text:
        entry["chars"] = len(text)
        entry["excerpt"] = text[:args.excerpt_chars]
        # Save full text under text-dir (gitignored).
        fname = "%s_%s.txt" % (entry["inferred_role"], entry["sha256"][:16])
        text_path = os.path.join(args.text_dir, fname)
        _ensure_safe_file(text_path, "--text-dir text file")
        with open(text_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        entry["text_location"] = os.path.normpath(text_path)
        if entry["extraction_status"] not in ("extracted",):
            entry["extraction_status"] = "extracted"
    else:
        if entry["extraction_status"] == "extracted":
            entry["extraction_status"] = "text_empty"

    return entry


# --------------------------------------------------------------------------- #
# Manifest / report
# --------------------------------------------------------------------------- #
def build_counts(selected, result_records):
    detected_types = Counter()
    roles = Counter()
    status_counter = Counter()
    attempted = 0
    for rec in result_records:
        for d in rec["documents"]:
            roles[d["inferred_role"]] += 1
            if d.get("detected_type"):
                detected_types[d["detected_type"]] += 1
            status_counter[d["extraction_status"]] += 1
            if d["extraction_status"] != "selected_only":
                attempted += 1
    selected_urls = sum(len(r["documents"]) for r in selected)
    return OrderedDict([
        ("selected_records", len(selected)),
        ("selected_urls", selected_urls),
        ("attempted", attempted),
        ("extracted", status_counter.get("extracted", 0)),
        ("partial_parse", status_counter.get("partial_parse", 0)),
        ("text_empty", status_counter.get("text_empty", 0)),
        ("unsupported_type", status_counter.get("unsupported_type", 0)),
        ("download_failed", status_counter.get("download_failed", 0)),
        ("too_large", status_counter.get("too_large", 0)),
        ("timeout", status_counter.get("timeout", 0)),
        ("parse_failed", status_counter.get("parse_failed", 0)),
        ("detected_types", OrderedDict(sorted(detected_types.items()))),
        ("roles", OrderedDict(sorted(roles.items()))),
    ])


def build_report(manifest, dry_run):
    counts = manifest["counts"]
    lines = []
    a = lines.append
    a("# feed_xml Attachment Probe Report — p198b (%s)\n" % VERSION)
    a("## STATE")
    a("- schema: `%s` (%s)" % (manifest["schema"], manifest["schema_version"]))
    a("- generated_at_utc: %s" % manifest["generated_at_utc"])
    a("- mode: **%s**" % ("DRY-RUN SELECT (no network)" if dry_run else "BOUNDED LIVE PROBE"))
    a("- production_write_performed: **%s**" % manifest["production_write_performed"])
    a("- input: `%s`" % manifest["input"])
    a("- limits: `%s`" % json.dumps(manifest["limits"], ensure_ascii=False))
    a("")
    a("## SELECTION STRATEGY")
    a("- Only `provenance == feed_xml` docs in `legaldocumentreference` (PCAP) or")
    a("  `technicaldocumentreference` (PPT) with a non-empty http URL.")
    a("- Priority: p198 sampled records, then newest year (2026>2025), then")
    a("  active/no-award (estat == 'Vigente'), then canonical_key.")
    a("- Per record: prefer one PCAP + one PPT pair (docs-per-record cap).")
    a("- Global URL de-duplication across the whole selection.")
    a("")
    a("## SELECTED RECORDS / URLS")
    a("- selected_records: %d" % counts["selected_records"])
    a("- selected_urls: %d" % counts["selected_urls"])
    a("- role mix: %s" % json.dumps(counts["roles"], ensure_ascii=False))
    a("")
    a("| record | year | estat | role | endpoint | url (head) |")
    a("| --- | --- | --- | --- | --- | --- |")
    for rec in manifest["records"]:
        for d in rec["documents"]:
            a("| %s | %s | %s | %s | %s | %s |" % (
                rec.get("canonical_key"), rec.get("year"), rec.get("estat"),
                d["inferred_role"], d["endpoint_family"],
                (d["url"][:70] + "…") if len(d["url"]) > 70 else d["url"]))
    a("")
    if not dry_run:
        a("## DETECTED TYPE COUNTS")
        a("- %s" % json.dumps(counts["detected_types"], ensure_ascii=False))
        a("")
        a("## EXTRACTION RESULTS")
        a("- attempted: %d" % counts["attempted"])
        a("- extracted: %d" % counts["extracted"])
        a("- text_empty: %d" % counts["text_empty"])
        a("- unsupported_type: %d" % counts["unsupported_type"])
        a("- too_large: %d" % counts["too_large"])
        a("- timeout: %d" % counts["timeout"])
        a("- download_failed: %d" % counts["download_failed"])
        a("- parse_failed: %d" % counts["parse_failed"])
        a("")
        a("| record | role | http | detected | bytes | pages | chars | status | extractor |")
        a("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for rec in manifest["records"]:
            for d in rec["documents"]:
                a("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    rec.get("canonical_key"), d["inferred_role"], d.get("http_status"),
                    d.get("detected_type"), d.get("downloaded_bytes"),
                    d.get("pages"), d.get("chars"), d["extraction_status"],
                    d.get("extractor")))
        a("")
        a("## REPRESENTATIVE EXAMPLES (capped excerpts)")
        shown = 0
        for rec in manifest["records"]:
            for d in rec["documents"]:
                if d["extraction_status"] == "extracted" and shown < 3:
                    shown += 1
                    a("### %s — %s (%s)" % (
                        rec.get("canonical_key"), d["display_label"], d["detected_type"]))
                    a("- chars: %d | pages: %s | extractor: %s" % (
                        d["chars"], d.get("pages"), d.get("extractor")))
                    a("- text_location: `%s`" % d.get("text_location"))
                    a("```")
                    a((d["excerpt"] or "")[:600])
                    a("```")
                    a("")
        if shown == 0:
            a("- No document yielded extractable PCAP/PPT text in this run.")
            a("")
        a("## IS REAL PCAP/PPT TEXT NOW AVAILABLE?")
        if counts["extracted"] > 0:
            a("- **YES.** %d feed_xml legal/technical attachment(s) returned real,"
              " extractable PCAP/PPT text." % counts["extracted"])
            a("- Next: p199 = PCAP/PPT Appendix extractor over the feed_xml fetch path.")
        else:
            a("- **NO.** Endpoints behaved as follows: %s." %
              json.dumps(counts["detected_types"], ensure_ascii=False))
            a("- Next: p199 = feed_xml resolver hardening (endpoint/auth/format).")
        a("")
    a("## SAFETY / NO-TOUCH STATUS")
    a("- production_write_performed=false")
    a("- bounded downloads only (<= %d urls, <= %d MB/file)" % (
        manifest["limits"]["max_urls"], manifest["limits"]["max_mb"]))
    a("- no PDF/DOCX/raw binary committed; full text only under text-dir")
    a("- data/licitaciones.json read-only; UI/runtime untouched")
    a("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build_argparser():
    p = argparse.ArgumentParser(
        prog="feedxml_attachment_probe",
        description="Targeted feed_xml attachment probe — local-only bounded (p198b).",
    )
    p.add_argument("--data", default=os.path.join("data", "licitaciones.json"))
    p.add_argument("--targeting", default=None,
                   help="optional p198 document_role_index manifest (for sample priority)")
    p.add_argument("--out", default=os.path.join(
        "_tmp", "feedxml_probe", "feedxml_probe_manifest_p198b.json"))
    p.add_argument("--report", default=os.path.join(
        "_tmp", "feedxml_probe", "report_p198b.md"))
    p.add_argument("--text-dir", default=os.path.join("_tmp", "feedxml_probe", "text"))
    p.add_argument("--cache-dir", default=os.path.join("_tmp", "feedxml_probe", "cache"))
    p.add_argument("--cache", action="store_true", default=False)
    p.add_argument("--max-records", type=int, default=8)
    p.add_argument("--max-urls", type=int, default=12)
    p.add_argument("--docs-per-record", type=int, default=2)
    p.add_argument("--max-mb", type=int, default=20)
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--sleep", type=float, default=1.0)
    p.add_argument("--excerpt-chars", type=int, default=1000)
    p.add_argument("--dry-run-select", action="store_true", default=False)
    p.add_argument("--verbose", action="store_true", default=False)
    return p


def main(argv=None):
    import time
    args = build_argparser().parse_args(argv)

    out_norm = _ensure_safe_file(args.out, "--out")
    report_norm = _ensure_safe_file(args.report, "--report")
    text_dir_norm = _ensure_safe_dir(args.text_dir, "--text-dir")

    # Load production data (read-only).
    if not os.path.isfile(args.data):
        sys.stderr.write("[feedxml-probe] --data not found: %s\n" % args.data)
        sys.exit(2)
    with open(args.data, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    records = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        sys.stderr.write("[feedxml-probe] unexpected --data shape; expected dict.data[]\n")
        sys.exit(2)

    # Optional targeting manifest -> sampled record keys for priority.
    sampled_keys = set()
    if args.targeting:
        targ = _load_json(args.targeting, "--targeting", required=False)
        if targ:
            for tr in (targ.get("records") or []):
                sampled_keys.add((tr.get("notice_id"), tr.get("canonical_key")))

    selected = select_targets(
        records, sampled_keys, args.max_records, args.max_urls, args.docs_per_record)

    if args.verbose:
        sys.stderr.write("[feedxml-probe] selected %d records / %d urls\n" % (
            len(selected), sum(len(r["documents"]) for r in selected)))

    limits = OrderedDict([
        ("max_records", args.max_records),
        ("max_urls", args.max_urls),
        ("docs_per_record", args.docs_per_record),
        ("max_mb", args.max_mb),
        ("timeout", args.timeout),
        ("sleep", args.sleep),
        ("excerpt_chars", args.excerpt_chars),
        ("cache", args.cache),
    ])

    # Build result records (probe unless dry-run).
    session = None
    result_records = []
    if not args.dry_run_select:
        session = requests.Session()
        session.headers.update({"User-Agent": _USER_AGENT})

    for i, rec in enumerate(selected):
        doc_entries = []
        for d in rec["documents"]:
            if args.dry_run_select:
                doc_entries.append(OrderedDict([
                    ("source_section", d["source_section"]),
                    ("inferred_role", d["inferred_role"]),
                    ("display_label", d["display_label"]),
                    ("url", d["url"]),
                    ("final_url", None),
                    ("endpoint_family", d["endpoint_family"]),
                    ("original_title", d.get("original_title") or ""),
                    ("mime_hint", d.get("mime_hint") or ""),
                    ("http_status", None),
                    ("header_content_type", None),
                    ("detected_type", None),
                    ("downloaded_bytes", 0),
                    ("sha256", None),
                    ("pages", None),
                    ("chars", 0),
                    ("extractor", None),
                    ("extraction_status", "selected_only"),
                    ("text_location", None),
                    ("excerpt", ""),
                    ("warnings", []),
                ]))
            else:
                entry = probe_document(d, args, session, text_dir_norm)
                doc_entries.append(entry)
                if args.verbose:
                    sys.stderr.write("[feedxml-probe]   %s %s -> %s (%s)\n" % (
                        entry["inferred_role"], entry["url"][:60],
                        entry["extraction_status"], entry.get("detected_type")))
                if args.sleep:
                    time.sleep(args.sleep)
        result_records.append(OrderedDict([
            ("notice_id", rec["notice_id"]),
            ("canonical_key", rec["canonical_key"]),
            ("titol", rec["titol"]),
            ("estat", rec["estat"]),
            ("year", rec["year"]),
            ("in_p198_sample", rec["in_p198_sample"]),
            ("documents", doc_entries),
        ]))

    counts = build_counts(selected, result_records)

    manifest = OrderedDict([
        ("schema", SCHEMA),
        ("schema_version", SCHEMA_VERSION),
        ("generated_by_prompt", GENERATED_BY_PROMPT),
        ("target_version", VERSION),
        ("production_write_performed", False),
        ("dry_run_select", bool(args.dry_run_select)),
        ("generated_at_utc", datetime.now(timezone.utc).isoformat()),
        ("input", os.path.normpath(args.data)),
        ("targeting", os.path.normpath(args.targeting) if args.targeting else None),
        ("limits", limits),
        ("counts", counts),
        ("records", result_records),
    ])

    # --- inline assertions -------------------------------------------------- #
    assert manifest["schema"] == "feedxml_probe/1", "schema mismatch"
    assert manifest["production_write_performed"] is False
    assert counts["selected_urls"] <= args.max_urls, "selected_urls exceeds cap"
    assert counts["attempted"] <= args.max_urls, "attempted exceeds cap"
    for rec in result_records:
        for d in rec["documents"]:
            assert d["source_section"] in (LEGAL_SECTION, TECH_SECTION), \
                "selected doc has unexpected source_section"
            assert d["url"].lower().startswith("http"), "non-http url selected"
            if d.get("text_location"):
                ok, _ = _is_safe_output(d["text_location"])
                assert ok, "text_location not under safe root"
                tl = os.path.normpath(d["text_location"])
                assert tl.startswith(os.path.normpath(args.text_dir)), \
                    "text_location not under --text-dir"
            if d["extraction_status"] == "extracted":
                assert d["chars"] > 0, "extracted but chars==0"
                assert d.get("text_location"), "extracted but no text_location"
    if not args.dry_run_select and counts["selected_urls"] > 0:
        assert counts["attempted"] >= 1, "selected urls but nothing attempted"
    if not args.cache:
        assert not (os.path.isdir(args.cache_dir) and os.listdir(args.cache_dir)), \
            "cache dir non-empty but --cache not passed"

    # --- write outputs ------------------------------------------------------ #
    _ensure_safe_file(args.out, "--out")
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    report = build_report(manifest, args.dry_run_select)
    _ensure_safe_file(args.report, "--report")
    with open(args.report, "w", encoding="utf-8") as fh:
        fh.write(report)

    print("[feedxml-probe] %s %s (%s)" % (
        SCHEMA, VERSION, "dry-run-select" if args.dry_run_select else "live"))
    print("[feedxml-probe] selected_records=%d selected_urls=%d attempted=%d extracted=%d"
          % (counts["selected_records"], counts["selected_urls"],
             counts["attempted"], counts["extracted"]))
    if not args.dry_run_select:
        print("[feedxml-probe] detected_types=%s" %
              json.dumps(counts["detected_types"], ensure_ascii=False))
    print("[feedxml-probe] manifest -> %s" % out_norm)
    print("[feedxml-probe] report   -> %s" % report_norm)
    print("[feedxml-probe] text-dir -> %s" % text_dir_norm)
    print("[feedxml-probe] production_write_performed=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
