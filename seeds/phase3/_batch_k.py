"""Phase 3 batch K — 25 spines, balanced fill."""

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


PHASE3_BATCH_K: list[Phase3GroupSpec] = [
    # narrow (5)
    _trip(_s(sample_id="p3-narrow-pull-request-base-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's PR base-branch rule — three explicit narrowings: any → main only → main only with rebased commits",
        target_slot_id="pr_base::v1", topic="pr_base_branch_rule",
        versions=[
            VersionSpec(value="open pull requests against any branch in the repository", polarity="constraint", session_introduced=1),
            VersionSpec(value="open pull requests only against the main branch", polarity="constraint", session_introduced=2),
            VersionSpec(value="open pull requests only against main with the feature commits rebased into single squashed history", polarity="constraint", session_introduced=3),
        ],
        current_query="Marcus is opening his first PR after onboarding — what should he target?",
        required_behavior="Marcus targets main with his commits rebased into a single squashed history.",
        invalid_behavior=["Open against any feature branch", "Open against main without rebasing", "Open against the develop branch"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-customer-call-001", target_type="procedural_constraint", domain="business",
        target_description="user's customer-call attendance rule — three explicit narrowings: any → ARR-above-$50K → ARR above $50K AND committed roadmap input",
        target_slot_id="customer_call::v1", topic="customer_call_attendance",
        versions=[
            VersionSpec(value="join any customer call that the success team requests", polarity="constraint", session_introduced=1),
            VersionSpec(value="join customer calls only when the customer's ARR is above fifty thousand dollars", polarity="constraint", session_introduced=2),
            VersionSpec(value="join calls only for customers above $50K ARR who have committed roadmap input expectations", polarity="constraint", session_introduced=3),
        ],
        current_query="Success wants me on a call with Acme tomorrow — should I join?",
        required_behavior="Join the Acme call only if Acme is above $50K ARR AND has committed roadmap input expectations.",
        invalid_behavior=["Join any call success requests", "Join based on ARR alone", "Join based on roadmap expectations alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-launch-spec-001", target_type="conceptual_stance", domain="work_workflow",
        target_description="user's launch-spec acceptance criteria — three explicit narrowings: any spec → with rollback plan → with rollback plan + measured success metric",
        target_slot_id="launch_spec_accept::v1", topic="launch_spec_acceptance",
        versions=[
            VersionSpec(value="approve any launch spec the team brings forward", polarity="prefer", session_introduced=1),
            VersionSpec(value="approve only launch specs that include a documented rollback plan", polarity="prefer", session_introduced=2),
            VersionSpec(value="approve only specs with a documented rollback plan AND a measurable success metric defined upfront", polarity="prefer", session_introduced=3),
        ],
        current_query="The new pricing-page launch spec is in front of me — green-light or block?",
        required_behavior="Green-light only if the pricing-page launch spec has both a documented rollback plan AND a measurable success metric defined upfront.",
        invalid_behavior=["Green-light any spec", "Green-light on rollback plan alone", "Green-light on success metric alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-coaching-001", target_type="interpersonal_boundary", domain="management",
        target_description="user's report-coaching availability — three explicit narrowings: any time → scheduled monthly → scheduled monthly with written prep",
        target_slot_id="report_coaching::v1", topic="report_coaching_availability",
        versions=[
            VersionSpec(value="report coaching is available any time the report asks", polarity="constraint", session_introduced=1),
            VersionSpec(value="coaching is available only in monthly scheduled sessions, not ad-hoc", polarity="constraint", session_introduced=2),
            VersionSpec(value="coaching is available only in monthly scheduled sessions with the report submitting written prep 24 hours ahead", polarity="constraint", session_introduced=3),
        ],
        current_query="Priya just dropped by my desk wanting career advice on the spot — handle it now or schedule?",
        required_behavior="Schedule the next monthly coaching slot for Priya and ask her to submit written prep 24 hours ahead.",
        invalid_behavior=["Handle the conversation on the spot", "Schedule with no written prep requirement", "Decline coaching entirely"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-engineering-debt-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's engineering-debt allocation rule — three explicit narrowings: ad-hoc → 20% → 20% with written debt-tickets",
        target_slot_id="eng_debt::v1", topic="engineering_debt_allocation",
        versions=[
            VersionSpec(value="address engineering debt whenever a feature work block ends early", polarity="constraint", session_introduced=1),
            VersionSpec(value="dedicate 20 percent of every sprint to engineering debt work", polarity="constraint", session_introduced=2),
            VersionSpec(value="dedicate 20 percent of every sprint to debt work, drawn only from explicitly written debt tickets", polarity="constraint", session_introduced=3),
        ],
        current_query="Plan the next two-week sprint for the team.",
        required_behavior="Plan 20% of the sprint for debt work drawn only from explicitly written debt tickets.",
        invalid_behavior=["Address debt only when feature work ends early", "Allocate 20% without requiring written tickets", "Skip debt allocation"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi triple (4)
    _trip(_s(sample_id="p3-multi-mockup-tool-001", target_type="object_preference", domain="creative",
        target_description="user's UI mockup tool — three-version chain: Balsamiq → Whimsical → Excalidraw",
        target_slot_id="mockup_tool::v1", topic="ui_mockup_tool",
        versions=[
            VersionSpec(value="Balsamiq with the legacy hand-drawn-style component library", polarity="prefer", session_introduced=1),
            VersionSpec(value="Whimsical with the flowchart-and-board hybrid canvas", polarity="prefer", session_introduced=2),
            VersionSpec(value="Excalidraw with the open-source self-hosted instance and the live collaboration", polarity="prefer", session_introduced=3),
        ],
        current_query="Sketch the new sign-up flow before the design review.",
        required_behavior="Sketch the sign-up flow in Excalidraw using the open-source self-hosted instance.",
        invalid_behavior=["Sketch in Balsamiq", "Sketch in Whimsical", "Sketch on paper"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-customer-survey-001", target_type="object_preference", domain="business",
        target_description="user's NPS survey tool — three-version chain: Delighted → Wootric → Refiner",
        target_slot_id="nps_survey::v1", topic="nps_survey_tool",
        versions=[
            VersionSpec(value="Delighted with the legacy single-channel email survey", polarity="prefer", session_introduced=1),
            VersionSpec(value="Wootric with the in-app prompt and verbatim-comment analytics", polarity="prefer", session_introduced=2),
            VersionSpec(value="Refiner with the conditional follow-up prompts and the salesforce sync", polarity="prefer", session_introduced=3),
        ],
        current_query="Send out this quarter's NPS survey to active customers.",
        required_behavior="Send the NPS survey through Refiner using conditional follow-up prompts and the salesforce sync.",
        invalid_behavior=["Send through Delighted", "Send through Wootric", "Send a manual email survey"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-engineering-blog-host-001", target_type="object_preference", domain="creative",
        target_description="team's engineering blog host — three-version chain: Medium → Hashnode → custom Astro+Cloudflare",
        target_slot_id="eng_blog_host::v1", topic="engineering_blog_host",
        versions=[
            VersionSpec(value="Medium with the publication-tier reach and the partner program", polarity="prefer", session_introduced=1),
            VersionSpec(value="Hashnode with the personal-domain mapping and the developer-community boost", polarity="prefer", session_introduced=2),
            VersionSpec(value="custom Astro static site deployed to Cloudflare Pages with the RSS feed and the Algolia search", polarity="prefer", session_introduced=3),
        ],
        current_query="Publish the new post on auth-token rotation patterns.",
        required_behavior="Publish the auth-token rotation post on the custom Astro static site deployed to Cloudflare Pages.",
        invalid_behavior=["Publish on Medium", "Publish on Hashnode", "Publish on a generic WordPress blog"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-meditation-program-001", target_type="conceptual_stance", domain="lifestyle",
        target_description="user's mindfulness program — three-version chain: MBSR → Vipassana → Zen sit",
        target_slot_id="mindfulness_program::v1", topic="mindfulness_program",
        versions=[
            VersionSpec(value="Mindfulness-Based Stress Reduction (MBSR) eight-week structured course", polarity="prefer", session_introduced=1),
            VersionSpec(value="Vipassana ten-day silent retreat at the Dhamma Dharā center", polarity="prefer", session_introduced=2),
            VersionSpec(value="Zen sit practice at the Brooklyn Zen Center with the seven-day sesshin format", polarity="prefer", session_introduced=3),
        ],
        current_query="Block this year's intensive mindfulness practice.",
        required_behavior="Block this year's mindfulness practice as a Zen sit seven-day sesshin at the Brooklyn Zen Center.",
        invalid_behavior=["Block an MBSR eight-week course", "Block a Vipassana ten-day retreat", "Skip the practice"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    # multi doublet (4)
    _doub(_s(sample_id="p3-multi-onboarding-tool-4v-001", target_type="object_preference", domain="business",
        target_description="team's customer onboarding platform — four-version chain: Pendo → Userpilot → Appcues → Userflow",
        target_slot_id="onboarding_platform::v1", topic="customer_onboarding_platform",
        versions=[
            VersionSpec(value="Pendo with the legacy product-tour builder", polarity="prefer", session_introduced=1),
            VersionSpec(value="Userpilot with the segment-based experience triggers", polarity="prefer", session_introduced=2),
            VersionSpec(value="Appcues with the no-code flow editor and analytics", polarity="prefer", session_introduced=3),
            VersionSpec(value="Userflow with the version-controlled flows and the Slack-integrated review process", polarity="prefer", session_introduced=4),
        ],
        current_query="Build the onboarding flow for the new self-serve tier.",
        required_behavior="Build the self-serve tier onboarding flow in Userflow with version-controlled flows and Slack-integrated review.",
        invalid_behavior=["Build in Pendo", "Build in Userpilot", "Build in Appcues"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-feature-flag-platform-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's feature-flag platform — four-version chain: home-grown DB → LaunchDarkly → Split → Flagsmith",
        target_slot_id="feature_flag_platform::v1", topic="feature_flag_platform",
        versions=[
            VersionSpec(value="home-grown database-backed feature flag table with the legacy admin UI", polarity="prefer", session_introduced=1),
            VersionSpec(value="LaunchDarkly with the multi-environment targeting and the audit log", polarity="prefer", session_introduced=2),
            VersionSpec(value="Split with the unified feature-management and experimentation in one platform", polarity="prefer", session_introduced=3),
            VersionSpec(value="Flagsmith open-source self-hosted with the local-evaluation SDK and the segment overrides", polarity="prefer", session_introduced=4),
        ],
        current_query="Add a flag for the new beta-only homepage variant.",
        required_behavior="Add the beta-only homepage flag in Flagsmith using the local-evaluation SDK and segment overrides.",
        invalid_behavior=["Add in the home-grown database table", "Add in LaunchDarkly", "Add in Split"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-doc-rag-tool-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's internal doc Q&A — four-version chain: Slack search → Glean → Mendable → Vectara",
        target_slot_id="doc_qa::v1", topic="internal_doc_qa",
        versions=[
            VersionSpec(value="Slack message search across the company workspace", polarity="prefer", session_introduced=1),
            VersionSpec(value="Glean with the unified cross-source enterprise search", polarity="prefer", session_introduced=2),
            VersionSpec(value="Mendable with the LLM-grounded chat over the public docs", polarity="prefer", session_introduced=3),
            VersionSpec(value="Vectara with the hybrid retrieval and the citation-ranked answer cards", polarity="prefer", session_introduced=4),
        ],
        current_query="Find the explanation of why we deprecated v1 of the auth API.",
        required_behavior="Find the auth API v1 deprecation explanation through Vectara using hybrid retrieval and citation-ranked answer cards.",
        invalid_behavior=["Find through Slack search", "Find through Glean", "Find through Mendable"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-text-editor-4v-001", target_type="object_preference", domain="creative",
        target_description="user's primary text editor — four-version chain: Sublime → Atom → VSCode → Helix",
        target_slot_id="text_editor::v1", topic="primary_text_editor",
        versions=[
            VersionSpec(value="Sublime Text 3 with the package-control extensions", polarity="prefer", session_introduced=1),
            VersionSpec(value="Atom with the GitHub-integrated panes and the teletype collaboration", polarity="prefer", session_introduced=2),
            VersionSpec(value="VSCode with the remote-containers extension and the live-share session", polarity="prefer", session_introduced=3),
            VersionSpec(value="Helix with the modal-by-default editing and the built-in tree-sitter highlighting", polarity="prefer", session_introduced=4),
        ],
        current_query="Open the new dotfile for editing.",
        required_behavior="Open the dotfile in Helix using the modal-by-default editing and built-in tree-sitter highlighting.",
        invalid_behavior=["Open in Sublime Text 3", "Open in Atom", "Open in VSCode"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    # explicit (4)
    _trip(_s(sample_id="p3-explicit-design-system-001", target_type="object_preference", domain="creative",
        target_description="team's design system — explicit replacement of Material UI with Radix Themes",
        target_slot_id="design_system::v1", topic="design_system",
        versions=[
            VersionSpec(value="Material UI with the legacy v4 theming and component overrides", polarity="prefer", session_introduced=1),
            VersionSpec(value="Radix Themes with the unstyled-primitive composition and the design-token system", polarity="prefer", session_introduced=2),
        ],
        current_query="Build the new settings page UI.",
        required_behavior="Build the settings page UI using Radix Themes with the unstyled-primitive composition.",
        invalid_behavior=["Build using Material UI", "Build with raw Tailwind only", "Build with custom CSS"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-team-survey-001", target_type="object_preference", domain="management",
        target_description="team's pulse survey vendor — explicit replacement of Culture Amp with Glint",
        target_slot_id="pulse_vendor::v1", topic="team_pulse_vendor",
        versions=[
            VersionSpec(value="Culture Amp with the legacy engagement-survey templates", polarity="prefer", session_introduced=1),
            VersionSpec(value="Glint with the manager-action plans and the pulse-cadence configurability", polarity="prefer", session_introduced=2),
        ],
        current_query="Run the next quarterly engagement check on my team.",
        required_behavior="Run the quarterly engagement check through Glint using manager-action plans.",
        invalid_behavior=["Run through Culture Amp", "Run through a free Google Forms survey", "Skip the engagement check"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-ml-platform-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's ML training platform — explicit replacement of SageMaker with Modal",
        target_slot_id="ml_platform::v1", topic="ml_training_platform",
        versions=[
            VersionSpec(value="AWS SageMaker with the legacy training-job and notebook instances", polarity="prefer", session_introduced=1),
            VersionSpec(value="Modal with the serverless-GPU and the function-as-job execution", polarity="prefer", session_introduced=2),
        ],
        current_query="Run training for the new ranking model.",
        required_behavior="Run the ranking-model training on Modal using the serverless-GPU and function-as-job execution.",
        invalid_behavior=["Run on AWS SageMaker", "Run on a local GPU box", "Run on Colab Pro"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-newsletter-host-001", target_type="object_preference", domain="creative",
        target_description="user's newsletter host — explicit replacement of Substack with Ghost",
        target_slot_id="newsletter_host::v1", topic="newsletter_host",
        versions=[
            VersionSpec(value="Substack with the public discoverability and the recommendation widget", polarity="prefer", session_introduced=1),
            VersionSpec(value="Ghost with the self-hosted instance and the membership-payment integration", polarity="prefer", session_introduced=2),
        ],
        current_query="Send out this Friday's newsletter to subscribers.",
        required_behavior="Send Friday's newsletter through Ghost using the self-hosted instance and membership-payment integration.",
        invalid_behavior=["Send through Substack", "Send through Mailchimp", "Skip the send"],
        failure_patterns=["explicit_replacement"])),

    # repeated_use (3)
    _drift(_s(sample_id="p3-drift-incident-tool-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's incident-coordination — drifted to a dedicated incident.io workspace from a Slack channel + spreadsheet, repeated active use",
        target_slot_id="incident_coord::v1", topic="incident_coordination",
        versions=[
            VersionSpec(value="ad-hoc Slack channel plus a shared Google spreadsheet for action items", polarity="prefer", session_introduced=1),
            VersionSpec(value="dedicated incident.io workspace with auto-created channels and structured timelines", polarity="prefer", session_introduced=2),
        ],
        current_query="The payments service is throwing 500s — kick off the response.",
        required_behavior="Kick off the response by spinning up an incident.io workspace with auto-created channels and structured timeline.",
        invalid_behavior=["Spin up a Slack channel and shared Google spreadsheet", "Coordinate via email", "Wing the response"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-board-meeting-001", target_type="procedural_constraint", domain="management",
        target_description="user's quarterly business review — drifted to a fully written 10-page memo from a slide deck + live walkthrough, repeated active use",
        target_slot_id="qbr_format::v1", topic="qbr_format",
        versions=[
            VersionSpec(value="20-slide deck plus 90-minute live walkthrough with the leadership team", polarity="prefer", session_introduced=1),
            VersionSpec(value="fully written 10-page memo circulated 48 hours ahead with no live walkthrough", polarity="prefer", session_introduced=2),
        ],
        current_query="Q1 wraps next week — prepare the QBR materials.",
        required_behavior="Prepare a fully written 10-page memo circulated 48 hours ahead, with no live walkthrough.",
        invalid_behavior=["Prepare a 20-slide deck plus live walkthrough", "Prepare both formats", "Skip the QBR"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-presentation-format-001", target_type="conceptual_stance", domain="work_communication",
        target_description="user's all-hands presentation style — drifted to a 5-minute lightning-round summary from a 30-minute prepared deck, repeated active use",
        target_slot_id="all_hands_style::v1", topic="all_hands_presentation_style",
        versions=[
            VersionSpec(value="30-minute prepared deck with detailed slides and rehearsed talking points", polarity="prefer", session_introduced=1),
            VersionSpec(value="5-minute lightning-round summary with three bullet headlines and Q&A", polarity="prefer", session_introduced=2),
        ],
        current_query="The all-hands is in two days — what am I presenting?",
        required_behavior="Present a 5-minute lightning-round summary with three bullet headlines and open Q&A.",
        invalid_behavior=["Present a 30-minute prepared deck", "Present a hybrid format", "Skip the presentation"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    # abandonment (3)
    _drift(_s(sample_id="p3-drift-spec-template-001", target_type="object_preference", domain="work_workflow",
        target_description="user's spec-doc template — abandoned the long Notion template; one-page Slab template only now",
        target_slot_id="spec_template::v1", topic="spec_doc_template",
        versions=[
            VersionSpec(value="long Notion template with eight required sections and the linked-database side panel", polarity="prefer", session_introduced=1),
            VersionSpec(value="one-page Slab template with title, problem, approach, and rollout-plan only", polarity="prefer", session_introduced=2),
        ],
        current_query="Start the spec for the new fraud-rules engine.",
        required_behavior="Start the fraud-rules-engine spec using the one-page Slab template with title, problem, approach, and rollout-plan only.",
        invalid_behavior=["Start with the long Notion template", "Start with a blank doc", "Start in a slide deck"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-old-rotation-001", target_type="procedural_constraint", domain="management",
        target_description="user's coffee-chat rotation — abandoned the company-wide random pairing; team-only office hours only now",
        target_slot_id="coffee_chat::v1", topic="coffee_chat_rotation",
        versions=[
            VersionSpec(value="company-wide random pairing every other Friday morning via the Donut bot", polarity="constraint", session_introduced=1),
            VersionSpec(value="team-only office hours every Tuesday and Thursday afternoon for ad-hoc drop-ins", polarity="constraint", session_introduced=2),
        ],
        current_query="Set up this week's casual conversation time.",
        required_behavior="Set up team-only office hours on Tuesday and Thursday afternoon for ad-hoc drop-ins.",
        invalid_behavior=["Set up Friday morning random pairing via Donut", "Set up cross-team coffee chats", "Skip the conversation time"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-paper-magazine-001", target_type="object_preference", domain="leisure",
        target_description="user's monthly magazine — abandoned the print Atlantic subscription; The New Yorker digital app only now",
        target_slot_id="monthly_magazine::v1", topic="monthly_magazine",
        versions=[
            VersionSpec(value="print Atlantic subscription mailed monthly with the cover-story bookmarks", polarity="prefer", session_introduced=1),
            VersionSpec(value="The New Yorker digital app subscription with the offline reading queue", polarity="prefer", session_introduced=2),
        ],
        current_query="What should I dig into this evening?",
        required_behavior="Dig into the latest issue on The New Yorker digital app using the offline reading queue.",
        invalid_behavior=["Read the print Atlantic", "Browse a different magazine", "Skip reading entirely"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    # gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-meeting-narrow-2-001", target_type="conceptual_stance", domain="management",
        target_description="user's RSVP-yes for cross-team meetings — gradually narrowed from any meeting to only meetings tied to the user's quarterly OKR via cumulative preference",
        target_slot_id="cross_team_meeting::v1", topic="cross_team_meeting_rsvp",
        versions=[
            VersionSpec(value="any cross-team meeting that the calendar shows the user as optional", polarity="prefer", session_introduced=1),
            VersionSpec(value="only cross-team meetings tied to the user's current quarterly OKR objectives", polarity="prefer", session_introduced=2),
        ],
        current_query="A platform-team review just popped up on my calendar — RSVP yes or no?",
        required_behavior="RSVP only if the platform-team review is tied to the user's current quarterly OKR objectives; otherwise decline.",
        invalid_behavior=["RSVP yes to any optional cross-team meeting", "RSVP yes for the first 15 minutes", "Forward to a deputy"],
        failure_patterns=["implicit_drift"]), "gradual_narrowing"),
]
