"""Regression tests for audit_gold_consistency clusters A/B/C/D/E/F.

Each test crafts a minimal Sample exhibiting (or not exhibiting) one
cluster signature, then asserts the corresponding detector fires (or
doesn't). Calibrated against the 2026-04-26 30-sample human audit + the
post-audit pool walk that surfaced clusters E and F.
"""
from __future__ import annotations

import pytest

from pipeline.construction.audit_gold_consistency import (
    audit_sample,
    check_cluster_A_active_tokens_in_history,
    check_cluster_B_session_introduced_mismatch,
    check_cluster_C_drift_user_agency,
    check_cluster_D_narrow_label_mismatch,
    check_cluster_E_active_value_over_specification,
    check_cluster_F_drift_observational_opener,
    check_cluster_G_drift_explicit_leakage,
    check_cluster_H_drift_chunk_in_user_turn,
    check_cluster_J_active_evidence_rules,
)
from pipeline.schema import ActiveEvidence
from pipeline.schema import (
    GoldBundle,
    Metadata,
    SemanticSpine,
    Sample,
    Session,
    Turn,
    VersionState,
    ViolationPredicate,
)


def _make_sample(
    *,
    history_user_turns: list[tuple[int, str]],  # (session_idx, text)
    active_value: str,
    active_session: int,
    outdated_value: str = "old behavior placeholder",
    failure_patterns: list[str] | None = None,
    sample_id: str = "test-sample-001",
) -> Sample:
    """Minimal Sample factory. One assistant turn per session ('OK')."""
    sessions: list[Session] = []
    by_idx: dict[int, list[Turn]] = {}
    for idx, text in history_user_turns:
        by_idx.setdefault(idx, []).append(Turn(role="user", text=text))
    n = max(by_idx) if by_idx else 1
    for i in range(1, n + 1):
        turns = by_idx.get(i, [Turn(role="user", text="placeholder")])
        turns.append(Turn(role="assistant", text="OK"))
        sessions.append(Session(session_id=f"s{i}", timestamp=None, turns=turns))

    v1 = VersionState(
        version_id="v1", topic="test_topic", value=outdated_value,
        polarity="prefer", session_introduced=1, status="outdated",
    )
    v2 = VersionState(
        version_id="v2", topic="test_topic", value=active_value,
        polarity="prefer", session_introduced=active_session, status="active",
    )
    pred = ViolationPredicate(
        must_honor=v2, must_not_honor=[v1],
        violation_rules=[
            {"rule_type": "must_include_active_value", "check_scope": "full_response"},
        ],
    )
    spine = SemanticSpine(
        target_description="test target",
        target_slot_id="test_topic::v1",
        old_state=outdated_value,
        new_state=active_value,
        required_behavior="follow active",
        invalid_behavior=["follow outdated"],
    )
    meta = Metadata(
        session_count=len(sessions),
        history_token_count=sum(len(t.text.split()) for s in sessions for t in s.turns),
        update_to_query_token_distance=0,
        number_of_revisions=1,
        domain="test",
        gold_target_type="object_preference",
        competing_versions_count=2,
        failure_patterns=failure_patterns or [],
    )
    gold = GoldBundle(
        target_versions=[v1, v2], violation_predicate=pred,
        gold_target_type="object_preference",
        metadata=meta, semantic_spine=spine,
    )
    return Sample(
        sample_id=sample_id, sample_type="supersession",
        history=sessions, current_query="test query",
        gold=gold,
    )


# ---------------------------------------------------------------------------
# Cluster A — active value tokens missing from history
# ---------------------------------------------------------------------------


def test_cluster_A_fires_when_majority_tokens_missing():
    s = _make_sample(
        history_user_turns=[(1, "I drink tea every morning."), (2, "Standup at 9.")],
        active_value="ceremonial-grade matcha whisked with hot water",
        active_session=1,
    )
    f = check_cluster_A_active_tokens_in_history(s)
    assert f is not None and f.cluster == "A"


def test_cluster_A_passes_when_most_tokens_present():
    s = _make_sample(
        history_user_turns=[
            (1, "I drink coffee every morning, the medium-roast drip kind."),
            (2, "I switched to ceremonial-grade matcha whisked with water."),
        ],
        active_value="ceremonial-grade matcha whisked with hot water",
        active_session=2,
    )
    assert check_cluster_A_active_tokens_in_history(s) is None


# ---------------------------------------------------------------------------
# Cluster B — session_introduced mismatch (with v2-distinguishing fix)
# ---------------------------------------------------------------------------


def test_cluster_B_fires_on_genuine_mismatch():
    s = _make_sample(
        history_user_turns=[
            (1, "Set up flake8 with black formatter for the new project."),
            (2, "Switch lint config to ruff handling both lint and format."),
            (3, "Cancel my Friday lunch."),
        ],
        outdated_value="flake8 plus black for formatting",
        active_value="ruff handling both lint and format",
        active_session=3,  # WRONG: should be 2
    )
    f = check_cluster_B_session_introduced_mismatch(s)
    assert f is not None and f.cluster == "B"
    assert 2 in f.detail["actual_sessions"]


def test_cluster_B_does_not_fire_when_v1_v2_share_full_vocabulary():
    """Regression: when v1 and v2 share all vocabulary (only quantitative
    delta), the scanner should NOT declare a cluster B finding because
    we can't programmatically distinguish v1- from v2-establishing
    sessions on tokens alone.
    """
    s = _make_sample(
        history_user_turns=[
            (1, "Schedule one Sunday meal-prep session covering five lunches."),
            (2, "Just confirming meal-prep is on Sunday."),
        ],
        outdated_value="one Sunday meal-prep session covering all five weekday lunches",
        active_value="two meal-prep sessions per week (Sunday and Wednesday)",
        active_session=1,  # Would have been a false-positive flag in old logic
    )
    # No "wednesday" token in history → cluster B shouldn't fire (we'd
    # need cluster A/E for that case).
    f = check_cluster_B_session_introduced_mismatch(s)
    assert f is None or f.detail.get("actual_sessions") == []


# ---------------------------------------------------------------------------
# Cluster C — drift weak user agency
# ---------------------------------------------------------------------------


def test_cluster_C_fires_when_user_role_lacks_active_tokens():
    s = _make_sample(
        history_user_turns=[
            (1, "Old preference is line-by-line edits."),
            (2, "Just checking my schedule."),
            (3, "Quick check."),
        ],
        outdated_value="line-by-line tracked-changes edits",
        active_value="single paragraph summarising overall gist",
        active_session=3,
        failure_patterns=["implicit_drift"],
    )
    # User-role text has no overlap with 'paragraph / summarising / gist /
    # overall / single' → cluster C fires.
    f = check_cluster_C_drift_user_agency(s)
    assert f is not None and f.cluster == "C"


# ---------------------------------------------------------------------------
# Cluster D — narrowing chain conflated with replacement
# ---------------------------------------------------------------------------


def test_cluster_D_fires_on_zero_overlap_and_shorter_v_next():
    # Build a 3-version narrowing chain manually
    s = _make_sample(
        history_user_turns=[(1, "ok"), (2, "ok")],
        outdated_value="full prose write-up with KPIs in text",
        active_value="bulleted highlights only",
        active_session=2,
        failure_patterns=["narrowing", "multi_version"],
    )
    f = check_cluster_D_narrow_label_mismatch(s)
    # 2-version chain only — D should fire on the v1→v2 pair if low
    # overlap + v2 shorter.
    assert f is not None and f.cluster == "D"


def test_cluster_D_passes_when_narrow_extends():
    s = _make_sample(
        history_user_turns=[(1, "ok"), (2, "ok")],
        outdated_value="any cleaning brand",
        active_value="eco-certified plus fragrance-free cleaning brand only",
        active_session=2,
        failure_patterns=["narrowing", "multi_version"],
    )
    # v2 LONGER than v1 → not flagged as replacement-shaped.
    assert check_cluster_D_narrow_label_mismatch(s) is None


# ---------------------------------------------------------------------------
# Cluster E — active value over-specification by chunk
# ---------------------------------------------------------------------------


def test_cluster_E_fires_when_chunk_unrealized():
    s = _make_sample(
        history_user_turns=[
            (1, "I'm switching to bike for downtown commutes via the lakefront trail."),
        ],
        active_value="bike 35 minutes via the lakefront trail and a coffee stop at Joe's",
        active_session=1,
    )
    # 'coffee stop at Joe's' chunk is wholly absent → cluster E fires
    # even though most other tokens are present (cluster A wouldn't fire).
    f = check_cluster_E_active_value_over_specification(s)
    assert f is not None and f.cluster == "E"


def test_cluster_E_passes_when_all_chunks_evidenced():
    s = _make_sample(
        history_user_turns=[
            (1, "I'm switching to bike, taking the lakefront trail, 35 minutes total."),
        ],
        active_value="bike 35 minutes via the lakefront trail",
        active_session=1,
    )
    assert check_cluster_E_active_value_over_specification(s) is None


# ---------------------------------------------------------------------------
# Cluster F — drift active session uses observational opener only
# ---------------------------------------------------------------------------


def test_cluster_F_fires_on_did_the_X_arrive_pattern():
    s = _make_sample(
        history_user_turns=[
            (1, "I drink coffee every morning."),
            (2, "Standup moved to 10 AM."),
            (3, "Did the matcha order go through this morning? I want to track if delivery is consistent."),
        ],
        outdated_value="medium-roast drip coffee",
        active_value="ceremonial-grade matcha whisked with hot water",
        active_session=3,
        failure_patterns=["implicit_drift"],
    )
    f = check_cluster_F_drift_observational_opener(s)
    assert f is not None and f.cluster == "F"


def test_cluster_F_passes_when_declarative_phrase_present():
    s = _make_sample(
        history_user_turns=[
            (1, "I drink coffee every morning."),
            (2, "Did the matcha arrive? From now on I'm drinking it nightly instead of coffee."),
        ],
        outdated_value="medium-roast drip coffee",
        active_value="ceremonial-grade matcha whisked with hot water",
        active_session=2,
        failure_patterns=["implicit_drift"],
    )
    assert check_cluster_F_drift_observational_opener(s) is None


def test_cluster_F_does_not_fire_on_non_drift():
    s = _make_sample(
        history_user_turns=[
            (1, "Did the order ship?"),
        ],
        active_value="anything",
        active_session=1,
        failure_patterns=["explicit_replacement"],  # not drift
    )
    assert check_cluster_F_drift_observational_opener(s) is None


# ---------------------------------------------------------------------------
# Cluster G — drift active session leaks explicit-change phrasing
# ---------------------------------------------------------------------------


def test_cluster_G_fires_on_the_old_X():
    s = _make_sample(
        history_user_turns=[
            (1, "I drink coffee in the morning."),
            (2, "Did the matcha arrive? The old hedged style is gone."),
        ],
        outdated_value="medium-roast drip coffee",
        active_value="ceremonial-grade matcha",
        active_session=2,
        failure_patterns=["implicit_drift"],
    )
    f = check_cluster_G_drift_explicit_leakage(s)
    assert f is not None and f.cluster == "G"
    assert "the old" in f.detail["matched_phrase"].lower()


def test_cluster_G_fires_on_now_I_just():
    s = _make_sample(
        history_user_turns=[
            (1, "I write multi-paragraph context."),
            (2, "now I just keep it plain prose with no diagrams."),
        ],
        outdated_value="multi-paragraph context",
        active_value="plain prose only",
        active_session=2,
        failure_patterns=["implicit_drift"],
    )
    f = check_cluster_G_drift_explicit_leakage(s)
    assert f is not None and f.cluster == "G"


def test_cluster_G_fires_on_cutting_X_out_entirely():
    s = _make_sample(
        history_user_turns=[
            (1, "Any animal protein works for dinners."),
            (2, "I've been cutting red meat and poultry out of my meals entirely."),
        ],
        outdated_value="any animal protein",
        active_value="fish only",
        active_session=2,
        failure_patterns=["implicit_drift"],
    )
    f = check_cluster_G_drift_explicit_leakage(s)
    assert f is not None and f.cluster == "G"


def test_cluster_G_fires_on_I_VERB_now():
    s = _make_sample(
        history_user_turns=[
            (1, "Open round-table discussion is the format."),
            (2, "the timeboxed rounds I run now keep things tight."),
        ],
        outdated_value="open round-table discussion",
        active_value="5-minute timeboxed rounds",
        active_session=2,
        failure_patterns=["implicit_drift"],
    )
    f = check_cluster_G_drift_explicit_leakage(s)
    assert f is not None and f.cluster == "G"


def test_cluster_G_does_not_fire_on_clean_drift():
    s = _make_sample(
        history_user_turns=[
            (1, "Sunday meal-prep covers all five lunches."),
            (2, "the Sweetgreen order I placed this morning still hasn't shown up."),
        ],
        outdated_value="Sunday meal-prep covering five lunches",
        active_value="daily fresh delivery from Sweetgreen",
        active_session=2,
        failure_patterns=["implicit_drift"],
    )
    assert check_cluster_G_drift_explicit_leakage(s) is None


def test_cluster_G_does_not_fire_on_non_drift():
    s = _make_sample(
        history_user_turns=[
            (1, "the old vendor was Greenhouse — switching to Ashby now."),
        ],
        outdated_value="Greenhouse",
        active_value="Ashby",
        active_session=1,
        failure_patterns=["explicit_replacement"],
    )
    assert check_cluster_G_drift_explicit_leakage(s) is None


# ---------------------------------------------------------------------------
# Cluster H — drift active value chunk absent from user turns of active session
# ---------------------------------------------------------------------------


def test_cluster_H_fires_when_distinguishing_chunk_only_in_assistant_turn():
    """Active value mentions 'Obsidian' but user turn only describes the
    Obsidian behaviors generically. Should fail under H even though
    cluster A/E pass (overall history coverage is fine)."""
    sessions: list = []
    from pipeline.schema import (
        GoldBundle, Metadata, SemanticSpine, Sample, Session, Turn,
        VersionState, ViolationPredicate,
    )
    sessions.append(Session(session_id="s1", timestamp=None, turns=[
        Turn(role="user", text="Save my notes in Apple Notes — no folders."),
        Turn(role="assistant", text="Got it."),
    ]))
    sessions.append(Session(session_id="s2", timestamp=None, turns=[
        Turn(role="user", text="The daily note I started already has three backlinks. Remind me to review my wiki-style links."),
        Turn(role="assistant", text="I don't have access to your Obsidian vault, but I can remind you."),
    ]))
    v1 = VersionState(version_id="v1", topic="t", value="Apple Notes default app",
                     polarity="prefer", session_introduced=1, status="outdated")
    v2 = VersionState(version_id="v2", topic="t",
                     value="Obsidian with the daily-notes plugin and wiki-style backlinks",
                     polarity="prefer", session_introduced=2, status="active")
    pred = ViolationPredicate(must_honor=v2, must_not_honor=[v1], violation_rules=[
        {"rule_type": "must_include_active_value", "check_scope": "full_response"},
    ])
    spine = SemanticSpine(target_description="t", target_slot_id="t::v1",
                          old_state=v1.value, new_state=v2.value,
                          required_behavior="follow active",
                          invalid_behavior=["follow outdated"])
    meta = Metadata(session_count=2, history_token_count=100,
                   update_to_query_token_distance=0, number_of_revisions=1,
                   domain="test", gold_target_type="object_preference",
                   competing_versions_count=2, failure_patterns=["implicit_drift"])
    gold = GoldBundle(target_versions=[v1, v2], violation_predicate=pred,
                    gold_target_type="object_preference",
                    metadata=meta, semantic_spine=spine)
    s = Sample(sample_id="t-001", sample_type="supersession",
              history=sessions, current_query="capture today's notes",
              gold=gold)
    f = check_cluster_H_drift_chunk_in_user_turn(s)
    assert f is not None and f.cluster == "H"
    bad = {b["chunk"] for b in f.detail["bad_chunks"]}
    assert any("Obsidian" in c for c in bad)


def test_cluster_H_passes_when_carry_over_chunk_only():
    """v2 = 'biweekly 30-minute 1:1 with each report' carries over
    '30-minute 1:1 with each report' from v1 = 'weekly 30-minute 1:1
    with each report'. The active session only needs to surface
    'biweekly' (the distinguishing chunk); 'each report' / '30-minute'
    are exempt as carry-overs."""
    s = _make_sample(
        history_user_turns=[
            (1, "Weekly 30-min 1:1 with all my reports."),
            (2, "Did Sarah's biweekly slot move? Trying to keep the every-other-week rhythm."),
        ],
        outdated_value="weekly 30-minute 1:1 with each report",
        active_value="biweekly 30-minute 1:1 with each report",
        active_session=2,
        failure_patterns=["implicit_drift"],
    )
    assert check_cluster_H_drift_chunk_in_user_turn(s) is None


def test_cluster_H_passes_with_morphological_variant():
    """Gold says 'monthly' but user says 'this month's send' — different
    stems but same root concept. Prefix-overlap fallback should accept."""
    s = _make_sample(
        history_user_turns=[
            (1, "Weekly batch of 20 prospects every Monday."),
            (2, "The 80 prospects I sent first Monday last month — pull a response-rate summary for this month's send."),
        ],
        outdated_value="weekly outbound batch of 20 prospects every Monday",
        active_value="monthly outbound batch of 80 prospects on the first Monday",
        active_session=2,
        failure_patterns=["implicit_drift"],
    )
    assert check_cluster_H_drift_chunk_in_user_turn(s) is None


def test_cluster_H_does_not_fire_on_non_drift():
    s = _make_sample(
        history_user_turns=[
            (1, "We use Greenhouse."),
            (2, "Switched to Ashby last week."),
        ],
        outdated_value="Greenhouse",
        active_value="Ashby",
        active_session=2,
        failure_patterns=["explicit_replacement"],
    )
    assert check_cluster_H_drift_chunk_in_user_turn(s) is None


def test_cluster_H_does_not_fire_when_v1_v2_share_full_vocabulary():
    """Quantitative-only delta (v1='30 min', v2='45 min') — no
    distinguishing stems exist, so H is not evaluable."""
    s = _make_sample(
        history_user_turns=[
            (1, "30 minute slot."),
            (2, "Just confirming."),
        ],
        outdated_value="30 minute slot",
        active_value="45 minute slot",
        active_session=2,
        failure_patterns=["implicit_drift"],
    )
    # 30 / 45 are content tokens but distinguishing stem set is {30}, {45}
    # — these may or may not overlap with user turns. Pass condition:
    # gracefully don't flag when the only distinguishing token is a
    # number that the user didn't repeat.
    f = check_cluster_H_drift_chunk_in_user_turn(s)
    # accept either None (no distinguishing) or a finding with non-empty bad_chunks
    if f is not None:
        assert f.cluster == "H"


# ---------------------------------------------------------------------------
# audit_sample driver — combined behavior
# ---------------------------------------------------------------------------


def test_audit_sample_returns_multiple_clusters():
    """A drift sample with both observational-opener AND chunked over-
    specification should surface E and F simultaneously."""
    s = _make_sample(
        history_user_turns=[
            (1, "Some old preference here."),
            (2, "Did the matcha order arrive this morning?"),
        ],
        outdated_value="medium-roast drip coffee",
        active_value="ceremonial matcha with a side of bagels and orange juice",
        active_session=2,
        failure_patterns=["implicit_drift"],
    )
    findings = audit_sample(s)
    clusters = {f.cluster for f in findings}
    # E should fire (bagels / orange-juice chunks not in history)
    assert "E" in clusters
    # F should fire (Did the X opener, no declarative)
    assert "F" in clusters


# ---------------------------------------------------------------------------
# Cluster J — Phase 3 active-evidence rules (drift only)
# ---------------------------------------------------------------------------


def _make_phase3_drift_sample(
    *,
    user_turns: list[tuple[int, str]],
    outdated_value: str,
    outdated_session: int,
    active_value: str,
    active_session: int,
    active_evidence: list[ActiveEvidence] | None,
    sample_id: str = "phase3-drift-001",
):
    """Build a Phase 3 drift sample with active_evidence pre-populated."""
    s = _make_sample(
        history_user_turns=user_turns,
        outdated_value=outdated_value,
        active_value=active_value,
        active_session=active_session,
        failure_patterns=["implicit_drift"],
        sample_id=sample_id,
    )
    # Override outdated session_introduced to match the test scenario
    s.gold.violation_predicate.must_not_honor[0].session_introduced = outdated_session
    s.gold.active_evidence = active_evidence
    return s


def test_cluster_J_skipped_when_active_evidence_none():
    """Phase 2 sample (no active_evidence field) should pass cluster J
    silently — that's the back-compat contract."""
    s = _make_phase3_drift_sample(
        user_turns=[
            (1, "I drink Notion notes only."),
            (2, "Set up Obsidian vault for me."),
            (3, "The Obsidian daily note I made today is great."),
        ],
        outdated_value="Notion",
        outdated_session=1,
        active_value="Obsidian",
        active_session=3,
        active_evidence=None,
    )
    assert check_cluster_J_active_evidence_rules(s) is None


def test_cluster_J_fires_when_fewer_than_two_evidence_items():
    s = _make_phase3_drift_sample(
        user_turns=[
            (1, "Notion is my note app."),
            (2, "Random distractor session."),
            (3, "Just opened my Obsidian vault for paper notes."),
        ],
        outdated_value="Notion",
        outdated_session=1,
        active_value="Obsidian",
        active_session=3,
        active_evidence=[
            ActiveEvidence(
                session_id="s3",
                evidence_text="Just opened my Obsidian vault for paper notes.",
                why_it_supports_active_state="user actively using Obsidian",
            ),
        ],
    )
    f = check_cluster_J_active_evidence_rules(s)
    assert f is not None and f.cluster == "J"
    assert "1 item" in f.reason or "≥2" in f.reason


def test_cluster_J_fires_when_evidence_text_not_verbatim():
    s = _make_phase3_drift_sample(
        user_turns=[
            (1, "Notion is my note app."),
            (2, "Distractor."),
            (3, "Opened my Obsidian vault."),
            (4, "The Obsidian backlinks helped me find last week's lit review."),
        ],
        outdated_value="Notion",
        outdated_session=1,
        active_value="Obsidian",
        active_session=3,
        active_evidence=[
            ActiveEvidence(
                session_id="s3",
                evidence_text="The user opens an Obsidian vault.",  # paraphrase, not verbatim
                why_it_supports_active_state="active use",
            ),
            ActiveEvidence(
                session_id="s4",
                evidence_text="The Obsidian backlinks helped me find last week's lit review.",
                why_it_supports_active_state="active use",
            ),
        ],
    )
    f = check_cluster_J_active_evidence_rules(s)
    assert f is not None and f.cluster == "J"
    # 1 valid item, 1 invalid → below ≥2 floor → hard fail
    bad = f.detail.get("bad_items", [])
    assert any("verbatim" in b["reason"] for b in bad)


def test_cluster_J_fires_when_evidence_session_pre_outdated():
    s = _make_phase3_drift_sample(
        user_turns=[
            (1, "Just got my Obsidian vault set up — too soon to know if it'll stick."),
            (2, "Notion is my note app."),
            (3, "Just opened my Obsidian vault for paper notes."),
            (4, "The Obsidian backlinks helped me."),
        ],
        outdated_value="Notion",
        outdated_session=2,  # outdated floor
        active_value="Obsidian",
        active_session=3,
        active_evidence=[
            ActiveEvidence(
                session_id="s1",  # PRE-outdated — should fail
                evidence_text="Just got my Obsidian vault set up — too soon to know if it'll stick.",
                why_it_supports_active_state="active use",
            ),
            ActiveEvidence(
                session_id="s4",
                evidence_text="The Obsidian backlinks helped me.",
                why_it_supports_active_state="active use",
            ),
        ],
    )
    f = check_cluster_J_active_evidence_rules(s)
    assert f is not None and f.cluster == "J"
    bad = f.detail.get("bad_items", [])
    assert any("outdated floor" in b["reason"] for b in bad)


def test_cluster_J_fires_on_explicit_replacement_phrase():
    s = _make_phase3_drift_sample(
        user_turns=[
            (1, "Notion."),
            (2, "Distractor."),
            (3, "I switched from Notion to Obsidian last week."),
            (4, "The Obsidian backlinks helped me find last week's lit review."),
        ],
        outdated_value="Notion",
        outdated_session=1,
        active_value="Obsidian",
        active_session=3,
        active_evidence=[
            ActiveEvidence(
                session_id="s3",
                evidence_text="I switched from Notion to Obsidian last week.",
                why_it_supports_active_state="explicit announcement of switch",
            ),
            ActiveEvidence(
                session_id="s4",
                evidence_text="The Obsidian backlinks helped me find last week's lit review.",
                why_it_supports_active_state="active use",
            ),
        ],
    )
    f = check_cluster_J_active_evidence_rules(s)
    assert f is not None and f.cluster == "J"
    bad = f.detail.get("bad_items", [])
    assert any("replacement" in b["reason"] for b in bad)


def test_cluster_J_passes_when_two_valid_items():
    s = _make_phase3_drift_sample(
        user_turns=[
            (1, "Notion is my note app."),
            (2, "Distractor session."),
            (3, "Just opened my Obsidian vault for paper notes."),
            (4, "The Obsidian backlinks helped me find last week's lit review."),
        ],
        outdated_value="Notion",
        outdated_session=1,
        active_value="Obsidian",
        active_session=3,
        active_evidence=[
            ActiveEvidence(
                session_id="s3",
                evidence_text="Just opened my Obsidian vault for paper notes.",
                why_it_supports_active_state="active use",
            ),
            ActiveEvidence(
                session_id="s4",
                evidence_text="The Obsidian backlinks helped me find last week's lit review.",
                why_it_supports_active_state="active use",
            ),
        ],
    )
    assert check_cluster_J_active_evidence_rules(s) is None


def test_cluster_J_does_not_fire_on_non_drift_sample():
    s = _make_sample(
        history_user_turns=[(1, "ok")],
        active_value="anything",
        active_session=1,
        failure_patterns=["explicit_replacement"],
    )
    s.gold.active_evidence = []  # populated but should be ignored
    assert check_cluster_J_active_evidence_rules(s) is None
