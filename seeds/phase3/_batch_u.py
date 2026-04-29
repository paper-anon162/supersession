"""Phase 3 batch U — 25 spines biased toward drift triples and multi
doublets to compensate for cluster L drops on compact non-drift × 3+ version."""

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


PHASE3_BATCH_U: list[Phase3GroupSpec] = [
    # multi_version doublet (8) — heavy underfill, no compact-realizer risk
    _doub(_s(sample_id="p3-multi-doub-bookshop-001", target_type="object_preference", domain="hobby",
        target_description="user's go-to bookshop — Strand-NYC → Powell's-online",
        target_slot_id="bookshop::v1", topic="go_to_bookshop",
        versions=[
            VersionSpec(value="buy books in person at the Strand bookstore in lower Manhattan", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy books online from Powell's Books with their used-paperback discount instead", polarity="prefer", session_introduced=2),
        ],
        current_query="I want to pick up the new biography everyone is talking about — where do I order from?",
        required_behavior="Order from Powell's Books online.",
        invalid_behavior=["Walk to the Strand bookstore"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-pacing-app-001", target_type="object_preference", domain="health",
        target_description="user's running-pace app — Strava-with-segments → COROS-watch-native",
        target_slot_id="run_app::v1", topic="running_pace_app",
        versions=[
            VersionSpec(value="track running pace in Strava with the segment leaderboards on", polarity="prefer", session_introduced=1),
            VersionSpec(value="track running pace natively on the COROS watch with no Strava sync", polarity="prefer", session_introduced=2),
        ],
        current_query="I am about to head out the door for the run — which app do I open?",
        required_behavior="Track on the COROS watch directly, no Strava.",
        invalid_behavior=["Open Strava with segments"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-doc-platform-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's design-doc platform — Google-Docs → Notion-shared-pages",
        target_slot_id="design_doc::v1", topic="design_doc_platform",
        versions=[
            VersionSpec(value="draft engineering design docs in Google Docs with comments threaded inline", polarity="prefer", session_introduced=1),
            VersionSpec(value="draft engineering design docs in Notion shared pages with the database backlinks instead", polarity="prefer", session_introduced=2),
        ],
        current_query="A teammate asked where to find the latest design doc — point them at which one?",
        required_behavior="Point them at the Notion shared page.",
        invalid_behavior=["Point them at the Google Docs file"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-eve-routine-001", target_type="procedural_constraint", domain="health",
        target_description="user's evening wind-down — herbal-tea-and-reading → ten-minute-meditation-and-stretch",
        target_slot_id="eve_routine::v1", topic="evening_wind_down_routine",
        versions=[
            VersionSpec(value="wind down every evening with a cup of herbal tea and thirty minutes of reading on the couch", polarity="constraint", session_introduced=1),
            VersionSpec(value="wind down every evening with ten minutes of meditation followed by a stretching sequence on the floor", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 9pm — should I put the kettle on for tea?",
        required_behavior="No tea; the routine is meditation plus stretching now.",
        invalid_behavior=["Put the kettle on for herbal tea"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-bday-flowers-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's gift for partner's birthday — flowers-and-card → handwritten-letter-and-experience",
        target_slot_id="partner_bday::v1", topic="partner_birthday_gift",
        versions=[
            VersionSpec(value="give the partner a bouquet of flowers and a store-bought card on their birthday", polarity="prefer", session_introduced=1),
            VersionSpec(value="give the partner a handwritten letter and a planned experience like a museum or concert on their birthday", polarity="prefer", session_introduced=2),
        ],
        current_query="My partner's birthday is next week — what do I plan for the gift?",
        required_behavior="Plan a handwritten letter and a planned experience like a museum or concert.",
        invalid_behavior=["Order a bouquet of flowers and a store-bought card"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-paint-001", target_type="object_preference", domain="hobby",
        target_description="user's painting medium — oil-on-canvas → watercolor-on-paper",
        target_slot_id="paint::v1", topic="painting_medium",
        versions=[
            VersionSpec(value="paint with oils on stretched canvas every Saturday afternoon in the studio", polarity="prefer", session_introduced=1),
            VersionSpec(value="paint with watercolors on cold-press paper every Saturday afternoon in the studio", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Saturday afternoon — which supplies do I pull out for today's painting session?",
        required_behavior="Pull out watercolors and cold-press paper.",
        invalid_behavior=["Pull out oils and stretched canvas"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-newsletter-001", target_type="object_preference", domain="learning",
        target_description="user's economics newsletter — Matt-Levine → Money-Stuff-replacement",
        target_slot_id="econ_news::v1", topic="economics_newsletter",
        versions=[
            VersionSpec(value="read Matt Levine's daily Money Stuff column on Bloomberg every weekday", polarity="prefer", session_introduced=1),
            VersionSpec(value="read the Concoda independent finance newsletter every weekday instead of Money Stuff", polarity="prefer", session_introduced=2),
        ],
        current_query="It is 9am and the morning newsletter slot is open — which one do I read?",
        required_behavior="Read the Concoda independent finance newsletter.",
        invalid_behavior=["Read Money Stuff on Bloomberg"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-1on1-format-001", target_type="procedural_constraint", domain="management",
        target_description="user's 1:1 format — verbal-walkthrough → shared-doc-async",
        target_slot_id="1on1_format::v1", topic="one_on_one_format",
        versions=[
            VersionSpec(value="run 1:1 conversations as a verbal walkthrough of the report's projects, no agenda doc", polarity="constraint", session_introduced=1),
            VersionSpec(value="run 1:1 conversations through a shared async doc filled in by the report 24 hours before, no verbal walkthrough", polarity="constraint", session_introduced=2),
        ],
        current_query="My next 1:1 is in two days — should I expect a verbal update or check the doc?",
        required_behavior="Check the shared async doc that the report fills in 24 hours before.",
        invalid_behavior=["Expect a verbal walkthrough"],
        failure_patterns=["multi_version"], subtype="strong")),

    # implicit_drift / repeated_use (4) — drift compact is reliable
    _drift(_s(sample_id="p3-drift-ru-pomodoro-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's deep-work timer — old 25-min pomodoros gradually replaced by 90-min flow blocks user runs daily",
        target_slot_id="pomo::v1", topic="deep_work_timer",
        versions=[
            VersionSpec(value="run deep work in 25-minute pomodoros with five-minute breaks between blocks", polarity="constraint", session_introduced=1),
            VersionSpec(value="run deep work in 90-minute uninterrupted flow blocks with one long break between blocks", polarity="constraint", session_introduced=2),
        ],
        current_query="I am sitting down to write — which timer do I set?",
        required_behavior="Set a 90-minute uninterrupted flow block.",
        invalid_behavior=["Set a 25-minute pomodoro"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-bagsource-001", target_type="object_preference", domain="hobby",
        target_description="user's everyday bag — old leather-tote gradually replaced by canvas-backpack user carries daily",
        target_slot_id="bag::v1", topic="everyday_bag",
        versions=[
            VersionSpec(value="carry a leather tote bag for the daily commute and errands", polarity="prefer", session_introduced=1),
            VersionSpec(value="carry a waxed-canvas backpack for the daily commute and errands instead", polarity="prefer", session_introduced=2),
        ],
        current_query="I am about to head out for the day — which bag do I grab from the closet?",
        required_behavior="Grab the waxed-canvas backpack.",
        invalid_behavior=["Grab the leather tote bag"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-banking-app-001", target_type="object_preference", domain="finance",
        target_description="user's daily banking app — old Chase mobile gradually replaced by Mercury app user opens daily",
        target_slot_id="bank_app::v1", topic="daily_banking_app",
        versions=[
            VersionSpec(value="check daily balances and transfers on the Chase mobile banking app", polarity="prefer", session_introduced=1),
            VersionSpec(value="check daily balances and transfers on the Mercury banking app for the small-business account", polarity="prefer", session_introduced=2),
        ],
        current_query="I want to confirm a wire arrived this morning — which app do I open?",
        required_behavior="Open the Mercury banking app.",
        invalid_behavior=["Open the Chase mobile banking app"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-podcast-format-001", target_type="object_preference", domain="hobby",
        target_description="user's podcast subscription queue — old true-crime gradually replaced by long-form business interviews user listens to weekly",
        target_slot_id="pod_queue::v1", topic="podcast_subscription_queue",
        versions=[
            VersionSpec(value="subscribe to true-crime podcasts as the weekly listening queue", polarity="prefer", session_introduced=1),
            VersionSpec(value="subscribe to long-form business interview podcasts as the weekly listening queue instead of true crime", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a new true-crime podcast about a 1970s case — add it to the queue?",
        required_behavior="Pass; the queue is long-form business interview podcasts now.",
        invalid_behavior=["Add the true-crime podcast to the queue"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    # implicit_drift / abandonment (3)
    _drift(_s(sample_id="p3-drift-aban-tennis-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's weekly tennis match — abandoned after partner moved away, no replacement",
        target_slot_id="tennis::v1", topic="weekly_tennis_match",
        versions=[
            VersionSpec(value="play a weekly singles tennis match with the regular partner every Saturday morning", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop playing the weekly tennis match after the regular partner moved away and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I packing the tennis bag for the match?",
        required_behavior="No; the weekly tennis match has been abandoned.",
        invalid_behavior=["Pack the tennis bag for the match"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-discord-001", target_type="procedural_constraint", domain="relationships",
        target_description="user's Discord-server hosting — abandoned after server went quiet, no replacement",
        target_slot_id="discord::v1", topic="discord_server_hosting",
        versions=[
            VersionSpec(value="host a 200-member Discord server with weekly Friday game nights for the community", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop hosting the Discord server entirely after the membership went quiet and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Friday evening — am I hopping into the Discord server to host game night?",
        required_behavior="No; the Discord server has been abandoned.",
        invalid_behavior=["Hop into Discord to host game night"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-sketch-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's daily sketch journal — abandoned after wrist injury, no replacement",
        target_slot_id="sketch::v1", topic="daily_sketch_journal_practice",
        versions=[
            VersionSpec(value="fill one page of the sketch journal every morning with a quick observational drawing", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop filling the sketch journal after the wrist injury and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is morning — am I picking up the sketchbook for today's page?",
        required_behavior="No; the sketch journal has been abandoned.",
        invalid_behavior=["Pick up the sketchbook for today's page"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # implicit_drift / gradual_narrowing (3)
    _drift(_s(sample_id="p3-drift-gn-vacation-001", target_type="object_preference", domain="travel",
        target_description="user's vacation destination — gradually narrowing without announcement: any city → only-coastal-cities → only-coastal-cities + Spanish-speaking",
        target_slot_id="vacation_dest::v1", topic="vacation_destination",
        versions=[
            VersionSpec(value="vacation in any city the user finds interesting in travel reading", polarity="prefer", session_introduced=1),
            VersionSpec(value="vacation only in coastal cities AND only in Spanish-speaking countries for the user's vacation choices", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend invited me to share a flat in Berlin for a two-week trip — accept?",
        required_behavior="Pass; user vacations only in coastal Spanish-speaking cities.",
        invalid_behavior=["Accept the Berlin flat share"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-watch-001", target_type="object_preference", domain="hobby",
        target_description="user's watch-collection criteria — gradually narrowing without announcement: any brand → mechanical-only → mechanical + under-1500-dollars",
        target_slot_id="watch::v1", topic="watch_collection_criteria",
        versions=[
            VersionSpec(value="add any watch the user finds interesting to the collection", polarity="prefer", session_introduced=1),
            VersionSpec(value="add only mechanical watches priced under fifteen hundred dollars to the collection", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend offered me a quartz Seiko at a great price — buy it for the collection?",
        required_behavior="Pass; user adds only mechanical watches under fifteen hundred dollars.",
        invalid_behavior=["Buy the quartz Seiko for the collection"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-content-001", target_type="object_preference", domain="learning",
        target_description="user's YouTube subscriptions — gradually narrowing without announcement: any channel → only-educational → only-educational + under-30-min-episodes",
        target_slot_id="yt_subs::v1", topic="youtube_subscription_criteria",
        versions=[
            VersionSpec(value="subscribe to any YouTube channel that catches the user's eye", polarity="prefer", session_introduced=1),
            VersionSpec(value="subscribe only to educational YouTube channels AND only ones whose episodes run under thirty minutes", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a 90-minute educational lecture series on YouTube — subscribe?",
        required_behavior="Pass; user subscribes only to educational channels with under-thirty-minute episodes.",
        invalid_behavior=["Subscribe to the 90-minute lecture series"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    # explicit_replacement (5) — 2 versions, lower compact-realizer risk than 3+
    _trip(_s(sample_id="p3-explicit-task-tracker-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's personal task tracker — explicitly replaces Trello with Linear",
        target_slot_id="task_tracker::v1", topic="personal_task_tracker",
        versions=[
            VersionSpec(value="track personal projects in a Trello board with kanban columns", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget Trello — track personal projects in Linear with the cycle and project hierarchy instead", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend asked which app I use for personal projects — what do I tell them?",
        required_behavior="Tell them Linear.",
        invalid_behavior=["Tell them Trello"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-cardio-style-001", target_type="procedural_constraint", domain="health",
        target_description="user's cardio choice — explicitly replaces road-running with rowing-machine",
        target_slot_id="cardio_style::v1", topic="cardio_workout_style",
        versions=[
            VersionSpec(value="run six miles on the road three times a week for cardio", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget road running — row 5000 meters on the home rowing machine three times a week for cardio instead", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Tuesday morning and the cardio slot is open — what do I do?",
        required_behavior="Row 5000 meters on the home rowing machine.",
        invalid_behavior=["Run six miles on the road"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-news-app-001", target_type="object_preference", domain="learning",
        target_description="user's morning news app — explicitly replaces Apple-News with Reuters-direct",
        target_slot_id="news_app::v1", topic="morning_news_app",
        versions=[
            VersionSpec(value="read morning news headlines on the Apple News app on iPhone", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget Apple News — read morning news directly on the Reuters website with no app", polarity="prefer", session_introduced=2),
        ],
        current_query="My phone notification is from Apple News about a breaking story — should I tap in?",
        required_behavior="No; news comes from the Reuters website directly now.",
        invalid_behavior=["Tap in to the Apple News notification"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-snack-001", target_type="object_preference", domain="food",
        target_description="user's afternoon snack — explicitly replaces granola-bar with apple-and-almond-butter",
        target_slot_id="snack::v1", topic="afternoon_snack",
        versions=[
            VersionSpec(value="eat a packaged granola bar at three in the afternoon for the daily snack break", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the granola bar — eat a sliced apple with almond butter at three in the afternoon for the daily snack break instead", polarity="prefer", session_introduced=2),
        ],
        current_query="It is 3pm — what is on the snack plate today?",
        required_behavior="Sliced apple with almond butter.",
        invalid_behavior=["A packaged granola bar"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-room-temp-001", target_type="procedural_constraint", domain="home",
        target_description="user's bedroom thermostat — explicitly replaces 72-degrees with 65-degrees-for-sleep",
        target_slot_id="thermostat::v1", topic="bedroom_thermostat_setting",
        versions=[
            VersionSpec(value="set the bedroom thermostat to 72 degrees Fahrenheit overnight every night", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget the 72 setting — set the bedroom thermostat to 65 degrees Fahrenheit overnight every night for better sleep", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 11pm — what temperature do I leave the bedroom thermostat at overnight?",
        required_behavior="Leave it at 65 degrees Fahrenheit overnight.",
        invalid_behavior=["Leave it at 72 degrees Fahrenheit"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    # narrowing (2) — 3-version narrowings, accept the cluster L drop risk
    _trip(_s(sample_id="p3-narrow-grocery-store-001", target_type="object_preference", domain="food",
        target_description="user's grocery-store rule — three explicit narrowings: any store → organic-only → organic + within-walking-distance",
        target_slot_id="grocery_store::v1", topic="grocery_store_rule",
        versions=[
            VersionSpec(value="shop at any grocery store that fits the user's day", polarity="prefer", session_introduced=1),
            VersionSpec(value="shop only at grocery stores stocked with mostly organic produce", polarity="prefer", session_introduced=2),
            VersionSpec(value="shop only at grocery stores with mostly organic produce AND within walking distance of home", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend recommended a great new organic store ten miles across town — go check it out?",
        required_behavior="Pass; the rule is organic AND within walking distance of home.",
        invalid_behavior=["Shop at any store", "Shop at any organic store", "Shop at a non-organic walking-distance store"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-job-app-pace-001", target_type="procedural_constraint", domain="career",
        target_description="user's job-application pace — three explicit narrowings: any rate → 5-per-week → 5-per-week + only-Mondays",
        target_slot_id="job_pace::v1", topic="job_application_pace",
        versions=[
            VersionSpec(value="apply to job postings at whatever rate fits the user's schedule", polarity="constraint", session_introduced=1),
            VersionSpec(value="apply to no more than five job postings per week", polarity="constraint", session_introduced=2),
            VersionSpec(value="apply to no more than five job postings per week AND only batched on Mondays", polarity="constraint", session_introduced=3),
        ],
        current_query="It is Wednesday and I have three application drafts ready — submit them today?",
        required_behavior="Pass; the rule is ≤5/week AND only batched on Mondays.",
        invalid_behavior=["Submit at any rate", "Submit any time under 5/week", "Submit on a non-Monday day under the cap"],
        failure_patterns=["narrowing"], subtype="multi_step")),
]
