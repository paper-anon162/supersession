"""Gold-vs-history consistency audit for Phase 2 samples.

Detects eight clusters of construction defects surfaced by the
2026-04-26 30-sample human audit and the 2026-04-26 v9 drift sweep:

  Cluster A: gold active value contains content tokens that never
             appear in any session of the history. (Hand-authored
             seeds may carry "spec lore" not actually realized into
             the dialogue.)
  Cluster B: ``session_introduced`` field on the active version
             points at a session that does NOT contain the active
             value's distinguishing tokens. The actual evidence sits
             in some other (usually earlier) session.
  Cluster C: implicit_drift active session lacks user-role agency —
             evidence is a one-off third-party reference or single
             passive mention, not the user repeatedly establishing
             the new pattern.
  Cluster D: ``failure_patterns`` carries the ``narrowing`` label,
             but at least one consecutive (v_i, v_{i+1}) pair is a
             pure replacement (v_{i+1} value is not a token-subset of
             v_i). Label semantics are sliding from "chain has at
             least one narrowing transition" to "chain narrows
             monotonically".
  Cluster E: active.value carries distinguishing chunks (split on
             top-level connectors) with zero token overlap in the
             whole history. Stricter than A: even one fabricated
             chunk fires.
  Cluster F: implicit_drift active session opens with an
             observational / status-check speech act ("Did the X
             arrive?") and contains no declarative phrase rescuing
             the drift inference.
  Cluster G: implicit_drift active session leaks explicit-change
             phrasing ("the old X", "now I just X", "cutting X out
             entirely", "stick to Y only", "I X now") that
             contradicts the implicit form. Symmetric to F: F flags
             too-passive sessions; G flags too-active ones.
  Cluster H: implicit_drift active session has a v2-distinguishing
             chunk whose tokens never surface in any USER turn of
             that session. Stricter than C/E for drift: a chunk
             counts only if it carries v2-distinguishing stems
             (active.value stems minus outdated stems), and coverage
             is checked per chunk in user turns of the active session
             only — not assistant turns, not other sessions.
  Cluster J: Phase 3 only — implicit_drift sample's gold-only
             ``active_evidence`` field (populated by the Sonnet 4.6
             extractor pass, see active_evidence.py) fails one or
             more §10.4 rules: <2 items, evidence_text not verbatim,
             session_id pre-outdated, evidence uses explicit
             replacement language. Phase 2 samples (no active_evidence
             field) are skipped — they aren't required to carry one.

Usage
-----

    from pipeline.construction.audit_gold_consistency import audit_sample

    findings = audit_sample(sample)
    if findings:  # any non-empty list = at least one cluster fired
        ...

Each finding is a small dataclass with ``cluster`` ∈ {A, B, C, D}
plus a short human-readable ``reason`` string and the affected
tokens / sessions, so callers can route to per-cluster handling
(e.g. retry the realizer, re-label, or mark ambiguous).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from pipeline.construction.leakage_filter import (
    _TOKEN_RE,
    _content_tokens,
    _stem,
    _tokenize_value,
)
from pipeline.schema import Sample

# Tunable thresholds, validated against the 30-sample human audit
# (2026-04-26). Calibration target: catch all 5 annotator-flagged
# samples while avoiding flagging the 25 annotator-passed ones with too
# many false positives.
#
# - _SESSION_EVIDENCING_MIN_RATIO: a single session must carry ≥50% of
#   the active value's distinguishing stems before counting as
#   evidencing that session (used for cluster B).
# - _CLUSTER_A_HISTORY_MIN_RATIO: ≥50% of active value stems must
#   appear somewhere across the whole history. Below this, the gold
#   contains "spec lore" not actually realized into dialogue
#   (h-expl-pro-002 sits at 33%; f-drift-con-001 at 80%; threshold
#   cleanly separates).
# - _CLUSTER_C_USER_MIN_RATIO: drift-only — user-role text must carry
#   ≥50% of active value stems. Below this, the active value is
#   surfaced predominantly by assistant or third-party turns
#   (p2-drift-feedback-001 user-coverage 20% vs all-coverage 60%).
# - _CLUSTER_D_MIN_OVERLAP_RATIO: narrowing chain consecutive-pair
#   token overlap floor; below this AND v_next shorter than v_prev →
#   true replacement, not narrowing.
_SESSION_EVIDENCING_MIN_RATIO = 0.5
_CLUSTER_A_HISTORY_MIN_RATIO = 0.5
_CLUSTER_C_USER_MIN_RATIO = 0.5
_CLUSTER_D_MIN_OVERLAP_RATIO = 0.05


@dataclass
class GoldConsistencyFinding:
    cluster: str  # one of "A", "B", "C", "D"
    reason: str
    detail: dict = field(default_factory=dict)


def _stems(tokens: Iterable[str]) -> set[str]:
    return {_stem(t) for t in tokens}


def _session_text(sess) -> str:
    return " ".join(t.text for t in sess.turns)


def _user_text(sess) -> str:
    return " ".join(t.text for t in sess.turns if t.role == "user")


def _sessions_evidencing(active_value, sessions, *, role: str = "all") -> list[int]:
    """Return 1-based session indices whose `role` text shares enough
    distinguishing tokens with ``active_value`` to count as evidence.

    role="all"  → all turns
    role="user" → user turns only (cluster C user-agency check)
    """
    raw = _tokenize_value(active_value)
    if not raw:
        return []
    active_stems = _stems(raw)
    if not active_stems:
        return []
    out: list[int] = []
    for i, sess in enumerate(sessions, start=1):
        text = _user_text(sess) if role == "user" else _session_text(sess)
        sess_stems = _stems(_content_tokens(text))
        overlap = active_stems & sess_stems
        ratio = len(overlap) / max(1, len(active_stems))
        if ratio >= _SESSION_EVIDENCING_MIN_RATIO:
            out.append(i)
    return out


def _coverage(active_value, text: str) -> tuple[float, set[str]]:
    """Return (coverage_ratio, missing_stems) of active value tokens in text."""
    raw = _tokenize_value(active_value)
    active_stems = _stems(raw)
    if not active_stems:
        return 1.0, set()
    text_stems = _stems(_content_tokens(text))
    missing = active_stems - text_stems
    coverage = (len(active_stems) - len(missing)) / len(active_stems)
    return coverage, missing


# ---------------------------------------------------------------------------
# Cluster A — active value tokens missing from entire history
# ---------------------------------------------------------------------------


def check_cluster_A_active_tokens_in_history(sample: Sample) -> GoldConsistencyFinding | None:
    """Flag samples whose active value has < _CLUSTER_A_HISTORY_MIN_RATIO
    coverage in the history. A single missing descriptive token (e.g.
    "direct" within "conversational direct, first-person") is allowed
    as long as the bulk of the value is realized into dialogue."""
    active = sample.gold.violation_predicate.must_honor
    history_text = " ".join(_session_text(s) for s in sample.history)
    coverage, missing = _coverage(active.value, history_text)
    if coverage < _CLUSTER_A_HISTORY_MIN_RATIO:
        return GoldConsistencyFinding(
            cluster="A",
            reason=(
                f"only {coverage*100:.0f}% of active.value stems appear in "
                f"history (threshold ≥{_CLUSTER_A_HISTORY_MIN_RATIO*100:.0f}%); "
                f"missing: {sorted(missing)}"
            ),
            detail={
                "coverage": coverage,
                "missing_stems": sorted(missing),
                "active_value": active.value,
            },
        )
    return None


# ---------------------------------------------------------------------------
# Cluster B — session_introduced points at a session that doesn't carry
#             the active value's distinguishing tokens
# ---------------------------------------------------------------------------


def check_cluster_B_session_introduced_mismatch(
    sample: Sample,
) -> GoldConsistencyFinding | None:
    """Detect session_introduced mismatch using *v2-distinguishing* tokens.

    Earlier draft used the union of active.value tokens, which produced
    false positives whenever v1 and v2 shared most vocabulary (e.g.
    'one Sunday meal-prep session' vs 'two meal-prep sessions per week
    (Sunday and Wednesday)' — both tokenize to {meal, prep, session,
    sunday, ...}). The v1-establishing session would slip past the
    50% threshold and get picked as 'actual'. We now compute the
    *distinguishing* stems (active stems minus union of outdated
    stems) and only flag when those distinguishing stems appear in a
    different session than ``claimed``.
    """
    active = sample.gold.violation_predicate.must_honor
    if not sample.history:
        return None

    active_stems = _stems(_tokenize_value(active.value))
    if not active_stems:
        return None
    outdated_stems: set[str] = set()
    for ov in sample.gold.violation_predicate.must_not_honor or []:
        outdated_stems |= _stems(_tokenize_value(ov.value))
    distinguishing = active_stems - outdated_stems
    if not distinguishing:
        # v1 and v2 share full vocabulary (e.g. quantitative-only delta);
        # we can't programmatically distinguish session-by-session.
        return None

    claimed = active.session_introduced
    actual: list[int] = []
    for i, sess in enumerate(sample.history, start=1):
        sess_stems = _stems(_content_tokens(_session_text(sess)))
        if distinguishing & sess_stems:
            actual.append(i)
    if not actual:
        # No session contains any v2-distinguishing token — Cluster A
        # / E territory, not B.
        return None
    if claimed not in actual:
        return GoldConsistencyFinding(
            cluster="B",
            reason=(
                f"session_introduced={claimed} but the v2-distinguishing "
                f"tokens {sorted(distinguishing)[:6]} appear in sessions "
                f"{actual}"
            ),
            detail={
                "claimed_session": claimed,
                "actual_sessions": actual,
                "distinguishing_stems": sorted(distinguishing),
                "active_value": active.value,
            },
        )
    return None


# ---------------------------------------------------------------------------
# Cluster C — drift active session lacks user-role agency
# ---------------------------------------------------------------------------


def check_cluster_C_drift_user_agency(sample: Sample) -> GoldConsistencyFinding | None:
    """Flag implicit_drift samples whose user-role text covers fewer
    than _CLUSTER_C_USER_MIN_RATIO of the active value's distinguishing
    tokens. A blind reader cannot infer that the user (not someone
    else) shifted to the new pattern when the new tokens come
    predominantly from assistant or third-party turns."""
    patterns = list(getattr(sample.gold.metadata, "failure_patterns", None) or [])
    if "implicit_drift" not in patterns:
        return None

    active = sample.gold.violation_predicate.must_honor
    user_text = " ".join(
        t.text for sess in sample.history for t in sess.turns if t.role == "user"
    )
    user_cov, _ = _coverage(active.value, user_text)
    history_text = " ".join(_session_text(s) for s in sample.history)
    hist_cov, _ = _coverage(active.value, history_text)

    if user_cov < _CLUSTER_C_USER_MIN_RATIO:
        return GoldConsistencyFinding(
            cluster="C",
            reason=(
                f"user-role coverage of active value is {user_cov*100:.0f}% "
                f"(history-wide {hist_cov*100:.0f}%; threshold "
                f"≥{_CLUSTER_C_USER_MIN_RATIO*100:.0f}%). Active value is "
                f"surfaced by assistant or third-party turns, not the user "
                f"themselves; drift inference requires user-role agency."
            ),
            detail={
                "user_coverage": user_cov,
                "history_coverage": hist_cov,
                "active_value": active.value,
            },
        )
    return None


# ---------------------------------------------------------------------------
# Cluster D — narrowing label conflated with replacement transition
# ---------------------------------------------------------------------------


def check_cluster_D_narrow_label_mismatch(
    sample: Sample,
) -> GoldConsistencyFinding | None:
    """Flag narrowing chains whose consecutive pair (v_prev, v_next)
    looks like a *replacement* (different vocabulary AND v_next is
    shorter) rather than a true narrowing. Narrowing should add
    constraints; surface tokens often differ between v_i values, so
    we use a combined rule: low token overlap (<25%) AND v_next char
    length below v_prev's. Both must hold to flag — single-condition
    rules over-fire."""
    patterns = list(getattr(sample.gold.metadata, "failure_patterns", None) or [])
    if "narrowing" not in patterns:
        return None
    versions = sorted(
        sample.gold.target_versions, key=lambda v: v.session_introduced
    )
    if len(versions) < 2:
        return None
    bad_pairs: list[dict] = []
    for v_prev, v_next in zip(versions, versions[1:]):
        prev_stems = _stems(_tokenize_value(v_prev.value))
        next_stems = _stems(_tokenize_value(v_next.value))
        if not prev_stems or not next_stems:
            continue
        overlap = prev_stems & next_stems
        ratio = len(overlap) / max(1, len(prev_stems | next_stems))
        prev_len = len(str(v_prev.value))
        next_len = len(str(v_next.value))
        if ratio < _CLUSTER_D_MIN_OVERLAP_RATIO and next_len < prev_len:
            bad_pairs.append({
                "v_prev": v_prev.version_id,
                "v_next": v_next.version_id,
                "token_overlap_ratio": round(ratio, 2),
                "prev_chars": prev_len,
                "next_chars": next_len,
            })
    if bad_pairs:
        return GoldConsistencyFinding(
            cluster="D",
            reason=(
                f"failure_patterns includes 'narrowing' but transition(s) "
                f"{[p['v_prev']+'→'+p['v_next'] for p in bad_pairs]} look like "
                f"replacement (low token overlap AND v_next shorter)"
            ),
            detail={"replacement_pairs": bad_pairs},
        )
    return None


# ---------------------------------------------------------------------------
# Cluster E — active value over-specifies attributes not in any session
# ---------------------------------------------------------------------------


# Split active.value into "distinguishing chunks" — the gold author
# usually concatenates several attributes with these connectors. Each
# chunk encodes one promise the model is expected to honor; if any
# whole chunk is unrealized in dialogue, the gold over-specifies.
import re as _re

# Strip parenthesized content entirely before chunking — parenthetical
# lists (e.g. "fresh fruit (apple or pear)" or "tracks (e.g. Pixies,
# Fugazi)") are normally examples, not separately required attributes.
# Treating them as required would false-positive on legitimate
# example-list golds.
_PAREN_CONTENT_RE = _re.compile(r"\s*\([^)]*\)")
# Split on top-level structural connectors. ";" and "—" / " - " are
# strong separators; ", " and " and "/" with " separate co-required
# attributes. We deliberately DO NOT split on "or" — top-level "or"
# usually signals optionality ("apple or pear" = either is fine).
#
# Special case for " with ": skip when the right-hand side is just
# "the/a/an + single token + clause-end". "send a written note with
# the substance" should not split into ["send a written note", "the
# substance"] — "with the substance" is an integral phrase, not a
# co-required attribute. Multi-token RHS like "with one-line atomic
# notes" or "with the daily-notes plugin and ..." still splits.
_CHUNK_SPLIT_RE = _re.compile(
    r"\s*[,;]\s*"
    r"|\s+(?:and|plus)\s+"
    r"|\s+with\s+(?!(?:the|a|an)\s+\w+\s*(?:[,;.]|$))"
    r"|\s+—\s+|\s+--\s+|\s+-\s+",
    flags=_re.IGNORECASE,
)


# Negation prefixes — chunks like "no narrative" or "without diagrams"
# claim the *absence* of an attribute and don't need separate
# evidence; the active session shows the new behavior, not negative
# space. These chunks are dropped from cluster E.
_NEGATION_PREFIX_RE = _re.compile(
    r"^(?:no\s+|not\s+|without\s+|none\s+of\s+|skip\s+)",
    flags=_re.IGNORECASE,
)


def _value_chunks(value) -> list[str]:
    if not isinstance(value, str):
        return [str(value)]
    stripped = _PAREN_CONTENT_RE.sub("", value)
    raw = _CHUNK_SPLIT_RE.split(stripped)
    out: list[str] = []
    for c in raw:
        c = c.strip()
        if not c:
            continue
        if _NEGATION_PREFIX_RE.match(c):
            continue
        out.append(c)
    return out


def check_cluster_E_active_value_over_specification(
    sample: Sample,
) -> GoldConsistencyFinding | None:
    """Flag samples whose active.value carries distinguishing chunks
    that the realized history never establishes.

    Stricter than cluster A: cluster A flags only when ≥50% of overall
    tokens are missing. Cluster E flags when ANY single chunk has
    zero token overlap with history — even one fabricated chunk means
    the gold over-specifies a behavioral attribute the user never
    declared.
    """
    active = sample.gold.violation_predicate.must_honor
    chunks = _value_chunks(active.value)
    if len(chunks) < 2:
        # Single-chunk active values are covered by cluster A.
        return None
    history_text = " ".join(_session_text(s) for s in sample.history)
    history_stems = _stems(_content_tokens(history_text))
    bad_chunks: list[dict] = []
    for chunk in chunks:
        chunk_stems = _stems(_tokenize_value(chunk))
        if not chunk_stems:
            continue
        if not (chunk_stems & history_stems):
            bad_chunks.append(
                {"chunk": chunk, "stems": sorted(chunk_stems)}
            )
    if bad_chunks:
        return GoldConsistencyFinding(
            cluster="E",
            reason=(
                f"active value contains chunk(s) with zero history "
                f"overlap: {[b['chunk'] for b in bad_chunks]}. The gold "
                f"over-specifies an attribute the user never establishes."
            ),
            detail={"bad_chunks": bad_chunks, "active_value": active.value},
        )
    return None


# ---------------------------------------------------------------------------
# Cluster F — drift active session uses observational speech act, not
#             a declarative one
# ---------------------------------------------------------------------------


# Patterns that consistently encode "user is asking about a past event /
# checking a third-party action" rather than "user is declaring a new
# preference". These are the speech-act signatures that the 2026-04-26
# audit found surfaced borderline drift cases.
_OBSERVATIONAL_OPENERS = _re.compile(
    r"(?:^|\n)\s*(?:hey,?\s+)?(?:"
    r"did\s+(?:the|my|that|those|i|she|he|they|we)\b|"
    r"quick\s+check\b|"
    r"just\s+checking\b|"
    r"is\s+the\s+\w+\s+(?:working|on\s+track|ready|flagged|in\s+place)\b|"
    r"can\s+you\s+(?:check|verify|confirm)\s+(?:whether|if|the|my)\b|"
    r"do\s+you\s+(?:see|have)\s+the\b"
    r")",
    flags=_re.IGNORECASE,
)


# Phrases that, when present in the user-role active session text,
# indicate an explicit declarative speech act and override an
# observational-opener flag (the user IS declaring even after a
# prefatory "did the X arrive").
_DECLARATIVE_PHRASES = _re.compile(
    r"(?:"
    r"\bgoing\s+forward\b|"
    r"\bfrom\s+now\s+on\b|"
    r"\bI('|\s)?(m|ve|ll)?\s+(switching|switched|moving|moved|starting|cutting|"
    r"dropping|sticking|locking)\b|"
    r"\bnew\s+rule\b|"
    r"\bnew\s+policy\b|"
    r"\bnew\s+routine\b|"
    r"\bI\s+want\s+(?:to\s+)?(?:start|stop|switch|move)\b"
    r")",
    flags=_re.IGNORECASE,
)


def check_cluster_F_drift_observational_opener(
    sample: Sample,
) -> GoldConsistencyFinding | None:
    """Flag implicit_drift samples whose active session opens with a
    *status-check* / *observation* speech act and lacks any declarative
    phrase elsewhere in the same session.

    Catches the borderline drift case the human auditor surfaced
    (#7 Priya's Loom, #8 Marcus's paragraph): user mentions the
    active value's tokens passively (asking about a delivery,
    observing a third-party action) without committing to a new
    pattern. A blind reader can't tell "noticed" from "now does".
    """
    patterns = list(getattr(sample.gold.metadata, "failure_patterns", None) or [])
    if "implicit_drift" not in patterns:
        return None
    active = sample.gold.violation_predicate.must_honor
    if not sample.history:
        return None
    idx = active.session_introduced
    if not (1 <= idx <= len(sample.history)):
        return None
    sess = sample.history[idx - 1]
    user_text = "\n".join(t.text for t in sess.turns if t.role == "user")
    if not user_text:
        return None
    if not _OBSERVATIONAL_OPENERS.search(user_text):
        return None
    # Observational opener present — only flag if no declarative phrase
    # rescues the session (e.g. "Did the kombucha arrive? From now on
    # I'm drinking it nightly" is fine).
    if _DECLARATIVE_PHRASES.search(user_text):
        return None
    return GoldConsistencyFinding(
        cluster="F",
        reason=(
            "active session user-role text opens with an observational / "
            "status-check speech act and contains no declarative phrase "
            "('going forward', 'from now on', 'new rule', etc.). A blind "
            "reader cannot reliably infer that the user has shifted "
            "preference rather than merely noticed a one-off event."
        ),
        detail={
            "active_session_idx": idx,
            "user_text_preview": user_text[:200],
        },
    )


# ---------------------------------------------------------------------------
# Cluster G — drift active session leaks explicit-change phrasing
# ---------------------------------------------------------------------------


# Phrases that contradict implicit-drift form by directly announcing
# the change or referring to the prior version. Symmetric to cluster
# F: F flags too-passive sessions (status checks with no declaration);
# G flags too-active ones (announcements that violate implicit form).
#
# All four 2026-04-26 v9 drift-sweep findings produce a hit here:
#   p2-hard-drift-tone-001:        "the old hedged style"
#   p2d-narrow-imp-doc-001:        "now I just keep it plain prose";
#                                  "stick to text only"
#   p2d-narrow-imp-meal-001:       "I've been cutting red meat ...
#                                  out of my meals entirely"
#   p2j-hard-drift-meeting-style-001: "the timeboxed rounds I run now"
#
# Patterns are anchored on word boundaries to avoid matching tokens
# inside larger words (e.g. "snowing" should not match "now").
_EXPLICIT_LEAKAGE_RE = _re.compile(
    r"(?:"
    # "the old X" — explicit reference to the prior version.
    r"\bthe\s+old\s+\w+|"
    # "now I just/only/always X" — present-tense announcement of new state.
    r"\bnow\s+I\s+(?:just|only|always|usually|mostly)\b|"
    # "I VERB now" (e.g. "I run now", "I write now") — change marker
    # tacked onto a present-tense verb. Restricted to a closed set of
    # present-tense action verbs to avoid false-positives on "I am
    # now"/"I have now"/"I do now" which are common in non-drift
    # contexts.
    r"\bI\s+(?:run|write|use|keep|prefer|order|read|cook|train|sleep|"
    r"drink|eat|wake|wear|build|host|send|review|track|log|capture|"
    r"draft|publish|deploy|ship|teach|teach|pitch)\s+now\b|"
    # "cutting X out (of Y) entirely" — explicit elimination phrasing.
    r"\bcutting\s+(?:[^.\n]{1,60})?\bout\b(?:[^.\n]{0,40})?\bentirely\b|"
    # "I've been Xing ... entirely" — long-form explicit narration.
    r"\bI(?:'ve|\s+have)\s+been\s+\w+ing\b[^.\n]{0,100}\bentirely\b|"
    # "stick to X only" — narrowing announcement.
    r"\bstick\s+(?:to\s+)?\w+(?:\s+\w+){0,3}?\s+only\b|"
    # "I (am|'m) (switching|switched|moving|moved) to X" — fully
    # explicit change announcement (also caught by realizer-prompt
    # rule 7a but kept here as a backstop).
    r"\bI(?:'m|\s+am)?\s+(?:switching|switched|moving|moved)\s+to\b|"
    # "from now on" / "going forward" — same backstop role.
    r"\bfrom\s+now\s+on\b|"
    r"\bgoing\s+forward\b|"
    # "new (rule|policy|routine|standard) (is|:)" — declarative naming.
    r"\bnew\s+(?:rule|policy|routine|standard)\b"
    r")",
    flags=_re.IGNORECASE,
)


def check_cluster_G_drift_explicit_leakage(
    sample: Sample,
) -> GoldConsistencyFinding | None:
    """Flag implicit_drift samples whose active session leaks
    explicit-change phrasing in user turns.

    Only the active session's USER text is checked. Assistant turns are
    out of scope: a clarifying "Updated — switching to X" from the
    assistant is fine; a user-side "the old X" / "now I just X" is
    not.
    """
    patterns = list(getattr(sample.gold.metadata, "failure_patterns", None) or [])
    if "implicit_drift" not in patterns:
        return None
    active = sample.gold.violation_predicate.must_honor
    if not sample.history:
        return None
    idx = active.session_introduced
    if not (1 <= idx <= len(sample.history)):
        return None
    sess = sample.history[idx - 1]
    user_text = "\n".join(t.text for t in sess.turns if t.role == "user")
    if not user_text:
        return None
    m = _EXPLICIT_LEAKAGE_RE.search(user_text)
    if not m:
        return None
    return GoldConsistencyFinding(
        cluster="G",
        reason=(
            f"active session user-role text contains explicit-change "
            f"phrasing {m.group(0)!r} that contradicts implicit_drift "
            f"form. The active state should appear as ambient fact, not "
            f"a stated change."
        ),
        detail={
            "active_session_idx": idx,
            "matched_phrase": m.group(0),
            "user_text_preview": user_text[:200],
        },
    )


# ---------------------------------------------------------------------------
# Cluster H — drift active value chunk absent from user turns of the
#             active session (drift-strict, distinguishing-only)
# ---------------------------------------------------------------------------


def check_cluster_H_drift_chunk_in_user_turn(
    sample: Sample,
) -> GoldConsistencyFinding | None:
    """Flag implicit_drift samples whose v2-distinguishing chunks fail
    to surface in USER turns of the active session.

    Why a separate cluster from E: E checks the *whole history* for any
    overlap of any chunk; H checks the *active session, user turns
    only*, against *distinguishing* chunks (chunks that carry tokens
    unique to v2). Carry-over chunks (whose tokens are shared between
    v1 and v2) are exempt — they're already established in earlier
    sessions and don't need to surface in the active session for the
    drift inference to land.

    A chunk passes when ≥1 of its distinguishing stems appears in any
    user turn of the active session. The chunk fails when every
    distinguishing stem is absent — meaning a blind reader of the
    active session's user turns can't tell that the user (not the
    assistant, not someone else) is the agent of that attribute.

    Only fires on implicit_drift; explicit replacement / multi_step
    samples are out of scope (those announce changes directly).
    """
    patterns = list(getattr(sample.gold.metadata, "failure_patterns", None) or [])
    if "implicit_drift" not in patterns:
        return None
    active = sample.gold.violation_predicate.must_honor
    if not sample.history:
        return None
    idx = active.session_introduced
    if not (1 <= idx <= len(sample.history)):
        return None

    # Distinguishing stems: active stems minus union of outdated stems.
    active_stems = _stems(_tokenize_value(active.value))
    if not active_stems:
        return None
    outdated_stems: set[str] = set()
    for ov in sample.gold.violation_predicate.must_not_honor or []:
        outdated_stems |= _stems(_tokenize_value(ov.value))
    distinguishing = active_stems - outdated_stems
    if not distinguishing:
        # v1 and v2 share full vocabulary (e.g. quantitative-only delta);
        # H can't be evaluated on tokens alone.
        return None

    chunks = _value_chunks(active.value)
    if not chunks:
        return None
    sess = sample.history[idx - 1]
    user_text = " ".join(t.text for t in sess.turns if t.role == "user")
    user_stems = _stems(_content_tokens(user_text))
    # Raw tokens (no stopword removal) for the morphological fallback.
    # _content_tokens drops temporal stopwords like "month" — but a user
    # writing "this month's send" IS surfacing the cadence the gold
    # encodes as "monthly". Bypass the stopword filter for prefix-overlap
    # so we don't lose that signal.
    user_raw_tokens = set(_TOKEN_RE.findall(user_text.lower()))

    def _has_morphological_match(stem: str) -> bool:
        """Fallback for stem collisions the conservative _stem misses
        (e.g. architectural/architecture, leave/leaving) or that get
        filtered by stopword removal (monthly→month). True if any
        raw user token shares a 4-char prefix with the gold stem."""
        if len(stem) < 4:
            return False
        prefix = stem[:4]
        for u in user_raw_tokens:
            if len(u) >= 4 and u[:4] == prefix:
                return True
        return False

    bad_chunks: list[dict] = []
    for chunk in chunks:
        chunk_stems = _stems(_tokenize_value(chunk))
        chunk_distinguishing = chunk_stems & distinguishing
        if not chunk_distinguishing:
            # Chunk carries no v2-unique tokens — pure carry-over from
            # v1. Skip.
            continue
        if chunk_distinguishing & user_stems:
            continue
        if any(_has_morphological_match(s) for s in chunk_distinguishing):
            continue
        bad_chunks.append({
            "chunk": chunk,
            "distinguishing_stems": sorted(chunk_distinguishing),
        })
    if not bad_chunks:
        return None
    return GoldConsistencyFinding(
        cluster="H",
        reason=(
            f"v2-distinguishing chunk(s) {[b['chunk'] for b in bad_chunks]} "
            f"have no token overlap with USER turns of the active session "
            f"(s{idx}). The drift inference requires the user to surface "
            f"the new attribute directly; assistant-only or other-session "
            f"mentions don't establish user agency."
        ),
        detail={
            "active_session_idx": idx,
            "bad_chunks": bad_chunks,
            "active_value": active.value,
        },
    )


# ---------------------------------------------------------------------------
# Cluster J — Phase 3 active-evidence rules (drift only)
# ---------------------------------------------------------------------------


# Phrases that disqualify an evidence item — same blacklist as cluster
# G's explicit-leakage detector, applied per-evidence-item rather than
# per-active-session.
_EVIDENCE_REPLACEMENT_BLACKLIST = _re.compile(
    r"(?:"
    r"\bI\s+switched\s+from\b|"
    r"\bI(?:'m|\s+am)?\s+(?:switching|switched|moving|moved)\s+(?:from|to)\b|"
    r"\bno\s+longer\s+(?:use|using|need|needs|do|does)\b|"
    r"\bfrom\s+now\s+on\b|"
    r"\bgoing\s+forward\b|"
    r"\bI\s+changed\s+my\s+mind\b|"
    r"\breplace\s+\w+\s+with\b|"
    r"\bthe\s+old\s+\w+|"
    r"\bnow\s+I\s+(?:just|only|always)\b|"
    r"\bI\s+(?:run|write|use|keep|prefer|order|read|cook|train|sleep|"
    r"drink|eat|wake|wear|build|host|send|review|track|log|capture|"
    r"draft|publish|deploy|ship)\s+now\b|"
    r"\bcutting\s+(?:[^.\n]{1,60})?\bout\b(?:[^.\n]{0,40})?\bentirely\b|"
    r"\bstick\s+(?:to\s+)?\w+(?:\s+\w+){0,3}?\s+only\b|"
    r"\bnew\s+(?:rule|policy|routine|standard)\b"
    r")",
    flags=_re.IGNORECASE,
)


def _evidence_text_in_session(evidence_text: str, session) -> bool:
    """True if evidence_text appears verbatim in some turn of session."""
    et = evidence_text.strip()
    if not et:
        return False
    for turn in session.turns:
        if et in turn.text:
            return True
    return False


def _find_session_by_id(sample: Sample, session_id: str):
    """Match the cited session_id ('s1', 's2', ...) to a Session.
    Falls back to index parse if .session_id field doesn't match."""
    for s in sample.history:
        if getattr(s, "session_id", None) == session_id:
            return s
    # Fallback: parse 'sN' format and index 1-based.
    if session_id.startswith("s"):
        try:
            idx = int(session_id[1:]) - 1
        except ValueError:
            return None
        if 0 <= idx < len(sample.history):
            return sample.history[idx]
    return None


def _session_index(sample: Sample, session) -> int | None:
    """1-based index of session within sample.history, or None if missing."""
    for i, s in enumerate(sample.history, start=1):
        if s is session:
            return i
    return None


def check_cluster_J_active_evidence_rules(
    sample: Sample,
) -> GoldConsistencyFinding | None:
    """Phase 3 only. Validate the gold-only `active_evidence` list per
    protocol §10.4 / cluster J catalog rules.

    Skipped silently when:
      - sample is not implicit_drift, OR
      - sample.gold.active_evidence is None (Phase 2 sample, not yet
        through the extractor pass).

    Fails when active_evidence is present but violates any rule:
      - <2 items
      - evidence_text not verbatim in cited session
      - cited session_id is at or before max(outdated.session_introduced)
      - evidence_text contains an explicit-replacement phrase
        (cluster G blacklist applied per-item)

    Same target-slot / same active state checks are deferred to the
    construction layer (the extractor prompt is keyed on the gold
    target slot + active state, so a well-formed extraction can't
    cite an off-target span without violating rule 6 / 7 of the
    prompt — and any contamination is caught by the verbatim check).
    """
    patterns = list(getattr(sample.gold.metadata, "failure_patterns", None) or [])
    if "implicit_drift" not in patterns:
        return None
    evidence = getattr(sample.gold, "active_evidence", None)
    if evidence is None:
        # Phase 2 sample, no active_evidence requirement. Skip.
        return None

    # Rule 1: ≥2 items.
    if len(evidence) < 2:
        return GoldConsistencyFinding(
            cluster="J",
            reason=(
                f"active_evidence has only {len(evidence)} item(s); cluster J "
                f"requires ≥2 independent post-old-state evidence items per "
                f"protocol §10.4. Likely the extractor returned an empty "
                f"list (deliberate 'cannot comply' signal) or the realized "
                f"history doesn't carry enough behavioral evidence."
            ),
            detail={"n_items": len(evidence)},
        )

    outdated = sample.gold.violation_predicate.must_not_honor or []
    if not outdated:
        # Single-version implicit_drift sample is malformed (drift
        # implies superseded state). Treat as cluster J failure with
        # a structured reason rather than silently passing.
        return GoldConsistencyFinding(
            cluster="J",
            reason=(
                "implicit_drift sample has no must_not_honor versions; "
                "active_evidence cannot be evaluated against an outdated "
                "state floor."
            ),
            detail={"n_outdated": 0},
        )
    outdated_floor = max(v.session_introduced for v in outdated)

    bad_items: list[dict] = []
    for i, item in enumerate(evidence):
        sess = _find_session_by_id(sample, item.session_id)
        if sess is None:
            bad_items.append({
                "index": i, "session_id": item.session_id,
                "reason": "cited session_id not found in history",
            })
            continue
        sess_idx = _session_index(sample, sess)
        if sess_idx is None or sess_idx <= outdated_floor:
            bad_items.append({
                "index": i, "session_id": item.session_id,
                "reason": f"cited session is at or before outdated floor s{outdated_floor}",
            })
            continue
        if not _evidence_text_in_session(item.evidence_text, sess):
            bad_items.append({
                "index": i, "session_id": item.session_id,
                "reason": "evidence_text not verbatim in cited session",
                "evidence_preview": item.evidence_text[:80],
            })
            continue
        m = _EVIDENCE_REPLACEMENT_BLACKLIST.search(item.evidence_text)
        if m:
            bad_items.append({
                "index": i, "session_id": item.session_id,
                "reason": f"evidence_text contains explicit-replacement phrase {m.group(0)!r}",
            })
            continue

    # Reject if any item failed AND the survivors fall below 2.
    n_pass = len(evidence) - len(bad_items)
    if bad_items and n_pass < 2:
        return GoldConsistencyFinding(
            cluster="J",
            reason=(
                f"active_evidence had {len(bad_items)} item(s) failing rules "
                f"(verbatim / session order / replacement-phrase); only "
                f"{n_pass} valid item(s) remain, below the ≥2 floor."
            ),
            detail={"bad_items": bad_items, "n_pass": n_pass},
        )
    if bad_items:
        # ≥2 items still pass after rejecting the bad ones. Treat as
        # advisory: log a finding but don't hard-fail. (Caller can
        # choose to drop the bad items from the final manifest.)
        return GoldConsistencyFinding(
            cluster="J",
            reason=(
                f"active_evidence contains {len(bad_items)} rule-violating "
                f"item(s) but {n_pass} valid items remain; sample passes "
                f"the ≥2 floor but the failed items should be dropped at "
                f"manifest write."
            ),
            detail={"bad_items": bad_items, "n_pass": n_pass, "advisory": True},
        )
    return None


# ---------------------------------------------------------------------------
# Cluster L — every version's distinguishing stems must appear in user
# turns at-or-before its declared session_introduced
# ---------------------------------------------------------------------------
#
# Phase 3 self-audit (2026-04-27) discovered a class of compact-horizon
# realizer defects: the realizer occasionally emits the active version
# correctly but drops one or more *intermediate* versions of a
# multi_version / narrowing / explicit_replacement chain. Cluster A
# only checks the active value's full stems with a 50% threshold; that
# fires too late when (a) the dropped version is a proper subset of
# the active value (narrowing — its stems already appear in the active
# turn) or (b) topic-shared stems mask an actual missing brand
# substring (e.g. "Google Meet" v.s. "Zoom" both stem-overlap on
# "meet/meeting").
#
# Cluster L uses *distinguishing* stems — stems that are unique to one
# version against the union of all others — and searches user turns
# in sessions[:v.session_introduced] (inclusive). When a version has
# no distinguishing stems (revert-style collapse, where v_i.value ==
# v_active.value), it is skipped.

_CLUSTER_L_MIN_RATIO = 0.5


def check_cluster_L_intermediate_version_coverage(
    sample: Sample,
) -> GoldConsistencyFinding | None:
    # Scope: only compact-horizon non-drift patterns. The blind audit
    # localised the realizer-drops-a-version-turn bug to this cell;
    # outside it, the LLM realizer routinely paraphrases v1 into casual
    # turns ("any community-service opportunity fits the calendar" →
    # "volunteer opportunities... doesn't conflict") that defeat
    # stem-based coverage but preserve meaning.
    meta = sample.gold.metadata
    if (meta.horizon or "").lower() != "compact":
        return None
    patterns = list(meta.failure_patterns or [])
    if "implicit_drift" in patterns:
        return None

    pred = sample.gold.violation_predicate
    must_not = pred.must_not_honor or []
    active = pred.must_honor
    all_versions = [active] + list(must_not)
    if len(all_versions) < 2:
        return None

    stems_by_id: dict[str, set[str]] = {}
    for v in all_versions:
        stems_by_id[v.version_id] = _stems(_tokenize_value(v.value))

    missing: list[dict] = []
    for v in all_versions:
        my_stems = stems_by_id[v.version_id]
        if not my_stems:
            continue
        others: set[str] = set()
        for o in all_versions:
            if o.version_id != v.version_id:
                others |= stems_by_id[o.version_id]
        distinguishing = my_stems - others
        if not distinguishing:
            # Stems collapse with another version (revert / strict
            # subset). No reliable signal at the stem level — skip.
            continue
        sess_floor = v.session_introduced
        if sess_floor is None or sess_floor < 1:
            continue
        scope = sample.history[: sess_floor]
        if not scope:
            continue
        scope_stems = _stems(
            _content_tokens(" ".join(_user_text(s) for s in scope))
        )
        present = distinguishing & scope_stems
        ratio = len(present) / len(distinguishing)
        if ratio < _CLUSTER_L_MIN_RATIO:
            missing.append({
                "version_id": v.version_id,
                "value": v.value,
                "session_introduced": v.session_introduced,
                "coverage": round(ratio, 3),
                "distinguishing_stems": sorted(distinguishing),
                "missing_stems": sorted(distinguishing - scope_stems),
                "is_active": v is active,
            })
    if not missing:
        return None
    # Fire only on the realizer-bug signature: either the *active*
    # version is under-covered (realizer dropped the active turn — e.g.
    # explicit_replacement where v_active replacement was never
    # written), or ≥2 versions are under-covered (multi/narrow where
    # several event turns were merged/dropped). A single
    # outdated-version miss is most often the LLM paraphrasing v1 into
    # casual language and is not a structural defect.
    active_missing = any(m["is_active"] for m in missing)
    if not active_missing and len(missing) < 2:
        return None
    first = missing[0]
    label = "active" if first["is_active"] else "outdated"
    return GoldConsistencyFinding(
        cluster="L",
        reason=(
            f"{len(missing)} version(s) under-covered by their "
            f"distinguishing stems in user turns at-or-before their "
            f"declared session_introduced (threshold "
            f"≥{_CLUSTER_L_MIN_RATIO*100:.0f}%); realizer likely merged "
            f"or dropped their event session(s). First miss: {label} "
            f"version {first['version_id']!r} ({first['value']!r}) at "
            f"coverage {first['coverage']*100:.0f}%, missing stems "
            f"{first['missing_stems']}."
        ),
        detail={"missing_versions": missing},
    )


# ---------------------------------------------------------------------------
# Top-level driver
# ---------------------------------------------------------------------------


def audit_sample(sample: Sample) -> list[GoldConsistencyFinding]:
    """Run all nine cluster checks; return list of findings (empty = pass).

    Order: A (universal coverage) → B (when A passes, check session
    pointer) → C (drift user agency) → D (narrow label) → E (chunk
    over-specification) → F (drift observational opener) → G (drift
    explicit leakage) → H (drift chunk-in-user-turn) → J (Phase 3
    active-evidence rules; skipped if active_evidence is None).
    """
    findings: list[GoldConsistencyFinding] = []

    a = check_cluster_A_active_tokens_in_history(sample)
    if a:
        findings.append(a)
    else:
        b = check_cluster_B_session_introduced_mismatch(sample)
        if b:
            findings.append(b)

    c = check_cluster_C_drift_user_agency(sample)
    if c:
        findings.append(c)

    d = check_cluster_D_narrow_label_mismatch(sample)
    if d:
        findings.append(d)

    e = check_cluster_E_active_value_over_specification(sample)
    if e:
        findings.append(e)

    f = check_cluster_F_drift_observational_opener(sample)
    if f:
        findings.append(f)

    g = check_cluster_G_drift_explicit_leakage(sample)
    if g:
        findings.append(g)

    h = check_cluster_H_drift_chunk_in_user_turn(sample)
    if h:
        findings.append(h)

    j = check_cluster_J_active_evidence_rules(sample)
    if j:
        findings.append(j)

    l = check_cluster_L_intermediate_version_coverage(sample)
    if l:
        findings.append(l)

    return findings


__all__ = [
    "GoldConsistencyFinding",
    "audit_sample",
    "check_cluster_A_active_tokens_in_history",
    "check_cluster_B_session_introduced_mismatch",
    "check_cluster_C_drift_user_agency",
    "check_cluster_D_narrow_label_mismatch",
    "check_cluster_E_active_value_over_specification",
    "check_cluster_F_drift_observational_opener",
    "check_cluster_G_drift_explicit_leakage",
    "check_cluster_H_drift_chunk_in_user_turn",
    "check_cluster_J_active_evidence_rules",
    "check_cluster_L_intermediate_version_coverage",
]
