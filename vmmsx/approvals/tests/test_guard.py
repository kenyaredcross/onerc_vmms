# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Only the engine moves an application, and deciding needs no edit rights.

Two halves of one rule. `approvals/services/guard.py` refuses a save that
changes the engine's fields unless the engine is making it, so a person with
write permission cannot set `approval_state` to Approved through the REST API.
And `engine.decide` saves a decision it has already authorised without asking
again whether the approver may *edit* the record, so an approver whose role only
reads applications can still decide the ones routed to them.

The stand-in doctype is created at test time and is not in `hooks.py`, so the
guard is attached to it for the duration of each test exactly as `doc_events`
attaches it to the real ones. `test_every_governed_doctype_is_guarded` holds
the real registration.
"""

import frappe
from frappe.client import set_value
from frappe.permissions import add_permission

from vmmsx.api import approvals
from vmmsx.approvals import states
from vmmsx.approvals.services import contract, engine
from vmmsx.approvals.tests import fixtures
from vmmsx.approvals.tests.base import ApprovalTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

GUARD = "vmmsx.approvals.services.guard.validate"
READER_ROLE = f"{fixtures.TEST_PREFIX} Reading Approver"

# Every doctype this app governs through the engine. The service certificate
# request carries the same rule in its own controller.
GUARDED = (
	"VMMS Volunteer Application",
	"VMMS Membership",
	"VMMS Deployment Request",
	"VMMS Terms of Reference",
	"VMMS Branch Transfer",
)


class TestEngineOwnsTheState(ApprovalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county = fixtures.make_user("guard_county", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])
		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)]
		)

	def setUp(self):
		super().setUp()
		hooks = frappe.get_doc_hooks()
		hooks.setdefault(fixtures.APPROVABLE_DOCTYPE, {}).setdefault("validate", []).append(GUARD)
		self.addCleanup(self._detach_guard)

	def _detach_guard(self):
		hooks = frappe.get_doc_hooks().get(fixtures.APPROVABLE_DOCTYPE, {})
		if GUARD in hooks.get("validate", []):
			hooks["validate"].remove(GUARD)

	def in_review(self, title: str) -> str:
		name = self.application(title, self.kenya["kihara"])
		engine.submit(self.reload(name))
		self.assertEqual(self.state(name), states.IN_REVIEW)
		return name

	# --- the bypass is closed ---------------------------------------------

	def test_writer_cannot_set_the_state_directly(self):
		name = self.in_review("direct state")

		with fixtures.acting_as(self.county), self.assertRaises(frappe.PermissionError):
			set_value(fixtures.APPROVABLE_DOCTYPE, name, "approval_state", states.APPROVED)

		self.assertEqual(self.state(name), states.IN_REVIEW)

	def test_system_manager_cannot_set_the_state_directly(self):
		name = self.in_review("administrator state")

		with self.assertRaises(frappe.PermissionError):
			set_value(fixtures.APPROVABLE_DOCTYPE, name, "approval_state", states.APPROVED)

	def test_stage_and_clock_are_protected_too(self):
		name = self.in_review("stage")

		with fixtures.acting_as(self.county), self.assertRaises(frappe.PermissionError):
			set_value(fixtures.APPROVABLE_DOCTYPE, name, "approval_stage", "")

	def test_a_decision_row_cannot_be_typed_in(self):
		name = self.in_review("forged decision")
		doc = self.reload(name)
		doc.append(
			contract.decisions_field(doc.doctype),
			{"approver": self.county, "decision": states.DECISION_APPROVED, "stage": doc.approval_stage},
		)

		with self.assertRaises(frappe.PermissionError):
			doc.save()

	def test_a_new_record_cannot_arrive_approved(self):
		doc = frappe.get_doc(
			{
				"doctype": fixtures.APPROVABLE_DOCTYPE,
				"title": f"{fixtures.TEST_PREFIX} born approved",
				fixtures.GEO_FIELD: self.kenya["kihara"],
				"approval_state": states.APPROVED,
			}
		)

		with self.assertRaises(frappe.PermissionError):
			doc.insert()

	# --- what still works ---------------------------------------------------

	def test_an_ordinary_edit_is_untouched(self):
		name = self.in_review("ordinary edit")

		with fixtures.acting_as(self.county):
			set_value(fixtures.APPROVABLE_DOCTYPE, name, "title", f"{fixtures.TEST_PREFIX} renamed")

		self.assertEqual(self.state(name), states.IN_REVIEW)

	def test_the_engine_still_decides(self):
		name = self.in_review("engine decides")

		with fixtures.acting_as(self.county):
			approvals.decide(fixtures.APPROVABLE_DOCTYPE, name, states.DECISION_APPROVED)

		self.assertEqual(self.state(name), states.APPROVED)

	def test_application_code_saving_without_permission_checks_is_left_alone(self):
		"""An import or a migration loader inserts history on purpose."""
		doc = frappe.get_doc(
			{
				"doctype": fixtures.APPROVABLE_DOCTYPE,
				"title": f"{fixtures.TEST_PREFIX} imported",
				fixtures.GEO_FIELD: self.kenya["kihara"],
				"approval_state": states.APPROVED,
			}
		).insert(ignore_permissions=True)

		self.assertEqual(self.state(doc.name), states.APPROVED)

	# --- registration -------------------------------------------------------

	def test_every_governed_doctype_is_guarded(self):
		events = frappe.get_hooks("doc_events")

		for doctype in GUARDED:
			with self.subTest(doctype=doctype):
				self.assertTrue(contract.meets(doctype), doctype)
				self.assertIn(GUARD, events.get(doctype, {}).get("validate", []))


class TestDecidingNeedsNoEditRights(ApprovalTestCase):
	"""A County Coordinator whose role only reads applications can still decide them."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_role(READER_ROLE)
		add_permission(fixtures.APPROVABLE_DOCTYPE, READER_ROLE, 0, "read")

		cls.reader = fixtures.make_user("guard_reader", [READER_ROLE])
		cls.elsewhere = fixtures.make_user("guard_reader_elsewhere", [READER_ROLE])
		fixtures.make_assignment(cls.reader, READER_ROLE, cls.kenya["kiambu"])
		fixtures.make_assignment(cls.elsewhere, READER_ROLE, cls.kenya["nakuru"])
		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, READER_ROLE, resolution_rule="at_level",
				geo_level=cls.kenya["levels"]["county"], completion_rule="any_of")]
		)

	def test_the_role_really_is_read_only(self):
		name = self.application("read only", self.kenya["kihara"])

		self.assertTrue(frappe.has_permission(fixtures.APPROVABLE_DOCTYPE, "read", name, user=self.reader))
		self.assertFalse(frappe.has_permission(fixtures.APPROVABLE_DOCTYPE, "write", name, user=self.reader))

	def test_routed_reader_approves(self):
		name = self.application("reader approves", self.kenya["kihara"])
		engine.submit(self.reload(name))

		with fixtures.acting_as(self.reader):
			approvals.decide(fixtures.APPROVABLE_DOCTYPE, name, states.DECISION_APPROVED)

		self.assertEqual(self.state(name), states.APPROVED)

	def test_routed_reader_requests_more_information(self):
		name = self.application("reader returns", self.kenya["kihara"])
		engine.submit(self.reload(name))

		with fixtures.acting_as(self.reader):
			approvals.decide(
				fixtures.APPROVABLE_DOCTYPE, name, states.DECISION_MORE_INFO, reason="Add your ID copy"
			)

		self.assertEqual(self.state(name), states.DRAFT)

	def test_reading_is_not_deciding(self):
		"""The other county's holder can read the doctype but was not routed this one."""
		name = self.application("not yours", self.kenya["kihara"])
		engine.submit(self.reload(name))

		with fixtures.acting_as(self.elsewhere), self.assertRaises(frappe.PermissionError):
			approvals.decide(fixtures.APPROVABLE_DOCTYPE, name, states.DECISION_APPROVED)

		self.assertEqual(self.state(name), states.IN_REVIEW)

	def test_reader_still_cannot_edit(self):
		name = self.application("no edit", self.kenya["kihara"])

		with fixtures.acting_as(self.reader), self.assertRaises(frappe.PermissionError):
			set_value(fixtures.APPROVABLE_DOCTYPE, name, "title", "changed")
