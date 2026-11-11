"""Give every volunteer the emergency contacts their approved application named.

`VMMS Volunteer.emergency_contacts` is new. Acceptance fills it from now on
(`capabilities.seed`); this fills it for the volunteers accepted before it
existed, from their most recent approved application, and only where the
volunteer has none yet. A volunteer with no approved application — every record
migrated from the old system — is left empty and asked for one on their profile.
"""

import frappe

from vmmsx.volunteer.services.capabilities import EMERGENCY_CONTACT_FIELDS


def execute():
	if not frappe.get_meta("VMMS Volunteer").has_field("emergency_contacts"):
		return

	applications = frappe.get_all(
		"VMMS Volunteer Application",
		filters={"approval_state": "Approved", "volunteer": ("is", "set")},
		fields=["name", "volunteer"],
		order_by="modified desc",
	)

	done = set()

	for application in applications:
		if application.volunteer in done:
			continue

		done.add(application.volunteer)

		if frappe.db.exists(
			"VMMS Emergency Contact",
			{"parent": application.volunteer, "parenttype": "VMMS Volunteer"},
		):
			continue

		rows = frappe.get_all(
			"VMMS Emergency Contact",
			filters={"parent": application.name, "parenttype": "VMMS Volunteer Application"},
			fields=list(EMERGENCY_CONTACT_FIELDS),
			order_by="idx asc",
		)

		if not rows:
			continue

		volunteer = frappe.get_doc("VMMS Volunteer", application.volunteer)
		volunteer.set("emergency_contacts", [dict(row) for row in rows])
		volunteer.flags.ignore_permissions = True
		volunteer.save()
