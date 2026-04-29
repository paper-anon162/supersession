"""Phase 3 batch X — 25 spines, drift + doublet heavy."""

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

def _drift(s, dt): return Phase3GroupSpec(spine=s, group_type="triple", horizons=["compact","standard","hard"], implicit_drift_type=dt, spine_source="hand")
def _trip(s): return Phase3GroupSpec(spine=s, group_type="triple", horizons=["compact","standard","hard"], implicit_drift_type=None, spine_source="hand")
def _doub(s): return Phase3GroupSpec(spine=s, group_type="doublet", horizons=["standard","hard"], implicit_drift_type=None, spine_source="hand")


PHASE3_BATCH_X: list[Phase3GroupSpec] = [
    # multi_version doublet (8)
    _doub(_s(sample_id="p3-multi-doub-bike-tire-001", target_type="object_preference", domain="hobby",
        target_description="user's road-bike tire — Continental-GP5000 → Vittoria-Corsa",
        target_slot_id="bike_tire::v1", topic="road_bike_tire",
        versions=[
            VersionSpec(value="run Continental GP5000 clincher tires at 80psi on the road bike", polarity="prefer", session_introduced=1),
            VersionSpec(value="run Vittoria Corsa Speed tubeless tires at 65psi on the road bike instead of the GP5000", polarity="prefer", session_introduced=2),
        ],
        current_query="The bike shop asked which tires to mount during the spring tune-up — what do I tell them?",
        required_behavior="Mount Vittoria Corsa Speed tubeless at 65psi.",
        invalid_behavior=["Mount Continental GP5000 clincher at 80psi"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-grocery-cart-001", target_type="procedural_constraint", domain="food",
        target_description="user's grocery shopping cadence — once-weekly-big-haul → twice-weekly-small-haul",
        target_slot_id="grocery_cad::v1", topic="grocery_shopping_cadence",
        versions=[
            VersionSpec(value="grocery shop once a week on Saturday morning with a 200-dollar haul covering the full week", polarity="constraint", session_introduced=1),
            VersionSpec(value="grocery shop twice a week on Tuesday and Friday evenings with smaller fresher hauls instead of the Saturday big shop", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I heading to the grocery store for the weekly big shop?",
        required_behavior="No big shop; the routine is twice-weekly Tuesday/Friday smaller shops now.",
        invalid_behavior=["Head to the grocery store for the weekly big shop"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-newsletter-tool-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's newsletter platform — Substack → Beehiiv",
        target_slot_id="news_tool::v1", topic="newsletter_publishing_platform",
        versions=[
            VersionSpec(value="publish the weekly newsletter on Substack with their default subscriber emails", polarity="prefer", session_introduced=1),
            VersionSpec(value="publish the weekly newsletter on Beehiiv with the recommendations network instead of Substack", polarity="prefer", session_introduced=2),
        ],
        current_query="I am ready to send this week's newsletter — which platform do I publish on?",
        required_behavior="Publish on Beehiiv.",
        invalid_behavior=["Publish on Substack"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-flight-class-001", target_type="object_preference", domain="travel",
        target_description="user's flight booking class — economy-with-extra-legroom → premium-economy",
        target_slot_id="flight_class::v1", topic="flight_booking_class",
        versions=[
            VersionSpec(value="book economy-class flights with the extra-legroom seat upgrade for trips under five hours", polarity="prefer", session_introduced=1),
            VersionSpec(value="book premium-economy flights for any trip over three hours instead of economy with legroom", polarity="prefer", session_introduced=2),
        ],
        current_query="I am booking a 4-hour flight to Denver next month — which class do I pick?",
        required_behavior="Pick premium-economy.",
        invalid_behavior=["Pick economy with extra-legroom upgrade"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-1on1-cadence-001", target_type="procedural_constraint", domain="management",
        target_description="user's 1:1 cadence with skip-level — quarterly → monthly",
        target_slot_id="skip_cad::v1", topic="skip_level_one_on_one_cadence",
        versions=[
            VersionSpec(value="hold a 1:1 with the skip-level VP once a quarter for an hour", polarity="constraint", session_introduced=1),
            VersionSpec(value="hold a 1:1 with the skip-level VP once a month for thirty minutes instead of quarterly", polarity="constraint", session_introduced=2),
        ],
        current_query="My calendar is asking about the next skip-level VP 1:1 — how often does it recur?",
        required_behavior="Set it to a monthly thirty-minute recurrence.",
        invalid_behavior=["Set it to a quarterly hour-long recurrence"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-vacation-budget-001", target_type="procedural_constraint", domain="finance",
        target_description="user's vacation budget — fixed-3000-per-trip → percentage-of-monthly-savings",
        target_slot_id="vac_budget::v1", topic="vacation_budget_rule",
        versions=[
            VersionSpec(value="set a hard $3000 cap on every vacation trip including flights and lodging", polarity="constraint", session_introduced=1),
            VersionSpec(value="set the vacation budget at five percent of the prior six months' savings instead of a fixed dollar cap", polarity="constraint", session_introduced=2),
        ],
        current_query="I am planning a Europe trip — how much can I spend on flights and lodging?",
        required_behavior="Compute five percent of the prior six months' savings.",
        invalid_behavior=["Use a hard $3000 cap"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-essay-edit-001", target_type="procedural_constraint", domain="writing",
        target_description="user's essay editing process — one-pass-self-edit → three-pass-with-cooling-period",
        target_slot_id="essay_edit::v1", topic="essay_editing_process",
        versions=[
            VersionSpec(value="run a single self-edit pass on essay drafts before publishing", polarity="constraint", session_introduced=1),
            VersionSpec(value="run three self-edit passes spaced 24 hours apart on essay drafts before publishing instead of one pass", polarity="constraint", session_introduced=2),
        ],
        current_query="I just finished a 2000-word essay — when can I publish it?",
        required_behavior="In three days, after three edit passes spaced 24 hours apart.",
        invalid_behavior=["Publish today after one self-edit pass"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-friend-call-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's check-in call cadence with parents — weekly-Sunday-call → daily-five-min-text",
        target_slot_id="parent_call::v1", topic="parent_checkin_cadence",
        versions=[
            VersionSpec(value="call parents on the phone every Sunday afternoon for thirty minutes", polarity="constraint", session_introduced=1),
            VersionSpec(value="text parents every weekday morning with a five-minute update instead of the Sunday call", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday afternoon — should I call mom for the weekly catch-up?",
        required_behavior="No call; check-ins are daily morning texts now.",
        invalid_behavior=["Call mom for the weekly catch-up"],
        failure_patterns=["multi_version"], subtype="strong")),

    # implicit_drift / repeated_use (4)
    _drift(_s(sample_id="p3-drift-ru-coffeespot-001", target_type="object_preference", domain="food",
        target_description="user's after-work coffee spot — old chain Starbucks gradually replaced by independent neighborhood roaster user visits daily",
        target_slot_id="coffee_spot::v1", topic="afterwork_coffee_spot",
        versions=[
            VersionSpec(value="grab the after-work espresso at the Starbucks across the street from the office", polarity="prefer", session_introduced=1),
            VersionSpec(value="grab the after-work espresso at the independent Devoción roaster two blocks from the office instead of Starbucks", polarity="prefer", session_introduced=2),
        ],
        current_query="It is 5pm and I am ready for the after-work espresso — where do I walk to?",
        required_behavior="Walk to the Devoción roaster two blocks away.",
        invalid_behavior=["Walk to the Starbucks across the street"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-watch-strap-001", target_type="object_preference", domain="hobby",
        target_description="user's daily-driver watch strap — old leather strap gradually replaced by NATO nylon strap user wears every day",
        target_slot_id="strap::v1", topic="daily_watch_strap",
        versions=[
            VersionSpec(value="wear the brown leather strap on the daily-driver watch every day", polarity="prefer", session_introduced=1),
            VersionSpec(value="wear the navy NATO nylon strap on the daily-driver watch every day instead of the leather", polarity="prefer", session_introduced=2),
        ],
        current_query="I am putting on the watch this morning — which strap goes on?",
        required_behavior="Put on the navy NATO nylon strap.",
        invalid_behavior=["Put on the brown leather strap"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-evening-music-001", target_type="object_preference", domain="hobby",
        target_description="user's evening music — old jazz vinyl gradually replaced by ambient streaming user plays each night",
        target_slot_id="eve_music::v1", topic="evening_music_choice",
        versions=[
            VersionSpec(value="play classic jazz vinyl on the turntable every evening for the wind-down", polarity="prefer", session_introduced=1),
            VersionSpec(value="stream ambient music from Hammock and Brian Eno every evening for the wind-down instead of jazz vinyl", polarity="prefer", session_introduced=2),
        ],
        current_query="It is 9pm wind-down time — what goes on as background music?",
        required_behavior="Stream ambient music from Hammock and Brian Eno.",
        invalid_behavior=["Spin classic jazz vinyl on the turntable"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-feedback-tool-001", target_type="object_preference", domain="management",
        target_description="user's team feedback tool — old anonymous Officevibe gradually replaced by named Lattice user uses each week",
        target_slot_id="fb_tool::v1", topic="team_feedback_tool",
        versions=[
            VersionSpec(value="collect weekly team feedback through the anonymous Officevibe pulse survey", polarity="prefer", session_introduced=1),
            VersionSpec(value="collect weekly team feedback through named Lattice review docs instead of anonymous Officevibe", polarity="prefer", session_introduced=2),
        ],
        current_query="A direct report asked where to leave their weekly feedback — point them at which tool?",
        required_behavior="Point them at the Lattice review doc.",
        invalid_behavior=["Point them at the Officevibe pulse survey"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    # implicit_drift / abandonment (3)
    _drift(_s(sample_id="p3-drift-aban-fasting-001", target_type="procedural_constraint", domain="health",
        target_description="user's daily intermittent fasting — abandoned after side effects, no replacement",
        target_slot_id="fasting::v1", topic="intermittent_fasting_practice",
        versions=[
            VersionSpec(value="do a daily 16:8 intermittent-fasting window with eating only between noon and 8pm", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the daily 16:8 intermittent fasting after side effects and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 9am — am I skipping breakfast for the fast?",
        required_behavior="No; the intermittent fasting practice has been abandoned.",
        invalid_behavior=["Skip breakfast for the fast"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-bookclub-001", target_type="procedural_constraint", domain="learning",
        target_description="user's monthly book club — abandoned after the founding members moved away, no replacement",
        target_slot_id="bookclub::v1", topic="monthly_book_club_practice",
        versions=[
            VersionSpec(value="host a monthly book club at the apartment on the second Sunday afternoon every month", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop hosting the monthly book club after the founding members moved away and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the second Sunday — am I prepping snacks for the book club?",
        required_behavior="No; the monthly book club has been abandoned.",
        invalid_behavior=["Prep snacks for the book club"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-jogging-001", target_type="procedural_constraint", domain="health",
        target_description="user's morning jogging — abandoned after knee surgery, no replacement",
        target_slot_id="jogging::v1", topic="morning_jogging_practice",
        versions=[
            VersionSpec(value="jog three miles every morning before work along the riverside path", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the morning jogging after the knee surgery and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 6am — am I lacing up the running shoes for the morning jog?",
        required_behavior="No; the morning jogging has been abandoned.",
        invalid_behavior=["Lace up the running shoes for the morning jog"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # implicit_drift / gradual_narrowing (3)
    _drift(_s(sample_id="p3-drift-gn-art-buy-001", target_type="object_preference", domain="hobby",
        target_description="user's art-buying rule — gradually narrowing without announcement: any artist → only-emerging-women → only-emerging-women + under-2000",
        target_slot_id="art_buy::v1", topic="art_purchase_criteria",
        versions=[
            VersionSpec(value="buy any artwork the user finds compelling at galleries or art fairs", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only artwork by emerging women artists AND only pieces priced under two thousand dollars", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a 5000-dollar piece by an emerging woman artist at the local gallery — buy it?",
        required_behavior="Pass; user buys only emerging-women artists' work under 2000 dollars.",
        invalid_behavior=["Buy the 5000-dollar piece"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-tutorial-001", target_type="object_preference", domain="learning",
        target_description="user's online tutorial choice — gradually narrowing without announcement: any platform → only-paid-bootcamps → only-paid-bootcamps + with-cohort-of-15-or-fewer",
        target_slot_id="tutorial::v1", topic="online_tutorial_criteria",
        versions=[
            VersionSpec(value="enroll in any online tutorial the user finds interesting on YouTube or free platforms", polarity="prefer", session_introduced=1),
            VersionSpec(value="enroll only in paid bootcamps AND only ones with a cohort size of fifteen or fewer students", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a paid bootcamp with 30 students — enroll?",
        required_behavior="Pass; user enrolls only in paid bootcamps with cohorts ≤15.",
        invalid_behavior=["Enroll in the bootcamp with 30 students"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-event-go-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's event-attendance rule — gradually narrowing without announcement: any event → only-close-friends-host → only-close-friends-host + within-30-min-travel",
        target_slot_id="event_go::v1", topic="event_attendance_rule",
        versions=[
            VersionSpec(value="attend any social event the user is invited to that fits the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="attend social events only when hosted by a close friend AND only when the venue is within thirty minutes of travel", polarity="constraint", session_introduced=2),
        ],
        current_query="A close friend invited me to a party 90 minutes away by train next Friday — accept?",
        required_behavior="Pass; user attends only when hosted by close friend AND within 30 min travel.",
        invalid_behavior=["Accept the close-friend party 90 minutes away"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    # explicit_replacement (5)
    _trip(_s(sample_id="p3-explicit-grocery-method-001", target_type="procedural_constraint", domain="food",
        target_description="user's grocery method — explicitly replaces in-store-shopping with curbside-pickup",
        target_slot_id="grocery_method::v1", topic="grocery_shopping_method",
        versions=[
            VersionSpec(value="shop for weekly groceries in person at the local market with a paper list", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget in-person shopping — order weekly groceries through curbside pickup with the order placed online and picked up by car instead", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I driving to the market to shop in person?",
        required_behavior="No; place a curbside pickup order online and pick up by car.",
        invalid_behavior=["Drive to the market to shop in person"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-team-tool-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's team chat — explicitly replaces Slack with Discord-server",
        target_slot_id="team_chat::v1", topic="team_chat_tool",
        versions=[
            VersionSpec(value="run team chat coordination on Slack with channel-per-project and DMs", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget Slack — run team chat coordination on a private Discord server with voice rooms instead", polarity="prefer", session_introduced=2),
        ],
        current_query="A new hire asked where to ping me for quick questions — what do I tell them?",
        required_behavior="Tell them to ping in the team Discord server.",
        invalid_behavior=["Tell them to DM on Slack"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-news-source-001", target_type="object_preference", domain="learning",
        target_description="user's morning news — explicitly replaces NYT-app with FT-print-edition",
        target_slot_id="news_src::v1", topic="primary_news_source",
        versions=[
            VersionSpec(value="read morning news on the New York Times app for the daily digest", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the NYT app — read morning news in the Financial Times print edition delivered to the door instead", polarity="prefer", session_introduced=2),
        ],
        current_query="A breaking-news push from the NYT app just lit up my phone — open it?",
        required_behavior="No; news comes from the FT print edition now.",
        invalid_behavior=["Open the NYT push notification"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-skin-care-001", target_type="object_preference", domain="health",
        target_description="user's morning skincare — explicitly replaces 5-step-Korean with 3-step-CeraVe",
        target_slot_id="skin::v1", topic="morning_skincare_routine",
        versions=[
            VersionSpec(value="run a 5-step Korean skincare routine every morning with cleanser, toner, essence, serum, and SPF", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the 5-step routine — run a 3-step CeraVe routine of cleanser, moisturizer, and SPF every morning instead", polarity="prefer", session_introduced=2),
        ],
        current_query="I am at the bathroom counter — which products do I reach for in the morning?",
        required_behavior="Reach for CeraVe cleanser, moisturizer, and SPF.",
        invalid_behavior=["Reach for the 5-step Korean lineup"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-meeting-default-001", target_type="procedural_constraint", domain="management",
        target_description="user's meeting-default — explicitly replaces 60-min-default with 30-min-default",
        target_slot_id="meet_default::v1", topic="default_meeting_length",
        versions=[
            VersionSpec(value="default all calendar meetings to 60-minute slots when scheduling", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget the 60-minute default — default all calendar meetings to 30-minute slots when scheduling, requiring justification for anything longer", polarity="constraint", session_introduced=2),
        ],
        current_query="I am scheduling a sync with the design lead next week — what slot length do I default to?",
        required_behavior="Default to 30 minutes.",
        invalid_behavior=["Default to 60 minutes"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    # narrowing (2)
    _trip(_s(sample_id="p3-narrow-podcast-record-001", target_type="procedural_constraint", domain="media",
        target_description="user's podcast-recording rule — three explicit narrowings: any guest → invited-friends-only → invited-friends-only + with-pre-call",
        target_slot_id="pod_rec::v1", topic="podcast_recording_rule",
        versions=[
            VersionSpec(value="record podcast episodes with any guest who agrees to come on", polarity="constraint", session_introduced=1),
            VersionSpec(value="record podcast episodes only with guests the user has invited personally, never cold pitches", polarity="constraint", session_introduced=2),
            VersionSpec(value="record podcast episodes only with personally-invited guests AND only after a 15-minute pre-call to align expectations", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend just asked me on as a guest with no pre-call — record?",
        required_behavior="Pass; the rule is invited-by-user AND with a 15-min pre-call first.",
        invalid_behavior=["Record any guest", "Record any invited friend without pre-call", "Record a non-invited guest with pre-call"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-class-pick-001", target_type="procedural_constraint", domain="learning",
        target_description="user's class-attendance rule — three explicit narrowings: any → online-only → online-only + recorded-archive",
        target_slot_id="class_pick::v1", topic="continuing_education_rule",
        versions=[
            VersionSpec(value="enroll in any continuing-education class that catches the user's eye", polarity="constraint", session_introduced=1),
            VersionSpec(value="enroll only in online-format continuing-education classes, no in-person", polarity="constraint", session_introduced=2),
            VersionSpec(value="enroll only in online-format classes AND only ones that provide a recorded archive for catch-up", polarity="constraint", session_introduced=3),
        ],
        current_query="A live online seminar with no recording offered — enroll?",
        required_behavior="Pass; the rule is online AND with recorded archive.",
        invalid_behavior=["Enroll in any class", "Enroll in any online class", "Enroll in an in-person class with recordings"],
        failure_patterns=["narrowing"], subtype="multi_step")),
]
