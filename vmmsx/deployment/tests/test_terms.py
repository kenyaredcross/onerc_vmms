# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Freezing a mission document: finished first, approved where the society says so.

A terms of reference is the contract. There is no separate agreement document —
accepting a deployment assignment is accepting this wording — so the moment it is
submitted is the moment it stops being editable and starts being something people
can be asked to agree to. Three rules guard that moment and this suite is about
all three.

1. **It has to be finished.** `terms.REQUIRED_AT_SUBMISSION` is the list, and it
   is checked at submission and never on save: a mission document is written over
   several sittings, and a draft that refused to save until it was complete would
   be a draft nobody could use.
2. **Who freezes it is configuration.** With no `VMMS Approval Workflow` for the
   doctype, anybody with submit permission submits it. With one, the direct door
   is closed and the engine's is the only way through — and the document submits
   itself the moment the last approver says yes. Neither path is a fallback for
   the other; both refuse explicitly.
3. **What is agreed stays agreed.** Cancelling terms a deployment points at is
   refused, because the people already deployed agreed to exactly that wording.
   Respecifying the mission is `supersede`: a new document, a link back, and the
   original untouched.
"""

import frappe

from vmmsx.approvals import states
from vmmsx.approvals.services import engine
from vmmsx.deployment.services import terms as terms_service
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

TERMS_APPROVER_ROLE = f"{fixtures.TEST_PREFIX} Terms Approver"


class TermsTestCase(DeploymentTestCase):
	def bare_terms(self, **values):
		"""A draft with nothing on it but a name and a place. The gate's starting point.

		Deliberately not `fixtures.make_terms`, which fills in a whole mission
		document precisely so that every other suite can submit one. What is being
		tested here is what happens when it has not been filled in.

		The place is here because `geo_scope` is the one item on the submission
		list that is *also* mandatory at creation: a mission document that applies
		nowhere in particular cannot be routed to anybody, so it is refused a save
		rather than a submission. `test_the_place_is_the_one_answer_asked_for_up_front`
		is that rule on its own.
		"""
		payload = {
			"doctype": fixtures.TERMS_DOCTYPE,
			"tor_key": f"{fixtures.TEST_PREFIX}-bare-{frappe.generate_hash(length=8)}",
			"tor_name": "Half Written Mission",
			"purpose": "Whatever this society uses these terms for.",
			"approval_mode": "direct",
			"is_active": 1,
			"geo_scope": fixtures.default_scope(),
		}
		payload.update(values)

		return frappe.get_doc(payload).insert()

	def complete_payload(self, **values):
		"""Everything the gate asks for, so a test can take exactly one thing away."""
		from frappe.utils import add_days, today

		node = fixtures.default_scope()
		payload = {
			"geo_scope": node,
			"project": fixtures.make_project(node),
			"expected_start_date": today(),
			"expected_end_date": add_days(today(), 6),
			"mission_background": "<p>Why the society keeps a specification for this.</p>",
			"objectives": [{"objective": "Do the work."}],
			"expected_outputs": [{"output": "A record of what was done."}],
			"stakeholders": [{"designation": "Branch Coordinator"}],
			"itinerary": [{"activity_date": today(), "activity": "Briefing"}],
			"has_no_resources": 1,
		}
		payload.update(values)

		return payload


class TestTheMissionDocumentHasToBeFinished(TermsTestCase):
	def test_a_half_written_draft_saves_perfectly_well(self):
		"""The gate is at submission. Writing one over several sittings has to work."""
		self.assertTrue(self.bare_terms().name)

	def test_but_it_will_not_submit(self):
		draft = self.bare_terms()

		with self.assertRaises(frappe.MandatoryError):
			draft.submit()

	def test_the_refusal_names_everything_missing_at_once(self):
		"""Nine round trips is not a form. The whole list comes back in one sentence.

		Everything on the list except the place, which a draft already had to
		carry before it could be saved at all, plus the resources answer.
		"""
		draft = self.bare_terms()
		missing = terms_service.missing_at_submission(draft)

		self.assertEqual(len(missing), len(terms_service.REQUIRED_AT_SUBMISSION))

	def test_the_place_is_the_one_answer_asked_for_up_front(self):
		"""Not at submission but at creation, because an unplaced mission document
		cannot be routed to anybody and cannot be scoped to anybody's register."""
		with self.assertRaises(frappe.MandatoryError):
			self.bare_terms(geo_scope=None)

	def test_a_complete_document_submits(self):
		draft = self.bare_terms(**self.complete_payload())
		draft.submit()

		self.assertEqual(draft.docstatus, 1)
		self.assertEqual(terms_service.missing_at_submission(draft), [])

	def test_each_required_answer_is_actually_required(self):
		"""Taken away one at a time, so a passing gate cannot be one rule doing all the work.

		The refusal is asserted around building *and* submitting, because one of
		the nine — the place — is refused at the earlier of the two doors. Which
		door said no is not what this test is about; that nothing gets through
		without each answer is.
		"""
		for field, _label in terms_service.REQUIRED_AT_SUBMISSION:
			with self.subTest(field=field):
				with self.assertRaises(frappe.MandatoryError):
					self.bare_terms(**self.complete_payload(**{field: None})).submit()

	def test_a_mission_with_no_resource_lines_and_no_declaration_is_refused(self):
		draft = self.bare_terms(**self.complete_payload(has_no_resources=0))

		with self.assertRaises(frappe.MandatoryError):
			draft.submit()

	def test_the_declaration_is_one_of_the_two_right_answers(self):
		draft = self.bare_terms(**self.complete_payload(has_no_resources=1))
		draft.submit()

		self.assertEqual(draft.docstatus, 1)

	def test_and_resource_lines_are_the_other(self):
		draft = self.bare_terms(
			**self.complete_payload(
				has_no_resources=0,
				resources=[{"resource": "Tarpaulin", "quantity": 10, "unit_cost": 32000}],
			)
		)
		draft.submit()

		self.assertEqual(draft.docstatus, 1)


class TestResourceLinesArePriced(TermsTestCase):
	def test_the_total_is_derived_from_the_two_numbers_it_comes_from(self):
		draft = self.bare_terms(
			**self.complete_payload(
				has_no_resources=0,
				resources=[{"resource": "Jerry can", "quantity": 150, "unit_cost": 7500}],
			)
		)

		self.assertEqual(draft.resources[0].total_cost, 150 * 7500)

	def test_it_is_recomputed_rather_than_only_filled_in_when_blank(self):
		"""A stored total that can drift from its inputs eventually disagrees with them."""
		draft = self.bare_terms(
			**self.complete_payload(
				has_no_resources=0,
				resources=[{"resource": "Mosquito net", "quantity": 2, "unit_cost": 100}],
			)
		)
		draft.resources[0].quantity = 3
		draft.save()

		self.assertEqual(draft.resources[0].total_cost, 300)

	def test_the_unit_is_a_real_unit_of_measure(self):
		"""Free text could never be added up or compared against a purchase."""
		self.assertEqual(
			frappe.get_meta("VMMS TOR Resource").get_field("unit").options, "UOM"
		)

	def test_the_mission_total_is_the_sum_of_its_lines(self):
		draft = self.bare_terms(
			**self.complete_payload(
				has_no_resources=0,
				resources=[
					{"resource": "Life jacket", "quantity": 24, "unit_cost": 45000},
					{"resource": "Stretcher", "quantity": 4, "unit_cost": 180000},
				],
			)
		)

		self.assertEqual(
			terms_service.mission_dto(draft.name)["resources_total"], 24 * 45000 + 4 * 180000
		)


class TestWithNoWorkflowTheAuthorisedSubmitDirectly(TermsTestCase):
	def test_the_doctype_is_not_governed_on_a_site_that_configured_nothing(self):
		self.assertFalse(terms_service.is_governed())

	def test_a_finished_document_submits_directly(self):
		draft = self.bare_terms(**self.complete_payload())

		self.assertTrue(terms_service.submit(draft.name)["is_submitted"])

	def test_submitting_one_already_submitted_is_harmless(self):
		draft = self.bare_terms(**self.complete_payload())
		terms_service.submit(draft.name)

		self.assertTrue(terms_service.submit(draft.name)["is_submitted"])

	def test_asking_for_approval_is_refused_rather_than_quietly_submitting(self):
		"""There is nobody to route to, and a submitted document with no approval
		recorded against it would say there was."""
		draft = self.bare_terms(**self.complete_payload())

		with self.assertRaises(frappe.ValidationError):
			terms_service.send_for_approval(draft.name)

	def test_a_submitted_document_cannot_be_edited(self):
		draft = self.bare_terms(**self.complete_payload())
		terms_service.submit(draft.name)

		with self.assertRaises(frappe.ValidationError):
			terms_service.update(draft.name, purpose="Something else entirely.")


class TestWithAWorkflowTheEngineIsTheOnlyDoor(TermsTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.grant_doctype_access(fixtures.TERMS_DOCTYPE, TERMS_APPROVER_ROLE)
		fixtures.make_workflow(
			fixtures.TERMS_DOCTYPE, TERMS_APPROVER_ROLE, geo_node_field="geo_scope"
		)

		# The person the region's terms route to. `default_scope()` anchors every
		# fixture mission at society A's region, so that is where they hold it.
		cls.approver = fixtures.make_user("terms_approver")
		fixtures.grant_scope(cls.approver, TERMS_APPROVER_ROLE, cls.society_a["region"])
		frappe.get_doc("User", cls.approver).add_roles(TERMS_APPROVER_ROLE)

	@classmethod
	def tearDownClass(cls):
		if frappe.db.exists("Role", TERMS_APPROVER_ROLE):
			frappe.delete_doc("Role", TERMS_APPROVER_ROLE, force=True)

		super().tearDownClass()

	def routed_draft(self):
		return self.bare_terms(**self.complete_payload())

	def test_the_doctype_meets_the_engines_contract(self):
		"""A workflow refuses a doctype that cannot carry an approval, so this
		passing is what makes every test below possible."""
		from vmmsx.approvals.services import contract

		contract.assert_approvable(fixtures.TERMS_DOCTYPE)

	def test_the_doctype_is_governed(self):
		self.assertTrue(terms_service.is_governed())

	def test_the_direct_door_is_closed(self):
		draft = self.routed_draft()

		with self.assertRaises(frappe.PermissionError):
			draft.submit()

	def test_and_it_is_closed_on_the_document_itself_not_only_in_the_service(self):
		"""The desk's own Submit button goes through the controller, not the API."""
		draft = self.routed_draft()

		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(fixtures.TERMS_DOCTYPE, draft.name).submit()

	def test_an_unfinished_draft_cannot_even_be_sent_for_approval(self):
		"""Routing an unfinished mission would put a half-written document in
		front of an approver and call it a decision."""
		draft = self.bare_terms()

		with self.assertRaises(frappe.MandatoryError):
			terms_service.send_for_approval(draft.name)

	def test_sending_it_puts_it_in_front_of_the_person_it_routed_to(self):
		draft = self.routed_draft()
		status = terms_service.send_for_approval(draft.name)

		self.assertEqual(status["state"], states.IN_REVIEW)
		self.assertEqual(engine.authorised(draft.reload())["approvers"], [self.approver])

	def test_it_is_still_a_draft_while_it_is_under_review(self):
		draft = self.routed_draft()
		terms_service.send_for_approval(draft.name)

		self.assertEqual(frappe.db.get_value(fixtures.TERMS_DOCTYPE, draft.name, "docstatus"), 0)

	def test_approval_freezes_the_wording_without_anybody_pressing_submit(self):
		"""The engine knows nothing about terms of reference. `try_freeze` is the seam."""
		draft = self.routed_draft()
		terms_service.send_for_approval(draft.name)

		frappe.set_user(self.approver)
		engine.decide(
			frappe.get_doc(fixtures.TERMS_DOCTYPE, draft.name), states.DECISION_APPROVED
		)
		frappe.set_user("Administrator")

		self.assertEqual(frappe.db.get_value(fixtures.TERMS_DOCTYPE, draft.name, "docstatus"), 1)
		self.assertEqual(
			frappe.db.get_value(fixtures.TERMS_DOCTYPE, draft.name, "approval_state"),
			states.APPROVED,
		)

	def test_a_rejected_mission_stays_a_draft(self):
		draft = self.routed_draft()
		terms_service.send_for_approval(draft.name)

		frappe.set_user(self.approver)
		engine.decide(
			frappe.get_doc(fixtures.TERMS_DOCTYPE, draft.name),
			states.DECISION_REJECTED,
			"The itinerary does not add up.",
		)
		frappe.set_user("Administrator")

		self.assertEqual(frappe.db.get_value(fixtures.TERMS_DOCTYPE, draft.name, "docstatus"), 0)

	def test_holding_the_role_somewhere_else_is_not_being_the_approver(self):
		"""The engine's person-gate, reached through terms of reference for the
		first time. Holding the role is not authorisation."""
		outsider = fixtures.make_user("terms_outsider")
		fixtures.grant_scope(outsider, TERMS_APPROVER_ROLE, self.society_b["region"])
		frappe.get_doc("User", outsider).add_roles(TERMS_APPROVER_ROLE)

		draft = self.routed_draft()
		terms_service.send_for_approval(draft.name)

		frappe.set_user(outsider)

		with self.assertRaises(frappe.PermissionError):
			engine.decide(
				frappe.get_doc(fixtures.TERMS_DOCTYPE, draft.name), states.DECISION_APPROVED
			)


class TestWhatIsAgreedStaysAgreed(TermsTestCase):
	def test_terms_nothing_points_at_can_be_cancelled(self):
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}")
		terms.cancel()

		self.assertEqual(terms.docstatus, 2)

	def test_terms_a_deployment_points_at_cannot(self):
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}")
		fixtures.make_deployment(terms.name, self.society_a["branch"])

		with self.assertRaises(frappe.ValidationError):
			terms.cancel()

	def test_superseding_leaves_the_original_exactly_as_it_is(self):
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}")
		fixtures.make_deployment(terms.name, self.society_a["branch"])

		terms_service.supersede(terms.name)
		terms.reload()

		self.assertEqual(terms.docstatus, 1)
		self.assertTrue(terms.is_active)

	def test_the_replacement_carries_the_mission_across_and_links_back(self):
		terms = fixtures.make_terms(
			f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}",
			purpose="The original purpose.",
		)

		replacement = terms_service.supersede(terms.name)

		self.assertEqual(replacement["supersedes"], terms.name)
		self.assertEqual(replacement["purpose"], "The original purpose.")
		self.assertEqual(replacement["project"], terms.project)
		self.assertEqual(len(replacement["objectives"]), len(terms.objectives))

	def test_the_replacement_starts_as_a_draft(self):
		"""It is a new mission document, and nobody has agreed to it yet."""
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}")

		self.assertTrue(terms_service.supersede(terms.name)["is_draft"])

	def test_a_respecification_can_change_something_on_the_way_through(self):
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}")

		replacement = terms_service.supersede(terms.name, purpose="The revised purpose.")

		self.assertEqual(replacement["purpose"], "The revised purpose.")

	def test_a_draft_cannot_be_superseded_because_it_can_simply_be_edited(self):
		draft = self.bare_terms(**self.complete_payload())

		with self.assertRaises(frappe.ValidationError):
			terms_service.supersede(draft.name)

	def test_the_deployments_already_run_keep_pointing_at_the_original(self):
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}")
		deployment = fixtures.make_deployment(terms.name, self.society_a["branch"])

		terms_service.supersede(terms.name)

		self.assertEqual(
			frappe.db.get_value(fixtures.DEPLOYMENT_DOCTYPE, deployment.name, "terms_of_reference"),
			terms.name,
		)


class TestANewProgrammeCannotBeAClosedOne(TermsTestCase):
	def test_terms_cannot_be_written_under_a_completed_programme(self):
		from vmmsx.deployment.services import project as project_service

		project = project_service.create(
			project_name=f"{fixtures.TEST_PREFIX} {frappe.generate_hash(length=8)}",
			geo_node=self.society_a["branch"],
		)
		project_service.set_status(project, project_service.STATUS_COMPLETED)

		with self.assertRaises(frappe.ValidationError):
			self.bare_terms(**self.complete_payload(project=project.name))

	def test_but_a_draft_already_written_under_one_can_still_be_saved(self):
		"""Somebody closed the programme while a specification under it was half
		written. A rule that fired on every save would make that draft unfixable."""
		from vmmsx.deployment.services import project as project_service

		project = project_service.create(
			project_name=f"{fixtures.TEST_PREFIX} {frappe.generate_hash(length=8)}",
			geo_node=self.society_a["branch"],
		)
		draft = self.bare_terms(**self.complete_payload(project=project.name))
		project_service.set_status(project, project_service.STATUS_COMPLETED)

		draft.purpose = "Rewritten after the programme closed."
		draft.save()

		self.assertTrue(draft.name)
