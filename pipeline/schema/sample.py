"""Sample schema per data_plan §2.

Public fields are visible to systems / probes / interventions.
Gold-only fields live under `_gold` and must never reach systems.
Enforcement is the responsibility of pipeline.io.loaders.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Atoms
# ---------------------------------------------------------------------------

Polarity = Literal["prefer", "avoid", "constraint"]
VersionStatus = Literal["active", "outdated"]
SampleType = Literal["supersession", "carryover", "stress"]
SupersessionSubtype = Literal["strong", "multi_step", "reverted"]
SignalStrength = Literal["strong", "weak"]
GoldTargetType = Literal[
    "object_preference",
    "interpersonal_boundary",
    "conceptual_stance",
    "procedural_constraint",
]
RuleType = Literal[
    "must_include_active_value",
    "must_not_include_outdated_value",
    "must_not_mix",
    "must_address_target_slot",
    "must_not_avoid_required_choice",
]
CheckScope = Literal["top_recommendation", "full_response"]
ScoringMode = Literal["binary", "graded"]


class StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=False)


# ---------------------------------------------------------------------------
# History (kept lightweight for v1 — we treat sessions as ordered turn lists)
# ---------------------------------------------------------------------------


class Turn(StrictBase):
    role: Literal["user", "assistant"]
    text: str


class Session(StrictBase):
    session_id: str
    timestamp: str | None = None
    turns: list[Turn]


# ---------------------------------------------------------------------------
# Version & Spine
# ---------------------------------------------------------------------------


class VersionState(StrictBase):
    version_id: str
    topic: str
    value: str | list[str] | dict
    polarity: Polarity
    session_introduced: int
    status: VersionStatus


class SemanticSpine(StrictBase):
    """Gold anchor for judge & failure attribution.

    All judge decisions and attribution annotations resolve back to this spine
    rather than to the surface realization (data_plan §2.3).
    """

    target_description: str
    target_slot_id: str
    old_state: str
    new_state: str
    required_behavior: str
    invalid_behavior: list[str]


# ---------------------------------------------------------------------------
# Violation predicate
# ---------------------------------------------------------------------------


class Rule(StrictBase):
    rule_type: RuleType
    check_scope: CheckScope


class ViolationPredicate(StrictBase):
    must_honor: VersionState
    must_not_honor: list[VersionState]
    violation_rules: list[Rule]
    partial_credit: bool = False
    scoring: ScoringMode = "binary"


# ---------------------------------------------------------------------------
# Probe (reverted-only, diagnostic)
# ---------------------------------------------------------------------------


class ProbeQuery(StrictBase):
    query: str
    expected_mention: str


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


Horizon = Literal["compact", "standard", "hard"]
FailurePattern = Literal[
    "implicit_drift", "narrowing", "multi_version", "explicit_replacement"
]
ConstructionSource = Literal["hand", "llm_realized", "skeleton_realized"]
# Phase 3 (protocol §10.3) subdivides implicit_drift into three structural
# types so authoring and audit can apply distinguishable rules.
# - repeated_use: later sessions repeatedly show the user actively using /
#   requesting / organizing around the new state.
# - abandonment: later sessions show the old state retired, archived,
#   avoided, or no longer governing behavior.
# - gradual_narrowing: later sessions progressively narrow acceptable
#   behavior toward the active state without an explicit replacement
#   statement (distinct from `narrowing` failure_pattern, which has ≥3
#   explicitly declared versions).
# Phase 2 samples leave this None.
ImplicitDriftType = Literal["repeated_use", "abandonment", "gradual_narrowing"]
# Phase 3 (protocol §10.5) coarse 4-bucket topic balance, replacing
# strict per-domain quotas. Phase 2 samples leave this None.
TopicGroup = Literal[
    "daily_preference",      # food / travel / entertainment / shopping / hobbies / home / pet care / lifestyle / fitness
    "work_tooling",          # software tools / work workflow / project workflow / note-taking / productivity / tech_workflow / work_communication
    "learning_routine",      # learning / fitness routine / scheduling / recurring habits / management cadence
    "communication_boundary",  # tone / discussion boundary / message style / interpersonal phrasing
]
# Sample-level ambiguity flag (codex audit P0). Used to exclude samples
# from headline VF slices when the realizer's output makes the gold
# determination unfair — e.g. an implicit_drift sample whose active
# event session does not allow a reader to infer the active value
# without an explicit announcement.
AmbiguityClass = Literal[
    "not_ambiguous",
    "ambiguous_active_evidence",  # active value not inferable from active event session
    "ambiguous_other",            # other audit-flagged ambiguity
]


class Metadata(StrictBase):
    session_count: int
    history_token_count: int
    update_to_query_token_distance: int
    number_of_revisions: int
    supersession_subtype: SupersessionSubtype | None = None
    signal_strength: SignalStrength | None = None
    domain: str
    gold_target_type: GoldTargetType
    competing_versions_count: int
    # Phase 2 metadata (added per audit P1 §"Preserve analysis metadata").
    # Optional so existing Phase 1 samples remain valid without migration.
    horizon: Horizon | None = None
    failure_patterns: list[FailurePattern] = Field(default_factory=list)
    construction_source: ConstructionSource | None = None
    skeleton_source: str | None = None
    # Codex audit P0: mark samples whose gold decision is unfair (e.g.
    # active event session doesn't entail the active value). Default None
    # means "not yet reviewed for ambiguity" — distinct from
    # "not_ambiguous" which records an active human/audit pass.
    ambiguity_class: AmbiguityClass | None = None
    ambiguity_reason: str | None = None
    # Matched-triples design (protocol §9.2.2). All members of a triple
    # share the same triple_id and gold predicate; only horizon, history
    # length, and distractor loadout differ. 4+-version multi_version
    # chains may form a doublet (std + hard only) instead of a triple
    # — also identified via triple_id. None means "not part of any
    # matched group" (legacy samples or singletons).
    triple_id: str | None = None
    # Phase 3 additions (protocol §10).
    # implicit_drift_type subdivides drift; only set when failure_patterns
    # includes "implicit_drift". Phase 2 samples leave None.
    implicit_drift_type: ImplicitDriftType | None = None
    # topic_group is the coarse 4-bucket topic balance axis (§10.5).
    # Phase 2 samples leave None — backfill at audit time when needed.
    topic_group: TopicGroup | None = None
    # Phase 3 group_id (the matched triple/doublet's group identifier)
    # is currently aliased to triple_id. Phase 3 group_type can be
    # "triple" (compact + standard + hard) or "doublet" (standard +
    # hard only). Phase 2 samples leave group_type None.
    group_type: Literal["triple", "doublet"] | None = None


# ---------------------------------------------------------------------------
# Run metadata (data_plan §2.6)
# ---------------------------------------------------------------------------


class RunMetadata(StrictBase):
    system_name: str
    run_id: str
    sample_id: str
    memory_infra_location: Literal["local", "aws", "cloud_api", "none"]
    answer_backbone: str
    answer_backbone_provider: Literal[
        "local", "bedrock", "openai", "anthropic", "other"
    ]
    embedding_model: str
    embedding_provider: Literal["local", "api", "none"]
    vector_store: str | None = None
    graph_store: str | None = None
    uses_full_history: bool
    uses_retrieved_memory: bool
    prompt_template_id: str
    temperature: float
    max_tokens: int


# ---------------------------------------------------------------------------
# Gold bundle
# ---------------------------------------------------------------------------


class ActiveEvidence(StrictBase):
    """One active-evidence item for a Phase 3 implicit_drift sample
    (protocol §10.4). Populated by the cluster J extractor pass
    (Sonnet 4.6 over the realized history) and validated by cluster J
    against six rules. Gold-only — stripped from public/judge bundles
    that don't need it.

    `evidence_text` must appear verbatim somewhere in the cited
    `session_id`. `why_it_supports_active_state` is a one-sentence
    rationale used for human audit; not consumed by automated VF.
    """

    session_id: str
    evidence_text: str
    why_it_supports_active_state: str


class GoldBundle(StrictBase):
    target_versions: list[VersionState]
    violation_predicate: ViolationPredicate
    gold_target_type: GoldTargetType
    metadata: Metadata
    semantic_spine: SemanticSpine
    reverted_probe: ProbeQuery | None = None
    # Phase 3 cluster J: gold-only evidence list for implicit_drift
    # samples. Phase 2 samples leave None. ≥2 items required for the
    # sample to land in the canonical Phase 3 manifest.
    active_evidence: list[ActiveEvidence] | None = None


# ---------------------------------------------------------------------------
# Top-level sample
# ---------------------------------------------------------------------------


class Sample(StrictBase):
    """Top-level sample. `_gold` is gold-only and must be stripped before
    feeding to systems / probes / interventions (see pipeline.io.loaders).
    """

    sample_id: str
    history: list[Session]
    current_query: str
    sample_type: SampleType
    recall_query: str | None = None
    gold: GoldBundle = Field(alias="_gold")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _check_invariants(self) -> "Sample":
        # recall_query is only emitted for supersession samples (data_plan §3, §7)
        if self.sample_type != "supersession" and self.recall_query is not None:
            raise ValueError(
                f"recall_query must be None for sample_type={self.sample_type!r}"
            )
        # Core supersession hard constraint: ≥ 2 competing versions on same slot
        # (data_plan §2.5, §6.2; protocol §6.1)
        if self.sample_type == "supersession":
            cv = self.gold.metadata.competing_versions_count
            if cv < 2:
                raise ValueError(
                    f"core supersession sample {self.sample_id} has "
                    f"competing_versions_count={cv}; must be ≥ 2"
                )
        # Reverted probe is reverted-only (data_plan §3.2)
        if self.gold.reverted_probe is not None:
            if self.gold.metadata.supersession_subtype != "reverted":
                raise ValueError(
                    "reverted_probe is set on a non-reverted sample"
                )
        return self


__all__ = [
    "AmbiguityClass",
    "CheckScope",
    "GoldBundle",
    "GoldTargetType",
    "Metadata",
    "Polarity",
    "ProbeQuery",
    "Rule",
    "RuleType",
    "RunMetadata",
    "Sample",
    "SampleType",
    "ScoringMode",
    "SemanticSpine",
    "Session",
    "SignalStrength",
    "StrictBase",
    "SupersessionSubtype",
    "Turn",
    "VersionState",
    "VersionStatus",
    "ViolationPredicate",
]
