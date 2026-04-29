"""LLM judge for Version Fidelity (protocol §8).

The judge consumes the *full* sample (gold included) plus the model's response
and emits a structured JSON verdict. The backbone (which actual LLM is used)
is pluggable; Phase 0 ships a deterministic stub so the dry run does not need
external compute.

Phase 1+ wires in:
  - the primary frontier LLM judge (Claude / GPT)
  - a cross-judge for agreement / ranking-stability checks

The judge surface-level output contains:

    {
      "vf": 0 | 1,
      "confidence": "low" | "medium" | "high",
      "ambiguity_class": one of the literal classes,
      "rationale": str,
    }

The default-scoring step (ambiguous → VF=0) is applied in
``pipeline.evaluation.vf_scoring``, not here. This module is responsible only
for *eliciting* the verdict.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from jinja2 import Template

from pipeline.io import load_for_judge
from pipeline.schema import Sample

AmbiguityClass = Literal[
    "not_ambiguous",
    "target_avoidance",
    "topic_shift",
    "refusal",
    "vague",
    "mixed",
]
Confidence = Literal["low", "medium", "high"]


# ---------------------------------------------------------------------------
# Backbone protocol
# ---------------------------------------------------------------------------


class JudgeBackbone(Protocol):
    """Anything that turns a judge prompt into a raw response string."""

    name: str

    def __call__(self, prompt: str) -> str: ...


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------


PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "judge_vf.jinja"


def _normalize_value(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    return str(value)


def render_judge_prompt(sample: Sample, response: str) -> str:
    judge_view = load_for_judge(sample)
    gold = judge_view["_gold"]
    spine = gold["semantic_spine"]
    must_honor = gold["violation_predicate"]["must_honor"]
    must_not_honor = gold["violation_predicate"]["must_not_honor"]
    template = Template(PROMPT_PATH.read_text())
    return template.render(
        history=judge_view["history"],
        current_query=judge_view["current_query"],
        response=response,
        spine=spine,
        active_value=_normalize_value(must_honor["value"]),
        outdated_values=[_normalize_value(v["value"]) for v in must_not_honor],
    )


def render_judge_prompt_split(
    sample: Sample, response: str
) -> tuple[str, str]:
    """Render the judge prompt as ``(system_text, user_text)``.

    Splits at the literal `\\nUSER\\n` separator inside the template so the
    SYSTEM section can be passed to the Bedrock Converse `system` field
    rather than smuggled in as part of the user message (audit P0 §1
    "Judge instructions are not separated into true API roles").

    Falls back to (empty system, full prompt) if the marker isn't found.
    """
    full = render_judge_prompt(sample, response)
    marker = "\nUSER\n"
    idx = full.find(marker)
    if idx < 0:
        return "", full
    system_text = full[:idx].lstrip("\n")
    # Strip the leading "SYSTEM\n" header if present.
    if system_text.startswith("SYSTEM\n"):
        system_text = system_text[len("SYSTEM\n"):]
    user_text = full[idx + len(marker):]
    return system_text, user_text


# ---------------------------------------------------------------------------
# Verdict & parsing
# ---------------------------------------------------------------------------


@dataclass
class JudgeVerdict:
    sample_id: str
    backbone: str
    vf: int
    confidence: Confidence
    ambiguity_class: AmbiguityClass
    rationale: str
    raw_output: str

    def to_dict(self) -> dict:
        return {
            "sample_id": self.sample_id,
            "backbone": self.backbone,
            "vf": self.vf,
            "confidence": self.confidence,
            "ambiguity_class": self.ambiguity_class,
            "rationale": self.rationale,
        }


_JSON_BLOCK_RE = re.compile(r"\{.*\}", flags=re.DOTALL)


class JudgeParseError(ValueError):
    pass


def parse_verdict(sample_id: str, backbone: str, raw: str) -> JudgeVerdict:
    """Extract structured JSON from a judge response.

    Tolerates a fenced code block or stray prose around the JSON object, but
    rejects multiple objects or invalid field values.
    """
    # Find the first '{' and use raw_decode so we tolerate trailing prose or
    # a second JSON object that some judges occasionally append.
    start = raw.find("{")
    if start < 0:
        raise JudgeParseError(f"no JSON object in judge output for {sample_id}")
    try:
        obj, _ = json.JSONDecoder().raw_decode(raw[start:])
    except json.JSONDecodeError as e:
        # Fall back to greedy regex (first { to last }) for the rare case
        # the model wrote a non-prefix valid object.
        match = _JSON_BLOCK_RE.search(raw)
        if match is None:
            raise JudgeParseError(f"no JSON object in judge output for {sample_id}") from e
        try:
            obj = json.loads(match.group(0))
        except json.JSONDecodeError as e2:
            raise JudgeParseError(f"invalid JSON for {sample_id}: {e2}") from e2

    try:
        vf = int(obj["vf"])
        if vf not in (0, 1):
            raise ValueError(f"vf must be 0 or 1, got {vf}")
        # Confidence and ambiguity_class are optional metadata; some judges
        # (notably Opus 4.6) occasionally omit them while still producing a
        # valid vf. Default to medium / not_ambiguous so we don't lose the
        # vf signal — apply_default_scoring will still take effect for any
        # explicitly-flagged ambiguity.
        confidence = obj.get("confidence", "medium")
        ambiguity = obj.get("ambiguity_class", "not_ambiguous")
        rationale = str(obj.get("rationale", "")).strip()
    except (KeyError, TypeError, ValueError) as e:
        raise JudgeParseError(f"missing/invalid field in {sample_id}: {e}") from e

    if confidence not in ("low", "medium", "high"):
        raise JudgeParseError(f"invalid confidence={confidence!r} for {sample_id}")
    if ambiguity not in (
        "not_ambiguous",
        "target_avoidance",
        "topic_shift",
        "refusal",
        "vague",
        "mixed",
    ):
        raise JudgeParseError(
            f"invalid ambiguity_class={ambiguity!r} for {sample_id}"
        )

    return JudgeVerdict(
        sample_id=sample_id,
        backbone=backbone,
        vf=vf,
        confidence=confidence,  # type: ignore[arg-type]
        ambiguity_class=ambiguity,  # type: ignore[arg-type]
        rationale=rationale,
        raw_output=raw,
    )


def judge_sample(
    sample: Sample, response: str, backbone: JudgeBackbone
) -> JudgeVerdict:
    """Run the judge backbone on the sample/response pair.

    If the backbone exposes a ``system_prompt`` attribute (HF and Bedrock
    backbones do), the SYSTEM portion of the prompt is set there for the
    duration of this call so it lands in the API's true system role,
    rather than being smuggled into the user message (audit P0 §1).
    """
    if hasattr(backbone, "system_prompt"):
        system_text, user_text = render_judge_prompt_split(sample, response)
        prior = backbone.system_prompt
        backbone.system_prompt = system_text
        try:
            raw = backbone(user_text)
        finally:
            backbone.system_prompt = prior
    else:
        prompt = render_judge_prompt(sample, response)
        raw = backbone(prompt)
    return parse_verdict(sample.sample_id, backbone.name, raw)


# ---------------------------------------------------------------------------
# Stub backbone for Phase 0 dry run
# ---------------------------------------------------------------------------


@dataclass
class HeuristicJudgeBackbone:
    """Deterministic Phase 0 stub.

    Implements a minimal heuristic that lets the dry run produce realistic
    verdicts without an LLM. It echoes the same logic that an LLM judge would
    apply to obvious cases:

      - response contains active value tokens and no outdated tokens → vf=1
      - response contains outdated tokens (with or without active) → vf=0
      - response contains neither → vf=0 with target_avoidance ambiguity

    This is *only* for Phase 0 wiring. Phase 1 must replace this with a
    frontier LLM backbone before any benchmark result is interpreted.
    """

    name: str = "heuristic_stub"

    def __call__(self, prompt: str) -> str:
        active, outdated = _parse_gold_lines(prompt)
        response = _extract_response_block(prompt)
        active_hits = _word_hits(active, response)
        outdated_hits = any(_word_hits(o, response) for o in outdated)

        if active_hits and not outdated_hits:
            verdict = {
                "vf": 1,
                "confidence": "high",
                "ambiguity_class": "not_ambiguous",
                "rationale": "Response honors active value with no outdated contamination.",
            }
        elif outdated_hits and active_hits:
            verdict = {
                "vf": 0,
                "confidence": "medium",
                "ambiguity_class": "mixed",
                "rationale": "Response mixes active and outdated versions.",
            }
        elif outdated_hits:
            verdict = {
                "vf": 0,
                "confidence": "high",
                "ambiguity_class": "not_ambiguous",
                "rationale": "Response follows an outdated version.",
            }
        else:
            verdict = {
                "vf": 0,
                "confidence": "medium",
                "ambiguity_class": "target_avoidance",
                "rationale": "Response does not address the target slot.",
            }
        return json.dumps(verdict)


_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "at", "for", "with",
    "as", "is", "are", "was", "were", "be", "by", "from",
}


def _content_words(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) >= 3}


def _word_hits(target: str, response: str) -> bool:
    target_words = _content_words(target)
    if not target_words:
        return False
    return bool(target_words & _content_words(response))


# `[ \t]*` (not `\s*`) so the regex can't consume newlines and slurp the
# following line when the outdated list is empty.
_ACTIVE_LINE_RE = re.compile(r"Active version value:[ \t]*(.+)")
_OUTDATED_LINE_RE = re.compile(r"Outdated version values:[ \t]*(.+)")
_RESPONSE_BLOCK_RE = re.compile(
    r"=== Model response ===\s*(.*?)\s*=== Gold reference",
    flags=re.DOTALL,
)


def _parse_gold_lines(prompt: str) -> tuple[str, list[str]]:
    am = _ACTIVE_LINE_RE.search(prompt)
    om = _OUTDATED_LINE_RE.search(prompt)
    active = am.group(1).strip() if am else ""
    outdated_raw = om.group(1).strip() if om else ""
    outdated = [s.strip() for s in outdated_raw.split(",") if s.strip()]
    return active, outdated


def _extract_response_block(prompt: str) -> str:
    m = _RESPONSE_BLOCK_RE.search(prompt)
    return m.group(1) if m else ""


__all__ = [
    "AmbiguityClass",
    "Confidence",
    "HeuristicJudgeBackbone",
    "JudgeBackbone",
    "JudgeParseError",
    "JudgeVerdict",
    "judge_sample",
    "parse_verdict",
    "render_judge_prompt",
]
