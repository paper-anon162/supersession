"""Naturalness scanner for distractor sessions and finished samples.

Two complementary uses:

1. ``is_distractor_natural(session)`` — gate distractor sampling at
   realization time so the LongMemEval / LoCoMo source corpora's most
   blatant non-conversational artifacts (web-result dumps, multi-part
   document feeds, role-play openers, model self-disclosure) don't
   leak into a SupersessionBench history.

2. ``scan_sample`` / ``scan_dataset`` / ``scan_dataset_file`` — audit a
   finished dataset and return per-sample / per-category violation
   reports that the data-construction audit can cite directly.

Categories (deliberately conservative — each pattern was observed at
least once in `data/realized_phase2_*_full.jsonl` per
DATA_CONSTRUCTION_AUDIT.md):

- ``ai_disclaimer``       : "as an AI language model", etc.
- ``raw_web_artifact``    : "Web search results", "sourceText",
                            article-list scaffolding, raw source dumps.
- ``staged_qa_artifact``  : multi-part document feeds — "Part 5
                            (acknowledge and wait for the next part)",
                            "Here is the final part:", etc.
- ``roleplay_opener``     : persona injection — "act as a", "you are
                            now", "pretend to be".
- ``corporate_jargon``    : narrow product/topic markers that the audit
                            flagged as breaking the single-user
                            illusion (Brexit, D365, Navision, "sales
                            funnels", "Ankara fashion", "taxonomy of N
                            categories").

The scanner is intentionally *not* a paraphrase / semantic check — it
only catches artifacts that have a deterministic surface signature.
Borderline naturalness still needs human review.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Pattern catalogue
# ---------------------------------------------------------------------------

NaturalnessCategory = str  # informal alias; values listed below.

_CATEGORY_PATTERNS: dict[NaturalnessCategory, list[str]] = {
    "ai_disclaimer": [
        r"\bas an ai\b",
        r"\bas an ai language model\b",
        r"\bi'?m an ai\b",
        r"\bi am an ai\b",
        r"\bas a language model\b",
        r"\bi'?m just a language model\b",
        r"\bi don'?t have personal\b",
        r"\bi do not have personal\b",
        r"\bi don'?t have memories\b",
        r"\bi do not have memories\b",
        r"\bi'?m not able to\b",
        r"\bi cannot recall\b",
        r"\bi can'?t recall\b",
        r"\bi don'?t have access to\b",
        r"\bi do not have access to\b",
        r"\bi'?m sorry,?\s+but i cannot\b",
    ],
    "raw_web_artifact": [
        r"\bweb search results\b",
        r"\bsourcetext\b",
        r"<doc[\s>]",
        r"\bhere are the (?:articles|results|links|sources)\b",
        r"\barticle links\b",
        r"\bsearch results\s*[:\-]\s*",
    ],
    "staged_qa_artifact": [
        r"\bpart \d+\s*\(",
        r"\bhere is the final part\b",
        r"\bhere is part \d+\b",
        r"\backnowledge and wait for the next part\b",
        r"\bi'?ll send (?:you )?the (?:next|rest|remaining) part",
    ],
    "roleplay_opener": [
        # `act as a`: only flag when followed by a persona-noun. Bare
        # `act as a buffer` / `act as a sponsor` are normal English
        # ("act as a [structural/functional role]") and were producing
        # false positives on legitimate event-session content.
        r"\bact as an? (?:\w+\s+){0,3}(expert|professional|consultant|specialist|coach|guide|tutor|advisor|instructor|teacher|trainer|character|persona|assistant|chatbot|bot|writer|editor|reviewer|analyst|judge|critic)\b",
        r"\byou are now an?\b",
        r"\bpretend to be an?\b",
        r"\byour role is to\b",
        r"\byou will play the role of\b",
    ],
    "corporate_jargon": [
        r"\bbrexit\b",
        r"\bd365\b",
        r"\bnavision\b",
        r"\bankara\s+fashion\b",
        r"\bsales funnels?\b",
        r"\btaxonomy of \d+\s+categor",
        r"\btypography style guide\b",
    ],
}

_COMPILED: dict[NaturalnessCategory, re.Pattern[str]] = {
    cat: re.compile("|".join(pats), flags=re.IGNORECASE)
    for cat, pats in _CATEGORY_PATTERNS.items()
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NaturalnessHit:
    category: NaturalnessCategory
    phrase: str
    session_id: str | None = None
    turn_role: str | None = None


@dataclass
class NaturalnessIssue:
    """Per-sample naturalness scan result."""

    sample_id: str
    sample_type: str | None
    horizon: str | None
    failure_patterns: list[str]
    hits: list[NaturalnessHit] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.hits

    @property
    def categories(self) -> list[NaturalnessCategory]:
        return sorted({h.category for h in self.hits})


@dataclass
class NaturalnessReport:
    file: str | None
    n_samples: int
    n_clean: int
    issues: list[NaturalnessIssue]
    rejected_by_category: dict[NaturalnessCategory, int]

    @property
    def n_dirty(self) -> int:
        return self.n_samples - self.n_clean

    @property
    def pass_rate(self) -> float:
        if self.n_samples == 0:
            return 0.0
        return self.n_clean / self.n_samples


# ---------------------------------------------------------------------------
# Scan primitives
# ---------------------------------------------------------------------------


def scan_text(text: str) -> list[tuple[NaturalnessCategory, str]]:
    """Return a list of ``(category, matched_phrase)`` tuples."""
    out: list[tuple[NaturalnessCategory, str]] = []
    for cat, pat in _COMPILED.items():
        for m in pat.finditer(text):
            out.append((cat, m.group(0)))
    return out


def _iter_session_turns(session: Any) -> Iterable[tuple[str | None, str]]:
    """Yield ``(role, text)`` from a session object that may be a dataclass,
    a Pydantic model, or a plain dict (as produced by JSONL loaders).
    """
    turns = getattr(session, "turns", None)
    if turns is None and isinstance(session, dict):
        turns = session.get("turns", [])
    for t in turns or []:
        if isinstance(t, dict):
            role = t.get("role")
            text = t.get("text", "")
        else:
            role = getattr(t, "role", None)
            text = getattr(t, "text", "")
        yield role, text or ""


def scan_session(session: Any) -> list[NaturalnessHit]:
    sid = getattr(session, "session_id", None)
    if sid is None and isinstance(session, dict):
        sid = session.get("session_id")
    hits: list[NaturalnessHit] = []
    for role, text in _iter_session_turns(session):
        for cat, phrase in scan_text(text):
            hits.append(
                NaturalnessHit(
                    category=cat, phrase=phrase, session_id=sid, turn_role=role,
                )
            )
    return hits


def is_distractor_natural(session: Any) -> bool:
    """Used by the realizer's distractor sampler. Returns False if the
    session contains any artifact pattern from any category.
    """
    for _, text in _iter_session_turns(session):
        for pat in _COMPILED.values():
            if pat.search(text):
                return False
    return True


# ---------------------------------------------------------------------------
# Distractor topic-orthogonality (protocol §9.2.2)
# ---------------------------------------------------------------------------


_TOPIC_TOKEN_RE = re.compile(r"[a-z][a-z0-9\-]{2,}")
# Function words / generic content words that appear frequently in
# both target descriptions and unrelated distractor sessions and would
# trigger false-positive rejection. Same shape as leakage_filter's
# stopword list.
_TOPIC_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "these",
    "those", "have", "has", "had", "into", "user", "users", "morning",
    "evening", "afternoon", "today", "tomorrow", "yesterday", "week",
    "month", "year", "time", "day", "your", "what", "when", "where",
    "should", "would", "could", "about", "after", "before", "their",
    "them", "they", "any", "all", "one", "two", "three", "five", "ten",
    "many", "much", "more", "less", "few", "preferred", "preference",
    "rule", "policy", "setting", "default", "standard", "active",
    "current", "previous", "version", "format", "style", "kind",
    "type", "name", "value", "list", "item", "entry",
}


def _topic_tokens(text: str) -> set[str]:
    return {
        t for t in _TOPIC_TOKEN_RE.findall(text.lower())
        if t not in _TOPIC_STOPWORDS and len(t) >= 4
    }


def is_distractor_topic_orthogonal(
    session: Any, *, target_tokens: Iterable[str], min_overlap: int = 1,
) -> bool:
    """Return False if the distractor session shares too many topical
    tokens with the spine's target slot.

    ``target_tokens`` is the token set derived from the spine's
    target_description, target_slot_id, and active value's
    distinguishing string. The default ``min_overlap=1`` rejects any
    session that mentions even one such token — strict by design,
    since distractor topical overlap directly contaminates supersession
    measurement (e.g. an "morning_beverage" target with a distractor
    talking about coffee).

    Callers typically build the target token set once per spine via
    ``build_target_tokens()`` and pass it on each candidate.
    """
    targets = {t.lower() for t in target_tokens if isinstance(t, str)}
    if not targets:
        return True
    for _, text in _iter_session_turns(session):
        if len(_topic_tokens(text) & targets) >= min_overlap:
            return False
    return True


def build_target_tokens(
    *,
    target_description: str = "",
    target_slot_id: str = "",
    active_value: str | list | dict = "",
    distinguishing_extra: Iterable[str] = (),
) -> set[str]:
    """Build the token set used by ``is_distractor_topic_orthogonal``.

    Combines the spine's target_description, target_slot_id, and the
    active value's distinguishing string. ``distinguishing_extra``
    lets the caller add domain-specific tokens (e.g. brand names,
    proper nouns) that the default tokenizer might miss.
    """
    pieces = [target_description, target_slot_id]
    if isinstance(active_value, str):
        pieces.append(active_value)
    elif isinstance(active_value, list):
        pieces.extend(str(x) for x in active_value)
    elif isinstance(active_value, dict):
        pieces.extend(f"{k} {v}" for k, v in active_value.items())
    out: set[str] = set()
    for piece in pieces:
        out |= _topic_tokens(piece or "")
    for extra in distinguishing_extra:
        if isinstance(extra, str):
            out |= _topic_tokens(extra)
    return out


# ---------------------------------------------------------------------------
# Sample / dataset scan
# ---------------------------------------------------------------------------


def _sample_field(sample: Any, key: str, default=None):
    if isinstance(sample, dict):
        return sample.get(key, default)
    return getattr(sample, key, default)


def _sample_metadata(sample: Any) -> dict:
    """Pull metadata out of either the dict shape (`_gold.metadata`) or the
    Pydantic shape (`gold.metadata`)."""
    if isinstance(sample, dict):
        gold = sample.get("_gold") or sample.get("gold") or {}
        if isinstance(gold, dict):
            return gold.get("metadata") or {}
        meta = getattr(gold, "metadata", None)
        return meta if isinstance(meta, dict) else {}
    gold = getattr(sample, "gold", None)
    meta = getattr(gold, "metadata", None) if gold is not None else None
    if meta is None:
        return {}
    if hasattr(meta, "model_dump"):
        return meta.model_dump()
    return dict(meta) if isinstance(meta, dict) else {}


def scan_sample(sample: Any) -> NaturalnessIssue:
    sid = _sample_field(sample, "sample_id", "?")
    stype = _sample_field(sample, "sample_type")
    history = _sample_field(sample, "history") or []
    meta = _sample_metadata(sample)
    horizon = meta.get("horizon")
    failure_patterns = list(meta.get("failure_patterns") or [])

    hits: list[NaturalnessHit] = []
    for sess in history:
        hits.extend(scan_session(sess))
    return NaturalnessIssue(
        sample_id=sid,
        sample_type=stype,
        horizon=horizon,
        failure_patterns=failure_patterns,
        hits=hits,
    )


def scan_dataset(samples: Iterable[Any], *, file: str | None = None) -> NaturalnessReport:
    issues: list[NaturalnessIssue] = []
    counter: Counter[NaturalnessCategory] = Counter()
    n = 0
    n_clean = 0
    for s in samples:
        n += 1
        issue = scan_sample(s)
        issues.append(issue)
        if issue.clean:
            n_clean += 1
        else:
            for cat in issue.categories:
                counter[cat] += 1
    return NaturalnessReport(
        file=file,
        n_samples=n,
        n_clean=n_clean,
        issues=issues,
        rejected_by_category=dict(counter),
    )


def scan_dataset_file(path: str | Path) -> NaturalnessReport:
    p = Path(path)
    samples = []
    with p.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            samples.append(json.loads(line))
    return scan_dataset(samples, file=str(p))


__all__ = [
    "NaturalnessCategory",
    "NaturalnessHit",
    "NaturalnessIssue",
    "NaturalnessReport",
    "build_target_tokens",
    "is_distractor_natural",
    "is_distractor_topic_orthogonal",
    "scan_dataset",
    "scan_dataset_file",
    "scan_sample",
    "scan_session",
    "scan_text",
]
