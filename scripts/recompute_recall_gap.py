#!/usr/bin/env python3
"""Recompute Recall + Recall-VF gap per-system (overall, drift, non-drift).

Reproduces the Recall-VF gap table from §5.1 — supports the paper's
"recall does not equal behavioral supersession" framing.

Reads only cached verdicts + gold metadata; no API calls.

Usage:
  python scripts/recompute_recall_gap.py
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
    p.add_argument("--csv", type=Path, default=None,
                   help="Write per-system Recall + VF + gap to this CSV")
    args = p.parse_args()

    pat_map = load_pattern_map(args.gold)

    # Per-system aggregates
    overall_v = defaultdict(lambda: {"vf": [], "rec": []})
    drift_v = defaultdict(lambda: {"vf": [], "rec": []})
    nondrift_v = defaultdict(lambda: {"vf": [], "rec": []})

    for line in open(args.verdicts):
        v = json.loads(line)
        sid = v["sample_id"]
        sys = v["system_name"]
        pat = pat_map.get(sid)
        if not pat:
            continue
        vf = 1 if v.get("vf") in (1, 1.0) else 0
        rec = v.get("recall")
        overall_v[sys]["vf"].append(vf)
        if rec is not None:
            overall_v[sys]["rec"].append(rec)
        if pat == "implicit_drift":
            drift_v[sys]["vf"].append(vf)
            if rec is not None:
                drift_v[sys]["rec"].append(rec)
        else:
            nondrift_v[sys]["vf"].append(vf)
            if rec is not None:
                nondrift_v[sys]["rec"].append(rec)

    def fmt(d: dict, sys: str, key: str) -> str:
        vs = d[sys].get(key, [])
        return f"{mean(vs)*100:>6.1f}%" if vs else f"{'-':>7}"

    def fmt_gap(d: dict, sys: str) -> str:
        if d[sys]["vf"] and d[sys]["rec"]:
            gap = mean(d[sys]["rec"]) * 100 - mean(d[sys]["vf"]) * 100
            return f"{gap:>+6.1f}"
        return f"{'-':>7}"

    print(f"\nRecall + VF + Recall-VF gap per system\n")
    print(f"{'System':<28}  Recall_O   VF_O  Gap_O |"
          f"  Rec_d   VF_d  Gap_d |"
          f" Rec_nd  VF_nd Gap_nd")
    print("-" * 96)
    for sys in SYSTEMS_ORDER:
        if sys not in overall_v:
            continue
        line = f"{sys:<28} "
        line += f" {fmt(overall_v, sys, 'rec')} {fmt(overall_v, sys, 'vf')} "
        line += f"{fmt_gap(overall_v, sys)} | "
        line += f"{fmt(drift_v, sys, 'rec')} {fmt(drift_v, sys, 'vf')} "
        line += f"{fmt_gap(drift_v, sys)} | "
        line += f"{fmt(nondrift_v, sys, 'rec')} {fmt(nondrift_v, sys, 'vf')} "
        line += f"{fmt_gap(nondrift_v, sys)}"
        print(line)

    print("\nReading:")
    print("  • structured_sonnet uniquely closes the gap (overall +0.8pp)")
    print("  • Frontier long-context: high recall, drift VF still low")
    print("  • Drift gap is dominant signal across all systems")

    if args.csv:
        import csv as _csv
        with open(args.csv, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["system", "recall_overall", "vf_overall", "gap_overall",
                        "recall_drift", "vf_drift", "gap_drift",
                        "recall_nondrift", "vf_nondrift", "gap_nondrift",
                        "n_overall", "n_drift", "n_nondrift"])
            def _v(d, sys, key):
                vs = d[sys].get(key, [])
                return round(mean(vs) * 100, 2) if vs else None
            def _g(d, sys):
                if d[sys]["vf"] and d[sys]["rec"]:
                    return round(mean(d[sys]["rec"]) * 100 - mean(d[sys]["vf"]) * 100, 2)
                return None
            for sys in SYSTEMS_ORDER:
                if sys not in overall_v:
                    continue
                w.writerow([
                    sys,
                    _v(overall_v, sys, "rec"), _v(overall_v, sys, "vf"), _g(overall_v, sys),
                    _v(drift_v, sys, "rec"), _v(drift_v, sys, "vf"), _g(drift_v, sys),
                    _v(nondrift_v, sys, "rec"), _v(nondrift_v, sys, "vf"), _g(nondrift_v, sys),
                    len(overall_v[sys]["vf"]), len(drift_v[sys]["vf"]), len(nondrift_v[sys]["vf"]),
                ])
        print(f"\nWrote {args.csv}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
