"""Phase 3 batch AC — second deficit-focused: narrowing + abandonment + multi triple."""

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


PHASE3_BATCH_AC: list[Phase3GroupSpec] = [
    # narrowing (10)
    _trip(_s(sample_id="p3-narrow-mentee-001", target_type="interpersonal_boundary", domain="career",
        target_description="user's mentee-acceptance rule — three explicit narrowings: any → women-in-tech → women-in-tech + first-five-years",
        target_slot_id="mentee::v1", topic="mentee_accept_rule",
        versions=[
            VersionSpec(value="accept any aspiring mentee who reaches out by email", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept only women-in-tech mentees, no other groups", polarity="constraint", session_introduced=2),
            VersionSpec(value="accept only women-in-tech mentees AND only those in their first five years of an engineering career", polarity="constraint", session_introduced=3),
        ],
        current_query="A woman with twelve years engineering experience emailed asking for mentorship — accept?",
        required_behavior="Pass; rule is women-in-tech AND first-five-years.",
        invalid_behavior=["Accept anyone", "Accept any woman-in-tech mentee", "Accept male first-five-years"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-budget-001", target_type="procedural_constraint", domain="finance",
        target_description="user's vacation-budget rule — three explicit narrowings: any → under-3000 → under-3000 + within-Americas",
        target_slot_id="vbudget::v1", topic="vacation_budget_rule",
        versions=[
            VersionSpec(value="set vacation budgets at whatever the user feels like spending per trip", polarity="constraint", session_introduced=1),
            VersionSpec(value="set vacation budgets at under three thousand dollars per trip total", polarity="constraint", session_introduced=2),
            VersionSpec(value="set vacation budgets at under three thousand dollars per trip AND only travel within North or South America", polarity="constraint", session_introduced=3),
        ],
        current_query="A two-week Tokyo trip in shoulder season costs $2500 — book?",
        required_behavior="Pass; rule is under-3000 AND within Americas.",
        invalid_behavior=["Book any vacation", "Book any under-3000 trip", "Book non-Americas at over 3000"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-cookbook-001", target_type="object_preference", domain="food",
        target_description="user's cookbook-buy rule — three explicit narrowings: any → vegetarian-only → vegetarian-only + region-specific",
        target_slot_id="cbk::v1", topic="cookbook_buy_rule",
        versions=[
            VersionSpec(value="buy any cookbook that catches the user's eye at the bookshop", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only vegetarian-themed cookbooks for the kitchen library", polarity="prefer", session_introduced=2),
            VersionSpec(value="buy only vegetarian cookbooks AND only ones focused on a single regional cuisine", polarity="prefer", session_introduced=3),
        ],
        current_query="A bookshop has a great new pan-European vegetarian cookbook — buy?",
        required_behavior="Pass; rule is vegetarian AND single-region.",
        invalid_behavior=["Buy any cookbook", "Buy any vegetarian cookbook", "Buy a non-vegetarian regional cookbook"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-podcast-on-001", target_type="procedural_constraint", domain="media",
        target_description="user's podcast-guest acceptance rule — three explicit narrowings: any → recorded-only → recorded-only + question-list-3-days-ahead",
        target_slot_id="pgon::v1", topic="podcast_guest_rule",
        versions=[
            VersionSpec(value="accept any podcast guest invitation that fits the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept podcast guest invitations only when the show records audio in advance, never live", polarity="constraint", session_introduced=2),
            VersionSpec(value="accept podcast guest invitations only when recorded in advance AND when the host sends a question list at least three days ahead", polarity="constraint", session_introduced=3),
        ],
        current_query="A podcast emailed asking me on, recorded next week, no question list yet — accept?",
        required_behavior="Pass; rule is recorded AND question list 3 days ahead.",
        invalid_behavior=["Accept any invite", "Accept recorded without question list", "Accept live with question list"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-gift-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's birthday-gift rule — three explicit narrowings: any → handmade-only → handmade-only + made-by-user-personally",
        target_slot_id="gift::v1", topic="birthday_gift_rule",
        versions=[
            VersionSpec(value="give any birthday gift that fits the recipient's interests", polarity="prefer", session_introduced=1),
            VersionSpec(value="give only handmade birthday gifts, no store-bought items", polarity="prefer", session_introduced=2),
            VersionSpec(value="give only handmade birthday gifts AND only ones the user made personally, not commissioned", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend's birthday is next week — should I commission a handmade ceramic mug from a local artisan?",
        required_behavior="Pass; rule is handmade AND made by user personally.",
        invalid_behavior=["Buy any store-bought gift", "Commission any handmade gift", "Make a non-personal gift"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-investment-001", target_type="procedural_constraint", domain="finance",
        target_description="user's startup-investing rule — three explicit narrowings: any → seed-stage-only → seed-stage-only + B2B-SaaS",
        target_slot_id="vinv::v1", topic="startup_invest_rule",
        versions=[
            VersionSpec(value="take meetings with any founder pitching the user as a check writer", polarity="constraint", session_introduced=1),
            VersionSpec(value="take meetings only with founders raising at the seed stage", polarity="constraint", session_introduced=2),
            VersionSpec(value="take meetings only with seed-stage founders AND only those building B2B SaaS products", polarity="constraint", session_introduced=3),
        ],
        current_query="A consumer-app seed-stage founder asked for a meeting via cold email — accept?",
        required_behavior="Pass; rule is seed-stage AND B2B SaaS.",
        invalid_behavior=["Take any pitch", "Take any seed-stage", "Take non-seed B2B SaaS"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-paint-buy-001", target_type="object_preference", domain="hobby",
        target_description="user's painting-supply rule — three explicit narrowings: any → professional-grade → professional-grade + single-pigment",
        target_slot_id="psup::v1", topic="painting_supply_rule",
        versions=[
            VersionSpec(value="buy any oil-paint tubes the user finds at the art store", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only professional-grade oil paints, no student-grade lines", polarity="prefer", session_introduced=2),
            VersionSpec(value="buy only professional-grade oil paints AND only single-pigment colors, never multi-pigment mixes", polarity="prefer", session_introduced=3),
        ],
        current_query="The art store has a great deal on a professional-grade three-pigment cobalt-mix tube — buy?",
        required_behavior="Pass; rule is professional-grade AND single-pigment.",
        invalid_behavior=["Buy any tube", "Buy any professional-grade", "Buy student-grade single-pigment"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-house-guest-002", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's house-guest rule — three explicit narrowings: any → close-friends → close-friends + with-2-week-notice",
        target_slot_id="hg::v1", topic="house_guest_rule",
        versions=[
            VersionSpec(value="welcome any acquaintance to stay overnight at the user's apartment", polarity="constraint", session_introduced=1),
            VersionSpec(value="welcome only close friends to stay overnight at the apartment, no acquaintances", polarity="constraint", session_introduced=2),
            VersionSpec(value="welcome close friends only when they ask at least two weeks ahead, no last-minute crashes", polarity="constraint", session_introduced=3),
        ],
        current_query="A close friend just texted asking to crash on the couch this Friday — agree?",
        required_behavior="Pass; rule is close friends AND 2-week notice.",
        invalid_behavior=["Welcome any acquaintance", "Welcome any close friend short notice", "Welcome anyone with notice"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-volunteer-001", target_type="procedural_constraint", domain="community",
        target_description="user's volunteer-signup rule — three explicit narrowings: any → literacy-only → literacy-only + 4-hours-or-fewer",
        target_slot_id="vol::v1", topic="volunteer_signup_rule",
        versions=[
            VersionSpec(value="sign up for any volunteer opportunity that fits the user's schedule", polarity="constraint", session_introduced=1),
            VersionSpec(value="sign up only for literacy-program volunteer roles, no other types of cause", polarity="constraint", session_introduced=2),
            VersionSpec(value="sign up only for literacy-program volunteer shifts AND only ones that take four hours or fewer per session", polarity="constraint", session_introduced=3),
        ],
        current_query="A literacy nonprofit asked for a Saturday all-day six-hour shift — sign up?",
        required_behavior="Pass; rule is literacy AND ≤4-hour shifts.",
        invalid_behavior=["Sign up for any cause", "Sign up for any literacy shift", "Sign up for any 4-hour-shift"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-team-001", target_type="procedural_constraint", domain="management",
        target_description="user's team-promo rule — three explicit narrowings: any → tenured-2-years → tenured-2-years + project-lead-experience",
        target_slot_id="promo::v1", topic="team_promotion_rule",
        versions=[
            VersionSpec(value="promote any team member when their performance reaches the next level", polarity="constraint", session_introduced=1),
            VersionSpec(value="promote only team members who have been on the team at least two years", polarity="constraint", session_introduced=2),
            VersionSpec(value="promote only team members who have been on the team at least two years AND have led at least one major project end-to-end", polarity="constraint", session_introduced=3),
        ],
        current_query="A 3-year team member who's never led a project is performing at the next level — promote?",
        required_behavior="Pass; rule is 2-years tenure AND project-lead experience.",
        invalid_behavior=["Promote based on performance alone", "Promote on tenure alone", "Promote on project-lead alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # implicit_drift / abandonment (10)
    _drift(_s(sample_id="p3-drift-aban-fasting-002", target_type="procedural_constraint", domain="health",
        target_description="user's daily intermittent fasting — abandoned after side effects, no replacement",
        target_slot_id="fast::v1", topic="intermittent_fasting_practice",
        versions=[
            VersionSpec(value="run a daily 18:6 intermittent-fasting window, eating only between 1pm and 7pm", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the daily 18:6 intermittent fasting after side effects and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 9am — am I skipping breakfast for the fast?",
        required_behavior="No; the intermittent fasting practice has been abandoned.",
        invalid_behavior=["Skip breakfast for the fast"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-yt-001", target_type="procedural_constraint", domain="media",
        target_description="user's weekly YouTube video — abandoned after burnout, no replacement",
        target_slot_id="ytvid::v1", topic="weekly_youtube_video_practice",
        versions=[
            VersionSpec(value="record and upload a weekly 12-minute YouTube tutorial every Sunday afternoon", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop recording the weekly YouTube tutorial after burnout and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday afternoon — am I setting up the camera for the weekly upload?",
        required_behavior="No; the weekly YouTube practice has been abandoned.",
        invalid_behavior=["Set up the camera for the weekly upload"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-strength-001", target_type="procedural_constraint", domain="health",
        target_description="user's strength-training routine — abandoned after gym membership lapse, no replacement",
        target_slot_id="strn::v1", topic="strength_training_practice",
        versions=[
            VersionSpec(value="run a 5x5 strength-training routine three times a week at the gym with squats, bench, and deadlift", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the 5x5 strength training after the gym membership lapsed and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Tuesday evening — am I packing the gym bag for the strength session?",
        required_behavior="No; the strength training practice has been abandoned.",
        invalid_behavior=["Pack the gym bag for strength training"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-conf-host-001", target_type="procedural_constraint", domain="career",
        target_description="user's annual conference hosting — abandoned after sponsor pulled out, no replacement",
        target_slot_id="confhost::v1", topic="annual_conference_host_practice",
        versions=[
            VersionSpec(value="host the annual local-tech conference every October at the user's company office", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop hosting the annual local-tech conference after the title sponsor pulled out and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is early October — am I sending out invites for this year's conference?",
        required_behavior="No; the annual conference hosting has been abandoned.",
        invalid_behavior=["Send out the conference invites"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-pottery-002", target_type="procedural_constraint", domain="hobby",
        target_description="user's pottery wheel practice — abandoned after move to apartment, no replacement",
        target_slot_id="pott::v1", topic="pottery_wheel_practice",
        versions=[
            VersionSpec(value="throw on the home pottery wheel every Saturday morning at the basement studio", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the pottery wheel practice after moving to the apartment with no studio space and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I pulling out the clay for the wheel session?",
        required_behavior="No; the pottery wheel practice has been abandoned.",
        invalid_behavior=["Pull out the clay for the wheel session"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-club-attend-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's monthly wine club — abandoned after subscription canceled, no replacement",
        target_slot_id="wineclub::v1", topic="monthly_wine_club_practice",
        versions=[
            VersionSpec(value="receive the monthly wine club shipment of three bottles from the regional importer every first of the month", polarity="constraint", session_introduced=1),
            VersionSpec(value="cancel the monthly wine club subscription and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the first of the month — should I expect a wine shipment notification today?",
        required_behavior="No; the monthly wine club has been abandoned.",
        invalid_behavior=["Expect today's wine shipment notification"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-pa-001", target_type="procedural_constraint", domain="management",
        target_description="user's quarterly performance reviews — abandoned after team restructure, no replacement",
        target_slot_id="pa::v1", topic="quarterly_performance_review_practice",
        versions=[
            VersionSpec(value="run formal quarterly performance reviews with each direct report at the end of each quarter", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop running quarterly performance reviews after the team restructure moved to continuous feedback only and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the last week of the quarter — am I scheduling formal performance review meetings?",
        required_behavior="No; the quarterly performance reviews have been abandoned.",
        invalid_behavior=["Schedule the quarterly performance review meetings"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-jazz-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's monthly jazz performance — abandoned after the venue closed, no replacement",
        target_slot_id="jazz::v1", topic="monthly_jazz_performance_practice",
        versions=[
            VersionSpec(value="play the monthly Friday-night jazz set at the regular cafe with the user's quartet", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the monthly jazz set performance after the cafe closed and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the last Friday of the month — am I packing up the saxophone for the jazz set?",
        required_behavior="No; the monthly jazz performance has been abandoned.",
        invalid_behavior=["Pack up the saxophone for the set"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-news-001", target_type="procedural_constraint", domain="learning",
        target_description="user's daily morning newspaper — abandoned after subscription cancellation, no replacement",
        target_slot_id="newspaper::v1", topic="daily_newspaper_practice",
        versions=[
            VersionSpec(value="read the New York Times print edition cover to cover every weekday morning over breakfast", polarity="constraint", session_introduced=1),
            VersionSpec(value="cancel the New York Times print subscription and never resume the daily-newspaper practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 7am over breakfast — am I expecting the New York Times print delivery on the front step?",
        required_behavior="No; the daily print newspaper practice has been abandoned.",
        invalid_behavior=["Expect the New York Times delivery"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-call-001", target_type="procedural_constraint", domain="relationships",
        target_description="user's weekly grandparent call — abandoned after grandparent's hearing loss, no replacement",
        target_slot_id="gpcall::v1", topic="weekly_grandparent_call_practice",
        versions=[
            VersionSpec(value="call the user's grandmother every Sunday afternoon for a thirty-minute phone conversation", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the weekly Sunday phone call after grandmother's hearing loss made phone calls difficult, switching to letters that the user no longer maintains and never resume the call practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday afternoon — am I dialing grandmother for the weekly call?",
        required_behavior="No; the weekly Sunday phone call practice has been abandoned.",
        invalid_behavior=["Dial grandmother for the weekly call"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # multi_version triple (4)
    _trip(_s(sample_id="p3-multi-trip-mailclient-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's email client — four versions: Apple-Mail → Spark → Hey → Mimestream",
        target_slot_id="emc::v1", topic="email_client",
        versions=[
            VersionSpec(value="check personal email in Apple Mail with the unified inbox feature", polarity="prefer", session_introduced=1),
            VersionSpec(value="check personal email in Spark with the smart-inbox prioritization", polarity="prefer", session_introduced=2),
            VersionSpec(value="check personal email in Hey from 37signals with the screener-and-reply-later workflow", polarity="prefer", session_introduced=3),
            VersionSpec(value="check personal email in Mimestream as a native Gmail client built specifically for macOS", polarity="prefer", session_introduced=4),
        ],
        current_query="A friend asked which email app I use these days — what do I tell them?",
        required_behavior="Tell them Mimestream.",
        invalid_behavior=["Tell them Apple Mail", "Tell them Spark", "Tell them Hey"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-style-001", target_type="object_preference", domain="hobby",
        target_description="user's daily style — four versions: streetwear → workwear → minimal-suiting → vintage-Italian",
        target_slot_id="style::v1", topic="daily_dress_style",
        versions=[
            VersionSpec(value="dress in streetwear style with hoodies and sneakers for daily wear", polarity="prefer", session_introduced=1),
            VersionSpec(value="dress in workwear style with denim and boots for daily wear", polarity="prefer", session_introduced=2),
            VersionSpec(value="dress in minimal-suiting style with tailored separates and loafers for daily wear", polarity="prefer", session_introduced=3),
            VersionSpec(value="dress in vintage-Italian style with knit polos and pleated trousers for daily wear", polarity="prefer", session_introduced=4),
        ],
        current_query="I am about to head out for the day — what is the outfit?",
        required_behavior="Vintage-Italian: knit polo and pleated trousers.",
        invalid_behavior=["Streetwear hoodie and sneakers", "Workwear denim and boots", "Minimal suit separates and loafers"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-stock-platform-001", target_type="object_preference", domain="finance",
        target_description="user's brokerage platform — four versions: Robinhood → Fidelity → Interactive-Brokers → Wealthfront",
        target_slot_id="brokers::v1", topic="brokerage_platform",
        versions=[
            VersionSpec(value="trade individual stocks through Robinhood with the commission-free retail interface", polarity="prefer", session_introduced=1),
            VersionSpec(value="trade individual stocks through Fidelity with the active-trader pro platform", polarity="prefer", session_introduced=2),
            VersionSpec(value="trade individual stocks through Interactive Brokers with the professional-grade execution", polarity="prefer", session_introduced=3),
            VersionSpec(value="invest only through Wealthfront's automated robo-advisor with no individual stock trades", polarity="prefer", session_introduced=4),
        ],
        current_query="I want to invest tomorrow's bonus — which platform do I use?",
        required_behavior="Move it into Wealthfront's robo-advisor.",
        invalid_behavior=["Buy stocks on Robinhood", "Buy stocks on Fidelity", "Buy stocks on Interactive Brokers"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-bookwrite-001", target_type="procedural_constraint", domain="writing",
        target_description="user's writing routine — four versions: morning-1000-words → evening-pomodoro → weekend-marathon → daily-handwritten-pages",
        target_slot_id="write::v1", topic="writing_routine",
        versions=[
            VersionSpec(value="write 1000 words every morning before work as the daily writing practice", polarity="constraint", session_introduced=1),
            VersionSpec(value="write in evening pomodoro blocks of three 25-minute sessions after dinner instead of mornings", polarity="constraint", session_introduced=2),
            VersionSpec(value="write in weekend marathon sessions of four hours on Saturday and four on Sunday with no weekday writing", polarity="constraint", session_introduced=3),
            VersionSpec(value="write three handwritten pages in a notebook every morning, no laptop writing", polarity="constraint", session_introduced=4),
        ],
        current_query="It is 7am — what's the writing for today?",
        required_behavior="Three handwritten pages in the notebook.",
        invalid_behavior=["1000 words on the laptop", "Three evening pomodoro blocks", "Wait for weekend marathon"],
        failure_patterns=["multi_version"], subtype="strong")),

    # implicit_drift / gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-gn-meeting-002", target_type="procedural_constraint", domain="management",
        target_description="user's external meeting acceptance — gradually narrowing without announcement: any → only-existing-clients → only-existing-clients + Tuesday-only",
        target_slot_id="extmeet::v1", topic="external_meeting_drift_rule",
        versions=[
            VersionSpec(value="accept any external meeting request that fits the user's calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept external meetings only with existing client contacts AND only schedule them on Tuesdays", polarity="constraint", session_introduced=2),
        ],
        current_query="A new prospect asked for a Wednesday meeting next week — accept?",
        required_behavior="Pass; user takes external meetings only with existing clients on Tuesdays.",
        invalid_behavior=["Accept the new prospect Wednesday"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),
]
