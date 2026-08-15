# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The approval stub: submittable, visibly stuck, and refusing to lie about it.

Stipend approval runs from the supervisor to the head of the volunteer's
**department**. The approval engine resolves approvers by walking **up the geo
tree**, and a head of department is not up the geo tree from a volunteer, so
wiring one to the other would route every report confidently to the wrong person.
A wrong approver who approves is worse than no approver: the paperwork comes back
signed and nothing records that whoever signed it had no standing to.

So the feature is present and the routing is explicitly absent. What is asserted:

1. **Submission works.** The paperwork really is submitted, really is frozen, and
   really records who submitted it and when.
2. **It lands in a dead end.** `Pending Departmental Approval`, and there is no
   state after it, because the only two moves out are approval and rejection.
3. **Nobody can approve it, including Administrator.** The refusal is asserted to
   carry the message that says why, so a stub that quietly started succeeding
   fails here.
4. **It is not wired to the geo engine, and cannot be by configuration.** No
   workflow governs either doctype, and neither satisfies the engine's document
   contract, so one cannot be pointed at them.
5. **The routing target is recorded.** The volunteer's department, captured for
   the subsystem that will eventually resolve a head of department, and degrading
   to nothing on a site that has no HR app.
"""

import frappe

from vmmsx.api import stipend as stipend_api
from vmmsx.approvals.services import config as approvals_config
from vmmsx.approvals.services import contract
from vmmsx.stipend.services import approval, department
from vmmsx.stipend.services import payment as payment_service
from vmmsx.stipend.services import report as report_service
from vmmsx.stipend.tests import fixtures
from vmmsx.stipend.tests.base import StipendTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class StubTestCase(StipendTestCase):
	def setUp(self):
		super().setUp()
		self.node = self.society_a["ward"]
		self.person = self.volunteer_at(self.node, "Stub", "Subject")
		self.report = fixtures.make_report(self.node, [self.person.name])
		self.form = fixtures.make_payment_form(
			self.report.name,
			self.node,
			[fixtures.line(self.person.name, self.report.period_from, amount=300)],
		)


class TestSubmissionLandsInADeadEnd(StubTestCase):
	def test_a_report_starts_as_a_draft(self):
		self.assertEqual(approval.state(self.report), approval.DRAFT)

	def test_submitting_a_report_moves_it_to_pending_departmental_approval(self):
		report_service.submit(self.report)

		self.assertEqual(
			self.approval_state(fixtures.REPORT_DOCTYPE, self.report.name),
			approval.PENDING_DEPARTMENTAL,
		)

	def test_submitting_a_payment_form_does_the_same(self):
		payment_service.submit(self.form)

		self.assertEqual(
			self.approval_state(fixtures.PAYMENT_DOCTYPE, self.form.name),
			approval.PENDING_DEPARTMENTAL,
		)

	def test_submission_records_who_and_when(self):
		"""Both ends of the supervisor to head of department chain, minus the head."""
		report_service.submit(self.report)
		stored = self.reload_report(self.report.name)

		self.assertTrue(stored.submitted_on)
		self.assertEqual(stored.submitted_by, frappe.session.user)

	def test_submitting_twice_changes_nothing_the_second_time(self):
		first = report_service.submit(self.report)
		second = report_service.submit(self.report)

		self.assertEqual(first["submitted_on"], second["submitted_on"])

	def test_there_is_no_state_after_pending(self):
		"""The two moves that would end this lifecycle do not exist, so nor do they."""
		self.assertEqual(approval.TRANSITIONS[approval.PENDING_DEPARTMENTAL], (approval.DRAFT,))

	def test_the_select_offers_no_state_nobody_can_reach(self):
		"""An Approved value nobody can get to would be a lie in a Select."""
		for doctype in (fixtures.REPORT_DOCTYPE, fixtures.PAYMENT_DOCTYPE):
			options = frappe.get_meta(doctype).get_field("approval_state").options.split("\n")

			self.assertEqual(options, [approval.DRAFT, approval.PENDING_DEPARTMENTAL], doctype)

	def test_the_state_field_is_read_only(self):
		for doctype in (fixtures.REPORT_DOCTYPE, fixtures.PAYMENT_DOCTYPE):
			self.assertTrue(frappe.get_meta(doctype).get_field("approval_state").read_only, doctype)


class TestNobodyCanApproveIt(StubTestCase):
	"""The heart of the stub. Every route to a decision is refused, out loud."""

	def test_deciding_a_report_is_refused(self):
		report_service.submit(self.report)

		with self.assertRaises(frappe.ValidationError):
			approval.decide(self.reload_report(self.report.name), "Approved")

	def test_the_refusal_carries_the_message_that_says_why(self):
		report_service.submit(self.report)

		with self.assertRaises(frappe.ValidationError) as caught:
			approval.decide(self.reload_report(self.report.name), "Approved")

		self.assertIn(approval.PENDING_ROUTING_REFUSAL, str(caught.exception))

	def test_the_message_names_the_department_chain_and_the_engine_it_is_not_using(self):
		"""A stub whose message drifted into vagueness is a stub nobody understands."""
		self.assertIn("department", approval.PENDING_ROUTING_REFUSAL.lower())
		self.assertIn("geo", approval.PENDING_ROUTING_REFUSAL.lower())

	def test_administrator_is_refused_too(self):
		"""What is missing is not permission. It is the answer to who."""
		report_service.submit(self.report)

		self.assertEqual(frappe.session.user, "Administrator")

		with self.assertRaises(frappe.ValidationError) as caught:
			stipend_api.decide(fixtures.REPORT_DOCTYPE, self.report.name, "Approved")

		self.assertIn(approval.PENDING_ROUTING_REFUSAL, str(caught.exception))

	def test_a_payment_form_is_refused_the_same_way(self):
		payment_service.submit(self.form)

		with self.assertRaises(frappe.ValidationError) as caught:
			stipend_api.decide(fixtures.PAYMENT_DOCTYPE, self.form.name, "Approved")

		self.assertIn(approval.PENDING_ROUTING_REFUSAL, str(caught.exception))

	def test_rejecting_is_refused_as_well_as_approving(self):
		"""Both directions are decisions, and neither has anybody to take it."""
		report_service.submit(self.report)

		with self.assertRaises(frappe.ValidationError):
			stipend_api.decide(fixtures.REPORT_DOCTYPE, self.report.name, "Rejected")

	def test_deciding_a_draft_is_refused_for_the_same_reason(self):
		"""The refusal is about routing, not about which state it is in."""
		with self.assertRaises(frappe.ValidationError) as caught:
			approval.decide(self.report, "Approved")

		self.assertIn(approval.PENDING_ROUTING_REFUSAL, str(caught.exception))

	def test_the_state_survives_the_attempt(self):
		report_service.submit(self.report)

		with self.assertRaises(frappe.ValidationError):
			stipend_api.decide(fixtures.REPORT_DOCTYPE, self.report.name, "Approved")

		self.assertEqual(
			self.approval_state(fixtures.REPORT_DOCTYPE, self.report.name),
			approval.PENDING_DEPARTMENTAL,
		)

	def test_the_status_dto_says_plainly_that_it_cannot_be_decided(self):
		report_service.submit(self.report)
		status = approval.status(self.reload_report(self.report.name))

		self.assertFalse(status["can_be_decided"])
		self.assertTrue(status["is_pending"])
		self.assertEqual(status["blocked_because"], approval.PENDING_ROUTING_REFUSAL)


class TestItIsNotWiredToTheGeoEngine(StubTestCase):
	"""And cannot be wired to it by configuration alone."""

	def test_no_approval_workflow_governs_either_doctype(self):
		for doctype in (fixtures.REPORT_DOCTYPE, fixtures.PAYMENT_DOCTYPE):
			self.assertFalse(approvals_config.is_approvable(doctype), doctype)

	def test_neither_doctype_satisfies_the_engines_contract(self):
		"""So a workflow cannot be pointed at one: the engine refuses it on save."""
		for doctype in (fixtures.REPORT_DOCTYPE, fixtures.PAYMENT_DOCTYPE):
			with self.assertRaises(frappe.MandatoryError, msg=doctype):
				contract.assert_approvable(doctype)

	def test_neither_doctype_carries_the_engines_fields(self):
		for doctype in (fixtures.REPORT_DOCTYPE, fixtures.PAYMENT_DOCTYPE):
			meta = frappe.get_meta(doctype)

			self.assertIsNone(meta.get_field(contract.STAGE_FIELD), doctype)
			self.assertIsNone(meta.get_field(contract.STAGE_ENTERED_FIELD), doctype)
			self.assertEqual(
				[field for field in meta.get_table_fields() if field.options == contract.DECISION_DOCTYPE],
				[],
				doctype,
			)

	def test_the_generic_approval_endpoint_refuses_these_doctypes(self):
		"""One door, and it is not that one: that endpoint is the geo engine's."""
		from vmmsx.api import approvals as approvals_api

		report_service.submit(self.report)

		with self.assertRaises(frappe.ValidationError):
			approvals_api.get_status(fixtures.REPORT_DOCTYPE, self.report.name)

	def test_the_stipend_endpoint_refuses_a_doctype_that_is_not_stipend_paperwork(self):
		with self.assertRaises(frappe.ValidationError):
			stipend_api.get_approval_status(fixtures.VOLUNTEER_DOCTYPE, self.person.name)


class TestWithdrawingAndFreezing(StubTestCase):
	"""The one move out, and what submission actually protects."""

	def test_withdrawing_returns_it_to_draft(self):
		report_service.submit(self.report)
		report_service.withdraw(self.reload_report(self.report.name))

		self.assertEqual(self.approval_state(fixtures.REPORT_DOCTYPE, self.report.name), approval.DRAFT)

	def test_withdrawing_clears_the_submission_stamps(self):
		report_service.submit(self.report)
		report_service.withdraw(self.reload_report(self.report.name))
		stored = self.reload_report(self.report.name)

		self.assertIsNone(stored.submitted_on)
		self.assertIsNone(stored.submitted_by)

	def test_withdrawing_something_that_is_already_a_draft_changes_nothing(self):
		self.assertFalse(report_service.withdraw(self.report)["is_pending"])

	def test_a_submitted_report_cannot_have_its_people_changed(self):
		report_service.submit(self.report)
		stored = self.reload_report(self.report.name)

		with self.assertRaises(frappe.ValidationError):
			report_service.add_volunteer(stored, self.volunteer_at(self.node, "Late", "Arrival").name)

	def test_a_submitted_report_frozen_at_the_document_too(self):
		"""Not only through the service: an edit that arrived any other way is refused."""
		report_service.submit(self.report)
		stored = self.reload_report(self.report.name)
		stored.append("volunteers", {"volunteer": self.volunteer_at(self.node, "Side", "Door").name})

		with self.assertRaises(frappe.ValidationError):
			stored.save()

	def test_a_submitted_payment_form_cannot_have_its_grid_changed(self):
		payment_service.submit(self.form)
		stored = self.reload_form(self.form.name)
		stored.attendance[0].stipend_amount = 9000

		with self.assertRaises(frappe.ValidationError):
			stored.save()

	def test_withdrawing_makes_it_editable_again(self):
		report_service.submit(self.report)
		report_service.withdraw(self.reload_report(self.report.name))
		stored = self.reload_report(self.report.name)

		self.assertTrue(
			report_service.add_volunteer(stored, self.volunteer_at(self.node, "After", "Withdrawal").name)
		)
		stored.save()

	def test_the_state_cannot_be_set_by_hand(self):
		"""Setting it would skip what a move checks first."""
		self.report.approval_state = approval.PENDING_DEPARTMENTAL

		with self.assertRaises(frappe.ValidationError):
			self.report.save()

	def test_an_empty_report_cannot_reach_pending_by_setting_the_field(self):
		empty = fixtures.make_report(self.node)
		empty.approval_state = approval.PENDING_DEPARTMENTAL

		with self.assertRaises(frappe.ValidationError):
			empty.save()


class TestTheRoutingTargetIsRecorded(StubTestCase):
	"""Recorded for the subsystem that will route, and routed on by nothing."""

	def test_a_volunteer_with_no_employment_record_has_no_department(self):
		self.assertIsNone(department.of(self.person.name))

	def test_a_report_whose_people_have_no_department_still_files(self):
		"""Degrading to nothing is ordinary, not an error."""
		stored = self.reload_report(self.report.name)

		self.assertFalse(stored.routing_departments)
		self.assertTrue(report_service.submit(stored)["is_pending"])

	def test_the_description_says_so_rather_than_returning_a_bare_empty_list(self):
		answer = department.describe(self.reload_report(self.report.name))

		self.assertEqual(answer["departments"], [])
		self.assertEqual(answer["note"], department.NO_TARGET)
		self.assertEqual(answer["volunteers_without_a_department"], [self.person.name])

	def test_the_dto_never_claims_to_route(self):
		self.assertFalse(department.describe(self.reload_report(self.report.name))["routes_today"])

	def test_the_chain_is_stated_so_the_next_stage_inherits_it(self):
		self.assertIn("department", department.describe(self.report)["chain"])

	def test_the_field_is_derived_and_read_only(self):
		field = frappe.get_meta(fixtures.REPORT_DOCTYPE).get_field("routing_departments")

		self.assertTrue(field.read_only)

	def test_capture_re_derives_rather_than_topping_up(self):
		"""A stale value is blanked, not left behind.

		Written directly to the row and to the parent, which is what a value left
		over from an earlier save looks like, and then the report is saved. Both are
		gone afterwards, because `capture` recomputes the whole answer every time
		rather than filling in what is missing. This is the half of the capture path
		that can be tested on a site with no HR records at all.
		"""
		stored = self.reload_report(self.report.name)
		frappe.db.set_value(
			fixtures.REPORT_VOLUNTEER_DOCTYPE,
			stored.volunteers[0].name,
			"department",
			"a department that has since gone",
			update_modified=False,
		)
		frappe.db.set_value(
			fixtures.REPORT_DOCTYPE,
			stored.name,
			"routing_departments",
			"a department that has since gone",
			update_modified=False,
		)

		reloaded = self.reload_report(self.report.name)
		reloaded.save()

		self.assertIsNone(reloaded.volunteers[0].department)
		self.assertFalse(reloaded.routing_departments)

	def test_a_department_is_captured_when_hr_holds_one(self):
		"""The one path that needs a real HR record, skipped where HR cannot hold one.

		The department is read from the site rather than named here: what a society
		calls its departments is its own business, and a test that typed one would
		be the first place in this app to contain a department name.
		"""
		employee, expected = self._employee_with_department()
		frappe.db.set_value(
			fixtures.VOLUNTEER_DOCTYPE, self.person.name, "employee", employee, update_modified=False
		)

		self.assertEqual(department.of(self.person.name), expected)

		stored = self.reload_report(self.report.name)
		stored.save()

		self.assertEqual(stored.volunteers[0].department, expected)
		self.assertEqual(stored.routing_departments, expected)
		self.assertEqual(department.describe(stored)["departments"], [expected])
		self.assertIsNone(department.describe(stored)["note"])

	def _employee_with_department(self) -> tuple[str, str]:
		"""An Employee HR already holds, in whichever department this site has."""
		company = frappe.db.get_value("Company", {}, "name")

		if not company:
			self.skipTest(
				"no Company on this site, so HR cannot hold an Employee record;"
				" complete ERPNext/HR setup to exercise the department capture path"
			)

		on_site = frappe.db.get_value("Department", {"company": company}, "name")

		if not on_site:
			self.skipTest("no Department on this site to capture as a routing target")

		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": f"{fixtures.TEST_PREFIX} Departmental",
				"company": company,
				"gender": frappe.db.get_value("Gender", {}, "name"),
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"status": "Active",
				"department": on_site,
			}
		).insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, "Employee", employee.name, force=True)

		return employee.name, on_site
