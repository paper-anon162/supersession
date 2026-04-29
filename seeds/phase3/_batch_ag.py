"""Phase 3 batch AG — deficit-and-topic-targeted final fill.

Constraints:
- 14 narrowing triple, ALL non-daily-preference (work_tooling /
  learning_routine / communication_boundary domains) to break the 52.4%
  daily_preference breach in narrowing × {compact,standard,hard} cells.
- 5 gradual_narrowing drift (deficit -3)
- 4 multi_version triple (deficit -3)
- 2 abandonment drift (deficit -1)

Domain → topic_group:
- tech_workflow / business / productivity / career / writing → work_tooling
- learning / management → learning_routine
- work_communication / relationships → communication_boundary
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

def _drift(s, dt): return Phase3GroupSpec(spine=s, group_type="triple", horizons=["compact","standard","hard"], implicit_drift_type=dt, spine_source="hand")
def _trip(s): return Phase3GroupSpec(spine=s, group_type="triple", horizons=["compact","standard","hard"], implicit_drift_type=None, spine_source="hand")


PHASE3_BATCH_AG: list[Phase3GroupSpec] = [
    # ------------------------------------------------------------------
    # 14 narrowing triple — all non-daily-preference domains
    # ------------------------------------------------------------------

    # work_tooling narrowing (5)
    _trip(_s(sample_id="p3-narrow-pull-pr-merge-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's pull-request merge rule — three explicit narrowings: any → with-CI-green → with-CI-green + reviewed-by-staff-engineer",
        target_slot_id="prmerge::v1", topic="pr_merge_rule",
        versions=[
            VersionSpec(value="merge any pull request the user opens whenever the user wants", polarity="constraint", session_introduced=1),
            VersionSpec(value="merge pull requests only after the continuous-integration suite returns green on the diff", polarity="constraint", session_introduced=2),
            VersionSpec(value="merge pull requests only after CI is green AND the diff has been signed off by a staff-level reviewer", polarity="constraint", session_introduced=3),
        ],
        current_query="My CI run just passed on a non-trivial diff with no senior review yet — does the merge rule allow it?",
        required_behavior="No; the rule needs the staff-level sign-off before merge.",
        invalid_behavior=["Merge whenever", "Merge on CI alone", "Merge on senior-only without CI"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-deploy-window-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's deploy window rule — three explicit narrowings: any → weekday-only → weekday-only + before-3pm-Pacific",
        target_slot_id="depwin::v1", topic="deploy_window_rule",
        versions=[
            VersionSpec(value="ship production deploys whenever the release branch is ready, any day or hour", polarity="constraint", session_introduced=1),
            VersionSpec(value="ship production deploys only on weekdays, never on weekends", polarity="constraint", session_introduced=2),
            VersionSpec(value="ship production deploys only on weekdays AND only before 3pm Pacific to leave on-call coverage", polarity="constraint", session_introduced=3),
        ],
        current_query="The release branch is ready and it's Wednesday at 5pm Pacific — does the rule allow it?",
        required_behavior="No; the rule cuts off deploys at the 3pm Pacific boundary.",
        invalid_behavior=["Ship anytime", "Ship weekday late", "Ship weekend early"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-vendor-select-001", target_type="procedural_constraint", domain="business",
        target_description="user's vendor-selection rule — three explicit narrowings: any → SOC2-Type-2 → SOC2-Type-2 + signed-DPA",
        target_slot_id="vendor::v1", topic="vendor_selection_rule",
        versions=[
            VersionSpec(value="contract any vendor the user finds in the procurement search", polarity="constraint", session_introduced=1),
            VersionSpec(value="contract only vendors holding a current SOC2 Type 2 audit report", polarity="constraint", session_introduced=2),
            VersionSpec(value="contract only vendors with current SOC2 Type 2 AND a signed Data Processing Agreement on file", polarity="constraint", session_introduced=3),
        ],
        current_query="Procurement found a vendor with SOC2 audit but no DPA on file yet — does the rule allow signing?",
        required_behavior="No; the rule requires both SOC2 AND a signed DPA before signing.",
        invalid_behavior=["Sign with any vendor", "Sign on SOC2 alone", "Sign without SOC2 if DPA in place"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-design-spec-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's design-doc rule — three explicit narrowings: any → with-roll-out-plan → with-roll-out-plan + cost-estimate",
        target_slot_id="designdoc::v1", topic="design_doc_rule",
        versions=[
            VersionSpec(value="approve any design doc the team submits for the review queue", polarity="constraint", session_introduced=1),
            VersionSpec(value="approve design docs only when the document includes an explicit roll-out plan section", polarity="constraint", session_introduced=2),
            VersionSpec(value="approve design docs only with a roll-out plan AND an explicit cost-and-staffing estimate at the top", polarity="constraint", session_introduced=3),
        ],
        current_query="An engineer submitted a doc with the deployment plan but no cost section — does the rule approve?",
        required_behavior="No; the rule needs both the roll-out plan AND the cost estimate.",
        invalid_behavior=["Approve any doc", "Approve on plan alone", "Approve on cost alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-doc-write-001", target_type="procedural_constraint", domain="writing",
        target_description="user's writing-publish rule — three explicit narrowings: any → with-source-citations → with-source-citations + peer-edit-pass",
        target_slot_id="docpub::v1", topic="writing_publish_rule",
        versions=[
            VersionSpec(value="publish any technical article the user finishes drafting", polarity="constraint", session_introduced=1),
            VersionSpec(value="publish articles only when every claim has a primary-source citation footnoted", polarity="constraint", session_introduced=2),
            VersionSpec(value="publish articles only with primary-source citations AND only after a peer-reviewed copy-edit pass", polarity="constraint", session_introduced=3),
        ],
        current_query="A finished article has all citations but no peer copy-edit yet — does the rule allow publishing today?",
        required_behavior="No; the rule needs the peer edit pass before publish.",
        invalid_behavior=["Publish any draft", "Publish on citations alone", "Publish on peer-edit alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # learning_routine narrowing (4)
    _trip(_s(sample_id="p3-narrow-pull-course-take-001", target_type="procedural_constraint", domain="learning",
        target_description="user's course-enrollment rule — three explicit narrowings: any → with-graded-projects → with-graded-projects + cohort-of-twenty-or-fewer",
        target_slot_id="course::v1", topic="course_enrollment_rule",
        versions=[
            VersionSpec(value="enroll in any continuing-education course the user finds compelling", polarity="constraint", session_introduced=1),
            VersionSpec(value="enroll only in courses that have graded project assignments, no lecture-only", polarity="constraint", session_introduced=2),
            VersionSpec(value="enroll only in courses with graded projects AND only ones where the cohort holds twenty or fewer students", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend recommended a project-based course with forty students enrolled — does the rule allow signing up?",
        required_behavior="No; the rule caps cohort size below this enrollment.",
        invalid_behavior=["Enroll in any course", "Enroll in any project-based course", "Enroll in a small lecture-only course"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-tutor-pick-001", target_type="procedural_constraint", domain="learning",
        target_description="user's tutor-acceptance rule — three explicit narrowings: any → master's-credential → master's-credential + verified-references",
        target_slot_id="tutor::v1", topic="tutor_acceptance_rule",
        versions=[
            VersionSpec(value="hire any tutor the user finds on the language-learning platform", polarity="constraint", session_introduced=1),
            VersionSpec(value="hire only tutors holding at least a master's-level credential in the target language", polarity="constraint", session_introduced=2),
            VersionSpec(value="hire only tutors with a master's credential AND only those with at least three verified prior-student references", polarity="constraint", session_introduced=3),
        ],
        current_query="A platform tutor with the credential but only one student review showing — does the rule allow hiring?",
        required_behavior="No; the rule needs at least three verified references.",
        invalid_behavior=["Hire any tutor", "Hire on credential alone", "Hire on references alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-1on1-cad-001", target_type="procedural_constraint", domain="management",
        target_description="user's 1:1 cadence rule — three explicit narrowings: any → biweekly-min → biweekly-min + with-shared-doc",
        target_slot_id="1on1::v1", topic="one_on_one_cadence_rule",
        versions=[
            VersionSpec(value="hold direct-report 1:1s whenever the calendar happens to permit", polarity="constraint", session_introduced=1),
            VersionSpec(value="hold direct-report 1:1s on a strict biweekly minimum cadence with no skipped weeks", polarity="constraint", session_introduced=2),
            VersionSpec(value="hold direct-report 1:1s on a biweekly minimum AND only when a shared async-update doc has been filled in beforehand", polarity="constraint", session_introduced=3),
        ],
        current_query="The next biweekly 1:1 slot is tomorrow but the report hasn't filled in their doc yet — does the rule still hold the meeting?",
        required_behavior="No; the rule requires the doc to be filled in first.",
        invalid_behavior=["Hold whenever", "Hold biweekly without doc", "Hold off-cadence with doc"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-skill-pract-001", target_type="procedural_constraint", domain="management",
        target_description="user's hiring-loop rule — three explicit narrowings: any → onsite-five-rounds → onsite-five-rounds + bar-raiser-attached",
        target_slot_id="hiring::v1", topic="hiring_loop_rule",
        versions=[
            VersionSpec(value="extend offers to any candidate the user feels confident about after the conversation", polarity="constraint", session_introduced=1),
            VersionSpec(value="extend offers only after a complete onsite loop of exactly five technical rounds", polarity="constraint", session_introduced=2),
            VersionSpec(value="extend offers only after the five-round onsite AND only when an external bar-raiser has been attached to the panel", polarity="constraint", session_introduced=3),
        ],
        current_query="A candidate finished all five rounds with strong scores but no bar-raiser was assigned — does the rule allow the offer?",
        required_behavior="No; the rule requires the bar-raiser on the panel.",
        invalid_behavior=["Offer based on confidence", "Offer on five-rounds alone", "Offer on bar-raiser without full loop"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # communication_boundary narrowing (5)
    _trip(_s(sample_id="p3-narrow-pull-comm-channel-001", target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's incoming-channel rule — three explicit narrowings: any → email-only → email-only + scheduled-time-window",
        target_slot_id="incoming::v1", topic="incoming_channel_rule",
        versions=[
            VersionSpec(value="answer incoming work questions on whatever channel the sender chose", polarity="constraint", session_introduced=1),
            VersionSpec(value="answer incoming work questions only when sent via the formal email channel, never DMs", polarity="constraint", session_introduced=2),
            VersionSpec(value="answer incoming work questions only via formal email AND only during the scheduled 10am-to-noon response window", polarity="constraint", session_introduced=3),
        ],
        current_query="An email arrived at 4pm asking for a quick answer — does the rule allow responding?",
        required_behavior="No; the rule restricts responses to the morning window.",
        invalid_behavior=["Answer any channel", "Answer email any time", "Answer DM in window"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-comm-respond-001", target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's slack-mention rule — three explicit narrowings: any → flagged-urgent → flagged-urgent + from-direct-manager",
        target_slot_id="mention::v1", topic="slack_mention_rule",
        versions=[
            VersionSpec(value="respond to any Slack mention the user receives during work hours", polarity="constraint", session_introduced=1),
            VersionSpec(value="respond to Slack mentions only when the sender flagged the thread as urgent", polarity="constraint", session_introduced=2),
            VersionSpec(value="respond to Slack mentions only when flagged urgent AND only when the sender is the user's direct manager", polarity="constraint", session_introduced=3),
        ],
        current_query="A peer engineer just flagged a Slack mention as urgent — does the rule allow responding mid-task?",
        required_behavior="No; the rule restricts responses to the direct manager.",
        invalid_behavior=["Respond to any mention", "Respond to peer urgent", "Respond to manager non-urgent"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-comm-dinner-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's dinner-host rule — three explicit narrowings: any → small-group → small-group + with-week-notice",
        target_slot_id="dinhost::v1", topic="dinner_host_rule",
        versions=[
            VersionSpec(value="host any dinner gathering at the user's apartment that the user feels like having", polarity="constraint", session_introduced=1),
            VersionSpec(value="host dinner gatherings only when the planned guest list is six or fewer people", polarity="constraint", session_introduced=2),
            VersionSpec(value="host dinner gatherings only with six-or-fewer guests AND only when invitations went out at least one week in advance", polarity="constraint", session_introduced=3),
        ],
        current_query="A close friend asked the user to host a five-person dinner this Saturday — does the rule allow it?",
        required_behavior="No; the rule requires the week of advance notice that this Saturday-this-week ask doesn't have.",
        invalid_behavior=["Host any dinner", "Host five-person no-notice", "Host larger with notice"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-comm-text-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's group-text reply rule — three explicit narrowings: any → tagged-name → tagged-name + within-business-hours",
        target_slot_id="grouptext::v1", topic="group_text_reply_rule",
        versions=[
            VersionSpec(value="reply to any message in the family group text the user is part of", polarity="constraint", session_introduced=1),
            VersionSpec(value="reply to family group text messages only when the user's name was explicitly tagged in the message", polarity="constraint", session_introduced=2),
            VersionSpec(value="reply to family group texts only when explicitly tagged AND only during business hours of nine to five", polarity="constraint", session_introduced=3),
        ],
        current_query="The user's mother just tagged the user in a family thread at 9pm — does the rule allow replying tonight?",
        required_behavior="No; the rule restricts replies to business hours.",
        invalid_behavior=["Reply any message", "Reply tagged any time", "Reply untagged business hours"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-comm-talkrec-001", target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's talk-recommendation rule — three explicit narrowings: any → former-colleague → former-colleague + with-permission",
        target_slot_id="rec::v1", topic="talk_recommendation_rule",
        versions=[
            VersionSpec(value="write recommendation letters for any former colleague the user is asked to support", polarity="constraint", session_introduced=1),
            VersionSpec(value="write recommendation letters only for former colleagues the user worked with directly on a project", polarity="constraint", session_introduced=2),
            VersionSpec(value="write recommendation letters only for direct former colleagues AND only when the user has been given written permission to discuss the colleague's work history", polarity="constraint", session_introduced=3),
        ],
        current_query="A former colleague the user mentored just emailed asking for a letter without sharing any release form — does the rule allow writing?",
        required_behavior="No; the rule needs the written permission to discuss work history.",
        invalid_behavior=["Write for anyone", "Write on direct-colleague alone", "Write on permission alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # ------------------------------------------------------------------
    # 5 gradual_narrowing drift (deficit -3, over-fill cushion)
    # ------------------------------------------------------------------
    _drift(_s(sample_id="p3-drift-gn-blogread-001", target_type="object_preference", domain="learning",
        target_description="user's blog-reading rule — gradually narrowing without announcement: any → only-substack → only-substack + paid-subscription",
        target_slot_id="blogr::v1", topic="blog_reading_drift",
        versions=[
            VersionSpec(value="read any blog the user finds in the daily feed reader", polarity="prefer", session_introduced=1),
            VersionSpec(value="read only blogs hosted on Substack AND only ones with an active paid subscription tier the user has signed up for", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a free Substack blog with great recent posts — what now?",
        required_behavior="Pass; user reads only paid-subscription Substack blogs.",
        invalid_behavior=["Add the free Substack to the reader"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-confgo-001", target_type="procedural_constraint", domain="career",
        target_description="user's conference-attendance — gradually narrowing without announcement: any → only-keynote-speaker → only-keynote-speaker + travel-fully-covered",
        target_slot_id="confgo::v1", topic="conference_attendance_drift",
        versions=[
            VersionSpec(value="attend any tech conference the user finds compelling on the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="attend tech conferences only when invited as a keynote speaker AND only when the conference fully covers travel and lodging", polarity="constraint", session_introduced=2),
        ],
        current_query="A regional conference invited the user to keynote with travel reimbursement capped at half the cost — what now?",
        required_behavior="Pass; user attends only fully-covered keynote slots.",
        invalid_behavior=["Accept the half-covered keynote"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-podpick-001", target_type="object_preference", domain="learning",
        target_description="user's podcast pick — gradually narrowing without announcement: any → economics-focused → economics-focused + interview-format",
        target_slot_id="podpick::v1", topic="podcast_pick_drift",
        versions=[
            VersionSpec(value="add any podcast the user finds compelling to the listening queue", polarity="prefer", session_introduced=1),
            VersionSpec(value="add only economics-focused podcasts AND only ones in long-form interview format with a single guest", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended an economics roundtable show with three rotating hosts — what now?",
        required_behavior="Pass; user adds only single-guest interview-format economics podcasts.",
        invalid_behavior=["Add the multi-host economics show"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-meetwith-001", target_type="interpersonal_boundary", domain="career",
        target_description="user's external-meeting acceptance — gradually narrowing without announcement: any → only-existing-clients → only-existing-clients + on-Tuesdays",
        target_slot_id="extm::v1", topic="external_meeting_drift",
        versions=[
            VersionSpec(value="accept any external meeting request the user is sent", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept external meetings only with existing client contacts AND only schedule them on Tuesdays", polarity="constraint", session_introduced=2),
        ],
        current_query="A new prospect emailed asking the user for a Wednesday introductory meeting — what now?",
        required_behavior="Pass; user takes external meetings only with existing clients on Tuesdays.",
        invalid_behavior=["Accept the prospect Wednesday"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-classpick-001", target_type="object_preference", domain="management",
        target_description="user's continuing-ed pick — gradually narrowing without announcement: any → only-online-async → only-online-async + with-recorded-archive",
        target_slot_id="classpk::v1", topic="continuing_ed_drift",
        versions=[
            VersionSpec(value="enroll in any continuing-education class the user finds compelling", polarity="prefer", session_introduced=1),
            VersionSpec(value="enroll only in online async classes AND only ones that provide a recorded archive for catch-up", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a live online seminar with no recording — what now?",
        required_behavior="Pass; user enrolls only in async classes with recorded archives.",
        invalid_behavior=["Enroll in the live no-recording seminar"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    # ------------------------------------------------------------------
    # 4 multi_version triple (deficit -3, over-fill cushion)
    # ------------------------------------------------------------------
    _trip(_s(sample_id="p3-multi-trip-mtg-cad-001", target_type="procedural_constraint", domain="management",
        target_description="user's standup cadence — four versions: daily-30 → twice-week-15 → weekly-async-doc → none-at-all",
        target_slot_id="standup::v1", topic="standup_cadence",
        versions=[
            VersionSpec(value="run daily 30-minute team standups every weekday morning at the round table", polarity="constraint", session_introduced=1),
            VersionSpec(value="run twice-weekly 15-minute team standups Tuesday and Thursday mornings", polarity="constraint", session_introduced=2),
            VersionSpec(value="run a weekly async standup doc the team fills in by Monday noon, no live meeting", polarity="constraint", session_introduced=3),
            VersionSpec(value="run no standups at all; coordination through pull-request comments only", polarity="constraint", session_introduced=4),
        ],
        current_query="A new team member asked the user how the team coordinates day-to-day — what does the user say?",
        required_behavior="Coordination is through pull-request comments; no standup of any kind.",
        invalid_behavior=["Tell them daily 30-min standup", "Tell them twice-weekly 15-min", "Tell them weekly async doc"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-write-tool-001", target_type="object_preference", domain="writing",
        target_description="user's drafting tool — four versions: Scrivener → Ulysses → iA-Writer → plain-vim-markdown",
        target_slot_id="drafttool::v1", topic="drafting_tool",
        versions=[
            VersionSpec(value="draft long-form essays in Scrivener with the corkboard layout enabled", polarity="prefer", session_introduced=1),
            VersionSpec(value="draft long-form essays in Ulysses with the markdown library and goal-tracking enabled", polarity="prefer", session_introduced=2),
            VersionSpec(value="draft long-form essays in iA Writer with focus mode and grammar review enabled", polarity="prefer", session_introduced=3),
            VersionSpec(value="draft long-form essays in plain Vim with markdown files in a flat folder", polarity="prefer", session_introduced=4),
        ],
        current_query="A friend asked which tool the user uses for drafting essays now — what does the user say?",
        required_behavior="Tell them plain Vim with markdown files in a flat folder.",
        invalid_behavior=["Tell them Scrivener", "Tell them Ulysses", "Tell them iA Writer"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-bizmodel-001", target_type="conceptual_stance", domain="business",
        target_description="user's startup business model — four versions: SaaS-subscription → marketplace-fee → enterprise-license → open-source-services",
        target_slot_id="bizmodel::v1", topic="startup_business_model",
        versions=[
            VersionSpec(value="build the startup as a SaaS subscription with monthly per-seat pricing", polarity="prefer", session_introduced=1),
            VersionSpec(value="build the startup as a two-sided marketplace with a per-transaction fee", polarity="prefer", session_introduced=2),
            VersionSpec(value="build the startup as an enterprise-license model with annual six-figure contracts", polarity="prefer", session_introduced=3),
            VersionSpec(value="build the startup as open-source software with paid services and support contracts", polarity="prefer", session_introduced=4),
        ],
        current_query="An investor asked the user how the startup makes money — what does the user say?",
        required_behavior="Open-source software with paid services and support contracts.",
        invalid_behavior=["SaaS subscription per-seat", "Marketplace per-transaction fee", "Enterprise annual license"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-codereview-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's code-review process — four versions: solo-merge-no-review → required-pair-review → async-comment-review → live-pairing-only",
        target_slot_id="codereview::v1", topic="code_review_process",
        versions=[
            VersionSpec(value="merge the user's own engineering pull requests solo without any review step", polarity="constraint", session_introduced=1),
            VersionSpec(value="require a synchronous pair-review session with one other engineer before any merge", polarity="constraint", session_introduced=2),
            VersionSpec(value="require async written-comment review on the diff before merge, with all threads resolved", polarity="constraint", session_introduced=3),
            VersionSpec(value="require live pair-programming through the whole change, no separate review step", polarity="constraint", session_introduced=4),
        ],
        current_query="A teammate asked how the user wants their next pull request handled — what does the user say?",
        required_behavior="Live pair-programming through the change with no separate review step.",
        invalid_behavior=["Tell them solo merge", "Tell them sync pair-review", "Tell them async comments"],
        failure_patterns=["multi_version"], subtype="strong")),

    # ------------------------------------------------------------------
    # 2 abandonment drift
    # ------------------------------------------------------------------
    _drift(_s(sample_id="p3-drift-aban-conf-host-002", target_type="procedural_constraint", domain="career",
        target_description="user's annual conference hosting — abandoned after company shutdown, no replacement",
        target_slot_id="confhost2::v1", topic="conference_host_practice",
        versions=[
            VersionSpec(value="host the annual local-tech conference every October at the user's company office", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop hosting the annual local-tech conference after the title sponsor pulled out and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It's early October and a long-time attendee asked when this year's event is — what does the user say?",
        required_behavior="No event; the conference hosting practice has been abandoned.",
        invalid_behavior=["Tell them this October"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-mentees-001", target_type="interpersonal_boundary", domain="career",
        target_description="user's monthly mentoring rounds — abandoned after mentees graduated, no replacement",
        target_slot_id="mentees::v1", topic="mentoring_rounds_practice",
        versions=[
            VersionSpec(value="hold a monthly mentorship round with the cohort of three mentees on the first Saturday of each month", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the monthly mentorship rounds after all three mentees graduated to senior roles and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It's the first Saturday of the month and the calendar shows the old slot — what does the user do?",
        required_behavior="Skip the slot; the mentorship rounds practice has been abandoned.",
        invalid_behavior=["Send mentorship invites for the slot"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),
]
