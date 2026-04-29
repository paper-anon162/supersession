"""Phase 3 batch AD — leakage-safe narrowing + abandonment.

Lesson from ab/ac: current_query must NOT contain distinguishing tokens
from active value (e.g., 'dividend', 'minutes', 'weekly'). Queries here
use referential phrasing ('the rule', 'this approach', 'today's plan')
to avoid lexical leakage."""

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


PHASE3_BATCH_AD: list[Phase3GroupSpec] = [
    # narrowing (15) — leakage-safe queries
    _trip(_s(sample_id="p3-narrow-pull-conf-002", target_type="procedural_constraint", domain="career",
        target_description="user's conf-attendance — three explicit narrowings: any → in-person → in-person + speaker-slot",
        target_slot_id="conf2::v1", topic="conference_attend_rule",
        versions=[
            VersionSpec(value="attend any tech conference the user finds compelling on the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="attend tech conferences only when the event runs as in-person, never the virtual format", polarity="constraint", session_introduced=2),
            VersionSpec(value="attend tech conferences only when the event runs in-person AND when the user is invited to take the stage as a speaker", polarity="constraint", session_introduced=3),
        ],
        current_query="A great event has open registration next month for paying audience members — does this fit?",
        required_behavior="No; the rule needs in-person AND a speaker invitation.",
        invalid_behavior=["Treat any event as fitting", "Accept in-person without speaker role", "Accept virtual with speaker role"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-cookbook-001", target_type="object_preference", domain="food",
        target_description="user's cookbook-buy — three explicit narrowings: any → vegetarian → vegetarian + single-region",
        target_slot_id="cbk2::v1", topic="cookbook_buy_rule",
        versions=[
            VersionSpec(value="buy any cookbook that catches the user's eye at the bookshop", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only vegetarian-themed cookbooks for the kitchen library", polarity="prefer", session_introduced=2),
            VersionSpec(value="buy only vegetarian-themed cookbooks AND only ones focused on a single regional cuisine", polarity="prefer", session_introduced=3),
        ],
        current_query="A bookshop has a beautiful new pan-European meatless cookbook on display — does it fit?",
        required_behavior="No; the rule requires a single-region focus.",
        invalid_behavior=["Buy any cookbook", "Buy a meaty cookbook", "Buy a multi-region meatless cookbook"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-housguest-002", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's house-guest — three explicit narrowings: any → close-friends → close-friends + 2-week-notice",
        target_slot_id="hg2::v1", topic="house_guest_rule",
        versions=[
            VersionSpec(value="welcome any acquaintance to stay overnight at the user's apartment", polarity="constraint", session_introduced=1),
            VersionSpec(value="welcome only close friends to stay overnight at the apartment, no acquaintances", polarity="constraint", session_introduced=2),
            VersionSpec(value="welcome close friends to stay overnight only when they ask at least two weeks ahead", polarity="constraint", session_introduced=3),
        ],
        current_query="An old close friend just texted me asking to crash on the couch this Friday — does this fit?",
        required_behavior="No; the rule requires the ask to come at least two weeks ahead.",
        invalid_behavior=["Welcome any acquaintance", "Welcome any close friend on short notice", "Welcome an acquaintance with notice"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-podcast-002", target_type="procedural_constraint", domain="media",
        target_description="user's podcast-guest — three explicit narrowings: any → recorded → recorded + question-list-ahead",
        target_slot_id="pgon2::v1", topic="podcast_guest_rule",
        versions=[
            VersionSpec(value="accept any podcast guest invitation that fits the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept podcast guest invitations only when the host records audio in advance, never live broadcast", polarity="constraint", session_introduced=2),
            VersionSpec(value="accept podcast guest invitations only when recorded in advance AND when the host shares a question list at least three days ahead", polarity="constraint", session_introduced=3),
        ],
        current_query="A small show emailed asking me on as a guest next week with no preparation materials yet — does this fit?",
        required_behavior="No; the rule needs both pre-recorded format AND a question list ahead.",
        invalid_behavior=["Accept any invite", "Accept a recorded show without question list", "Accept a live show with question list"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-mentee-002", target_type="interpersonal_boundary", domain="career",
        target_description="user's mentee — three explicit narrowings: any → women-in-tech → women-in-tech + first-five-years",
        target_slot_id="mentee2::v1", topic="mentee_accept_rule",
        versions=[
            VersionSpec(value="accept any aspiring mentee who reaches out by email", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept only women-in-tech mentees, no other groups", polarity="constraint", session_introduced=2),
            VersionSpec(value="accept only women-in-tech mentees AND only those still in their first five years of an engineering career", polarity="constraint", session_introduced=3),
        ],
        current_query="A senior staff engineer just emailed asking for a mentorship slot citing my recent post — does this fit?",
        required_behavior="No; the rule restricts to early-career mentees.",
        invalid_behavior=["Accept anyone", "Accept any woman-in-tech mentee", "Accept a male early-career mentee"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-volunteer-002", target_type="procedural_constraint", domain="community",
        target_description="user's volunteer — three explicit narrowings: any → literacy-only → literacy-only + 4-hours-or-fewer",
        target_slot_id="vol2::v1", topic="volunteer_signup_rule",
        versions=[
            VersionSpec(value="sign up for any volunteer opportunity that fits the user's schedule", polarity="constraint", session_introduced=1),
            VersionSpec(value="sign up only for literacy-program volunteer roles, no other types of cause", polarity="constraint", session_introduced=2),
            VersionSpec(value="sign up only for literacy-program volunteer shifts AND only ones that take four hours or fewer per session", polarity="constraint", session_introduced=3),
        ],
        current_query="A literacy nonprofit asked for a Saturday all-day commitment next month — does this fit?",
        required_behavior="No; the rule caps shift length below the all-day requirement.",
        invalid_behavior=["Sign up for any cause", "Sign up for a long literacy shift", "Sign up for a short non-literacy shift"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-friend-loan-003", target_type="interpersonal_boundary", domain="finance",
        target_description="user's friend-loan — three explicit narrowings: any → close-friends → close-friends + small-amounts",
        target_slot_id="floan2::v1", topic="friend_loan_rule",
        versions=[
            VersionSpec(value="lend money to any friend who asks for help", polarity="constraint", session_introduced=1),
            VersionSpec(value="lend money only to close friends in the user's inner circle of five", polarity="constraint", session_introduced=2),
            VersionSpec(value="lend money only to close inner-circle friends AND only in amounts under one hundred dollars", polarity="constraint", session_introduced=3),
        ],
        current_query="An inner-circle friend asked to borrow about three hundred dollars for a deposit — does this fit?",
        required_behavior="No; the rule caps loan amounts below the request.",
        invalid_behavior=["Lend to any friend", "Lend any sum to close friend", "Lend small to outer friend"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-event-rsvp-002", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's event-RSVP — three explicit narrowings: any → close-friend-host → close-friend-host + nearby",
        target_slot_id="rsvp2::v1", topic="event_rsvp_rule",
        versions=[
            VersionSpec(value="RSVP yes to any social event invitation the user gets", polarity="constraint", session_introduced=1),
            VersionSpec(value="RSVP yes only to events hosted by a close friend, never by acquaintances", polarity="constraint", session_introduced=2),
            VersionSpec(value="RSVP yes only to events hosted by a close friend AND only when the venue sits within thirty minutes of travel from home", polarity="constraint", session_introduced=3),
        ],
        current_query="A close friend invited me to a party at a venue ninety minutes away by train — does this fit?",
        required_behavior="No; the rule caps travel time below the venue distance.",
        invalid_behavior=["RSVP yes to any event", "RSVP to a far close-friend event", "RSVP to a near acquaintance event"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-podc-listen-001", target_type="object_preference", domain="learning",
        target_description="user's podcast-listen — three explicit narrowings: any → finance-only → finance-only + short",
        target_slot_id="podlisten::v1", topic="podcast_listen_rule",
        versions=[
            VersionSpec(value="add any podcast that sounds interesting to the daily listen queue", polarity="prefer", session_introduced=1),
            VersionSpec(value="add only finance-focused podcasts to the daily listen queue", polarity="prefer", session_introduced=2),
            VersionSpec(value="add only finance-focused podcasts AND only ones whose episodes run under thirty minutes", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend recommended a fascinating ninety-minute interview with a hedge-fund manager — does this fit?",
        required_behavior="No; the rule caps episode length below the recommended length.",
        invalid_behavior=["Add any podcast", "Add long finance show", "Add short non-finance show"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-budget-002", target_type="procedural_constraint", domain="finance",
        target_description="user's vacation-budget — three explicit narrowings: any → under-3000 → under-3000 + within-Americas",
        target_slot_id="vbud2::v1", topic="vacation_budget_rule",
        versions=[
            VersionSpec(value="set vacation budgets at whatever the user feels like spending per trip", polarity="constraint", session_introduced=1),
            VersionSpec(value="set vacation budgets at no more than three thousand dollars total per trip", polarity="constraint", session_introduced=2),
            VersionSpec(value="set vacation budgets at no more than three thousand dollars per trip AND only travel within North or South America", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend invited me to share a flat in Tokyo for a week at twenty-five hundred dollars total — does this fit?",
        required_behavior="No; the rule restricts destinations to the Americas.",
        invalid_behavior=["Approve any spend", "Approve cheap non-Americas trip", "Approve expensive Americas trip"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-house-002", target_type="procedural_constraint", domain="home",
        target_description="user's house-cleaner — three explicit narrowings: any → eco-products-only → eco-products-only + bonded-and-insured",
        target_slot_id="cln::v1", topic="house_cleaner_rule",
        versions=[
            VersionSpec(value="hire any house-cleaning service the user finds in the neighborhood", polarity="constraint", session_introduced=1),
            VersionSpec(value="hire only house-cleaning services that use eco-friendly cleaning products", polarity="constraint", session_introduced=2),
            VersionSpec(value="hire only eco-friendly house-cleaning services AND only ones that are licensed-bonded-and-insured", polarity="constraint", session_introduced=3),
        ],
        current_query="A neighbor recommended a green-cleaning company that's just family-run with no formal licensing — does this fit?",
        required_behavior="No; the rule requires bonded-and-insured status.",
        invalid_behavior=["Hire any cleaner", "Hire green cleaner without licensing", "Hire licensed non-green cleaner"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-content-002", target_type="procedural_constraint", domain="writing",
        target_description="user's blog-publish — three explicit narrowings: any → twice-monthly → twice-monthly + with-original-data",
        target_slot_id="pub2::v1", topic="blog_publish_rule",
        versions=[
            VersionSpec(value="publish blog posts whenever a draft happens to be ready", polarity="constraint", session_introduced=1),
            VersionSpec(value="publish blog posts on a strict twice-monthly cadence on the 1st and 15th of each month", polarity="constraint", session_introduced=2),
            VersionSpec(value="publish blog posts on a twice-monthly cadence AND only when the post contains an original-data analysis section", polarity="constraint", session_introduced=3),
        ],
        current_query="It is the 15th and a polished essay draft is sitting in the queue with no quantitative section — does this fit?",
        required_behavior="No; the rule requires the data section.",
        invalid_behavior=["Publish whenever ready", "Publish on cadence without data", "Publish off-cadence with data"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-art-001", target_type="object_preference", domain="hobby",
        target_description="user's art-buy — three explicit narrowings: any → emerging-women → emerging-women + under-2000",
        target_slot_id="art::v1", topic="art_purchase_rule",
        versions=[
            VersionSpec(value="buy any artwork the user finds compelling at galleries or art fairs", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only artwork by emerging women artists, no established or male artists", polarity="prefer", session_introduced=2),
            VersionSpec(value="buy only artwork by emerging women artists AND only pieces priced under two thousand dollars", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend recommended a piece by an up-and-coming female painter at five thousand dollars — does this fit?",
        required_behavior="No; the rule caps price below the asking amount.",
        invalid_behavior=["Buy any art", "Buy expensive emerging-women art", "Buy cheap male-artist art"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-promo-001", target_type="procedural_constraint", domain="management",
        target_description="user's team-promo — three explicit narrowings: any → tenured-2-years → tenured-2-years + project-lead",
        target_slot_id="prom::v1", topic="team_promotion_rule",
        versions=[
            VersionSpec(value="promote any team member when their performance reaches the next level", polarity="constraint", session_introduced=1),
            VersionSpec(value="promote only team members who have been on the team at least two years", polarity="constraint", session_introduced=2),
            VersionSpec(value="promote only team members who have been on the team at least two years AND have led at least one major project end-to-end", polarity="constraint", session_introduced=3),
        ],
        current_query="A three-year tenured engineer is performing well but has only contributed to projects, never led one — does this fit?",
        required_behavior="No; the rule requires project-lead experience.",
        invalid_behavior=["Promote on perf alone", "Promote on tenure alone", "Promote on lead-experience alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-grocery-002", target_type="object_preference", domain="food",
        target_description="user's grocery-store — three explicit narrowings: any → organic-only → organic-only + within-walking-distance",
        target_slot_id="gstore::v1", topic="grocery_store_rule",
        versions=[
            VersionSpec(value="shop at any grocery store that fits the user's day", polarity="prefer", session_introduced=1),
            VersionSpec(value="shop only at grocery stores stocked with mostly organic produce", polarity="prefer", session_introduced=2),
            VersionSpec(value="shop only at grocery stores with mostly organic produce AND within walking distance of home", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend recommended a farm-to-table store ten miles across town — does this fit?",
        required_behavior="No; the rule requires walking distance.",
        invalid_behavior=["Shop anywhere", "Shop far organic store", "Shop nearby non-organic store"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # implicit_drift / abandonment (10) — drift compact is reliable, no leakage issues
    _drift(_s(sample_id="p3-drift-aban-trello-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's project tracker — abandoned after pivot to single-task focus, no replacement",
        target_slot_id="trello::v1", topic="project_tracker_practice",
        versions=[
            VersionSpec(value="maintain the personal project board on Trello with weekly card updates and labels", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop maintaining the project tracker after pivoting to a single-deep-focus approach and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="A friend asked which project board I keep my work in these days — what do I tell them?",
        required_behavior="Tell them I no longer maintain a project board; the practice has been abandoned.",
        invalid_behavior=["Point them at the Trello board"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-yoga-prac-001", target_type="procedural_constraint", domain="health",
        target_description="user's home yoga — abandoned after spine injury, no replacement",
        target_slot_id="yog::v1", topic="home_yoga_practice",
        versions=[
            VersionSpec(value="run a 60-minute home yoga flow every Sunday morning in the living room", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the Sunday home yoga flow after the spine injury and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday morning — am I rolling out the mat?",
        required_behavior="No; the home yoga practice has been abandoned.",
        invalid_behavior=["Roll out the mat for the flow"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-wake-001", target_type="procedural_constraint", domain="health",
        target_description="user's 5am wake-up — abandoned after job change, no replacement",
        target_slot_id="wake::v1", topic="early_wake_practice",
        versions=[
            VersionSpec(value="wake at 5am every weekday for the morning routine of journaling and meditation before work", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the 5am wake-up routine after the new job removed the rationale and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 4:30am on a Tuesday and the alarm just went off — should I get out of bed?",
        required_behavior="No; the early wake-up routine has been abandoned.",
        invalid_behavior=["Get out of bed for the routine"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-newsletter-002", target_type="procedural_constraint", domain="writing",
        target_description="user's daily newsletter writeup — abandoned after audience plateau, no replacement",
        target_slot_id="dnews::v1", topic="daily_newsletter_practice",
        versions=[
            VersionSpec(value="publish a daily 600-word email newsletter every weekday morning to the subscriber list", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop publishing the daily newsletter after the audience plateaued and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 7am Tuesday and the inbox is open — am I drafting today's edition?",
        required_behavior="No; the daily newsletter practice has been abandoned.",
        invalid_behavior=["Draft today's edition"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-running-002", target_type="procedural_constraint", domain="health",
        target_description="user's marathon training — abandoned after injury, no replacement",
        target_slot_id="mara2::v1", topic="marathon_training_practice",
        versions=[
            VersionSpec(value="run twenty-mile training sessions every Saturday morning on the riverside path", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the long Saturday training runs after the stress fracture and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I lacing up for the long run?",
        required_behavior="No; the long-run training practice has been abandoned.",
        invalid_behavior=["Lace up for the twenty-mile run"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-cookbook-001", target_type="procedural_constraint", domain="food",
        target_description="user's cookbook-of-the-month — abandoned after life got busier, no replacement",
        target_slot_id="cbkpr::v1", topic="cookbook_of_the_month_practice",
        versions=[
            VersionSpec(value="cook through one full cookbook every month picking five recipes per week from a single book", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the cookbook-of-the-month project after life got busier and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the first of the month — am I picking a new cookbook off the shelf?",
        required_behavior="No; the cookbook-of-the-month practice has been abandoned.",
        invalid_behavior=["Pick a new cookbook off the shelf"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-stamp-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's stamp collecting — abandoned after move and lost interest, no replacement",
        target_slot_id="stamp::v1", topic="stamp_collecting_practice",
        versions=[
            VersionSpec(value="add new stamps to the album every Sunday afternoon by sorting and cataloging recent acquisitions", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop adding to the stamp album after the move and the loss of interest, and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday afternoon — am I pulling out the stamp album?",
        required_behavior="No; the stamp collecting practice has been abandoned.",
        invalid_behavior=["Pull out the stamp album"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-1on1-002", target_type="procedural_constraint", domain="management",
        target_description="user's regular skip-level 1:1s — abandoned after re-org, no replacement",
        target_slot_id="skp::v1", topic="skip_level_one_on_one_practice",
        versions=[
            VersionSpec(value="hold a skip-level 1:1 with each grandchild-team member every quarter for a thirty-minute conversation", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the skip-level 1:1 practice after the team restructure removed the relevant teams and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the start of the quarter — am I scheduling the skip-level meetings?",
        required_behavior="No; the skip-level 1:1 practice has been abandoned.",
        invalid_behavior=["Schedule the skip-level meetings"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-coffee-002", target_type="procedural_constraint", domain="career",
        target_description="user's networking coffees — abandoned after job change made them unnecessary, no replacement",
        target_slot_id="cmeet2::v1", topic="networking_coffee_practice",
        versions=[
            VersionSpec(value="schedule three networking coffees per week with new contacts at the cafe near the office", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop scheduling networking coffees after the new role made them unnecessary, and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="A LinkedIn DM asked for a coffee chat next Tuesday — am I accepting?",
        required_behavior="No; the networking coffee practice has been abandoned.",
        invalid_behavior=["Accept the coffee chat"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-meditate-001", target_type="procedural_constraint", domain="health",
        target_description="user's Insight Timer streak — abandoned after focus shift, no replacement",
        target_slot_id="insight::v1", topic="insight_timer_practice",
        versions=[
            VersionSpec(value="open the Insight Timer app every morning before coffee for a ten-minute guided meditation session", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the daily Insight Timer session after the focus shifted away from app-based meditation and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is morning and the coffee is brewing — should I open the meditation app?",
        required_behavior="No; the daily Insight Timer practice has been abandoned.",
        invalid_behavior=["Open the meditation app"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),
]
