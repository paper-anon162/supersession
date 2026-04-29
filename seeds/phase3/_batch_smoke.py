"""Phase 3 smoke batch — 3 groups for end-to-end pipeline testing.

Three groups covering each implicit_drift_type once, plus one
non-drift group as a control. Used by scripts/realize_phase3.py to
verify the full stack:

  1. Spine → realize_with_skeleton at 3 horizons
  2. For drift: active_evidence extractor pass
  3. Cluster A–J validation (J on extractor output)
  4. Group-level acceptance + manifest write

Production batches go in adjacent files (e.g. _batch_drift_repeated_use.py).
"""

from pipeline.construction import VersionSpec
from pipeline.construction.phase3 import Phase3GroupSpec
from pipeline.construction.skeleton_realizer import SkeletonAwareSpine


PHASE3_SMOKE: list[Phase3GroupSpec] = [

    # ---------------------------------------------------------------
    # Group 1: implicit_drift / repeated_use (Notion → Obsidian)
    # ---------------------------------------------------------------
    Phase3GroupSpec(
        spine=SkeletonAwareSpine(
            sample_id="p3-smoke-drift-noteapp-001",
            sample_type="supersession",
            target_type="object_preference",
            domain="productivity",
            target_description=(
                "user's drifted note-taking app — moved from Notion to "
                "Obsidian via repeated active use, no explicit announcement"
            ),
            target_slot_id="note_taking_app::v1",
            topic="note_taking_workflow",
            versions=[
                VersionSpec(value="Notion workspace with templated databases",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Obsidian vault with daily-notes plugin and wiki-style backlinks",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "Capture today's takeaways from the founders' summit — "
                "where am I writing?"
            ),
            required_behavior=(
                "Write the takeaways into the Obsidian vault, using the "
                "daily-notes plugin and wiki-style backlinks."
            ),
            invalid_behavior=[
                "Save the takeaways to Notion",
                "Suggest a templated Notion database",
                "Treat both as equivalent options",
            ],
            n_sessions=5,
            subtype="strong",
            horizon="standard",  # placeholder; overridden by group orchestrator
            failure_patterns=["implicit_drift"],
            triple_id="p3-smoke-drift-noteapp-001",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="repeated_use",
        spine_source="hand",
    ),

    # ---------------------------------------------------------------
    # Group 2: implicit_drift / abandonment (Kindle reading → done with reading)
    # Note: this one is harder to author cleanly as drift; using a
    # different example: in-bed phone scrolling → archived for sleep
    # ---------------------------------------------------------------
    Phase3GroupSpec(
        spine=SkeletonAwareSpine(
            sample_id="p3-smoke-drift-bedphone-001",
            sample_type="supersession",
            target_type="procedural_constraint",
            domain="lifestyle",
            target_description=(
                "user's drifted bedtime phone behavior — abandoned in-bed "
                "scrolling, phone now parked outside bedroom (abandonment)"
            ),
            target_slot_id="bedtime_phone::v1",
            topic="bedtime_routine",
            versions=[
                VersionSpec(value="phone in bed scrolling until lights-out",
                            polarity="constraint", session_introduced=1),
                VersionSpec(value="phone parked outside the bedroom on the hallway charger",
                            polarity="constraint", session_introduced=2),
            ],
            current_query=(
                "10 p.m. — give me my wind-down sequence for the next hour."
            ),
            required_behavior=(
                "Wind down without the phone in bed; phone parked on the "
                "hallway charger before lights-out."
            ),
            invalid_behavior=[
                "Suggest scrolling on the phone in bed",
                "Suggest checking notifications from bed",
                "Treat phone-in-bed as still acceptable",
            ],
            n_sessions=5,
            subtype="strong",
            horizon="standard",
            failure_patterns=["implicit_drift"],
            triple_id="p3-smoke-drift-bedphone-001",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type="abandonment",
        spine_source="hand",
    ),

    # ---------------------------------------------------------------
    # Group 3: explicit_replacement (control — non-drift, no extractor)
    # ---------------------------------------------------------------
    Phase3GroupSpec(
        spine=SkeletonAwareSpine(
            sample_id="p3-smoke-explicit-vendor-001",
            sample_type="supersession",
            target_type="object_preference",
            domain="business",
            target_description=(
                "team's explicit ATS switch — Greenhouse retired, Ashby "
                "is the new system going forward"
            ),
            target_slot_id="ats_vendor::v1",
            topic="ats_vendor",
            versions=[
                VersionSpec(value="Greenhouse",
                            polarity="prefer", session_introduced=1),
                VersionSpec(value="Ashby",
                            polarity="prefer", session_introduced=2),
            ],
            current_query=(
                "Need to post the staff-engineer role — where's it going up?"
            ),
            required_behavior=(
                "Post the role to Ashby."
            ),
            invalid_behavior=[
                "Post the role to Greenhouse",
                "Mention both as options",
            ],
            n_sessions=5,
            subtype="strong",
            horizon="standard",
            failure_patterns=["explicit_replacement"],
            triple_id="p3-smoke-explicit-vendor-001",
        ),
        group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None,
        spine_source="hand",
    ),

]
