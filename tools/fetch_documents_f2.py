#!/usr/bin/env python3
"""
tools/fetch_documents_f2.py  —  F2-A document-link / pliego discovery
Reads licitaciones.json, requests detail page HTML, extracts candidate
document/pliego/anexo links. Writes sidecar manifest only.
Never mutates data/licitaciones.json. Never downloads binary files.
"""

import argparse
import hashlib
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
from html.parser import HTMLParser

VERSION = "v0.5.0n"

_SAFE_PREFIXES = [
    os.path.normpath("_tmp"),
    os.path.normpath(os.path.join("data", "fetcher2")),
]
_FORBIDDEN = {
    os.path.normpath(os.path.join("data", "licitaciones.json")),
    os.path.normpath("fetch_licitaciones.py"),
    os.path.normpath(os.path.join("tools", "scheduled_fetch_merge.py")),
}

_DOC_KEYWORDS = (
    "pliego", "plec", "prescripciones", "prescripcions",
    "cláusulas", "clausulas", "clausules",
    "pcap", "ppt", "documento", "document", "expediente",
    "anexo", "annex", "anexos", "annexos",
    "adjudica", "formalizaci",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip",
    "getdocumentbyidservlet", "docacccmpnt", "descargar", "download",
)

# Most-specific multi-word patterns checked before single-word fallbacks.
# First matching rule wins.
_KIND_RULES = (
    (("pliego de prescripciones", "prescripciones tecnicas", "pliego tecnico",
      "plec de prescripcions", "plec prescripcions tecniques"), "pliego_tecnico"),
    (("pliego de clausulas", "clausulas administrativas", "pliego administrativo",
      "plec de clausules administratives", "plec clausules administratives",
      "pcap"), "pliego_admin"),
    (("prescripciones", "prescripcions", "ppt"), "pliego_tecnico"),
    (("clausulas", "clausules", "cláusulas", "pca"), "pliego_admin"),
    (("pliego", "plec"), "pliego_admin"),
    (("anexo", "annex", "anexos", "annexos"), "annex"),
    (("adjudicaci", "adjudicatario", "formalizaci", "acta adjudica"), "award_doc"),
    (("getdocumentbyidservlet", "docacccmpnt"), "generic_doc"),
    (("documento", "document", "descargar", "download", "expediente",
      ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip"), "generic_doc"),
)

_HIGH_KW = frozenset({
    "pcap", "ppt", "pliego", "plec", "prescripciones", "prescripcions",
    "clausulas", "clausules", "cláusulas", "anexo", "annex",
    "adjudicaci", "formalizaci",
})
_GATEWAY_PATTERNS = frozenset({"getdocumentbyidservlet", "docacccmpnt"})

# Tokens that must match at word boundaries only (short acronyms, false-positive prone).
_WB_TOKENS = frozenset({"pca", "pcap", "ppt", "pptx"})
_WB_PATTERNS = {tok: re.compile(r"\b" + re.escape(tok) + r"\b") for tok in _WB_TOKENS}

_KIND_RANK = {
    "pliego_admin": 5, "pliego_tecnico": 5, "award_doc": 4,
    "annex": 3, "generic_doc": 2, "unknown": 1,
}
_CONF_RANK = {"high": 3, "medium": 2, "low": 1}

# Titles filtered by default (all lowercase; compared against normalized title)
_VER_EXACT = "ver"
_DEFERRED_MODULES_SUB = "deferred modules"
_GENERIC_HTML_XML_EXACT = frozenset({"documento html", "documento xml"})
# Navigation/UI labels that must never survive as kept candidates.
_GENERIC_NAV_EXACT = frozenset({
    # Original set
    "cerrar", "imprimir", "volver", "siguiente", "anterior",
    "inicio", "atrás", "atras", "tancar", "tornar",
    # Expanded: observed portal navigation/noise labels
    "bienvenidos", "ongi etorri", "benvinguts", "benvidos",
    "welcome", "bienvenue", "home", "search",
    "contractor profile", "companies",
    "información legal", "informacion legal",
    "suscribir alertas anuncio",
    "acuerdos sobre contratación c.a.e.",
    "acuerdos sobre contratacion c.a.e.",
    "plazo cerrado",
    "abierto / plazo de presentación",
    "abierto / plazo de presentacion",
    "descargar",
    "descargar todos los archivos",
    "búsqueda de poderes adjudicadores",
    "busqueda de poderes adjudicadores",
    "acceso poderes adjudicadores",
})


def _normalize_title(title):
    """Lowercase, strip, collapse internal whitespace."""
    return " ".join((title or "").lower().split())


def _make_candidate_id(rec_canonical_key, normalized_url):
    raw = rec_canonical_key + "|" + normalized_url
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


class _LinkExtractor(HTMLParser):
    """
    Extract <a> links with rich context:
    - link text (including img alt/title inside the link)
    - <a> title / aria-label attributes
    - parent <td>/<th> cell text as fallback context
    """

    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._link_attrs = {}
        self._link_buf = []
        self._cell_buf = []
        self._cell_depth = 0
        self._link_depth = 0

    def handle_starttag(self, tag, attrs):
        attr_d = dict(attrs)
        if tag in ("td", "th"):
            self._cell_depth += 1
            if self._cell_depth == 1:
                self._cell_buf = []
        elif tag == "a":
            if self._link_depth == 0:
                self._href = attr_d.get("href") or ""
                self._link_attrs = attr_d
                self._link_buf = []
            self._link_depth += 1
        elif tag == "img":
            alt   = attr_d.get("alt", "").strip()
            title = attr_d.get("title", "").strip()
            for val in filter(None, (alt, title)):
                if self._link_depth > 0:
                    self._link_buf.append(val)
                if self._cell_depth > 0:
                    self._cell_buf.append(val)

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            if self._cell_depth > 0:
                self._cell_depth -= 1
            if self._cell_depth == 0:
                self._cell_buf = []
        elif tag == "a":
            if self._link_depth > 0:
                self._link_depth -= 1
            if self._link_depth == 0 and self._href is not None:
                link_text = " ".join(self._link_buf).strip()
                a_title   = self._link_attrs.get("title", "").strip()
                a_aria    = self._link_attrs.get("aria-label", "").strip()
                cell_text = " ".join(self._cell_buf).strip()

                best_title = link_text or a_title or a_aria or ""
                if a_title and a_title != link_text:
                    context = a_title
                elif a_aria and a_aria != link_text:
                    context = a_aria
                elif cell_text:
                    context = cell_text
                else:
                    context = ""

                if link_text:
                    strategy = "link_text"
                elif a_title:
                    strategy = "a_title_attr"
                elif a_aria:
                    strategy = "a_aria_label"
                elif cell_text:
                    strategy = "parent_cell"
                else:
                    strategy = "none"

                self.links.append({
                    "href":                 self._href,
                    "link_text":            link_text[:300],
                    "context_text":         context[:300],
                    "source_text_strategy": strategy,
                    "title":                best_title[:200],
                })
                self._href = None

    def handle_data(self, data):
        s = data.strip()
        if not s:
            return
        if self._link_depth > 0:
            self._link_buf.append(s)
        if self._cell_depth > 0:
            self._cell_buf.append(s)


def _is_candidate(href_l, combined_l):
    return any(kw in href_l or kw in combined_l for kw in _DOC_KEYWORDS)


def _tok_match(kw, text):
    """Match kw in text; word-boundary regex for short acronyms, substring otherwise."""
    pat = _WB_PATTERNS.get(kw)
    if pat is not None:
        return bool(pat.search(text))
    return kw in text


def _infer_kind(href_l, combined_l):
    for kws, kind in _KIND_RULES:
        matched = [kw for kw in kws if _tok_match(kw, combined_l) or _tok_match(kw, href_l)]
        if matched:
            return kind, matched[:5]
    return "unknown", []


def _infer_confidence(href_l, combined_l):
    has_strong = any(_tok_match(kw, combined_l) for kw in _HIGH_KW)
    has_ext    = any(ext in href_l for ext in (".pdf", ".docx", ".doc"))
    has_text   = bool(combined_l.strip())
    if has_strong or (has_ext and has_text):
        return "high"
    if has_text:
        return "medium"
    return "low"


def _infer_ext(url):
    path = urllib.parse.urlparse(url).path.lower()
    for ext in (".pdf", ".docx", ".doc", ".xlsx", ".xls", ".zip", ".odt", ".ods"):
        if path.endswith(ext):
            return ext.lstrip(".")
    url_l = url.lower()
    if any(p in url_l for p in _GATEWAY_PATTERNS):
        return "gateway"
    return ""


def _normalize_url(url):
    try:
        p = urllib.parse.urlparse(url)
        return urllib.parse.urlunparse((
            p.scheme.lower(), p.netloc.lower(), p.path, p.params, p.query, ""
        ))
    except Exception:
        return url.lower()


def _dedupe_candidates(candidates):
    seen = {}
    for c in candidates:
        key = _normalize_url(c["url"])
        if key not in seen:
            seen[key] = c
        else:
            ex = seen[key]
            ex_score = (
                bool((ex.get("title") or "").strip()),
                _CONF_RANK.get(ex.get("confidence", "low"), 0),
                _KIND_RANK.get(ex.get("kind", "unknown"), 0),
            )
            new_score = (
                bool((c.get("title") or "").strip()),
                _CONF_RANK.get(c.get("confidence", "low"), 0),
                _KIND_RANK.get(c.get("kind", "unknown"), 0),
            )
            if new_score > ex_score:
                seen[key] = c
    deduped = list(seen.values())
    return deduped, len(candidates) - len(deduped)


def _extract_doc_family_key(url):
    """Return (netloc, doc_id_token) for grouping sibling document format variants."""
    try:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
        for key in ("docId", "docid", "id", "iddocument", "nodeId", "nodeid",
                    "idDocument", "documentId", "fileId", "fileid"):
            if key in params and params[key]:
                return (parsed.netloc.lower(), key.lower() + "=" + params[key][0])
        path_no_ext = os.path.splitext(parsed.path)[0]
        if path_no_ext and path_no_ext not in ("/", ""):
            return (parsed.netloc.lower(), path_no_ext.lower())
    except Exception:
        pass
    return None


def _filter_candidates(candidates, min_conf_rank, keep_ver, include_html_xml,
                       skip_generic_titles, prefer_pdf):
    """Apply quality filters. Returns (kept_list, skipped_counts dict)."""
    skipped = Counter()
    first_pass = []

    for c in candidates:
        title_l = _normalize_title(c.get("title") or "")
        conf = c.get("confidence", "low")

        # Confidence floor
        if _CONF_RANK.get(conf, 0) < min_conf_rank:
            skipped["skip_below_min_confidence"] += 1
            continue

        # Title exactly "Ver" (navigation link, not a document)
        if not keep_ver and title_l == _VER_EXACT:
            skipped["skip_ver_title"] += 1
            continue

        # Title contains "Deferred Modules" (JS framework artefact)
        if _DEFERRED_MODULES_SUB in title_l:
            skipped["skip_deferred_modules"] += 1
            continue

        # Generic html/xml document placeholders
        if not include_html_xml and title_l in _GENERIC_HTML_XML_EXACT:
            skipped["skip_generic_html_xml"] += 1
            continue

        # Navigation/UI labels — blocked at all confidence levels
        if skip_generic_titles and title_l in _GENERIC_NAV_EXACT:
            skipped["skip_generic_nav"] += 1
            continue

        first_pass.append(c)

    if not prefer_pdf:
        return first_pass, dict(skipped)

    # PDF preference: within a doc family, drop html/xml siblings when a PDF sibling exists
    families = {}
    ungrouped = []
    for c in first_pass:
        key = _extract_doc_family_key(c["url"])
        if key:
            families.setdefault(key, []).append(c)
        else:
            ungrouped.append(c)

    kept = list(ungrouped)
    for group in families.values():
        if len(group) == 1:
            kept.extend(group)
            continue
        has_pdf_member = any(
            c.get("extension") == "pdf" or "pdf" in (c.get("title") or "").lower()
            for c in group
        )
        if not has_pdf_member:
            kept.extend(group)
            continue
        for c in group:
            title_l_g = (c.get("title") or "").lower()
            ext = c.get("extension") or ""
            is_html_xml_variant = (
                ext in ("", "gateway")
                and ("html" in title_l_g or "xml" in title_l_g)
                and "pdf" not in title_l_g
            )
            if is_html_xml_variant:
                skipped["skip_pdf_preferred"] += 1
            else:
                kept.append(c)

    return kept, dict(skipped)


def _check_output_safe(path, allow_outside):
    norm = os.path.normpath(path)
    if norm in _FORBIDDEN:
        return False, f"Output path resolves to forbidden file: {norm}"
    if not allow_outside and not any(norm.startswith(p) for p in _SAFE_PREFIXES):
        return False, "Output path outside safe area; use --allow-output-outside-safe-area to override"
    return True, None


def _fetch_html(url, timeout, user_agent, max_bytes):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.status
            chunks = []
            total = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total >= max_bytes:
                    break
        return code, b"".join(chunks).decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as e:
        return e.code, None, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"


def _select_records(data, active_only, limit, source_domains):
    def passes(r):
        if not r.get("url"):
            return False
        if active_only and r.get("active_opportunity_eligible") is not True:
            return False
        if source_domains and not any(d in r.get("url", "") for d in source_domains):
            return False
        return True

    eligible = [r for r in data if passes(r)]
    has_docs = [r for r in eligible if r.get("documents")]
    no_docs  = [r for r in eligible if not r.get("documents")]
    return (has_docs + no_docs)[:limit]


def main():
    ap = argparse.ArgumentParser(
        description="F2-A document-link / pliego discovery sidecar — ADG OPS v0.5.0n"
    )
    ap.add_argument("--input", default=os.path.join("data", "licitaciones.json"),
                    help="Path to licitaciones.json")
    ap.add_argument("--output", required=True,
                    help="Sidecar manifest output path (must be inside _tmp/ or data/fetcher2/)")
    ap.add_argument("--limit", type=int, default=10,
                    help="Max records to process")
    ap.add_argument("--active-only", action="store_true",
                    help="Only process active_opportunity_eligible=True records")
    ap.add_argument("--timeout", type=float, default=12.0,
                    help="HTTP request timeout in seconds")
    ap.add_argument("--sleep", type=float, default=1.0,
                    help="Sleep between requests in seconds")
    ap.add_argument("--dry-run", action="store_true",
                    help="Label output as DRY_RUN; no production mutation (default safe behavior)")
    ap.add_argument("--source-domain", action="append", dest="source_domains", default=[],
                    metavar="DOMAIN", help="Restrict to records whose url contains DOMAIN")
    ap.add_argument("--max-html-bytes", type=int, default=2_000_000,
                    help="Max bytes to read per HTML response")
    ap.add_argument("--user-agent",
                    default="ADG-OPS-Fetcher2/0.5.0n document-link-discovery",
                    help="HTTP User-Agent header")
    ap.add_argument("--allow-output-outside-safe-area", action="store_true",
                    help="Bypass safe-area restriction on output path")
    # Quality hardening flags (v0.5.0m+)
    ap.add_argument("--min-confidence", choices=["high", "medium", "low"], default="medium",
                    help="Minimum confidence level to keep a candidate (default: medium)")
    ap.add_argument("--prefer-pdf", action=argparse.BooleanOptionalAction, default=True,
                    help="Within a doc family, prefer PDF over html/xml siblings (default: on)")
    ap.add_argument("--skip-generic-titles", action=argparse.BooleanOptionalAction, default=True,
                    help="Drop candidates with known generic UI/navigation titles (default: on)")
    ap.add_argument("--max-candidates-per-record", type=int, default=10,
                    help="Cap candidates per record after filtering (default: 10)")
    ap.add_argument("--include-html-xml", action="store_true", default=False,
                    help="Keep generic 'Documento html'/'Documento xml' candidates (default: off)")
    ap.add_argument("--keep-ver-links", action="store_true", default=False,
                    help="Keep candidates with title exactly 'Ver' (default: off)")
    args = ap.parse_args()

    ok, msg = _check_output_safe(args.output, args.allow_output_outside_safe_area)
    if not ok:
        print(f"[F2-A BLOCKED] {msg}", file=sys.stderr)
        sys.exit(1)

    min_conf_rank = _CONF_RANK.get(args.min_confidence, 2)

    with open(args.input, encoding="utf-8") as f:
        raw = json.load(f)
    data = raw.get("data", raw) if isinstance(raw, dict) else raw
    data = [r for r in data if isinstance(r, dict)]

    sample = _select_records(data, args.active_only, args.limit, args.source_domains)
    mode   = "F2-A_DETAIL_LINK_DISCOVERY_DRY_RUN" if args.dry_run else "F2-A_DETAIL_LINK_DISCOVERY"

    manifest = {
        "schema": "f2a/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
        "mode": mode,
        "input": args.input,
        "limit": args.limit,
        "active_only": args.active_only,
        "filter_params": {
            "min_confidence": args.min_confidence,
            "prefer_pdf": args.prefer_pdf,
            "skip_generic_titles": args.skip_generic_titles,
            "max_candidates_per_record": args.max_candidates_per_record,
            "include_html_xml": args.include_html_xml,
            "keep_ver_links": args.keep_ver_links,
        },
        "counts": {
            "records_seen": len(data),
            "records_attempted": 0,
            "records_with_candidates": 0,
            "candidates_before_filter": 0,
            "candidate_links_total": 0,
            "duplicates_removed": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            "non_empty_titles": 0,
            "errors": 0,
        },
        "records": [],
    }

    total_skipped: Counter = Counter()
    capped_records_count = 0

    print(f"[F2-A] {mode} | limit={args.limit} active_only={args.active_only} "
          f"sample={len(sample)}")
    print(f"[F2-A] filters: min_conf={args.min_confidence} prefer_pdf={args.prefer_pdf} "
          f"skip_generic_titles={args.skip_generic_titles} "
          f"max_per_rec={args.max_candidates_per_record} "
          f"include_html_xml={args.include_html_xml} keep_ver={args.keep_ver_links}")

    for i, rec in enumerate(sample):
        url = rec.get("url", "")
        entry = {
            "id": rec.get("id", ""),
            "canonical_key": rec.get("canonical_key", ""),
            "title": rec.get("titol") or rec.get("titulo", ""),
            "url": url,
            "organisme": rec.get("organisme", ""),
            "data_pub": rec.get("data_pub", ""),
            "data_limit": rec.get("data_limit", ""),
            "existing_documents_count": len(rec.get("documents") or []),
            "fetch_status": "skipped",
            "http_status": None,
            "error": None,
            "candidates": [],
        }

        manifest["counts"]["records_attempted"] += 1
        short = (url[:67] + "...") if len(url) > 70 else url
        print(f"  [{i+1}/{len(sample)}] {short}", end=" ", flush=True)

        code, html, err = _fetch_html(url, args.timeout, args.user_agent, args.max_html_bytes)

        if err or html is None:
            entry["fetch_status"] = "error"
            entry["error"]        = err or "no content"
            entry["http_status"]  = code
            manifest["counts"]["errors"] += 1
            print(f"ERROR ({entry['error'][:60]})")
        else:
            entry["fetch_status"] = "ok"
            entry["http_status"]  = code

            extractor = _LinkExtractor()
            try:
                extractor.feed(html)
            except Exception as ex:
                entry["error"] = f"parse error: {ex}"

            raw_candidates = []
            for link in extractor.links:
                href = link["href"]
                if not href or href.startswith(("javascript:", "mailto:", "#")):
                    continue
                try:
                    full_url = urllib.parse.urljoin(url, href)
                except Exception:
                    continue

                href_l   = href.lower()
                title    = link["title"]
                context  = link["context_text"]
                combined = (title + " " + context + " " + link["link_text"]).lower()

                if not _is_candidate(href_l, combined):
                    continue

                kind, signals = _infer_kind(href_l, combined)
                conf          = _infer_confidence(href_l, combined)

                raw_candidates.append({
                    "title":                title[:200],
                    "link_text":            link["link_text"][:200],
                    "context_text":         context[:200],
                    "source_text_strategy": link["source_text_strategy"],
                    "url":                  full_url[:500],
                    "kind":                 kind,
                    "raw_kind_signals":     signals,
                    "extension":            _infer_ext(full_url),
                    "source_domain":        urllib.parse.urlparse(full_url).netloc,
                    "confidence":           conf,
                    "provenance":           "fetcher2_detail_html",
                    "discovery_method":     "detail_html_link_scan",
                    "no_binary_download":   True,
                })

            candidates, dups = _dedupe_candidates(raw_candidates)
            manifest["counts"]["duplicates_removed"] += dups
            n_before_filter = len(candidates)
            manifest["counts"]["candidates_before_filter"] += n_before_filter

            candidates, rec_skipped = _filter_candidates(
                candidates,
                min_conf_rank=min_conf_rank,
                keep_ver=args.keep_ver_links,
                include_html_xml=args.include_html_xml,
                skip_generic_titles=args.skip_generic_titles,
                prefer_pdf=args.prefer_pdf,
            )
            total_skipped.update(rec_skipped)

            n_capped = 0
            if len(candidates) > args.max_candidates_per_record:
                candidates.sort(key=lambda c: (
                    _CONF_RANK.get(c.get("confidence", "low"), 0),
                    _KIND_RANK.get(c.get("kind", "unknown"), 0),
                ), reverse=True)
                n_capped = len(candidates) - args.max_candidates_per_record
                candidates = candidates[:args.max_candidates_per_record]
                total_skipped["skip_max_per_record"] += n_capped
                capped_records_count += 1

            # Candidate model v2: inject stable fields on every kept candidate.
            rec_key = (
                rec.get("canonical_key")
                or rec.get("id")
                or rec.get("idExpediente")
                or rec.get("expediente")
                or ""
            )
            for c in candidates:
                norm_url   = _normalize_url(c["url"])
                norm_title = _normalize_title(c.get("title") or "")
                c["candidate_id"]    = _make_candidate_id(rec_key, norm_url)
                c["canonical_key"]   = rec_key
                c["normalized_url"]  = norm_url
                c["normalized_title"] = norm_title
                c["source_domain"]   = urllib.parse.urlparse(c["url"]).netloc.lower()
                c["source_adapter"]  = "generic_html"
                c["needs_resolver"]  = c.get("extension", "") in ("gateway", "")
                c["merge_ready"]     = False

            for c in candidates:
                manifest["counts"][f"{c['confidence']}_confidence"] += 1
                if (c.get("title") or "").strip():
                    manifest["counts"]["non_empty_titles"] += 1

            entry["candidates"] = candidates
            if candidates:
                manifest["counts"]["records_with_candidates"] += 1
                manifest["counts"]["candidate_links_total"]   += len(candidates)

            n_skipped = sum(rec_skipped.values()) + n_capped
            print(f"HTTP {code} raw={len(raw_candidates)} deduped={n_before_filter} "
                  f"kept={len(candidates)} skipped={n_skipped} dups_removed={dups}")

        manifest["records"].append(entry)
        if i < len(sample) - 1:
            time.sleep(args.sleep)

    # Build quality_summary from all final candidates
    all_final = [c for r in manifest["records"] for c in r.get("candidates", [])]
    title_counter = Counter((c.get("title") or "").strip() for c in all_final)
    conf_counter  = Counter(c.get("confidence", "low") for c in all_final)
    kind_counter  = Counter(c.get("kind", "unknown") for c in all_final)
    ext_counter   = Counter(c.get("extension", "") for c in all_final)
    domain_counter = Counter(c.get("source_domain", "") for c in all_final)
    _KNOWN_GENERIC_LC = frozenset({
        "ver", "documento html", "documento xml", "documento pdf",
        "deferred modules",
    })
    generic_title_count = sum(
        1 for c in all_final
        if (c.get("title") or "").strip().lower() in _KNOWN_GENERIC_LC
    )
    nav_title_count = sum(
        1 for c in all_final
        if _normalize_title(c.get("title") or "") in _GENERIC_NAV_EXACT
    )

    cnt = manifest["counts"]
    candidates_after = cnt["candidate_links_total"]
    records_attempted = cnt["records_attempted"]
    error_count = cnt["errors"]

    manifest["quality_summary"] = {
        "records_attempted":              records_attempted,
        "records_with_candidates":        cnt["records_with_candidates"],
        "candidates_before_filter":       cnt["candidates_before_filter"],
        "candidates_after_filter":        candidates_after,
        "error_count":                    error_count,
        "error_rate":                     round(error_count / records_attempted, 6) if records_attempted else 0,
        "records_with_candidates_ratio":  round(cnt["records_with_candidates"] / records_attempted, 6) if records_attempted else 0,
        "generic_title_count":            generic_title_count,
        "generic_title_ratio":            round(generic_title_count / candidates_after, 6) if candidates_after else 0,
        "nav_title_count":                nav_title_count,
        "capped_records_count":           capped_records_count,
        "confidence_counts":              dict(conf_counter),
        "kind_counts":                    dict(kind_counter),
        "extension_counts":               dict(ext_counter),
        "per_domain_counts":              dict(domain_counter),
        "title_counts_top":               title_counter.most_common(15),
        "duplicate_url_count":            cnt["duplicates_removed"],
        "skipped_counts":                 dict(total_skipped),
    }

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    c = manifest["counts"]
    qs = manifest["quality_summary"]
    print(f"\n[F2-A] done: attempted={c['records_attempted']} "
          f"with_candidates={c['records_with_candidates']} "
          f"links={c['candidate_links_total']} "
          f"(before_filter={c['candidates_before_filter']}) "
          f"dups_removed={c['duplicates_removed']} "
          f"high={c['high_confidence']} med={c['medium_confidence']} "
          f"low={c['low_confidence']} errors={c['errors']}")
    if qs["skipped_counts"]:
        print(f"[F2-A] skipped: {qs['skipped_counts']}")
    print(f"[F2-A] manifest -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
