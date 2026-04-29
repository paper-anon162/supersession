"""Phase 3 batch AE — communication_boundary + interpersonal_boundary heavy.

Targets the topic-balance bottleneck blocking selector load. Pool has
76 surplus groups but only ~6.8% comm_boundary topic; selector 50% cap
means we can't seat the surplus until we add more comm_boundary anchors.
All spines use referential current_query phrasing to avoid leakage filter."""

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


PHASE3_BATCH_AE: list[Phase3GroupSpec] = [
    # abandonment (8) — comm_boundary heavy
    _drift(_s(sample_id="p3-drift-aban-comm-callback-001", target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's same-day callback rule for clients — abandoned after burnout, no replacement",
        target_slot_id="callback::v1", topic="client_callback_practice",
        versions=[
            VersionSpec(value="return every client phone call by end of the same business day, no exceptions", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop returning client calls same-day after burnout and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="A client just left a voicemail at 4pm Tuesday — does the old urgency rule apply?",
        required_behavior="No; the same-day callback practice has been abandoned.",
        invalid_behavior=["Apply the same-day callback rule"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-comm-officehours-001", target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's open-door office hours — abandoned after move to async-first culture, no replacement",
        target_slot_id="ohours::v1", topic="open_door_office_hours_practice",
        versions=[
            VersionSpec(value="hold drop-in office hours every Wednesday afternoon at the desk for any team member", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop holding the open-door Wednesday office hours after the team shifted to async-first culture and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Wednesday afternoon and a teammate poked their head in — does the old hours pattern apply?",
        required_behavior="No; the open-door office hours practice has been abandoned.",
        invalid_behavior=["Apply the open-door rule"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-comm-thankyou-001", target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's thank-you note practice — abandoned after life got busier, no replacement",
        target_slot_id="thank::v1", topic="handwritten_thank_you_practice",
        versions=[
            VersionSpec(value="send a handwritten thank-you note to every client after each completed engagement", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop sending handwritten thank-you notes after life got busier and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="A client engagement just wrapped up — does the post-engagement gesture practice apply?",
        required_behavior="No; the handwritten thank-you note practice has been abandoned.",
        invalid_behavior=["Apply the post-engagement note rule"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-comm-syncs-001", target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's weekly cross-team syncs — abandoned after re-org, no replacement",
        target_slot_id="syncs::v1", topic="cross_team_sync_practice",
        versions=[
            VersionSpec(value="hold a weekly Friday cross-team sync with the design and PM leads at the round table", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop holding the weekly cross-team sync after the re-org separated the user from the design and PM teams and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Friday morning — does the old recurring-with-other-leads slot still apply?",
        required_behavior="No; the cross-team sync practice has been abandoned.",
        invalid_behavior=["Apply the recurring sync rule"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-comm-newsletter-001", target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's quarterly investor update — abandoned after company shutdown, no replacement",
        target_slot_id="invupd::v1", topic="quarterly_investor_update_practice",
        versions=[
            VersionSpec(value="send a quarterly investor update email at the end of each quarter to the angel-investor list", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop sending quarterly investor updates after the startup shut down and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the last week of the quarter — does the old recurring-update obligation apply?",
        required_behavior="No; the quarterly update practice has been abandoned.",
        invalid_behavior=["Apply the recurring update rule"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-comm-grouptext-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's daily group-text catchups — abandoned after group dispersal, no replacement",
        target_slot_id="gtext::v1", topic="daily_group_text_practice",
        versions=[
            VersionSpec(value="post a morning hello in the college-friends group text every weekday", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the daily morning post in the college-friends group text after the group dispersed across countries and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 7am and the group thread is open — does the old morning-greeting pattern apply?",
        required_behavior="No; the daily group-text practice has been abandoned.",
        invalid_behavior=["Apply the daily greeting rule"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-comm-handoffmemo-001", target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's project-handoff memo — abandoned after standardized handoff template adopted then dropped, no replacement",
        target_slot_id="handoff::v1", topic="project_handoff_memo_practice",
        versions=[
            VersionSpec(value="write a 1500-word handoff memo at the end of every engineering project for the next owner", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop writing the handoff memo after the team adopted then dropped a Notion template and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="A project just wrapped this week and a new owner is taking over — does the old handoff-document obligation apply?",
        required_behavior="No; the handoff memo practice has been abandoned.",
        invalid_behavior=["Apply the handoff-document rule"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-comm-icebreaker-001", target_type="interpersonal_boundary", domain="management",
        target_description="user's team icebreaker round — abandoned after pivot to async standups, no replacement",
        target_slot_id="ice::v1", topic="team_icebreaker_practice",
        versions=[
            VersionSpec(value="open every Monday team meeting with a five-minute icebreaker question round for the entire team", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop the Monday icebreaker round after pivoting to async standups in the team channel and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Monday and a stand-in is leading the team meeting — does the old opening-segment pattern apply?",
        required_behavior="No; the icebreaker practice has been abandoned.",
        invalid_behavior=["Apply the opening-icebreaker rule"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # narrowing (6) — comm_boundary heavy with referential queries
    _trip(_s(sample_id="p3-narrow-pull-comm-email-001", target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's email reply rule — three explicit narrowings: any → existing-clients-only → existing-clients-only + within-2-business-days",
        target_slot_id="email::v1", topic="email_reply_rule",
        versions=[
            VersionSpec(value="reply to any email that hits the inbox within the same business day", polarity="constraint", session_introduced=1),
            VersionSpec(value="reply only to emails from existing client contacts, never new prospects or vendors", polarity="constraint", session_introduced=2),
            VersionSpec(value="reply only to emails from existing client contacts AND only when the response can fit within two business days of receipt", polarity="constraint", session_introduced=3),
        ],
        current_query="An email from a long-time client just landed but I am traveling for the next four business days — does this fit?",
        required_behavior="No; the rule requires the reply to fit within two business days, which the trip blocks.",
        invalid_behavior=["Reply to any email", "Reply to existing client outside the window", "Reply within window to a non-client"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-comm-feedback-001", target_type="interpersonal_boundary", domain="management",
        target_description="user's peer-feedback rule — three explicit narrowings: any → asked-for-only → asked-for-only + sandwich-format",
        target_slot_id="feedback::v1", topic="peer_feedback_rule",
        versions=[
            VersionSpec(value="give peer feedback to anyone on the team whenever the user notices something worth saying", polarity="constraint", session_introduced=1),
            VersionSpec(value="give peer feedback only to people who explicitly ask for it, never unsolicited", polarity="constraint", session_introduced=2),
            VersionSpec(value="give peer feedback only to people who explicitly ask AND only delivered in a praise-criticism-praise sandwich format", polarity="constraint", session_introduced=3),
        ],
        current_query="A teammate asked for blunt critical feedback on their proposal directly — does this fit?",
        required_behavior="No; the rule requires the wrapper format the teammate explicitly opted out of.",
        invalid_behavior=["Volunteer feedback", "Give blunt asked-for feedback", "Give sandwich-wrapped unsolicited feedback"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-comm-meet-001", target_type="interpersonal_boundary", domain="work_communication",
        target_description="user's meeting-host rule — three explicit narrowings: any → with-prepared-agenda → with-prepared-agenda + 30-minute-cap",
        target_slot_id="hostmeet::v1", topic="meeting_hosting_rule",
        versions=[
            VersionSpec(value="host any meeting on the team's calendar that fits the day", polarity="constraint", session_introduced=1),
            VersionSpec(value="host meetings only when a prepared written agenda has been circulated 24 hours ahead", polarity="constraint", session_introduced=2),
            VersionSpec(value="host meetings only with a prepared written agenda 24 hours ahead AND only when the planned slot is 30 minutes or shorter", polarity="constraint", session_introduced=3),
        ],
        current_query="The product manager wants me to host a 90-minute discovery session next Tuesday with the agenda already shared — does this fit?",
        required_behavior="No; the rule caps the session length below the requested duration.",
        invalid_behavior=["Host without agenda", "Host any agenda-prepared meeting", "Host short meeting without agenda"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-comm-call-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's after-hours call rule — three explicit narrowings: any → close-circle → close-circle + emergencies-only",
        target_slot_id="afterhours::v1", topic="after_hours_call_rule",
        versions=[
            VersionSpec(value="answer any phone call on the personal line outside of work hours", polarity="constraint", session_introduced=1),
            VersionSpec(value="answer after-hours phone calls only from people in the user's close inner circle of five", polarity="constraint", session_introduced=2),
            VersionSpec(value="answer after-hours phone calls only from people in the close inner circle AND only when the call is flagged as an emergency", polarity="constraint", session_introduced=3),
        ],
        current_query="A close-circle friend is calling at 10pm Tuesday to chat about their work day — does this fit?",
        required_behavior="No; the rule requires the call to be an emergency.",
        invalid_behavior=["Answer any after-hours call", "Answer close-circle non-emergency", "Answer outsider emergency"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-comm-mentor-001", target_type="interpersonal_boundary", domain="career",
        target_description="user's mentee accept rule — three explicit narrowings: any → former-coworkers → former-coworkers + still-in-tech",
        target_slot_id="mentee::v1", topic="mentee_accept_rule",
        versions=[
            VersionSpec(value="accept any aspiring mentee who reaches out by email", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept mentee requests only from people who once worked with the user directly", polarity="constraint", session_introduced=2),
            VersionSpec(value="accept mentee requests only from people who once worked with the user directly AND who are still active in the tech industry today", polarity="constraint", session_introduced=3),
        ],
        current_query="A former direct coworker just emailed asking for mentorship; they recently transitioned out of tech to law — does this fit?",
        required_behavior="No; the rule requires the mentee to still be active in tech.",
        invalid_behavior=["Accept any mentee", "Accept any former coworker", "Accept any tech outsider"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-pull-comm-rsvp-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's wedding-RSVP rule — three explicit narrowings: any → close-friends → close-friends + within-2-hours-travel",
        target_slot_id="weddingrsvp::v1", topic="wedding_rsvp_rule",
        versions=[
            VersionSpec(value="RSVP yes to any wedding invitation the user receives", polarity="constraint", session_introduced=1),
            VersionSpec(value="RSVP yes only to weddings of close friends in the user's inner circle", polarity="constraint", session_introduced=2),
            VersionSpec(value="RSVP yes only to weddings of close inner-circle friends AND only when the venue sits within two hours of travel from home", polarity="constraint", session_introduced=3),
        ],
        current_query="A close-circle friend's destination wedding in Greece arrived in the mail — does this fit?",
        required_behavior="No; the rule requires the venue to sit within two hours of home.",
        invalid_behavior=["RSVP to any wedding", "RSVP to far close-friend wedding", "RSVP to local outsider wedding"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi_version triple (4) — comm_boundary heavy
    _trip(_s(sample_id="p3-multi-trip-comm-tone-001", target_type="conceptual_stance", domain="work_communication",
        target_description="user's written-feedback tone — four versions: warm-with-emojis → formal-corporate → blunt-direct → praise-only-no-criticism",
        target_slot_id="tone::v1", topic="written_feedback_tone",
        versions=[
            VersionSpec(value="write team feedback in a warm tone with emoji punctuation and lots of enthusiasm markers", polarity="prefer", session_introduced=1),
            VersionSpec(value="write team feedback in a formal corporate tone with full sentences and no emojis", polarity="prefer", session_introduced=2),
            VersionSpec(value="write team feedback in a blunt direct tone with the issue stated up front and no padding", polarity="prefer", session_introduced=3),
            VersionSpec(value="write team feedback as praise-only celebration messages with no criticism at all", polarity="prefer", session_introduced=4),
        ],
        current_query="A direct report just shipped a launch with one major bug — how do I word the feedback?",
        required_behavior="Praise-only celebration of what shipped well, no critique of the bug.",
        invalid_behavior=["Use warm tone with emojis", "Use formal corporate tone", "Use blunt direct tone with the bug callout"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-comm-meet-001", target_type="procedural_constraint", domain="management",
        target_description="user's meeting-pace style — four versions: agenda-driven-strict → discussion-driven-loose → decision-driven-fast → silent-with-written-doc",
        target_slot_id="meetpace::v1", topic="meeting_pace_style",
        versions=[
            VersionSpec(value="run meetings tightly to the prepared agenda, marching through every item in order", polarity="constraint", session_introduced=1),
            VersionSpec(value="run meetings as loose open discussions, letting topics emerge organically without an agenda", polarity="constraint", session_introduced=2),
            VersionSpec(value="run meetings as fast decision-driven sessions, skipping discussion and ending the moment the call is made", polarity="constraint", session_introduced=3),
            VersionSpec(value="run meetings as silent reading sessions where the team reads a pre-written doc together for fifteen minutes before any talking", polarity="constraint", session_introduced=4),
        ],
        current_query="The team wants me to lead the next product review — what format do I run?",
        required_behavior="Pre-circulate a doc, open with fifteen minutes of silent reading, then discuss.",
        invalid_behavior=["Run agenda-driven", "Run discussion-driven loose", "Run fast decision-driven"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-comm-channel-001", target_type="object_preference", domain="work_communication",
        target_description="user's primary work-comm channel — four versions: Slack → Discord → Microsoft-Teams → email-only",
        target_slot_id="commchan::v1", topic="primary_work_comm_channel",
        versions=[
            VersionSpec(value="run primary work coordination on Slack with channels for every project", polarity="prefer", session_introduced=1),
            VersionSpec(value="run primary work coordination on Discord with voice rooms and topic channels", polarity="prefer", session_introduced=2),
            VersionSpec(value="run primary work coordination on Microsoft Teams with the company tenant", polarity="prefer", session_introduced=3),
            VersionSpec(value="run primary work coordination through email only, no chat tool at all", polarity="prefer", session_introduced=4),
        ],
        current_query="A teammate asked where to send me a quick async question — what do I tell them?",
        required_behavior="Tell them to use email only.",
        invalid_behavior=["Send via Slack", "Send via Discord", "Send via Microsoft Teams"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-comm-bday-001", target_type="conceptual_stance", domain="relationships",
        target_description="user's birthday-celebration approach — four versions: big-house-party → quiet-with-partner → solo-trip → no-celebration-at-all",
        target_slot_id="bday::v1", topic="own_birthday_celebration",
        versions=[
            VersionSpec(value="celebrate the user's own birthday with a thirty-person house party every year", polarity="prefer", session_introduced=1),
            VersionSpec(value="celebrate the user's own birthday with a quiet dinner alone with the partner at home", polarity="prefer", session_introduced=2),
            VersionSpec(value="celebrate the user's own birthday with a solo trip to a national park, no other people involved", polarity="prefer", session_introduced=3),
            VersionSpec(value="skip celebrating the user's own birthday entirely; treat it as a normal day", polarity="prefer", session_introduced=4),
        ],
        current_query="My birthday is in three weeks — what do I plan?",
        required_behavior="Plan nothing; treat the day as a normal day.",
        invalid_behavior=["Plan the house party", "Plan the quiet partner dinner", "Plan the solo park trip"],
        failure_patterns=["multi_version"], subtype="strong")),

    # gradual_narrowing (2)
    _drift(_s(sample_id="p3-drift-gn-comm-event-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's event-attendance — gradually narrowing without announcement: any → only-close-friends-host → only-close-friends-host + small-gatherings-only",
        target_slot_id="evgn::v1", topic="event_attendance_drift_rule",
        versions=[
            VersionSpec(value="attend any social event the user is invited to", polarity="constraint", session_introduced=1),
            VersionSpec(value="attend social events only when hosted by a close friend AND only when the gathering is fewer than ten people total", polarity="constraint", session_introduced=2),
        ],
        current_query="A close friend invited me to her thirty-person summer potluck next Saturday — go?",
        required_behavior="Pass; user attends only small gatherings hosted by close friends.",
        invalid_behavior=["Go to the thirty-person potluck"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-comm-mentor-001", target_type="interpersonal_boundary", domain="career",
        target_description="user's mentorship-time — gradually narrowing without announcement: anyone → former-coworkers → former-coworkers + within-2-years",
        target_slot_id="mentortime::v1", topic="mentorship_time_drift_rule",
        versions=[
            VersionSpec(value="offer mentorship hours to anyone who reaches out on LinkedIn", polarity="constraint", session_introduced=1),
            VersionSpec(value="offer mentorship hours only to people who once worked with the user directly AND only those who left the user's company within the last two years", polarity="constraint", session_introduced=2),
        ],
        current_query="A former direct coworker who left my old company eight years ago just emailed asking for mentorship — accept?",
        required_behavior="Pass; user offers mentorship only to former coworkers within the last two years.",
        invalid_behavior=["Accept the eight-years-out former coworker"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),
]
