#!/usr/bin/env python3
"""Merge 2 primary-annotator + 1 arbiter CSVs from the Failure
Attribution annotation (per outline §5.4) and produce the attribution
distribution report.

Reads:
  - data/failure_attribution_pool/master_pool.jsonl
    (150 pairs + hidden stratification metadata)
  - 2 primary annotator CSVs (annotator_id ∈ {a, b})
  - 1 arbiter CSV (annotator_id = arbiter)

  All CSVs have columns: pair_id, annotator_id, label
  label ∈ {A, B, C}
    A = target-binding failure
    B = current-state-resolution failure
    C = mixed

Adjudication rule:
  - If A_label == B_label   → final_label = that label
  - Else                    → final_label = arbiter_label

Outputs (per outline §5.4 reports):
  - 2-annotator pairwise Cohen's κ (3-class) + raw agreement
  - Pre-registered acceptance: raw ≥ 75%, κ ≥ 0.55
  - Post-arbitration 3-class distribution on full N=150
  - By-pattern decomposition (drift / explicit / multi / narrowing)
  - By-system decomposition (per outline §5.4 mechanism narrative)
  - By-horizon decomposition (compact / standard / hard)

Usage:
  python scripts/merge_failure_attribution.py \\
      --master data/failure_attribution_pool/master_pool.jsonl \\
      --primary failure_attribution_a.csv failure_attribution_b.csv \\
      --arbiter failure_attribution_arbiter.csv \\
      --out data/failure_attribution_pool/failure_attribution_report.md
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

LABELS = ("A", "B", "C")
LABEL_NAMES = {
    "A": "target_resolution",
    "B": "current_state_resolution",
    "C": "mixed",
}


def cohens_kappa_multiclass(a: list[str], b: list[str],
                             classes: tuple[str, ...] = LABELS) -> float:
    """Multi-class Cohen's κ on aligned label lists.

    Uses marginal probabilities for each class.
    """
    if not a:
        return float("nan")
    n = len(a)
    n_agree = sum(1 for x, y in zip(a, b) if x == y)
    p_o = n_agree / n
    p_e = 0.0
    for c in classes:
        p_a = sum(1 for x in a if x == c) / n
        p_b = sum(1 for x in b if x == c) / n
        p_e += p_a * p_b
    if p_e >= 0.999999:
        return 1.0 if p_o == 1.0 else 0.0
    return (p_o - p_e) / (1 - p_e)


def load_master(path: Path) -> dict[str, dict]:
    out = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            out[r["pair_id"]] = r
    return out


def load_csv(path: Path) -> dict[str, str | None]:
    out = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            pid = (row.get("pair_id") or "").strip()
            label = (row.get("label") or "").strip().upper()
            if pid:
                out[pid] = label if label in LABELS else None
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--master",
                   default="data/failure_attribution_pool/master_pool.jsonl",
                   type=Path)
    p.add_argument("--primary", nargs=2, required=True, type=Path,
                   help="two primary annotator CSVs (e.g., a.csv b.csv)")
    p.add_argument("--arbiter", required=True, type=Path,
                   help="arbiter CSV (resolves A-B disagreements)")
    p.add_argument("--out",
                   default="data/failure_attribution_pool/failure_attribution_report.md",
                   type=Path)
    p.add_argument("--final-out",
                   default="data/failure_attribution_pool/final_labels.jsonl",
                   type=Path)
    args = p.parse_args()

    master = load_master(args.master)
    print(f"Master pool: {len(master)} pairs")

    primary = [load_csv(f) for f in args.primary]
    arbiter = load_csv(args.arbiter)
    print(f"  Primary A: {sum(1 for v in primary[0].values() if v)} labelled")
    print(f"  Primary B: {sum(1 for v in primary[1].values() if v)} labelled")
    print(f"  Arbiter:   {sum(1 for v in arbiter.values() if v)} labelled")

    pair_ids = list(master.keys())

    # --- Pairwise primary κ (3-class) + raw agreement ---
    a_labels: list[str] = []
    b_labels: list[str] = []
    eval_pids: list[str] = []
    for pid in pair_ids:
        la = primary[0].get(pid)
        lb = primary[1].get(pid)
        if la is None or lb is None:
            continue
        a_labels.append(la)
        b_labels.append(lb)
        eval_pids.append(pid)
    pairwise_kappa = cohens_kappa_multiclass(a_labels, b_labels)
    pairwise_raw = (sum(1 for x, y in zip(a_labels, b_labels) if x == y)
                    / len(a_labels) if a_labels else float("nan"))

    # --- Adjudication ---
    final_labels: dict[str, str] = {}
    n_agreement = 0
    n_arbitrated = 0
    n_unresolved = 0
    for pid in pair_ids:
        la = primary[0].get(pid)
        lb = primary[1].get(pid)
        if la is None or lb is None:
            continue
        if la == lb:
            final_labels[pid] = la
            n_agreement += 1
        else:
            arb = arbiter.get(pid)
            if arb in LABELS:
                final_labels[pid] = arb
                n_arbitrated += 1
            else:
                n_unresolved += 1

    # --- Distribution: overall + by stratum ---
    def _dist(pids: list[str]) -> dict[str, int]:
        c = Counter()
        for pid in pids:
            if pid in final_labels:
                c[final_labels[pid]] += 1
        return dict(c)

    overall_dist = _dist(list(final_labels.keys()))

    # by pattern
    by_pattern_pids: dict[str, list[str]] = defaultdict(list)
    for pid, rec in master.items():
        pat = rec["_hidden"]["stratification"].get("pattern") or "unknown"
        if pid in final_labels:
            by_pattern_pids[pat].append(pid)

    # by system
    by_system_pids: dict[str, list[str]] = defaultdict(list)
    for pid, rec in master.items():
        if pid in final_labels:
            by_system_pids[rec["system_name"]].append(pid)

    # by horizon
    by_horizon_pids: dict[str, list[str]] = defaultdict(list)
    for pid, rec in master.items():
        h = rec["_hidden"]["stratification"].get("horizon") or "unknown"
        if pid in final_labels:
            by_horizon_pids[h].append(pid)

    # --- Pre-registered acceptance ---
    pass_raw = pairwise_raw == pairwise_raw and pairwise_raw >= 0.75
    pass_kappa = pairwise_kappa == pairwise_kappa and pairwise_kappa >= 0.55

    # --- Build report ---
    out = ["# Failure Attribution report (per outline §5.4)\n\n"]
    out.append(f"Pool size: {len(master)} pairs (vf=0 only)\n")
    out.append(f"Both-primaries-labelled subset: {len(eval_pids)}\n")
    out.append(f"Final adjudicated labels: {len(final_labels)}\n")
    out.append(f"  - primary agreement: {n_agreement}\n")
    out.append(f"  - arbitrated:        {n_arbitrated}\n")
    out.append(f"  - unresolved:        {n_unresolved}\n\n")

    out.append("## 1. Inter-annotator agreement (2 primaries, 3-class)\n\n")
    out.append(f"- Pairwise Cohen's κ: **{pairwise_kappa:.3f}**\n")
    out.append(f"- Raw agreement: **{pairwise_raw*100:.1f}%**\n")
    out.append(f"- N: {len(a_labels)}\n\n")

    out.append("## 2. Pre-registered acceptance thresholds\n\n")
    out.append("| Threshold | Required | Got | Status |\n"
               "|---|---|---|---|\n")
    out.append(f"| Raw agreement | ≥ 75% | "
               f"{pairwise_raw*100:.1f}% | "
               f"{'PASS ✅' if pass_raw else 'FAIL ❌'} |\n")
    out.append(f"| Cohen's κ (3-class) | ≥ 0.55 | "
               f"{pairwise_kappa:.3f} | "
               f"{'PASS ✅' if pass_kappa else 'FAIL ❌'} |\n\n")

    out.append("## 3. Three-class attribution distribution (overall)\n\n")
    total = sum(overall_dist.values())
    out.append("| Class | Label | N | Share |\n|---|---|---:|---:|\n")
    for c in LABELS:
        n = overall_dist.get(c, 0)
        share = (n / total * 100) if total else 0.0
        out.append(f"| {c} | {LABEL_NAMES[c]} | {n} | {share:.1f}% |\n")
    out.append(f"| **Total** | | **{total}** | 100.0% |\n\n")

    def _dist_table(by: dict[str, list[str]], header: str) -> list[str]:
        lines: list[str] = [f"## {header}\n\n"]
        lines.append("| Stratum | N | A target | B current_state | C mixed |\n"
                     "|---|---:|---:|---:|---:|\n")
        for k in sorted(by.keys()):
            pids = by[k]
            d = _dist(pids)
            n = len(pids)
            if n == 0:
                lines.append(f"| {k} | 0 | – | – | – |\n")
                continue
            a_pct = d.get("A", 0) / n * 100
            b_pct = d.get("B", 0) / n * 100
            c_pct = d.get("C", 0) / n * 100
            lines.append(f"| {k} | {n} | {a_pct:.1f}% | {b_pct:.1f}% | "
                         f"{c_pct:.1f}% |\n")
        lines.append("\n")
        return lines

    out += _dist_table(by_pattern_pids,
                        "4. By failure pattern (drift focal cell)")
    out += _dist_table(by_system_pids,
                        "5. By system (mechanism narrative)")
    out += _dist_table(by_horizon_pids,
                        "6. By horizon")

    out.append("## 7. Reading guide\n\n")
    out.append("- **A (target-binding)**: model didn't bind the update to "
               "the right target — likely a retrieval / extraction problem.\n")
    out.append("- **B (current-state-resolution)**: model located the update "
               "but followed the OUTDATED version — a precedence problem.\n")
    out.append("- **C (mixed)**: both broken or response too sparse — "
               "the irreducible attribution-overlap floor.\n\n")
    out.append("Per §5.4, we report this as a *post-hoc qualitative anchor* "
               "for §5.3 and §6 — not as a second main metric.\n")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(out))
    print(f"\nWrote report to {args.out}")

    # Final-label file (audit trail).
    args.final_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.final_out, "w") as f:
        for pid, lab in final_labels.items():
            rec = master[pid]
            f.write(json.dumps({
                "pair_id": pid,
                "sample_id": rec["sample_id"],
                "system_name": rec["system_name"],
                "stratification": rec["_hidden"]["stratification"],
                "primary_a": primary[0].get(pid),
                "primary_b": primary[1].get(pid),
                "arbiter": arbiter.get(pid),
                "final_label": lab,
                "final_label_name": LABEL_NAMES[lab],
            }, ensure_ascii=False) + "\n")
    print(f"Wrote final labels to {args.final_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
