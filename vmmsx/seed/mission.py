# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Filling in a demonstration mission document, and two small registers it needs.

A terms of reference cannot be submitted until it is finished — a programme, a
period, a place, a background, objectives, outputs, stakeholders, an itinerary,
and either resource lines or an explicit statement that it needs none. That rule
is `deployment/services/terms.py::REQUIRED_AT_SUBMISSION`, and it is right: what
a volunteer accepts when they accept an assignment is exactly this document.

It also means every seeded terms of reference has to be a complete mission
document, and most of this app's seeds were written when three fields were
enough. `tanzania_deployments.py` writes its missions out in full, because that
site exists to be demonstrated and a generated itinerary would look like one.
The rest — Kenya's nineteen, Gambia's fifteen — get their structure from here.

**What comes out of `furnish` is scaffolding, and it says so.** Every sentence
is built from the terms' own purpose and responsibilities, which the seed did
write, so nothing here invents a fact about a society. It is the shape of a
mission document rather than a mission document, and its purpose is that a
freshly seeded site has a register of specifications that can actually be used
rather than nineteen drafts. A society replaces the wording the first time it
opens one.

**Nothing here is product behaviour.** No service imports this module; only
seeds do. The rule it satisfies lives in `terms.py`, and if that rule changes,
this is one of the places that has to follow — which is the correct direction,
and the reason the required list is not restated here.
"""

import frappe
from frappe.utils import add_days, today

PROJECT_DOCTYPE = "Project"
UOM_DOCTYPE = "UOM"


def uom(word: str) -> str:
	"""The `UOM` a seed's own word for a unit resolves to, created if absent.

	A mission's resource lines count in ERPNext's UOM register now, and a Link
	refuses a value that is not in it. ERPNext ships Unit, Nos, Box, Set, Day and
	two hundred more, and does not ship "Kit" — which is a real unit a relief
	operation counts in. Matched case-insensitively so "unit" finds "Unit" rather
	than creating a second one that differs by a capital letter.
	"""
	existing = frappe.db.get_value(UOM_DOCTYPE, {"uom_name": word}, "name")

	if existing:
		return existing

	for candidate in frappe.get_all(UOM_DOCTYPE, pluck="name"):
		if candidate.lower() == word.strip().lower():
			return candidate

	return frappe.get_doc({"doctype": UOM_DOCTYPE, "uom_name": word.strip(), "enabled": 1}).insert(
		ignore_permissions=True
	).name


def standing_project(name: str, geo_node: str, summary: str, company: str | None = None) -> str:
	"""The programme a seed's ungrouped terms of reference are written under.

	Every terms of reference belongs to a programme now, and a society's standing
	work — branch first aid duty, the blood drive rota, the family links desk —
	genuinely is a programme even though nobody thought of it as one while it was
	a list of opportunities. This is that programme, one per society, created on
	first use and found by name afterwards.

	Inserted directly rather than through `api/deployment.py::create_project`
	because a seed runs as Administrator, who is unrestricted, and the endpoint's
	authority check would be answering a question nobody asked.
	"""
	from vmmsx.deployment.services import project as project_service

	existing = frappe.db.get_value(PROJECT_DOCTYPE, {"project_name": name}, "name")

	if existing:
		return existing

	doc = frappe.get_doc(
		{
			"doctype": PROJECT_DOCTYPE,
			"project_name": name,
			"company": company or project_service.default_company(),
			"status": project_service.STATUS_OPEN,
			"vmms_geo_node": geo_node,
			"notes": summary,
		}
	)
	doc.insert(ignore_permissions=True)

	return doc.name


def furnish(
	*,
	name: str,
	purpose: str,
	responsibilities: str,
	geo_node: str,
	project: str,
	starts_in: int = 0,
	days: int = 1,
) -> dict:
	"""The mission tables a seeded terms of reference needs to be submittable.

	Returns exactly the keys `create_terms` takes, so a seed spreads it into the
	call and adds nothing of its own. Every value is derived from the two things
	the seed already wrote — what the work is for, and what the volunteer does —
	so the document says nothing this app invented about a society.

	The itinerary is briefing, work, debrief, clamped inside the period, because
	`validate_itinerary` refuses a row dated outside it and a one-day mission has
	all three on the same day.
	"""
	opens = add_days(today(), starts_in)
	closes = add_days(today(), starts_in + max(days - 1, 0))
	duties = [line.strip() for line in (responsibilities or "").splitlines() if line.strip()]

	return {
		"project": project,
		"geo_scope": geo_node,
		"expected_start_date": opens,
		"expected_end_date": closes,
		"mission_background": (
			f"<p>{purpose}</p><p>The branch runs this work often enough to keep a written"
			" specification for it, so that everybody asked to take part is asked on the same"
			" terms and knows what the mission is for before they answer.</p>"
		),
		"objectives": [
			{"objective": f"Deliver {name} safely and to the branch's own standards."},
			*[{"objective": f"Carry out the work as specified: {duty}"} for duty in duties[:2]],
		],
		"expected_outputs": [
			{"output": "A daily report to the branch operations desk for each day worked."},
			{"output": "A complete record of who took part and for how long."},
			{"output": "A short end-of-mission note from the team leader."},
		],
		"stakeholders": [
			{"designation": "Branch Coordinator"},
			{"designation": "Team Leader"},
		],
		"itinerary": [
			{"activity_date": opens, "activity": "Briefing and team assignment", "person_responsible": "Team Leader"},
			{"activity_date": opens, "activity": name, "person_responsible": "Team Leader"},
			{"activity_date": closes, "activity": "Debrief and hand over the record", "person_responsible": "Branch Coordinator"},
		],
		# The explicit half of the resources rule. These specifications are for
		# standing work a branch resources from its own stock, so the honest
		# answer is that the mission budgets nothing — and saying so is what
		# distinguishes it from a table somebody had not got to yet.
		"has_no_resources": 1,
	}
