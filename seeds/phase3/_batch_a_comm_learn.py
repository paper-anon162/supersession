"""Phase 3 batch A — 15 spines covering communication_boundary and
learning_routine topic_groups.

The starter batch left these two topic_groups underrepresented (0 and
6 samples respectively in the v10 manifest). This batch fills both,
biased toward non-object target_types to fix the starter's 40%
non-object share (the §10.3 floor is 50%).

Distribution:

  By failure_pattern:
    narrowing                 5  (3 communication, 1 learning, 1 daily-cap variant)
    multi_version triple      2  (1 learning, 1 communication tool chain)
    multi_version doublet     1  (4-version cardio chain — fills the 0/50 doublet bucket)
    explicit_replacement      1  (communication tool)
    implicit_drift            6  (2 repeated_use, 2 abandonment, 2 gradual_narrowing)

  By topic_group:
    communication_boundary    8
    learning_routine          7

  By target_type (non-object share = 12/15 = 80%):
    procedural_constraint     6
    conceptual_stance         3
    interpersonal_boundary    3
    object_preference         3

Drift-type sub-allocation aims to chip into the 0/20 gradual_narrowing
gap, the most underfilled bucket in the starter pool.

See seeds/phase3/AUTHORING.md for the per-field rules.
"""

from pipeline.construction import VersionSpec
from pipeline.construction.phase3 import Phase3GroupSpec
from pipeline.construction.skeleton_realizer import SkeletonAwareSpine


def _spine(
    *,
    sample_id: str,
    target_type: str,
    domain: str,
    target_description: str,
    target_slot_id: str,
    topic: str,
    versions: list[VersionSpec],
    current_query: str,
    required_behavior: str,
    invalid_behavior: list[str],
    failure_patterns: list[str],
    subtype: str = "strong",
) -> SkeletonAwareSpine:
    return SkeletonAwareSpine(
        sample_id=sample_id,
        sample_type="supersession",
        target_type=target_type,
        domain=domain,
        target_description=target_description,
        target_slot_id=target_slot_id,
        topic=topic,
        versions=versions,
        current_query=current_query,
        required_behavior=required_behavior,
        invalid_behavior=invalid_behavior,
        n_sessions=5,
        subtype=subtype,
        horizon="standard",  # placeholder; group orchestrator overrides
        failure_patterns=failure_patterns,
        triple_id=sample_id,
    )


PHASE3_BATCH_A: list[Phase3GroupSpec] = [

    # =====================================================================
    # COMMUNICATION_BOUNDARY (8 spines)
    # =====================================================================

    # narrowing — response-time tightening (interpersonal_boundary)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-narrow-response-time-001",
            target_type="interpersonal_boundary",
            domain="work_communication",
            target_description=(
                "user's expected response time for direct reports — three "
                "explicit narrowings from immediate to next-day to "
                "batched-twice-daily"
            ),
            target_slot_id="response_time::v1",
            topic="report_response_time",
            versions=[
                VersionSpec(value="reply to direct-report messages immediately, any time of day",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="reply to direct-report messages within the same business day",
                            polarity="constraint", session_introduced=2),
                VersionSpec(value="reply to direct-report messages in two daily batches at 11 AM and 4 PM",
                            polarity="constraint", session_introduced=3),
            ],
            current_query=(
                "Marcus just sent me a question about the auth migration at "
                "9:30 AM. When do I respond?"
            ),
            required_behavior=(
                "Hold the reply until the 11 AM batch window."
            ),
            invalid_behavior=[
                "Tell the user to reply immediately",
                "Tell the user to reply later in the day at no fixed time",
                "Tell the user to reply tomorrow",
            ],
            failure_patterns=["narrowing"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # narrowing — meeting cadence
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-narrow-meeting-cadence-001",
            target_type="procedural_constraint",
            domain="work_communication",
            target_description=(
                "user's report 1:1 cadence — three explicit narrowings from "
                "weekly to biweekly to monthly"
            ),
            target_slot_id="report_1on1_cadence::v1",
            topic="report_1on1_cadence",
            versions=[
                VersionSpec(value="weekly 30-minute 1:1 with each direct report",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="biweekly 30-minute 1:1 with each direct report",
                            polarity="constraint", session_introduced=2),
                VersionSpec(value="monthly 30-minute 1:1 with each direct report",
                            polarity="constraint", session_introduced=3),
            ],
            current_query=(
                "Set up the next round of touch-bases with my team."
            ),
            required_behavior=(
                "Schedule a single 30-minute 1:1 per direct report this month."
            ),
            invalid_behavior=[
                "Schedule weekly 1:1s",
                "Schedule biweekly 1:1s",
                "Skip 1:1s entirely",
            ],
            failure_patterns=["narrowing"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # narrowing — DM access
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-narrow-dm-access-001",
            target_type="interpersonal_boundary",
            domain="work_communication",
            target_description=(
                "who is allowed to DM the user — three explicit narrowings "
                "from anyone in company to direct reports + skip-levels to "
                "direct reports only"
            ),
            target_slot_id="dm_access::v1",
            topic="dm_access_policy",
            versions=[
                VersionSpec(value="anyone in the company may DM the user",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="only direct reports and skip-level reports may DM the user",
                            polarity="constraint", session_introduced=2),
                VersionSpec(value="only direct reports may DM the user",
                            polarity="constraint", session_introduced=3),
            ],
            current_query=(
                "A skip-level engineer named Tomas wants to send me a quick "
                "DM about the auth migration. Should I expect his message?"
            ),
            required_behavior=(
                "Tell the user not to expect Tomas's DM; route it through "
                "Tomas's manager instead."
            ),
            invalid_behavior=[
                "Tell the user the message will arrive normally",
                "Tell the user only company-wide messages are restricted",
                "Suggest the user disable Slack entirely",
            ],
            failure_patterns=["narrowing"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # narrowing — tone formality (conceptual_stance)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-narrow-tone-formality-001",
            target_type="conceptual_stance",
            domain="work_communication",
            target_description=(
                "user's outgoing email tone — three explicit narrowings "
                "from formal to plainspoken to plainspoken-with-no-greeting"
            ),
            target_slot_id="email_tone::v1",
            topic="outgoing_email_tone",
            versions=[
                VersionSpec(value="formal opening, third-person passive, qualified hedges",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="plainspoken first-person, short sentences",
                            polarity="prefer", session_introduced=2),
                VersionSpec(value="plainspoken first-person with no greeting line, straight to the subject",
                            polarity="prefer", session_introduced=3),
            ],
            current_query=(
                "Halda's counsel asked for our take on the indemnification "
                "clause — draft my reply."
            ),
            required_behavior=(
                "Draft a plainspoken first-person reply with no greeting "
                "line, going straight to the indemnification subject."
            ),
            invalid_behavior=[
                "Open the reply with a formal greeting like 'Dear Counsel'",
                "Use third-person passive constructions",
                "Add 'Hope you're well' or similar warm-up",
            ],
            failure_patterns=["narrowing"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # drift / repeated_use — walking 1:1s
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-walking-1on1-001",
            target_type="procedural_constraint",
            domain="management",
            target_description=(
                "user's 1:1 format — drifted from desk-side 30-min sit-down "
                "to 20-minute walking conversation via repeated active use"
            ),
            target_slot_id="onon_format::v1",
            topic="onon_format",
            versions=[
                VersionSpec(value="30-minute sit-down 1:1 at the user's desk",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="20-minute walking 1:1 outside the building",
                            polarity="constraint", session_introduced=2),
            ],
            current_query=(
                "Priya's 1:1 is on my calendar for 2 PM Tuesday — get me ready."
            ),
            required_behavior=(
                "Block 20 minutes for a walking 1:1 with Priya outside the "
                "building."
            ),
            invalid_behavior=[
                "Schedule a 30-minute sit-down at the user's desk",
                "Suggest a video call",
                "Schedule for an hour",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="repeated_use",
        spine_source="hand",
    ),

    # drift / abandonment — written status updates retired
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-status-update-format-001",
            target_type="conceptual_stance",
            domain="work_communication",
            target_description=(
                "user's weekly status update format — abandoned the long "
                "written summary in favor of a short bulleted Slack thread"
            ),
            target_slot_id="weekly_status_format::v1",
            topic="weekly_status_format",
            versions=[
                VersionSpec(value="long written summary in the team Notion page",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="three to five terse bullets posted in the team Slack thread",
                            polarity="constraint", session_introduced=2),
            ],
            current_query=(
                "It's Friday afternoon — help me put together this week's "
                "status update for everyone."
            ),
            required_behavior=(
                "Compose three to five terse bullets and post them in the "
                "team Slack thread."
            ),
            invalid_behavior=[
                "Draft a long written summary in the team Notion page",
                "Suggest both formats together",
                "Skip the status update entirely",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="abandonment",
        spine_source="hand",
    ),

    # drift / gradual_narrowing — meeting prep depth
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-meeting-prep-001",
            target_type="procedural_constraint",
            domain="management",
            target_description=(
                "user's customer-call prep — gradually narrowed from full "
                "deck plus talking points to three open questions only, "
                "via cumulative preference signals"
            ),
            target_slot_id="customer_call_prep::v1",
            topic="customer_call_prep",
            versions=[
                VersionSpec(value="review the full deck, draft talking points, list questions",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="three open-ended questions only, no deck or talking points",
                            polarity="constraint", session_introduced=2),
            ],
            current_query=(
                "Tomorrow's call with the Acme procurement team — what's "
                "my prep tonight?"
            ),
            required_behavior=(
                "Draft three open-ended questions for the Acme call; skip "
                "deck review and talking points."
            ),
            invalid_behavior=[
                "Suggest reviewing the deck",
                "Suggest drafting talking points",
                "Suggest both questions and a deck",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="gradual_narrowing",
        spine_source="hand",
    ),

    # explicit_replacement — feedback tool
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-explicit-feedback-tool-001",
            target_type="object_preference",
            domain="work_communication",
            target_description=(
                "team's feedback-collection tool — explicit replacement of "
                "Officevibe with Lattice for quarterly review cycles"
            ),
            target_slot_id="feedback_tool::v1",
            topic="feedback_tool",
            versions=[
                VersionSpec(value="Officevibe with anonymous weekly pulse questions",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Lattice with structured quarterly review templates",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "It's the start of a new evaluation period for the team — "
                "where do I run the cycle?"
            ),
            required_behavior=(
                "Run the team's evaluation cycle in Lattice using the "
                "structured quarterly review templates."
            ),
            invalid_behavior=[
                "Set up the review in Officevibe",
                "Suggest both tools in parallel",
                "Pick a third tool not in the version chain",
            ],
            failure_patterns=["explicit_replacement"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # =====================================================================
    # LEARNING_ROUTINE (7 spines)
    # =====================================================================

    # narrowing — study window
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-narrow-study-window-001",
            target_type="procedural_constraint",
            domain="learning",
            target_description=(
                "user's study window — three explicit narrowings from any "
                "time of day to evenings only to weeknight evenings 7–9 PM"
            ),
            target_slot_id="study_window::v1",
            topic="study_window",
            versions=[
                VersionSpec(value="study at any time of day, any day of the week",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="study only in the evenings, any day of the week",
                            polarity="constraint", session_introduced=2),
                VersionSpec(value="study only on weeknight evenings between 7 and 9 PM",
                            polarity="constraint", session_introduced=3),
            ],
            current_query=(
                "Block time tomorrow for the algorithms textbook."
            ),
            required_behavior=(
                "Block 7–9 PM tomorrow (a weeknight) for the algorithms "
                "textbook session."
            ),
            invalid_behavior=[
                "Block a morning slot",
                "Block a weekend slot",
                "Block more than two hours",
            ],
            failure_patterns=["narrowing"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # multi_version triple — language-learning method chain
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-multi-language-method-001",
            target_type="object_preference",
            domain="learning",
            target_description=(
                "user's Spanish-learning method — three-version replacement "
                "chain: Duolingo → Pimsleur → 1:1 italki tutor"
            ),
            target_slot_id="spanish_method::v1",
            topic="spanish_learning_method",
            versions=[
                VersionSpec(value="Duolingo daily streak with the gamified lessons",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Pimsleur audio drills, 30 minutes per session",
                            polarity="prefer", session_introduced=2),
                VersionSpec(value="weekly 1:1 italki tutor session, 60 minutes",
                            polarity="prefer", session_introduced=3),
            ],
            current_query=(
                "It's 7 PM Tuesday — what's tonight's Spanish-practice plan?"
            ),
            required_behavior=(
                "Tonight's Spanish practice is a 60-minute 1:1 italki tutor "
                "session."
            ),
            invalid_behavior=[
                "Suggest a Duolingo lesson",
                "Suggest a Pimsleur audio drill",
                "Suggest skipping practice",
            ],
            failure_patterns=["multi_version"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # multi_version triple — strength-training program
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-multi-strength-program-001",
            target_type="procedural_constraint",
            domain="fitness",
            target_description=(
                "user's strength-training program — three-version chain: "
                "StrongLifts 5x5 → Starting Strength → Greyskull LP"
            ),
            target_slot_id="strength_program::v1",
            topic="strength_training_program",
            versions=[
                VersionSpec(value="StrongLifts 5x5 with the standard barbell lifts",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="Starting Strength linear progression with the four core lifts",
                            polarity="constraint", session_introduced=2),
                VersionSpec(value="Greyskull LP with AMRAP-style top sets",
                            polarity="constraint", session_introduced=3),
            ],
            current_query=(
                "Tomorrow morning's gym session — what am I lifting?"
            ),
            required_behavior=(
                "Run a Greyskull LP session with AMRAP-style top sets."
            ),
            invalid_behavior=[
                "Suggest a StrongLifts 5x5 session",
                "Suggest a Starting Strength session",
                "Suggest a cardio-only session",
            ],
            failure_patterns=["multi_version"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # drift / repeated_use — daily reading habit
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-reading-cadence-001",
            target_type="procedural_constraint",
            domain="learning",
            target_description=(
                "user's daily reading cadence — drifted from one chapter "
                "per evening to a fixed 45-minute morning block, repeated "
                "active use"
            ),
            target_slot_id="reading_cadence::v1",
            topic="daily_reading",
            versions=[
                VersionSpec(value="one chapter of nonfiction every evening before bed",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="a fixed 45-minute reading block every morning at 6 AM",
                            polarity="constraint", session_introduced=2),
            ],
            current_query=(
                "I want to make time for the next chapter of my book "
                "tomorrow — when?"
            ),
            required_behavior=(
                "Block 6:00–6:45 AM tomorrow for the morning reading "
                "session."
            ),
            invalid_behavior=[
                "Block an evening slot",
                "Block a one-chapter target without a fixed time",
                "Skip blocking entirely",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="repeated_use",
        spine_source="hand",
    ),

    # drift / gradual_narrowing — skill focus narrowing
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-skill-focus-001",
            target_type="conceptual_stance",
            domain="learning",
            target_description=(
                "user's professional development focus — gradually narrowed "
                "from broad ML self-study to systems-design-only via "
                "cumulative preference signals"
            ),
            target_slot_id="prodev_focus::v1",
            topic="prodev_focus",
            versions=[
                VersionSpec(value="broad ML self-study covering papers, Kaggle, and library tutorials",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="systems-design-only self-study using textbook chapters and architecture case studies",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "Recommend tonight's professional development material."
            ),
            required_behavior=(
                "Recommend a systems-design textbook chapter or "
                "architecture case study for tonight's session."
            ),
            invalid_behavior=[
                "Recommend an ML paper",
                "Recommend a Kaggle competition",
                "Recommend a library tutorial",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="gradual_narrowing",
        spine_source="hand",
    ),

    # drift / abandonment — class attendance
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-class-attendance-001",
            target_type="procedural_constraint",
            domain="learning",
            target_description=(
                "user's weekly creative practice routine — abandoned the "
                "Wednesday-evening community ceramics class; now does "
                "self-paced practice at the rented studio twice a week"
            ),
            target_slot_id="evening_practice::v1",
            topic="evening_creative_practice",
            versions=[
                VersionSpec(value="weekly Wednesday-evening in-person ceramics class at the community studio",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="self-paced ceramics practice twice a week at the rented studio",
                            polarity="constraint", session_introduced=2),
            ],
            current_query=(
                "Plan my creative time for this week."
            ),
            required_behavior=(
                "Block two self-paced ceramics practice sessions at the "
                "rented studio this week."
            ),
            invalid_behavior=[
                "Block a Wednesday-evening community class",
                "Block one session only",
                "Block a class that's no longer attended",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="abandonment",
        spine_source="hand",
    ),

    # multi_version doublet — 4-version cardio chain
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-multi-cardio-4v-001",
            target_type="object_preference",
            domain="fitness",
            target_description=(
                "user's primary cardio modality — four-version chain: "
                "treadmill → elliptical → stationary cycling → rowing erg"
            ),
            target_slot_id="cardio_modality::v1",
            topic="primary_cardio",
            versions=[
                VersionSpec(value="treadmill running at the gym",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="elliptical with arm engagement",
                            polarity="prefer", session_introduced=2),
                VersionSpec(value="stationary cycling on the spin bike",
                            polarity="prefer", session_introduced=3),
                VersionSpec(value="rowing erg with intervals at 24 strokes per minute",
                            polarity="prefer", session_introduced=4),
            ],
            current_query=(
                "I have a free cardio slot at the gym this morning — what "
                "am I doing?"
            ),
            required_behavior=(
                "Use the rowing erg with intervals at 24 strokes per minute."
            ),
            invalid_behavior=[
                "Suggest treadmill running",
                "Suggest the elliptical",
                "Suggest stationary cycling",
            ],
            failure_patterns=["multi_version"],
            subtype="multi_step",
        ),
        # 4-version chain → standard-hard doublet (compact can't fit
        # 4 events with gap_inter=1 in <3K tokens cleanly)
        group_type="doublet",
        horizons=["standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

]
