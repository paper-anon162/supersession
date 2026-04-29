#!/usr/bin/env python3
"""Generate the 4 data-driven figures from data/paper/*.csv.

Each figure is saved as PDF in paper/figures/. No API calls;
deterministic; cached-only.

Outputs (figure numbers match PDF rendering; fig1 is the example
illustration teaser, kept under version control as a separate PNG):
  paper/figures/fig2_architecture_x_backbone.pdf
  paper/figures/fig3_pattern_heatmap.pdf
  paper/figures/fig4_recall_vs_vf.pdf
  paper/figures/fig5_horizon_degradation.pdf

Usage:
  python scripts/build_paper_figures.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[1]
PAPER_DATA = REPO / "data" / "paper"
FIG_DIR = REPO / "paper" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# NeurIPS-friendly styling: Times-like serif, clean look
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "Liberation Serif"],
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "pdf.fonttype": 42,        # Type-1 / TrueType embedded
    "ps.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def read_csv(name: str) -> list[dict]:
    with open(PAPER_DATA / name) as f:
        return list(csv.DictReader(f))


def fig2_architecture_x_backbone() -> None:
    """Slope chart: drift VF for direct long-context vs extract+select,
    4 backbones — Llama 8B, Sonnet 4.6, Gemini 2.5 Pro (3-vendor main
    replication) + GPT-5.4 (visual outlier with dashed line)."""
    rows = read_csv("figure1_architecture_x_backbone.csv")
    by_backbone = {r["row_label"]: r for r in rows
                   if not r["row_label"].startswith("DiD")}

    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    x = [0, 1]
    xticklabels = ["Direct\nlong-context", "Extract\n+ select"]

    main_specs = [
        ("Llama 8B",       "#d62728", "-",  6),
        ("Sonnet 4.6",     "#1f77b4", "-",  6),
        ("Gemini 2.5 Pro", "#2ca02c", "-",  6),
    ]
    outlier_specs = [
        ("GPT-5.4 (outlier)", "#7f7f7f", "--", 5),
    ]

    for label, color, ls, ms in main_specs + outlier_specs:
        if label not in by_backbone:
            continue
        r = by_backbone[label]
        y = [float(r["long_context_drift_vf"]),
             float(r["extract_select_drift_vf"])]
        lift = float(r["lift_pp"])
        lo = float(r["lift_ci_lo_pp"])
        hi = float(r["lift_ci_hi_pp"])
        ax.plot(x, y, marker="o", linestyle=ls, color=color,
                linewidth=1.5, markersize=ms,
                label=f"{label}: +{lift:.1f} pp [{lo:.1f}, {hi:.1f}]")
        # Endpoint labels
        ax.text(x[0] - 0.04, y[0], f"{y[0]:.1f}",
                ha="right", va="center", fontsize=7.5, color=color)
        ax.text(x[1] + 0.04, y[1], f"{y[1]:.1f}",
                ha="left", va="center", fontsize=7.5, color=color)

    # Human ceiling reference line
    ax.axhline(97.8, color="gray", linestyle=":", linewidth=0.6)
    ax.text(1.02, 97.8, "human 97.8%",
            ha="left", va="center", fontsize=7, color="gray")

    ax.set_xticks(x)
    ax.set_xticklabels(xticklabels)
    ax.set_xlim(-0.32, 1.42)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Drift VF (%)")
    ax.set_title("Architecture × backbone on implicit drift\n"
                 "(N=359-360 paired bootstrap, drift focal cell)")
    ax.legend(loc="upper left", frameon=False, fontsize=7.5,
              title="Within-backbone lift (paired 95% CI)",
              title_fontsize=7.5, alignment="left")
    fig.tight_layout()
    out = FIG_DIR / "fig2_architecture_x_backbone.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.relative_to(REPO)}")


def fig3_pattern_heatmap() -> None:
    """Pattern × system VF heatmap; drift focal column highlighted.

    Display order is overall-VF descending (leaderboard-style). Family
    structure is documented separately; the heatmap rows are the
    standard rank order so reviewers can read top-to-bottom as best to
    worst."""
    rows = read_csv("table6_pattern_matrix.csv")
    order = ["structured_sonnet", "long_context_sonnet46", "long_context_mistral",
             "recency_wrapper", "sonnet_extract", "active_state_wrapper",
             "recency_rag", "long_context_llama8b", "graphiti", "naive_rag",
             "graphiti_inv_off"]
    sys_rows = {r["system"]: r for r in rows}

    cols = [("drift_vf", "drift"),
            ("explicit_vf", "explicit"),
            ("multi_vf", "multi"),
            ("narrow_vf", "narrowing")]
    matrix = []
    for sys in order:
        if sys not in sys_rows:
            continue
        r = sys_rows[sys]
        matrix.append([float(r[c[0]]) if r[c[0]] else 0.0 for c in cols])
    matrix = np.array(matrix)

    fig, ax = plt.subplots(figsize=(4.4, 2.8))
    im = ax.imshow(matrix, aspect="auto", cmap="RdYlGn",
                   vmin=0, vmax=100)

    # Annotate each cell with the VF value
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            v = matrix[i, j]
            txt_color = "white" if v < 30 or v > 75 else "black"
            ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                    fontsize=7, color=txt_color)

    # Highlight drift column (focal)
    ax.add_patch(plt.Rectangle((-0.5, -0.5), 1, matrix.shape[0],
                                fill=False, edgecolor="black",
                                linewidth=1.5, linestyle="-"))

    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([c[1] for c in cols], fontsize=8)
    ax.set_yticks(range(matrix.shape[0]))
    ax.set_yticklabels([s for s in order
                         if s in sys_rows], fontsize=7.5,
                        family="monospace")
    ax.set_xlabel("Failure pattern")
    ax.set_title("Per-system VF (%) by failure pattern\n(drift focal cell boxed)",
                 fontsize=9)

    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("VF (%)", fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    fig.tight_layout()
    out = FIG_DIR / "fig3_pattern_heatmap.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.relative_to(REPO)}")


def fig4_recall_vs_vf() -> None:
    """Per-system scatter: recall_drift vs vf_drift, zoomed to the
    populated region (recall 70-95%, VF 0-80%). Two reference lines:
    y=x (no gap) and y=x-45 (drift-cell mean gap of +45 pp). Marker
    shape = architectural family; one color per family; tight clusters
    are jittered horizontally and labelled with leader lines so each
    label clearly attaches to its marker."""
    rows = read_csv("table7_recall_vf_gap.csv")

    family = {
        "structured_sonnet":     "wrapper",
        "recency_wrapper":       "wrapper",
        "sonnet_extract":        "wrapper",
        "active_state_wrapper":  "wrapper",
        "long_context_sonnet46": "long-context",
        "long_context_mistral":  "long-context",
        "long_context_llama8b":  "long-context",
        "naive_rag":             "RAG",
        "recency_rag":           "RAG",
        "graphiti":              "graph",
        "graphiti_inv_off":      "graph",
    }
    family_color  = {"wrapper": "#1f77b4", "long-context": "#d62728",
                     "RAG": "#2ca02c", "graph": "#9467bd"}
    family_marker = {"wrapper": "^", "long-context": "o",
                     "RAG": "s", "graph": "D"}
    family_size   = {"o": 60, "s": 55, "^": 70, "D": 60}

    by_sys = {r["system"]: r for r in rows}
    pts_raw: list[tuple[str, float, float]] = []
    for sys in family:
        if sys not in by_sys: continue
        r = by_sys[sys]
        if not r.get("recall_drift") or not r.get("vf_drift"): continue
        pts_raw.append((sys, float(r["recall_drift"]), float(r["vf_drift"])))

    XLIM = (70, 95)
    YLIM = (0, 80)
    fig, ax = plt.subplots(figsize=(7.6, 5.0))

    # Reference lines (drawn first, low zorder)
    xs = [XLIM[0], XLIM[1]]
    ax.plot(xs, xs, "k--", linewidth=0.7, alpha=0.55, zorder=1)
    ax.plot(xs, [x - 45 for x in xs], color="#444", linestyle=":",
            linewidth=0.9, alpha=0.7, zorder=1)

    # Reference-line labels: place y=x label INSIDE the chart along the
    # line at its visible mid-segment (recall=75 -> y=75); place
    # y=x-45 label along its line at recall=92 -> y=47.
    ax.text(75.5, 75.0, "y = x  (no gap)", fontsize=7.5, color="black",
            alpha=0.75, ha="left", va="bottom",
            rotation=0)
    ax.text(91.5, 91.5 - 45 + 0.5, "y = x − 45 pp  (drift mean gap)",
            fontsize=7.5, color="#333", alpha=0.85, ha="right", va="bottom")

    # Jitter clusters horizontally so markers don't overlap, then place
    # each label directly adjacent to its (jittered) marker. No leader
    # lines: each label sits in its own quadrant relative to the marker
    # so attribution stays unambiguous.
    # tuple = (marker_x, marker_y, label_dx, label_dy, ha, va)
    layout = {
        # ----- Cluster A: recency_wrapper / sonnet_extract / active_state_wrapper -----
        # raw: (78.6, 48.6) (77.9, 45.8) (78.1, 45.8) — last two collide
        "recency_wrapper":       (78.6, 48.6, 0.0, +2.2, "center", "bottom"),   # above
        "sonnet_extract":        (77.4, 45.8, -0.5, 0.0, "right",  "center"),   # left of marker
        "active_state_wrapper":  (79.0, 45.8, +0.5, 0.0, "left",   "center"),   # right of marker
        # ----- Cluster B: recency_rag / long_context_llama8b / naive_rag -----
        # raw: (80.0, 25.8) (79.7, 21.7) (81.7, 20.6)
        "recency_rag":           (80.0, 25.8, 0.0, +2.2, "center", "bottom"),   # above cluster
        "long_context_llama8b":  (79.7, 21.7, -0.5, 0.0, "right",  "center"),   # left of marker
        "naive_rag":             (81.7, 20.6, +0.5, 0.0, "left",   "center"),   # right of marker
        # ----- standalone points -----
        "structured_sonnet":     (90.7, 59.4, -0.5, 0.0, "right",  "center"),
        "long_context_sonnet46": (93.6, 35.3, -0.5, 0.0, "right",  "center"),
        "long_context_mistral":  (88.3, 33.3, 0.0, -2.2, "center", "top"),
        "graphiti":              (74.2, 36.3, +0.5, 0.0, "left",   "center"),
        "graphiti_inv_off":      (75.1, 32.7, 0.0, -2.2, "center", "top"),
    }

    for sys, _, _ in pts_raw:
        if sys not in layout:
            continue
        mx, my, dx, dy, ha, va = layout[sys]
        fam = family[sys]
        m = family_marker[fam]
        ax.scatter(mx, my, color=family_color[fam], s=family_size[m],
                   alpha=0.9, marker=m, edgecolors="black",
                   linewidth=0.5, zorder=4)
        ax.annotate(sys, xy=(mx + dx, my + dy), fontsize=6.5,
                    family="monospace", ha=ha, va=va, zorder=5)

    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.set_xlabel("Recall on drift focal cell (%)")
    ax.set_ylabel("VF on drift focal cell (%)")
    ax.set_title("Recall $\\neq$ behavioral supersession (drift cell)")

    # Family-marker legend in lower-right corner (empty region, no overlap
    # with reference lines or any data point).
    from matplotlib.lines import Line2D
    family_handles = [
        Line2D([0], [0], marker=family_marker[f], color="w",
               markerfacecolor=family_color[f], markeredgecolor="black",
               markersize=8, label=f)
        for f in ["wrapper", "long-context", "RAG", "graph"]
    ]
    ax.legend(handles=family_handles, loc="lower right", frameon=True,
              framealpha=0.95, edgecolor="#bbb",
              fontsize=7.5, title="Architectural family",
              title_fontsize=7.5, handletextpad=0.4, borderaxespad=0.6)

    fig.tight_layout()
    out = FIG_DIR / "fig4_recall_vs_vf.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out.relative_to(REPO)}")


def fig5_horizon_degradation() -> None:
    """Slope chart: per-system Δ VF along compact → standard → hard.

    Plot cumulative compact baseline + each transition delta."""
    rows = read_csv("horizon_paired_ci.csv")
    # Read also table5 for actual horizon-specific VF anchors
    t5 = {r["system"]: r for r in read_csv("table5_overall_vf.csv")}

    order = ["structured_sonnet", "long_context_sonnet46", "long_context_mistral",
             "sonnet_extract", "long_context_llama8b", "naive_rag",
             "graphiti"]
    colors = {
        "structured_sonnet": "#1f77b4",
        "long_context_sonnet46": "#ff7f0e",
        "long_context_mistral": "#2ca02c",
        "sonnet_extract": "#9467bd",
        "long_context_llama8b": "#d62728",
        "naive_rag": "#7f7f7f",
        "graphiti": "#8c564b",
    }

    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    x = [0, 1, 2]

    for sys in order:
        if sys not in t5:
            continue
        r = t5[sys]
        y = [float(r["compact_vf"]), float(r["standard_vf"]),
             float(r["hard_vf"])]
        ax.plot(x, y, "o-", color=colors[sys], linewidth=1.4, markersize=4.5,
                label=sys, alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels(["compact", "standard", "hard"])
    ax.set_xlabel("Horizon tier")
    ax.set_ylabel("Overall VF (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Horizon degradation by system (matched-triples paired)")
    ax.legend(loc="lower left", frameon=False, fontsize=6.5,
              ncol=2, columnspacing=0.8, handlelength=1.4)
    fig.tight_layout()
    out = FIG_DIR / "fig5_horizon_degradation.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.relative_to(REPO)}")


def main() -> int:
    print("Building paper figures from data/paper/*.csv ...\n")
    fig2_architecture_x_backbone()
    fig3_pattern_heatmap()
    fig4_recall_vs_vf()
    fig5_horizon_degradation()
    print(f"\nAll 4 PDFs written to {FIG_DIR.relative_to(REPO)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
