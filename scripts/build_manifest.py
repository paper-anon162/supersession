#!/usr/bin/env python3
"""Build a manifest from one or more pool JSONL files.

Loads every sample, optionally excludes ones flagged
``_gold.metadata.ambiguity_class != None``, groups by ``triple_id``
(falling back to ``sample_id`` for legacy samples without one), and
writes a ``pipeline.manifest.Manifest`` JSON to disk.

This is a structure builder, not a quota enforcer — protocol §9.2.2
proportional coverage and matched-triples completeness are checked by
``scripts/validate_manifest.py`` against the resulting manifest. Build
includes everything that passes the ambiguity / sample-type filter; if
the resulting manifest violates §9.2.2, that's a signal the pool is
too small or unbalanced, not a build-script bug.

Examples::

    # All clean samples, default settings
    uv run python scripts/build_manifest.py \\
        --name phase2_v5_main --version 1 \\
        data/realized_phase2_a_full.jsonl \\
        data/realized_phase2_b_full.jsonl

    # Including ambiguous samples for a debug manifest
    uv run python scripts/build_manifest.py \\
        --name phase2_v5_with_ambiguous --version 1 --include-ambiguous \\
        data/realized_phase2_a_full.jsonl data/realized_phase2_b_full.jsonl

    # Limit to specific sample types
    uv run python scripts/build_manifest.py \\
        --name supersession_only --version 1 --include-types supersession \\
        data/pool/*.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pipeline.cache import sample_content_hash  # noqa: E402
from pipeline.manifest import (  # noqa: E402
    Manifest,
    ManifestGroup,
    ManifestMember,
    write_manifest,
)
from pipeline.schema import Sample  # noqa: E402

DEFAULT_OUT_DIR = REPO / "data" / "manifests"


def _load_pool(paths: list[Path]) -> list[Sample]:
    # Later wins on duplicate sample_id, matching the runtime pool dedup
    # used by score_responses / incremental_benchmark. This keeps manifest
    # member hashes aligned with what those scripts will actually load.
    seen: dict[str, Sample] = {}
    for p in paths:
        with p.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                s = Sample.model_validate_json(line)
                seen[s.sample_id] = s
    return list(seen.values())


def _group_by_triple(samples: list[Sample]) -> dict[str, list[Sample]]:
    """Group samples by triple_id; fall back to sample_id for singletons."""
    groups: dict[str, list[Sample]] = defaultdict(list)
    for s in samples:
        tid = s.gold.metadata.triple_id or s.sample_id
        groups[tid].append(s)
    return groups


def _build_manifest(
    samples: list[Sample], *, name: str, version: str, selection_rule: str,
    notes: str | None,
) -> Manifest:
    groups: list[ManifestGroup] = []
    by_triple = _group_by_triple(samples)
    # Stable ordering: sort triple ids alphabetically, members by horizon
    # (compact → standard → hard → None) then by sample_id.
    horizon_order = {"compact": 0, "standard": 1, "hard": 2, None: 3}
    for tid in sorted(by_triple):
        members_raw = by_triple[tid]
        members_raw.sort(
            key=lambda s: (horizon_order.get(s.gold.metadata.horizon, 99), s.sample_id)
        )
        members = [
            ManifestMember(
                sample_id=s.sample_id,
                horizon=s.gold.metadata.horizon,
                sample_content_hash=sample_content_hash(s),
            )
            for s in members_raw
        ]
        groups.append(ManifestGroup(triple_id=tid, members=members))
    return Manifest(
        name=name,
        version=version,
        selection_rule=selection_rule,
        notes=notes,
        groups=groups,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pool", type=Path, nargs="+", help="One or more pool JSONL files.")
    ap.add_argument("--name", required=True, help="Manifest name (e.g. phase2_v5_main).")
    ap.add_argument("--version", default="1", help="Manifest version string.")
    ap.add_argument("--out", type=Path, default=None, help="Output path (default data/manifests/<name>.json).")
    ap.add_argument(
        "--include-ambiguous",
        action="store_true",
        help="Include samples flagged ambiguity_class != None (default: exclude).",
    )
    ap.add_argument(
        "--include-types",
        nargs="+",
        default=["supersession", "carryover"],
        help="Sample types to include (default: supersession + carryover).",
    )
    ap.add_argument(
        "--selection-rule",
        default="all_clean_samples_grouped_by_triple_id",
        help="Free-form description of how this manifest was built; recorded in the manifest.",
    )
    ap.add_argument("--notes", default=None)
    args = ap.parse_args(argv)

    samples = _load_pool(args.pool)
    print(f"loaded {len(samples)} samples from {len(args.pool)} pool file(s)")

    types_set = set(args.include_types)
    filtered: list[Sample] = []
    n_dropped_type = 0
    n_dropped_ambig = 0
    for s in samples:
        if s.sample_type not in types_set:
            n_dropped_type += 1
            continue
        if (
            not args.include_ambiguous
            and s.gold.metadata.ambiguity_class is not None
            and s.gold.metadata.ambiguity_class != "not_ambiguous"
        ):
            n_dropped_ambig += 1
            continue
        filtered.append(s)

    print(f"  dropped: {n_dropped_type} by sample_type filter, {n_dropped_ambig} by ambiguity filter")
    print(f"  kept   : {len(filtered)}")

    manifest = _build_manifest(
        filtered,
        name=args.name,
        version=args.version,
        selection_rule=args.selection_rule,
        notes=args.notes,
    )
    print(f"  groups : {manifest.n_groups}")
    print(f"  samples: {manifest.n_samples}")

    out_path = args.out or DEFAULT_OUT_DIR / f"{args.name}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(manifest, out_path)
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
