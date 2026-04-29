"""Phase 3 batch S — 25 spines biased to multi_doublet, narrowing,
gradual_narrowing, drift, communication_boundary topic, interpersonal target."""

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


PHASE3_BATCH_S: list[Phase3GroupSpec] = [
    # narrowing (5)
    _trip(_s(sample_id="p3-narrow-pr-review-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's pull-request-review rule — three explicit narrowings: any PR → with-tests → with-tests + 200-line-cap",
        target_slot_id="pr_review::v1", topic="pull_request_review_rule",
        versions=[
            VersionSpec(value="approve any pull request that arrives in the queue", polarity="constraint", session_introduced=1),
            VersionSpec(value="approve only pull requests that include automated tests for the changed code", polarity="constraint", session_introduced=2),
            VersionSpec(value="approve only pull requests that include automated tests AND keep the diff under two hundred lines", polarity="constraint", session_introduced=3),
        ],
        current_query="A teammate's PR with tests but a 400-line diff is in my review queue — approve it?",
        required_behavior="Send back for splitting; the rule is tests AND under-200-line diff.",
        invalid_behavior=["Approve any PR", "Approve on tests alone", "Approve on under-200-lines alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-vc-pitch-001", target_type="procedural_constraint", domain="business",
        target_description="user's VC-pitch acceptance rule — three explicit narrowings: any → seed-stage → seed-stage + B2B-SaaS",
        target_slot_id="vc_pitch::v1", topic="vc_pitch_acceptance_rule",
        versions=[
            VersionSpec(value="take a meeting with any founder who pitches the user as a check writer", polarity="constraint", session_introduced=1),
            VersionSpec(value="take meetings only with founders raising at the seed stage", polarity="constraint", session_introduced=2),
            VersionSpec(value="take meetings only with founders raising at the seed stage AND building B2B SaaS products", polarity="constraint", session_introduced=3),
        ],
        current_query="A consumer-app seed-stage founder asked for a meeting via cold email — accept?",
        required_behavior="Pass; the rule is seed-stage AND B2B SaaS.",
        invalid_behavior=["Take any pitch", "Take any seed-stage pitch", "Take a non-seed B2B SaaS pitch"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-coffee-shop-work-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's remote-work-spot rule — three explicit narrowings: any cafe → coffee-shop-only → coffee-shop-only + walking-distance-from-home",
        target_slot_id="work_spot::v1", topic="remote_work_spot_rule",
        versions=[
            VersionSpec(value="work remotely from any indoor venue with wifi for the day", polarity="constraint", session_introduced=1),
            VersionSpec(value="work remotely only from coffee shops, never restaurants or libraries", polarity="constraint", session_introduced=2),
            VersionSpec(value="work remotely only from coffee shops within walking distance of home", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend invited me to work from a coffee shop ten miles across town — go?",
        required_behavior="Pass; the rule is coffee shops AND within walking distance of home.",
        invalid_behavior=["Work from any wifi venue", "Work from any coffee shop", "Work from a non-coffee venue nearby"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-restaurant-reserve-001", target_type="procedural_constraint", domain="food",
        target_description="user's date-night-reservation rule — three explicit narrowings: any restaurant → tasting-menu → tasting-menu + reservation-2-weeks-ahead",
        target_slot_id="date_reserve::v1", topic="date_night_reservation_rule",
        versions=[
            VersionSpec(value="book any restaurant the user finds interesting for date night", polarity="constraint", session_introduced=1),
            VersionSpec(value="book only restaurants offering a chef's tasting menu for date night", polarity="constraint", session_introduced=2),
            VersionSpec(value="book only tasting-menu restaurants where reservations open at least two weeks ahead", polarity="constraint", session_introduced=3),
        ],
        current_query="A new tasting-menu restaurant just opened reservations one week out for next Friday — book?",
        required_behavior="Pass; the rule is tasting-menu AND reservations at least two weeks ahead.",
        invalid_behavior=["Book any interesting restaurant", "Book any tasting-menu place", "Book a reservation under two weeks"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-class-attend-001", target_type="procedural_constraint", domain="learning",
        target_description="user's continuing-education rule — three explicit narrowings: any course → in-person → in-person + cohort-of-10-or-fewer",
        target_slot_id="class_attend::v1", topic="continuing_education_rule",
        versions=[
            VersionSpec(value="enroll in any continuing education course that catches the user's eye", polarity="constraint", session_introduced=1),
            VersionSpec(value="enroll only in continuing education courses taught in person, never online", polarity="constraint", session_introduced=2),
            VersionSpec(value="enroll only in in-person continuing education courses with cohorts of ten or fewer students", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend recommended an in-person photography class with 25 enrolled students — enroll?",
        required_behavior="Pass; the rule is in-person AND cohorts of ten or fewer.",
        invalid_behavior=["Enroll in any interesting course", "Enroll in any in-person course", "Enroll in an online course of ten students"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi_version doublet (8)
    _doub(_s(sample_id="p3-multi-doub-shoe-brand-001", target_type="object_preference", domain="hobby",
        target_description="user's everyday sneaker — Allbirds → New-Balance-990",
        target_slot_id="shoe::v1", topic="everyday_sneaker",
        versions=[
            VersionSpec(value="wear Allbirds Tree Runners as the everyday sneaker on weekdays", polarity="prefer", session_introduced=1),
            VersionSpec(value="wear New Balance 990v6 as the everyday sneaker on weekdays instead", polarity="prefer", session_introduced=2),
        ],
        current_query="I am about to head out the door — which sneakers do I lace up?",
        required_behavior="Lace up the New Balance 990v6.",
        invalid_behavior=["Lace up the Allbirds Tree Runners"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-grocery-deliver-001", target_type="object_preference", domain="food",
        target_description="user's grocery-delivery service — Instacart → Whole-Foods-direct",
        target_slot_id="grocery_deliver::v1", topic="grocery_delivery_service",
        versions=[
            VersionSpec(value="order weekly groceries through the Instacart app from local stores", polarity="prefer", session_introduced=1),
            VersionSpec(value="order weekly groceries directly through the Whole Foods online delivery instead of Instacart", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Saturday and the grocery list is ready — which app do I open to place the order?",
        required_behavior="Open the Whole Foods online delivery.",
        invalid_behavior=["Open the Instacart app"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-task-cap-001", target_type="procedural_constraint", domain="management",
        target_description="user's daily-task cap — top-3-per-day → unlimited-with-end-of-day-review",
        target_slot_id="task_cap::v1", topic="daily_task_cap",
        versions=[
            VersionSpec(value="commit to the top three tasks each day and ignore everything else until tomorrow", polarity="constraint", session_introduced=1),
            VersionSpec(value="commit to as many tasks as the day permits and run an end-of-day review to clear what slipped", polarity="constraint", session_introduced=2),
        ],
        current_query="It is morning, and my todo list has eight items — do I cut down to three?",
        required_behavior="No cap; work through what the day permits and clear leftovers in the end-of-day review.",
        invalid_behavior=["Cut the list down to the top three"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-essay-platform-001", target_type="object_preference", domain="writing",
        target_description="user's essay platform — Medium → personal-Hugo-site",
        target_slot_id="essay_platform::v1", topic="essay_publishing_platform",
        versions=[
            VersionSpec(value="publish essays on Medium under the user's profile for the built-in audience", polarity="prefer", session_introduced=1),
            VersionSpec(value="publish essays on a personal Hugo site at the user's own domain instead of Medium", polarity="prefer", session_introduced=2),
        ],
        current_query="I just finished a draft essay — where do I push it when I am ready to publish?",
        required_behavior="Push it to the personal Hugo site at the user's own domain.",
        invalid_behavior=["Push it to Medium"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-laptop-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's daily-driver laptop — MacBook-Pro → Framework-13",
        target_slot_id="laptop::v1", topic="daily_driver_laptop",
        versions=[
            VersionSpec(value="use the MacBook Pro M2 as the daily-driver laptop for all work", polarity="prefer", session_introduced=1),
            VersionSpec(value="use the Framework 13 running Linux as the daily-driver laptop for all work instead of the MacBook", polarity="prefer", session_introduced=2),
        ],
        current_query="I am packing my bag for an off-site work day — which laptop goes in?",
        required_behavior="Pack the Framework 13.",
        invalid_behavior=["Pack the MacBook Pro M2"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-savings-rate-001", target_type="procedural_constraint", domain="finance",
        target_description="user's savings rule — 20-percent-of-paycheck → fixed-2000-per-month",
        target_slot_id="savings_rule::v1", topic="monthly_savings_rule",
        versions=[
            VersionSpec(value="save twenty percent of every paycheck into the brokerage account", polarity="constraint", session_introduced=1),
            VersionSpec(value="save a fixed two thousand dollars per month into the brokerage account, regardless of paycheck size", polarity="constraint", session_introduced=2),
        ],
        current_query="My paycheck just landed — how much do I transfer to the brokerage?",
        required_behavior="Transfer the fixed two thousand dollars for the month.",
        invalid_behavior=["Transfer twenty percent of the paycheck"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-friend-checkin-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's check-in rule with close friends — weekly-phone-call → monthly-long-form-letter",
        target_slot_id="friend_checkin::v1", topic="close_friend_checkin_rule",
        versions=[
            VersionSpec(value="call each close friend every week for a thirty-minute phone catch-up", polarity="constraint", session_introduced=1),
            VersionSpec(value="write each close friend a monthly long-form letter instead of weekly phone calls", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday evening — should I call my close friend for the weekly catch-up?",
        required_behavior="No call; check-ins are now a monthly long-form letter.",
        invalid_behavior=["Call the close friend for a weekly catch-up"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-photo-share-001", target_type="procedural_constraint", domain="relationships",
        target_description="user's photo-sharing channel with family — group-iMessage-thread → private-Immich-album-link",
        target_slot_id="photo_share::v1", topic="family_photo_sharing_channel",
        versions=[
            VersionSpec(value="share family photos in the group iMessage thread that includes parents and siblings", polarity="constraint", session_introduced=1),
            VersionSpec(value="share family photos by sending a private Immich album link to parents and siblings instead of iMessage", polarity="constraint", session_introduced=2),
        ],
        current_query="I just took photos at a family dinner — where do I post them for parents and siblings?",
        required_behavior="Send the private Immich album link.",
        invalid_behavior=["Post in the group iMessage thread"],
        failure_patterns=["multi_version"], subtype="strong")),

    # multi_version triple (3)
    _trip(_s(sample_id="p3-multi-trip-cardio-001", target_type="procedural_constraint", domain="health",
        target_description="user's cardio workout — four versions: long-easy-runs → tempo-intervals → spin-bike-classes → HIIT-rowing",
        target_slot_id="cardio::v1", topic="cardio_workout_choice",
        versions=[
            VersionSpec(value="run long easy six-mile runs three times a week for cardio", polarity="constraint", session_introduced=1),
            VersionSpec(value="run tempo interval workouts on the track three times a week for cardio", polarity="constraint", session_introduced=2),
            VersionSpec(value="take spin bike classes at the gym three times a week for cardio", polarity="constraint", session_introduced=3),
            VersionSpec(value="row HIIT intervals on the home rowing machine three times a week for cardio", polarity="constraint", session_introduced=4),
        ],
        current_query="It is Tuesday — what is the cardio workout for tonight?",
        required_behavior="Row HIIT intervals on the home rowing machine.",
        invalid_behavior=["Run a long easy six-miler", "Run tempo intervals on the track", "Take a spin bike class"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-language-001", target_type="object_preference", domain="learning",
        target_description="user's primary foreign language — four versions: Mandarin → Japanese → German → Korean",
        target_slot_id="lang::v1", topic="primary_foreign_language",
        versions=[
            VersionSpec(value="study Mandarin Chinese as the primary foreign language with the daily tutor", polarity="prefer", session_introduced=1),
            VersionSpec(value="study Japanese as the primary foreign language with the daily tutor instead", polarity="prefer", session_introduced=2),
            VersionSpec(value="study German as the primary foreign language with the daily tutor instead", polarity="prefer", session_introduced=3),
            VersionSpec(value="study Korean as the primary foreign language with the daily tutor instead", polarity="prefer", session_introduced=4),
        ],
        current_query="The tutor asked which language we are working on this week — what do I tell them?",
        required_behavior="Tell them Korean.",
        invalid_behavior=["Tell them Mandarin", "Tell them Japanese", "Tell them German"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-skin-care-001", target_type="procedural_constraint", domain="health",
        target_description="user's skin-care routine — four versions: 3-step-CeraVe → 5-step-Korean → barrier-only-La-Roche-Posay → minimalist-Vaseline-only",
        target_slot_id="skin::v1", topic="skin_care_routine",
        versions=[
            VersionSpec(value="run a three-step CeraVe routine of cleanser, moisturizer, and SPF every morning", polarity="constraint", session_introduced=1),
            VersionSpec(value="run a five-step Korean routine of cleanser, toner, essence, serum, and SPF every morning", polarity="constraint", session_introduced=2),
            VersionSpec(value="run a barrier-only La Roche Posay routine of just gentle cleanser plus barrier cream every morning", polarity="constraint", session_introduced=3),
            VersionSpec(value="run a minimalist Vaseline-slugging routine of just water rinse plus Vaseline every morning", polarity="constraint", session_introduced=4),
        ],
        current_query="I am at the bathroom counter ready for the morning routine — which products do I reach for?",
        required_behavior="Reach for water rinse plus Vaseline only.",
        invalid_behavior=["Reach for the three-step CeraVe", "Reach for the five-step Korean", "Reach for the La Roche Posay barrier routine"],
        failure_patterns=["multi_version"], subtype="strong")),

    # explicit_replacement (3)
    _trip(_s(sample_id="p3-explicit-yoga-style-001", target_type="object_preference", domain="health",
        target_description="user's yoga style — explicitly replaces vinyasa-flow with yin-yoga",
        target_slot_id="yoga::v1", topic="yoga_style",
        versions=[
            VersionSpec(value="practice vinyasa flow yoga at the studio every Saturday morning", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget vinyasa flow — practice yin yoga at the studio every Saturday morning", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Saturday morning — which class do I sign up for at the studio?",
        required_behavior="Sign up for the yin yoga class.",
        invalid_behavior=["Sign up for the vinyasa flow class"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-grocery-list-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's grocery-list app — explicitly replaces Notes-app with AnyList",
        target_slot_id="grocery_list::v1", topic="grocery_list_app",
        versions=[
            VersionSpec(value="track the weekly grocery list in the iPhone Notes app for quick access", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the iPhone Notes app — track the weekly grocery list in AnyList for shared editing with the partner", polarity="prefer", session_introduced=2),
        ],
        current_query="I want to add eggs to the grocery list — where do I open?",
        required_behavior="Open AnyList to add eggs.",
        invalid_behavior=["Open the iPhone Notes app to add eggs"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-meeting-cap-001", target_type="procedural_constraint", domain="management",
        target_description="user's daily-meeting cap — explicitly replaces six-meetings with three-meetings",
        target_slot_id="meet_cap::v1", topic="daily_meeting_cap",
        versions=[
            VersionSpec(value="cap the daily calendar at six meetings to leave a few hours for deep work", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget the six-meeting cap — cap the daily calendar at three meetings to leave the rest for deep work", polarity="constraint", session_introduced=2),
        ],
        current_query="My EA wants to add a fourth meeting to tomorrow's calendar — accept it?",
        required_behavior="Decline; the daily cap is three meetings now.",
        invalid_behavior=["Accept the fourth meeting because the cap is six"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    # implicit_drift / repeated_use (3)
    _drift(_s(sample_id="p3-drift-ru-haircut-001", target_type="procedural_constraint", domain="health",
        target_description="user's haircut place — old neighborhood barbershop gradually replaced by salon-across-town the user goes to monthly",
        target_slot_id="haircut::v1", topic="monthly_haircut_place",
        versions=[
            VersionSpec(value="get a monthly haircut at the neighborhood barbershop two blocks from home", polarity="constraint", session_introduced=1),
            VersionSpec(value="get a monthly haircut at the salon across town with a specific stylist by appointment", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the first Saturday of the month — am I walking to the neighborhood barbershop?",
        required_behavior="No; the haircut appointment is at the salon across town now.",
        invalid_behavior=["Walk to the neighborhood barbershop"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-mealkit-001", target_type="object_preference", domain="food",
        target_description="user's weekly dinner — old HelloFresh meal kits gradually replaced by Sunday batch-cook-from-scratch user does every week",
        target_slot_id="mealkit::v1", topic="weekly_dinner_source",
        versions=[
            VersionSpec(value="cook weekday dinners from HelloFresh meal kits delivered every Tuesday", polarity="prefer", session_introduced=1),
            VersionSpec(value="cook weekday dinners from a Sunday batch-cook-from-scratch session that fills five containers in the fridge", polarity="prefer", session_introduced=2),
        ],
        current_query="HelloFresh just emailed about pausing my next delivery — should I pause it for one week or many?",
        required_behavior="Pause it indefinitely; weekday dinners come from the Sunday batch-cook now.",
        invalid_behavior=["Pause it for one week only"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-laundry-001", target_type="procedural_constraint", domain="home",
        target_description="user's laundry day — old Saturday-morning gradually replaced by Wednesday-evening user does every week",
        target_slot_id="laundry::v1", topic="weekly_laundry_day",
        versions=[
            VersionSpec(value="run the weekly laundry every Saturday morning at the in-building machines", polarity="constraint", session_introduced=1),
            VersionSpec(value="run the weekly laundry every Wednesday evening at the in-building machines after work", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I heading down with the laundry basket?",
        required_behavior="No; laundry day is Wednesday evening now.",
        invalid_behavior=["Head down with the laundry basket on Saturday morning"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    # implicit_drift / abandonment (1)
    _drift(_s(sample_id="p3-drift-aban-podcast-prod-001", target_type="procedural_constraint", domain="media",
        target_description="user's biweekly interview podcast — abandoned after sponsor-loss session, no replacement",
        target_slot_id="pod_prod::v1", topic="biweekly_interview_podcast_practice",
        versions=[
            VersionSpec(value="record a biweekly interview podcast every other Tuesday and publish on Friday", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop recording the biweekly interview podcast after losing the sponsor and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Tuesday and the recording slot is on the calendar — am I recording today?",
        required_behavior="No; the biweekly interview podcast has been abandoned.",
        invalid_behavior=["Record today's biweekly interview"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # implicit_drift / gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-gn-friends-time-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's friend-meetup rule — gradually narrowing without announcement: any friend → close-circle-only → close-circle + within-30-min-travel",
        target_slot_id="friend_meet::v1", topic="friend_meetup_rule",
        versions=[
            VersionSpec(value="meet up with any friend who suggests grabbing dinner or coffee", polarity="constraint", session_introduced=1),
            VersionSpec(value="meet up only with the user's close inner circle of five people AND only when the venue is within thirty minutes of travel", polarity="constraint", session_introduced=2),
        ],
        current_query="A college acquaintance who lives downtown invited me to dinner this Saturday — go?",
        required_behavior="Pass; the user meets only with the close inner circle within thirty minutes of travel.",
        invalid_behavior=["Go to dinner with the college acquaintance"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),
]
