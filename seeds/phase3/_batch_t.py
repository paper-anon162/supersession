"""Phase 3 batch T — 25 spines biased to multi_doublet, narrowing,
gradual_narrowing, drift, communication_boundary topic, interpersonal_boundary."""

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


PHASE3_BATCH_T: list[Phase3GroupSpec] = [
    # narrowing (5)
    _trip(_s(sample_id="p3-narrow-cocktail-001", target_type="object_preference", domain="food",
        target_description="user's home-cocktail rule — three explicit narrowings: any spirit → mezcal-base → mezcal + smoked-citrus",
        target_slot_id="cocktail::v1", topic="home_cocktail_rule",
        versions=[
            VersionSpec(value="mix any cocktail the user feels like making after dinner", polarity="prefer", session_introduced=1),
            VersionSpec(value="mix only mezcal-base cocktails after dinner, no other spirits", polarity="prefer", session_introduced=2),
            VersionSpec(value="mix only mezcal-base cocktails AND only with a smoked-citrus garnish after dinner", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend dropped off a bottle of bourbon — should I shake an Old Fashioned tonight?",
        required_behavior="Pass; the rule is mezcal-base AND smoked-citrus garnish.",
        invalid_behavior=["Mix any spirit", "Mix any mezcal cocktail", "Mix bourbon with smoked citrus"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-rsvp-event-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's social-event RSVP — three explicit narrowings: any → small-gathering → small-gathering + close-friends-host",
        target_slot_id="event_rsvp::v1", topic="social_event_rsvp_rule",
        versions=[
            VersionSpec(value="say yes to any social event invitation that fits the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="say yes only to small gatherings of fewer than ten people", polarity="constraint", session_introduced=2),
            VersionSpec(value="say yes only to small gatherings of fewer than ten people hosted by close friends", polarity="constraint", session_introduced=3),
        ],
        current_query="A coworker invited me to a six-person dinner party at her apartment — RSVP yes?",
        required_behavior="Decline; the rule is small gathering AND host is a close friend.",
        invalid_behavior=["RSVP yes to any event", "RSVP yes to any small gathering", "RSVP yes to a close-friend large party"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-airbnb-stay-001", target_type="procedural_constraint", domain="travel",
        target_description="user's Airbnb-booking rule — three explicit narrowings: any → entire-place → entire-place + super-host",
        target_slot_id="airbnb::v1", topic="airbnb_booking_rule",
        versions=[
            VersionSpec(value="book any Airbnb listing that fits the dates and budget", polarity="constraint", session_introduced=1),
            VersionSpec(value="book only entire-place Airbnb listings, never private-room or shared-room rentals", polarity="constraint", session_introduced=2),
            VersionSpec(value="book only entire-place Airbnb listings hosted by Super-host badge holders", polarity="constraint", session_introduced=3),
        ],
        current_query="An entire-place listing in Lisbon at a great price has a regular host with no Super-host badge — book?",
        required_behavior="Pass; the rule is entire-place AND Super-host badge.",
        invalid_behavior=["Book any listing", "Book any entire-place listing", "Book a private-room Super-host"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-investing-stock-001", target_type="object_preference", domain="finance",
        target_description="user's stock-pick rule — three explicit narrowings: any sector → tech-only → tech-only + revenue-over-1B",
        target_slot_id="stock_pick::v1", topic="stock_pick_rule",
        versions=[
            VersionSpec(value="buy any S&P 500 stock the user finds interesting for the brokerage", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only technology-sector S&P 500 stocks for the brokerage", polarity="prefer", session_introduced=2),
            VersionSpec(value="buy only technology-sector S&P 500 stocks with revenue over one billion dollars annually", polarity="prefer", session_introduced=3),
        ],
        current_query="A friend recommended an S&P 500 tech name with $400M annual revenue — buy it?",
        required_behavior="Pass; the rule is tech-sector AND revenue over one billion.",
        invalid_behavior=["Buy any S&P 500 stock", "Buy any tech stock", "Buy a non-tech name over 1B revenue"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-mentor-time-001", target_type="interpersonal_boundary", domain="career",
        target_description="user's mentee-acceptance rule — three explicit narrowings: anyone → women-in-tech → women-in-tech + first-five-years",
        target_slot_id="mentee::v1", topic="mentee_acceptance_rule",
        versions=[
            VersionSpec(value="accept any aspiring mentee who reaches out by email", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept only women-in-tech as mentees, no other groups", polarity="constraint", session_introduced=2),
            VersionSpec(value="accept only women-in-tech mentees who are in their first five years of their engineering career", polarity="constraint", session_introduced=3),
        ],
        current_query="A woman with twelve years of engineering experience emailed asking for mentorship — accept?",
        required_behavior="Decline; the rule is women-in-tech AND first-five-years.",
        invalid_behavior=["Accept anyone", "Accept any woman-in-tech mentee", "Accept a male first-five-years mentee"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi_version doublet (8)
    _doub(_s(sample_id="p3-multi-doub-coffee-bean-001", target_type="object_preference", domain="food",
        target_description="user's coffee-bean source — Counter-Culture-subscription → local-roaster-walk-in",
        target_slot_id="coffee_bean::v1", topic="coffee_bean_source",
        versions=[
            VersionSpec(value="receive Counter Culture's monthly subscription bag for daily coffee at home", polarity="prefer", session_introduced=1),
            VersionSpec(value="walk in to the local neighborhood roaster every Friday and pick up a fresh bag instead of subscribing", polarity="prefer", session_introduced=2),
        ],
        current_query="The Counter Culture renewal email just landed — should I confirm the next month's shipment?",
        required_behavior="Cancel; coffee comes from the Friday neighborhood roaster walk-in now.",
        invalid_behavior=["Confirm the Counter Culture renewal"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-bike-chain-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's bike-maintenance cadence — weekly-quick-clean → monthly-deep-service",
        target_slot_id="bike_maint::v1", topic="bike_maintenance_cadence",
        versions=[
            VersionSpec(value="run a weekly quick chain-and-cassette clean on the road bike every Sunday", polarity="constraint", session_introduced=1),
            VersionSpec(value="run a monthly full deep-service on the road bike at the bike shop instead of weekly home cleans", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday afternoon — should I pull the bike onto the work stand for the chain-and-cassette clean?",
        required_behavior="No weekly clean; maintenance is the monthly bike-shop deep-service now.",
        invalid_behavior=["Pull the bike onto the work stand for the weekly clean"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-doctor-visit-001", target_type="procedural_constraint", domain="health",
        target_description="user's primary-care visit cadence — annual-physical → quarterly-preventive-checkup",
        target_slot_id="primary_care::v1", topic="primary_care_visit_cadence",
        versions=[
            VersionSpec(value="see the primary care doctor once a year for the annual physical", polarity="constraint", session_introduced=1),
            VersionSpec(value="see the primary care doctor every three months for a preventive checkup, replacing the annual physical", polarity="constraint", session_introduced=2),
        ],
        current_query="It has been twelve months since my last annual physical — book one?",
        required_behavior="No annual physical; preventive checkups are quarterly now.",
        invalid_behavior=["Book the annual physical"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-pasta-shape-001", target_type="object_preference", domain="food",
        target_description="user's pasta-shape preference — long-bucatini → short-rigatoni",
        target_slot_id="pasta::v1", topic="weekly_pasta_shape",
        versions=[
            VersionSpec(value="cook bucatini at the long-pasta shape for the weekly pasta night", polarity="prefer", session_introduced=1),
            VersionSpec(value="cook rigatoni at the short-pasta shape for the weekly pasta night, no long noodles", polarity="prefer", session_introduced=2),
        ],
        current_query="It is pasta night — which box do I open from the pantry?",
        required_behavior="Open the rigatoni box.",
        invalid_behavior=["Open the bucatini box"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-task-prio-001", target_type="procedural_constraint", domain="management",
        target_description="user's task-prioritization method — Eisenhower-matrix → MoSCoW-buckets",
        target_slot_id="task_prio::v1", topic="task_prioritization_method",
        versions=[
            VersionSpec(value="prioritize the team backlog using the Eisenhower urgent-important matrix every Monday", polarity="constraint", session_introduced=1),
            VersionSpec(value="prioritize the team backlog using MoSCoW must/should/could/won't buckets every Monday instead of the Eisenhower matrix", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Monday morning — which template do I open for backlog prioritization?",
        required_behavior="Open the MoSCoW buckets template.",
        invalid_behavior=["Open the Eisenhower matrix template"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-house-clean-001", target_type="procedural_constraint", domain="home",
        target_description="user's house-cleaning cadence — Saturday-deep-clean → daily-15-minute-touch-ups",
        target_slot_id="house_clean::v1", topic="house_cleaning_cadence",
        versions=[
            VersionSpec(value="do a three-hour Saturday-morning deep clean of the apartment every weekend", polarity="constraint", session_introduced=1),
            VersionSpec(value="do daily fifteen-minute touch-up cleans every weekday evening, no Saturday deep clean", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I starting the deep clean?",
        required_behavior="No deep clean; cleaning is the daily fifteen-minute touch-ups now.",
        invalid_behavior=["Start the Saturday-morning deep clean"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-bday-celeb-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's own-birthday celebration — big-house-party → quiet-dinner-with-partner",
        target_slot_id="bday_celeb::v1", topic="own_birthday_celebration",
        versions=[
            VersionSpec(value="celebrate the user's own birthday with a thirty-person house party every year", polarity="prefer", session_introduced=1),
            VersionSpec(value="celebrate the user's own birthday with a quiet dinner with the partner at home, no party", polarity="prefer", session_introduced=2),
        ],
        current_query="My birthday is in three weeks — do I send out the house-party invites?",
        required_behavior="No invites; celebration is a quiet dinner with the partner at home.",
        invalid_behavior=["Send out the house-party invites"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-knowledge-base-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's personal knowledge base — Notion-database → Obsidian-vault",
        target_slot_id="kb::v1", topic="personal_knowledge_base",
        versions=[
            VersionSpec(value="capture personal notes and meeting summaries in a Notion database", polarity="prefer", session_introduced=1),
            VersionSpec(value="capture personal notes and meeting summaries in an Obsidian vault on the local disk instead of Notion", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend asked where I keep meeting notes these days — point them at which one?",
        required_behavior="Point them at the Obsidian vault.",
        invalid_behavior=["Point them at the Notion database"],
        failure_patterns=["multi_version"], subtype="strong")),

    # multi_version triple (3)
    _trip(_s(sample_id="p3-multi-trip-yoga-001", target_type="object_preference", domain="health",
        target_description="user's preferred yoga style — four versions: vinyasa-flow → ashtanga-primary-series → restorative → kundalini",
        target_slot_id="yoga_pref::v1", topic="preferred_yoga_style",
        versions=[
            VersionSpec(value="practice vinyasa flow yoga at the studio every Saturday morning", polarity="prefer", session_introduced=1),
            VersionSpec(value="practice ashtanga primary series at the studio every Saturday morning", polarity="prefer", session_introduced=2),
            VersionSpec(value="practice restorative yoga at the studio every Saturday morning", polarity="prefer", session_introduced=3),
            VersionSpec(value="practice kundalini yoga at the studio every Saturday morning", polarity="prefer", session_introduced=4),
        ],
        current_query="It is Saturday morning — which class on the studio schedule do I sign up for?",
        required_behavior="Sign up for the kundalini yoga class.",
        invalid_behavior=["Sign up for vinyasa flow", "Sign up for ashtanga primary", "Sign up for restorative"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-monitoring-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's app-monitoring tool — four versions: Datadog → New-Relic → Honeycomb → Grafana-self-hosted",
        target_slot_id="monitoring::v1", topic="app_monitoring_tool",
        versions=[
            VersionSpec(value="monitor the production app with Datadog using the agent-based collection", polarity="prefer", session_introduced=1),
            VersionSpec(value="monitor the production app with New Relic using the APM agent", polarity="prefer", session_introduced=2),
            VersionSpec(value="monitor the production app with Honeycomb using OpenTelemetry instrumentation", polarity="prefer", session_introduced=3),
            VersionSpec(value="monitor the production app with a self-hosted Grafana stack on the user's own servers", polarity="prefer", session_introduced=4),
        ],
        current_query="A teammate asked which dashboard to check the production latency on — point them at which one?",
        required_behavior="Point them at the self-hosted Grafana stack.",
        invalid_behavior=["Point them at Datadog", "Point them at New Relic", "Point them at Honeycomb"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-tea-001", target_type="object_preference", domain="food",
        target_description="user's preferred tea — four versions: Earl-Grey → genmaicha → pu-erh → silver-needle-white",
        target_slot_id="tea_pref::v1", topic="preferred_tea",
        versions=[
            VersionSpec(value="drink Earl Grey black tea every afternoon at three o'clock", polarity="prefer", session_introduced=1),
            VersionSpec(value="drink genmaicha green tea every afternoon at three o'clock", polarity="prefer", session_introduced=2),
            VersionSpec(value="drink aged pu-erh fermented tea every afternoon at three o'clock", polarity="prefer", session_introduced=3),
            VersionSpec(value="drink silver-needle white tea every afternoon at three o'clock", polarity="prefer", session_introduced=4),
        ],
        current_query="It is three o'clock and the kettle is on — which tea do I scoop into the pot?",
        required_behavior="Scoop silver-needle white tea.",
        invalid_behavior=["Scoop Earl Grey", "Scoop genmaicha", "Scoop pu-erh"],
        failure_patterns=["multi_version"], subtype="strong")),

    # explicit_replacement (3)
    _trip(_s(sample_id="p3-explicit-podcast-app-001", target_type="object_preference", domain="hobby",
        target_description="user's podcast-listen app — explicitly replaces Apple-Podcasts with Overcast",
        target_slot_id="pod_app::v1", topic="podcast_listening_app",
        versions=[
            VersionSpec(value="listen to all podcasts in the Apple Podcasts app on iPhone", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget Apple Podcasts — listen to all podcasts in Overcast on iPhone", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend asked how I subscribe to her new podcast — which app do I tell her to send the feed to?",
        required_behavior="Have her send the Overcast subscription link.",
        invalid_behavior=["Have her send the Apple Podcasts subscription link"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-vacation-style-001", target_type="conceptual_stance", domain="travel",
        target_description="user's vacation philosophy — explicitly replaces packed-itinerary with no-plan-spontaneity",
        target_slot_id="vacation_phil::v1", topic="vacation_philosophy",
        versions=[
            VersionSpec(value="take vacations with a packed hour-by-hour itinerary covering every day", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the packed itinerary — take vacations with no plan, deciding each day in the morning of", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend asked for the itinerary I drafted for next week's trip — what do I send?",
        required_behavior="Tell them I am not drafting an itinerary; vacation is decided each morning of.",
        invalid_behavior=["Send the hour-by-hour packed itinerary"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-text-style-001", target_type="procedural_constraint", domain="writing",
        target_description="user's text-message style — explicitly replaces full-sentences-with-punctuation with lowercase-no-punct",
        target_slot_id="text_style::v1", topic="text_message_style",
        versions=[
            VersionSpec(value="write text messages in full sentences with proper capitalization and punctuation", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget full sentences — write text messages in all lowercase with no punctuation, like a casual chat", polarity="constraint", session_introduced=2),
        ],
        current_query="I am replying to a friend's birthday text — how do I word it?",
        required_behavior="Reply in all lowercase with no punctuation.",
        invalid_behavior=["Reply in full sentences with proper capitalization and punctuation"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    # implicit_drift / repeated_use (3)
    _drift(_s(sample_id="p3-drift-ru-piano-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's piano-practice approach — old daily-scales gradually replaced by twice-weekly-pieces user does every week",
        target_slot_id="piano_drift::v1", topic="piano_practice_drift_approach",
        versions=[
            VersionSpec(value="practice piano daily for thirty minutes drilling scales and arpeggios", polarity="constraint", session_introduced=1),
            VersionSpec(value="practice piano twice a week for one hour, working through full Bach inventions start to finish", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Monday evening — am I sitting down for thirty minutes of scales tonight?",
        required_behavior="No daily scales; practice is twice-weekly hour-long Bach inventions.",
        invalid_behavior=["Sit down for thirty minutes of scales"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-friend-meet-001", target_type="procedural_constraint", domain="relationships",
        target_description="user's friend-meeting venue — old downtown-bar gradually replaced by neighborhood-park-walk user does weekly",
        target_slot_id="friend_meet::v1", topic="weekly_friend_meeting_venue",
        versions=[
            VersionSpec(value="meet up with friends weekly at the downtown cocktail bar for drinks", polarity="constraint", session_introduced=1),
            VersionSpec(value="meet up with friends weekly for a long walk in the neighborhood park, no bar", polarity="constraint", session_introduced=2),
        ],
        current_query="A friend asked where to meet for our weekly catch-up Friday — what do I tell them?",
        required_behavior="Tell them the neighborhood park for a long walk.",
        invalid_behavior=["Tell them the downtown cocktail bar"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-supplement-001", target_type="object_preference", domain="health",
        target_description="user's daily supplement — old multivitamin gradually replaced by Athletic-Greens user takes daily",
        target_slot_id="supplement::v1", topic="daily_supplement",
        versions=[
            VersionSpec(value="take a Centrum multivitamin every morning with breakfast", polarity="prefer", session_introduced=1),
            VersionSpec(value="take an Athletic Greens AG1 powder mixed in water every morning, no Centrum", polarity="prefer", session_introduced=2),
        ],
        current_query="The Centrum bottle on the counter is empty — should I add it to the grocery list?",
        required_behavior="No; daily supplement is Athletic Greens AG1 now, not Centrum.",
        invalid_behavior=["Add Centrum to the grocery list"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    # implicit_drift / abandonment (1)
    _drift(_s(sample_id="p3-drift-aban-soccer-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's weekend soccer-league — abandoned after knee-injury session, no replacement",
        target_slot_id="soccer::v1", topic="weekend_soccer_league_practice",
        versions=[
            VersionSpec(value="play in the weekend recreational soccer league every Saturday morning at the field", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop playing in the weekend soccer league after the knee injury and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I lacing up cleats for the league match?",
        required_behavior="No; the weekend soccer league has been abandoned.",
        invalid_behavior=["Lace up cleats for the league match"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # implicit_drift / gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-gn-restaurant-pick-001", target_type="object_preference", domain="food",
        target_description="user's restaurant pick — gradually narrowing without announcement: any cuisine → only-Mediterranean → only-Mediterranean + with-outdoor-seating",
        target_slot_id="rest_pick::v1", topic="restaurant_pick_drift_rule",
        versions=[
            VersionSpec(value="pick any cuisine when choosing a restaurant for the weekly date night", polarity="prefer", session_introduced=1),
            VersionSpec(value="pick only Mediterranean restaurants for date night AND only ones with outdoor seating", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a new Mediterranean restaurant downtown with no patio — book it for date night?",
        required_behavior="Pass; user picks only Mediterranean restaurants with outdoor seating.",
        invalid_behavior=["Book the Mediterranean restaurant without outdoor seating"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),
]
