#!/usr/bin/env python3
"""Paired-bootstrap CIs on horizon transitions using matched triples.

The Phase 3 manifest ships 350 matched groups: 301 triples (compact +
standard + hard from the same skeleton) + 49 doublets (compact +
standard or compact + hard). For each system, we compute the
within-group VF differences along compact→standard, standard→hard, and
compact→hard transitions, then paired-bootstrap (n=2000, seed=42) over
matched triples / doublets to produce 95% CIs on each transition.

This is what the matched-triples manifest design is for; without it,
horizon Δ confounds horizon length with skeleton-level difficulty.

Reads only cached verdicts + manifest. No API calls.

Usage:
  python scripts/recompute_horizon_paired.py
  python scripts/recompute_horizon_paired.py --csv data/paper/horizon_paired_ci.csv
"""

from __future__ import annotations

import argparse
import csv as _csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"

SYSTEMS_ORDER = [
    "structured_sonnet", "long_context_sonnet46", "long_context_mistral",
    "recency_wrapper", "sonnet_extract", "active_state_wrapper",
    "recency_rag", "long_context_llama8b", "graphiti", "naive_rag",
    "graphiti_inv_off",
]

TRANSITIONS = [
    ("compact", "standard"),
    ("standard", "hard"),
    ("compact", "hard"),
]


def load_groups(manifest_path: Path) -> list[dict]:
    """Return list of groups from manifest, each with member sample_ids
    keyed by horizon."""
    m = json.loads(manifest_path.read_text())
    out = []
    for g in m.get("groups", []):
        members_by_h: dict[str, str] = {}
        for mem in g.get("members", []):
            sid = mem["sample_id"]
            # Member metadata records horizon directly; if not, fall back
            # to parsing from sample_id (...-compact / -standard / -hard).
            horizon = mem.get("horizon")
            if not horizon:
                for h in ("compact", "standard", "hard"):
                    if sid.endswith(f"-{h}"):
                        horizon = h
                        break
            if horizon:
                members_by_h[horizon] = sid
        if members_by_h:
            out.append(members_by_h)
    return out


def load_vf(verdicts_path: Path) -> dict[tuple[str, str], int]:
    out = {}
    with open(verdicts_path) as f:
        for line in f:
            v = json.loads(line)
            out[(v["sample_id"], v["system_name"])] = (
                1 if v.get("vf") in (1, 1.0) else 0)
    return out


def paired_diff_within_group(groups: list[dict], h_from: str, h_to: str,
                              sys_name: str, vf: dict,
                              n_boot: int, seed: int) -> tuple:
    """Paired bootstrap of VF(h_to) - VF(h_from) within matched groups."""
    pairs: list[tuple[int, int]] = []
    for g in groups:
        if h_from in g and h_to in g:
            sid_a = g[h_from]
            sid_b = g[h_to]
            if (sid_a, sys_name) in vf and (sid_b, sys_name) in vf:
                pairs.append((vf[(sid_a, sys_name)], vf[(sid_b, sys_name)]))
    if not pairs:
        return float("nan"), float("nan"), float("nan"), 0
    n = len(pairs)
    pt = sum(p[1] - p[0] for p in pairs) / n  # h_to - h_from
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        idxs = [rng.randrange(n) for _ in range(n)]
        a = sum(pairs[i][0] for i in idxs) / n
        b = sum(pairs[i][1] for i in idxs) / n
        boots.append(b - a)
    boots.sort()
    return pt, boots[int(n_boot * 0.025)], boots[int(n_boot * 0.975)], n


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest",
                   default=str(DATA / "manifests" / "phase3_main.json"),
                   type=Path)
    p.add_argument("--verdicts",
                   default=str(DATA / "verdicts/phase3_xsystem_opus_verdicts.jsonl"),
                   type=Path)
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--csv", type=Path, default=None,
                   help="Write the per-system × transition CI table to CSV")
    args = p.parse_args()

    groups = load_groups(args.manifest)
    triples = sum(1 for g in groups if all(h in g for h in ("compact", "standard", "hard")))
    print(f"Loaded {len(groups)} matched groups ({triples} triples + "
          f"{len(groups) - triples} doublets)\n")

    vf = load_vf(args.verdicts)

    # Header
    print(f"{'System':<28} | {'compact→standard':>22} {'N':>4} | "
          f"{'standard→hard':>22} {'N':>4} | "
          f"{'compact→hard':>22} {'N':>4}")
    print("-" * 120)

    rows: list[list] = []
    for sys_name in SYSTEMS_ORDER:
        if (any(g.get("compact") and (g["compact"], sys_name) in vf for g in groups)) is False:
            continue
        line = f"{sys_name:<28} |"
        row = [sys_name]
        for h_from, h_to in TRANSITIONS:
            pt, lo, hi, n = paired_diff_within_group(
                groups, h_from, h_to, sys_name, vf, args.n_boot, args.seed)
            if n == 0:
                line += f" {'—':>22} {0:>4} |"
                row += [None, None, None, 0]
                continue
            ci_excl = "✅" if (lo > 0 or hi < 0) else "  "
            line += (f" {pt*100:>+5.1f}pp [{lo*100:>+5.1f},"
                     f"{hi*100:>+5.1f}]{ci_excl} {n:>4} |")
            row += [round(pt * 100, 2), round(lo * 100, 2),
                    round(hi * 100, 2), n]
        print(line)
        rows.append(row)

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="") as f:
            w = _csv.writer(f)
            header = ["system"]
            for h_from, h_to in TRANSITIONS:
                tag = f"{h_from}_to_{h_to}"
                header += [f"{tag}_delta_pp", f"{tag}_ci_lo_pp",
                           f"{tag}_ci_hi_pp", f"{tag}_n"]
            w.writerow(header)
            w.writerows(rows)
        import sys as _smod
        print(f"\nWrote {args.csv}", file=_smod.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
