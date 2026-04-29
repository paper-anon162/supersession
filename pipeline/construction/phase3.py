"""Phase 3 group-level realize loop (protocol §10.1).

A *Phase 3 group* is a SkeletonAwareSpine that should be realized at
multiple horizons sharing the same gold predicate:

  - matched triple: compact + standard + hard
  - standard-hard doublet: standard + hard

A group is accepted into the canonical Phase 3 manifest only when
**every** required horizon passes cluster A–J validation. Partial
groups are not selectable; failed groups land in the failed pool with
structured reasons for debugging.

This module provides the per-group orchestrator that
`scripts/realize_phase3.py` drives. The orchestrator:

  1. For each declared horizon, runs `realize_with_skeleton` to get a
     candidate Sample (or a parse / gauntlet failure).
  2. For implicit_drift samples, runs the cluster J extractor pass
     (Sonnet 4.6 over the realized history) to populate
     ``gold.active_evidence``.
  3. Re-runs the audit to catch cluster J findings that the realize
     gauntlet skipped (the gauntlet runs cluster A–J on the
     extractor-populated sample at this stage).
  4. Returns a Phase3GroupResult with per-member status and the
     combined accept/reject decision.

The orchestrator does NOT write to disk — the caller does, so cache
+ manifest semantics stay testable.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Literal

from pipeline.construction.active_evidence import (
    EVIDENCE_PROMPT_VERSION,
    extract_active_evidence,
)
from pipeline.construction.audit_gold_consistency import audit_sample
from pipeline.construction.skeleton_realizer import (
    SkeletonAwareSpine,
    realize_with_skeleton,
)
from pipeline.construction.topic_groups import annotate_sample_topic_group
from pipeline.evaluation.bedrock_backbone import BedrockBackbone
from pipeline.schema import (
    Horizon,
    ImplicitDriftType,
    Sample,
)

log = logging.getLogger(__name__)


# Phase 3 rule version stamp (cache key component). Bump when the
# group-level orchestration semantics change so old cache entries are
# treated as stale.
PHASE3_RULE_VERSION = "v1.0-2026-04-26"


@dataclass
class Phase3GroupSpec:
    """One Phase 3 group: a single shared spine + the horizons to
    realize. The spine's `triple_id` (or `sample_id` stem if missing)
    is used as the group_id; downstream samples carry that as their
    metadata.triple_id.
    """

    spine: SkeletonAwareSpine
    group_type: Literal["triple", "doublet"]
    horizons: list[Horizon]  # e.g. ["compact", "standard", "hard"] or ["standard", "hard"]
    implicit_drift_type: ImplicitDriftType | None = None
    # Source-of-spine identifier for cache + report.
    spine_source: str = "hand"

    @property
    def group_id(self) -> str:
        return self.spine.triple_id or self.spine.sample_id


@dataclass
class Phase3MemberResult:
    horizon: Horizon
    sample: Sample | None
    accepted: bool
    failure_reason: str | None  # populated when accepted=False
    realize_attempts: int
    evidence_attempts: int
    evidence_extractor_raw: str | None
    elapsed_s: float


@dataclass
class Phase3GroupResult:
    spec: Phase3GroupSpec
    members: list[Phase3MemberResult]
    accepted: bool
    failure_reasons: list[str] = field(default_factory=list)
    rule_version: str = PHASE3_RULE_VERSION
    evidence_prompt_version: str = EVIDENCE_PROMPT_VERSION

    @property
    def accepted_samples(self) -> list[Sample]:
        return [m.sample for m in self.members if m.accepted and m.sample is not None]


def _spine_for_horizon(spine: SkeletonAwareSpine, horizon: Horizon) -> SkeletonAwareSpine:
    """Make a copy of the spine with the requested horizon set. The
    sample_id is suffixed so each horizon gets a distinct id; the
    triple_id stays at the group level."""
    from dataclasses import replace
    new_id = f"{spine.sample_id}-{horizon}" if not spine.sample_id.endswith(f"-{horizon}") else spine.sample_id
    return replace(spine, sample_id=new_id, horizon=horizon, triple_id=spine.triple_id or spine.sample_id)


def _realize_one_member(
    *,
    spine: SkeletonAwareSpine,
    horizon: Horizon,
    realize_llm: Callable[[str], str],
    realize_max_retries: int,
    used_distractor_ids: set[str] | None,
    used_distractor_lock: "threading.Lock | None" = None,
    evidence_backbone: BedrockBackbone | None,
    evidence_max_retries: int,
    implicit_drift_type: ImplicitDriftType | None,
) -> Phase3MemberResult:
    horizon_spine = _spine_for_horizon(spine, horizon)
    is_drift = horizon_spine.is_implicit_drift

    t0 = time.perf_counter()
    realize_result = realize_with_skeleton(
        horizon_spine,
        realize_llm,
        max_retries=realize_max_retries,
        used_distractor_ids=used_distractor_ids,
        used_distractor_lock=used_distractor_lock,
    )
    if realize_result.sample is None:
        return Phase3MemberResult(
            horizon=horizon,
            sample=None,
            accepted=False,
            failure_reason=f"realize failed: {realize_result.failure_reason}",
            realize_attempts=realize_result.attempts,
            evidence_attempts=0,
            evidence_extractor_raw=None,
            elapsed_s=time.perf_counter() - t0,
        )

    sample = realize_result.sample
    # Phase 3 metadata stamps that the realize gauntlet doesn't know
    # about: implicit_drift_type, group_type (caller fills from spec).
    if is_drift:
        sample.gold.metadata.implicit_drift_type = implicit_drift_type
    annotate_sample_topic_group(sample)

    # If this is an implicit_drift sample, run the active-evidence
    # extractor pass (cluster J extractor) to populate
    # gold.active_evidence. Then re-run audit to confirm cluster J
    # passes. The realize gauntlet already ran clusters A-H; we re-run
    # to pick up cluster J specifically.
    extractor_raw = None
    evidence_attempts = 0
    if is_drift:
        if evidence_backbone is None:
            return Phase3MemberResult(
                horizon=horizon,
                sample=sample,
                accepted=False,
                failure_reason="implicit_drift sample but no evidence_backbone provided",
                realize_attempts=realize_result.attempts,
                evidence_attempts=0,
                evidence_extractor_raw=None,
                elapsed_s=time.perf_counter() - t0,
            )
        if implicit_drift_type is None:
            return Phase3MemberResult(
                horizon=horizon,
                sample=sample,
                accepted=False,
                failure_reason="implicit_drift sample but no implicit_drift_type declared in spec",
                realize_attempts=realize_result.attempts,
                evidence_attempts=0,
                evidence_extractor_raw=None,
                elapsed_s=time.perf_counter() - t0,
            )

        last_extractor_failure: str | None = None
        for attempt in range(1, evidence_max_retries + 1):
            evidence_attempts = attempt
            try:
                extract_result = extract_active_evidence(
                    sample=sample,
                    backbone=evidence_backbone,
                    implicit_drift_type=implicit_drift_type,
                )
            except Exception as e:  # noqa: BLE001
                last_extractor_failure = f"extractor exception: {type(e).__name__}: {e}"
                continue
            extractor_raw = extract_result.raw_response
            sample.gold.active_evidence = extract_result.evidence
            findings = audit_sample(sample)
            cluster_j = next((f for f in findings if f.cluster == "J"), None)
            if cluster_j is None or cluster_j.detail.get("advisory"):
                # Pass (or advisory-only J that the manifest writer can drop).
                break
            last_extractor_failure = f"cluster J failed: {cluster_j.reason}"
        else:
            return Phase3MemberResult(
                horizon=horizon,
                sample=sample,
                accepted=False,
                failure_reason=last_extractor_failure or "evidence extraction exhausted retries",
                realize_attempts=realize_result.attempts,
                evidence_attempts=evidence_attempts,
                evidence_extractor_raw=extractor_raw,
                elapsed_s=time.perf_counter() - t0,
            )

    # Final audit pass — catches anything the realize gauntlet missed.
    findings = audit_sample(sample)
    # Cluster L is non-blocking here (see realization.py for rationale);
    # the manifest selector handles it as a per-member drop so the
    # group can degrade triple → doublet without losing standard/hard.
    blocking = [
        f for f in findings
        if f.cluster in ("A", "B", "C", "E", "F", "G", "H")
        or (f.cluster == "J" and not f.detail.get("advisory"))
    ]
    if blocking:
        reasons = "; ".join(f"cluster {f.cluster}: {f.reason}" for f in blocking)
        return Phase3MemberResult(
            horizon=horizon,
            sample=sample,
            accepted=False,
            failure_reason=f"final audit failed: {reasons}",
            realize_attempts=realize_result.attempts,
            evidence_attempts=evidence_attempts,
            evidence_extractor_raw=extractor_raw,
            elapsed_s=time.perf_counter() - t0,
        )

    return Phase3MemberResult(
        horizon=horizon,
        sample=sample,
        accepted=True,
        failure_reason=None,
        realize_attempts=realize_result.attempts,
        evidence_attempts=evidence_attempts,
        evidence_extractor_raw=extractor_raw,
        elapsed_s=time.perf_counter() - t0,
    )


def realize_phase3_group(
    *,
    spec: Phase3GroupSpec,
    realize_backbone: BedrockBackbone,
    evidence_backbone: BedrockBackbone | None = None,
    realize_max_retries: int = 5,
    evidence_max_retries: int = 2,
    used_distractor_ids: set[str] | None = None,
    used_distractor_lock: "threading.Lock | None" = None,
) -> Phase3GroupResult:
    """Realize all required horizons of a Phase 3 group; return a
    structured per-member result. Group is accepted only when every
    member passes.

    `evidence_backbone` is required for any group whose spine is
    implicit_drift; pass None for non-drift groups (the orchestrator
    won't call the extractor on them).

    `used_distractor_ids` is shared across calls to prevent
    cross-sample distractor reuse (audit P0 §3); pair it with
    `used_distractor_lock` when callers run multiple workers.
    """
    if not spec.horizons:
        raise ValueError(f"group {spec.group_id!r} has no horizons declared")
    members: list[Phase3MemberResult] = []
    for horizon in spec.horizons:
        member = _realize_one_member(
            spine=spec.spine,
            horizon=horizon,
            realize_llm=realize_backbone,
            realize_max_retries=realize_max_retries,
            used_distractor_ids=used_distractor_ids,
            used_distractor_lock=used_distractor_lock,
            evidence_backbone=evidence_backbone,
            evidence_max_retries=evidence_max_retries,
            implicit_drift_type=spec.implicit_drift_type,
        )
        members.append(member)
        # Stamp group_type on accepted samples now that we know their
        # canonical group context.
        if member.accepted and member.sample is not None:
            member.sample.gold.metadata.group_type = spec.group_type
            member.sample.gold.metadata.triple_id = spec.group_id

    accepted = all(m.accepted for m in members)
    failure_reasons: list[str] = []
    if not accepted:
        for m in members:
            if not m.accepted:
                failure_reasons.append(f"{m.horizon}: {m.failure_reason}")

    return Phase3GroupResult(
        spec=spec,
        members=members,
        accepted=accepted,
        failure_reasons=failure_reasons,
    )


__all__ = [
    "PHASE3_RULE_VERSION",
    "Phase3GroupResult",
    "Phase3GroupSpec",
    "Phase3MemberResult",
    "realize_phase3_group",
]
