"""Phase 3 batch L — 25 spines, balanced fill."""

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


PHASE3_BATCH_L: list[Phase3GroupSpec] = [
    # narrow (5)
    _trip(_s(sample_id="p3-narrow-test-coverage-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's test-coverage rule — three explicit narrowings: any → ≥80% line coverage → ≥80% line and ≥70% branch",
        target_slot_id="test_coverage::v1", topic="test_coverage_requirement",
        versions=[
            VersionSpec(value="merge any pull request regardless of test coverage metrics", polarity="constraint", session_introduced=1),
            VersionSpec(value="require at least 80 percent line coverage on every pull request before merge", polarity="constraint", session_introduced=2),
            VersionSpec(value="require at least 80 percent line coverage and 70 percent branch coverage on every pull request", polarity="constraint", session_introduced=3),
        ],
        current_query="Marcus's auth-token rotation PR has 82% line coverage and 64% branch — can it merge?",
        required_behavior="Block the merge; branch coverage of 64 percent is below the 70 percent threshold.",
        invalid_behavior=["Merge since line coverage exceeds 80 percent", "Merge regardless of metrics", "Merge with a coverage exception"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-data-export-001", target_type="procedural_constraint", domain="business",
        target_description="user's customer-data export rule — three explicit narrowings: any → with NDA → with NDA + audit log entry",
        target_slot_id="data_export::v1", topic="customer_data_export",
        versions=[
            VersionSpec(value="export any customer dataset that the partner team requests", polarity="constraint", session_introduced=1),
            VersionSpec(value="export only when an NDA is on file with the requesting partner", polarity="constraint", session_introduced=2),
            VersionSpec(value="export only with an NDA on file plus a logged audit entry capturing who, what, and when", polarity="constraint", session_introduced=3),
        ],
        current_query="Sales partner Acme just asked for a slice of the user-events table — can I export?",
        required_behavior="Export only if Acme has an NDA on file AND a logged audit entry capturing who, what, and when is created.",
        invalid_behavior=["Export on partner request alone", "Export with NDA only without the audit entry", "Export without checking NDA"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-meeting-room-001", target_type="procedural_constraint", domain="management",
        target_description="user's offsite booking rule — three explicit narrowings: any → finance approval → finance approval + 60-day advance booking",
        target_slot_id="offsite_booking::v1", topic="offsite_booking",
        versions=[
            VersionSpec(value="book the team offsite venue at the moment leadership decides", polarity="constraint", session_introduced=1),
            VersionSpec(value="book only after the finance partner has approved the budget", polarity="constraint", session_introduced=2),
            VersionSpec(value="book only after finance has approved AND the booking is at least 60 days in advance", polarity="constraint", session_introduced=3),
        ],
        current_query="Leadership wants the team offsite at the Cape May lodge in March — can I book?",
        required_behavior="Book only if finance has approved AND March is at least 60 days from today.",
        invalid_behavior=["Book on leadership decision alone", "Book on finance approval without the 60-day check", "Book without finance approval"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-vendor-onboard-001", target_type="procedural_constraint", domain="business",
        target_description="user's new-vendor onboarding rule — three explicit narrowings: any → security questionnaire → security questionnaire + reference check",
        target_slot_id="vendor_onboarding::v1", topic="new_vendor_onboarding",
        versions=[
            VersionSpec(value="onboard any vendor the team wants to start using", polarity="constraint", session_introduced=1),
            VersionSpec(value="onboard only after the vendor passes the standard security questionnaire", polarity="constraint", session_introduced=2),
            VersionSpec(value="onboard only after the vendor passes the security questionnaire AND a reference check from two other customers", polarity="constraint", session_introduced=3),
        ],
        current_query="Engineering wants to start using a new build-cache vendor — can I sign?",
        required_behavior="Sign only if the build-cache vendor passes the security questionnaire AND a reference check from two other customers.",
        invalid_behavior=["Sign on team request alone", "Sign on security questionnaire alone", "Sign on reference check alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-hire-bar-001", target_type="conceptual_stance", domain="management",
        target_description="user's senior-engineer hiring bar — three explicit narrowings: any → strong system-design signal → strong system-design + production-ownership track record",
        target_slot_id="hire_bar::v1", topic="senior_hire_bar",
        versions=[
            VersionSpec(value="advance any candidate the recruiter brings forward to onsite", polarity="prefer", session_introduced=1),
            VersionSpec(value="advance only candidates with a strong system-design signal in the screen", polarity="prefer", session_introduced=2),
            VersionSpec(value="advance only candidates with a strong system-design signal AND a documented production-ownership track record", polarity="prefer", session_introduced=3),
        ],
        current_query="Marcus the recruiter just sent over a senior backend candidate — advance to onsite?",
        required_behavior="Advance only if the candidate has a strong system-design signal AND a documented production-ownership track record.",
        invalid_behavior=["Advance any candidate the recruiter sends", "Advance on system-design signal alone", "Advance on production track record alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi triple (4)
    _trip(_s(sample_id="p3-multi-board-software-001", target_type="object_preference", domain="business",
        target_description="user's board-deck builder — three-version chain: PowerPoint → Pitch → Tome",
        target_slot_id="board_deck::v1", topic="board_deck_builder",
        versions=[
            VersionSpec(value="Microsoft PowerPoint with the legacy corporate template", polarity="prefer", session_introduced=1),
            VersionSpec(value="Pitch with the real-time multi-cursor editing and template-import flow", polarity="prefer", session_introduced=2),
            VersionSpec(value="Tome with the AI outline-scaffolding and the responsive native-web layouts", polarity="prefer", session_introduced=3),
        ],
        current_query="Build the Q1 board deck.",
        required_behavior="Build the Q1 board deck in Tome using the AI outline-scaffolding.",
        invalid_behavior=["Build in PowerPoint", "Build in Pitch", "Build in Google Slides"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-customer-support-001", target_type="object_preference", domain="business",
        target_description="team's customer-support tool — three-version chain: Zendesk → Help Scout → Plain",
        target_slot_id="support_tool::v1", topic="customer_support_tool",
        versions=[
            VersionSpec(value="Zendesk with the legacy ticket macros and the multi-brand portal", polarity="prefer", session_introduced=1),
            VersionSpec(value="Help Scout with the inbox-style threading and the saved replies", polarity="prefer", session_introduced=2),
            VersionSpec(value="Plain with the developer-first API workflow and the customer-context sidecar", polarity="prefer", session_introduced=3),
        ],
        current_query="Set up support for the new product line.",
        required_behavior="Set up support for the new product line through Plain using the developer-first API workflow and customer-context sidecar.",
        invalid_behavior=["Set up through Zendesk", "Set up through Help Scout", "Use a generic shared inbox"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-typing-tutor-001", target_type="object_preference", domain="learning",
        target_description="user's typing-improvement tool — three-version chain: keybr → Monkeytype → Typingclub",
        target_slot_id="typing_tutor::v1", topic="typing_improvement_tool",
        versions=[
            VersionSpec(value="keybr with the algorithmic letter-frequency drills", polarity="prefer", session_introduced=1),
            VersionSpec(value="Monkeytype with the random-word-list races and themable presets", polarity="prefer", session_introduced=2),
            VersionSpec(value="Typingclub with the structured curriculum and the school-style progress tracking", polarity="prefer", session_introduced=3),
        ],
        current_query="Practice typing for ten minutes.",
        required_behavior="Practice typing on Typingclub using the structured curriculum and school-style progress tracking.",
        invalid_behavior=["Practice on keybr", "Practice on Monkeytype", "Practice on a random typing site"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-feedback-survey-001", target_type="object_preference", domain="management",
        target_description="user's career-conversation tool — three-version chain: Reflektive → 15Five → Lattice",
        target_slot_id="career_tool::v1", topic="career_conversation_tool",
        versions=[
            VersionSpec(value="Reflektive with the legacy 360-question template", polarity="prefer", session_introduced=1),
            VersionSpec(value="15Five with the weekly-pulse and HighFive recognition", polarity="prefer", session_introduced=2),
            VersionSpec(value="Lattice with the OKR-tied check-ins and the growth-area planning", polarity="prefer", session_introduced=3),
        ],
        current_query="Schedule the next round of career conversations with my reports.",
        required_behavior="Schedule the career conversations through Lattice using the OKR-tied check-ins and growth-area planning.",
        invalid_behavior=["Schedule through Reflektive", "Schedule through 15Five", "Use ad-hoc free-form notes"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    # multi doublet (4)
    _doub(_s(sample_id="p3-multi-loadbalancer-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's load balancer — four-version chain: HAProxy → Nginx → Envoy → Caddy",
        target_slot_id="load_balancer::v1", topic="load_balancer",
        versions=[
            VersionSpec(value="HAProxy with the legacy active-passive failover configuration", polarity="prefer", session_introduced=1),
            VersionSpec(value="Nginx with the upstream-health-check module and the rate-limit zones", polarity="prefer", session_introduced=2),
            VersionSpec(value="Envoy with the xDS dynamic configuration and the gRPC support", polarity="prefer", session_introduced=3),
            VersionSpec(value="Caddy with the automatic-HTTPS-via-Let's-Encrypt and the JSON config API", polarity="prefer", session_introduced=4),
        ],
        current_query="Front the new admin dashboard with a load balancer.",
        required_behavior="Front the admin dashboard with Caddy using automatic-HTTPS-via-Let's-Encrypt and the JSON config API.",
        invalid_behavior=["Front with HAProxy", "Front with Nginx", "Front with Envoy"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-billing-platform-4v-001", target_type="object_preference", domain="business",
        target_description="team's subscription billing — four-version chain: Stripe Billing → Recurly → Chargebee → Orb",
        target_slot_id="billing_platform::v1", topic="subscription_billing_platform",
        versions=[
            VersionSpec(value="Stripe Billing with the legacy fixed-price plans and prorated-charge logic", polarity="prefer", session_introduced=1),
            VersionSpec(value="Recurly with the dunning-management and revenue-recognition automation", polarity="prefer", session_introduced=2),
            VersionSpec(value="Chargebee with the catalog-driven pricing and entitlement management", polarity="prefer", session_introduced=3),
            VersionSpec(value="Orb with the usage-based metering and event-driven invoicing engine", polarity="prefer", session_introduced=4),
        ],
        current_query="Wire billing for the new metered API service.",
        required_behavior="Wire metered API billing through Orb using the usage-based metering and event-driven invoicing engine.",
        invalid_behavior=["Wire through Stripe Billing", "Wire through Recurly", "Wire through Chargebee"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-team-photo-shoot-4v-001", target_type="object_preference", domain="creative",
        target_description="user's primary camera for portraits — four-version chain: iPhone → Sony A7iv → Fuji X100V → Leica Q3",
        target_slot_id="portrait_camera::v1", topic="portrait_camera",
        versions=[
            VersionSpec(value="iPhone 15 Pro with the portrait-mode computational photography", polarity="prefer", session_introduced=1),
            VersionSpec(value="Sony A7iv with the 33-megapixel full-frame sensor and the 50mm prime", polarity="prefer", session_introduced=2),
            VersionSpec(value="Fuji X100V with the fixed 23mm prime and the film-simulation modes", polarity="prefer", session_introduced=3),
            VersionSpec(value="Leica Q3 with the 60-megapixel full-frame sensor and the fixed 28mm Summilux lens", polarity="prefer", session_introduced=4),
        ],
        current_query="Shoot the team-headshot session for the new website.",
        required_behavior="Shoot the team headshots with the Leica Q3 using the 60-megapixel full-frame sensor and 28mm Summilux lens.",
        invalid_behavior=["Shoot with iPhone 15 Pro", "Shoot with Sony A7iv", "Shoot with Fuji X100V"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-customer-onboarding-rule-4v-001", target_type="procedural_constraint", domain="business",
        target_description="user's customer onboarding flow — four-version chain across iterations",
        target_slot_id="onboarding_flow::v1", topic="customer_onboarding_flow",
        versions=[
            VersionSpec(value="single welcome email plus a 30-minute kickoff call", polarity="constraint", session_introduced=1),
            VersionSpec(value="three-step automated email drip plus a 60-minute kickoff call with technical lead", polarity="constraint", session_introduced=2),
            VersionSpec(value="self-serve in-app tutorial plus an optional 30-minute office-hour drop-in", polarity="constraint", session_introduced=3),
            VersionSpec(value="customer-success-led 90-day program with weekly check-ins and milestone-gated certifications", polarity="constraint", session_introduced=4),
        ],
        current_query="Onboard the new enterprise customer Acme starting next Monday.",
        required_behavior="Onboard Acme through the customer-success-led 90-day program with weekly check-ins and milestone-gated certifications.",
        invalid_behavior=["Onboard with welcome email plus 30-minute call", "Onboard with email drip plus 60-minute call", "Onboard with self-serve tutorial only"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    # explicit (4)
    _trip(_s(sample_id="p3-explicit-monitoring-tool-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's APM tool — explicit replacement of New Relic with Datadog",
        target_slot_id="apm_tool::v1", topic="apm_tool",
        versions=[
            VersionSpec(value="New Relic with the legacy NRQL query language and the alert policy", polarity="prefer", session_introduced=1),
            VersionSpec(value="Datadog with the unified APM-and-infrastructure dashboards and the Watchdog AIOps", polarity="prefer", session_introduced=2),
        ],
        current_query="Set up application performance tracking for the new ranking service.",
        required_behavior="Set up application performance tracking through Datadog using unified APM-and-infrastructure dashboards.",
        invalid_behavior=["Set up through New Relic", "Set up through a free OSS tool", "Skip APM tracking"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-mailing-list-001", target_type="object_preference", domain="business",
        target_description="team's transactional email provider — explicit replacement of SendGrid with Postmark",
        target_slot_id="transactional_email::v1", topic="transactional_email_provider",
        versions=[
            VersionSpec(value="SendGrid with the legacy template-engine and the IP-pool warmup", polarity="prefer", session_introduced=1),
            VersionSpec(value="Postmark with the broadcast-and-transactional separation and the deliverability-focused infrastructure", polarity="prefer", session_introduced=2),
        ],
        current_query="Wire the password-reset email path for the new auth service.",
        required_behavior="Wire the password-reset email through Postmark using the broadcast-and-transactional separation.",
        invalid_behavior=["Wire through SendGrid", "Wire through a self-hosted SMTP server", "Skip the password-reset email"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-issue-tracker-001", target_type="object_preference", domain="work_workflow",
        target_description="team's customer-feedback tracker — explicit replacement of Productboard with Canny",
        target_slot_id="feedback_tracker::v1", topic="customer_feedback_tracker",
        versions=[
            VersionSpec(value="Productboard with the legacy roadmap-and-prioritization tier", polarity="prefer", session_introduced=1),
            VersionSpec(value="Canny with the public roadmap and the changelog-broadcast feature", polarity="prefer", session_introduced=2),
        ],
        current_query="Log the request three customers made for SAML SSO.",
        required_behavior="Log the SAML SSO request in Canny using the public roadmap.",
        invalid_behavior=["Log in Productboard", "Log in a Slack channel", "Email it to engineering"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-recruiter-tool-001", target_type="object_preference", domain="management",
        target_description="user's recruiter outreach tool — explicit replacement of Gem with Findem",
        target_slot_id="recruiter_outreach::v1", topic="recruiter_outreach_tool",
        versions=[
            VersionSpec(value="Gem with the LinkedIn-integrated sequences and the Greenhouse handoff", polarity="prefer", session_introduced=1),
            VersionSpec(value="Findem with the AI-powered talent-graph search and the diversity-aware sourcing", polarity="prefer", session_introduced=2),
        ],
        current_query="Source the senior infrastructure-engineer pipeline for the platform team.",
        required_behavior="Source the senior infrastructure pipeline through Findem using the AI-powered talent-graph search.",
        invalid_behavior=["Source through Gem", "Source through LinkedIn Recruiter manually", "Skip sourcing"],
        failure_patterns=["explicit_replacement"])),

    # repeated_use (3)
    _drift(_s(sample_id="p3-drift-postmortem-format-001", target_type="conceptual_stance", domain="tech_workflow",
        target_description="user's postmortem document style — drifted to a one-page Loom video walkthrough from a multi-page written doc, repeated active use",
        target_slot_id="postmortem_format::v1", topic="postmortem_format",
        versions=[
            VersionSpec(value="multi-page written postmortem document with the timeline, root cause, and action items", polarity="prefer", session_introduced=1),
            VersionSpec(value="one-page Loom video walkthrough with the engineer narrating the timeline live on screen-share", polarity="prefer", session_introduced=2),
        ],
        current_query="Wrap up the postmortem for the database-replication outage.",
        required_behavior="Wrap up the database-replication outage with a one-page Loom video walkthrough narrating the timeline.",
        invalid_behavior=["Write a multi-page written postmortem", "Skip the postmortem", "Make a slide deck"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-team-celebration-001", target_type="procedural_constraint", domain="management",
        target_description="user's team-win celebration — drifted to a written #wins-of-the-week Slack thread from a Friday all-hands shout-out, repeated active use",
        target_slot_id="team_celebration::v1", topic="team_win_celebration",
        versions=[
            VersionSpec(value="Friday afternoon all-hands shout-out where the manager calls out individual wins", polarity="constraint", session_introduced=1),
            VersionSpec(value="written #wins-of-the-week Slack thread posted Friday morning with everyone tagged", polarity="constraint", session_introduced=2),
        ],
        current_query="Marcus shipped the auth-token rotation this week — recognize the win.",
        required_behavior="Recognize Marcus's win in the #wins-of-the-week Slack thread on Friday morning, tagging Marcus.",
        invalid_behavior=["Call out Marcus in the Friday all-hands shout-out", "Send Marcus a private DM", "Skip the recognition"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-debug-pattern-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's debugging style — drifted to a hypothesis-driven scientific-method approach from print-debugging-everything, repeated active use",
        target_slot_id="debug_style::v1", topic="debugging_style",
        versions=[
            VersionSpec(value="add print statements throughout the code path to reveal what's happening", polarity="constraint", session_introduced=1),
            VersionSpec(value="state a hypothesis, design the smallest test that disproves it, run, observe, repeat", polarity="constraint", session_introduced=2),
        ],
        current_query="The fraud rules engine is returning wrong scores intermittently — how do I track it down?",
        required_behavior="Track it down by stating a hypothesis, designing the smallest test that disproves it, running, observing, and repeating.",
        invalid_behavior=["Add print statements throughout the rules engine", "Restart the service and see if it recurs", "Ask Marcus to look"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    # abandonment (3)
    _drift(_s(sample_id="p3-drift-old-tool-cluster-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="team's hot-fix workflow — abandoned the cherry-pick-to-release-branch flow; trunk-based-with-rollback only now",
        target_slot_id="hotfix_workflow::v1", topic="hotfix_workflow",
        versions=[
            VersionSpec(value="cherry-pick the fix commit to the release branch and cut a patched build from there", polarity="constraint", session_introduced=1),
            VersionSpec(value="commit the fix to main and use the deploy-tool's rollback feature to restore green state if needed", polarity="constraint", session_introduced=2),
        ],
        current_query="The auth service is rejecting valid tokens — push a hotfix.",
        required_behavior="Push the auth-service hotfix by committing the fix to main and using the deploy-tool's rollback feature.",
        invalid_behavior=["Cherry-pick the fix to the release branch", "Cut a patched build from the release branch", "Skip the hotfix"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-physical-archive-001", target_type="object_preference", domain="lifestyle",
        target_description="user's tax-document archival — abandoned the physical filing cabinet; encrypted iCloud Drive only now",
        target_slot_id="tax_archive::v1", topic="tax_document_archive",
        versions=[
            VersionSpec(value="physical filing cabinet in the home office with the year-labeled hanging folders", polarity="prefer", session_introduced=1),
            VersionSpec(value="encrypted iCloud Drive folder with the year-and-document-type tagging", polarity="prefer", session_introduced=2),
        ],
        current_query="The 1099 from Acme just arrived — where does it go?",
        required_behavior="Save the Acme 1099 to the encrypted iCloud Drive folder using year-and-document-type tagging.",
        invalid_behavior=["File in the physical filing cabinet", "Email it to yourself", "Throw it away"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-skill-gym-001", target_type="procedural_constraint", domain="learning",
        target_description="user's coding-practice approach — abandoned the LeetCode interview prep; building real projects from idea to deploy only now",
        target_slot_id="coding_practice::v1", topic="coding_practice_approach",
        versions=[
            VersionSpec(value="daily LeetCode problem solving with the medium-and-hard difficulty filter", polarity="constraint", session_introduced=1),
            VersionSpec(value="weekly project-based building from idea to deploy with public GitHub repos", polarity="constraint", session_introduced=2),
        ],
        current_query="It's Sunday afternoon — how am I sharpening my coding chops this week?",
        required_behavior="Sharpen by starting a new weekly project from idea to deploy and publishing the GitHub repo publicly.",
        invalid_behavior=["Solve LeetCode medium-and-hard problems", "Read code-style books", "Skip practice"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    # gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-recommendation-narrow-001", target_type="conceptual_stance", domain="management",
        target_description="user's recommendation criteria for new senior hires — gradually narrowed from any successful candidate to only candidates the user has personally pair-programmed with via cumulative preference",
        target_slot_id="hire_recommendation::v1", topic="senior_hire_recommendation",
        versions=[
            VersionSpec(value="recommend any senior candidate who passes the team's interview loop", polarity="prefer", session_introduced=1),
            VersionSpec(value="recommend only candidates the user has personally pair-programmed with for at least one full session", polarity="prefer", session_introduced=2),
        ],
        current_query="A senior platform-engineer candidate just cleared the interview loop — should I recommend the offer?",
        required_behavior="Recommend the offer only if the user has personally pair-programmed with the candidate for at least one full session.",
        invalid_behavior=["Recommend based on loop pass alone", "Recommend based on the recruiter's read", "Recommend conditional on a pair-programming session next week"],
        failure_patterns=["implicit_drift"]), "gradual_narrowing"),
]
