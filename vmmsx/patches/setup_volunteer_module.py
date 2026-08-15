# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install what the Volunteer module needs before a society can configure it.

Four things, all idempotent, all *seeds a society then edits* rather than
constants the code depends on:

1. **The ACC-03 anchor-level field** on core's National Society Settings, as a
   Custom Field. vmmsx owns the field and installs it; core's source is not
   touched, because a product pushing its own fields into the shared
   foundation's schema is how the foundation stops being shared. Left empty,
   which means "anchor anywhere" until a society narrows it.
2. **The HR provisioning switch and its company**, also Custom Fields. The
   switch ships **off**: a society running volunteering without HR involvement
   is the ordinary case, and creating Employee records for it uninvited would
   put volunteers into a payroll-shaped system nobody asked for.
3. **A starting set of time-log categories.** A vocabulary, not a closed one: a
   society may add to it, rename it or empty it, and no source file branches on
   a category value.
4. **The `volunteer` Affiliation Type**, so this app's second satellite has
   somewhere to report on core's index — alongside `member`, not instead of it.

What is deliberately **not** here: any certification type, any course mapping.
Those name real qualifications and real courses, and this app has no business
inventing either. A society writes its own, which is the whole reason they are
doctypes.

Every step checks before it writes, so re-running the patch — which migrate will
do on a site that already has all four — changes nothing and overwrites nothing
an administrator has since edited.
"""

import frappe

from vmmsx.volunteer.services.society import (
	ANCHOR_LEVEL_FIELD,
	EMPLOYEE_COMPANY_FIELD,
	PROVISION_EMPLOYEE_FIELD,
)
from vmmsx.volunteer.services.volunteer import VOLUNTEER_AFFILIATION_KEY

SETTINGS_DOCTYPE = "National Society Settings"

# The field the Member stage installed. Ours are inserted after it so the
# volunteer settings sit together and below membership's, rather than being
# scattered through the form in the order the patches happened to run.
MEMBER_SCOPE_ROLE_FIELD = "vmms_membership_scope_role"

# A starting vocabulary. Seeded, then owned by the society.
TIME_LOG_CATEGORIES = (
	("training", "Training", "Time spent being trained, or training others."),
	("community_event", "Community Event", "A public activity: an open day, a drive, a campaign."),
	(
		"operations_support",
		"Operations Support",
		"Support to the society's running: office, logistics, admin.",
	),
)


def execute():
	install_anchor_level_field()
	install_hr_provisioning_fields()
	install_time_log_categories()
	install_volunteer_affiliation_type()


def install_anchor_level_field() -> None:
	"""ACC-03 — where a society says its volunteers may be anchored."""
	_custom_field(
		{
			"fieldname": ANCHOR_LEVEL_FIELD,
			"label": "Volunteer Anchor Level",
			"fieldtype": "Link",
			"options": "Geo Level",
			"insert_after": MEMBER_SCOPE_ROLE_FIELD,
			"description": (
				"ACC-03. The geo level a VMMS Volunteer must be anchored at. Left empty, a"
				" volunteer may be anchored at any level; this narrows it, it does not enable"
				" it. Owned by vmmsx."
			),
		}
	)


def install_hr_provisioning_fields() -> None:
	"""Whether accepting a volunteer creates an HR record, and under which company.

	Both ship empty or off. A society that wants HR records switches the first on
	and names the second; a society that does not gets no Employee records at
	all, which is the shipped behaviour and the one most societies want.
	"""
	_custom_field(
		{
			"fieldname": PROVISION_EMPLOYEE_FIELD,
			"label": "Provision an HR Employee for a Volunteer",
			"fieldtype": "Check",
			"default": "0",
			"insert_after": ANCHOR_LEVEL_FIELD,
			"description": (
				"Off by default. When on, accepting a volunteer application links the volunteer to"
				" the Frappe HR Employee record for that person, adopting an existing one where"
				" there is one and creating one otherwise. Identity never moves: Red Profile stays"
				" the spine, and vmmsx will not invent a date of birth or a gender to satisfy HR's"
				" schema. Where HR refuses for want of data this app does not hold, the refusal is"
				" logged and the volunteer is unaffected. Owned by vmmsx."
			),
		}
	)
	_custom_field(
		{
			"fieldname": EMPLOYEE_COMPANY_FIELD,
			"label": "Volunteer Employee Company",
			"fieldtype": "Link",
			"options": "Company",
			"depends_on": f"eval:doc.{PROVISION_EMPLOYEE_FIELD}",
			"insert_after": PROVISION_EMPLOYEE_FIELD,
			"description": (
				"Which company a provisioned Employee is created under. HR cannot create one"
				" without it, and vmmsx has no business guessing it. Left empty with provisioning"
				" on, nothing is created and the reason is logged. Owned by vmmsx."
			),
		}
	)


def install_time_log_categories() -> None:
	"""How a society classifies volunteered time. An open set; nothing branches on it."""
	for key, name, description in TIME_LOG_CATEGORIES:
		if frappe.db.exists("VMMS Time Log Category", key):
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


def install_volunteer_affiliation_type() -> None:
	"""The vocabulary entry this app's second satellite reports under."""
	if frappe.db.exists("Affiliation Type", VOLUNTEER_AFFILIATION_KEY):
		return

	frappe.get_doc(
		{
			"doctype": "Affiliation Type",
			"affiliation_type_key": VOLUNTEER_AFFILIATION_KEY,
			"affiliation_type_name": "Volunteer",
			"description": (
				"A volunteer of the national society. Owned by vmmsx's VMMS Volunteer satellite,"
				" which is the truth of it. This row is a derived summary."
			),
			"is_active": 1,
		}
	).insert(ignore_permissions=True)


def _custom_field(definition: dict) -> None:
	"""Install one Custom Field on core's settings, once."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": definition["fieldname"]}):
		return

	create_custom_field(SETTINGS_DOCTYPE, definition, ignore_validate=True)
