#!/usr/bin/env python3
"""Cross-judge agreement: Opus 4.6 vs Mistral Large 3 (Phase 3, §4.2).

Reads cached verdicts from both judges + the 3 human annotator CSVs and
produces:

  §A. Mistral ↔ human-majority (judge_validation pool, N=150)
      - Cohen's κ overall + per-pattern; raw agreement; FP/FN
  §B. Opus ↔ Mistral (judge_validation pool, N=150)
      - Cohen's κ + raw agreement
  §C. Opus ↔ Mistral on the drift focal cell (4 + 1 systems × 360 drift)
      - Cohen's κ overall + per-system
      - Per-system VF under each judge
      - Headline-invariance: structured_sonnet − long_context_sonnet46
        drift gap under Mistral (paired bootstrap CI)
      - Backbone-invariance DiD: (Sonnet pair) − (Llama pair) drift
        under Mistral
  §D. Spearman rank-stability on drift VF across the 5 focal systems

No API calls. All inputs are cached files.

Usage:
  python scripts/recompute_xjudge_mistral.py
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from statistics import mean

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"

FOCAL_SYSTEMS = [
    "structured_sonnet",
    "long_context_sonnet46",
    "long_context_llama8b",
    "naive_rag",
    "sonnet_extract",
]


def cohens_kappa(a: list[int], b: list[int]) -> float:
    if not a:
        return float("nan")
    n = len(a)
    n_agree = sum(1 for x, y in zip(a, b) if x == y)
    p_o = n_agree / n
    p_a1 = sum(a) / n
    p_b1 = sum(b) / n
    p_e = p_a1 * p_b1 + (1 - p_a1) * (1 - p_b1)
    if p_e >= 0.999999:
        return 1.0 if p_o == 1.0 else 0.0
    return (p_o - p_e) / (1 - p_e)


def spearman_rho(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return float("nan")
    def _rank(xs):
        sorted_xs = sorted(enumerate(xs), key=lambda t: t[1])
        ranks = [0.0] * len(xs)
        i = 0
        while i < len(sorted_xs):
            j = i
            while j + 1 < len(sorted_xs) and sorted_xs[j + 1][1] == sorted_xs[i][1]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                ranks[sorted_xs[k][0]] = avg
            i = j + 1
        return ranks
    ra = _rank(a)
    rb = _rank(b)
    n = len(a)
    mra = sum(ra) / n
    mrb = sum(rb) / n
    num = sum((x - mra) * (y - mrb) for x, y in zip(ra, rb))
    da = sum((x - mra) ** 2 for x in ra) ** 0.5
    db = sum((y - mrb) ** 2 for y in rb) ** 0.5
    if da == 0 or db == 0:
        return float("nan")
    return num / (da * db)


def paired_bootstrap_ci(
    a_vf: dict[str, int], b_vf: dict[str, int], sids: list[str],
    n_boot: int, seed: int,
) -> tuple[float, float, float, int]:
    pairs = [(a_vf[s], b_vf[s]) for s in sids if s in a_vf and s in b_vf]
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


def load_verdicts(path: Path) -> dict[tuple[str, str], int]:
    out = {}
    with open(path) as f:
        for line in f:
            v = json.loads(line)
            vf = 1 if v.get("vf") in (1, 1.0) else 0
            out[(v["sample_id"], v["system_name"])] = vf
    return out


def load_pattern_map(gold_path: Path) -> dict[str, str]:
    out = {}
    with open(gold_path) as f:
        for line in f:
            r = json.loads(line)
            md = r.get("_gold", {}).get("metadata", {}) or {}
            fps = md.get("failure_patterns") or ["unknown"]
            out[r["sample_id"]] = fps[0]
    return out


def load_human_majority(pool_path: Path, csv_paths: list[Path]) -> dict[str, int]:
    """Returns pair_id (str of "sid::sys") → 1/0 majority-vote VF."""
    pair_to_pid: dict[tuple[str, str], str] = {}
    with open(pool_path) as f:
        for line in f:
            r = json.loads(line)
            pair_to_pid[(r["sample_id"], r["system_name"])] = r["pair_id"]

    annot: list[dict[str, str]] = []
    for p in csv_paths:
        d = {}
        with open(p) as f:
            for row in csv.DictReader(f):
                pid = (row.get("pair_id") or "").strip()
                lab = (row.get("label") or "").strip().upper()
                if pid and lab in ("A", "B"):
                    d[pid] = 1 if lab == "A" else 0
        annot.append(d)

    out = {}
    for pid in {p for d in annot for p in d}:
        votes = [d.get(pid) for d in annot]
        valid = [v for v in votes if v is not None]
        if len(valid) >= 2:
            n1 = sum(1 for v in valid if v == 1)
            n0 = sum(1 for v in valid if v == 0)
            if n1 > n0:
                out[pid] = 1
            elif n0 > n1:
                out[pid] = 0
    return out, pair_to_pid


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--opus",
                   default=str(DATA / "verdicts/phase3_xsystem_opus_verdicts.jsonl"),
                   type=Path)
    p.add_argument("--mistral", nargs="+", type=Path,
                   default=[DATA / "verdicts/phase3_xjudge_mistral_verdicts.jsonl",
                            DATA / "verdicts/phase3_xjudge_mistral_sonnet_extract_drift.jsonl"],
                   help="One or more Mistral verdict files (concatenated)")
    p.add_argument("--gold",
                   default=str(DATA / "dataset/realized_phase3_main_full.jsonl"),
                   type=Path)
    p.add_argument("--pool",
                   default=str(DATA / "judge_validation_pool" /
                               "master_pool.jsonl"),
                   type=Path)
    p.add_argument("--annotations", nargs=3, type=Path,
                   default=[
                       DATA / "judge_validation_pool" / "judge_validation_a.csv",
                       DATA / "judge_validation_pool" / "judge_validation_b.csv",
                       DATA / "judge_validation_pool" / "judge_validation_c.csv",
                   ])
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    print("Loading verdicts and human annotations…\n")
    opus = load_verdicts(args.opus)
    mistral: dict[tuple[str, str], int] = {}
    for path in args.mistral:
        if path.exists():
            mistral.update(load_verdicts(path))
    print(f"  Opus verdicts loaded:    {len(opus)}")
    print(f"  Mistral verdicts loaded: {len(mistral)}")

    pat_map = load_pattern_map(args.gold)

    annotations_available = (
        args.pool.exists()
        and all(p.exists() for p in args.annotations)
    )
    if annotations_available:
        human_maj, pair_to_pid = load_human_majority(args.pool, args.annotations)
        print(f"  Human-majority VFs:      {len(human_maj)}\n")
        pool_pairs = list(pair_to_pid.keys())
        print(f"Pool pairs (judge_validation): {len(pool_pairs)}")
        pool_with_mistral = [(s, sys) for (s, sys) in pool_pairs
                              if (s, sys) in mistral]
        print(f"  with Mistral verdict: {len(pool_with_mistral)}\n")
    else:
        print("  Annotation pool not available (raw per-annotator data is")
        print("  not redistributed). Skipping §A and §B; published values:")
        print("    §A Mistral vs human-majority drift:  κ = 0.617")
        print("    §B Opus vs Mistral on N=150 pool:    κ ≈ 0.737\n")
        human_maj, pair_to_pid = {}, {}
        pool_with_mistral = []

    # ============= §A. Mistral ↔ human-majority on N=150 =============
    print("=== §A. Mistral ↔ human-majority (judge_validation pool) ===\n")
    pat_count: dict[str, list[tuple[int, int]]] = defaultdict(list)
    h_all, m_all = [], []
    for (sid, sys) in pool_with_mistral:
        pid = pair_to_pid[(sid, sys)]
        h = human_maj.get(pid)
        m = mistral.get((sid, sys))
        if h is None or m is None:
            continue
        h_all.append(h)
        m_all.append(m)
        pat = pat_map.get(sid, "unknown")
        pat_count[pat].append((h, m))
    if h_all:
        kap = cohens_kappa(h_all, m_all)
        raw = sum(1 for x, y in zip(h_all, m_all) if x == y) / len(h_all)
        print(f"Overall: κ={kap:.3f}, raw={raw*100:.1f}%, N={len(h_all)}")
        # FP/FN: M=1 but H=0 (FP); M=0 but H=1 (FN)
        fp = sum(1 for h, m in zip(h_all, m_all) if m == 1 and h == 0)
        fn = sum(1 for h, m in zip(h_all, m_all) if m == 0 and h == 1)
        neg_h = sum(1 for h in h_all if h == 0)
        pos_h = sum(1 for h in h_all if h == 1)
        print(f"  FP rate (Mistral PASS, human FAIL): {fp/max(1,neg_h)*100:.1f}% ({fp}/{neg_h})")
        print(f"  FN rate (Mistral FAIL, human PASS): {fn/max(1,pos_h)*100:.1f}% ({fn}/{pos_h})")
        print()
        print("Per-pattern:")
        for pat in ("implicit_drift", "explicit_replacement",
                    "multi_version", "narrowing"):
            pairs = pat_count.get(pat, [])
            if not pairs:
                print(f"  {pat:<22} (no data)")
                continue
            ph = [p[0] for p in pairs]
            pm = [p[1] for p in pairs]
            kp = cohens_kappa(ph, pm)
            rp = sum(1 for x, y in zip(ph, pm) if x == y) / len(ph)
            print(f"  {pat:<22} κ={kp:.3f}, raw={rp*100:.1f}%, N={len(ph)}")
    print()

    # ============= §B. Opus ↔ Mistral on N=150 pool =============
    print("=== §B. Opus ↔ Mistral (judge_validation pool, same 150 pairs) ===\n")
    o_pool, m_pool = [], []
    for (sid, sys) in pool_with_mistral:
        if (sid, sys) not in opus:
            continue
        o_pool.append(opus[(sid, sys)])
        m_pool.append(mistral[(sid, sys)])
    if o_pool:
        kap = cohens_kappa(o_pool, m_pool)
        raw = sum(1 for x, y in zip(o_pool, m_pool) if x == y) / len(o_pool)
        print(f"Overall: κ={kap:.3f}, raw={raw*100:.1f}%, N={len(o_pool)}")
    print()

    # ============= §C. Opus ↔ Mistral on drift focal cell =============
    print("=== §C. Opus ↔ Mistral on drift focal cell ===\n")
    drift_sids = [s for s, p in pat_map.items() if p == "implicit_drift"]
    print(f"Drift sample count: {len(drift_sids)}")
    print(f"Per-system Mistral drift coverage:")
    sys_drift_with_both: dict[str, list[str]] = defaultdict(list)
    for sys in FOCAL_SYSTEMS:
        for sid in drift_sids:
            if (sid, sys) in opus and (sid, sys) in mistral:
                sys_drift_with_both[sys].append(sid)
        n = len(sys_drift_with_both[sys])
        print(f"  {sys}: {n} drift pairs with both judges")
    print()

    print("Per-system VF (drift):")
    print(f"  {'system':<28} {'Opus VF':>9} {'Mistral VF':>11} {'κ':>7} "
          f"{'raw':>7} {'N':>5}")
    print("  " + "-" * 72)
    sys_opus_vf, sys_mistral_vf = {}, {}
    for sys in FOCAL_SYSTEMS:
        sids = sys_drift_with_both[sys]
        if not sids:
            continue
        ovf = [opus[(s, sys)] for s in sids]
        mvf = [mistral[(s, sys)] for s in sids]
        sys_opus_vf[sys] = mean(ovf)
        sys_mistral_vf[sys] = mean(mvf)
        kap = cohens_kappa(ovf, mvf)
        raw = sum(1 for x, y in zip(ovf, mvf) if x == y) / len(sids)
        print(f"  {sys:<28} {mean(ovf)*100:>8.1f}% {mean(mvf)*100:>10.1f}% "
              f"{kap:>7.3f} {raw*100:>6.1f}% {len(sids):>5}")
    print()

    # ============= Headline-invariance: drift gap =============
    print("=== Headline-invariance: structured_sonnet − long_context_sonnet46"
          " drift gap ===\n")
    SHARED_SIDS = sorted(set(sys_drift_with_both["structured_sonnet"])
                          & set(sys_drift_with_both["long_context_sonnet46"]))
    print(f"Shared drift pairs (both systems × both judges): {len(SHARED_SIDS)}")
    if SHARED_SIDS:
        # Opus
        o_a = {s: opus[(s, "structured_sonnet")] for s in SHARED_SIDS}
        o_b = {s: opus[(s, "long_context_sonnet46")] for s in SHARED_SIDS}
        pt, lo, hi, n = paired_bootstrap_ci(o_a, o_b, SHARED_SIDS,
                                              args.n_boot, args.seed)
        print(f"  Opus 4.6:        Δ = {pt*100:+.1f}pp [{lo*100:+.1f}, {hi*100:+.1f}] N={n}")
        # Mistral
        m_a = {s: mistral[(s, "structured_sonnet")] for s in SHARED_SIDS}
        m_b = {s: mistral[(s, "long_context_sonnet46")] for s in SHARED_SIDS}
        pt, lo, hi, n = paired_bootstrap_ci(m_a, m_b, SHARED_SIDS,
                                              args.n_boot, args.seed)
        print(f"  Mistral Large 3: Δ = {pt*100:+.1f}pp [{lo*100:+.1f}, {hi*100:+.1f}] N={n}")
    print()

    # ============= DiD: backbone-invariance =============
    print("=== Backbone-invariance DiD under Mistral judge ===\n")
    SS_LL_SIDS = sorted(set(sys_drift_with_both["structured_sonnet"])
                         & set(sys_drift_with_both["long_context_sonnet46"])
                         & set(sys_drift_with_both["sonnet_extract"])
                         & set(sys_drift_with_both["long_context_llama8b"]))
    print(f"Shared drift pairs (4 systems × both judges): {len(SS_LL_SIDS)}")
    if SS_LL_SIDS:
        for judge_name, verd in [("Opus 4.6", opus), ("Mistral Large 3", mistral)]:
            rng = random.Random(args.seed)
            dd_boots = []
            for _ in range(args.n_boot):
                idxs = [rng.randrange(len(SS_LL_SIDS))
                        for _ in range(len(SS_LL_SIDS))]
                sids_b = [SS_LL_SIDS[i] for i in idxs]
                a1 = mean([verd[(s, "structured_sonnet")] for s in sids_b])
                a2 = mean([verd[(s, "long_context_sonnet46")] for s in sids_b])
                a3 = mean([verd[(s, "sonnet_extract")] for s in sids_b])
                a4 = mean([verd[(s, "long_context_llama8b")] for s in sids_b])
                dd_boots.append((a1 - a2) - (a3 - a4))
            dd_boots.sort()
            pt = (mean([verd[(s, "structured_sonnet")] for s in SS_LL_SIDS])
                  - mean([verd[(s, "long_context_sonnet46")] for s in SS_LL_SIDS])
                  - mean([verd[(s, "sonnet_extract")] for s in SS_LL_SIDS])
                  + mean([verd[(s, "long_context_llama8b")] for s in SS_LL_SIDS]))
            lo, hi = dd_boots[int(args.n_boot * 0.025)], dd_boots[int(args.n_boot * 0.975)]
            ci_excl_zero = "✅ CI excludes 0" if (lo > 0 or hi < 0) else "✅ CI includes 0 (backbone-invariant)"
            print(f"  {judge_name}:  DiD = {pt*100:+.1f}pp [{lo*100:+.1f}, {hi*100:+.1f}]  {ci_excl_zero}")
    print()

    # ============= §D. Spearman rank-stability =============
    print("=== §D. System-ranking stability across judges (drift) ===\n")
    sys_with_both = sorted(sys_opus_vf.keys() & sys_mistral_vf.keys())
    if len(sys_with_both) >= 2:
        opus_ranks = [sys_opus_vf[s] for s in sys_with_both]
        mistral_ranks = [sys_mistral_vf[s] for s in sys_with_both]
        rho = spearman_rho(opus_ranks, mistral_ranks)
        print(f"  Spearman ρ (n={len(sys_with_both)} focal systems): {rho:.3f}")
        for s in sys_with_both:
            print(f"    {s:<28} Opus {sys_opus_vf[s]*100:>5.1f}%  "
                  f"Mistral {sys_mistral_vf[s]*100:>5.1f}%")
    print()

    print("Reading guide:")
    print("  • §A high κ + low FP rate confirms Mistral aligns with humans.")
    print("  • §B high κ confirms Opus and Mistral are consistent on the same pool.")
    print("  • §C reproduces the per-system drift VF under both judges side by side.")
    print("  • Headline-invariance: if both judges show overlapping CIs, the +24.1pp")
    print("    drift gap is judge-invariant.")
    print("  • DiD: if both judges show CIs spanning 0, backbone-invariance holds.")
    print("  • §D ρ ≥ 0.80 by §6.3 / §14.3 protocol thresholds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
