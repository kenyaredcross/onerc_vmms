# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Gambia Red Cross Society's operations: what it does, and what it did.

    bench --site <site> execute vmmsx.seed.gambia_operations.main

Kept separate from `gambia.py` for the reason `kenya_operations.py` is kept
separate from `kenya.py`: configuration is what a society *holds* and an
operation is what it *did last month*. A site being set up for real wants the
first and may not want the second.

It requires `gambia.py` to have run, and reads that society's nodes by shape
rather than by name, so a branch renamed in the desk does not break it.

**What is in here, and where it came from.**

* **Vocabularies** — skills, motivations, availability, time-log categories,
  certification types and announcement types. The society's own words.
* **Terms of reference and published opportunities** — the twelve volunteering
  roles in the society's seed-data pack, each modelled on a real GRCS
  programme: the SMC malaria campaign, the Farafenni migration assistance
  point, the Spanish Red Cross borehole project, the mpox response.
* **Stories** — twelve articles, each sourced from a published GRCS, IFRC,
  ICRC, WHO or Gambian press report, and each carrying its source URL into
  core's `Article.source_url` so a reader can check it. Nothing here is
  invented and no quotation is paraphrased.
* **Branch locations** — the seven regional branches with real coordinates,
  published so they draw on the public map.

**What is deliberately not in here: people.** No volunteer, no member and no
Red Profile is created. The society's registration sheets carry 24,000 names'
worth of headcount, and a seed that turned those into records would be filling
a national register with people who do not exist — which is worse than an empty
one, because an empty register is obviously empty and a fabricated one is not.
The structure they belong to is real and is seeded; the people register
themselves, or a branch enters them.

Idempotent, and it says what it did.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.seed import gambia

# --- the society's vocabularies -------------------------------------------

SKILLS = (
	("first-aid", "First Aid", "Basic and advanced first aid, delivered under a branch first aider."),
	("psychosocial-support", "Psychosocial Support", "Psychological first aid and community support."),
	("community-health", "Community Health", "CBHFA household visits, hygiene and health promotion."),
	("water-safety", "Water Safety and Rescue", "Search, evacuation and rescue on and near water."),
	("logistics", "Logistics", "Warehousing, distribution and fleet support during an operation."),
	("communications", "Communications", "Risk communication, social mobilisation and reporting."),
	("data-collection", "Data Collection", "KoboToolbox, assessments and community mapping."),
	("restoring-family-links", "Restoring Family Links", "Tracing requests and family reunification."),
	("youth-leadership", "Youth Leadership", "Peer education and running a Link's youth programme."),
	("blood-donor-care", "Blood Donor Care", "Donor reception, counselling and recovery monitoring."),
)

MOTIVATIONS = (
	("serve-community", "To serve my community", ""),
	("learn-skills", "To learn new skills", ""),
	("humanitarian-principles", "I believe in the Fundamental Principles", ""),
	("career", "To build experience for my career", ""),
	("family-tradition", "My family has served with the Red Cross", ""),
)

AVAILABILITY = (
	("weekday-daytime", "Weekdays, daytime", ""),
	("weekday-evening", "Weekdays, evenings", ""),
	("weekends", "Weekends", ""),
	("school-holidays", "School holidays only", ""),
	("emergency-only", "Emergencies only, at any time", ""),
)

TIME_LOG_CATEGORIES = (
	("emergency-response", "Emergency Response", "Flood, fire, accident and outbreak response."),
	("health-campaign", "Health Campaign", "Malaria, immunisation and community health outreach."),
	("first-aid-duty", "First Aid Duty", "Staffing a first aid post at an event."),
	("training", "Training", "Attending or delivering a course."),
	("branch-admin", "Branch Administration", "Meetings, registration and Link administration."),
	("blood-drive", "Blood Drive", "Supporting a mobile or fixed blood donation session."),
)

# `blocks_deployment_when_lapsed` is the only field here that changes anything:
# a lapsed certification that blocks deployment is how the society says a
# volunteer must not be sent on this without it.
CERTIFICATION_TYPES = (
	("first-aid", "First Aid", 730, 1, "Basic first aid certificate, renewed every two years."),
	("advanced-first-aid", "Advanced First Aid", 730, 1, "Advanced life support and trauma care."),
	("ecv", "Epidemic Control for Volunteers", 1095, 0, "The IFRC ECV manual, as trained in 2023-24."),
	("cbhfa", "Community-Based Health and First Aid", 1095, 0, "CBHFA methodology for household visits."),
	("psychological-first-aid", "Psychological First Aid", 1095, 0, "Psychosocial support for survivors."),
	("water-safety", "Water Safety and Rescue", 730, 1, "Rescue on and near water, for flood response."),
	("rfl", "Restoring Family Links", 1095, 0, "Tracing procedure and the Family Links Network."),
)

# `VMMS Announcement Type` names itself by prompt rather than by a key field,
# so the label *is* the docname here. Nothing branches on it either way.
ANNOUNCEMENT_TYPES = (
	("General", "Branch and national notices."),
	("Emergency", "Flood, fire, accident and outbreak alerts."),
	("Training", "Course announcements and calls to enrol."),
	("Event", "Blood drives, campaigns and public events."),
)

# --- what the society asks volunteers to do -------------------------------

# (key, name, region, purpose, responsibilities, days, certifications,
#  volunteers, from, until)
#
# The society's twelve volunteering opportunities. Each becomes a Terms of
# Reference (what the role is) and one published Deployment Request (this
# branch, these dates, this many people) — which is the pair the opportunities
# board reads, because `api/opportunities.py` is bounded by `is_published` on
# the request and the role itself is reusable across seasons.
OPPORTUNITIES = (
	{
		"key": "emergency-shelter-support",
		"name": "Emergency Shelter Support Volunteer",
		"region": "West Coast Region",
		"purpose": (
			"Setting up and running a temporary reception centre for displaced households following"
			" seasonal flooding in the West Coast Region."
		),
		"responsibilities": (
			"Shelter setup and management. Non-food item distribution. Registration of displaced"
			" families. Coordination with local government disaster management committees."
		),
		"certifications": ("first-aid", "psychological-first-aid"),
		"volunteers": 8,
		"from": "2026-08-13",
		"until": "2026-08-23",
	},
	{
		"key": "flood-response-team",
		"name": "Flood Response Team Member",
		"region": "Central River Region",
		"purpose": (
			"Search, evacuation support and relief distribution in communities cut off by seasonal"
			" flooding along the Gambia River."
		),
		"responsibilities": (
			"Needs assessment. Distribution of emergency supplies including water purification"
			" tablets and hygiene kits. Evacuation logistics using GRCS boats and vehicles."
		),
		"certifications": ("water-safety", "first-aid"),
		"volunteers": 12,
		"from": "2026-08-15",
		"until": "2026-08-29",
	},
	{
		"key": "blood-drive-support",
		"name": "Blood Drive Support Volunteer",
		"region": "West Coast Region",
		"purpose": (
			"Running the reception, refreshment and recovery areas at a mobile blood donation drive"
			" in partnership with the National Blood Transfusion Service."
		),
		"responsibilities": (
			"Register donors. Provide pre-donation counselling. Serve refreshments. Monitor"
			" recovery. Distribute donor appreciation materials."
		),
		"certifications": (),
		"volunteers": 6,
		"from": "2026-08-20",
		"until": "2026-08-21",
	},
	{
		"key": "event-first-aid-post",
		"name": "Event First Aid Post Volunteer",
		"region": "Kanifing Municipal",
		"purpose": "Staffing a first aid post at a major public event under a branch first aider.",
		"responsibilities": (
			"Injury assessment. Wound care. Heat stroke management. Triage. Two-hour shifts with"
			" full first aid kit provision."
		),
		"certifications": ("first-aid",),
		"volunteers": 4,
		"from": "2026-08-23",
		"until": "2026-08-23",
	},
	{
		"key": "community-health-outreach",
		"name": "Community Health Outreach Volunteer",
		"region": "Upper River Region",
		"purpose": (
			"Household and school visits on a branch health campaign covering hygiene, immunisation"
			" awareness, nutrition and maternal health referral."
		),
		"responsibilities": (
			"Door-to-door visits in assigned compounds, using CBHFA methodology to deliver health"
			" messages in local languages."
		),
		"certifications": ("cbhfa", "psychological-first-aid"),
		"volunteers": 20,
		"from": "2026-08-31",
		"until": "2026-09-05",
	},
	{
		"key": "road-safety-campaign",
		"name": "Road Safety Campaign Volunteer",
		"region": "Kanifing Municipal",
		"purpose": (
			"Public awareness at transport stages, schools and along major roads ahead of the busy"
			" travel season."
		),
		"responsibilities": (
			"Distribute road safety leaflets. Conduct school assemblies on pedestrian safety."
			" Support G-Plus ambulance visibility events at transport hubs."
		),
		"certifications": (),
		"volunteers": 15,
		"from": "2026-09-10",
		"until": "2026-09-17",
	},
	{
		"key": "smc-support",
		"name": "Seasonal Malaria Chemoprevention Support",
		"region": "Banjul",
		"purpose": (
			"Supporting the Ministry of Health's SMC campaign nationwide. Part of the CIDCA-funded"
			" Accelerating Malaria Elimination project implemented through IFRC."
		),
		"responsibilities": (
			"Door-to-door education on malaria prevention. Assist with mosquito net distribution."
			" Register beneficiary households."
		),
		"certifications": ("first-aid", "cbhfa"),
		"volunteers": 50,
		"from": "2026-09-01",
		"until": "2026-11-30",
	},
	{
		"key": "migration-assistance-point",
		"name": "Migration Assistance Point Volunteer",
		"region": "North Bank Region",
		"purpose": (
			"Providing humanitarian assistance to migrants at the Farafenni border crossing point."
			" Part of the EU-funded Migration Project (2025 to 2029)."
		),
		"responsibilities": (
			"First aid. Psychosocial support. Referral to medical and legal services. Restoring"
			" Family Links support. Distribution of food and hygiene items."
		),
		"certifications": ("psychological-first-aid", "first-aid", "rfl"),
		"volunteers": 8,
		"from": "2026-08-01",
		"until": "2026-12-31",
	},
	{
		"key": "wash-hygiene-promotion",
		"name": "WASH Hygiene Promotion Volunteer",
		"region": "Central River Region",
		"purpose": (
			"Community-level hygiene promotion alongside the Spanish Red Cross-funded borehole project."
		),
		"responsibilities": (
			"Train village water committees on borehole maintenance. Conduct handwashing"
			" demonstrations at schools. Promote safe water storage in households."
		),
		"certifications": ("cbhfa",),
		"volunteers": 10,
		"from": "2026-09-15",
		"until": "2026-09-30",
	},
	{
		"key": "mpox-risk-communication",
		"name": "Mpox Risk Communication Volunteer",
		"region": "Banjul",
		"purpose": (
			"Community-based risk communication and social mobilisation in response to the declared"
			" mpox outbreak. ECV training is provided on onboarding."
		),
		"responsibilities": (
			"Awareness sessions in markets, schools and transport hubs. Counter misinformation."
			" Refer suspected cases to health facilities."
		),
		"certifications": ("ecv",),
		"volunteers": 25,
		"from": "2026-08-01",
		"until": "2026-12-31",
	},
	{
		"key": "youth-peer-educator",
		"name": "Youth Peer Educator, Irregular Migration Awareness",
		"region": "North Bank Region",
		"purpose": "Peer-to-peer education targeting youth considering irregular migration.",
		"responsibilities": (
			"Facilitate group discussions. Share information on legal migration pathways. Connect"
			" returnees with reintegration services. Document stories for the communications team."
		),
		"certifications": ("psychological-first-aid",),
		"volunteers": 12,
		"from": "2026-10-01",
		"until": "2026-12-31",
	},
	{
		"key": "drr-community-mapping",
		"name": "Disaster Risk Reduction Community Mapping Volunteer",
		"region": "Lower River Region",
		"purpose": ("Supporting Vulnerability and Capacity Assessment exercises in flood-prone communities."),
		"responsibilities": (
			"Facilitate community mapping sessions. Collect hazard data using KoboToolbox. Conduct"
			" focus group discussions with community leaders. Assist in producing community-level"
			" disaster preparedness plans."
		),
		"certifications": ("data-collection",),
		"volunteers": 8,
		"from": "2026-10-05",
		"until": "2026-10-15",
	},
)

# --- where the society is -------------------------------------------------

# (region, location name, address, latitude, longitude, phone, hours)
#
# Real coordinates for the seven regional headquarters. Half a coordinate is
# refused at save, so every row here carries both or neither.
LOCATIONS = (
	(
		"Kanifing Municipal",
		"GRCS National Headquarters",
		"56 Mamadi Manyang Highway, Kanifing Industrial Area, P.O. Box 472, Banjul",
		13.4432,
		-16.6790,
		"+220 439 2405",
		"Monday to Friday, 08:30 to 16:30",
	),
	("Banjul", "Banjul Branch", "Banjul", 13.4549, -16.5790, "", "Monday to Friday, 08:30 to 16:30"),
	(
		"West Coast Region",
		"West Coast Region Branch",
		"Brikama, West Coast Region",
		13.2714,
		-16.6494,
		"",
		"Monday to Friday, 08:30 to 16:30",
	),
	(
		"North Bank Region",
		"North Bank Region Branch",
		"Kerewan, North Bank Region",
		13.4894,
		-16.0917,
		"",
		"Monday to Friday, 08:30 to 16:30",
	),
	(
		"Lower River Region",
		"Lower River Region Branch",
		"Mansakonko, Lower River Region",
		13.4333,
		-15.5500,
		"",
		"Monday to Friday, 08:30 to 16:30",
	),
	(
		"Central River Region",
		"Central River Region Branch",
		"Janjanbureh, Central River Region",
		13.5389,
		-14.7669,
		"",
		"Monday to Friday, 08:30 to 16:30",
	),
	(
		"Upper River Region",
		"Upper River Region Branch",
		"Basse Santa Su, Upper River Region",
		13.3097,
		-14.2151,
		"",
		"Monday to Friday, 08:30 to 16:30",
	),
)


# --- the diary ------------------------------------------------------------

# Buzz owns events; vmmsx only reads the published ones, through the one-way
# seam in `vmmsx/buzz/services/events.py`. These are seeded into Buzz's own
# doctypes because that is where an event lives.
EVENT_HOST = gambia.ORGANIZATION_NAME

EVENT_CATEGORIES = (
	("Training", "Courses and refreshers run for volunteers and the public."),
	("Community", "Open days, campaigns and public health activities."),
	("Blood Donation", "Mobile and static blood donation drives."),
	("Fundraising", "Events raising funds for the society's work."),
)

# Buzz makes a venue's address mandatory, so every row carries one.
EVENT_VENUES = (
	("GRCS National Headquarters", "56 Mamadi Manyang Highway, Kanifing Industrial Area, Banjul"),
	("Banjul Branch", "Banjul"),
	("Brikama Branch Office", "Brikama, West Coast Region"),
	("Kerewan Branch Office", "Kerewan, North Bank Region"),
	("Online", "Delivered over video conference"),
)

# `start_in` / `end_in` are days from the day the seed runs, so the diary is
# always ahead of whoever is looking at it — an events page whose newest entry
# is four months old reads as a site nobody maintains.
#
# `where` is a region name resolved through `gambia.region()`, or None. None is
# deliberate and not an oversight: BUZZ-01 made the anchor optional, and an
# unplaced event is shown to everybody rather than filtered out, which is
# exactly right for an online session.
#
# Titles carry no dash. Buzz builds an event's route from its title with
# `cleanup_page_name`, which keeps a dash it does not recognise, and a URL with
# an em dash in it is not one to put on a screen in front of anybody.
EVENTS = (
	{
		"title": "First Aid at Work: two day certificate",
		"category": "Training",
		"venue": "GRCS National Headquarters",
		"medium": "In Person",
		"start_in": 5,
		"end_in": 6,
		"start_time": "08:30:00",
		"end_time": "16:30:00",
		"where": "Kanifing Municipal",
		"summary": (
			"The standard two day certificate, assessed on the second afternoon. Open to"
			" volunteers and to the public."
		),
	},
	{
		"title": "World Blood Donor Day drive",
		"category": "Blood Donation",
		"venue": "Banjul Branch",
		"medium": "In Person",
		"start_in": 9,
		"end_in": None,
		"start_time": "09:00:00",
		"end_time": "17:00:00",
		"where": "Banjul",
		"summary": "Walk in donation with the national blood transfusion service. Bring identification.",
	},
	{
		"title": "Psychological First Aid refresher",
		"category": "Training",
		"venue": "Online",
		"medium": "Online",
		"start_in": 13,
		"end_in": None,
		"start_time": "14:00:00",
		"end_time": "17:00:00",
		"where": None,
		"summary": "A half day online refresher for anybody already holding the certificate.",
	},
	{
		"title": "Brikama branch open day",
		"category": "Community",
		"venue": "Brikama Branch Office",
		"medium": "In Person",
		"start_in": 19,
		"end_in": None,
		"start_time": "10:00:00",
		"end_time": "16:00:00",
		"where": "West Coast Region",
		"summary": (
			"Meet the branch team, see the response equipment, and find out what volunteering"
			" here actually involves."
		),
	},
	{
		"title": "Volunteer induction for the new intake",
		"category": "Training",
		"venue": "GRCS National Headquarters",
		"medium": "In Person",
		"start_in": 24,
		"end_in": None,
		"start_time": "09:00:00",
		"end_time": "13:00:00",
		"where": "Kanifing Municipal",
		"summary": "Everything a newly accepted volunteer needs before their first deployment.",
	},
	{
		"title": "Community health outreach in Kerewan",
		"category": "Community",
		"venue": "Kerewan Branch Office",
		"medium": "In Person",
		"start_in": 31,
		"end_in": 32,
		"start_time": "08:00:00",
		"end_time": "15:00:00",
		"where": "North Bank Region",
		"summary": "Two days of screening and health promotion with the North Bank branch team.",
	},
	{
		"title": "Annual charity walk",
		"category": "Fundraising",
		"venue": "GRCS National Headquarters",
		"medium": "In Person",
		"start_in": 45,
		"end_in": None,
		"start_time": "06:30:00",
		"end_time": "12:00:00",
		"where": "Kanifing Municipal",
		"summary": "Ten kilometres along the coast road, raising funds for the branch emergency fund.",
	},
)


def main(commit: bool = True) -> dict:
	"""Seed the society's operations and report what changed. Safe to re-run."""
	if not gambia.national():
		print("The Gambia configuration is not on this site. Run vmmsx.seed.gambia.main first.")
		return {}

	report = {
		"skills": _vocabulary("VMMS Skill", "skill", SKILLS),
		"motivations": _vocabulary("VMMS Motivation", "motivation", MOTIVATIONS),
		"availability": _vocabulary("VMMS Availability Slot", "slot", AVAILABILITY),
		"time_log_categories": _vocabulary("VMMS Time Log Category", "category", TIME_LOG_CATEGORIES),
		"announcement_types": _announcement_types(),
		"certification_types": _certification_types(),
		"terms_of_reference": _terms_of_reference(),
		"opportunities": _opportunities(),
		"locations": _locations(),
		"event_setup": _event_setup(),
		"events": _events(),
		"stories": _stories(),
	}

	if commit:
		frappe.db.commit()

	_print(report)

	return report


# --- the vocabularies -----------------------------------------------------


def _vocabulary(doctype: str, prefix: str, rows: tuple) -> list[dict]:
	"""One shape for four doctypes: `<prefix>_key`, `<prefix>_name`, description.

	They differ only in what the prefix is called, which is a naming convention
	rather than four different ideas, so one function writes all four.
	"""
	report = []

	for key, label, description in rows:
		if frappe.db.exists(doctype, key):
			report.append({"key": key, "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": doctype,
				f"{prefix}_key": key,
				f"{prefix}_name": label,
				"description": description,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		report.append({"key": key, "status": "created"})

	return report


def _announcement_types() -> list[dict]:
	rows = []

	for label, description in ANNOUNCEMENT_TYPES:
		if frappe.db.exists("VMMS Announcement Type", label):
			rows.append({"key": label, "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": "VMMS Announcement Type",
				"__newname": label,
				"description": description,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)

		rows.append({"key": label, "status": "created"})

	return rows


def _certification_types() -> list[dict]:
	rows = []

	for key, label, validity, blocks, description in CERTIFICATION_TYPES:
		if frappe.db.exists("VMMS Certification Type", key):
			rows.append({"key": key, "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": "VMMS Certification Type",
				"certification_type_key": key,
				"certification_type_name": label,
				"validity_days": validity,
				"blocks_deployment_when_lapsed": blocks,
				"description": description,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		rows.append({"key": key, "status": "created", "validity": f"{validity}d"})

	return rows


# --- the roles and the openings -------------------------------------------


def _terms_of_reference() -> list[dict]:
	rows = []

	for opportunity in OPPORTUNITIES:
		if frappe.db.exists("VMMS Terms of Reference", opportunity["key"]):
			rows.append({"key": opportunity["key"], "status": "exists"})
			continue

		node = gambia.region(opportunity["region"])

		if not node:
			rows.append({"key": opportunity["key"], "status": f"skipped: no {opportunity['region']}"})
			continue

		# A certification named here but absent from the site is dropped rather
		# than failing the insert: the requirement list is the society's wish and
		# the vocabulary above is what this site actually knows.
		required = [
			{"certification_type": key}
			for key in opportunity["certifications"]
			if frappe.db.exists("VMMS Certification Type", key)
		]

		frappe.get_doc(
			{
				"doctype": "VMMS Terms of Reference",
				"tor_key": opportunity["key"],
				"tor_name": opportunity["name"],
				"purpose": opportunity["purpose"],
				"responsibilities": opportunity["responsibilities"],
				"geo_scope": node,
				"default_duration_days": _days(opportunity),
				# `direct`, because advertising an opportunity is not a request
				# the branch owes anybody an approval for. Under `routed` a
				# request stays unsettled until somebody approves it, and
				# `api/opportunities.py::_is_offered` asks the deployment
				# service whether the approval requirement is *met* rather than
				# comparing a state — so a routed request nobody has approved is
				# published and invisible, which is the worst of both.
				"approval_mode": "direct",
				"required_certifications": required,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		rows.append({"key": opportunity["key"], "status": "created", "requires": len(required)})

	return rows


def _opportunities() -> list[dict]:
	"""One published Deployment Request per role. `is_published` is the whole
	of the guest-read rule, so a request created here and not flagged would be
	a role nobody outside the desk can see."""
	rows = []

	for opportunity in OPPORTUNITIES:
		if not frappe.db.exists("VMMS Terms of Reference", opportunity["key"]):
			rows.append({"key": opportunity["key"], "status": "skipped: no terms of reference"})
			continue

		node = gambia.region(opportunity["region"])
		existing = frappe.db.exists(
			"VMMS Deployment Request",
			{"terms_of_reference": opportunity["key"], "geo_node": node, "needed_from": opportunity["from"]},
		)

		if existing:
			rows.append({"key": opportunity["key"], "name": existing, "status": "exists"})
			continue

		request = frappe.get_doc(
			{
				"doctype": "VMMS Deployment Request",
				"terms_of_reference": opportunity["key"],
				"geo_node": node,
				"volunteers_requested": opportunity["volunteers"],
				"needed_from": opportunity["from"],
				"needed_until": opportunity["until"],
				"justification": opportunity["purpose"],
				"is_published": 1,
			}
		).insert(ignore_permissions=True)

		rows.append(
			{
				"key": opportunity["key"],
				"name": request.name,
				"status": "created",
				"places": opportunity["volunteers"],
				"at": opportunity["region"],
			}
		)

	return rows


def _days(opportunity: dict) -> int:
	from frappe.utils import date_diff

	return max(1, date_diff(opportunity["until"], opportunity["from"]) + 1)


# --- where the society is -------------------------------------------------


def _locations() -> list[dict]:
	rows = []

	for region, label, address, latitude, longitude, phone, hours in LOCATIONS:
		node = gambia.region(region)

		if not node:
			rows.append({"key": label, "status": f"skipped: no {region}"})
			continue

		if frappe.db.exists("VMMS Branch Location", {"location_name": label, "geo_node": node}):
			rows.append({"key": label, "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": "VMMS Branch Location",
				"location_name": label,
				"geo_node": node,
				"address": address,
				"latitude": latitude,
				"longitude": longitude,
				"phone": phone,
				"opening_hours": hours,
				"is_published": 1,
			}
		).insert(ignore_permissions=True)

		rows.append({"key": label, "status": "created", "at": f"{latitude},{longitude}"})

	return rows


# --- the diary ------------------------------------------------------------


def _event_setup() -> list[dict]:
	"""Buzz's own host, categories and venues. Its records, its rules.

	Skipped whole when Buzz is not installed, which is the same graceful absence
	`vmmsx/buzz/services/events.py` keeps: a society running without Buzz is an
	ordinary state, and the portal's events screen says the app is not there
	rather than showing an empty list.
	"""
	if not frappe.db.exists("DocType", "Buzz Event"):
		return [{"key": "buzz", "status": "skipped: Buzz is not installed"}]

	rows = []

	if frappe.db.exists("Event Host", EVENT_HOST):
		rows.append({"key": EVENT_HOST, "status": "exists"})
	else:
		frappe.get_doc(
			{"doctype": "Event Host", "__newname": EVENT_HOST, "by_line": gambia.ORGANIZATION_NAME}
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
	"""Published events in Buzz, dated forward from the day this runs.

	The anchor is vmmsx's one custom field on `Buzz Event` (BUZZ-01) and it is
	optional by design, so one event below carries none at all. `route` is left
	for Buzz to generate: its own `validate_route` builds one from the title on
	publish, and a seed writing that field would be this app deciding another
	app's URLs.
	"""
	if not frappe.db.exists("DocType", "Buzz Event"):
		return [{"key": "buzz", "status": "skipped: Buzz is not installed"}]

	from vmmsx.buzz.services import geo

	rows = []

	for spec in EVENTS:
		if frappe.db.exists("Buzz Event", {"title": spec["title"]}):
			rows.append({"key": spec["title"], "status": "exists"})
			continue

		node = gambia.region(spec["where"]) if spec["where"] else None

		if spec["where"] and not node:
			rows.append({"key": spec["title"], "status": f"skipped: no {spec['where']}"})
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
				geo.GEO_NODE_FIELD: node,
			}
		)
		event.insert(ignore_permissions=True)

		rows.append({"key": spec["title"], "status": "created", "route": event.route or "none"})

	return rows


# --- the stories ----------------------------------------------------------


def _stories() -> list[dict]:
	"""Core's `Article`, one per published report, each carrying its source.

	Called through a lazy import of the story text so this module reads as the
	operations it seeds rather than as twelve pages of prose. `source_url` is
	the point: every claim on the site's stories page leads back to the
	publication it came from.
	"""
	from vmmsx.seed.gambia_stories import STORIES

	rows = []
	article_type = _localisation("Localisation Type", "type_name", "Story")
	category = _localisation("Localisation Category", "category_name", "Humanitarian Action")

	if not (article_type and category):
		return [{"key": "stories", "status": "skipped: Article needs a Type and a Category"}]

	for story in STORIES:
		if frappe.db.exists("Article", {"slug": story["slug"]}):
			rows.append({"key": story["slug"], "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": "Article",
				"title": story["title"],
				"slug": story["slug"],
				"subtitle": story["subtitle"],
				"article_type": article_type,
				"category": category,
				"location": story["location"],
				"summary": story["summary"],
				"body": "".join(f"<p>{para}</p>" for para in story["body"]),
				"author": "Administrator",
				"source_name": story["source_name"],
				"source_url": story["source_url"],
				"status": "Published",
				"published_on": story["published_on"],
				"is_featured": story.get("featured", 0),
			}
		).insert(ignore_permissions=True)

		rows.append({"key": story["slug"], "status": "created"})

	return rows


def _localisation(doctype: str, field: str, label: str) -> str | None:
	"""Find or create one of core's Article vocabularies.

	`Article` makes both mandatory, and a site that has never used core's
	knowledge hub has neither. Creating one is the same act an editor performs
	on first use, so the seed does it rather than refusing to write a story.

	**The field name is passed in because both doctypes autoname from one**, and
	this is the bug that cost a fresh site its twelve stories. Setting `name`
	directly does nothing on a `field:` autoname — the document is inserted with
	an empty `type_name`, the controller refuses it as mandatory, and the
	`except` below turned that refusal into a quiet `None` and a skipped
	section. On a bench where somebody had already created a type by hand the
	first lookup found one and the bug never showed; on a new site every story
	silently vanished.

	The exception is still swallowed, because a society that has no knowledge
	hub configured should get its volunteers and its events rather than an
	install that stops. It now says so in the report instead of leaving the
	caller to guess.
	"""
	if not frappe.db.exists("DocType", doctype):
		return None

	existing = frappe.db.get_value(doctype, {field: label}, "name") or frappe.db.get_value(
		doctype, {}, "name"
	)

	if existing:
		return existing

	try:
		return (
			frappe.get_doc({"doctype": doctype, field: label, "is_active": 1})
			.insert(ignore_permissions=True)
			.name
		)
	except Exception:
		frappe.log_error(title=f"Seed could not create {doctype} {label!r}")

		return None


# --- the report -----------------------------------------------------------


def _print(report: dict) -> None:
	print(f"\nGambia Red Cross Society operations on {frappe.local.site}\n" + "=" * 60)

	for section, rows in report.items():
		created = sum(1 for row in rows if row["status"] == "created")
		print(f"\n{section.replace('_', ' ').title()}  ({created} created, {len(rows)} total)")

		for row in rows:
			extra = " ".join(f"{k}={v}" for k, v in row.items() if k not in ("key", "status"))
			print(f"  [{row['status']:<28}] {row['key']}{'  ' + extra if extra else ''}")

	print()
