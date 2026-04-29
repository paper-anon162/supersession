"""Phase 3 batch I — 25 spines, multi-version + narrow heavy."""

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


PHASE3_BATCH_I: list[Phase3GroupSpec] = [
    # narrow (6)
    _trip(_s(sample_id="p3-narrow-postmortem-001", target_type="procedural_constraint", domain="management",
        target_description="user's postmortem owner — three explicit narrowings: any senior → on-call lead → on-call lead with two-week incident-history experience",
        target_slot_id="postmortem_owner::v1", topic="postmortem_owner",
        versions=[
            VersionSpec(value="any senior engineer on the team writes the postmortem", polarity="constraint", session_introduced=1),
            VersionSpec(value="the on-call lead during the incident writes the postmortem", polarity="constraint", session_introduced=2),
            VersionSpec(value="the on-call lead with at least two weeks of prior incident-history experience writes the postmortem", polarity="constraint", session_introduced=3),
        ],
        current_query="Last night's database outage is mitigated — who writes it up?",
        required_behavior="The on-call lead during the incident writes the writeup, but only if they have at least two weeks of prior incident-history experience.",
        invalid_behavior=["Any senior engineer", "The on-call lead without checking experience", "The team manager"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-architecture-review-001", target_type="conceptual_stance", domain="tech_workflow",
        target_description="user's architecture-review scope — three explicit narrowings: any new system → cross-team boundary → cross-team boundary with persistent state",
        target_slot_id="arch_review_scope::v1", topic="arch_review_scope",
        versions=[
            VersionSpec(value="every new internal system gets an architecture review", polarity="prefer", session_introduced=1),
            VersionSpec(value="only systems crossing a team boundary trigger the review", polarity="prefer", session_introduced=2),
            VersionSpec(value="only cross-team-boundary systems that introduce persistent state trigger the review", polarity="prefer", session_introduced=3),
        ],
        current_query="Marcus is launching a new caching service used by three teams — does it need an architecture review?",
        required_behavior="Yes, the caching service needs the review only if it crosses team boundaries AND introduces persistent state.",
        invalid_behavior=["Trigger review for any new system", "Trigger only for cross-team boundary", "Skip the review entirely"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-experiment-tracking-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's ML experiment tracking requirement — three explicit narrowings: ad-hoc → mandatory MLflow → MLflow + automated model card",
        target_slot_id="exp_tracking::v1", topic="ml_experiment_tracking",
        versions=[
            VersionSpec(value="track ML experiments however the engineer wants — notebook, spreadsheet, or memory", polarity="constraint", session_introduced=1),
            VersionSpec(value="track every ML experiment in MLflow with run-name, parameters, and metrics logged", polarity="constraint", session_introduced=2),
            VersionSpec(value="track in MLflow plus auto-generate a model card with intended-use, limitations, and dataset summary", polarity="constraint", session_introduced=3),
        ],
        current_query="Erin just finished tuning the ranking-quality model — what does she submit?",
        required_behavior="Erin submits the MLflow run with parameters and metrics logged, plus the auto-generated model card with intended-use, limitations, and dataset summary.",
        invalid_behavior=["Submit ad-hoc notebook only", "Submit MLflow without the model card", "Submit only the model card"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pulse-survey-001", target_type="procedural_constraint", domain="management",
        target_description="user's team-pulse survey cadence — three explicit narrowings: any → quarterly → quarterly with two follow-up 1:1s",
        target_slot_id="pulse_survey::v1", topic="team_pulse_survey",
        versions=[
            VersionSpec(value="run team-pulse surveys whenever the user feels something is off", polarity="constraint", session_introduced=1),
            VersionSpec(value="run a quarterly team-pulse survey at the start of each quarter", polarity="constraint", session_introduced=2),
            VersionSpec(value="run a quarterly survey followed by two follow-up 1:1s with the lowest-scoring respondents", polarity="constraint", session_introduced=3),
        ],
        current_query="Q1 just started — kick off the team-pulse process.",
        required_behavior="Run the Q1 team-pulse survey AND schedule two follow-up 1:1s with the lowest-scoring respondents.",
        invalid_behavior=["Skip the survey since nothing seems off", "Run only the survey", "Run only the follow-up 1:1s"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-keynote-prep-001", target_type="procedural_constraint", domain="learning",
        target_description="user's conference-keynote prep — three explicit narrowings: any prep → two-week dry-run schedule → two-week dry-run plus pre-recorded backup",
        target_slot_id="keynote_prep::v1", topic="conference_keynote_prep",
        versions=[
            VersionSpec(value="prep keynotes the way the moment calls for it", polarity="constraint", session_introduced=1),
            VersionSpec(value="run a structured two-week dry-run schedule with three full rehearsals", polarity="constraint", session_introduced=2),
            VersionSpec(value="run the two-week dry-run plus record a pre-recorded backup video the night before the talk", polarity="constraint", session_introduced=3),
        ],
        current_query="The QCon keynote is in three weeks — set up my prep timeline.",
        required_behavior="Set up the two-week dry-run schedule with three rehearsals AND record a pre-recorded backup the night before.",
        invalid_behavior=["Just wing it", "Run dry-runs without the backup recording", "Record a backup without dry-runs"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-feature-flag-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's feature-flag rollout rule — three explicit narrowings: any → 1%/10%/100% staged → 1%/10%/100% with metric-gate at each stage",
        target_slot_id="feature_flag_rollout::v1", topic="feature_flag_rollout",
        versions=[
            VersionSpec(value="flip the feature flag to 100% as soon as the build is green", polarity="constraint", session_introduced=1),
            VersionSpec(value="roll out feature flags in stages: 1% then 10% then 100%", polarity="constraint", session_introduced=2),
            VersionSpec(value="roll out 1% then 10% then 100%, with a metric-gate check between each stage", polarity="constraint", session_introduced=3),
        ],
        current_query="Marcus's new ranking flag is ready to flip — what's the rollout?",
        required_behavior="Roll out the ranking flag at 1%, then 10%, then 100%, with a metric-gate check between each stage.",
        invalid_behavior=["Flip directly to 100%", "Roll out 1%/10%/100% without metric gates", "Skip the rollout entirely"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi triple (5)
    _trip(_s(sample_id="p3-multi-stack-trace-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's stack-trace tool — three-version chain: Sentry → Honeycomb → Embrace",
        target_slot_id="trace_tool::v1", topic="stack_trace_tool",
        versions=[
            VersionSpec(value="Sentry with the legacy issue grouping", polarity="prefer", session_introduced=1),
            VersionSpec(value="Honeycomb with the BubbleUp anomaly detection and the trigger boards", polarity="prefer", session_introduced=2),
            VersionSpec(value="Embrace with the user-session replays and the device-context dashboard", polarity="prefer", session_introduced=3),
        ],
        current_query="Wire up error tracking for the new mobile checkout flow.",
        required_behavior="Wire mobile checkout error tracking through Embrace using user-session replays and the device-context dashboard.",
        invalid_behavior=["Wire to Sentry", "Wire to Honeycomb", "Skip tracking"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-form-tool-001", target_type="object_preference", domain="business",
        target_description="user's contact-form tool — three-version chain: Wufoo → Formstack → Fillout",
        target_slot_id="form_tool::v1", topic="contact_form_tool",
        versions=[
            VersionSpec(value="Wufoo with the legacy paid pro tier", polarity="prefer", session_introduced=1),
            VersionSpec(value="Formstack with the conditional-logic builder and the Salesforce integration", polarity="prefer", session_introduced=2),
            VersionSpec(value="Fillout with the embeddable widgets and the Notion-database backend", polarity="prefer", session_introduced=3),
        ],
        current_query="Build a beta-signup intake page for the new product.",
        required_behavior="Build the beta-signup page on Fillout using the embeddable widgets and the Notion-database backend.",
        invalid_behavior=["Build on Wufoo", "Build on Formstack", "Build on a fourth tool"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-static-host-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's static-site host — three-version chain: GitHub Pages → Netlify → Vercel",
        target_slot_id="static_host::v1", topic="static_site_host",
        versions=[
            VersionSpec(value="GitHub Pages with the user-page source branch", polarity="prefer", session_introduced=1),
            VersionSpec(value="Netlify with the form handling and the deploy-preview branches", polarity="prefer", session_introduced=2),
            VersionSpec(value="Vercel with the edge functions and the preview-comments collaboration", polarity="prefer", session_introduced=3),
        ],
        current_query="Deploy the personal portfolio refresh.",
        required_behavior="Deploy the portfolio refresh on Vercel with edge functions and preview-comments collaboration.",
        invalid_behavior=["Deploy on GitHub Pages", "Deploy on Netlify", "Deploy on a self-hosted server"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-podcast-host-001", target_type="object_preference", domain="creative",
        target_description="user's podcast hosting platform — three-version chain: Anchor → Transistor → Captivate",
        target_slot_id="podcast_host::v1", topic="podcast_hosting_platform",
        versions=[
            VersionSpec(value="Anchor with the free unlimited storage tier", polarity="prefer", session_introduced=1),
            VersionSpec(value="Transistor with the multi-show plan and analytics", polarity="prefer", session_introduced=2),
            VersionSpec(value="Captivate with the dynamic insertion ads and the website builder", polarity="prefer", session_introduced=3),
        ],
        current_query="Upload tomorrow morning's recorded interview.",
        required_behavior="Upload the interview recording to Captivate using the dynamic insertion ads and website builder.",
        invalid_behavior=["Upload on Anchor", "Upload on Transistor", "Upload to YouTube only"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-coaching-format-001", target_type="conceptual_stance", domain="management",
        target_description="user's executive-coaching format — three-version chain: peer mastermind → 1:1 coach → group cohort (with revert to 1:1)",
        target_slot_id="coaching_format::v1", topic="executive_coaching_format",
        versions=[
            VersionSpec(value="monthly peer-mastermind group with five other directors", polarity="prefer", session_introduced=1),
            VersionSpec(value="biweekly 1:1 sessions with a dedicated executive coach", polarity="prefer", session_introduced=2),
            VersionSpec(value="quarterly cohort program with the structured curriculum and group calls", polarity="prefer", session_introduced=3),
            VersionSpec(value="biweekly 1:1 sessions with a dedicated executive coach", polarity="prefer", session_introduced=4),
        ],
        current_query="Block this month's coaching engagement on my calendar.",
        required_behavior="Block this month's coaching as biweekly 1:1 sessions with the dedicated executive coach.",
        invalid_behavior=["Block monthly peer-mastermind", "Block quarterly cohort program", "Skip coaching"],
        failure_patterns=["multi_version"], subtype="reverted")),

    # multi doublet (4)
    _doub(_s(sample_id="p3-multi-data-warehouse-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's data warehouse — four-version chain: Redshift → BigQuery → Snowflake → Databricks SQL",
        target_slot_id="data_warehouse::v1", topic="data_warehouse",
        versions=[
            VersionSpec(value="Amazon Redshift with the dense-storage cluster", polarity="prefer", session_introduced=1),
            VersionSpec(value="Google BigQuery with the on-demand query pricing", polarity="prefer", session_introduced=2),
            VersionSpec(value="Snowflake with the multi-cluster shared-data architecture", polarity="prefer", session_introduced=3),
            VersionSpec(value="Databricks SQL with the Unity Catalog and the lakehouse query engine", polarity="prefer", session_introduced=4),
        ],
        current_query="Land the new event stream into the warehouse for analytics.",
        required_behavior="Land the event stream into Databricks SQL using Unity Catalog and the lakehouse query engine.",
        invalid_behavior=["Land in Redshift", "Land in BigQuery", "Land in Snowflake"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-experiment-platform-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's A/B experiment platform — four-version chain: Optimizely → LaunchDarkly → Statsig → Eppo",
        target_slot_id="experiment_platform::v1", topic="experiment_platform",
        versions=[
            VersionSpec(value="Optimizely with the visual-editor variation builder", polarity="prefer", session_introduced=1),
            VersionSpec(value="LaunchDarkly with the feature flag and experimentation tier", polarity="prefer", session_introduced=2),
            VersionSpec(value="Statsig with the warehouse-native pulse-experiment runtime", polarity="prefer", session_introduced=3),
            VersionSpec(value="Eppo with the geographic-cluster randomization and CUPED variance reduction", polarity="prefer", session_introduced=4),
        ],
        current_query="Launch the new pricing-page experiment for measurement.",
        required_behavior="Launch the pricing-page experiment on Eppo with geographic-cluster randomization and CUPED variance reduction.",
        invalid_behavior=["Launch on Optimizely", "Launch on LaunchDarkly", "Launch on Statsig"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-async-msg-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's message queue — four-version chain: SQS → RabbitMQ → Kafka → NATS JetStream",
        target_slot_id="message_queue::v1", topic="message_queue",
        versions=[
            VersionSpec(value="AWS SQS with the standard queue and the lambda triggers", polarity="prefer", session_introduced=1),
            VersionSpec(value="RabbitMQ self-hosted with the topic-exchange routing", polarity="prefer", session_introduced=2),
            VersionSpec(value="Apache Kafka with the partitioned-topic streaming and Confluent connectors", polarity="prefer", session_introduced=3),
            VersionSpec(value="NATS JetStream with the work-queue persistence and the multi-tenancy", polarity="prefer", session_introduced=4),
        ],
        current_query="Wire the new order-processing async pipeline.",
        required_behavior="Wire the order-processing pipeline through NATS JetStream using work-queue persistence and multi-tenancy.",
        invalid_behavior=["Wire through AWS SQS", "Wire through RabbitMQ", "Wire through Apache Kafka"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-payroll-4v-001", target_type="object_preference", domain="business",
        target_description="user's small-business payroll — four-version chain: Gusto → Justworks → Rippling → Deel",
        target_slot_id="payroll::v1", topic="small_business_payroll",
        versions=[
            VersionSpec(value="Gusto with the basic plan and the auto-tax filings", polarity="prefer", session_introduced=1),
            VersionSpec(value="Justworks with the PEO benefits and HR compliance", polarity="prefer", session_introduced=2),
            VersionSpec(value="Rippling with the unified HR and IT identity provisioning", polarity="prefer", session_introduced=3),
            VersionSpec(value="Deel with the international-contractor coverage in 150 countries", polarity="prefer", session_introduced=4),
        ],
        current_query="Onboard the two new contractors who are based in Portugal and Argentina.",
        required_behavior="Onboard the contractors through Deel using its international-contractor coverage in 150 countries.",
        invalid_behavior=["Onboard through Gusto", "Onboard through Justworks", "Onboard through Rippling"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    # explicit (4) — non-daily_preference focus
    _trip(_s(sample_id="p3-explicit-load-test-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's load testing tool — explicit replacement of JMeter with k6",
        target_slot_id="load_test_tool::v1", topic="load_test_tool",
        versions=[
            VersionSpec(value="Apache JMeter with the GUI-based test plan builder", polarity="prefer", session_introduced=1),
            VersionSpec(value="k6 with the JavaScript-based scripting and the Grafana Cloud integration", polarity="prefer", session_introduced=2),
        ],
        current_query="Run a stress test on the new search endpoint before launch.",
        required_behavior="Run the stress test through k6 using the JavaScript-based scripting and Grafana Cloud integration.",
        invalid_behavior=["Run through Apache JMeter", "Run through a third tool", "Skip the test"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-feedback-rubric-001", target_type="conceptual_stance", domain="management",
        target_description="user's career-ladder feedback rubric — explicit replacement of CompetencyMatrix with the levelsfyi-aligned ladder",
        target_slot_id="career_rubric::v1", topic="career_ladder_rubric",
        versions=[
            VersionSpec(value="CompetencyMatrix with the four-axis grid by level", polarity="prefer", session_introduced=1),
            VersionSpec(value="the levelsfyi-aligned career ladder with the impact-scope and breadth-of-influence axes", polarity="prefer", session_introduced=2),
        ],
        current_query="Run Marcus's promotion case for the L6 review committee.",
        required_behavior="Frame Marcus's promotion case using the levelsfyi-aligned career ladder with the impact-scope and breadth-of-influence axes.",
        invalid_behavior=["Frame using CompetencyMatrix", "Frame using a custom rubric", "Skip the case write-up"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-research-tool-001", target_type="object_preference", domain="learning",
        target_description="user's academic research-paper search — explicit replacement of Google Scholar with Semantic Scholar",
        target_slot_id="paper_search::v1", topic="academic_paper_search",
        versions=[
            VersionSpec(value="Google Scholar with the citation-count-based ranking", polarity="prefer", session_introduced=1),
            VersionSpec(value="Semantic Scholar with the AI-summary and the citation-context graph", polarity="prefer", session_introduced=2),
        ],
        current_query="Find the most relevant survey on retrieval-augmented generation.",
        required_behavior="Find the survey through Semantic Scholar using the AI-summary and citation-context graph.",
        invalid_behavior=["Find through Google Scholar", "Find through arxiv-sanity", "Find through a generic search engine"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-status-tool-001", target_type="object_preference", domain="work_workflow",
        target_description="team's incident-status page — explicit replacement of Statuspage with Instatus",
        target_slot_id="status_page::v1", topic="incident_status_page",
        versions=[
            VersionSpec(value="Atlassian Statuspage with the legacy subscriber email tier", polarity="prefer", session_introduced=1),
            VersionSpec(value="Instatus with the real-time updates and the public Slack widget", polarity="prefer", session_introduced=2),
        ],
        current_query="Post a public update for the ongoing checkout incident.",
        required_behavior="Post the checkout-incident update on Instatus using real-time updates and the public Slack widget.",
        invalid_behavior=["Post on Statuspage", "Tweet from the company account", "Skip the public update"],
        failure_patterns=["explicit_replacement"])),

    # repeated_use (3)
    _drift(_s(sample_id="p3-drift-debug-tool-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's local debugger — drifted to dap-mode in Emacs from the IDE breakpoint UI, repeated active use",
        target_slot_id="debugger::v1", topic="local_debugger",
        versions=[
            VersionSpec(value="VSCode IDE breakpoint UI with the visual call-stack and watches panel", polarity="prefer", session_introduced=1),
            VersionSpec(value="dap-mode in Emacs with the GDB/MI protocol and the headless terminal layout", polarity="prefer", session_introduced=2),
        ],
        current_query="Step through the auth-token rotation bug locally.",
        required_behavior="Step through the auth-token rotation bug locally using dap-mode in Emacs with the GDB/MI protocol.",
        invalid_behavior=["Step through with the VSCode IDE breakpoint UI", "Step through with print-debugging only", "Skip the debugging"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-stand-time-001", target_type="procedural_constraint", domain="lifestyle",
        target_description="user's afternoon energy break — drifted to a 5-minute walk around the block from a coffee refill, repeated active use",
        target_slot_id="afternoon_break::v1", topic="afternoon_energy_break",
        versions=[
            VersionSpec(value="3 PM coffee refill from the office espresso machine", polarity="constraint", session_introduced=1),
            VersionSpec(value="5-minute walk around the block before returning to the desk", polarity="constraint", session_introduced=2),
        ],
        current_query="It's 3 PM and I feel sluggish — what's my reset?",
        required_behavior="Take a 5-minute walk around the block before returning to the desk.",
        invalid_behavior=["Get a coffee refill from the office espresso machine", "Take a power nap", "Push through without a break"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-doc-storage-loc-001", target_type="object_preference", domain="work_workflow",
        target_description="user's spec-doc home — drifted to a Notion company-wide database from per-team Google Drive folders, repeated active use",
        target_slot_id="spec_home::v1", topic="spec_doc_home",
        versions=[
            VersionSpec(value="per-team Google Drive folders organized by quarter", polarity="prefer", session_introduced=1),
            VersionSpec(value="company-wide Notion database with the linked-relations across teams", polarity="prefer", session_introduced=2),
        ],
        current_query="Save the new fraud-detection spec where the team can find it later.",
        required_behavior="Save the fraud-detection spec in the company-wide Notion database with the linked-relations across teams.",
        invalid_behavior=["Save in per-team Google Drive folder", "Save in a personal Google Doc", "Skip saving"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    # abandonment (2)
    _drift(_s(sample_id="p3-drift-personal-trainer-001", target_type="procedural_constraint", domain="fitness",
        target_description="user's strength-coach engagement — abandoned the in-person personal-trainer sessions; programming-only via Substack subscription now",
        target_slot_id="strength_coach::v1", topic="strength_coach_engagement",
        versions=[
            VersionSpec(value="weekly in-person personal-trainer sessions at the local gym", polarity="constraint", session_introduced=1),
            VersionSpec(value="programming-only Substack subscription delivering weekly workout plans", polarity="constraint", session_introduced=2),
        ],
        current_query="What's tomorrow's strength session?",
        required_behavior="Tomorrow's strength session follows the workout plan from the weekly Substack programming subscription.",
        invalid_behavior=["Tomorrow's session is with the in-person personal trainer", "Skip strength entirely", "Wing the session without programming"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-old-vendor-list-001", target_type="procedural_constraint", domain="business",
        target_description="user's vendor-payment workflow — abandoned the manual ACH transfers; auto-pay via Bill.com only now",
        target_slot_id="vendor_payment::v1", topic="vendor_payment_workflow",
        versions=[
            VersionSpec(value="manual ACH transfers initiated each Friday from the business checking account", polarity="constraint", session_introduced=1),
            VersionSpec(value="auto-pay through Bill.com with the approval workflow and the audit log", polarity="constraint", session_introduced=2),
        ],
        current_query="Three vendor invoices arrived this week — when do they get paid?",
        required_behavior="The three vendor invoices auto-pay through Bill.com under the approval workflow with the audit log.",
        invalid_behavior=["Initiate manual ACH transfers Friday", "Pay by paper check", "Hold payments until next month"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    # gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-content-narrow-001", target_type="conceptual_stance", domain="creative",
        target_description="user's content-output focus — gradually narrowed from any topic to engineering deep-dives only via cumulative preference signals",
        target_slot_id="content_focus::v1", topic="content_output_focus",
        versions=[
            VersionSpec(value="any topic the user feels expertise in — engineering, books, productivity, or career", polarity="prefer", session_introduced=1),
            VersionSpec(value="engineering deep-dives only — at least 2000 words explaining a specific system or trade-off", polarity="prefer", session_introduced=2),
        ],
        current_query="A book-review piece is half-drafted — should I push to ship it?",
        required_behavior="Hold the book-review piece; the user only ships engineering deep-dives of at least 2000 words explaining a specific system or trade-off.",
        invalid_behavior=["Push the book-review piece", "Convert it into a productivity essay", "Cross-post and see what happens"],
        failure_patterns=["implicit_drift"]), "gradual_narrowing"),
]
