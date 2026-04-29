"""Phase 3 batch AH — final push to N=1000.

Targets (after batch AG closed narrowing): -2 multi triple, -1
gradual_narrowing, -1 abandonment. Author 10 spines for safe cushion."""

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


PHASE3_BATCH_AH: list[Phase3GroupSpec] = [
    # multi_version triple (5) — mixed topics, non-object heavy
    _trip(_s(sample_id="p3-multi-trip-vacroute-001", target_type="object_preference", domain="travel",
        target_description="user's vacation route — four versions: solo-backpack-Asia → group-tour-Europe → cruise-Caribbean → road-trip-USA",
        target_slot_id="vacroute::v1", topic="annual_vacation_route",
        versions=[
            VersionSpec(value="take an annual solo backpacking trip across Southeast Asia for two weeks", polarity="prefer", session_introduced=1),
            VersionSpec(value="take an annual organized group tour through European capitals for two weeks", polarity="prefer", session_introduced=2),
            VersionSpec(value="take an annual cruise vacation through the Caribbean for ten days", polarity="prefer", session_introduced=3),
            VersionSpec(value="take an annual cross-country road trip across the United States by car for three weeks", polarity="prefer", session_introduced=4),
        ],
        current_query="A friend asked the user about this year's vacation plans — what's the answer?",
        required_behavior="A cross-country US road trip by car for three weeks.",
        invalid_behavior=["Solo backpacking in Southeast Asia", "Group tour through Europe", "Caribbean cruise"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-charity-001", target_type="conceptual_stance", domain="finance",
        target_description="user's giving philosophy — four versions: monthly-recurring-one-charity → annual-lump-sum-three-charities → time-not-money-volunteering → no-formal-giving-only-help-friends",
        target_slot_id="givephil::v1", topic="charitable_giving_philosophy",
        versions=[
            VersionSpec(value="give monthly recurring contributions to one chosen charity year-round", polarity="prefer", session_introduced=1),
            VersionSpec(value="give an annual lump-sum donation split across three chosen charities at year-end", polarity="prefer", session_introduced=2),
            VersionSpec(value="give time as volunteering hours rather than money for charitable engagement", polarity="prefer", session_introduced=3),
            VersionSpec(value="forego all formal charity giving and only help friends and family directly when needed", polarity="prefer", session_introduced=4),
        ],
        current_query="A nonprofit asked the user about a year-end donation pledge — what's the answer?",
        required_behavior="Decline; the user no longer makes formal donations and only helps friends and family directly.",
        invalid_behavior=["Pledge a monthly recurring", "Pledge a year-end lump sum split three ways", "Pledge volunteer hours"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-langlearn-001", target_type="procedural_constraint", domain="learning",
        target_description="user's language-learning approach — four versions: classroom-twice-week → solo-app-daily → tutor-hourly-weekly → immersion-trip-quarterly",
        target_slot_id="langlearn::v1", topic="language_learning_approach",
        versions=[
            VersionSpec(value="learn the target language in a twice-weekly classroom group at the community center", polarity="constraint", session_introduced=1),
            VersionSpec(value="learn the target language solo via the daily phone app fifteen minutes a day", polarity="constraint", session_introduced=2),
            VersionSpec(value="learn the target language via weekly one-on-one tutor sessions with a paid native speaker", polarity="constraint", session_introduced=3),
            VersionSpec(value="learn the target language only through quarterly immersion trips of a full week each", polarity="constraint", session_introduced=4),
        ],
        current_query="A friend asked the user how the language study is going these days — what's the answer?",
        required_behavior="Through quarterly week-long immersion trips, no other practice between trips.",
        invalid_behavior=["Tell them twice-weekly classroom", "Tell them daily app practice", "Tell them weekly tutor"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-decor-001", target_type="conceptual_stance", domain="home",
        target_description="user's home-decor philosophy — four versions: minimalist-white → maximalist-color → midcentury-warm-wood → industrial-concrete-steel",
        target_slot_id="decor::v1", topic="home_decor_philosophy",
        versions=[
            VersionSpec(value="decorate the apartment in minimalist white with no color and bare walls", polarity="prefer", session_introduced=1),
            VersionSpec(value="decorate the apartment in maximalist color with patterned wallpaper and gallery walls", polarity="prefer", session_introduced=2),
            VersionSpec(value="decorate the apartment in midcentury-modern with warm wood furniture and brass accents", polarity="prefer", session_introduced=3),
            VersionSpec(value="decorate the apartment in industrial style with exposed concrete walls and steel furniture", polarity="prefer", session_introduced=4),
        ],
        current_query="A friend dropped off a vintage teak credenza for the user's apartment — does it fit?",
        required_behavior="Pass; the apartment style is now industrial concrete-and-steel, not midcentury wood.",
        invalid_behavior=["Tell them it fits the minimalist white look", "Tell them it fits the maximalist look", "Tell them it fits the midcentury warm-wood look"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-coachstyle-001", target_type="procedural_constraint", domain="management",
        target_description="user's coaching style — four versions: socratic-questions → directive-feedback → role-play-mock → silent-listening",
        target_slot_id="coachst::v1", topic="coaching_style",
        versions=[
            VersionSpec(value="run direct-report coaching as Socratic questioning sessions where the report figures out the answer themselves", polarity="constraint", session_introduced=1),
            VersionSpec(value="run direct-report coaching as directive feedback sessions where the user states the issue and the prescribed change clearly", polarity="constraint", session_introduced=2),
            VersionSpec(value="run direct-report coaching as live role-play mock conversations rehearsing the difficult interactions", polarity="constraint", session_introduced=3),
            VersionSpec(value="run direct-report coaching as silent listening sessions where the user only validates and never offers any suggestion", polarity="constraint", session_introduced=4),
        ],
        current_query="A direct report came in for the next coaching session asking for advice — what does the user offer?",
        required_behavior="Listen silently and only validate; offer no advice or suggestion.",
        invalid_behavior=["Run Socratic questions", "Run directive feedback", "Run live role-play"],
        failure_patterns=["multi_version"], subtype="strong")),

    # gradual_narrowing (3)
    _drift(_s(sample_id="p3-drift-gn-cookbook-001", target_type="object_preference", domain="learning",
        target_description="user's cookbook-buy rule — gradually narrowing: any → vegetarian-only → vegetarian-only + single-region",
        target_slot_id="ckbk::v1", topic="cookbook_buy_drift",
        versions=[
            VersionSpec(value="buy any cookbook the user finds compelling at the bookshop", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only vegetarian-themed cookbooks AND only ones focused on a single regional cuisine, no pan-cuisine compilations", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a beautiful new pan-Mediterranean meatless cookbook — what now?",
        required_behavior="Pass; user buys only single-region vegetarian cookbooks.",
        invalid_behavior=["Buy the pan-Mediterranean cookbook"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-prodtool-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's productivity-app criteria — gradually narrowing: any → keyboard-first → keyboard-first + paid-tier",
        target_slot_id="prodtool::v1", topic="productivity_app_drift",
        versions=[
            VersionSpec(value="install any productivity app the user finds in the app store", polarity="prefer", session_introduced=1),
            VersionSpec(value="install only productivity apps with keyboard-first UX AND only paid-tier versions with no ads or freemium limits", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a free keyboard-driven note app the friend uses every day — what now?",
        required_behavior="Pass; user installs only paid-tier keyboard-first apps.",
        invalid_behavior=["Install the free keyboard-driven note app"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-eventgo-001", target_type="interpersonal_boundary", domain="career",
        target_description="user's industry-event attendance — gradually narrowing: any → invite-only-events → invite-only-events + with-prep-doc",
        target_slot_id="industry::v1", topic="industry_event_drift",
        versions=[
            VersionSpec(value="attend any industry event the user finds compelling on the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="attend industry events only when the access is invite-only AND only when the host distributes a prep doc to attendees beforehand", polarity="constraint", session_introduced=2),
        ],
        current_query="A friend forwarded an invite-only roundtable next week with no prep doc circulated — what now?",
        required_behavior="Pass; user attends only invite-only events that come with a prep doc.",
        invalid_behavior=["Accept the invite-only no-prep roundtable"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    # abandonment (2)
    _drift(_s(sample_id="p3-drift-aban-newsletter-003", target_type="procedural_constraint", domain="writing",
        target_description="user's monthly newsletter — abandoned after pivot to twitter-only, no replacement",
        target_slot_id="news3::v1", topic="monthly_newsletter_practice",
        versions=[
            VersionSpec(value="publish a monthly long-form newsletter on the personal Substack on the first Friday of each month", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop publishing the monthly Substack newsletter after pivoting communication to short Twitter threads only and never resume the long-form practice", polarity="constraint", session_introduced=2),
        ],
        current_query="A subscriber emailed asking when the next issue is coming — what does the user say?",
        required_behavior="Tell them the newsletter has been discontinued; communication is now Twitter threads only.",
        invalid_behavior=["Promise an issue this Friday"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-mentorrounds-001", target_type="interpersonal_boundary", domain="career",
        target_description="user's quarterly mentor sessions — abandoned after mentor relocated, no replacement",
        target_slot_id="mr::v1", topic="quarterly_mentor_session_practice",
        versions=[
            VersionSpec(value="hold a quarterly two-hour mentor session with the long-time professional mentor at the cafe in midtown", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop holding the quarterly mentor session after the mentor relocated cross-country and the in-person practice was retired without a replacement", polarity="constraint", session_introduced=2),
        ],
        current_query="It's the start of the new quarter and a friend asked the user about the mentor catch-up — what's the plan?",
        required_behavior="No catch-up; the quarterly mentor session has been abandoned.",
        invalid_behavior=["Schedule the quarterly mentor catch-up"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),
]
