"""Phase 3 batch C — 20 spines targeting the deepest underfills.

After batch_b: 42 groups; topic-cell breaches 0; non-object 59.5%.
Remaining underfills (target — selected):
  repeated_use         55
  narrowing            59
  multi triple         55
  multi doublet        45
  explicit             44
  abandonment          36
  gradual_narrowing    14

This batch authors 20 spines weighted toward those gaps:
  6 repeated_use (mixed topics)
  4 narrowing (mixed topics)
  3 multi triple (mixed topics)
  2 multi doublet (4+ version chains)
  3 abandonment (mixed topics)
  1 explicit
  1 gradual_narrowing

Topic distribution kept balanced across all 4 buckets, target_type
biased ~50% non-object so we stay above the §10.3 floor.
"""

from pipeline.construction import VersionSpec
from pipeline.construction.phase3 import Phase3GroupSpec
from pipeline.construction.skeleton_realizer import SkeletonAwareSpine


def _spine(*, sample_id, target_type, domain, target_description, target_slot_id,
           topic, versions, current_query, required_behavior, invalid_behavior,
           failure_patterns, subtype="strong"):
    return SkeletonAwareSpine(
        sample_id=sample_id, sample_type="supersession",
        target_type=target_type, domain=domain,
        target_description=target_description, target_slot_id=target_slot_id,
        topic=topic, versions=versions, current_query=current_query,
        required_behavior=required_behavior, invalid_behavior=invalid_behavior,
        n_sessions=5, subtype=subtype, horizon="standard",
        failure_patterns=failure_patterns, triple_id=sample_id,
    )


def _drift_triple(spine, drift_type):
    return Phase3GroupSpec(
        spine=spine, group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=drift_type, spine_source="hand",
    )


def _other_triple(spine):
    return Phase3GroupSpec(
        spine=spine, group_type="triple",
        horizons=["compact", "standard", "hard"],
        implicit_drift_type=None, spine_source="hand",
    )


def _doublet(spine):
    return Phase3GroupSpec(
        spine=spine, group_type="doublet",
        horizons=["standard", "hard"],
        implicit_drift_type=None, spine_source="hand",
    )


PHASE3_BATCH_C: list[Phase3GroupSpec] = [

    # ============= REPEATED_USE (6) =============

    _drift_triple(_spine(
        sample_id="p3-drift-water-bottle-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's daily water bottle — drifted from disposable plastic to insulated steel via repeated active use",
        target_slot_id="water_bottle::v1", topic="daily_water_bottle",
        versions=[
            VersionSpec(value="disposable plastic water bottles from the office cooler", polarity="prefer", session_introduced=1),
            VersionSpec(value="insulated stainless steel bottle refilled at the filter station", polarity="prefer", session_introduced=2),
        ],
        current_query="Set up a hydration reminder for my afternoon work block.",
        required_behavior="Set the reminder around the user's insulated stainless steel bottle, refilled at the filter station.",
        invalid_behavior=["Suggest grabbing a disposable plastic bottle", "Suggest sparkling water cans", "Suggest no bottle at all"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift_triple(_spine(
        sample_id="p3-drift-saved-search-001",
        target_type="procedural_constraint", domain="work",
        target_description="user's how-they-find-similar-tickets habit — drifted from manual Jira search to a saved-filter dashboard, repeated active use",
        target_slot_id="ticket_lookup::v1", topic="ticket_lookup_workflow",
        versions=[
            VersionSpec(value="manual keyword search across the Jira project board", polarity="constraint", session_introduced=1),
            VersionSpec(value="the saved-filter dashboard pinned to the team's Jira home", polarity="constraint", session_introduced=2),
        ],
        current_query="I need similar incident tickets from the past quarter — pull them up.",
        required_behavior="Open the saved-filter dashboard pinned to the team's Jira home and pull recent incident tickets from there.",
        invalid_behavior=["Run a manual keyword search across the Jira board", "Suggest a different ticketing tool", "Skip the lookup"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift_triple(_spine(
        sample_id="p3-drift-grocery-app-001",
        target_type="object_preference", domain="food_dining",
        target_description="user's grocery-ordering channel — drifted from in-store shopping to Instacart Costco delivery, repeated active use",
        target_slot_id="grocery_channel::v1", topic="grocery_channel",
        versions=[
            VersionSpec(value="in-store shopping at the neighborhood Trader Joe's", polarity="prefer", session_introduced=1),
            VersionSpec(value="Instacart same-day delivery from the Costco warehouse", polarity="prefer", session_introduced=2),
        ],
        current_query="The fridge is almost empty — what's my next move?",
        required_behavior="Place an Instacart same-day delivery order from the Costco warehouse.",
        invalid_behavior=["Suggest going to Trader Joe's in-store", "Suggest curbside pickup", "Suggest skipping the order"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift_triple(_spine(
        sample_id="p3-drift-prayer-meditation-001",
        target_type="procedural_constraint", domain="lifestyle",
        target_description="user's morning quiet time — drifted from prayer at the kitchen table to silent meditation on the balcony, repeated active use",
        target_slot_id="morning_quiet::v1", topic="morning_quiet_time",
        versions=[
            VersionSpec(value="ten minutes of structured prayer at the kitchen table", polarity="constraint", session_introduced=1),
            VersionSpec(value="fifteen minutes of silent meditation on the balcony", polarity="constraint", session_introduced=2),
        ],
        current_query="What's the first item on my calendar tomorrow morning?",
        required_behavior="Block fifteen minutes of silent meditation on the balcony first thing tomorrow.",
        invalid_behavior=["Block prayer at the kitchen table", "Skip morning quiet time", "Suggest a guided audio session indoors"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift_triple(_spine(
        sample_id="p3-drift-team-doc-format-001",
        target_type="conceptual_stance", domain="work_communication",
        target_description="user's team RFC drafting style — drifted from full prose to one-page decision matrix, repeated active use",
        target_slot_id="rfc_format::v1", topic="rfc_drafting_style",
        versions=[
            VersionSpec(value="full prose RFC with motivation, options, and tradeoffs sections", polarity="prefer", session_introduced=1),
            VersionSpec(value="one-page decision matrix with options as rows and dimensions as columns", polarity="prefer", session_introduced=2),
        ],
        current_query="I need to propose a new caching layer — start the design doc.",
        required_behavior="Start a one-page decision matrix with caching options as rows and dimensions as columns.",
        invalid_behavior=["Start a full prose RFC", "Mix prose and matrix", "Suggest a slide deck"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift_triple(_spine(
        sample_id="p3-drift-newsletter-cadence-001",
        target_type="procedural_constraint", domain="leisure",
        target_description="user's weekly tech newsletter intake — drifted from skim-on-Saturday to read-during-Monday-commute, repeated active use",
        target_slot_id="newsletter_intake::v1", topic="newsletter_intake_cadence",
        versions=[
            VersionSpec(value="Saturday-morning skim of the past week's newsletters with coffee", polarity="constraint", session_introduced=1),
            VersionSpec(value="Monday-morning commute read-through on the train", polarity="constraint", session_introduced=2),
        ],
        current_query="When should I batch my industry-content intake this week?",
        required_behavior="Schedule the industry-content batch for the Monday-morning commute on the train.",
        invalid_behavior=["Read them Saturday morning with coffee", "Read them throughout the week as they arrive", "Skip them"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    # ============= NARROWING (4) =============

    _other_triple(_spine(
        sample_id="p3-narrow-dinner-protein-001",
        target_type="object_preference", domain="food",
        target_description="user's weeknight dinner protein — three explicit narrowings: any animal protein → poultry-and-fish only → fish only",
        target_slot_id="dinner_protein::v1", topic="weeknight_protein",
        versions=[
            VersionSpec(value="any animal protein — beef, pork, chicken, fish", polarity="prefer", session_introduced=1),
            VersionSpec(value="poultry and fish only — no red meat or pork", polarity="prefer", session_introduced=2),
            VersionSpec(value="fish only — no poultry, red meat, or pork", polarity="prefer", session_introduced=3),
        ],
        current_query="Pick tonight's main dish.",
        required_behavior="Pick a fish-based main dish.",
        invalid_behavior=["Pick a pork dish", "Pick a poultry dish", "Pick a red-meat dish"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _other_triple(_spine(
        sample_id="p3-narrow-deploy-window-001",
        target_type="procedural_constraint", domain="tech_workflow",
        target_description="team's production deploy window — three explicit narrowings: 24/7 → business hours → Tue/Thu mornings 10–12",
        target_slot_id="deploy_window::v1", topic="prod_deploy_window",
        versions=[
            VersionSpec(value="any time of day, any day of the week", polarity="constraint", session_introduced=1),
            VersionSpec(value="business hours only, Monday through Friday 9 AM to 5 PM", polarity="constraint", session_introduced=2),
            VersionSpec(value="Tuesday and Thursday mornings between 10 AM and noon only", polarity="constraint", session_introduced=3),
        ],
        current_query="Marcus has a finished feature branch ready — when can it ship to prod?",
        required_behavior="Schedule the deploy for the next Tuesday or Thursday morning between 10 AM and noon.",
        invalid_behavior=["Deploy immediately on a Friday afternoon", "Deploy any time during business hours", "Deploy on a weekend"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _other_triple(_spine(
        sample_id="p3-narrow-hiring-source-001",
        target_type="procedural_constraint", domain="management",
        target_description="user's senior-engineer sourcing — three explicit narrowings: any channel → in-network referral → in-network referral with prior-shipped-product",
        target_slot_id="senior_sourcing::v1", topic="senior_engineer_sourcing",
        versions=[
            VersionSpec(value="any candidate from job boards, LinkedIn, or recruiting agencies", polarity="constraint", session_introduced=1),
            VersionSpec(value="only candidates referred by someone already in our network", polarity="constraint", session_introduced=2),
            VersionSpec(value="only network referrals who have shipped at least one production system in their last role", polarity="constraint", session_introduced=3),
        ],
        current_query="Recruiting just flagged a promising inbound — should we move them forward?",
        required_behavior="Move the candidate forward only if they came via in-network referral AND shipped at least one production system in their last role.",
        invalid_behavior=["Move forward any LinkedIn inbound", "Move forward any network referral", "Reject all inbound applications outright"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _other_triple(_spine(
        sample_id="p3-narrow-bedtime-content-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's pre-sleep content — three explicit narrowings: any podcast/show → audiobooks only → audiobooks of fiction only",
        target_slot_id="bedtime_content::v1", topic="bedtime_audio_content",
        versions=[
            VersionSpec(value="any podcast or streaming show", polarity="prefer", session_introduced=1),
            VersionSpec(value="audiobooks only — no podcasts or video", polarity="prefer", session_introduced=2),
            VersionSpec(value="audiobooks of fiction only — no non-fiction", polarity="prefer", session_introduced=3),
        ],
        current_query="Queue something for me to put on after lights-out tonight.",
        required_behavior="Queue an audiobook of fiction.",
        invalid_behavior=["Queue a non-fiction audiobook", "Queue a podcast", "Queue a streaming show"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    # ============= MULTI_VERSION TRIPLE (3) =============

    _other_triple(_spine(
        sample_id="p3-multi-doc-tool-001",
        target_type="object_preference", domain="work_workflow",
        target_description="team's design-doc home — three-version chain: Confluence → Notion → Slab",
        target_slot_id="doc_home::v1", topic="design_doc_home",
        versions=[
            VersionSpec(value="Confluence with the legacy template gallery", polarity="prefer", session_introduced=1),
            VersionSpec(value="Notion with the linked-database hierarchy", polarity="prefer", session_introduced=2),
            VersionSpec(value="Slab with the team-scoped folders", polarity="prefer", session_introduced=3),
        ],
        current_query="Sarah's writing the auth-refactor design — where does it go?",
        required_behavior="The auth-refactor design doc goes in Slab under the team-scoped folder.",
        invalid_behavior=["Put it in Confluence", "Put it in Notion", "Put it in a Google Doc"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _other_triple(_spine(
        sample_id="p3-multi-photo-storage-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's primary photo storage — three-version chain: iCloud → Google Photos → self-hosted Immich",
        target_slot_id="photo_storage::v1", topic="primary_photo_storage",
        versions=[
            VersionSpec(value="iCloud Photos with the family-sharing album", polarity="prefer", session_introduced=1),
            VersionSpec(value="Google Photos with the unlimited high-quality plan", polarity="prefer", session_introduced=2),
            VersionSpec(value="self-hosted Immich photo library on the home NAS", polarity="prefer", session_introduced=3),
        ],
        current_query="I just got back from the trip — where do the new shots go?",
        required_behavior="Upload the trip shots to the self-hosted Immich photo library on the home NAS.",
        invalid_behavior=["Upload to iCloud Photos", "Upload to Google Photos", "Leave them on the phone"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _other_triple(_spine(
        sample_id="p3-multi-mentorship-format-001",
        target_type="procedural_constraint", domain="management",
        target_description="user's junior-engineer mentorship format — three-version chain with one revert: weekly 1:1 → group office hours → weekly 1:1",
        target_slot_id="mentorship_format::v1", topic="junior_mentorship_format",
        versions=[
            VersionSpec(value="weekly 30-minute 1:1 mentorship session with each junior engineer", polarity="constraint", session_introduced=1),
            VersionSpec(value="group office hours every Friday afternoon for any junior engineer to drop in", polarity="constraint", session_introduced=2),
            VersionSpec(value="weekly 30-minute 1:1 mentorship session with each junior engineer", polarity="constraint", session_introduced=3),
        ],
        current_query="Block the next round of junior-engineer mentorship time on my calendar.",
        required_behavior="Block weekly 30-minute 1:1 mentorship sessions with each junior engineer.",
        invalid_behavior=["Block group office hours on Friday", "Block ad-hoc mentorship without a fixed cadence", "Skip blocking entirely"],
        failure_patterns=["multi_version"], subtype="reverted",
    )),

    # ============= MULTI_VERSION DOUBLET (2, 4+ versions) =============

    _doublet(_spine(
        sample_id="p3-multi-database-4v-001",
        target_type="procedural_constraint", domain="tech_workflow",
        target_description="team's primary OLTP database — four-version chain across infra migrations",
        target_slot_id="oltp_database::v1", topic="primary_oltp_database",
        versions=[
            VersionSpec(value="MySQL 5.7 self-hosted on the legacy bare-metal cluster", polarity="prefer", session_introduced=1),
            VersionSpec(value="Aurora MySQL with the read-replica fleet", polarity="prefer", session_introduced=2),
            VersionSpec(value="Postgres 14 on RDS with logical replication", polarity="prefer", session_introduced=3),
            VersionSpec(value="CockroachDB Serverless with the multi-region deployment", polarity="prefer", session_introduced=4),
        ],
        current_query="Provision the primary store for the new payments microservice.",
        required_behavior="Provision the new payments service on CockroachDB Serverless with the multi-region deployment.",
        invalid_behavior=["Provision on MySQL 5.7 bare-metal", "Provision on Aurora MySQL", "Provision on Postgres RDS"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _doublet(_spine(
        sample_id="p3-multi-payment-method-4v-001",
        target_type="object_preference", domain="finance",
        target_description="user's primary credit card for travel — four-version chain across rewards-program changes",
        target_slot_id="travel_credit_card::v1", topic="travel_credit_card",
        versions=[
            VersionSpec(value="Chase Sapphire Preferred with the Ultimate Rewards transfer partners", polarity="prefer", session_introduced=1),
            VersionSpec(value="Amex Platinum with the airline lounge access", polarity="prefer", session_introduced=2),
            VersionSpec(value="Capital One Venture X with the unlimited 2x miles", polarity="prefer", session_introduced=3),
            VersionSpec(value="Citi Strata Premier with the rotating 3x bonus categories", polarity="prefer", session_introduced=4),
        ],
        current_query="Book the next conference flight to Seattle.",
        required_behavior="Book the Seattle flight on the Citi Strata Premier card to capture the rotating 3x bonus.",
        invalid_behavior=["Book on Chase Sapphire Preferred", "Book on Amex Platinum", "Book on Capital One Venture X"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    # ============= ABANDONMENT (3) =============

    _drift_triple(_spine(
        sample_id="p3-drift-physical-mail-001",
        target_type="procedural_constraint", domain="lifestyle",
        target_description="user's bill payment — abandoned the paper-mail-and-check workflow; now everything paperless via auto-pay",
        target_slot_id="bill_payment::v1", topic="bill_payment_method",
        versions=[
            VersionSpec(value="check writing and physical-mail return for monthly utility bills", polarity="constraint", session_introduced=1),
            VersionSpec(value="paperless auto-pay through the bank's bill-pay service", polarity="constraint", session_introduced=2),
        ],
        current_query="The water bill arrived in my inbox — what do I do with it?",
        required_behavior="Confirm the bill is on the bank's auto-pay schedule and let it pay automatically.",
        invalid_behavior=["Suggest writing a check and mailing it", "Suggest manually paying via the utility's website", "Suggest ignoring the bill"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    _drift_triple(_spine(
        sample_id="p3-drift-conference-attendance-001",
        target_type="procedural_constraint", domain="learning",
        target_description="user's industry-conference attendance — abandoned in-person travel; remote-only via streaming",
        target_slot_id="conference_attendance::v1", topic="conference_mode",
        versions=[
            VersionSpec(value="in-person attendance with travel and the hotel block", polarity="constraint", session_introduced=1),
            VersionSpec(value="remote streaming attendance from the home office", polarity="constraint", session_introduced=2),
        ],
        current_query="Sign me up for next month's KubeCon.",
        required_behavior="Sign up for the remote streaming pass to KubeCon and watch from the home office.",
        invalid_behavior=["Book the in-person registration with travel and hotel", "Skip registration entirely", "Suggest the in-person and remote combo pass"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    _drift_triple(_spine(
        sample_id="p3-drift-personal-blog-001",
        target_type="object_preference", domain="creative",
        target_description="user's writing outlet — abandoned the personal blog; substack newsletter is the new home",
        target_slot_id="writing_outlet::v1", topic="public_writing_outlet",
        versions=[
            VersionSpec(value="self-hosted personal blog on the WordPress instance", polarity="prefer", session_introduced=1),
            VersionSpec(value="Substack newsletter with the paid-subscriber tier", polarity="prefer", session_introduced=2),
        ],
        current_query="I just finished a draft on remote-work patterns — where do I publish it?",
        required_behavior="Publish the remote-work piece as a new Substack newsletter issue.",
        invalid_behavior=["Publish to the WordPress blog", "Cross-post to both", "Save as a draft and publish nowhere"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    # ============= EXPLICIT (1) =============

    _other_triple(_spine(
        sample_id="p3-explicit-music-streaming-001",
        target_type="object_preference", domain="leisure",
        target_description="user's music streaming service — explicit replacement of Spotify with Apple Music",
        target_slot_id="music_service::v1", topic="music_streaming_service",
        versions=[
            VersionSpec(value="Spotify Premium with the personalized Discover Weekly", polarity="prefer", session_introduced=1),
            VersionSpec(value="Apple Music with the Lossless tier", polarity="prefer", session_introduced=2),
        ],
        current_query="Queue something to play during dinner tonight.",
        required_behavior="Queue music from the Apple Music Lossless library for dinner tonight.",
        invalid_behavior=["Queue from Spotify Premium", "Queue from a third service", "Suggest no music"],
        failure_patterns=["explicit_replacement"],
    )),

    # ============= GRADUAL_NARROWING (1) =============

    _drift_triple(_spine(
        sample_id="p3-drift-clothing-narrow-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's office clothing — gradually narrowed from any business-casual to a fixed three-color capsule wardrobe via cumulative preference signals",
        target_slot_id="office_clothing::v1", topic="office_clothing_choice",
        versions=[
            VersionSpec(value="any business-casual outfit from the closet", polarity="prefer", session_introduced=1),
            VersionSpec(value="a fixed three-color capsule wardrobe of black, navy, and grey only", polarity="prefer", session_introduced=2),
        ],
        current_query="What should I wear to the office tomorrow?",
        required_behavior="Pick an outfit from the three-color capsule wardrobe of black, navy, and grey.",
        invalid_behavior=["Pick a brightly colored shirt", "Pick anything outside the three-color palette", "Suggest a suit"],
        failure_patterns=["implicit_drift"],
    ), "gradual_narrowing"),

]
