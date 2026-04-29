"""Phase 3 batch B — 15 spines targeting the §10.5 cell breaches and
the deepest §10.2 underfills the selector flagged after batch_a.

Selector report after batch_a (27 groups in pool):

  topic-cell breaches:
    narrowing × all horizons:                71% communication_boundary
    explicit_replacement × all horizons:     67% work_tooling

  deepest underfills:
    multi_version/doublet:    1/50  → 49 missing  (entire bucket nearly empty)
    gradual_narrowing:        3/20  → 17 missing  (most underfilled drift type)
    explicit_replacement:     3/50  → 47 missing
    narrowing:                7/70  → 63 missing

This batch deliberately authors:

  - 4 multi_version doublets (4+ version chains; only place doublets
    live, since simple chains can be triples). Mixed topics.
  - 3 gradual_narrowing drift across daily_preference / work_tooling /
    learning_routine — diversifies away from comm_boundary.
  - 3 explicit_replacement in daily_preference / learning_routine /
    communication_boundary (away from work_tooling — fixes 67% breach).
  - 4 narrowing in daily_preference / work_tooling / learning_routine
    (away from communication_boundary — fixes 71% breach).
  - 1 multi_version triple in daily_preference (light extra).

Distribution:
  multi_version doublet      4
  multi_version triple       1
  narrowing                  4
  explicit_replacement       3
  implicit_drift             3  (all gradual_narrowing)

  By topic_group:
    daily_preference         5
    work_tooling             3
    learning_routine         4
    communication_boundary   3   (1 each: explicit, narrow-different-flavor, drift)

  By target_type (non-object %):
    object_preference        7
    procedural_constraint    5
    conceptual_stance        2
    interpersonal_boundary   1
    non-object: 8/15 = 53%

Net pool composition target after this batch (~42 groups):
  Most cell breaches resolved by the cross-topic diversification.
  Major underfills (multi doublets, gradual_narrowing) get sustainable
  fill rates.
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
        horizon="standard",
        failure_patterns=failure_patterns,
        triple_id=sample_id,
    )


PHASE3_BATCH_B: list[Phase3GroupSpec] = [

    # =====================================================================
    # MULTI_VERSION DOUBLETS (4 spines, 4+ version chains)
    # =====================================================================

    # doublet 1: monitoring tool 4-version chain (work_tooling, procedural)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-multi-monitoring-4v-001",
            target_type="procedural_constraint",
            domain="tech_workflow",
            target_description=(
                "team's production monitoring stack — four-version "
                "replacement chain across vendor migrations"
            ),
            target_slot_id="monitoring_stack::v1",
            topic="production_monitoring",
            versions=[
                VersionSpec(value="Datadog with default APM dashboards",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="New Relic with custom NRQL queries",
                            polarity="prefer", session_introduced=2),
                VersionSpec(value="Prometheus and Grafana self-hosted",
                            polarity="prefer", session_introduced=3),
                VersionSpec(value="OpenTelemetry with Honeycomb backend",
                            polarity="prefer", session_introduced=4),
            ],
            current_query=(
                "Wire up observability for the new search-ranking microservice."
            ),
            required_behavior=(
                "Wire OpenTelemetry instrumentation pointing at the "
                "Honeycomb backend."
            ),
            invalid_behavior=[
                "Configure Datadog APM",
                "Configure New Relic with NRQL queries",
                "Set up Prometheus and Grafana",
            ],
            failure_patterns=["multi_version"],
            subtype="multi_step",
        ),
        group_type="doublet",
        horizons=["standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # doublet 2: car commute → bike → train → walk (daily_preference, object)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-multi-commute-mode-4v-001",
            target_type="object_preference",
            domain="travel",
            target_description=(
                "user's daily commute mode — four-version replacement "
                "chain through transit experiments"
            ),
            target_slot_id="commute_mode::v1",
            topic="daily_commute_mode",
            versions=[
                VersionSpec(value="solo car driving with the gas sedan",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="electric scooter on the protected bike lane",
                            polarity="prefer", session_introduced=2),
                VersionSpec(value="commuter rail with the monthly pass",
                            polarity="prefer", session_introduced=3),
                VersionSpec(value="walking the 25-minute waterfront route",
                            polarity="prefer", session_introduced=4),
            ],
            current_query=(
                "It's Monday morning — how am I getting to the office?"
            ),
            required_behavior=(
                "Take the 25-minute waterfront walk to the office."
            ),
            invalid_behavior=[
                "Drive the gas sedan",
                "Take the electric scooter",
                "Take the commuter rail",
            ],
            failure_patterns=["multi_version"],
            subtype="multi_step",
        ),
        group_type="doublet",
        horizons=["standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # doublet 3: investing chain (object, daily_preference)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-multi-investing-platform-4v-001",
            target_type="object_preference",
            domain="finance",
            target_description=(
                "user's primary brokerage — four-version replacement "
                "chain across platform migrations"
            ),
            target_slot_id="brokerage::v1",
            topic="primary_brokerage",
            versions=[
                VersionSpec(value="Fidelity with the legacy mutual-fund account",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Vanguard with the Roth IRA and brokerage combo",
                            polarity="prefer", session_introduced=2),
                VersionSpec(value="Schwab with the unified Investor Checking + brokerage",
                            polarity="prefer", session_introduced=3),
                VersionSpec(value="Interactive Brokers with the API-driven margin account",
                            polarity="prefer", session_introduced=4),
            ],
            current_query=(
                "Move the bonus into my main investment account."
            ),
            required_behavior=(
                "Move the bonus into the Interactive Brokers margin account."
            ),
            invalid_behavior=[
                "Move it to Fidelity",
                "Move it to Vanguard",
                "Move it to Schwab",
            ],
            failure_patterns=["multi_version"],
            subtype="multi_step",
        ),
        group_type="doublet",
        horizons=["standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # doublet 4: design framework chain (work_tooling, conceptual_stance, reverted)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-multi-design-framework-4v-001",
            target_type="conceptual_stance",
            domain="work",
            target_description=(
                "user's product-strategy framework — four-version chain "
                "with one revert (Porter → Wardley → JTBD → back to Wardley)"
            ),
            target_slot_id="strategy_framework::v1",
            topic="strategy_framework",
            versions=[
                VersionSpec(value="Porter's Five Forces with industry-structure analysis",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Wardley Maps with evolution-axis positioning",
                            polarity="prefer", session_introduced=2),
                VersionSpec(value="Jobs-to-be-Done with the customer-progress lens",
                            polarity="prefer", session_introduced=3),
                VersionSpec(value="Wardley Maps with evolution-axis positioning",
                            polarity="prefer", session_introduced=4),
            ],
            current_query=(
                "Frame the competitive landscape section for the Q3 strategy memo."
            ),
            required_behavior=(
                "Frame the competitive landscape using Wardley Maps with "
                "evolution-axis positioning."
            ),
            invalid_behavior=[
                "Use Porter's Five Forces",
                "Use Jobs-to-be-Done",
                "Mix multiple frameworks together",
            ],
            failure_patterns=["multi_version"],
            subtype="reverted",
        ),
        group_type="doublet",
        horizons=["standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # =====================================================================
    # GRADUAL_NARROWING DRIFT (3 spines, diversifying topic_group)
    # =====================================================================

    # gradual_narrowing — caffeine intake (daily_preference, object)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-caffeine-narrow-001",
            target_type="object_preference",
            domain="food",
            target_description=(
                "user's afternoon caffeine — gradually narrowed from any "
                "caffeinated beverage to decaf herbal tea only via "
                "cumulative preference signals"
            ),
            target_slot_id="afternoon_caffeine::v1",
            topic="afternoon_caffeine",
            versions=[
                VersionSpec(value="any afternoon caffeinated drink — coffee, tea, or energy drink",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="decaf herbal tea only in the afternoon",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "It's 3 PM and I want something warm — what should I make?"
            ),
            required_behavior=(
                "Make decaf herbal tea."
            ),
            invalid_behavior=[
                "Make regular coffee",
                "Make caffeinated tea",
                "Make an energy drink",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="gradual_narrowing",
        spine_source="hand",
    ),

    # gradual_narrowing — code review scope (work_tooling, procedural)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-review-scope-narrow-001",
            target_type="procedural_constraint",
            domain="work",
            target_description=(
                "user's code-review scope — gradually narrowed from "
                "every PR to architecture-only via cumulative preference"
            ),
            target_slot_id="review_scope::v1",
            topic="code_review_scope",
            versions=[
                VersionSpec(value="every PR opened against the team's repos",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="only PRs that touch architectural boundaries or public interfaces",
                            polarity="constraint", session_introduced=2),
            ],
            current_query=(
                "Marcus has a 12-line bugfix PR up — am I reviewing it?"
            ),
            required_behavior=(
                "Skip the bugfix PR; only review when it touches "
                "architectural boundaries or public interfaces."
            ),
            invalid_behavior=[
                "Review the bugfix PR",
                "Tell the user to review every PR",
                "Auto-approve the PR",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="gradual_narrowing",
        spine_source="hand",
    ),

    # gradual_narrowing — book-club scope (learning_routine, conceptual)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-drift-bookclub-scope-narrow-001",
            target_type="conceptual_stance",
            domain="leisure",
            target_description=(
                "user's book-club scope — gradually narrowed from any "
                "non-fiction to translated 20th-century literary fiction "
                "via cumulative preference"
            ),
            target_slot_id="bookclub_scope::v1",
            topic="bookclub_scope",
            versions=[
                VersionSpec(value="any non-fiction work the group nominates",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="translated 20th-century literary fiction only",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "Pick this month's book-club selection."
            ),
            required_behavior=(
                "Pick a translated 20th-century literary fiction title."
            ),
            invalid_behavior=[
                "Pick a non-fiction title",
                "Pick a 21st-century novel",
                "Pick an English-language original (untranslated) novel",
            ],
            failure_patterns=["implicit_drift"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="gradual_narrowing",
        spine_source="hand",
    ),

    # =====================================================================
    # EXPLICIT_REPLACEMENT × non-work_tooling (3 spines)
    # =====================================================================

    # explicit — meal-kit service (daily_preference, object)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-explicit-meal-kit-001",
            target_type="object_preference",
            domain="food_dining",
            target_description=(
                "user's meal-kit service — explicit replacement of "
                "HelloFresh with Sunbasket after subscription change"
            ),
            target_slot_id="meal_kit_service::v1",
            topic="meal_kit_subscription",
            versions=[
                VersionSpec(value="HelloFresh with the four-meal classic plan",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Sunbasket with the organic Mediterranean plan",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "Set up next week's grocery delivery."
            ),
            required_behavior=(
                "Set up the Sunbasket organic Mediterranean delivery for "
                "next week."
            ),
            invalid_behavior=[
                "Set up HelloFresh delivery",
                "Suggest both services",
                "Suggest no delivery (cook from scratch)",
            ],
            failure_patterns=["explicit_replacement"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # explicit — language-learning app (learning_routine, object)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-explicit-flashcard-app-001",
            target_type="object_preference",
            domain="learning",
            target_description=(
                "user's flashcard app for medical terminology — explicit "
                "replacement of Quizlet with Anki after switching study method"
            ),
            target_slot_id="flashcard_app::v1",
            topic="medical_flashcard_app",
            versions=[
                VersionSpec(value="Quizlet with the shared classroom decks",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Anki with the spaced-repetition algorithm",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "I just learned a new term in lecture — log it for review later."
            ),
            required_behavior=(
                "Log the term as a new card in Anki using the "
                "spaced-repetition algorithm."
            ),
            invalid_behavior=[
                "Log the term in Quizlet",
                "Suggest both apps",
                "Suggest skipping the log entirely",
            ],
            failure_patterns=["explicit_replacement"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # explicit — group-chat platform (communication_boundary, object)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-explicit-family-chat-001",
            target_type="object_preference",
            domain="work_communication",
            target_description=(
                "extended family's group-chat platform — explicit "
                "replacement of WhatsApp with Signal after privacy concerns"
            ),
            target_slot_id="family_groupchat::v1",
            topic="family_group_chat",
            versions=[
                VersionSpec(value="WhatsApp with the extended-family group",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Signal with the disappearing-messages group",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "Send the wedding photos to everyone."
            ),
            required_behavior=(
                "Send the wedding photos via Signal to the disappearing-"
                "messages family group."
            ),
            invalid_behavior=[
                "Send the photos via WhatsApp",
                "Send to both platforms",
                "Email the photos individually",
            ],
            failure_patterns=["explicit_replacement"],
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # =====================================================================
    # NARROWING × non-communication_boundary (4 spines)
    # =====================================================================

    # narrow — gym attendance (learning_routine domain → fitness, procedural)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-narrow-gym-frequency-001",
            target_type="procedural_constraint",
            domain="fitness",
            target_description=(
                "user's gym attendance — three explicit narrowings from "
                "daily to four-times-weekly to twice-weekly + recovery yoga"
            ),
            target_slot_id="gym_attendance::v1",
            topic="gym_frequency",
            versions=[
                VersionSpec(value="six-day weekly gym attendance, full body daily",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="four-times-weekly gym attendance with split routines",
                            polarity="constraint", session_introduced=2),
                VersionSpec(value="twice-weekly gym attendance plus restorative yoga on rest days",
                            polarity="constraint", session_introduced=3),
            ],
            current_query=(
                "Block this week's training on my calendar."
            ),
            required_behavior=(
                "Block two gym sessions and three restorative yoga sessions "
                "this week."
            ),
            invalid_behavior=[
                "Block six daily gym sessions",
                "Block four split-routine sessions",
                "Skip blocking and let it be ad-hoc",
            ],
            failure_patterns=["narrowing"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # narrow — vendor approval (work_tooling, procedural)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-narrow-vendor-approval-001",
            target_type="procedural_constraint",
            domain="business",
            target_description=(
                "team's vendor-approval requirement — three explicit "
                "narrowings from any vendor to SOC2 to SOC2 + 5-day "
                "data-portability SLA"
            ),
            target_slot_id="vendor_approval::v1",
            topic="vendor_approval",
            versions=[
                VersionSpec(value="any vendor passing the basic security questionnaire",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="vendors with SOC 2 Type II certification only",
                            polarity="constraint", session_introduced=2),
                VersionSpec(value="vendors with SOC 2 Type II AND a 5-day data-portability SLA",
                            polarity="constraint", session_introduced=3),
            ],
            current_query=(
                "Marketing wants to onboard a new email-automation provider — "
                "approve or block?"
            ),
            required_behavior=(
                "Block the onboarding unless the provider has SOC 2 Type II "
                "AND guarantees a 5-day data-portability SLA."
            ),
            invalid_behavior=[
                "Approve based on the basic security questionnaire alone",
                "Approve based on SOC 2 alone",
                "Approve unconditionally",
            ],
            failure_patterns=["narrowing"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # narrow — recipe constraints (daily_preference, procedural)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-narrow-recipe-cap-001",
            target_type="procedural_constraint",
            domain="food",
            target_description=(
                "user's weeknight recipe constraints — three explicit "
                "narrowings from any recipe to ≤30-min cook time to "
                "≤30-min cook time + ≤8 ingredients"
            ),
            target_slot_id="recipe_cap::v1",
            topic="weeknight_recipe_cap",
            versions=[
                VersionSpec(value="any recipe regardless of cook time or ingredient count",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="recipes with under 30 minutes total cook time",
                            polarity="constraint", session_introduced=2),
                VersionSpec(value="recipes with under 30 minutes cook time AND 8 or fewer ingredients",
                            polarity="constraint", session_introduced=3),
            ],
            current_query=(
                "Pick tonight's main course."
            ),
            required_behavior=(
                "Pick a main course that cooks in under 30 minutes and "
                "uses 8 or fewer ingredients."
            ),
            invalid_behavior=[
                "Pick a recipe with 60+ minute cook time",
                "Pick a recipe with 12+ ingredients",
                "Pick any recipe without checking these caps",
            ],
            failure_patterns=["narrowing"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

    # narrow — book reading scope (learning_routine, conceptual)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-narrow-reading-genre-001",
            target_type="conceptual_stance",
            domain="learning",
            target_description=(
                "user's personal reading list scope — three explicit "
                "narrowings from any genre to non-fiction to "
                "non-fiction + post-2015 publications only"
            ),
            target_slot_id="reading_genre::v1",
            topic="personal_reading_genre",
            versions=[
                VersionSpec(value="any genre — fiction, memoir, essays, non-fiction",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="non-fiction only — no novels or memoirs",
                            polarity="prefer", session_introduced=2),
                VersionSpec(value="non-fiction published 2015 or later only",
                            polarity="prefer", session_introduced=3),
            ],
            current_query=(
                "Recommend my next book to start tonight."
            ),
            required_behavior=(
                "Recommend a non-fiction book published in 2015 or later."
            ),
            invalid_behavior=[
                "Recommend a novel",
                "Recommend a non-fiction book published before 2015",
                "Recommend a memoir",
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
    # MULTI_VERSION TRIPLE (1 spine, daily_preference)
    # =====================================================================

    # multi triple — fitness app chain (daily_preference, object)
    Phase3GroupSpec(
        spine=_spine(
            sample_id="p3-multi-fitness-app-001",
            target_type="object_preference",
            domain="fitness",
            target_description=(
                "user's fitness-tracking app — three-version replacement "
                "chain: Strava → Apple Fitness → Garmin Connect"
            ),
            target_slot_id="fitness_app::v1",
            topic="fitness_tracking_app",
            versions=[
                VersionSpec(value="Strava with the social-feed running club",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Apple Fitness with the closed activity rings",
                            polarity="prefer", session_introduced=2),
                VersionSpec(value="Garmin Connect with the multi-sport profiles",
                            polarity="prefer", session_introduced=3),
            ],
            current_query=(
                "Log this morning's workout when I get home."
            ),
            required_behavior=(
                "Log this morning's workout in Garmin Connect using the "
                "multi-sport profile."
            ),
            invalid_behavior=[
                "Log it in Strava",
                "Log it in Apple Fitness",
                "Skip logging",
            ],
            failure_patterns=["multi_version"],
            subtype="multi_step",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

]
