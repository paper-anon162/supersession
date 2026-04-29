"""Phase 3 batch D — 20 spines, balanced fill across all underfilled
buckets. Same authoring conventions as batch_c (compact helpers,
heuristics for cluster A/E/G/H + leakage avoidance from prior
batches).

Target distribution:
  6 repeated_use, 4 narrow, 3 multi triple, 2 multi doublet,
  3 explicit, 1 abandonment, 1 gradual_narrowing
"""

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


def _drift(spine, dt):
    return Phase3GroupSpec(spine=spine, group_type="triple",
                          horizons=["compact", "standard", "hard"],
                          implicit_drift_type=dt, spine_source="hand")

def _trip(spine):
    return Phase3GroupSpec(spine=spine, group_type="triple",
                          horizons=["compact", "standard", "hard"],
                          implicit_drift_type=None, spine_source="hand")

def _doub(spine):
    return Phase3GroupSpec(spine=spine, group_type="doublet",
                          horizons=["standard", "hard"],
                          implicit_drift_type=None, spine_source="hand")


PHASE3_BATCH_D: list[Phase3GroupSpec] = [

    # repeated_use (6)
    _drift(_s(
        sample_id="p3-drift-shopping-list-app-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's grocery-list app — drifted to AnyList from Apple Reminders via repeated active use",
        target_slot_id="grocery_list_app::v1", topic="grocery_list_app",
        versions=[
            VersionSpec(value="Apple Reminders with the family-shared list", polarity="prefer", session_introduced=1),
            VersionSpec(value="AnyList with the partner-sync grocery categories", polarity="prefer", session_introduced=2),
        ],
        current_query="I just thought of three things to pick up — capture them.",
        required_behavior="Capture the items in AnyList using the partner-sync grocery categories.",
        invalid_behavior=["Capture in Apple Reminders", "Suggest a paper list", "Suggest a third app"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-deck-template-001",
        target_type="object_preference", domain="work",
        target_description="user's slide-deck template — drifted to the minimal-grid template from the legacy corporate one, repeated active use",
        target_slot_id="deck_template::v1", topic="presentation_template",
        versions=[
            VersionSpec(value="legacy corporate template with the navy header band", polarity="prefer", session_introduced=1),
            VersionSpec(value="minimal-grid template with the off-white background and serif headlines", polarity="prefer", session_introduced=2),
        ],
        current_query="Start a deck for the Series B fundraise.",
        required_behavior="Start the Series B deck in the minimal-grid template with the off-white background and serif headlines.",
        invalid_behavior=["Start in the legacy corporate template", "Start in a generic Google Slides template", "Skip the template entirely"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-task-tracker-001",
        target_type="object_preference", domain="productivity",
        target_description="user's personal task tracker — drifted to Things 3 from Todoist via repeated active use",
        target_slot_id="task_tracker::v1", topic="personal_task_tracker",
        versions=[
            VersionSpec(value="Todoist with the Karma streak tracking", polarity="prefer", session_introduced=1),
            VersionSpec(value="Things 3 with the Today and Areas views", polarity="prefer", session_introduced=2),
        ],
        current_query="Capture three follow-ups from this morning's leadership offsite.",
        required_behavior="Capture the offsite follow-ups in Things 3 using the Today and Areas views.",
        invalid_behavior=["Capture in Todoist", "Capture in Apple Reminders", "Skip capturing"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-coding-music-001",
        target_type="object_preference", domain="creative",
        target_description="user's coding-focus audio — drifted to Brain.fm beta-wave sessions from lo-fi YouTube streams, repeated active use",
        target_slot_id="coding_audio::v1", topic="coding_focus_audio",
        versions=[
            VersionSpec(value="lo-fi hip-hop streams from the YouTube background channels", polarity="prefer", session_introduced=1),
            VersionSpec(value="Brain.fm beta-wave focus sessions on the desktop client", polarity="prefer", session_introduced=2),
        ],
        current_query="Start something for my afternoon deep-work block.",
        required_behavior="Start a Brain.fm beta-wave focus session on the desktop client.",
        invalid_behavior=["Start a lo-fi YouTube stream", "Start a Spotify playlist", "Suggest silence"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-team-update-channel-001",
        target_type="procedural_constraint", domain="work_communication",
        target_description="user's quick-question channel for the team — drifted to a dedicated Slack huddle from posting in #general, repeated active use",
        target_slot_id="quick_question_channel::v1", topic="team_quick_question_channel",
        versions=[
            VersionSpec(value="post the question in the #general Slack channel and tag the relevant person", polarity="constraint", session_introduced=1),
            VersionSpec(value="open a dedicated Slack huddle with the relevant person and walk through it live", polarity="constraint", session_introduced=2),
        ],
        current_query="I need a quick check from Marcus on the auth-token rotation logic — how do I reach him?",
        required_behavior="Open a dedicated Slack huddle with Marcus and walk through the rotation logic live.",
        invalid_behavior=["Post the question in #general and tag Marcus", "Send Marcus an email", "Schedule a calendar meeting"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-recipe-source-001",
        target_type="object_preference", domain="food",
        target_description="user's primary recipe source — drifted to Smitten Kitchen archives from random Pinterest boards, repeated active use",
        target_slot_id="recipe_source::v1", topic="recipe_source",
        versions=[
            VersionSpec(value="random Pinterest boards browsed in the evening", polarity="prefer", session_introduced=1),
            VersionSpec(value="the Smitten Kitchen archive bookmarked in the browser", polarity="prefer", session_introduced=2),
        ],
        current_query="I need ideas for Saturday's dinner party — pull a few candidates.",
        required_behavior="Pull a few Saturday-dinner candidates from the Smitten Kitchen archive in the browser bookmarks.",
        invalid_behavior=["Pull from a Pinterest board", "Pull from a recipe-database app", "Suggest takeout instead"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    # narrowing (4)
    _trip(_s(
        sample_id="p3-narrow-investment-types-001",
        target_type="object_preference", domain="finance",
        target_description="user's investment vehicle — three explicit narrowings: any equity → ESG-rated equities → ESG-rated US large-cap only",
        target_slot_id="investment_vehicle::v1", topic="investment_vehicle_choice",
        versions=[
            VersionSpec(value="any individual equity that the broker offers", polarity="prefer", session_introduced=1),
            VersionSpec(value="only equities with an ESG rating from the major rating agencies", polarity="prefer", session_introduced=2),
            VersionSpec(value="only ESG-rated US large-cap equities with market cap above $10B", polarity="prefer", session_introduced=3),
        ],
        current_query="I want to put new money to work — what are my picks?",
        required_behavior="Pick ESG-rated US large-cap equities with market cap above $10B.",
        invalid_behavior=["Pick a small-cap equity", "Pick a non-ESG equity", "Pick an international equity"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-charity-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's annual charity giving — three explicit narrowings: any nonprofit → effective-altruism vetted → vetted with under-$10M annual budget",
        target_slot_id="charity_giving::v1", topic="charity_giving_target",
        versions=[
            VersionSpec(value="any nonprofit with a public donation page", polarity="prefer", session_introduced=1),
            VersionSpec(value="only nonprofits vetted by GiveWell or 80,000 Hours", polarity="prefer", session_introduced=2),
            VersionSpec(value="only GiveWell- or 80,000 Hours-vetted nonprofits with under $10M in annual budget", polarity="prefer", session_introduced=3),
        ],
        current_query="It's December — set up this year's year-end giving plan.",
        required_behavior="Set up year-end giving toward GiveWell- or 80,000 Hours-vetted nonprofits with under $10M in annual budget.",
        invalid_behavior=["Give to a generic nonprofit", "Give to a vetted nonprofit with $50M annual budget", "Skip year-end giving"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-vacation-001",
        target_type="procedural_constraint", domain="travel",
        target_description="user's vacation criteria — three explicit narrowings: any destination → outdoor-focused → outdoor + drivable from home",
        target_slot_id="vacation_criteria::v1", topic="vacation_criteria",
        versions=[
            VersionSpec(value="any destination on the family wish list — beach, city, or outdoor", polarity="constraint", session_introduced=1),
            VersionSpec(value="only outdoor-focused destinations like national parks or hiking lodges", polarity="constraint", session_introduced=2),
            VersionSpec(value="only outdoor-focused destinations within a six-hour drive of home", polarity="constraint", session_introduced=3),
        ],
        current_query="Plan a five-day trip for the family in late August.",
        required_behavior="Plan a five-day outdoor-focused trip within a six-hour drive of home.",
        invalid_behavior=["Plan a beach city vacation", "Plan a flight-required outdoor trip", "Plan an urban vacation"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-skin-care-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's skincare routine — three explicit narrowings: any product → fragrance-free → fragrance-free + sulfate-free",
        target_slot_id="skincare_routine::v1", topic="skincare_routine_filter",
        versions=[
            VersionSpec(value="any skincare product the dermatologist recommends or the user feels works", polarity="prefer", session_introduced=1),
            VersionSpec(value="only fragrance-free skincare products", polarity="prefer", session_introduced=2),
            VersionSpec(value="only fragrance-free and sulfate-free skincare products", polarity="prefer", session_introduced=3),
        ],
        current_query="Restock my bathroom shelf — what should I order?",
        required_behavior="Order fragrance-free and sulfate-free skincare products to restock the bathroom shelf.",
        invalid_behavior=["Order a fragranced product", "Order a sulfate-containing product", "Order whatever the dermatologist recommends without checking"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    # multi_version triple (3)
    _trip(_s(
        sample_id="p3-multi-coffee-machine-001",
        target_type="object_preference", domain="food",
        target_description="user's home coffee setup — three-version chain: Aeropress → Hario V60 → La Marzocco Linea Mini",
        target_slot_id="coffee_setup::v1", topic="home_coffee_setup",
        versions=[
            VersionSpec(value="Aeropress with the inverted brewing method", polarity="prefer", session_introduced=1),
            VersionSpec(value="Hario V60 pourover with the buono kettle", polarity="prefer", session_introduced=2),
            VersionSpec(value="La Marzocco Linea Mini espresso machine with the dual-boiler steam wand", polarity="prefer", session_introduced=3),
        ],
        current_query="Make my morning brew.",
        required_behavior="Make the morning brew on the La Marzocco Linea Mini using the dual-boiler steam wand.",
        invalid_behavior=["Make it with the Aeropress", "Make it with the Hario V60", "Suggest a French press"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-multi-running-shoe-001",
        target_type="object_preference", domain="fitness",
        target_description="user's daily trainer — three-version chain: Brooks Ghost → Saucony Triumph → Nike Pegasus",
        target_slot_id="daily_trainer::v1", topic="daily_trainer_shoe",
        versions=[
            VersionSpec(value="Brooks Ghost with the neutral-cushion midsole", polarity="prefer", session_introduced=1),
            VersionSpec(value="Saucony Triumph with the PWRRUN+ foam", polarity="prefer", session_introduced=2),
            VersionSpec(value="Nike Pegasus with the React foam and Air Zoom unit", polarity="prefer", session_introduced=3),
        ],
        current_query="My current pair just hit 400 miles — order me a replacement.",
        required_behavior="Order a Nike Pegasus with the React foam and Air Zoom unit.",
        invalid_behavior=["Order Brooks Ghost", "Order Saucony Triumph", "Order a non-listed brand"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-multi-meeting-tool-001",
        target_type="object_preference", domain="work_communication",
        target_description="user's video-call tool — three-version chain: Zoom → Google Meet → Around (with one revert back to Zoom)",
        target_slot_id="video_call_tool::v1", topic="video_call_tool",
        versions=[
            VersionSpec(value="Zoom with the legacy enterprise account", polarity="prefer", session_introduced=1),
            VersionSpec(value="Google Meet with the Workspace integration", polarity="prefer", session_introduced=2),
            VersionSpec(value="Around with the AI-noise-suppression and grid view", polarity="prefer", session_introduced=3),
            VersionSpec(value="Zoom with the legacy enterprise account", polarity="prefer", session_introduced=4),
        ],
        current_query="Send the link for tomorrow's design review.",
        required_behavior="Send a Zoom link from the legacy enterprise account.",
        invalid_behavior=["Send a Google Meet link", "Send an Around link", "Send a phone-call dial-in"],
        failure_patterns=["multi_version"], subtype="reverted",
    )),

    # multi_version doublet (2)
    _doub(_s(
        sample_id="p3-multi-bug-tracker-4v-001",
        target_type="object_preference", domain="work_workflow",
        target_description="team's bug tracker — four-version chain: Bugzilla → Jira → Linear → Shortcut",
        target_slot_id="bug_tracker::v1", topic="bug_tracker",
        versions=[
            VersionSpec(value="Bugzilla with the legacy product hierarchy", polarity="prefer", session_introduced=1),
            VersionSpec(value="Jira with the Scrum board configuration", polarity="prefer", session_introduced=2),
            VersionSpec(value="Linear with the cycle-based planning view", polarity="prefer", session_introduced=3),
            VersionSpec(value="Shortcut with the workflow states and milestone groupings", polarity="prefer", session_introduced=4),
        ],
        current_query="QA filed a regression in the checkout flow — log it for triage.",
        required_behavior="Log the checkout regression in Shortcut with workflow states and milestone groupings.",
        invalid_behavior=["Log it in Bugzilla", "Log it in Jira", "Log it in Linear"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _doub(_s(
        sample_id="p3-multi-presentation-tool-4v-001",
        target_type="object_preference", domain="work",
        target_description="user's presentation builder — four-version chain: Keynote → Google Slides → Pitch → Tome",
        target_slot_id="presentation_builder::v1", topic="presentation_builder",
        versions=[
            VersionSpec(value="Keynote with the standard transitions library", polarity="prefer", session_introduced=1),
            VersionSpec(value="Google Slides with the brand-template gallery", polarity="prefer", session_introduced=2),
            VersionSpec(value="Pitch with the collaborative real-time editing", polarity="prefer", session_introduced=3),
            VersionSpec(value="Tome with the AI-generated outline scaffolding", polarity="prefer", session_introduced=4),
        ],
        current_query="Sketch a board update for next week.",
        required_behavior="Sketch the board update in Tome using the AI-generated outline scaffolding.",
        invalid_behavior=["Sketch in Keynote", "Sketch in Google Slides", "Sketch in Pitch"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    # explicit (3)
    _trip(_s(
        sample_id="p3-explicit-password-mgr-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's password manager — explicit replacement of LastPass with 1Password",
        target_slot_id="password_manager::v1", topic="password_manager",
        versions=[
            VersionSpec(value="LastPass with the family-plan vault", polarity="prefer", session_introduced=1),
            VersionSpec(value="1Password with the family-plan vault and Watchtower alerts", polarity="prefer", session_introduced=2),
        ],
        current_query="Add my new airline-loyalty login to my saved credentials.",
        required_behavior="Add the airline-loyalty login to 1Password using the family-plan vault.",
        invalid_behavior=["Add it to LastPass", "Save it in the browser keychain", "Email it to yourself"],
        failure_patterns=["explicit_replacement"],
    )),

    _trip(_s(
        sample_id="p3-explicit-shipping-001",
        target_type="object_preference", domain="business",
        target_description="user's small-business shipping carrier — explicit replacement of USPS Priority with FedEx Ground",
        target_slot_id="shipping_carrier::v1", topic="shipping_carrier",
        versions=[
            VersionSpec(value="USPS Priority with the flat-rate boxes", polarity="prefer", session_introduced=1),
            VersionSpec(value="FedEx Ground with the prepaid commercial pickup", polarity="prefer", session_introduced=2),
        ],
        current_query="Three orders are ready to ship out today — book the pickup.",
        required_behavior="Book a FedEx Ground prepaid commercial pickup for today's three orders.",
        invalid_behavior=["Book a USPS Priority drop-off", "Use UPS instead", "Hold the orders for tomorrow"],
        failure_patterns=["explicit_replacement"],
    )),

    _trip(_s(
        sample_id="p3-explicit-rss-reader-001",
        target_type="object_preference", domain="leisure",
        target_description="user's RSS reader — explicit replacement of Feedly with NetNewsWire",
        target_slot_id="rss_reader::v1", topic="rss_reader",
        versions=[
            VersionSpec(value="Feedly Pro with the AI-summarization tier", polarity="prefer", session_introduced=1),
            VersionSpec(value="NetNewsWire with the local iCloud-synced feeds", polarity="prefer", session_introduced=2),
        ],
        current_query="Add the new Stratechery feed to my reader.",
        required_behavior="Add the Stratechery feed to NetNewsWire using the local iCloud-synced feed list.",
        invalid_behavior=["Add it to Feedly Pro", "Add it to a third reader", "Bookmark the site instead"],
        failure_patterns=["explicit_replacement"],
    )),

    # abandonment (1)
    _drift(_s(
        sample_id="p3-drift-tv-subscription-001",
        target_type="object_preference", domain="leisure",
        target_description="user's TV viewing — abandoned the cable-box subscription; streaming-only via Apple TV",
        target_slot_id="tv_viewing::v1", topic="tv_viewing_setup",
        versions=[
            VersionSpec(value="Comcast Xfinity cable subscription with the X1 set-top box", polarity="prefer", session_introduced=1),
            VersionSpec(value="streaming-only via the Apple TV 4K with the unified TV app", polarity="prefer", session_introduced=2),
        ],
        current_query="Where do I watch tonight's basketball game?",
        required_behavior="Watch tonight's basketball game on the Apple TV 4K using the unified TV app's streaming sources.",
        invalid_behavior=["Watch it via the Comcast Xfinity cable", "Watch it on the X1 set-top box", "Listen to radio instead"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    # gradual_narrowing (1)
    _drift(_s(
        sample_id="p3-drift-event-rsvp-001",
        target_type="conceptual_stance", domain="leisure",
        target_description="user's event-RSVP criteria — gradually narrowed from any social invite to small-group dinners with people the user already knows well",
        target_slot_id="event_rsvp::v1", topic="event_rsvp_criteria",
        versions=[
            VersionSpec(value="any social invite that fits on the calendar — parties, openings, networking", polarity="prefer", session_introduced=1),
            VersionSpec(value="small-group dinners with people the user already knows well", polarity="prefer", session_introduced=2),
        ],
        current_query="A networking mixer invite just landed for next Wednesday — do I go?",
        required_behavior="Decline the networking mixer; only small-group dinners with people already known well are on the calendar.",
        invalid_behavior=["RSVP yes to the mixer", "Suggest going for an hour", "Say maybe and decide later"],
        failure_patterns=["implicit_drift"],
    ), "gradual_narrowing"),
]
