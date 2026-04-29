"""Phase 3 batch AF — final deficit-focused push.

Strategy: most-distinctive active values, abstract current_queries that
ask about *the situation* rather than mentioning the rule's tokens."""

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


PHASE3_BATCH_AF: list[Phase3GroupSpec] = [
    # abandonment (10) — diverse topics; use uncommon practice names so leakage is low
    _drift(_s(sample_id="p3-drift-aban-zazen-001", target_type="procedural_constraint", domain="health",
        target_description="user's morning zazen sit — abandoned after teacher moved away, no replacement",
        target_slot_id="zazen::v1", topic="morning_zazen_practice",
        versions=[
            VersionSpec(value="sit forty-five minutes of zazen meditation every morning at the home altar before breakfast", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the morning zazen sit after the dharma teacher moved away and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 6am and the cushion is on the floor — what now?",
        required_behavior="Skip the cushion; the morning zazen practice is over.",
        invalid_behavior=["Sit on the cushion for forty-five minutes"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-permaculture-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's permaculture garden journal — abandoned after garden died, no replacement",
        target_slot_id="permac::v1", topic="permaculture_journal_practice",
        versions=[
            VersionSpec(value="record garden observations in the permaculture journal every Sunday afternoon with sketches and rainfall notes", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop recording in the permaculture journal after the garden died in last summer's heatwave and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday afternoon — what's the routine?",
        required_behavior="No journal entry; the practice has been abandoned.",
        invalid_behavior=["Pull out the journal for the weekly entry"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-bullet-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's bullet-journal review — abandoned after switching to digital, no replacement",
        target_slot_id="bujo::v1", topic="bullet_journal_review_practice",
        versions=[
            VersionSpec(value="run a Sunday-evening bullet journal review with a fresh weekly spread and a monthly migration", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the bullet journal Sunday review after switching to a digital system and never resume the paper practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday evening and the desk has the open notebook on it — what now?",
        required_behavior="Skip the review; the paper practice has been abandoned.",
        invalid_behavior=["Open the notebook and run the review"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-cyclo-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's cyclocross race calendar — abandoned after retiring from racing, no replacement",
        target_slot_id="cyclo::v1", topic="cyclocross_race_practice",
        versions=[
            VersionSpec(value="register for one cyclocross race every other weekend in fall season at the regional series", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop registering for cyclocross races after retiring from competitive cycling and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="A teammate forwarded the fall race calendar — what now?",
        required_behavior="No registration; the racing practice has been abandoned.",
        invalid_behavior=["Register for the next race on the calendar"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-sourdough-001", target_type="procedural_constraint", domain="food",
        target_description="user's sourdough starter — abandoned after starter died, no replacement",
        target_slot_id="sourd::v1", topic="sourdough_starter_practice",
        versions=[
            VersionSpec(value="feed the sourdough starter every twelve hours with a fifty-fifty mix of bread flour and rye", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop feeding the sourdough starter after it died from neglect during the trip and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="The kitchen timer just buzzed for the usual reminder — what now?",
        required_behavior="Ignore the timer; the starter practice has been abandoned.",
        invalid_behavior=["Feed the starter on the schedule"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-darkroom-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's darkroom prints — abandoned after switching to digital photography, no replacement",
        target_slot_id="darkroom::v1", topic="darkroom_printing_practice",
        versions=[
            VersionSpec(value="print one black-and-white darkroom photograph every Saturday afternoon at the home darkroom", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the Saturday darkroom printing after switching fully to digital workflow and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday afternoon and the safelight is on the bench — what now?",
        required_behavior="Skip the print; the darkroom practice has been abandoned.",
        invalid_behavior=["Set up trays for the weekly print"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-mahjong-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's weekly mahjong night — abandoned after group dispersed, no replacement",
        target_slot_id="mahjong::v1", topic="mahjong_night_practice",
        versions=[
            VersionSpec(value="host the Friday-evening mahjong night at the apartment with the regular four-player group", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop hosting the Friday mahjong night after the regular four-player group dispersed across cities and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Friday evening — what's the plan?",
        required_behavior="No hosting; the mahjong practice has been abandoned.",
        invalid_behavior=["Set up the mahjong table for tonight"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-paleo-001", target_type="procedural_constraint", domain="health",
        target_description="user's strict paleo eating — abandoned after physician advised reintroduction, no replacement",
        target_slot_id="paleo::v1", topic="paleo_eating_practice",
        versions=[
            VersionSpec(value="eat strictly paleo for every meal with no grains, legumes, or refined sugar", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop eating strictly paleo after the physician advised reintroducing grains and legumes and never resume the strict diet", polarity="constraint", session_introduced=2),
        ],
        current_query="A friend invited me to a pizza dinner Friday — what now?",
        required_behavior="Accept; the strict diet practice has been abandoned.",
        invalid_behavior=["Decline citing the strict diet"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-tarot-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's tarot daily card — abandoned after losing interest, no replacement",
        target_slot_id="tarot::v1", topic="tarot_daily_card_practice",
        versions=[
            VersionSpec(value="draw one tarot card every morning over coffee and journal a brief reflection on what comes up", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop drawing the daily tarot card after losing interest in the practice and never resume it", polarity="constraint", session_introduced=2),
        ],
        current_query="It is morning and the deck is on the table — what now?",
        required_behavior="Leave the deck; the practice has been abandoned.",
        invalid_behavior=["Draw the daily card and write the reflection"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-letter-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's monthly letter to grandmother — abandoned after grandmother passed, no replacement",
        target_slot_id="letter::v1", topic="monthly_letter_practice",
        versions=[
            VersionSpec(value="write a handwritten monthly letter to grandmother on the first Sunday of every month with photos enclosed", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop writing the monthly letter to grandmother after she passed away last fall and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the first Sunday of the month and the stationery is in the drawer — what now?",
        required_behavior="Leave the stationery; the practice has been abandoned.",
        invalid_behavior=["Pull out the stationery and write this month's letter"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # narrowing (5) — short distinctive active values, abstract queries
    _trip(_s(sample_id="p3-narrow-pull-investing-002", target_type="object_preference", domain="finance",
        target_description="user's brokerage rule — three explicit narrowings: any → S&P-500 → S&P-500 + with-dividends",
        target_slot_id="brk2::v1", topic="brokerage_rule",
        versions=[
            VersionSpec(value="buy any individual stock that catches the user's eye", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only S&P 500 index components for the brokerage account", polarity="prefer", session_introduced=2),
            VersionSpec(value="buy only S&P 500 index components AND only ones paying a quarterly cash distribution", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend recommended a fast-growing index name with no shareholder payouts — what now?",
        required_behavior="Pass; the rule requires regular quarterly payouts.",
        invalid_behavior=["Buy any stock", "Buy any S&P 500 stock", "Buy a non-S&P 500 payout stock"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-vacrent-001", target_type="object_preference", domain="travel",
        target_description="user's vacation-rental rule — three explicit narrowings: any → entire-place → entire-place + super-host-rated",
        target_slot_id="vacrent::v1", topic="vacation_rental_rule",
        versions=[
            VersionSpec(value="book any vacation rental that fits the dates on the listing site", polarity="constraint", session_introduced=1),
            VersionSpec(value="book only entire-place rentals, no shared rooms or private rooms", polarity="constraint", session_introduced=2),
            VersionSpec(value="book only entire-place rentals AND only ones whose host has the platform's super-host badge", polarity="constraint", session_introduced=3),
        ],
        current_query="An apartment in Lisbon for the user's dates is hosted by a regular member with no platform badge — what now?",
        required_behavior="Pass; the rule needs the host badge.",
        invalid_behavior=["Book any listing", "Book any entire-place", "Book a badged shared-room"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-grocery-002", target_type="object_preference", domain="food",
        target_description="user's market-shop rule — three explicit narrowings: any → certified-organic → certified-organic + within-walking-distance",
        target_slot_id="market::v1", topic="market_shop_rule",
        versions=[
            VersionSpec(value="shop at any grocery store that fits the user's day", polarity="prefer", session_introduced=1),
            VersionSpec(value="shop only at stores stocked with mostly certified-organic produce", polarity="prefer", session_introduced=2),
            VersionSpec(value="shop only at stores with mostly certified-organic produce AND within walking distance of home", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend recommended a great new green-label store ten miles across town — what now?",
        required_behavior="Pass; the rule requires the store be near home.",
        invalid_behavior=["Shop anywhere", "Shop at a far green store", "Shop at a nearby non-green store"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-photo-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's portfolio-image rule — three explicit narrowings: any → portrait-only → portrait-only + raw-format",
        target_slot_id="photop::v1", topic="portfolio_image_rule",
        versions=[
            VersionSpec(value="add any photo from the camera roll to the photographer's portfolio", polarity="constraint", session_introduced=1),
            VersionSpec(value="add only portrait-orientation photos to the portfolio, no landscape or square", polarity="constraint", session_introduced=2),
            VersionSpec(value="add only portrait-orientation photos AND only ones shot in raw format, no JPEGs", polarity="constraint", session_introduced=3),
        ],
        current_query="The user has a great shot from yesterday's hike on a JPEG — what now?",
        required_behavior="Pass; the rule requires raw format.",
        invalid_behavior=["Add any shot", "Add a portrait JPEG", "Add a landscape raw"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-charity-002", target_type="procedural_constraint", domain="finance",
        target_description="user's charity-give rule — three explicit narrowings: any → climate-only → climate-only + four-star-rated",
        target_slot_id="char2::v1", topic="charity_give_rule",
        versions=[
            VersionSpec(value="donate to any 501(c)(3) the user is asked to support", polarity="constraint", session_introduced=1),
            VersionSpec(value="donate only to climate-focused 501(c)(3) nonprofits, no other causes", polarity="constraint", session_introduced=2),
            VersionSpec(value="donate only to climate-focused 501(c)(3) nonprofits AND only ones rated four stars on the public watchdog site", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend asked the user to back her three-star carbon-capture nonprofit — what now?",
        required_behavior="Pass; the rule requires four-star rating.",
        invalid_behavior=["Donate to any 501(c)(3)", "Donate to any climate cause", "Donate to non-climate four-star"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi_version triple (5)
    _trip(_s(sample_id="p3-multi-trip-piano-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's piano practice format — four versions: scales-and-arpeggios → Hanon-exercises → Bach-inventions → improvise-jazz",
        target_slot_id="piano::v1", topic="piano_practice_format",
        versions=[
            VersionSpec(value="practice piano daily with thirty minutes of major-scale and arpeggio drills", polarity="constraint", session_introduced=1),
            VersionSpec(value="practice piano daily with thirty minutes of Hanon finger-strength exercises", polarity="constraint", session_introduced=2),
            VersionSpec(value="practice piano daily with thirty minutes working through Bach inventions front-to-back", polarity="constraint", session_introduced=3),
            VersionSpec(value="practice piano daily with thirty minutes of improvising over jazz lead sheets", polarity="constraint", session_introduced=4),
        ],
        current_query="It is 7pm and the user is sitting down at the bench — what is tonight's session?",
        required_behavior="Improvise over jazz lead sheets for thirty minutes.",
        invalid_behavior=["Drill major scales and arpeggios", "Drill Hanon exercises", "Work through Bach inventions"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-cardio-002", target_type="procedural_constraint", domain="health",
        target_description="user's cardio workout — four versions: zone-2-run → tempo-intervals → fasted-fifty-mile-bike → swimming-laps",
        target_slot_id="cardio::v1", topic="cardio_workout_format",
        versions=[
            VersionSpec(value="run zone-two heart-rate runs three times a week for sixty minutes each", polarity="constraint", session_introduced=1),
            VersionSpec(value="run tempo-pace interval workouts on the track three times a week for forty-five minutes each", polarity="constraint", session_introduced=2),
            VersionSpec(value="ride a fasted fifty-mile bike on Saturday morning for the long aerobic session", polarity="constraint", session_introduced=3),
            VersionSpec(value="swim sixty laps in the pool three times a week for the cardio block", polarity="constraint", session_introduced=4),
        ],
        current_query="It is Tuesday morning and the cardio slot is open — where do I head?",
        required_behavior="Head to the pool for sixty laps.",
        invalid_behavior=["Run zone-two", "Run tempo intervals", "Ride the long fasted bike"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-budget-001", target_type="procedural_constraint", domain="finance",
        target_description="user's budgeting method — four versions: zero-based-YNAB → cash-envelope → 50-30-20 → no-budget-monthly-review",
        target_slot_id="budget::v1", topic="budgeting_method",
        versions=[
            VersionSpec(value="run a zero-based YNAB budget reviewed every Sunday evening with category-by-category planning", polarity="constraint", session_introduced=1),
            VersionSpec(value="run a cash envelope system pulled from the bank every Friday afternoon for the week's discretionary spend", polarity="constraint", session_introduced=2),
            VersionSpec(value="run a 50-30-20 percentage spreadsheet budget updated monthly with the paycheck breakdown", polarity="constraint", session_introduced=3),
            VersionSpec(value="skip detailed budgeting and run only a monthly bank-statement review for outliers", polarity="constraint", session_introduced=4),
        ],
        current_query="It is Sunday evening and the laptop is open — what's the routine?",
        required_behavior="Skip the laptop; the budgeting practice is now just a monthly statement review.",
        invalid_behavior=["Run YNAB zero-based review", "Pull cash for envelopes", "Update 50-30-20 spreadsheet"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-mtg-format-001", target_type="procedural_constraint", domain="management",
        target_description="user's team-meeting format — four versions: live-zoom-talk → silent-doc-read → async-loom-video → no-meeting-just-write-up",
        target_slot_id="mtg_fmt::v1", topic="team_meeting_format",
        versions=[
            VersionSpec(value="run team meetings as live zoom calls with the team talking through the agenda points", polarity="constraint", session_introduced=1),
            VersionSpec(value="run team meetings as silent doc-reading sessions where everyone reads the prepared brief together for the first fifteen minutes", polarity="constraint", session_introduced=2),
            VersionSpec(value="run team meetings as async Loom videos the manager records and posts to the channel", polarity="constraint", session_introduced=3),
            VersionSpec(value="skip team meetings entirely; replace with a written manager update posted in the team channel each week", polarity="constraint", session_introduced=4),
        ],
        current_query="The team is asking how to handle the launch decision this week — what's the format?",
        required_behavior="Post a written update in the team channel; no meeting at all.",
        invalid_behavior=["Schedule a live zoom talk", "Schedule a silent doc-reading session", "Record an async Loom"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-laptop-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's daily laptop — four versions: MacBook-Pro-M2 → ThinkPad-X1 → Framework-13-Linux → iPad-Magic-Keyboard",
        target_slot_id="laptop::v1", topic="daily_driver_laptop",
        versions=[
            VersionSpec(value="use the MacBook Pro M2 as the daily-driver laptop for all work", polarity="prefer", session_introduced=1),
            VersionSpec(value="use the ThinkPad X1 Carbon running Windows 11 as the daily-driver laptop for all work", polarity="prefer", session_introduced=2),
            VersionSpec(value="use the Framework 13 running Arch Linux as the daily-driver laptop for all work", polarity="prefer", session_introduced=3),
            VersionSpec(value="use the iPad Pro with Magic Keyboard as the daily-driver computer for all work, no laptop", polarity="prefer", session_introduced=4),
        ],
        current_query="The user is packing for an off-site work week — which device goes in the bag?",
        required_behavior="Pack the iPad Pro with Magic Keyboard.",
        invalid_behavior=["Pack the MacBook Pro M2", "Pack the ThinkPad X1 Carbon", "Pack the Framework 13"],
        failure_patterns=["multi_version"], subtype="strong")),

    # gradual_narrowing (5) — push from 17 → 20+ to fully fill
    _drift(_s(sample_id="p3-drift-gn-restbook-001", target_type="object_preference", domain="learning",
        target_description="user's bookbuy rule — gradually narrowing without announcement: any → translated-Japanese → translated-Japanese + post-1990",
        target_slot_id="bbk::v1", topic="bookbuy_drift_rule",
        versions=[
            VersionSpec(value="buy any book the user finds compelling at the local bookshop", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only books translated from Japanese AND only those originally published after 1990", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a 1968 classic translated from Japanese — what now?",
        required_behavior="Pass; user buys only post-1990 Japanese translations.",
        invalid_behavior=["Buy the 1968 classic translation"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-fitness-001", target_type="object_preference", domain="health",
        target_description="user's fitness-class rule — gradually narrowing without announcement: any → outdoor-only → outdoor-only + with-cohort-of-five",
        target_slot_id="fclass::v1", topic="fitness_class_drift_rule",
        versions=[
            VersionSpec(value="enroll in any fitness class the user finds interesting at the gym", polarity="prefer", session_introduced=1),
            VersionSpec(value="enroll only in fitness classes held outdoors AND only ones with a small cohort of five or fewer participants", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a great new outdoor bootcamp with twenty participants — what now?",
        required_behavior="Pass; user enrolls only in outdoor classes with cohorts of five or fewer.",
        invalid_behavior=["Enroll in the twenty-person outdoor bootcamp"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-tutor-001", target_type="object_preference", domain="learning",
        target_description="user's tutor pick — gradually narrowing without announcement: any → native-speaker → native-speaker + literature-PhD",
        target_slot_id="tutor::v1", topic="language_tutor_pick_drift",
        versions=[
            VersionSpec(value="hire any language tutor the user finds on the platform", polarity="prefer", session_introduced=1),
            VersionSpec(value="hire only native-speaker tutors AND only those holding a PhD in literature of the target language", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a fluent native tutor with a journalism background — what now?",
        required_behavior="Pass; user hires only native tutors with literature PhDs.",
        invalid_behavior=["Hire the journalism-background tutor"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-podgo-001", target_type="object_preference", domain="hobby",
        target_description="user's podcast-guest acceptance — gradually narrowing without announcement: any → recorded-audio → recorded-audio + over-1M-downloads",
        target_slot_id="podg::v1", topic="podcast_guest_drift_rule",
        versions=[
            VersionSpec(value="accept any podcast guest invitation the user receives", polarity="prefer", session_introduced=1),
            VersionSpec(value="accept podcast guest invitations only when the show records audio in advance AND only when the show has over a million downloads per episode", polarity="prefer", session_introduced=2),
        ],
        current_query="A small audio-recorded show with thirty thousand downloads asked the user on as a guest — what now?",
        required_behavior="Pass; user accepts only large pre-recorded shows.",
        invalid_behavior=["Accept the small thirty-thousand-download show"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-coffee-001", target_type="object_preference", domain="food",
        target_description="user's coffee shop rule — gradually narrowing without announcement: any → independent-roaster → independent-roaster + with-public-cupping",
        target_slot_id="coff::v1", topic="coffee_shop_drift_rule",
        versions=[
            VersionSpec(value="grab coffee at any shop the user passes by", polarity="prefer", session_introduced=1),
            VersionSpec(value="grab coffee only at independent roasters AND only ones that host public cupping events on weekends", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a great new independent roaster downtown that does no public events — what now?",
        required_behavior="Pass; user goes only to independents with public cuppings.",
        invalid_behavior=["Grab coffee at the no-event independent"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),
]
