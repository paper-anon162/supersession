"""Phase 3 batch H — 25 spines, heavy on narrow + multi to fill the
biggest underfills.

Distribution:
  6 narrow, 5 multi triple, 4 multi doublet, 4 explicit (non-daily
  preference), 3 repeated_use, 2 abandonment, 1 gradual_narrowing
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


PHASE3_BATCH_H: list[Phase3GroupSpec] = [

    # narrow (6)
    _trip(_s(
        sample_id="p3-narrow-pr-merge-001",
        target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's PR merge gate — three explicit narrowings: green CI → green CI plus one approval → green CI plus two approvals plus security scan pass",
        target_slot_id="pr_merge::v1", topic="pr_merge_gate",
        versions=[
            VersionSpec(value="merge once continuous integration is green", polarity="constraint", session_introduced=1),
            VersionSpec(value="merge once CI is green plus one peer approval", polarity="constraint", session_introduced=2),
            VersionSpec(value="merge once CI is green plus two peer approvals plus the security-scan workflow pass", polarity="constraint", session_introduced=3),
        ],
        current_query="Marcus's auth-token branch is ready — can it ship?",
        required_behavior="Ship Marcus's branch only after CI is green, two peer approvals are in, and the security-scan workflow has passed.",
        invalid_behavior=["Ship after CI green only", "Ship after one approval", "Ship without the security scan"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-doc-publish-001",
        target_type="procedural_constraint", domain="work_workflow",
        target_description="user's documentation publish criteria — three explicit narrowings: any → reviewed-by-tech-lead → reviewed by tech lead plus example code tested",
        target_slot_id="doc_publish::v1", topic="documentation_publish",
        versions=[
            VersionSpec(value="publish once the author marks the doc complete", polarity="constraint", session_introduced=1),
            VersionSpec(value="publish only after the technical lead has reviewed and approved", polarity="constraint", session_introduced=2),
            VersionSpec(value="publish only after the tech lead reviews and the example code in the doc has been tested by a second engineer", polarity="constraint", session_introduced=3),
        ],
        current_query="Sarah marked the new SDK guide ready — should it go live?",
        required_behavior="Hold publishing until the tech lead has approved AND a second engineer has tested the example code.",
        invalid_behavior=["Publish on author completion", "Publish on lead approval alone", "Publish on second-engineer testing alone"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-incident-page-001",
        target_type="procedural_constraint", domain="work_workflow",
        target_description="user's incident-page criteria — three explicit narrowings: any user complaint → revenue-affecting → revenue-affecting plus customer-facing >5% impact",
        target_slot_id="incident_page::v1", topic="incident_paging_criteria",
        versions=[
            VersionSpec(value="page on-call for any user complaint that arrives in the support channel", polarity="constraint", session_introduced=1),
            VersionSpec(value="page on-call only when the complaint correlates with revenue-affecting telemetry", polarity="constraint", session_introduced=2),
            VersionSpec(value="page on-call only for revenue-affecting issues with measured customer-facing impact above five percent", polarity="constraint", session_introduced=3),
        ],
        current_query="Three users just complained about slow checkout — do I page on-call?",
        required_behavior="Page on-call only if the slow-checkout reports correlate with revenue-affecting telemetry AND measured customer-facing impact exceeds five percent.",
        invalid_behavior=["Page on three user complaints alone", "Page on revenue correlation without 5% threshold", "Skip paging entirely"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-feedback-asks-001",
        target_type="conceptual_stance", domain="management",
        target_description="user's report-feedback ask criteria — three explicit narrowings: any topic → behavior-only → behavior-only with one concrete example",
        target_slot_id="feedback_asks::v1", topic="report_feedback_asks",
        versions=[
            VersionSpec(value="give feedback on any topic the user notices in the report's work", polarity="prefer", session_introduced=1),
            VersionSpec(value="give feedback only on observable behavior, never on traits or motivations", polarity="prefer", session_introduced=2),
            VersionSpec(value="give feedback only on observable behavior, anchored with at least one concrete example from the past week", polarity="prefer", session_introduced=3),
        ],
        current_query="Marcus shipped the auth feature with three regressions — give him feedback.",
        required_behavior="Frame the feedback on Marcus's observable behavior shipping the auth feature, anchored with at least one concrete example from the past week.",
        invalid_behavior=["Frame feedback on Marcus's perceived motivation", "Frame on behavior without a concrete example", "Frame on personality traits"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-conf-talk-001",
        target_type="conceptual_stance", domain="learning",
        target_description="user's conference talk submission criteria — three explicit narrowings: any topic → first-author original → first-author original with deployed production system",
        target_slot_id="conf_submission::v1", topic="conference_talk_submission",
        versions=[
            VersionSpec(value="submit talk proposals on any topic the user finds interesting", polarity="prefer", session_introduced=1),
            VersionSpec(value="submit only proposals where the user is first-author on original work", polarity="prefer", session_introduced=2),
            VersionSpec(value="submit only first-author original-work proposals where the system has been deployed in production for at least six months", polarity="prefer", session_introduced=3),
        ],
        current_query="QCon's CFP closes Friday — should I submit my talk on consensus protocols?",
        required_behavior="Submit only if the consensus protocol is the user's first-author original work AND has been deployed in production at least six months.",
        invalid_behavior=["Submit any interesting talk", "Submit a co-author proposal", "Submit a first-author proposal not yet deployed"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-pull-rotation-001",
        target_type="procedural_constraint", domain="management",
        target_description="user's on-call pull rule — three explicit narrowings: anyone → senior engineers → senior engineers who are not also tech-lead",
        target_slot_id="oncall_pull::v1", topic="oncall_rotation_pull",
        versions=[
            VersionSpec(value="any team member can be pulled into the rotation", polarity="constraint", session_introduced=1),
            VersionSpec(value="only senior engineers (L5 and above) are pulled into the rotation", polarity="constraint", session_introduced=2),
            VersionSpec(value="only senior engineers (L5 and above) who are not also serving as a tech lead are pulled into the rotation", polarity="constraint", session_introduced=3),
        ],
        current_query="Priya, an L5 tech lead, has open shifts next quarter — should she go on rotation?",
        required_behavior="Skip Priya from the rotation; she is L5 but also serving as a tech lead.",
        invalid_behavior=["Add Priya since she is on the team", "Add Priya since she is L5", "Add Priya for half the shifts"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    # multi triple (5)
    _trip(_s(
        sample_id="p3-multi-cdn-001",
        target_type="object_preference", domain="tech_workflow",
        target_description="team's CDN — three-version chain: Akamai → Fastly → Cloudflare",
        target_slot_id="cdn::v1", topic="content_delivery_network",
        versions=[
            VersionSpec(value="Akamai with the legacy origin pull configuration", polarity="prefer", session_introduced=1),
            VersionSpec(value="Fastly with the VCL custom edge logic", polarity="prefer", session_introduced=2),
            VersionSpec(value="Cloudflare with the Workers runtime and the Argo smart routing", polarity="prefer", session_introduced=3),
        ],
        current_query="Front the new marketing site behind a CDN.",
        required_behavior="Front the marketing site behind Cloudflare with the Workers runtime and Argo smart routing.",
        invalid_behavior=["Front behind Akamai", "Front behind Fastly", "Skip the CDN"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-multi-search-engine-001",
        target_type="object_preference", domain="tech_workflow",
        target_description="team's search backend — three-version chain: Solr → Elasticsearch → Typesense",
        target_slot_id="search_backend::v1", topic="search_backend",
        versions=[
            VersionSpec(value="Apache Solr with the legacy schema-based config", polarity="prefer", session_introduced=1),
            VersionSpec(value="Elasticsearch with the dynamic mapping and the index-lifecycle policies", polarity="prefer", session_introduced=2),
            VersionSpec(value="Typesense with the typo-tolerant ranking and the geo-spatial filters", polarity="prefer", session_introduced=3),
        ],
        current_query="Wire the new product-search endpoint to a search backend.",
        required_behavior="Wire the product-search endpoint to Typesense using the typo-tolerant ranking and geo-spatial filters.",
        invalid_behavior=["Wire to Solr", "Wire to Elasticsearch", "Wire to a third backend"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-multi-language-runtime-001",
        target_type="object_preference", domain="tech_workflow",
        target_description="team's primary backend language — three-version chain: Ruby → Go → Rust",
        target_slot_id="backend_language::v1", topic="primary_backend_language",
        versions=[
            VersionSpec(value="Ruby with the legacy Rails 6 web stack", polarity="prefer", session_introduced=1),
            VersionSpec(value="Go with the standard library plus the chi router", polarity="prefer", session_introduced=2),
            VersionSpec(value="Rust with the Axum framework and the tokio async runtime", polarity="prefer", session_introduced=3),
        ],
        current_query="Pick the language for the new fraud-detection service.",
        required_behavior="Pick Rust with the Axum framework and tokio async runtime for the fraud-detection service.",
        invalid_behavior=["Pick Ruby on Rails", "Pick Go with chi", "Pick a fourth language"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-multi-task-coord-001",
        target_type="conceptual_stance", domain="management",
        target_description="user's team coordination model — three-version chain: weekly all-hands → biweekly leads sync → monthly written summary",
        target_slot_id="team_coord::v1", topic="team_coordination_model",
        versions=[
            VersionSpec(value="weekly hour-long all-hands video call with everyone in the meeting", polarity="prefer", session_introduced=1),
            VersionSpec(value="biweekly 30-minute leads-only sync with the leads cascading information to their teams", polarity="prefer", session_introduced=2),
            VersionSpec(value="monthly written summary posted to the team Notion page replacing live syncs entirely", polarity="prefer", session_introduced=3),
        ],
        current_query="Set up next month's team coordination cadence.",
        required_behavior="Set up next month's coordination as a monthly written summary posted to the team Notion page.",
        invalid_behavior=["Set up weekly all-hands video calls", "Set up biweekly leads-only syncs", "Skip coordination entirely"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-multi-storage-arch-001",
        target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's data lake — three-version chain: HDFS → S3 raw → S3 with Iceberg tables (with one revert back to S3 raw)",
        target_slot_id="data_lake::v1", topic="data_lake_architecture",
        versions=[
            VersionSpec(value="HDFS on the bare-metal Hadoop cluster", polarity="prefer", session_introduced=1),
            VersionSpec(value="raw Parquet files written directly to S3 with no table layer", polarity="prefer", session_introduced=2),
            VersionSpec(value="S3 with Apache Iceberg tables and the Trino query engine", polarity="prefer", session_introduced=3),
            VersionSpec(value="raw Parquet files written directly to S3 with no table layer", polarity="prefer", session_introduced=4),
        ],
        current_query="Land the new event-stream batch in the data lake.",
        required_behavior="Land the event-stream batch as raw Parquet files written directly to S3 with no table layer.",
        invalid_behavior=["Land on HDFS Hadoop cluster", "Land in S3 with Apache Iceberg tables", "Skip the lake entirely"],
        failure_patterns=["multi_version"], subtype="reverted",
    )),

    # multi doublet (4) — 4-version chains
    _doub(_s(
        sample_id="p3-multi-cache-4v-001",
        target_type="object_preference", domain="tech_workflow",
        target_description="team's distributed cache — four-version chain: memcached → Redis → DynamoDB cache → Redis Cluster",
        target_slot_id="distributed_cache::v1", topic="distributed_cache",
        versions=[
            VersionSpec(value="memcached on the dedicated cache fleet", polarity="prefer", session_introduced=1),
            VersionSpec(value="Redis 5 with the AOF persistence and replica-of replication", polarity="prefer", session_introduced=2),
            VersionSpec(value="DynamoDB with DAX accelerator as the primary cache layer", polarity="prefer", session_introduced=3),
            VersionSpec(value="Redis Cluster with hash-slot sharding and the multi-AZ replicas", polarity="prefer", session_introduced=4),
        ],
        current_query="Add a hot-key cache layer to the new pricing service.",
        required_behavior="Add Redis Cluster with hash-slot sharding and multi-AZ replicas as the pricing-service cache.",
        invalid_behavior=["Add memcached", "Add single-node Redis 5 with AOF", "Add DynamoDB with DAX"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _doub(_s(
        sample_id="p3-multi-meeting-cadence-4v-001",
        target_type="procedural_constraint", domain="management",
        target_description="user's leadership review cadence — four-version chain: monthly → biweekly → weekly → quarterly written-only",
        target_slot_id="leadership_review_cadence::v1", topic="leadership_review_cadence",
        versions=[
            VersionSpec(value="monthly two-hour leadership review on the first Tuesday", polarity="constraint", session_introduced=1),
            VersionSpec(value="biweekly one-hour leadership review every other Tuesday", polarity="constraint", session_introduced=2),
            VersionSpec(value="weekly 30-minute leadership review every Tuesday morning", polarity="constraint", session_introduced=3),
            VersionSpec(value="quarterly two-day off-site with no live cadence in between", polarity="constraint", session_introduced=4),
        ],
        current_query="Set up the next round of leadership reviews on my calendar.",
        required_behavior="Set up a quarterly two-day off-site for leadership review with no live cadence in between.",
        invalid_behavior=["Set up monthly two-hour reviews", "Set up biweekly one-hour reviews", "Set up weekly 30-minute reviews"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _doub(_s(
        sample_id="p3-multi-goals-framework-4v-001",
        target_type="conceptual_stance", domain="management",
        target_description="user's quarterly goal-setting framework — four-version chain: SMART → OKRs → V2MOM → DRI-driven NSMs",
        target_slot_id="goal_framework::v1", topic="quarterly_goal_framework",
        versions=[
            VersionSpec(value="SMART goals with the standard specific-measurable-achievable-relevant-timebound criteria", polarity="prefer", session_introduced=1),
            VersionSpec(value="OKRs with the objectives-and-key-results structure aligned to company OKRs", polarity="prefer", session_introduced=2),
            VersionSpec(value="V2MOM with the vision-values-methods-obstacles-measures structure", polarity="prefer", session_introduced=3),
            VersionSpec(value="DRI-driven North Star Metrics with a single accountable engineer per metric", polarity="prefer", session_introduced=4),
        ],
        current_query="Kick off this quarter's planning for the team.",
        required_behavior="Kick off this quarter's planning using the DRI-driven North Star Metrics framework with one accountable engineer per metric.",
        invalid_behavior=["Use SMART goals", "Use OKRs", "Use V2MOM"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _doub(_s(
        sample_id="p3-multi-scheduling-tool-4v-001",
        target_type="object_preference", domain="productivity",
        target_description="user's external-meeting scheduling tool — four-version chain: x.ai → Calendly → SavvyCal → motion-AI assistant",
        target_slot_id="scheduling_tool::v1", topic="external_meeting_scheduler",
        versions=[
            VersionSpec(value="x.ai with the email-bot Andrew that handled scheduling on the user's behalf", polarity="prefer", session_introduced=1),
            VersionSpec(value="Calendly with the personalized booking page and round-robin team links", polarity="prefer", session_introduced=2),
            VersionSpec(value="SavvyCal with the overlay availability and ranked time preferences", polarity="prefer", session_introduced=3),
            VersionSpec(value="Motion AI assistant with the auto-rescheduling and priority-based time blocks", polarity="prefer", session_introduced=4),
        ],
        current_query="Send a scheduling link to the journalist who wants to interview me next week.",
        required_behavior="Send a Motion AI assistant scheduling link with the auto-rescheduling and priority-based time blocks.",
        invalid_behavior=["Send an x.ai email-bot link", "Send a Calendly link", "Send a SavvyCal link"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    # explicit (4) — non-daily_preference to fix cell breach
    _trip(_s(
        sample_id="p3-explicit-deployment-tool-001",
        target_type="object_preference", domain="tech_workflow",
        target_description="team's deployment tool — explicit replacement of Spinnaker with ArgoCD",
        target_slot_id="deployment_tool::v1", topic="deployment_tool",
        versions=[
            VersionSpec(value="Spinnaker with the multi-cloud pipeline templates", polarity="prefer", session_introduced=1),
            VersionSpec(value="ArgoCD with the Git-Ops sync waves and the rollback-to-revision workflow", polarity="prefer", session_introduced=2),
        ],
        current_query="Push the new ranking model from staging to production.",
        required_behavior="Push the ranking model from staging to production through ArgoCD using the Git-Ops sync waves.",
        invalid_behavior=["Push through Spinnaker", "Push directly via kubectl", "Skip the push"],
        failure_patterns=["explicit_replacement"],
    )),

    _trip(_s(
        sample_id="p3-explicit-knowledge-search-001",
        target_type="object_preference", domain="work_workflow",
        target_description="team's internal knowledge search — explicit replacement of Confluence search with Glean",
        target_slot_id="knowledge_search::v1", topic="internal_knowledge_search",
        versions=[
            VersionSpec(value="Confluence built-in search with the wiki indexed pages", polarity="prefer", session_introduced=1),
            VersionSpec(value="Glean with the unified cross-source search and the AI-summarized results", polarity="prefer", session_introduced=2),
        ],
        current_query="Pull up the runbook on auth-token rotation.",
        required_behavior="Pull up the auth-token rotation runbook through Glean using the unified cross-source search.",
        invalid_behavior=["Pull through Confluence built-in search", "Browse manually", "Ask in Slack"],
        failure_patterns=["explicit_replacement"],
    )),

    _trip(_s(
        sample_id="p3-explicit-class-platform-001",
        target_type="object_preference", domain="learning",
        target_description="user's online-class platform — explicit replacement of Coursera with edX",
        target_slot_id="class_platform::v1", topic="online_class_platform",
        versions=[
            VersionSpec(value="Coursera with the Specializations and Plus subscription", polarity="prefer", session_introduced=1),
            VersionSpec(value="edX with the verified-certificate program and MicroMasters tracks", polarity="prefer", session_introduced=2),
        ],
        current_query="Sign me up for an introductory machine-learning course this fall.",
        required_behavior="Sign up for an intro machine-learning course on edX using the verified-certificate program.",
        invalid_behavior=["Sign up on Coursera Specializations", "Sign up on a third platform", "Skip the course"],
        failure_patterns=["explicit_replacement"],
    )),

    _trip(_s(
        sample_id="p3-explicit-form-builder-001",
        target_type="object_preference", domain="business",
        target_description="team's customer-survey form tool — explicit replacement of Typeform with Tally",
        target_slot_id="survey_tool::v1", topic="customer_survey_tool",
        versions=[
            VersionSpec(value="Typeform with the conversational one-question-at-a-time format", polarity="prefer", session_introduced=1),
            VersionSpec(value="Tally with the unlimited submissions and the no-code logic blocks", polarity="prefer", session_introduced=2),
        ],
        current_query="Build a quick onboarding-feedback survey for new customers.",
        required_behavior="Build the onboarding-feedback survey on Tally using the unlimited submissions and no-code logic blocks.",
        invalid_behavior=["Build on Typeform", "Build on Google Forms", "Skip the survey"],
        failure_patterns=["explicit_replacement"],
    )),

    # repeated_use (3) — work / comm focused
    _drift(_s(
        sample_id="p3-drift-status-update-cadence-001",
        target_type="procedural_constraint", domain="work_communication",
        target_description="user's status update timing — drifted to a Friday end-of-day post from a Monday morning post, repeated active use",
        target_slot_id="status_update_timing::v1", topic="status_update_timing",
        versions=[
            VersionSpec(value="Monday morning status post to the team channel before the standup", polarity="constraint", session_introduced=1),
            VersionSpec(value="Friday end-of-day status post wrapping up the week with weekend follow-ups", polarity="constraint", session_introduced=2),
        ],
        current_query="When am I posting this week's status this time?",
        required_behavior="Post this week's status on Friday end-of-day, wrapping up the week with weekend follow-ups.",
        invalid_behavior=["Post Monday morning before standup", "Post mid-week ad-hoc", "Skip the status post"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-skill-practice-001",
        target_type="procedural_constraint", domain="learning",
        target_description="user's keyboard-practice habit — drifted to a 20-minute morning slot before email from a 45-minute evening session, repeated active use",
        target_slot_id="keyboard_practice::v1", topic="keyboard_practice_habit",
        versions=[
            VersionSpec(value="45-minute evening practice session after dinner with the metronome at 80 BPM", polarity="constraint", session_introduced=1),
            VersionSpec(value="20-minute morning slot before opening email with the metronome at 100 BPM", polarity="constraint", session_introduced=2),
        ],
        current_query="Block tomorrow's piano work on my calendar.",
        required_behavior="Block tomorrow's piano work as a 20-minute morning slot before opening email, metronome at 100 BPM.",
        invalid_behavior=["Block a 45-minute evening session after dinner", "Block any time slot without the morning constraint", "Skip the block entirely"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-speaking-prep-001",
        target_type="conceptual_stance", domain="work_communication",
        target_description="user's keynote-prep style — drifted to memorizing the first three minutes verbatim from making slide notecards, repeated active use",
        target_slot_id="keynote_prep::v1", topic="keynote_prep_style",
        versions=[
            VersionSpec(value="slide notecards drafted the night before with bullet-point reminders per slide", polarity="prefer", session_introduced=1),
            VersionSpec(value="memorizing the first three minutes verbatim and ad-libbing the rest with no notes", polarity="prefer", session_introduced=2),
        ],
        current_query="The Q4 all-hands keynote is in two days — get me ready.",
        required_behavior="Prepare by memorizing the first three minutes verbatim; ad-lib the rest with no notes.",
        invalid_behavior=["Prepare by drafting slide notecards with bullet-point reminders", "Prepare a full word-for-word script", "Don't prepare at all"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    # abandonment (2)
    _drift(_s(
        sample_id="p3-drift-staff-meeting-001",
        target_type="procedural_constraint", domain="management",
        target_description="user's all-staff meeting — abandoned the monthly all-staff Zoom; written-only quarterly memo replaces it",
        target_slot_id="all_staff::v1", topic="all_staff_meeting",
        versions=[
            VersionSpec(value="monthly all-staff Zoom call with the live Q&A segment at the end", polarity="constraint", session_introduced=1),
            VersionSpec(value="quarterly written-only memo posted to the company-wide Notion homepage", polarity="constraint", session_introduced=2),
        ],
        current_query="Update the company on the new fraud-team org structure.",
        required_behavior="Post a quarterly written memo to the company-wide Notion homepage announcing the fraud-team org structure.",
        invalid_behavior=["Schedule a monthly all-staff Zoom", "Send an all-employee email", "Skip the announcement"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    _drift(_s(
        sample_id="p3-drift-old-skill-001",
        target_type="procedural_constraint", domain="learning",
        target_description="user's research-paper reading source — abandoned the printed-PDF stack; iPad annotation-only now",
        target_slot_id="paper_reading::v1", topic="research_paper_reading",
        versions=[
            VersionSpec(value="printed PDFs read with the highlighter and clipped to the binder", polarity="constraint", session_introduced=1),
            VersionSpec(value="iPad annotation in GoodNotes with the synced cloud library", polarity="constraint", session_introduced=2),
        ],
        current_query="The new ICML proceedings just dropped — pick three to read.",
        required_behavior="Pick three ICML papers to read on the iPad in GoodNotes with the synced cloud library.",
        invalid_behavior=["Print the PDFs to read with a highlighter", "Read on the laptop", "Skip the papers"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    # gradual_narrowing (1)
    _drift(_s(
        sample_id="p3-drift-budget-narrow-001",
        target_type="conceptual_stance", domain="business",
        target_description="user's discretionary-budget criteria — gradually narrowed from any vendor to vendors with under $5K annual contract via cumulative preference",
        target_slot_id="discretionary_budget::v1", topic="discretionary_budget_criteria",
        versions=[
            VersionSpec(value="any vendor request that fits within the discretionary line item", polarity="prefer", session_introduced=1),
            VersionSpec(value="only vendors with annual contracts under five thousand dollars and a one-page justification", polarity="prefer", session_introduced=2),
        ],
        current_query="A new analytics vendor wants $12K annually — can I sign?",
        required_behavior="Decline the analytics vendor; the $12K annual contract exceeds the under-$5K threshold.",
        invalid_behavior=["Approve since it's discretionary", "Approve with a request to negotiate down", "Approve only the first quarter"],
        failure_patterns=["implicit_drift"],
    ), "gradual_narrowing"),
]
