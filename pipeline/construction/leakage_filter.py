"""Leakage filter (data_plan §6.1; protocol §6.4).

Four layers:

1. ``check_lexical_leakage``         — case-insensitive literal match for
   the active version's value tokens in the current query.
2. ``check_update_relation_leakage`` — regex blacklist of phrases that
   explicitly signal an update relation ("I switched to", "no longer",
   "previously", "instead of"...). Protocol requires ZERO accepted samples
   matching these.
3. ``check_semantic_leakage``        — light stem-collapse paraphrase
   check that catches plural / inflected forms of value tokens that
   ``check_lexical_leakage`` misses (e.g. value="bullet list",
   query="...bullet-point list..."). This is intentionally heuristic and
   does NOT use an embedding model — embedding-based semantic leakage
   would be wired in via a separate optional path in Phase 1+.
4. ``check_degeneracy``              — regex blacklist of recall-shaped
   queries that turn the supposedly-behavioral current_query into a
   thinly disguised recall question ("what's my preference for X?",
   "remind me what my X is", "what did I tell you about X?"). Such
   queries are degenerate because they make the recall and behavior
   tasks identical.

The filter records pass/reject counts and per-rule rejection reasons so the
pilot can produce the leakage report required by protocol §6.4.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable

from pipeline.schema import Sample

# ---------------------------------------------------------------------------
# Update-relation regex blacklist
# ---------------------------------------------------------------------------

# These phrases would expose the update relation if present in the current
# query. The blacklist is intentionally case-insensitive and word-boundary
# anchored. Protocol §6.4 requires ZERO accepted samples that match.
_UPDATE_RELATION_PATTERNS = [
    r"\bswitched\s+to\b",
    r"\bswitched\s+from\b",
    r"\bchanged\s+(?:from|to|my\s+mind)\b",
    r"\bused\s+to\b",
    r"\bno\s+longer\b",
    r"\bnot\s+anymore\b",
    r"\bany\s*more\b",
    r"\binstead\s+of\b",
    r"\bpreviously\b",
    r"\bbefore[,]?\s+I\b",
    r"\bI\s+told\s+you\s+(?:before|earlier|previously)\b",
    r"\blast\s+(?:time|month|week)\s+I\s+said\b",
    r"\bas\s+I\s+(?:said|told|mentioned)\s+(?:before|earlier|previously)\b",
    r"\bnow\s+I(?:'m|\s+am)?\b",
    r"\bI'?ve?\s+(?:moved|switched|migrated|transitioned)\b",
    r"\binitially\b.*\bbut\b",
    r"\bI\s+revised\b",
    r"\bI\s+updated\b",
    r"\bsuperseded\b",
    r"\boutdated\b",
    r"\bI'?ll\s+go\s+back\s+to\b",
    r"\bback\s+to\b",
]

_UPDATE_RELATION_RE = re.compile(
    "|".join(_UPDATE_RELATION_PATTERNS), flags=re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Lexical leakage
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Includes common English function words plus high-frequency content words
# that produce false-positive lexical leakage matches when value strings
# include them descriptively (e.g. "first move", "two approvers", "change to").
_STOPWORDS = {
    # function words
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "at", "for", "with",
    "as", "is", "are", "was", "were", "be", "by", "from", "that", "this",
    "these", "those", "it", "its", "i", "you", "he", "she", "we", "they",
    "my", "your", "our", "their", "his", "her", "any", "no", "not",
    "do", "does", "did", "have", "has", "had", "will", "would", "should",
    "can", "could", "may", "might", "must", "than", "so", "if", "but",
    # common adverbs / quantifiers that easily collide
    "very", "just", "only", "even", "also", "still", "now", "then", "before",
    "after", "always", "never", "often", "again", "back", "forward",
    # common temporal / modifying adjectives + temporal nouns
    "new", "old", "first", "last", "next", "previous", "current", "future",
    "early", "late", "time", "day", "week", "month", "year", "today", "tomorrow",
    "yesterday", "morning", "afternoon", "evening", "night", "ago",
    # numbers and approximations as words
    "one", "two", "three", "four", "five", "ten", "many", "much", "more",
    "less", "few",
    # common verbs that appear in both value and unrelated query contexts
    "make", "made", "use", "used", "using", "go", "going", "want", "need",
    "need", "see", "say", "said", "tell", "told", "ask", "asked", "give",
    "given", "find", "found", "take", "took", "put", "set", "let",
    "change", "changed", "changes", "switch", "move", "keep", "kept",
    "include", "includes", "included",
}


def _tokenize_value(value) -> list[str]:
    if isinstance(value, str):
        s = value
    elif isinstance(value, list):
        s = " ".join(str(v) for v in value)
    elif isinstance(value, dict):
        s = " ".join(str(v) for v in value.values())
    else:
        s = str(value)
    toks = [t for t in _TOKEN_RE.findall(s.lower()) if t not in _STOPWORDS]
    # Drop very short fragments to reduce false positives ("a", "is", ...)
    return [t for t in toks if len(t) >= 3]


def _tokenize_value_with_signal(value) -> list[tuple[str, bool]]:
    """Tokenize keeping a "high-signal" flag per token.

    A token is *high-signal* if its raw form was capitalized (proper
    noun like "Greenhouse"/"Ashby") or contains a digit (specific value
    like "100"/"5pm"). High-signal tokens reveal the version directly
    when echoed in the query and so trip the leakage filter on a
    single match. Low-signal (lowercase common-English) tokens are
    abstract dimension words ("dollars", "minutes", "ingredients") that
    a query may legitimately mention to test the constraint without
    revealing the active value; these only trip the filter when ≥2
    overlap with the query.

    Used by ``check_lexical_leakage``; the returned ``raw`` is already
    lowercased so it can be intersected with query tokens directly.
    """
    if isinstance(value, str):
        s = value
    elif isinstance(value, list):
        s = " ".join(str(v) for v in value)
    elif isinstance(value, dict):
        s = " ".join(str(v) for v in value.values())
    else:
        s = str(value)
    out: list[tuple[str, bool]] = []
    for raw in _TOKEN_RE.findall(s):
        low = raw.lower()
        if low in _STOPWORDS or len(low) < 3:
            continue
        # high-signal: contains a digit, OR is a Capitalized proper noun
        # (and not the first word of a sentence — heuristic: longer than
        # 2 chars and original starts with uppercase letter).
        has_digit = any(c.isdigit() for c in raw)
        is_caps = len(raw) >= 2 and raw[0].isupper() and any(c.islower() for c in raw[1:])
        out.append((low, has_digit or is_caps))
    return out


def _content_tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class LeakageVerdict:
    sample_id: str
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    matched_tokens: list[str] = field(default_factory=list)
    matched_relation_phrases: list[str] = field(default_factory=list)
    matched_semantic_stems: list[str] = field(default_factory=list)
    matched_degeneracy_phrases: list[str] = field(default_factory=list)


@dataclass
class LeakageReport:
    total: int
    accepted: int
    rejected: int
    rejected_by_reason: dict[str, int]
    verdicts: list[LeakageVerdict]

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.accepted / self.total


# ---------------------------------------------------------------------------
# Layer 1: lexical
# ---------------------------------------------------------------------------


def check_lexical_leakage(sample: Sample) -> tuple[bool, list[str]]:
    """Return (leaks, matched_tokens).

    Protected vocabulary = **version-distinguishing** tokens (the union
    of v1-only and v2-only stems). Topic-shared tokens (present in both
    active and at least one outdated value) are NOT protected.

    **Hard vs soft signal** (2026-04-27 narrowing-pattern fix): a
    distinguishing token is *high-signal* if it was originally
    capitalized (proper noun like "Greenhouse") or contains a digit
    (specific value like "100"). Single-token leaks of high-signal
    tokens are real (echoing the brand / value gives away the version).
    *Low-signal* distinguishing tokens are lowercase abstract dimension
    words ("dollars", "minutes", "ingredients") that a narrowing query
    may legitimately mention to test the constraint without revealing
    the active value — these only trip the filter when ≥2 overlap with
    the query simultaneously. This unblocks narrowing-pattern queries
    that need to reference the constraint dimension by name without
    being forced to use synonyms.

    Carryover samples (no outdated versions) fall back to the strict
    behavior: all active-value tokens are protected as high-signal.
    """
    active = sample.gold.violation_predicate.must_honor
    # Tokens with case info — needed to split into hard/soft.
    active_signaled = _tokenize_value_with_signal(active.value)
    active_raw = {raw for raw, _ in active_signaled}
    if not active_raw:
        return False, []
    active_stems = {_stem(t) for t in active_raw}
    # Map raw -> high_signal across active vocab (last write wins for
    # repeats; harmless because protection is set-based).
    raw_signal: dict[str, bool] = {raw: hi for raw, hi in active_signaled}

    outdated_versions = sample.gold.violation_predicate.must_not_honor or []
    if outdated_versions:
        outdated_stems: set[str] = set()
        for v in outdated_versions:
            for raw, hi in _tokenize_value_with_signal(v.value):
                outdated_stems.add(_stem(raw))
                # carry signal info from outdated tokens so a v1-only
                # proper noun ("Greenhouse") still trips as hard.
                raw_signal.setdefault(raw, False)
                if hi:
                    raw_signal[raw] = True
        distinguishing_stems = (active_stems ^ outdated_stems)
        protected_raw = {t for t in active_raw if _stem(t) in distinguishing_stems}
        for v in outdated_versions:
            for raw, _ in _tokenize_value_with_signal(v.value):
                if _stem(raw) in distinguishing_stems and _stem(raw) not in active_stems:
                    protected_raw.add(raw)
    else:
        protected_raw = active_raw

    if not protected_raw:
        return False, []
    query_tokens = _content_tokens(sample.current_query)
    matched = sorted(protected_raw & query_tokens)
    if not matched:
        return False, []
    # Split matches by signal. Carryover (no outdated) falls back to
    # treating every match as hard — same as the pre-2026-04-27 strict
    # behavior.
    hard_matches = [t for t in matched if raw_signal.get(t, True)]
    soft_matches = [t for t in matched if not raw_signal.get(t, True)]
    if hard_matches:
        return True, matched
    # Only soft (lowercase common-English dimension) matches: require
    # ≥2 to flag as a leak.
    if len(soft_matches) >= 2:
        return True, matched
    return False, []


# ---------------------------------------------------------------------------
# Layer 2: update-relation regex
# ---------------------------------------------------------------------------


def check_update_relation_leakage(sample: Sample) -> tuple[bool, list[str]]:
    matches = _UPDATE_RELATION_RE.findall(sample.current_query)
    return bool(matches), matches


# ---------------------------------------------------------------------------
# Layer 3: semantic leakage (stem-collapse paraphrase)
# ---------------------------------------------------------------------------


# Strip simple English inflections so plural / progressive / past forms
# collide with the lemma. Deliberately conservative — we only collapse
# the most common suffixes (-ies, -ing, -ed, -ly, -s). Token stays
# untouched below 4 characters to avoid mangling short words
# ("ring" -> "r").
#
# 2026-04-26 (cluster H FP sweep): added -ly handling so "monthly" and
# "month" collide (h-drift / outbound-cadence FP), and dropped the -s
# minimum from len>4 to len>=4 so 4-letter plurals like "asks" / "runs"
# / "logs" stem to "ask" / "run" / "log". Both were silent stemmer
# bugs that caused cluster H to mis-fire on legitimate drift evidence.
def _stem(token: str) -> str:
    if len(token) < 4:
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if token.endswith("ly") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss") and len(token) >= 4:
        return token[:-1]
    return token


def _stemmed_tokens(text: str) -> set[str]:
    return {_stem(t) for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def check_semantic_leakage(sample: Sample) -> tuple[bool, list[str]]:
    """Return ``(leaks, matched_stems)``.

    Stem-collapse paraphrase check, mirroring ``check_lexical_leakage``
    semantics. Protected stems = union of v2-distinguishing and
    v1-distinguishing stems (topic-shared stems are not protected).
    """
    active = sample.gold.violation_predicate.must_honor
    raw_value_tokens = _tokenize_value(active.value)
    if not raw_value_tokens:
        return False, []
    active_stems = {_stem(t) for t in raw_value_tokens}
    outdated_versions = sample.gold.violation_predicate.must_not_honor or []
    if outdated_versions:
        outdated_stems: set[str] = set()
        for v in outdated_versions:
            outdated_stems |= {_stem(t) for t in _tokenize_value(v.value)}
        v2_distinguishing = active_stems - outdated_stems
        v1_distinguishing = outdated_stems - active_stems
        value_stems = v2_distinguishing | v1_distinguishing
    else:
        value_stems = active_stems
    if not value_stems:
        return False, []
    query_stems = _stemmed_tokens(sample.current_query)
    # Subtract literal lexical overlap so the same hit isn't double-counted.
    literal_overlap = set(raw_value_tokens) & {
        t for t in _TOKEN_RE.findall(sample.current_query.lower())
        if t not in _STOPWORDS
    }
    literal_stems = {_stem(t) for t in literal_overlap}
    semantic_only = sorted((value_stems & query_stems) - literal_stems)
    return bool(semantic_only), semantic_only


# ---------------------------------------------------------------------------
# Layer 4: query degeneracy (recall-shaped current_query)
# ---------------------------------------------------------------------------


# A current_query is "degenerate" when the user is essentially asking the
# model to recite the active version rather than to perform a behavioral
# task that would expose violation. These patterns convert the behavioral
# probe into a recall probe and must not be accepted.
_DEGENERACY_PATTERNS = [
    r"\bwhat'?s\s+my\s+(?:preference|rule|policy|usual|favorite|preferred|standard|default|setting)\b",
    r"\bwhat\s+(?:did|do)\s+i\s+(?:prefer|like|tell\s+you|say|usually\s+(?:do|like|use))\b",
    r"\bremind\s+me\s+(?:what|of\s+my|about\s+my)\b",
    r"\bwhat\s+(?:was|is)\s+my\s+(?:last|usual|previous|current|standing)\s+(?:rule|policy|preference|setting|order|format|approach)\b",
    r"\bwhat\s+did\s+we\s+(?:decide|agree|settle)\s+(?:on|about)\b",
    r"\bwhat\s+(?:do|did)\s+you\s+know\s+about\s+my\b",
    r"\bwhat'?s\s+the\s+rule\s+(?:for|about|on)\s+my\b",
    r"\btell\s+me\s+(?:my|what\s+my)\s+(?:preference|rule|policy|standing)\b",
]
_DEGENERACY_RE = re.compile("|".join(_DEGENERACY_PATTERNS), flags=re.IGNORECASE)


def check_degeneracy(sample: Sample) -> tuple[bool, list[str]]:
    """Return ``(degenerate, matched_phrases)`` based on the current_query."""
    matches = _DEGENERACY_RE.findall(sample.current_query)
    return bool(matches), matches


# ---------------------------------------------------------------------------
# Top-level filter
# ---------------------------------------------------------------------------


def filter_sample(sample: Sample) -> LeakageVerdict:
    reasons: list[str] = []
    matched_tokens: list[str] = []
    matched_relation: list[str] = []
    matched_semantic: list[str] = []
    matched_degeneracy: list[str] = []

    leaks_lex, tokens = check_lexical_leakage(sample)
    if leaks_lex:
        reasons.append("active_value_lexical_leakage")
        matched_tokens = tokens

    leaks_rel, phrases = check_update_relation_leakage(sample)
    if leaks_rel:
        reasons.append("update_relation_leakage")
        matched_relation = phrases

    leaks_sem, sem_stems = check_semantic_leakage(sample)
    if leaks_sem:
        reasons.append("active_value_semantic_leakage")
        matched_semantic = sem_stems

    degen, degen_phrases = check_degeneracy(sample)
    if degen:
        reasons.append("query_degeneracy")
        matched_degeneracy = degen_phrases

    accepted = not reasons
    return LeakageVerdict(
        sample_id=sample.sample_id,
        accepted=accepted,
        reasons=reasons,
        matched_tokens=matched_tokens,
        matched_relation_phrases=matched_relation,
        matched_semantic_stems=matched_semantic,
        matched_degeneracy_phrases=matched_degeneracy,
    )


def filter_samples(samples: Iterable[Sample]) -> LeakageReport:
    verdicts: list[LeakageVerdict] = []
    counter: Counter[str] = Counter()
    for s in samples:
        v = filter_sample(s)
        verdicts.append(v)
        for r in v.reasons:
            counter[r] += 1
    accepted = sum(1 for v in verdicts if v.accepted)
    return LeakageReport(
        total=len(verdicts),
        accepted=accepted,
        rejected=len(verdicts) - accepted,
        rejected_by_reason=dict(counter),
        verdicts=verdicts,
    )


__all__ = [
    "LeakageReport",
    "LeakageVerdict",
    "check_degeneracy",
    "check_lexical_leakage",
    "check_semantic_leakage",
    "check_update_relation_leakage",
    "filter_sample",
    "filter_samples",
]
