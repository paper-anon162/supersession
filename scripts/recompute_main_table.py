#!/usr/bin/env python3
"""Recompute the Phase 3 main results table (11 systems × overall + per-pattern VF).

Produces the headline table used in §5.1 of the paper. Reads only:
  - data/verdicts/phase3_xsystem_opus_verdicts.jsonl (10988 verdicts)
  - data/dataset/realized_phase3_main_full.jsonl (1000 samples; gold metadata)

No API calls; runs in seconds.

Usage:
  python scripts/recompute_main_table.py
  python scripts/recompute_main_table.py --markdown    # paper-ready md
  python scripts/recompute_main_table.py --csv out.csv # for further analysis
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"

PATTERNS = ["implicit_drift", "explicit_replacement",
            "multi_version", "narrowing"]
SYSTEMS_ORDER = [
    "structured_sonnet",
    "long_context_sonnet46", "long_context_mistral",
    "recency_wrapper", "sonnet_extract", "active_state_wrapper",
    "recency_rag", "long_context_llama8b",
    "graphiti", "naive_rag", "graphiti_inv_off",
]


def load_pattern_map(gold_path: Path) -> dict[str, str]:
    out = {}
    with open(gold_path) as f:
        for line in f:
            r = json.loads(line)
            md = r.get("_gold", {}).get("metadata", {}) or {}
            fps = md.get("failure_patterns") or ["unknown"]
            out[r["sample_id"]] = fps[0]
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--verdicts",
                   default=str(DATA / "verdicts/phase3_xsystem_opus_verdicts.jsonl"),
                   type=Path)
    p.add_argument("--gold",
                   default=str(DATA / "dataset/realized_phase3_main_full.jsonl"),
                   type=Path)
    p.add_argument("--markdown", action="store_true",
                   help="Paper-ready markdown table")
    p.add_argument("--csv", type=Path,
                   help="CSV output (for further analysis)")
    args = p.parse_args()

    pat_map = load_pattern_map(args.gold)
    by_sys_pat = defaultdict(lambda: defaultdict(list))
    for line in open(args.verdicts):
        v = json.loads(line)
        sid = v["sample_id"]
        sys = v["system_name"]
        pat = pat_map.get(sid)
        vf = 1 if v.get("vf") in (1, 1.0) else 0
        if pat:
            by_sys_pat[sys][pat].append(vf)

    rows = []
    for sys in SYSTEMS_ORDER:
        if sys not in by_sys_pat:
            continue
        all_vfs = [v for p in PATTERNS for v in by_sys_pat[sys].get(p, [])]
        n = len(all_vfs)
        overall = mean(all_vfs) * 100 if all_vfs else 0
        row = [sys, n, overall]
        for p in PATTERNS:
            vs = by_sys_pat[sys].get(p, [])
            row.append(mean(vs) * 100 if vs else float("nan"))
        rows.append(row)

    if args.markdown:
        print("| Rank | System | N | drift | explicit | multi | narrow | overall |")
        print("|---|---|---:|---:|---:|---:|---:|---:|")
        rows_sorted = sorted(rows, key=lambda r: -r[2])
        for i, (sys, n, overall, *pat_vals) in enumerate(rows_sorted, 1):
            d, e, m, nr = pat_vals
            print(f"| {i} | {sys} | {n} | "
                  f"{d:.1f}% | {e:.1f}% | {m:.1f}% | {nr:.1f}% | "
                  f"**{overall:.1f}%** |")
    else:
        print(f"{'System':<28} {'N':>5} {'overall':>9} {'drift':>9} "
              f"{'explicit':>9} {'multi':>9} {'narrow':>9}")
        for sys, n, overall, *pat_vals in sorted(rows, key=lambda r: -r[2]):
            line = f"{sys:<28} {n:>5} {overall:>8.1f}%"
            for v in pat_vals:
                line += f" {v:>8.1f}%" if v == v else f" {'-':>9}"  # NaN check
            print(line)

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["system", "n", "overall_vf",
                        "drift_vf", "explicit_vf", "multi_vf", "narrow_vf"])
            for row in rows:
                w.writerow(row)
        print(f"\nWrote {args.csv}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
