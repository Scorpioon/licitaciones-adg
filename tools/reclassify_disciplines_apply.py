#!/usr/bin/env python3
# tools/reclassify_disciplines_apply.py
# p206 / v0.6.58 — Controlled discipline reclassification write.
# Reads data/licitaciones.json, applies accepted p205 rules only,
# preserves all existing disciplines, writes back, then reports.
#
# Design:
#   - Only the NEW p205 rules are used for classification (not the full
#     DISC_KW). This prevents accidentally removing disciplines that were
#     set by the fetcher from description text not stored in JSON.
#   - Existing disciplines are always preserved (union, not replace).
#   - Deferred candidates (campaña de comunicación, plan de comunicación,
#     ia/ai) are explicitly absent and must not be added here.
#   - Backup must exist before any write; hard-fail otherwise.
#
# PRODUCTION_WRITE_PERFORMED: true (after backup confirmed)

import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE  = REPO_ROOT / "data" / "licitaciones.json"
BACKUP_DIR = REPO_ROOT / "data" / "_backup"
TMP_DIR    = REPO_ROOT / "_tmp" / "taxonomy_p206"

KNOWN_DISCIPLINES = {
    "branding", "editorial", "web", "uxui", "publicitat",
    "senyaletica", "fotografia", "audiovisual", "illustracio", "impressio",
}

# ---------------------------------------------------------------------------
# Accepted p205 additions ONLY — not the full DISC_KW.
# Deferred phrases deliberately absent: campaña de comunicación, plan de
# comunicación, campanya de comunicació, ia/ai and variants.
# ---------------------------------------------------------------------------
P205_NEW_DISC_KW = {
    "branding":   ["identidad visual", "identitat visual"],
    "editorial":  ["diseño gráfico", "disseny gràfic",
                   "comunicación visual", "comunicació visual",
                   "producción gráfica", "producció gràfica",
                   "artes finales"],
    "publicitat": ["material promocional", "materiales promocionales"],
    "impressio":  ["impresión gran formato", "impressió gran format"],
}

# Flat set of all new keywords for reporting
ALL_NEW_KEYWORDS = {kw for kws in P205_NEW_DISC_KW.values() for kw in kws}


# ---------------------------------------------------------------------------
# Helpers (stdlib-only; no import of fetch_licitaciones.py)
# ---------------------------------------------------------------------------

def norm(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def kw_in(text, kw):
    t, k = norm(text), norm(kw)
    if not t or not k:
        return False
    if len(k) <= 3 and " " not in k:
        return bool(re.search(rf"\b{re.escape(k)}\b", t))
    return k in t


def classify_new(titol):
    """Return set of disciplines triggered by p205 new rules on title only."""
    full = norm(titol)
    discs = set()
    matched_kws = []
    for disc, keys in P205_NEW_DISC_KW.items():
        for k in keys:
            if kw_in(full, k):
                discs.add(disc)
                matched_kws.append(k)
    return discs, matched_kws


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("  ADG OPS - Discipline Reclassification Apply (p206 / v0.6.58)")
    print("=" * 70)

    if not DATA_FILE.exists():
        sys.exit("ERROR: data file not found: %s" % DATA_FILE)

    # --- BACKUP FIRST -------------------------------------------------------
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / ("licitaciones_before_p206_%s.json" % ts)
    shutil.copy2(DATA_FILE, backup_path)
    backup_size = backup_path.stat().st_size
    print("\nBACKUP_CREATED: true")
    print("  path: %s" % backup_path.relative_to(REPO_ROOT))
    print("  size: %d bytes (%.1f KB)" % (backup_size, backup_size / 1024))

    # --- LOAD ---------------------------------------------------------------
    with open(DATA_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    items = raw.get("data", [])
    total = len(items)
    print("\nRecords loaded: %d" % total)

    # Baseline counts
    baseline_unclassified = sum(1 for it in items if not it.get("disciplines"))
    baseline_disc_counter = Counter()
    for it in items:
        for d in (it.get("disciplines") or []):
            baseline_disc_counter[d] += 1

    # --- VALIDATE EXISTING DISCIPLINES --------------------------------------
    unknown_found = []
    for it in items:
        for d in (it.get("disciplines") or []):
            if d not in KNOWN_DISCIPLINES:
                unknown_found.append((it.get("id","?"), d))
    if unknown_found:
        print("\nWARNING: unknown discipline keys in existing data:")
        for iid, d in unknown_found[:10]:
            print("  id=%s  disc=%s" % (iid, d))

    # --- APPLY RULES --------------------------------------------------------
    records_changed = 0
    disc_additions_total = 0
    newly_classified = 0
    kw_hit_counter = Counter()
    changed_sample = []
    still_unclassified_after = 0

    for it in items:
        titol = it.get("titol") or ""
        existing = sorted(set(it.get("disciplines") or []))
        proposed_additions, matched_kws = classify_new(titol)

        for kw in matched_kws:
            kw_hit_counter[kw] += 1

        new_discs = sorted(set(existing) | proposed_additions)

        # Validate no unknown keys introduced
        for d in new_discs:
            if d not in KNOWN_DISCIPLINES:
                print("ERROR: would introduce unknown discipline '%s' on id=%s — skipping"
                      % (d, it.get("id","?")))
                new_discs = existing
                break

        if new_discs != existing:
            additions = sorted(set(new_discs) - set(existing))
            disc_additions_total += len(additions)
            if not existing:
                newly_classified += 1
            records_changed += 1
            it["disciplines"] = new_discs
            if len(changed_sample) < 100:
                changed_sample.append({
                    "id": it.get("id", ""),
                    "titol": titol[:120],
                    "before": existing,
                    "after": new_discs,
                    "added": additions,
                    "matched_kws": matched_kws,
                })
        else:
            it["disciplines"] = existing  # ensure list (not None)

        if not it.get("disciplines"):
            still_unclassified_after += 1

    # --- POST-WRITE DISCIPLINE COUNTER --------------------------------------
    after_disc_counter = Counter()
    for it in items:
        for d in (it.get("disciplines") or []):
            after_disc_counter[d] += 1

    # --- WRITE DATA ---------------------------------------------------------
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    write_size = DATA_FILE.stat().st_size

    print("\nPRODUCTION_WRITE_PERFORMED: true")
    print("  path: data/licitaciones.json")
    print("  size: %d bytes (%.1f KB)" % (write_size, write_size / 1024))

    # --- CONSOLE REPORT -----------------------------------------------------
    print("\n--- APPLY RESULTS ---")
    print("  Total records:            %d" % total)
    print("  Records changed:          %d" % records_changed)
    print("  Discipline additions:     %d" % disc_additions_total)
    print("  Newly classified:         %d  (was 0 disciplines -> now has some)" % newly_classified)
    print("  Baseline unclassified:    %d" % baseline_unclassified)
    print("  Still unclassified after: %d" % still_unclassified_after)

    print("\n--- TOP KEYWORD HITS ---")
    for kw, cnt in kw_hit_counter.most_common():
        print("  [%4d] %s" % (cnt, kw))

    print("\n--- DISCIPLINE DISTRIBUTION: before -> after ---")
    all_discs = sorted(KNOWN_DISCIPLINES)
    for d in all_discs:
        b = baseline_disc_counter.get(d, 0)
        a = after_disc_counter.get(d, 0)
        delta = a - b
        marker = "  (+%d)" % delta if delta else ""
        print("  %-12s  %d -> %d%s" % (d, b, a, marker))

    print("\n--- SAMPLE CHANGED RECORDS (first 15) ---")
    for r in changed_sample[:15]:
        print("  [%s -> %s] %s"
              % (",".join(r["before"]) or "none",
                 ",".join(r["after"]),
                 r["titol"][:80]))

    # --- WRITE _TMP REPORTS -------------------------------------------------
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "PRODUCTION_WRITE_PERFORMED": True,
        "BACKUP_CREATED": True,
        "prompt": "p206",
        "version_target": "v0.6.58",
        "backup_path": str(backup_path.relative_to(REPO_ROOT)),
        "total_records": total,
        "records_changed": records_changed,
        "disc_additions_total": disc_additions_total,
        "newly_classified": newly_classified,
        "baseline_unclassified": baseline_unclassified,
        "still_unclassified_after": still_unclassified_after,
        "kw_hit_counter": dict(kw_hit_counter.most_common()),
        "discipline_before": dict(baseline_disc_counter),
        "discipline_after": dict(after_disc_counter),
        "accepted_p205_rules": {k: v for k, v in P205_NEW_DISC_KW.items()},
        "deferred_not_applied": [
            "campaña de comunicación", "campanya de comunicació",
            "plan de comunicación", "ia", "ai",
            "inteligencia artificial", "artificial intelligence",
        ],
    }
    _write(TMP_DIR / "reclassify_apply_summary.json", summary)
    _write(TMP_DIR / "reclassified_records.json", changed_sample)

    print("\n_tmp reports written to: _tmp/taxonomy_p206/")
    print("\n" + "=" * 70)
    print("  PRODUCTION_WRITE_PERFORMED: true")
    print("  BACKUP_CREATED: true")
    print("=" * 70)


def _write(path: Path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print("  wrote: %s" % path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
