"""Skeleton-aware seed realizer (Phase 2; protocol §9.2.1, §9.2.2).

Authors specify a "skeleton-aware spine" describing the supersession
target plus Phase 2 metadata (horizon tier, failure patterns). The
realizer:

  1. Samples real distractor sessions from a LongMemEval / LoCoMo
     corpus until the horizon's token budget is filled.
  2. Asks the LLM to author *only* the K event sessions where the user
     state changes (one per version).
  3. Splices: distractors + event sessions, interleaved by timestamp.
  4. Materializes and runs the validity gauntlet (same-target,
     leakage, schema). On failure, retries with sharpened error.

Compared to the vanilla ``realize()`` in ``realization.py``:

  - vanilla: LLM produces ALL sessions including the supersession events.
  - skeleton-aware: LLM produces only event sessions; distractors come
    from real corpora (data_plan §4.1).

This unblocks Phase 2 horizon composition (compact / standard / hard)
and the targeted-hard-case mix (implicit drift, narrowing, multi-version).
"""

from __future__ import annotations

import json
import random
import re
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Literal

from jinja2 import Template

from pipeline.construction.realization import (
    RealizationParseError,
    RealizationResult,
    ThinSpine,
    _gauntlet_check,
    _seed_spec_from,
)
from pipeline.construction.seeds import (
    SeedSpec,
    SessionSpec,
    TurnSpec,
    materialize,
)
from pipeline.construction.naturalness import (
    build_target_tokens,
    is_distractor_natural,
    is_distractor_topic_orthogonal,
)
from pipeline.construction.skeleton_loader import (
    DialogueCorpus,
    DialogueSession,
    load_locomo_corpus,
    load_longmemeval_corpus,
)

EVENT_PROMPT_PATH = (
    Path(__file__).resolve().parents[2] / "prompts" / "event_sessions.jinja"
)

Horizon = Literal["compact", "standard", "hard"]
SkeletonVariant = Literal["oracle", "s", "m", "locomo"]
FailurePattern = Literal[
    "implicit_drift", "narrowing", "multi_version", "explicit_replacement"
]


@dataclass
class HorizonBudget:
    """Token budget per horizon tier (per protocol §9.2.1)."""

    min_tokens: int
    max_tokens: int
    min_distractors: int
    max_distractors: int


HORIZON_BUDGETS: dict[Horizon, HorizonBudget] = {
    # Bounds are inclusive on min, exclusive on max — the strict horizon
    # gate in `_check_horizon_budget` enforces ``min_tokens <= history_tokens
    # < max_tokens`` against the spine's declared horizon.
    "compact":  HorizonBudget(min_tokens=0,     max_tokens=3000,  min_distractors=0, max_distractors=2),
    "standard": HorizonBudget(min_tokens=3000,  max_tokens=10000, min_distractors=3, max_distractors=8),
    "hard":     HorizonBudget(min_tokens=10000, max_tokens=20000, min_distractors=8, max_distractors=20),
}


@dataclass
class SkeletonAwareSpine(ThinSpine):
    """Thin spine extended with Phase 2 horizon and failure-pattern metadata."""

    horizon: Horizon = "compact"
    failure_patterns: list[FailurePattern] = field(default_factory=list)
    skeleton_variant: SkeletonVariant | None = "s"
    distractor_seed: int = 0
    skeleton_max_questions: int = 50
    distractor_max_turns: int = 15  # filter distractor sessions: skip very long ones
    # Matched-triples design (protocol §9.2.2): a spine may declare
    # multiple horizons it should be realized at. Each realization
    # shares the same triple_id (defaults to sample_id stem). Empty
    # list means "realize once at `horizon` only" (legacy / singleton
    # behavior).
    horizons: list[Horizon] = field(default_factory=list)
    triple_id: str | None = None

    @property
    def is_implicit_drift(self) -> bool:
        return "implicit_drift" in self.failure_patterns

    @property
    def is_narrowing(self) -> bool:
        return "narrowing" in self.failure_patterns


# ---------------------------------------------------------------------------
# Skeleton sampling
# ---------------------------------------------------------------------------


# Distractor-naturalness filter (audit P0 §1, §3): reject distractor
# sessions that visibly break the "same user, same long-running personal
# assistant" illusion — AI self-disclosure, raw web/QA artifacts, staged
# multi-part document feeds, role-play openers, and isolated corporate
# jargon. The full pattern catalogue lives in
# `pipeline/construction/naturalness.py` so the same gate is shared by
# the audit scanner.
def _is_distractor_clean(session: DialogueSession) -> bool:
    return is_distractor_natural(session)


def _load_skeleton_corpus(
    spine: SkeletonAwareSpine,
) -> DialogueCorpus | None:
    if spine.skeleton_variant is None:
        return None
    if spine.skeleton_variant == "locomo":
        return load_locomo_corpus()
    return load_longmemeval_corpus(
        variant=spine.skeleton_variant,
        max_questions=spine.skeleton_max_questions,
    )


def _sample_distractors(
    corpus: DialogueCorpus,
    budget: HorizonBudget,
    spine: SkeletonAwareSpine,
    event_token_estimate: int,
    *,
    used_distractor_ids: set[str] | None = None,
    used_distractor_lock: "threading.Lock | None" = None,
) -> list[DialogueSession]:
    """Sample distractor sessions until the token budget is filled.

    Audit P0 §3: filter out sessions with AI-disclaimer text and avoid
    cross-sample duplicates by consulting ``used_distractor_ids``. When
    multiple workers may call this concurrently with the same shared
    ``used_distractor_ids`` set, pass ``used_distractor_lock`` so the
    filter→pick→update region is atomic. Without the lock, two workers
    can each see the same session as un-used, both pick it, and both
    insert into the set after the fact — producing cross-spine
    duplicates.

    Strategy:
      1. Pre-filter for cleanliness (no disclaimers) and turn-count cap.
      2. Drop already-used sessions if a registry is supplied.
      3. Shuffle (seeded) for randomisation across runs.
      4. Greedily add sessions until ``min_distractors`` is reached.
      5. If still below ``min_tokens``, switch to a longest-first pass
         to fill the budget without unbounded fan-out.
      6. Stop at ``max_distractors`` regardless.
      7. Mutate ``used_distractor_ids`` with chosen sessions so subsequent
         spines in the same realization batch don't reuse them.
    """
    # Hold the lock across the whole filter→pick→update section so
    # concurrent realizers cannot pick the same session twice.
    @contextmanager
    def _critical_section():
        if used_distractor_lock is not None:
            with used_distractor_lock:
                yield
        else:
            yield

    with _critical_section():
        return _sample_distractors_unlocked(
            corpus, budget, spine, event_token_estimate,
            used_distractor_ids=used_distractor_ids,
        )


def _sample_distractors_unlocked(
    corpus: DialogueCorpus,
    budget: HorizonBudget,
    spine: SkeletonAwareSpine,
    event_token_estimate: int,
    *,
    used_distractor_ids: set[str] | None = None,
) -> list[DialogueSession]:
    rng = random.Random(spine.distractor_seed)
    used = used_distractor_ids if used_distractor_ids is not None else set()
    # Build the target token set ONCE per call so topic-orthogonality
    # rejection is cheap. Active value is the last spine version.
    active_value = spine.versions[-1].value if spine.versions else ""
    target_tokens = build_target_tokens(
        target_description=getattr(spine, "target_description", "") or "",
        target_slot_id=getattr(spine, "target_slot_id", "") or "",
        active_value=active_value,
    )
    candidates = [
        s for s in corpus.sessions
        if 1 <= s.n_turns <= spine.distractor_max_turns
        and _is_distractor_clean(s)
        and s.session_id not in used
        and is_distractor_topic_orthogonal(s, target_tokens=target_tokens)
    ]
    rng.shuffle(candidates)

    out: list[DialogueSession] = []
    chosen_ids: set[str] = set()
    accum_tokens = event_token_estimate

    def _would_overshoot(tokens: int) -> bool:
        # Stop accepting distractors that would push the history over
        # the horizon's declared max. The hard gate is enforced separately
        # in `_check_horizon_budget`; this is the soft sampling-time
        # boundary that keeps min satisfaction from accidentally over-
        # filling.
        return accum_tokens + tokens >= budget.max_tokens

    for s in candidates:
        if len(out) >= budget.max_distractors:
            break
        if _would_overshoot(s.approx_token_count) and accum_tokens >= budget.min_tokens:
            # We've already cleared the floor — adding this would exceed
            # the ceiling, so we're done.
            break
        if _would_overshoot(s.approx_token_count):
            # Need more tokens to clear the floor, but this candidate is
            # too big — try the next one.
            continue
        out.append(s)
        chosen_ids.add(s.session_id)
        accum_tokens += s.approx_token_count
        if (
            len(out) >= budget.min_distractors
            and accum_tokens >= budget.min_tokens
        ):
            break

    if accum_tokens < budget.min_tokens and len(out) < budget.max_distractors:
        remaining = sorted(
            (s for s in candidates if s.session_id not in chosen_ids),
            key=lambda s: -s.approx_token_count,
        )
        for s in remaining:
            if len(out) >= budget.max_distractors:
                break
            if _would_overshoot(s.approx_token_count):
                continue
            out.append(s)
            chosen_ids.add(s.session_id)
            accum_tokens += s.approx_token_count
            if accum_tokens >= budget.min_tokens:
                break

    used.update(chosen_ids)
    return out


# ---------------------------------------------------------------------------
# Implicit-drift active-session validator (audit P1)
# ---------------------------------------------------------------------------


# If implicit_drift is on, the active session's user turns must NOT contain
# any of these explicit-update phrases. Per data_plan §8.6 / audit P1.
_DRIFT_ANNOUNCEMENT_PHRASES = (
    "from now on",
    "going forward",
    "i switched to",
    "i've switched to",
    "i changed my mind",
    "no longer",
    "new rule",
    "new policy",
    "starting now",
    "as of today",
    "effective immediately",
    "i'm done with",
    "i no longer use",
    "i no longer want",
)


def _active_session_announces_drift(active_turns: list[TurnSpec]) -> str | None:
    """Return the offending phrase if any user turn contains an explicit-
    update marker; otherwise None.
    """
    for t in active_turns:
        if t.role != "user":
            continue
        text = t.text.lower()
        for phrase in _DRIFT_ANNOUNCEMENT_PHRASES:
            if phrase in text:
                return phrase
    return None


# ---------------------------------------------------------------------------
# Event-session prompt + parsing
# ---------------------------------------------------------------------------


def _render_event_prompt(spine: SkeletonAwareSpine) -> str:
    template = Template(EVENT_PROMPT_PATH.read_text())
    events = []
    n_versions = len(spine.versions)
    for i, v in enumerate(spine.versions):
        if i == n_versions - 1:
            label = "active"
        elif i == 0:
            label = "v1"
        else:
            label = f"v{i + 1}"
        events.append(
            {"label": label, "value": v.value, "polarity": v.polarity}
        )
    return template.render(
        target_description=spine.target_description,
        target_type=spine.target_type,
        domain=spine.domain,
        events=events,
        n_events=n_versions,
        current_query=spine.current_query,
        implicit_drift=spine.is_implicit_drift,
        narrowing=spine.is_narrowing,
    )


_JSON_BLOCK_RE = re.compile(r"\{.*\}", flags=re.DOTALL)


def _extract_json(raw: str) -> dict:
    start = raw.find("{")
    if start < 0:
        raise RealizationParseError("no JSON object in event-session output")
    try:
        obj, _ = json.JSONDecoder().raw_decode(raw[start:])
        return obj
    except json.JSONDecodeError:
        m = _JSON_BLOCK_RE.search(raw)
        if not m:
            raise RealizationParseError("no JSON object in event-session output")
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError as e:
            raise RealizationParseError(f"event-session JSON parse: {e}") from e


def parse_event_sessions(
    raw: str, expected_n: int
) -> list[list[TurnSpec]]:
    """Return the K event sessions as a list of TurnSpec lists, in order.

    Each entry corresponds to one version (v1 first, active last).
    """
    obj = _extract_json(raw)
    if "event_sessions" not in obj or not isinstance(obj["event_sessions"], list):
        raise RealizationParseError(
            "missing or non-list 'event_sessions' field"
        )
    items = obj["event_sessions"]
    if len(items) != expected_n:
        raise RealizationParseError(
            f"expected {expected_n} event sessions, got {len(items)}"
        )
    out: list[list[TurnSpec]] = []
    for i, ev in enumerate(items):
        turns_raw = ev.get("turns")
        if not isinstance(turns_raw, list) or not turns_raw:
            raise RealizationParseError(
                f"event session {i + 1}: missing or empty turns"
            )
        turns: list[TurnSpec] = []
        for t in turns_raw:
            role = t.get("role")
            text = (t.get("text") or "").strip()
            if role not in ("user", "assistant"):
                raise RealizationParseError(
                    f"event session {i + 1}: bad role {role!r}"
                )
            if not text:
                raise RealizationParseError(
                    f"event session {i + 1}: empty turn text"
                )
            turns.append(TurnSpec(role=role, text=text))
        out.append(turns)
    return out


# ---------------------------------------------------------------------------
# Splicing distractors + event sessions
# ---------------------------------------------------------------------------


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d (%a) %H:%M", "%Y/%m/%d %H:%M",
                "%Y-%m-%d"):
        try:
            return datetime.strptime(ts.strip(), fmt)
        except ValueError:
            continue
    # Last resort: try fromisoformat
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _choose_event_positions(
    n_total_sessions: int, n_events: int, rng: random.Random,
    *,
    min_active_to_query_gap: int = 2,
    min_inter_event_gap: int = 2,
) -> list[int]:
    """Pick 1-indexed positions in [1..n_total_sessions] for the K event
    sessions. Per data_plan §4.2:

      - v1 and v2 (and v_intermediate, if multi-step) must be in different
        sessions, never adjacent.
      - The active update must be at least ``min_active_to_query_gap``
        sessions before the current_query (i.e., before position
        n_total_sessions). Default 2.
      - Insertion is not fixed at session start or end.

    The realizer thus reserves the last ``min_active_to_query_gap``
    sessions as distractors between the active update and the query.
    """
    if n_events > n_total_sessions:
        raise ValueError("n_events > total sessions")
    # Active position cap: leave at least `min_active_to_query_gap` distractor
    # sessions after the active event.
    active_max = max(1, n_total_sessions - min_active_to_query_gap)
    # Floor for the first event: position 1 is fine when there's no need
    # to leave preceding distractors; this is also what compact (no
    # distractor) tier needs.
    first_min = 1
    span_needed = min_inter_event_gap * (n_events - 1)
    if active_max - first_min < span_needed:
        raise ValueError(
            f"cannot fit {n_events} events in {n_total_sessions} sessions "
            f"(active_max={active_max}, first_min={first_min}, "
            f"min_inter_event_gap={min_inter_event_gap})"
        )
    if n_events == 1:
        target = min(active_max, max(first_min + 1, n_total_sessions - 2))
        return [target]
    # Distribute events so they end at active_max with min gap.
    # Walk positions backward from active_max.
    positions: list[int] = [active_max]
    for _ in range(n_events - 1):
        positions.append(positions[-1] - min_inter_event_gap)
    positions.reverse()
    # If the first position is < first_min, shift everything forward.
    if positions[0] < first_min:
        shift = first_min - positions[0]
        positions = [p + shift for p in positions]
    return positions


def _splice_sessions(
    distractors: list[DialogueSession],
    event_turn_lists: list[list[TurnSpec]],
    rng: random.Random,
    *,
    min_active_to_query_gap: int = 2,
    min_inter_event_gap: int = 2,
) -> tuple[list[SessionSpec], list[int]]:
    """Splice distractors and event sessions, in chronological order.

    Returns ``(sessions, event_positions)`` where ``event_positions[i]``
    is the 1-indexed position of the i-th event session in the final
    list.
    """
    n_events = len(event_turn_lists)
    n_total = len(distractors) + n_events
    positions = _choose_event_positions(
        n_total, n_events, rng,
        min_active_to_query_gap=min_active_to_query_gap,
        min_inter_event_gap=min_inter_event_gap,
    )
    pos_set = set(positions)

    # Sort distractors by timestamp (parsed). Unparseable timestamps go last.
    def _ts_key(s: DialogueSession) -> tuple[int, datetime | int]:
        dt = _parse_iso(s.timestamp)
        if dt is None:
            return (1, 0)
        return (0, dt)

    distractors_sorted = sorted(distractors, key=_ts_key)

    # Walk positions 1..n_total, filling with events at event-positions and
    # distractors elsewhere.
    sessions: list[SessionSpec] = []
    d_iter = iter(distractors_sorted)
    event_iter = iter(event_turn_lists)
    last_ts: datetime | None = None
    pos_to_event_idx: dict[int, int] = {p: i for i, p in enumerate(positions)}

    for pos in range(1, n_total + 1):
        sid = f"s{pos}"
        if pos in pos_set:
            event_turns = next(event_iter)
            # Assign timestamp interpolated from neighbors. If we have a
            # last_ts, add a small gap (1-3 days). Else use a default
            # epoch.
            if last_ts is not None:
                ts_dt = last_ts + timedelta(days=1 + rng.randint(0, 3))
            else:
                ts_dt = datetime(2026, 1, 1)
            sessions.append(SessionSpec(
                session_id=sid,
                timestamp=ts_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                turns=event_turns,
            ))
            last_ts = ts_dt
        else:
            try:
                d = next(d_iter)
            except StopIteration:
                # Shouldn't happen with proper positions, but guard anyway.
                ts_dt = (last_ts or datetime(2026, 1, 1)) + timedelta(days=1)
                sessions.append(SessionSpec(
                    session_id=sid,
                    timestamp=ts_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    turns=[TurnSpec(role="user", text="(filler)"),
                           TurnSpec(role="assistant", text="OK.")],
                ))
                last_ts = ts_dt
                continue
            d_dt = _parse_iso(d.timestamp)
            if d_dt is None:
                d_dt = (last_ts or datetime(2026, 1, 1)) + timedelta(days=1)
            # Force monotonic
            if last_ts is not None and d_dt <= last_ts:
                d_dt = last_ts + timedelta(days=1)
            d_turns = [
                TurnSpec(role=t.role, text=t.text)
                for t in d.turns
                if t.text.strip()
            ]
            if not d_turns:
                d_turns = [
                    TurnSpec(role="user", text="(filler)"),
                    TurnSpec(role="assistant", text="OK."),
                ]
            sessions.append(SessionSpec(
                session_id=sid,
                timestamp=d_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                turns=d_turns,
            ))
            last_ts = d_dt
    return sessions, positions


# ---------------------------------------------------------------------------
# Realize entry point
# ---------------------------------------------------------------------------


def _spec_with_overridden_introductions(
    spine: SkeletonAwareSpine,
    sessions: list[SessionSpec],
    event_positions: list[int],
) -> SeedSpec:
    """Build a SeedSpec where each VersionSpec.session_introduced is set
    to the corresponding event position in the spliced session list.
    """
    if len(event_positions) != len(spine.versions):
        raise ValueError("event_positions length must match versions")
    spec = _seed_spec_from(spine, sessions)
    spec.versions = [
        type(v)(
            value=v.value,
            polarity=v.polarity,
            session_introduced=event_positions[i],
        )
        for i, v in enumerate(spine.versions)
    ]
    # Propagate Phase 2 metadata onto the SeedSpec so materialize() can
    # write horizon / failure_patterns / construction_source into Metadata
    # (audit P1).
    spec.horizon = spine.horizon
    spec.failure_patterns = list(spine.failure_patterns)
    spec.construction_source = "skeleton_realized"
    spec.skeleton_source = (
        f"longmemeval_{spine.skeleton_variant}"
        if spine.skeleton_variant in {"oracle", "s", "m"}
        else (spine.skeleton_variant or None)
    )
    # Matched-triples design — propagate triple_id so all members of
    # the same triple can be paired by aggregators downstream.
    spec.triple_id = spine.triple_id
    return spec


def realize_with_skeleton(
    spine: SkeletonAwareSpine,
    llm: Callable[[str], str],
    *,
    max_retries: int = 3,
    on_attempt: Callable[[int, str | None], None] | None = None,
    used_distractor_ids: set[str] | None = None,
    used_distractor_lock: threading.Lock | None = None,
) -> RealizationResult:
    """Generate a Phase 2 sample using a real-corpus distractor backbone.

    ``used_distractor_ids`` is an optional set the caller mutates across
    realization calls to prevent cross-sample distractor reuse (audit
    P0 §3). When None, no cross-call dedupe happens.

    ``used_distractor_lock`` should be passed alongside the set when
    multiple workers call this concurrently with the same set, so the
    distractor filter→pick→update region is atomic.
    """
    base_budget = HORIZON_BUDGETS[spine.horizon]
    n_events = len(spine.versions)
    # Adapt min_distractors so the position constraints (active ≥ 2 before
    # query, events ≥ 2 apart) are satisfiable for this n_events.
    # Required n_total ≥ active_max + 2 = (1 + 2*(n_events-1)) + 2.
    required_min_total = 1 + 2 * (n_events - 1) + 2
    required_min_distractors = max(0, required_min_total - n_events)
    budget = HorizonBudget(
        min_tokens=base_budget.min_tokens,
        max_tokens=base_budget.max_tokens,
        min_distractors=max(base_budget.min_distractors, required_min_distractors),
        max_distractors=max(base_budget.max_distractors, required_min_distractors + 2),
    )
    rng = random.Random(spine.distractor_seed)
    corpus = _load_skeleton_corpus(spine)

    raw_outputs: list[str] = []
    last_failure: str | None = None
    base_prompt = _render_event_prompt(spine)

    for attempt in range(1, max_retries + 1):
        prompt = base_prompt
        if last_failure:
            prompt += (
                "\n\nPrevious attempt failed validation: "
                f"{last_failure}\nTry again with strict JSON only."
            )
        if on_attempt is not None:
            on_attempt(attempt, last_failure)

        raw = llm(prompt)
        raw_outputs.append(raw)

        try:
            event_turn_lists = parse_event_sessions(
                raw, expected_n=len(spine.versions)
            )
        except RealizationParseError as e:
            last_failure = f"event-session parse error: {e}"
            continue

        # Audit P1: if implicit_drift is on, the active session's user turns
        # must not contain explicit-update phrases. The active event is the
        # last entry in event_turn_lists by ordering convention.
        if spine.is_implicit_drift and event_turn_lists:
            offending = _active_session_announces_drift(event_turn_lists[-1])
            if offending is not None:
                last_failure = (
                    f"active session contains explicit-update phrase "
                    f"{offending!r}; must be implicit (audit P1)"
                )
                continue

        # Estimate event token cost (ballpark) so we leave headroom for it.
        event_token_estimate = sum(
            sum(len(re.findall(r"\w+|[^\w\s]", t.text)) for t in turns)
            for turns in event_turn_lists
        )

        if corpus is not None:
            distractors = _sample_distractors(
                corpus, budget, spine, event_token_estimate,
                used_distractor_ids=used_distractor_ids,
                used_distractor_lock=used_distractor_lock,
            )
        else:
            distractors = []

        # Gap rules (data_plan §4.2):
        #   - active update must be ≥ 2 sessions before query
        #   - v1/v2/etc must not be adjacent
        # For pure compact (no distractors), both relax to 1 (events go in
        # back-to-back sessions; no distractors to space them out anyway).
        if not distractors:
            gap_active = 0
            gap_inter = 1
        else:
            gap_active = 2
            gap_inter = 2
        # Relax gaps when the available session count can't satisfy the
        # default rule. Specifically the splicer requires
        # n_total - gap_active - gap_inter * (n_events - 1) ≥ 1.
        # Compact + 2-event chains commonly hit this when the corpus
        # only yields 1 distractor under the token budget. Step the
        # gaps down (gap_inter first, then gap_active) until feasible
        # or both reach 0. Phase 3 §10.1 acceptance is at the group
        # level, so loosening compact gap rules here is preferred to
        # rejecting otherwise-valid spines.
        n_total_check = n_events + len(distractors)
        while (
            n_total_check - gap_active - gap_inter * (n_events - 1) < 1
            and (gap_inter > 0 or gap_active > 0)
        ):
            if gap_inter > 0:
                gap_inter -= 1
            else:
                gap_active -= 1

        try:
            sessions, event_positions = _splice_sessions(
                distractors, event_turn_lists, rng,
                min_active_to_query_gap=gap_active,
                min_inter_event_gap=gap_inter,
            )
        except ValueError as e:
            last_failure = f"splice error: {e}"
            continue

        try:
            spec = _spec_with_overridden_introductions(
                spine, sessions, event_positions
            )
            sample = materialize(spec)
        except Exception as e:  # noqa: BLE001
            last_failure = f"materialization failed: {type(e).__name__}: {e}"
            continue

        gauntlet_err = _gauntlet_check(sample)
        if gauntlet_err:
            last_failure = gauntlet_err
            continue

        return RealizationResult(
            seed_spec=spec,
            sample=sample,
            raw_outputs=raw_outputs,
            failure_reason=None,
            attempts=attempt,
        )

    return RealizationResult(
        seed_spec=None,
        sample=None,
        raw_outputs=raw_outputs,
        failure_reason=last_failure,
        attempts=max_retries,
    )


__all__ = [
    "FailurePattern",
    "Horizon",
    "HORIZON_BUDGETS",
    "HorizonBudget",
    "SkeletonAwareSpine",
    "SkeletonVariant",
    "parse_event_sessions",
    "realize_with_skeleton",
]
