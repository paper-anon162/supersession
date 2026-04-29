"""Phase 3 batch W — 25 spines, drift + doublet heavy."""

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


PHASE3_BATCH_W: list[Phase3GroupSpec] = [
    # multi_version doublet (8)
    _doub(_s(sample_id="p3-multi-doub-coffee-grind-001", target_type="object_preference", domain="food",
        target_description="user's coffee-grind setting — fine-espresso → coarse-french-press",
        target_slot_id="grind::v1", topic="coffee_grind_setting",
        versions=[
            VersionSpec(value="grind beans on the espresso-fine setting at the kitchen grinder for daily coffee", polarity="prefer", session_introduced=1),
            VersionSpec(value="grind beans on the coarse French-press setting at the kitchen grinder for daily coffee instead", polarity="prefer", session_introduced=2),
        ],
        current_query="It is morning — what setting do I dial the grinder to for the daily beans?",
        required_behavior="Dial it to the coarse French-press setting.",
        invalid_behavior=["Dial to the espresso-fine setting"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-laundry-deterg-001", target_type="object_preference", domain="home",
        target_description="user's laundry detergent — Tide-Pods → unscented-Seventh-Generation",
        target_slot_id="detergent::v1", topic="laundry_detergent",
        versions=[
            VersionSpec(value="wash all laundry loads with Tide Pods in the Original scent", polarity="prefer", session_introduced=1),
            VersionSpec(value="wash all laundry loads with unscented Seventh Generation liquid detergent instead", polarity="prefer", session_introduced=2),
        ],
        current_query="The detergent shelf is empty — what do I add to the grocery list?",
        required_behavior="Add unscented Seventh Generation liquid detergent.",
        invalid_behavior=["Add Tide Pods"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-running-pace-001", target_type="procedural_constraint", domain="health",
        target_description="user's running pace strategy — even-pace → negative-split",
        target_slot_id="run_pace::v1", topic="running_pace_strategy",
        versions=[
            VersionSpec(value="run all training miles at the same even pace per mile, no acceleration", polarity="constraint", session_introduced=1),
            VersionSpec(value="run training miles at a negative split, starting easier and finishing 30 seconds per mile faster", polarity="constraint", session_introduced=2),
        ],
        current_query="I am about to head out for a five-mile training run — what pace strategy do I use?",
        required_behavior="Negative split: easier start, finish 30 seconds per mile faster.",
        invalid_behavior=["Run all five miles at one even pace"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-resume-review-001", target_type="procedural_constraint", domain="career",
        target_description="user's resume review process — peer-feedback-only → professional-coach-paid",
        target_slot_id="resume_review::v1", topic="resume_review_process",
        versions=[
            VersionSpec(value="get resume feedback only from peer engineers via Slack DMs, no paid services", polarity="constraint", session_introduced=1),
            VersionSpec(value="get resume feedback only from a paid professional career coach with hourly sessions instead of peers", polarity="constraint", session_introduced=2),
        ],
        current_query="I want to refresh my resume this weekend — who do I send the latest version to?",
        required_behavior="Send to the paid professional career coach for an hourly session.",
        invalid_behavior=["Send via Slack DM to peer engineers"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-photo-share-001", target_type="object_preference", domain="relationships",
        target_description="user's family photo channel — group-text-thread → private-iCloud-shared-album",
        target_slot_id="photo_chan::v1", topic="family_photo_share_channel",
        versions=[
            VersionSpec(value="share family photos in the group text thread that includes parents and siblings", polarity="prefer", session_introduced=1),
            VersionSpec(value="share family photos via a private iCloud shared album invite link to parents and siblings instead of the group text", polarity="prefer", session_introduced=2),
        ],
        current_query="I just took photos at the family dinner tonight — where do I send them?",
        required_behavior="Send via the private iCloud shared album.",
        invalid_behavior=["Send in the group text thread"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-music-prac-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's guitar practice — daily-30-min-scales → twice-weekly-1-hour-songs",
        target_slot_id="guitar::v1", topic="guitar_practice_routine",
        versions=[
            VersionSpec(value="practice guitar daily for thirty minutes drilling scales and arpeggios", polarity="constraint", session_introduced=1),
            VersionSpec(value="practice guitar twice a week for one hour, working through full songs start to finish, no scales", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Wednesday evening — am I sitting down for thirty minutes of scale practice?",
        required_behavior="No daily scales; practice is twice-weekly hour-long song work now.",
        invalid_behavior=["Sit down for thirty minutes of scales"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-team-roadmap-001", target_type="object_preference", domain="management",
        target_description="user's team roadmap document — Notion-table → Linear-cycles",
        target_slot_id="roadmap::v1", topic="team_roadmap_format",
        versions=[
            VersionSpec(value="track the engineering team roadmap in a Notion table with columns for status and owner", polarity="prefer", session_introduced=1),
            VersionSpec(value="track the engineering team roadmap in Linear cycles with the issue board view instead of Notion", polarity="prefer", session_introduced=2),
        ],
        current_query="A skip-level asked where to find the team's roadmap — point them at which one?",
        required_behavior="Point them at the Linear cycles board.",
        invalid_behavior=["Point them at the Notion table"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-vacation-pack-001", target_type="procedural_constraint", domain="travel",
        target_description="user's vacation packing approach — checked-bag-with-shoes → carry-on-only",
        target_slot_id="pack::v1", topic="vacation_packing_approach",
        versions=[
            VersionSpec(value="check a 50-pound suitcase with multiple pairs of shoes for any vacation longer than a weekend", polarity="constraint", session_introduced=1),
            VersionSpec(value="travel with carry-on-only and one pair of shoes for any vacation, regardless of length", polarity="constraint", session_introduced=2),
        ],
        current_query="My ten-day Italy trip is in two weeks — should I plan to check a suitcase?",
        required_behavior="No checked bag; carry-on only with one pair of shoes.",
        invalid_behavior=["Plan to check a 50-pound suitcase"],
        failure_patterns=["multi_version"], subtype="strong")),

    # implicit_drift / repeated_use (4)
    _drift(_s(sample_id="p3-drift-ru-passion-001", target_type="object_preference", domain="learning",
        target_description="user's evening hobby — old language-learning gradually replaced by chess study user does daily",
        target_slot_id="hobby::v1", topic="evening_hobby",
        versions=[
            VersionSpec(value="study Spanish on Duolingo every evening for thirty minutes after dinner", polarity="prefer", session_introduced=1),
            VersionSpec(value="study chess openings on Lichess every evening for forty-five minutes after dinner", polarity="prefer", session_introduced=2),
        ],
        current_query="It is 8pm — which app do I open for the evening hobby session?",
        required_behavior="Open Lichess for chess openings study.",
        invalid_behavior=["Open Duolingo for Spanish"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-shopping-list-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's shopping list app — old paper-list gradually replaced by Bring shared list user uses weekly",
        target_slot_id="shop_list::v1", topic="shopping_list_method",
        versions=[
            VersionSpec(value="keep the weekly shopping list on a paper notepad on the fridge", polarity="prefer", session_introduced=1),
            VersionSpec(value="keep the weekly shopping list in the Bring app shared with the partner on phones", polarity="prefer", session_introduced=2),
        ],
        current_query="I want to add eggs and milk to the shopping list — where do I write?",
        required_behavior="Add them in the Bring app.",
        invalid_behavior=["Write on the paper notepad on the fridge"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-bike-001", target_type="object_preference", domain="health",
        target_description="user's exercise bike — old Peloton gradually replaced by outdoor road bike user rides daily",
        target_slot_id="bike::v1", topic="primary_cycling_practice",
        versions=[
            VersionSpec(value="take the Peloton spin class for cardio in the home gym every morning", polarity="prefer", session_introduced=1),
            VersionSpec(value="ride the outdoor road bike on the river path for cardio every morning instead of Peloton", polarity="prefer", session_introduced=2),
        ],
        current_query="It is 6am and the cardio slot is open — am I hopping on the Peloton?",
        required_behavior="No; ride the outdoor road bike on the river path.",
        invalid_behavior=["Hop on the Peloton spin class"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-team-comm-001", target_type="object_preference", domain="management",
        target_description="user's team coordination — old standup-meetings gradually replaced by daily-Loom-videos user records every workday",
        target_slot_id="team_comm::v1", topic="team_coordination_format",
        versions=[
            VersionSpec(value="run team coordination through a daily 9am video-call standup for fifteen minutes", polarity="constraint", session_introduced=1),
            VersionSpec(value="run team coordination through a daily Loom video the manager records and posts in Slack each morning", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 9am — am I starting the standup zoom?",
        required_behavior="No; record the daily Loom and post in Slack.",
        invalid_behavior=["Start the standup zoom"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    # implicit_drift / abandonment (3)
    _drift(_s(sample_id="p3-drift-aban-language-001", target_type="procedural_constraint", domain="learning",
        target_description="user's daily language tutor session — abandoned after job change, no replacement",
        target_slot_id="lang_tutor::v1", topic="daily_language_tutor_practice",
        versions=[
            VersionSpec(value="run a daily one-hour Italian tutor video session every weekday at 7pm", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop running the daily Italian tutor session after the job change made evenings too busy and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 7pm Tuesday — am I joining the Italian tutor video call?",
        required_behavior="No; the daily Italian tutor session has been abandoned.",
        invalid_behavior=["Join the Italian tutor video call"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-charity-001", target_type="procedural_constraint", domain="finance",
        target_description="user's monthly charity giving — abandoned after layoff, no replacement",
        target_slot_id="charity_give::v1", topic="monthly_charity_giving_practice",
        versions=[
            VersionSpec(value="set up a recurring 200-dollar monthly donation to a single charity on the first of each month", polarity="constraint", session_introduced=1),
            VersionSpec(value="cancel the recurring monthly donation after the layoff and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the first of the month and the bank notification arrived — confirm the charity transfer?",
        required_behavior="No; the recurring monthly charity donation has been abandoned.",
        invalid_behavior=["Confirm the charity transfer"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-yoga-class-001", target_type="procedural_constraint", domain="health",
        target_description="user's weekly yoga class — abandoned after instructor moved studios, no replacement",
        target_slot_id="yoga_class::v1", topic="weekly_yoga_class_practice",
        versions=[
            VersionSpec(value="attend the Saturday-morning vinyasa flow yoga class with the regular instructor every week", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop attending the Saturday yoga class after the instructor moved to a different studio and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I rolling up the yoga mat for class?",
        required_behavior="No; the Saturday yoga class has been abandoned.",
        invalid_behavior=["Roll up the yoga mat for class"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # implicit_drift / gradual_narrowing (3)
    _drift(_s(sample_id="p3-drift-gn-newsread-001", target_type="object_preference", domain="learning",
        target_description="user's news reading — gradually narrowing without announcement: any source → only-finance-publications → only-finance-publications + paid-subscription",
        target_slot_id="news_read::v1", topic="news_reading_criteria",
        versions=[
            VersionSpec(value="read news from any source the user finds interesting in the daily feed", polarity="prefer", session_introduced=1),
            VersionSpec(value="read news only from finance-focused publications AND only ones the user pays a paid subscription to", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a free finance newsletter on Substack — add it to the daily feed?",
        required_behavior="Pass; user reads only finance publications with paid subscriptions.",
        invalid_behavior=["Add the free finance newsletter"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-restaurant-002", target_type="object_preference", domain="food",
        target_description="user's lunch out criteria — gradually narrowing without announcement: any cuisine → vegetarian-only → vegetarian + within-15-min-walk",
        target_slot_id="lunch_out::v1", topic="lunch_out_criteria",
        versions=[
            VersionSpec(value="grab lunch at any restaurant the user feels like for weekday lunch breaks", polarity="prefer", session_introduced=1),
            VersionSpec(value="grab lunch only at vegetarian restaurants AND only ones within a fifteen-minute walk of the office", polarity="prefer", session_introduced=2),
        ],
        current_query="A coworker invited me to a vegetarian place 30 minutes' walk away for today's lunch — go?",
        required_behavior="Pass; user does lunch only at vegetarian restaurants within 15-min walk.",
        invalid_behavior=["Go to the 30-minute walk vegetarian place"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-meeting-001", target_type="procedural_constraint", domain="management",
        target_description="user's external-meeting acceptance — gradually narrowing without announcement: any meeting → only-with-existing-clients → only-with-existing-clients + on-Tuesdays-only",
        target_slot_id="ext_meet::v1", topic="external_meeting_acceptance",
        versions=[
            VersionSpec(value="accept any external meeting request that fits the user's calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept external meetings only with existing client contacts AND only schedule them on Tuesdays", polarity="constraint", session_introduced=2),
        ],
        current_query="A new prospect just emailed asking for a Tuesday meeting next week — accept?",
        required_behavior="Pass; user takes external meetings only with existing clients on Tuesdays.",
        invalid_behavior=["Accept the new prospect's Tuesday meeting"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    # explicit_replacement (5)
    _trip(_s(sample_id="p3-explicit-feedback-cadence-001", target_type="procedural_constraint", domain="management",
        target_description="user's feedback cadence — explicitly replaces yearly-review with monthly-1on1-feedback",
        target_slot_id="feedback_cad::v1", topic="feedback_cadence",
        versions=[
            VersionSpec(value="give direct reports formal feedback once a year in the annual review meeting", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget the yearly review — give direct reports written feedback in the monthly 1:1 doc instead", polarity="constraint", session_introduced=2),
        ],
        current_query="It is the end of the calendar year — should I schedule annual review meetings?",
        required_behavior="No; feedback comes through the monthly 1:1 docs now.",
        invalid_behavior=["Schedule annual review meetings"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-coffee-bean-001", target_type="object_preference", domain="food",
        target_description="user's coffee bean — explicitly replaces Stumptown with Onyx-Coffee",
        target_slot_id="coffee_bean::v1", topic="weekly_coffee_bean",
        versions=[
            VersionSpec(value="buy a weekly bag of Stumptown Hair Bender beans for daily coffee at home", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget Stumptown — buy a weekly bag of Onyx Coffee Monarch beans for daily coffee at home instead", polarity="prefer", session_introduced=2),
        ],
        current_query="The bean shelf is empty — what do I order for next week's coffee?",
        required_behavior="Order a bag of Onyx Coffee Monarch beans.",
        invalid_behavior=["Order a bag of Stumptown Hair Bender beans"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-document-tool-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's document tool — explicitly replaces Google-Docs with Obsidian-Publish",
        target_slot_id="doc_tool::v1", topic="document_authoring_tool",
        versions=[
            VersionSpec(value="write all personal documents in Google Docs with the comment threading on", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget Google Docs — write all personal documents in Obsidian Publish with markdown source instead", polarity="prefer", session_introduced=2),
        ],
        current_query="A teammate asked where to find my latest writeup — point them at which one?",
        required_behavior="Point them at the Obsidian Publish page.",
        invalid_behavior=["Point them at the Google Doc"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-monitoring-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's app monitoring — explicitly replaces Datadog with Honeycomb",
        target_slot_id="monitor_tool::v1", topic="app_monitoring_tool",
        versions=[
            VersionSpec(value="monitor production with Datadog using the agent-based collection on every host", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget Datadog — monitor production with Honeycomb using OpenTelemetry instrumentation instead", polarity="prefer", session_introduced=2),
        ],
        current_query="A teammate asked where to check this morning's latency spike — point them at which dashboard?",
        required_behavior="Point them at the Honeycomb dashboard.",
        invalid_behavior=["Point them at the Datadog dashboard"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-bday-celeb-001", target_type="conceptual_stance", domain="relationships",
        target_description="user's own-birthday celebration — explicitly replaces dinner-with-large-group with weekend-getaway-with-partner",
        target_slot_id="bday_celeb::v1", topic="own_birthday_celebration",
        versions=[
            VersionSpec(value="celebrate the user's birthday every year with a dinner at a fancy restaurant inviting eight or more friends", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the big group dinner — celebrate the user's birthday every year with a weekend getaway alone with the partner instead", polarity="prefer", session_introduced=2),
        ],
        current_query="My birthday is in three weeks — should I send out the dinner invites to the eight friends?",
        required_behavior="No invites; plan a weekend getaway alone with the partner.",
        invalid_behavior=["Send out the dinner invites to the eight friends"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    # narrowing (2)
    _trip(_s(sample_id="p3-narrow-conf-talk-002", target_type="procedural_constraint", domain="career",
        target_description="user's conference-talk acceptance rule — three explicit narrowings: any → keynote-only → keynote + one-track-conferences",
        target_slot_id="conf_talk::v1", topic="conference_talk_acceptance_rule",
        versions=[
            VersionSpec(value="accept any conference talk invitation that fits the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept conference talk invitations only when the slot is a keynote", polarity="constraint", session_introduced=2),
            VersionSpec(value="accept conference talk invitations only when the slot is a keynote AND the conference is single-track with no parallel sessions", polarity="constraint", session_introduced=3),
        ],
        current_query="A multi-track conference offered me a keynote slot — accept?",
        required_behavior="Pass; the rule is keynote AND single-track conference.",
        invalid_behavior=["Accept any invite", "Accept any keynote", "Accept a single-track non-keynote slot"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-bookbuy-001", target_type="object_preference", domain="learning",
        target_description="user's book-buy rule — three explicit narrowings: any → nonfiction-only → nonfiction-only + recommended-by-trusted-person",
        target_slot_id="bookbuy::v1", topic="book_buy_rule",
        versions=[
            VersionSpec(value="buy any book that catches the user's eye in a bookshop or online listing", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only nonfiction books, no fiction or memoir purchases", polarity="prefer", session_introduced=2),
            VersionSpec(value="buy only nonfiction books AND only ones recommended directly by a trusted friend or mentor", polarity="prefer", session_introduced=3),
        ],
        current_query="A bookshop window display has a fascinating new nonfiction book on neuroscience — buy it?",
        required_behavior="Pass; the rule is nonfiction AND recommended by a trusted friend or mentor.",
        invalid_behavior=["Buy any catchy book", "Buy any nonfiction", "Buy a fiction recommendation from a trusted friend"],
        failure_patterns=["narrowing"], subtype="multi_step")),
]
