# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Stipend Payment Form — the money half of a period already described.

The controller enforces what must be true of the record itself and hands the
pairing, the grid and the totals to `stipend/services/payment.py`.

**ACC-02 is checked here, at creation.** The anchor is held on this record rather
than read through the progress report, because core's geo scoping filters each
doctype on a field of its own; it is then checked against the report's anchor, so
holding it twice cannot mean holding two different answers.

**The period, the roster and the total are all derived on every save.** A form
whose report has since been corrected is brought back into line rather than left
paying for days the report no longer covers.

**Approval is a stub**, exactly as it is on the progress report. See
`stipend/services/approval.py`.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from vmmsx.stipend.services import approval, payment, society

GEO_NODE_FIELD = "geo_node"


class VMMSStipendPaymentForm(Document):
	def validate(self):
		self.validate_anchor()
		self.validate_approval_state()
		payment.sync(self)

	def validate_anchor(self):
		"""ACC-02, then the society's level (ACC-03)."""
		if not self.get(GEO_NODE_FIELD):
			frappe.throw(
				_(
					"A stipend payment form must be anchored to a Geo Node before it can exist. An"
					" unplaced form cannot be seen by geo scoping, so it would exist with nobody able"
					" to see or act on it."
				),
				frappe.MandatoryError,
				title=_("Missing Geo Anchor"),
			)

		society.assert_anchor_level(self.get(GEO_NODE_FIELD))

	def validate_approval_state(self):
		"""The state is moved by the service, never set on the document."""
		approval.assert_stored_transition(self)
		approval.assert_unchanged_while_pending(self, payment.signature, _("what it pays"))
