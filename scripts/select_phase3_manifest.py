"""Phase 3 manifest selector — read group pool, apply locked rules, write manifest.

Reads ``data/pool/phase3_groups.jsonl`` and produces:

  - ``data/manifests/phase3_main.json``       — selected groups
  - ``reports/phase3/selection_report.json``  — picks + cell counts + underfills

The selector is **deterministic**, **rule-locked**, and **never reads
model responses or VF verdicts**. The same input pool always produces
the same output manifest.

Selection rules (locked per protocol §10.2 + §10.5):

  - Hard count targets per failure_pattern × group_type:
      implicit_drift   triples 120, doublets 0
      narrowing        triples 70,  doublets 0
      explicit_replac. triples 50,  doublets 0
      multi_version    triples 60,  doublets 50
      total            triples 300, doublets 50  =  1000 samples

  - implicit_drift sub-targets (sum to 120 triples):
      repeated_use      60
      abandonment       40
      gradual_narrowing 20

  - Topic-group cap: no topic_group exceeds 50% of any
    (failure_pattern × horizon) cell.

  - Target-type hard constraint: non-object target types ≥ 50% of
    selected groups (counting per group, not per sample, since all
    members of a group share target_type).

  - Ambiguity hard constraint: only groups whose members all carry
    ambiguity_class ∈ {None, "not_ambiguous"} are eligible.

Greedy fill order (most-scarce buckets first):

  1. implicit_drift / gradual_narrowing  (target 20)
  2. implicit_drift / abandonment        (target 40)
  3. multi_version  / doublet            (target 50)
  4. explicit_replacement / triple       (target 50)
  5. implicit_drift / repeated_use       (target 60)
  6. multi_version  / triple             (target 60)
  7. narrowing      / triple             (target 70)

Within each bucket, candidates are scored:

  - primary: penalize candidates whose acceptance would push any
    occupied (failure_pattern × horizon) cell over the 50%
    topic-group cap (penalty = 1 per cell breached);
  - secondary: prefer candidates whose target_type is currently
    under-represented in the running selection (count balance);
  - tiebreaker: lexicographic group_id.

Underfill is reported (not silently truncated). The selector exits
with code 1 if any bucket underfills or the non-object hard
constraint isn't met.

Usage:

    uv run python scripts/select_phase3_manifest.py [--pool path] [--out path]

The default paths match the production layout.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
DEFAULT_POOL = DATA / "pool" / "phase3_groups.jsonl"
DEFAULT_MANIFEST = DATA / "manifests" / "phase3_main.json"
DEFAULT_REPORT = REPO / "reports" / "phase3" / "selection_report.json"


# Rule lock — protocol §10.2 / §10.5. Bumping any number here should be
# accompanied by a protocol amendment.
TARGET_GROUPS_BY_BUCKET: dict[tuple[str, str, str | None], int] = {
    # (failure_pattern, group_type, implicit_drift_type) -> target group count
    ("implicit_drift", "triple", "gradual_narrowing"): 20,
    ("implicit_drift", "triple", "abandonment"): 40,
    ("multi_version", "doublet", None): 50,
    ("explicit_replacement", "triple", None): 50,
    ("implicit_drift", "triple", "repeated_use"): 60,
    ("multi_version", "triple", None): 60,
    ("narrowing", "triple", None): 70,
}
# Filling order (scarcest first). Insertion order in TARGET_GROUPS_BY_BUCKET
# above is exactly this order.
FILL_ORDER = list(TARGET_GROUPS_BY_BUCKET.keys())

TOPIC_GROUP_CELL_CAP = 0.50  # protocol §10.5
NON_OBJECT_FLOOR = 0.50  # protocol §10.3
RULE_VERSION = "v1.0-2026-04-26"

# Object target_type — anything else counts as "non-object" for §10.3.
OBJECT_TARGET_TYPES = {"object_preference"}


@dataclass
class PoolGroup:
    group_id: str
    group_type: str  # triple / doublet
    failure_pattern: str
    implicit_drift_type: str | None
    members: list[dict]  # raw dicts as written to pool
    topic_groups_per_horizon: dict[str, str]  # horizon -> topic_group
    target_type: str  # all members share
    ambiguous: bool
    spine_source: str
    rule_version: str

    @classmethod
    def from_pool_record(cls, rec: dict) -> "PoolGroup":
        topic_groups_per_horizon: dict[str, str] = {}
        ambiguous = False
        target_types: set[str] = set()
        for m in rec.get("members", []):
            topic_groups_per_horizon[m["horizon"]] = m.get("topic_group") or "daily_preference"
            target_types.add(m.get("target_type") or "object_preference")
            ac = m.get("ambiguity_class")
            if ac is not None and ac != "not_ambiguous":
                ambiguous = True
        # All members of a group share target_type by spec; if not, log
        # the inconsistency and pick the first.
        target_type = sorted(target_types)[0] if target_types else "object_preference"
        return cls(
            group_id=rec["group_id"],
            group_type=rec["group_type"],
            failure_pattern=rec.get("failure_pattern") or "",
            implicit_drift_type=rec.get("implicit_drift_type"),
            members=rec.get("members", []),
            topic_groups_per_horizon=topic_groups_per_horizon,
            target_type=target_type,
            ambiguous=ambiguous,
            spine_source=rec.get("spine_source") or "hand",
            rule_version=rec.get("rule_version") or "",
        )

    def bucket_key(self) -> tuple[str, str, str | None]:
        return (
            self.failure_pattern,
            self.group_type,
            self.implicit_drift_type,
        )


def _load_pool(path: Path) -> list[PoolGroup]:
    if not path.exists():
        raise SystemExit(f"pool file not found: {path}")
    out: list[PoolGroup] = []
    seen: set[str] = set()
    for line in path.open():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        gid = rec.get("group_id")
        if not gid or gid in seen:
            continue  # pool can have duplicates from interrupted runs; first wins
        seen.add(gid)
        out.append(PoolGroup.from_pool_record(rec))
    return out


def _apply_cluster_L_filter(
    groups: list[PoolGroup],
    realized_path: Path,
) -> tuple[list[PoolGroup], dict[str, list[str]]]:
    """Drop members whose realized sample fails cluster L (intermediate
    version coverage). Cluster L scope is compact-horizon non-drift —
    where the realizer-drops-a-version-turn bug clusters per the
    2026-04-27 blind-extraction audit.

    Returns (filtered_groups, dropped_sample_ids_by_group).

    Per-MEMBER drop: a triple that loses its compact member becomes a
    two-member group (effectively a doublet for downstream purposes);
    a group that loses ≥half its members or all members is rejected
    entirely.
    """
    if not realized_path.exists():
        return groups, {}

    # Lazy index: load only the sample_ids we care about.
    needed_ids: set[str] = set()
    for g in groups:
        for m in g.members:
            sid = m.get("sample_id")
            if sid:
                needed_ids.add(sid)

    # Stream the realized file, keeping only the records we need.
    from pipeline.schema import Sample
    from pipeline.construction.audit_gold_consistency import (
        check_cluster_L_intermediate_version_coverage,
    )

    cluster_L_drops: set[str] = set()
    with realized_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            sid = d.get("sample_id")
            if sid not in needed_ids:
                continue
            sample = Sample.model_validate(d)
            finding = check_cluster_L_intermediate_version_coverage(sample)
            if finding is not None:
                cluster_L_drops.add(sid)

    if not cluster_L_drops:
        return groups, {}

    out: list[PoolGroup] = []
    dropped_by_group: dict[str, list[str]] = {}
    for g in groups:
        kept = [m for m in g.members if m.get("sample_id") not in cluster_L_drops]
        dropped = [m.get("sample_id") for m in g.members if m.get("sample_id") in cluster_L_drops]
        if dropped:
            dropped_by_group[g.group_id] = dropped
        if len(kept) < 2:
            # Rejecting the whole group — too few survivors for
            # matched-pair analysis. (Doublet floor is 2 per protocol.)
            continue
        # Recompute per-horizon topic groups only over surviving members.
        new_topic = {m["horizon"]: (m.get("topic_group") or "daily_preference") for m in kept}
        # If we dropped the compact and started from triple, the group
        # is effectively a doublet for downstream selection. Mark it
        # so quotas count correctly.
        new_group_type = g.group_type
        surviving_horizons = {m["horizon"] for m in kept}
        if g.group_type == "triple" and "compact" not in surviving_horizons:
            new_group_type = "doublet"
        new_g = PoolGroup(
            group_id=g.group_id,
            group_type=new_group_type,
            failure_pattern=g.failure_pattern,
            implicit_drift_type=g.implicit_drift_type,
            members=kept,
            topic_groups_per_horizon=new_topic,
            target_type=g.target_type,
            ambiguous=g.ambiguous,
            spine_source=g.spine_source,
            rule_version=g.rule_version,
        )
        out.append(new_g)
    return out, dropped_by_group


@dataclass
class SelectorState:
    """Running tallies the greedy selector consults when scoring
    candidates."""

    selected: list[PoolGroup]
    # (failure_pattern, horizon) -> topic_group -> count
    topic_cells: dict[tuple[str, str], Counter]
    target_type_count: Counter
    bucket_count: Counter

    @classmethod
    def empty(cls) -> "SelectorState":
        return cls(
            selected=[],
            topic_cells=defaultdict(Counter),
            target_type_count=Counter(),
            bucket_count=Counter(),
        )

    def add(self, g: PoolGroup) -> None:
        self.selected.append(g)
        for horizon, tg in g.topic_groups_per_horizon.items():
            self.topic_cells[(g.failure_pattern, horizon)][tg] += 1
        self.target_type_count[g.target_type] += 1
        self.bucket_count[g.bucket_key()] += 1


def _score_candidate(
    cand: PoolGroup,
    state: SelectorState,
    bucket_target: int,
) -> tuple[int, int, str]:
    """Return a sort key. Lower is better.

    Components (in priority order):
      1. cells_breaching_cap: number of (failure_pattern × horizon)
         cells that would exceed 50% topic_group share if cand were
         accepted. Hard penalty.
      2. target_type_balance: deviation from balanced target-type
         counts (favours under-represented types).
      3. group_id (lexicographic) — deterministic tiebreaker.
    """
    breaches = 0
    for horizon, tg in cand.topic_groups_per_horizon.items():
        cell = state.topic_cells[(cand.failure_pattern, horizon)]
        # Predicted new count of cand's topic_group / predicted cell total
        new_tg_count = cell[tg] + 1
        new_total = sum(cell.values()) + 1
        # Compare to bucket target (proxy for final cell total at completion)
        # This is approximate — actual cell total ends near bucket_target,
        # but smaller during fill. Use the larger of (new_total, bucket_target/n_horizons)
        # to avoid noise penalising the very first picks per bucket.
        denom = max(new_total, max(1, bucket_target // 3))
        if new_tg_count / denom > TOPIC_GROUP_CELL_CAP:
            breaches += 1
    # Target-type balance: how many groups have this target_type already?
    # We want non-object types to have parity. Prefer the under-represented one.
    tt_balance = state.target_type_count[cand.target_type]
    return (breaches, tt_balance, cand.group_id)


def _select_bucket(
    bucket: tuple[str, str, str | None],
    target: int,
    pool: list[PoolGroup],
    selected_ids: set[str],
    state: SelectorState,
) -> tuple[list[PoolGroup], int]:
    """Greedy-select up to `target` groups from `pool` matching
    `bucket`. Returns (selected_picks, underfill)."""
    candidates = [
        g for g in pool
        if g.bucket_key() == bucket
        and not g.ambiguous
        and g.group_id not in selected_ids
    ]
    picks: list[PoolGroup] = []
    while len(picks) < target and candidates:
        candidates.sort(key=lambda g: _score_candidate(g, state, target))
        winner = candidates.pop(0)
        picks.append(winner)
        state.add(winner)
        selected_ids.add(winner.group_id)
    underfill = max(0, target - len(picks))
    return picks, underfill


def select_phase3(pool: list[PoolGroup]) -> dict:
    """Apply rule-locked greedy selection. Returns a structured result
    with manifest + report payloads."""
    state = SelectorState.empty()
    selected_ids: set[str] = set()
    bucket_results: list[dict] = []

    for bucket in FILL_ORDER:
        target = TARGET_GROUPS_BY_BUCKET[bucket]
        picks, underfill = _select_bucket(bucket, target, pool, selected_ids, state)
        bucket_results.append({
            "bucket": list(bucket),
            "target": target,
            "picked": len(picks),
            "underfill": underfill,
            "picked_group_ids": [g.group_id for g in picks],
        })

    # Hard-constraint check: non-object ≥ 50% of selected groups.
    n_selected = len(state.selected)
    if n_selected:
        n_non_object = sum(
            1 for g in state.selected if g.target_type not in OBJECT_TARGET_TYPES
        )
        non_object_share = n_non_object / n_selected
    else:
        non_object_share = 0.0

    # Ambiguity check (defense-in-depth; selector already filters).
    has_ambiguous = any(g.ambiguous for g in state.selected)

    # Topic-cell breach summary post-hoc: with the running approximation
    # in the scorer, recompute against final counts for the report.
    final_cells: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for g in state.selected:
        for horizon, tg in g.topic_groups_per_horizon.items():
            final_cells[f"{g.failure_pattern}|{horizon}"][tg] += 1
    final_breaches: list[dict] = []
    for cell_key, tally in final_cells.items():
        total = sum(tally.values())
        if total == 0:
            continue
        for tg, c in tally.items():
            share = c / total
            if share > TOPIC_GROUP_CELL_CAP:
                final_breaches.append({
                    "cell": cell_key,
                    "topic_group": tg,
                    "share": round(share, 3),
                    "count": c,
                    "cell_total": total,
                })

    total_underfill = sum(b["underfill"] for b in bucket_results)
    samples_by_horizon: Counter = Counter()
    for g in state.selected:
        for m in g.members:
            samples_by_horizon[m["horizon"]] += 1

    return {
        "selected": state.selected,
        "bucket_results": bucket_results,
        "total_groups": n_selected,
        "total_samples": sum(samples_by_horizon.values()),
        "samples_by_horizon": dict(samples_by_horizon),
        "non_object_share": round(non_object_share, 3),
        "non_object_pass": non_object_share >= NON_OBJECT_FLOOR,
        "topic_cell_breaches": final_breaches,
        "topic_cell_breach_pass": len(final_breaches) == 0,
        "ambiguity_pass": not has_ambiguous,
        "total_underfill_groups": total_underfill,
        "underfill_pass": total_underfill == 0,
    }


def _build_manifest(result: dict, realized_path: Path | None = None) -> dict:
    """Emit the canonical ``pipeline.manifest.Manifest`` shape.

    Per `pipeline/manifest.py` (Pydantic model with `extra="forbid"`):
      Manifest:
        name: str
        version: str
        selection_rule: str
        notes: str | None
        groups: list[ManifestGroup]

      ManifestGroup:
        triple_id: str
        members: list[ManifestMember]

      ManifestMember:
        sample_id: str
        horizon: Horizon | None
        sample_content_hash: str | None

    Phase 3-specific group metadata (failure_pattern, implicit_drift_type,
    group_type, subtype) lives in the **sidecar** report
    (``selection_report.json``) — this manifest stays protocol-canonical
    so ``load_manifest`` can read it directly.

    ``sample_content_hash`` is computed from the realized sample's full
    record using the same hasher as Phase 2, so downstream
    ``validate_phase3_manifest`` can verify the pool sample hasn't drifted.
    """
    # Lazy hash lookup — only loaded if realized_path is given. Lets the
    # selector run even before realization is complete (smoke test path).
    hashes: dict[str, str | None] = {}
    if realized_path is not None and realized_path.exists():
        try:
            from pipeline.cache import sample_content_hash  # type: ignore[attr-defined]
            from pipeline.schema import Sample  # type: ignore[attr-defined]
        except Exception:
            sample_content_hash = None
            Sample = None
        if sample_content_hash is not None:
            with open(realized_path) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    sid = d.get("sample_id")
                    if not sid:
                        continue
                    try:
                        s = Sample.model_validate(d) if Sample else None
                        hashes[sid] = sample_content_hash(s) if s else None
                    except Exception:
                        hashes[sid] = None
    return {
        "name": "phase3_main",
        "version": "1",
        "selection_rule": (
            "phase3_greedy_rule_locked_v1 "
            f"(rule_version={RULE_VERSION})"
        ),
        "notes": (
            "Phase 3 main set per protocol §10.2 (v1.3.7). "
            "Per-group failure_pattern / implicit_drift_type / group_type "
            "metadata lives in the sidecar selection_report.json, keyed by "
            "triple_id."
        ),
        "groups": [
            {
                "triple_id": g.group_id,
                "members": [
                    {
                        "sample_id": m["sample_id"],
                        "horizon": m["horizon"],
                        "sample_content_hash": hashes.get(m["sample_id"]),
                    }
                    for m in g.members
                ],
            }
            for g in result["selected"]
        ],
    }


def _build_report(result: dict, pool_size: int) -> dict:
    return {
        "rule_version": RULE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pool_size": pool_size,
        "selected_groups": result["total_groups"],
        "selected_samples": result["total_samples"],
        "samples_by_horizon": result["samples_by_horizon"],
        "non_object_share": result["non_object_share"],
        "non_object_pass": result["non_object_pass"],
        "topic_cell_breaches": result["topic_cell_breaches"],
        "topic_cell_breach_pass": result["topic_cell_breach_pass"],
        "ambiguity_pass": result["ambiguity_pass"],
        "total_underfill_groups": result["total_underfill_groups"],
        "underfill_pass": result["underfill_pass"],
        "buckets": result["bucket_results"],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pool", default=str(DEFAULT_POOL), type=Path)
    p.add_argument("--manifest-out", default=str(DEFAULT_MANIFEST), type=Path)
    p.add_argument("--report-out", default=str(DEFAULT_REPORT), type=Path)
    p.add_argument(
        "--allow-underfill", action="store_true",
        help="Write the manifest + report even if buckets underfill or "
             "constraints fail. Without this flag, underfill or constraint "
             "failure causes the selector to write the report (so you can "
             "see what failed) but exit non-zero and skip manifest write.",
    )
    p.add_argument(
        "--realized-path",
        default=str(DATA / "dataset/realized_phase3_full.jsonl"), type=Path,
        help="Realized samples file used to apply the cluster L per-member "
             "drop. Pass --skip-cluster-L to disable.",
    )
    p.add_argument(
        "--skip-cluster-L", action="store_true",
        help="Skip the cluster L per-member drop. Use only when you "
             "explicitly want unfiltered pool selection.",
    )
    args = p.parse_args()

    pool = _load_pool(args.pool)
    print(f"Pool: {len(pool)} groups loaded from {args.pool}")
    if not args.skip_cluster_L:
        pool, dropped_by_group = _apply_cluster_L_filter(pool, args.realized_path)
        if dropped_by_group:
            n_members = sum(len(v) for v in dropped_by_group.values())
            n_groups_full_drop = sum(
                1 for v in dropped_by_group.values() if not v  # never empty here, kept for symmetry
            )
            print(
                f"Cluster L filter: dropped {n_members} members across "
                f"{len(dropped_by_group)} groups; {len(pool)} groups remain "
                f"(triples that lost compact downgraded to doublet)."
            )

    result = select_phase3(pool)

    print()
    print(f"Selected {result['total_groups']} groups, {result['total_samples']} samples")
    print(f"  by horizon: {result['samples_by_horizon']}")
    print(f"  non-object share: {result['non_object_share']*100:.1f}% "
          f"(floor {NON_OBJECT_FLOOR*100:.0f}% — {'pass' if result['non_object_pass'] else 'FAIL'})")
    print(f"  topic-cell breaches: {len(result['topic_cell_breaches'])} "
          f"({'pass' if result['topic_cell_breach_pass'] else 'FAIL'})")
    print(f"  ambiguity check: {'pass' if result['ambiguity_pass'] else 'FAIL'}")
    print(f"  total underfill: {result['total_underfill_groups']} groups "
          f"({'pass' if result['underfill_pass'] else 'FAIL'})")
    print()
    print("Per-bucket fill:")
    for b in result["bucket_results"]:
        bucket_label = "/".join(str(x) for x in b["bucket"] if x)
        status = "✓" if b["underfill"] == 0 else f"UNDERFILL by {b['underfill']}"
        print(f"  {bucket_label:60} {b['picked']:3}/{b['target']:3}  {status}")

    # Write report (always — useful even on failure).
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(_build_report(result, len(pool)), indent=2))
    print(f"\nReport: {args.report_out}")

    # Decide on manifest write.
    all_pass = (
        result["non_object_pass"]
        and result["topic_cell_breach_pass"]
        and result["ambiguity_pass"]
        and result["underfill_pass"]
    )
    if all_pass or args.allow_underfill:
        args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
        manifest = _build_manifest(result, realized_path=args.realized_path)
        args.manifest_out.write_text(json.dumps(manifest, indent=2))
        print(f"Manifest: {args.manifest_out}")
        if not all_pass:
            print("(written despite constraint failures because --allow-underfill was set)")
    else:
        print(
            "Manifest NOT written. Constraint failures above; pass "
            "--allow-underfill to write anyway, or generate more pool "
            "groups and re-run."
        )
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
