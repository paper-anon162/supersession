"""Phase 3 batch G — 20 spines biased to work_tooling /
communication_boundary / learning_routine to fix the
daily_preference 52-58% cell breaches that batches d/e/f introduced.

Topic distribution target:
  work_tooling           7
  communication_boundary 7
  learning_routine       5
  daily_preference       1   (deliberately small)

Pattern distribution target:
  6 repeated_use, 4 narrow, 3 multi triple, 2 multi doublet,
  2 explicit, 2 abandonment, 1 gradual_narrowing
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


PHASE3_BATCH_G: list[Phase3GroupSpec] = [

    # repeated_use (6) — work / comm / learning skewed
    _drift(_s(
        sample_id="p3-drift-status-channel-001",
        target_type="procedural_constraint", domain="work_communication",
        target_description="user's where-to-post-engineering-status — drifted to a private team channel from the public org-wide one, repeated active use",
        target_slot_id="status_channel::v1", topic="engineering_status_channel",
        versions=[
            VersionSpec(value="public org-wide #engineering-status Slack channel for everyone to follow", polarity="constraint", session_introduced=1),
            VersionSpec(value="private team-only #fraud-status channel that the leads pinned to the channel sidebar", polarity="constraint", session_introduced=2),
        ],
        current_query="Post the latest fraud-pipeline release notes for the team to see.",
        required_behavior="Post the fraud-pipeline release notes in the private team-only #fraud-status channel pinned to the sidebar.",
        invalid_behavior=["Post in the public org-wide #engineering-status channel", "Send via team email", "Skip posting"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-doc-review-process-001",
        target_type="procedural_constraint", domain="work_workflow",
        target_description="user's design-doc review workflow — drifted to a single 30-minute synchronous walk-through with stakeholders from a multi-day async comment thread, repeated active use",
        target_slot_id="doc_review_workflow::v1", topic="design_doc_review_workflow",
        versions=[
            VersionSpec(value="multi-day asynchronous comment thread on the shared Notion page", polarity="constraint", session_introduced=1),
            VersionSpec(value="a single 30-minute synchronous walk-through with all stakeholders on Zoom", polarity="constraint", session_introduced=2),
        ],
        current_query="Sarah finished the v2 of the auth-refactor design — set up the review.",
        required_behavior="Schedule a single 30-minute synchronous walk-through on Zoom with the stakeholders for Sarah's auth-refactor design.",
        invalid_behavior=["Open a multi-day async comment thread on Notion", "Email each stakeholder separately", "Skip the review entirely"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-mentorship-channel-001",
        target_type="procedural_constraint", domain="management",
        target_description="user's where-to-do-mentorship — drifted to a structured weekly write-up sent the night before from in-person whiteboarding, repeated active use",
        target_slot_id="mentorship_channel::v1", topic="mentorship_channel",
        versions=[
            VersionSpec(value="in-person whiteboarding sessions in the meeting room every Friday", polarity="constraint", session_introduced=1),
            VersionSpec(value="structured weekly write-up sent the night before with three discussion prompts", polarity="constraint", session_introduced=2),
        ],
        current_query="Plan this week's mentorship for Marcus.",
        required_behavior="Send Marcus a structured weekly write-up the night before with three discussion prompts.",
        invalid_behavior=["Plan an in-person whiteboarding session", "Schedule an unstructured 1:1", "Skip mentorship"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-language-tutor-channel-001",
        target_type="object_preference", domain="learning",
        target_description="user's Spanish-conversation channel — drifted to weekly italki video sessions with one tutor from the meetup-group practice, repeated active use",
        target_slot_id="spanish_practice::v1", topic="spanish_conversation_channel",
        versions=[
            VersionSpec(value="weekly Spanish-meetup practice at the community center with rotating partners", polarity="prefer", session_introduced=1),
            VersionSpec(value="weekly italki video session with the dedicated Madrid-based tutor", polarity="prefer", session_introduced=2),
        ],
        current_query="Block this week's Spanish practice on my calendar.",
        required_behavior="Block this week's Spanish practice as a weekly italki video session with the dedicated Madrid-based tutor.",
        invalid_behavior=["Block the Spanish-meetup at the community center", "Suggest a Duolingo session instead", "Skip practice"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-1on1-prep-001",
        target_type="procedural_constraint", domain="management",
        target_description="user's 1:1 prep workflow — drifted to a shared running doc that the report owns from a manager-led talking-points list, repeated active use",
        target_slot_id="onon_prep::v1", topic="onon_prep_workflow",
        versions=[
            VersionSpec(value="manager-led talking-points list drafted in the user's notebook before each session", polarity="constraint", session_introduced=1),
            VersionSpec(value="shared running doc owned by the report and updated continuously between sessions", polarity="constraint", session_introduced=2),
        ],
        current_query="Tomorrow's 1:1 with Priya is on the books — what do I need to do tonight?",
        required_behavior="Tonight just review the shared running doc Priya owns; she's already updated it for tomorrow's 1:1.",
        invalid_behavior=["Draft a manager-led talking-points list in your notebook", "Email Priya questions to prepare", "Cancel the 1:1"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-coding-pairing-001",
        target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's pair-programming setup — drifted to a Tuplecloud session with screen-share-host swapping from in-person side-by-side at the same monitor, repeated active use",
        target_slot_id="pairing_setup::v1", topic="pair_programming_setup",
        versions=[
            VersionSpec(value="in-person side-by-side pairing at a single monitor in the office", polarity="constraint", session_introduced=1),
            VersionSpec(value="Tuplecloud remote pairing with screen-share-host swapping every 25 minutes", polarity="constraint", session_introduced=2),
        ],
        current_query="Marcus and I are pairing on the auth-token rotation tomorrow morning — set it up.",
        required_behavior="Set up tomorrow's pairing as a Tuplecloud remote session with screen-share-host swapping every 25 minutes.",
        invalid_behavior=["Set up an in-person side-by-side at the office", "Set up a Zoom call", "Skip the pairing"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    # narrow (4)
    _trip(_s(
        sample_id="p3-narrow-rfc-process-001",
        target_type="procedural_constraint", domain="work_workflow",
        target_description="user's RFC approval requirement — three explicit narrowings: any RFC → 2-reviewer approval → 2-reviewer + on-call sign-off",
        target_slot_id="rfc_approval::v1", topic="rfc_approval_requirement",
        versions=[
            VersionSpec(value="any RFC merges with the author's own approval", polarity="constraint", session_introduced=1),
            VersionSpec(value="every RFC requires sign-off from two senior engineer reviewers", polarity="constraint", session_introduced=2),
            VersionSpec(value="every RFC requires sign-off from two senior engineers and the current on-call lead", polarity="constraint", session_introduced=3),
        ],
        current_query="Marcus's RFC for the new caching layer just hit ready-for-review — can it merge?",
        required_behavior="Hold the merge until two senior engineers and the current on-call lead have signed off.",
        invalid_behavior=["Merge with author's approval only", "Merge after one reviewer signs off", "Merge after two reviewers without the on-call sign-off"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-meeting-attendance-001",
        target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's optional-meeting attendance rule — three explicit narrowings: accept all → only with a written agenda → only with agenda + clear decision needed",
        target_slot_id="optional_meeting::v1", topic="optional_meeting_attendance",
        versions=[
            VersionSpec(value="accept any optional-meeting invite that doesn't conflict on the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept optional-meeting invites only when a written agenda is attached", polarity="constraint", session_introduced=2),
            VersionSpec(value="accept optional-meeting invites only when a written agenda is attached AND a clear decision is needed", polarity="constraint", session_introduced=3),
        ],
        current_query="Marketing just sent an optional invite for tomorrow afternoon — RSVP yes or no?",
        required_behavior="RSVP yes only if marketing's invite has a written agenda AND a clear decision is needed; otherwise decline.",
        invalid_behavior=["RSVP yes to any non-conflicting invite", "RSVP yes if there's only an agenda", "RSVP yes if there's only a decision needed"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-content-output-001",
        target_type="conceptual_stance", domain="creative",
        target_description="user's blog content scope — three explicit narrowings: any topic → engineering-only → engineering-only + ≥1500 words",
        target_slot_id="blog_scope::v1", topic="blog_content_scope",
        versions=[
            VersionSpec(value="any topic the user finds compelling — engineering, books, hobbies", polarity="prefer", session_introduced=1),
            VersionSpec(value="engineering topics only — no book reviews or hobby essays", polarity="prefer", session_introduced=2),
            VersionSpec(value="engineering topics only with at least 1500 words per post", polarity="prefer", session_introduced=3),
        ],
        current_query="I have a draft on home-network configuration — should I publish?",
        required_behavior="Publish the home-network configuration piece only if it's an engineering topic AND at least 1500 words; otherwise hold back.",
        invalid_behavior=["Publish anything compelling", "Publish if engineering only without checking length", "Publish a 700-word engineering post"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-tutoring-availability-001",
        target_type="procedural_constraint", domain="learning",
        target_description="user's tutoring availability — three explicit narrowings: any time → weekday evenings → Tue/Thu evenings only",
        target_slot_id="tutoring_window::v1", topic="tutoring_availability",
        versions=[
            VersionSpec(value="any time the student requests, weekdays or weekends", polarity="constraint", session_introduced=1),
            VersionSpec(value="only weekday evenings between 6 and 9 PM", polarity="constraint", session_introduced=2),
            VersionSpec(value="only Tuesday and Thursday evenings between 6 and 9 PM", polarity="constraint", session_introduced=3),
        ],
        current_query="A returning student is asking for a session this Saturday morning — yes or no?",
        required_behavior="Decline the Saturday morning session; available only Tuesday and Thursday evenings between 6 and 9 PM.",
        invalid_behavior=["Accept the Saturday morning session", "Offer a Wednesday evening alternative", "Offer Saturday evening"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    # multi triple (3)
    _trip(_s(
        sample_id="p3-multi-team-chat-tool-001",
        target_type="object_preference", domain="work_communication",
        target_description="team's chat tool — three-version chain: HipChat → Slack → Microsoft Teams",
        target_slot_id="chat_tool::v1", topic="team_chat_tool",
        versions=[
            VersionSpec(value="HipChat with the legacy room-based archive", polarity="prefer", session_introduced=1),
            VersionSpec(value="Slack with the team's enterprise grid configuration", polarity="prefer", session_introduced=2),
            VersionSpec(value="Microsoft Teams with the SharePoint integration and meeting recordings", polarity="prefer", session_introduced=3),
        ],
        current_query="Where do I post the announcement about Friday's all-hands?",
        required_behavior="Post the all-hands announcement in Microsoft Teams using the SharePoint integration.",
        invalid_behavior=["Post in HipChat", "Post in Slack", "Email the announcement"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-multi-curriculum-platform-001",
        target_type="object_preference", domain="learning",
        target_description="user's online-course delivery platform — three-version chain: Teachable → Thinkific → Maven (live cohort)",
        target_slot_id="course_platform::v1", topic="online_course_platform",
        versions=[
            VersionSpec(value="Teachable with the self-paced video module structure", polarity="prefer", session_introduced=1),
            VersionSpec(value="Thinkific with the bundled-package and drip-content settings", polarity="prefer", session_introduced=2),
            VersionSpec(value="Maven with the live-cohort format and 6-week structured sessions", polarity="prefer", session_introduced=3),
        ],
        current_query="My systems-design course is ready — where do I host it?",
        required_behavior="Host the systems-design course on Maven using the live-cohort format with 6-week structured sessions.",
        invalid_behavior=["Host on Teachable", "Host on Thinkific", "Host on a third platform"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-multi-feedback-cycle-001",
        target_type="conceptual_stance", domain="management",
        target_description="user's performance review framework — three-version chain: stack-ranking → 360-degree → continuous check-in (with revert back to 360)",
        target_slot_id="review_framework::v1", topic="performance_review_framework",
        versions=[
            VersionSpec(value="annual stack-ranking with the forced distribution curve", polarity="prefer", session_introduced=1),
            VersionSpec(value="360-degree review with peer, manager, and self inputs", polarity="prefer", session_introduced=2),
            VersionSpec(value="continuous monthly check-ins replacing the annual cycle", polarity="prefer", session_introduced=3),
            VersionSpec(value="360-degree review with peer, manager, and self inputs", polarity="prefer", session_introduced=4),
        ],
        current_query="Q4 is wrapping — kick off this year's performance review process for the team.",
        required_behavior="Kick off the team's review using the 360-degree framework with peer, manager, and self inputs.",
        invalid_behavior=["Run a stack-ranking", "Run continuous monthly check-ins", "Skip the review entirely"],
        failure_patterns=["multi_version"], subtype="reverted",
    )),

    # multi doublet (2, 4-version chains)
    _doub(_s(
        sample_id="p3-multi-onboarding-curriculum-4v-001",
        target_type="procedural_constraint", domain="management",
        target_description="user's senior-engineer onboarding curriculum — four-version chain across iterations",
        target_slot_id="senior_onboarding::v1", topic="senior_onboarding_curriculum",
        versions=[
            VersionSpec(value="two-week reading list followed by shadow rotation", polarity="constraint", session_introduced=1),
            VersionSpec(value="one-week reading list with a small shipping fix in week one", polarity="constraint", session_introduced=2),
            VersionSpec(value="pair on a real ticket from day one with no reading list", polarity="constraint", session_introduced=3),
            VersionSpec(value="full ownership of a scoped feature on day one with daily check-ins from a peer mentor", polarity="constraint", session_introduced=4),
        ],
        current_query="Erin starts Monday as a senior platform hire — what's her first few days look like?",
        required_behavior="Erin gets full ownership of a scoped feature on day one with daily check-ins from a peer mentor.",
        invalid_behavior=["Give her a two-week reading list and shadow rotation", "Give her a one-week reading list", "Have her pair on a real ticket all week"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _doub(_s(
        sample_id="p3-multi-knowledge-base-4v-001",
        target_type="object_preference", domain="work_workflow",
        target_description="team's customer-facing knowledge base — four-version chain: Zendesk Guide → HelpScout Docs → Intercom Articles → custom Astro site",
        target_slot_id="kb_platform::v1", topic="customer_knowledge_base",
        versions=[
            VersionSpec(value="Zendesk Guide with the legacy multi-brand configuration", polarity="prefer", session_introduced=1),
            VersionSpec(value="HelpScout Docs with the linked help center and category structure", polarity="prefer", session_introduced=2),
            VersionSpec(value="Intercom Articles with the in-app messenger integration", polarity="prefer", session_introduced=3),
            VersionSpec(value="custom Astro static site deployed to Cloudflare Pages with the Algolia search", polarity="prefer", session_introduced=4),
        ],
        current_query="Publish the new payment-error troubleshooting guide for customers.",
        required_behavior="Publish the troubleshooting guide on the custom Astro static site deployed to Cloudflare Pages with Algolia search.",
        invalid_behavior=["Publish in Zendesk Guide", "Publish in HelpScout Docs", "Publish in Intercom Articles"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    # explicit (2)
    _trip(_s(
        sample_id="p3-explicit-time-tracker-001",
        target_type="object_preference", domain="productivity",
        target_description="user's time-tracker — explicit replacement of Toggl with Harvest",
        target_slot_id="time_tracker::v1", topic="time_tracking_tool",
        versions=[
            VersionSpec(value="Toggl Track with the autotrack rules and project-level reporting", polarity="prefer", session_introduced=1),
            VersionSpec(value="Harvest with the integrated invoicing and client-export workflow", polarity="prefer", session_introduced=2),
        ],
        current_query="Log this morning's three hours on the fraud client.",
        required_behavior="Log the three hours in Harvest using the integrated invoicing and client-export workflow.",
        invalid_behavior=["Log in Toggl Track", "Log in a spreadsheet", "Skip the log"],
        failure_patterns=["explicit_replacement"],
    )),

    _trip(_s(
        sample_id="p3-explicit-team-wiki-001",
        target_type="object_preference", domain="work_workflow",
        target_description="team's internal wiki — explicit replacement of Notion with Slab",
        target_slot_id="internal_wiki::v1", topic="internal_team_wiki",
        versions=[
            VersionSpec(value="Notion with the linked-database hierarchy and the templates gallery", polarity="prefer", session_introduced=1),
            VersionSpec(value="Slab with the team-scoped folders and the meeting-notes auto-template", polarity="prefer", session_introduced=2),
        ],
        current_query="Document the new on-call rotation rules for the team.",
        required_behavior="Document the on-call rotation rules in Slab using the team-scoped folders and the meeting-notes auto-template.",
        invalid_behavior=["Document in Notion", "Document in a Google Doc", "Document in a Slack post"],
        failure_patterns=["explicit_replacement"],
    )),

    # abandonment (2)
    _drift(_s(
        sample_id="p3-drift-shared-vendor-meeting-001",
        target_type="procedural_constraint", domain="management",
        target_description="user's vendor-evaluation meetings — abandoned the cross-functional in-person meetings; written async-RFC review only now",
        target_slot_id="vendor_eval::v1", topic="vendor_evaluation_workflow",
        versions=[
            VersionSpec(value="cross-functional in-person meeting with sales, eng, and ops on the procurement floor", polarity="constraint", session_introduced=1),
            VersionSpec(value="written async-RFC review document circulated for two-business-day comment period", polarity="constraint", session_introduced=2),
        ],
        current_query="A new observability vendor wants a slot to pitch — set it up.",
        required_behavior="Set up the observability vendor evaluation as a written async-RFC review document circulated for a two-business-day comment period.",
        invalid_behavior=["Set up an in-person meeting on the procurement floor", "Set up a Zoom call", "Skip the evaluation entirely"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    _drift(_s(
        sample_id="p3-drift-monthly-review-001",
        target_type="procedural_constraint", domain="learning",
        target_description="user's self-improvement review — abandoned the monthly journaling session; quarterly retrospective with a written prompt-set only now",
        target_slot_id="self_review::v1", topic="self_improvement_review",
        versions=[
            VersionSpec(value="monthly free-form journaling session in the personal notebook", polarity="constraint", session_introduced=1),
            VersionSpec(value="quarterly structured retrospective with the written six-prompt-set in the planning doc", polarity="constraint", session_introduced=2),
        ],
        current_query="It's the start of a new month — block time for self-reflection on my calendar.",
        required_behavior="Block self-reflection time only at the start of a new quarter for the structured retrospective with the written six-prompt-set.",
        invalid_behavior=["Block monthly free-form journaling time", "Block weekly self-reflection time", "Skip self-reflection"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    # gradual_narrowing (1)
    _drift(_s(
        sample_id="p3-drift-meeting-narrow-001",
        target_type="conceptual_stance", domain="work_communication",
        target_description="user's RSVP-yes criteria for internal meetings — gradually narrowed to only meetings where the user is the decision-maker via cumulative preference signals",
        target_slot_id="internal_meeting::v1", topic="internal_meeting_rsvp",
        versions=[
            VersionSpec(value="any internal meeting that fits the calendar and asks for the user's input", polarity="prefer", session_introduced=1),
            VersionSpec(value="only internal meetings where the user is the decision-maker on the agenda", polarity="prefer", session_introduced=2),
        ],
        current_query="I just got pulled into a planning sync where the VP wants my input — go or skip?",
        required_behavior="Skip the planning sync; the user RSVPs only when they're the decision-maker on the agenda.",
        invalid_behavior=["RSVP yes to give input", "RSVP yes for the first 15 minutes only", "Send a deputy"],
        failure_patterns=["implicit_drift"],
    ), "gradual_narrowing"),
]
