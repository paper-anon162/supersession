"""Phase 3 batch N — 25 spines."""

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


PHASE3_BATCH_N: list[Phase3GroupSpec] = [
    # narrow (5)
    _trip(_s(sample_id="p3-narrow-pull-bug-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's bug-reporting requirement — three explicit narrowings: any → reproducer → reproducer + minimal-failing example",
        target_slot_id="bug_report::v1", topic="bug_reporting_requirement",
        versions=[
            VersionSpec(value="accept any bug report submitted to the support channel", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept only bug reports that include a step-by-step reproducer", polarity="constraint", session_introduced=2),
            VersionSpec(value="accept only bug reports with a step-by-step reproducer plus a minimal failing example in code", polarity="constraint", session_introduced=3),
        ],
        current_query="A user filed a bug saying 'login is broken' with no further detail — accept it?",
        required_behavior="Reject the bug; the report needs a step-by-step reproducer AND a minimal failing example.",
        invalid_behavior=["Accept any report that arrives", "Accept reports with reproducer alone", "Accept on a code example alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-meeting-prep-001", target_type="procedural_constraint", domain="management",
        target_description="user's executive-meeting prep — three explicit narrowings: any → 24-hour-deck → 24-hour-deck + 5-page memo",
        target_slot_id="exec_prep::v1", topic="executive_meeting_prep",
        versions=[
            VersionSpec(value="prepare for executive meetings the way the day allows", polarity="constraint", session_introduced=1),
            VersionSpec(value="prepare a polished slide deck circulated 24 hours ahead of every executive meeting", polarity="constraint", session_introduced=2),
            VersionSpec(value="prepare a polished deck circulated 24 hours ahead plus a five-page background memo", polarity="constraint", session_introduced=3),
        ],
        current_query="The board's quarterly review is in two weeks — what do I prep?",
        required_behavior="Prep a polished slide deck circulated 24 hours ahead AND a five-page background memo.",
        invalid_behavior=["Prep loosely as the day allows", "Prep slide deck without the memo", "Prep memo without the slide deck"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-investing-due-diligence-001", target_type="procedural_constraint", domain="business",
        target_description="user's startup-investing due diligence — three explicit narrowings: any → reference checks → reference checks + product walkthrough",
        target_slot_id="diligence::v1", topic="startup_due_diligence",
        versions=[
            VersionSpec(value="invest based on the founder pitch alone", polarity="constraint", session_introduced=1),
            VersionSpec(value="invest only after backchannel reference checks with two former colleagues of the founder", polarity="constraint", session_introduced=2),
            VersionSpec(value="invest only after backchannel reference checks with two former colleagues AND a hands-on product walkthrough", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend introduced me to a YC W26 founder asking for a check — what's my next step?",
        required_behavior="Pursue only if I can do backchannel reference checks with two former colleagues AND a hands-on product walkthrough.",
        invalid_behavior=["Decide on the founder pitch alone", "Decide on reference checks alone", "Decide on product walkthrough alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-coffee-buy-001", target_type="object_preference", domain="food",
        target_description="user's coffee bean criteria — three explicit narrowings: any roast → light roast only → light roast Ethiopian only",
        target_slot_id="coffee_bean::v1", topic="coffee_bean_criteria",
        versions=[
            VersionSpec(value="any whole-bean coffee that the user finds at the local roaster", polarity="prefer", session_introduced=1),
            VersionSpec(value="only light-roast whole-bean coffee, no medium or dark roasts", polarity="prefer", session_introduced=2),
            VersionSpec(value="only light-roast whole-bean coffee from Ethiopian origin", polarity="prefer", session_introduced=3),
        ],
        current_query="The corner roaster has a fresh bag of medium-roast Honduran on the shelf — buy it?",
        required_behavior="Pass on the medium-roast Honduran; user only buys light-roast Ethiopian whole-bean.",
        invalid_behavior=["Buy the medium-roast Honduran", "Buy any light-roast", "Buy a dark-roast Ethiopian"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-ride-share-001", target_type="object_preference", domain="travel",
        target_description="user's ride-share criteria — three explicit narrowings: any service → Uber Black only → Uber Black with 4.9+ rating",
        target_slot_id="rideshare::v1", topic="rideshare_criteria",
        versions=[
            VersionSpec(value="book any ride-share service that has shortest ETA at the moment", polarity="prefer", session_introduced=1),
            VersionSpec(value="book only Uber Black tier rides regardless of ETA", polarity="prefer", session_introduced=2),
            VersionSpec(value="book only Uber Black tier rides with a driver rating of 4.9 stars or higher", polarity="prefer", session_introduced=3),
        ],
        current_query="I need a ride to the airport in 20 minutes — book one.",
        required_behavior="Book an Uber Black ride with a driver rated 4.9 stars or higher.",
        invalid_behavior=["Book the fastest available ride", "Book any Uber Black", "Book a Lyft Lux"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi triple (4)
    _trip(_s(sample_id="p3-multi-static-typing-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's Python type-checker — three-version chain: mypy → pyright → ty",
        target_slot_id="py_type_checker::v1", topic="python_type_checker",
        versions=[
            VersionSpec(value="mypy with the legacy strict-optional-flag configuration", polarity="prefer", session_introduced=1),
            VersionSpec(value="pyright with the basic-mode editor integration and the strict-mode CI step", polarity="prefer", session_introduced=2),
            VersionSpec(value="ty (Astral) with the Rust-based fast-incremental type checker and the editor LSP", polarity="prefer", session_introduced=3),
        ],
        current_query="Add type checking to the new payments microservice CI.",
        required_behavior="Add type checking to the payments microservice CI using ty (Astral) with the Rust-based fast-incremental checker.",
        invalid_behavior=["Add mypy", "Add pyright", "Skip type checking"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-test-runner-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's Python test runner — three-version chain: nose → pytest → ward",
        target_slot_id="py_test_runner::v1", topic="python_test_runner",
        versions=[
            VersionSpec(value="nose with the legacy auto-discovery and the plugins.coverage", polarity="prefer", session_introduced=1),
            VersionSpec(value="pytest with the parametrize fixtures and the plugin ecosystem", polarity="prefer", session_introduced=2),
            VersionSpec(value="ward with the descriptive-test-name DSL and the parallel test execution", polarity="prefer", session_introduced=3),
        ],
        current_query="Set up the test runner for the new fraud-rules engine.",
        required_behavior="Set up the test runner with ward using the descriptive-test-name DSL.",
        invalid_behavior=["Set up nose", "Set up pytest", "Set up unittest"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-finance-tracker-001", target_type="object_preference", domain="business",
        target_description="user's expense-tracking app — three-version chain: Mint → Personal Capital → Copilot",
        target_slot_id="expense_tracker::v1", topic="expense_tracking_app",
        versions=[
            VersionSpec(value="Mint with the legacy automatic-categorization and the budget alerts", polarity="prefer", session_introduced=1),
            VersionSpec(value="Personal Capital with the net-worth tracker and retirement projections", polarity="prefer", session_introduced=2),
            VersionSpec(value="Copilot Money with the AI-rule-based categorization and the iCloud sync", polarity="prefer", session_introduced=3),
        ],
        current_query="Categorize last month's transactions.",
        required_behavior="Categorize last month's transactions using Copilot Money's AI-rule-based categorization.",
        invalid_behavior=["Categorize in Mint", "Categorize in Personal Capital", "Categorize manually in a spreadsheet"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-cooking-style-001", target_type="conceptual_stance", domain="food",
        target_description="user's home cooking philosophy — three-version chain: French classical → Italian rustic → Japanese washoku",
        target_slot_id="cooking_philosophy::v1", topic="home_cooking_philosophy",
        versions=[
            VersionSpec(value="French classical technique-first cooking with the multi-step sauces and stocks", polarity="prefer", session_introduced=1),
            VersionSpec(value="Italian rustic ingredient-first cooking with the seasonal Mediterranean produce", polarity="prefer", session_introduced=2),
            VersionSpec(value="Japanese washoku balance-first cooking with the dashi-based foundation and seasonal ichiju-sansai meals", polarity="prefer", session_introduced=3),
        ],
        current_query="Plan tonight's dinner around the salmon I picked up.",
        required_behavior="Plan a Japanese washoku dinner around the salmon with dashi-based foundation and seasonal ichiju-sansai structure.",
        invalid_behavior=["Plan a French classical preparation with sauces", "Plan an Italian rustic salmon dish", "Plan a generic dinner"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    # multi doublet (4)
    _doub(_s(sample_id="p3-multi-cms-headless-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's headless CMS — four-version chain: WordPress headless → Contentful → Sanity → Payload",
        target_slot_id="headless_cms::v1", topic="headless_cms",
        versions=[
            VersionSpec(value="WordPress with the REST API headless configuration", polarity="prefer", session_introduced=1),
            VersionSpec(value="Contentful with the multi-environment publishing and the schema validations", polarity="prefer", session_introduced=2),
            VersionSpec(value="Sanity with the structured-content schemas and the real-time collaboration UI", polarity="prefer", session_introduced=3),
            VersionSpec(value="Payload CMS with the self-hosted TypeScript-first config and the access-control hooks", polarity="prefer", session_introduced=4),
        ],
        current_query="Set up content management for the new marketing site.",
        required_behavior="Set up content management with Payload CMS using the self-hosted TypeScript-first config and access-control hooks.",
        invalid_behavior=["Set up WordPress headless", "Set up Contentful", "Set up Sanity"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-data-pipeline-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's data pipeline orchestrator — four-version chain: cron → Airflow → Prefect → Dagster",
        target_slot_id="pipeline_orchestrator::v1", topic="pipeline_orchestrator",
        versions=[
            VersionSpec(value="bare cron with shell-script invocations on the legacy ETL host", polarity="prefer", session_introduced=1),
            VersionSpec(value="Apache Airflow with the legacy DAG operators and the Postgres metadata DB", polarity="prefer", session_introduced=2),
            VersionSpec(value="Prefect with the dataflow-style task definitions and Cloud orchestration", polarity="prefer", session_introduced=3),
            VersionSpec(value="Dagster with the asset-based pipeline modeling and the software-defined data assets", polarity="prefer", session_introduced=4),
        ],
        current_query="Build the new daily-ranking-model retraining pipeline.",
        required_behavior="Build the daily ranking-model retraining pipeline in Dagster using asset-based pipeline modeling and software-defined data assets.",
        invalid_behavior=["Build with bare cron", "Build with Apache Airflow", "Build with Prefect"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-form-survey-4v-001", target_type="object_preference", domain="business",
        target_description="user's customer-research survey vendor — four-version chain: SurveyMonkey → Qualtrics → Maze → Sprig",
        target_slot_id="research_survey::v1", topic="customer_research_survey",
        versions=[
            VersionSpec(value="SurveyMonkey with the legacy basic survey templates and CSV export", polarity="prefer", session_introduced=1),
            VersionSpec(value="Qualtrics with the advanced branching logic and statistical analysis", polarity="prefer", session_introduced=2),
            VersionSpec(value="Maze with the prototype-testing and unmoderated user-research modules", polarity="prefer", session_introduced=3),
            VersionSpec(value="Sprig with the in-product micro-survey targeting and the AI insight extraction", polarity="prefer", session_introduced=4),
        ],
        current_query="Run a study on the new checkout-flow drop-off.",
        required_behavior="Run the checkout-flow drop-off study through Sprig using in-product micro-survey targeting and AI insight extraction.",
        invalid_behavior=["Run through SurveyMonkey", "Run through Qualtrics", "Run through Maze"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-mobile-build-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's mobile-app build pipeline — four-version chain: Xcode + Gradle → Fastlane → Bitrise → EAS",
        target_slot_id="mobile_build::v1", topic="mobile_build_pipeline",
        versions=[
            VersionSpec(value="Xcode + Gradle direct invocation from the developer's laptop with manual signing", polarity="prefer", session_introduced=1),
            VersionSpec(value="Fastlane with the Match-managed certificates and the automated lane scripts", polarity="prefer", session_introduced=2),
            VersionSpec(value="Bitrise with the visual-workflow editor and the 200+ pre-built integrations", polarity="prefer", session_introduced=3),
            VersionSpec(value="Expo Application Services (EAS) with the cloud build server and the over-the-air updates", polarity="prefer", session_introduced=4),
        ],
        current_query="Cut the next release build of the iOS app.",
        required_behavior="Cut the next iOS release build through EAS using the cloud build server and over-the-air updates.",
        invalid_behavior=["Cut via direct Xcode invocation", "Cut via Fastlane", "Cut via Bitrise"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    # explicit (4)
    _trip(_s(sample_id="p3-explicit-data-modeling-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's data-modeling tool — explicit replacement of dbt with SQLMesh",
        target_slot_id="data_modeling::v1", topic="data_modeling_tool",
        versions=[
            VersionSpec(value="dbt with the legacy YAML-based macro system and the test-builder ecosystem", polarity="prefer", session_introduced=1),
            VersionSpec(value="SQLMesh with the python-DSL transformation graph and the time-aware versioning", polarity="prefer", session_introduced=2),
        ],
        current_query="Build the new revenue-attribution data model.",
        required_behavior="Build the revenue-attribution data model in SQLMesh using the python-DSL transformation graph.",
        invalid_behavior=["Build in dbt", "Build with raw SQL files", "Skip the modeling layer"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-prototype-tool-001", target_type="object_preference", domain="creative",
        target_description="user's interactive prototyping — explicit replacement of InVision with ProtoPie",
        target_slot_id="prototyping::v1", topic="interactive_prototyping",
        versions=[
            VersionSpec(value="InVision with the legacy clickable hotspot prototypes", polarity="prefer", session_introduced=1),
            VersionSpec(value="ProtoPie with the interaction-physics support and the device-sensor inputs", polarity="prefer", session_introduced=2),
        ],
        current_query="Prototype the new haptic-feedback gesture for the mobile dashboard.",
        required_behavior="Prototype the haptic-feedback gesture in ProtoPie using the interaction-physics support and device-sensor inputs.",
        invalid_behavior=["Prototype in InVision", "Prototype in plain Figma", "Skip the prototype"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-virtual-machine-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's local development VM — explicit replacement of VMware Fusion with UTM",
        target_slot_id="local_vm::v1", topic="local_development_vm",
        versions=[
            VersionSpec(value="VMware Fusion with the legacy paid Pro license and the unified-mode integration", polarity="prefer", session_introduced=1),
            VersionSpec(value="UTM with the QEMU-based open-source virtualization and the Apple Silicon native support", polarity="prefer", session_introduced=2),
        ],
        current_query="Spin up a Linux VM to test the new database driver.",
        required_behavior="Spin up the Linux VM in UTM using the QEMU-based open-source virtualization with Apple Silicon native support.",
        invalid_behavior=["Spin up in VMware Fusion", "Spin up in VirtualBox", "Skip the VM and test on the host"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-pdf-tool-001", target_type="object_preference", domain="lifestyle",
        target_description="user's PDF annotation tool — explicit replacement of GoodNotes with PDF Expert",
        target_slot_id="pdf_annotation::v1", topic="pdf_annotation_tool",
        versions=[
            VersionSpec(value="GoodNotes with the iCloud-synced library and the handwritten-note conversion", polarity="prefer", session_introduced=1),
            VersionSpec(value="PDF Expert with the OCR-searchable text and the Mac/iPad continuity-handoff", polarity="prefer", session_introduced=2),
        ],
        current_query="Mark up the contract for the lawyer to review.",
        required_behavior="Mark up the contract in PDF Expert using the OCR-searchable text and Mac/iPad continuity-handoff.",
        invalid_behavior=["Mark up in GoodNotes", "Mark up in Apple Preview", "Skip the markup"],
        failure_patterns=["explicit_replacement"])),

    # repeated_use (4)
    _drift(_s(sample_id="p3-drift-stand-up-001", target_type="procedural_constraint", domain="management",
        target_description="user's morning routine pre-standup — drifted to a 5-minute calendar review from the email triage, repeated active use",
        target_slot_id="morning_pre_standup::v1", topic="morning_pre_standup",
        versions=[
            VersionSpec(value="email triage starting at 8:30am, clear inbox before the standup", polarity="constraint", session_introduced=1),
            VersionSpec(value="5-minute calendar review at 8:55am right before the 9am standup", polarity="constraint", session_introduced=2),
        ],
        current_query="What's my last task before standup tomorrow?",
        required_behavior="The last task before standup is a 5-minute calendar review at 8:55am.",
        invalid_behavior=["Email triage starting at 8:30am", "Skip pre-standup tasks", "Both email and calendar"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-doc-color-001", target_type="object_preference", domain="creative",
        target_description="user's slide-deck accent color — drifted to ochre from cobalt, repeated active use",
        target_slot_id="slide_color::v1", topic="slide_deck_accent_color",
        versions=[
            VersionSpec(value="cobalt-blue (hex 0047AB) accent color across all slides", polarity="prefer", session_introduced=1),
            VersionSpec(value="ochre-yellow (hex CC7722) accent color across all slides", polarity="prefer", session_introduced=2),
        ],
        current_query="Style the new product launch deck.",
        required_behavior="Style the product launch deck with the ochre-yellow (hex CC7722) accent color.",
        invalid_behavior=["Style with cobalt-blue accent", "Style with red accent", "Skip the styling"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-research-paper-source-001", target_type="object_preference", domain="learning",
        target_description="user's primary research paper venue — drifted to OpenReview from arXiv preprints, repeated active use",
        target_slot_id="paper_venue::v1", topic="paper_venue_source",
        versions=[
            VersionSpec(value="arXiv preprints with the daily cs.LG mailing-list digest", polarity="prefer", session_introduced=1),
            VersionSpec(value="OpenReview with the venue-specific tracks (ICLR, NeurIPS, ICML) and the discussion threads", polarity="prefer", session_introduced=2),
        ],
        current_query="Find papers on retrieval-augmented generation for tonight's reading.",
        required_behavior="Find papers on retrieval-augmented generation through OpenReview using the venue-specific tracks.",
        invalid_behavior=["Find on arXiv", "Find through Google Scholar", "Find through Semantic Scholar"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-deploy-comm-001", target_type="conceptual_stance", domain="work_communication",
        target_description="user's deploy-announcement style — drifted to a Loom video from a written #deploys post, repeated active use",
        target_slot_id="deploy_announce::v1", topic="deploy_announcement_style",
        versions=[
            VersionSpec(value="written #deploys-channel post with version, changelog, and rollback instructions", polarity="prefer", session_introduced=1),
            VersionSpec(value="2-minute Loom video walkthrough showing the change in production", polarity="prefer", session_introduced=2),
        ],
        current_query="Just deployed the auth-token rotation fix — announce it to the team.",
        required_behavior="Announce the auth-token rotation deploy with a 2-minute Loom video walkthrough showing the change in production.",
        invalid_behavior=["Announce in a written #deploys post", "Send a brief Slack DM", "Skip the announcement"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    # abandonment (3)
    _drift(_s(sample_id="p3-drift-mailing-list-001", target_type="procedural_constraint", domain="business",
        target_description="user's customer-update channel — abandoned the email newsletter; in-app changelog feed only now",
        target_slot_id="customer_update::v1", topic="customer_update_channel",
        versions=[
            VersionSpec(value="monthly email newsletter to the legacy subscriber list with the product highlights", polarity="constraint", session_introduced=1),
            VersionSpec(value="in-app changelog feed updated continuously with the recent-improvements panel", polarity="constraint", session_introduced=2),
        ],
        current_query="Announce the new beta features to existing customers.",
        required_behavior="Announce the new beta features through the in-app changelog feed updated with the recent-improvements panel.",
        invalid_behavior=["Send a monthly email newsletter", "Send a one-time email blast", "Skip the announcement"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-saas-tool-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's deploy preview environment — abandoned the staging-cluster shared instance; per-PR ephemeral previews only now",
        target_slot_id="deploy_preview::v1", topic="deploy_preview",
        versions=[
            VersionSpec(value="single shared staging cluster with the manual rebuild trigger", polarity="constraint", session_introduced=1),
            VersionSpec(value="per-pull-request ephemeral preview environment auto-spun by the CI pipeline", polarity="constraint", session_introduced=2),
        ],
        current_query="Marcus opened a PR for the new search ranker — set up the preview env.",
        required_behavior="Set up Marcus's PR preview as a per-pull-request ephemeral environment auto-spun by the CI pipeline.",
        invalid_behavior=["Use the shared staging cluster with manual rebuild", "Skip the preview", "Spin up a permanent cluster"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-old-event-format-001", target_type="conceptual_stance", domain="work_communication",
        target_description="user's all-hands format — abandoned the formal scripted Q&A; lightning-talk + open mic only now",
        target_slot_id="all_hands::v1", topic="all_hands_format",
        versions=[
            VersionSpec(value="formal scripted Q&A all-hands with pre-vetted questions and prepared answers", polarity="prefer", session_introduced=1),
            VersionSpec(value="lightning-talk plus open-mic all-hands with 5-minute team-led talks and unfiltered audience questions", polarity="prefer", session_introduced=2),
        ],
        current_query="Plan next month's all-hands.",
        required_behavior="Plan next month's all-hands as a lightning-talk plus open-mic format with 5-minute team-led talks and unfiltered audience questions.",
        invalid_behavior=["Plan a formal scripted Q&A", "Plan a hybrid scripted + Q&A", "Skip the all-hands"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    # gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-narrow-tools-001", target_type="conceptual_stance", domain="tech_workflow",
        target_description="user's daily-driver development environment — gradually narrowed from any IDE to a Neovim-only setup via cumulative preference signals",
        target_slot_id="daily_driver_dev::v1", topic="daily_dev_env",
        versions=[
            VersionSpec(value="any modern IDE — VSCode, IntelliJ, JetBrains Suite — depending on what fits the project", polarity="prefer", session_introduced=1),
            VersionSpec(value="Neovim-only setup with the Lua-based config and the lazy.nvim plugin manager", polarity="prefer", session_introduced=2),
        ],
        current_query="Open the new fraud-detection codebase locally.",
        required_behavior="Open the fraud-detection codebase in the Neovim setup with the Lua-based config and lazy.nvim plugin manager.",
        invalid_behavior=["Open in VSCode", "Open in IntelliJ", "Open in any other modern IDE"],
        failure_patterns=["implicit_drift"]), "gradual_narrowing"),
]
