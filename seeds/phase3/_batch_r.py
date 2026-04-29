"""Phase 3 batch R — 25 spines biased to multi_doublet, narrowing,
gradual_narrowing, drift, communication_boundary topic."""

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


PHASE3_BATCH_R: list[Phase3GroupSpec] = [
    # narrowing (5)
    _trip(_s(sample_id="p3-narrow-podcast-listen-001", target_type="object_preference", domain="learning",
        target_description="user's podcast-listen rule — three explicit narrowings: any → finance → finance + under-30-min episodes",
        target_slot_id="podcast::v1", topic="podcast_listen_rule",
        versions=[
            VersionSpec(value="add any podcast that sounds interesting to the daily listen queue", polarity="prefer", session_introduced=1),
            VersionSpec(value="add only finance podcasts to the daily listen queue", polarity="prefer", session_introduced=2),
            VersionSpec(value="add only finance podcasts with episodes under thirty minutes to the daily listen queue", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend recommended a 90-minute finance interview podcast — add it to my queue?",
        required_behavior="Pass; the rule is finance AND under-thirty-minute episodes.",
        invalid_behavior=["Add any interesting podcast", "Add any finance podcast", "Add a 90-minute non-finance podcast"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-newsletter-write-001", target_type="procedural_constraint", domain="writing",
        target_description="user's newsletter-publish rule — three explicit narrowings: any week → biweekly → biweekly + with-original-research-section",
        target_slot_id="newsletter_write::v1", topic="newsletter_publish_rule",
        versions=[
            VersionSpec(value="publish the personal newsletter whenever a draft happens to be ready", polarity="constraint", session_introduced=1),
            VersionSpec(value="publish the personal newsletter on a strict biweekly cadence", polarity="constraint", session_introduced=2),
            VersionSpec(value="publish the personal newsletter on a biweekly cadence AND only when the issue contains an original research section", polarity="constraint", session_introduced=3),
        ],
        current_query="It is publish day, the draft is ready, but I have no original research this issue — publish?",
        required_behavior="Hold the issue; the rule is biweekly AND original-research present.",
        invalid_behavior=["Publish whenever the draft is ready", "Publish on biweekly cadence without research", "Publish off-cadence with research"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-spending-cap-001", target_type="procedural_constraint", domain="finance",
        target_description="user's discretionary-spending rule — three explicit narrowings: any → under-100 → under-100 + after-30-day-wait",
        target_slot_id="spending::v1", topic="discretionary_spending_rule",
        versions=[
            VersionSpec(value="approve any discretionary purchase the user feels like making", polarity="constraint", session_introduced=1),
            VersionSpec(value="approve only discretionary purchases under one hundred dollars", polarity="constraint", session_introduced=2),
            VersionSpec(value="approve discretionary purchases only under one hundred dollars AND after a thirty-day cooling-off wait", polarity="constraint", session_introduced=3),
        ],
        current_query="I just spotted a 60-dollar gadget online and want to grab it tonight — buy it?",
        required_behavior="Pass; the rule is under-100 AND thirty-day cooling-off wait.",
        invalid_behavior=["Buy any discretionary item", "Buy on under-100 alone", "Buy after wait but over 100"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-dog-treat-001", target_type="object_preference", domain="home",
        target_description="user's dog-treat rule — three explicit narrowings: any treat → grain-free → grain-free + freeze-dried",
        target_slot_id="dog_treat::v1", topic="dog_treat_rule",
        versions=[
            VersionSpec(value="give the dog any treat from the pet store as a daily reward", polarity="prefer", session_introduced=1),
            VersionSpec(value="give the dog only grain-free treats as a daily reward", polarity="prefer", session_introduced=2),
            VersionSpec(value="give the dog only grain-free freeze-dried treats as a daily reward", polarity="prefer", session_introduced=3),
        ],
        current_query="The neighbor offered a grain-free baked biscuit for the dog — accept?",
        required_behavior="Decline; the rule is grain-free AND freeze-dried.",
        invalid_behavior=["Accept any treat", "Accept grain-free baked", "Accept non-grain-free freeze-dried"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-tea-brew-001", target_type="procedural_constraint", domain="food",
        target_description="user's morning-tea rule — three explicit narrowings: any tea → loose-leaf → loose-leaf + brewed-in-gaiwan",
        target_slot_id="tea::v1", topic="morning_tea_rule",
        versions=[
            VersionSpec(value="brew morning tea from any tea bag that happens to be in the cupboard", polarity="constraint", session_introduced=1),
            VersionSpec(value="brew morning tea only from loose-leaf tea, never from a tea bag", polarity="constraint", session_introduced=2),
            VersionSpec(value="brew morning tea only from loose-leaf tea AND only in a gaiwan with three quick infusions", polarity="constraint", session_introduced=3),
        ],
        current_query="It is morning, I have loose-leaf tea but only a Western teapot to brew it in — proceed?",
        required_behavior="Pass; the rule is loose-leaf AND brewed in a gaiwan.",
        invalid_behavior=["Brew any tea bag", "Brew loose-leaf in the Western teapot", "Brew a tea bag in the gaiwan"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi_version doublet (8)
    _doub(_s(sample_id="p3-multi-doub-todo-app-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's todo app — Things-3 → Todoist",
        target_slot_id="todo::v1", topic="todo_app",
        versions=[
            VersionSpec(value="track personal todos in Things 3 on the Mac with the daily-review feature", polarity="prefer", session_introduced=1),
            VersionSpec(value="track personal todos in Todoist on web and mobile, syncing across devices", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend asked which app I use for my personal todos — what do I tell them?",
        required_behavior="Tell them Todoist.",
        invalid_behavior=["Tell them Things 3"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-workout-time-001", target_type="procedural_constraint", domain="health",
        target_description="user's workout time — 6am-morning → lunch-break-noon",
        target_slot_id="workout_time::v1", topic="workout_time_of_day",
        versions=[
            VersionSpec(value="work out at 6am every weekday morning before the workday starts", polarity="constraint", session_introduced=1),
            VersionSpec(value="work out at noon during the daily lunch break instead, freeing up the morning", polarity="constraint", session_introduced=2),
        ],
        current_query="My alarm is set for 5:45am tomorrow — keep it for the morning workout?",
        required_behavior="Cancel the alarm; workouts happen at noon during lunch now.",
        invalid_behavior=["Keep the 5:45am alarm"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-coffee-method-001", target_type="object_preference", domain="food",
        target_description="user's coffee-brew method — V60-pourover → AeroPress",
        target_slot_id="coffee_method::v1", topic="coffee_brew_method",
        versions=[
            VersionSpec(value="brew morning coffee with a Hario V60 pour-over and a paper filter", polarity="prefer", session_introduced=1),
            VersionSpec(value="brew morning coffee with an AeroPress using the inverted method instead of the V60", polarity="prefer", session_introduced=2),
        ],
        current_query="It is morning — which gear do I pull from the cupboard for coffee?",
        required_behavior="Pull the AeroPress.",
        invalid_behavior=["Pull the V60 pour-over"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-blog-platform-001", target_type="object_preference", domain="writing",
        target_description="user's blog platform — Substack → self-hosted-Hugo",
        target_slot_id="blog_platform::v1", topic="blog_platform_choice",
        versions=[
            VersionSpec(value="publish the personal newsletter on Substack to handle the email list and payments", polarity="prefer", session_introduced=1),
            VersionSpec(value="publish the personal newsletter on a self-hosted Hugo site with a custom domain instead", polarity="prefer", session_introduced=2),
        ],
        current_query="I am drafting next week's issue — where do I push the post when it's done?",
        required_behavior="Push it to the self-hosted Hugo site.",
        invalid_behavior=["Push it to the Substack draft"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-running-shoe-001", target_type="object_preference", domain="health",
        target_description="user's running shoe — Hoka-Bondi → Saucony-Endorphin",
        target_slot_id="run_shoe::v1", topic="running_shoe_brand",
        versions=[
            VersionSpec(value="run in the Hoka Bondi cushioned trainer for daily mileage", polarity="prefer", session_introduced=1),
            VersionSpec(value="run in the Saucony Endorphin Speed lighter trainer for daily mileage", polarity="prefer", session_introduced=2),
        ],
        current_query="I am about to head out for the morning run — which trainer goes on?",
        required_behavior="Lace up the Saucony Endorphin Speed.",
        invalid_behavior=["Lace up the Hoka Bondi"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-meeting-notes-001", target_type="procedural_constraint", domain="management",
        target_description="user's meeting-notes practice — handwritten-paper → laptop-Obsidian",
        target_slot_id="meet_notes::v1", topic="meeting_notes_practice",
        versions=[
            VersionSpec(value="take meeting notes by hand in a paper notebook on the desk", polarity="constraint", session_introduced=1),
            VersionSpec(value="take meeting notes on the laptop directly into Obsidian instead of paper", polarity="constraint", session_introduced=2),
        ],
        current_query="I am walking into the next meeting — do I bring the paper notebook?",
        required_behavior="Leave the paper notebook; take notes in Obsidian on the laptop.",
        invalid_behavior=["Bring the paper notebook"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-cycling-route-001", target_type="object_preference", domain="hobby",
        target_description="user's Sunday cycling route — coastal-50-mile-loop → mountain-30-mile-climb",
        target_slot_id="cycle_route::v1", topic="sunday_cycling_route",
        versions=[
            VersionSpec(value="ride the coastal fifty-mile loop every Sunday morning on the road bike", polarity="prefer", session_introduced=1),
            VersionSpec(value="ride the mountain thirty-mile climb route every Sunday morning instead", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Sunday morning — which route am I rolling out to today?",
        required_behavior="Roll out to the mountain thirty-mile climb route.",
        invalid_behavior=["Roll out to the coastal fifty-mile loop"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-team-channel-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's team-comm channel — Slack-DMs → public-team-channel-only",
        target_slot_id="team_channel::v1", topic="team_communication_channel",
        versions=[
            VersionSpec(value="send team coordination questions in private Slack DMs to individual reports", polarity="constraint", session_introduced=1),
            VersionSpec(value="send team coordination questions only in the public team Slack channel where everyone can see them", polarity="constraint", session_introduced=2),
        ],
        current_query="I have a quick coordination question for one of my reports — DM them?",
        required_behavior="No; post the question in the public team channel.",
        invalid_behavior=["DM the report directly"],
        failure_patterns=["multi_version"], subtype="strong")),

    # multi_version triple (3)
    _trip(_s(sample_id="p3-multi-trip-headphone-001", target_type="object_preference", domain="hobby",
        target_description="user's daily headphones — four versions: AirPods-Pro → Sony-WH-1000XM5 → Sennheiser-Momentum → Bose-QC-Ultra",
        target_slot_id="headphone::v1", topic="daily_headphones",
        versions=[
            VersionSpec(value="use the AirPods Pro for daily listening on the commute", polarity="prefer", session_introduced=1),
            VersionSpec(value="use the Sony WH-1000XM5 over-ear headphones for daily listening on the commute", polarity="prefer", session_introduced=2),
            VersionSpec(value="use the Sennheiser Momentum 4 over-ear headphones for daily listening on the commute", polarity="prefer", session_introduced=3),
            VersionSpec(value="use the Bose QuietComfort Ultra over-ear headphones for daily listening on the commute", polarity="prefer", session_introduced=4),
        ],
        current_query="It is morning and I am heading to the commute — which headphones go in the bag?",
        required_behavior="Pack the Bose QuietComfort Ultra.",
        invalid_behavior=["Pack the AirPods Pro", "Pack the Sony WH-1000XM5", "Pack the Sennheiser Momentum 4"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-stretch-001", target_type="procedural_constraint", domain="health",
        target_description="user's evening-stretch routine — four versions: full-yoga-flow → foam-roller-only → 10-min-static-stretch → chiropractor-prescribed-sequence",
        target_slot_id="stretch::v1", topic="evening_stretch_routine",
        versions=[
            VersionSpec(value="run a full thirty-minute yoga flow every evening before bed", polarity="constraint", session_introduced=1),
            VersionSpec(value="use a foam roller for fifteen minutes every evening with no yoga flow", polarity="constraint", session_introduced=2),
            VersionSpec(value="run a ten-minute static-stretch routine every evening with no roller and no yoga", polarity="constraint", session_introduced=3),
            VersionSpec(value="run the chiropractor-prescribed mobility sequence every evening as posted on the fridge", polarity="constraint", session_introduced=4),
        ],
        current_query="It is 10pm — which routine am I running tonight?",
        required_behavior="Run the chiropractor-prescribed mobility sequence.",
        invalid_behavior=["Run the full yoga flow", "Run the foam-roller routine", "Run the ten-minute static stretch"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-budgeting-001", target_type="procedural_constraint", domain="finance",
        target_description="user's budgeting method — four versions: YNAB-zero-based → cash-envelope → 50-30-20-spreadsheet → no-budget-just-monthly-review",
        target_slot_id="budget::v1", topic="budgeting_method",
        versions=[
            VersionSpec(value="run a zero-based YNAB budget reviewed every Sunday evening", polarity="constraint", session_introduced=1),
            VersionSpec(value="run a cash envelope system pulled from the bank every Friday", polarity="constraint", session_introduced=2),
            VersionSpec(value="run a 50/30/20 percent spreadsheet budget updated monthly", polarity="constraint", session_introduced=3),
            VersionSpec(value="skip detailed budgeting and run only a monthly bank-statement review for outliers", polarity="constraint", session_introduced=4),
        ],
        current_query="It is Sunday evening — should I sit down for the YNAB review?",
        required_behavior="No; budgeting is just the monthly bank-statement review for outliers now.",
        invalid_behavior=["Sit down for YNAB", "Pull cash for envelopes", "Update the 50/30/20 spreadsheet"],
        failure_patterns=["multi_version"], subtype="strong")),

    # explicit_replacement (3)
    _trip(_s(sample_id="p3-explicit-pomodoro-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's deep-work technique — explicitly replaces 25-min-pomodoros with 90-min-flow-blocks",
        target_slot_id="deepwork::v1", topic="deep_work_technique",
        versions=[
            VersionSpec(value="run deep work in twenty-five-minute Pomodoro blocks with five-minute breaks", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget the Pomodoros — run deep work in ninety-minute uninterrupted flow blocks", polarity="constraint", session_introduced=2),
        ],
        current_query="I am sitting down to write — what timer do I set?",
        required_behavior="Set a ninety-minute uninterrupted flow block.",
        invalid_behavior=["Set a twenty-five-minute Pomodoro block"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-water-bottle-001", target_type="object_preference", domain="health",
        target_description="user's daily water bottle — explicitly replaces plastic-disposable with stainless-steel-Hydroflask",
        target_slot_id="water_bottle::v1", topic="daily_water_bottle",
        versions=[
            VersionSpec(value="use single-use plastic water bottles bought from the corner store for daily hydration", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget single-use plastic — use a stainless-steel HydroFlask refilled at home for daily hydration", polarity="prefer", session_introduced=2),
        ],
        current_query="I am heading out the door for the day — what do I grab for water?",
        required_behavior="Grab the stainless-steel HydroFlask from the kitchen.",
        invalid_behavior=["Grab a single-use plastic bottle from the store"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-photo-storage-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's photo storage — explicitly replaces iCloud-Photos with self-hosted-Immich",
        target_slot_id="photo_storage::v1", topic="photo_storage",
        versions=[
            VersionSpec(value="store all phone photos in iCloud Photos with the family-sharing feature on", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget iCloud Photos — store all phone photos on a self-hosted Immich server at home", polarity="prefer", session_introduced=2),
        ],
        current_query="My phone is asking me to upgrade iCloud storage — should I pay for the upgrade?",
        required_behavior="No; photos go to the self-hosted Immich server, not iCloud.",
        invalid_behavior=["Pay for the iCloud storage upgrade"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    # implicit_drift / repeated_use (3)
    _drift(_s(sample_id="p3-drift-ru-todo-method-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's todo method — old digital todo list gradually replaced by daily handwritten bullet journal user fills",
        target_slot_id="todo_method::v1", topic="daily_todo_method",
        versions=[
            VersionSpec(value="capture daily todos in the digital task app with reminders", polarity="constraint", session_introduced=1),
            VersionSpec(value="capture daily todos in a handwritten bullet journal opened on the desk every morning", polarity="constraint", session_introduced=2),
        ],
        current_query="A coworker asked where I keep my daily todos — point them at which one?",
        required_behavior="Point them at the handwritten bullet journal.",
        invalid_behavior=["Point them at the digital task app"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-lunchtime-001", target_type="procedural_constraint", domain="health",
        target_description="user's lunch routine — old desk-eat gradually replaced by daily walk-and-eat user does every day",
        target_slot_id="lunchtime::v1", topic="daily_lunch_routine",
        versions=[
            VersionSpec(value="eat lunch at the desk while answering emails every weekday", polarity="constraint", session_introduced=1),
            VersionSpec(value="eat lunch on a thirty-minute walk around the neighborhood every weekday, no email", polarity="constraint", session_introduced=2),
        ],
        current_query="It is noon and a coworker asked to chat at my desk over lunch — agree?",
        required_behavior="Decline the desk lunch; lunch is a thirty-minute walk now.",
        invalid_behavior=["Agree to the desk lunch chat"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-evening-read-001", target_type="object_preference", domain="learning",
        target_description="user's evening reading — old Kindle e-reader gradually replaced by hardcover library books user borrows weekly",
        target_slot_id="evening_read::v1", topic="evening_reading_format",
        versions=[
            VersionSpec(value="read evening books on the Kindle e-reader with the highlights export feature", polarity="prefer", session_introduced=1),
            VersionSpec(value="read evening books from hardcover library borrows picked up weekly at the local branch", polarity="prefer", session_introduced=2),
        ],
        current_query="My Kindle just told me a 30-day Kindle Unlimited promo expires today — sign up?",
        required_behavior="Skip the promo; evening reading is hardcover library borrows now.",
        invalid_behavior=["Sign up for the Kindle Unlimited promo"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    # implicit_drift / abandonment (1)
    _drift(_s(sample_id="p3-drift-aban-meditation-001", target_type="procedural_constraint", domain="health",
        target_description="user's morning meditation — abandoned after Headspace cancellation session, no replacement",
        target_slot_id="meditation::v1", topic="morning_meditation_practice",
        versions=[
            VersionSpec(value="run a ten-minute Headspace meditation every morning before coffee", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop running the morning meditation after canceling the Headspace subscription and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is morning, the coffee is brewing — am I sitting down for the meditation?",
        required_behavior="No; the morning meditation has been abandoned.",
        invalid_behavior=["Sit down for the Headspace meditation"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # implicit_drift / gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-gn-job-search-001", target_type="procedural_constraint", domain="career",
        target_description="user's job-application rule — gradually narrowing without announcement: any role → only-staff-eng → only-staff-eng-at-pre-IPO-companies",
        target_slot_id="job_app::v1", topic="job_application_rule",
        versions=[
            VersionSpec(value="apply to any open engineering role that catches the user's eye", polarity="constraint", session_introduced=1),
            VersionSpec(value="apply only to staff-engineer roles at pre-IPO companies for the current job search", polarity="constraint", session_introduced=2),
        ],
        current_query="A recruiter pinged me about a senior-engineer role at a public company — apply?",
        required_behavior="Pass; the user applies only to staff-engineer roles at pre-IPO companies.",
        invalid_behavior=["Apply to the senior-engineer role at a public company"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),
]
