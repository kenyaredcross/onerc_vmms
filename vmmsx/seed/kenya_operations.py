# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A worked Kenya Red Cross Society *operation*. Demo data, never behaviour.

    bench --site <site> execute vmmsx.seed.kenya_operations.main

`kenya.py` seeds a society's **configuration** — its ladder, its roles, its
membership types, the workflows that govern them. This seeds what that society
would then be *doing*: needs advertised on the notice board, events in the
diary, announcements sent from a branch, and volunteers with hours and
certifications against their names.

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
`kenya.branch()` rather than by docname — the same way that seed recognises its
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

from vmmsx.seed import kenya

# --- the demo volunteers --------------------------------------------------
#
# A password is set on each of these, which `kenya.py` deliberately does not do
# for its approver. The difference is what the account is for: that one is a
# named person a society signs in as, and these exist only so that somebody can
# open the portal and see it working. The value is a constant in this file
# rather than something the report invents, so it is as public as the accounts.

DEMO_PASSWORD = "krcs-demo-2026"

VOLUNTEERS = (
	{
		"email": "amina@krcs.demo",
		"first_name": "Amina",
		"last_name": "Wanjiku",
		"gender": "Female",
		"phone": "+254712000101",
		"date_of_birth": "1996-04-12",
		"branch": 0,
		"skills": ("first_aid", "driving"),
		"availability": ("weekend_mornings", "weekday_evenings"),
		# Also a member, and the membership is carried all the way to Active
		# below. Somebody who volunteers *and* holds a membership is the case
		# that shows the two satellites are independent: one Red Profile, two
		# affiliations, neither derived from the other.
		"membership": "approved",
		# Both of what `flood-response` requires, so a coordinator matching
		# against that terms of reference has somebody real to find.
		"certifications": (
			("first-aid", -200),
			("psychological-first-aid", -430),
			("water-safety", -150),
		),
		"logs": (
			(-3, 6.0, "emergency_response", "Flood assessment with the branch team in Kibera."),
			(-9, 4.5, "blood_drive", "Donor reception and refreshments at the Sarit drive."),
			(-16, 8.0, "emergency_response", "Overnight shelter support after the Mathare fire."),
			(-24, 3.0, "training", "Ran a first aid refresher for eight new volunteers."),
			(-38, 5.5, "community_event", "Household visits on the cholera awareness round."),
			(-52, 2.5, "operations_support", "Branch stock count and kit repacking."),
		),
	},
	{
		"email": "joseph@krcs.demo",
		"first_name": "Joseph",
		"last_name": "Kariuki",
		"gender": "Male",
		"phone": "+254712000102",
		"date_of_birth": "1989-11-02",
		"branch": 1,
		"skills": ("driving", "logistics"),
		"availability": ("weekday_mornings", "on_call"),
		"membership": None,
		# One lapsed certification on purpose: the deployability block on the
		# volunteer's own page is derived, not stored, and it has nothing to say
		# unless something has actually lapsed.
		"certifications": (("emergency-driving", -180), ("first-aid", -900)),
		"logs": (
			(-5, 7.0, "emergency_response", "Drove the ambulance on the Thika Road response."),
			(-12, 6.0, "emergency_response", "Relief distribution convoy to Kajiado."),
			(-31, 4.0, "operations_support", "Vehicle checks and fuel reconciliation."),
		),
	},
	{
		"email": "grace@krcs.demo",
		"first_name": "Grace",
		"last_name": "Achieng",
		"gender": "Female",
		"phone": "+254712000103",
		"date_of_birth": "2001-07-25",
		"branch": 0,
		"skills": ("first_aid", "counselling"),
		"availability": ("weekend_mornings", "weekend_evenings"),
		# Left sitting in the approver's queue on purpose, so the review side of
		# the product has something real to open.
		"membership": "pending",
		"certifications": (("psychological-first-aid", -95),),
		"logs": (
			(-2, 3.5, "community_event", "School talk on road safety in South B."),
			(-19, 5.0, "community_event", "Psychosocial support at the reception centre."),
		),
	},
	{
		"email": "peter@krcs.demo",
		"first_name": "Peter",
		"last_name": "Otieno",
		"gender": "Male",
		"phone": "+254712000104",
		"date_of_birth": "1993-02-18",
		"branch": 1,
		"skills": ("first_aid", "driving"),
		"availability": ("on_call", "weekend_mornings"),
		"membership": None,
		# Both of what `flood-response` requires as well, at the other branch:
		# a candidate search for it should turn up two people, not one.
		"certifications": (("first-aid", -100), ("water-safety", -100)),
		"logs": (
			(-6, 6.5, "emergency_response", "Boat patrol supporting the Nairobi West evacuation."),
			(-21, 4.0, "operations_support", "Kit inspection ahead of the long rains."),
		),
	},
	{
		"email": "fatuma@krcs.demo",
		"first_name": "Fatuma",
		"last_name": "Hassan",
		"gender": "Female",
		"phone": "+254712000105",
		"date_of_birth": "1998-09-30",
		"branch": 0,
		"skills": ("counselling", "first_aid"),
		"availability": ("weekday_mornings", "public_holidays"),
		"membership": "approved",
		# `blood-drive-support`'s desirable certification, so ranking has
		# something to prefer somebody for.
		"certifications": (("blood-donor-care", -60),),
		"logs": (
			(-4, 5.0, "blood_drive", "Donor reception at the Nairobi Central drive."),
			(-27, 3.0, "community_event", "Hygiene talk at a Nairobi Central primary school."),
		),
	},
	{
		"email": "daniel@krcs.demo",
		"first_name": "Daniel",
		"last_name": "Kiprop",
		"gender": "Male",
		"phone": "+254712000106",
		"date_of_birth": "2000-01-14",
		"branch": 1,
		"skills": ("logistics", "it"),
		"availability": ("weekday_evenings",),
		"membership": None,
		# Nobody's mandatory certification held yet, deliberately: a candidate
		# search for anything that requires one should pass over him rather than
		# every seeded volunteer qualifying for everything.
		"certifications": (),
		"logs": ((-8, 4.5, "operations_support", "Warehouse stock count at the Nairobi West store."),),
	},
)

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
	("emergency_response", "Emergency Response", "Time given on an active emergency or its immediate aftermath."),
	("blood_drive", "Blood Donation Drive", "Donor reception, screening support and post-donation care."),
)

# --- the programmes some of this work is written under ---------------------
#
# `VMMS Project` postdates the rest of this file: terms of reference were
# seeded before a project existed to write them under, which is exactly the
# situation the doctype itself was built to allow — see its own field
# description. Not every terms of reference gets one, deliberately: a society
# that runs standing duties beside its programmes should see both in the demo,
# not a portfolio where everything has been filed under something.

PROJECTS = (
	{
		"key": "nairobi-flood-response-2026",
		"name": "Nairobi Flood Response 2026",
		"where": ("county", 0),
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
		"where": ("branch", 0),
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
			"Search, evacuation support and relief distribution in communities cut off by"
			" seasonal flooding."
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
		"where": ("branch", 0),
		"volunteers": 12,
		"from_in": 4,
		"until_in": 18,
		"published": True,
		"justification": "Long rains forecast for the fortnight; two wards already reporting displacement.",
	},
	{
		"terms": "blood-drive-support",
		"where": ("branch", 1),
		"volunteers": 6,
		"from_in": 9,
		"until_in": 10,
		"published": True,
		"justification": "Mobile drive with the national blood service at the Westgate concourse.",
	},
	{
		"terms": "event-first-aid",
		"where": ("branch", 0),
		"volunteers": 4,
		"from_in": 12,
		"until_in": 12,
		"published": True,
		"justification": "Nairobi marathon feeder route; the organisers have asked for a staffed post.",
	},
	{
		"terms": "community-health",
		"where": ("county", 1),
		"volunteers": 20,
		"from_in": 20,
		"until_in": 25,
		"published": True,
		"justification": "Coastal hygiene campaign following the county health department's request.",
	},
	{
		"terms": "road-safety",
		"where": ("county", 0),
		"volunteers": 15,
		"from_in": 30,
		"until_in": 37,
		"published": True,
		"justification": "December travel season campaign, run jointly with the county transport office.",
	},
	{
		"terms": "shelter-support",
		"where": ("branch", 1),
		"volunteers": 8,
		"from_in": 2,
		"until_in": 12,
		"published": True,
		"justification": "Reception centre standing up after the Mathare fire; households still arriving.",
	},
	{
		"terms": "shelter-support",
		"where": ("county", 0),
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
)

EVENT_VENUES = (
	("KRCS Headquarters", "South C, Red Cross Road, Nairobi"),
	("Nairobi Central Branch Hall", "Haile Selassie Avenue, Nairobi"),
	("Mombasa Branch Office", "Moi Avenue, Mombasa"),
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
		"where": ("branch", 0),
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
		"where": ("branch", 0),
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
		"where": ("county", 1),
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
		"where": ("branch", 0),
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
		"where": ("county", 0),
		"summary": "Ten kilometres through South C, raising funds for the branch emergency response fund.",
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
		"where": ("county", 0),
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
		"where": ("county", 0),
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
		"where": ("branch", 0),
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
	if not kenya.branch(0):
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
		"volunteers": _volunteers(),
		"rosters": _rosters(),
		"certifications": _certifications(),
		"time_logs": _time_logs(),
		"memberships": _memberships(),
		"event_setup": _event_setup(),
		"events": _events(),
		"announcement_types": _announcement_types(),
		"announcements": _announcements(),
		"article_taxonomy": _article_taxonomy(),
		"articles": _articles(),
	}

	report["manual_steps"] = MANUAL_STEPS

	if commit:
		frappe.db.commit()

	_print(report)

	return report


MANUAL_STEPS = (
	f"Every demo volunteer signs in with the password {DEMO_PASSWORD}. Change or disable these"
	" accounts on anything that is not a demo bench.",
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

	* the Kenyan county and branch levels are *added* to `allowed_anchor_levels`
	  where they are missing. Nothing is removed, so the other society's records
	  still anchor exactly where they did. An empty table already means "any
	  active level" and is left alone rather than filled in, which would narrow
	  it from everything to two.
	* the Kenyan demo approver is granted whatever role each stage actually
	  names, at the Kenyan county. Routing asks core "who holds this role at or
	  above this node"; if nobody does, a correctly submitted application sits in
	  no queue at all. This grants the role the *configuration* asks for rather
	  than assuming it is one of the two `kenya.py` invented.

	On a site with only the Kenya seed on it, every check below passes and this
	step reports `exists` throughout.
	"""
	rows = []
	levels = [kenya.LEVELS[1]["key"], kenya.LEVELS[2]["key"]]
	county = kenya.county(0)

	for name in frappe.get_all("VMMS Approval Workflow", pluck="name"):
		workflow = frappe.get_doc("VMMS Approval Workflow", name)

		rows.extend(_widen_anchor_levels(workflow, levels))
		rows.extend(_place_approver(workflow, county))

	return rows


def _widen_anchor_levels(workflow, levels: list[str]) -> list[dict]:
	"""Add this society's levels to a workflow's anchor list. Never removes one."""
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
			rows.append({"key": f"{role} at {kenya.COUNTY_NODES[0]}", "status": "exists"})
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

		rows.append({"key": f"{role} at {kenya.COUNTY_NODES[0]}", "status": "created"})

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
	`kenya.county()`/`kenya.branch()` resolve geo by shape: `VMMS Project`
	autonames itself opaquely, and a second bench numbers its projects
	differently. `None` in, `None` out — most terms of reference name no
	project at all.
	"""
	if not key:
		return None

	spec = next((project for project in PROJECTS if project["key"] == key), None)

	if not spec:
		return None

	return frappe.db.get_value("VMMS Project", {"project_name": spec["name"]}, "name")


def _projects() -> list[dict]:
	"""The programmes of work some of this society's terms of reference are written under."""
	rows = []

	for project in PROJECTS:
		existing = frappe.db.get_value("VMMS Project", {"project_name": project["name"]}, "name")

		if existing:
			rows.append({"key": project["key"], "name": existing, "status": "exists"})
			continue

		node = _where(project["where"])

		if not node:
			rows.append({"key": project["key"], "status": "skipped: no geo node"})
			continue

		doc = frappe.get_doc(
			{
				"doctype": "VMMS Project",
				"project_name": project["name"],
				"geo_node": node,
				"status": project["status"],
				"start_date": add_days(today(), project["start_in"]),
				"end_date": add_days(today(), project["end_in"]),
				"summary": project["summary"],
			}
		).insert(ignore_permissions=True)

		rows.append({"key": project["key"], "name": doc.name, "status": "created"})

	return rows


# --- the work --------------------------------------------------------------


def _terms() -> list[dict]:
	"""The society's terms of reference, each autonamed from its own key.

	A terms of reference that already exists but names a project it is not yet
	linked to is updated rather than left behind — the ordinary case the first
	time this runs after `PROJECTS` gained an entry `TERMS` now points at.
	"""
	rows = []

	for terms in TERMS:
		project = _project(terms.get("project"))

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

		frappe.get_doc(
			{
				"doctype": "VMMS Terms of Reference",
				"tor_key": terms["key"],
				"tor_name": terms["name"],
				"project": project,
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
			}
		).insert(ignore_permissions=True)

		rows.append({"key": terms["key"], "status": "created"})

	return rows


def _where(spec) -> str | None:
	"""A ("county"|"branch", index) pair resolved to a Geo Node, or None.

	Read through `kenya.py`'s own lookups rather than by docname, because those
	names are opaque (`GEO-.#####`) and a second bench numbers them differently.
	"""
	if not spec:
		return None

	kind, index = spec

	return kenya.county(index) if kind == "county" else kenya.branch(index)


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


# --- the people ------------------------------------------------------------


def _volunteers() -> list[dict]:
	"""A login, a Red Profile and a volunteer record for each demo person.

	The volunteer is created through `volunteer_service.ensure`, the app's own
	idempotent constructor, so nothing here knows how a volunteer record is put
	together. `status` is then set to Active directly, which needs saying: the
	honest path to Active is an application the approval engine accepted, and
	`derive_status` reads exactly that. These three have no application, so they
	would sit at Prospective forever and a Prospective volunteer is shown none of
	the self-service surface. Setting it here is the seed standing in for an
	acceptance that happened before the demo started.
	"""
	from vmmsx.volunteer.services import volunteer as volunteer_service

	rows = []

	for person in VOLUNTEERS:
		node = kenya.branch(person["branch"])

		if not node:
			rows.append({"key": person["email"], "status": "skipped: no branch"})
			continue

		user_status = _user(person)
		profile = _profile(person, node)
		volunteer = volunteer_service.ensure(profile, node)

		changed = False

		if volunteer.status != "Active":
			volunteer.status = "Active"
			changed = True

		if not volunteer.joined_on:
			volunteer.joined_on = add_days(today(), -420)
			changed = True

		if not volunteer.skills:
			volunteer.set("skills", [{"skill": key} for key in person["skills"] if _skill_exists(key)])
			changed = True

		if not volunteer.availability:
			volunteer.set(
				"availability",
				[{"availability_slot": key} for key in person["availability"] if _slot_exists(key)],
			)
			changed = True

		if changed:
			volunteer.save(ignore_permissions=True)

		# The two things acceptance would have done: tell core what this person
		# is to the society, and hand them the self-service role.
		volunteer_service.report(volunteer)
		volunteer_service.grant_self_service(volunteer)

		rows.append(
			{
				"key": person["email"],
				"name": volunteer.name,
				"status": user_status,
				"branch": person["branch"],
			}
		)

	return rows


def _user(person: dict) -> str:
	"""The login, with a password set on it. See the note beside `DEMO_PASSWORD`."""
	from frappe.utils.password import update_password

	if frappe.db.exists("User", person["email"]):
		status = "exists"
	else:
		frappe.get_doc(
			{
				"doctype": "User",
				"email": person["email"],
				"first_name": person["first_name"],
				"last_name": person["last_name"],
				"send_welcome_email": 0,
				# A volunteer holding the self-service role is shown a workspace,
				# and Frappe derives `user_type` from desk access. The role grant
				# below is what actually settles it; this is the starting point.
				"user_type": "Website User",
			}
		).insert(ignore_permissions=True)
		status = "created"

	update_password(person["email"], DEMO_PASSWORD)

	return status


def _profile(person: dict, node: str) -> str:
	"""The Red Profile, which is core's and is the only place identity lives.

	Looked up by `user` first, because that is the unique column core guarantees
	and the one `registration/services/intake.py` resolves through. A demo bench
	that already ran a registration for this login must reuse that profile rather
	than create a second one — "one Red Profile per login, ever" is the app's
	rule and a seed is not exempt from it.
	"""
	existing = frappe.db.get_value("Red Profile", {"user": person["email"]}, "name")

	if existing:
		return existing

	orphan = frappe.db.get_value("Red Profile", {"email": person["email"], "user": ("is", "not set")}, "name")

	if orphan:
		# Adopted, exactly as `intake.claim_profile` adopts a login-less profile
		# with the same email rather than creating a rival one.
		frappe.db.set_value("Red Profile", orphan, "user", person["email"])
		return orphan

	profile = frappe.get_doc(
		{
			"doctype": "Red Profile",
			"first_name": person["first_name"],
			"last_name": person["last_name"],
			"email": person["email"],
			"user": person["email"],
			"phone": person["phone"],
			"gender": person["gender"] if frappe.db.exists("Gender", person["gender"]) else None,
			"date_of_birth": person["date_of_birth"],
			"home_geo_node": node,
		}
	)
	profile.insert(ignore_permissions=True)

	return profile.name


def _skill_exists(key: str) -> bool:
	return bool(frappe.db.exists("VMMS Skill", key))


def _slot_exists(key: str) -> bool:
	return bool(frappe.db.exists("VMMS Availability Slot", key))


def _volunteer_of(email: str) -> str | None:
	profile = frappe.db.get_value("Red Profile", {"user": email}, "name")

	return frappe.db.get_value("VMMS Volunteer", {"red_profile": profile}, "name") if profile else None


def _certifications() -> list[dict]:
	"""What each demo volunteer holds, dated relative to today.

	`expiry_date` is derived from the type's own `validity_days` rather than
	written here, so a lapse is a lapse because the configuration says so. One
	of Joseph's is deliberately old enough to have expired, because the
	deployability block on a volunteer's page is derived and has nothing to show
	otherwise.
	"""
	rows = []

	for person in VOLUNTEERS:
		volunteer = _volunteer_of(person["email"])

		if not volunteer:
			continue

		for kind, completed_in in person["certifications"]:
			if not frappe.db.exists("VMMS Certification Type", kind):
				continue

			completion = add_days(today(), completed_in)

			if frappe.db.exists(
				"VMMS Certification",
				{"volunteer": volunteer, "certification_type": kind, "completion_date": completion},
			):
				rows.append({"key": f"{person['first_name']} / {kind}", "status": "exists"})
				continue

			validity = frappe.db.get_value("VMMS Certification Type", kind, "validity_days")

			frappe.get_doc(
				{
					"doctype": "VMMS Certification",
					"volunteer": volunteer,
					"certification_type": kind,
					"completion_date": completion,
					"expiry_date": add_days(completion, validity) if validity else None,
				}
			).insert(ignore_permissions=True)

			rows.append({"key": f"{person['first_name']} / {kind}", "status": "created"})

	return rows


def _time_logs() -> list[dict]:
	"""Hours already given, so the portal's own history has something in it.

	All general logs. A deployment log names a deployment and is refused unless
	that deployment's roster lists the volunteer, and tying seeded hours to
	seeded rosters would make this the one part of the seed whose order matters.
	"""
	rows = []

	for person in VOLUNTEERS:
		volunteer = _volunteer_of(person["email"])
		node = kenya.branch(person["branch"])

		if not (volunteer and node):
			continue

		for days_ago, hours, category, notes in person["logs"]:
			activity_date = add_days(today(), days_ago)

			if frappe.db.exists(
				"VMMS Time Log",
				{"volunteer": volunteer, "activity_date": activity_date, "hours": hours},
			):
				rows.append({"key": f"{person['first_name']} {activity_date}", "status": "exists"})
				continue

			frappe.get_doc(
				{
					"doctype": "VMMS Time Log",
					"volunteer": volunteer,
					"geo_node": node,
					"activity_date": activity_date,
					"hours": hours,
					"log_type": "general",
					"log_category": category if frappe.db.exists("VMMS Time Log Category", category) else None,
					"notes": notes,
				}
			).insert(ignore_permissions=True)

			rows.append({"key": f"{person['first_name']} {activity_date}", "status": "created"})

	return rows


def _demo_membership_type() -> str | None:
	"""An active type that routes for approval and charges nothing. By shape.

	**Not `kenya.TYPE_LIFE` by name**, and the difference is not fussiness: a
	demo bench is a site somebody has been editing, and the type that was seeded
	free and lifetime may by now carry a fee. What this seed actually needs is
	structural — routed, so an approver's decision is what settles it, and free,
	so `payment.request` never asks a gateway this bench does not have. Asking
	for those two properties finds whatever type has them, or nothing.
	"""
	found = frappe.get_all(
		"VMMS Membership Type",
		filters={"is_active": 1, "approval_mode": "routed", "fee_amount": 0},
		pluck="name",
		order_by="creation asc",
		limit=1,
	)

	return found[0] if found else None


def _memberships() -> list[dict]:
	"""A membership for two of the demo volunteers, one settled and one waiting.

	Everything goes through the app's own services. `membership.submit()` starts
	the fee request and the approval; `engine.decide()` records the approver's
	decision and moves the state; activation is then the predicate
	`try_activate()` re-evaluating from `on_update`, exactly as it would if a
	person had clicked Approve on the screen. **Nothing here writes
	`membership_status` or `approval_state` directly** — a seed that set those by
	hand would produce a record no code path could have produced, which is the
	one thing demo data must not do.

	The approval is recorded as `kenya.APPROVER_USER`, who holds the membership
	approver role at the first county and is therefore genuinely among the people
	this membership routes to. The engine's person-gate is not bypassed; it is
	satisfied.
	"""
	from vmmsx.approvals.services import engine
	from vmmsx.member.services import member as member_service
	from vmmsx.member.services import membership as membership_service

	rows = []
	membership_type = _demo_membership_type()

	if not membership_type:
		return [
			{
				"key": "membership",
				"status": "skipped: no active routed membership type with a zero fee on this site",
			}
		]

	for person in VOLUNTEERS:
		wanted = person.get("membership")

		if not wanted:
			continue

		profile = frappe.db.get_value("Red Profile", {"user": person["email"]}, "name")
		node = kenya.branch(person["branch"])

		if not (profile and node):
			rows.append({"key": person["email"], "status": "skipped: no profile or branch"})
			continue

		member = member_service.ensure(profile)

		existing = frappe.db.exists(
			"VMMS Membership", {"member": member.name, "membership_type": membership_type}
		)

		if existing:
			membership = frappe.get_doc("VMMS Membership", existing)
			rows.append(
				{
					"key": person["email"],
					"name": membership.name,
					"status": "exists",
					"state": membership.membership_status,
				}
			)
			continue

		membership = frappe.get_doc(
			{
				"doctype": "VMMS Membership",
				"member": member.name,
				"membership_type": membership_type,
				"geo_node": node,
				"membership_source": "Gateway",
			}
		)
		membership.insert(ignore_permissions=True)
		membership_service.submit(membership)

		if wanted == "approved":
			_approve(engine, membership)

		membership.reload()

		rows.append(
			{
				"key": person["email"],
				"name": membership.name,
				"status": "created",
				"state": membership.membership_status,
				"approval": membership.approval_state,
			}
		)

	return rows


def _approve(engine, membership) -> None:
	"""Record the county approver's decision, as that user, through the gate.

	`frappe.set_user` rather than an `ignore_permissions` flag: the engine's
	check is *who is acting*, not what permission they hold, and there is no
	argument that overrides it. Restored in a `finally` so a refusal mid-way does
	not leave the rest of the seed running as somebody else.
	"""
	if not frappe.db.exists("User", kenya.APPROVER_USER):
		return

	original = frappe.session.user

	try:
		frappe.set_user(kenya.APPROVER_USER)
		membership.reload()
		engine.decide(membership, "Approved", reason="Verified against the branch's records.")
	finally:
		frappe.set_user(original)


def _rosters() -> list[dict]:
	"""Put the demo volunteers on the two soonest deployments.

	Only where a deployment actually exists — which is wherever a request was
	settled and fulfilled, and that is the app's decision rather than this
	seed's. A roster is what turns the opportunity card's "places filled" from a
	zero into a number somebody can read against the request.
	"""
	rows = []

	deployments = frappe.get_all(
		"VMMS Deployment",
		filters={"status": ("in", ("Planned", "Active"))},
		fields=["name"],
		order_by="start_date asc",
		limit=2,
	)

	volunteers = [name for name in (_volunteer_of(person["email"]) for person in VOLUNTEERS) if name]

	for entry in deployments:
		deployment = frappe.get_doc("VMMS Deployment", entry.name)
		listed = {row.volunteer for row in deployment.participants}
		added = 0

		for volunteer in volunteers:
			if volunteer in listed:
				continue

			deployment.append("participants", {"volunteer": volunteer, "joined_on": today()})
			added += 1

		if not added:
			rows.append({"key": deployment.name, "status": "exists"})
			continue

		deployment.save(ignore_permissions=True)
		rows.append({"key": deployment.name, "status": "created", "added": added})

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

		frappe.get_doc(
			{"doctype": "Event Venue", "__newname": name, "address": address}
		).insert(ignore_permissions=True)
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


# --- stories ---------------------------------------------------------------
#
# `Article` is **core's** doctype, and the portal reads it through core's own
# guest-readable API rather than through anything in this app. Seeded here for
# the same reason the Buzz events are: a stories tab with nothing in it
# demonstrates nothing, and the records belong to whichever app owns them.

ARTICLE_TYPES = (
	("News", "Something that happened, reported by the society."),
	("Story", "A volunteer, a branch or a community, in their own words."),
)

ARTICLE_CATEGORIES = (
	("Emergency Response", "Floods, fires, road accidents and the work that follows."),
	("Volunteering", "The people who give their time, and what it is like."),
	("Health", "Blood, first aid, community health and public awareness."),
	("Branch Life", "What is happening across the society's branches."),
)

ARTICLES = (
	{
		"title": "Three days in Mathare: what a reception centre actually looks like",
		"subtitle": "Forty households arrived in one night. Here is how the branch met them.",
		"type": "Story",
		"category": "Emergency Response",
		"read_time": 6,
		"featured": True,
		"published_in": -4,
		"summary": (
			"When fire went through part of Mathare, the branch had a reception centre standing"
			" within four hours. Three volunteers describe the first night, the registration"
			" queue, and what they would do differently."
		),
		"body": (
			"<p>The call came in at ten past eight. By midnight the hall had forty households in"
			" it, and by the following evening it had ninety.</p>"
			"<h2>The first four hours</h2>"
			"<p>Setting up is not the hard part. Sleeping mats, a washing point and a feeding area"
			" go in fast when there are enough hands, and there were. What takes the time is"
			" registration, because registration is what everything else depends on: how much"
			" food to cook, how many mats are still needed, who has not been accounted for.</p>"
			"<h2>What we would do differently</h2>"
			"<p>Two things. Put two people on registration from the start rather than one, and"
			" agree who is talking to the county before anybody does.</p>"
			"<blockquote>You are not there to fix somebody's week. You are there so that their"
			" night is survivable.</blockquote>"
			"<p>Everyone who worked the centre logged their hours against it, which is how the"
			" branch knows the centre cost 340 volunteer hours across three days.</p>"
		),
	},
	{
		"title": "Why your first aid certificate has an expiry date",
		"subtitle": "It is not administration. It is the difference between remembering and knowing.",
		"type": "News",
		"category": "Health",
		"read_time": 4,
		"featured": False,
		"published_in": -11,
		"summary": (
			"A number of certificates in the county expire this quarter. What lapses, what it"
			" stops you doing, and how to book the next sitting."
		),
		"body": (
			"<p>A first aid certificate is valid for two years, and the society treats a lapsed"
			" one as a lapsed one. That is deliberate.</p>"
			"<h2>What a lapse actually stops</h2>"
			"<p>Some certifications are held as a record and some are held as a requirement. A"
			" lapsed requirement is the reason somebody cannot be sent on work that names it,"
			" and the portal says so on your own training page rather than leaving you to find"
			" out when a coordinator calls.</p>"
			"<h2>Booking the next one</h2>"
			"<p>The two day certificate runs at headquarters and is listed under events. Book it"
			" before yours runs out rather than after.</p>"
		),
	},
	{
		"title": "Grace has given 200 hours this year. She is 24.",
		"subtitle": "A conversation about turning up, burning out, and turning up again.",
		"type": "Story",
		"category": "Volunteering",
		"read_time": 5,
		"featured": False,
		"published_in": -19,
		"summary": (
			"She joined for a line on a form and stayed for something else entirely. On"
			" psychosocial support, school talks, and what nobody tells you about the first"
			" deployment."
		),
		"body": (
			"<p>She signed up because a friend was signing up.</p>"
			"<h2>The first deployment</h2>"
			"<p>Nobody tells you that the hardest part is not the work. It is the hour"
			" afterwards, when there is nothing left to do and you are still there.</p>"
			"<h2>On not burning out</h2>"
			"<p>Log your hours honestly, including the ones you would rather not count. A branch"
			" that can see somebody is at 200 hours can do something about it. A branch that"
			" cannot see it will keep calling.</p>"
		),
	},
	{
		"title": "The blood drive moved 412 units in a weekend",
		"subtitle": "What the branch learned about donor reception.",
		"type": "News",
		"category": "Health",
		"read_time": 3,
		"featured": False,
		"published_in": -27,
		"summary": (
			"A two day mobile drive with the national blood service, and the small change in the"
			" reception area that cut the queue in half."
		),
		"body": (
			"<p>412 units over two days, against a target of 300.</p>"
			"<h2>The change that mattered</h2>"
			"<p>Screening and registration were run as one queue and it did not work. Splitting"
			" them, with two volunteers on each, halved the wait and dropped the number of"
			" people who left before donating to almost none.</p>"
		),
	},
	{
		"title": "Every branch is now on the same register",
		"subtitle": "What that changes for a volunteer, and what it does not.",
		"type": "News",
		"category": "Branch Life",
		"read_time": 4,
		"featured": False,
		"published_in": -40,
		"summary": (
			"One profile, whichever branch you serve through. What moves with you, what stays"
			" with the branch, and why your certifications are now visible to whoever is"
			" staffing a deployment."
		),
		"body": (
			"<p>You have one profile with the society and you will only ever have one.</p>"
			"<h2>What moves with you</h2>"
			"<p>Your name, your contact details, your certifications and every hour you have"
			" logged. Transferring between branches does not restart any of it.</p>"
			"<h2>What stays with the branch</h2>"
			"<p>Your placement, and the decisions a branch made about it. A transfer is a"
			" decision somebody makes, not a field you edit.</p>"
		),
	},
)


def _article_taxonomy() -> list[dict]:
	"""Core's article types and categories. Both autoname from their own label."""
	rows = []

	for doctype, entries, field in (
		("Localisation Type", ARTICLE_TYPES, "type_name"),
		("Localisation Category", ARTICLE_CATEGORIES, "category_name"),
	):
		if not frappe.db.exists("DocType", doctype):
			rows.append({"key": doctype, "status": "skipped: doctype not installed"})
			continue

		for label, description in entries:
			if frappe.db.exists(doctype, label):
				rows.append({"key": label, "status": "exists"})
				continue

			frappe.get_doc(
				{"doctype": doctype, field: label, "description": description, "is_active": 1}
			).insert(ignore_permissions=True)

			rows.append({"key": label, "status": "created"})

	return rows


def _articles() -> list[dict]:
	"""Published stories, submitted, because that is what `get_articles` reads.

	`Article` is submittable and core's list endpoint filters on
	`docstatus = 1` as well as `status = "Published"`. A seed that only set the
	status would produce records that look published on the desk and are invisible
	in the portal, which is the most confusing possible half-state — so each one
	is submitted here, deliberately and visibly.

	The author is the demo approver, who is a real user on this site. No cover
	image is attached: the portal draws a designed placeholder for an absent one,
	and a seed inventing photography would put a stock photograph on a society's
	own newsroom.
	"""
	if not frappe.db.exists("DocType", "Article"):
		return [{"key": "Article", "status": "skipped: doctype not installed"}]

	author = kenya.APPROVER_USER if frappe.db.exists("User", kenya.APPROVER_USER) else "Administrator"
	rows = []

	for spec in ARTICLES:
		if frappe.db.exists("Article", {"title": spec["title"]}):
			rows.append({"key": spec["title"][:44], "status": "exists"})
			continue

		article = frappe.get_doc(
			{
				"doctype": "Article",
				"title": spec["title"],
				"subtitle": spec["subtitle"],
				"article_type": spec["type"],
				"category": spec["category"],
				"summary": spec["summary"],
				"body": spec["body"],
				"read_time": spec["read_time"],
				"is_featured": int(spec["featured"]),
				"author": author,
				"status": "Published",
				"published_on": add_days(today(), spec["published_in"]),
			}
		)
		article.insert(ignore_permissions=True)
		article.submit()

		rows.append({"key": spec["title"][:44], "status": "created", "slug": article.slug})

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
