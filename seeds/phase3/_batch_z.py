"""Phase 3 batch Z — 25 spines, drift + doublet heavy, final push to 375."""

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


PHASE3_BATCH_Z: list[Phase3GroupSpec] = [
    # multi_version doublet (8)
    _doub(_s(sample_id="p3-multi-doub-yoga-mat-001", target_type="object_preference", domain="health",
        target_description="user's yoga mat — Liforme-printed → Manduka-Pro-black",
        target_slot_id="yoga_mat::v1", topic="yoga_mat_choice",
        versions=[
            VersionSpec(value="practice yoga on the Liforme alignment-printed mat at the home studio", polarity="prefer", session_introduced=1),
            VersionSpec(value="practice yoga on the Manduka Pro plain-black mat at the home studio instead of the Liforme", polarity="prefer", session_introduced=2),
        ],
        current_query="It is morning yoga time — which mat do I roll out?",
        required_behavior="Roll out the Manduka Pro plain-black mat.",
        invalid_behavior=["Roll out the Liforme alignment-printed mat"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-charity-001", target_type="object_preference", domain="finance",
        target_description="user's charity recipient — local-food-bank → international-malaria-fund",
        target_slot_id="charity::v1", topic="primary_charity_recipient",
        versions=[
            VersionSpec(value="donate the monthly charity contribution to the local food bank for direct community impact", polarity="prefer", session_introduced=1),
            VersionSpec(value="donate the monthly charity contribution to the Against Malaria Foundation for high cost-effectiveness instead of the local food bank", polarity="prefer", session_introduced=2),
        ],
        current_query="The first of the month is here — where do I send the charity transfer?",
        required_behavior="Send to the Against Malaria Foundation.",
        invalid_behavior=["Send to the local food bank"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-pasta-night-001", target_type="procedural_constraint", domain="food",
        target_description="user's pasta-night cadence — weekly-sunday → biweekly-friday",
        target_slot_id="pasta_night::v1", topic="pasta_night_cadence",
        versions=[
            VersionSpec(value="cook pasta night at home every Sunday evening with a different shape each week", polarity="constraint", session_introduced=1),
            VersionSpec(value="cook pasta night at home every other Friday evening instead of every Sunday", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday evening — should I start boiling water for pasta night?",
        required_behavior="No; pasta night is now every other Friday.",
        invalid_behavior=["Boil water for Sunday pasta night"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-paint-storage-001", target_type="object_preference", domain="hobby",
        target_description="user's painting storage — flat-files → wall-mounted-rack",
        target_slot_id="paint_store::v1", topic="painting_storage",
        versions=[
            VersionSpec(value="store finished paintings in flat-files in the studio drawer cabinet", polarity="prefer", session_introduced=1),
            VersionSpec(value="store finished paintings on a wall-mounted vertical rack in the studio instead of flat-files", polarity="prefer", session_introduced=2),
        ],
        current_query="I just finished a new piece — where does it go for storage?",
        required_behavior="Slide it into the wall-mounted vertical rack.",
        invalid_behavior=["Slide it into the flat-file drawer"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-team-decision-001", target_type="procedural_constraint", domain="management",
        target_description="user's team decision-making — manager-decides-after-discussion → consensus-vote-among-team",
        target_slot_id="decision::v1", topic="team_decision_making",
        versions=[
            VersionSpec(value="make team-level decisions as the manager after a brief group discussion", polarity="constraint", session_introduced=1),
            VersionSpec(value="make team-level decisions through a consensus vote among all team members instead of manager call", polarity="constraint", session_introduced=2),
        ],
        current_query="The team disagrees on the launch date — should I just make the call?",
        required_behavior="No; run a consensus vote among the team members.",
        invalid_behavior=["Make the call as manager after the discussion"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-flight-class-002", target_type="object_preference", domain="travel",
        target_description="user's flight cabin — premium-economy → business-class",
        target_slot_id="cabin::v1", topic="long_haul_cabin_class",
        versions=[
            VersionSpec(value="fly long-haul international flights in premium-economy with the seat upgrade", polarity="prefer", session_introduced=1),
            VersionSpec(value="fly long-haul international flights in business-class with lie-flat seats instead of premium-economy", polarity="prefer", session_introduced=2),
        ],
        current_query="I am booking a long-haul flight to Tokyo — which cabin class do I pick?",
        required_behavior="Pick business-class with lie-flat seats.",
        invalid_behavior=["Pick premium-economy with seat upgrade"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-trade-cad-001", target_type="procedural_constraint", domain="finance",
        target_description="user's stock-trading cadence — weekly-rebalance → monthly-set-and-forget",
        target_slot_id="trade::v1", topic="brokerage_trading_cadence",
        versions=[
            VersionSpec(value="rebalance the brokerage portfolio every Friday afternoon by trimming and adding positions", polarity="constraint", session_introduced=1),
            VersionSpec(value="rebalance the brokerage portfolio once a month on the last business day with a single set-and-forget review instead of weekly trimming", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Friday afternoon — should I open the brokerage app to rebalance?",
        required_behavior="No; rebalance happens monthly on the last business day.",
        invalid_behavior=["Open the brokerage app for the weekly rebalance"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-skill-prac-001", target_type="procedural_constraint", domain="learning",
        target_description="user's skill-practice format — 30-minute-deliberate → 90-minute-deep-flow",
        target_slot_id="prac::v1", topic="skill_practice_format",
        versions=[
            VersionSpec(value="practice the new skill in thirty-minute focused deliberate-practice sessions every weekday", polarity="constraint", session_introduced=1),
            VersionSpec(value="practice the new skill in ninety-minute deep-flow blocks twice a week instead of daily thirty-minute sessions", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Tuesday at 7pm — which practice format am I running tonight?",
        required_behavior="A ninety-minute deep-flow block (one of the two weekly slots).",
        invalid_behavior=["A thirty-minute deliberate-practice session"],
        failure_patterns=["multi_version"], subtype="strong")),

    # implicit_drift / repeated_use (4)
    _drift(_s(sample_id="p3-drift-ru-bag-001", target_type="object_preference", domain="hobby",
        target_description="user's gym bag — old leather duffel gradually replaced by canvas tote user carries each gym day",
        target_slot_id="gym_bag::v1", topic="gym_bag",
        versions=[
            VersionSpec(value="carry the leather duffel bag to the gym for each session", polarity="prefer", session_introduced=1),
            VersionSpec(value="carry the canvas tote bag to the gym for each session instead of the leather duffel", polarity="prefer", session_introduced=2),
        ],
        current_query="I am heading to the gym — which bag do I grab from the closet?",
        required_behavior="Grab the canvas tote bag.",
        invalid_behavior=["Grab the leather duffel bag"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-monitor-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's external monitor — old 27-inch 4K LG gradually replaced by 32-inch ultrawide Samsung user uses daily",
        target_slot_id="monitor::v1", topic="external_monitor",
        versions=[
            VersionSpec(value="connect the laptop to a 27-inch 4K LG monitor for daily coding work", polarity="prefer", session_introduced=1),
            VersionSpec(value="connect the laptop to a 32-inch ultrawide Samsung monitor for daily coding work instead of the 27-inch LG", polarity="prefer", session_introduced=2),
        ],
        current_query="I am setting up the desk for a fresh week of coding — which monitor cable do I plug in?",
        required_behavior="Plug in the 32-inch ultrawide Samsung.",
        invalid_behavior=["Plug in the 27-inch 4K LG"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-tea-001", target_type="object_preference", domain="food",
        target_description="user's afternoon drink — old coffee gradually replaced by green tea user makes every afternoon",
        target_slot_id="aft_drink::v1", topic="afternoon_beverage",
        versions=[
            VersionSpec(value="brew an espresso at three in the afternoon for the daily caffeine break", polarity="prefer", session_introduced=1),
            VersionSpec(value="brew a cup of green tea at three in the afternoon for the daily caffeine break instead of espresso", polarity="prefer", session_introduced=2),
        ],
        current_query="It is 3pm and the energy is dipping — what do I make?",
        required_behavior="Brew a cup of green tea.",
        invalid_behavior=["Pull an espresso shot"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-team-recogn-001", target_type="procedural_constraint", domain="management",
        target_description="user's team recognition method — old quarterly bonus gradually replaced by monthly handwritten note user gives every month",
        target_slot_id="recogn::v1", topic="team_recognition_method",
        versions=[
            VersionSpec(value="recognize standout team work with a quarterly bonus check at the end of each quarter", polarity="constraint", session_introduced=1),
            VersionSpec(value="recognize standout team work with a monthly handwritten note from the manager left on the desk instead of a quarterly bonus", polarity="constraint", session_introduced=2),
        ],
        current_query="A direct report just shipped a great project this morning — how do I recognize it?",
        required_behavior="Write a handwritten note and leave it on their desk.",
        invalid_behavior=["Note it for the quarterly bonus"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    # implicit_drift / abandonment (3)
    _drift(_s(sample_id="p3-drift-aban-fundraiser-001", target_type="procedural_constraint", domain="community",
        target_description="user's annual fundraiser hosting — abandoned after relocation, no replacement",
        target_slot_id="fundraiser::v1", topic="annual_fundraiser_hosting",
        versions=[
            VersionSpec(value="host the annual literacy nonprofit fundraiser at the user's apartment every December", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop hosting the annual fundraiser after relocating to a smaller apartment and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is early December — am I sending out invites for the annual fundraiser?",
        required_behavior="No; the annual fundraiser hosting has been abandoned.",
        invalid_behavior=["Send out the annual fundraiser invites"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-strava-001", target_type="procedural_constraint", domain="health",
        target_description="user's Strava cycling log — abandoned after frame stolen, no replacement",
        target_slot_id="strava::v1", topic="strava_cycling_log_practice",
        versions=[
            VersionSpec(value="log every weekend ride on Strava with the segments and elevation auto-uploaded from the Wahoo computer", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop logging rides on Strava after the road bike was stolen and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday morning — am I starting the Strava log for today's ride?",
        required_behavior="No; the Strava cycling log has been abandoned.",
        invalid_behavior=["Start the Strava log"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-poker-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's monthly poker night — abandoned after group dispersed, no replacement",
        target_slot_id="poker::v1", topic="monthly_poker_night_practice",
        versions=[
            VersionSpec(value="host a monthly Friday-evening poker night at the apartment with the regular six-person group", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop hosting the monthly poker night after the regular group dispersed across cities and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the last Friday of the month — am I setting out the poker chips?",
        required_behavior="No; the monthly poker night has been abandoned.",
        invalid_behavior=["Set out the poker chips"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # implicit_drift / gradual_narrowing (3)
    _drift(_s(sample_id="p3-drift-gn-vacation-002", target_type="object_preference", domain="travel",
        target_description="user's vacation rule — gradually narrowing without announcement: any destination → only-warm-climate → only-warm-climate + with-direct-flight",
        target_slot_id="vac::v1", topic="vacation_destination_rule",
        versions=[
            VersionSpec(value="vacation in any destination the user finds interesting in travel media", polarity="prefer", session_introduced=1),
            VersionSpec(value="vacation only in warm-climate destinations AND only ones reachable by a direct flight from the user's home airport", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend invited me to share a flat in Reykjavik for a week — accept?",
        required_behavior="Pass; user vacations only in warm-climate destinations with direct flights.",
        invalid_behavior=["Accept the Reykjavik flat share"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-attire-001", target_type="object_preference", domain="hobby",
        target_description="user's clothing rule — gradually narrowing without announcement: any item → only-natural-fibers → only-natural-fibers + neutral-tones-only",
        target_slot_id="attire::v1", topic="clothing_purchase_rule",
        versions=[
            VersionSpec(value="buy any clothing item that catches the user's eye when shopping", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only clothing made of natural fibers like wool and linen AND only in neutral tones like black, gray, navy, or beige", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a bright red wool sweater on sale — buy it?",
        required_behavior="Pass; user buys only natural-fiber clothing in neutral tones.",
        invalid_behavior=["Buy the bright red wool sweater"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-app-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's phone app install rule — gradually narrowing without announcement: any app → only-utility-apps → only-utility-apps + paid-no-ads",
        target_slot_id="app_install::v1", topic="phone_app_install_rule",
        versions=[
            VersionSpec(value="install any phone app the user finds interesting in the App Store", polarity="prefer", session_introduced=1),
            VersionSpec(value="install only utility apps for productivity AND only paid versions with no ads or freemium tier", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a free utility app for tracking habits — install it?",
        required_behavior="Pass; user installs only paid utility apps.",
        invalid_behavior=["Install the free habit-tracking utility app"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    # explicit_replacement (5)
    _trip(_s(sample_id="p3-explicit-walking-001", target_type="procedural_constraint", domain="health",
        target_description="user's daily walking step goal — explicitly replaces 10000-steps with 7000-steps",
        target_slot_id="steps::v1", topic="daily_walking_step_goal",
        versions=[
            VersionSpec(value="aim for 10,000 steps every day on the daily walk", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget the 10,000-step target — aim for 7,000 steps every day on the daily walk for a sustainable pace instead", polarity="constraint", session_introduced=2),
        ],
        current_query="My fitness ring shows 6,500 steps at 9pm — should I walk extra to hit the goal?",
        required_behavior="No; 7,000 is the goal now, just a short loop to clear that.",
        invalid_behavior=["Walk to hit 10,000 steps"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-paint-medium-001", target_type="object_preference", domain="hobby",
        target_description="user's painting medium — explicitly replaces oil-on-canvas with acrylic-on-board",
        target_slot_id="paint_medium::v1", topic="painting_medium",
        versions=[
            VersionSpec(value="paint with oils on stretched canvas every weekend in the home studio", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget oils on canvas — paint with acrylics on prepared wood board every weekend in the home studio for faster drying time instead", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Saturday morning — what do I pull out for the weekend painting session?",
        required_behavior="Pull out acrylics and a prepared wood board.",
        invalid_behavior=["Pull out oils and stretched canvas"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-bookbuy-002", target_type="procedural_constraint", domain="learning",
        target_description="user's book-buy decision — explicitly replaces buy-on-impulse with library-first-then-buy",
        target_slot_id="book_decision::v1", topic="book_buying_decision_rule",
        versions=[
            VersionSpec(value="buy any book the user wants to read on impulse the moment it catches the user's eye", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget impulse-buying — borrow any book from the public library first and only buy a copy if the user finishes the borrowed copy and wants to keep it instead", polarity="constraint", session_introduced=2),
        ],
        current_query="A friend recommended a fascinating new memoir — should I order a copy?",
        required_behavior="No; check the public library for a borrow first.",
        invalid_behavior=["Order a copy on impulse"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-meeting-followup-001", target_type="procedural_constraint", domain="management",
        target_description="user's meeting followup — explicitly replaces written-summary-email with shared-doc-link",
        target_slot_id="followup::v1", topic="meeting_followup_format",
        versions=[
            VersionSpec(value="send a written summary email after every team meeting with action items in the body of the email", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget the summary emails — send a shared doc link after every team meeting where action items live in a single source-of-truth doc instead", polarity="constraint", session_introduced=2),
        ],
        current_query="The team meeting just ended — am I drafting the summary email now?",
        required_behavior="No; send the shared doc link with action items in the doc.",
        invalid_behavior=["Draft the summary email"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-music-listen-001", target_type="object_preference", domain="hobby",
        target_description="user's primary listening setup — explicitly replaces wireless-AirPods with wired-IEMs",
        target_slot_id="listen::v1", topic="primary_listening_setup",
        versions=[
            VersionSpec(value="listen to all music on the wireless AirPods Pro for daily commute and home listening", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the wireless AirPods — listen to all music on the wired Moondrop Aria IEMs for higher-resolution audio instead", polarity="prefer", session_introduced=2),
        ],
        current_query="I am about to head out for the commute — which earphones go in the bag?",
        required_behavior="Pack the wired Moondrop Aria IEMs.",
        invalid_behavior=["Pack the wireless AirPods Pro"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    # narrowing (2)
    _trip(_s(sample_id="p3-narrow-event-host-001", target_type="procedural_constraint", domain="community",
        target_description="user's event-hosting rule — three explicit narrowings: any → friend-circle-only → friend-circle-only + RSVP-required",
        target_slot_id="host::v1", topic="event_hosting_rule",
        versions=[
            VersionSpec(value="host any community event at the user's apartment that fits the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="host events only when guests are from the user's existing friend circle, no acquaintances or strangers", polarity="constraint", session_introduced=2),
            VersionSpec(value="host events only with friend-circle guests AND only when every guest RSVPs at least 48 hours in advance", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend asked me to host a casual dinner Friday for some of her acquaintances — agree?",
        required_behavior="Pass; the rule is friend-circle only AND with 48-hour RSVPs.",
        invalid_behavior=["Host any event", "Host friend-circle-only without RSVP", "Host RSVP-required for acquaintances"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-shopping-rule-001", target_type="procedural_constraint", domain="finance",
        target_description="user's online-shopping rule — three explicit narrowings: any → tab-and-wait-24-hr → tab-and-wait-24-hr + spousal-approval",
        target_slot_id="shop_rule::v1", topic="online_shopping_rule",
        versions=[
            VersionSpec(value="buy any item the user clicks add-to-cart on online without delay", polarity="constraint", session_introduced=1),
            VersionSpec(value="leave the item in the cart for at least 24 hours before checkout to cool off the impulse", polarity="constraint", session_introduced=2),
            VersionSpec(value="leave the item in the cart for at least 24 hours AND get explicit spousal approval before checkout", polarity="constraint", session_introduced=3),
        ],
        current_query="An item has been in my cart for 2 days and I still want it — checkout now?",
        required_behavior="Pass; rule is 24-hour wait AND spousal approval.",
        invalid_behavior=["Checkout immediately", "Checkout after 24 hours alone", "Checkout with spousal approval but no 24-hour wait"],
        failure_patterns=["narrowing"], subtype="multi_step")),
]
