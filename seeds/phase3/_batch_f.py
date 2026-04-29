"""Phase 3 batch F — 20 spines, balanced fill.

Target distribution:
  5 repeated_use, 4 narrow, 3 multi triple, 2 multi doublet,
  2 explicit, 3 abandonment, 1 gradual_narrowing
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


PHASE3_BATCH_F: list[Phase3GroupSpec] = [

    # repeated_use (5)
    _drift(_s(
        sample_id="p3-drift-cycling-route-001",
        target_type="object_preference", domain="travel",
        target_description="user's weekend cycling loop — drifted to the river-trail loop from the road circuit, repeated active use",
        target_slot_id="weekend_loop::v1", topic="weekend_cycling_loop",
        versions=[
            VersionSpec(value="40-mile road loop through the suburbs with the descents on Highway 9", polarity="prefer", session_introduced=1),
            VersionSpec(value="35-mile river-trail loop on the dedicated bike path with the bridge crossings", polarity="prefer", session_introduced=2),
        ],
        current_query="Saturday morning forecast looks dry — pick the route.",
        required_behavior="Pick the 35-mile river-trail loop on the dedicated bike path with the bridge crossings.",
        invalid_behavior=["Pick the 40-mile road loop on Highway 9", "Pick a different route", "Skip the ride"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-deep-work-block-001",
        target_type="procedural_constraint", domain="productivity",
        target_description="user's morning deep-work block — drifted to a 6 AM start from a 9 AM start, repeated active use",
        target_slot_id="deep_work_block::v1", topic="morning_deep_work_block",
        versions=[
            VersionSpec(value="9 AM to 11 AM deep-work block right after the morning meetings", polarity="constraint", session_introduced=1),
            VersionSpec(value="6 AM to 8 AM deep-work block before any meetings start", polarity="constraint", session_introduced=2),
        ],
        current_query="Block tomorrow's deep-work time.",
        required_behavior="Block tomorrow's deep-work session for 6 AM to 8 AM, before meetings.",
        invalid_behavior=["Block 9 AM to 11 AM", "Block an evening slot", "Skip blocking"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-team-standup-001",
        target_type="procedural_constraint", domain="management",
        target_description="user's team's standup format — drifted to async-Slack-thread from live-Zoom, repeated active use",
        target_slot_id="team_standup::v1", topic="team_standup_format",
        versions=[
            VersionSpec(value="live Zoom standup at 9:30 AM with everyone unmuted in turn", polarity="constraint", session_introduced=1),
            VersionSpec(value="async Slack-thread standup posted by 10 AM with the three-question template", polarity="constraint", session_introduced=2),
        ],
        current_query="Set up tomorrow morning's daily team check-in.",
        required_behavior="Set up tomorrow's check-in as an async Slack-thread standup posted by 10 AM with the three-question template.",
        invalid_behavior=["Set up a live Zoom standup", "Set up an in-person huddle", "Skip the check-in"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-vacation-package-001",
        target_type="procedural_constraint", domain="travel",
        target_description="user's vacation booking workflow — drifted to a single all-in-one travel agent from DIY booking, repeated active use",
        target_slot_id="vacation_booking::v1", topic="vacation_booking_workflow",
        versions=[
            VersionSpec(value="DIY booking across Booking.com, Skyscanner, and direct hotel sites", polarity="constraint", session_introduced=1),
            VersionSpec(value="single all-in-one travel agent at TravelStore who handles every leg", polarity="constraint", session_introduced=2),
        ],
        current_query="I'm planning the September Italy trip — start the bookings.",
        required_behavior="Start the Italy bookings through the single all-in-one travel agent at TravelStore.",
        invalid_behavior=["Start booking on Booking.com", "Start booking on Skyscanner", "Start booking via direct hotel sites"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    _drift(_s(
        sample_id="p3-drift-handoff-doc-001",
        target_type="conceptual_stance", domain="work_workflow",
        target_description="user's project-handoff doc style — drifted to a one-page checklist from a multi-section narrative, repeated active use",
        target_slot_id="handoff_doc::v1", topic="project_handoff_doc",
        versions=[
            VersionSpec(value="multi-section narrative covering background, decisions, open questions, and next steps", polarity="prefer", session_introduced=1),
            VersionSpec(value="one-page checklist with the open questions and next steps as bullets", polarity="prefer", session_introduced=2),
        ],
        current_query="I'm transferring the Q3 fraud project to Priya — write the handoff.",
        required_behavior="Write the Q3 fraud handoff as a one-page checklist with the open questions and next steps as bullets.",
        invalid_behavior=["Write a multi-section narrative", "Send a video walk-through instead", "Skip the handoff"],
        failure_patterns=["implicit_drift"],
    ), "repeated_use"),

    # narrowing (4)
    _trip(_s(
        sample_id="p3-narrow-app-permissions-001",
        target_type="procedural_constraint", domain="lifestyle",
        target_description="user's app-permissions stance — three explicit narrowings: any access → block-by-default → block-by-default + tracking-disabled",
        target_slot_id="app_permissions::v1", topic="app_permissions_stance",
        versions=[
            VersionSpec(value="grant whatever access an app requests at install", polarity="constraint", session_introduced=1),
            VersionSpec(value="block all permissions by default and grant only on demand", polarity="constraint", session_introduced=2),
            VersionSpec(value="block all permissions by default, grant only on demand, and disable tracking system-wide", polarity="constraint", session_introduced=3),
        ],
        current_query="A new mapping app wants location and contacts access — what do I tell it?",
        required_behavior="Block both location and contacts by default; grant only on demand; tracking remains disabled system-wide.",
        invalid_behavior=["Grant location and contacts at install", "Grant location only", "Grant contacts only"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-clothing-buy-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's clothing purchase rule — three explicit narrowings: any item → secondhand-or-sustainable → secondhand-only",
        target_slot_id="clothing_purchase::v1", topic="clothing_purchase_rule",
        versions=[
            VersionSpec(value="any clothing item that catches the user's eye and fits the budget", polarity="prefer", session_introduced=1),
            VersionSpec(value="only secondhand clothing or items from a certified sustainable brand", polarity="prefer", session_introduced=2),
            VersionSpec(value="only secondhand clothing — no new items even from sustainable brands", polarity="prefer", session_introduced=3),
        ],
        current_query="My winter coat is past saving — pick a replacement.",
        required_behavior="Pick a secondhand winter coat replacement.",
        invalid_behavior=["Pick a new coat from a sustainable brand", "Pick a new coat from any brand", "Suggest going without a coat"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-1on1-agenda-001",
        target_type="conceptual_stance", domain="management",
        target_description="user's report 1:1 agenda style — three explicit narrowings: any topic → report-led only → report-led with a single growth-question",
        target_slot_id="onon_agenda::v1", topic="report_1on1_agenda_style",
        versions=[
            VersionSpec(value="any topic the user or report brings up at the moment", polarity="prefer", session_introduced=1),
            VersionSpec(value="report-led only — the report sets the agenda each time", polarity="prefer", session_introduced=2),
            VersionSpec(value="report-led plus a single growth-oriented question from the user at the end", polarity="prefer", session_introduced=3),
        ],
        current_query="Marcus's 1:1 is on the books for tomorrow — frame the conversation.",
        required_behavior="Frame Marcus's 1:1 as report-led with a single growth-oriented question from the user at the end.",
        invalid_behavior=["Frame any-topic discussion", "Frame report-led only without a growth question", "Frame manager-led with talking points"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-narrow-class-attendance-001",
        target_type="procedural_constraint", domain="learning",
        target_description="user's evening adult-ed enrollment — three explicit narrowings: any class → certified-instructor → certified-instructor + small-group",
        target_slot_id="adult_ed::v1", topic="adult_ed_enrollment",
        versions=[
            VersionSpec(value="any adult-ed class the community center offers", polarity="constraint", session_introduced=1),
            VersionSpec(value="only classes taught by a certified instructor", polarity="constraint", session_introduced=2),
            VersionSpec(value="only classes taught by a certified instructor with class size capped at 8", polarity="constraint", session_introduced=3),
        ],
        current_query="The fall catalog just dropped — sign me up for one class.",
        required_behavior="Sign the user up for a fall class taught by a certified instructor with class size capped at 8.",
        invalid_behavior=["Sign up for a 25-person beginner class", "Sign up for a class without checking instructor certification", "Sign up for a peer-led workshop"],
        failure_patterns=["narrowing"], subtype="multi_step",
    )),

    # multi_version triple (3)
    _trip(_s(
        sample_id="p3-multi-translation-tool-001",
        target_type="object_preference", domain="learning",
        target_description="user's translation tool — three-version chain: Google Translate → DeepL → ChatGPT custom GPT",
        target_slot_id="translation_tool::v1", topic="translation_tool",
        versions=[
            VersionSpec(value="Google Translate web with the document upload", polarity="prefer", session_introduced=1),
            VersionSpec(value="DeepL Pro with the formality toggle and glossary", polarity="prefer", session_introduced=2),
            VersionSpec(value="ChatGPT custom GPT named 'Spanish Tutor' with the contextual rewrites", polarity="prefer", session_introduced=3),
        ],
        current_query="Translate this two-page proposal into Spanish for the client.",
        required_behavior="Translate the proposal using the ChatGPT custom GPT 'Spanish Tutor' with contextual rewrites.",
        invalid_behavior=["Translate via Google Translate", "Translate via DeepL Pro", "Translate manually with a dictionary"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-multi-meditation-app-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's meditation app — three-version chain: Headspace → Calm → Waking Up",
        target_slot_id="meditation_app::v1", topic="meditation_app",
        versions=[
            VersionSpec(value="Headspace with the basics-pack 10-day series", polarity="prefer", session_introduced=1),
            VersionSpec(value="Calm with the Daily Calm session and sleep stories", polarity="prefer", session_introduced=2),
            VersionSpec(value="Waking Up with the Sam Harris guided practice library", polarity="prefer", session_introduced=3),
        ],
        current_query="Queue tonight's wind-down session.",
        required_behavior="Queue tonight's wind-down from the Waking Up Sam Harris guided practice library.",
        invalid_behavior=["Queue from Headspace", "Queue from Calm", "Queue a free YouTube guided session"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _trip(_s(
        sample_id="p3-multi-travel-payments-001",
        target_type="object_preference", domain="travel",
        target_description="user's travel-spending account — three-version chain: USD checking → Wise multi-currency → Revolut Premium",
        target_slot_id="travel_spending_account::v1", topic="travel_spending_account",
        versions=[
            VersionSpec(value="USD checking account with the foreign-transaction fee waived", polarity="prefer", session_introduced=1),
            VersionSpec(value="Wise multi-currency account with the borderless debit card", polarity="prefer", session_introduced=2),
            VersionSpec(value="Revolut Premium account with the metal card and travel insurance", polarity="prefer", session_introduced=3),
        ],
        current_query="Pre-load the trip funds before leaving for Lisbon.",
        required_behavior="Pre-load the Lisbon trip funds into the Revolut Premium account using the metal card.",
        invalid_behavior=["Pre-load the USD checking account", "Pre-load the Wise multi-currency account", "Carry physical cash only"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    # multi_version doublet (2)
    _doub(_s(
        sample_id="p3-multi-runtime-4v-001",
        target_type="procedural_constraint", domain="tech_workflow",
        target_description="team's serverless runtime — four-version chain: Lambda Node 14 → Lambda Node 18 → Lambda Python → Cloudflare Workers",
        target_slot_id="serverless_runtime::v1", topic="serverless_runtime",
        versions=[
            VersionSpec(value="AWS Lambda on Node.js 14 with the legacy bundler", polarity="prefer", session_introduced=1),
            VersionSpec(value="AWS Lambda on Node.js 18 with the ESM module support", polarity="prefer", session_introduced=2),
            VersionSpec(value="AWS Lambda on Python 3.11 with the SAM build pipeline", polarity="prefer", session_introduced=3),
            VersionSpec(value="Cloudflare Workers with the Wrangler CLI deployment", polarity="prefer", session_introduced=4),
        ],
        current_query="Stand up the new image-resize endpoint for the marketing site.",
        required_behavior="Stand up the image-resize endpoint on Cloudflare Workers using the Wrangler CLI deployment.",
        invalid_behavior=["Deploy on Lambda Node.js 14", "Deploy on Lambda Node.js 18", "Deploy on Lambda Python 3.11"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    _doub(_s(
        sample_id="p3-multi-side-project-stack-4v-001",
        target_type="procedural_constraint", domain="tech_workflow",
        target_description="user's side-project web stack — four-version chain across full-stack rewrites",
        target_slot_id="side_project_stack::v1", topic="side_project_web_stack",
        versions=[
            VersionSpec(value="Rails 6 with PostgreSQL and Heroku deployment", polarity="prefer", session_introduced=1),
            VersionSpec(value="Next.js 12 with Supabase and Vercel deployment", polarity="prefer", session_introduced=2),
            VersionSpec(value="SvelteKit with Turso and Fly.io deployment", polarity="prefer", session_introduced=3),
            VersionSpec(value="Astro with the islands architecture, Cloudflare D1, and Cloudflare Pages deployment", polarity="prefer", session_introduced=4),
        ],
        current_query="Spin up the scaffold for the new recipe-bookmark side project.",
        required_behavior="Spin up the recipe-bookmark side project on Astro with islands architecture, Cloudflare D1, and Cloudflare Pages deployment.",
        invalid_behavior=["Spin up on Rails 6 + PostgreSQL + Heroku", "Spin up on Next.js 12 + Supabase + Vercel", "Spin up on SvelteKit + Turso + Fly.io"],
        failure_patterns=["multi_version"], subtype="multi_step",
    )),

    # explicit (2)
    _trip(_s(
        sample_id="p3-explicit-vpn-service-001",
        target_type="object_preference", domain="lifestyle",
        target_description="user's VPN service — explicit replacement of NordVPN with Mullvad",
        target_slot_id="vpn_service::v1", topic="vpn_service",
        versions=[
            VersionSpec(value="NordVPN with the standard subscription tier", polarity="prefer", session_introduced=1),
            VersionSpec(value="Mullvad with the cash-paid anonymous account number", polarity="prefer", session_introduced=2),
        ],
        current_query="Set up secure browsing on the new work laptop.",
        required_behavior="Set up Mullvad on the new work laptop using the cash-paid anonymous account number.",
        invalid_behavior=["Set up NordVPN", "Set up a free VPN", "Skip the VPN entirely"],
        failure_patterns=["explicit_replacement"],
    )),

    _trip(_s(
        sample_id="p3-explicit-yoga-studio-001",
        target_type="object_preference", domain="fitness",
        target_description="user's yoga studio — explicit replacement of CorePower with a local independent Iyengar studio",
        target_slot_id="yoga_studio::v1", topic="yoga_studio",
        versions=[
            VersionSpec(value="CorePower Yoga with the chain-wide unlimited membership", polarity="prefer", session_introduced=1),
            VersionSpec(value="Park Slope Iyengar studio with the alignment-focused weekly class card", polarity="prefer", session_introduced=2),
        ],
        current_query="Book my Saturday yoga class.",
        required_behavior="Book the Saturday class at the Park Slope Iyengar studio using the alignment-focused weekly class card.",
        invalid_behavior=["Book at CorePower Yoga", "Book a different yoga chain", "Skip the class"],
        failure_patterns=["explicit_replacement"],
    )),

    # abandonment (3)
    _drift(_s(
        sample_id="p3-drift-physical-mail-storage-001",
        target_type="procedural_constraint", domain="lifestyle",
        target_description="user's bill and document storage — abandoned the filing cabinet; everything scanned to encrypted cloud now",
        target_slot_id="document_storage::v1", topic="document_storage",
        versions=[
            VersionSpec(value="paper filing cabinet in the home office with the labeled hanging folders", polarity="constraint", session_introduced=1),
            VersionSpec(value="encrypted cloud archive with the scanned PDFs and tag metadata", polarity="constraint", session_introduced=2),
        ],
        current_query="The new health-insurance card came in the mail — where does it go?",
        required_behavior="Scan the health-insurance card to the encrypted cloud archive and tag it with the right metadata.",
        invalid_behavior=["File it in the paper filing cabinet", "Stick it on the fridge", "Throw it away"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    _drift(_s(
        sample_id="p3-drift-paper-calendar-001",
        target_type="object_preference", domain="productivity",
        target_description="user's planning system — abandoned the paper calendar; everything in Fantastical now",
        target_slot_id="planning_system::v1", topic="planning_system",
        versions=[
            VersionSpec(value="Hobonichi paper planner with the daily one-page layout", polarity="prefer", session_introduced=1),
            VersionSpec(value="Fantastical with the natural-language event entry and proposal-time integration", polarity="prefer", session_introduced=2),
        ],
        current_query="Marcus suggested coffee Thursday at 3 — get it on my schedule.",
        required_behavior="Add Thursday 3 PM coffee with Marcus to Fantastical using the natural-language event entry.",
        invalid_behavior=["Write it in the Hobonichi paper planner", "Email yourself a reminder", "Trust your memory"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    _drift(_s(
        sample_id="p3-drift-cooking-class-001",
        target_type="procedural_constraint", domain="learning",
        target_description="user's cooking-skill source — abandoned the in-person cooking class; YouTube channel binge-watching only now",
        target_slot_id="cooking_skill_source::v1", topic="cooking_skill_source",
        versions=[
            VersionSpec(value="weekly in-person cooking class at the culinary school with the chef instructor", polarity="constraint", session_introduced=1),
            VersionSpec(value="YouTube binge-watching of the Adam Ragusea and J. Kenji López-Alt channels", polarity="constraint", session_introduced=2),
        ],
        current_query="I want to learn knife skills properly this month — how?",
        required_behavior="Learn knife skills by binge-watching the Adam Ragusea and J. Kenji López-Alt YouTube channels.",
        invalid_behavior=["Sign up for an in-person cooking class", "Hire a private chef tutor", "Read a cookbook only"],
        failure_patterns=["implicit_drift"],
    ), "abandonment"),

    # gradual_narrowing (1)
    _drift(_s(
        sample_id="p3-drift-charity-narrow-001",
        target_type="conceptual_stance", domain="lifestyle",
        target_description="user's volunteering criteria — gradually narrowed from any community-service opportunity to weekly literacy tutoring at a single school via cumulative preference",
        target_slot_id="volunteer_criteria::v1", topic="volunteer_criteria",
        versions=[
            VersionSpec(value="any community-service opportunity that fits the calendar", polarity="prefer", session_introduced=1),
            VersionSpec(value="weekly literacy tutoring at a single neighborhood elementary school", polarity="prefer", session_introduced=2),
        ],
        current_query="The food bank is looking for Saturday volunteers — am I going?",
        required_behavior="Decline the food-bank Saturday slot; the weekly commitment is literacy tutoring at the neighborhood elementary school.",
        invalid_behavior=["RSVP yes to the food-bank slot", "Volunteer at both", "Suggest skipping volunteer time entirely"],
        failure_patterns=["implicit_drift"],
    ), "gradual_narrowing"),
]
