# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The unit on a mission's resource line becomes a real UOM.

`VMMS TOR Resource.unit` was free text, so one branch wrote "unit", another
"units" and a third "pcs", and nothing could ever add two lines together or
compare a planned quantity against a purchased one. It is now a Link to
ERPNext's own `UOM` — which is the register a purchase, a stock entry and a
delivery note all already count in.

Changing the fieldtype leaves the column and its values exactly as they were, so
without this patch every existing row would render as a broken link and refuse
the next save. What it does is match each distinct value onto a UOM the site
already has, case-insensitively, and create one where a society's own word for
something has no match.

**Creating a UOM is the right answer here and it is worth saying why.** The
alternative is to blank the value, and that throws away the only record of how
many of something a mission asked for. A society that wrote "kit" meant a unit
of measure; ERPNext's list simply does not happen to ship that one, and adding
it is the same act an administrator would perform by hand on the first purchase
order. Nothing is renamed and nothing existing is touched.
"""

import frappe

RESOURCE_DOCTYPE = "VMMS TOR Resource"


def execute():
	if not frappe.db.table_exists(RESOURCE_DOCTYPE):
		return

	written = frappe.db.sql_list(
		f"SELECT DISTINCT `unit` FROM `tab{RESOURCE_DOCTYPE}` WHERE IFNULL(`unit`, '') != ''"
	)

	if not written:
		return

	# Matched case-insensitively against what the site already has, so a row
	# saying "unit" finds ERPNext's "Unit" rather than creating a second one that
	# differs only in a capital letter.
	known = {name.lower(): name for name in frappe.get_all("UOM", pluck="name")}

	for value in written:
		resolved = known.get(value.strip().lower())

		if not resolved:
			resolved = frappe.get_doc(
				{"doctype": "UOM", "uom_name": value.strip(), "enabled": 1}
			).insert(ignore_permissions=True).name
			known[value.strip().lower()] = resolved

		if resolved == value:
			continue

		frappe.db.sql(
			f"UPDATE `tab{RESOURCE_DOCTYPE}` SET `unit` = %(resolved)s WHERE `unit` = %(value)s",
			{"resolved": resolved, "value": value},
		)
