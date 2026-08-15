# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Volunteer Application goes through the real approval engine. Third time, no drift.

The engine already has its own tests, and Membership already proved a real
module can consume it. What a third consumer is worth proving is that it is the
*same* engine — that nothing about volunteering needed a special case, a second
routing path, or a private notion of who may act. So these tests assert against
the engine's own services and the real `VMMS Approval Workflow`, never against
anything this module reimplemented, because there is nothing this module
reimplemented.

Four things are established:

1. **Routing lands on the person core resolved**, through a role held at a place
   — and the same configuration resolves correctly in two societies with
   differently-shaped hierarchies.
2. **The gate is a person-gate, not a role-gate.** A user holding the very same
   role, in the very same society, who is not the person this document routed
   to, is refused — and the refusal changes nothing at all.
3. **Approval produces a volunteer**, through the acceptance predicate, without
   the engine knowing volunteers exist.
4. **The anchor rules bind here too** — ACC-02 at creation, ACC-03 through the
   workflow's permitted levels at submission.
"""

import frappe

from vmmsx.approvals import states
from vmmsx.approvals.services import config, contract
from vmmsx.volunteer.services import application as application_service
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class EngineTestCase(VolunteerTestCase):
	"""One workflow, one approver per society, and applicants in both."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_workflow()
		fixtures.grant_doctype_access(fixtures.APPLICATION_DOCTYPE, fixtures.APPROVER_ROLE)

		# The approver for society A, placed at its county. Core resolves the
		# nearest ancestor holding the role, so an application anchored at a ward
		# beneath this node routes here.
		cls.approver_a = cls.scoped_user("engine_approver_a", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver_a, fixtures.APPROVER_ROLE, cls.society_a["county"])

		# The approver for society B, placed at its district. Same role, same
		# configuration, a differently-shaped hierarchy.
		cls.approver_b = cls.scoped_user("engine_approver_b", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver_b, fixtures.APPROVER_ROLE, cls.society_b["district"])

		# Holds the approver role but is placed nowhere near society A's ward.
		# This is the user the person-gate has to refuse.
		cls.wrong_approver = cls.approver_b

		# Holds no approver role at all.
		cls.outsider = cls.scoped_user("engine_outsider", [fixtures.APPLICANT_ROLE])

	def submitted_application(self, node: str | None = None):
		"""An application in review, submitted through the engine."""
		profile = fixtures.make_profile("Engine", "Applicant")
		application = fixtures.make_application(profile, node or self.society_a["ward"])

		application_service.submit(application)

		return application


class TestTheEngineIsTheRealOne(EngineTestCase):
	def test_the_application_is_governed_by_a_real_workflow(self):
		"""Read from the engine's own configuration service, not from a fixture."""
		workflow = config.for_doctype(fixtures.APPLICATION_DOCTYPE)

		self.assertEqual(workflow.workflow_for, fixtures.APPLICATION_DOCTYPE)
		self.assertEqual(workflow.geo_node_field, "geo_node")
		self.assertTrue(config.is_approvable(fixtures.APPLICATION_DOCTYPE))

	def test_the_doctype_satisfies_the_engine_contract(self):
		"""The contract check the engine runs when a workflow is saved.

		If this doctype did not meet it, the workflow above would have refused to
		save — so asserting it directly is asserting the reason that worked.
		"""
		contract.assert_approvable(fixtures.APPLICATION_DOCTYPE)

		self.assertTrue(contract.decisions_field(fixtures.APPLICATION_DOCTYPE))

	def test_submission_moves_the_engine_state(self):
		application = self.submitted_application()

		self.assertEqual(self.approval_state(application.name), states.IN_REVIEW)
		self.assertTrue(contract.stage(application), "the engine set no stage")

	def test_docstatus_is_not_used_as_the_lifecycle(self):
		"""An approvable document stays at docstatus 0; the state is the lifecycle."""
		application = self.submitted_application()

		self.assertEqual(application.docstatus, 0)


class TestRouting(EngineTestCase):
	def test_it_routes_to_the_person_core_resolved(self):
		application = self.submitted_application()

		self.assertIn(application.name, self.queue_of(self.approver_a))

	def test_the_gate_agrees_with_the_queue(self):
		"""Being in somebody's queue and being allowed to act must not diverge.

		The assignment is a notification; the gate is the authority. They are
		computed from the same resolution, so a document in a queue whose holder
		the gate refuses would mean routing and the gate had drifted apart.
		"""
		from vmmsx.approvals.services import engine

		application = self.submitted_application()

		self.assertTrue(engine.may_act(application, self.approver_a))
		self.assertIn(self.approver_a, engine.authorised(application)["approvers"])

	def test_the_same_configuration_routes_in_the_other_society(self):
		"""A differently-shaped hierarchy, the same stage, no code aware of either."""
		application = self.submitted_application(self.society_b["ward"])

		self.assertIn(application.name, self.queue_of(self.approver_b))
		self.assertNotIn(application.name, self.queue_of(self.approver_a))

	def test_it_does_not_route_to_a_holder_somewhere_else(self):
		application = self.submitted_application()

		self.assertNotIn(application.name, self.queue_of(self.approver_b))


class TestTheGateRefusesTheWrongPerson(EngineTestCase):
	"""Holding the role is not enough. This is the whole reason for the engine."""

	def test_a_holder_of_the_same_role_elsewhere_is_refused(self):
		application = self.submitted_application()

		self.assertIn(
			fixtures.APPROVER_ROLE,
			frappe.get_roles(self.wrong_approver),
			"the test is meaningless unless this user really holds the role",
		)

		with fixtures.acting_as(self.wrong_approver), self.assertRaises(frappe.PermissionError):
			self.decide(application, states.DECISION_APPROVED)

	def test_the_refused_user_could_read_the_document_perfectly_well(self):
		"""So the refusal above was the person-gate and not a read permission.

		Without this, a test asserting "the wrong approver is refused" would pass
		just as happily if they had been stopped at the door by permissions, and
		the gate the engine exists for would never have been exercised.
		"""
		application = self.submitted_application()

		with fixtures.acting_as(self.wrong_approver):
			readable = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name)

			self.assertEqual(readable.name, application.name)
			self.assertTrue(frappe.has_permission(fixtures.APPLICATION_DOCTYPE, doc=readable, ptype="read"))

	def test_a_user_with_no_approver_role_is_refused(self):
		application = self.submitted_application()

		with fixtures.acting_as(self.outsider), self.assertRaises(frappe.PermissionError):
			self.decide(application, states.DECISION_APPROVED)

	def test_the_refusal_changes_nothing(self):
		"""A refused decision must leave no trace: no state, no row, no queue change.

		The check that matters. A gate that refuses but has already written half
		an audit trail is a gate that can be used to write audit trails.
		"""
		application = self.submitted_application()
		before = {
			"state": self.approval_state(application.name),
			"stage": frappe.db.get_value(fixtures.APPLICATION_DOCTYPE, application.name, "approval_stage"),
			"decisions": self.decision_count(application.name),
			"volunteer": self.volunteer_of(application.name),
			"queue": self.queue_of(self.approver_a),
		}

		with fixtures.acting_as(self.wrong_approver), self.assertRaises(frappe.PermissionError):
			self.decide(application, states.DECISION_APPROVED)

		self.assertEqual(self.approval_state(application.name), before["state"])
		self.assertEqual(
			frappe.db.get_value(fixtures.APPLICATION_DOCTYPE, application.name, "approval_stage"),
			before["stage"],
		)
		self.assertEqual(self.decision_count(application.name), before["decisions"])
		self.assertIsNone(before["volunteer"])
		self.assertIsNone(self.volunteer_of(application.name), "a refused decision created a volunteer")
		self.assertEqual(self.queue_of(self.approver_a), before["queue"])

	def test_the_right_person_is_not_refused(self):
		"""Guards the four tests above: the refusals are about the person, not a bug."""
		application = self.submitted_application()

		with fixtures.acting_as(self.approver_a):
			self.decide(application, states.DECISION_APPROVED)

		self.assertEqual(self.approval_state(application.name), states.APPROVED)

	def decide(self, application, decision: str, reason: str | None = None):
		"""Act on an approval the way the API does — through the engine, every time.

		The document is re-read inside the acting user's session, because that is
		what an API request does and because the gate recomputes from the document
		it is given.
		"""
		from vmmsx.approvals.services import engine

		return engine.decide(
			frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name),
			decision,
			reason=reason,
		)


class TestApprovalProducesAVolunteer(EngineTestCase):
	def approved(self):
		application = self.submitted_application()

		with fixtures.acting_as(self.approver_a):
			from vmmsx.approvals.services import engine

			engine.decide(
				frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name),
				states.DECISION_APPROVED,
			)

		return self.reload_application(application.name)

	def test_approval_creates_the_volunteer(self):
		application = self.approved()

		self.assertEqual(application.approval_state, states.APPROVED)
		self.assertTrue(application.volunteer, "an approved application produced no volunteer")

	def test_the_volunteer_is_active_and_placed_where_they_applied(self):
		application = self.approved()
		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, application.volunteer)

		self.assertEqual(volunteer.status, "Active")
		self.assertEqual(volunteer.home_geo_node, application.geo_node)
		self.assertEqual(volunteer.red_profile, application.red_profile)

	def test_the_affiliation_index_was_written(self):
		application = self.approved()

		self.assertIn("volunteer", self.affiliation_types(application.red_profile))

	def test_acceptance_is_idempotent(self):
		"""Saving an accepted application again must not make a second volunteer."""
		application = self.approved()
		first = application.volunteer

		application.save(ignore_permissions=True)
		application_service.try_accept(application)

		self.assertEqual(self.volunteer_of(application.name), first)
		self.assertEqual(
			frappe.db.count(fixtures.VOLUNTEER_DOCTYPE, {"red_profile": application.red_profile}),
			1,
		)

	def test_a_rejection_produces_no_volunteer(self):
		"""A rejection ends the application, not the person."""
		from vmmsx.approvals.services import engine

		application = self.submitted_application()

		with fixtures.acting_as(self.approver_a):
			engine.decide(
				frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name),
				states.DECISION_REJECTED,
				reason="Not this time.",
			)

		self.assertEqual(self.approval_state(application.name), states.REJECTED)
		self.assertIsNone(self.volunteer_of(application.name))
		self.assertFalse(
			frappe.db.exists(fixtures.VOLUNTEER_DOCTYPE, {"red_profile": application.red_profile})
		)


class TestTheAnchorRules(EngineTestCase):
	def test_an_unplaced_application_cannot_exist(self):
		"""ACC-02, refused at creation rather than corrected later."""
		profile = fixtures.make_profile("Unplaced", "Applicant")

		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc(
				{
					"doctype": fixtures.APPLICATION_DOCTYPE,
					"red_profile": profile,
					"geo_node": None,
				}
			).insert()

	def test_the_workflow_refuses_a_level_the_society_did_not_permit(self):
		"""ACC-03, and it lives on the workflow rather than in this module.

		The workflow is narrowed to ward level, so an application anchored at the
		county above it is refused at submission — by the engine, reading
		configuration, with no level name anywhere in the Volunteer module.
		"""
		fixtures.make_workflow(allowed_anchor_levels=[{"geo_level": self.society_a["levels"]["ward"]}])
		self.addCleanup(fixtures.make_workflow)

		profile = fixtures.make_profile("Wrong", "Level")
		application = fixtures.make_application(profile, self.society_a["county"])

		with self.assertRaises(frappe.ValidationError):
			application_service.submit(application)

		self.assertEqual(self.approval_state(application.name), states.DRAFT)

	def test_the_permitted_level_still_works(self):
		"""Guards the test above: the narrowing permits what it says it permits."""
		fixtures.make_workflow(allowed_anchor_levels=[{"geo_level": self.society_a["levels"]["ward"]}])
		self.addCleanup(fixtures.make_workflow)

		application = self.submitted_application(self.society_a["ward"])

		self.assertEqual(self.approval_state(application.name), states.IN_REVIEW)
