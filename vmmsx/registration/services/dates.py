# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""An end date is never earlier than its start date, on any registration row.

Runs on every save of a Red Profile (`hooks.doc_events`), so the portal, the
console and the desk are all held to it. A row whose end is open (does not
expire, still ongoing, still there) is not checked against a date it does not
have.
"""

import frappe
from frappe import _
from frappe.utils import cint, getdate

# Red Profile table: (heading, start field, start label, end field, end label, open-ended flag, years)
PAIRS = (
	("vmms_education", "Education", "started_in", "Started", "finished_in", "Finished", "is_ongoing", True),
	(
		"vmms_training",
		"Training and courses",
		"started_on",
		"Started",
		"completed_on",
		"Completed",
		None,
		False,
	),
	(
		"vmms_certifications",
		"Certifications",
		"issue_date",
		"Issued",
		"expiration_date",
		"Expires",
		None,
		False,
	),
	("vmms_work_experience", "Experience", "started_on", "From", "ended_on", "To", "is_current", False),
	(
		"vmms_licences",
		"Licences",
		"valid_from",
		"Valid from",
		"valid_to",
		"Valid until",
		"does_not_expire",
		False,
	),
)


def validate_profile(doc, method=None) -> None:
	"""Refuse the save when any row ends before it starts."""
	for table, heading, start, start_label, end, end_label, open_flag, years in PAIRS:
		if not doc.meta.has_field(table):
			continue
		for index, row in enumerate(doc.get(table) or [], start=1):
			if open_flag and row.get(open_flag):
				continue
			if table == "vmms_certifications" and row.meta.has_field("expire") and not row.get("expire"):
				continue
			if ends_before(row.get(start), row.get(end), years):
				frappe.throw(
					_("{0}, row {1}: {2} cannot be before {3}.").format(
						_(heading), index, _(end_label), _(start_label)
					),
					frappe.ValidationError,
					title=_("Check the dates"),
				)


def ends_before(start, end, years: bool = False) -> bool:
	if not start or not end:
		return False
	if years:
		return cint(end) < cint(start)
	return getdate(end) < getdate(start)
