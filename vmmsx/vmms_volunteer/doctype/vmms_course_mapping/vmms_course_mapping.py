# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Course Mapping — the learning seam's whole configuration.

One row per course a society treats as a qualification: complete that course,
hold that certification. The row is the mapping; there is no dictionary in a
source file, and no course or certification name appears in any of this app's
code. Pointing an existing row at a different `VMMS Certification Type` changes
what every future completion awards, with no code change anywhere.

`external_course` is the learning system's identifier and is deliberately Data
rather than a Link — see the field's own description. The controller does the
one thing a Data field cannot do for itself: it refuses a value that is only
whitespace, which would otherwise become a mapping that silently matches
nothing.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class VMMSCourseMapping(Document):
	def validate(self):
		self.normalise_course()

	def normalise_course(self):
		"""Trim the identifier, and refuse an empty one.

		A stray space either side of a course identifier is the difference
		between a mapping that fires and one that never does, and the failure is
		invisible: the seam simply finds nothing and awards nothing.
		"""
		self.external_course = (self.external_course or "").strip()

		if self.external_course:
			return

		frappe.throw(
			_(
				"A course mapping needs the learning system's identifier for the course. Without"
				" one it matches no completion and awards nothing, silently."
			),
			frappe.MandatoryError,
			title=_("No Course Identifier"),
		)
