"""Phase 3 batch AA — final push, drift + doublet only (highest accept rate)."""

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
def _doub(s): return Phase3GroupSpec(spine=s, group_type="doublet", horizons=["standard","hard"], implicit_drift_type=None, spine_source="hand")


PHASE3_BATCH_AA: list[Phase3GroupSpec] = [
    # multi_version doublet (10) — highest accept-rate cell
    _doub(_s(sample_id="p3-multi-doub-cooking-fat-001", target_type="object_preference", domain="food",
        target_description="user's cooking fat — extra-virgin-olive-oil → grass-fed-ghee",
        target_slot_id="cook_fat::v1", topic="cooking_fat",
        versions=[
            VersionSpec(value="cook savory dishes with extra-virgin olive oil from the Italian importer for the daily home cooking", polarity="prefer", session_introduced=1),
            VersionSpec(value="cook savory dishes with grass-fed ghee from the local creamery for the daily home cooking instead of olive oil", polarity="prefer", session_introduced=2),
        ],
        current_query="The pan is hot for tonight's stir-fry — what fat goes in first?",
        required_behavior="Spoon in grass-fed ghee.",
        invalid_behavior=["Pour in extra-virgin olive oil"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-bedding-001", target_type="object_preference", domain="home",
        target_description="user's bedsheet material — percale-cotton → linen-flax",
        target_slot_id="sheets::v1", topic="bedsheet_material",
        versions=[
            VersionSpec(value="sleep on percale cotton sheets year-round for the crisp feel", polarity="prefer", session_introduced=1),
            VersionSpec(value="sleep on French linen flax sheets year-round for the textured feel instead of percale cotton", polarity="prefer", session_introduced=2),
        ],
        current_query="The sheets need replacing — what material do I order?",
        required_behavior="Order French linen flax sheets.",
        invalid_behavior=["Order percale cotton sheets"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-mailclient-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's email client — Apple-Mail → Hey-from-37signals",
        target_slot_id="mail::v1", topic="email_client",
        versions=[
            VersionSpec(value="check personal email in Apple Mail on the Mac and iPhone with the unified inbox", polarity="prefer", session_introduced=1),
            VersionSpec(value="check personal email in Hey from 37signals with the screener and reply-later workflow instead of Apple Mail", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend asked which app I use for personal email — what do I tell them?",
        required_behavior="Tell them Hey from 37signals.",
        invalid_behavior=["Tell them Apple Mail"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-deck-tool-001", target_type="object_preference", domain="management",
        target_description="user's slide-deck tool — Keynote → Pitch-shared-app",
        target_slot_id="deck::v1", topic="slide_deck_tool",
        versions=[
            VersionSpec(value="build executive slide decks in Keynote on the Mac with custom templates", polarity="prefer", session_introduced=1),
            VersionSpec(value="build executive slide decks in Pitch with the shared real-time editing instead of Keynote", polarity="prefer", session_introduced=2),
        ],
        current_query="The board deck is due Friday — which app do I open to start drafting?",
        required_behavior="Open Pitch.",
        invalid_behavior=["Open Keynote"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-water-001", target_type="object_preference", domain="health",
        target_description="user's water source — bottled-spring-water → home-Berkey-filter",
        target_slot_id="water::v1", topic="drinking_water_source",
        versions=[
            VersionSpec(value="drink bottled spring water from cases ordered weekly off Amazon for daily hydration", polarity="prefer", session_introduced=1),
            VersionSpec(value="drink filtered tap water from the home Berkey gravity filter for daily hydration instead of bottled water", polarity="prefer", session_introduced=2),
        ],
        current_query="The water-cooler shelf is empty — should I add bottled water to next week's Amazon order?",
        required_behavior="No; the home Berkey filter handles drinking water now.",
        invalid_behavior=["Add bottled spring water to the Amazon order"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-cycling-time-001", target_type="procedural_constraint", domain="health",
        target_description="user's cycling-training time — early-morning-5am → after-work-6pm",
        target_slot_id="cycling_time::v1", topic="cycling_training_time",
        versions=[
            VersionSpec(value="ride the road bike at 5am every weekday morning for two-hour training rides", polarity="constraint", session_introduced=1),
            VersionSpec(value="ride the road bike at 6pm every weekday evening for two-hour training rides instead of early morning", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 4:30am Tuesday — am I getting up for the morning ride?",
        required_behavior="No; rides happen at 6pm now.",
        invalid_behavior=["Get up for the 5am morning ride"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-mealplan-001", target_type="object_preference", domain="food",
        target_description="user's meal-plan service — HelloFresh → Sakara",
        target_slot_id="mealplan::v1", topic="weekly_meal_plan_service",
        versions=[
            VersionSpec(value="receive HelloFresh meal kits delivered every Tuesday with five recipes per week", polarity="prefer", session_introduced=1),
            VersionSpec(value="receive Sakara plant-based prepared meals delivered every Tuesday with three meals per day instead of HelloFresh", polarity="prefer", session_introduced=2),
        ],
        current_query="The Tuesday delivery just arrived — which box am I unpacking?",
        required_behavior="Unpack the Sakara plant-based meals box.",
        invalid_behavior=["Unpack the HelloFresh meal-kit box"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-comm-style-001", target_type="conceptual_stance", domain="management",
        target_description="user's team-comms style — long-form-writeups → terse-bullet-summaries",
        target_slot_id="comm_style::v1", topic="team_communication_style",
        versions=[
            VersionSpec(value="communicate team decisions through long-form 600-word writeups in the team channel", polarity="prefer", session_introduced=1),
            VersionSpec(value="communicate team decisions through terse three-bullet summaries in the team channel instead of long-form writeups", polarity="prefer", session_introduced=2),
        ],
        current_query="The team needs the launch decision rationale by EOD — how do I write it up?",
        required_behavior="Three terse bullets in the team channel.",
        invalid_behavior=["Long-form 600-word writeup in the team channel"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-jacket-002", target_type="object_preference", domain="hobby",
        target_description="user's rain jacket — Patagonia-Torrentshell → Arc'teryx-Beta",
        target_slot_id="rain_jacket::v1", topic="rain_jacket_brand",
        versions=[
            VersionSpec(value="wear the Patagonia Torrentshell rain jacket as the everyday wet-weather layer", polarity="prefer", session_introduced=1),
            VersionSpec(value="wear the Arc'teryx Beta LT rain jacket as the everyday wet-weather layer instead of the Torrentshell", polarity="prefer", session_introduced=2),
        ],
        current_query="It is pouring outside and I am about to head out — which jacket goes on?",
        required_behavior="The Arc'teryx Beta LT.",
        invalid_behavior=["The Patagonia Torrentshell"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-podcast-001", target_type="object_preference", domain="hobby",
        target_description="user's go-to podcast — Tim-Ferriss-show → Acquired-podcast",
        target_slot_id="pod::v1", topic="weekly_listening_podcast",
        versions=[
            VersionSpec(value="listen to The Tim Ferriss Show as the weekly podcast for long commutes", polarity="prefer", session_introduced=1),
            VersionSpec(value="listen to Acquired as the weekly podcast for long commutes instead of Tim Ferriss", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Sunday and I am about to download a podcast for tomorrow's commute — which one?",
        required_behavior="Download the latest Acquired episode.",
        invalid_behavior=["Download the latest Tim Ferriss Show episode"],
        failure_patterns=["multi_version"], subtype="strong")),

    # implicit_drift / repeated_use (5)
    _drift(_s(sample_id="p3-drift-ru-water-001", target_type="object_preference", domain="health",
        target_description="user's daily water vessel — old plastic bottle gradually replaced by stainless flask user refills daily",
        target_slot_id="water_v::v1", topic="daily_water_vessel",
        versions=[
            VersionSpec(value="drink from disposable plastic water bottles bought from the corner store for daily hydration", polarity="prefer", session_introduced=1),
            VersionSpec(value="drink from a stainless-steel HydroFlask refilled at home for daily hydration instead of disposable bottles", polarity="prefer", session_introduced=2),
        ],
        current_query="I am heading out for the day — what do I grab for water?",
        required_behavior="Grab the stainless-steel HydroFlask from the kitchen.",
        invalid_behavior=["Buy a disposable plastic water bottle from the corner store"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-flowers-001", target_type="procedural_constraint", domain="home",
        target_description="user's home flower-buying — old weekly bouquet gradually replaced by potted-plants user waters daily",
        target_slot_id="flowers::v1", topic="home_flower_practice",
        versions=[
            VersionSpec(value="buy a fresh bouquet of cut flowers for the dining table at the Saturday farmers market every weekend", polarity="constraint", session_introduced=1),
            VersionSpec(value="keep potted houseplants on the dining table that the user waters daily, no fresh-cut bouquets", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday at the farmers market — should I pick up a bouquet for the dining table?",
        required_behavior="No; the dining table now has the daily-watered potted plants.",
        invalid_behavior=["Pick up a bouquet for the dining table"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-vendor-001", target_type="object_preference", domain="finance",
        target_description="user's expense-tracking vendor — old QuickBooks gradually replaced by Mercury-built-in user uses every workweek",
        target_slot_id="expense::v1", topic="business_expense_tracking",
        versions=[
            VersionSpec(value="track business expenses in QuickBooks Online with the bank-feed reconciliation each Friday", polarity="prefer", session_introduced=1),
            VersionSpec(value="track business expenses in Mercury's built-in expense module each Friday instead of QuickBooks", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Friday afternoon — which app am I opening for the weekly expense reconciliation?",
        required_behavior="Open Mercury's built-in expense module.",
        invalid_behavior=["Open QuickBooks Online"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-readinglist-001", target_type="object_preference", domain="learning",
        target_description="user's reading list app — old Pocket gradually replaced by Readwise-Reader user uses daily",
        target_slot_id="readlist::v1", topic="reading_list_app",
        versions=[
            VersionSpec(value="save articles to the Pocket reading-list app for later reading on the iPad", polarity="prefer", session_introduced=1),
            VersionSpec(value="save articles to the Readwise Reader app for later reading on the iPad with the highlight-export feature instead of Pocket", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend just shared a great article — where do I save it for later?",
        required_behavior="Save it to the Readwise Reader app.",
        invalid_behavior=["Save it to the Pocket app"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-feedback-001", target_type="procedural_constraint", domain="management",
        target_description="user's feedback delivery — old verbal-in-1on1 gradually replaced by written-in-shared-doc user uses every week",
        target_slot_id="fb_deliv::v1", topic="feedback_delivery_format",
        versions=[
            VersionSpec(value="deliver feedback to direct reports verbally in the weekly 1:1 conversation at the office", polarity="constraint", session_introduced=1),
            VersionSpec(value="deliver feedback to direct reports in writing in the shared 1:1 doc updated every week instead of verbally", polarity="constraint", session_introduced=2),
        ],
        current_query="A direct report is heading into the next 1:1 expecting feedback on the launch — what's my format?",
        required_behavior="Update the written feedback in the shared 1:1 doc before the meeting.",
        invalid_behavior=["Plan to deliver the feedback verbally in the 1:1"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    # implicit_drift / abandonment (3)
    _drift(_s(sample_id="p3-drift-aban-volunteer-001", target_type="procedural_constraint", domain="community",
        target_description="user's volunteer shift — abandoned after burnout, no replacement",
        target_slot_id="volunteer::v1", topic="weekly_volunteer_shift_practice",
        versions=[
            VersionSpec(value="volunteer at the homeless shelter every Saturday morning for a four-hour serving shift", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop volunteering at the homeless shelter after burnout and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I packing the apron for the shelter shift?",
        required_behavior="No; the volunteer shift has been abandoned.",
        invalid_behavior=["Pack the apron for the shelter shift"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-meditation-002", target_type="procedural_constraint", domain="health",
        target_description="user's silent retreat — abandoned after two-year cancellation, no replacement",
        target_slot_id="retreat::v1", topic="annual_silent_retreat_practice",
        versions=[
            VersionSpec(value="attend a 10-day silent vipassana retreat at the upstate center every August", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop attending the annual silent retreat after two years of pandemic cancellations and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is early August and the retreat registration just opened — am I signing up?",
        required_behavior="No; the annual silent retreat has been abandoned.",
        invalid_behavior=["Sign up for the August silent retreat"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-music-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's monthly band rehearsal — abandoned after lead guitarist moved away, no replacement",
        target_slot_id="band::v1", topic="monthly_band_rehearsal_practice",
        versions=[
            VersionSpec(value="rehearse with the four-piece indie band on the first Sunday of every month at the rented studio", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop rehearsing with the band after the lead guitarist moved cross-country and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the first Sunday of the month — am I packing the bass for rehearsal?",
        required_behavior="No; the monthly band rehearsal has been abandoned.",
        invalid_behavior=["Pack the bass for rehearsal"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # implicit_drift / gradual_narrowing (2)
    _drift(_s(sample_id="p3-drift-gn-meals-001", target_type="object_preference", domain="food",
        target_description="user's restaurant rule — gradually narrowing without announcement: any → only-walking-distance → only-walking-distance + with-vegan-menu",
        target_slot_id="meals::v1", topic="restaurant_pick_rule",
        versions=[
            VersionSpec(value="pick any restaurant the user is in the mood for on date nights", polarity="prefer", session_introduced=1),
            VersionSpec(value="pick only restaurants within walking distance of home AND only ones with a clearly marked vegan menu", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a great vegan place 20 minutes away by car — book it for date night?",
        required_behavior="Pass; user picks only walking-distance vegan-menu restaurants.",
        invalid_behavior=["Book the 20-minute-drive vegan place"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-event-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's social-event acceptance — gradually narrowing without announcement: any → only-eight-or-fewer → only-eight-or-fewer + close-friends-host",
        target_slot_id="ev::v1", topic="social_event_acceptance_rule",
        versions=[
            VersionSpec(value="accept any social event invitation that fits the user's calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept social events only with eight or fewer guests AND only when hosted by a close friend", polarity="constraint", session_introduced=2),
        ],
        current_query="A coworker invited me to a six-person dinner party at her apartment — accept?",
        required_behavior="Pass; user accepts only when host is a close friend AND ≤8 guests.",
        invalid_behavior=["Accept the coworker's six-person dinner party"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),
]
