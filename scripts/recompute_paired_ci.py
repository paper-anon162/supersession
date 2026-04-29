#!/usr/bin/env python3
"""Recompute paired bootstrap 95% CIs for headline comparisons (§5.1).

Reproduces the 8 CI rows in outline §5.1 from cached verdicts.
No API calls. Default 2000 bootstrap resamples.

Usage:
  python scripts/recompute_paired_ci.py
  python scripts/recompute_paired_ci.py --n-boot 10000
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"


def load_pattern_map(gold_path: Path) -> dict[str, str]:
    out = {}
    with open(gold_path) as f:
        for line in f:
            r = json.loads(line)
            md = r.get("_gold", {}).get("metadata", {}) or {}
            fps = md.get("failure_patterns") or ["unknown"]
            out[r["sample_id"]] = fps[0]
    return out


def paired_diff(sys_a_vf: dict, sys_b_vf: dict, sids: list[str],
                n_boot: int, seed: int) -> tuple[float, float, float, int]:
    pairs = [(sys_a_vf[s], sys_b_vf[s]) for s in sids
             if s in sys_a_vf and s in sys_b_vf]
    if not pairs:
        return float("nan"), float("nan"), float("nan"), 0
    n = len(pairs)
    pt = sum(p[0] - p[1] for p in pairs) / n
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        idxs = [rng.randrange(n) for _ in range(n)]
        a = sum(pairs[i][0] for i in idxs) / n
        b = sum(pairs[i][1] for i in idxs) / n
        boots.append(a - b)
    boots.sort()
    return pt, boots[int(n_boot * 0.025)], boots[int(n_boot * 0.975)], n


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--verdicts",
                   default=str(DATA / "verdicts/phase3_xsystem_opus_verdicts.jsonl"),
                   type=Path)
    p.add_argument("--gold",
                   default=str(DATA / "dataset/realized_phase3_main_full.jsonl"),
                   type=Path)
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--csv", type=Path, default=None,
                   help="Write headline + DiD rows to this CSV")
    args = p.parse_args()

    pat_map = load_pattern_map(args.gold)
    sys_vf: dict[str, dict[str, int]] = defaultdict(dict)
    for line in open(args.verdicts):
        v = json.loads(line)
        sys_vf[v["system_name"]][v["sample_id"]] = (
            1 if v.get("vf") in (1, 1.0) else 0
        )

    all_sids = sorted(pat_map.keys())
    drift = [s for s in all_sids if pat_map.get(s) == "implicit_drift"]
    non_drift = [s for s in all_sids
                 if pat_map.get(s) and pat_map.get(s) != "implicit_drift"]

    comparisons = [
        ("structured_sonnet", "long_context_sonnet46", "overall", all_sids),
        ("structured_sonnet", "long_context_sonnet46", "drift", drift),
        ("sonnet_extract", "long_context_llama8b", "drift", drift),
        ("structured_sonnet", "long_context_sonnet46", "non-drift", non_drift),
        ("graphiti", "graphiti_inv_off", "drift", drift),
        ("graphiti", "graphiti_inv_off", "overall", all_sids),
        ("graphiti", "long_context_sonnet46", "drift", drift),
    ]

    print(f"Paired bootstrap 95% CI (n_boot={args.n_boot})\n")
    print(f"{'Comparison':<55} {'Δ':>9} {'95% CI':>22} {'N':>5}")
    print("-" * 92)
    rows: list[dict] = []
    for a, b, slice_name, sids in comparisons:
        pt, lo, hi, n = paired_diff(sys_vf[a], sys_vf[b], sids,
                                     args.n_boot, args.seed)
        ci_excl_zero = "✅" if (lo > 0 or hi < 0) else "  "
        label = f"{a} − {b} ({slice_name})"
        print(f"{label[:54]:<55} {pt*100:>+8.1f}pp "
              f"[{lo*100:>+5.1f}, {hi*100:>+5.1f}] {n:>5} {ci_excl_zero}")
        rows.append({
            "comparison": f"{a} - {b}",
            "slice": slice_name,
            "delta_vf_pp": round(pt * 100, 2),
            "ci_lo_pp": round(lo * 100, 2),
            "ci_hi_pp": round(hi * 100, 2),
            "n": n,
            "ci_excludes_zero": (lo > 0 or hi < 0),
        })

    # Diff-in-diff for backbone-invariance
    print()
    print("Difference-in-differences (backbone-invariance check):")
    rng = random.Random(args.seed)
    dd_boots = []
    for _ in range(args.n_boot):
        idxs = [rng.randrange(len(drift)) for _ in range(len(drift))]
        sids_b = [drift[i] for i in idxs]
        a1 = sum(sys_vf["structured_sonnet"].get(s, 0) for s in sids_b) / len(sids_b)
        a2 = sum(sys_vf["long_context_sonnet46"].get(s, 0) for s in sids_b) / len(sids_b)
        a3 = sum(sys_vf["sonnet_extract"].get(s, 0) for s in sids_b) / len(sids_b)
        a4 = sum(sys_vf["long_context_llama8b"].get(s, 0) for s in sids_b) / len(sids_b)
        dd_boots.append((a1 - a2) - (a3 - a4))
    dd_boots.sort()
    pt_dd = ((sum(sys_vf["structured_sonnet"].get(s, 0) for s in drift) / len(drift))
             - (sum(sys_vf["long_context_sonnet46"].get(s, 0) for s in drift) / len(drift))
             - (sum(sys_vf["sonnet_extract"].get(s, 0) for s in drift) / len(drift))
             + (sum(sys_vf["long_context_llama8b"].get(s, 0) for s in drift) / len(drift)))
    lo, hi = dd_boots[int(args.n_boot * 0.025)], dd_boots[int(args.n_boot * 0.975)]
    print(f"  (Sonnet pair) − (Llama pair) drift = "
          f"{pt_dd*100:>+5.1f}pp [{lo*100:>+5.1f}, {hi*100:>+5.1f}] {len(drift)}")
    if lo < 0 < hi:
        print("  → CI includes 0:architectural lift is backbone-invariant ✅")
    rows.append({
        "comparison": "(Sonnet pair) - (Llama pair) DiD",
        "slice": "drift",
        "delta_vf_pp": round(pt_dd * 100, 2),
        "ci_lo_pp": round(lo * 100, 2),
        "ci_hi_pp": round(hi * 100, 2),
        "n": len(drift),
        "ci_excludes_zero": (lo > 0 or hi < 0),
    })

    if args.csv:
        import csv as _csv
        with open(args.csv, "w", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nWrote {args.csv}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
