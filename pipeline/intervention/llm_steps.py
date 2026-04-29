"""LLM-backed candidate extraction and active-version selection.

Replaces the Phase 0 stubs (``stub_extract_candidates`` /
``stub_select_active``) with prompts evaluated against a real LLM. The
wrapper still consumes ONLY public sample fields — the gold-isolation
contract in ``pipeline.intervention.wrapper`` is preserved.

Robustness:

  - JSON parse errors return an empty list (extraction) or None (selection).
  - Indices outside the candidates list return None.
  - The wrapper's ``abstain_with_no_injection`` policy then takes effect.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from jinja2 import Template

from pipeline.intervention.wrapper import CandidateUpdate

EXTRACT_PROMPT = (
    Path(__file__).resolve().parents[2] / "prompts" / "intervention_extract.jinja"
)
EXTRACT_DRIFT_AWARE_PROMPT = (
    Path(__file__).resolve().parents[2] / "prompts" / "intervention_extract_drift_aware.jinja"
)
SELECT_PROMPT = (
    Path(__file__).resolve().parents[2] / "prompts" / "intervention_select.jinja"
)


_JSON_BLOCK_RE = re.compile(r"\{.*\}", flags=re.DOTALL)


def _extract_json(raw: str) -> dict[str, Any] | None:
    match = _JSON_BLOCK_RE.search(raw)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _format_history(history: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for s in history:
        ts = f" @ {s['timestamp']}" if s.get("timestamp") else ""
        blocks.append(f"[Session {s['session_id']}{ts}]")
        for t in s["turns"]:
            blocks.append(f"{t['role']}: {t['text']}")
        blocks.append("")
    return "\n".join(blocks)


def _build_extractor(
    llm: Callable[[str], str], prompt_path: Path, max_candidates: int
) -> Callable[[dict[str, Any]], list[CandidateUpdate]]:
    template = Template(prompt_path.read_text())

    def extract(public_sample: dict[str, Any]) -> list[CandidateUpdate]:
        prompt = template.render(
            history=_format_history(public_sample["history"]),
            current_query=public_sample["current_query"],
        )
        raw = llm(prompt)
        obj = _extract_json(raw)
        if not obj or "candidates" not in obj:
            return []
        out: list[CandidateUpdate] = []
        for c in obj["candidates"][:max_candidates]:
            try:
                # Carry "kind" through the rationale so the selector can see
                # whether a candidate came from explicit announcement or
                # behavioral drift inference. Drift candidates are appended
                # with a "kind=drift" prefix so downstream traces remain
                # interpretable.
                kind = str(c.get("kind", "stated")).strip().lower()
                rationale = str(c.get("rationale", ""))
                if kind == "drift" and "drift" not in rationale.lower():
                    rationale = f"[drift] {rationale}".strip()
                out.append(
                    CandidateUpdate(
                        topic=str(c["topic"]),
                        value=str(c["value"]),
                        polarity=str(c.get("polarity", "prefer")),
                        session_introduced=int(c.get("session_introduced", 0)),
                        rationale=rationale,
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return out

    return extract


def make_llm_extractor(
    llm: Callable[[str], str], *, max_candidates: int = 16
) -> Callable[[dict[str, Any]], list[CandidateUpdate]]:
    """Stated-only extractor (original behavior, protocol §12.2).

    ``max_candidates`` was raised from 8 to 16: on long (hard-horizon)
    histories the extractor can legitimately emit >8 candidates spanning
    multiple targets; the previous truncation at 8 silently dropped any
    candidates after position 8 before the selector saw them, including
    the active version when it was preceded by older / unrelated updates."""
    return _build_extractor(llm, EXTRACT_PROMPT, max_candidates)


def make_drift_aware_llm_extractor(
    llm: Callable[[str], str], *, max_candidates: int = 16
) -> Callable[[dict[str, Any]], list[CandidateUpdate]]:
    """Stated + behavioral-drift extractor with conservative ≥2-evidence
    gate enforced inside the prompt. Use with the SAME selector and
    responder as the stated-only variant. ``max_candidates`` raised
    from 8 to 16 (see ``make_llm_extractor`` rationale)."""
    return _build_extractor(llm, EXTRACT_DRIFT_AWARE_PROMPT, max_candidates)


def make_llm_selector(
    llm: Callable[[str], str],
) -> Callable[[list[CandidateUpdate], dict[str, Any]], CandidateUpdate | None]:
    """Build an LLM-backed active-version selector compatible with the wrapper."""
    template = Template(SELECT_PROMPT.read_text())

    def select(
        candidates: list[CandidateUpdate], public_sample: dict[str, Any]
    ) -> CandidateUpdate | None:
        if not candidates:
            return None
        # Heuristic tie-breaking: if multiple candidates share a topic, prefer
        # the latest by session_introduced. The LLM still gets to pick across
        # topics; this just collapses redundant within-topic chains for it.
        candidates_payload = [
            {
                "index": i,
                "topic": c.topic,
                "value": c.value,
                "polarity": c.polarity,
                "session_introduced": c.session_introduced,
                "rationale": c.rationale,
            }
            for i, c in enumerate(candidates)
        ]
        prompt = template.render(
            candidates_json=json.dumps(candidates_payload, ensure_ascii=False),
            current_query=public_sample["current_query"],
        )
        raw = llm(prompt)
        obj = _extract_json(raw)
        if not obj:
            return None
        idx = obj.get("selected_index")
        if idx is None:
            return None
        try:
            i = int(idx)
        except (TypeError, ValueError):
            return None
        if i < 0 or i >= len(candidates):
            return None
        return candidates[i]

    return select


__all__ = [
    "make_llm_extractor",
    "make_drift_aware_llm_extractor",
    "make_llm_selector",
]
