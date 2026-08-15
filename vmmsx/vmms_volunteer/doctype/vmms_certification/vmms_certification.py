# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Certification — a held qualification, and the date it runs out.

The controller writes one field and enforces two rules.

**`expiry_date` is computed, never typed.** It is the completion date plus the
type's configured validity period, recomputed on every save so that a society
correcting a validity period brings the certifications already held with it. No
duration appears in this file; it is read from `VMMS Certification Type`.

**Lapse is not here, and that is the design.** There is no `lapsed` field on
this doctype, nothing sets one, and no scheduled job flips one. Whether a
certification has lapsed is derived at the point it matters by
`volunteer/services/certification.py::is_lapsed()`, from `expiry_date` and the
date being asked about. See that module for why a stored flag was rejected.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

from vmmsx.volunteer.services import certification


class VMMSCertification(Document):
	def validate(self):
		self.validate_completion_date()
		self.validate_one_per_type()

		# Written here rather than by whoever is saving: the field is read-only,
		# and its value is a function of configuration.
		certification.apply_expiry(self)

	def validate_completion_date(self):
		"""Training cannot have been completed in the future."""
		if not self.completion_date:
			frappe.throw(
				_("A certification records the date the training was completed."),
				frappe.MandatoryError,
				title=_("No Completion Date"),
			)

		if getdate(self.completion_date) <= getdate(today()):
			return

		frappe.throw(
			_("This certification was completed on {0}, which has not happened yet.").format(
				frappe.bold(frappe.format(self.completion_date, {"fieldtype": "Date"}))
			),
			frappe.ValidationError,
			title=_("Completion Date In The Future"),
		)

	def validate_one_per_type(self):
		"""One row per volunteer per type — a renewal updates, it does not accrue.

		Two rows of the same type on one volunteer would make "has this person's
		first aid lapsed" a question with two answers, and every caller would
		have to invent a rule for choosing between them. The renewal path is
		`certification.record()`, which moves the dates on the row that is
		already there.
		"""
		duplicate = frappe.db.exists(
			self.doctype,
			{
				"volunteer": self.volunteer,
				"certification_type": self.certification_type,
				"name": ("!=", self.name),
			},
		)

		if not duplicate:
			return

		frappe.throw(
			_(
				"This volunteer already holds {0} on {1}. A renewal updates the certification they"
				" hold rather than adding a second, so that there is never a question of which one"
				" is current."
			).format(frappe.bold(self.certification_type), frappe.bold(duplicate)),
			frappe.DuplicateEntryError,
			title=_("Already Held"),
		)
