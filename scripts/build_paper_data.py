#!/usr/bin/env python3
"""Generate every table / figure dataset cited in the article into
data/paper/ as standalone CSV files, and refresh data/paper/index.md.

Sources are all cached: no API calls.

Inputs:
  data/dataset/realized_phase3_main_full.jsonl
  data/verdicts/phase3_xsystem_opus_verdicts.jsonl
  data/verdicts/phase3_xjudge_mistral_verdicts.jsonl
  data/verdicts/phase3_xjudge_mistral_sonnet_extract_drift.jsonl

Annotation summary CSVs (judge_validation_summary, naturalness_summary,
solvability_summary, etc.) are emitted with pre-computed aggregate
values; raw per-annotator data is not redistributed.

Outputs (data/paper/):
  table5_overall_vf.csv                       — §5.1 Table 5
  table6_pattern_matrix.csv                   — §5.2 Table 6
  table6b_paired_ci.csv                       — §5.2 Table 6b
  figure1_architecture_x_backbone.csv         — §5.3 Figure 1
  table7_recall_vf_gap.csv                    — §5.5 Table 7
  table8_diagnostic_floor_ceiling.csv         — §6.1 Table 8
  table9_graphiti_ablation.csv                — §6.4 Table 9
  xjudge_mistral_summary.csv                  — §4.4 cross-judge
  per_system_by_horizon.csv                   — Appendix
  per_system_by_target_type.csv               — Appendix
  per_system_by_domain_top10.csv              — Appendix
  judge_validation_summary.csv                — §4.5
  naturalness_summary.csv                     — Appendix E
  solvability_summary.csv                     — §4.5

Usage:
  python scripts/build_paper_data.py
"""

from __future__ import annotations

import csv
import json
import random
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
PAPER = DATA / "paper"
PAPER.mkdir(parents=True, exist_ok=True)


def load_meta() -> dict[str, dict]:
    out = {}
    with open(DATA / "dataset/realized_phase3_main_full.jsonl") as f:
        for line in f:
            r = json.loads(line)
            g = r.get("_gold", {}) or {}
            md = g.get("metadata", {}) or {}
            n_versions = (md.get("competing_versions_count")
                          or len(g.get("target_versions") or [])
                          or 2)
            out[r["sample_id"]] = {
                "horizon": md.get("horizon"),
                "pattern": (md.get("failure_patterns") or ["unknown"])[0],
                "target_type": md.get("gold_target_type"),
                "domain": md.get("domain"),
                "n_versions": n_versions,
            }
    return out


def load_verdicts(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path)]


SYS_ORDER = [
    "structured_sonnet", "long_context_sonnet46", "long_context_mistral",
    "recency_wrapper", "sonnet_extract", "active_state_wrapper",
    "recency_rag", "long_context_llama8b", "graphiti", "naive_rag",
    "graphiti_inv_off",
]


def paired_diff(a_vf, b_vf, sids, n_boot=2000, seed=42):
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


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {path.name}")


def build_table5(meta, opus_verdicts):
    """Overall VF per system × horizon."""
    by_sys_h = defaultdict(lambda: defaultdict(list))
    by_sys_overall = defaultdict(list)
    for v in opus_verdicts:
        sid = v["sample_id"]
        if sid not in meta:
            continue
        sys = v["system_name"]
        if sys not in SYS_ORDER:
            continue
        vf = 1 if v.get("vf") in (1, 1.0) else 0
        by_sys_overall[sys].append(vf)
        h = meta[sid]["horizon"]
        if h:
            by_sys_h[sys][h].append(vf)
    rows = []
    for sys in SYS_ORDER:
        if sys not in by_sys_overall:
            continue
        ovf = mean(by_sys_overall[sys]) * 100
        c = mean(by_sys_h[sys].get("compact", [0])) * 100 if by_sys_h[sys].get("compact") else None
        s = mean(by_sys_h[sys].get("standard", [0])) * 100 if by_sys_h[sys].get("standard") else None
        h = mean(by_sys_h[sys].get("hard", [0])) * 100 if by_sys_h[sys].get("hard") else None
        delta = round(h - c, 2) if (c is not None and h is not None) else None
        rows.append([sys, len(by_sys_overall[sys]), round(ovf, 2),
                     round(c, 2) if c is not None else None,
                     round(s, 2) if s is not None else None,
                     round(h, 2) if h is not None else None,
                     delta])
    write_csv(PAPER / "table5_overall_vf.csv",
              ["system", "n", "overall_vf", "compact_vf", "standard_vf", "hard_vf",
               "delta_compact_to_hard_pp"], rows)


def build_table6(meta, opus_verdicts):
    """Pattern × system VF matrix."""
    by_sys_p = defaultdict(lambda: defaultdict(list))
    by_sys_overall = defaultdict(list)
    for v in opus_verdicts:
        sid = v["sample_id"]
        if sid not in meta:
            continue
        sys = v["system_name"]
        if sys not in SYS_ORDER:
            continue
        vf = 1 if v.get("vf") in (1, 1.0) else 0
        by_sys_overall[sys].append(vf)
        p = meta[sid]["pattern"]
        if p:
            by_sys_p[sys][p].append(vf)
    rows = []
    for sys in SYS_ORDER:
        if sys not in by_sys_overall:
            continue
        ovf = mean(by_sys_overall[sys]) * 100
        d = round(mean(by_sys_p[sys].get("implicit_drift", [0])) * 100, 2) if by_sys_p[sys].get("implicit_drift") else None
        e = round(mean(by_sys_p[sys].get("explicit_replacement", [0])) * 100, 2) if by_sys_p[sys].get("explicit_replacement") else None
        m = round(mean(by_sys_p[sys].get("multi_version", [0])) * 100, 2) if by_sys_p[sys].get("multi_version") else None
        n = round(mean(by_sys_p[sys].get("narrowing", [0])) * 100, 2) if by_sys_p[sys].get("narrowing") else None
        rows.append([sys, len(by_sys_overall[sys]), round(ovf, 2), d, e, m, n])
    write_csv(PAPER / "table6_pattern_matrix.csv",
              ["system", "n", "overall_vf", "drift_vf", "explicit_vf",
               "multi_vf", "narrow_vf"], rows)


def build_table6b_and_figure1(meta, opus_verdicts):
    """Paired bootstrap CIs (Table 6b) + Figure 1 architecture × backbone."""
    sys_vf = defaultdict(dict)
    for v in opus_verdicts:
        sys_vf[v["system_name"]][v["sample_id"]] = (
            1 if v.get("vf") in (1, 1.0) else 0)
    all_sids = sorted(meta.keys())
    drift = [s for s in all_sids if meta[s]["pattern"] == "implicit_drift"]
    non_drift = [s for s in all_sids if meta[s]["pattern"] != "implicit_drift"]

    comparisons = [
        ("structured_sonnet", "long_context_sonnet46", "overall", all_sids),
        ("structured_sonnet", "long_context_sonnet46", "drift", drift),
        ("sonnet_extract", "long_context_llama8b", "drift", drift),
        ("structured_sonnet", "long_context_sonnet46", "non-drift", non_drift),
        ("graphiti", "graphiti_inv_off", "drift", drift),
        ("graphiti", "graphiti_inv_off", "overall", all_sids),
        ("graphiti", "long_context_sonnet46", "drift", drift),
    ]
    rows_ci = []
    for a, b, slice_, sids in comparisons:
        pt, lo, hi, n = paired_diff(sys_vf[a], sys_vf[b], sids)
        rows_ci.append([f"{a} - {b}", slice_,
                         round(pt * 100, 2), round(lo * 100, 2),
                         round(hi * 100, 2), n,
                         (lo > 0 or hi < 0)])

    # DiD
    rng = random.Random(42)
    dd_boots = []
    for _ in range(2000):
        idxs = [rng.randrange(len(drift)) for _ in range(len(drift))]
        sids_b = [drift[i] for i in idxs]
        a1 = mean([sys_vf["structured_sonnet"].get(s, 0) for s in sids_b])
        a2 = mean([sys_vf["long_context_sonnet46"].get(s, 0) for s in sids_b])
        a3 = mean([sys_vf["sonnet_extract"].get(s, 0) for s in sids_b])
        a4 = mean([sys_vf["long_context_llama8b"].get(s, 0) for s in sids_b])
        dd_boots.append((a1 - a2) - (a3 - a4))
    dd_boots.sort()
    pt_dd = (mean([sys_vf["structured_sonnet"].get(s, 0) for s in drift])
             - mean([sys_vf["long_context_sonnet46"].get(s, 0) for s in drift])
             - mean([sys_vf["sonnet_extract"].get(s, 0) for s in drift])
             + mean([sys_vf["long_context_llama8b"].get(s, 0) for s in drift]))
    lo, hi = dd_boots[int(2000 * 0.025)], dd_boots[int(2000 * 0.975)]
    rows_ci.append(["(Sonnet pair) - (Llama pair) DiD", "drift",
                     round(pt_dd * 100, 2), round(lo * 100, 2),
                     round(hi * 100, 2), len(drift), (lo > 0 or hi < 0)])
    write_csv(PAPER / "table6b_paired_ci.csv",
              ["comparison", "slice", "delta_vf_pp", "ci_lo_pp", "ci_hi_pp",
               "n", "ci_excludes_zero"], rows_ci)

    # Figure 1 — architecture × backbone (4-vendor) auto-emit. Gemini and
    # GPT shards are now ingested in main(), so sys_vf contains all four
    # backbones. Each vendor row is restricted to the drift focal cell
    # using the matched sample_ids actually present in the structured arm.
    fig1_rows: list[list] = []
    fig1_specs = [
        ("Llama 8B",          "long_context_llama8b",  "sonnet_extract"),
        ("Sonnet 4.6",        "long_context_sonnet46", "structured_sonnet"),
        ("Gemini 2.5 Pro",    "long_context_gemini25pro", "structured_gemini25pro"),
        ("GPT-5.4 (outlier)", "long_context_gpt54",    "structured_gpt54"),
    ]
    for label, lc, sx in fig1_specs:
        # Pair on intersection of sids present in BOTH systems on drift.
        paired = [s for s in drift if s in sys_vf[lc] and s in sys_vf[sx]]
        if not paired:
            continue
        lc_vf = mean(sys_vf[lc][s] for s in paired) * 100
        sx_vf = mean(sys_vf[sx][s] for s in paired) * 100
        pt, lo_l, hi_l, n_l = paired_diff(sys_vf[sx], sys_vf[lc], paired)
        fig1_rows.append([
            label, lc, round(lc_vf, 2), sx, round(sx_vf, 2),
            round(pt * 100, 2), round(lo_l * 100, 2),
            round(hi_l * 100, 2), n_l,
        ])
    # DiD (Sonnet pair − Llama pair) on drift, recomputed from sys_vf.
    fig1_rows.append([
        "DiD (Sonnet pair − Llama pair)", "", "", "", "",
        round(pt_dd * 100, 2), round(lo * 100, 2), round(hi * 100, 2),
        len(drift),
    ])
    write_csv(PAPER / "figure1_architecture_x_backbone.csv",
              ["row_label", "long_context_system", "long_context_drift_vf",
               "extract_select_system", "extract_select_drift_vf",
               "lift_pp", "lift_ci_lo_pp", "lift_ci_hi_pp", "n"], fig1_rows)


def build_table7(meta, opus_verdicts):
    """Recall + VF + gap, overall / drift / non-drift per system."""
    overall = defaultdict(lambda: {"vf": [], "rec": []})
    drift_v = defaultdict(lambda: {"vf": [], "rec": []})
    nondrift = defaultdict(lambda: {"vf": [], "rec": []})
    for v in opus_verdicts:
        sid = v["sample_id"]
        if sid not in meta:
            continue
        sys = v["system_name"]
        if sys not in SYS_ORDER:
            continue
        vf = 1 if v.get("vf") in (1, 1.0) else 0
        rec = v.get("recall")
        overall[sys]["vf"].append(vf)
        if rec is not None:
            overall[sys]["rec"].append(rec)
        is_drift = meta[sid]["pattern"] == "implicit_drift"
        bucket = drift_v if is_drift else nondrift
        bucket[sys]["vf"].append(vf)
        if rec is not None:
            bucket[sys]["rec"].append(rec)

    def _row(sys):
        def f(d, key):
            return round(mean(d[sys][key]) * 100, 2) if d[sys][key] else None
        def g(d):
            if d[sys]["vf"] and d[sys]["rec"]:
                return round(mean(d[sys]["rec"]) * 100 - mean(d[sys]["vf"]) * 100, 2)
            return None
        return [sys,
                f(overall, "rec"), f(overall, "vf"), g(overall),
                f(drift_v, "rec"), f(drift_v, "vf"), g(drift_v),
                f(nondrift, "rec"), f(nondrift, "vf"), g(nondrift),
                len(overall[sys]["vf"]), len(drift_v[sys]["vf"]),
                len(nondrift[sys]["vf"])]
    rows = [_row(s) for s in SYS_ORDER if s in overall]
    write_csv(PAPER / "table7_recall_vf_gap.csv",
              ["system", "recall_overall", "vf_overall", "gap_overall",
               "recall_drift", "vf_drift", "gap_drift",
               "recall_nondrift", "vf_nondrift", "gap_nondrift",
               "n_overall", "n_drift", "n_nondrift"], rows)


def build_table8(meta, opus_verdicts):
    """Diagnostic floor / recall_only / ceiling, by horizon × pattern."""
    rec_cells = defaultdict(list)
    vf_cells = defaultdict(list)
    SYS_FOR_RECALL = SYS_ORDER[:-1]  # exclude graphiti_inv_off ablation
    for v in opus_verdicts:
        sid = v["sample_id"]
        if sid not in meta or v["system_name"] not in SYS_FOR_RECALL:
            continue
        rec = v.get("recall")
        if rec is None:
            continue
        vf = 1 if v.get("vf") in (1, 1.0) else 0
        m = meta[sid]
        for kind, val in [("overall", "overall"),
                            ("pattern", m["pattern"]),
                            ("horizon", m["horizon"])]:
            if val:
                rec_cells[(kind, val)].append(rec)
                vf_cells[(kind, val)].append(vf)

    # Read the diagnostic VF directly from query_only / oracle_current_version verdicts
    diag_vf = defaultdict(lambda: defaultdict(list))
    for v in opus_verdicts:
        sid = v["sample_id"]
        if sid not in meta:
            continue
        sys = v["system_name"]
        if sys not in ("query_only", "oracle_current_version"):
            continue
        vf = 1 if v.get("vf") in (1, 1.0) else 0
        m = meta[sid]
        diag_vf[sys][("overall", "overall")].append(vf)
        diag_vf[sys][("pattern", m["pattern"])].append(vf)
        diag_vf[sys][("horizon", m["horizon"])].append(vf)

    cols = [("overall", "overall"),
            ("pattern", "implicit_drift"),
            ("pattern", "explicit_replacement"),
            ("pattern", "multi_version"),
            ("pattern", "narrowing"),
            ("horizon", "compact"),
            ("horizon", "standard"),
            ("horizon", "hard")]
    header = ["row_label"] + [f"{c[1]}_pct" for c in cols] + ["n"]
    rows = []
    # query_only
    rows.append(["query_only_vf"] + [
        round(mean(diag_vf["query_only"][c]) * 100, 2)
        if diag_vf["query_only"].get(c) else None for c in cols
    ] + [sum(len(diag_vf["query_only"][c]) for c in cols if c[0]=="overall")])
    # recall_only mean recall
    rows.append(["recall_only_mean_recall"] + [
        round(mean(rec_cells[c]) * 100, 2) if rec_cells.get(c) else None
        for c in cols
    ] + [len(rec_cells[("overall", "overall")])])
    # paired mean per-system VF
    rows.append(["mean_per_system_vf"] + [
        round(mean(vf_cells[c]) * 100, 2) if vf_cells.get(c) else None
        for c in cols
    ] + [len(vf_cells[("overall", "overall")])])
    # gap
    rows.append(["recall_minus_vf_pp"] + [
        round(mean(rec_cells[c]) * 100 - mean(vf_cells[c]) * 100, 2)
        if rec_cells.get(c) and vf_cells.get(c) else None
        for c in cols
    ] + [None])
    # oracle ceiling
    rows.append(["oracle_current_version_vf"] + [
        round(mean(diag_vf["oracle_current_version"][c]) * 100, 2)
        if diag_vf["oracle_current_version"].get(c) else None for c in cols
    ] + [sum(len(diag_vf["oracle_current_version"][c]) for c in cols if c[0]=="overall")])
    write_csv(PAPER / "table8_diagnostic_floor_ceiling.csv", header, rows)


def build_table9(meta, opus_verdicts):
    """Graphiti invalidation ablation."""
    sys_vf = defaultdict(dict)
    for v in opus_verdicts:
        sys_vf[v["system_name"]][v["sample_id"]] = (
            1 if v.get("vf") in (1, 1.0) else 0)
    all_sids = sorted(meta.keys())
    drift = [s for s in all_sids if meta[s]["pattern"] == "implicit_drift"]
    rows = []
    for sys in ("graphiti", "graphiti_inv_off"):
        ov = mean([sys_vf[sys][s] for s in all_sids if s in sys_vf[sys]]) * 100
        dv = mean([sys_vf[sys][s] for s in drift if s in sys_vf[sys]]) * 100
        rows.append([sys, round(ov, 2), round(dv, 2),
                      sum(1 for s in all_sids if s in sys_vf[sys]),
                      sum(1 for s in drift if s in sys_vf[sys])])
    # Δ on - off, paired
    pt_d, lo_d, hi_d, n_d = paired_diff(sys_vf["graphiti"], sys_vf["graphiti_inv_off"], drift)
    pt_o, lo_o, hi_o, n_o = paired_diff(sys_vf["graphiti"], sys_vf["graphiti_inv_off"], all_sids)
    rows.append(["delta_on_minus_off_drift_pp",
                  round(pt_d * 100, 2),
                  f"[{round(lo_d*100,2)}, {round(hi_d*100,2)}]",
                  n_d, "drift"])
    rows.append(["delta_on_minus_off_overall_pp",
                  round(pt_o * 100, 2),
                  f"[{round(lo_o*100,2)}, {round(hi_o*100,2)}]",
                  n_o, "overall"])
    write_csv(PAPER / "table9_graphiti_ablation.csv",
              ["row", "overall_vf_or_delta", "drift_vf_or_ci",
               "n_overall", "n_drift_or_slice"], rows)


def build_xjudge_summary():
    """Mistral cross-judge summary (per-system VF Opus vs Mistral on drift focal)."""
    mistral_paths = [DATA / "verdicts/phase3_xjudge_mistral_verdicts.jsonl",
                     DATA / "verdicts/phase3_xjudge_mistral_sonnet_extract_drift.jsonl"]
    mistral = {}
    for p in mistral_paths:
        if p.exists():
            for v in load_verdicts(p):
                mistral[(v["sample_id"], v["system_name"])] = (
                    1 if v.get("vf") in (1, 1.0) else 0)
    opus = {}
    for v in load_verdicts(DATA / "verdicts/phase3_xsystem_opus_verdicts.jsonl"):
        opus[(v["sample_id"], v["system_name"])] = (
            1 if v.get("vf") in (1, 1.0) else 0)
    meta = load_meta()
    drift = sorted([s for s, m in meta.items() if m["pattern"] == "implicit_drift"])
    FOCAL = ["structured_sonnet", "long_context_sonnet46",
             "long_context_llama8b", "naive_rag", "sonnet_extract"]
    rows = []
    for sys in FOCAL:
        sids = [s for s in drift if (s, sys) in opus and (s, sys) in mistral]
        if not sids:
            continue
        ovf = mean([opus[(s, sys)] for s in sids]) * 100
        mvf = mean([mistral[(s, sys)] for s in sids]) * 100
        n_agree = sum(1 for s in sids if opus[(s, sys)] == mistral[(s, sys)])
        raw = n_agree / len(sids) * 100
        # Cohen's κ
        n = len(sids)
        p_o = raw / 100
        p_a1 = sum(opus[(s, sys)] for s in sids) / n
        p_b1 = sum(mistral[(s, sys)] for s in sids) / n
        p_e = p_a1 * p_b1 + (1 - p_a1) * (1 - p_b1)
        kap = (p_o - p_e) / (1 - p_e) if p_e < 0.999999 else float("nan")
        rows.append([sys, len(sids), round(ovf, 2), round(mvf, 2),
                      round(kap, 3), round(raw, 1)])
    write_csv(PAPER / "xjudge_mistral_summary.csv",
              ["system", "n_drift_paired", "opus_drift_vf",
               "mistral_drift_vf", "cohens_kappa", "raw_agreement_pct"], rows)


def build_per_system_slices():
    """Run the existing recompute_per_system_tables script for each axis."""
    for axis, fname, extra in [
        ("horizon", "per_system_by_horizon.csv", []),
        ("target_type", "per_system_by_target_type.csv", []),
        ("domain", "per_system_by_domain_top10.csv", ["--topn", "10"]),
    ]:
        out = PAPER / fname
        cmd = [sys.executable, str(REPO / "scripts" / "recompute_per_system_tables.py"),
               "--by", axis, "--csv", str(out)] + extra
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"  wrote {out.name}")


def build_horizon_paired():
    """Run recompute_horizon_paired script (matched-triples bootstrap)."""
    out = PAPER / "horizon_paired_ci.csv"
    cmd = [sys.executable, str(REPO / "scripts" / "recompute_horizon_paired.py"),
           "--csv", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  wrote {out.name}")


def build_cost_latency():
    """Per-system mean / median / p95 / total wall-clock from response files."""
    SYS_FILES = {
        "structured_sonnet": "responses/phase3_structured_sonnet_responses.jsonl",
        "long_context_sonnet46": "responses/phase3_long_context_sonnet46_responses.jsonl",
        "long_context_mistral": "responses/phase3_long_context_mistral_responses.jsonl",
        "long_context_llama8b": "responses/phase3_long_context_llama8b_responses.jsonl",
        "naive_rag": "responses/phase3_naive_rag_responses.jsonl",
        "recency_rag": "responses/phase3_recency_rag_responses.jsonl",
        "recency_wrapper": "responses/phase3_recency_wrapper_responses.jsonl",
        "sonnet_extract": "responses/phase3_sonnet_extract_responses.jsonl",
        "active_state_wrapper": "responses/phase3_active_state_wrapper_responses.jsonl",
        "graphiti": "responses/phase3_graphiti_responses.jsonl",
        "graphiti_inv_off": "responses/phase3_graphiti_inv_off_responses.jsonl",
        "query_only": "responses/phase3_query_only_responses.jsonl",
        "oracle_current_version": "responses/phase3_oracle_current_version_responses.jsonl",
    }
    rows = []
    for sys_name, fn in SYS_FILES.items():
        p = DATA / fn
        if not p.exists():
            continue
        elapsed = []
        for line in open(p):
            e = json.loads(line).get("elapsed_s")
            if e is not None:
                elapsed.append(e)
        if not elapsed:
            continue
        elapsed.sort()
        p95 = elapsed[int(0.95 * len(elapsed))] if len(elapsed) >= 20 else elapsed[-1]
        rows.append([sys_name, len(elapsed),
                     round(mean(elapsed), 2), round(elapsed[len(elapsed) // 2], 2),
                     round(p95, 2), round(sum(elapsed), 0)])
    write_csv(PAPER / "cost_latency.csv",
              ["system", "n", "mean_s", "median_s", "p95_s", "total_wall_s"], rows)


def build_judge_validation_summary():
    """Lift the headline numbers from judge_validation_report.md into a small CSV."""
    rows = [
        ["overall", 150, 0.821, 91.3, 0.0, 13.5, 0.737],
        ["implicit_drift", 90, 0.775, 88.9, None, None, None],
        ["explicit_replacement", 20, 1.000, 100.0, None, None, None],
        ["multi_version", 20, 0.583, 85.0, None, None, None],
        ["narrowing", 20, 1.000, 100.0, None, None, None],
    ]
    write_csv(PAPER / "judge_validation_summary.csv",
              ["slice", "n", "cohens_kappa_judge_vs_human",
               "raw_agreement_pct", "fp_rate_pct", "fn_rate_pct",
               "fleiss_kappa_3_annotators"], rows)

    # Contingency table (Appendix F.4) — pre-computed aggregate.
    # Raw per-annotator data is not redistributed.
    write_csv(PAPER / "judge_validation_contingency.csv",
              ["humans", "judge_pass", "judge_fail", "row_total"],
              [["pass", 83, 13, 96],
               ["fail", 0, 54, 54],
               ["column_total", 83, 67, 150]])


def build_naturalness_summary():
    """Per-dim mean + 95% CI + ICC, per-cell × dim, per-annotator, acceptance.
    Pre-computed aggregate from the Phase 3 naturalness annotation pool;
    raw per-annotator data is not redistributed."""
    # Per-dim headline (with 95% CI lo/hi)
    write_csv(PAPER / "naturalness_summary.csv",
              ["dimension", "mean_score_1to5", "ci_lo", "ci_hi",
               "icc_2_1", "n_ratings", "pre_registered_threshold"],
              [["D1_dialogue_naturalness", 3.78, 3.67, 3.89, 0.615, 120, ">=3.5"],
               ["D2_pragmatic_plausibility", 3.93, 3.81, 4.06, 0.486, 120, ">=3.5"],
               ["D3_supersession_naturalness", 3.90, 3.77, 4.03, 0.452, 120, ">=3.5"],
               ["D4_artifact_absence", 3.66, 3.53, 3.79, 0.499, 120, ">=3.5"]])
    # Per-cell × dim (compact + standard horizons; hard excluded by design)
    cells = [
        # (pattern, horizon, D1, D2, D3, D4)
        ("implicit_drift", "compact", 3.73, 3.87, 3.93, 3.27),
        ("implicit_drift", "standard", 3.73, 4.20, 4.20, 4.00),
        ("explicit_replacement", "compact", 3.87, 4.00, 4.13, 3.80),
        ("explicit_replacement", "standard", 3.80, 4.13, 4.27, 3.40),
        ("narrowing", "compact", 3.80, 3.53, 3.47, 3.47),
        ("narrowing", "standard", 4.00, 4.27, 4.33, 4.13),
        ("multi_version", "compact", 4.13, 3.60, 3.40, 3.67),
        ("multi_version", "standard", 3.20, 3.87, 3.47, 3.53),
    ]
    write_csv(PAPER / "naturalness_per_cell.csv",
              ["pattern", "horizon", "D1_mean", "D2_mean", "D3_mean", "D4_mean", "n_per_dim"],
              [list(c) + [15] for c in cells])
    # Per-annotator drift check
    write_csv(PAPER / "naturalness_per_annotator.csv",
              ["annotator", "D1_mean", "D2_mean", "D3_mean", "D4_mean",
               "mean_of_dims"],
              [["A", 3.85, 3.90, 4.05, 3.62, 3.86],
               ["B", 3.70, 4.00, 3.85, 3.62, 3.79],
               ["C", 3.80, 3.90, 3.80, 3.73, 3.81]])
    # Pre-registered acceptance summary
    write_csv(PAPER / "naturalness_acceptance.csv",
              ["threshold", "required", "got", "status"],
              [["per_dim_mean_ge_3_5", "all 4 dims", "all 4 >= 3.66", "PASS"],
               ["per_cell_mean_ge_3_0", "all 32 means", "0 below 3.0", "PASS"],
               ["icc_2_1_ge_0_5", "all 4 dims", "D1 0.615, others 0.45-0.50", "marginal"],
               ["pct_cells_dim_below_3_0_le_10pct", "<= 3.2 of 32", "0/32 = 0.0%", "PASS"]])


def build_solvability_summary():
    """Pre-computed aggregate from the Phase 3 solvability annotation pool;
    raw per-annotator data is not redistributed."""
    # Headline + per-pattern with unanimous + problematic
    write_csv(PAPER / "solvability_summary.csv",
              ["slice", "n", "majority_solvability_pct",
               "unanimous_correct_pct", "problematic_sample_pct",
               "pairwise_mean_kappa"],
              [["overall", 270, 98.1, 74.4, 1.9, 0.688],
               ["implicit_drift", 180, 97.8, 68.9, 2.2, None],
               ["explicit_replacement", 30, 100.0, 90.0, 0.0, None],
               ["narrowing", 30, 100.0, 83.3, 0.0, None],
               ["multi_version", 30, 96.7, 83.3, 3.3, None]])
    # By drift subtype
    write_csv(PAPER / "solvability_by_drift_subtype.csv",
              ["drift_subtype", "n", "majority_solvability_pct",
               "unanimous_correct_pct", "problematic_sample_pct"],
              [["repeated_use", 80, 96.2, 70.0, 3.8],
               ["abandonment", 60, 100.0, 66.7, 0.0],
               ["gradual_narrowing", 40, 97.5, 70.0, 2.5]])
    # By horizon
    write_csv(PAPER / "solvability_by_horizon.csv",
              ["horizon", "n", "majority_solvability_pct",
               "unanimous_correct_pct", "problematic_sample_pct"],
              [["compact", 90, 100.0, 78.9, 0.0],
               ["standard", 90, 96.7, 75.6, 3.3],
               ["hard", 90, 97.8, 68.9, 2.2]])
    # Annotator-level accuracy
    write_csv(PAPER / "solvability_per_annotator.csv",
              ["annotator", "accuracy_pct"],
              [["A", 91.1], ["B", 87.4], ["C", 93.7]])


def build_dataset_statistics():
    """Phase 3 main set scale + axes (Table 1)."""
    meta = load_meta()
    # Pattern, horizon, target_type, domain
    pat_count = defaultdict(int)
    horizon_count = defaultdict(int)
    target_count = defaultdict(int)
    domain_count = defaultdict(int)
    for sid, m in meta.items():
        pat_count[m["pattern"]] += 1
        horizon_count[m["horizon"]] += 1
        target_count[m["target_type"]] += 1
        domain_count[m["domain"]] += 1
    # Manifest groups
    mf = json.loads((DATA / "manifests" / "phase3_main.json").read_text())
    groups = mf["groups"]
    triples = sum(1 for g in groups if len(g.get("members", [])) == 3)
    doublets = sum(1 for g in groups if len(g.get("members", [])) == 2)
    # Version chain count
    chain_count = defaultdict(int)
    for sid, m in meta.items():
        chain_count[f"{m['n_versions']}_way"] += 1
    rows = [
        ["overall", "samples", len(meta)],
        ["overall", "matched_groups", len(groups)],
        ["overall", "triples", triples],
        ["overall", "doublets", doublets],
    ]
    for k in ("compact", "standard", "hard"):
        rows.append(["horizon", k, horizon_count.get(k, 0)])
    for k in ("implicit_drift", "multi_version", "narrowing", "explicit_replacement"):
        rows.append(["pattern", k, pat_count.get(k, 0)])
    for k in ("object_preference", "procedural_constraint",
              "conceptual_stance", "interpersonal_boundary"):
        rows.append(["target_type", k, target_count.get(k, 0)])
    non_obj = sum(v for k, v in target_count.items() if k != "object_preference")
    rows.append(["target_type", "non_object_share_pct",
                 round(non_obj / max(1, sum(target_count.values())) * 100, 1)])
    for k in sorted(chain_count.keys()):
        rows.append(["version_chain", k, chain_count[k]])
    rows.append(["domains", "distinct", len(domain_count)])
    rows.append(["domains", "largest_share_pct",
                 round(max(domain_count.values()) /
                       max(1, sum(domain_count.values())) * 100, 1)])
    write_csv(PAPER / "dataset_statistics.csv",
              ["panel", "statistic", "count_or_value"], rows)


def write_index():
    """index.md is maintained as a static document under data/paper/.

    This function is a no-op when the index already exists, so running
    build_paper_data.py does not overwrite the curated paper-artefact ->
    CSV mapping. If a clean repo lacks the index, a minimal placeholder
    is emitted to point users at the canonical path.
    """
    target = PAPER / "index.md"
    if target.exists():
        print(f"  (kept existing index.md)")
        return
    target.write_text(
        "# `data/paper/` — paper-table data index\n\n"
        "See the canonical paper artefact -> CSV mapping in the\n"
        "repository at `data/paper/index.md`.\n"
    )
    print(f"  wrote index.md (placeholder)")


def main() -> int:
    print(f"Building data/paper/ from cached sources...\n")
    meta = load_meta()
    print(f"Loaded {len(meta)} gold samples")
    opus_verdicts = load_verdicts(DATA / "verdicts/phase3_xsystem_opus_verdicts.jsonl")
    print(f"Loaded {len(opus_verdicts)} Opus verdicts (main shard)")
    # Optional shards for Gemini 2.5 Pro and GPT-5.4 (these systems were
    # added after the main verdict shard was assembled). Loading them
    # into the same opus_verdicts list lets all downstream builders see
    # their rows. If a shard is missing the file is simply skipped.
    #
    # Order matters: later shards win on (system_name, sample_id)
    # collision. List canonical / latest re-runs LAST so the dedup keeps
    # the cleanest version. (E.g., structured_gpt54_v2 supersedes the
    # v1 rows in phase3_xsystem_opus_verdicts_gpt54.jsonl.)
    extra_shards = [
        "verdicts/phase3_xsystem_opus_verdicts_gemini25.jsonl",
        "verdicts/phase3_xsystem_opus_verdicts_gpt54.jsonl",          # v1 medium structured_gpt54
        "verdicts/phase3_xsystem_opus_verdicts_gpt54_high.jsonl",     # high direct + high structured
        "verdicts/phase3_xsystem_opus_verdicts_structured_gpt54_v3.jsonl",  # canonical medium structured_gpt54
        # NOTE: phase3_xsystem_opus_verdicts_structured_gpt54_high8.jsonl is
        # excluded. Its 8 records carry system_name="structured_gpt54" but
        # were generated from a high-reasoning recovery run; including them
        # corrupted the medium structured_gpt54 dataset because they
        # overwrote 8 v2 sids in the dedup. Re-tag and re-include if/when
        # we run a clean medium recovery shard.
    ]
    for fname in extra_shards:
        path = DATA / fname
        if not path.exists():
            continue
        extra = load_verdicts(path)
        opus_verdicts.extend(extra)
        print(f"Loaded {len(extra)} verdicts from {fname}")
    # Dedupe by (system_name, sample_id), keeping the LAST occurrence
    # (later shards win, per the order above).
    seen: dict[tuple[str, str], dict] = {}
    for v in opus_verdicts:
        seen[(v["system_name"], v["sample_id"])] = v
    n_before = len(opus_verdicts)
    opus_verdicts = list(seen.values())
    if n_before != len(opus_verdicts):
        print(f"Dedup: {n_before} -> {len(opus_verdicts)} verdicts "
              f"({n_before - len(opus_verdicts)} duplicate keys, latest wins)")
    print(f"Total verdicts: {len(opus_verdicts)}\n")

    print("Building tables:")
    build_table5(meta, opus_verdicts)
    build_table6(meta, opus_verdicts)
    build_table6b_and_figure1(meta, opus_verdicts)
    build_table7(meta, opus_verdicts)
    build_table8(meta, opus_verdicts)
    build_table9(meta, opus_verdicts)
    build_xjudge_summary()
    build_per_system_slices()
    build_horizon_paired()
    build_cost_latency()
    build_judge_validation_summary()
    build_naturalness_summary()
    build_solvability_summary()
    build_dataset_statistics()
    write_index()
    print(f"\nAll outputs in {PAPER}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
