"""Phase 3 batch M — 25 spines."""

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


PHASE3_BATCH_M: list[Phase3GroupSpec] = [
    # narrow (5)
    _trip(_s(sample_id="p3-narrow-deploy-window-2-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's mobile-app deploy schedule — three explicit narrowings: any time → weekly Tuesday → weekly Tuesday 10am with QA sign-off",
        target_slot_id="mobile_deploy::v1", topic="mobile_app_deploy_schedule",
        versions=[
            VersionSpec(value="ship mobile-app updates whenever the engineering team is ready", polarity="constraint", session_introduced=1),
            VersionSpec(value="ship mobile-app updates only on Tuesdays", polarity="constraint", session_introduced=2),
            VersionSpec(value="ship mobile-app updates only on Tuesdays at 10am after QA has signed off", polarity="constraint", session_introduced=3),
        ],
        current_query="The new checkout flow build is ready — when can it ship?",
        required_behavior="Ship the checkout build only on a Tuesday at 10am after QA has signed off.",
        invalid_behavior=["Ship as soon as engineering is ready", "Ship on Tuesday at any time", "Ship without QA sign-off"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-meeting-time-zone-001", target_type="interpersonal_boundary", domain="management",
        target_description="user's report meeting time zone — three explicit narrowings: any → 9am-5pm in user's zone → 9am-5pm in zones overlapping all participants",
        target_slot_id="report_meeting_tz::v1", topic="report_meeting_timezone",
        versions=[
            VersionSpec(value="schedule report meetings whenever the calendar shows availability", polarity="constraint", session_introduced=1),
            VersionSpec(value="schedule report meetings only between 9am and 5pm in the user's home time zone", polarity="constraint", session_introduced=2),
            VersionSpec(value="schedule report meetings only in the overlapping 9am-5pm window across the user's and the report's home time zones", polarity="constraint", session_introduced=3),
        ],
        current_query="Schedule a 30-minute review with Priya who is in Berlin.",
        required_behavior="Schedule the Berlin review only inside the overlapping 9am-5pm window across both time zones.",
        invalid_behavior=["Schedule whenever the calendar shows availability", "Schedule in the user's 9am-5pm without checking Berlin", "Schedule in Berlin's morning regardless of user's time"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-skill-investment-001", target_type="conceptual_stance", domain="learning",
        target_description="user's professional development time — three explicit narrowings: any topic → ML/AI focus → ML/AI focus + applied to a current project",
        target_slot_id="prodev_time::v1", topic="prodev_time_focus",
        versions=[
            VersionSpec(value="spend professional development time on any topic that's interesting", polarity="prefer", session_introduced=1),
            VersionSpec(value="spend professional development time only on machine learning or AI topics", polarity="prefer", session_introduced=2),
            VersionSpec(value="spend professional development time only on machine learning or AI topics that apply to a current production project", polarity="prefer", session_introduced=3),
        ],
        current_query="My company offers $2000 for professional development this year — what should I take?",
        required_behavior="Spend the budget on a course in machine learning or AI that applies to a current production project at the company.",
        invalid_behavior=["Take a course on any interesting topic", "Take an ML/AI course unrelated to current projects", "Take a leadership course"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-volunteer-001", target_type="interpersonal_boundary", domain="lifestyle",
        target_description="user's volunteering criteria — three explicit narrowings: any cause → mission-aligned → mission-aligned + leadership role",
        target_slot_id="volunteering::v1", topic="volunteering_criteria",
        versions=[
            VersionSpec(value="volunteer for any cause that asks for help", polarity="constraint", session_introduced=1),
            VersionSpec(value="volunteer only for causes aligned with the user's professional mission", polarity="constraint", session_introduced=2),
            VersionSpec(value="volunteer only for mission-aligned causes where the user can take a leadership role", polarity="constraint", session_introduced=3),
        ],
        current_query="The local food bank is recruiting weekend volunteers — sign up?",
        required_behavior="Decline; the food bank is not aligned with the user's professional mission and the user only takes leadership roles in volunteering.",
        invalid_behavior=["Sign up to volunteer", "Sign up only as a contributor", "Suggest a one-time donation"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-investment-001", target_type="conceptual_stance", domain="business",
        target_description="user's startup investment criteria — three explicit narrowings: any pitch → B2B SaaS → B2B SaaS with $1M+ ARR",
        target_slot_id="investment_criteria::v1", topic="startup_investment_criteria",
        versions=[
            VersionSpec(value="evaluate any startup pitch that comes through the network", polarity="prefer", session_introduced=1),
            VersionSpec(value="evaluate only B2B SaaS company pitches", polarity="prefer", session_introduced=2),
            VersionSpec(value="evaluate only B2B SaaS company pitches with at least $1 million in annual recurring revenue", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend introduced me to a B2B SaaS startup at $400K ARR — should I take the meeting?",
        required_behavior="Skip the meeting; the user only evaluates B2B SaaS pitches with at least $1 million in ARR.",
        invalid_behavior=["Take the meeting", "Take a 15-minute intro call", "Refer to another investor"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi triple (4)
    _trip(_s(sample_id="p3-multi-version-control-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's local git GUI — three-version chain: SourceTree → GitKraken → Tower",
        target_slot_id="git_gui::v1", topic="git_gui_tool",
        versions=[
            VersionSpec(value="Atlassian SourceTree with the legacy free desktop client", polarity="prefer", session_introduced=1),
            VersionSpec(value="GitKraken with the visual commit graph and the keyboard-driven workflows", polarity="prefer", session_introduced=2),
            VersionSpec(value="Tower with the macOS-native UI and the conflict-resolution wizard", polarity="prefer", session_introduced=3),
        ],
        current_query="Set up the git workflow on my new dev machine.",
        required_behavior="Set up the git workflow with Tower using the macOS-native UI and the conflict-resolution wizard.",
        invalid_behavior=["Set up SourceTree", "Set up GitKraken", "Use git from the command line only"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-task-runner-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's task automation tool — three-version chain: Make → Just → Task",
        target_slot_id="task_runner::v1", topic="task_automation_tool",
        versions=[
            VersionSpec(value="GNU Make with the legacy Makefile syntax", polarity="prefer", session_introduced=1),
            VersionSpec(value="just with the simpler justfile syntax and recipe parameters", polarity="prefer", session_introduced=2),
            VersionSpec(value="Task with the YAML-based Taskfile and the conditional execution operators", polarity="prefer", session_introduced=3),
        ],
        current_query="Set up a build automation file for the new microservice.",
        required_behavior="Set up the automation in Task using the YAML-based Taskfile and conditional execution operators.",
        invalid_behavior=["Set up GNU Make Makefile", "Set up just justfile", "Set up bash scripts only"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-clipboard-mgr-001", target_type="object_preference", domain="productivity",
        target_description="user's clipboard manager — three-version chain: Alfred clipboard → Maccy → Raycast",
        target_slot_id="clipboard::v1", topic="clipboard_manager",
        versions=[
            VersionSpec(value="Alfred Powerpack with the clipboard-history feature enabled", polarity="prefer", session_introduced=1),
            VersionSpec(value="Maccy with the menu-bar quick access and the search-as-you-type", polarity="prefer", session_introduced=2),
            VersionSpec(value="Raycast with the unified launcher and the AI-powered clipboard recall", polarity="prefer", session_introduced=3),
        ],
        current_query="Pull up the API key I copied earlier.",
        required_behavior="Pull up the API key from Raycast using the AI-powered clipboard recall.",
        invalid_behavior=["Pull from Alfred Powerpack", "Pull from Maccy", "Browse the system clipboard manually"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-website-builder-001", target_type="object_preference", domain="creative",
        target_description="user's marketing site builder — three-version chain: Wix → Squarespace → Framer",
        target_slot_id="site_builder::v1", topic="marketing_site_builder",
        versions=[
            VersionSpec(value="Wix with the legacy template gallery and drag-drop editor", polarity="prefer", session_introduced=1),
            VersionSpec(value="Squarespace with the standard typography library and the seven theme system", polarity="prefer", session_introduced=2),
            VersionSpec(value="Framer with the no-code visual editor and the published-from-design real-time CMS", polarity="prefer", session_introduced=3),
        ],
        current_query="Build the landing page for the new product launch.",
        required_behavior="Build the landing page in Framer using the no-code visual editor and published-from-design CMS.",
        invalid_behavior=["Build in Wix", "Build in Squarespace", "Build by hand-coding HTML"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    # multi doublet (4)
    _doub(_s(sample_id="p3-multi-runtime-deno-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's JavaScript runtime — four-version chain: Node 14 → Node 18 → Deno 1 → Bun",
        target_slot_id="js_runtime::v1", topic="javascript_runtime",
        versions=[
            VersionSpec(value="Node.js 14 with the npm package manager and CommonJS modules", polarity="prefer", session_introduced=1),
            VersionSpec(value="Node.js 18 with the npm package manager and ESM module support", polarity="prefer", session_introduced=2),
            VersionSpec(value="Deno 1 with the URL-based imports and the built-in TypeScript compiler", polarity="prefer", session_introduced=3),
            VersionSpec(value="Bun with the native bundler, transpiler, and the built-in test runner", polarity="prefer", session_introduced=4),
        ],
        current_query="Spin up the JavaScript runtime for the new internal CLI.",
        required_behavior="Spin up the runtime with Bun using the native bundler, transpiler, and built-in test runner.",
        invalid_behavior=["Spin up with Node.js 14", "Spin up with Node.js 18", "Spin up with Deno 1"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-event-bus-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's event bus — four-version chain: AWS SNS → Kafka → Pulsar → Inngest",
        target_slot_id="event_bus::v1", topic="event_bus",
        versions=[
            VersionSpec(value="AWS SNS with the legacy fan-out subscriptions", polarity="prefer", session_introduced=1),
            VersionSpec(value="Apache Kafka with the partitioned topics and the Confluent connectors", polarity="prefer", session_introduced=2),
            VersionSpec(value="Apache Pulsar with the topic tiered-storage and Functions runtime", polarity="prefer", session_introduced=3),
            VersionSpec(value="Inngest with the durable-execution model and the developer-first event API", polarity="prefer", session_introduced=4),
        ],
        current_query="Wire up the event-driven order-processing pipeline.",
        required_behavior="Wire up order-processing through Inngest using the durable-execution model and developer-first event API.",
        invalid_behavior=["Wire through AWS SNS", "Wire through Apache Kafka", "Wire through Apache Pulsar"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-team-comms-4v-001", target_type="object_preference", domain="work_communication",
        target_description="team's primary chat tool — four-version chain: HipChat → Slack → Microsoft Teams → Discord",
        target_slot_id="team_chat::v1", topic="team_chat_primary",
        versions=[
            VersionSpec(value="HipChat with the legacy room-based chat and the API integrations", polarity="prefer", session_introduced=1),
            VersionSpec(value="Slack with the channel-and-DM model and the enterprise grid configuration", polarity="prefer", session_introduced=2),
            VersionSpec(value="Microsoft Teams with the SharePoint integration and meeting recordings", polarity="prefer", session_introduced=3),
            VersionSpec(value="Discord with the topic-based servers and the voice-chat-first culture", polarity="prefer", session_introduced=4),
        ],
        current_query="Where do I post the announcement about the team off-site?",
        required_behavior="Post the off-site announcement in Discord using the topic-based server.",
        invalid_behavior=["Post in HipChat", "Post in Slack", "Post in Microsoft Teams"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-photo-print-4v-001", target_type="object_preference", domain="lifestyle",
        target_description="user's photo print service — four-version chain: Snapfish → Shutterfly → Mpix → Whitewall",
        target_slot_id="photo_print::v1", topic="photo_print_service",
        versions=[
            VersionSpec(value="Snapfish with the legacy 4x6 print packages", polarity="prefer", session_introduced=1),
            VersionSpec(value="Shutterfly with the unlimited 4x6 print plan and the photo-book templates", polarity="prefer", session_introduced=2),
            VersionSpec(value="Mpix with the Kodak professional paper and the metallic finish options", polarity="prefer", session_introduced=3),
            VersionSpec(value="Whitewall with the museum-grade aluminum-mounted prints and the gallery framing", polarity="prefer", session_introduced=4),
        ],
        current_query="Order prints of the engagement-shoot favorites.",
        required_behavior="Order the engagement-shoot prints through Whitewall using the museum-grade aluminum-mounted prints and gallery framing.",
        invalid_behavior=["Order through Snapfish", "Order through Shutterfly", "Order through Mpix"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    # explicit (3)
    _trip(_s(sample_id="p3-explicit-payment-processor-001", target_type="object_preference", domain="business",
        target_description="team's payment processor — explicit replacement of Stripe with Adyen",
        target_slot_id="payment_processor::v1", topic="payment_processor",
        versions=[
            VersionSpec(value="Stripe with the legacy charge API and the standard fee schedule", polarity="prefer", session_introduced=1),
            VersionSpec(value="Adyen with the unified-commerce platform and the dynamic 3D Secure", polarity="prefer", session_introduced=2),
        ],
        current_query="Charge the customer for the new annual subscription.",
        required_behavior="Charge the annual subscription through Adyen using the unified-commerce platform.",
        invalid_behavior=["Charge through Stripe", "Charge through PayPal", "Send a manual invoice"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-translation-platform-001", target_type="object_preference", domain="business",
        target_description="team's localization platform — explicit replacement of Lokalise with Crowdin",
        target_slot_id="localization::v1", topic="localization_platform",
        versions=[
            VersionSpec(value="Lokalise with the in-context editor and the GitHub-sync workflow", polarity="prefer", session_introduced=1),
            VersionSpec(value="Crowdin with the over-the-air mobile delivery and the AI-translation memory", polarity="prefer", session_introduced=2),
        ],
        current_query="Translate the new onboarding strings into Japanese, Korean, and German.",
        required_behavior="Translate the strings through Crowdin using the AI-translation memory.",
        invalid_behavior=["Translate through Lokalise", "Translate through Google Translate manually", "Skip translation"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-game-launcher-001", target_type="object_preference", domain="leisure",
        target_description="user's PC game launcher — explicit replacement of Steam with Heroic",
        target_slot_id="game_launcher::v1", topic="pc_game_launcher",
        versions=[
            VersionSpec(value="Steam with the legacy library client and the regional pricing", polarity="prefer", session_introduced=1),
            VersionSpec(value="Heroic with the GOG and Epic store integration and the open-source codebase", polarity="prefer", session_introduced=2),
        ],
        current_query="Install the new RPG release on my desktop.",
        required_behavior="Install the new RPG through Heroic using the GOG and Epic store integration.",
        invalid_behavior=["Install through Steam", "Install through a third-party launcher", "Skip installing"],
        failure_patterns=["explicit_replacement"])),

    # repeated_use (4)
    _drift(_s(sample_id="p3-drift-coffee-shop-001", target_type="object_preference", domain="food",
        target_description="user's afternoon coffee location — drifted to the corner roaster from the chain on the way to the office, repeated active use",
        target_slot_id="afternoon_coffee_loc::v1", topic="afternoon_coffee_location",
        versions=[
            VersionSpec(value="Starbucks on the corner of the office street with the morning rush queue", polarity="prefer", session_introduced=1),
            VersionSpec(value="independent corner roaster Mavelous Beans with the single-origin daily pour-over", polarity="prefer", session_introduced=2),
        ],
        current_query="It's 3pm — grab my afternoon coffee.",
        required_behavior="Grab the afternoon coffee from the independent corner roaster Mavelous Beans, single-origin daily pour-over.",
        invalid_behavior=["Grab from Starbucks", "Grab from a third café", "Skip the coffee"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-morning-routine-001", target_type="procedural_constraint", domain="lifestyle",
        target_description="user's morning routine — drifted to a 5am-start cold shower + journaling sequence from a 7am-start gradual wakeup, repeated active use",
        target_slot_id="morning_routine::v1", topic="morning_routine",
        versions=[
            VersionSpec(value="7am alarm followed by gradual wakeup with coffee and a slow scroll through the news", polarity="constraint", session_introduced=1),
            VersionSpec(value="5am alarm followed immediately by a cold shower then 20 minutes of journaling", polarity="constraint", session_introduced=2),
        ],
        current_query="Set my alarm and morning routine for tomorrow.",
        required_behavior="Set the alarm for 5am and structure the routine as cold shower then 20 minutes of journaling.",
        invalid_behavior=["Set alarm at 7am with gradual wakeup", "Set alarm at 6am", "Skip the morning routine"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-stand-up-tool-2-001", target_type="object_preference", domain="work_communication",
        target_description="user's standup format — drifted to a Loom video update from a written Slack thread, repeated active use",
        target_slot_id="standup_format::v1", topic="standup_format",
        versions=[
            VersionSpec(value="written Slack thread with the three-question template posted by 10am", polarity="prefer", session_introduced=1),
            VersionSpec(value="Loom video update of 60 seconds posted to the team channel by 10am", polarity="prefer", session_introduced=2),
        ],
        current_query="Send my Wednesday standup update.",
        required_behavior="Send the Wednesday standup as a 60-second Loom video update to the team channel by 10am.",
        invalid_behavior=["Send a written Slack-thread update", "Skip the update", "Schedule a live Zoom"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-paper-format-001", target_type="conceptual_stance", domain="learning",
        target_description="user's paper-reading note format — drifted to a one-sentence summary plus three-bullet implications from full-page detailed notes, repeated active use",
        target_slot_id="paper_notes_format::v1", topic="paper_notes_format",
        versions=[
            VersionSpec(value="full-page detailed notes covering motivation, methods, results, and personal commentary", polarity="prefer", session_introduced=1),
            VersionSpec(value="one-sentence summary plus three-bullet implications written in the user's notes app", polarity="prefer", session_introduced=2),
        ],
        current_query="I just finished the new RAG survey paper — capture the takeaways.",
        required_behavior="Capture the RAG-survey takeaways as a one-sentence summary plus three-bullet implications in the notes app.",
        invalid_behavior=["Write full-page detailed notes", "Skip note-taking", "Highlight passages in the PDF only"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    # abandonment (3)
    _drift(_s(sample_id="p3-drift-quarterly-planning-001", target_type="procedural_constraint", domain="management",
        target_description="user's quarterly planning offsite — abandoned the in-person planning offsite; remote-async via Loom + Notion only now",
        target_slot_id="quarterly_planning::v1", topic="quarterly_planning_offsite",
        versions=[
            VersionSpec(value="three-day in-person planning offsite at the rented venue with full-team attendance", polarity="constraint", session_introduced=1),
            VersionSpec(value="remote-async planning via Loom video updates and a shared Notion page over a two-week window", polarity="constraint", session_introduced=2),
        ],
        current_query="Q3 starts next month — set up the planning process.",
        required_behavior="Set up Q3 planning as remote-async via Loom video updates and a shared Notion page over a two-week window.",
        invalid_behavior=["Plan a three-day in-person offsite", "Plan a one-day virtual offsite", "Skip planning"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-learning-001", target_type="procedural_constraint", domain="learning",
        target_description="user's continuing-education credits — abandoned the formal university certificate program; informal evening lecture series only now",
        target_slot_id="continuing_ed::v1", topic="continuing_education",
        versions=[
            VersionSpec(value="enrolled formal university certificate program with the structured 12-week curriculum and graded assignments", polarity="constraint", session_introduced=1),
            VersionSpec(value="ad-hoc evening lecture series at the public library and online community talks with no certification", polarity="constraint", session_introduced=2),
        ],
        current_query="Block this month's continuing-education time on my calendar.",
        required_behavior="Block this month's continuing-education time for ad-hoc evening lecture series at the public library and online community talks.",
        invalid_behavior=["Block formal university certificate program time", "Block both formats", "Skip continuing education"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-investing-001", target_type="object_preference", domain="business",
        target_description="user's angel-investment style — abandoned the active angel-investing track; LP-only into vetted seed funds now",
        target_slot_id="angel_style::v1", topic="angel_investment_style",
        versions=[
            VersionSpec(value="active angel investing with personal checks of $10K-$25K into individual founders", polarity="prefer", session_introduced=1),
            VersionSpec(value="limited-partner only into two vetted seed funds with the fund managers handling all check writing", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend is raising for her seed round — should I write a check?",
        required_behavior="Pass on the personal check; the user only invests as an LP in vetted seed funds and lets the fund managers handle individual check writing.",
        invalid_behavior=["Write a personal $10K-$25K check", "Write a smaller personal check", "Connect the founder to other angels"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    # gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-skill-narrow-001", target_type="conceptual_stance", domain="learning",
        target_description="user's reading focus — gradually narrowed from any nonfiction to founder biographies only via cumulative preference signals",
        target_slot_id="reading_focus::v1", topic="reading_focus",
        versions=[
            VersionSpec(value="any nonfiction book that catches the user's attention", polarity="prefer", session_introduced=1),
            VersionSpec(value="founder-biography books only — no business strategy or self-help", polarity="prefer", session_introduced=2),
        ],
        current_query="Recommend my next book to start tonight.",
        required_behavior="Recommend a founder biography for tonight's read.",
        invalid_behavior=["Recommend a business strategy book", "Recommend a self-help book", "Recommend a memoir from a non-founder"],
        failure_patterns=["implicit_drift"]), "gradual_narrowing"),
]
