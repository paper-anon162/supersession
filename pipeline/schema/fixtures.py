"""Synthetic fixtures used in tests and dry runs.

These are not real benchmark samples — they exist purely so the pipeline can
be exercised end-to-end before any seed has been written.
"""

from __future__ import annotations

from pipeline.schema.sample import (
    GoldBundle,
    Metadata,
    Rule,
    Sample,
    SemanticSpine,
    Session,
    Turn,
    VersionState,
    ViolationPredicate,
)


def dummy_supersession_sample(sample_id: str = "demo-strong-001") -> Sample:
    v1 = VersionState(
        version_id="v1",
        topic="morning_beverage",
        value="oat-milk latte",
        polarity="prefer",
        session_introduced=1,
        status="outdated",
    )
    v2 = VersionState(
        version_id="v2",
        topic="morning_beverage",
        value="black coffee",
        polarity="prefer",
        session_introduced=3,
        status="active",
    )
    history = [
        Session(
            session_id="s1",
            timestamp="2026-01-04T08:00:00Z",
            turns=[
                Turn(role="user", text="I usually grab an oat-milk latte before work."),
                Turn(role="assistant", text="Noted — oat-milk latte in the morning."),
            ],
        ),
        Session(
            session_id="s2",
            timestamp="2026-01-12T08:00:00Z",
            turns=[
                Turn(role="user", text="Looking at our quarterly review next week."),
                Turn(role="assistant", text="Sure, I have time blocked Tuesday."),
            ],
        ),
        Session(
            session_id="s3",
            timestamp="2026-02-02T08:00:00Z",
            turns=[
                Turn(
                    role="user",
                    text="Actually I've cut dairy entirely — black coffee from now on.",
                ),
                Turn(role="assistant", text="Got it, switching that over."),
            ],
        ),
    ]
    spine = SemanticSpine(
        target_description="user's standard morning beverage order",
        target_slot_id="morning_beverage::v1",
        old_state="oat-milk latte",
        new_state="black coffee",
        required_behavior="recommend or prepare a black-coffee-only order",
        invalid_behavior=[
            "recommend an oat-milk latte",
            "include any dairy-based morning drink",
        ],
    )
    predicate = ViolationPredicate(
        must_honor=v2,
        must_not_honor=[v1],
        violation_rules=[
            Rule(rule_type="must_include_active_value", check_scope="full_response"),
            Rule(
                rule_type="must_not_include_outdated_value",
                check_scope="full_response",
            ),
            Rule(rule_type="must_address_target_slot", check_scope="full_response"),
        ],
    )
    metadata = Metadata(
        session_count=3,
        history_token_count=120,
        update_to_query_token_distance=20,
        number_of_revisions=1,
        supersession_subtype="strong",
        signal_strength="strong",
        domain="food_dining",
        gold_target_type="object_preference",
        competing_versions_count=2,
    )
    gold = GoldBundle(
        target_versions=[v1, v2],
        violation_predicate=predicate,
        gold_target_type="object_preference",
        metadata=metadata,
        semantic_spine=spine,
    )
    return Sample.model_validate(
        {
            "sample_id": sample_id,
            "history": [s.model_dump() for s in history],
            "current_query": (
                "I'm putting in tomorrow's drinks order for the team. "
                "What should I list for me?"
            ),
            "sample_type": "supersession",
            "recall_query": (
                "In our past conversations, what did you learn about my "
                "morning_beverage? List all versions you recall."
            ),
            "_gold": gold.model_dump(),
        }
    )
