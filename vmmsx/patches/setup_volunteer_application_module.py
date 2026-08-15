# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Seed the structured vocabularies `VMMS Volunteer Application` offers.

Three starting sets, all idempotent, all *seeds a society then edits* rather
than constants the code depends on. Nothing under `vmmsx/volunteer/` or the
application's own controller branches on any key seeded here — a society may
rename, deactivate or add to every one of them and no source file changes.

Every step checks before it writes, so re-running the patch — which migrate
will do on a site that already has all three — changes nothing and overwrites
nothing an administrator has since edited.
"""

import frappe

SKILLS = (
	("first_aid", "First Aid", "Basic life support and emergency first response."),
	("driving", "Driving", "Holds a licence and is willing to drive society vehicles."),
	("logistics", "Logistics", "Warehousing, distribution and supply coordination."),
	("counselling", "Counselling", "Psychosocial support and active listening."),
	("it", "IT", "Computers, data entry and digital tools."),
	("translation", "Translation", "Interpreting or translating between languages."),
)

MOTIVATIONS = (
	("community_service", "Community Service", "Wanting to give back to the community."),
	("skill_building", "Skill-building", "Learning new, transferable skills."),
	("career_development", "Career Development", "Building experience relevant to a career."),
	("faith", "Faith", "Acting on a religious or spiritual conviction."),
	("personal_growth", "Personal Growth", "Personal development or a new challenge."),
)

AVAILABILITY_SLOTS = (
	("weekday_mornings", "Weekday Mornings", "Weekdays, before midday."),
	("weekday_evenings", "Weekday Evenings", "Weekdays, after work hours."),
	("weekend_mornings", "Weekend Mornings", "Saturdays and Sundays, before midday."),
	("weekend_evenings", "Weekend Evenings", "Saturdays and Sundays, after midday."),
	("public_holidays", "Public Holidays", "Gazetted public holidays."),
	("on_call", "On-call", "Available on short notice, outside a fixed slot."),
)


def execute():
	install_skills()
	install_motivations()
	install_availability_slots()


def install_skills() -> None:
	_seed("VMMS Skill", "skill_key", "skill_name", SKILLS)


def install_motivations() -> None:
	_seed("VMMS Motivation", "motivation_key", "motivation_name", MOTIVATIONS)


def install_availability_slots() -> None:
	_seed("VMMS Availability Slot", "slot_key", "slot_name", AVAILABILITY_SLOTS)


def _seed(doctype: str, key_field: str, name_field: str, rows: tuple) -> None:
	for key, name, description in rows:
		if frappe.db.exists(doctype, key):
			continue

		frappe.get_doc(
			{
				"doctype": doctype,
				key_field: key,
				name_field: name,
				"description": description,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
