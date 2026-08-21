# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Two starting vocabularies a society edits from the moment they land.

Both are configuration on the same footing as `VMMS Skill` and
`VMMS Motivation`: an open set, seeded with something usable, owned by the
society afterwards, and **branched on by no code anywhere**.

Availability windows with hours
-------------------------------

`setup_volunteer_application_module` already seeds availability slots, and they
are day-scoped by design — "Weekday Mornings", "Weekend Evenings". Those are
right for what they were built for: a self-description a volunteer picks at
intake and a coordinator searches on.

They are wrong as columns in `VMMS Availability Schedule`'s weekly grid, whose
rows are already the seven days. "Weekday Mornings" against Sunday means nothing
anybody could act on. What that grid needs is a span of the *day*, day-agnostic
by construction, so this seeds four of those with real opening and closing
times. `availability.slots()` shows a window in the grid only once it carries
hours, which is what keeps the two kinds apart without either of them having to
know about the other.

The hours are a starting point and nothing reads them as policy: a society whose
afternoons run to six o'clock edits the row.

Mission methodologies
---------------------

`VMMS TOR Methodology` is the register a terms of reference picks its approach
from. An empty register means the approach tab of the mission editor has nothing
to offer, which is a worse first experience than a handful of methods a society
can rename or retire. These are drawn from what humanitarian missions actually
do rather than from anything this app needs — no source file mentions any of
them.

**What is still deliberately not seeded is a terms of reference.** Those name
real work a society does, and this app has no business inventing one. That
argument has not changed; a vocabulary a mission is *written with* is a
different thing from the mission itself.

Every step checks before it writes, so re-running changes nothing and overwrites
nothing an administrator has since edited.
"""

import frappe

SLOT_DOCTYPE = "VMMS Availability Slot"
METHODOLOGY_DOCTYPE = "VMMS TOR Methodology"

# key, label, opens, closes, description
SCHEDULABLE_WINDOWS = (
	("morning", "Morning", "08:00:00", "12:00:00", "The first half of the day."),
	("afternoon", "Afternoon", "12:00:00", "17:00:00", "The second half of the day."),
	("evening", "Evening", "17:00:00", "21:00:00", "After the working day."),
	(
		"overnight",
		"Overnight",
		"21:00:00",
		"23:59:00",
		"The late shift. A window running past midnight is two rows — this one, and"
		" an early-hours one — because a single row spanning midnight would belong"
		" to two days at once.",
	),
)

# key, label, description
METHODOLOGIES = (
	("household_survey", "Household Survey", "Going door to door with a structured form."),
	(
		"focus_group_discussion",
		"Focus Group Discussion",
		"A facilitated conversation with a small group drawn from the community.",
	),
	(
		"key_informant_interview",
		"Key Informant Interview",
		"A one-to-one conversation with somebody who holds a particular view of the situation.",
	),
	(
		"community_mobilisation",
		"Community Mobilisation",
		"Public meetings, announcements and door-to-door work to bring people out.",
	),
	(
		"direct_service",
		"Direct Service",
		"Delivering the assistance itself: clinics, distributions, transport.",
	),
	("observation", "Observation", "Being present and recording what is seen, without intervening."),
	("training", "Training", "Teaching a skill to volunteers or to the community."),
)


def execute():
	install_windows()
	install_methodologies()


def install_windows() -> None:
	"""The day-spans a weekly availability grid is built from."""
	for key, label, opens, closes, description in SCHEDULABLE_WINDOWS:
		if frappe.db.exists(SLOT_DOCTYPE, key):
			continue

		frappe.get_doc(
			{
				"doctype": SLOT_DOCTYPE,
				"slot_key": key,
				"slot_name": label,
				"is_active": 1,
				"start_time": opens,
				"end_time": closes,
				"description": description,
			}
		).insert(ignore_permissions=True)


def install_methodologies() -> None:
	"""The register a mission's approach is written from."""
	if not frappe.db.table_exists(METHODOLOGY_DOCTYPE):
		return

	for key, label, description in METHODOLOGIES:
		if frappe.db.exists(METHODOLOGY_DOCTYPE, key):
			continue

		frappe.get_doc(
			{
				"doctype": METHODOLOGY_DOCTYPE,
				"methodology_key": key,
				"methodology_name": label,
				"is_active": 1,
				"description": description,
			}
		).insert(ignore_permissions=True)
