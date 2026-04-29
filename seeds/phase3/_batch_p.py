"""Phase 3 batch P — 25 spines biased to multi_doublet, gradual_narrowing,
narrowing, communication_boundary topic, interpersonal_boundary target_type."""

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


PHASE3_BATCH_P: list[Phase3GroupSpec] = [
    # narrowing (5) — interpersonal_boundary heavy
    _trip(_s(sample_id="p3-narrow-friend-favor-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's rule for taking favor requests from friends — three explicit narrowings: any favor → in-person only → in-person + same-week notice",
        target_slot_id="friend_favor::v1", topic="friend_favor_rule",
        versions=[
            VersionSpec(value="agree to friend favors that come over text whenever they ask", polarity="constraint", session_introduced=1),
            VersionSpec(value="agree to friend favors only if asked face to face", polarity="constraint", session_introduced=2),
            VersionSpec(value="agree to friend favors only if asked face to face AND with at least one week of notice", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend just texted asking me to help them move this Saturday — agree?",
        required_behavior="Decline; the rule is face to face AND at least one week of notice.",
        invalid_behavior=["Agree because it came over text", "Agree on face-to-face alone", "Agree on one-week-notice alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-mentor-hours-001", target_type="interpersonal_boundary", domain="career",
        target_description="user's mentorship-time rule — three explicit narrowings: anyone → former coworkers → former coworkers within two years",
        target_slot_id="mentor_hours::v1", topic="mentorship_eligibility",
        versions=[
            VersionSpec(value="offer mentorship hours to anyone who reaches out on LinkedIn", polarity="constraint", session_introduced=1),
            VersionSpec(value="offer mentorship hours only to people who once worked with the user directly", polarity="constraint", session_introduced=2),
            VersionSpec(value="offer mentorship hours only to people who worked with the user directly AND within the last two years", polarity="constraint", session_introduced=3),
        ],
        current_query="A LinkedIn stranger asked for a mentorship slot citing my recent post — accept?",
        required_behavior="Decline; the rule is former direct coworkers AND within the last two years.",
        invalid_behavior=["Accept any LinkedIn ask", "Accept on direct-coworker alone", "Accept on within-two-years alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-late-night-text-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's late-night text rule — three explicit narrowings: anyone → close circle → close circle and only urgent",
        target_slot_id="late_night::v1", topic="late_night_text_rule",
        versions=[
            VersionSpec(value="reply to late-night texts from anyone in the contact list", polarity="constraint", session_introduced=1),
            VersionSpec(value="reply to late-night texts only from the user's close inner circle of five people", polarity="constraint", session_introduced=2),
            VersionSpec(value="reply to late-night texts only from the close inner circle of five AND only when the message is urgent", polarity="constraint", session_introduced=3),
        ],
        current_query="A close-circle friend just texted at 1am asking what podcast I listened to today — reply?",
        required_behavior="Wait until morning; the rule is close circle AND urgent.",
        invalid_behavior=["Reply because anyone is allowed", "Reply on close-circle alone", "Reply on urgency alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-side-gig-001", target_type="procedural_constraint", domain="career",
        target_description="user's side-gig acceptance rule — three explicit narrowings: any side gig → paid only → paid + under-ten-hours",
        target_slot_id="side_gig::v1", topic="side_gig_rule",
        versions=[
            VersionSpec(value="take side gigs whenever they sound interesting, paid or unpaid", polarity="constraint", session_introduced=1),
            VersionSpec(value="take side gigs only when they pay at market rate", polarity="constraint", session_introduced=2),
            VersionSpec(value="take side gigs only when they pay at market rate AND require under ten hours of total work", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend offered a paid side gig — design a small landing page over twenty hours — take it?",
        required_behavior="Decline; the rule is market-rate paid AND under ten hours of work.",
        invalid_behavior=["Take it because the topic is interesting", "Take it on paid alone", "Take it on under-ten-hours alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-podcast-guest-001", target_type="procedural_constraint", domain="media",
        target_description="user's podcast-guest acceptance rule — three explicit narrowings: any invite → recorded only → recorded + sent-questions",
        target_slot_id="podcast_guest::v1", topic="podcast_guest_rule",
        versions=[
            VersionSpec(value="accept any podcast guest invitation that arrives over email", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept podcast guest invitations only when the show records audio in advance, never live", polarity="constraint", session_introduced=2),
            VersionSpec(value="accept podcast guest invitations only when the show records in advance AND sends a question list at least three days ahead", polarity="constraint", session_introduced=3),
        ],
        current_query="A small podcast emailed asking me on as a guest, recorded next Tuesday with no question list yet — accept?",
        required_behavior="Decline; the rule is recorded-in-advance AND a question list at least three days ahead.",
        invalid_behavior=["Accept any invite", "Accept on recorded-in-advance alone", "Accept on a sent-question-list alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi_version triple (4) — heavy on procedural / interpersonal
    _trip(_s(sample_id="p3-multi-trip-coach-style-001", target_type="procedural_constraint", domain="career",
        target_description="user's job-coaching style — four versions: didactic-lecture → Socratic-questions → role-play-mock → written-feedback-only",
        target_slot_id="coach_style::v1", topic="coaching_style",
        versions=[
            VersionSpec(value="run job-coaching sessions as a didactic lecture with the user listening and taking notes", polarity="prefer", session_introduced=1),
            VersionSpec(value="run job-coaching sessions Socratic style, with the coach asking probing questions throughout", polarity="prefer", session_introduced=2),
            VersionSpec(value="run job-coaching sessions as live role-play interview practice", polarity="prefer", session_introduced=3),
            VersionSpec(value="receive written feedback only on a recorded mock interview, no live coaching", polarity="prefer", session_introduced=4),
        ],
        current_query="My coach asked whether I want to schedule another live mock interview Friday — what do I tell them?",
        required_behavior="Pass on the live mock; ask for written feedback only on a recorded mock instead.",
        invalid_behavior=["Schedule a didactic lecture", "Schedule a Socratic-questioning live session", "Schedule a live role-play mock"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-savings-vehicle-001", target_type="object_preference", domain="finance",
        target_description="user's savings vehicle — four versions: high-yield-savings → 6-month-Treasuries → laddered-CDs → I-bonds",
        target_slot_id="savings_vehicle::v1", topic="savings_vehicle",
        versions=[
            VersionSpec(value="park emergency savings in a high-yield savings account at the user's online bank", polarity="prefer", session_introduced=1),
            VersionSpec(value="park emergency savings in rolling six-month US Treasury bills", polarity="prefer", session_introduced=2),
            VersionSpec(value="park emergency savings in a five-rung laddered CD ladder at the credit union", polarity="prefer", session_introduced=3),
            VersionSpec(value="park emergency savings in Series I bonds bought directly through Treasury Direct", polarity="prefer", session_introduced=4),
        ],
        current_query="The CD ladder rung came due this week — what should I roll it into?",
        required_behavior="Roll the matured CD into Series I bonds via Treasury Direct.",
        invalid_behavior=["Move it to high-yield savings", "Move it to a six-month Treasury", "Roll it into another CD rung"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-meal-prep-001", target_type="procedural_constraint", domain="health",
        target_description="user's meal-prep approach — four versions: Sunday-batch-cook → Wednesday-mid-week-restock → Mon-Wed-Fri-cook-fresh → meal-delivery-service",
        target_slot_id="meal_prep::v1", topic="meal_prep_approach",
        versions=[
            VersionSpec(value="batch-cook all five weekday lunches on Sunday afternoon", polarity="constraint", session_introduced=1),
            VersionSpec(value="batch-cook lunches twice — Sunday and again on Wednesday — to keep meals fresh", polarity="constraint", session_introduced=2),
            VersionSpec(value="cook lunch fresh on Monday, Wednesday, and Friday mornings", polarity="constraint", session_introduced=3),
            VersionSpec(value="subscribe to a chef-prepared meal-delivery service and skip home meal prep entirely", polarity="constraint", session_introduced=4),
        ],
        current_query="It is Sunday afternoon — should I start prepping lunches for the week?",
        required_behavior="No prep; meals come from the chef-prepared delivery service now.",
        invalid_behavior=["Batch-cook all five lunches", "Batch-cook for half the week", "Cook fresh Monday morning"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-team-1on1-001", target_type="procedural_constraint", domain="management",
        target_description="user's 1:1 cadence — four versions: weekly-30 → biweekly-45 → weekly-60-deep-dive → monthly-skip-level-only",
        target_slot_id="team_1on1::v1", topic="team_one_on_one_cadence",
        versions=[
            VersionSpec(value="hold team 1:1s every week for thirty minutes per direct report", polarity="constraint", session_introduced=1),
            VersionSpec(value="hold team 1:1s every other week for forty-five minutes per direct report", polarity="constraint", session_introduced=2),
            VersionSpec(value="hold team 1:1s every week for sixty minutes as deep-dive working sessions", polarity="constraint", session_introduced=3),
            VersionSpec(value="skip 1:1s with direct reports entirely and run only monthly skip-level meetings with the wider team", polarity="constraint", session_introduced=4),
        ],
        current_query="My calendar is asking me to confirm next week's 30-minute 1:1 with one of my reports — confirm it?",
        required_behavior="Cancel the 1:1; the cadence is monthly skip-levels only now.",
        invalid_behavior=["Confirm the weekly thirty", "Confirm a biweekly forty-five", "Confirm a weekly sixty-minute deep dive"],
        failure_patterns=["multi_version"], subtype="strong")),

    # multi_version doublet (8) — heavy underfill
    _doub(_s(sample_id="p3-multi-doub-resume-format-001", target_type="object_preference", domain="career",
        target_description="user's resume format — chronological → skills-based functional",
        target_slot_id="resume::v1", topic="resume_format",
        versions=[
            VersionSpec(value="use a reverse-chronological resume listing roles by date with bullet accomplishments", polarity="prefer", session_introduced=1),
            VersionSpec(value="use a skills-based functional resume that groups bullets under skill clusters instead of dates", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend offered to review my resume for the Friday application — which version do I send them?",
        required_behavior="Send the skills-based functional version.",
        invalid_behavior=["Send the chronological version"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-pet-feeder-001", target_type="object_preference", domain="home",
        target_description="user's cat-feeding approach — manual two-meals → smart auto-feeder",
        target_slot_id="cat_feed::v1", topic="cat_feeding_approach",
        versions=[
            VersionSpec(value="feed the cat manually twice a day at 7am and 6pm with measured wet-food cups", polarity="prefer", session_introduced=1),
            VersionSpec(value="rely on a smart auto-feeder that dispenses dry food on a programmed schedule", polarity="prefer", session_introduced=2),
        ],
        current_query="It is 6pm — should I open a wet-food can for the cat?",
        required_behavior="No manual meal; the smart auto-feeder handles feeding now.",
        invalid_behavior=["Open the wet-food can manually"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-status-update-001", target_type="procedural_constraint", domain="management",
        target_description="user's status-update format — Friday-written-summary → Monday-standup-only",
        target_slot_id="status::v1", topic="status_update_format",
        versions=[
            VersionSpec(value="post a written status summary every Friday afternoon in the team channel", polarity="constraint", session_introduced=1),
            VersionSpec(value="give status updates only verbally in the Monday standup, no written summary", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Friday afternoon — should I post the written status summary in the team channel?",
        required_behavior="No written post; status comes only from the Monday standup now.",
        invalid_behavior=["Post the written status summary"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-essay-style-001", target_type="conceptual_stance", domain="writing",
        target_description="user's essay style — long-form-narrative → punchy-listicle",
        target_slot_id="essay_style::v1", topic="essay_style",
        versions=[
            VersionSpec(value="write blog posts as long-form narrative essays of two thousand words", polarity="prefer", session_introduced=1),
            VersionSpec(value="write blog posts as punchy listicles of seven to nine numbered points each", polarity="prefer", session_introduced=2),
        ],
        current_query="I drafted a 2000-word narrative on remote work — should I publish as is?",
        required_behavior="Reformat into a punchy listicle of seven to nine numbered points before publishing.",
        invalid_behavior=["Publish the long-form narrative"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-bday-gift-001", target_type="object_preference", domain="relationships",
        target_description="user's birthday-gift approach for friends — handwritten-card-only → curated-experience-gift",
        target_slot_id="bday_gift::v1", topic="birthday_gift_approach",
        versions=[
            VersionSpec(value="give friends a handwritten card and nothing else for birthdays", polarity="prefer", session_introduced=1),
            VersionSpec(value="give friends a curated experience gift such as a class or concert ticket for birthdays", polarity="prefer", session_introduced=2),
        ],
        current_query="My closest friend's birthday is next week — what should I plan as the gift?",
        required_behavior="Plan a curated experience gift such as a class or concert ticket.",
        invalid_behavior=["Send a handwritten card alone"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-bug-tracker-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's bug-tracking tool — GitHub-Issues → Linear",
        target_slot_id="bug_tracker::v1", topic="bug_tracker_tool",
        versions=[
            VersionSpec(value="track engineering bugs in GitHub Issues attached to each repository", polarity="prefer", session_introduced=1),
            VersionSpec(value="track engineering bugs in Linear, syncing them to GitHub only as code links", polarity="prefer", session_introduced=2),
        ],
        current_query="My report just found a regression — where do I file the bug?",
        required_behavior="File the bug in Linear.",
        invalid_behavior=["File the bug in GitHub Issues"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-volunteer-001", target_type="interpersonal_boundary", domain="community",
        target_description="user's volunteering — weekly-soup-kitchen-shift → quarterly-board-membership",
        target_slot_id="volunteer::v1", topic="volunteering_commitment",
        versions=[
            VersionSpec(value="volunteer with the local soup kitchen one Saturday morning every week", polarity="constraint", session_introduced=1),
            VersionSpec(value="volunteer by serving on the nonprofit's quarterly board of directors instead", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday morning — should I head to the soup kitchen for my shift?",
        required_behavior="Skip the shift; commitment is the quarterly board role now.",
        invalid_behavior=["Head to the soup kitchen shift"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-bookclub-001", target_type="conceptual_stance", domain="learning",
        target_description="user's book-club picks — contemporary-fiction-only → classics-of-philosophy",
        target_slot_id="bookclub::v1", topic="book_club_picks",
        versions=[
            VersionSpec(value="pick contemporary fiction novels published in the last five years for the book club", polarity="prefer", session_introduced=1),
            VersionSpec(value="pick classics of Western philosophy for the book club, no fiction", polarity="prefer", session_introduced=2),
        ],
        current_query="The club asked me to suggest next month's pick — what do I propose?",
        required_behavior="Propose a classic of Western philosophy.",
        invalid_behavior=["Propose a contemporary fiction novel"],
        failure_patterns=["multi_version"], subtype="strong")),

    # explicit_replacement (4) — interpersonal_boundary + procedural heavy
    _trip(_s(sample_id="p3-explicit-meeting-host-001", target_type="procedural_constraint", domain="management",
        target_description="user's meeting-host preference — explicitly replaces zoom with google-meet",
        target_slot_id="meet_host::v1", topic="meeting_host_tool",
        versions=[
            VersionSpec(value="host all team meetings on Zoom with the company recording feature on", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget Zoom — host all team meetings on Google Meet with the built-in recording", polarity="prefer", session_introduced=2),
        ],
        current_query="My EA asked which calendar link to send for tomorrow's all-hands — what do I tell them?",
        required_behavior="Send the Google Meet link.",
        invalid_behavior=["Send a Zoom link"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-rsvp-rule-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's RSVP rule — explicitly replaces yes-by-default with no-by-default",
        target_slot_id="rsvp::v1", topic="rsvp_rule",
        versions=[
            VersionSpec(value="say yes to social invitations by default and only decline when there is a hard conflict", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget the yes-by-default rule — say no to social invitations by default and only accept when the user truly wants to go", polarity="constraint", session_introduced=2),
        ],
        current_query="A coworker invited me to a Friday happy hour — how do I respond?",
        required_behavior="Decline by default unless the user truly wants to attend.",
        invalid_behavior=["Accept by default"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-feedback-tone-001", target_type="conceptual_stance", domain="management",
        target_description="user's feedback tone — explicitly replaces sandwich with direct-clear",
        target_slot_id="feedback_tone::v1", topic="feedback_tone",
        versions=[
            VersionSpec(value="give written feedback in a praise-criticism-praise sandwich format", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the sandwich — give written feedback as a direct clear statement of the issue first, no padding", polarity="prefer", session_introduced=2),
        ],
        current_query="I am drafting feedback for my report's project review — how do I open it?",
        required_behavior="Open with a direct clear statement of the issue, no padding.",
        invalid_behavior=["Open with praise to soften the criticism"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-airport-arrival-001", target_type="procedural_constraint", domain="travel",
        target_description="user's airport-arrival rule — explicitly replaces 90-min-buffer with 3-hour-buffer",
        target_slot_id="airport::v1", topic="airport_arrival_buffer",
        versions=[
            VersionSpec(value="arrive at the airport ninety minutes before any domestic flight", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget the ninety-minute buffer — arrive at the airport three hours before any domestic flight", polarity="constraint", session_introduced=2),
        ],
        current_query="My domestic flight is at 11am Wednesday — what time do I leave for the airport?",
        required_behavior="Leave so I arrive at the airport three hours before, around 8am.",
        invalid_behavior=["Leave so I arrive ninety minutes before"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    # implicit_drift / repeated_use (2)
    _drift(_s(sample_id="p3-drift-ru-language-app-001", target_type="object_preference", domain="learning",
        target_description="user's language-learning app — old Duolingo gradually replaced by Anki SRS reviews user actually does daily",
        target_slot_id="lang_app::v1", topic="language_learning_app",
        versions=[
            VersionSpec(value="use Duolingo daily for fifteen minutes to learn Spanish", polarity="prefer", session_introduced=1),
            VersionSpec(value="use Anki spaced-repetition decks daily for Spanish vocabulary review", polarity="prefer", session_introduced=2),
        ],
        current_query="My streak app reminded me about Duolingo — should I open it for today's lesson?",
        required_behavior="Skip Duolingo; the daily Anki SRS review is what the user actually does now.",
        invalid_behavior=["Open Duolingo for the daily lesson"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-commute-001", target_type="procedural_constraint", domain="travel",
        target_description="user's commute mode — old subway gradually replaced by daily bike commute user logs miles for",
        target_slot_id="commute::v1", topic="commute_mode",
        versions=[
            VersionSpec(value="commute to the office on the F train every weekday morning", polarity="constraint", session_introduced=1),
            VersionSpec(value="commute to the office by bike along the river path every weekday morning", polarity="constraint", session_introduced=2),
        ],
        current_query="The MTA just texted about F-train weekend service changes — does it affect my commute?",
        required_behavior="No effect; the user bikes the river path to the office now.",
        invalid_behavior=["Treat the F-train change as relevant to my commute"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    # implicit_drift / abandonment (1)
    _drift(_s(sample_id="p3-drift-aban-vlog-001", target_type="procedural_constraint", domain="media",
        target_description="user's weekly YouTube vlog — abandoned after camera-broken session, no replacement",
        target_slot_id="vlog::v1", topic="weekly_vlog_practice",
        versions=[
            VersionSpec(value="film a weekly fifteen-minute YouTube vlog every Sunday night", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop filming the weekly vlog after the camera broke and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday night — am I shooting the vlog tonight?",
        required_behavior="No vlog; the weekly vlog practice has been abandoned.",
        invalid_behavior=["Shoot the weekly vlog tonight"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # implicit_drift / gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-gn-investing-001", target_type="object_preference", domain="finance",
        target_description="user's stock-buy criteria — gradually narrowing without announcement: any-S&P-500 → only-with-positive-FCF → only-with-positive-FCF-and-under-20-PE",
        target_slot_id="stock_buy::v1", topic="stock_buy_criteria",
        versions=[
            VersionSpec(value="buy any S&P 500 stock when adding to the brokerage account", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy S&P 500 stocks only when free cash flow is positive AND the price-to-earnings ratio is under 20", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended an S&P 500 name with negative FCF — buy it for the brokerage?",
        required_behavior="Pass; the user buys only when free cash flow is positive AND PE is under 20.",
        invalid_behavior=["Buy it because it is in the S&P 500"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),
]
