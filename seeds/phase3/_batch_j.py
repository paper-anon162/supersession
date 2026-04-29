"""Phase 3 batch J — 25 spines, balanced fill across all underfilled buckets."""

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


PHASE3_BATCH_J: list[Phase3GroupSpec] = [
    # narrow (5)
    _trip(_s(sample_id="p3-narrow-design-review-001", target_type="procedural_constraint", domain="work_workflow",
        target_description="user's design-doc circulation rule — three explicit narrowings: any → posted-with-RSVPs → posted with RSVPs and a deadline",
        target_slot_id="design_doc_circulation::v1", topic="design_doc_circulation",
        versions=[
            VersionSpec(value="circulate the design via Slack as soon as the draft feels ready", polarity="constraint", session_introduced=1),
            VersionSpec(value="circulate via posted invite with RSVP collected from each stakeholder", polarity="constraint", session_introduced=2),
            VersionSpec(value="circulate via posted invite with RSVPs collected and a 5-business-day comment deadline noted", polarity="constraint", session_introduced=3),
        ],
        current_query="Sarah's auth-refactor design is ready — share it with the stakeholders.",
        required_behavior="Share the auth-refactor design via posted invite with RSVPs collected and a 5-business-day comment deadline noted.",
        invalid_behavior=["Share via Slack ad-hoc", "Share via posted invite without a comment deadline", "Email it without RSVPs"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-promotion-001", target_type="procedural_constraint", domain="management",
        target_description="user's promotion-case requirement — three explicit narrowings: any submission → manager + skip-level approval → manager + skip approval + peer letter",
        target_slot_id="promotion_case::v1", topic="promotion_case_requirement",
        versions=[
            VersionSpec(value="any promotion case submitted to the committee with the manager's signature", polarity="constraint", session_introduced=1),
            VersionSpec(value="cases require both manager and skip-level approval before going to the committee", polarity="constraint", session_introduced=2),
            VersionSpec(value="cases require manager approval, skip-level approval, and one peer-engineer letter of support", polarity="constraint", session_introduced=3),
        ],
        current_query="Marcus is going up for L6 promotion next cycle — what's his case package?",
        required_behavior="Marcus's L6 case requires the manager approval, the skip-level approval, AND one peer-engineer letter of support.",
        invalid_behavior=["Submit with manager signature only", "Submit with manager and skip approval but no peer letter", "Submit with peer letter but missing skip approval"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-vendor-renewal-001", target_type="procedural_constraint", domain="business",
        target_description="user's vendor-renewal review — three explicit narrowings: any → annual → annual + benchmark-3-alternatives",
        target_slot_id="vendor_renewal::v1", topic="vendor_renewal_review",
        versions=[
            VersionSpec(value="renew vendor contracts as they come up with the existing terms", polarity="constraint", session_introduced=1),
            VersionSpec(value="formal review every renewal with the annual cost and usage analysis", polarity="constraint", session_introduced=2),
            VersionSpec(value="formal review with annual cost and usage analysis plus a benchmark of three alternative vendors", polarity="constraint", session_introduced=3),
        ],
        current_query="The Datadog renewal hits in March — get me ready.",
        required_behavior="Run the formal Datadog renewal review with the annual cost and usage analysis AND benchmark three alternative vendors.",
        invalid_behavior=["Auto-renew with existing terms", "Run cost analysis only", "Skip the renewal review"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-meeting-types-001", target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's external-stakeholder meeting requests — three explicit narrowings: any → with written agenda → with agenda + clear proposal-to-decide",
        target_slot_id="external_meeting::v1", topic="external_stakeholder_meeting",
        versions=[
            VersionSpec(value="accept any external-stakeholder meeting request that fits the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept only requests with a written agenda attached to the invite", polarity="constraint", session_introduced=2),
            VersionSpec(value="accept only requests with a written agenda AND a clear proposal-to-decide framing in the invite body", polarity="constraint", session_introduced=3),
        ],
        current_query="A potential partner from Acme requested a 30-minute intro call — RSVP?",
        required_behavior="RSVP only if Acme's request has a written agenda AND a clear proposal-to-decide framing.",
        invalid_behavior=["RSVP for any external request", "RSVP based on agenda alone", "RSVP based on proposal alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-paper-reading-001", target_type="conceptual_stance", domain="learning",
        target_description="user's research-paper reading rule — three explicit narrowings: any → seminal-only → seminal-only + ≥10 citations of recent extensions",
        target_slot_id="paper_reading_rule::v1", topic="research_paper_reading_rule",
        versions=[
            VersionSpec(value="read any research paper that catches the user's attention in the field", polarity="prefer", session_introduced=1),
            VersionSpec(value="read only seminal papers identified by the field's leading textbooks", polarity="prefer", session_introduced=2),
            VersionSpec(value="read only seminal papers that have at least ten citations of recent extensions in the past year", polarity="prefer", session_introduced=3),
        ],
        current_query="Pick the next paper for tonight's reading session.",
        required_behavior="Pick a seminal paper that has at least ten citations of recent extensions in the past year.",
        invalid_behavior=["Pick a paper that just caught the user's attention", "Pick a seminal paper without checking recent citations", "Pick a recent extension without the seminal anchor"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi triple (4)
    _trip(_s(sample_id="p3-multi-bookmark-tool-001", target_type="object_preference", domain="productivity",
        target_description="user's bookmark-management tool — three-version chain: Pinboard → Raindrop.io → Anybox",
        target_slot_id="bookmark_tool::v1", topic="bookmark_management_tool",
        versions=[
            VersionSpec(value="Pinboard with the legacy 11-dollar archival upgrade", polarity="prefer", session_introduced=1),
            VersionSpec(value="Raindrop.io with the nested-collections folder structure", polarity="prefer", session_introduced=2),
            VersionSpec(value="Anybox with the iCloud-sync and the offline reading queue", polarity="prefer", session_introduced=3),
        ],
        current_query="Save the Stratechery article I just read.",
        required_behavior="Save the Stratechery article in Anybox using iCloud-sync and the offline reading queue.",
        invalid_behavior=["Save in Pinboard", "Save in Raindrop.io", "Save as a browser bookmark only"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-prototyping-tool-001", target_type="object_preference", domain="creative",
        target_description="user's wireframing tool — three-version chain: Sketch → Figma → Penpot",
        target_slot_id="wireframe_tool::v1", topic="wireframing_tool",
        versions=[
            VersionSpec(value="Sketch with the legacy macOS-only license", polarity="prefer", session_introduced=1),
            VersionSpec(value="Figma with the multi-cursor real-time editing and Auto-Layout", polarity="prefer", session_introduced=2),
            VersionSpec(value="Penpot with the open-source self-hosted instance and the SVG-native files", polarity="prefer", session_introduced=3),
        ],
        current_query="Sketch the new onboarding flow for the design review.",
        required_behavior="Sketch the onboarding flow in Penpot using the open-source self-hosted instance.",
        invalid_behavior=["Sketch in Sketch", "Sketch in Figma", "Sketch on paper only"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-task-mgmt-personal-001", target_type="object_preference", domain="productivity",
        target_description="user's habit-tracking app — three-version chain: Strides → Streaks → Streaks (revert) — actually use a clean three-version: Strides → Streaks → Habitica",
        target_slot_id="habit_tracker::v1", topic="habit_tracker",
        versions=[
            VersionSpec(value="Strides with the legacy goal-counting tier", polarity="prefer", session_introduced=1),
            VersionSpec(value="Streaks with the simple six-habits limit and red-flame streak counter", polarity="prefer", session_introduced=2),
            VersionSpec(value="Habitica with the gamified RPG-style party system and quests", polarity="prefer", session_introduced=3),
        ],
        current_query="Log this morning's run.",
        required_behavior="Log the morning run in Habitica using the gamified RPG-style party system.",
        invalid_behavior=["Log in Strides", "Log in Streaks", "Log on paper"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-coaching-cadence-001", target_type="procedural_constraint", domain="management",
        target_description="user's executive coaching frequency — three-version chain with revert: monthly → biweekly → weekly → biweekly (reverted)",
        target_slot_id="coaching_cadence::v1", topic="executive_coaching_cadence",
        versions=[
            VersionSpec(value="monthly 60-minute coaching session on the first Monday", polarity="constraint", session_introduced=1),
            VersionSpec(value="biweekly 60-minute coaching session every other Monday", polarity="constraint", session_introduced=2),
            VersionSpec(value="weekly 30-minute coaching session every Monday morning", polarity="constraint", session_introduced=3),
            VersionSpec(value="biweekly 60-minute coaching session every other Monday", polarity="constraint", session_introduced=4),
        ],
        current_query="Block the next round of coaching engagements on my calendar.",
        required_behavior="Block biweekly 60-minute coaching sessions every other Monday for the next round.",
        invalid_behavior=["Block monthly 60-minute sessions", "Block weekly 30-minute sessions", "Skip blocking entirely"],
        failure_patterns=["multi_version"], subtype="reverted")),

    # multi doublet (4)
    _doub(_s(sample_id="p3-multi-graph-store-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's graph store — four-version chain: Neo4j community → Neo4j enterprise → Amazon Neptune → Memgraph",
        target_slot_id="graph_store::v1", topic="graph_store",
        versions=[
            VersionSpec(value="Neo4j community edition with the desktop-installed local database", polarity="prefer", session_introduced=1),
            VersionSpec(value="Neo4j enterprise with the causal cluster and the role-based access control", polarity="prefer", session_introduced=2),
            VersionSpec(value="Amazon Neptune with the SPARQL endpoint and the property-graph dual-mode", polarity="prefer", session_introduced=3),
            VersionSpec(value="Memgraph with the in-memory engine and the streaming triggers", polarity="prefer", session_introduced=4),
        ],
        current_query="Wire the new fraud-detection graph queries.",
        required_behavior="Wire the fraud-detection graph queries to Memgraph with the in-memory engine and streaming triggers.",
        invalid_behavior=["Wire to Neo4j community edition", "Wire to Neo4j enterprise", "Wire to Amazon Neptune"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-secret-mgr-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's secret-management tool — four-version chain: env vars → AWS Secrets Manager → HashiCorp Vault → 1Password Secrets Automation",
        target_slot_id="secrets_mgr::v1", topic="secret_management_tool",
        versions=[
            VersionSpec(value="environment variables in the .env file checked into the repo", polarity="prefer", session_introduced=1),
            VersionSpec(value="AWS Secrets Manager with the rotation Lambda triggers", polarity="prefer", session_introduced=2),
            VersionSpec(value="HashiCorp Vault self-hosted with the dynamic-database credentials", polarity="prefer", session_introduced=3),
            VersionSpec(value="1Password Secrets Automation with the K8s injector and the SSH cert authority", polarity="prefer", session_introduced=4),
        ],
        current_query="Store the new third-party API key for the analytics service.",
        required_behavior="Store the analytics API key in 1Password Secrets Automation using the K8s injector.",
        invalid_behavior=["Store in env vars in the repo", "Store in AWS Secrets Manager", "Store in HashiCorp Vault"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-feed-platform-4v-001", target_type="object_preference", domain="creative",
        target_description="user's content-feed platform — four-version chain: Twitter → Bluesky → Mastodon → Threads",
        target_slot_id="content_feed::v1", topic="content_feed_platform",
        versions=[
            VersionSpec(value="Twitter X with the legacy verified blue-check and the algorithmic feed", polarity="prefer", session_introduced=1),
            VersionSpec(value="Bluesky with the AT Protocol and the customizable feed algorithms", polarity="prefer", session_introduced=2),
            VersionSpec(value="Mastodon on the fosstodon.org instance with the chronological federation", polarity="prefer", session_introduced=3),
            VersionSpec(value="Threads with the Instagram-graph integration and the Fediverse compatibility", polarity="prefer", session_introduced=4),
        ],
        current_query="Post the launch announcement for the new product.",
        required_behavior="Post the launch announcement on Threads using the Instagram-graph integration and Fediverse compatibility.",
        invalid_behavior=["Post on Twitter X", "Post on Bluesky", "Post on Mastodon"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-domain-registrar-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's domain registrar — four-version chain: GoDaddy → Namecheap → Hover → Cloudflare Registrar",
        target_slot_id="domain_registrar::v1", topic="domain_registrar",
        versions=[
            VersionSpec(value="GoDaddy with the legacy ten-year auto-renewal", polarity="prefer", session_introduced=1),
            VersionSpec(value="Namecheap with the WhoisGuard privacy and the discount renewals", polarity="prefer", session_introduced=2),
            VersionSpec(value="Hover with the no-upsell pricing and the bundled email forwarding", polarity="prefer", session_introduced=3),
            VersionSpec(value="Cloudflare Registrar with the at-cost pricing and the integrated DNS", polarity="prefer", session_introduced=4),
        ],
        current_query="Register the new product domain.",
        required_behavior="Register the new product domain at Cloudflare Registrar using the at-cost pricing and integrated DNS.",
        invalid_behavior=["Register on GoDaddy", "Register on Namecheap", "Register on Hover"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    # explicit (4)
    _trip(_s(sample_id="p3-explicit-cli-tool-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's terminal multiplexer — explicit replacement of tmux with Zellij",
        target_slot_id="terminal_mux::v1", topic="terminal_multiplexer",
        versions=[
            VersionSpec(value="tmux with the manually-edited ~/.tmux.conf and vim-style keybindings", polarity="prefer", session_introduced=1),
            VersionSpec(value="Zellij with the layout files and the floating-pane mode", polarity="prefer", session_introduced=2),
        ],
        current_query="Set up a workspace for the auth-refactor debugging session.",
        required_behavior="Set up the workspace in Zellij using the layout files and floating-pane mode.",
        invalid_behavior=["Set up in tmux", "Set up in screen", "Skip the multiplexer"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-board-tool-001", target_type="object_preference", domain="management",
        target_description="user's board-meeting prep — explicit replacement of Diligent with BoardEffect",
        target_slot_id="board_prep::v1", topic="board_prep_tool",
        versions=[
            VersionSpec(value="Diligent Boards with the legacy PDF distribution and the chairperson workflow", polarity="prefer", session_introduced=1),
            VersionSpec(value="BoardEffect with the embedded analytics dashboards and the in-app voting", polarity="prefer", session_introduced=2),
        ],
        current_query="Distribute the Q1 board package.",
        required_behavior="Distribute the Q1 board package through BoardEffect using the embedded analytics dashboards.",
        invalid_behavior=["Distribute through Diligent Boards", "Email PDFs directly", "Skip distribution"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-stand-up-tool-001", target_type="object_preference", domain="work_workflow",
        target_description="team's daily-standup tool — explicit replacement of Geekbot with Standup-Bot",
        target_slot_id="standup_tool::v1", topic="standup_tool",
        versions=[
            VersionSpec(value="Geekbot with the legacy Slack scheduled prompts", polarity="prefer", session_introduced=1),
            VersionSpec(value="Standup-Bot with the rotating-questions configuration and the threaded summaries", polarity="prefer", session_introduced=2),
        ],
        current_query="Set up the new fraud-team's daily standup automation.",
        required_behavior="Set up the daily standup automation in Standup-Bot with the rotating-questions configuration.",
        invalid_behavior=["Set up in Geekbot", "Set up a manual reminder", "Skip standups"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-photo-edit-001", target_type="object_preference", domain="creative",
        target_description="user's photo editing tool — explicit replacement of Lightroom with Capture One",
        target_slot_id="photo_editor::v1", topic="photo_editor",
        versions=[
            VersionSpec(value="Adobe Lightroom Classic with the legacy catalog file", polarity="prefer", session_introduced=1),
            VersionSpec(value="Capture One Pro with the session-based file structure and tethered shooting", polarity="prefer", session_introduced=2),
        ],
        current_query="Edit the wedding photoshoot from Saturday.",
        required_behavior="Edit the wedding photoshoot in Capture One Pro using the session-based file structure.",
        invalid_behavior=["Edit in Adobe Lightroom Classic", "Edit in a free editor", "Skip editing"],
        failure_patterns=["explicit_replacement"])),

    # repeated_use (3)
    _drift(_s(sample_id="p3-drift-snippet-storage-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's code snippet storage — drifted to a personal Gist account from local text files, repeated active use",
        target_slot_id="snippet_storage::v1", topic="code_snippet_storage",
        versions=[
            VersionSpec(value="local text files in ~/snippets organized by language", polarity="prefer", session_introduced=1),
            VersionSpec(value="personal GitHub Gist account with the per-snippet cross-machine sync", polarity="prefer", session_introduced=2),
        ],
        current_query="Save the regex pattern I just figured out.",
        required_behavior="Save the regex pattern as a personal GitHub Gist with cross-machine sync.",
        invalid_behavior=["Save to a local text file in ~/snippets", "Save in a Slack DM to yourself", "Just remember it"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-meeting-recap-001", target_type="conceptual_stance", domain="work_communication",
        target_description="user's post-meeting recap style — drifted to a five-bullet summary sent within an hour from no recap, repeated active use",
        target_slot_id="meeting_recap::v1", topic="post_meeting_recap_style",
        versions=[
            VersionSpec(value="no formal recap — rely on participants' own notes", polarity="prefer", session_introduced=1),
            VersionSpec(value="a five-bullet summary sent to all attendees within one hour of meeting end", polarity="prefer", session_introduced=2),
        ],
        current_query="The customer-discovery call with Acme just wrapped — what's next?",
        required_behavior="Send a five-bullet summary to all Acme call attendees within one hour of the meeting end.",
        invalid_behavior=["Skip the recap and rely on participants' notes", "Send a long-form recap", "Wait until tomorrow to recap"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-feedback-channel-001", target_type="procedural_constraint", domain="management",
        target_description="user's where-to-give-feedback choice — drifted to a private DM at end-of-day from in-the-moment public correction, repeated active use",
        target_slot_id="feedback_channel::v1", topic="feedback_channel",
        versions=[
            VersionSpec(value="in-the-moment public correction during meetings or in shared channels", polarity="constraint", session_introduced=1),
            VersionSpec(value="a private DM at end-of-day summarizing the feedback in writing", polarity="constraint", session_introduced=2),
        ],
        current_query="Marcus interrupted Priya twice in the planning meeting just now — how do I address it?",
        required_behavior="Send Marcus a private DM at end-of-day summarizing the interruption-related feedback in writing.",
        invalid_behavior=["Correct Marcus in the meeting publicly", "Bring it up in the next 1:1", "Send Marcus a DM right now"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    # abandonment (3)
    _drift(_s(sample_id="p3-drift-recurring-call-001", target_type="procedural_constraint", domain="work_communication",
        target_description="user's external-board calls — abandoned the monthly board-update calls; quarterly investor letters only",
        target_slot_id="board_calls::v1", topic="board_update_communication",
        versions=[
            VersionSpec(value="monthly 60-minute board update call with the investors", polarity="constraint", session_introduced=1),
            VersionSpec(value="quarterly written investor letter with no live calls", polarity="constraint", session_introduced=2),
        ],
        current_query="It's the end of February — what do I owe the investors?",
        required_behavior="Owe nothing live; the next investor communication is the quarterly written letter at end of Q1.",
        invalid_behavior=["Schedule a monthly board update call", "Schedule a quick check-in call", "Send a monthly written summary"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-trade-show-001", target_type="procedural_constraint", domain="business",
        target_description="user's marketing-channel — abandoned the trade-show booth circuit; LinkedIn-content-only marketing now",
        target_slot_id="marketing_channel::v1", topic="primary_marketing_channel",
        versions=[
            VersionSpec(value="trade-show booth circuit with quarterly attendance at five major industry shows", polarity="constraint", session_introduced=1),
            VersionSpec(value="LinkedIn content marketing with weekly long-form posts and the company-page newsletter", polarity="constraint", session_introduced=2),
        ],
        current_query="The annual SaaStr conference is open for booth registration — sign up?",
        required_behavior="Skip the SaaStr booth registration; primary marketing is now LinkedIn content with weekly long-form posts.",
        invalid_behavior=["Sign up for the booth", "Sign up for a smaller exhibitor package", "Send a single attendee without a booth"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-old-cv-001", target_type="object_preference", domain="learning",
        target_description="user's resume / CV venue — abandoned the static PDF; LinkedIn profile + read.cv only now",
        target_slot_id="resume_venue::v1", topic="resume_venue",
        versions=[
            VersionSpec(value="static PDF resume hosted on the personal website", polarity="prefer", session_introduced=1),
            VersionSpec(value="LinkedIn profile combined with the read.cv minimalist single-page hosted profile", polarity="prefer", session_introduced=2),
        ],
        current_query="A recruiter reached out — what do I send them?",
        required_behavior="Send the recruiter the LinkedIn profile link plus the read.cv minimalist single-page profile.",
        invalid_behavior=["Send the static PDF resume", "Send a Word document", "Skip sending"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    # gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-spending-narrow-001", target_type="conceptual_stance", domain="business",
        target_description="user's discretionary spend criteria — gradually narrowed from any new tool to free-tier-or-zero-cost-only via cumulative preference signals",
        target_slot_id="discretionary_spend::v1", topic="discretionary_spend_criteria",
        versions=[
            VersionSpec(value="any new tool or service that promises productivity gain", polarity="prefer", session_introduced=1),
            VersionSpec(value="only free-tier or zero-cost open-source tools", polarity="prefer", session_introduced=2),
        ],
        current_query="A new note-taking app is on a $9/month plan — sign up?",
        required_behavior="Skip the $9/month plan; the user only adopts free-tier or zero-cost open-source tools now.",
        invalid_behavior=["Sign up for the $9/month plan", "Sign up for the annual plan to save", "Sign up for a free trial then convert"],
        failure_patterns=["implicit_drift"]), "gradual_narrowing"),
]
