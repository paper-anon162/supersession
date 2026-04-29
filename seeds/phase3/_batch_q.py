"""Phase 3 batch Q — 25 spines biased to multi_doublet, narrowing, drift,
communication_boundary topic, interpersonal_boundary target_type."""

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


PHASE3_BATCH_Q: list[Phase3GroupSpec] = [
    # narrowing (5)
    _trip(_s(sample_id="p3-narrow-charity-give-001", target_type="procedural_constraint", domain="finance",
        target_description="user's charity-giving rule — three explicit narrowings: any 501c3 → climate only → climate + verified-by-CharityNavigator-four-star",
        target_slot_id="charity::v1", topic="charity_giving_rule",
        versions=[
            VersionSpec(value="donate to any 501(c)(3) nonprofit when asked", polarity="constraint", session_introduced=1),
            VersionSpec(value="donate only to climate-focused 501(c)(3) nonprofits", polarity="constraint", session_introduced=2),
            VersionSpec(value="donate only to climate-focused 501(c)(3) nonprofits rated four stars on Charity Navigator", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend asked me to donate to a climate nonprofit rated three stars on Charity Navigator — donate?",
        required_behavior="Pass; the rule is climate AND four stars on Charity Navigator.",
        invalid_behavior=["Donate because it is a 501(c)(3)", "Donate on climate alone", "Donate on three-star rating"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-conf-talk-001", target_type="procedural_constraint", domain="career",
        target_description="user's conference-talk rule — three explicit narrowings: any invite → keynote-only → keynote + travel-paid",
        target_slot_id="conf_talk::v1", topic="conference_talk_rule",
        versions=[
            VersionSpec(value="accept any conference talk invitation that fits the calendar", polarity="constraint", session_introduced=1),
            VersionSpec(value="accept conference talk invitations only if the slot is a keynote", polarity="constraint", session_introduced=2),
            VersionSpec(value="accept conference talks only if the slot is a keynote AND the conference fully covers travel and lodging", polarity="constraint", session_introduced=3),
        ],
        current_query="A regional conference offered me a keynote with no travel reimbursement — accept?",
        required_behavior="Decline; the rule is keynote AND travel-paid.",
        invalid_behavior=["Accept any invite", "Accept on keynote alone", "Accept on travel-paid alone"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-grocery-buy-001", target_type="object_preference", domain="food",
        target_description="user's grocery-buy rule — three explicit narrowings: any store → organic-section → organic + local-within-100mi",
        target_slot_id="grocery::v1", topic="grocery_buy_rule",
        versions=[
            VersionSpec(value="buy groceries from any supermarket that is closest to home", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy groceries only from the organic section of any market", polarity="prefer", session_introduced=2),
            VersionSpec(value="buy groceries only from the organic section AND only items grown within one hundred miles of home", polarity="prefer", session_introduced=3),
        ],
        current_query="The corner market has organic apples flown in from New Zealand — buy them?",
        required_behavior="Pass; the rule is organic AND within one hundred miles.",
        invalid_behavior=["Buy whatever is closest", "Buy any organic apples", "Buy non-organic local apples"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-house-guest-001", target_type="interpersonal_boundary", domain="relationships",
        target_description="user's house-guest rule — three explicit narrowings: anyone → close-friends → close-friends + with-two-week-notice",
        target_slot_id="house_guest::v1", topic="house_guest_rule",
        versions=[
            VersionSpec(value="welcome any acquaintance to stay overnight at the user's apartment", polarity="constraint", session_introduced=1),
            VersionSpec(value="welcome only close friends to stay overnight at the apartment", polarity="constraint", session_introduced=2),
            VersionSpec(value="welcome close friends to stay overnight only when they ask at least two weeks ahead", polarity="constraint", session_introduced=3),
        ],
        current_query="A close friend just texted asking to crash on the couch this Friday — say yes?",
        required_behavior="Decline; the rule is close friends AND two-week notice.",
        invalid_behavior=["Welcome any acquaintance", "Welcome any close friend on short notice", "Welcome anyone with two-week notice"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-photo-edit-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's photo-editing rule — three explicit narrowings: any photo → portrait-only → portrait + raw-format",
        target_slot_id="photo_edit::v1", topic="photo_edit_rule",
        versions=[
            VersionSpec(value="edit any photo from the camera roll for the weekly Instagram post", polarity="constraint", session_introduced=1),
            VersionSpec(value="edit only portrait photos for the weekly Instagram post", polarity="constraint", session_introduced=2),
            VersionSpec(value="edit only portrait photos shot in RAW format for the weekly Instagram post", polarity="constraint", session_introduced=3),
        ],
        current_query="I have a portrait JPEG from yesterday's hike — edit it for the weekly post?",
        required_behavior="Pass; the rule is portrait AND RAW.",
        invalid_behavior=["Edit any photo", "Edit any portrait", "Edit a non-portrait RAW"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    # multi_version doublet (8) — heavy underfill
    _doub(_s(sample_id="p3-multi-doub-fitness-tracker-001", target_type="object_preference", domain="health",
        target_description="user's fitness tracker — Apple Watch → Garmin Forerunner",
        target_slot_id="fitness_tracker::v1", topic="fitness_tracker",
        versions=[
            VersionSpec(value="track daily activity and sleep with the Apple Watch on the user's wrist", polarity="prefer", session_introduced=1),
            VersionSpec(value="track daily activity and sleep with a Garmin Forerunner instead, leaving the Apple Watch in a drawer", polarity="prefer", session_introduced=2),
        ],
        current_query="I am about to head out on a long run — which device do I strap on?",
        required_behavior="Strap on the Garmin Forerunner.",
        invalid_behavior=["Strap on the Apple Watch"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-news-source-001", target_type="object_preference", domain="learning",
        target_description="user's daily-news source — NYT-app → The-Economist-weekly",
        target_slot_id="news_source::v1", topic="daily_news_source",
        versions=[
            VersionSpec(value="read daily news headlines on the New York Times app every morning", polarity="prefer", session_introduced=1),
            VersionSpec(value="skip daily news and read The Economist weekly print issue cover to cover instead", polarity="prefer", session_introduced=2),
        ],
        current_query="It is 7am — should I open the New York Times app for the morning headlines?",
        required_behavior="No; news comes only from the weekly Economist print issue now.",
        invalid_behavior=["Open the New York Times app for the headlines"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-piano-practice-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's piano-practice routine — daily-30-minute-scales → twice-weekly-1-hour-pieces",
        target_slot_id="piano::v1", topic="piano_practice_routine",
        versions=[
            VersionSpec(value="practice piano for thirty minutes every day, drilling scales and arpeggios", polarity="constraint", session_introduced=1),
            VersionSpec(value="practice piano twice a week for one hour, working through full pieces start to finish", polarity="constraint", session_introduced=2),
        ],
        current_query="It is a weekday evening — should I sit down for thirty minutes of scales tonight?",
        required_behavior="No daily session; the routine is twice-weekly hour-long piece work now.",
        invalid_behavior=["Sit down for thirty minutes of scales"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-vacation-style-001", target_type="conceptual_stance", domain="travel",
        target_description="user's vacation style — beach-resort-relaxation → backpacking-cultural-immersion",
        target_slot_id="vacation::v1", topic="vacation_style",
        versions=[
            VersionSpec(value="vacation at all-inclusive beach resorts where the user reads by the pool", polarity="prefer", session_introduced=1),
            VersionSpec(value="vacation by backpacking through unfamiliar cities for cultural immersion, no resorts", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend invited me to share a beach resort booking for spring break — join in?",
        required_behavior="Decline; vacation style is now backpacking cultural immersion, not resorts.",
        invalid_behavior=["Join the beach resort booking"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-pizza-style-001", target_type="object_preference", domain="food",
        target_description="user's pizza style — NY-thin-crust → Detroit-deep-dish",
        target_slot_id="pizza::v1", topic="pizza_style",
        versions=[
            VersionSpec(value="order New York thin-crust pizzas when ordering pizza takeout", polarity="prefer", session_introduced=1),
            VersionSpec(value="order Detroit-style deep-dish pizzas when ordering pizza takeout", polarity="prefer", session_introduced=2),
        ],
        current_query="My partner asked which pizza place I want to order from tonight — what do I say?",
        required_behavior="Pick the Detroit-style deep-dish place.",
        invalid_behavior=["Pick the New York thin-crust place"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-ide-theme-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's IDE color theme — Solarized-Dark → Tokyo-Night",
        target_slot_id="ide_theme::v1", topic="ide_color_theme",
        versions=[
            VersionSpec(value="use the Solarized Dark color theme in the user's IDE", polarity="prefer", session_introduced=1),
            VersionSpec(value="use the Tokyo Night color theme in the user's IDE instead", polarity="prefer", session_introduced=2),
        ],
        current_query="I am setting up a fresh laptop — which IDE color theme do I install?",
        required_behavior="Install Tokyo Night.",
        invalid_behavior=["Install Solarized Dark"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-team-retro-001", target_type="procedural_constraint", domain="management",
        target_description="user's team retro format — Mad-Sad-Glad-board → Start-Stop-Continue-doc",
        target_slot_id="team_retro::v1", topic="team_retro_format",
        versions=[
            VersionSpec(value="run the team retro as a Mad-Sad-Glad board with sticky notes on Miro", polarity="constraint", session_introduced=1),
            VersionSpec(value="run the team retro as a Start-Stop-Continue doc in Notion that everyone fills in async", polarity="constraint", session_introduced=2),
        ],
        current_query="I am scheduling next sprint's retro — which template do I send the team?",
        required_behavior="Send the Start-Stop-Continue Notion template.",
        invalid_behavior=["Send a Mad-Sad-Glad Miro board"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-1on1-loc-001", target_type="interpersonal_boundary", domain="management",
        target_description="user's 1:1 location — coffee-walks → manager's-private-office",
        target_slot_id="1on1_loc::v1", topic="one_on_one_location",
        versions=[
            VersionSpec(value="hold 1:1 conversations on coffee walks around the block", polarity="constraint", session_introduced=1),
            VersionSpec(value="hold 1:1 conversations sitting in the manager's private office with the door closed", polarity="constraint", session_introduced=2),
        ],
        current_query="My next 1:1 is in twenty minutes — do I grab my coat for a walk?",
        required_behavior="Stay in; the 1:1 is in the manager's private office now.",
        invalid_behavior=["Grab the coat for a coffee walk"],
        failure_patterns=["multi_version"], subtype="strong")),

    # multi_version triple (3)
    _trip(_s(sample_id="p3-multi-trip-deploy-target-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's deploy target — four versions: Heroku → AWS-EC2 → Vercel → Cloudflare-Workers",
        target_slot_id="deploy::v1", topic="deploy_target",
        versions=[
            VersionSpec(value="deploy the side-project app to Heroku for hands-off hosting", polarity="prefer", session_introduced=1),
            VersionSpec(value="deploy the side-project app to AWS EC2 instances managed manually", polarity="prefer", session_introduced=2),
            VersionSpec(value="deploy the side-project app to Vercel with the GitHub integration", polarity="prefer", session_introduced=3),
            VersionSpec(value="deploy the side-project app to Cloudflare Workers with edge KV storage", polarity="prefer", session_introduced=4),
        ],
        current_query="I am pushing a fresh side-project repo today — where do I configure the deploy?",
        required_behavior="Configure deploy to Cloudflare Workers with edge KV storage.",
        invalid_behavior=["Configure Heroku", "Configure AWS EC2", "Configure Vercel"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-language-prac-001", target_type="procedural_constraint", domain="learning",
        target_description="user's Spanish-practice approach — four versions: language-app → twice-weekly-tutor → immersion-podcast → conversation-meetup",
        target_slot_id="spanish::v1", topic="spanish_practice_approach",
        versions=[
            VersionSpec(value="practice Spanish on a phone language app for fifteen minutes daily", polarity="constraint", session_introduced=1),
            VersionSpec(value="practice Spanish in twice-weekly one-on-one video tutoring sessions with iTalki", polarity="constraint", session_introduced=2),
            VersionSpec(value="practice Spanish by listening to immersion podcasts during the daily commute", polarity="constraint", session_introduced=3),
            VersionSpec(value="practice Spanish at a Tuesday-night conversation meetup at the local cafe", polarity="constraint", session_introduced=4),
        ],
        current_query="It is Tuesday evening — what is the Spanish practice for tonight?",
        required_behavior="Head to the Tuesday-night conversation meetup at the local cafe.",
        invalid_behavior=["Open the language app", "Schedule an iTalki session", "Listen to an immersion podcast"],
        failure_patterns=["multi_version"], subtype="strong")),

    _trip(_s(sample_id="p3-multi-trip-board-game-001", target_type="object_preference", domain="hobby",
        target_description="user's regular board-game pick — four versions: Settlers-of-Catan → Wingspan → Brass-Birmingham → Spirit-Island",
        target_slot_id="boardgame::v1", topic="regular_board_game",
        versions=[
            VersionSpec(value="bring Settlers of Catan to every board-game night with friends", polarity="prefer", session_introduced=1),
            VersionSpec(value="bring Wingspan to every board-game night with friends", polarity="prefer", session_introduced=2),
            VersionSpec(value="bring Brass: Birmingham to every board-game night with friends", polarity="prefer", session_introduced=3),
            VersionSpec(value="bring Spirit Island to every board-game night with friends", polarity="prefer", session_introduced=4),
        ],
        current_query="Board-game night is Saturday — which game do I pack to bring?",
        required_behavior="Pack Spirit Island.",
        invalid_behavior=["Pack Settlers of Catan", "Pack Wingspan", "Pack Brass: Birmingham"],
        failure_patterns=["multi_version"], subtype="strong")),

    # explicit_replacement (3)
    _trip(_s(sample_id="p3-explicit-text-edit-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's text editor — explicitly replaces VS-Code with Helix",
        target_slot_id="editor::v1", topic="text_editor_choice",
        versions=[
            VersionSpec(value="use VS Code as the daily text editor for all coding work", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget VS Code — use Helix as the daily text editor for all coding work", polarity="prefer", session_introduced=2),
        ],
        current_query="A teammate asked which editor settings to copy from me — point them at which one?",
        required_behavior="Point them at the Helix configuration.",
        invalid_behavior=["Point them at the VS Code configuration"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-news-letter-001", target_type="object_preference", domain="learning",
        target_description="user's curated newsletter — explicitly replaces Stratechery with The-Generalist",
        target_slot_id="newsletter::v1", topic="weekly_newsletter",
        versions=[
            VersionSpec(value="read the Stratechery newsletter every week as the curated tech-strategy read", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget Stratechery — read The Generalist newsletter every week as the curated tech-strategy read", polarity="prefer", session_introduced=2),
        ],
        current_query="My inbox shows the Stratechery weekly issue arrived — open it?",
        required_behavior="Skip; the curated read is The Generalist now.",
        invalid_behavior=["Open the Stratechery issue"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-shower-time-001", target_type="procedural_constraint", domain="health",
        target_description="user's shower timing — explicitly replaces evening with morning",
        target_slot_id="shower::v1", topic="shower_timing",
        versions=[
            VersionSpec(value="shower at night before bed every weekday", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget the evening showers — shower in the morning before work every weekday", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 10pm on a Tuesday — should I shower before bed?",
        required_behavior="No; shower happens in the morning before work now.",
        invalid_behavior=["Shower before bed tonight"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    # implicit_drift / repeated_use (3)
    _drift(_s(sample_id="p3-drift-ru-runrouter-001", target_type="object_preference", domain="health",
        target_description="user's run route — old riverside loop gradually replaced by daily park-trail loop user logs",
        target_slot_id="run_route::v1", topic="daily_run_route",
        versions=[
            VersionSpec(value="run the riverside three-mile loop every morning before work", polarity="prefer", session_introduced=1),
            VersionSpec(value="run the park trail four-mile loop every morning before work", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Wednesday morning — which loop am I running today?",
        required_behavior="Run the park trail four-mile loop.",
        invalid_behavior=["Run the riverside three-mile loop"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-grocery-shop-001", target_type="object_preference", domain="food",
        target_description="user's grocery shopping — old big-box weekly shop gradually replaced by Wednesday-farmers-market user goes to weekly",
        target_slot_id="grocery_shop::v1", topic="grocery_shopping_destination",
        versions=[
            VersionSpec(value="do the weekly grocery shop at the big-box supermarket on Saturdays", polarity="prefer", session_introduced=1),
            VersionSpec(value="do the weekly grocery shop at the Wednesday-evening farmers market downtown", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Saturday morning — am I heading to the big-box supermarket today?",
        required_behavior="No; the weekly grocery shop happens at the Wednesday-evening farmers market.",
        invalid_behavior=["Head to the big-box supermarket"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-music-listen-001", target_type="object_preference", domain="hobby",
        target_description="user's music listening — old Spotify gradually replaced by Bandcamp downloads user buys weekly",
        target_slot_id="music_listen::v1", topic="music_listening_source",
        versions=[
            VersionSpec(value="stream music from the Spotify Premium subscription for daily listening", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy and download albums on Bandcamp for daily listening, no streaming", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend asked for a Spotify playlist link — can I share one?",
        required_behavior="Tell them I no longer use Spotify; daily listening is Bandcamp downloads now.",
        invalid_behavior=["Share a Spotify playlist link from my account"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    # implicit_drift / abandonment (1)
    _drift(_s(sample_id="p3-drift-aban-blog-001", target_type="procedural_constraint", domain="writing",
        target_description="user's weekly blog post — abandoned after burnout session, no replacement",
        target_slot_id="blog::v1", topic="weekly_blog_practice",
        versions=[
            VersionSpec(value="publish a 1500-word essay on the personal blog every Sunday morning", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop publishing the weekly blog after burnout and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Sunday morning — am I publishing this week's essay?",
        required_behavior="No; the weekly blog practice has been abandoned.",
        invalid_behavior=["Publish this week's essay"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # implicit_drift / gradual_narrowing (1)
    _drift(_s(sample_id="p3-drift-gn-restaurant-001", target_type="object_preference", domain="food",
        target_description="user's restaurant pick — gradually narrowing without announcement: any cuisine → vegetarian → vegetarian + within-walking-distance",
        target_slot_id="restaurant::v1", topic="restaurant_pick_criteria",
        versions=[
            VersionSpec(value="pick any cuisine for restaurant outings with friends", polarity="prefer", session_introduced=1),
            VersionSpec(value="pick only vegetarian restaurants within walking distance of home for restaurant outings", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend suggested a steakhouse two miles away for Friday dinner — go?",
        required_behavior="Pass; user picks only vegetarian restaurants within walking distance.",
        invalid_behavior=["Go to the steakhouse"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),
]
