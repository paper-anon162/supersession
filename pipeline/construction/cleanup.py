"""Distractor cleanup pass.

After a sample has been realized, some of its distractor sessions may
contain raw QA / web / role-play / disclaimer / corporate-jargon
artifacts that the realizer's distractor sampler would now reject (per
`pipeline/construction/naturalness.py`) but which were generated under a
laxer filter. This module rewrites such distractor sessions in place by
swapping their turn content for a clean session drawn from the same
corpus, preserving:

  - session_id and timestamp (so positional indexing stays valid),
  - the set of *event* session positions registered in the violation
    predicate (so the supersession spine is preserved exactly),
  - approximate token count (so the horizon tier remains valid).

The cleanup is idempotent: a sample with no scanner hits passes through
unchanged. It is also Bedrock-free — we only resample distractor turns
from a local corpus.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Iterable

from pipeline.construction.naturalness import is_distractor_natural, scan_session
from pipeline.construction.skeleton_loader import (
    DialogueCorpus,
    DialogueSession,
)


_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


def _approx_token_count(turns: list[dict]) -> int:
    return sum(len(_TOKEN_RE.findall(t.get("text", "") or "")) for t in turns)


def _event_positions(sample: dict) -> set[int]:
    pred = (sample.get("_gold") or {}).get("violation_predicate") or {}
    positions: set[int] = set()
    must_honor = pred.get("must_honor") or {}
    pos = must_honor.get("session_introduced")
    if isinstance(pos, int):
        positions.add(pos)
    for v in pred.get("must_not_honor") or []:
        pos = v.get("session_introduced") if isinstance(v, dict) else None
        if isinstance(pos, int):
            positions.add(pos)
    return positions


@dataclass(frozen=True)
class Replacement:
    sample_id: str
    session_position: int       # 1-indexed position in history
    session_id: str             # local session_id (e.g. "s4")
    matched_categories: list[str]
    replaced_with_corpus_id: str
    target_tokens: int
    actual_tokens: int


@dataclass
class CleanupResult:
    n_samples: int = 0
    n_samples_changed: int = 0
    replacements: list[Replacement] = field(default_factory=list)
    skipped_no_replacement: list[Replacement] = field(default_factory=list)
    event_session_dirty: list[Replacement] = field(default_factory=list)


def _candidate_pool(corpus: DialogueCorpus) -> list[DialogueSession]:
    """Pre-filter: only sessions that pass the naturalness gate."""
    return [s for s in corpus.sessions if is_distractor_natural(s)]


def _pick_replacement(
    pool: list[DialogueSession],
    *,
    target_tokens: int,
    used_corpus_ids: set[str],
    rng: random.Random,
    tolerance: float = 0.5,
) -> DialogueSession | None:
    """Pick a clean corpus session whose token count is within
    ``[target * (1 - tolerance), target * (1 + tolerance)]``. Falls back
    to closest-by-token-count match if no session is in-band. Returns
    ``None`` only if the pool is empty.
    """
    available = [s for s in pool if s.session_id not in used_corpus_ids]
    if not available:
        return None
    lo = max(1, int(target_tokens * (1 - tolerance)))
    hi = max(lo + 1, int(target_tokens * (1 + tolerance)))
    in_band = [s for s in available if lo <= s.approx_token_count <= hi]
    if in_band:
        return rng.choice(in_band)
    return min(available, key=lambda s: abs(s.approx_token_count - target_tokens))


def _turns_to_dicts(session: DialogueSession) -> list[dict]:
    return [
        {"role": t.role, "text": t.text}
        for t in session.turns
        if (t.text or "").strip()
    ]


def clean_sample(
    sample: dict,
    *,
    pool: list[DialogueSession],
    used_corpus_ids: set[str],
    rng: random.Random,
) -> tuple[dict, list[Replacement], list[Replacement]]:
    """Return ``(cleaned_sample, replacements, skipped)``.

    ``replacements`` records successful swaps. ``skipped`` records
    sessions that were dirty but for which no replacement was available.
    """
    sid = sample.get("sample_id", "?")
    history = sample.get("history") or []
    event_pos = _event_positions(sample)
    replacements: list[Replacement] = []
    skipped: list[Replacement] = []

    new_history: list[dict] = []
    for i, sess in enumerate(history, start=1):
        if i in event_pos:
            new_history.append(sess)
            continue
        hits = scan_session(sess)
        if not hits:
            new_history.append(sess)
            continue
        cats = sorted({h.category for h in hits})
        target = _approx_token_count(sess.get("turns") or [])
        repl = _pick_replacement(
            pool,
            target_tokens=target,
            used_corpus_ids=used_corpus_ids,
            rng=rng,
        )
        if repl is None:
            skipped.append(Replacement(
                sample_id=sid,
                session_position=i,
                session_id=sess.get("session_id", f"s{i}"),
                matched_categories=cats,
                replaced_with_corpus_id="",
                target_tokens=target,
                actual_tokens=0,
            ))
            new_history.append(sess)
            continue
        used_corpus_ids.add(repl.session_id)
        new_turns = _turns_to_dicts(repl)
        new_sess = {
            "session_id": sess.get("session_id", f"s{i}"),
            "timestamp": sess.get("timestamp"),
            "turns": new_turns,
        }
        new_history.append(new_sess)
        replacements.append(Replacement(
            sample_id=sid,
            session_position=i,
            session_id=new_sess["session_id"],
            matched_categories=cats,
            replaced_with_corpus_id=repl.session_id,
            target_tokens=target,
            actual_tokens=repl.approx_token_count,
        ))

    cleaned = dict(sample)
    cleaned["history"] = new_history

    # Keep _gold.metadata.history_token_count accurate after distractor
    # swaps so downstream horizon checks read the post-cleanup truth.
    if replacements:
        gold = cleaned.get("_gold")
        if isinstance(gold, dict):
            gold = dict(gold)
            meta = gold.get("metadata")
            if isinstance(meta, dict):
                meta = dict(meta)
                new_total = sum(
                    _approx_token_count(s.get("turns") or [])
                    for s in new_history
                )
                meta["history_token_count"] = new_total
                gold["metadata"] = meta
                cleaned["_gold"] = gold

    # Also flag (but don't modify) any event session that has artifact
    # hits — those need re-realization, not in-place cleanup. They get
    # appended onto ``skipped`` and the caller splits by position.
    for i, sess in enumerate(history, start=1):
        if i not in event_pos:
            continue
        hits = scan_session(sess)
        if not hits:
            continue
        skipped.append(Replacement(
            sample_id=sid,
            session_position=i,
            session_id=sess.get("session_id", f"s{i}"),
            matched_categories=sorted({h.category for h in hits}),
            replaced_with_corpus_id="",
            target_tokens=_approx_token_count(sess.get("turns") or []),
            actual_tokens=0,
        ))
    return cleaned, replacements, skipped


def clean_dataset(
    samples: Iterable[dict],
    *,
    corpus: DialogueCorpus,
    seed: int = 0,
    used_corpus_ids: set[str] | None = None,
    rng: random.Random | None = None,
) -> tuple[list[dict], CleanupResult]:
    """Run the cleanup pass over a dataset. Returns ``(cleaned_samples, result)``.

    Pass ``used_corpus_ids`` and ``rng`` to share dedup state and
    deterministic randomness across multiple ``clean_dataset`` calls
    (e.g. when cleaning several files in one CLI invocation). When
    ``None``, fresh state is used and the call is self-contained.
    """
    pool = _candidate_pool(corpus)
    used = used_corpus_ids if used_corpus_ids is not None else set()
    rng = rng or random.Random(seed)
    cleaned_out: list[dict] = []
    result = CleanupResult()
    for sample in samples:
        cleaned, repls, skipped = clean_sample(
            sample, pool=pool, used_corpus_ids=used, rng=rng,
        )
        cleaned_out.append(cleaned)
        result.n_samples += 1
        if repls:
            result.n_samples_changed += 1
        result.replacements.extend(repls)
        # split skipped into "no replacement available" vs "event session
        # was dirty" by checking position membership in event_pos
        evt = _event_positions(sample)
        for s in skipped:
            if s.session_position in evt:
                result.event_session_dirty.append(s)
            else:
                result.skipped_no_replacement.append(s)
    return cleaned_out, result


__all__ = [
    "CleanupResult",
    "Replacement",
    "clean_dataset",
    "clean_sample",
]
