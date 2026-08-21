# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One day-and-window pair on a volunteer's weekly availability.

A child row with no rules of its own. "Saturday" plus the society's own
"Afternoons" slot is one row, and a schedule is a handful of them. The hours
live on the slot rather than here, so a society that shifts what it means by
"Afternoons" shifts it once rather than across every volunteer who chose it.

The duplicate rule — the same day and slot twice — lives on the parent, in
`VMMS Availability Schedule.validate_pattern`, because Frappe does not call a
child controller's `validate` and a rule written here would look like it worked
and quietly never run.
"""

from frappe.model.document import Document


class VMMSAvailabilityDay(Document):
	pass
