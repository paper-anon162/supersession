"""Phase 3 batch Y — 25 spines, drift + doublet heavy."""

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


PHASE3_BATCH_Y: list[Phase3GroupSpec] = [
    # multi_version doublet (8)
    _doub(_s(sample_id="p3-multi-doub-bread-source-001", target_type="object_preference", domain="food",
        target_description="user's bread source — supermarket-store-brand → neighborhood-bakery-sourdough",
        target_slot_id="bread::v1", topic="weekly_bread_source",
        versions=[
            VersionSpec(value="buy weekly bread as the supermarket store-brand sliced loaf", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy weekly bread as the neighborhood bakery's sourdough boule, picked up Saturday morning", polarity="prefer", session_introduced=2),
        ],
        current_query="The bread shelf is empty — what do I add to the grocery list?",
        required_behavior="Plan a Saturday-morning pickup of the neighborhood bakery sourdough.",
        invalid_behavior=["Add the supermarket store-brand sliced loaf"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-vacation-pace-001", target_type="procedural_constraint", domain="travel",
        target_description="user's vacation pace — three-cities-in-ten-days → one-city-with-day-trips",
        target_slot_id="vac_pace::v1", topic="vacation_itinerary_pace",
        versions=[
            VersionSpec(value="plan a ten-day vacation hitting three different European cities with two flights between them", polarity="constraint", session_introduced=1),
            VersionSpec(value="plan a ten-day vacation staying in one base city the whole time with day trips by train instead of multi-city flights", polarity="constraint", session_introduced=2),
        ],
        current_query="I am drafting next month's Italy itinerary — should I split between Rome, Florence, and Venice?",
        required_behavior="No; pick one base city and run day trips by train.",
        invalid_behavior=["Split between Rome, Florence, and Venice"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-hair-cut-001", target_type="procedural_constraint", domain="health",
        target_description="user's haircut cadence — every-three-weeks → every-eight-weeks",
        target_slot_id="haircut::v1", topic="haircut_cadence",
        versions=[
            VersionSpec(value="get a haircut at the salon every three weeks to keep the close-cropped fade tidy", polarity="constraint", session_introduced=1),
            VersionSpec(value="get a haircut at the salon every eight weeks to grow the hair longer instead of the close fade", polarity="constraint", session_introduced=2),
        ],
        current_query="It has been three weeks since my last cut — am I booking another?",
        required_behavior="No; the salon visit is now every eight weeks.",
        invalid_behavior=["Book a haircut at three weeks"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-savings-buck-001", target_type="object_preference", domain="finance",
        target_description="user's emergency savings vehicle — high-yield-savings → 3-month-T-Bills",
        target_slot_id="emerg::v1", topic="emergency_savings_vehicle",
        versions=[
            VersionSpec(value="park emergency cash in the Marcus high-yield savings account for instant access", polarity="prefer", session_introduced=1),
            VersionSpec(value="park emergency cash in rolling three-month US Treasury bills bought through Treasury Direct instead of the savings account", polarity="prefer", session_introduced=2),
        ],
        current_query="The next paycheck just landed — where do I move the emergency cash portion?",
        required_behavior="Buy a three-month US Treasury bill on Treasury Direct.",
        invalid_behavior=["Move it to the Marcus high-yield savings account"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-mentor-001", target_type="interpersonal_boundary", domain="career",
        target_description="user's mentorship pattern — one-monthly-mentor → quarterly-rotating-mentors",
        target_slot_id="mentor::v1", topic="mentorship_pattern",
        versions=[
            VersionSpec(value="meet the same one mentor every month for an hour-long career conversation", polarity="constraint", session_introduced=1),
            VersionSpec(value="meet a different mentor each quarter, rotating through three peers in the network instead of the one monthly mentor", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the start of the quarter — who do I email for the next mentorship session?",
        required_behavior="Email the next peer in the rotating quarterly schedule.",
        invalid_behavior=["Email the same monthly mentor as before"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-club-001", target_type="object_preference", domain="hobby",
        target_description="user's recurring sports club — pickleball → squash",
        target_slot_id="club::v1", topic="weekly_sports_club",
        versions=[
            VersionSpec(value="play pickleball every Wednesday evening at the local rec center with the regular group", polarity="prefer", session_introduced=1),
            VersionSpec(value="play squash every Wednesday evening at the downtown squash club instead of pickleball", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Wednesday evening — which gear bag do I grab?",
        required_behavior="Grab the squash gear bag.",
        invalid_behavior=["Grab the pickleball gear bag"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-blog-format-001", target_type="object_preference", domain="writing",
        target_description="user's blog format — long-essay → bullet-thread-recap",
        target_slot_id="blog_fmt::v1", topic="blog_writing_format",
        versions=[
            VersionSpec(value="publish blog posts as long-form 2000-word essays with sub-headings", polarity="prefer", session_introduced=1),
            VersionSpec(value="publish blog posts as numbered bullet-list recaps of about 600 words instead of long-form essays", polarity="prefer", session_introduced=2),
        ],
        current_query="I drafted a 2000-word essay on remote work — publish as is?",
        required_behavior="No; convert it to a numbered bullet-list recap of about 600 words first.",
        invalid_behavior=["Publish the 2000-word essay as is"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-keyboard-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's daily keyboard — Apple-Magic → split-ergonomic-Moonlander",
        target_slot_id="keyboard::v1", topic="daily_keyboard",
        versions=[
            VersionSpec(value="type all daily code on the Apple Magic Keyboard with the standard layout", polarity="prefer", session_introduced=1),
            VersionSpec(value="type all daily code on the split ZSA Moonlander ergonomic keyboard with a Colemak layout instead of Apple Magic", polarity="prefer", session_introduced=2),
        ],
        current_query="I am setting up the desk for the day — which keyboard plugs in?",
        required_behavior="Plug in the Moonlander split keyboard.",
        invalid_behavior=["Plug in the Apple Magic Keyboard"],
        failure_patterns=["multi_version"], subtype="strong")),

    # implicit_drift / repeated_use (4)
    _drift(_s(sample_id="p3-drift-ru-grocer-source-001", target_type="object_preference", domain="food",
        target_description="user's grocery destination — old big-box gradually replaced by Saturday farmers market user goes weekly",
        target_slot_id="grocer::v1", topic="weekly_grocery_destination",
        versions=[
            VersionSpec(value="do the weekly grocery shop at the big-box supermarket on Saturdays", polarity="prefer", session_introduced=1),
            VersionSpec(value="do the weekly grocery shop at the Saturday farmers market in the town square instead of the big-box supermarket", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I driving to the big-box supermarket?",
        required_behavior="No; walk to the Saturday farmers market.",
        invalid_behavior=["Drive to the big-box supermarket"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-evening-walk-001", target_type="procedural_constraint", domain="health",
        target_description="user's evening exercise — old indoor treadmill gradually replaced by outdoor neighborhood walk user does daily",
        target_slot_id="eve_exer::v1", topic="evening_exercise_routine",
        versions=[
            VersionSpec(value="walk thirty minutes on the indoor treadmill in the basement after dinner every evening", polarity="constraint", session_introduced=1),
            VersionSpec(value="walk thirty minutes outdoors around the neighborhood after dinner every evening instead of the indoor treadmill", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 8pm after dinner — am I heading down to the basement for the treadmill?",
        required_behavior="No; head outside for the neighborhood walk.",
        invalid_behavior=["Head down to the basement for the treadmill"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-codingfont-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's coding font — old Menlo gradually replaced by Berkeley Mono user uses daily",
        target_slot_id="font::v1", topic="coding_font",
        versions=[
            VersionSpec(value="use Menlo at 14pt as the coding font in the editor and terminal", polarity="prefer", session_introduced=1),
            VersionSpec(value="use Berkeley Mono at 13pt as the coding font in the editor and terminal instead of Menlo", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend asked which monospace font I am using these days — what do I tell them?",
        required_behavior="Tell them Berkeley Mono at 13pt.",
        invalid_behavior=["Tell them Menlo at 14pt"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-1on1-loc-001", target_type="procedural_constraint", domain="management",
        target_description="user's 1:1 location with reports — old conference-room gradually replaced by coffee-shop-walks user does weekly",
        target_slot_id="1on1_loc::v1", topic="one_on_one_location",
        versions=[
            VersionSpec(value="hold weekly 1:1 conversations in the booked conference room on the office's third floor", polarity="constraint", session_introduced=1),
            VersionSpec(value="hold weekly 1:1 conversations on a walking coffee chat to the cafe down the street from the office instead of the conference room", polarity="constraint", session_introduced=2),
        ],
        current_query="My next 1:1 with a direct report is in twenty minutes — do I head to the conference room?",
        required_behavior="No; grab a coat and walk to the cafe down the street.",
        invalid_behavior=["Head to the third-floor conference room"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    # implicit_drift / abandonment (3)
    _drift(_s(sample_id="p3-drift-aban-painting-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's weekend painting practice — abandoned after move to smaller apartment, no replacement",
        target_slot_id="paint::v1", topic="weekend_painting_practice",
        versions=[
            VersionSpec(value="paint with oils on stretched canvas every Saturday afternoon in the studio at home", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop weekend painting after moving to the smaller apartment with no studio space and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday afternoon — am I pulling out the oils and canvas for the weekend painting session?",
        required_behavior="No; the weekend painting practice has been abandoned.",
        invalid_behavior=["Pull out the oils and canvas"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-language-class-001", target_type="procedural_constraint", domain="learning",
        target_description="user's evening language class — abandoned after schedule conflict, no replacement",
        target_slot_id="lang_class::v1", topic="evening_language_class_practice",
        versions=[
            VersionSpec(value="attend the Tuesday-evening German class at the community center every week", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop attending the Tuesday-evening German class after the schedule conflict with the new evening commitment and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Tuesday evening — am I packing the German textbook for class?",
        required_behavior="No; the evening German class has been abandoned.",
        invalid_behavior=["Pack the German textbook for class"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-board-001", target_type="procedural_constraint", domain="community",
        target_description="user's nonprofit board service — abandoned after term limits, no replacement",
        target_slot_id="board::v1", topic="nonprofit_board_service",
        versions=[
            VersionSpec(value="serve on the local literacy nonprofit's board with monthly board meetings on the first Thursday", polarity="constraint", session_introduced=1),
            VersionSpec(value="rotate off the literacy nonprofit's board at the end of the term and never join another board, abandoning the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the first Thursday of the month — am I joining the board zoom?",
        required_behavior="No; the nonprofit board service has been abandoned.",
        invalid_behavior=["Join the board zoom"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # implicit_drift / gradual_narrowing (3)
    _drift(_s(sample_id="p3-drift-gn-restaurant-002", target_type="object_preference", domain="food",
        target_description="user's restaurant rule — gradually narrowing without announcement: any cuisine → only-tasting-menus → only-tasting-menus + reservations-only",
        target_slot_id="rest::v1", topic="restaurant_pick_criteria",
        versions=[
            VersionSpec(value="pick any restaurant the user is in the mood for on date nights", polarity="prefer", session_introduced=1),
            VersionSpec(value="pick only restaurants that offer a chef's tasting menu AND only ones that require reservations made ahead", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a great walk-in tasting-menu place for tonight — book it?",
        required_behavior="Pass; user picks only tasting-menu restaurants that require reservations made ahead.",
        invalid_behavior=["Walk in to the walk-in tasting-menu place tonight"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-purchase-002", target_type="object_preference", domain="finance",
        target_description="user's purchase rule — gradually narrowing without announcement: any item → only-needed-replacements → only-needed-replacements + bought-secondhand",
        target_slot_id="purch::v1", topic="discretionary_purchase_rule",
        versions=[
            VersionSpec(value="buy any discretionary item the user feels like making space for", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only items that replace something already broken or worn out AND only ones bought secondhand from eBay or thrift stores", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a brand-new electric kettle to replace my broken one — buy it?",
        required_behavior="Pass; user buys only secondhand replacement items.",
        invalid_behavior=["Buy the brand-new electric kettle"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-talk-002", target_type="procedural_constraint", domain="career",
        target_description="user's conference-talk acceptance — gradually narrowing without announcement: any → only-keynotes → only-keynotes + at-in-person-events",
        target_slot_id="talk::v1", topic="conference_talk_acceptance",
        versions=[
            VersionSpec(value="accept any conference talk invitation that fits the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept conference talk invitations only when the slot is a keynote AND only when the conference is held in person, no virtual events", polarity="constraint", session_introduced=2),
        ],
        current_query="A virtual conference offered me a keynote slot next quarter — accept?",
        required_behavior="Pass; user accepts only in-person keynote slots.",
        invalid_behavior=["Accept the virtual keynote"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    # explicit_replacement (5)
    _trip(_s(sample_id="p3-explicit-bookbuy-001", target_type="object_preference", domain="learning",
        target_description="user's book-buying channel — explicitly replaces Amazon-Kindle with Bookshop-org-paperbacks",
        target_slot_id="bookbuy::v1", topic="book_buying_channel",
        versions=[
            VersionSpec(value="buy all books as Kindle ebooks through the Amazon Kindle store for instant download", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget Kindle and Amazon — buy all books as paperbacks through Bookshop.org to support independent bookstores instead", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a new biography I want to read this weekend — where do I order it?",
        required_behavior="Order the paperback through Bookshop.org.",
        invalid_behavior=["Order the Kindle ebook through Amazon"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-mtg-tone-001", target_type="conceptual_stance", domain="management",
        target_description="user's meeting tone — explicitly replaces formal-with-prepared-agenda with casual-discussion",
        target_slot_id="mtg_tone::v1", topic="meeting_tone",
        versions=[
            VersionSpec(value="run team meetings as formal sessions with a prepared written agenda circulated 24 hours ahead", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the formal-agenda format — run team meetings as casual discussions with a single high-level question on a whiteboard instead", polarity="prefer", session_introduced=2),
        ],
        current_query="Tomorrow's team meeting is on my calendar — should I draft the formal agenda tonight?",
        required_behavior="No; just pick a single high-level question to put on the whiteboard tomorrow.",
        invalid_behavior=["Draft the formal agenda tonight"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-deploy-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's deploy approval — explicitly replaces solo-approval with peer-pair-approval",
        target_slot_id="deploy_approval::v1", topic="production_deploy_approval",
        versions=[
            VersionSpec(value="approve production deploys solo as the engineering lead any time the CI is green", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget solo approvals — require a peer pair-approval from two engineers on every production deploy regardless of CI status instead", polarity="constraint", session_introduced=2),
        ],
        current_query="A teammate's PR just hit green CI — can I approve and deploy it?",
        required_behavior="No solo approval; need a second engineer to pair-approve before deploy.",
        invalid_behavior=["Approve and deploy solo"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-restaurant-001", target_type="object_preference", domain="food",
        target_description="user's friday dinner spot — explicitly replaces the-italian-place with the-thai-place",
        target_slot_id="fri_din::v1", topic="friday_dinner_spot",
        versions=[
            VersionSpec(value="have Friday dinner at the local Italian place on the corner with the regular pasta order", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the Italian place — have Friday dinner at the new Thai restaurant two blocks over with their pad-see-ew instead", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Friday evening — where do I walk for dinner?",
        required_behavior="Walk to the Thai restaurant two blocks over for pad-see-ew.",
        invalid_behavior=["Walk to the Italian place on the corner"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-sleeptracker-001", target_type="object_preference", domain="health",
        target_description="user's sleep-tracking — explicitly replaces Oura-Ring with Eight-Sleep-mattress",
        target_slot_id="sleep_track::v1", topic="sleep_tracking_device",
        versions=[
            VersionSpec(value="track nightly sleep with the Oura Ring on the user's finger", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the Oura Ring — track nightly sleep with the Eight Sleep mattress sensor instead", polarity="prefer", session_introduced=2),
        ],
        current_query="I want to check last night's sleep score — which app do I open?",
        required_behavior="Open the Eight Sleep app.",
        invalid_behavior=["Open the Oura Ring app"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    # narrowing (2)
    _trip(_s(sample_id="p3-narrow-friend-loan-001", target_type="interpersonal_boundary", domain="finance",
        target_description="user's friend-loan rule — three explicit narrowings: any → close-friends → close-friends + under-200",
        target_slot_id="loan::v1", topic="friend_loan_rule",
        versions=[
            VersionSpec(value="lend money to any friend who asks for it", polarity="constraint", session_introduced=1),
            VersionSpec(value="lend money only to close friends in the user's inner circle of five", polarity="constraint", session_introduced=2),
            VersionSpec(value="lend money only to close inner-circle friends AND only in amounts under two hundred dollars", polarity="constraint", session_introduced=3),
        ],
        current_query="A close-circle friend just asked to borrow 500 dollars — agree?",
        required_behavior="Pass; the rule is close friends AND under 200 dollars.",
        invalid_behavior=["Lend to any friend", "Lend any amount to close friend", "Lend under-200 to non-close friend"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-cocktail-002", target_type="object_preference", domain="food",
        target_description="user's home-bar drink rule — three explicit narrowings: any → spirit-forward → spirit-forward + with-citrus",
        target_slot_id="cocktail::v1", topic="home_bar_cocktail_rule",
        versions=[
            VersionSpec(value="mix any cocktail the user feels like making at the home bar after dinner", polarity="prefer", session_introduced=1),
            VersionSpec(value="mix only spirit-forward cocktails like an old fashioned or martini at the home bar after dinner", polarity="prefer", session_introduced=2),
            VersionSpec(value="mix only spirit-forward cocktails AND only ones that include a fresh citrus garnish", polarity="prefer", session_introduced=3),
        ],
        current_query="The freezer has a chilled martini glass and no citrus — should I make a martini tonight?",
        required_behavior="Pass; the rule is spirit-forward AND with fresh citrus garnish.",
        invalid_behavior=["Mix any cocktail", "Mix a citrus-free spirit-forward drink", "Mix a citrus-garnished light cocktail"],
        failure_patterns=["narrowing"], subtype="multi_step")),
]
