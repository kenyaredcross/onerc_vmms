# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Approval applies where there is an approval cycle to apply, and not before.

A society sets `routed` on a terms of reference. Whether there is anybody to
route *to* is a separate answer and lives on `VMMS Approval Workflow`. Before,
the two were conflated: a routed terms of reference on a site with no workflow
for deployment requests threw "no approval workflow is configured" at whoever
raised the request — a piece of configuration nobody had done blocking work
nobody had been told to stop.

Now the two questions are asked separately, and the answer narrows in one
direction only:

* **workflow configured** → routed, exactly as before. Nothing about the engine,
  the person-gate or the audit trail changes, and this suite asserts that first
  because a "narrowing" that quietly disabled approvals would be the worst
  possible outcome.
* **no workflow** → handled directly, and the record says so. `approval_
  unconfigured` is on the DTO precisely so that "nobody approved this" is
  visible rather than inferred from the absence of a decision.

`direct` is never turned into `routed` by any of this.
"""

import frappe

from vmmsx.approvals import states
from vmmsx.deployment.services import approval
from vmmsx.deployment.services import request as request_service
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestWithNoWorkflowTheWorkGetsDone(DeploymentTestCase):
	"""The shipped state of a site that has asked for approvals and set none up."""

	def test_the_doctype_is_not_governed(self):
		self.assertFalse(approval.has_workflow(fixtures.REQUEST_DOCTYPE))

	def test_a_routed_request_is_handled_directly(self):
		terms = fixtures.make_terms_requiring(approval_mode="routed")
		request = fixtures.make_request(terms.name, self.society_a["branch"])

		self.assertEqual(
			approval.effective_mode(request, "routed", "these terms"), approval.MODE_DIRECT
		)

	def test_and_becomes_a_deployment_rather_than_an_error(self):
		"""The failure this change exists to remove: unfinished configuration
		stopping a branch from deploying anybody."""
		terms = fixtures.make_terms_requiring(approval_mode="routed")
		request = fixtures.make_request(terms.name, self.society_a["branch"])

		result = request_service.submit(request)

		self.assertTrue(result["is_fulfilled"])

	def test_the_record_says_nobody_approved_it(self):
		terms = fixtures.make_terms_requiring(approval_mode="routed")
		request = fixtures.make_request(terms.name, self.society_a["branch"])
		request_service.submit(request)

		answer = request_service.status(request)

		self.assertTrue(answer["requires_approver"])
		self.assertTrue(answer["approval_unconfigured"])
		self.assertEqual(answer["effective_approval_mode"], approval.MODE_DIRECT)

	def test_and_it_is_left_at_draft_rather_than_marked_approved(self):
		"""The absence of an approval is not an approval, and writing `Approved`
		onto a record nobody approved would be a lie in an audit trail. Draft is
		where a record nobody has decided sits, and it stays there."""
		terms = fixtures.make_terms_requiring(approval_mode="routed")
		request = fixtures.make_request(terms.name, self.society_a["branch"])
		request_service.submit(request)

		self.assertEqual(
			frappe.db.get_value(fixtures.REQUEST_DOCTYPE, request.name, "approval_state"),
			states.DRAFT,
		)

	def test_a_direct_terms_of_reference_is_unaffected(self):
		terms = fixtures.make_terms_requiring(approval_mode="direct")
		request = fixtures.make_request(terms.name, self.society_a["branch"])

		self.assertEqual(
			approval.effective_mode(request, "direct", "these terms"), approval.MODE_DIRECT
		)
		self.assertFalse(approval.downgraded(request, "direct", "these terms"))


class TestWithAWorkflowNothingChanges(DeploymentTestCase):
	"""The half that matters most: a configured society still gets its approvals."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.grant_doctype_access(fixtures.REQUEST_DOCTYPE, fixtures.REQUEST_APPROVER_ROLE)
		fixtures.make_workflow(fixtures.REQUEST_DOCTYPE, fixtures.REQUEST_APPROVER_ROLE)

		cls.approver = fixtures.make_user("configured_approver")
		fixtures.grant_scope(cls.approver, fixtures.REQUEST_APPROVER_ROLE, cls.society_a["branch"])
		fixtures.grant_scope(cls.approver, fixtures.REQUEST_SCOPE_ROLE, cls.society_a["region"])
		frappe.get_doc("User", cls.approver).add_roles(fixtures.REQUEST_APPROVER_ROLE)

	def test_the_doctype_is_governed(self):
		self.assertTrue(approval.has_workflow(fixtures.REQUEST_DOCTYPE))

	def test_a_routed_request_stays_routed(self):
		terms = fixtures.make_terms_requiring(approval_mode="routed")
		request = fixtures.make_request(terms.name, self.society_a["branch"])

		self.assertEqual(
			approval.effective_mode(request, "routed", "these terms"), approval.MODE_ROUTED
		)
		self.assertFalse(approval.downgraded(request, "routed", "these terms"))

	def test_it_enters_review_and_is_not_fulfilled(self):
		terms = fixtures.make_terms_requiring(approval_mode="routed")
		request = fixtures.make_request(terms.name, self.society_a["post"])
		request_service.submit(request)

		self.assertEqual(
			frappe.db.get_value(fixtures.REQUEST_DOCTYPE, request.name, "approval_state"),
			states.IN_REVIEW,
		)
		self.assertIsNone(request.deployment)

	def test_the_dto_does_not_claim_it_is_unconfigured(self):
		terms = fixtures.make_terms_requiring(approval_mode="routed")
		request = fixtures.make_request(terms.name, self.society_a["post"])
		request_service.submit(request)

		self.assertFalse(request_service.status(request)["approval_unconfigured"])
