# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Stipend Progress Report — a period, a place, and the people it was about.

The controller enforces what must be true of the record itself and hands
everything else to a service, exactly as `VMMS Deployment Request` and
`VMMS Membership` do.

**ACC-02 is checked here, at creation, and not filled in later.** An unplaced
report is invisible to geo scoping — core's query filter uses `IN`, which
excludes NULL — and unroutable, so it would exist with nobody able to see or act
on it. ACC-03 follows it: which level a society files stipend paperwork at is
`vmms_stipend_anchor_level`, and no level name appears in this file.

**The department is derived on every save, never typed.** It is the routing
target the eventual departmental approval will use, recorded now and routed by
nothing. See `stipend/services/department.py`.

**Approval is a stub.** Submitting moves the report to
`Pending Departmental Approval`, where it stays: nobody can approve it, and the
refusal says why. See `stipend/services/approval.py` before wiring anything to
this doctype.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from vmmsx.stipend.services import approval, department, society
from vmmsx.stipend.services import report as report_service

GEO_NODE_FIELD = "geo_node"


class VMMSStipendProgressReport(Document):
	def validate(self):
		self.validate_anchor()
		self.validate_period()
		self.validate_volunteers()
		self.validate_approval_state()
		department.capture(self)

	def validate_anchor(self):
		"""ACC-02, then the society's level (ACC-03)."""
		if not self.get(GEO_NODE_FIELD):
			frappe.throw(
				_(
					"A stipend progress report must be anchored to a Geo Node before it can exist. An"
					" unplaced report cannot be seen by geo scoping, so it would exist with nobody"
					" able to see or act on it."
				),
				frappe.MandatoryError,
				title=_("Missing Geo Anchor"),
			)

		society.assert_anchor_level(self.get(GEO_NODE_FIELD))

	def validate_period(self):
		if not (self.period_from and self.period_to):
			frappe.throw(
				_("A progress report covers a period. Both dates are needed."),
				frappe.MandatoryError,
				title=_("Missing Period"),
			)

		if getdate(self.period_to) >= getdate(self.period_from):
			return

		frappe.throw(
			_("This report covers until {0}, before it covers from {1}.").format(
				frappe.bold(frappe.format(self.period_to, {"fieldtype": "Date"})),
				frappe.bold(frappe.format(self.period_from, {"fieldtype": "Date"})),
			),
			frappe.ValidationError,
			title=_("Period Runs Backwards"),
		)

	def validate_volunteers(self):
		"""One volunteer, one row. A report covering many people is the point.

		A draft may cover nobody; `report.submit()` is where the report is required
		to be about somebody, because that is when it stops being a working
		document.
		"""
		seen = set()

		for row in self.get(report_service.VOLUNTEERS_FIELD) or []:
			if row.volunteer in seen:
				frappe.throw(
					_("{0} is on this report twice. One row per volunteer.").format(
						frappe.bold(row.volunteer)
					),
					frappe.ValidationError,
					title=_("Volunteer Listed Twice"),
				)

			seen.add(row.volunteer)

	def validate_approval_state(self):
		"""The state is moved by the service, never set on the document.

		The field is read-only on the form, so this is not about the desk: it is
		about a script assigning `approval_state` and saving, which would otherwise
		walk straight past `submit()` and `withdraw()` and the grammar they hold.
		"""
		approval.assert_stored_transition(self)
		approval.assert_unchanged_while_pending(self, report_service.signature, _("who this report covers"))
