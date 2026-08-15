# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Project — the programme of work a terms of reference is written under.

A society does not deploy volunteers to "a deployment". It runs a programme —
a flood response, a vaccination campaign, a season of branch first aid duty —
writes one or more terms of reference under it, and deploys people against
those. This doctype is that outer container, and it is deliberately thin: it
holds what the programme *is* and where it sits, and nothing about who serves.

**It decides nothing.** No code branches on a project, no candidate search reads
one, and a deployment reaches its project through its terms rather than storing
a second copy of the answer. What the record buys is the thing a coordinator
actually needs on the day: the terms of reference for one piece of work grouped
under the programme that commissioned them, printable together on the society's
own paper.

The two rules here are both about the record being coherent rather than about
any particular society's practice. Everything else about a project is the
society's to write.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from vmmsx.deployment.services import project


class VMMSProject(Document):
	def validate(self):
		self.validate_period()
		self.validate_status()

	def validate_period(self):
		"""A project may not end before it began.

		Both dates are optional, because a society planning a programme often has
		a start before it has an end. The rule applies only once both are set.
		"""
		if not (self.start_date and self.end_date):
			return

		if getdate(self.end_date) >= getdate(self.start_date):
			return

		frappe.throw(
			_("This project ends on {0}, before it starts on {1}.").format(
				frappe.bold(frappe.utils.format_date(self.end_date)),
				frappe.bold(frappe.utils.format_date(self.start_date)),
			),
			frappe.ValidationError,
			title=_("End Before Start"),
		)

	def validate_status(self):
		"""Refuse a status outside the closed set, and a move outside the grammar.

		Checked on the form as well as in the service so that a society editing a
		project on the desk is told here, rather than on the first deployment
		somebody tries to run under it.
		"""
		project.assert_status(self.status)

		before = self.get_doc_before_save() if not self.is_new() else None

		if before and before.status != self.status:
			project.assert_transition(before.status, self.status)
