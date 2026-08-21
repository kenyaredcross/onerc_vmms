# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Deployment Assignment — one person's deployment.

The record of being placed on a deployment or asked to join one, and of what
they said. `deployment/services/assignment.py` owns the lifecycle and states the
case for this being a document rather than a row on the deployment's own roster;
this file holds the rules that must be true of any one assignment however it was
written, including by somebody editing it on the desk.

**The grammar is enforced here as well as in the service**, and that is not
belt-and-braces. The service is the door every screen goes through; the desk is
a second door, and a status moved by hand from Declined back to Accepted would
be a volunteer's answer overwritten with no record that it ever said otherwise.
Both doors lead to the same table in `assignment.TRANSITIONS`.

**The terms are copied, not followed.** `terms_of_reference` is written when the
assignment is raised and read-only afterwards, because accepting an assignment
is accepting that document. There is no separate contract in this app — the
terms of reference *is* the contract — which is why it is submittable and why
this record names the exact one.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from vmmsx.deployment.services import assignment


class VMMSDeploymentAssignment(Document):
	def validate(self):
		self.validate_transition()
		self.validate_dates()
		self.validate_terms()
		self.validate_single_leader()

	def validate_transition(self):
		"""Refuse a status move the grammar does not admit.

		Only on an edit: a new assignment has no previous status to have moved
		from, and `assignment.create` has already refused the two statuses an
		assignment may not be raised in.
		"""
		if self.is_new():
			assignment.assert_status(self.status)
			return

		previous = self.get_doc_before_save()

		if not previous or previous.status == self.status:
			return

		assignment.assert_transition(previous.status, self.status)

	def validate_dates(self):
		"""An assignment cannot end before it begins."""
		assignment.assert_dates(self)

	def validate_terms(self):
		"""Terms that no longer take new work cannot take a new assignment either."""
		assignment.assert_terms_offered(self)

	def validate_single_leader(self):
		"""One deployment, at most one leader.

		Checked across the deployment rather than on this row, because "is there
		already a leader" is not a question a single row can answer. Only
		assignments that are actually on the deployment count: somebody named
		leader who then declined is not leading anything, and letting them block
		the appointment of a real leader would be the wrong answer twice over.
		"""
		if self.role != "leader" or self.status not in assignment.ON_DEPLOYMENT:
			return

		other = frappe.db.get_value(
			self.doctype,
			{
				"deployment": self.deployment,
				"role": "leader",
				"status": ("in", assignment.ON_DEPLOYMENT),
				"name": ("!=", self.name),
			},
			"volunteer",
		)

		if not other:
			return

		frappe.throw(
			_(
				"{0} is already leading this deployment. A deployment has one leader, so that"
				" updates and reports have one person to be addressed to. Return them to the"
				" ranks first if the lead is changing."
			).format(frappe.bold(assignment.volunteer_label(other))),
			frappe.ValidationError,
			title=_("Deployment Already Has A Leader"),
		)

	def after_insert(self):
		"""Tell the volunteer, on the record that is about them.

		**One notification per assignment, addressed to the assignment.** This is
		the thing a child row could not do: a notification about one person's
		deployment had to point at the whole deployment, so the link took them to
		a roster rather than to the question they were being asked.

		Only a question is announced. An `Assigned` row is a coordinator recording
		that somebody is going, often after arranging it by phone, and a
		notification saying "you have been asked" would be describing a
		conversation that already happened differently.
		"""
		if self.status != assignment.STATUS_PENDING:
			return

		from vmmsx.notifications.services import direct

		login = direct.login_of(self.volunteer)

		if not login:
			return

		direct.tell(
			[login],
			_("You have been asked to join a deployment starting {0}").format(
				frappe.format_value(self.start_date, {"fieldtype": "Date"})
			),
			self.doctype,
			self.name,
		)
