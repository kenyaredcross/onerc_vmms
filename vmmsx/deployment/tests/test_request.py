# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Deployment requests: two modes, one dispatch, and no shadow approval.

The base case is `direct`: a society that does not gate its deployments gets a
request that becomes a deployment when it is submitted, with no approver, no
workflow to configure, and no approval state pretending to be one. That is the
shipped default on a terms of reference, and the first suite below is about it.

The other case is `routed`, and the whole point is that it goes through **the
real engine, exactly as built**. There is no second approval path in this
module: no resolver, no role check, no "if the user holds the role" shortcut.
The tests that matter here are the ones that show the engine's person-gate doing
the refusing — a user who holds the approver role, at the wrong place, with
every permission needed to see the record, is still refused, because holding the
role is not being the person this document routed to.

`test_delegation.py` asserts the same thing against the source. This suite
asserts it against behaviour, and the two catch different mistakes: a module can
be free of `resolve_approvers` and still have grown a `if role in
frappe.get_roles(user)` somewhere.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.approvals import states
from vmmsx.approvals.services import engine
from vmmsx.deployment.services import request as request_service
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class RequestTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.grant_doctype_access(fixtures.REQUEST_DOCTYPE, fixtures.REQUEST_APPROVER_ROLE)

		# The person the branch's requests route to: they hold the approver role
		# at the branch, and the request scope role wide enough to open one.
		cls.approver = fixtures.make_user("branch_approver")
		fixtures.grant_scope(cls.approver, fixtures.REQUEST_APPROVER_ROLE, cls.society_a["branch"])
		fixtures.grant_scope(cls.approver, fixtures.REQUEST_SCOPE_ROLE, cls.society_a["region"])
		frappe.get_doc("User", cls.approver).add_roles(fixtures.REQUEST_APPROVER_ROLE)

		# Somebody holding the *same role* somewhere else, with the *same* scope.
		# Everything about them is right except that this document did not route
		# to them, which is the only thing the gate is testing.
		cls.other_approver = fixtures.make_user("other_approver")
		fixtures.grant_scope(
			cls.other_approver, fixtures.REQUEST_APPROVER_ROLE, cls.society_a["other_branch"]
		)
		fixtures.grant_scope(cls.other_approver, fixtures.REQUEST_SCOPE_ROLE, cls.society_a["region"])
		frappe.get_doc("User", cls.other_approver).add_roles(fixtures.REQUEST_APPROVER_ROLE)


class TestTheDirectModeIsTheBaseCase(RequestTestCase):
	def test_a_direct_request_becomes_a_deployment_on_submission(self):
		terms = fixtures.make_terms_requiring()
		request = fixtures.make_request(terms.name, self.society_a["branch"])

		result = request_service.submit(request)

		self.assertTrue(result["is_fulfilled"])
		self.assertTrue(request.deployment)
		self.assertTrue(frappe.db.exists(fixtures.DEPLOYMENT_DOCTYPE, request.deployment))

	def test_the_deployment_carries_the_requests_terms_place_and_dates(self):
		terms = fixtures.make_terms_requiring()
		request = fixtures.make_request(
			terms.name,
			self.society_a["branch"],
			needed_from=add_days(today(), 3),
			needed_until=add_days(today(), 9),
		)
		request_service.submit(request)

		deployment = frappe.get_doc(fixtures.DEPLOYMENT_DOCTYPE, request.deployment)

		self.assertEqual(deployment.terms_of_reference, terms.name)
		self.assertEqual(deployment.geo_node, self.society_a["branch"])
		self.assertEqual(str(deployment.start_date), str(request.needed_from))
		self.assertEqual(str(deployment.end_date), str(request.needed_until))

	def test_a_direct_request_never_touches_the_approval_state(self):
		"""The absence of an approval is not an approval, and is not written as one."""
		terms = fixtures.make_terms_requiring()
		request = fixtures.make_request(terms.name, self.society_a["branch"])
		request_service.submit(request)

		self.assertEqual(self.approval_state(fixtures.REQUEST_DOCTYPE, request.name), states.DRAFT)
		self.assertFalse(request.approval_stage)
		self.assertEqual(request.approval_decisions, [])

	def test_no_approval_workflow_is_needed_for_a_direct_request(self):
		"""Nothing governs VMMS Deployment Request here, and nothing needs to."""
		from vmmsx.approvals.services import config

		self.assertFalse(config.is_approvable(fixtures.REQUEST_DOCTYPE))

		terms = fixtures.make_terms_requiring()
		request = fixtures.make_request(terms.name, self.society_a["branch"])

		self.assertTrue(request_service.submit(request)["is_fulfilled"])

	def test_submitting_twice_creates_one_deployment(self):
		terms = fixtures.make_terms_requiring()
		request = fixtures.make_request(terms.name, self.society_a["branch"])

		request_service.submit(request)
		first = request.deployment

		request_service.submit(request)

		self.assertEqual(request.deployment, first)
		# Counted by these terms, which this test alone uses: the transaction
		# rolls back once per class, so counting by node would see siblings'.
		self.assertEqual(frappe.db.count(fixtures.DEPLOYMENT_DOCTYPE, {"terms_of_reference": terms.name}), 1)

	def test_the_deployment_starts_with_nobody_on_it(self):
		"""Who goes is a coordinator's judgement, not a consequence of approval."""
		terms = fixtures.make_terms_requiring()
		request = fixtures.make_request(terms.name, self.society_a["branch"])
		request_service.submit(request)

		deployment = frappe.get_doc(fixtures.DEPLOYMENT_DOCTYPE, request.deployment)

		self.assertEqual(deployment.participants, [])


class TestTheRoutedModeUsesTheRealEngine(RequestTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_workflow(fixtures.REQUEST_DOCTYPE, fixtures.REQUEST_APPROVER_ROLE)

	def routed_request(self, node=None):
		terms = fixtures.make_terms_requiring(approval_mode="routed")
		request = fixtures.make_request(terms.name, node or self.society_a["post"])
		request_service.submit(request)

		return request

	def test_a_routed_request_enters_review_and_is_not_fulfilled(self):
		request = self.routed_request()

		self.assertEqual(self.approval_state(fixtures.REQUEST_DOCTYPE, request.name), states.IN_REVIEW)
		self.assertIsNone(request.deployment)

	def test_it_routes_to_the_person_the_engine_resolved(self):
		"""Nearest ancestor holding the role, found by core, from the request's anchor."""
		request = self.routed_request()

		self.assertEqual(engine.authorised(request)["approvers"], [self.approver])

	def test_it_lands_in_that_persons_queue(self):
		request = self.routed_request()

		queued = frappe.get_all(
			"ToDo",
			filters={
				"allocated_to": self.approver,
				"reference_type": fixtures.REQUEST_DOCTYPE,
				"reference_name": request.name,
				"status": ("in", ("Open", "Overdue")),
			},
			pluck="name",
		)

		self.assertTrue(queued)

	def test_approving_through_the_engine_creates_the_deployment(self):
		request = self.routed_request()

		with fixtures.acting_as(self.approver):
			engine.decide(request, states.DECISION_APPROVED)

		request = self.reload_request(request.name)

		self.assertEqual(request.approval_state, states.APPROVED)
		self.assertTrue(request.deployment)
		self.assertTrue(frappe.db.exists(fixtures.DEPLOYMENT_DOCTYPE, request.deployment))

	def test_the_wrong_approver_is_refused_even_holding_the_role(self):
		"""The person-gate, and the reason Frappe's native Workflow is not enough.

		`other_approver` holds the required role, holds the scope role that lets
		them open the record, and would satisfy any check of the form "does this
		user hold Deployment Approver". The document did not route to them.
		"""
		request = self.routed_request()

		self.assertIn(fixtures.REQUEST_APPROVER_ROLE, frappe.get_roles(self.other_approver))

		with fixtures.acting_as(self.other_approver), self.assertRaises(frappe.PermissionError):
			engine.decide(request, states.DECISION_APPROVED)

	def test_nothing_is_deployed_when_the_wrong_approver_is_refused(self):
		request = self.routed_request()

		with fixtures.acting_as(self.other_approver), self.assertRaises(frappe.PermissionError):
			engine.decide(request, states.DECISION_APPROVED)

		self.assertIsNone(self.reload_request(request.name).deployment)

	def test_a_rejected_request_never_becomes_a_deployment(self):
		request = self.routed_request()

		with fixtures.acting_as(self.approver):
			engine.decide(request, states.DECISION_REJECTED, reason="Not this time.")

		request = self.reload_request(request.name)

		self.assertEqual(request.approval_state, states.REJECTED)
		self.assertIsNone(request.deployment)
		self.assertFalse(request_service.is_fulfillable(request))

	def test_a_rejected_request_stays_refused_when_it_is_saved_again(self):
		"""The predicate must not treat "not approved" as "still waiting"."""
		request = self.routed_request()

		with fixtures.acting_as(self.approver):
			engine.decide(request, states.DECISION_REJECTED, reason="No.")

		request = self.reload_request(request.name)
		request.justification = "Edited afterwards."
		request.save()

		self.assertIsNone(self.reload_request(request.name).deployment)

	def test_the_engine_records_who_decided(self):
		"""There is no shadow trail: the audit rows are the engine's own."""
		request = self.routed_request()

		with fixtures.acting_as(self.approver):
			engine.decide(request, states.DECISION_APPROVED)

		request = self.reload_request(request.name)

		self.assertEqual(len(request.approval_decisions), 1)
		self.assertEqual(request.approval_decisions[0].approver, self.approver)


class TestSwitchingModeIsConfigurationAlone(RequestTestCase):
	def test_the_same_code_routes_or_does_not_by_configuration(self):
		"""One code path, and a settings value deciding the outcome.

		The two requests below differ in exactly one field on their terms of
		reference. Nothing in the module compared a terms of reference to a name
		to produce these two outcomes.
		"""
		fixtures.make_workflow(fixtures.REQUEST_DOCTYPE, fixtures.REQUEST_APPROVER_ROLE)

		direct = fixtures.make_request(
			fixtures.make_terms_requiring(approval_mode="direct").name, self.society_a["post"]
		)
		routed = fixtures.make_request(
			fixtures.make_terms_requiring(approval_mode="routed").name, self.society_a["post"]
		)

		request_service.submit(direct)
		request_service.submit(routed)

		self.assertTrue(direct.deployment)
		self.assertIsNone(routed.deployment)
		self.assertEqual(self.approval_state(fixtures.REQUEST_DOCTYPE, routed.name), states.IN_REVIEW)

	def test_a_routed_terms_with_no_workflow_refuses_loudly(self):
		"""Loudly, rather than deploying unapproved. The failure has to be visible."""
		terms = fixtures.make_terms_requiring(approval_mode="routed")
		request = fixtures.make_request(terms.name, self.society_a["post"])

		with self.assertRaises(frappe.ValidationError):
			request_service.submit(request)

		self.assertIsNone(self.reload_request(request.name).deployment)

	def test_a_mode_nobody_defined_is_refused_at_the_terms(self):
		with self.assertRaises(frappe.ValidationError):
			fixtures.make_terms(f"{fixtures.TEST_PREFIX}-bad-mode", approval_mode="whenever")


class TestTheRequestRecordItself(RequestTestCase):
	def test_a_request_for_nobody_is_refused(self):
		terms = fixtures.make_terms_requiring()

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_request(terms.name, self.society_a["branch"], volunteers_requested=0)

	def test_a_period_running_backwards_is_refused(self):
		terms = fixtures.make_terms_requiring()

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_request(
				terms.name,
				self.society_a["branch"],
				needed_from=today(),
				needed_until=add_days(today(), -1),
			)

	def test_the_headcount_is_what_was_asked_for_and_not_a_quota(self):
		"""A deployment that ran with fewer people is an ordinary outcome."""
		terms = fixtures.make_terms_requiring()
		request = fixtures.make_request(terms.name, self.society_a["branch"], volunteers_requested=5)
		request_service.submit(request)

		deployment = frappe.get_doc(fixtures.DEPLOYMENT_DOCTYPE, request.deployment)

		self.assertEqual(deployment.participants, [])
		self.assertEqual(request.volunteers_requested, 5)
