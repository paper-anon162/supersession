"""Active-evidence extractor for Phase 3 implicit_drift samples.

Implements the cluster J extractor pass (protocol §10.4):

    realized history (multi-session)
        + outdated state
        + candidate active state
        + implicit_drift_type
              ↓ Sonnet 4.6 Bedrock pass with prompts/active_evidence_extract.jinja
    list of {session_id, evidence_text, why_it_supports_active_state}

The extractor is content-agnostic: it consumes a sample (or a Phase 3
group member) and returns an `active_evidence` list. The
counterpart cluster J validator (`audit_gold_consistency`) is what
enforces the rules; the extractor's job is to emit candidate
evidence spans plus a structured rationale.

Usage
-----

    from pipeline.construction.active_evidence import extract_active_evidence

    evidence = extract_active_evidence(
        sample=sample,
        backbone=BedrockBackbone(model_id="us.anthropic.claude-sonnet-4-6", ...),
    )
    if evidence is None:
        # extractor returned an empty list ("I cannot extract valid
        # evidence"); cluster J will reject the sample.
        ...

The extractor emits at most 3 items. Empty-list output is a
deliberate "I cannot find 2+ items satisfying every rule" signal
from the model — preferred over fabrication.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Template

from pipeline.evaluation.bedrock_backbone import BedrockBackbone
from pipeline.schema import ActiveEvidence, ImplicitDriftType, Sample

EVIDENCE_PROMPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "prompts"
    / "active_evidence_extract.jinja"
)
EVIDENCE_PROMPT_VERSION = "v1.0-2026-04-26"

_JSON_BLOCK_RE = re.compile(r"\{.*\}", flags=re.DOTALL)


@dataclass
class EvidenceExtractionResult:
    evidence: list[ActiveEvidence]
    raw_response: str
    prompt_version: str
    model_id: str


def _outdated_session_introduced(sample: Sample) -> int:
    """Smallest session_introduced among outdated versions (i.e. the
    earliest outdated state, which is the last session whose evidence
    is *not* eligible — evidence must come strictly after this one).

    For multi-step chains (v1 outdated → v2 outdated → v3 active) we
    use the LATEST outdated session_introduced as the floor: evidence
    must appear after the most recent superseded state."""
    outdated = sample.gold.violation_predicate.must_not_honor or []
    if not outdated:
        # Single-version carryover sample — no outdated state. Caller
        # shouldn't be invoking the extractor on this.
        return 0
    return max(v.session_introduced for v in outdated)


def _active_session_introduced(sample: Sample) -> int:
    return sample.gold.violation_predicate.must_honor.session_introduced


def _render_extract_prompt(
    sample: Sample, implicit_drift_type: ImplicitDriftType
) -> str:
    template = Template(EVIDENCE_PROMPT_PATH.read_text())
    return template.render(
        implicit_drift_type=implicit_drift_type,
        outdated_state=sample.gold.violation_predicate.must_not_honor[0].value,
        outdated_session_introduced=_outdated_session_introduced(sample),
        active_state=sample.gold.violation_predicate.must_honor.value,
        active_session_introduced=_active_session_introduced(sample),
        sessions=sample.history,
    )


def _parse_evidence_response(text: str) -> list[ActiveEvidence]:
    """Extract JSON object from raw model output, validate keys, build
    ActiveEvidence dataclasses. Returns empty list on parse failure
    (caller treats this as "extractor unable to comply")."""
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        return []
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    raw_items = obj.get("active_evidence", [])
    if not isinstance(raw_items, list):
        return []
    out: list[ActiveEvidence] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        sid = item.get("session_id")
        ev = item.get("evidence_text")
        why = item.get("why_it_supports_active_state")
        if not (isinstance(sid, str) and isinstance(ev, str) and isinstance(why, str)):
            continue
        out.append(
            ActiveEvidence(
                session_id=sid,
                evidence_text=ev,
                why_it_supports_active_state=why,
            )
        )
    return out


def extract_active_evidence(
    *,
    sample: Sample,
    backbone: BedrockBackbone,
    implicit_drift_type: ImplicitDriftType | None = None,
) -> EvidenceExtractionResult:
    """Run the active-evidence extractor on a single Phase 3
    implicit_drift sample. Returns an EvidenceExtractionResult; the
    .evidence list is empty when the model declined to comply or
    parsing failed. Cluster J does the actual rule enforcement on the
    returned evidence list.

    `implicit_drift_type` falls back to `sample.gold.metadata.implicit_drift_type`
    when not passed explicitly. Callers running pre-schema-extension
    samples must pass this argument.
    """
    drift_type = implicit_drift_type or sample.gold.metadata.implicit_drift_type
    if drift_type is None:
        raise ValueError(
            f"sample {sample.sample_id!r}: implicit_drift_type is required for "
            f"active-evidence extraction (passed neither as arg nor as "
            f"metadata.implicit_drift_type)"
        )
    prompt = _render_extract_prompt(sample, drift_type)
    raw = backbone(prompt)
    evidence = _parse_evidence_response(raw)
    return EvidenceExtractionResult(
        evidence=evidence,
        raw_response=raw,
        prompt_version=EVIDENCE_PROMPT_VERSION,
        model_id=backbone.model_id,
    )


__all__ = [
    "EVIDENCE_PROMPT_PATH",
    "EVIDENCE_PROMPT_VERSION",
    "EvidenceExtractionResult",
    "extract_active_evidence",
]
