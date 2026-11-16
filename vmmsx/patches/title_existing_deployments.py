# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Every deployment has a title now; give the ones written before that one.

The title is its terms of reference and the month it starts — "Nairobi Terms –
November 2026" — numbered where two open deployments would otherwise share it,
which is the same rule `deployment.default_title` applies to a deployment a
routed request becomes. Written straight to the column, oldest first so the
numbering is stable, and only where the title is empty: a title somebody has
since typed is theirs.
"""

import frappe


def execute():
	from vmmsx.deployment.services import deployment as deployment_service

	for name in frappe.get_all(
		"VMMS Deployment",
		filters={"title": ("is", "not set")},
		order_by="creation asc",
		pluck="name",
	):
		doc = frappe.get_doc("VMMS Deployment", name)
		frappe.db.set_value(
			"VMMS Deployment", name, "title", deployment_service.default_title(doc), update_modified=False
		)
