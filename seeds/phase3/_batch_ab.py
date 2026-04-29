"""Phase 3 batch AB — deficit-focused: narrowing + abandonment + multi triple."""

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


PHASE3_BATCH_AB: list[Phase3GroupSpec] = [
    # narrowing (10)
    _trip(_s(sample_id="p3-narrow-conf-attend-001", target_type="procedural_constraint", domain="career",
        target_description="user's conference-attendance rule — three explicit narrowings: any → in-person-only → in-person-only + with-talk-slot",
        target_slot_id="conf::v1", topic="conference_attendance_rule",
        versions=[
            VersionSpec(value="attend any tech conference the user finds interesting in the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="attend tech conferences only when held in person, never virtual", polarity="constraint", session_introduced=2),
            VersionSpec(value="attend tech conferences only when held in person AND when the user is invited as a speaker, not just an attendee", polarity="constraint", session_introduced=3),
        ],
        current_query="A great in-person conference has open attendee tickets next month — register?",
        required_behavior="Pass; the rule is in-person AND with a speaker slot.",
        invalid_behavior=["Register for any conference", "Register for in-person without speaker slot", "Register for virtual with speaker slot"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-recipe-pick-001", target_type="object_preference", domain="food",
        target_description="user's weeknight-recipe rule — three explicit narrowings: any → under-30-min → under-30-min + 8-or-fewer-ingredients",
        target_slot_id="recipe::v1", topic="weeknight_recipe_rule",
        versions=[
            VersionSpec(value="cook any weeknight recipe regardless of time or complexity", polarity="prefer", session_introduced=1),
            VersionSpec(value="cook only weeknight recipes that take under thirty minutes total to prepare", polarity="prefer", session_introduced=2),
            VersionSpec(value="cook only weeknight recipes that take under thirty minutes AND use eight or fewer ingredients", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend recommended a fast 25-minute pasta dish that uses 14 ingredients — cook tonight?",
        required_behavior="Pass; rule is under-30-min AND 8-or-fewer-ingredients.",
        invalid_behavior=["Cook anything regardless", "Cook 25-min any-ingredient", "Cook 8-ingredient over-30-min"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-investing-001", target_type="object_preference", domain="finance",
        target_description="user's brokerage rule — three explicit narrowings: any → S&P-500-only → S&P-500-only + dividend-paying",
        target_slot_id="brok::v1", topic="brokerage_buy_rule",
        versions=[
            VersionSpec(value="buy any individual stock the user finds interesting for the brokerage", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only S&P 500 index components for the brokerage", polarity="prefer", session_introduced=2),
            VersionSpec(value="buy only S&P 500 index components AND only ones paying a quarterly dividend", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend recommended a fast-growing S&P 500 tech name with no dividend — buy?",
        required_behavior="Pass; rule is S&P 500 AND dividend-paying.",
        invalid_behavior=["Buy any stock", "Buy any S&P 500 stock", "Buy a non-S&P 500 dividend payer"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-event-rsvp-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's event-RSVP rule — three explicit narrowings: any → close-friend-host → close-friend-host + within-30-min-travel",
        target_slot_id="rsvp::v1", topic="event_rsvp_rule",
        versions=[
            VersionSpec(value="RSVP yes to any social event invitation the user gets", polarity="constraint", session_introduced=1),
            VersionSpec(value="RSVP yes only to events hosted by a close friend, never acquaintances", polarity="constraint", session_introduced=2),
            VersionSpec(value="RSVP yes only to events hosted by a close friend AND within 30 minutes of travel from home", polarity="constraint", session_introduced=3),
        ],
        current_query="A close friend invited me to a party 90 minutes away — RSVP yes?",
        required_behavior="Pass; rule is close-friend host AND within 30 min travel.",
        invalid_behavior=["RSVP yes to any event", "RSVP to close-friend over 30 min", "RSVP to acquaintance within 30 min"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-coffee-buy-001", target_type="object_preference", domain="food",
        target_description="user's coffee-bean rule — three explicit narrowings: any → light-roast-only → light-roast-only + Ethiopian-origin",
        target_slot_id="cbean::v1", topic="coffee_bean_rule",
        versions=[
            VersionSpec(value="buy any whole-bean coffee that catches the user's eye at the shop", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only light-roast whole-bean coffee, no medium or dark roasts", polarity="prefer", session_introduced=2),
            VersionSpec(value="buy only light-roast whole-bean coffee from Ethiopian origin specifically", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend recommended a light-roast Colombian bean — buy?",
        required_behavior="Pass; rule is light-roast AND Ethiopian.",
        invalid_behavior=["Buy any roast", "Buy any light-roast", "Buy a medium-roast Ethiopian"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-friend-loan-002", target_type="interpersonal_boundary", domain="finance",
        target_description="user's friend-loan rule — three explicit narrowings: any → close-friends → close-friends + under-100",
        target_slot_id="floan::v1", topic="friend_loan_rule",
        versions=[
            VersionSpec(value="lend money to any friend who asks for help", polarity="constraint", session_introduced=1),
            VersionSpec(value="lend money only to close friends in the inner circle, never acquaintances", polarity="constraint", session_introduced=2),
            VersionSpec(value="lend money only to close inner-circle friends AND only in amounts under one hundred dollars", polarity="constraint", session_introduced=3),
        ],
        current_query="A close friend asked to borrow 250 dollars for a deposit — agree?",
        required_behavior="Pass; rule is close friends AND under 100 dollars.",
        invalid_behavior=["Lend to any friend", "Lend any amount to close friend", "Lend under-100 to acquaintance"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-talk-prep-001", target_type="procedural_constraint", domain="career",
        target_description="user's talk-prep rule — three explicit narrowings: any → with-slides-deck → with-slides-deck + dry-run-with-peer",
        target_slot_id="talk_prep::v1", topic="conference_talk_prep_rule",
        versions=[
            VersionSpec(value="prepare for conference talks however the day permits, sometimes off-the-cuff", polarity="constraint", session_introduced=1),
            VersionSpec(value="prepare for conference talks only with a complete polished slide deck, no off-the-cuff talks", polarity="constraint", session_introduced=2),
            VersionSpec(value="prepare for conference talks with a polished slide deck AND a full dry-run delivered to a peer reviewer at least one week ahead", polarity="constraint", session_introduced=3),
        ],
        current_query="My talk is in five days, slides are done, no peer dry-run scheduled — am I ready?",
        required_behavior="Pass; need the dry-run with peer reviewer too.",
        invalid_behavior=["Go off-the-cuff", "Go with deck only", "Go with peer-reviewed but no slide deck"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-charity-001", target_type="procedural_constraint", domain="finance",
        target_description="user's charity-give rule — three explicit narrowings: any → climate-only → climate-only + four-star-Charity-Navigator",
        target_slot_id="give::v1", topic="charity_give_rule",
        versions=[
            VersionSpec(value="donate to any 501(c)(3) the user is asked to support", polarity="constraint", session_introduced=1),
            VersionSpec(value="donate only to climate-focused 501(c)(3) nonprofits", polarity="constraint", session_introduced=2),
            VersionSpec(value="donate only to climate-focused 501(c)(3) nonprofits rated four stars on Charity Navigator", polarity="constraint", session_introduced=3),
        ],
        current_query="A climate nonprofit rated three stars asked for a donation — give?",
        required_behavior="Pass; rule is climate AND four-star rated.",
        invalid_behavior=["Donate to any 501(c)(3)", "Donate to any climate cause", "Donate to non-climate four-star"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-vacation-001", target_type="procedural_constraint", domain="travel",
        target_description="user's vacation-pick rule — three explicit narrowings: any → Spanish-speaking → Spanish-speaking + coastal",
        target_slot_id="vac::v1", topic="vacation_destination_rule",
        versions=[
            VersionSpec(value="vacation in any city the user finds compelling in travel media", polarity="constraint", session_introduced=1),
            VersionSpec(value="vacation only in Spanish-speaking countries", polarity="constraint", session_introduced=2),
            VersionSpec(value="vacation only in Spanish-speaking countries AND only in coastal cities specifically", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend invited me to share a flat in Madrid for a week — accept?",
        required_behavior="Pass; rule is Spanish-speaking AND coastal.",
        invalid_behavior=["Accept any city", "Accept any Spanish-speaking city", "Accept any coastal city"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-content-pub-001", target_type="procedural_constraint", domain="writing",
        target_description="user's blog-publish rule — three explicit narrowings: any → twice-monthly-cadence → twice-monthly + with-original-data",
        target_slot_id="pub::v1", topic="blog_publish_rule",
        versions=[
            VersionSpec(value="publish blog posts whenever a draft happens to be ready", polarity="constraint", session_introduced=1),
            VersionSpec(value="publish blog posts on a strict twice-monthly cadence, the 1st and 15th", polarity="constraint", session_introduced=2),
            VersionSpec(value="publish blog posts on a twice-monthly cadence AND only when the post contains an original-data analysis section", polarity="constraint", session_introduced=3),
        ],
        current_query="It is the 15th, the draft is ready, but it has no original-data analysis section — publish?",
        required_behavior="Pass; rule is twice-monthly AND with original-data section.",
        invalid_behavior=["Publish any draft", "Publish on cadence without data", "Publish off-cadence with data"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # implicit_drift / abandonment (10)
    _drift(_s(sample_id="p3-drift-aban-yoga-002", target_type="procedural_constraint", domain="health",
        target_description="user's evening yoga session — abandoned after back injury, no replacement",
        target_slot_id="yoga2::v1", topic="evening_yoga_practice",
        versions=[
            VersionSpec(value="run a 45-minute evening yoga flow at home every weekday", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the evening yoga flow after the back injury and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 8pm — am I rolling out the yoga mat for the evening flow?",
        required_behavior="No; the evening yoga has been abandoned.",
        invalid_behavior=["Roll out the yoga mat for the evening flow"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-coffee-meet-001", target_type="procedural_constraint", domain="career",
        target_description="user's networking coffee meets — abandoned after job change, no replacement",
        target_slot_id="cmeet::v1", topic="networking_coffee_practice",
        versions=[
            VersionSpec(value="schedule three networking coffee meets per week with new contacts at the cafe", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop scheduling networking coffees after the job change made the existing role enough and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="A LinkedIn DM asked for a networking coffee next week — accept?",
        required_behavior="No; the networking coffee practice has been abandoned.",
        invalid_behavior=["Accept the networking coffee"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-twitter-001", target_type="procedural_constraint", domain="media",
        target_description="user's Twitter posting — abandoned after pivot to longform, no replacement",
        target_slot_id="tw::v1", topic="daily_twitter_posting",
        versions=[
            VersionSpec(value="post three insights to Twitter every weekday for the audience-building practice", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop posting to Twitter after pivoting to longform writing on the personal newsletter and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="An interesting industry thought just struck — am I posting it on Twitter?",
        required_behavior="No; the daily Twitter posting practice has been abandoned.",
        invalid_behavior=["Post the thought on Twitter"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-meal-prep-001", target_type="procedural_constraint", domain="food",
        target_description="user's Sunday meal prep — abandoned after partner moved in and started cooking, no replacement",
        target_slot_id="mealprep::v1", topic="sunday_meal_prep_practice",
        versions=[
            VersionSpec(value="batch-cook five lunches every Sunday afternoon to fill the fridge for the week", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the Sunday meal prep after the partner moved in and started handling weeknight dinners and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday afternoon — am I starting the meal prep for the week?",
        required_behavior="No; the Sunday meal prep practice has been abandoned.",
        invalid_behavior=["Start the meal prep for the week"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-marathon-001", target_type="procedural_constraint", domain="health",
        target_description="user's marathon training — abandoned after race-day-injury, no replacement",
        target_slot_id="mara::v1", topic="marathon_training_practice",
        versions=[
            VersionSpec(value="run a Saturday-morning long-run training session of 15 miles for marathon prep", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the long-run marathon training after the race-day injury and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I lacing up for the long run?",
        required_behavior="No; the long-run marathon training has been abandoned.",
        invalid_behavior=["Lace up for the 15-mile long run"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-paint-class-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's weekly painting class — abandoned after schedule conflict, no replacement",
        target_slot_id="pclass::v1", topic="weekly_painting_class_practice",
        versions=[
            VersionSpec(value="attend the Wednesday-evening painting class at the local art center every week", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop attending the Wednesday-evening painting class after the schedule conflict with the new evening commitment and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Wednesday evening — am I packing the brushes for class?",
        required_behavior="No; the painting class has been abandoned.",
        invalid_behavior=["Pack the brushes for class"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-bookreview-001", target_type="procedural_constraint", domain="writing",
        target_description="user's monthly book review — abandoned after burnout, no replacement",
        target_slot_id="brev::v1", topic="monthly_book_review_practice",
        versions=[
            VersionSpec(value="publish a 1500-word book review on the personal blog the last Friday of every month", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop publishing the monthly book review after burnout and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the last Friday of the month — am I publishing this month's book review?",
        required_behavior="No; the monthly book review practice has been abandoned.",
        invalid_behavior=["Publish this month's book review"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-meeting-prep-001", target_type="procedural_constraint", domain="management",
        target_description="user's daily morning meeting prep — abandoned after async-first move, no replacement",
        target_slot_id="mprep::v1", topic="morning_meeting_prep_practice",
        versions=[
            VersionSpec(value="prep for the day's first meeting every morning with a 30-minute agenda review and notes", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the morning meeting prep after moving the team to async-first communication and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 8:30am and there's a 9am meeting on my calendar — should I run the prep?",
        required_behavior="No; the morning meeting prep practice has been abandoned.",
        invalid_behavior=["Run the 30-min prep before the 9am meeting"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-trivia-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's weekly trivia night — abandoned after team dispersed, no replacement",
        target_slot_id="trivia::v1", topic="weekly_trivia_night_practice",
        versions=[
            VersionSpec(value="attend the Tuesday-evening pub trivia at the corner bar with the regular team every week", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop attending pub trivia after the regular team dispersed across cities and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Tuesday evening — am I heading to the corner bar for trivia?",
        required_behavior="No; the weekly trivia night has been abandoned.",
        invalid_behavior=["Head to the corner bar for trivia"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-mentor-002", target_type="procedural_constraint", domain="career",
        target_description="user's monthly mentoring of others — abandoned after mentees graduated, no replacement",
        target_slot_id="mentor2::v1", topic="monthly_mentoring_practice",
        versions=[
            VersionSpec(value="hold a one-hour mentorship session with each of three mentees on the first Saturday of every month", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the monthly mentorship sessions after all three mentees graduated to senior roles and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the first Saturday of the month — am I sending the mentorship invites?",
        required_behavior="No; the monthly mentorship practice has been abandoned.",
        invalid_behavior=["Send the mentorship invites"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # multi_version triple (4)
    _trip(_s(sample_id="p3-multi-trip-stack-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's frontend stack — four versions: React-CRA → Next.js → Remix → SvelteKit",
        target_slot_id="fe_stack::v1", topic="frontend_stack",
        versions=[
            VersionSpec(value="build new frontend apps with React Create-React-App as the default scaffold", polarity="prefer", session_introduced=1),
            VersionSpec(value="build new frontend apps with Next.js as the default scaffold", polarity="prefer", session_introduced=2),
            VersionSpec(value="build new frontend apps with Remix as the default scaffold", polarity="prefer", session_introduced=3),
            VersionSpec(value="build new frontend apps with SvelteKit as the default scaffold", polarity="prefer", session_introduced=4),
        ],
        current_query="I am starting a new side project frontend — which scaffold do I use?",
        required_behavior="Use SvelteKit as the scaffold.",
        invalid_behavior=["Use Create-React-App", "Use Next.js", "Use Remix"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-design-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's design tool — four versions: Sketch → Figma → Framer → Penpot",
        target_slot_id="design::v1", topic="design_tool",
        versions=[
            VersionSpec(value="design product mockups in Sketch on the Mac with Abstract for version control", polarity="prefer", session_introduced=1),
            VersionSpec(value="design product mockups in Figma with the team auto-save and shared libraries", polarity="prefer", session_introduced=2),
            VersionSpec(value="design product mockups in Framer with the interactive prototyping features", polarity="prefer", session_introduced=3),
            VersionSpec(value="design product mockups in Penpot self-hosted on the user's own server", polarity="prefer", session_introduced=4),
        ],
        current_query="A teammate asked where the latest mockup file is — point them at which tool?",
        required_behavior="Point them at the Penpot self-hosted instance.",
        invalid_behavior=["Point them at Sketch", "Point them at Figma", "Point them at Framer"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-finance-001", target_type="procedural_constraint", domain="finance",
        target_description="user's investing strategy — four versions: passive-index → factor-tilt → individual-stocks → cash-and-bonds",
        target_slot_id="invest::v1", topic="investing_strategy",
        versions=[
            VersionSpec(value="invest 100% in a passive S&P 500 index fund with no active management", polarity="constraint", session_introduced=1),
            VersionSpec(value="invest in a factor-tilted portfolio with small-cap and value tilts on top of the S&P 500 base", polarity="constraint", session_introduced=2),
            VersionSpec(value="invest by stock-picking individual companies based on fundamental analysis instead of indexing", polarity="constraint", session_introduced=3),
            VersionSpec(value="invest only in cash savings accounts and short-duration government bonds, no equities", polarity="constraint", session_introduced=4),
        ],
        current_query="My next paycheck just landed — where do I park the savings portion?",
        required_behavior="Park it in cash savings and short-duration government bonds.",
        invalid_behavior=["Buy passive S&P 500 index", "Buy factor-tilted portfolio", "Buy individual stock picks"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-fitness-class-001", target_type="object_preference", domain="health",
        target_description="user's primary fitness class — four versions: SoulCycle → Barry's-Bootcamp → CorePower-yoga → climbing-gym",
        target_slot_id="class::v1", topic="primary_fitness_class",
        versions=[
            VersionSpec(value="take the SoulCycle spin class three times a week as the primary fitness practice", polarity="prefer", session_introduced=1),
            VersionSpec(value="take the Barry's Bootcamp class three times a week as the primary fitness practice", polarity="prefer", session_introduced=2),
            VersionSpec(value="take the CorePower yoga class three times a week as the primary fitness practice", polarity="prefer", session_introduced=3),
            VersionSpec(value="climb at the bouldering gym three times a week as the primary fitness practice", polarity="prefer", session_introduced=4),
        ],
        current_query="It is Tuesday evening and the fitness slot is open — where do I head?",
        required_behavior="Head to the bouldering gym for climbing.",
        invalid_behavior=["Head to SoulCycle", "Head to Barry's Bootcamp", "Head to CorePower yoga"],
        failure_patterns=["multi_version"], subtype="strong")),

    # implicit_drift / gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-gn-attend-001", target_type="procedural_constraint", domain="career",
        target_description="user's conf-attendance rule — gradually narrowing without announcement: any → only-keynote-talks → only-keynote-talks + sponsored-travel",
        target_slot_id="conf_gn::v1", topic="conference_attend_drift_rule",
        versions=[
            VersionSpec(value="accept any conference invite that fits the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept conferences only when invited as a keynote speaker AND only when the conference fully sponsors travel", polarity="constraint", session_introduced=2),
        ],
        current_query="A regional conference invited me as a keynote with no travel sponsorship — accept?",
        required_behavior="Pass; user accepts only keynote slots with sponsored travel.",
        invalid_behavior=["Accept the unsponsored keynote"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),
]
