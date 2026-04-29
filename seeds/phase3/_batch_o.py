"""Phase 3 batch O — 25 spines."""

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


PHASE3_BATCH_O: list[Phase3GroupSpec] = [
    # narrow (5)
    _trip(_s(sample_id="p3-narrow-pull-meeting-cancel-001", target_type="procedural_constraint", domain="management",
        target_description="user's meeting-cancellation rule — three explicit narrowings: any reason → conflict only → conflict + 24-hour notice",
        target_slot_id="meeting_cancel::v1", topic="meeting_cancellation_rule",
        versions=[
            VersionSpec(value="cancel meetings whenever the user feels overbooked", polarity="constraint", session_introduced=1),
            VersionSpec(value="cancel meetings only when there is a genuine schedule conflict", polarity="constraint", session_introduced=2),
            VersionSpec(value="cancel meetings only on a genuine conflict AND with at least 24 hours notice to other participants", polarity="constraint", session_introduced=3),
        ],
        current_query="A board prep meeting tomorrow afternoon collides with a urgent customer call — cancel the board prep?",
        required_behavior="Cancel the board prep only if there's a true conflict AND notify participants at least 24 hours ahead.",
        invalid_behavior=["Cancel because of feeling overbooked", "Cancel without 24-hour notice", "Cancel anything overbooked"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-vendor-pull-001", target_type="procedural_constraint", domain="business",
        target_description="user's vendor-renewal evaluation rule — three explicit narrowings: any → annual review → annual + cost-benefit + alternative-quote",
        target_slot_id="vendor_renewal_eval::v1", topic="vendor_renewal_eval",
        versions=[
            VersionSpec(value="renew vendor contracts as they come up with the existing terms", polarity="constraint", session_introduced=1),
            VersionSpec(value="annual evaluation with cost-benefit analysis attached to renewal request", polarity="constraint", session_introduced=2),
            VersionSpec(value="annual evaluation with cost-benefit analysis AND at least one alternative-vendor quote on file", polarity="constraint", session_introduced=3),
        ],
        current_query="Datadog wants to renew the contract — approve?",
        required_behavior="Approve only if cost-benefit analysis is attached AND at least one alternative-vendor quote is on file.",
        invalid_behavior=["Approve at existing terms", "Approve on cost-benefit alone", "Approve on quote alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-customer-success-pull-001", target_type="procedural_constraint", domain="business",
        target_description="user's customer-success escalation rule — three explicit narrowings: any reach-out → low-NPS only → low-NPS + churn-risk-flag",
        target_slot_id="cs_escalation::v1", topic="cs_escalation_rule",
        versions=[
            VersionSpec(value="reach out to any customer who has a question or complaint", polarity="constraint", session_introduced=1),
            VersionSpec(value="reach out only to customers with low NPS scores below 5", polarity="constraint", session_introduced=2),
            VersionSpec(value="reach out only to low-NPS customers (below 5) who also have a churn-risk flag", polarity="constraint", session_introduced=3),
        ],
        current_query="A customer with NPS 3 just left a complaint in the support inbox — should I reach out?",
        required_behavior="Reach out only if the customer is also flagged as a churn risk.",
        invalid_behavior=["Reach out on the complaint", "Reach out on low NPS alone", "Reach out on churn risk alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-language-tutor-001", target_type="procedural_constraint", domain="learning",
        target_description="user's language-learning instructor criteria — three explicit narrowings: any teacher → native speaker → native speaker + pedagogical certification",
        target_slot_id="language_tutor::v1", topic="language_tutor_criteria",
        versions=[
            VersionSpec(value="hire any language teacher available on the marketplace", polarity="constraint", session_introduced=1),
            VersionSpec(value="hire only native-speaker language teachers", polarity="constraint", session_introduced=2),
            VersionSpec(value="hire only native-speaker language teachers with a recognized pedagogical certification", polarity="constraint", session_introduced=3),
        ],
        current_query="My current Spanish tutor is moving on — find a replacement.",
        required_behavior="Find a replacement Spanish tutor who is a native speaker AND has a recognized pedagogical certification.",
        invalid_behavior=["Find any available Spanish tutor", "Find a native speaker without certification", "Find a certified non-native speaker"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-engineering-team-pull-001", target_type="procedural_constraint", domain="management",
        target_description="user's team weekly-cadence rule — three explicit narrowings: any check-in → midweek → midweek + topic-tied",
        target_slot_id="team_weekly::v1", topic="team_weekly_cadence",
        versions=[
            VersionSpec(value="hold team check-ins whenever the calendar shows a free slot", polarity="constraint", session_introduced=1),
            VersionSpec(value="hold team check-ins only on midweek (Wednesday) afternoons", polarity="constraint", session_introduced=2),
            VersionSpec(value="hold team check-ins only on midweek Wednesday afternoons AND only when tied to a specific decision-needed topic", polarity="constraint", session_introduced=3),
        ],
        current_query="The team has been complaining about visibility — schedule a check-in this week?",
        required_behavior="Schedule the check-in only on Wednesday afternoon AND only if a specific decision-needed topic frames the agenda.",
        invalid_behavior=["Schedule any time the calendar shows", "Schedule Wednesday without a specific topic", "Schedule a generic visibility check-in"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi triple (4)
    _trip(_s(sample_id="p3-multi-package-mgr-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's Python package manager — three-version chain: pip → poetry → uv",
        target_slot_id="python_pkg_mgr::v1", topic="python_package_manager",
        versions=[
            VersionSpec(value="pip with the legacy requirements.txt and the manual virtualenv activation", polarity="prefer", session_introduced=1),
            VersionSpec(value="poetry with the pyproject.toml-based dependency declarations and the lock file", polarity="prefer", session_introduced=2),
            VersionSpec(value="uv (Astral) with the Rust-based fast resolver and the unified workflow command", polarity="prefer", session_introduced=3),
        ],
        current_query="Set up the Python environment for the new microservice.",
        required_behavior="Set up the Python environment with uv (Astral) using the Rust-based fast resolver.",
        invalid_behavior=["Set up with pip and requirements.txt", "Set up with poetry", "Set up with conda"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-frontend-fw-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's frontend framework — three-version chain: Backbone → React → Solid",
        target_slot_id="frontend_fw::v1", topic="frontend_framework",
        versions=[
            VersionSpec(value="Backbone.js with the legacy underscore.js helpers and Marionette views", polarity="prefer", session_introduced=1),
            VersionSpec(value="React with the standard hooks and the create-react-app starter", polarity="prefer", session_introduced=2),
            VersionSpec(value="SolidJS with the fine-grained reactivity and the JSX-without-VDOM rendering", polarity="prefer", session_introduced=3),
        ],
        current_query="Build the new admin dashboard frontend.",
        required_behavior="Build the admin dashboard frontend with SolidJS using fine-grained reactivity.",
        invalid_behavior=["Build with Backbone.js", "Build with React", "Build with Vue"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-marathon-prep-001", target_type="procedural_constraint", domain="fitness",
        target_description="user's marathon training plan source — three-version chain: Hal Higdon plans → Hanson method → Pfitzinger 18/55",
        target_slot_id="marathon_plan::v1", topic="marathon_training_plan",
        versions=[
            VersionSpec(value="Hal Higdon novice marathon plans with the standard 18-week structure", polarity="constraint", session_introduced=1),
            VersionSpec(value="Hanson method with the cumulative-fatigue training principle and the 16-week build", polarity="constraint", session_introduced=2),
            VersionSpec(value="Pfitzinger 18/55 plan with the lactate-threshold focus and the 18-week peak weeks at 55 miles", polarity="constraint", session_introduced=3),
        ],
        current_query="Block the next 18 weeks for marathon training.",
        required_behavior="Block the next 18 weeks for the Pfitzinger 18/55 plan with lactate-threshold focus and 55-mile peak weeks.",
        invalid_behavior=["Block for Hal Higdon novice plan", "Block for Hanson method", "Skip the structured plan"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _trip(_s(sample_id="p3-multi-task-management-001", target_type="object_preference", domain="management",
        target_description="user's project-management methodology — three-version chain: waterfall → scrum → shape-up",
        target_slot_id="pm_methodology::v1", topic="project_management_methodology",
        versions=[
            VersionSpec(value="waterfall planning with the upfront detailed Gantt chart and the milestone gates", polarity="prefer", session_introduced=1),
            VersionSpec(value="scrum sprints with the 2-week iterations, daily standups, and sprint retrospectives", polarity="prefer", session_introduced=2),
            VersionSpec(value="shape-up with the 6-week appetite cycles, the betting table, and the cool-down weeks", polarity="prefer", session_introduced=3),
        ],
        current_query="Plan the next development cycle for the new fraud-rules engine.",
        required_behavior="Plan the next cycle with shape-up using 6-week appetite cycles, the betting table, and cool-down weeks.",
        invalid_behavior=["Plan with waterfall and Gantt chart", "Plan with scrum sprints", "Plan ad-hoc without methodology"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    # multi doublet (4)
    _doub(_s(sample_id="p3-multi-storage-tier-4v-001", target_type="object_preference", domain="tech_workflow",
        target_description="team's object storage tier — four-version chain: S3 standard → S3 IA → S3 Glacier → R2",
        target_slot_id="object_storage::v1", topic="object_storage_tier",
        versions=[
            VersionSpec(value="AWS S3 Standard with the legacy bucket-policy IAM configuration", polarity="prefer", session_introduced=1),
            VersionSpec(value="AWS S3 Infrequent Access with the lifecycle-rule auto-tiering", polarity="prefer", session_introduced=2),
            VersionSpec(value="AWS S3 Glacier Deep Archive with the bulk-restore option and the long-term retention policy", polarity="prefer", session_introduced=3),
            VersionSpec(value="Cloudflare R2 with the zero-egress pricing and the S3-compatible API", polarity="prefer", session_introduced=4),
        ],
        current_query="Wire the new media-asset uploads from the marketing CMS.",
        required_behavior="Wire the media-asset uploads to Cloudflare R2 using zero-egress pricing and S3-compatible API.",
        invalid_behavior=["Wire to AWS S3 Standard", "Wire to AWS S3 IA", "Wire to AWS S3 Glacier"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-fraud-tool-4v-001", target_type="object_preference", domain="business",
        target_description="team's fraud-detection vendor — four-version chain: home-grown rules → Sift → Castle → Forter",
        target_slot_id="fraud_detection::v1", topic="fraud_detection_vendor",
        versions=[
            VersionSpec(value="home-grown rules engine with the legacy SQL-based detection rules", polarity="prefer", session_introduced=1),
            VersionSpec(value="Sift with the machine-learning behavior scoring and the API-driven decisions", polarity="prefer", session_introduced=2),
            VersionSpec(value="Castle with the device-fingerprint risk model and the no-touch user-friction policies", polarity="prefer", session_introduced=3),
            VersionSpec(value="Forter with the identity-based decisioning and the chargeback-guarantee SLA", polarity="prefer", session_introduced=4),
        ],
        current_query="Wire the new credit-card-checkout fraud check.",
        required_behavior="Wire the credit-card-checkout fraud check through Forter using identity-based decisioning and the chargeback-guarantee SLA.",
        invalid_behavior=["Wire to the home-grown SQL rules", "Wire to Sift", "Wire to Castle"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-storage-personal-4v-001", target_type="object_preference", domain="lifestyle",
        target_description="user's personal cloud-photo backup — four-version chain: Dropbox → Google Photos → Apple Photos → SmugMug",
        target_slot_id="photo_backup::v1", topic="personal_photo_backup",
        versions=[
            VersionSpec(value="Dropbox with the legacy Camera Uploads automatic feature", polarity="prefer", session_introduced=1),
            VersionSpec(value="Google Photos with the unlimited high-quality storage and the AI-driven Memories", polarity="prefer", session_introduced=2),
            VersionSpec(value="Apple Photos with the iCloud Photo Library and the People-and-Places search", polarity="prefer", session_introduced=3),
            VersionSpec(value="SmugMug with the unlimited original-quality storage and the photographer-friendly portfolio site", polarity="prefer", session_introduced=4),
        ],
        current_query="Back up this weekend's photo shoot.",
        required_behavior="Back up the photo shoot to SmugMug using unlimited original-quality storage and the portfolio site.",
        invalid_behavior=["Back up to Dropbox Camera Uploads", "Back up to Google Photos", "Back up to Apple iCloud Photo Library"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    _doub(_s(sample_id="p3-multi-meeting-recording-4v-001", target_type="object_preference", domain="work_workflow",
        target_description="team's meeting-recording platform — four-version chain: Zoom Cloud → Otter → Fathom → tl;dv",
        target_slot_id="meeting_record::v1", topic="meeting_recording",
        versions=[
            VersionSpec(value="Zoom Cloud Recording with the legacy paid-tier 90-day retention", polarity="prefer", session_introduced=1),
            VersionSpec(value="Otter.ai with the auto-transcription and speaker diarization", polarity="prefer", session_introduced=2),
            VersionSpec(value="Fathom with the AI-summary action items and the CRM auto-sync", polarity="prefer", session_introduced=3),
            VersionSpec(value="tl;dv with the searchable highlight reels and the multi-platform recording capture", polarity="prefer", session_introduced=4),
        ],
        current_query="Record tomorrow's customer-onboarding call for review.",
        required_behavior="Record the customer-onboarding call through tl;dv using searchable highlight reels and multi-platform recording capture.",
        invalid_behavior=["Record through Zoom Cloud", "Record through Otter", "Record through Fathom"],
        failure_patterns=["multi_version"], subtype="multi_step")),

    # explicit (4)
    _trip(_s(sample_id="p3-explicit-cli-shell-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's interactive shell — explicit replacement of zsh with fish",
        target_slot_id="shell::v1", topic="interactive_shell",
        versions=[
            VersionSpec(value="zsh with the oh-my-zsh framework and powerlevel10k prompt theme", polarity="prefer", session_introduced=1),
            VersionSpec(value="fish with the autosuggestions feature and the tide prompt theme", polarity="prefer", session_introduced=2),
        ],
        current_query="Open a terminal session to debug the local environment.",
        required_behavior="Open the terminal session in fish using the autosuggestions feature and tide prompt theme.",
        invalid_behavior=["Open in zsh with oh-my-zsh", "Open in bash", "Open in PowerShell"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-survey-tool-001", target_type="object_preference", domain="management",
        target_description="user's team-engagement survey tool — explicit replacement of TINYpulse with Lattice Engagement",
        target_slot_id="engagement_tool::v1", topic="engagement_survey_tool",
        versions=[
            VersionSpec(value="TINYpulse with the weekly anonymous one-question pulse", polarity="prefer", session_introduced=1),
            VersionSpec(value="Lattice Engagement with the quarterly deep-dive surveys and the manager dashboards", polarity="prefer", session_introduced=2),
        ],
        current_query="Run this quarter's team-engagement check.",
        required_behavior="Run the team-engagement check through Lattice Engagement using the quarterly deep-dive surveys and manager dashboards.",
        invalid_behavior=["Run through TINYpulse", "Run an ad-hoc Google Forms survey", "Skip the check"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-image-host-001", target_type="object_preference", domain="creative",
        target_description="user's photo-hosting platform for the personal site — explicit replacement of Flickr with Glass",
        target_slot_id="photo_host::v1", topic="personal_photo_host",
        versions=[
            VersionSpec(value="Flickr with the legacy 1TB free-tier and the Pro paid-album upgrade", polarity="prefer", session_introduced=1),
            VersionSpec(value="Glass with the photographer-only invite community and the no-algorithm chronological feed", polarity="prefer", session_introduced=2),
        ],
        current_query="Post the new photo essay from the trip.",
        required_behavior="Post the photo essay on Glass using the photographer-only invite community and chronological feed.",
        invalid_behavior=["Post on Flickr", "Post on Instagram", "Post on a personal blog only"],
        failure_patterns=["explicit_replacement"])),

    _trip(_s(sample_id="p3-explicit-pdf-sign-001", target_type="object_preference", domain="business",
        target_description="user's e-signature service — explicit replacement of DocuSign with Documenso",
        target_slot_id="esign::v1", topic="esignature_service",
        versions=[
            VersionSpec(value="DocuSign with the legacy enterprise contract template library", polarity="prefer", session_introduced=1),
            VersionSpec(value="Documenso with the open-source self-hosted instance and the audit trail receipts", polarity="prefer", session_introduced=2),
        ],
        current_query="Send the new partnership agreement out for signing.",
        required_behavior="Send the partnership agreement through Documenso using the open-source self-hosted instance and audit trail receipts.",
        invalid_behavior=["Send through DocuSign", "Send through Adobe Sign", "Send a printed copy via mail"],
        failure_patterns=["explicit_replacement"])),

    # repeated_use (4)
    _drift(_s(sample_id="p3-drift-running-shoe-2-001", target_type="object_preference", domain="fitness",
        target_description="user's recovery-day shoe — drifted to Hoka Bondi from On Cloudflyer, repeated active use",
        target_slot_id="recovery_shoe::v1", topic="recovery_running_shoe",
        versions=[
            VersionSpec(value="On Cloudflyer with the moderate-cushion CloudTec midsole", polarity="prefer", session_introduced=1),
            VersionSpec(value="Hoka Bondi with the maximum-cushion meta-rocker geometry", polarity="prefer", session_introduced=2),
        ],
        current_query="Tomorrow is a 6-mile recovery run — pick the shoe.",
        required_behavior="Pick the Hoka Bondi with maximum-cushion meta-rocker for tomorrow's recovery run.",
        invalid_behavior=["Pick the On Cloudflyer", "Pick a daily-trainer shoe", "Pick a racing flat"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-team-mtg-format-001", target_type="conceptual_stance", domain="management",
        target_description="user's senior-leader 1:1 style — drifted to a 30-minute walking 1:1 from a desk-side sit-down, repeated active use",
        target_slot_id="senior_leader_meeting::v1", topic="senior_leader_meeting_style",
        versions=[
            VersionSpec(value="60-minute desk-side sit-down 1:1 in the user's office every Tuesday", polarity="prefer", session_introduced=1),
            VersionSpec(value="30-minute walking 1:1 around the building's outdoor loop every Tuesday morning", polarity="prefer", session_introduced=2),
        ],
        current_query="Block this Tuesday's senior-leader 1:1.",
        required_behavior="Block this Tuesday morning's senior-leader 1:1 as a 30-minute walking session around the outdoor loop.",
        invalid_behavior=["Block a 60-minute desk-side sit-down", "Block a Zoom call", "Skip the 1:1"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-paper-tracking-001", target_type="object_preference", domain="learning",
        target_description="user's read-paper log — drifted to a Notion paper-database from a private GitHub repo of markdown notes, repeated active use",
        target_slot_id="paper_log::v1", topic="paper_log_tool",
        versions=[
            VersionSpec(value="private GitHub repository of markdown notes one-per-paper with cross-linking", polarity="prefer", session_introduced=1),
            VersionSpec(value="Notion paper-database with the structured fields, taggable filters, and graph view", polarity="prefer", session_introduced=2),
        ],
        current_query="Log the survey paper I just finished.",
        required_behavior="Log the survey paper in the Notion paper-database with the structured fields and taggable filters.",
        invalid_behavior=["Log in the private GitHub repo of markdown notes", "Log in a personal text file", "Skip logging"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    _drift(_s(sample_id="p3-drift-news-source-001", target_type="object_preference", domain="leisure",
        target_description="user's morning-news source — drifted to The Information daily-digest from the WSJ Print edition, repeated active use",
        target_slot_id="morning_news::v1", topic="morning_news_source",
        versions=[
            VersionSpec(value="Wall Street Journal print-edition delivery with the morning paper at the door", polarity="prefer", session_introduced=1),
            VersionSpec(value="The Information daily-digest email subscription delivered to inbox at 6am", polarity="prefer", session_introduced=2),
        ],
        current_query="What's the first thing I read with my morning coffee?",
        required_behavior="The first morning read is The Information daily-digest email delivered at 6am.",
        invalid_behavior=["Read the Wall Street Journal print edition", "Read a different paper", "Skip the morning read"],
        failure_patterns=["implicit_drift"]), "repeated_use"),

    # abandonment (3)
    _drift(_s(sample_id="p3-drift-old-tool-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's local environment management — abandoned the docker-compose-only setup; nix flakes only now",
        target_slot_id="local_env::v1", topic="local_dev_env_management",
        versions=[
            VersionSpec(value="docker-compose with the legacy multi-service definitions and bind-mounts", polarity="prefer", session_introduced=1),
            VersionSpec(value="nix flakes with the reproducible-by-hash dependency tree and direnv integration", polarity="prefer", session_introduced=2),
        ],
        current_query="Stand up a development environment for the new microservice on my laptop.",
        required_behavior="Stand up the development environment with nix flakes using the reproducible-by-hash dependency tree and direnv integration.",
        invalid_behavior=["Stand up with docker-compose", "Stand up with virtualenv-only", "Stand up with bare bash exports"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-board-meeting-format-001", target_type="procedural_constraint", domain="management",
        target_description="user's investor-update format — abandoned the quarterly all-investor video call; written-only memo + AMA Slack thread now",
        target_slot_id="investor_update::v1", topic="investor_update_format",
        versions=[
            VersionSpec(value="quarterly all-investor video call with the live presentation and Q&A", polarity="constraint", session_introduced=1),
            VersionSpec(value="written-only quarterly memo plus a 24-hour AMA Slack thread for follow-up questions", polarity="constraint", session_introduced=2),
        ],
        current_query="Q1 wraps next week — set up the investor update.",
        required_behavior="Set up the Q1 investor update as a written-only memo plus a 24-hour AMA Slack thread.",
        invalid_behavior=["Schedule a quarterly all-investor video call", "Send only a memo without the AMA thread", "Skip the update"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    _drift(_s(sample_id="p3-drift-snapchat-comm-001", target_type="object_preference", domain="lifestyle",
        target_description="user's family-photo-sharing channel — abandoned the family WhatsApp group; Apple Photos shared album only now",
        target_slot_id="family_photos::v1", topic="family_photo_sharing",
        versions=[
            VersionSpec(value="family WhatsApp group with the daily photos and short messages", polarity="prefer", session_introduced=1),
            VersionSpec(value="Apple Photos shared album with the synced thumbnails and per-album notifications", polarity="prefer", session_introduced=2),
        ],
        current_query="Share the photos from this weekend's family dinner.",
        required_behavior="Share the family-dinner photos via the Apple Photos shared album using synced thumbnails and per-album notifications.",
        invalid_behavior=["Share via the family WhatsApp group", "Share via email", "Share via SMS individually"],
        failure_patterns=["implicit_drift"]), "abandonment"),

    # gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-coding-narrow-001", target_type="conceptual_stance", domain="tech_workflow",
        target_description="user's side-project tech-stack focus — gradually narrowed from any language to Rust-only via cumulative preference signals",
        target_slot_id="side_project_lang::v1", topic="side_project_language",
        versions=[
            VersionSpec(value="any language that fits the side project — Python, Go, TypeScript, Rust, Elixir", polarity="prefer", session_introduced=1),
            VersionSpec(value="Rust-only side projects with the standard cargo workflow and the tokio async runtime", polarity="prefer", session_introduced=2),
        ],
        current_query="I want to spin up a small CLI side project this weekend — what language?",
        required_behavior="Spin up the CLI side project in Rust with the standard cargo workflow and tokio async runtime.",
        invalid_behavior=["Spin up in Python", "Spin up in Go", "Spin up in TypeScript"],
        failure_patterns=["implicit_drift"]), "gradual_narrowing"),
]
