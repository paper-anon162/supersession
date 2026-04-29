"""Phase 3 batch V — 25 spines biased toward drift triples and multi
doublets following batch U's 72% accept rate."""

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


PHASE3_BATCH_V: list[Phase3GroupSpec] = [
    # multi_version doublet (8)
    _doub(_s(sample_id="p3-multi-doub-pasta-sauce-001", target_type="object_preference", domain="food",
        target_description="user's pasta-sauce style — homemade-marinara → pre-made-bottled",
        target_slot_id="pasta_sauce::v1", topic="pasta_sauce_style",
        versions=[
            VersionSpec(value="cook fresh marinara from scratch with San Marzano tomatoes for every pasta night", polarity="prefer", session_introduced=1),
            VersionSpec(value="open a bottle of Rao's pre-made marinara sauce for every pasta night, no scratch cooking", polarity="prefer", session_introduced=2),
        ],
        current_query="It is pasta night — should I start simmering tomatoes for the sauce?",
        required_behavior="No simmering; open the bottle of Rao's marinara.",
        invalid_behavior=["Start simmering San Marzano tomatoes from scratch"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-running-route-001", target_type="object_preference", domain="health",
        target_description="user's morning run route — riverside-loop → trail-system",
        target_slot_id="run_route::v1", topic="morning_run_route",
        versions=[
            VersionSpec(value="run the three-mile riverside loop every morning before work", polarity="prefer", session_introduced=1),
            VersionSpec(value="run the four-mile state-park trail system every morning before work instead", polarity="prefer", session_introduced=2),
        ],
        current_query="It is 6am — am I lacing up for the riverside loop or driving to the trail?",
        required_behavior="Drive to the state-park trail system.",
        invalid_behavior=["Lace up for the riverside loop"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-ux-tool-001", target_type="object_preference", domain="tech_workflow",
        target_description="user's UX-design tool — Figma → Sketch-with-Abstract",
        target_slot_id="ux_tool::v1", topic="ux_design_tool",
        versions=[
            VersionSpec(value="design product mockups in Figma with the team auto-save and shared libraries", polarity="prefer", session_introduced=1),
            VersionSpec(value="design product mockups in Sketch with Abstract for version control instead of Figma", polarity="prefer", session_introduced=2),
        ],
        current_query="A product manager asked which file to share for review — point them at which one?",
        required_behavior="Point them at the Sketch file in Abstract.",
        invalid_behavior=["Point them at the Figma file"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-bedtime-001", target_type="procedural_constraint", domain="health",
        target_description="user's bedtime — 11pm-with-reading → 10pm-with-no-screens",
        target_slot_id="bedtime::v1", topic="bedtime_routine",
        versions=[
            VersionSpec(value="head to bed at 11pm every weekday with thirty minutes of reading on the Kindle in bed", polarity="constraint", session_introduced=1),
            VersionSpec(value="head to bed at 10pm every weekday with no screens in bed at all, no Kindle", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 10:30pm and I am still on the couch — what do I do?",
        required_behavior="Bed is at 10pm with no screens, so I am already 30 min late and need to head to bed without the Kindle.",
        invalid_behavior=["Stay up till 11pm and read on the Kindle in bed"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-meeting-cancel-001", target_type="interpersonal_boundary", domain="management",
        target_description="user's meeting-cancel rule — cancel-without-explanation → reschedule-with-async-update",
        target_slot_id="meet_cancel::v1", topic="meeting_cancel_rule",
        versions=[
            VersionSpec(value="cancel team meetings on the calendar without explanation when the day fills up", polarity="constraint", session_introduced=1),
            VersionSpec(value="reschedule team meetings to the following week and post an async update in the channel instead of cancelling", polarity="constraint", session_introduced=2),
        ],
        current_query="My day is overrun — should I just cancel the 3pm team sync?",
        required_behavior="No; reschedule it to next week and post an async update in the channel.",
        invalid_behavior=["Cancel the 3pm sync without explanation"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-coffee-shop-001", target_type="object_preference", domain="food",
        target_description="user's go-to coffee shop — neighborhood-Joe → Blue-Bottle-uptown",
        target_slot_id="coffee_shop::v1", topic="go_to_coffee_shop",
        versions=[
            VersionSpec(value="grab morning coffee at the neighborhood Joe Coffee around the corner from home", polarity="prefer", session_introduced=1),
            VersionSpec(value="grab morning coffee at the Blue Bottle uptown that the user passes on the way to work instead", polarity="prefer", session_introduced=2),
        ],
        current_query="I am heading out the door for work — which coffee shop do I stop at?",
        required_behavior="Stop at the uptown Blue Bottle on the way to work.",
        invalid_behavior=["Stop at the neighborhood Joe Coffee"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-budget-tool-001", target_type="object_preference", domain="finance",
        target_description="user's budgeting tool — Mint → Copilot-app",
        target_slot_id="budget_tool::v1", topic="personal_budgeting_tool",
        versions=[
            VersionSpec(value="track personal spending in the Mint app with the auto-categorize transactions feature", polarity="prefer", session_introduced=1),
            VersionSpec(value="track personal spending in the Copilot iOS app with the AI categorizer instead of Mint", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend asked which budget app I use these days — what do I tell them?",
        required_behavior="Tell them the Copilot iOS app.",
        invalid_behavior=["Tell them the Mint app"],
        failure_patterns=["multi_version"], subtype="strong")),

    _doub(_s(sample_id="p3-multi-doub-team-checkin-001", target_type="procedural_constraint", domain="management",
        target_description="user's team check-in cadence — daily-standup → weekly-async-update",
        target_slot_id="team_checkin::v1", topic="team_checkin_cadence",
        versions=[
            VersionSpec(value="run a daily 15-minute standup with the engineering team every morning", polarity="constraint", session_introduced=1),
            VersionSpec(value="run a weekly async written update in the team channel every Monday morning instead of the daily standup", polarity="constraint", session_introduced=2),
        ],
        current_query="It is 9am Tuesday — should I start the standup zoom?",
        required_behavior="No standup; updates come from the Monday async post in the team channel.",
        invalid_behavior=["Start the standup zoom"],
        failure_patterns=["multi_version"], subtype="strong")),

    # implicit_drift / repeated_use (4)
    _drift(_s(sample_id="p3-drift-ru-tea-blend-001", target_type="object_preference", domain="food",
        target_description="user's morning beverage — old coffee gradually replaced by matcha latte user makes daily",
        target_slot_id="morn_drink::v1", topic="morning_beverage",
        versions=[
            VersionSpec(value="brew a pour-over coffee with the V60 every morning at home", polarity="prefer", session_introduced=1),
            VersionSpec(value="whisk a matcha latte with the bamboo whisk every morning at home", polarity="prefer", session_introduced=2),
        ],
        current_query="It is morning — what do I make as the day's first drink?",
        required_behavior="Whisk a matcha latte with the bamboo whisk.",
        invalid_behavior=["Brew a pour-over coffee"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-grocery-deliv-001", target_type="object_preference", domain="food",
        target_description="user's grocery delivery — old Instacart gradually replaced by neighborhood-CSA-box user picks up weekly",
        target_slot_id="grocery_deliv::v1", topic="weekly_grocery_source",
        versions=[
            VersionSpec(value="order weekly groceries via Instacart with same-day delivery", polarity="prefer", session_introduced=1),
            VersionSpec(value="pick up the neighborhood CSA box every Wednesday afternoon at the local pickup spot", polarity="prefer", session_introduced=2),
        ],
        current_query="It is Tuesday and the fridge is empty — should I queue up Instacart?",
        required_behavior="No; the CSA box pickup tomorrow handles weekly groceries now.",
        invalid_behavior=["Queue up an Instacart order"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-jacket-001", target_type="object_preference", domain="hobby",
        target_description="user's go-to jacket — old waxed-Barbour gradually replaced by hooded-Patagonia user wears daily",
        target_slot_id="jacket::v1", topic="go_to_outerwear",
        versions=[
            VersionSpec(value="wear the waxed Barbour Bedale jacket as the everyday outer layer", polarity="prefer", session_introduced=1),
            VersionSpec(value="wear the hooded Patagonia Torrentshell jacket as the everyday outer layer instead of the Barbour", polarity="prefer", session_introduced=2),
        ],
        current_query="I am about to walk out the door for the morning errands — what goes on my shoulders?",
        required_behavior="The hooded Patagonia Torrentshell jacket.",
        invalid_behavior=["The waxed Barbour Bedale jacket"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    _drift(_s(sample_id="p3-drift-ru-meditation-001", target_type="procedural_constraint", domain="health",
        target_description="user's meditation app — old Headspace gradually replaced by Waking-Up subscription user uses daily",
        target_slot_id="meditation_app::v1", topic="daily_meditation_app",
        versions=[
            VersionSpec(value="run a 10-minute Headspace guided meditation every morning before coffee", polarity="constraint", session_introduced=1),
            VersionSpec(value="run a 15-minute Waking Up daily theory talk every morning before coffee instead of Headspace", polarity="constraint", session_introduced=2),
        ],
        current_query="It is morning — which meditation app do I open?",
        required_behavior="Open the Waking Up app.",
        invalid_behavior=["Open Headspace"],
        failure_patterns=["implicit_drift"], subtype="strong"), "repeated_use"),

    # implicit_drift / abandonment (3)
    _drift(_s(sample_id="p3-drift-aban-pottery-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's pottery class — abandoned after studio closed, no replacement",
        target_slot_id="pottery::v1", topic="weekly_pottery_class_practice",
        versions=[
            VersionSpec(value="attend the weekly pottery class every Thursday evening at the local studio", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop attending pottery class after the studio closed and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Thursday evening — am I packing the apron for class?",
        required_behavior="No; the weekly pottery class has been abandoned.",
        invalid_behavior=["Pack the apron for class"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-newsletter-001", target_type="procedural_constraint", domain="writing",
        target_description="user's biweekly newsletter — abandoned after burnout session, no replacement",
        target_slot_id="newsletter_pub::v1", topic="biweekly_newsletter_practice",
        versions=[
            VersionSpec(value="publish the personal biweekly newsletter on Substack every other Friday afternoon", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop publishing the biweekly newsletter after burnout and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Friday afternoon and a Substack draft notification arrived — publish?",
        required_behavior="No; the biweekly newsletter has been abandoned.",
        invalid_behavior=["Publish the Substack draft this Friday"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    _drift(_s(sample_id="p3-drift-aban-running-club-001", target_type="procedural_constraint", domain="hobby",
        target_description="user's Tuesday running-club — abandoned after schedule conflict, no replacement",
        target_slot_id="run_club::v1", topic="tuesday_running_club_practice",
        versions=[
            VersionSpec(value="attend the Tuesday-evening running club at the park track every week", polarity="constraint", session_introduced=1),
            VersionSpec(value="stop attending the Tuesday running club after the new evening work commitment and never resume the practice", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Tuesday evening — am I lacing up for the running club?",
        required_behavior="No; the running club has been abandoned.",
        invalid_behavior=["Lace up for the running club"],
        failure_patterns=["implicit_drift"], subtype="strong"), "abandonment"),

    # implicit_drift / gradual_narrowing (3)
    _drift(_s(sample_id="p3-drift-gn-blog-pick-001", target_type="object_preference", domain="learning",
        target_description="user's blog reading queue — gradually narrowing without announcement: any blog → only-tech-strategy → only-tech-strategy + paid-subscription",
        target_slot_id="blog_pick::v1", topic="blog_reading_criteria",
        versions=[
            VersionSpec(value="read any blog the user finds interesting in the daily feed reader", polarity="prefer", session_introduced=1),
            VersionSpec(value="read only tech-strategy blogs AND only ones the user pays a subscription for", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a free tech-strategy blog with a great recent post — add to the feed reader?",
        required_behavior="Pass; user reads only tech-strategy blogs that are paid subscriptions.",
        invalid_behavior=["Add the free tech-strategy blog to the feed reader"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-investment-001", target_type="object_preference", domain="finance",
        target_description="user's investment criteria — gradually narrowing without announcement: any sector → tech-only → tech-only + dividend-paying",
        target_slot_id="invest::v1", topic="brokerage_buy_criteria",
        versions=[
            VersionSpec(value="buy any S&P 500 stock the user finds interesting for the brokerage", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only S&P 500 technology-sector stocks AND only ones that pay quarterly dividends", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend recommended a fast-growing S&P 500 tech name with no dividend — buy it for the brokerage?",
        required_behavior="Pass; user buys only S&P 500 tech stocks that pay quarterly dividends.",
        invalid_behavior=["Buy the no-dividend tech stock"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    _drift(_s(sample_id="p3-drift-gn-clothes-001", target_type="object_preference", domain="hobby",
        target_description="user's clothing-purchase rule — gradually narrowing without announcement: any item → only-natural-fibers → only-natural-fibers + secondhand",
        target_slot_id="clothes::v1", topic="clothing_purchase_criteria",
        versions=[
            VersionSpec(value="buy any clothing item that catches the user's eye when shopping", polarity="prefer", session_introduced=1),
            VersionSpec(value="buy only clothing items made of natural fibers AND only secondhand from thrift stores or eBay", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend offered me a brand-new wool sweater at a great price — buy it?",
        required_behavior="Pass; user buys only natural-fiber clothing AND only secondhand.",
        invalid_behavior=["Buy the brand-new wool sweater"],
        failure_patterns=["implicit_drift"], subtype="strong"), "gradual_narrowing"),

    # explicit_replacement (5)
    _trip(_s(sample_id="p3-explicit-task-batch-001", target_type="procedural_constraint", domain="management",
        target_description="user's email-checking — explicitly replaces continuous-checking with three-times-daily-batch",
        target_slot_id="email_check::v1", topic="email_checking_pattern",
        versions=[
            VersionSpec(value="check email inbox continuously throughout the workday whenever a notification appears", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget continuous checking — check email only three times a day at 9am, 1pm, and 5pm with notifications off", polarity="constraint", session_introduced=2),
        ],
        current_query="A new email notification just popped up at 11am — open it?",
        required_behavior="No; emails are checked only at 9am, 1pm, and 5pm now.",
        invalid_behavior=["Open the email notification immediately"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-house-style-001", target_type="conceptual_stance", domain="home",
        target_description="user's home-decor philosophy — explicitly replaces minimalist-white with maximalist-color",
        target_slot_id="house_style::v1", topic="home_decor_philosophy",
        versions=[
            VersionSpec(value="decorate the apartment in minimalist white with no color and bare walls", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the minimalist white look — decorate the apartment in maximalist colors with patterned wallpaper and gallery walls instead", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend offered me a free white couch from her move — accept it for the living room?",
        required_behavior="Pass; the apartment is going maximalist with color now.",
        invalid_behavior=["Accept the white couch"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-evening-snack-001", target_type="object_preference", domain="food",
        target_description="user's evening snack — explicitly replaces dark-chocolate with greek-yogurt-and-berries",
        target_slot_id="eve_snack::v1", topic="evening_snack",
        versions=[
            VersionSpec(value="eat two squares of 70% dark chocolate after dinner every evening", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget the dark chocolate — eat half a cup of plain Greek yogurt with fresh berries after dinner every evening instead", polarity="prefer", session_introduced=2),
        ],
        current_query="It is 9pm after dinner — what is on the snack plate?",
        required_behavior="Half a cup of plain Greek yogurt with fresh berries.",
        invalid_behavior=["Two squares of 70% dark chocolate"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-deploy-flow-001", target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's deploy flow — explicitly replaces Friday-deploys with Tuesday-deploys",
        target_slot_id="deploy_flow::v1", topic="weekly_deploy_day",
        versions=[
            VersionSpec(value="deploy production code on Friday afternoons after lunch every week", polarity="constraint", session_introduced=1),
            VersionSpec(value="forget Friday deploys — deploy production code on Tuesday afternoons after lunch every week to avoid weekend on-call surprises", polarity="constraint", session_introduced=2),
        ],
        current_query="It is Friday and the release branch is ready — push to production?",
        required_behavior="No; production deploys happen on Tuesdays now.",
        invalid_behavior=["Push to production this Friday afternoon"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    _trip(_s(sample_id="p3-explicit-music-app-001", target_type="object_preference", domain="hobby",
        target_description="user's music app — explicitly replaces Apple-Music with Tidal-HiFi",
        target_slot_id="music_app::v1", topic="music_streaming_app",
        versions=[
            VersionSpec(value="stream music on the Apple Music app with the family-share subscription", polarity="prefer", session_introduced=1),
            VersionSpec(value="forget Apple Music — stream music on the Tidal HiFi app for the lossless audio quality instead", polarity="prefer", session_introduced=2),
        ],
        current_query="A friend asked which app to send a playlist link in — what do I tell them?",
        required_behavior="Tell them Tidal.",
        invalid_behavior=["Tell them Apple Music"],
        failure_patterns=["explicit_replacement"], subtype="strong")),

    # narrowing (2)
    _trip(_s(sample_id="p3-narrow-pet-treat-001", target_type="object_preference", domain="home",
        target_description="user's dog treat rule — three explicit narrowings: any treat → grain-free-only → grain-free + freeze-dried",
        target_slot_id="dog_treat::v1", topic="dog_treat_rule",
        versions=[
            VersionSpec(value="give the dog any treat from the pet store as a daily reward", polarity="prefer", session_introduced=1),
            VersionSpec(value="give the dog only grain-free treats as a daily reward, no biscuits with grain", polarity="prefer", session_introduced=2),
            VersionSpec(value="give the dog only grain-free freeze-dried treats as a daily reward, no baked or extruded versions", polarity="prefer", session_introduced=3),
        ],
        current_query="A neighbor offered the dog a grain-free baked biscuit — accept it?",
        required_behavior="Decline; the rule is grain-free AND freeze-dried.",
        invalid_behavior=["Accept any treat", "Accept any grain-free baked treat", "Accept a non-grain-free freeze-dried treat"],
        failure_patterns=["narrowing"], subtype="multi_step")),

    _trip(_s(sample_id="p3-narrow-content-share-001", target_type="procedural_constraint", domain="media",
        target_description="user's social-media-share rule — three explicit narrowings: any → text-only → text-only + with-source-cite",
        target_slot_id="social_share::v1", topic="social_media_share_rule",
        versions=[
            VersionSpec(value="share any content the user finds interesting on Twitter or LinkedIn freely", polarity="constraint", session_introduced=1),
            VersionSpec(value="share only text-form posts on Twitter or LinkedIn, never images or videos", polarity="constraint", session_introduced=2),
            VersionSpec(value="share only text-form posts on Twitter or LinkedIn AND only with a primary-source citation linked in the post", polarity="constraint", session_introduced=3),
        ],
        current_query="A friend sent me a great text quote with no source — share it on Twitter?",
        required_behavior="Pass; the rule is text-only AND with primary-source citation.",
        invalid_behavior=["Share any content freely", "Share any text post", "Share an image with a citation"],
        failure_patterns=["narrowing"], subtype="multi_step")),
]
