#!/usr/bin/env python3
"""
tools/privacy_validator.py
ADG OPS v0.6.93 / Prompt 246 (P246 foundation) — Public-data privacy regression
validator.

Standard-library only. No network. No package install. No filesystem writes.
Reads JSON surfaces and reports privacy findings; it NEVER mutates any file and
NEVER prints a rejected raw value, a rejected raw key, an operator-provided
absolute path, or any digest derived from a rejected raw value.

P246 foundation phase (inert / report-only):
  - hard privacy classes fail closed (ERROR, exit 2) for synthetic fixtures and
    direct CLI negative cases;
  - current public production is scanned in REPORT-ONLY mode: known hygiene
    findings are WARN and never escalate the exit code;
  - the validator is NOT wired into any production/CI gate here.

Three trust surfaces (see LOCKED P246 POLICY):

  internal-ephemeral   gitignored candidates/reports/backups/logs. May legitimately
                       carry bounded operational metadata (LOCAL markers, _tmp paths,
                       diagnostic carriers such as source_errors / traceback). Public
                       output/hygiene rules do NOT apply, but HARD private-data rules
                       (secrets, contact PII incl. phone values, personal-id values,
                       NIF) still do.

  public-build         data/licitaciones.json, shards, manifest, data/public/**,
                       data/recursos.json — strict privacy validation.

  public-diagnostic    validator/report/log output — must never echo a raw value;
                       any hard-class value present is an ERROR, and public raw
                       carriers (content/response/source_errors/traceback/...) are
                       ERROR here too.

Exit codes:
  0  no ERROR findings (WARN allowed; report-only / current-production mode)
  2  one or more ERROR privacy violations
  1  usage / file-read / JSON-parse / structural execution failure

Diagnostics only ever contain: rule id, severity, surface, safe repository-relative
or safe-basename source label, safe JSON pointer (sensitive/unsafe keys redacted),
value type, bounded length, and a deterministic fingerprint derived ONLY from that
safe metadata (never from the raw value).
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Public surfaces scanned by --validate-public (repository-relative, read-only)
# ---------------------------------------------------------------------------

PUBLIC_SURFACES = [
    "data/licitaciones.json",
    "data/licitaciones_2024.json",
    "data/licitaciones_2025.json",
    "data/licitaciones_2026.json",
    "data/licitaciones_archive.json",
    "data/licitaciones_manifest.json",
    "data/public/directorio/socios.json",
    "data/public/laus/categories.json",
    "data/public/laus/editions.json",
    "data/public/laus/juries.json",
    "data/recursos.json",
]


def public_surface_paths() -> list[Path]:
    """Absolute paths of the tracked public surfaces, for callers/tests."""
    return [REPO_ROOT / rel for rel in PUBLIC_SURFACES]


# ---------------------------------------------------------------------------
# Severity + surfaces
# ---------------------------------------------------------------------------

ERROR = "ERROR"
WARN = "WARN"

SURFACE_INTERNAL = "internal-ephemeral"
SURFACE_PUBLIC = "public-build"
SURFACE_DIAGNOSTIC = "public-diagnostic"
SURFACES = (SURFACE_INTERNAL, SURFACE_PUBLIC, SURFACE_DIAGNOSTIC)


class PrivacyValidatorUsageError(ValueError):
    """Raised by the public validation API for structurally invalid calls
    (P246 corr F5): e.g. an unknown trust-surface identifier. The message
    never includes the caller-supplied value."""

# Rule classes.
#   HARD_ALL      ERROR on every surface (hard private-data — applies even to
#                 gitignored ephemeral state: secrets, contact PII incl. phone
#                 values, personal-id values, NIF).
#   PUBLIC_HARD   ERROR on public-build & public-diagnostic; suppressed on
#                 internal-ephemeral (local operational state may hold these:
#                 paths, raw carriers, private-host URLs).
#   HYGIENE_WARN  WARN on public-build only; suppressed elsewhere.
HARD_ALL = {
    "CREDENTIAL_KEY",
    "CREDENTIAL_VALUE",
    "PRIVATE_KEY_BLOCK",
    "EMAIL_VALUE",
    "EMAIL_KEY",
    "CONTACT_KEY",
    "CONTACT_VALUE",
    "PERSONAL_ID_KEY",
    "PERSONAL_ID_VALUE",
    "POPULATED_WINNING_PARTY_NIF",
}
PUBLIC_HARD = {
    "WINDOWS_ABS_PATH",
    "UNC_PATH",
    "UNIX_HOME_PATH",
    "RAW_PAYLOAD_CARRIER",
    "DANGEROUS_URL_SCHEME",
    "UNSAFE_URL_HOST",
}
HYGIENE_WARN = {
    "RELATIVE_TMP_PATH",
    "LOCAL_MARKER",
    "BOOKKEEPING_FIELD",
    "FAMILY_SOURCE_FILE",
    "SCHEMA_UNKNOWN",
}


def severity_for(rule_id: str, surface: str):
    """Return 'ERROR', 'WARN', or None (suppressed) for a rule on a surface."""
    if rule_id in HARD_ALL:
        return ERROR
    if rule_id in PUBLIC_HARD:
        return ERROR if surface in (SURFACE_PUBLIC, SURFACE_DIAGNOSTIC) else None
    if rule_id in HYGIENE_WARN:
        return WARN if surface == SURFACE_PUBLIC else None
    return None


# ---------------------------------------------------------------------------
# Unicode-aware key folding + tokenization (F1 / F2)
# ---------------------------------------------------------------------------

def _fold(s) -> str:
    """NFKD normalize, drop combining marks, lowercase.

    "Teléfono" -> "telefono"; "Contraseña" -> "contrasena".
    """
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()


def normalize_key(key: str) -> str:
    """Fold accents/case, then strip to a compact alphanumeric token.

    "E-Mail" -> "email"; "api_key"/"API KEY"/"apiKey" -> "apikey";
    "Teléfono" -> "telefono".
    """
    return re.sub(r"[^a-z0-9]", "", _fold(key))


_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def key_tokens(key) -> list[str]:
    """Tokenize a key across separators and camelCase boundaries, accent-folded.

    "contact_phone" -> ["contact","phone"]; "databasePassword" ->
    ["database","password"]; "correo_electrónico" -> ["correo","electronico"].
    """
    s = unicodedata.normalize("NFKD", str(key))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = _CAMEL_BOUNDARY_RE.sub(" ", s).lower()
    return [t for t in re.split(r"[^a-z0-9]+", s) if t]


# URL-like key/field names (P246 corr F4): a value under one of these keys is
# held to the stricter "must be a valid http/https URL" policy in _scan_uri.
_URL_LIKE_KEY_TOKENS = {"url", "uri", "href", "link"}


def _is_url_like_key(key) -> bool:
    if key is None:
        return False
    return bool(set(key_tokens(key)) & _URL_LIKE_KEY_TOKENS)


# ---------------------------------------------------------------------------
# Sensitive key vocabularies (folded tokens / phrases)
# ---------------------------------------------------------------------------

CREDENTIAL_SINGLE = {
    "token", "secret", "password", "passwd", "pwd", "passphrase",
    "contrasena", "contrasenya", "credential", "credentials",
    "authorization", "bearer",
    # compact forms for keys with no separator/camel boundary to split on
    "apikey", "apitoken", "authtoken", "accesstoken", "refreshtoken",
    "sessiontoken", "accesskey", "secretkey", "clientsecret", "privatekey",
}
CREDENTIAL_PHRASES = {
    ("api", "key"), ("api", "token"), ("private", "key"), ("access", "token"),
    ("access", "key"), ("secret", "key"), ("client", "secret"),
    ("session", "token"), ("auth", "token"), ("refresh", "token"),
    ("bearer", "token"),
}
EMAIL_SINGLE = {"email", "mail", "correo", "emailaddress", "mailaddress"}
EMAIL_PHRASES = {("e", "mail"), ("email", "address"), ("mail", "address"),
                 ("correo", "electronico")}
CONTACT_SINGLE = {"phone", "tel", "telefon", "telefono", "mobile", "movil",
                  "fax", "whatsapp"}
PERSONAL_ID_SINGLE = {"dni", "nie"}
# Raw/diagnostic payload carriers matched on the WHOLE compact key (never on a
# contained token) so enumerated schema fields such as estat_raw /
# status_code_raw — whose names merely contain "raw" — are NOT misclassified.
RAW_COMPACT = {
    "raw", "payload", "body", "snippet", "content", "response",
    "traceback", "exception", "stderr", "stdout",
    "rawbody", "rawresponse", "rawcontent", "httpbody",
    "responsebody", "responsecontent", "sourceerrors", "helperlog",
}
RAW_PHRASES = {
    ("raw", "body"), ("raw", "response"), ("raw", "content"),
    ("http", "body"), ("response", "body"), ("response", "content"),
    ("source", "errors"), ("helper", "log"),
}
FAMILY_SOURCE_FILE_KEYS = {"sourcefile"}

# Known hygiene / bookkeeping keys. Presence -> WARN, never ERROR.
BOOKKEEPING_KEYS = {
    "statusprovenance", "winnerprovenance", "sourcemergeclass",
    "lifecyclecategory", "lifecyclereviewrequired", "activeopportunityeligible",
    "productiononlypreserved", "enrichmentpreserved", "enrichmentversion",
    "enrichmentrules", "importbatch", "sourceref", "prompt", "note", "mode",
    "backuppath", "candidate109input", "policy110input", "policy111input",
    "generatedbyprompt", "canonicalsourcepreserved",
}
BOOKKEEPING_PREFIXES = (
    "dryrun", "scheduledmerge", "productionwrite", "policy", "candidate",
)


def _is_bookkeeping_key(nkey: str) -> bool:
    if nkey in BOOKKEEPING_KEYS:
        return True
    if nkey.endswith("gatenote"):
        return True
    return any(nkey.startswith(p) for p in BOOKKEEPING_PREFIXES)


# Known public schema keys. Anything else -> SCHEMA_UNKNOWN WARN in production
# mode. Intentionally NOT an exhaustive procurement schema.
KNOWN_PUBLIC_KEYS = {normalize_key(k) for k in {
    # monolith wrapper
    "meta", "data",
    # licitaciones record (top-level)
    "id", "titol", "organisme", "adjudicatari", "tipus", "pressupost",
    "disciplines", "ccaa", "lloc", "data_pub", "data_limit", "estat",
    "estat_raw", "rellevancia", "url", "font", "kw", "cpv", "historial",
    "contract_folder_id", "canonical_key", "notice_type", "notice_type_code",
    "status_rank", "first_pub_date", "last_notice_date", "status_provenance",
    "winner_provenance", "related_contract_ids", "sources_seen",
    "award_results", "documents", "notice_history", "duplicate_relations",
    "source_merge_class", "lifecycle_category", "active_opportunity_eligible",
    "lifecycle_review_required", "production_only_preserved",
    "enrichment_preserved", "enrichment_version", "enrichment_rules",
    "dry_run_mode", "dry_run_note",
    # historial[]
    "data", "estat", "nota",
    # award_results[]
    "notice_id", "result_code", "winning_party_name", "winning_party_nif",
    "award_amount_tax_excl", "award_amount_tax_incl", "lot_id", "lot_title",
    "contract_id", "award_date", "formalization_date", "modification_date",
    "provenance",
    # documents[]
    "document_type", "source_section", "title", "mime_hint", "format_hint",
    "published_at",
    # notice_history[]
    "status_key", "status_code_raw", "issue_date", "source",
    # duplicate_relations[]
    "tender_id", "relation_type",
    # monolith meta / manifest
    "prompt", "version", "mode", "production_write", "generated_at",
    "production_input", "candidate_109_input", "policy_110_input",
    "policy_111_input", "note", "production_write_gate_prompt",
    "production_write_gate_version", "production_write_gate_applied_at",
    "production_write_gate_backup", "production_write_gate_note",
    "scheduled_merge_mode", "scheduled_merge_prompt", "scheduled_merge_version",
    "scheduled_merge_applied_at", "production_write_performed", "backup_path",
    "run_status", "is_partial", "failed_sources", "source_errors",
    "schema", "generated_by_prompt", "target_version", "source",
    "source_sha256", "generated_at_utc", "canonical_source_preserved",
    "top_shape", "source_meta", "shards", "counts", "year", "path", "count",
    "bytes", "priority", "source_records", "sharded_records", "duplicate_ids",
    "missing_year_records", "shard_meta",
    # families: socios / juries / editions / categories
    "name", "type", "source_ref", "role", "studio_or_context",
    "category_judged", "category_id", "is_chair", "import_batch",
    "source_file", "edition_label", "edition_number",
    "edition_number_estimated", "edition_number_source", "participants",
    "nationalities", "awards_count", "attendees_nit_laus", "status_note",
    "label",
    # recursos.json
    "updated", "calculadora", "proyectos", "disc", "horasBase", "experiencia",
    "tarifaHora", "complejidad", "mult", "urgencia", "recursos", "plantillas",
}}


def classify_key(key):
    """Return the sensitive/carrier/bookkeeping rule a key triggers, or None.

    Compound and camelCase keys are tokenized (F1) and accent-folded (F2), so
    contact_phone / databasePassword / github_token / operator_dni /
    config_private_key / teléfono / correo_electrónico / contraseña are all
    detected. Multi-word credential concepts (api key, private key, access
    token, ...) match only as adjacent token phrases, so ordinary schema keys
    that merely contain "key" (canonical_key, status_key) are NOT flagged.
    """
    compact = normalize_key(key)
    if compact == "winningpartynif":
        return "POPULATED_WINNING_PARTY_NIF"
    toks = key_tokens(key)
    tokset = set(toks)
    pairs = set(zip(toks, toks[1:]))
    if tokset & CREDENTIAL_SINGLE or pairs & CREDENTIAL_PHRASES:
        return "CREDENTIAL_KEY"
    if tokset & EMAIL_SINGLE or pairs & EMAIL_PHRASES:
        return "EMAIL_KEY"
    if tokset & CONTACT_SINGLE:
        return "CONTACT_KEY"
    if tokset & PERSONAL_ID_SINGLE:
        return "PERSONAL_ID_KEY"
    if compact in RAW_COMPACT or pairs & RAW_PHRASES:
        return "RAW_PAYLOAD_CARRIER"
    if compact in FAMILY_SOURCE_FILE_KEYS:
        return "FAMILY_SOURCE_FILE"
    if _is_bookkeeping_key(compact):
        return "BOOKKEEPING_FIELD"
    return None


# Rules whose emission is gated on a populated value.
_POPULATED_GATED = {
    "CREDENTIAL_KEY", "EMAIL_KEY", "CONTACT_KEY", "PERSONAL_ID_KEY",
    "POPULATED_WINNING_PARTY_NIF", "RAW_PAYLOAD_CARRIER",
}


# ---------------------------------------------------------------------------
# Value pattern detectors
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
CREDENTIAL_VALUE_RES = [
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(
        r"(?i)\b(api[_\-]?key|secret|secret[_\-]?key|password|passwd|"
        r"access[_\-]?token|auth[_\-]?token|client[_\-]?secret)\b\s*[:=]\s*\S{6,}"
    ),
    re.compile(r"(?i)\bauthorization\s*:\s*\S{6,}"),
]
# Drive-rooted Windows absolute paths, either slash style (P246 corr F3):
# "C:\Users\..." or "C:/Users/...". The negative lookbehind keeps ordinary
# multi-letter schemes (http://, ftp://, ...) and "C: text" drive-relative
# prose from matching, since the drive letter itself must not be preceded by
# another alphanumeric character, and the colon must be immediately followed
# by a path separator.
WINDOWS_ABS_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
UNC_RE = re.compile(r"\\\\[^\\]")
UNIX_HOME_RE = re.compile(r"(?:^|[\s\"'(=,:])/(?:home|Users|root)/[^/\s]")

# --- conservative phone-value detector (F3) --------------------------------
# Fires ONLY on an explicit international "+" prefix followed by 9..15 digits in
# phone-separator form (space / dot / hyphen / parentheses). Requiring the "+"
# is a deliberately conservative boundary: public procurement data is dense with
# space/dot-separated expedient codes, budgets, CPV codes, dates and long
# reference identifiers, and only the international prefix reliably distinguishes
# a leaked phone number from those. National-format numbers without a "+" are
# intentionally NOT flagged in this foundation phase (documented limitation).
_PHONE_RE = re.compile(r"(?<![\w+])\+\d[\d ().\-]{7,17}\d(?![\w])")


def _looks_like_phone(value: str) -> bool:
    for m in _PHONE_RE.finditer(value):
        digits = re.sub(r"\D", "", m.group(0))
        if 9 <= len(digits) <= 15:
            return True
    return False


# --- conservative DNI/NIE value detector (F4) ------------------------------
# DNI = 8 digits + control letter; NIE = [XYZ] + 7 digits + control letter, at
# alphanumeric boundaries. The trailing letter must satisfy the official mod-23
# control-letter checksum. Checksum validation is what gives false-positive
# resistance against synthetic contract/reference identifiers: production shapes
# such as "2019/00014032E" or "2023/ETSAE0814/00004284E" match the length shape
# but FAIL the checksum, so they are not flagged. Company CIFs (letter + 8
# digits) do not match the shape at all. (A person-form value under the
# winning_party_nif key is caught unconditionally by the KEY rule, independent
# of this checksum.)
_DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
_NIE_PREFIX = {"X": "0", "Y": "1", "Z": "2"}
# The leading negative lookbehind also excludes code separators "/ - ." so a
# DNI-shaped segment embedded in a slash-delimited reference code (e.g.
# ".../00000411C") is not treated as a person identifier. A heavily zero-padded
# body (4+ leading zeros) is likewise a reference/expediente code, never a real
# issued DNI, and is rejected below.
_DNI_RE = re.compile(r"(?<![A-Za-z0-9/.\-])(\d{8})([A-Za-z])(?![A-Za-z0-9])")
_NIE_RE = re.compile(r"(?<![A-Za-z0-9/.\-])([XYZxyz])(\d{7})([A-Za-z])(?![A-Za-z0-9])")


def _looks_like_dni_nie(value: str) -> bool:
    for m in _DNI_RE.finditer(value):
        num = m.group(1)
        if num.startswith("0000"):
            continue
        if _DNI_LETTERS[int(num) % 23] == m.group(2).upper():
            return True
    for m in _NIE_RE.finditer(value):
        num = m.group(2)
        if num.startswith("0000"):
            continue
        n = int(_NIE_PREFIX[m.group(1).upper()] + num)
        if _DNI_LETTERS[n % 23] == m.group(3).upper():
            return True
    return False


# --- contextual phone/DNI-NIE detectors under an explicit label (P246 corr
# F7) -------------------------------------------------------------------
# The conservative "+"-prefixed phone detector and checksum-validated
# DNI/NIE detector above stay unconditional and unweakened. These two
# additions ONLY fire when an explicit contact/identifier label word sits
# shortly before the candidate shape in the SAME string — a labeled
# "Tel: 612 345 678" or "DNI-12345678Z" is disclosive even without a "+"
# prefix or a valid checksum, but an unlabeled bare number/code (a
# procurement reference, a budget figure, a CPV code, ...) must stay
# conservative and pass.
_PHONE_LABEL_TOKENS = {
    "tel", "telefon", "telefono", "phone", "mobile", "movil", "whatsapp",
    "contacte", "contact", "llama", "call",
}
_NATIONAL_PHONE_RE = re.compile(r"(?<!\d)[6-9]\d{2}[ .\-]?\d{3}[ .\-]?\d{3}(?!\d)")
_LABEL_LOOKBACK = 25


def _looks_like_labeled_national_phone(value: str) -> bool:
    folded = _fold(value)
    for m in _NATIONAL_PHONE_RE.finditer(folded):
        window = folded[max(0, m.start() - _LABEL_LOOKBACK):m.start()]
        if set(re.split(r"[^a-z0-9]+", window)) & _PHONE_LABEL_TOKENS:
            return True
    return False


_LABELED_DNI_RE = re.compile(r"(?<![A-Za-z0-9])(\d{8})([A-Za-z])(?![A-Za-z0-9])")
_LABELED_NIE_RE = re.compile(r"(?<![A-Za-z0-9])([xyz])(\d{7})([A-Za-z])(?![A-Za-z0-9])")


def _looks_like_labeled_dni_nie(value: str) -> bool:
    folded = _fold(value)
    for m in re.finditer(r"\bdni\b|\bnie\b", folded):
        window = folded[m.end():m.end() + 20]
        if _LABELED_DNI_RE.search(window) or _LABELED_NIE_RE.search(window):
            return True
    return False


# --- URI safety (F6 baseline; P246 corr F4 context-aware rewrite; P246 v0.4
# F1/F2 micro-correction) ----------------------------------------------
# _URI_AUTH_RE recognizes any "scheme://" authority anchored at the start of
# a (stripped) value — used to decide whether a URL-like field's whole value
# is a syntactically valid http/https URL.
_URI_AUTH_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9+.\-]*)://")
NONHTTP_OPAQUE_SCHEMES = {
    "file", "ftp", "ftps", "mailto", "javascript", "vbscript", "tel", "sms",
    "ssh", "ldap", "gopher", "about", "blob", "filesystem", "view-source",
    "ws", "wss", "dict", "smb", "nfs", "chrome", "resource",
}
# A credible URI-scheme token boundary anywhere in a string (P246 corr F4):
# start-of-string, or preceded by whitespace/quote/paren/angle-bracket/comma/
# semicolon, then a scheme-shaped word, ':', an optional "//" authority
# marker, and a non-space character — so "Note: text" (space after ':')
# never matches, but "See javascript:alert(1)" and "Mirror ftp://host/x" do.
_DANGEROUS_SCHEME_TOKEN_RE = re.compile(
    r"(?:^|(?<=[\s\"'(<,;]))([A-Za-z][A-Za-z0-9+.\-]{0,30}):(//)?(?=\S)"
)
# Embedded special-HTTP(S) token anywhere a start-or-non-word boundary
# occurs (P246 v0.8.1: the v0.8 boundary set — start-of-string, or
# whitespace/quote/paren/angle-bracket/comma/semicolon only — missed
# credible tokens preceded by other non-word punctuation such as ":", "-",
# "=", "[", "|"). The fixed-width negative lookbehind `(?<!\w)` succeeds at
# string start and after any non-word (non letter/digit/underscore)
# character, but fails when "http"/"https" is glued onto a preceding
# alphanumeric/underscore identifier (e.g. "abchttp://", "foo_https://",
# "123http:") so those stay unmatched. "http"/"https" is matched case-
# insensitively, then ":", then the bounded non-whitespace tail. Zero, one,
# three-or-more forward slashes, and any backslash/forward-slash mix are
# ALL recognized here (not just the canonical "//") because browser/WHATWG
# special-URL parsing canonicalizes every one of those forms to the same
# network authority; "HTTP: 2026 status" never matches because a space
# immediately after the colon fails the non-whitespace-tail requirement.
_EMBEDDED_SPECIAL_HTTP_TOKEN_RE = re.compile(
    r"(?<!\w)(https?):(\S+)", re.IGNORECASE
)


def _rebuild_special_http_inspection_value(scheme: str, tail: str):
    """Normalize an embedded 'scheme:tail' special-HTTP(S) token into a
    single inspection-only value (P246 v0.8 SPECIAL-URL INSPECTION
    NORMALIZATION): lowercase the scheme, convert every backslash in the
    tail to '/', strip the complete leading '/' run, and rebuild exactly
    'scheme://<remaining tail>'. Returns None if no tail content remains
    once the leading slash run is removed (invalid/missing authority) —
    this is what makes zero/one/three/many slash-or-backslash separator
    forms ("http:127.0.0.1/x", "http:///127.0.0.1/x", "http:\\\\127.0.0.1\\x",
    ...) all resolve to the identical rebuilt authority a browser would
    parse. Never returns the raw token; the caller must not log this value.
    """
    normalized_tail = tail.replace("\\", "/").lstrip("/")
    if not normalized_tail:
        return None
    return f"{scheme.lower()}://{normalized_tail}"


def _embedded_http_token_is_unsafe(scheme: str, tail: str) -> bool:
    """True iff an embedded 'scheme:tail' special-HTTP(S) token (P246 v0.8)
    must produce a hard finding: invalid/missing authority (including a
    tail that normalizes to nothing), embedded credentials, an invalid/
    out-of-range port, or a non-public host — localhost/.local/.internal or
    a private/loopback/link-local/reserved/obfuscated address — classified
    only through the shared `_canonical_host()` path via `_host_is_private()`
    so this can never disagree with `_is_valid_public_url()` about the same
    host. A valid public host returns False. Returns a boolean only; never
    returns or logs the raw token/URL.
    """
    rebuilt = _rebuild_special_http_inspection_value(scheme, tail)
    if rebuilt is None:
        return True
    try:
        parts = urlsplit(rebuilt)
    except ValueError:
        return True
    if not parts.netloc or not parts.hostname:
        return True
    if parts.username or parts.password:
        return True
    try:
        parts.port
    except ValueError:
        return True
    return _host_is_private(parts.hostname)


_DNS_LABEL_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$")
# Every dot-separated component is a bare decimal/octal-looking/hex integer
# (P246 v0.7 F1): a browser-canonicalized IPv4 obfuscation such as
# "2130706433", "017700000001", "0x7f000001", "127.1", "0xc0.0xa8.0x1.0x1".
_NUMERIC_HOST_COMPONENT_RE = re.compile(r"^(?:0x[0-9a-f]+|[0-9]+)$", re.IGNORECASE)

_HOST_INVALID = "invalid"
_HOST_IP = "ip"
_HOST_DNS = "dns"


def _canonical_host(host: str):
    """Canonicalize a URL hostname for policy decisions (P246 v0.7 shared
    host-normalization path). `host` must already be `urlsplit(...).hostname`
    (bracket-stripped, credential-free, as returned for both IPv6-literal and
    ordinary forms). Returns a `(kind, value)` pair:

      (_HOST_INVALID, None)          empty / malformed / obfuscated host
      (_HOST_IP, ip_address object)  a canonical IPv4/IPv6 address
      (_HOST_DNS, ascii_hostname)    a normalized, lowercase, trailing-dot-
                                     stripped ASCII DNS hostname

    `_is_valid_public_url()` and `_host_is_private()` both classify through
    this one path so a host cannot be treated as valid public DNS by one
    function while being rejected — or vice versa — by the other (P246 v0.7:
    prior versions ran independent, inconsistent host logic in each).

    No DNS resolution or network access is performed anywhere in this path.
    """
    if not host:
        return (_HOST_INVALID, None)
    try:
        return (_HOST_IP, ipaddress.ip_address(host))
    except ValueError:
        pass
    try:
        ascii_host = host.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return (_HOST_INVALID, None)
    # Unicode dot variants (U+3002, U+FF0E, U+FF61) and full-width digits
    # IDNA/nameprep-normalize to canonical ASCII dotted-decimal or hex-colon
    # literals (e.g. "127。0。0。1" / "１２７.０.０.１" -> "127.0.0.1") — retry
    # IP parsing on the normalized form so these cannot slip through as DNS
    # (P246 v0.7 F1 #5).
    try:
        return (_HOST_IP, ipaddress.ip_address(ascii_host))
    except ValueError:
        pass
    normalized = (
        ascii_host[:-1] if ascii_host.endswith(".") and len(ascii_host) > 1
        else ascii_host
    )
    if not (1 <= len(normalized) <= 253):
        return (_HOST_INVALID, None)
    labels = normalized.split(".")
    for label in labels:
        if not (1 <= len(label) <= 63):
            return (_HOST_INVALID, None)
        if not _DNS_LABEL_RE.match(label):
            return (_HOST_INVALID, None)
    if all(_NUMERIC_HOST_COMPONENT_RE.match(label) for label in labels):
        # Every label is a bare number: a canonicalized-IPv4 obfuscation
        # (decimal-integer/octal-looking/hex/shortened/leading-zero), not a
        # real DNS name — reject rather than accept as public DNS
        # (P246 v0.7 F1 #6). A real DNS name always has at least one
        # non-numeric label (e.g. "123.com" keeps its "com" label).
        return (_HOST_INVALID, None)
    return (_HOST_DNS, normalized)


def _is_valid_public_url(value: str) -> bool:
    """True iff `value` is, in its entirety, a well-formed absolute
    http/https URL with a non-empty, syntactically valid hostname and no
    embedded credentials (P246 v0.4 F1; P246 v0.5 F1 authority-syntax
    micro-correction; P246 v0.6 F1 raw-value whitespace/format-char
    correction; P246 v0.7 F1 canonical-host policy correction). Used to hold
    url/uri/href/link-shaped fields to a stricter contract than free-text URI
    scanning: a scheme-less host/path ("example.test/file"), plain prose
    ("not a url"), any whitespace, backslash, or Unicode "C*" category
    character (control/format/surrogate/private-use/unassigned, including
    invisible U+200B-style characters) anywhere in the *original* (unstripped)
    value, an opaque/authority-less http(s) form ("http://", "http:///path"),
    a malformed authority ("https://.", "https://-bad-.com",
    "https://example..com", "https://example.com:abc/x"), or a
    browser-canonicalized IPv4 obfuscation ("http://2130706433/",
    "http://0x7f000001/", "http://127.1/", Unicode-dot/full-width-digit
    variants of "127.0.0.1") is rejected even though none of those is one of
    the explicitly dangerous schemes below. Private-host policy (loopback/
    private/link-local/unspecified/reserved/multicast) is intentionally NOT
    duplicated here — that stays the job of `_embedded_http_token_is_unsafe()`
    / `_host_is_private()`, both of which classify through the same
    `_canonical_host()` used here.
    """
    for ch in value:
        if ch == "\\" or ch.isspace() or unicodedata.category(ch).startswith("C"):
            return False
    if value != value.strip():
        return False
    stripped = value.strip()
    auth = _URI_AUTH_RE.match(stripped)
    if not auth or auth.group(1).lower() not in ("http", "https"):
        return False
    try:
        parts = urlsplit(stripped)
    except ValueError:
        return False
    if not parts.netloc or not parts.hostname:
        return False
    if parts.username or parts.password:
        return False
    try:
        parts.port
    except ValueError:
        return False
    kind, _ = _canonical_host(parts.hostname)
    return kind != _HOST_INVALID


RELATIVE_TMP_RE = re.compile(r"(?:^|[\s\"'(/=])_tmp/|data/_backup/|(?:^|/)_backup")
LOCAL_MARKER_VALUES = {"LOCAL", "LOCAL-ZIP"}


def _host_is_private(host: str) -> bool:
    """True iff `host` must be treated as non-public: a private/loopback/
    link-local/unspecified/reserved/multicast IP, a localhost/.local/
    .internal DNS name, or an invalid/obfuscated host (P246 v0.7 F1) —
    everything but a `host` empty at the `urlsplit()` level, which callers
    handle themselves (an authority-less URL is flagged elsewhere as a
    malformed/dangerous URL, not as an unsafe host). Classification is
    delegated entirely to the shared `_canonical_host()` path so this
    function and `_is_valid_public_url()` can never disagree about whether a
    given raw host string is a canonical IP, a valid DNS name, or garbage.
    """
    if not host:
        return False
    kind, value = _canonical_host(host.strip("[]"))
    if kind == _HOST_INVALID:
        # P246 v0.7 F1: fail closed on obfuscated/unclassifiable hosts
        # (e.g. "2130706433", "0xc0.0xa8.0x1.0x1") rather than silently
        # treating them as public — this is what makes embedded HTTP URLs
        # with a canonicalized-IPv4 host a hard failure too, not just
        # url-like fields.
        return True
    if kind == _HOST_DNS:
        return (value == "localhost" or value.endswith(".localhost")
                or value.endswith(".local") or value.endswith(".internal"))
    ip = value
    # P246 v0.4 F3: is_multicast was missing, so an IPv6 multicast host
    # (e.g. ff02::1) was misclassified as public — private/loopback/
    # link-local/unspecified/reserved were already covered.
    return (ip.is_loopback or ip.is_private or ip.is_link_local
            or ip.is_unspecified or ip.is_reserved or ip.is_multicast)


# ---------------------------------------------------------------------------
# Safe pointer + safe source (F7 / F9 / F10; P246 corr F1 / F2 additions)
# ---------------------------------------------------------------------------

def _ptr_escape(token: str) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


_PLAIN_KEY_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,40}$")
_SAFE_BASENAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")
# Sensitive key classes that must never be echoed literally in a pointer.
_REDACT_KEY_RULES = {"CREDENTIAL_KEY", "EMAIL_KEY", "CONTACT_KEY", "PERSONAL_ID_KEY"}


def _key_hard_rules(s: str):
    """Hard-class rule ids triggered by treating raw text `s` as a VALUE
    (P246 corr F1): a DNI-shaped, credential-shaped, or absolute-path-shaped
    dictionary KEY is exactly as disclosive as the same text stored as a
    value, so it is run through the same hard-value detectors scan_value()
    uses.
    """
    rules = []
    if PRIVATE_KEY_RE.search(s):
        rules.append("PRIVATE_KEY_BLOCK")
    for rx in CREDENTIAL_VALUE_RES:
        if rx.search(s):
            rules.append("CREDENTIAL_VALUE")
            break
    if EMAIL_RE.search(s):
        rules.append("EMAIL_VALUE")
    if _looks_like_phone(s):
        rules.append("CONTACT_VALUE")
    if _looks_like_dni_nie(s):
        rules.append("PERSONAL_ID_VALUE")
    if WINDOWS_ABS_RE.search(s):
        rules.append("WINDOWS_ABS_PATH")
    if UNC_RE.search(s):
        rules.append("UNC_PATH")
    if UNIX_HOME_RE.search(s):
        rules.append("UNIX_HOME_PATH")
    return rules


def _key_looks_value_shaped(key) -> bool:
    """True if a KEY's text, independent of its schema name, is itself
    shaped like a hard-class value (P246 corr F1; P246 v0.8 shared
    embedded special-HTTP token path) — used to force pointer redaction
    even for a plain-ASCII key with no unsafe punctuation."""
    s = str(key)
    if _key_hard_rules(s):
        return True
    for m in _EMBEDDED_SPECIAL_HTTP_TOKEN_RE.finditer(s):
        if _embedded_http_token_is_unsafe(m.group(1), m.group(2)):
            return True
    return False


def _scan_key_as_value(pointer, key, findings, ctx):
    """Emit the same hard-class findings scan_value() would emit, for a
    dictionary KEY's text (P246 corr F1). `pointer` is already built from
    the redacted key segment (see _safe_key_token), so nothing emitted here
    can leak the raw key text.
    """
    s = str(key)
    for rule in _key_hard_rules(s):
        _emit(findings, rule, ctx, pointer, s)
    _scan_uri(pointer, s, findings, ctx, url_like=False)


def _safe_key_token(key, index: int) -> str:
    """Pointer segment for a dict key that never discloses sensitive material.

    Plain, bounded, non-sensitive keys are shown in canonical form. Keys that
    carry sensitive material, unsafe punctuation, control characters, are
    over-long, or are themselves shaped like a hard-class value (P246 corr
    F1) are replaced by a positional redaction token (F7).
    """
    s = str(key)
    if _PLAIN_KEY_RE.match(s) and "\x00" not in s:
        if classify_key(s) in _REDACT_KEY_RULES:
            return f"__redacted_key_{index}__"
        if _key_looks_value_shaped(s):
            return f"__redacted_key_{index}__"
        return _ptr_escape(s)
    return f"__redacted_key_{index}__"


def _safe_source_label(path_or_name) -> str:
    """A safe basename source label; never an absolute or directory path (F9/F10)."""
    name = Path(str(path_or_name)).name
    return name if _SAFE_BASENAME_RE.match(name) else "<source>"


_SOURCE_PLACEHOLDERS = {"<memory>", "<source>"}


def _sanitize_source(source) -> str:
    """Central, API-enforced source-label sanitizer (P246 corr F2).

    Only an exact known PUBLIC_SURFACES repository-relative label, one of
    the fixed internal placeholders, or a safe non-sensitive basename may
    reach Finding.source. Any other label — an absolute path, a directory
    path, a sensitive filename — collapses to the "<source>" placeholder.
    Enforced here (not only at CLI call sites) so any future caller of the
    library API is covered too.
    """
    s = str(source)
    if s in PUBLIC_SURFACES or s in _SOURCE_PLACEHOLDERS:
        return s
    name = Path(s.replace("\\", "/")).name
    if not _SAFE_BASENAME_RE.match(name):
        return "<source>"
    if _key_looks_value_shaped(name):
        return "<source>"
    return name


# ---------------------------------------------------------------------------
# Finding model + safe formatting
# ---------------------------------------------------------------------------

def _value_type(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _bounded_len(value) -> int:
    try:
        return len(value) if isinstance(value, (str, list, dict)) else len(str(value))
    except Exception:
        return -1


def _fingerprint(rule_id, source, pointer, value_type, length) -> str:
    """Deterministic diagnostic fingerprint from SAFE metadata only (F8).

    Never derived from the raw value or raw key — so it cannot be brute-forced
    back to a low-entropy secret (phone, NIF, token, path).
    """
    basis = f"{rule_id}|{source}|{pointer}|{value_type}|{length}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:8]


class Finding:
    __slots__ = ("rule_id", "severity", "surface", "source", "pointer",
                 "value_type", "length", "fp")

    def __init__(self, rule_id, severity, surface, source, pointer, value):
        self.rule_id = rule_id
        self.severity = severity
        self.surface = surface
        self.source = source
        self.pointer = pointer
        self.value_type = _value_type(value)
        self.length = _bounded_len(value)
        self.fp = _fingerprint(rule_id, source, pointer, self.value_type, self.length)

    def key(self):
        return (self.source, self.surface, 0 if self.severity == ERROR else 1,
                self.rule_id, self.pointer)

    def dedup_key(self):
        # Collapse repeated occurrences of the same rule on the same key name so
        # scanning thousands of records yields a bounded, deterministic report.
        # Source is part of the key so identical pointers from two source files
        # stay distinguishable (F10).
        last = self.pointer.rsplit("/", 1)[-1]
        last = re.sub(r"\[\d+\]", "[]", last)
        parent = re.sub(r"\[\d+\]", "[]", self.pointer)
        parent = parent.rsplit("/", 1)[0] if "/" in self.pointer else self.pointer
        return (self.source, self.surface, self.rule_id, parent + "/" + last)

    def as_dict(self, count=1):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "surface": self.surface, "source": self.source,
            "pointer": self.pointer, "value_type": self.value_type,
            "length": self.length, "fp": self.fp, "count": count,
        }

    def format_line(self, count=1):
        return (f"[{self.severity}] {self.rule_id} surface={self.surface} "
                f"source={self.source} pointer={self.pointer} "
                f"type={self.value_type} len={self.length} fp={self.fp} "
                f"count={count}")


# ---------------------------------------------------------------------------
# Scanners
# ---------------------------------------------------------------------------

def _is_populated(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _emit(findings, rule_id, ctx, pointer, value):
    sev = severity_for(rule_id, ctx.surface)
    if sev is None:
        return
    findings.append(Finding(rule_id, sev, ctx.surface, ctx.source, pointer, value))


def scan_key(pointer, key, value, findings, ctx):
    rule = classify_key(key)
    if rule is not None:
        if rule in _POPULATED_GATED:
            if _is_populated(value):
                _emit(findings, rule, ctx, pointer, value)
        else:
            _emit(findings, rule, ctx, pointer, value)
        return

    if ctx.production:
        nkey = normalize_key(key)
        if nkey and nkey not in KNOWN_PUBLIC_KEYS:
            _emit(findings, "SCHEMA_UNKNOWN", ctx, pointer, value)


def scan_value(pointer, value, findings, ctx, key_hint=None):
    if not isinstance(value, str) or value == "":
        return

    # Hard private-data value patterns (any surface).
    if PRIVATE_KEY_RE.search(value):
        _emit(findings, "PRIVATE_KEY_BLOCK", ctx, pointer, value)
    for rx in CREDENTIAL_VALUE_RES:
        if rx.search(value):
            _emit(findings, "CREDENTIAL_VALUE", ctx, pointer, value)
            break
    if EMAIL_RE.search(value):
        _emit(findings, "EMAIL_VALUE", ctx, pointer, value)
    if _looks_like_phone(value) or _looks_like_labeled_national_phone(value):
        _emit(findings, "CONTACT_VALUE", ctx, pointer, value)
    if _looks_like_dni_nie(value) or _looks_like_labeled_dni_nie(value):
        _emit(findings, "PERSONAL_ID_VALUE", ctx, pointer, value)

    # Path leakage (public surfaces).
    if WINDOWS_ABS_RE.search(value):
        _emit(findings, "WINDOWS_ABS_PATH", ctx, pointer, value)
    if UNC_RE.search(value):
        _emit(findings, "UNC_PATH", ctx, pointer, value)
    if UNIX_HOME_RE.search(value):
        _emit(findings, "UNIX_HOME_PATH", ctx, pointer, value)

    # URI safety (public surfaces; P246 corr F4 context-aware inspection).
    _scan_uri(pointer, value, findings, ctx, url_like=_is_url_like_key(key_hint))

    # Hygiene (public surfaces, report-only).
    if RELATIVE_TMP_RE.search(value):
        _emit(findings, "RELATIVE_TMP_PATH", ctx, pointer, value)
    if value.strip() in LOCAL_MARKER_VALUES:
        _emit(findings, "LOCAL_MARKER", ctx, pointer, value)


def _scan_uri(pointer, value, findings, ctx, url_like=False):
    """Context-aware URI inspection (P246 corr F4; P246 v0.4 F1/F2 micro-
    correction; P246 v0.8 embedded special-HTTP token correction).

    Explicitly dangerous schemes (javascript, data, file, ftp, mailto, ...)
    are located anywhere a credible URI token boundary occurs in the string,
    and every embedded http(s) special-HTTP token — recognized at that same
    credible token boundary, independent of separator form (zero, one,
    three-or-more forward slashes, any backslash mix) — is inspected via
    the shared `_embedded_http_token_is_unsafe()` path for credentials/
    invalid ports/private hosts wherever it occurs, not only at the start of
    the value and not only for the canonical "//" form. A credible "data:"
    token (any non-space form, e.g. "data:payload") is always dangerous
    (P246 v0.4 F2); ordinary colon-prose with a space right after the colon
    ("Data: 2026-01-01", "HTTP: 2026 status") never matches the token
    boundary at all, so it stays unaffected. When `url_like` is True (the
    value populates a url/uri/href/link-shaped field) a populated value
    must, in its entirety, be a valid absolute http/https URL with a
    non-empty hostname and no embedded credentials (P246 v0.4 F1) —
    independent of whether it also contains a recognizable scheme token, so
    scheme-less text ("example.test/file", "not a url") and opaque/
    authority-less http(s) forms ("http://", "http:///path") are rejected
    too.
    """
    reported = False
    for m in _DANGEROUS_SCHEME_TOKEN_RE.finditer(value):
        scheme = m.group(1).lower()
        has_authority = m.group(2) == "//"
        if scheme in ("http", "https"):
            continue  # handled by the embedded-http scan below
        if scheme == "data":
            _emit(findings, "DANGEROUS_URL_SCHEME", ctx, pointer, value)
            reported = True
        elif scheme in NONHTTP_OPAQUE_SCHEMES:
            _emit(findings, "DANGEROUS_URL_SCHEME", ctx, pointer, value)
            reported = True
        elif url_like and not has_authority:
            _emit(findings, "DANGEROUS_URL_SCHEME", ctx, pointer, value)
            reported = True

    for m in _EMBEDDED_SPECIAL_HTTP_TOKEN_RE.finditer(value):
        if _embedded_http_token_is_unsafe(m.group(1), m.group(2)):
            _emit(findings, "UNSAFE_URL_HOST", ctx, pointer, value)

    if url_like and not reported and value.strip() and not _is_valid_public_url(value):
        _emit(findings, "DANGEROUS_URL_SCHEME", ctx, pointer, value)


class _Ctx:
    __slots__ = ("surface", "production", "source")

    def __init__(self, surface, production, source):
        self.surface = surface
        self.production = production
        self.source = source


def walk(node, pointer, findings, ctx, key_hint=None):
    if isinstance(node, dict):
        for i, (k, v) in enumerate(node.items()):
            child = f"{pointer}/{_safe_key_token(k, i)}"
            scan_key(child, k, v, findings, ctx)
            _scan_key_as_value(child, k, findings, ctx)
            walk(v, child, findings, ctx, key_hint=k)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            walk(item, f"{pointer}[{i}]", findings, ctx, key_hint=key_hint)
    elif isinstance(node, str):
        scan_value(pointer, node, findings, ctx, key_hint=key_hint)


def classify_surface(path_or_mode) -> str:
    """Map an explicit surface name, or a repo path, to a trust surface."""
    if path_or_mode in SURFACES:
        return path_or_mode
    p = str(path_or_mode).replace("\\", "/")
    if "/_tmp/" in p or p.startswith("_tmp/") or "/data/_backup/" in p \
            or "/_handoffs/" in p:
        return SURFACE_INTERNAL
    return SURFACE_PUBLIC


def validate_json_object(obj, surface, production=False, source="<memory>"):
    """Scan an already-parsed JSON object; return a list of Finding.

    Raises PrivacyValidatorUsageError for an unknown trust surface, so an
    invalid identifier fails closed instead of silently suppressing rules
    (P246 corr F5). The source label is centrally sanitized regardless of
    what the caller supplies (P246 corr F2).
    """
    if surface not in SURFACES:
        raise PrivacyValidatorUsageError(
            "unknown trust surface; must be one of: " + ", ".join(SURFACES)
        )
    findings: list[Finding] = []
    walk(obj, "$", findings, _Ctx(surface, production, _sanitize_source(source)))
    return findings


def validate_path_read_only(path: Path, surface, production=False, source=None):
    """Read + parse a JSON file (read-only) and scan it. Raises on read/parse.

    The source label is a safe basename unless the caller supplies an explicit
    safe repository-relative label.
    """
    if source is None:
        source = _safe_source_label(path)
    text = Path(path).read_text(encoding="utf-8")
    obj = json.loads(text)
    return validate_json_object(obj, surface, production, source)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _dedup(findings):
    """Deterministic order + collapse repeats; return list of (Finding, count)."""
    by_key = {}
    for f in sorted(findings, key=lambda x: x.key()):
        dk = f.dedup_key()
        if dk not in by_key:
            by_key[dk] = [f, 0]
        by_key[dk][1] += 1
    rows = [(f, c) for (f, c) in by_key.values()]
    rows.sort(key=lambda fc: fc[0].key())
    return rows


def _grouped_summary(findings):
    """Aggregate findings by (severity, rule_id, source) only (P246 corr
    F9): no pointer, value_type, length, or fingerprint — the output is
    bounded by the number of distinct rule/source groups, not by finding or
    record count."""
    groups: dict = {}
    for f in findings:
        key = (f.severity, f.rule_id, f.source)
        groups[key] = groups.get(key, 0) + 1
    return sorted(
        groups.items(),
        key=lambda kv: (0 if kv[0][0] == ERROR else 1, kv[0][1], kv[0][2]),
    )


def emit_report(findings, as_json, stream=None, summary_only=False):
    # Resolve the stream at call time so contextlib.redirect_stdout works.
    if stream is None:
        stream = sys.stdout
    rows = _dedup(findings)
    n_error = sum(c for f, c in rows if f.severity == ERROR)
    n_warn = sum(c for f, c in rows if f.severity == WARN)

    if summary_only:
        # Bounded reporting support (P246 corr F9; P246 v0.4 F4 micro-
        # correction): grouped aggregation plus a distinct finding-row count
        # (len(rows), the same _dedup() row count the full report uses) —
        # never a raw value/key/pointer, and never a change to the
        # error/warn totals or the caller's exit-code decision.
        groups = _grouped_summary(findings)
        distinct_count = len(rows)
        group_count = len(groups)
        if as_json:
            payload = {
                "schema": "ADGOPS_PRIVACY_VALIDATOR_SUMMARY_V1",
                "error_count": n_error,
                "warn_count": n_warn,
                "distinct_count": distinct_count,
                "group_count": group_count,
                "groups": [
                    {"severity": sev, "rule_id": rid, "source": src, "count": c}
                    for (sev, rid, src), c in groups
                ],
            }
            stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        else:
            for (sev, rid, src), c in groups:
                stream.write(f"[{sev}] {rid} source={src} count={c}\n")
            stream.write(
                f"PRIVACY: errors={n_error} warnings={n_warn} "
                f"distinct={distinct_count} groups={group_count}\n"
            )
        return n_error, n_warn

    if as_json:
        payload = {
            "schema": "ADGOPS_PRIVACY_VALIDATOR_REPORT_V1",
            "error_count": n_error,
            "warn_count": n_warn,
            "findings": [f.as_dict(c) for f, c in rows],
        }
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    else:
        for f, c in rows:
            stream.write(f.format_line(c) + "\n")
        stream.write(
            f"PRIVACY: errors={n_error} warnings={n_warn} "
            f"(distinct={len(rows)})\n"
        )
    return n_error, n_warn


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="privacy_validator",
        description="ADG OPS public-data privacy regression validator (P246 "
                    "foundation, inert/report-only). Never writes files; never "
                    "echoes raw values, raw keys, absolute paths, or raw digests.",
    )
    p.add_argument("--fixture", metavar="PATH",
                   help="Validate one synthetic fixture JSON file.")
    p.add_argument("--surface", choices=list(SURFACES), default=SURFACE_PUBLIC,
                   help="Trust surface for --fixture (default: public-build).")
    p.add_argument("--validate-public", action="store_true",
                   help="Scan tracked public JSON surfaces (public-build, "
                        "production mode).")
    p.add_argument("--report-only", action="store_true",
                   help="Guarantee WARN never escalates the exit code (the "
                        "default behaviour in the P246 foundation; explicit for "
                        "forward compatibility).")
    p.add_argument("--json", action="store_true",
                   help="Emit machine-readable safe diagnostics (no raw values).")
    p.add_argument("--summary-only", action="store_true",
                   help="Bounded diagnostic aggregation grouped by severity+"
                        "rule+source only (no pointers, no per-record detail). "
                        "Never alters exit-code decisions (P246 corr F9 "
                        "foundation reporting support; not wired into any "
                        "gate here).")
    return p


def run(argv):
    args = build_parser().parse_args(argv)

    if args.validate_public and args.fixture:
        sys.stderr.write("[USAGE] --validate-public and --fixture are exclusive\n")
        return 1
    if not args.validate_public and not args.fixture:
        sys.stderr.write("[USAGE] specify --validate-public or --fixture PATH\n")
        return 1

    all_findings = []
    try:
        if args.validate_public:
            missing = []
            for rel in PUBLIC_SURFACES:
                path = REPO_ROOT / rel
                if not path.exists():
                    missing.append(rel)
                    continue
                all_findings.extend(
                    validate_path_read_only(path, SURFACE_PUBLIC,
                                            production=True, source=rel)
                )
            if missing:
                # Report only safe repository-relative labels (never absolute).
                sys.stderr.write(
                    "[STRUCTURAL] missing public surface(s): "
                    + ", ".join(missing) + "\n"
                )
                return 1
        else:
            path = Path(args.fixture)
            if not path.is_absolute():
                path = (Path.cwd() / path)
            if not path.exists():
                # Never echo the operator-provided absolute path (F9).
                sys.stderr.write(
                    f"[STRUCTURAL] fixture not found: {_safe_source_label(args.fixture)}\n"
                )
                return 1
            all_findings.extend(
                validate_path_read_only(path, args.surface, production=False)
            )
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"[PARSE] invalid JSON: line {exc.lineno} col {exc.colno}\n")
        return 1
    except UnicodeError:
        # Never echo the decode error's message (it can carry raw byte/
        # position detail from the input) (P246 corr F6).
        sys.stderr.write("[PARSE] invalid text encoding (expected UTF-8)\n")
        return 1
    except RecursionError:
        sys.stderr.write("[STRUCTURAL] input nesting exceeds safe recursion depth\n")
        return 1
    except OSError as exc:
        sys.stderr.write(f"[READ] {exc.__class__.__name__}: {exc.strerror}\n")
        return 1
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:
        # Fail-closed exception boundary (P246 corr F6): exception class
        # only, never its message, filename, local path, raw input, or
        # traceback.
        sys.stderr.write(
            f"[STRUCTURAL] internal validation failure ({exc.__class__.__name__})\n"
        )
        return 1

    n_error, _ = emit_report(all_findings, args.json, summary_only=args.summary_only)
    return 2 if n_error > 0 else 0


def main():
    return run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
