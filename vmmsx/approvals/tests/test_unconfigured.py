# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Applying before the society has written its approval workflow.

A site is live from the day it is installed. Deciding who signs off on what is
an administrator's job that happens on its own timetable, and the person filling
in the registration form is the one party who can do nothing about the gap. So
the engine accepts the application and holds it — Submitted, routed to nobody,
decided by nobody — and routes it the moment the workflow exists.

The two failures these tests exist to prevent are opposite and both are bad:

1. **Refusing the applicant**, which turns unfinished setup into a public door
   that looks broken, with a message addressed to whoever configures the site.
2. **Approving them**, which is what a workflow with no stages means and is
   emphatically not what *no workflow* means. Nobody becomes a volunteer or a
   member without somebody deciding they should.
"""

import frappe

from vmmsx.approvals import states
from vmmsx.approvals.services import contract, engine, repair
from vmmsx.approvals.tests import fixtures
from vmmsx.approvals.tests.base import ApprovalTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestApplyingBeforeTheWorkflowExists(ApprovalTestCase):
	"""The stand-in doctype, ungoverned — and then governed halfway through."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county = fixtures.make_user("unset_county", [fixtures.APPROVER_ROLE])
		cls.applicant = fixtures.make_user("unset_applicant", [fixtures.APPLICANT_ROLE])
		fixtures.make_assignment(cls.county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

	def setUp(self):
		super().setUp()

		# Every test in this class starts on a site whose society has configured
		# nothing. The ones that go on to configure something do it themselves.
		fixtures.remove_workflow()

	def configure(self):
		"""Write the workflow these applications have been waiting for."""
		return fixtures.make_workflow([fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)])

	# --- accepted, and held ------------------------------------------------

	def test_an_application_is_accepted_with_no_workflow(self):
		application = self.application("no workflow", self.kenya["kihara"])
		status = engine.submit(self.reload(application))

		self.assertEqual(status["state"], states.SUBMITTED)
		self.assertTrue(status["is_open"])
		self.assertIsNone(status["stage"])

	def test_it_is_held_rather_than_approved(self):
		"""The trap: a workflow with no stages approves, and no workflow must not."""
		application = self.application("not approved", self.kenya["kihara"])
		engine.submit(self.reload(application))

		self.assertEqual(self.state(application), states.SUBMITTED)
		self.assertNotEqual(self.state(application), states.APPROVED)

	def test_it_is_assigned_to_nobody(self):
		application = self.application("unassigned", self.kenya["kihara"])
		engine.submit(self.reload(application))

		self.assertNotIn(application, self.queue_of(self.county))

	def test_the_status_says_it_is_waiting_on_configuration(self):
		"""A parked application and a draft both have no stage, and are opposites."""
		application = self.application("waiting", self.kenya["kihara"])
		status = engine.submit(self.reload(application))

		self.assertTrue(status["awaiting_workflow"])

	def test_submitting_twice_holds_it_once(self):
		application = self.application("twice", self.kenya["kihara"])
		engine.submit(self.reload(application))
		status = engine.submit(self.reload(application))

		self.assertEqual(status["state"], states.SUBMITTED)
		self.assertEqual(self.state(application), states.SUBMITTED)

	def test_the_applicant_may_still_withdraw(self):
		"""Waiting on configuration must not be the one state nobody can leave."""
		application = self.application("withdrawn", self.kenya["kihara"], owner=self.applicant)
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.applicant):
			status = engine.withdraw(self.reload(application), "Changed my mind")

		self.assertEqual(status["state"], states.WITHDRAWN)

	# --- and then the workflow arrives -------------------------------------

	def test_writing_the_workflow_routes_what_was_waiting(self):
		application = self.application("adopted", self.kenya["kihara"])
		engine.submit(self.reload(application))

		self.configure()
		repair.resync_pending(fixtures.APPROVABLE_DOCTYPE)

		self.assertEqual(self.state(application), states.IN_REVIEW)
		self.assertIn(application, self.queue_of(self.county))

	def test_it_enters_the_first_stage_rather_than_skipping_it(self):
		application = self.application("first stage", self.kenya["kihara"])
		engine.submit(self.reload(application))

		self.configure()
		repair.resync_pending(fixtures.APPROVABLE_DOCTYPE)
		status = engine.status(self.reload(application))

		self.assertEqual(status["stage"]["sequence"], 1)
		self.assertEqual(status["approvers"], [self.county])
		self.assertFalse(status["awaiting_workflow"])

	def test_submit_itself_routes_a_parked_application(self):
		"""The sweep is one caller; re-asking the engine directly is another."""
		application = self.application("resubmitted", self.kenya["kihara"])
		engine.submit(self.reload(application))

		self.configure()
		status = engine.submit(self.reload(application))

		self.assertEqual(status["state"], states.IN_REVIEW)
		self.assertEqual(status["approvers"], [self.county])

	def test_the_sweep_leaves_an_already_routed_application_alone(self):
		"""Routing runs once: a second sweep must not restart a stage's clock."""
		application = self.application("routed once", self.kenya["kihara"])
		engine.submit(self.reload(application))

		self.configure()
		repair.resync_pending(fixtures.APPROVABLE_DOCTYPE)
		entered = contract.stage_entered_on(self.reload(application))

		repair.resync_pending(fixtures.APPROVABLE_DOCTYPE)

		self.assertEqual(contract.stage_entered_on(self.reload(application)), entered)

	def test_a_decision_can_then_be_taken_on_it(self):
		"""The whole point: it reaches whoever is assigned, and they decide it."""
		application = self.application("decided", self.kenya["kihara"])
		engine.submit(self.reload(application))

		self.configure()
		repair.resync_pending(fixtures.APPROVABLE_DOCTYPE)

		with fixtures.acting_as(self.county):
			status = engine.decide(self.reload(application), states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.APPROVED)

	def test_a_withdrawn_application_is_not_routed_later(self):
		"""Terminal is terminal. A workflow written afterwards does not revive it."""
		application = self.application("gone", self.kenya["kihara"], owner=self.applicant)
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.applicant):
			engine.withdraw(self.reload(application), "No longer needed")

		self.configure()
		repair.resync_pending(fixtures.APPROVABLE_DOCTYPE)

		self.assertEqual(self.state(application), states.WITHDRAWN)


class TestTheQueueOfAnUngovernedRegister(ApprovalTestCase):
	"""What the console shows a coordinator before the workflow is written.

	Nothing is routed to anybody — there is nobody to route to — but the screens
	have to say that by being empty, not by failing. A queue that errors on a
	fresh site is the first thing an administrator sees of this app.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county = fixtures.make_user("unset_queue", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

	def setUp(self):
		super().setUp()
		fixtures.remove_workflow()

	def test_the_open_queue_is_empty_rather_than_refused(self):
		from vmmsx.api import approvals

		application = self.application("queue", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.county):
			self.assertEqual(approvals.my_queue(fixtures.APPROVABLE_DOCTYPE), [])

	def test_the_history_bands_are_empty_rather_than_refused(self):
		from vmmsx.api import approvals

		with fixtures.acting_as(self.county):
			closed = approvals.my_cases(fixtures.APPROVABLE_DOCTYPE, approvals.CASE_CLOSED)

		self.assertEqual(closed["cases"], [])

	def test_a_doctype_that_is_not_approvable_at_all_is_still_refused(self):
		"""The narrowing the gate exists for, unchanged."""
		from vmmsx.api import approvals

		with self.assertRaises(frappe.ValidationError):
			approvals.my_queue("ToDo")
