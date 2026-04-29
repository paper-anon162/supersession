"""Phase 3 batch E — 20 spines, balanced fill.

Target distribution:
  6 repeated_use, 4 narrow, 3 multi triple, 2 multi doublet,
  2 explicit, 2 abandonment, 1 gradual_narrowing
"""

from pipeline.construction import VersionSpec
from pipeline.construction.phase3 import Phase3GroupSpec
from pipeline.construction.skeleton_realizer import SkeletonAwareSpine


def _s(*, sample_id, target_type, domain, target_description, target_slot_id,
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

def _drift(spine, dt):
    return Phase3GroupSpec(spine=spine, group_type="triple",
                          horizons=["compact", "standard", "hard"],
                          implicit_drift_type=dt, spine_source="hand")

def _trip(spine):
    return Phase3GroupSpec(spine=spine, group_type="triple",
                          horizons=["compact", "standard", "hard"],
                          implicit_drift_type=None, spine_source="hand")

def _doub(spine):
    return Phase3GroupSpec(spine=spine, group_type="doublet",
                          horizons=["standard", "hard"],
                          implicit_drift_type=None, spine_source="hand")


PHASE3_BATCH_E: list[Phase3GroupSpec] = [

    # repeated_use (6)
    _drift(_s(
        sample_id="p3-drift-doc-handwriting-001",
        target_type="object_preference", domain="creative",
        target_description="user's daily journaling tool — drifted to a Remarkable 2 tablet from a leather Moleskine notebook, repeated active use",
        target_slot_id="journal_tool::v1", topic="daily_journal_tool",
        versions=[
            VersionSpec(value="leather Moleskine notebook with the fountain pen and ruled pages", polarity="prefer", session_introduced=1),
            VersionSpec(value="Remarkable 2 tablet with the synced cloud library", polarity="prefer", session_introduced=2),
        ],
        current_query="Capture today's reflections from the long walk this morning.",
        required_behavior="Capture today's reflections on the Remarkable 2 tablet, synced to the cloud library.",
        invalid_behavior=["Capture in the Moleskine notebook with the fountain pen", "Capture in a digital text editor", "Skip capturing"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-meal-portion-001",
        target_type="procedural_constraint", domain="food",
        target_description="user's plate composition — drifted to a fixed half-veggies/quarter-protein/quarter-grain plate from any-portion eating, repeated active use",
        target_slot_id="plate_portion::v1", topic="plate_composition",
        versions=[
            VersionSpec(value="any portion split that the user feels like at the moment", polarity="constraint", session_introduced=1),
            VersionSpec(value="half veggies, quarter protein, quarter grain on every plate", polarity="constraint", session_introduced=2),
        ],
        current_query="What's the layout for tonight's plate?",
        required_behavior="Split the plate as half veggies, quarter protein, and quarter grain.",
        invalid_behavior=["Pile mostly grain", "Pile mostly protein", "Skip the structure entirely"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-newsletter-host-001",
        target_type="object_preference", domain="creative",
        target_description="user's newsletter publishing platform — drifted to Buttondown from Substack via repeated active use",
        target_slot_id="newsletter_platform::v1", topic="newsletter_platform",
        versions=[
            VersionSpec(value="Substack with the public discoverability and recommendation algorithm", polarity="prefer", session_introduced=1),
            VersionSpec(value="Buttondown with the markdown editor and self-hosted archive", polarity="prefer", session_introduced=2),
        ],
        current_query="I'm ready to send the next issue — where do I draft and publish it?",
        required_behavior="Draft and publish the next issue in Buttondown using the markdown editor and self-hosted archive.",
        invalid_behavior=["Draft and publish in Substack", "Send via plain email", "Cross-post to both"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-meal-prep-day-001",
        target_type="procedural_constraint", domain="food",
        target_description="user's meal-prep day — drifted to Wednesday-evening prep from Sunday-afternoon prep, repeated active use",
        target_slot_id="meal_prep_day::v1", topic="meal_prep_day",
        versions=[
            VersionSpec(value="Sunday-afternoon meal prep covering all weekday lunches", polarity="constraint", session_introduced=1),
            VersionSpec(value="Wednesday-evening meal prep covering Wednesday through Sunday lunches", polarity="constraint", session_introduced=2),
        ],
        current_query="Block this week's meal-prep time on my calendar.",
        required_behavior="Block Wednesday-evening time for meal prep covering Wednesday through Sunday lunches.",
        invalid_behavior=["Block Sunday-afternoon time", "Block ad-hoc time without a fixed day", "Skip blocking"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-pull-request-format-001",
        target_type="conceptual_stance", domain="tech_workflow",
        target_description="user's PR description style — drifted to a structured 'why/what/test' three-section template from free-form prose, repeated active use",
        target_slot_id="pr_description_style::v1", topic="pr_description_style",
        versions=[
            VersionSpec(value="free-form prose paragraphs with no fixed structure", polarity="prefer", session_introduced=1),
            VersionSpec(value="structured three-section template — Why, What, Test — for every pull request", polarity="prefer", session_introduced=2),
        ],
        current_query="I just pushed the auth-token rotation branch — write the description.",
        required_behavior="Write the auth-token rotation pull request description using the Why, What, Test three-section template.",
        invalid_behavior=["Write a free-form prose description", "Skip the description and just push", "Use a different template"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-incident-debrief-001",
        target_type="procedural_constraint", domain="management",
        target_description="user's incident-debrief format — drifted to a blameless five-question template from open-ended discussion, repeated active use",
        target_slot_id="incident_debrief::v1", topic="incident_debrief_format",
        versions=[
            VersionSpec(value="open-ended discussion with the on-call engineer the day after", polarity="constraint", session_introduced=1),
            VersionSpec(value="blameless five-question template covering trigger, detection, mitigation, customer impact, and prevention", polarity="constraint", session_introduced=2),
        ],
        current_query="Yesterday's database outage is settled — set up the debrief.",
        required_behavior="Set up the database-outage debrief using the blameless five-question template covering trigger, detection, mitigation, customer impact, and prevention.",
        invalid_behavior=["Set up an open-ended discussion", "Skip the debrief", "Send a postmortem doc instead"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    # narrowing (4)
    _trip(_s(
        sample_id="p3-narrow-screen-time-001",
        target_type="procedural_constraint", domain="lifestyle",
        target_description="user's screen-time discipline — three explicit narrowings: any time → no after-9-PM → no after-9-PM and no before-8-AM",
        target_slot_id="screen_discipline::v1", topic="screen_time_discipline",
        versions=[
            VersionSpec(value="screen time at any hour with no fixed window", polarity="constraint", session_introduced=1),
            VersionSpec(value="no screen time after 9 PM", polarity="constraint", session_introduced=2),
            VersionSpec(value="no screen time after 9 PM and no screen time before 8 AM", polarity="constraint", session_introduced=3),
        ],
        current_query="It's 7:30 AM and the phone is buzzing — should I look?",
        required_behavior="Hold off until 8 AM before checking the phone.",
        invalid_behavior=["Check immediately", "Check after 7:45 AM", "Defer for the rest of the day"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-feedback-format-001",
        target_type="conceptual_stance", domain="management",
        target_description="user's report-feedback format — three explicit narrowings: any format → SBI structured → SBI plus written follow-up",
        target_slot_id="feedback_format::v1", topic="report_feedback_format",
        versions=[
            VersionSpec(value="any format that fits the conversation in the moment", polarity="prefer", session_introduced=1),
            VersionSpec(value="the SBI structure — Situation, Behavior, Impact — for every piece of report feedback", polarity="prefer", session_introduced=2),
            VersionSpec(value="the SBI structure with a written follow-up doc summarizing each session", polarity="prefer", session_introduced=3),
        ],
        current_query="Marcus shipped the auth feature with three regressions — give him feedback.",
        required_behavior="Deliver the feedback using the SBI structure (Situation, Behavior, Impact) and follow up with a written doc summarizing the session.",
        invalid_behavior=["Deliver freely without structure", "Deliver SBI without the written follow-up", "Skip the feedback entirely"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-coffee-source-001",
        target_type="object_preference", domain="food",
        target_description="user's coffee bean source — three explicit narrowings: any roaster → small-batch local → small-batch local with direct-trade certification",
        target_slot_id="coffee_source::v1", topic="coffee_bean_source",
        versions=[
            VersionSpec(value="any commercial coffee roaster the grocery store stocks", polarity="prefer", session_introduced=1),
            VersionSpec(value="only small-batch local roasters within the metro area", polarity="prefer", session_introduced=2),
            VersionSpec(value="only small-batch local roasters with direct-trade certification on the bag", polarity="prefer", session_introduced=3),
        ],
        current_query="Restock the bean jar this weekend.",
        required_behavior="Restock with beans from a small-batch local roaster carrying direct-trade certification.",
        invalid_behavior=["Buy from a commercial supermarket roaster", "Buy from a non-local small batch", "Buy from a local roaster without direct-trade certification"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-meeting-prep-001",
        target_type="procedural_constraint", domain="management",
        target_description="user's pre-meeting prep — three explicit narrowings: any prep → 24-hr-advance written agenda → 24-hr-advance agenda + circulated reading list",
        target_slot_id="meeting_prep::v1", topic="meeting_prep_workflow",
        versions=[
            VersionSpec(value="prep the meeting however it fits the day — verbally or in a doc", polarity="constraint", session_introduced=1),
            VersionSpec(value="circulate a written agenda 24 hours before every meeting", polarity="constraint", session_introduced=2),
            VersionSpec(value="circulate a written agenda 24 hours before plus a reading list for every meeting", polarity="constraint", session_introduced=3),
        ],
        current_query="Tomorrow's leadership review is on the books — get me ready.",
        required_behavior="Get the user ready by circulating a written agenda 24 hours ahead and a curated reading list for the leadership review.",
        invalid_behavior=["Just prep it in your head", "Send only an agenda without a reading list", "Send only a reading list without an agenda"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    # multi_version triple (3)
    _trip(_s(
        sample_id="p3-multi-newsletter-tool-001",
        target_type="object_preference", domain="creative",
        target_description="user's newsletter authoring tool — three-version chain: Mailchimp → ConvertKit → beehiiv",
        target_slot_id="newsletter_authoring::v1", topic="newsletter_authoring_tool",
        versions=[
            VersionSpec(value="Mailchimp with the legacy free-tier templates", polarity="prefer", session_introduced=1),
            VersionSpec(value="ConvertKit with the creator-pro automation sequences", polarity="prefer", session_introduced=2),
            VersionSpec(value="beehiiv with the referral-program and paid-recommendations features", polarity="prefer", session_introduced=3),
        ],
        current_query="I'm starting a new vertical — set up the publishing workspace.",
        required_behavior="Set up the new vertical's publishing workspace in beehiiv using the referral-program and paid-recommendations features.",
        invalid_behavior=["Set up in Mailchimp", "Set up in ConvertKit", "Set up in a generic email tool"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-multi-bike-001",
        target_type="object_preference", domain="travel",
        target_description="user's primary bike — three-version chain: hybrid commuter → road bike → gravel bike",
        target_slot_id="primary_bike::v1", topic="primary_bike",
        versions=[
            VersionSpec(value="hybrid commuter bike with the upright handlebars and rack", polarity="prefer", session_introduced=1),
            VersionSpec(value="road bike with the carbon frame and drop bars", polarity="prefer", session_introduced=2),
            VersionSpec(value="gravel bike with the wide tires and frame bag", polarity="prefer", session_introduced=3),
        ],
        current_query="Saturday morning weather looks great — pull out the right bike.",
        required_behavior="Pull out the gravel bike with the wide tires and frame bag for Saturday morning.",
        invalid_behavior=["Pull out the hybrid commuter", "Pull out the road bike", "Stay home"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-multi-vegetable-delivery-001",
        target_type="object_preference", domain="food_dining",
        target_description="user's weekly produce source — three-version chain: Whole Foods → Imperfect Foods → local CSA box",
        target_slot_id="produce_source::v1", topic="weekly_produce_source",
        versions=[
            VersionSpec(value="Whole Foods 365-tier in-store shopping", polarity="prefer", session_introduced=1),
            VersionSpec(value="Imperfect Foods weekly delivery box with the customizable selection", polarity="prefer", session_introduced=2),
            VersionSpec(value="local CSA box from the Hudson Valley farm with the seasonal-only selection", polarity="prefer", session_introduced=3),
        ],
        current_query="Where am I sourcing this week's produce?",
        required_behavior="Source this week's produce from the local CSA box from the Hudson Valley farm.",
        invalid_behavior=["Source from Whole Foods", "Source from Imperfect Foods", "Source from a generic supermarket"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    # multi_version doublet (2)
    _doub(_s(
        sample_id="p3-multi-orchestration-4v-001",
        target_type="procedural_constraint", domain="tech_workflow",
        target_description="team's container orchestration — four-version chain: Docker Compose → Nomad → ECS Fargate → EKS",
        target_slot_id="orchestration::v1", topic="container_orchestration",
        versions=[
            VersionSpec(value="Docker Compose on the single bare-metal host", polarity="prefer", session_introduced=1),
            VersionSpec(value="HashiCorp Nomad with Consul service discovery", polarity="prefer", session_introduced=2),
            VersionSpec(value="AWS ECS Fargate with the task-definition templates", polarity="prefer", session_introduced=3),
            VersionSpec(value="AWS EKS with the managed node groups and Helm charts", polarity="prefer", session_introduced=4),
        ],
        current_query="Deploy the new fraud-detection microservice this sprint.",
        required_behavior="Deploy the fraud-detection microservice on AWS EKS using the managed node groups and Helm charts.",
        invalid_behavior=["Deploy on Docker Compose", "Deploy on Nomad", "Deploy on ECS Fargate"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _doub(_s(
        sample_id="p3-multi-dietary-style-4v-001",
        target_type="procedural_constraint", domain="food",
        target_description="user's overall eating pattern — four-version chain: standard omnivore → pescatarian → vegetarian → strict vegan",
        target_slot_id="eating_pattern::v1", topic="overall_eating_pattern",
        versions=[
            VersionSpec(value="standard omnivore diet with all meat, fish, and dairy", polarity="constraint", session_introduced=1),
            VersionSpec(value="pescatarian diet with fish and dairy but no other meat", polarity="constraint", session_introduced=2),
            VersionSpec(value="vegetarian diet with dairy and eggs but no meat or fish", polarity="constraint", session_introduced=3),
            VersionSpec(value="strict vegan diet with no animal products at all", polarity="constraint", session_introduced=4),
        ],
        current_query="Plan tonight's main course.",
        required_behavior="Plan a main course that follows a strict vegan profile with no animal products.",
        invalid_behavior=["Plan a meat-based dish", "Plan a fish-based dish", "Plan a dish with cheese or eggs"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    # explicit (2)
    _trip(_s(
        sample_id="p3-explicit-cloud-storage-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's personal cloud-storage service — explicit replacement of Dropbox with iCloud Drive",
        target_slot_id="personal_cloud::v1", topic="personal_cloud_storage",
        versions=[
            VersionSpec(value="Dropbox Plus with the smart-sync selective folders", polarity="prefer", session_introduced=1),
            VersionSpec(value="iCloud Drive with the 2TB family-sharing tier", polarity="prefer", session_introduced=2),
        ],
        current_query="Save the new tax documents somewhere durable.",
        required_behavior="Save the tax documents to iCloud Drive in the 2TB family-sharing tier.",
        invalid_behavior=["Save to Dropbox Plus", "Save to a generic cloud bucket", "Save to local disk only"],
        failure_patterns=["explicit_replacement"],
    )),

    _trip(_s(
        sample_id="p3-explicit-headphones-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's commute headphones — explicit replacement of Bose QuietComfort with Apple AirPods Max",
        target_slot_id="commute_headphones::v1", topic="commute_headphones",
        versions=[
            VersionSpec(value="Bose QuietComfort over-ear with the active noise cancellation", polarity="prefer", session_introduced=1),
            VersionSpec(value="Apple AirPods Max with the spatial-audio mode and digital crown", polarity="prefer", session_introduced=2),
        ],
        current_query="Pack the headphones for tomorrow's flight.",
        required_behavior="Pack the Apple AirPods Max with the spatial-audio mode for tomorrow's flight.",
        invalid_behavior=["Pack the Bose QuietComfort", "Pack a third pair", "Skip the headphones"],
        failure_patterns=["explicit_replacement"],
    )),

    # abandonment (2)
    _drift(_s(
        sample_id="p3-drift-paid-news-001",
        target_type="object_preference", domain="leisure",
        target_description="user's daily news source — abandoned the NYT paid subscription; only Hacker News and direct-blog reading now",
        target_slot_id="daily_news_source::v1", topic="daily_news_source",
        versions=[
            VersionSpec(value="New York Times paid subscription with the morning briefing email", polarity="prefer", session_introduced=1),
            VersionSpec(value="Hacker News and direct-blog reading via RSS only", polarity="prefer", session_introduced=2),
        ],
        current_query="What's on my reading list this morning?",
        required_behavior="Pull this morning's reading from Hacker News and the direct-blog RSS feeds.",
        invalid_behavior=["Pull from the New York Times morning briefing", "Pull from a third aggregator", "Skip reading"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    _drift(_s(
        sample_id="p3-drift-gym-membership-001",
        target_type="procedural_constraint", domain="fitness",
        target_description="user's strength-training venue — abandoned the commercial gym membership; home garage gym only now",
        target_slot_id="strength_venue::v1", topic="strength_training_venue",
        versions=[
            VersionSpec(value="commercial gym membership at the downtown chain with the morning class schedule", polarity="constraint", session_introduced=1),
            VersionSpec(value="home garage gym with the squat rack, bumper plates, and folding bench", polarity="constraint", session_introduced=2),
        ],
        current_query="Block tomorrow's strength session.",
        required_behavior="Block the strength session in the home garage gym with the squat rack, bumper plates, and folding bench.",
        invalid_behavior=["Block at the downtown commercial gym", "Block a class slot", "Skip strength training"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    # gradual_narrowing (1)
    _drift(_s(
        sample_id="p3-drift-investment-narrow-001",
        target_type="object_preference", domain="finance",
        target_description="user's discretionary investing — gradually narrowed from any individual equity to long-only S&P 500 index funds via cumulative preference signals",
        target_slot_id="discretionary_invest::v1", topic="discretionary_investing",
        versions=[
            VersionSpec(value="any individual equity that the user finds compelling", polarity="prefer", session_introduced=1),
            VersionSpec(value="long-only S&P 500 index funds with low expense ratios", polarity="prefer", session_introduced=2),
        ],
        current_query="Put this month's surplus to work.",
        required_behavior="Put the surplus into a long-only S&P 500 index fund with a low expense ratio.",
        invalid_behavior=["Put it into individual equities", "Put it into actively managed funds", "Hold it in cash indefinitely"],
        failure_patterns=["implicit_drift"],
    ), "gradual_narrowing"),
]
