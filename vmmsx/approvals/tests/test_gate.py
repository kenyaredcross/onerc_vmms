# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The gate — an approval routes to a person, and refuses everyone else.

This is the test the whole design exists for. Frappe's native Workflow can ask
*does this user hold Volunteer Approver*; four different people in this file
hold it, and only one of them may act. Holding the role is not authorisation.
Being the person this document resolved to is.

Everybody refused here is refused for a different reason, and each of them is a
real failure that has shipped in systems like this:

- the coordinator of **another county** — right role, wrong place;
- a role holder with **no geo authority at all** — a role granted and forgotten;
- the **applicant** — the most obvious one, and the one a UI-only check misses;
- a **System Manager** — every permission in the system, and still not the
  person this application routed to.

And the gate is recomputed, never remembered: an approver whose authority ended
is refused today even though they were the right person yesterday.
"""

import frappe
from onerc_core.access.services.registry import SCOPEABLE_DOCTYPE_HOOK

from vmmsx.api import approvals as api
from vmmsx.approvals import states
from vmmsx.approvals.services import contract, engine
from vmmsx.approvals.tests import fixtures
from vmmsx.approvals.tests.base import ApprovalTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestThePersonGate(ApprovalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.kiambu_coordinator = fixtures.make_user("gate_kiambu", [fixtures.APPROVER_ROLE])
		cls.nakuru_coordinator = fixtures.make_user("gate_nakuru", [fixtures.APPROVER_ROLE])
		cls.unassigned_holder = fixtures.make_user("gate_unassigned", [fixtures.APPROVER_ROLE])
		cls.applicant = fixtures.make_user("gate_applicant", [fixtures.APPLICANT_ROLE])
		# The one exception to "never a System Manager" in these fixtures: this
		# user exists to prove that the framework's most powerful role does not
		# open the gate either.
		cls.system_manager = fixtures.make_user("gate_sysmanager", ["System Manager"])

		fixtures.make_assignment(cls.kiambu_coordinator, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])
		fixtures.make_assignment(cls.nakuru_coordinator, fixtures.APPROVER_ROLE, cls.kenya["nakuru"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)]
		)

	def setUp(self):
		super().setUp()

		self.application = fixtures.make_application(
			"gate", self.kenya["kihara"], applicant=self.applicant, owner=self.applicant
		)
		engine.submit(self.reload(self.application))

	def everyone_else(self) -> list[str]:
		return [
			self.nakuru_coordinator,
			self.unassigned_holder,
			self.applicant,
			self.system_manager,
		]

	# --- the one person who may ------------------------------------------

	def test_the_resolved_approver_may_approve(self):
		with fixtures.acting_as(self.kiambu_coordinator):
			status = engine.decide(self.reload(self.application), states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.APPROVED)
		self.assertEqual(self.state(self.application), states.APPROVED)

	def test_the_resolved_approver_sees_that_they_may_act(self):
		with fixtures.acting_as(self.kiambu_coordinator):
			status = engine.status(self.reload(self.application))

		self.assertTrue(status["can_act"])
		self.assertEqual(status["approvers"], [self.kiambu_coordinator])

	# --- everybody else ---------------------------------------------------

	def test_it_refuses_everyone_else(self):
		for user in self.everyone_else():
			with (
				fixtures.acting_as(user),
				self.assertRaises(frappe.PermissionError, msg=f"{user} got through"),
			):
				engine.decide(self.reload(self.application), states.DECISION_APPROVED)

	def test_a_refusal_changes_nothing(self):
		"""No state, no audit row, and it stays in the right person's queue."""
		for user in self.everyone_else():
			with fixtures.acting_as(user), self.assertRaises(frappe.PermissionError):
				engine.decide(self.reload(self.application), states.DECISION_APPROVED, "let me in")

		self.assertEqual(self.state(self.application), states.IN_REVIEW)
		self.assertEqual(contract.decisions(self.reload(self.application)), [])
		self.assertIn(self.application, self.queue_of(self.kiambu_coordinator))

	def test_holding_the_role_elsewhere_is_not_enough(self):
		"""Right role, wrong place. The most plausible mistake in the whole system."""
		self.assertIn(fixtures.APPROVER_ROLE, frappe.get_roles(self.nakuru_coordinator))

		with fixtures.acting_as(self.nakuru_coordinator):
			self.assertFalse(engine.may_act(self.reload(self.application)))

	def test_a_system_manager_is_not_the_routed_approver(self):
		"""Every permission in the system, and still not this application's approver.

		Deliberate. Core's scope layer lets a System Manager *reach* any record;
		routing does not name them, so they cannot decide one. An administrator
		who genuinely must act grants themselves a Geo Assignment, and the audit
		trail then shows who really acted.
		"""
		with fixtures.acting_as(self.system_manager):
			self.assertFalse(engine.may_act(self.reload(self.application)))

	def test_nobody_else_has_it_in_their_queue(self):
		for user in self.everyone_else():
			self.assertNotIn(self.application, self.queue_of(user))

	def test_the_applicant_is_not_told_who_holds_it(self):
		"""How many, not which. The count is theirs; the names are not."""
		with fixtures.acting_as(self.applicant):
			status = engine.status(self.reload(self.application))

		self.assertFalse(status["can_act"])
		self.assertIsNone(status["approvers"])
		self.assertEqual(status["approver_count"], 1)

	# --- the same gate through the public endpoint ------------------------

	def test_the_api_refuses_the_wrong_person(self):
		with fixtures.acting_as(self.nakuru_coordinator), self.assertRaises(frappe.PermissionError):
			api.decide(fixtures.APPROVABLE_DOCTYPE, self.application, states.DECISION_APPROVED)

	def test_the_api_admits_the_right_person(self):
		with fixtures.acting_as(self.kiambu_coordinator):
			status = api.decide(fixtures.APPROVABLE_DOCTYPE, self.application, states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.APPROVED)

	def test_the_api_refuses_a_doctype_no_workflow_governs(self):
		with self.assertRaises(frappe.ValidationError):
			api.get_status("ToDo", "does-not-matter")

	def test_the_queue_endpoint_shows_the_approver_their_work(self):
		with fixtures.acting_as(self.kiambu_coordinator):
			queue = api.my_queue()

		self.assertIn(self.application, [row["name"] for row in queue])

	def test_the_queue_endpoint_shows_everyone_else_nothing(self):
		for user in self.everyone_else():
			with fixtures.acting_as(user):
				self.assertEqual(api.my_queue(), [], f"{user} sees somebody else's queue")


class TestAuthorityThatEnded(ApprovalTestCase):
	"""The gate is recomputed from Geo Assignment, never cached on the document.

	Yesterday's approver is not today's. If the resolution were stored when the
	application was routed, an approver whose assignment ended last week could
	still approve — which is the failure the access model exists to prevent.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.former = fixtures.make_user("ended_county", [fixtures.APPROVER_ROLE])
		cls.regional = fixtures.make_user("ended_region", [fixtures.APPROVER_ROLE])

		fixtures.make_assignment(
			cls.former,
			fixtures.APPROVER_ROLE,
			cls.kenya["kiambu"],
			valid_to=frappe.utils.add_days(frappe.utils.today(), -1),
		)
		fixtures.make_assignment(cls.regional, fixtures.APPROVER_ROLE, cls.kenya["region"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)]
		)

	def test_the_walk_passes_a_county_whose_authority_expired(self):
		application = self.application("expired authority", self.kenya["kihara"])
		status = engine.submit(self.reload(application))

		self.assertEqual(status["approvers"], [self.regional])

	def test_the_former_approver_is_refused(self):
		application = self.application("expired approver", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.former), self.assertRaises(frappe.PermissionError):
			engine.decide(self.reload(application), states.DECISION_APPROVED)


class TestGeoScopeAndTheGateAgree(ApprovalTestCase):
	"""Two layers, one answer.

	Core's enforcement decides whether a user may *reach* the record; the gate
	decides whether they may *decide* it. Both read Geo Assignment, so a user
	refused by one is never admitted by the other — and the engine asks core
	first, so an approver outside the area is stopped before the routing check
	even runs.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.kiambu_coordinator = fixtures.make_user("scoped_kiambu", [fixtures.APPROVER_ROLE])
		cls.nakuru_coordinator = fixtures.make_user("scoped_nakuru", [fixtures.APPROVER_ROLE])

		fixtures.make_assignment(cls.kiambu_coordinator, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])
		fixtures.make_assignment(cls.nakuru_coordinator, fixtures.APPROVER_ROLE, cls.kenya["nakuru"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)]
		)

	def scoped(self):
		"""Register the stand-in with core, exactly as a product app would."""
		return self.patch_hooks(
			{
				SCOPEABLE_DOCTYPE_HOOK: [
					{
						"doctype": fixtures.APPROVABLE_DOCTYPE,
						"geo_node_field": fixtures.GEO_FIELD,
						"role": fixtures.APPROVER_ROLE,
					}
				]
			}
		)

	def test_the_scoped_out_approver_cannot_even_read_it(self):
		application = self.application("scoped read", self.kenya["kihara"])

		with self.scoped():
			self.assertFalse(
				frappe.has_permission(
					fixtures.APPROVABLE_DOCTYPE,
					doc=frappe.get_doc(fixtures.APPROVABLE_DOCTYPE, application),
					user=self.nakuru_coordinator,
					ptype="read",
				)
			)

	def test_and_cannot_decide_it_either(self):
		application = self.application("scoped decide", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with (
			self.scoped(),
			fixtures.acting_as(self.nakuru_coordinator),
			self.assertRaises(frappe.PermissionError),
		):
			engine.decide(self.reload(application), states.DECISION_APPROVED)

	def test_the_routed_approver_passes_both_layers(self):
		application = self.application("scoped pass", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with self.scoped(), fixtures.acting_as(self.kiambu_coordinator):
			status = engine.decide(self.reload(application), states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.APPROVED)
