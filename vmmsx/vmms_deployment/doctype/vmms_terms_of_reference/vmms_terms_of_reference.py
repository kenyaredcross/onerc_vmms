# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Terms of Reference — the specification a deployment is run against.

Configuration, not an operational record: a society writes one per kind of work
it deploys volunteers to do, and every deployment and every request points at
one. That is why it is keyed by a stable business key rather than an opaque
series, the same rule `VMMS Certification Type` and `VMMS Time Log Category`
follow.

Three things on it are read by code, and each is a society's answer rather than
this app's:

    geo_scope               where these terms may be used. Empty means anywhere.
    approval_mode           whether a request under them needs an approver.
    required_certifications what a candidate must, or would ideally, hold.

Nothing else here is read by anything. The purpose and the responsibilities are
for the people involved.

The controller holds two rules, both about the terms being coherent rather than
about any particular society's practice.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from vmmsx.deployment.services import terms


class VMMSTermsofReference(Document):
	def validate(self):
		self.validate_requirements()
		self.validate_approval_mode()

	def validate_requirements(self):
		"""One row per certification type. Two would be two answers to one question.

		A terms of reference listing the same certification twice, once mandatory
		and once not, has no single answer to "is this required", and every reader
		would have to invent a tie-break. Refusing it here means no reader has to.
		"""
		seen = set()

		for row in self.required_certifications or []:
			if row.certification_type in seen:
				frappe.throw(
					_("{0} is listed twice in the requirements. List each certification once.").format(
						frappe.bold(row.certification_type)
					),
					frappe.DuplicateEntryError,
					title=_("Requirement Listed Twice"),
				)

			seen.add(row.certification_type)

	def validate_approval_mode(self):
		"""Refuse a mode nobody wrote a rule for, before anything depends on it.

		Checked here as well as at the point of use so that a society choosing a
		mode is told on the form, rather than on the first request raised under
		these terms.
		"""
		terms.assert_approval_mode(self)
