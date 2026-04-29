"""Phase 3 group-pool realize driver (protocol §10).

Loads a list of Phase3GroupSpec values from a Python module, realizes
each as a group (matched triple or doublet), runs the full cluster
A–J validation, and **appends accepted groups to the group-level
pool**:

  - data/dataset/realized_phase3_full.jsonl     — accepted samples (append-only)
  - data/dataset/realized_phase3_public.jsonl   — public-only view
  - data/dataset/realized_phase3_gold.jsonl     — gold-only view
  - data/pool/phase3_groups.jsonl       — one record per accepted group

Manifest construction is a separate step (`scripts/select_phase3_manifest.py`)
that reads the pool, applies the locked selection rules, and writes
`data/manifests/phase3_main.json`. This separation gives:

  - global topic-balance enforcement (selector sees the full pool)
  - audit story: generation and selection decoupled, rules
    pre-locked, no model-response visibility
  - p-hacking defense: selector cannot read VF / verdicts

Failed groups land in ``data/cache/phase3/failed/<group_id>.json``
for debugging — never selectable.

Usage:

    AWS_PROFILE=ahe-long uv run python scripts/realize_phase3.py \\
        --batch starter \\
        --workers 6

The driver is **incremental**: cached accepted groups under the
active rule version are skipped; failed groups are re-attempted only
when ``--retry-failed`` is passed; ``--ignore-cache`` re-runs
everything and stamps the new rule version.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from pipeline._runner_utils import enable_live_stdout, print_eta_banner
from pipeline.construction.phase3 import (
    PHASE3_RULE_VERSION,
    Phase3GroupResult,
    Phase3GroupSpec,
    realize_phase3_group,
)
from pipeline.evaluation.bedrock_backbone import BedrockBackbone
from pipeline.io import write_gold_jsonl, write_public_jsonl, write_samples_jsonl

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
REPORTS = REPO / "reports" / "phase3"
CACHE_DIR = DATA / "cache" / "phase3"
ACCEPTED_DIR = CACHE_DIR / "accepted"
FAILED_DIR = CACHE_DIR / "failed"
POOL_DIR = DATA / "pool"
POOL_PATH = POOL_DIR / "phase3_groups.jsonl"
FULL_PATH = DATA / "dataset/realized_phase3_full.jsonl"
PUBLIC_PATH = DATA / "dataset/realized_phase3_public.jsonl"
GOLD_PATH = DATA / "dataset/realized_phase3_gold.jsonl"


# Map of batch name → (module path, attribute returning list[Phase3GroupSpec]).
BATCH_MODULES: dict[str, tuple[str, str]] = {
    # Smoke batch is a tiny hand-authored set for end-to-end testing.
    "smoke": ("seeds.phase3._batch_smoke", "PHASE3_SMOKE"),
    # Starter batch: 10 spines covering all 4 patterns + 3 drift types.
    "starter": ("seeds.phase3._batch_starter", "PHASE3_STARTER"),
    # Batch A: 15 spines targeting communication_boundary +
    # learning_routine, biased toward non-object target_types.
    "a_comm_learn": ("seeds.phase3._batch_a_comm_learn", "PHASE3_BATCH_A"),
    # Batch B: 15 spines targeting cell breaches (multi doublets,
    # gradual_narrowing, explicit/narrow non-dominant topics).
    "b_breach_fill": ("seeds.phase3._batch_b_breach_fill", "PHASE3_BATCH_B"),
    # Batch C: 20 spines targeting deepest underfills (repeated_use,
    # narrow, multi triple/doublet, abandonment).
    "c_deeper": ("seeds.phase3._batch_c_deeper", "PHASE3_BATCH_C"),
    # Batches D / E / F: continue scaling toward 350. Same balanced
    # distribution as C; topic + target_type rotation.
    "d": ("seeds.phase3._batch_d", "PHASE3_BATCH_D"),
    "e": ("seeds.phase3._batch_e", "PHASE3_BATCH_E"),
    "f": ("seeds.phase3._batch_f", "PHASE3_BATCH_F"),
    # Batch G: 20 spines biased work_tooling / communication_boundary /
    # learning_routine to fix daily_preference cell breach from d/e/f.
    "g": ("seeds.phase3._batch_g", "PHASE3_BATCH_G"),
    # Batch H: 25 spines, narrow + multi heavy.
    "h": ("seeds.phase3._batch_h", "PHASE3_BATCH_H"),
    "i": ("seeds.phase3._batch_i", "PHASE3_BATCH_I"),
    "j": ("seeds.phase3._batch_j", "PHASE3_BATCH_J"),
    "k": ("seeds.phase3._batch_k", "PHASE3_BATCH_K"),
    "l": ("seeds.phase3._batch_l", "PHASE3_BATCH_L"),
    "m": ("seeds.phase3._batch_m", "PHASE3_BATCH_M"),
    "n": ("seeds.phase3._batch_n", "PHASE3_BATCH_N"),
    "o": ("seeds.phase3._batch_o", "PHASE3_BATCH_O"),
    "p": ("seeds.phase3._batch_p", "PHASE3_BATCH_P"),
    "q": ("seeds.phase3._batch_q", "PHASE3_BATCH_Q"),
    "r": ("seeds.phase3._batch_r", "PHASE3_BATCH_R"),
    "s": ("seeds.phase3._batch_s", "PHASE3_BATCH_S"),
    "t": ("seeds.phase3._batch_t", "PHASE3_BATCH_T"),
    "u": ("seeds.phase3._batch_u", "PHASE3_BATCH_U"),
    "v": ("seeds.phase3._batch_v", "PHASE3_BATCH_V"),
    "w": ("seeds.phase3._batch_w", "PHASE3_BATCH_W"),
    "x": ("seeds.phase3._batch_x", "PHASE3_BATCH_X"),
    "y": ("seeds.phase3._batch_y", "PHASE3_BATCH_Y"),
    "z": ("seeds.phase3._batch_z", "PHASE3_BATCH_Z"),
    "aa": ("seeds.phase3._batch_aa", "PHASE3_BATCH_AA"),
    "ab": ("seeds.phase3._batch_ab", "PHASE3_BATCH_AB"),
    "ac": ("seeds.phase3._batch_ac", "PHASE3_BATCH_AC"),
    "ad": ("seeds.phase3._batch_ad", "PHASE3_BATCH_AD"),
    "ae": ("seeds.phase3._batch_ae", "PHASE3_BATCH_AE"),
    "af": ("seeds.phase3._batch_af", "PHASE3_BATCH_AF"),
    "ag": ("seeds.phase3._batch_ag", "PHASE3_BATCH_AG"),
    "ah": ("seeds.phase3._batch_ah", "PHASE3_BATCH_AH"),
}


def _load_batch(batch: str) -> list[Phase3GroupSpec]:
    if batch not in BATCH_MODULES:
        raise ValueError(
            f"unknown phase 3 batch {batch!r}; expected one of {list(BATCH_MODULES)}"
        )
    mod_path, attr = BATCH_MODULES[batch]
    mod = importlib.import_module(mod_path)
    return getattr(mod, attr)


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------


def _cache_path(group_id: str, accepted: bool) -> Path:
    sub = ACCEPTED_DIR if accepted else FAILED_DIR
    sub.mkdir(parents=True, exist_ok=True)
    safe = group_id.replace("/", "__")
    return sub / f"{safe}.json"


def _is_cached_accepted(group_id: str) -> bool:
    """True if there's an accepted-cache entry for this group under
    the active rule version."""
    p = _cache_path(group_id, accepted=True)
    if not p.exists():
        return False
    try:
        d = json.loads(p.read_text())
    except json.JSONDecodeError:
        return False
    return d.get("rule_version") == PHASE3_RULE_VERSION


def _is_cached_failed(group_id: str) -> bool:
    p = _cache_path(group_id, accepted=False)
    if not p.exists():
        return False
    try:
        d = json.loads(p.read_text())
    except json.JSONDecodeError:
        return False
    return d.get("rule_version") == PHASE3_RULE_VERSION


def _write_cache(result: Phase3GroupResult) -> None:
    p = _cache_path(result.spec.group_id, accepted=result.accepted)
    payload = {
        "group_id": result.spec.group_id,
        "group_type": result.spec.group_type,
        "horizons": result.spec.horizons,
        "spine_source": result.spec.spine_source,
        "implicit_drift_type": result.spec.implicit_drift_type,
        "accepted": result.accepted,
        "rule_version": result.rule_version,
        "evidence_prompt_version": result.evidence_prompt_version,
        "members": [
            {
                "horizon": m.horizon,
                "accepted": m.accepted,
                "failure_reason": m.failure_reason,
                "realize_attempts": m.realize_attempts,
                "evidence_attempts": m.evidence_attempts,
                "elapsed_s": m.elapsed_s,
                "sample_id": m.sample.sample_id if m.sample else None,
            }
            for m in result.members
        ],
        "failure_reasons": result.failure_reasons,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    p.write_text(json.dumps(payload, indent=2, default=str))


# ---------------------------------------------------------------------------
# Manifest + sample I/O (append-only)
# ---------------------------------------------------------------------------


_REALIZED_SID_CACHE: set[str] | None = None


def _load_realized_sids() -> set[str]:
    """Lazy-load (and cache) the set of sample_ids already present in
    ``realized_phase3_full.jsonl``. Used by ``_append_samples`` to skip
    samples that would otherwise become duplicate lines (the prior
    failure mode that produced 18 dupes from retry runs in
    2026-04-27)."""
    global _REALIZED_SID_CACHE
    if _REALIZED_SID_CACHE is not None:
        return _REALIZED_SID_CACHE
    out: set[str] = set()
    if FULL_PATH.exists():
        with FULL_PATH.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    sid = json.loads(line).get("sample_id")
                except Exception:
                    continue
                if sid:
                    out.add(sid)
    _REALIZED_SID_CACHE = out
    return out


def _append_samples(samples: list) -> None:
    """Append samples to the three Phase 3 jsonl files. Each invocation
    is atomic at the line level (no group-level lock needed across
    files since writes are append-only).

    Skips samples whose sample_id already exists in
    ``realized_phase3_full.jsonl`` — prevents duplicate lines when a
    retry path re-realizes a group already in the realized files.
    The duplicate filter uses a lazily-built in-memory set updated as
    samples are written, so within a single process new appends from
    earlier batches are remembered and not re-appended.
    """
    if not samples:
        return
    DATA.mkdir(parents=True, exist_ok=True)
    seen_sids = _load_realized_sids()
    fresh = [s for s in samples if s.sample_id not in seen_sids]
    if not fresh:
        return
    # write_samples_jsonl / write_public / write_gold all open in
    # 'w' mode by default — we want append. Re-implement append here.
    from pipeline.io.loaders import (
        PUBLIC_FIELDS,
        _public_view,  # type: ignore[attr-defined]
    )

    with FULL_PATH.open("a") as f:
        for s in fresh:
            d = s.model_dump(by_alias=True)
            f.write(json.dumps(d, ensure_ascii=False, default=str) + "\n")
    with PUBLIC_PATH.open("a") as f:
        for s in fresh:
            f.write(
                json.dumps(_public_view(s, PUBLIC_FIELDS), ensure_ascii=False, default=str)
                + "\n"
            )
    with GOLD_PATH.open("a") as f:
        for s in fresh:
            d = s.model_dump(by_alias=True)
            gold_only = {"sample_id": s.sample_id, "_gold": d["_gold"]}
            f.write(json.dumps(gold_only, ensure_ascii=False, default=str) + "\n")
    # Update the cache so subsequent appends in the same process know
    # these sids are now in the file.
    seen_sids.update(s.sample_id for s in fresh)


def _pool_record(result: Phase3GroupResult) -> dict:
    """Build the group-level pool record. Captures everything the
    selector needs to make a rule-locked manifest pick — without
    reading the (possibly large) realized sample files."""
    accepted_members = [
        m for m in result.members if m.accepted and m.sample is not None
    ]
    members_payload = []
    for m in accepted_members:
        md = m.sample.gold.metadata
        members_payload.append({
            "sample_id": m.sample.sample_id,
            "horizon": m.horizon,
            "topic_group": md.topic_group,
            "target_type": md.gold_target_type,
            "ambiguity_class": md.ambiguity_class,
            "domain": md.domain,
            "history_token_count": md.history_token_count,
        })
    primary_pattern = (
        result.spec.spine.failure_patterns[0]
        if result.spec.spine.failure_patterns
        else None
    )
    return {
        "group_id": result.spec.group_id,
        "group_type": result.spec.group_type,
        "horizons": result.spec.horizons,
        "failure_pattern": primary_pattern,
        "subtype": result.spec.spine.subtype,
        "implicit_drift_type": result.spec.implicit_drift_type,
        "spine_source": result.spec.spine_source,
        "members": members_payload,
        "rule_version": result.rule_version,
        "evidence_prompt_version": result.evidence_prompt_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _append_to_pool(record: dict) -> None:
    """Append one group record to the pool jsonl. Atomic at the line
    level. Caller is responsible for dedup (driver checks cache hit
    before regenerating)."""
    POOL_DIR.mkdir(parents=True, exist_ok=True)
    with POOL_PATH.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def _pool_has_group(group_id: str) -> bool:
    """Cheap pool-side dedup check. Used to avoid double-appending
    when the cache check missed (e.g. crashed mid-write)."""
    if not POOL_PATH.exists():
        return False
    target = json.dumps(group_id)  # cheap substring check
    for line in POOL_PATH.open():
        if target in line and json.loads(line).get("group_id") == group_id:
            return True
    return False


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main() -> int:
    enable_live_stdout()
    p = argparse.ArgumentParser()
    p.add_argument("--batch", default="smoke", choices=list(BATCH_MODULES))
    p.add_argument("--realize-model", default="us.anthropic.claude-sonnet-4-6")
    p.add_argument("--evidence-model", default="us.anthropic.claude-sonnet-4-6")
    p.add_argument("--profile", default="ahe-long")
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--realize-max-tokens", type=int, default=2000)
    p.add_argument("--evidence-max-tokens", type=int, default=1500)
    p.add_argument("--realize-max-retries", type=int, default=5)
    p.add_argument("--evidence-max-retries", type=int, default=2)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--ignore-cache", action="store_true")
    p.add_argument("--retry-failed", action="store_true")
    args = p.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    specs = _load_batch(args.batch)
    if args.limit is not None:
        specs = specs[: args.limit]

    realize_bb = BedrockBackbone(
        model_id=args.realize_model, profile=args.profile, region=args.region,
        max_new_tokens=args.realize_max_tokens, temperature=0.0,
    )
    evidence_bb = BedrockBackbone(
        model_id=args.evidence_model, profile=args.profile, region=args.region,
        max_new_tokens=args.evidence_max_tokens, temperature=0.0,
    )

    # Filter cache hits.
    pending: list[Phase3GroupSpec] = []
    cache_skipped = 0
    for spec in specs:
        if args.ignore_cache:
            pending.append(spec)
            continue
        if _is_cached_accepted(spec.group_id):
            cache_skipped += 1
            continue
        if _is_cached_failed(spec.group_id) and not args.retry_failed:
            cache_skipped += 1
            continue
        pending.append(spec)

    print(f"phase 3 batch={args.batch}  total_specs={len(specs)}  pending={len(pending)}  cache_skipped={cache_skipped}")
    if not pending:
        print("nothing to do")
        return 0

    print_eta_banner(
        label=f"realize_phase3 ({args.batch})",
        n_units=len(pending), seconds_per_unit=120, unit="group",
    )

    # Distractor dedup across groups. The lock is passed alongside the
    # set so the realizer's filter→pick→update region runs atomically;
    # without it, two workers can each see the same session as un-used,
    # both pick it, and both insert into the set after the fact.
    distractor_lock = threading.Lock()
    log_lock = threading.Lock()
    used_distractors: set[str] = set()

    def _do_one(idx_spec):
        idx, spec = idx_spec
        ts = time.perf_counter()
        result = realize_phase3_group(
            spec=spec,
            realize_backbone=realize_bb,
            evidence_backbone=evidence_bb if spec.spine.is_implicit_drift else None,
            realize_max_retries=args.realize_max_retries,
            evidence_max_retries=args.evidence_max_retries,
            used_distractor_ids=used_distractors,
            used_distractor_lock=distractor_lock,
        )
        elapsed = time.perf_counter() - ts
        return idx, spec, result, elapsed

    n_workers = max(1, args.workers)
    accepted_count = 0
    failed_count = 0
    t0 = time.perf_counter()

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = {pool.submit(_do_one, (i, sp)): i for i, sp in enumerate(pending)}
        for fut in as_completed(futures):
            idx, spec, result, elapsed = fut.result()
            with log_lock:
                _write_cache(result)
                if result.accepted:
                    samples = [m.sample for m in result.members if m.sample is not None]
                    _append_samples(samples)
                    if not _pool_has_group(result.spec.group_id):
                        _append_to_pool(_pool_record(result))
                    accepted_count += 1
                    member_summary = " ".join(
                        f"{m.horizon}({m.realize_attempts}r/{m.evidence_attempts}e)"
                        for m in result.members
                    )
                    print(
                        f"  ✓ [{accepted_count + failed_count}/{len(pending)}] "
                        f"{spec.group_id:50} {spec.group_type:7} {member_summary} "
                        f"elapsed={elapsed:.1f}s"
                    )
                else:
                    failed_count += 1
                    fail_summary = " | ".join(result.failure_reasons[:2])[:120]
                    print(
                        f"  ✗ [{accepted_count + failed_count}/{len(pending)}] "
                        f"{spec.group_id:50} {spec.group_type:7} FAIL: {fail_summary}"
                    )

    wall = time.perf_counter() - t0
    print()
    print(f"Phase 3 batch={args.batch} done in {wall:.1f}s")
    print(f"Accepted groups: {accepted_count}/{len(pending)}")
    print(f"Failed groups:   {failed_count}/{len(pending)}")
    print(f"Cache skipped:   {cache_skipped}/{len(specs)}")
    print(f"Pool:            {POOL_PATH}")
    print(f"Samples:         {FULL_PATH}")
    print(f"Failed cache:    {FAILED_DIR}")
    print()
    print("Run scripts/select_phase3_manifest.py to build phase3_main.json from the pool.")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
