"""Enumerate (sample, system) pairs that are missing from a cache layer.

Useful before a partial re-run: pipe the output sample IDs into a runner
script's ``--sample-ids`` flag and only that subset will be (re)generated
or (re)judged.

Examples:

  # Which samples are missing a long_context_sonnet46 response?
  uv run python scripts/list_missing.py --layer responses \\
      --systems long_context_sonnet46

  # Which (sample, system) pairs have a response but no verdict yet?
  uv run python scripts/list_missing.py --layer verdicts \\
      --systems long_context_sonnet46,intervention_wrapper

  # Pipe straight into a runner
  IDS=$(uv run python scripts/list_missing.py --layer responses \\
          --systems long_context_sonnet46 --format ids-only)
  AWS_PROFILE=ahe-long uv run python scripts/run_closed_long_context.py \\
      --sample-ids "$IDS"

The "expected" set is the cross product of (loaded samples) × (systems
of interest). For verdicts, the expected set is the cross product of
(samples that have a response) × (systems of interest). Pass
``--all-systems`` to use every system seen in the response file.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from pipeline._runner_utils import enable_live_stdout
from pipeline.cache import load_cache_index
from pipeline.construction import load_all_seeds, materialize_all
from pipeline.io import iter_samples_from_jsonl

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"

DEFAULT_PHASE2_BATCH_FILES = (
    "realized_v1_full.jsonl",
    "realized_v2_full.jsonl",
    "realized_v3_full.jsonl",
    "realized_phase2_a_full.jsonl",
    "realized_phase2_b_full.jsonl",
    "realized_phase2_c_full.jsonl",
    "realized_phase2_d_full.jsonl",
    "realized_phase2_e_full.jsonl",
    "realized_phase2_g_full.jsonl",
    "realized_phase2_i_full.jsonl",
    "realized_phase2_j_full.jsonl",
    "realized_phase2_drift_v3_full.jsonl",
)

KNOWN_SYSTEMS = (
    "long_context_local",
    "naive_rag_local",
    "intervention_wrapper",
    "intervention_wrapper_drift_aware",
    "intervention_wrapper_drift_aware_sonnet_extract",
    "ablated_wrapper",
    "oracle_current_version",
    "query_only",
    "long_context_sonnet46",
    "long_context_mistral",
)


def _load_samples() -> list:
    samples = materialize_all(load_all_seeds())
    seen = {s.sample_id for s in samples}
    for f in DEFAULT_PHASE2_BATCH_FILES:
        fp = DATA / f
        if fp.exists():
            for s in iter_samples_from_jsonl(fp):
                if s.sample_id not in seen:
                    samples.append(s)
                    seen.add(s.sample_id)
    return samples


def main() -> int:
    enable_live_stdout()
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--layer",
        choices=("responses", "verdicts"),
        required=True,
        help="Which cache layer to audit.",
    )
    p.add_argument(
        "--systems",
        default=None,
        help="Comma-separated system names to require (default: all known systems).",
    )
    p.add_argument(
        "--all-systems",
        action="store_true",
        help="For --layer verdicts, include every system seen in the response file.",
    )
    p.add_argument(
        "--samples",
        default=None,
        help="Comma-separated sample IDs to restrict to. Default: all loaded samples.",
    )
    p.add_argument(
        "--responses-file",
        default=str(DATA / "benchmark_v1_responses.jsonl"),
        help="For --layer verdicts, the response file used to enumerate "
        "(sample, system) pairs. Default: data/benchmark_v1_responses.jsonl.",
    )
    p.add_argument(
        "--format",
        choices=("ids-only", "table", "tuples"),
        default="table",
        help="ids-only: comma-separated sample_ids; tuples: 'sample\\tsystem' lines; "
        "table: human-readable count summary plus details (default).",
    )
    args = p.parse_args()

    if args.systems:
        systems = tuple(s.strip() for s in args.systems.split(",") if s.strip())
    else:
        systems = KNOWN_SYSTEMS

    samples = _load_samples()
    if args.samples:
        keep = {s.strip() for s in args.samples.split(",") if s.strip()}
        samples = [s for s in samples if s.sample_id in keep]
    if not samples:
        print("ERROR: no samples loaded", file=sys.stderr)
        return 2

    sample_ids = [s.sample_id for s in samples]

    # Build the "expected" set of (sample, system) pairs.
    expected: set[tuple[str, str]] = set()
    if args.layer == "responses":
        for sid in sample_ids:
            for sys_name in systems:
                expected.add((sid, sys_name))
    else:
        # verdicts: every (sample, system) that has a response
        responses = []
        rp = Path(args.responses_file)
        if not rp.exists():
            print(f"ERROR: --responses-file not found: {rp}", file=sys.stderr)
            return 2
        for line in rp.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            responses.append((obj["sample_id"], obj["system_name"]))
        if args.all_systems:
            seen_systems = sorted({s for _, s in responses})
            systems = tuple(seen_systems)
        sid_set = set(sample_ids)
        for sid, sys_name in responses:
            if sid not in sid_set:
                continue
            if sys_name not in systems:
                continue
            expected.add((sid, sys_name))

    # What we have in the cache.
    cache_dir = DATA / "cache" / args.layer
    cache_idx = load_cache_index(cache_dir)
    have: set[tuple[str, str]] = set()
    for row in cache_idx.rows.values():
        sid = row.get("sample_id")
        sys_name = row.get("system_name")
        if sid and sys_name:
            have.add((sid, sys_name))

    missing = sorted(expected - have)

    if args.format == "ids-only":
        # Comma-separated sample_ids (de-duplicated).
        ids = sorted({sid for sid, _ in missing})
        print(",".join(ids))
        return 0
    if args.format == "tuples":
        for sid, sys_name in missing:
            print(f"{sid}\t{sys_name}")
        return 0

    # Table format
    print(f"Layer: {args.layer}")
    print(f"Cache rows loaded: {len(cache_idx)}")
    print(f"Samples in scope:  {len(samples)}")
    print(f"Systems in scope:  {len(systems)}")
    print(f"Expected pairs:    {len(expected)}")
    print(f"Have pairs:        {len(expected & have)}")
    print(f"Missing pairs:     {len(missing)}")
    if not missing:
        print("\nNothing missing.")
        return 0
    print("\nMissing by system:")
    by_sys: dict[str, list[str]] = defaultdict(list)
    for sid, sys_name in missing:
        by_sys[sys_name].append(sid)
    for sys_name in sorted(by_sys):
        ids = by_sys[sys_name]
        head = ", ".join(ids[:6])
        more = f", ... (+{len(ids) - 6} more)" if len(ids) > 6 else ""
        print(f"  {sys_name:30s} {len(ids):3d} missing  [{head}{more}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
