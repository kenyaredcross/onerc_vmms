# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A worked Kenya Red Cross Society *operation*. Demo data, never behaviour.

    bench --site <site> execute vmmsx.seed.kenya_operations.main

`kenya.py` seeds a society's **configuration** — its ladder, its roles, its
membership types, the workflows that govern them. This seeds what that society
would then be *doing*: programmes, terms of reference, needs advertised on the
notice board, events in the diary, and announcements sent from a county.

**It no longer seeds people, and that is the point of the site it builds.** The
demo volunteers, their memberships, their rosters, their hours and their
certifications were all removed from this file: the site it now produces is one
where every register and every queue starts empty, because it is stood up for
acceptance testing and those records are what the testing is *about*. Seeding
them would mean the registration and the decision on it had already happened
offstage. `kenya.promote_coordinator` gives a coordinator who has signed up for
their own account standing over a county; everything else is done by whoever is
testing. The newsroom moved out too, to `kenya_stories.py`, and the
opportunities board lives in `kenya_jobs.py`.

The two are separate files because they answer different questions and keep
different company. Configuration is what a society holds; an operation is what
it did last month, and an empty portal demonstrates nothing. Note that
`kenya.py` deliberately seeds **no certification type**, on the grounds that
neither this app nor that seed has any business inventing a real qualification.
This file does invent them, and the distinction is that everything here is
openly demo material for a demo society: a real society deletes the lot and
enters its own.

**It requires `kenya.py` to have run.** Everything here hangs off that society's
geo nodes and roles, and they are read *by shape* through `kenya.county()` and
`kenya.county_named()` rather than by docname — the same way that seed recognises its
own nodes. Nothing here is seeded if the society is not there; the step reports
a skip and the run continues.

**Idempotent, and it says what it did.** Every step checks before it writes, so
running it twice changes nothing. Where a doctype names itself opaquely, the
check is a lookup on the shape of the row: a deployment request is the same
request when its terms, its anchor and its period all match.

**The elevation is the one `kenya.py` already uses.** `ignore_permissions=True`
on the inserts: a seed runs as Administrator from the bench, creating a
society's own records on its behalf, and nothing in this module is reachable
from a request.

**What it deliberately does not do.**

* **No photograph is attached to anything.** An event with an invented banner
  looks finished and is not, and the portal draws a placeholder for an empty
  image slot precisely so that a seed does not have to lie about one.
* **No terms of reference is routed.** Every one below uses `direct` mode,
  because a routed request needs a `VMMS Approval Workflow` governing
  `VMMS Deployment Request` and this society has not configured one. A routed
  request without a workflow never settles, so it would never reach the notice
  board — correct behaviour, and a poor demonstration.
* **No money.** Stipends and membership fees belong to `onerc_payments` and to
  a gateway a demo bench does not have.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.seed import kenya, mission

# --- what a society records as a qualification ----------------------------
#
# `validity_days` of 0 means it never expires. `blocks` is whether a lapse of
# this kind *costs* anything — the difference between a reminder and the reason
# somebody cannot be sent.

CERTIFICATION_TYPES = (
	{
		"key": "first-aid",
		"name": "First Aid",
		"validity_days": 730,
		"blocks": True,
		"description": "Standard first aid certificate. Required before any front-line deployment.",
	},
	{
		"key": "psychological-first-aid",
		"name": "Psychological First Aid",
		"validity_days": 1095,
		"blocks": False,
		"description": "Supporting people in distress in the hours after an emergency.",
	},
	{
		"key": "water-safety",
		"name": "Water Safety and Rescue",
		"validity_days": 730,
		"blocks": True,
		"description": "Swift water awareness and shore-based rescue. Required for flood response.",
	},
	{
		"key": "emergency-driving",
		"name": "Emergency Response Driving",
		"validity_days": 1095,
		"blocks": True,
		"description": "Ambulance and response vehicle handling under emergency conditions.",
	},
	{
		"key": "blood-donor-care",
		"name": "Blood Donor Care",
		"validity_days": 365,
		"blocks": False,
		"description": "Donor reception, screening support and post-donation care.",
	},
)

# --- how a society classifies the time its volunteers give -----------------
#
# An open vocabulary on which no code anywhere branches.
# `patches/setup_volunteer_module.py` already seeds a starting three — training,
# community_event, operations_support — and says in as many words that a society
# owns it from then on. So this adds the two a Red Cross society would obviously
# want and reuses the rest rather than shipping a near-duplicate of each: a
# picker offering both "Training" and "Training delivered" is a picker nobody can
# answer correctly.

TIME_LOG_CATEGORIES = (
	(
		"emergency_response",
		"Emergency Response",
		"Time given on an active emergency or its immediate aftermath.",
	),
	("blood_drive", "Blood Donation Drive", "Donor reception, screening support and post-donation care."),
)

# --- the programmes some of this work is written under ---------------------
#
# The programmes postdate the rest of this file: terms of reference were seeded
# before a project existed to write them under. They are ERPNext `Project`
# records now — `VMMS Project` was retired for it — and **every** terms of
# reference belongs to one, which is the part that changed: a mission document
# cannot be submitted without a programme. The standing duties that used to have
# none are written under a standing-services programme instead, which is that
# argument answered rather than abandoned. See `seed/mission.py`.

PROJECTS = (
	{
		"key": "nairobi-flood-response-2026",
		"name": "Nairobi Flood Response 2026",
		"where": ("county", "Nairobi"),
		"status": "Active",
		"start_in": -14,
		"end_in": 30,
		"summary": (
			"The society's coordinated response to the 2026 long rains: evacuation support, relief"
			" distribution and temporary shelter across Nairobi county's flood-affected branches."
		),
	},
	{
		"key": "community-health-safety-2026",
		"name": "Community Health & Safety Programme",
		"where": ("county", "Nairobi"),
		"status": "Planned",
		"start_in": 7,
		"end_in": 120,
		"summary": (
			"A branch-led programme of household health outreach and road safety campaigning,"
			" running through the last quarter of the year."
		),
	},
)

# --- the work a society asks for ------------------------------------------
#
# Every one of these is `direct` mode; see the module docstring for why. The
# certifications named must exist above, and the mandatory ones are what the
# opportunity card shows as a requirement. `project`, where present, is one of
# `PROJECTS`' own keys, resolved by `_project()` the same way `where` is
# resolved by `_where()`.

TERMS = (
	{
		"key": "flood-response",
		"name": "Flood Response Team",
		"project": "nairobi-flood-response-2026",
		"purpose": (
			"Search, evacuation support and relief distribution in communities cut off by seasonal flooding."
		),
		"responsibilities": (
			"Assist with household evacuation and headcount.\n"
			"Distribute relief items against the branch register.\n"
			"Report needs and hazards back to the branch operations desk daily."
		),
		"duration_days": 14,
		"requires": (("water-safety", True), ("first-aid", True)),
	},
	{
		"key": "blood-drive-support",
		"name": "Blood Drive Support",
		"purpose": "Running the reception, refreshment and recovery areas at a mobile blood drive.",
		"responsibilities": (
			"Register donors and direct them through the drive.\n"
			"Staff the refreshment and recovery area.\n"
			"Watch for and escalate any donor who becomes unwell."
		),
		"duration_days": 2,
		"requires": (("blood-donor-care", False),),
	},
	{
		"key": "event-first-aid",
		"name": "Event First Aid Post",
		"purpose": "Staffing a first aid post at a public event under a branch first aider.",
		"responsibilities": (
			"Staff the first aid post for the duration of the event.\n"
			"Treat minor injuries and refer anything beyond scope.\n"
			"Keep the treatment log and hand it to the branch afterwards."
		),
		"duration_days": 1,
		"requires": (("first-aid", True),),
	},
	{
		"key": "community-health",
		"name": "Community Health Outreach",
		"project": "community-health-safety-2026",
		"purpose": (
			"Household and school visits on a branch health campaign — hygiene, immunisation"
			" awareness and referral."
		),
		"responsibilities": (
			"Visit households on the round the branch has planned.\n"
			"Deliver the campaign's key messages as written.\n"
			"Refer anybody who needs care to the nearest facility and record it."
		),
		"duration_days": 5,
		"requires": (("psychological-first-aid", False),),
	},
	{
		"key": "road-safety",
		"name": "Road Safety Campaign",
		"project": "community-health-safety-2026",
		"purpose": "Public awareness at matatu stages and schools ahead of the December travel season.",
		"responsibilities": (
			"Run stage-side awareness sessions with the branch team.\n"
			"Distribute campaign materials and record reach.\n"
			"Support the schools programme where scheduled."
		),
		"duration_days": 7,
		"requires": (),
	},
	{
		"key": "shelter-support",
		"name": "Emergency Shelter Support",
		"project": "nairobi-flood-response-2026",
		"purpose": "Setting up and running a temporary reception centre for displaced households.",
		"responsibilities": (
			"Set up sleeping, washing and feeding areas to the branch standard.\n"
			"Register arriving households and track occupancy.\n"
			"Refer protection and health concerns to the branch lead the same day."
		),
		"duration_days": 10,
		"requires": (("first-aid", False), ("psychological-first-aid", False)),
	},
)

# --- what the society is currently asking for ------------------------------
#
# `where` is ("county"|"branch", index) resolved through `kenya.py`'s own
# lookups. `from_in` / `until_in` are days from today, so a re-run months later
# still produces a board with work on it rather than a page of expired needs.
# One request ships unpublished, deliberately: `is_published` is the whole of
# the notice board's read rule, and a demo in which everything is visible does
# not show that.

REQUESTS = (
	{
		"terms": "flood-response",
		"where": ("county", "Nairobi"),
		"volunteers": 12,
		"from_in": 4,
		"until_in": 18,
		"published": True,
		"justification": "Long rains forecast for the fortnight; two wards already reporting displacement.",
	},
	{
		"terms": "blood-drive-support",
		"where": ("county", "Kisumu"),
		"volunteers": 6,
		"from_in": 9,
		"until_in": 10,
		"published": True,
		"justification": "Mobile drive with the national blood service at the Westgate concourse.",
	},
	{
		"terms": "event-first-aid",
		"where": ("county", "Nairobi"),
		"volunteers": 4,
		"from_in": 12,
		"until_in": 12,
		"published": True,
		"justification": "Nairobi marathon feeder route; the organisers have asked for a staffed post.",
	},
	{
		"terms": "community-health",
		"where": ("county", "Mombasa"),
		"volunteers": 20,
		"from_in": 20,
		"until_in": 25,
		"published": True,
		"justification": "Coastal hygiene campaign following the county health department's request.",
	},
	{
		"terms": "road-safety",
		"where": ("county", "Nairobi"),
		"volunteers": 15,
		"from_in": 30,
		"until_in": 37,
		"published": True,
		"justification": "December travel season campaign, run jointly with the county transport office.",
	},
	{
		"terms": "shelter-support",
		"where": ("county", "Kisumu"),
		"volunteers": 8,
		"from_in": 2,
		"until_in": 12,
		"published": True,
		"justification": "Reception centre standing up after the Mathare fire; households still arriving.",
	},
	{
		"terms": "shelter-support",
		"where": ("county", "Nairobi"),
		"volunteers": 30,
		"from_in": 45,
		"until_in": 75,
		# Left unpublished on purpose. It is a real request the branch is
		# planning; nobody has decided to advertise it, so the board must not
		# show it. That is the boundary, and it is a field on this record.
		"published": False,
		"justification": "Contingency capacity for the short rains. Not advertised until the budget is confirmed.",
	},
)

# --- the diary -------------------------------------------------------------
#
# Buzz owns events; vmmsx only reads the published ones. These are seeded into
# Buzz's own doctypes because that is where an event lives, and the portal reads
# them through the one-way seam in `vmmsx/buzz/services/events.py`.

EVENT_HOST = "Kenya Red Cross Society"

EVENT_CATEGORIES = (
	("Training", "Courses and refreshers run for volunteers and the public."),
	("Community", "Open days, campaigns and public health activities."),
	("Blood Donation", "Mobile and static blood donation drives."),
	("Fundraising", "Events raising funds for the society's work."),
	("Recruitment", "Open sessions for people thinking about volunteering."),
	("Simulation", "Rehearsed responses, run against a scenario."),
)

# Buildings, not rungs. These are the names KRCS's own offices go by, which is
# why several of them still say "Branch" while the geo ladder does not: a venue
# is a place with an address, and renaming somebody's building to match a level
# key would also break idempotence on every site already seeded.
EVENT_VENUES = (
	("KRCS Headquarters", "South C, Red Cross Road, Nairobi"),
	("Nairobi Central Branch Hall", "Haile Selassie Avenue, Nairobi"),
	("Mombasa Branch Office", "Moi Avenue, Mombasa"),
	("Kisumu Branch Office", "Oginga Odinga Street, Kisumu"),
	("Nakuru Branch Office", "Kenyatta Avenue, Nakuru"),
	("Eldoret Branch Office", "Oloo Street, Eldoret"),
	("Garissa Branch Office", "Kismayu Road, Garissa"),
	("Lodwar Branch Office", "Kenyatta Street, Lodwar"),
	("Online", "Delivered over video conference"),
)

EVENTS = (
	{
		# Titles carry no dash: Buzz builds an event's route from its title with
		# `cleanup_page_name`, which keeps a dash it does not recognise, and
		# `/b/first-aid-at-work-—-two-day-certificate` is not a URL to put on a
		# screen in front of anybody.
		"title": "First Aid at Work: two day certificate",
		"category": "Training",
		"venue": "KRCS Headquarters",
		"medium": "In Person",
		"start_in": 6,
		"end_in": 7,
		"start_time": "08:30:00",
		"end_time": "16:30:00",
		"where": ("county", "Nairobi"),
		"summary": "The standard two day certificate, assessed on the second afternoon. Open to volunteers and the public.",
	},
	{
		"title": "World Blood Donor Day drive",
		"category": "Blood Donation",
		"venue": "Nairobi Central Branch Hall",
		"medium": "In Person",
		"start_in": 11,
		"end_in": None,
		"start_time": "09:00:00",
		"end_time": "17:00:00",
		"where": ("county", "Nairobi"),
		"summary": "Walk-in donation with the national blood transfusion service. Bring identification.",
	},
	{
		"title": "Psychological First Aid refresher",
		"category": "Training",
		"venue": "Online",
		"medium": "Online",
		"start_in": 15,
		"end_in": None,
		"start_time": "14:00:00",
		"end_time": "17:00:00",
		# No anchor at all, on purpose: BUZZ-01 made the geo field optional, and
		# an event with no placement is shown to everybody rather than filtered
		# out. An online session is exactly that case.
		"where": None,
		"summary": "A half day online refresher for anybody holding the certificate, ahead of the rains.",
	},
	{
		"title": "Mombasa branch open day",
		"category": "Community",
		"venue": "Mombasa Branch Office",
		"medium": "In Person",
		"start_in": 22,
		"end_in": None,
		"start_time": "10:00:00",
		"end_time": "16:00:00",
		"where": ("county", "Mombasa"),
		"summary": "Meet the branch team, see the response vehicles, and find out what volunteering here involves.",
	},
	{
		"title": "Volunteer induction for the Nairobi intake",
		"category": "Training",
		"venue": "Nairobi Central Branch Hall",
		"medium": "In Person",
		"start_in": 28,
		"end_in": None,
		"start_time": "09:00:00",
		"end_time": "13:00:00",
		"where": ("county", "Nairobi"),
		"summary": "Everything a newly accepted volunteer needs before their first deployment. Attendance is expected.",
	},
	{
		"title": "Annual charity run",
		"category": "Fundraising",
		"venue": "KRCS Headquarters",
		"medium": "In Person",
		"start_in": 44,
		"end_in": None,
		"start_time": "06:30:00",
		"end_time": "12:00:00",
		"where": ("county", "Nairobi"),
		"summary": "Ten kilometres through South C, raising funds for the branch emergency response fund.",
	},
	{
		"title": "Kisumu volunteer open evening",
		"category": "Recruitment",
		"venue": "Kisumu Branch Office",
		"medium": "In Person",
		"start_in": 9,
		"end_in": None,
		"start_time": "17:30:00",
		"end_time": "19:30:00",
		"where": ("county", "Kisumu"),
		"summary": "Two hours, no commitment. What the county actually needs, what the training involves, and how to apply.",
	},
	{
		"title": "Water and sanitation refresher for the long rains",
		"category": "Training",
		"venue": "Garissa Branch Office",
		"medium": "In Person",
		"start_in": 13,
		"end_in": 14,
		"start_time": "08:00:00",
		"end_time": "16:00:00",
		"where": ("county", "Garissa"),
		"summary": "Two days for anybody holding the certificate, run ahead of the rains. Bring your certification number.",
	},
	{
		"title": "Nakuru county show first aid duty briefing",
		"category": "Training",
		"venue": "Nakuru Branch Office",
		"medium": "In Person",
		"start_in": 18,
		"end_in": None,
		"start_time": "18:00:00",
		"end_time": "20:00:00",
		"where": ("county", "Nakuru"),
		"summary": "Shift pattern, kit list and the pairing rule, for everybody rostered on the show.",
	},
	{
		"title": "Mass casualty simulation: Eldoret",
		"category": "Simulation",
		"venue": "Eldoret Branch Office",
		"medium": "In Person",
		"start_in": 25,
		"end_in": None,
		"start_time": "07:00:00",
		"end_time": "15:00:00",
		"where": ("county", "Uasin Gishu"),
		"summary": "A full-day rehearsed road traffic scenario with the county health team. Rostered volunteers only.",
	},
	{
		"title": "Mobile blood drive: Lodwar",
		"category": "Blood Donation",
		"venue": "Lodwar Branch Office",
		"medium": "In Person",
		"start_in": 31,
		"end_in": 32,
		"start_time": "09:00:00",
		"end_time": "16:00:00",
		"where": ("county", "Turkana"),
		"summary": "Two days with the national blood transfusion service. Screening desk first, then registration.",
	},
	{
		"title": "Community health volunteer induction: Coast",
		"category": "Training",
		"venue": "Mombasa Branch Office",
		"medium": "In Person",
		"start_in": 37,
		"end_in": 38,
		"start_time": "09:00:00",
		"end_time": "15:30:00",
		"where": ("county", "Mombasa"),
		"summary": "Household registers, growth monitoring and referral, for new community health volunteers across the coast counties.",
	},
	{
		"title": "Safeguarding and code of conduct: annual session",
		"category": "Training",
		"venue": "Online",
		"medium": "Online",
		"start_in": 20,
		"end_in": None,
		"start_time": "10:00:00",
		"end_time": "12:00:00",
		# Unplaced on purpose, like the psychological first aid refresher above:
		# an annual session every volunteer in the country has to sit is not a
		# county's event, and BUZZ-01 made the geo field optional for exactly this.
		"where": None,
		"summary": "Two hours, required annually of every volunteer. Recorded, but attendance is taken live.",
	},
	# Two that have already happened. A diary whose earliest entry is next week
	# is a diary installed last night, and the portal's past-events view has
	# nothing to render without them.
	{
		"title": "First Aid at Work: two day certificate (March sitting)",
		"category": "Training",
		"venue": "KRCS Headquarters",
		"medium": "In Person",
		"start_in": -38,
		"end_in": -37,
		"start_time": "08:30:00",
		"end_time": "16:30:00",
		"where": ("county", "Nairobi"),
		"summary": "The March sitting of the standard two day certificate. Twenty-two candidates, twenty passes.",
	},
	{
		"title": "Kisumu lakeside clean-up and health campaign",
		"category": "Community",
		"venue": "Kisumu Branch Office",
		"medium": "In Person",
		"start_in": -61,
		"end_in": None,
		"start_time": "08:00:00",
		"end_time": "13:00:00",
		"where": ("county", "Kisumu"),
		"summary": "A morning on the lakeshore with four schools, a clean-up and a hygiene talk. Around 300 people came.",
	},
)

# --- what a branch has told people -----------------------------------------

ANNOUNCEMENT_TYPES = (
	("Operational", "Something happening now that volunteers need to know about."),
	("Training", "Courses, refreshers and anything with a place to book."),
	("Notice", "General branch and society notices."),
)

ANNOUNCEMENTS = (
	{
		"title": "Flood response standing up in Nairobi",
		"type": "Operational",
		"urgency": "urgent",
		"audience": "volunteers",
		"where": ("county", "Nairobi"),
		"summary": "Two wards reporting displacement. The branch needs flood-trained volunteers from Monday.",
		"body": (
			"The long rains have displaced households in two wards and the branch is standing up a"
			" response from Monday morning.\n\n"
			"If you hold a current water safety certificate and are available for any part of the"
			" fortnight, tell your branch coordinator today. The opportunity is on the board with the"
			" dates and the requirements.\n\n"
			"If you are not flood trained, the shelter support need at Nairobi West is open as well and"
			" asks for first aid only."
		),
		"link_label": "See the opportunities",
		"link_href": "/portal/opportunities",
	},
	{
		"title": "First aid certificates expiring this quarter",
		"type": "Training",
		"urgency": "important",
		"audience": "volunteers",
		"where": ("county", "Nairobi"),
		"summary": "Check your training page. A lapsed first aid certificate stops you being deployed.",
		"body": (
			"A number of first aid certificates in this county expire before the end of the quarter.\n\n"
			"Your own expiry dates are on your training page, and anything lapsed is marked there. A"
			" lapsed first aid certificate blocks deployment, so please book onto the two day"
			" certificate course before yours runs out.\n\n"
			"The next sitting is at headquarters and is listed under events."
		),
		"link_label": "Check your training",
		"link_href": "/portal/training",
	},
	{
		"title": "Branch office closed for stock take",
		"type": "Notice",
		"urgency": "routine",
		"audience": "everyone",
		"where": ("county", "Nairobi"),
		"summary": "The Nairobi Central office is closed to visitors on Friday while we count the store.",
		"body": (
			"The branch office will be closed to visitors this Friday while the annual stock take is"
			" carried out.\n\n"
			"Emergency response is unaffected and the duty phone is staffed as usual. Anybody who was"
			" coming in to collect kit, please make it Thursday or the following Monday."
		),
		"link_label": None,
		"link_href": None,
	},
)


def main(commit: bool = True) -> dict:
	"""Seed the society's operations and report what changed. Safe to re-run.

	`commit` matches `kenya.main`'s argument and exists for the same reason: the
	bench path needs the writes to persist, and a test running this for real
	must not escape the transaction the runner rolls back.
	"""
	if not kenya.primary_county():
		report = {"society": [{"key": "kenya.py", "status": "skipped: run vmmsx.seed.kenya.main first"}]}
		_print(report)
		return report

	report = {
		"workflow_reconciliation": _reconcile_workflows(),
		"certification_types": _certification_types(),
		"time_log_categories": _time_log_categories(),
		"time_log_permission": _time_log_permission(),
		"projects": _projects(),
		"terms_of_reference": _terms(),
		"deployment_requests": _requests(),
		"event_setup": _event_setup(),
		"events": _events(),
		"announcement_types": _announcement_types(),
		"announcements": _announcements(),
	}

	report["manual_steps"] = MANUAL_STEPS

	if commit:
		frappe.db.commit()

	_print(report)

	return report


MANUAL_STEPS = (
	"No volunteer, member or coordinator is seeded here. Rosters, hours and certifications are"
	" therefore empty, and the deployment requests below are open needs with nobody on them yet —"
	" which is what a site looks like the day before acceptance testing starts. See"
	" `kenya.promote_coordinator` for giving a coordinator who has signed up standing over their"
	" county.",
	"No image is seeded on any event or content block. The portal draws a placeholder with an"
	" upload control on it; a seed inventing photography would put a stock photo on a society's"
	" own page.",
	"Announcements are seeded with email delivery off, because a demo bench has no outgoing"
	" account. The in-app copy is delivered either way, which is the point of the two channels"
	" being resolved independently.",
)


# --- the workflows this society's records have to pass through -------------


def _reconcile_workflows() -> list[dict]:
	"""Make this society's records acceptable to whatever workflows the site has.

	**Why this step exists at all.** `kenya._workflows()` creates one workflow per
	approvable doctype *if there is not one already*, and skips otherwise —
	correctly, because a workflow is a society's governance and a seed must not
	overwrite it. On a bench where another society was seeded first, that means
	the workflow governing `VMMS Membership` is the other society's: it permits
	only their branch level and names a role their approver holds. A Kenyan
	membership is then refused by ACC-03 at submission, and a Kenyan application
	routes to nobody.

	So this reconciles, and only ever **widens**:

	* the Kenyan **county** level is *added* to `allowed_anchor_levels` where it
	  is missing. Nothing is removed, so the other society's records still anchor
	  exactly where they did. An empty table already means "any active level" and
	  is left alone rather than filled in, which would narrow it from everything
	  to one.

	  **The county, and nothing below it.** This step used to widen by the county
	  *and* the level under it, and doing that now would quietly undo the one rule
	  this society asked for: `kenya._workflows()` writes exactly one anchor row,
	  the county, and running this afterwards would append the sub-county level to
	  Kenya's own workflows and make 290 sub-counties anchorable again. Widening
	  by what Kenyan records actually need is the fix, and Kenyan records need the
	  county.
	* the Kenyan demo approver is granted whatever role each stage actually
	  names, at the Kenyan county. Routing asks core "who holds this role at or
	  above this node"; if nobody does, a correctly submitted application sits in
	  no queue at all. This grants the role the *configuration* asks for rather
	  than assuming it is one of the two `kenya.py` invented.

	On a site with only the Kenya seed on it, every check below passes and this
	step reports `exists` throughout.
	"""
	rows = []
	levels = [kenya.LEVELS[1]["key"]]
	county = kenya.primary_county()

	for name in frappe.get_all("VMMS Approval Workflow", pluck="name"):
		workflow = frappe.get_doc("VMMS Approval Workflow", name)

		rows.extend(_widen_anchor_levels(workflow, levels))
		rows.extend(_place_approver(workflow, county))

	return rows


def _widen_anchor_levels(workflow, levels: list[str]) -> list[dict]:
	"""Add this society's anchor level to a workflow's list. Never removes one."""
	if not workflow.allowed_anchor_levels:
		# Empty means any active level, which already admits ours. Filling it in
		# would turn "anywhere" into "these two" for everybody on the site.
		return [{"key": f"{workflow.name} anchor levels", "status": "exists", "note": "unconstrained"}]

	held = {row.geo_level for row in workflow.allowed_anchor_levels}
	missing = [level for level in levels if level not in held and frappe.db.exists("Geo Level", level)]

	if not missing:
		return [{"key": f"{workflow.name} anchor levels", "status": "exists"}]

	for level in missing:
		workflow.append("allowed_anchor_levels", {"geo_level": level})

	workflow.save(ignore_permissions=True)

	return [
		{
			"key": f"{workflow.name} ({workflow.workflow_for}) anchor levels",
			"status": "created",
			"added": ",".join(missing),
		}
	]


def _place_approver(workflow, county: str | None) -> list[dict]:
	"""Give the demo approver every role this workflow's stages ask for, at the county.

	The role is read off the stage rather than assumed, so a workflow somebody
	else configured routes to somebody who exists. Placement is a Geo Assignment,
	which is core's answer to *where* — holding the role is not authority
	anywhere, and holding it at Nairobi is authority over Nairobi and everything
	beneath it.
	"""
	if not (county and frappe.db.exists("User", kenya.APPROVER_USER)):
		return []

	rows = []
	user = frappe.get_doc("User", kenya.APPROVER_USER)

	for stage in workflow.stages:
		role = stage.required_role

		if not role or not frappe.db.exists("Role", role):
			continue

		if role not in frappe.get_roles(kenya.APPROVER_USER):
			user.add_roles(role)
			rows.append({"key": f"{kenya.APPROVER_USER} holds {role}", "status": "created"})

		if frappe.db.exists(
			"Geo Assignment", {"user": kenya.APPROVER_USER, "role": role, "geo_node": county}
		):
			rows.append({"key": f"{role} at {kenya.PRIMARY_COUNTY}", "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": "Geo Assignment",
				"user": kenya.APPROVER_USER,
				"role": role,
				"geo_node": county,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		rows.append({"key": f"{role} at {kenya.PRIMARY_COUNTY}", "status": "created"})

	if rows:
		frappe.clear_cache(user=kenya.APPROVER_USER)

	return rows


# --- qualifications --------------------------------------------------------


def _certification_types() -> list[dict]:
	"""The qualifications this society records. Named by their own key, so opaque."""
	rows = []

	for kind in CERTIFICATION_TYPES:
		if frappe.db.exists("VMMS Certification Type", kind["key"]):
			rows.append({"key": kind["key"], "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": "VMMS Certification Type",
				"certification_type_key": kind["key"],
				"certification_type_name": kind["name"],
				"description": kind["description"],
				"validity_days": kind["validity_days"],
				"blocks_deployment_when_lapsed": int(kind["blocks"]),
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		rows.append({"key": kind["key"], "status": "created"})

	return rows


def _time_log_categories() -> list[dict]:
	rows = []

	for key, name, description in TIME_LOG_CATEGORIES:
		if frappe.db.exists("VMMS Time Log Category", key):
			rows.append({"key": key, "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": "VMMS Time Log Category",
				"category_key": key,
				"category_name": name,
				"description": description,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		rows.append({"key": key, "status": "created"})

	return rows


def _time_log_permission() -> list[dict]:
	"""Let this society's volunteers file their own time.

	`registration/services/permissions.py` grants the self-service role `read` on
	`VMMS Time Log` and stops there, and states why: a volunteer looking at the
	hours somebody recorded for them is a different act from recording them, and
	a society that wants its volunteers filing their own says so by adding the
	permission. **This is a society saying so.** It is configuration, which is
	why it is in a seed and not in that module's defaults.
	"""
	from vmmsx.volunteer.services import society as volunteer_society

	role = volunteer_society.volunteer_member_role()

	if not role:
		return [{"key": "VMMS Time Log create", "status": "skipped: no volunteer role configured"}]

	from frappe.permissions import add_permission, update_permission_property

	# `add_permission` returns falsy when a DocPerm for this role and level is
	# already there, which is what makes the re-run report honestly rather than
	# claiming a grant it did not make. The property is set either way, so a row
	# somebody created and then emptied is repaired rather than trusted — the
	# same argument `registration/services/permissions.py::grant_read` gives.
	added = bool(add_permission("VMMS Time Log", role, 0))
	held = frappe.db.get_value(
		"Custom DocPerm", {"parent": "VMMS Time Log", "role": role, "permlevel": 0}, "create"
	)

	update_permission_property("VMMS Time Log", role, 0, "create", 1)
	frappe.clear_cache(doctype="VMMS Time Log")

	return [
		{
			"key": f"{role} may create VMMS Time Log",
			"status": "created" if (added or not held) else "exists",
		}
	]


# --- the programmes ---------------------------------------------------------


def _project(key: str | None) -> str | None:
	"""The seeded project matching this `PROJECTS` key, by its name.

	Looked up by `project_name` rather than by docname, the same reason
	`kenya.county_named()` resolves geo by shape: `Project` autonames
	itself opaquely, and a second bench numbers its projects differently.
	`None` in, `None` out — and a terms of reference that names no programme of
	its own is written under the society's standing-services one instead, which
	`_standing()` provides.
	"""
	if not key:
		return None

	spec = next((project for project in PROJECTS if project["key"] == key), None)

	if not spec:
		return None

	return frappe.db.get_value("Project", {"project_name": spec["name"]}, "name")


def _projects() -> list[dict]:
	"""The programmes of work this society's terms of reference are written under."""
	from vmmsx.deployment.services import project as project_service

	rows = []

	for project in PROJECTS:
		existing = frappe.db.get_value("Project", {"project_name": project["name"]}, "name")

		if existing:
			rows.append({"key": project["key"], "name": existing, "status": "exists"})
			continue

		node = _where(project["where"])

		if not node:
			rows.append({"key": project["key"], "status": "skipped: no geo node"})
			continue

		# `notes` is ERPNext's own — the story of the programme, and what the
		# printed terms of reference puts at its head. Planned and Active both
		# become Open: ERPNext expresses the two as one status and nothing in this
		# app ever read the difference. See `setup/project_fields.py`.
		doc = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": project["name"],
				"company": project_service.default_company(),
				"vmms_geo_node": node,
				"status": project_service.STATUS_OPEN,
				"expected_start_date": add_days(today(), project["start_in"]),
				"expected_end_date": add_days(today(), project["end_in"]),
				"notes": project["summary"],
			}
		).insert(ignore_permissions=True)

		rows.append({"key": project["key"], "name": doc.name, "status": "created"})

	return rows


# --- the work --------------------------------------------------------------


def _standing() -> str | None:
	"""The programme this society's standing duties are written under.

	Every terms of reference belongs to a programme now, and the blood drive
	rota, the event first aid post and the family links desk genuinely are one:
	work the society runs continuously rather than a campaign with an end.
	Anchored at the first county, which is where the rest of this seed's
	county-level work sits.
	"""
	node = kenya.county(0)

	if not node:
		return None

	return mission.standing_project(
		"Branch Standing Services",
		node,
		"The duties this society runs all year rather than as a campaign: the branch first aid"
		" post, the blood drive rota, and the standing community services.",
	)


def _terms() -> list[dict]:
	"""The society's terms of reference, each autonamed from its own key.

	A terms of reference that already exists but names a project it is not yet
	linked to is updated rather than left behind — the ordinary case the first
	time this runs after `PROJECTS` gained an entry `TERMS` now points at.

	**The mission tables come from `seed/mission.py::furnish`.** A terms of
	reference cannot be submitted until it is a finished mission document, and
	these entries carry a purpose, some responsibilities and a duration; the
	background, objectives, outputs, stakeholders, itinerary and period are built
	from those, so nothing here invents a fact about this society. That module's
	docstring says what the scaffolding is and is not.
	"""
	rows = []

	for terms in TERMS:
		project = _project(terms.get("project")) or _standing()

		if not project:
			rows.append({"key": terms["key"], "status": "skipped: no programme"})
			continue

		node = frappe.db.get_value("Project", project, "vmms_geo_node")

		if frappe.db.exists("VMMS Terms of Reference", terms["key"]):
			if project:
				doc = frappe.get_doc("VMMS Terms of Reference", terms["key"])

				if doc.project != project:
					doc.project = project
					doc.save(ignore_permissions=True)
					rows.append({"key": terms["key"], "status": "linked to project"})
					continue

			rows.append({"key": terms["key"], "status": "exists"})
			continue

		doc = frappe.get_doc(
			{
				"doctype": "VMMS Terms of Reference",
				"tor_key": terms["key"],
				"tor_name": terms["name"],
				"purpose": terms["purpose"],
				"responsibilities": terms["responsibilities"],
				"default_duration_days": terms["duration_days"],
				# Every one is direct; see the module docstring.
				"approval_mode": "direct",
				"is_active": 1,
				"required_certifications": [
					{"certification_type": key, "is_mandatory": int(mandatory)}
					for key, mandatory in terms["requires"]
				],
				**mission.furnish(
					name=terms["name"],
					purpose=terms["purpose"],
					responsibilities=terms["responsibilities"],
					geo_node=node,
					project=project,
					days=terms["duration_days"],
				),
			}
		)
		doc.insert(ignore_permissions=True)
		# Submitted, not left as a draft: a terms of reference takes no deployment
		# until its wording is frozen, and a seed that stopped at draft would hand
		# a society a register of specifications none of which can be used.
		doc.submit()

		rows.append({"key": terms["key"], "status": "created"})

	return rows


def _where(spec) -> str | None:
	"""A ("county", name) pair resolved to a Geo Node, or None for unplaced.

	Read through `kenya.py`'s own lookups rather than by docname, because those
	names are opaque (`GEO-.#####`) and a second bench numbers them differently.
	Named rather than indexed since the county table grew to 47: an index into it
	is a demo that moves to a different county the day somebody reorders a row.

	**Everything this file places is placed at a county, never a sub-county**,
	and that is a rule about consequences rather than about taste. This society
	records at the county — see the note above `kenya.LEVELS` — so nothing is ever
	anchored below one, and a record placed at a sub-county would have an empty
	scope: `announce.publish` would address nobody, and a roster raised there
	would find no volunteer in range. The sub-counties are geography for a person
	to recognise, not somewhere the society's own records live.
	"""
	if not spec:
		return None

	kind, name = spec

	if kind != "county":
		frappe.throw(f"{kind!r} is not a placement this seed knows. Every record here sits at a county.")

	return kenya.county_named(name)


def _requests() -> list[dict]:
	"""The needs this society has open. Each may become a deployment on insert.

	Nothing here creates a `VMMS Deployment`. The request controller's
	`on_update` calls `try_fulfil`, which asks whether the approval requirement
	is settled and whether a deployment exists already — and for a `direct` mode
	terms of reference the first is true the moment the record exists. So the
	deployment appears because the app decided it should, not because a seed
	wrote one.
	"""
	rows = []

	for spec in REQUESTS:
		node = _where(spec["where"])

		if not node:
			rows.append({"key": spec["terms"], "status": "skipped: no geo node"})
			continue

		needed_from = add_days(today(), spec["from_in"])
		needed_until = add_days(today(), spec["until_in"])

		existing = frappe.db.exists(
			"VMMS Deployment Request",
			{
				"terms_of_reference": spec["terms"],
				"geo_node": node,
				"needed_from": needed_from,
			},
		)

		if existing:
			rows.append({"key": spec["terms"], "name": existing, "status": "exists"})
			continue

		request = frappe.get_doc(
			{
				"doctype": "VMMS Deployment Request",
				"terms_of_reference": spec["terms"],
				"geo_node": node,
				"volunteers_requested": spec["volunteers"],
				"needed_from": needed_from,
				"needed_until": needed_until,
				"justification": spec["justification"],
				"is_published": int(spec["published"]),
			}
		)
		request.insert(ignore_permissions=True)
		request.reload()

		rows.append(
			{
				"key": spec["terms"],
				"name": request.name,
				"status": "created",
				"published": int(spec["published"]),
				"deployment": request.deployment or "none yet",
			}
		)

	return rows


# --- the diary -------------------------------------------------------------


def _event_setup() -> list[dict]:
	"""Buzz's own host, categories and venues. Its records, its rules.

	Skipped whole if Buzz is not installed, which is the same graceful-absence
	contract `vmmsx/buzz/services/events.py` holds: the portal's events screen
	says the app is not installed rather than showing an empty list.
	"""
	if not frappe.db.exists("DocType", "Buzz Event"):
		return [{"key": "buzz", "status": "skipped: Buzz is not installed"}]

	rows = []

	if frappe.db.exists("Event Host", EVENT_HOST):
		rows.append({"key": EVENT_HOST, "status": "exists"})
	else:
		frappe.get_doc(
			{"doctype": "Event Host", "__newname": EVENT_HOST, "by_line": "Kenya Red Cross Society"}
		).insert(ignore_permissions=True)
		rows.append({"key": EVENT_HOST, "status": "created"})

	for name, description in EVENT_CATEGORIES:
		if frappe.db.exists("Event Category", name):
			rows.append({"key": name, "status": "exists"})
			continue

		frappe.get_doc(
			{"doctype": "Event Category", "__newname": name, "description": description, "enabled": 1}
		).insert(ignore_permissions=True)
		rows.append({"key": name, "status": "created"})

	for name, address in EVENT_VENUES:
		if frappe.db.exists("Event Venue", name):
			rows.append({"key": name, "status": "exists"})
			continue

		frappe.get_doc({"doctype": "Event Venue", "__newname": name, "address": address}).insert(
			ignore_permissions=True
		)
		rows.append({"key": name, "status": "created"})

	return rows


def _events() -> list[dict]:
	"""Published events in Buzz, anchored where the society runs them.

	The anchor is vmmsx's one custom field on `Buzz Event` (BUZZ-01) and it is
	optional by design, so one event below carries none. `route` is left for
	Buzz to generate: its own `validate_route` builds one from the title when an
	event is published, and a seed writing that field would be this app deciding
	another app's URLs.
	"""
	if not frappe.db.exists("DocType", "Buzz Event"):
		return [{"key": "buzz", "status": "skipped: Buzz is not installed"}]

	from vmmsx.buzz.services import geo

	rows = []

	for spec in EVENTS:
		if frappe.db.exists("Buzz Event", {"title": spec["title"]}):
			rows.append({"key": spec["title"], "status": "exists"})
			continue

		event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": spec["title"],
				"category": spec["category"],
				"venue": spec["venue"],
				"medium": spec["medium"],
				"host": EVENT_HOST,
				"start_date": add_days(today(), spec["start_in"]),
				"end_date": add_days(today(), spec["end_in"]) if spec["end_in"] else None,
				"start_time": spec["start_time"],
				"end_time": spec["end_time"],
				"short_description": spec["summary"],
				"is_published": 1,
				geo.GEO_NODE_FIELD: _where(spec["where"]),
			}
		)
		event.insert(ignore_permissions=True)

		rows.append({"key": spec["title"], "status": "created", "route": event.route or "none"})

	return rows


# --- what a branch has said ------------------------------------------------


def _announcement_types() -> list[dict]:
	rows = []

	for name, description in ANNOUNCEMENT_TYPES:
		if frappe.db.exists("VMMS Announcement Type", name):
			rows.append({"key": name, "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": "VMMS Announcement Type",
				"__newname": name,
				"description": description,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)

		rows.append({"key": name, "status": "created"})

	return rows


def _announcements() -> list[dict]:
	"""Three announcements, published through the service that fans them out.

	`announce.publish` rather than a status written on the record: publishing is
	the fan-out, it is idempotent, and a row set to Published without it would be
	an announcement nobody holds a copy of. Email is off — see the manual steps.
	"""
	from vmmsx.notifications.services import announce

	rows = []

	for spec in ANNOUNCEMENTS:
		node = _where(spec["where"])

		if not node:
			rows.append({"key": spec["title"], "status": "skipped: no geo node"})
			continue

		existing = frappe.db.exists("VMMS Announcement", {"title": spec["title"]})

		if existing:
			announcement = frappe.get_doc("VMMS Announcement", existing)
			status = "exists"
		else:
			announcement = frappe.get_doc(
				{
					"doctype": "VMMS Announcement",
					"title": spec["title"],
					"announcement_type": spec["type"]
					if frappe.db.exists("VMMS Announcement Type", spec["type"])
					else None,
					"urgency": spec["urgency"],
					"audience": spec["audience"],
					"geo_node": node,
					"summary": spec["summary"],
					"body": spec["body"],
					"link_label": spec["link_label"],
					"link_href": spec["link_href"],
					"status": "Published",
					"also_email": 0,
					"expires_on": add_days(today(), 45),
				}
			)
			announcement.insert(ignore_permissions=True)
			status = "created"

		fanned = announce.publish(announcement)

		rows.append(
			{
				"key": spec["title"],
				"status": status,
				"addressed": fanned["addressed"],
				"delivered": fanned["delivered"],
			}
		)

	return rows


# --- the report ------------------------------------------------------------


def _print(report: dict) -> None:
	"""Say what happened, in the shape `kenya.py`'s report already uses."""
	print(f"\nKenya Red Cross Society operations seed on {frappe.local.site}\n" + "=" * 62)

	for section, rows in report.items():
		if section == "manual_steps":
			continue

		print(f"\n{section.replace('_', ' ').title()}")

		for row in rows:
			extra = " ".join(f"{k}={v}" for k, v in row.items() if k not in ("key", "status"))
			print(f"  [{row['status']:<8}] {row['key']}{'  ' + extra if extra else ''}")

	if "manual_steps" not in report:
		print()
		return

	print("\nWorth knowing")

	for step in report["manual_steps"]:
		print(f"  - {step}")

	print()
