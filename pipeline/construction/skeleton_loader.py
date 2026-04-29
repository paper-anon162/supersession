"""Skeleton loader (data_plan §4.1).

Ingests external long-horizon dialogue corpora — LoCoMo and LongMemEval —
and exposes their structural / temporal / distractor characteristics so
SupersessionBench seed authoring can borrow real conversation cadence
without copying the corpora's QA pairs.

Data layout (under ``data/skeletons/``):

  data/skeletons/
    locomo/
      locomo10.json              # 10 long conversations × ~35 sessions avg
      msc_personas_all.json      # MSC persona pool LoCoMo seeds personas from
    longmemeval/
      longmemeval_oracle.json    # only evidence sessions per question
      longmemeval_s_cleaned.json # ~115k tokens / ~40 sessions (default skeleton)
      longmemeval_m_cleaned.json # ~500 sessions / much larger haystack

Public API:

  - ``load_locomo_corpus``         : parse the LoCoMo JSON into a uniform
                                     ``DialogueCorpus`` representation.
  - ``load_longmemeval_oracle_corpus`` : haystack from oracle (evidence only)
  - ``load_longmemeval_corpus``    : load _s or _m; richer distractor density
  - ``DialogueCorpus.distractor_sessions`` : sample N sessions for stress /
                                              bridge use.
  - ``DialogueCorpus.session_length_distribution`` : empirical (turns,
                                                      token-rough-count) per
                                                      session.

Hard rule (data_plan §4.1): we borrow structure / length / timestamps /
distractor distribution. We **never** copy a foreign QA into a
SupersessionBench gold predicate. Distractor sessions surfaced here are
intended for use as bridge content in the *history* portion of stress
samples — not for the spine, current_query, or violation predicate.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parents[2]
SKELETONS_DIR = REPO / "data" / "skeletons"
LOCOMO_PATH = SKELETONS_DIR / "locomo" / "locomo10.json"
LOCOMO_PERSONAS_PATH = SKELETONS_DIR / "locomo" / "msc_personas_all.json"
LONGMEMEVAL_ORACLE_PATH = SKELETONS_DIR / "longmemeval" / "longmemeval_oracle.json"
LONGMEMEVAL_S_PATH = SKELETONS_DIR / "longmemeval" / "longmemeval_s_cleaned.json"
LONGMEMEVAL_M_PATH = SKELETONS_DIR / "longmemeval" / "longmemeval_m_cleaned.json"


@dataclass
class DialogueTurn:
    role: str  # "user" or "assistant" — mapped from corpus speakers
    text: str


@dataclass
class DialogueSession:
    session_id: str
    timestamp: str | None
    turns: list[DialogueTurn]
    source: str = ""

    @property
    def n_turns(self) -> int:
        return len(self.turns)

    @property
    def approx_token_count(self) -> int:
        # rough: words + punctuation
        return sum(len(re.findall(r"\w+|[^\w\s]", t.text)) for t in self.turns)


@dataclass
class DialogueCorpus:
    name: str
    sessions: list[DialogueSession] = field(default_factory=list)

    def session_length_distribution(self) -> list[tuple[int, int]]:
        """Return list of (n_turns, approx_token_count) per session."""
        return [(s.n_turns, s.approx_token_count) for s in self.sessions]

    def distractor_sessions(
        self,
        *,
        n: int,
        max_turns: int | None = None,
        min_turns: int = 1,
        rng: random.Random | None = None,
    ) -> list[DialogueSession]:
        """Sample ``n`` sessions usable as distractor / bridge content.

        Filters by turn count to keep distractor sessions short. Returns
        copies; mutating the result does not affect the corpus.
        """
        rng = rng or random.Random()
        candidates: list[DialogueSession] = []
        for s in self.sessions:
            if s.n_turns < min_turns:
                continue
            if max_turns is not None and s.n_turns > max_turns:
                continue
            candidates.append(s)
        if not candidates:
            return []
        rng.shuffle(candidates)
        return candidates[:n]

    def __len__(self) -> int:
        return len(self.sessions)


# ---------------------------------------------------------------------------
# LoCoMo loader
# ---------------------------------------------------------------------------


def _locomo_speaker_to_role(spkr: str, speaker_a: str, speaker_b: str) -> str:
    """Map speaker name to user/assistant. We arbitrarily treat speaker_a as
    the "user" and speaker_b as the "assistant" — for distractor purposes,
    the role labels are stylistic only.
    """
    if spkr == speaker_a:
        return "user"
    if spkr == speaker_b:
        return "assistant"
    return "user"


def load_locomo_corpus(path: str | Path = LOCOMO_PATH) -> DialogueCorpus:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"LoCoMo data not found at {p}. See data/skeletons/README.md."
        )
    with p.open() as f:
        data = json.load(f)

    sessions: list[DialogueSession] = []
    for record_idx, record in enumerate(data):
        conv = record.get("conversation", {})
        speaker_a = conv.get("speaker_a", "Speaker A")
        speaker_b = conv.get("speaker_b", "Speaker B")
        sample_id = record.get("sample_id", f"locomo-{record_idx}")
        # session keys: session_1, session_2, ...
        session_keys = sorted(
            (k for k in conv.keys() if re.fullmatch(r"session_\d+", k)),
            key=lambda k: int(k.split("_")[1]),
        )
        for sk in session_keys:
            turns_raw = conv.get(sk, [])
            if not isinstance(turns_raw, list):
                continue
            ts = conv.get(f"{sk}_date_time")
            turns: list[DialogueTurn] = []
            for t in turns_raw:
                if not isinstance(t, dict):
                    continue
                spkr = t.get("speaker", "")
                role = _locomo_speaker_to_role(spkr, speaker_a, speaker_b)
                text = t.get("text", "").strip()
                if not text:
                    continue
                turns.append(DialogueTurn(role=role, text=text))
            if not turns:
                continue
            sessions.append(
                DialogueSession(
                    session_id=f"{sample_id}::{sk}",
                    timestamp=ts,
                    turns=turns,
                    source="locomo",
                )
            )
    return DialogueCorpus(name="locomo", sessions=sessions)


# ---------------------------------------------------------------------------
# LongMemEval loaders
# ---------------------------------------------------------------------------


_LONGMEMEVAL_VARIANT_PATHS = {
    "oracle": LONGMEMEVAL_ORACLE_PATH,
    "s": LONGMEMEVAL_S_PATH,
    "m": LONGMEMEVAL_M_PATH,
}


def load_longmemeval_corpus(
    variant: str = "oracle",
    *,
    path: str | Path | None = None,
    max_questions: int | None = None,
) -> DialogueCorpus:
    """Load any LongMemEval variant into a uniform ``DialogueCorpus``.

    Parameters
    ----------
    variant
        One of ``"oracle"`` (15 MB, evidence-only), ``"s"`` (265 MB, ~40
        sessions per question — recommended default skeleton), or ``"m"``
        (2.6 GB, ~500 sessions per question — only use when you specifically
        need very-long-haystack distractor density).
    path
        Override the on-disk path (e.g. for tests).
    max_questions
        If set, parse only the first N question-haystacks. Useful with
        ``"m"`` variant to avoid the multi-GB memory footprint when you
        only need a sample of distractor sessions.
    """
    if path is None:
        if variant not in _LONGMEMEVAL_VARIANT_PATHS:
            raise ValueError(
                f"unknown LongMemEval variant {variant!r}; "
                f"expected one of {sorted(_LONGMEMEVAL_VARIANT_PATHS)}"
            )
        path = _LONGMEMEVAL_VARIANT_PATHS[variant]
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"LongMemEval data not found at {p}. See data/skeletons/README.md "
            "for download instructions."
        )
    with p.open() as f:
        data = json.load(f)

    if max_questions is not None:
        data = data[:max_questions]

    source_label = f"longmemeval_{variant}"
    sessions: list[DialogueSession] = []
    for q_idx, item in enumerate(data):
        haystack = item.get("haystack_sessions", [])
        haystack_dates = item.get("haystack_dates", [])
        haystack_ids = item.get("haystack_session_ids", [])
        question_id = item.get("question_id", f"lme-{q_idx}")
        for s_idx, session in enumerate(haystack):
            if not isinstance(session, list) or not session:
                continue
            ts = haystack_dates[s_idx] if s_idx < len(haystack_dates) else None
            sid_part = (
                haystack_ids[s_idx] if s_idx < len(haystack_ids) else f"s{s_idx}"
            )
            turns: list[DialogueTurn] = []
            for t in session:
                if not isinstance(t, dict):
                    continue
                role = t.get("role", "user")
                if role not in ("user", "assistant"):
                    role = "user"
                text = (t.get("content") or "").strip()
                if not text:
                    continue
                turns.append(DialogueTurn(role=role, text=text))
            if not turns:
                continue
            sessions.append(
                DialogueSession(
                    session_id=f"{question_id}::{sid_part}",
                    timestamp=ts,
                    turns=turns,
                    source=source_label,
                )
            )
    return DialogueCorpus(name=source_label, sessions=sessions)


def load_longmemeval_oracle_corpus(
    path: str | Path = LONGMEMEVAL_ORACLE_PATH,
) -> DialogueCorpus:
    """Backward-compatible wrapper for the oracle variant."""
    return load_longmemeval_corpus(variant="oracle", path=path)


def session_length_summary(corpus: DialogueCorpus) -> dict[str, float]:
    if not corpus.sessions:
        return {"n_sessions": 0}
    turns = [s.n_turns for s in corpus.sessions]
    toks = [s.approx_token_count for s in corpus.sessions]
    return {
        "n_sessions": len(corpus.sessions),
        "turns_mean": sum(turns) / len(turns),
        "turns_min": min(turns),
        "turns_max": max(turns),
        "tokens_mean": sum(toks) / len(toks),
        "tokens_min": min(toks),
        "tokens_max": max(toks),
    }


__all__ = [
    "DialogueCorpus",
    "DialogueSession",
    "DialogueTurn",
    "LOCOMO_PATH",
    "LOCOMO_PERSONAS_PATH",
    "LONGMEMEVAL_ORACLE_PATH",
    "LONGMEMEVAL_S_PATH",
    "LONGMEMEVAL_M_PATH",
    "SKELETONS_DIR",
    "load_locomo_corpus",
    "load_longmemeval_corpus",
    "load_longmemeval_oracle_corpus",
    "session_length_summary",
]
