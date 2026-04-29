"""Phase 3 starter batch — 10 spines covering all 4 patterns + 3
implicit_drift types + 4 topic groups.

Designed to validate the Phase 3 pipeline at moderate scale before
committing to a full ~350-spine authoring effort. Pattern mix
mirrors the Phase 3 §10.2 final-manifest proportions (loosely):

  - 1 explicit_replacement    (will scale to 50 in full)
  - 2 narrowing               (will scale to 70 in full)
  - 2 multi_version           (will scale to 60 triples + 50 doublets)
  - 5 implicit_drift          (will scale to 120 in full)
      2 repeated_use, 2 abandonment, 1 gradual_narrowing

Topic-group distribution intentionally rotates across all 4 buckets
so the topic-balance tracker has data to validate against.

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
    """Helper that fills the boilerplate; group orchestrator
    overrides horizon + sample_id per realization."""
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


PHASE3_STARTER: list[Phase3GroupSpec] = [

    # =====================================================================
    # explicit_replacement (1 spine, work_tooling)
    # =====================================================================

    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-explicit-pmtool-001",
            target_type="object_preference",
            domain="work",
            target_description=(
                "team's project-management tool — explicit replacement of "
                "Asana with Linear after migration"
            ),
            target_slot_id="pm_tool::v1",
            topic="project_management_tool",
            versions=[
                VersionSpec(value="Asana with custom fields and dashboards",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Linear with cycle planning",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "Marcus needs to file the Q3 ranking-experiment tickets — "
                "where do they go?"
            ),
            required_behavior=(
                "File the tickets in Linear, organized into the current cycle."
            ),
            invalid_behavior=[
                "File the tickets in Asana",
                "Suggest both as options",
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
    # narrowing (2 spines)
    # =====================================================================

    # narrowing 1: communication_boundary
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-narrow-slack-availability-001",
            target_type="interpersonal_boundary",
            domain="work_communication",
            target_description=(
                "user's Slack availability — three explicit narrowings: any "
                "time → 9–6 weekdays → 9–6 weekdays excluding focus blocks"
            ),
            target_slot_id="slack_availability::v1",
            topic="slack_availability",
            versions=[
                VersionSpec(value="reachable on Slack any time, weekends included",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="reachable on Slack 9–6 weekday work hours only",
                            polarity="constraint", session_introduced=2),
                VersionSpec(value="reachable on Slack 9–6 weekdays except during calendar focus blocks",
                            polarity="constraint", session_introduced=3),
            ],
            current_query=(
                "Priya wants to ping me about the Q3 deck Wednesday at 2 PM. "
                "Tell me whether to expect her message."
            ),
            required_behavior=(
                "Tell the user to expect Priya's ping only if 2 PM Wednesday "
                "isn't a calendar focus block; otherwise the user is "
                "unavailable."
            ),
            invalid_behavior=[
                "Say the user is reachable any time",
                "Say only 9–6 without mentioning focus-block exception",
                "Say the user isn't reachable at all on weekdays",
            ],
            failure_patterns=["narrowing"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # narrowing 2: daily_preference (food)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-narrow-salad-diet-001",
            target_type="object_preference",
            domain="food_dining",
            target_description=(
                "user's salad order — three explicit narrowings: any salad → "
                "no dairy → no dairy and no gluten"
            ),
            target_slot_id="lunch_salad::v1",
            topic="lunch_salad_diet",
            versions=[
                VersionSpec(value="any salad on the Sweetgreen menu",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="salad without dairy",
                            polarity="prefer", session_introduced=2),
                VersionSpec(value="salad without dairy and without gluten",
                            polarity="prefer", session_introduced=3),
            ],
            current_query=(
                "Order me lunch from Sweetgreen for tomorrow."
            ),
            required_behavior=(
                "Order a Sweetgreen salad with no dairy and no gluten."
            ),
            invalid_behavior=[
                "Order any salad without checking dietary constraints",
                "Order a salad with dairy",
                "Order a salad with gluten",
            ],
            failure_patterns=["narrowing"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # =====================================================================
    # multi_version (2 spines)
    # =====================================================================

    # multi_version 1: work_tooling — CI/CD chain
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-multi-ci-001",
            target_type="procedural_constraint",
            domain="tech_workflow",
            target_description=(
                "team's CI/CD platform — three-version replacement chain: "
                "Jenkins → Buildkite → GitHub Actions"
            ),
            target_slot_id="ci_platform::v1",
            topic="ci_platform",
            versions=[
                VersionSpec(value="Jenkins pipelines with bash glue",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Buildkite with parallelized pipeline steps",
                            polarity="prefer", session_introduced=2),
                VersionSpec(value="GitHub Actions with reusable workflows",
                            polarity="prefer", session_introduced=3),
            ],
            current_query=(
                "Set up CI/CD for the new analytics microservice the team is starting."
            ),
            required_behavior=(
                "Configure GitHub Actions with reusable workflows for the "
                "new microservice's CI/CD."
            ),
            invalid_behavior=[
                "Configure Jenkins pipelines",
                "Configure Buildkite pipelines",
                "Suggest two different platforms in parallel",
            ],
            failure_patterns=["multi_version"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # multi_version 2: learning_routine — flashcards chain (reverted)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-multi-flashcards-001",
            target_type="procedural_constraint",
            domain="learning",
            target_description=(
                "user's vocabulary review system — Anki spaced repetition → "
                "Quizlet → back to Anki spaced repetition (reverted chain)"
            ),
            target_slot_id="vocab_review::v1",
            topic="vocab_review_system",
            versions=[
                VersionSpec(value="Anki with spaced-repetition decks",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Quizlet with shared classroom decks",
                            polarity="prefer", session_introduced=2),
                VersionSpec(value="Anki with spaced-repetition decks",
                            polarity="prefer", session_introduced=3),
            ],
            current_query=(
                "I just finished tonight's chapter — log the new vocab somewhere."
            ),
            required_behavior=(
                "Log the new vocabulary into Anki using spaced-repetition decks."
            ),
            invalid_behavior=[
                "Log the vocab in Quizlet",
                "Suggest both apps as alternatives",
                "Skip logging and just review the chapter",
            ],
            failure_patterns=["multi_version"],
            subtype="reverted",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # =====================================================================
    # implicit_drift / repeated_use (2 spines)
    # =====================================================================

    # repeated_use 1: daily_preference (afternoon drink)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-matcha-001",
            target_type="object_preference",
            domain="food",
            target_description=(
                "user's afternoon drink — drifted from drip coffee to "
                "ceremonial matcha via repeated active use"
            ),
            target_slot_id="afternoon_drink::v1",
            topic="afternoon_drink",
            versions=[
                VersionSpec(value="medium-roast drip coffee, black",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="ceremonial-grade matcha whisked with hot water",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "Heading to the office kitchen at 3 — pick something for me."
            ),
            required_behavior=(
                "Make ceremonial-grade matcha whisked with hot water."
            ),
            invalid_behavior=[
                "Make medium-roast drip coffee",
                "Suggest both drinks as options",
                "Pick a third drink not in the version chain",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="repeated_use",
        spine_source="hand",
    ),

    # repeated_use 2: learning_routine (study cadence)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-pomodoro-001",
            target_type="procedural_constraint",
            domain="learning",
            target_description=(
                "user's deep-work cadence — drifted from 25-minute pomodoros "
                "to 90-minute deep blocks via repeated active use"
            ),
            target_slot_id="deep_work_cadence::v1",
            topic="deep_work_cadence",
            versions=[
                VersionSpec(value="25-minute pomodoro followed by 5-minute break",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="single 90-minute deep block followed by 30-minute break",
                            polarity="constraint", session_introduced=2),
            ],
            current_query=(
                "I have the whole afternoon to work on the strategy memo — "
                "schedule my time."
            ),
            required_behavior=(
                "Schedule a single 90-minute deep block followed by a "
                "30-minute break, repeated as the afternoon allows."
            ),
            invalid_behavior=[
                "Schedule 25-minute pomodoros",
                "Mix pomodoros and 90-minute blocks",
                "Skip the break entirely",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="repeated_use",
        spine_source="hand",
    ),

    # =====================================================================
    # implicit_drift / abandonment (2 spines)
    # =====================================================================

    # abandonment 1: communication_boundary (DMs)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-team-channel-001",
            target_type="interpersonal_boundary",
            domain="work_communication",
            target_description=(
                "user's team broadcast channel — abandoned the open #general "
                "channel in favor of direct DMs to the relevant person"
            ),
            target_slot_id="team_broadcast::v1",
            topic="team_broadcast_channel",
            versions=[
                VersionSpec(value="post all team-wide updates to #general",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="send direct DMs to the relevant individuals; #general retired for new posts",
                            polarity="constraint", session_introduced=2),
            ],
            current_query=(
                "I have an update about the new auth refactor that affects "
                "Marcus and Priya. How do I tell them?"
            ),
            required_behavior=(
                "Send direct DMs to Marcus and Priya about the auth refactor "
                "update; do not post to #general."
            ),
            invalid_behavior=[
                "Post the update to #general",
                "Tell the user to email the whole team",
                "Suggest using both channels in parallel",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="abandonment",
        spine_source="hand",
    ),

    # abandonment 2: daily_preference (cooking method)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-stovetop-001",
            target_type="object_preference",
            domain="food",
            target_description=(
                "user's weeknight cooking method — abandoned stovetop after "
                "the burner replacement; oven-only is the new norm"
            ),
            target_slot_id="cooking_method::v1",
            topic="weeknight_cooking_method",
            versions=[
                VersionSpec(value="stovetop and oven both available for weeknight cooking",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="oven only — stovetop retired during the burner replacement",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "Salmon, asparagus, and a sweet potato — what am I making for dinner?"
            ),
            required_behavior=(
                "Make a sheet-pan dinner with salmon, asparagus, and sweet "
                "potato — oven only, no stovetop."
            ),
            invalid_behavior=[
                "Suggest pan-searing the salmon on the stovetop",
                "Suggest a stovetop-only dish",
                "Suggest using both the stovetop and oven",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="abandonment",
        spine_source="hand",
    ),

    # =====================================================================
    # implicit_drift / gradual_narrowing (1 spine)
    # =====================================================================

    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-podcast-niche-001",
            target_type="object_preference",
            domain="leisure",
            target_description=(
                "user's commute listening — gradually narrowed from any tech "
                "industry show to founder-interview-only via cumulative "
                "preference signals; never explicitly announced"
            ),
            target_slot_id="commute_audio::v1",
            topic="commute_audio",
            versions=[
                VersionSpec(value="any tech-industry show — news roundups, interviews, or panels",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="tech-industry founder-interview shows only",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "Pick something for me to listen to on tomorrow's commute."
            ),
            required_behavior=(
                "Pick a tech-industry founder-interview show."
            ),
            invalid_behavior=[
                "Pick a tech-industry news roundup",
                "Pick a tech-industry panel show",
                "Pick a non-tech-industry show",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="gradual_narrowing",
        spine_source="hand",
    ),

]
