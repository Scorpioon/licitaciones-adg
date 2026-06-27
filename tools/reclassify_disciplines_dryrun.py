#!/usr/bin/env python3
# tools/reclassify_disciplines_dryrun.py
# p205 / v0.6.57 — Discipline classifier coverage dry-run harness.
# Reads data/licitaciones.json, applies current vs proposed DISC_KW rules,
# compares results, and writes bounded _tmp reports.
# PRODUCTION_WRITE_PERFORMED: false

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "licitaciones.json"
TMP_DIR = REPO_ROOT / "_tmp" / "taxonomy_p205"

# ---------------------------------------------------------------------------
# Minimal classifier helpers (stdlib-only; no import of fetch_licitaciones.py)
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


def classify(title, desc, disc_kw):
    full = norm(title + " " + (desc or ""))
    discs = set()
    rule_hits = defaultdict(list)
    for disc, keys in disc_kw.items():
        for k in keys:
            if kw_in(full, k):
                discs.add(disc)
                rule_hits[k].append(disc)
    return sorted(discs), dict(rule_hits)


# ---------------------------------------------------------------------------
# DISC_KW — CURRENT (baseline, copied from fetch_licitaciones.py pre-p205)
# ---------------------------------------------------------------------------
DISC_KW_CURRENT = {
    "branding":    ["branding", "identidad corporativa", "identitat corporativa", "logotipo", "logotip",
                    "logo", "manual de marca", "manual de identidad", "imagen corporativa"],
    "editorial":   ["editorial", "maquetación", "maquetació", "revista", "catálogo", "catàleg",
                    "folleto", "fullet", "cartel", "cartell", "infografía", "memoria anual",
                    "publicación", "publicació", "díptico", "tríptico"],
    "web":         ["diseño web", "disseny web", "página web", "pàgina web", "sitio web", "portal web",
                    "wordpress", "diseño digital"],
    "uxui":        ["ux", "ui", "experiencia de usuario", "usabilidad", "interfaz", "app", "aplicación",
                    "ux/ui", "experiència d'usuari"],
    "publicitat":  ["publicidad", "publicitat", "campaña publicitaria", "campanya publicitària",
                    "marketing", "màrqueting", "promoción", "spot publicitario"],
    "senyaletica": ["señalética", "senyalètica", "rotulación", "retolació", "señalización corporativa",
                    "museografía", "diseño de exposición", "expositores", "señales"],
    "fotografia":  ["fotografía corporativa", "fotografía de producto", "reportaje fotográfico",
                    "fotografía profesional"],
    "audiovisual": ["producción audiovisual", "producció audiovisual", "vídeo corporativo",
                    "motion graphics", "animación gráfica", "spot", "multimedia"],
    "illustracio": ["ilustración", "il·lustració", "ilustración editorial"],
    "impressio":   ["impresión", "impressió", "artes gráficas", "arts gràfiques", "offset", "serigrafía"],
}

# ---------------------------------------------------------------------------
# DISC_KW — PROPOSED (p205 additions annotated)
# ---------------------------------------------------------------------------
DISC_KW_PROPOSED = {
    "branding":    ["branding", "identidad corporativa", "identitat corporativa", "logotipo", "logotip",
                    "logo", "manual de marca", "manual de identidad", "imagen corporativa",
                    # p205: brand identity phrases missing from current rules
                    "identidad visual", "identitat visual"],
    "editorial":   ["editorial", "maquetación", "maquetació", "revista", "catálogo", "catàleg",
                    "folleto", "fullet", "cartel", "cartell", "infografía", "memoria anual",
                    "publicación", "publicació", "díptico", "tríptico",
                    # p205: high-frequency graphic design phrases not previously mapped
                    "diseño gráfico", "disseny gràfic",
                    "comunicación visual", "comunicació visual",
                    "producción gráfica", "producció gràfica",
                    "artes finales"],
    "web":         ["diseño web", "disseny web", "página web", "pàgina web", "sitio web", "portal web",
                    "wordpress", "diseño digital"],
    "uxui":        ["ux", "ui", "experiencia de usuario", "usabilidad", "interfaz", "app", "aplicación",
                    "ux/ui", "experiència d'usuari"],
    "publicitat":  ["publicidad", "publicitat", "campaña publicitaria", "campanya publicitària",
                    "marketing", "màrqueting", "promoción", "spot publicitario",
                    # p205: promotional material (communication-campaign phrases deferred — FP risk)
                    "material promocional", "materiales promocionales"],
    "senyaletica": ["señalética", "senyalètica", "rotulación", "retolació", "señalización corporativa",
                    "museografía", "diseño de exposición", "expositores", "señales"],
    "fotografia":  ["fotografía corporativa", "fotografía de producto", "reportaje fotográfico",
                    "fotografía profesional"],
    "audiovisual": ["producción audiovisual", "producció audiovisual", "vídeo corporativo",
                    "motion graphics", "animación gráfica", "spot", "multimedia"],
    "illustracio": ["ilustración", "il·lustració", "ilustración editorial"],
    "impressio":   ["impresión", "impressió", "artes gráficas", "arts gràfiques", "offset", "serigrafía",
                    # p205: large-format printing
                    "impresión gran formato", "impressió gran format"],
}

# Rules added in p205 (for rule_hits report)
P205_NEW_RULES = {
    "identidad visual", "identitat visual",
    "diseño gráfico", "disseny gràfic",
    "comunicación visual", "comunicació visual",
    "producción gráfica", "producció gràfica",
    "artes finales",
    "material promocional", "materiales promocionales",
    "impresión gran formato", "impressió gran format",
}

# Rules with known false-positive risk — accepted in p205
FP_RISK_RULES = {
    "diseño gráfico": "broad phrase; can appear in mixed/multi-lot contracts",
}

# Deferred candidates — NOT included in p205; require manual review before adding
DEFERRED_CANDIDATES = {
    "campaña de comunicación": (
        "dry-run found waste-management contract classified as publicitat via this phrase; "
        "comms campaigns appear as sub-components of non-design contracts"
    ),
    "campanya de comunicació": "Catalan equivalent of deferred 'campaña de comunicación'",
    "plan de comunicación": "102 unclassified hits but too generic; appears in non-design institutional contracts",
}


def main():
    print("=" * 70)
    print("  ADG OPS — Discipline Classifier Dry-Run (p205 / v0.6.57)")
    print("  PRODUCTION_WRITE_PERFORMED: false")
    print("=" * 70)

    if not DATA_FILE.exists():
        sys.exit(f"ERROR: data file not found: {DATA_FILE}")

    with open(DATA_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    items = raw.get("data", [])
    total = len(items)
    print(f"\nRecords loaded: {total}")

    # -----------------------------------------------------------------------
    # Run both classifiers
    # -----------------------------------------------------------------------
    results = []
    rule_hits_counter_new = Counter()

    for it in items:
        iid = it.get("id", "")
        titol = it.get("titol", "") or ""
        desc = it.get("descripcio", "") or ""
        current_discs = sorted(it.get("disciplines", []) or [])

        cur_proposed, hits = classify(titol, desc, DISC_KW_PROPOSED)

        # Track only p205 new rule hits
        for rule, discs in hits.items():
            if rule in P205_NEW_RULES:
                rule_hits_counter_new[rule] += 1

        results.append({
            "id": iid,
            "titol": titol,
            "current": current_discs,
            "proposed": cur_proposed,
        })

    # -----------------------------------------------------------------------
    # Categorise
    # NOTE: this harness classifies from stored `titol` only — stored records
    # lack `descripcio` in the JSON (description was only available at fetch
    # time).  As a result:
    #   - "gained_discipline" (current → proposed adds new tag) is reliable.
    #   - "lost_discipline" (current had tag → harness doesn't see it) is a
    #     harness artefact, NOT a real regression; those tags survive in data.
    #   - "newly_classified" (0 → N disciplines) is fully reliable.
    # p206 must re-classify using the full score_item() path, not this harness.
    # -----------------------------------------------------------------------
    unchanged = []
    newly_classified = []        # current=[], proposed≠[]
    gained_discipline = []       # current≠[], proposed is superset
    changed_discipline = []      # current≠[], proposed differs (not strict superset)
    lost_discipline = []         # current≠[], proposed=[] — harness artefact
    still_unclassified = []

    for r in results:
        cur = set(r["current"])
        prop = set(r["proposed"])
        if cur == prop:
            unchanged.append(r)
        elif not cur and prop:
            newly_classified.append(r)
        elif cur and not prop:
            lost_discipline.append(r)
        elif prop > cur:
            gained_discipline.append(r)
        else:
            changed_discipline.append(r)
        if not prop:
            still_unclassified.append(r)

    current_unclassified_count = sum(1 for r in results if not r["current"])
    proposed_unclassified_count = len(still_unclassified)

    # -----------------------------------------------------------------------
    # Console report
    # -----------------------------------------------------------------------
    print("\n--- COUNTS ---")
    print(f"  Total records:           {total}")
    print(f"  Current unclassified:    {current_unclassified_count}")
    print(f"  Proposed unclassified:   {proposed_unclassified_count}  (title-only; see NOTE)")
    print(f"  Newly classified:        {len(newly_classified)}  (was empty -> gets discipline)")
    print(f"  Gained discipline:       {len(gained_discipline)}  (existing + new tag added)")
    print(f"  Changed discipline:      {len(changed_discipline)}")
    print(f"  Lost discipline:         {len(lost_discipline)}  (harness artefact: title-only gap)")
    print(f"  Unchanged:               {len(unchanged)}")
    print(f"  NOTE: 'lost' are harness artefacts; actual data disciplines are preserved.")

    print("\n--- TOP P205 NEW RULE HITS ---")
    for rule, cnt in rule_hits_counter_new.most_common(20):
        risk = " [FP-RISK]" if rule in FP_RISK_RULES else ""
        print(f"  [{cnt:4d}] {rule}{risk}")

    print("\n--- TOP NEWLY ASSIGNED DISCIPLINES ---")
    new_disc_counter = Counter()
    for r in newly_classified:
        for d in r["proposed"]:
            new_disc_counter[d] += 1
    for disc, cnt in new_disc_counter.most_common():
        print(f"  {disc}: {cnt}")

    print("\n--- SAMPLE NEWLY CLASSIFIED (first 10) ---")
    for r in newly_classified[:10]:
        print(f"  [{','.join(r['proposed'])}] {r['titol'][:90]}")

    print("\n--- SAMPLE STILL UNCLASSIFIED (first 10) ---")
    for r in still_unclassified[:10]:
        print(f"  {r['titol'][:90]}")

    print("\n--- FALSE-POSITIVE RISK NOTES (accepted p205 rules) ---")
    for rule, reason in FP_RISK_RULES.items():
        cnt = rule_hits_counter_new.get(rule, 0)
        print(f"  [{cnt} hits] '{rule}': {reason}")

    print("\n--- DEFERRED CANDIDATES (not in p205 — require manual review) ---")
    for rule, reason in DEFERRED_CANDIDATES.items():
        print(f"  '{rule}': {reason}")

    # -----------------------------------------------------------------------
    # Write _tmp reports
    # -----------------------------------------------------------------------
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "PRODUCTION_WRITE_PERFORMED": False,
        "prompt": "p205",
        "version_target": "v0.6.57",
        "harness_note": "title-only re-classification; lost_discipline is a harness artefact",
        "total_records": total,
        "current_unclassified": current_unclassified_count,
        "proposed_unclassified": proposed_unclassified_count,
        "newly_classified": len(newly_classified),
        "gained_discipline": len(gained_discipline),
        "changed_discipline": len(changed_discipline),
        "lost_discipline_harness_artefact": len(lost_discipline),
        "unchanged": len(unchanged),
        "top_new_rule_hits": rule_hits_counter_new.most_common(20),
        "top_newly_assigned_disciplines": new_disc_counter.most_common(),
        "fp_risk_rules": FP_RISK_RULES,
        "deferred_candidates": {k: v for k, v in DEFERRED_CANDIDATES.items()},
    }
    _write(TMP_DIR / "reclassify_summary.json", summary)

    newly_sample = [
        {"id": r["id"], "titol": r["titol"], "current": r["current"], "proposed": r["proposed"]}
        for r in newly_classified[:100]
    ]
    _write(TMP_DIR / "newly_classified_sample.json", newly_sample)

    still_sample = [
        {"id": r["id"], "titol": r["titol"]}
        for r in still_unclassified[:100]
    ]
    _write(TMP_DIR / "still_unclassified_sample.json", still_sample)

    rule_hits_report = {
        "p205_new_rules": sorted(P205_NEW_RULES),
        "hits_by_rule": dict(rule_hits_counter_new.most_common()),
        "fp_risk_rules": FP_RISK_RULES,
        "deferred_candidates": {k: v for k, v in DEFERRED_CANDIDATES.items()},
    }
    _write(TMP_DIR / "rule_hits.json", rule_hits_report)

    print(f"\n_tmp reports written to: {TMP_DIR}")
    print("\n" + "=" * 70)
    print("  PRODUCTION_WRITE_PERFORMED: false")
    print("=" * 70)


def _write(path: Path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"  wrote: {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
