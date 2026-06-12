#!/usr/bin/env python3
"""
tools/fetch_documents_f2b.py  —  F2-B resolver sidecar
Reads an F2-A manifest (schema f2a/1), selects candidates that need resolving
(gateway / empty-extension / needs_resolver), and probes each one over the
network to discover its final URL, content type, content length, content
disposition and inferred filename.

HEAD first; fall back to a bounded Range GET only when HEAD is unhelpful.
Never persists response bodies. Never writes production data. Writes a sidecar
manifest only (schema f2b/1).
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone

VERSION = "v0.5.0q"
SCHEMA = "f2b/1"

_SAFE_PREFIXES = [
    os.path.normpath("_tmp"),
    os.path.normpath(os.path.join("data", "fetcher2")),
]
_FORBIDDEN = {
    os.path.normpath(os.path.join("data", "licitaciones.json")),
    os.path.normpath("fetch_licitaciones.py"),
    os.path.normpath(os.path.join("tools", "scheduled_fetch_merge.py")),
}

# Content types / extensions we treat as a real document (merge-relevant).
_DOC_EXTENSIONS = frozenset({
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "odt", "ods", "odp", "rtf", "zip", "7z",
})
_DOC_CONTENT_TYPES = frozenset({
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
    "application/rtf",
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",  # generic binary — often a document behind a gateway
})
_HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/xml", "application/xml")

# Maps a (lowercased) content-type to a canonical inferred extension.
_CT_TO_EXT = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.oasis.opendocument.text": "odt",
    "application/vnd.oasis.opendocument.spreadsheet": "ods",
    "application/vnd.oasis.opendocument.presentation": "odp",
    "application/rtf": "rtf",
    "text/rtf": "rtf",
    "application/zip": "zip",
    "application/x-zip-compressed": "zip",
    "text/html": "html",
    "application/xhtml+xml": "html",
    "text/xml": "xml",
    "application/xml": "xml",
    "text/plain": "txt",
}

_USER_AGENT = "ADG-OPS-Fetcher2b/0.5.0q resolver-sidecar"
_CD_FILENAME_STAR = re.compile(r"filename\*\s*=\s*[^']*'[^']*'([^;]+)", re.IGNORECASE)
_CD_FILENAME = re.compile(r'filename\s*=\s*"?([^";]+)"?', re.IGNORECASE)


def _check_output_safe(path, allow_outside):
    norm = os.path.normpath(path)
    if norm in _FORBIDDEN:
        return False, f"Output path resolves to forbidden file: {norm}"
    if not allow_outside and not any(norm.startswith(p) for p in _SAFE_PREFIXES):
        return False, "Output path outside safe area; use --allow-output-outside-safe-area to override"
    return True, None


def _split_csv(values):
    """Flatten an --append list that may also carry comma-separated tokens."""
    out = []
    for v in values or []:
        out.extend(tok.strip() for tok in v.split(",") if tok.strip())
    return out


def _clean_content_type(raw):
    """Return (full_ct_lower, base_ct_lower) stripping parameters/charset."""
    if not raw:
        return "", ""
    full = raw.strip().lower()
    base = full.split(";", 1)[0].strip()
    return full, base


def _filename_from_disposition(content_disposition):
    if not content_disposition:
        return ""
    m = _CD_FILENAME_STAR.search(content_disposition)
    if m:
        val = m.group(1).strip().strip('"')
        try:
            return urllib.parse.unquote(val)
        except Exception:
            return val
    m = _CD_FILENAME.search(content_disposition)
    if m:
        return m.group(1).strip()
    return ""


def _filename_from_url(url):
    try:
        path = urllib.parse.urlparse(url).path
        base = os.path.basename(path)
        return urllib.parse.unquote(base) if base else ""
    except Exception:
        return ""


def _ext_from_filename(filename):
    if not filename:
        return ""
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    # Guard against query-ish junk being treated as an extension.
    if ext and re.fullmatch(r"[a-z0-9]{1,5}", ext):
        return ext
    return ""


def _infer_filename_and_ext(content_disposition, content_type_base, final_url):
    """Best-effort filename + extension from disposition, URL, then content-type."""
    filename = _filename_from_disposition(content_disposition)
    ext = _ext_from_filename(filename)
    if not ext:
        url_name = _filename_from_url(final_url)
        url_ext = _ext_from_filename(url_name)
        if url_ext:
            ext = url_ext
            if not filename:
                filename = url_name
    if not ext and content_type_base:
        ext = _CT_TO_EXT.get(content_type_base, "")
    if not filename and ext:
        filename = f"document.{ext}"
    return filename, ext


def _magic_kind(body):
    """Identify a document by its leading magic bytes (body is never stored)."""
    if not body:
        return None
    if body[:5] == b"%PDF-":
        return "pdf"
    if body[:4] == b"PK\x03\x04":
        return "zip"  # docx/xlsx/odt/zip family
    if body[:4] == b"\xd0\xcf\x11\xe0":
        return "ole"  # legacy doc/xls/ppt
    if body[:5].lower() == b"{\\rtf":
        return "rtf"
    return None


def _select_candidates(records, source_domains, candidate_ids, limit):
    """Pick resolver candidates, attaching the owning record for context."""
    dom_filter = set(source_domains)
    id_filter = set(candidate_ids)
    selected = []
    considered = 0
    for rec in records:
        for c in rec.get("candidates", []):
            needs = c.get("needs_resolver") is True or c.get("extension") in ("gateway", "")
            if not needs:
                continue
            considered += 1
            dom = (c.get("source_domain") or "").lower()
            if dom_filter and not any(d.lower() in dom for d in dom_filter):
                continue
            if id_filter and c.get("candidate_id") not in id_filter:
                continue
            selected.append((rec, c))
            if len(selected) >= limit:
                return selected, considered
    return selected, considered


def _open(url, method, timeout, max_range_bytes):
    """Issue a single HTTP request. Returns (resp_meta, body_or_None, error_meta)."""
    headers = {"User-Agent": _USER_AGENT, "Accept": "*/*"}
    if method == "GET":
        headers["Range"] = f"bytes=0-{max_range_bytes - 1}"
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = b""
            if method == "GET":
                body = resp.read(max_range_bytes)  # bounded; discarded after magic check
            meta = {
                "http_status": getattr(resp, "status", None) or resp.getcode(),
                "final_url": resp.geturl(),
                "content_type": resp.headers.get("Content-Type"),
                "content_length": resp.headers.get("Content-Length"),
                "content_disposition": resp.headers.get("Content-Disposition"),
            }
            return meta, body, None
    except urllib.error.HTTPError as e:
        meta = {
            "http_status": e.code,
            "final_url": e.url if getattr(e, "url", None) else url,
            "content_type": e.headers.get("Content-Type") if e.headers else None,
            "content_length": e.headers.get("Content-Length") if e.headers else None,
            "content_disposition": e.headers.get("Content-Disposition") if e.headers else None,
        }
        return meta, b"", {"error_type": "HTTPError", "error_message": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return None, None, {"error_type": type(e).__name__, "error_message": str(e)[:300]}


def _head_is_useful(meta):
    """True when a HEAD response alone is enough — avoids an unneeded GET."""
    if meta is None:
        return False
    if meta["http_status"] not in (200, 206):
        return False
    _, base = _clean_content_type(meta.get("content_type"))
    if not base:
        return False
    if base in _HTML_CONTENT_TYPES:
        # HTML may be a real gateway response hiding a PDF — a Range GET can confirm.
        return False
    if base == "application/octet-stream" and not meta.get("content_disposition"):
        # Ambiguous binary; a Range GET magic-byte check is worth it.
        return False
    return True


def _resolve_one(candidate, timeout, max_range_bytes):
    """Resolve a single candidate. Returns the resolved-candidate dict."""
    url = candidate.get("url") or candidate.get("normalized_url") or ""

    resolved = {
        "candidate_id": candidate.get("candidate_id"),
        "canonical_key": candidate.get("canonical_key"),
        "original_url": url,
        "normalized_url": candidate.get("normalized_url"),
        "source_domain": candidate.get("source_domain"),
        "source_adapter": candidate.get("source_adapter"),
        "original_title": candidate.get("title"),
        "normalized_title": candidate.get("normalized_title"),
        "original_kind": candidate.get("kind"),
        "original_confidence": candidate.get("confidence"),
        "original_extension": candidate.get("extension"),
        "needs_resolver_input": candidate.get("needs_resolver"),
        "resolver_status": "unresolved",
        "resolver_method": "SKIPPED",
        "http_status": None,
        "final_url": None,
        "final_domain": None,
        "content_type": None,
        "content_length": None,
        "content_disposition": None,
        "inferred_filename": None,
        "inferred_extension": None,
        "resolved_is_pdf": False,
        "resolved_is_document": False,
        "resolver_error_type": None,
        "resolver_error_message": None,
        "merge_ready_candidate": False,
        "merge_blockers": [],
    }

    if not url or not url.lower().startswith(("http://", "https://")):
        resolved["resolver_status"] = "skipped"
        resolved["resolver_method"] = "SKIPPED"
        resolved["resolver_error_type"] = "InvalidURL"
        resolved["resolver_error_message"] = "Missing or non-HTTP URL"
        resolved["merge_blockers"] = ["invalid_url"]
        return resolved

    # HEAD first.
    meta, _, err = _open(url, "HEAD", timeout, max_range_bytes)
    method = "HEAD"
    magic = None

    if err and err["error_type"] != "HTTPError":
        # HEAD failed at the transport level — try a Range GET before giving up.
        meta2, body2, err2 = _open(url, "GET", timeout, max_range_bytes)
        if err2 and meta2 is None:
            resolved["resolver_status"] = "error"
            resolved["resolver_method"] = "ERROR"
            resolved["resolver_error_type"] = err2["error_type"]
            resolved["resolver_error_message"] = err2["error_message"]
            resolved["merge_blockers"] = ["resolver_error"]
            return resolved
        meta, method = meta2, "RANGE_GET"
        magic = _magic_kind(body2)
        if err2:
            resolved["resolver_error_type"] = err2["error_type"]
            resolved["resolver_error_message"] = err2["error_message"]
    elif not _head_is_useful(meta):
        # HEAD reached the server but is unhelpful — confirm with a bounded GET.
        meta2, body2, err2 = _open(url, "GET", timeout, max_range_bytes)
        if meta2 is not None:
            meta, method = meta2, "RANGE_GET"
            magic = _magic_kind(body2)
            if err2:
                resolved["resolver_error_type"] = err2["error_type"]
                resolved["resolver_error_message"] = err2["error_message"]
        elif err:
            # Keep the original HEAD HTTPError context.
            resolved["resolver_error_type"] = err["error_type"]
            resolved["resolver_error_message"] = err["error_message"]
    elif err:
        resolved["resolver_error_type"] = err["error_type"]
        resolved["resolver_error_message"] = err["error_message"]

    if meta is None:
        resolved["resolver_status"] = "error"
        resolved["resolver_method"] = "ERROR"
        resolved["merge_blockers"] = ["resolver_error"]
        return resolved

    resolved["resolver_method"] = method
    resolved["http_status"] = meta["http_status"]
    resolved["final_url"] = meta["final_url"]
    resolved["final_domain"] = (
        urllib.parse.urlparse(meta["final_url"]).netloc.lower() if meta["final_url"] else None
    )
    resolved["content_type"] = meta["content_type"]
    resolved["content_disposition"] = meta["content_disposition"]
    try:
        resolved["content_length"] = (
            int(meta["content_length"]) if meta["content_length"] is not None else None
        )
    except (TypeError, ValueError):
        resolved["content_length"] = None

    full_ct, base_ct = _clean_content_type(meta["content_type"])
    filename, ext = _infer_filename_and_ext(meta["content_disposition"], base_ct, meta["final_url"])

    # Magic bytes (when a GET ran) override ambiguous/missing content-type signals.
    if magic == "pdf":
        ext = ext or "pdf"
        base_ct = base_ct or "application/pdf"
    elif magic == "zip" and not ext:
        ext = "zip"
    elif magic == "ole" and not ext:
        ext = "doc"
    elif magic == "rtf" and not ext:
        ext = "rtf"

    resolved["inferred_filename"] = filename or None
    resolved["inferred_extension"] = ext or None

    is_html = base_ct in _HTML_CONTENT_TYPES
    resolved_is_pdf = (
        base_ct == "application/pdf" or ext == "pdf" or magic == "pdf"
    )
    resolved_is_document = bool(
        resolved_is_pdf
        or (ext in _DOC_EXTENSIONS)
        or (base_ct in _DOC_CONTENT_TYPES and base_ct != "application/octet-stream")
        or (base_ct == "application/octet-stream" and (ext in _DOC_EXTENSIONS or magic in ("pdf", "zip", "ole", "rtf")))
    ) and not is_html

    resolved["resolved_is_pdf"] = bool(resolved_is_pdf)
    resolved["resolved_is_document"] = bool(resolved_is_document)

    if meta["http_status"] in (200, 206):
        resolved["resolver_status"] = "resolved"
    else:
        resolved["resolver_status"] = "unresolved"

    # Conservative merge-readiness flag (NEVER an actual merge).
    blockers = []
    if resolved["resolver_status"] != "resolved":
        blockers.append("not_resolved")
    if not resolved_is_document:
        blockers.append("not_document")
    if is_html:
        blockers.append("html_page")
    if not resolved["final_url"]:
        blockers.append("no_final_url")
    if not resolved["candidate_id"]:
        blockers.append("no_candidate_id")
    if not resolved["canonical_key"]:
        blockers.append("no_canonical_key")
    resolved["merge_blockers"] = blockers
    resolved["merge_ready_candidate"] = (len(blockers) == 0)
    return resolved


def _ratio(num, den):
    return round(num / den, 6) if den else 0.0


def _build_quality_summary(resolved_list, considered):
    attempted = len(resolved_list)
    resolved_count = sum(1 for r in resolved_list if r["resolver_status"] == "resolved")
    unresolved_count = sum(1 for r in resolved_list if r["resolver_status"] == "unresolved")
    error_count = sum(1 for r in resolved_list if r["resolver_status"] in ("error", "skipped"))
    pdf_count = sum(1 for r in resolved_list if r["resolved_is_pdf"])
    doc_count = sum(1 for r in resolved_list if r["resolved_is_document"])
    merge_ready = sum(1 for r in resolved_list if r["merge_ready_candidate"])

    per_domain = Counter(r.get("source_domain") or "" for r in resolved_list)
    per_domain_resolved = Counter(
        r.get("source_domain") or "" for r in resolved_list if r["resolver_status"] == "resolved"
    )
    ct_counts = Counter(
        _clean_content_type(r.get("content_type"))[1] or "" for r in resolved_list
    )
    ext_counts = Counter(r.get("inferred_extension") or "" for r in resolved_list)
    method_counts = Counter(r.get("resolver_method") or "" for r in resolved_list)
    status_counts = Counter(r.get("resolver_status") or "" for r in resolved_list)
    filenames = Counter(r["inferred_filename"] for r in resolved_list if r.get("inferred_filename"))
    error_types = Counter(
        r["resolver_error_type"] for r in resolved_list if r.get("resolver_error_type")
    )

    return {
        "candidates_considered": considered,
        "candidates_attempted": attempted,
        "resolved_count": resolved_count,
        "unresolved_count": unresolved_count,
        "error_count": error_count,
        "resolver_error_rate": _ratio(error_count, attempted),
        "resolved_ratio": _ratio(resolved_count, attempted),
        "resolved_pdf_count": pdf_count,
        "resolved_pdf_ratio": _ratio(pdf_count, attempted),
        "resolved_document_count": doc_count,
        "resolved_document_ratio": _ratio(doc_count, attempted),
        "merge_ready_candidate_count": merge_ready,
        "merge_ready_candidate_ratio": _ratio(merge_ready, attempted),
        "per_domain_counts": dict(per_domain),
        "per_domain_resolved_counts": dict(per_domain_resolved),
        "content_type_counts": dict(ct_counts),
        "inferred_extension_counts": dict(ext_counts),
        "resolver_method_counts": dict(method_counts),
        "resolver_status_counts": dict(status_counts),
        "top_filenames": filenames.most_common(15),
        "top_error_types": error_types.most_common(10),
    }


def parse_args():
    ap = argparse.ArgumentParser(
        description="F2-B resolver sidecar — resolves gateway/empty candidates (ADG OPS v0.5.0q)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--input", required=True, help="F2-A manifest (schema f2a/1) path.")
    ap.add_argument("--output", required=True, help="Resolver manifest output path (_tmp/ or data/fetcher2/).")
    ap.add_argument("--limit", type=int, default=50, help="Max candidates to resolve after filtering.")
    ap.add_argument("--source-domain", action="append", dest="source_domains", default=[],
                    metavar="DOMAIN", help="Restrict to candidates whose source_domain contains DOMAIN (repeatable / comma-separated).")
    ap.add_argument("--candidate-id", action="append", dest="candidate_ids", default=[],
                    metavar="ID", help="Restrict to specific candidate_id values (repeatable / comma-separated).")
    ap.add_argument("--timeout", type=float, default=20.0, help="HTTP request timeout (seconds).")
    ap.add_argument("--sleep", type=float, default=0.25, help="Sleep between candidates (seconds).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Label output DRY_RUN. No production write occurs either way (default-safe).")
    ap.add_argument("--max-range-bytes", type=int, default=4096,
                    help="Max bytes read on a fallback Range GET (body never stored).")
    ap.add_argument("--allow-output-outside-safe-area", action="store_true",
                    help="Bypass safe-area restriction on output path.")
    return ap.parse_args()


def main():
    args = parse_args()

    ok, msg = _check_output_safe(args.output, args.allow_output_outside_safe_area)
    if not ok:
        print(f"[F2-B BLOCKED] {msg}", file=sys.stderr)
        return 1

    source_domains = _split_csv(args.source_domains)
    candidate_ids = _split_csv(args.candidate_ids)

    try:
        with open(args.input, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[F2-B BLOCKED] Cannot read input manifest: {e}", file=sys.stderr)
        return 1

    src_schema = manifest.get("schema", "")
    if not src_schema.startswith("f2a/"):
        print(f"[F2-B BLOCKED] Unexpected input schema '{src_schema}'. Expected f2a/1.", file=sys.stderr)
        return 1

    records = manifest.get("records", [])
    if not isinstance(records, list):
        print("[F2-B BLOCKED] Manifest 'records' is not a list.", file=sys.stderr)
        return 1

    selected, considered = _select_candidates(records, source_domains, candidate_ids, args.limit)
    mode = "F2-B_RESOLVER_DRY_RUN" if args.dry_run else "F2-B_RESOLVER"

    print(f"[F2-B] {mode} | considered={considered} selected={len(selected)} "
          f"limit={args.limit} domains={source_domains or '*'}")

    resolved_list = []
    warnings = []
    for i, (_rec, cand) in enumerate(selected):
        short = (cand.get("source_domain") or "")[:40]
        print(f"  [{i+1}/{len(selected)}] {short} {str(cand.get('candidate_id'))[:16]}", end=" ", flush=True)
        r = _resolve_one(cand, args.timeout, args.max_range_bytes)
        resolved_list.append(r)
        print(f"-> {r['resolver_method']} status={r['http_status']} "
              f"{r['resolver_status']} doc={r['resolved_is_document']} "
              f"ct={_clean_content_type(r.get('content_type'))[1] or '-'}")
        if i < len(selected) - 1:
            time.sleep(args.sleep)

    quality_summary = _build_quality_summary(resolved_list, considered)

    out = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
        "mode": mode,
        "input": args.input,
        "source_f2a_schema": src_schema,
        "source_f2a_version": manifest.get("version"),
        "filter_params": {
            "limit": args.limit,
            "source_domains": source_domains,
            "candidate_ids": candidate_ids,
            "timeout": args.timeout,
            "sleep": args.sleep,
            "max_range_bytes": args.max_range_bytes,
            "dry_run": args.dry_run,
        },
        "counts": {
            "candidates_considered": considered,
            "candidates_attempted": len(resolved_list),
            "resolved_count": quality_summary["resolved_count"],
            "unresolved_count": quality_summary["unresolved_count"],
            "error_count": quality_summary["error_count"],
            "merge_ready_candidate_count": quality_summary["merge_ready_candidate_count"],
        },
        "resolved_candidates": resolved_list,
        "quality_summary": quality_summary,
        "warnings": warnings,
    }

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    qs = quality_summary
    print(f"\n[F2-B] done: attempted={qs['candidates_attempted']} "
          f"resolved={qs['resolved_count']} unresolved={qs['unresolved_count']} "
          f"errors={qs['error_count']} docs={qs['resolved_document_count']} "
          f"pdf={qs['resolved_pdf_count']} merge_ready={qs['merge_ready_candidate_count']}")
    print(f"[F2-B] content_types: {qs['content_type_counts']}")
    print(f"[F2-B] methods: {qs['resolver_method_counts']}")
    print(f"[F2-B] manifest -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
