# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Tanzania Red Cross Society's operations: what it does, and what it did.

    bench --site <site> execute vmmsx.seed.tanzania_operations.main

Kept separate from `tanzania.py` for the reason `gambia_operations.py` is kept
separate from `gambia.py`: configuration is what a society *holds* and an
operation is what it *did last month*.

It requires `tanzania.py` to have run, and reads that society's nodes by shape
rather than by name.

**What is in here, and where it came from.**

* **Vocabularies** — skills, motivations, availability, time-log categories,
  certification types and announcement types. Ordinary Red Cross vocabulary,
  not specific to any one branch's own records.
* **Job openings** — delegated to `tanzania_jobs.py`, which is where the
  sourcing note for those lives, since it needs its own HRMS prerequisites.
* **Events** — seven Buzz events, dated forward from the day this runs, one of
  them the real World First Aid Day (12 September, the second Saturday of
  September, an IFRC-wide observance every Red Cross society marks).
* **Stories** — four articles in `tanzania_stories.py`, each sourced from a
  published TRCS, EU or European Commission report, submitted so the public
  reader actually returns them (see that module and `_stories()` below for why
  submission, not just `status`, is what makes an article visible).
* **Branch locations** — a handful of real regional headquarters, with real
  coordinates, published so they draw on the public map.

**What is deliberately not in here: people, and the old opportunities-board
pattern.** No volunteer, no member and no Red Profile is created, for the same
reason `gambia_operations.py` creates none. And unlike Gambia's and Kenya's
operations seeds, this one does not create `VMMS Terms of Reference` or
`VMMS Deployment Request` — `api/opportunities.py` (HR-01) reads the live
opportunities board from HRMS's `Job Opening` now, not from that older pair,
so seeding the old doctypes here would populate a board the site no longer
reads. See `tanzania_jobs.py`.

Idempotent, and it says what it did.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.seed import tanzania

# --- the society's vocabularies -------------------------------------------

SKILLS = (
	("first-aid", "First Aid", "Basic and advanced first aid, delivered under a branch first aider."),
	("psychosocial-support", "Psychosocial Support", "Psychological first aid and community support."),
	("community-health", "Community Health", "Household visits, hygiene and health promotion."),
	("water-safety", "Water Safety and Rescue", "Search, evacuation and rescue on and near water."),
	("logistics", "Logistics", "Warehousing, distribution and fleet support during an operation."),
	("communications", "Communications", "Risk communication, social mobilisation and reporting."),
	("data-collection", "Data Collection", "Assessments, surveys and community mapping."),
	("restoring-family-links", "Restoring Family Links", "Tracing requests and family reunification."),
	("youth-leadership", "Youth Leadership", "Peer education and running a branch's youth programme."),
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
	("emergency-response", "Emergency Response", "Flood, landslide and outbreak response."),
	("health-campaign", "Health Campaign", "Community health outreach and awareness campaigns."),
	("first-aid-duty", "First Aid Duty", "Staffing a first aid post at an event."),
	("training", "Training", "Attending or delivering a course."),
	("branch-admin", "Branch Administration", "Meetings, registration and branch administration."),
	("blood-drive", "Blood Drive", "Supporting a mobile or fixed blood donation session."),
)

CERTIFICATION_TYPES = (
	("first-aid", "First Aid", 730, 1, "Basic first aid certificate, renewed every two years."),
	("advanced-first-aid", "Advanced First Aid", 730, 1, "Advanced life support and trauma care."),
	("disaster-response", "Disaster Response", 1095, 1, "Flood and landslide response, as run in Mbeya."),
	("cbha", "Community-Based Health and Awareness", 1095, 0, "Household-visit health promotion methodology."),
	("psychological-first-aid", "Psychological First Aid", 1095, 0, "Psychosocial support for survivors."),
	("water-safety", "Water Safety and Rescue", 730, 1, "Rescue on and near water, for flood response."),
	("rfl", "Restoring Family Links", 1095, 0, "Tracing procedure and the Family Links Network."),
)

ANNOUNCEMENT_TYPES = (
	("General", "Branch and national notices."),
	("Emergency", "Flood, landslide and outbreak alerts."),
	("Training", "Course announcements and calls to enrol."),
	("Event", "Blood drives, campaigns and public events."),
)

# --- where the society is -------------------------------------------------

# (region, location name, address, latitude, longitude, phone, hours)
LOCATIONS = (
	(
		"Dar es Salaam",
		"TRCS National Headquarters",
		"Mwai Kibaki Road, Plot 53, Block C, Mikocheni B, P.O. Box 1133, Dar es Salaam",
		-6.7735,
		39.2380,
		"0800 750 150",
		"Monday to Friday, 08:00 to 16:00",
	),
	("Arusha", "Arusha Regional Branch", "Arusha", -3.3869, 36.6830, "", "Monday to Friday, 08:00 to 16:00"),
	("Mwanza", "Mwanza Regional Branch", "Mwanza", -2.5164, 32.9175, "", "Monday to Friday, 08:00 to 16:00"),
	("Mbeya", "Mbeya Regional Branch", "Mbeya", -8.9094, 33.4608, "", "Monday to Friday, 08:00 to 16:00"),
	("Dodoma", "Dodoma Regional Branch", "Dodoma", -6.1630, 35.7516, "", "Monday to Friday, 08:00 to 16:00"),
	(
		"Mjini Magharibi",
		"Zanzibar Regional Branch",
		"Zanzibar Town, Mjini Magharibi",
		-6.1659,
		39.2026,
		"",
		"Monday to Friday, 08:00 to 16:00",
	),
	("Kigoma", "Kigoma Regional Branch", "Kigoma", -4.8766, 29.6267, "", "Monday to Friday, 08:00 to 16:00"),
)

# --- the diary --------------------------------------------------------------

EVENT_HOST = tanzania.ORGANIZATION_NAME

EVENT_CATEGORIES = (
	("Training", "Courses and refreshers run for volunteers and the public."),
	("Community", "Open days, campaigns and public health activities."),
	("Blood Donation", "Mobile and static blood donation drives."),
	("Fundraising", "Events raising funds for the society's work."),
)

EVENT_VENUES = (
	("TRCS National Headquarters", "Mwai Kibaki Road, Mikocheni B, Dar es Salaam"),
	("Mwanza Branch Office", "Mwanza"),
	("Arusha Branch Office", "Arusha"),
	("Zanzibar Branch Office", "Zanzibar Town, Mjini Magharibi"),
	("Mbeya Branch Office", "Mbeya"),
	("Online", "Delivered over video conference"),
)

# `start_in` / `end_in` are days from the day the seed runs, so the diary is
# always ahead of whoever is looking at it.
#
# The first row is real: World First Aid Day falls on the second Saturday of
# September every year (12 September in 2026), and every Red Cross and Red
# Crescent society, TRCS included, is expected to mark it — that is the one
# date in this list that is not invented for the demo.
EVENTS = (
	{
		"title": "World First Aid Day public demonstration",
		"category": "Community",
		"venue": "TRCS National Headquarters",
		"medium": "In Person",
		"start_date": "2026-09-12",
		"end_date": None,
		"start_time": "09:00:00",
		"end_time": "14:00:00",
		"where": "Dar es Salaam",
		"summary": (
			"Free first aid demonstrations and a walk-in refresher, marking World First Aid Day"
			" alongside Red Cross and Red Crescent societies worldwide."
		),
	},
	{
		"title": "First Aid at Work two day certificate",
		"category": "Training",
		"venue": "TRCS National Headquarters",
		"medium": "In Person",
		"start_in": 5,
		"end_in": 6,
		"start_time": "08:30:00",
		"end_time": "16:30:00",
		"where": "Dar es Salaam",
		"summary": (
			"The standard two day certificate, assessed on the second afternoon. Open to"
			" volunteers and to the public."
		),
	},
	{
		"title": "Mwanza regional blood donor drive",
		"category": "Blood Donation",
		"venue": "Mwanza Branch Office",
		"medium": "In Person",
		"start_in": 9,
		"end_in": None,
		"start_time": "09:00:00",
		"end_time": "17:00:00",
		"where": "Mwanza",
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
		"title": "Arusha branch open day",
		"category": "Community",
		"venue": "Arusha Branch Office",
		"medium": "In Person",
		"start_in": 19,
		"end_in": None,
		"start_time": "10:00:00",
		"end_time": "16:00:00",
		"where": "Arusha",
		"summary": (
			"Meet the branch team, see the response equipment, and find out what volunteering"
			" here actually involves."
		),
	},
	{
		"title": "Zanzibar heat safety and albinism awareness session",
		"category": "Community",
		"venue": "Zanzibar Branch Office",
		"medium": "In Person",
		"start_in": 31,
		"end_in": 32,
		"start_time": "08:00:00",
		"end_time": "15:00:00",
		"where": "Mjini Magharibi",
		"summary": (
			"A follow-on round of the branch's heat safety and albinism awareness campaign, in"
			" schools and markets around Zanzibar Town."
		),
	},
	{
		"title": "Volunteer induction for the new intake",
		"category": "Training",
		"venue": "TRCS National Headquarters",
		"medium": "In Person",
		"start_in": 24,
		"end_in": None,
		"start_time": "09:00:00",
		"end_time": "13:00:00",
		"where": "Dar es Salaam",
		"summary": "Everything a newly accepted volunteer needs before their first deployment.",
	},
)


def main(commit: bool = True) -> dict:
	"""Seed the society's operations and report what changed. Safe to re-run."""
	if not tanzania.national():
		print("The Tanzania configuration is not on this site. Run vmmsx.seed.tanzania.main first.")
		return {}

	from vmmsx.seed import tanzania_jobs

	report = {
		"skills": _vocabulary("VMMS Skill", "skill", SKILLS),
		"motivations": _vocabulary("VMMS Motivation", "motivation", MOTIVATIONS),
		"availability": _vocabulary("VMMS Availability Slot", "slot", AVAILABILITY),
		"time_log_categories": _vocabulary("VMMS Time Log Category", "category", TIME_LOG_CATEGORIES),
		"announcement_types": _announcement_types(),
		"certification_types": _certification_types(),
		"locations": _locations(),
		"event_setup": _event_setup(),
		"events": _events(),
		"stories": _stories(),
	}

	# Flattened rather than nested under one "job_openings" key: `_print` below
	# assumes every section is a flat list of report rows, the same shape
	# every step above already returns, and `tanzania_jobs.main()` returns a
	# dict of several such lists (company, departments, designations,
	# branches, job_openings) because it has its own multi-step prerequisite
	# chain to report on.
	report.update(tanzania_jobs.main(commit=False))

	if commit:
		frappe.db.commit()

	_print(report)

	return report


def _vocabulary(doctype: str, prefix: str, rows: tuple) -> list[dict]:
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


def _locations() -> list[dict]:
	rows = []

	for region_name, label, address, latitude, longitude, phone, hours in LOCATIONS:
		node = tanzania.region(region_name)

		if not node:
			rows.append({"key": label, "status": f"skipped: no {region_name}"})
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


def _event_setup() -> list[dict]:
	if not frappe.db.exists("DocType", "Buzz Event"):
		return [{"key": "buzz", "status": "skipped: Buzz is not installed"}]

	rows = []

	if frappe.db.exists("Event Host", EVENT_HOST):
		rows.append({"key": EVENT_HOST, "status": "exists"})
	else:
		frappe.get_doc(
			{"doctype": "Event Host", "__newname": EVENT_HOST, "by_line": tanzania.ORGANIZATION_NAME}
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
	if not frappe.db.exists("DocType", "Buzz Event"):
		return [{"key": "buzz", "status": "skipped: Buzz is not installed"}]

	from vmmsx.buzz.services import geo

	rows = []

	for spec in EVENTS:
		if frappe.db.exists("Buzz Event", {"title": spec["title"]}):
			rows.append({"key": spec["title"], "status": "exists"})
			continue

		node = tanzania.region(spec["where"]) if spec["where"] else None

		if spec["where"] and not node:
			rows.append({"key": spec["title"], "status": f"skipped: no {spec['where']}"})
			continue

		start_date = spec.get("start_date") or add_days(today(), spec["start_in"])
		end_date = spec.get("end_date")

		if end_date is None and spec.get("end_in"):
			end_date = add_days(today(), spec["end_in"])

		event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": spec["title"],
				"category": spec["category"],
				"venue": spec["venue"],
				"medium": spec["medium"],
				"host": EVENT_HOST,
				"start_date": start_date,
				"end_date": end_date,
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


def _stories() -> list[dict]:
	"""Core's `Article`, one per published report, each carrying its source.

	Submitted, not just marked Published: `onerc_core/api/article.py`'s guest
	reader filters on `docstatus = 1` as well as `status = "Published"`, so an
	article that is only saved is invisible on the portal even though it looks
	published on the desk. `gambia_stories.py` does not submit and is a known
	gap for that reason; this seed follows `kenya_operations.py::_articles`
	instead, which does.
	"""
	from vmmsx.seed.tanzania_stories import STORIES

	rows = []
	article_type = _localisation("Localisation Type", "type_name", "Story")

	if not article_type:
		return [{"key": "stories", "status": "skipped: Article needs a Type"}]

	author = tanzania.APPROVER_USER if frappe.db.exists("User", tanzania.APPROVER_USER) else "Administrator"

	for story in STORIES:
		if frappe.db.exists("Article", {"slug": story["slug"]}):
			rows.append({"key": story["slug"], "status": "exists"})
			continue

		# Each story names its own category — floods and landslides are
		# "Emergency Response", not whatever category happened to be created
		# first on the site. `_localisation` only falls back to an unrelated
		# existing row when the exact label truly cannot be created (see its
		# own docstring); naming the label a story actually wants avoids ever
		# hitting that fallback for a category that is simply missing.
		category = _localisation("Localisation Category", "category_name", story["category"])

		if not category:
			rows.append({"key": story["slug"], "status": "skipped: Article needs a Category"})
			continue

		article = frappe.get_doc(
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
				"author": author,
				"source_name": story["source_name"],
				"source_url": story["source_url"],
				"status": "Published",
				"published_on": story["published_on"],
				"is_featured": story.get("featured", 0),
			}
		)
		article.insert(ignore_permissions=True)
		article.submit()

		rows.append({"key": story["slug"], "status": "created"})

	return rows


def _localisation(doctype: str, field: str, label: str) -> str | None:
	if not frappe.db.exists("DocType", doctype):
		return None

	existing = frappe.db.get_value(doctype, {field: label}, "name") or frappe.db.get_value(doctype, {}, "name")

	if existing:
		return existing

	try:
		return (
			frappe.get_doc({"doctype": doctype, field: label, "is_active": 1}).insert(ignore_permissions=True).name
		)
	except Exception:
		frappe.log_error(title=f"Seed could not create {doctype} {label!r}")

		return None


def _print(report: dict) -> None:
	print(f"\nTanzania Red Cross Society operations on {frappe.local.site}\n" + "=" * 60)

	for section, rows in report.items():
		created = sum(1 for row in rows if row["status"] == "created")
		print(f"\n{section.replace('_', ' ').title()}  ({created} created, {len(rows)} total)")

		for row in rows:
			extra = " ".join(f"{k}={v}" for k, v in row.items() if k not in ("key", "status"))
			print(f"  [{row['status']:<28}] {row['key']}{'  ' + extra if extra else ''}")

	print()
