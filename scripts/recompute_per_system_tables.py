#!/usr/bin/env python3
"""Recompute per-system × {horizon, target_type, domain} VF tables (§5.1).

Reads only cached verdicts + gold metadata; no API calls.

Usage:
  python scripts/recompute_per_system_tables.py
  python scripts/recompute_per_system_tables.py --by horizon
  python scripts/recompute_per_system_tables.py --by target_type
  python scripts/recompute_per_system_tables.py --by domain --topn 10
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"

SYSTEMS_ORDER = [
    "structured_sonnet",
    "long_context_sonnet46", "long_context_mistral",
    "recency_wrapper", "sonnet_extract", "active_state_wrapper",
    "recency_rag", "long_context_llama8b",
    "graphiti", "naive_rag", "graphiti_inv_off",
]

HORIZON_ORDER = ["compact", "standard", "hard"]
TARGET_TYPE_ORDER = ["object_preference", "procedural_constraint",
                     "conceptual_stance", "interpersonal_boundary"]


def load_meta(gold_path: Path) -> dict[str, dict]:
    out = {}
    with open(gold_path) as f:
        for line in f:
            r = json.loads(line)
            md = r.get("_gold", {}).get("metadata", {}) or {}
            out[r["sample_id"]] = {
                "horizon": md.get("horizon"),
                "target_type": md.get("gold_target_type"),
                "domain": md.get("domain"),
            }
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--verdicts",
                   default=str(DATA / "verdicts/phase3_xsystem_opus_verdicts.jsonl"),
                   type=Path)
    p.add_argument("--gold",
                   default=str(DATA / "dataset/realized_phase3_main_full.jsonl"),
                   type=Path)
    p.add_argument("--by", default="horizon",
                   choices=["horizon", "target_type", "domain"])
    p.add_argument("--topn", type=int, default=None,
                   help="For --by domain, only show top-N domains")
    p.add_argument("--csv", type=Path, default=None,
                   help="Write the system × dim VF table to this CSV")
    args = p.parse_args()

    meta = load_meta(args.gold)
    by_sys_dim: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(list))
    overall_by_sys: dict[str, list[int]] = defaultdict(list)
    for line in open(args.verdicts):
        v = json.loads(line)
        sid = v["sample_id"]
        sys = v["system_name"]
        if sid not in meta:
            continue
        dim_val = meta[sid].get(args.by)
        vf = 1 if v.get("vf") in (1, 1.0) else 0
        overall_by_sys[sys].append(vf)
        if dim_val:
            by_sys_dim[sys][dim_val].append(vf)

    # Determine column ordering for the dimension
    if args.by == "horizon":
        cols = HORIZON_ORDER
    elif args.by == "target_type":
        cols = TARGET_TYPE_ORDER
    else:  # domain
        domain_counts: dict[str, int] = defaultdict(int)
        for sys_data in by_sys_dim.values():
            for d, vs in sys_data.items():
                domain_counts[d] += len(vs)
        cols = sorted(domain_counts, key=lambda d: -domain_counts[d])
        if args.topn:
            cols = cols[: args.topn]

    print(f"\nSystem × {args.by}\n")
    header = f"{'System':<28} {'overall':>8}"
    for c in cols:
        short = c[:14]
        header += f" {short:>14}"
    print(header)
    print("-" * len(header))

    for sys in SYSTEMS_ORDER:
        if sys not in overall_by_sys:
            continue
        line = f"{sys:<28} {mean(overall_by_sys[sys])*100:>7.1f}%"
        for c in cols:
            vs = by_sys_dim[sys].get(c, [])
            if vs:
                line += f" {mean(vs)*100:>13.1f}%"
            else:
                line += f" {'-':>14}"
        print(line)

    if args.by == "horizon":
        print("\nΔ(compact → hard):")
        for sys in SYSTEMS_ORDER:
            if sys not in by_sys_dim:
                continue
            c = mean(by_sys_dim[sys].get("compact", [0]))
            h = mean(by_sys_dim[sys].get("hard", [0]))
            print(f"  {sys:<28} {(h-c)*100:>+6.1f}pp")

    if args.csv:
        import csv as _csv
        import sys as _sys_mod
        with open(args.csv, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["system", "dimension_axis", "n_overall", "overall_vf"]
                       + [f"{c}_vf" for c in cols]
                       + [f"{c}_n" for c in cols])
            for system_name in SYSTEMS_ORDER:
                if system_name not in overall_by_sys:
                    continue
                row = [system_name, args.by, len(overall_by_sys[system_name]),
                       round(mean(overall_by_sys[system_name]) * 100, 2)]
                for c in cols:
                    vs = by_sys_dim[system_name].get(c, [])
                    row.append(round(mean(vs) * 100, 2) if vs else None)
                for c in cols:
                    row.append(len(by_sys_dim[system_name].get(c, [])))
                w.writerow(row)
        print(f"\nWrote {args.csv}", file=_sys_mod.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
