"""Cross-judge agreement + ranking-stability analysis.

Reads two judge-verdict files (the original Qwen-7B `benchmark_v1_verdicts.jsonl`
and the Mistral cross-judge `benchmark_v1_verdicts_mistral.jsonl`) and
produces:

  - Raw agreement %
  - Cohen's kappa
  - Per-system VF means under each judge
  - Spearman rank-stability of system orderings between judges

Maps to protocol §6.3 and §14.3 thresholds:

  - raw agreement ≥ 80%, κ ≥ 0.60
  - cross-judge ranking Spearman ≥ 0.80

Writes:
  reports/phase1/cross_judge_agreement.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from scipy import stats

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
REPORTS = REPO / "reports" / "phase1"


def _load_verdicts(path: Path) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    if not path.exists():
        return out
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            out[(obj["sample_id"], obj["system_name"])] = obj
    return out


def _cohen_kappa(a: list[int], b: list[int]) -> float:
    if len(a) != len(b) or not a:
        return float("nan")
    n = len(a)
    p_o = sum(1 for x, y in zip(a, b) if x == y) / n
    p_a_pos = sum(a) / n
    p_a_neg = 1 - p_a_pos
    p_b_pos = sum(b) / n
    p_b_neg = 1 - p_b_pos
    p_e = p_a_pos * p_b_pos + p_a_neg * p_b_neg
    if p_e == 1.0:
        return 1.0 if p_o == 1.0 else 0.0
    return (p_o - p_e) / (1 - p_e)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--judge-a", default=str(DATA / "benchmark_v1_verdicts.jsonl")
    )
    parser.add_argument(
        "--judge-b", default=str(DATA / "benchmark_v1_verdicts_mistral.jsonl")
    )
    parser.add_argument("--label-a", default="Qwen-7B")
    parser.add_argument("--label-b", default="Mistral-7B")
    args = parser.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    a = _load_verdicts(Path(args.judge_a))
    b = _load_verdicts(Path(args.judge_b))
    if not a or not b:
        print(f"ERROR: one of the verdicts files is empty / missing.")
        print(f"  judge-a {args.judge_a}: {len(a)} verdicts")
        print(f"  judge-b {args.judge_b}: {len(b)} verdicts")
        return 2

    # Aligned pairs
    common_keys = sorted(a.keys() & b.keys())
    a_vfs = [int(a[k]["vf"]) if a[k]["vf"] is not None else 0 for k in common_keys]
    b_vfs = [int(b[k]["vf"]) if b[k]["vf"] is not None else 0 for k in common_keys]
    raw_agreement = sum(1 for x, y in zip(a_vfs, b_vfs) if x == y) / len(common_keys)
    kappa = _cohen_kappa(a_vfs, b_vfs)

    # Per-system means under each judge
    by_sys_a: dict[str, list[int]] = defaultdict(list)
    by_sys_b: dict[str, list[int]] = defaultdict(list)
    for (sid, sys_name) in common_keys:
        by_sys_a[sys_name].append(int(a[(sid, sys_name)]["vf"] or 0))
        by_sys_b[sys_name].append(int(b[(sid, sys_name)]["vf"] or 0))
    sys_names = sorted(by_sys_a.keys())
    means_a = [sum(by_sys_a[s]) / len(by_sys_a[s]) for s in sys_names]
    means_b = [sum(by_sys_b[s]) / len(by_sys_b[s]) for s in sys_names]
    spearman = stats.spearmanr(means_a, means_b)
    kendall = stats.kendalltau(means_a, means_b)

    lines: list[str] = []
    lines.append("# Cross-judge agreement (protocol §6.3, §14.3)")
    lines.append("")
    lines.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_")
    lines.append("")
    lines.append(f"- Judge A: **{args.label_a}**  ({len(a)} verdicts)")
    lines.append(f"- Judge B: **{args.label_b}**  ({len(b)} verdicts)")
    lines.append(f"- Aligned pairs: **{len(common_keys)}**")
    lines.append("")
    lines.append("## Verdict-level agreement")
    lines.append("")
    lines.append(f"- Raw agreement: **{raw_agreement * 100:.1f}%** "
                 f"(protocol §6.3 threshold: ≥ 80%)")
    lines.append(f"- Cohen's κ:     **{kappa:.3f}** "
                 f"(threshold: ≥ 0.60)")
    if raw_agreement >= 0.80 and kappa >= 0.60:
        lines.append("- ✅ **Both thresholds met** — judge may be used for full-set VF.")
    elif raw_agreement >= 0.75 and kappa >= 0.50:
        lines.append(
            "- ⚠️ **Marginal**: raw 75-80% or κ 0.50-0.60. Per protocol "
            "§6.3, judge usable only with high-confidence analysis; claim "
            "strength capped at medium."
        )
    else:
        lines.append(
            "- ❌ **Below threshold**: raw < 75% or κ < 0.50. Primary judge "
            "cannot be used as-is. Falls back to human-graded VF on a "
            "stratified subset per protocol §6.3."
        )
    lines.append("")

    lines.append("## Per-system VF under each judge")
    lines.append("")
    lines.append(f"| System | n | {args.label_a} VF | {args.label_b} VF | Δ (B−A) |")
    lines.append("|---|---:|---:|---:|---:|")
    for s, ma, mb in zip(sys_names, means_a, means_b):
        n = len(by_sys_a[s])
        lines.append(f"| {s} | {n} | {ma:.3f} | {mb:.3f} | {(mb - ma):+.3f} |")
    lines.append("")

    lines.append("## Ranking stability")
    lines.append("")
    lines.append(f"- Spearman ρ (system rankings): **{spearman.statistic:.3f}** "
                 f"(p={spearman.pvalue:.3f}; protocol §14.3 threshold: ≥ 0.80)")
    lines.append(f"- Kendall  τ:                  **{kendall.statistic:.3f}** "
                 f"(p={kendall.pvalue:.3f})")
    if spearman.statistic >= 0.80:
        lines.append(
            "- ✅ Cross-judge ranking is stable (Spearman ≥ 0.80). "
            "System-ranking claims are valid."
        )
    elif spearman.statistic >= 0.70:
        lines.append(
            "- ⚠️ Marginal. Per protocol §6.3 fallback, ranking claims "
            "may be cited with caveats but not as primary findings."
        )
    else:
        lines.append(
            "- ❌ Cross-judge ranking is unstable (Spearman < 0.70). "
            "Per protocol §14.3, system-ranking claims must be demoted."
        )
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    lines.append(
        f"- n = {len(common_keys)} verdicts spanning {len(sys_names)} systems × "
        f"{len(common_keys) // len(sys_names)} samples. Below the ≥ 200 "
        "human-audited pool the protocol asks for; results are preliminary."
    )
    lines.append(
        f"- Both judges run locally on the 4090 ({args.label_a} and "
        f"{args.label_b}) — neither is a frontier-class judge. The "
        "agreement is a *consistency* check, not a *correctness* check."
    )

    out = REPORTS / "cross_judge_agreement.md"
    out.write_text("\n".join(lines))
    print(f"Raw agreement: {raw_agreement * 100:.1f}%, κ = {kappa:.3f}")
    print(f"Spearman ρ = {spearman.statistic:.3f}, Kendall τ = {kendall.statistic:.3f}")
    print(f"Report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
