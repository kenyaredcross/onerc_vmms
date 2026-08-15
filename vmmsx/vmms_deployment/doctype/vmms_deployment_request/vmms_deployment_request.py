# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Deployment Request — volunteers asked for, and the approval that may gate it.

The controller enforces the anchor rules and then hands the lifecycle to a
service, exactly as `VMMS Membership` does.

**Fulfilment is a predicate, not a sequence.** `request.try_fulfil()` asks two
questions: is this request's approval requirement settled, and has it become a
deployment already? Both are answered from the record and from configuration,
never from which code path happened to run, so it is safe to call after any
event and in any order. It runs from `on_update`, which is how a decision
recorded by the approval engine becomes a deployment without the engine knowing
that deployments exist. That is the same shape membership activation and
volunteer acceptance already have.

**Whether an approver is needed at all is the terms of reference's answer**, in
its `approval_mode`. No source file compares that value to a name; the two
tables in `deployment/services/approval.py` are keyed by it.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate

from vmmsx.deployment.services import request as request_service
from vmmsx.deployment.services import society, terms

GEO_NODE_FIELD = "geo_node"


class VMMSDeploymentRequest(Document):
	def validate(self):
		self.validate_anchor()
		self.validate_period()
		self.validate_headcount()

	def validate_anchor(self):
		"""ACC-02, then the society's level, then the terms' own scope.

		ACC-03 is asked of the society's setting here rather than of the approval
		workflow, because a request in `direct` mode never reaches the engine and
		would otherwise have no level rule at all. Where a workflow governs this
		doctype the engine checks its `allowed_anchor_levels` as well, at
		submission; the two narrow, they do not contradict.
		"""
		if not self.get(GEO_NODE_FIELD):
			frappe.throw(
				_(
					"A deployment request must be anchored to a Geo Node before it can exist. An"
					" unplaced request cannot be seen by geo scoping or routed to an approver, so it"
					" would exist with nobody able to act on it."
				),
				frappe.MandatoryError,
				title=_("Missing Geo Anchor"),
			)

		society.assert_deployment_anchor_level(self.get(GEO_NODE_FIELD))
		terms.assert_within_scope(self.terms_of_reference, self.get(GEO_NODE_FIELD))

	def validate_period(self):
		if not (self.needed_from and self.needed_until):
			frappe.throw(
				_("A deployment request names the days the volunteers are needed. Both are needed."),
				frappe.MandatoryError,
				title=_("Missing Period"),
			)

		if getdate(self.needed_until) >= getdate(self.needed_from):
			return

		frappe.throw(
			_("This request needs volunteers until {0}, before it needs them from {1}.").format(
				frappe.bold(frappe.format(self.needed_until, {"fieldtype": "Date"})),
				frappe.bold(frappe.format(self.needed_from, {"fieldtype": "Date"})),
			),
			frappe.ValidationError,
			title=_("Period Runs Backwards"),
		)

	def validate_headcount(self):
		if cint(self.volunteers_requested) > 0:
			return

		frappe.throw(
			_("A deployment request asks for at least one volunteer. This one asks for {0}.").format(
				frappe.bold(cint(self.volunteers_requested))
			),
			frappe.ValidationError,
			title=_("Nobody Requested"),
		)

	def on_update(self):
		"""Re-evaluate fulfilment after every save. Idempotent, and silent when nothing changed."""
		request_service.try_fulfil(self)
