# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Shared arrangement for the Stipend module's integration tests.

Frappe rolls the test transaction back once per class, not per method, so
authority — users, roles and Geo Assignments — is arranged in `setUpClass`. A
method that granted somebody a role would still have granted it for the next
method, and the test that then passed would be lying.

Each method makes its own report or payment form. They are cheap, and one per
test is what keeps a lifecycle test from inheriting state another one left
behind.

The three scope roles are configured here so that suites which are about the
grid, the pairing or the stub fail or pass on the thing they are actually
testing. The picker's own scope guarantee is tested in `test_picker.py`, which
arranges its own users and clears these settings where it needs to.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.stipend.tests import fixtures

EXTRA_TEST_RECORD_DEPENDENCIES = []


class StipendTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.reset()

		cls.society_a = fixtures.build_society_a()
		cls.society_b = fixtures.build_society_b()

		fixtures.set_volunteer_scope_role(fixtures.VOLUNTEER_SCOPE_ROLE)
		fixtures.set_report_scope_role(fixtures.REPORT_SCOPE_ROLE)
		fixtures.set_payment_scope_role(fixtures.PAYMENT_SCOPE_ROLE)

		# The picker asks two questions: a Frappe role for *what* and geo for
		# *where*. The shipped doctypes grant only System Manager, because which
		# society role reads the volunteer register is configuration, so the tests
		# grant it the way an administrator would.
		fixtures.grant_doctype_access(fixtures.VOLUNTEER_DOCTYPE, fixtures.VOLUNTEER_SCOPE_ROLE)
		fixtures.grant_doctype_access(fixtures.REPORT_DOCTYPE, fixtures.REPORT_SCOPE_ROLE)
		fixtures.grant_doctype_access(fixtures.PAYMENT_DOCTYPE, fixtures.PAYMENT_SCOPE_ROLE)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		fixtures.teardown()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")

	# --- people -----------------------------------------------------------

	@classmethod
	def supervisor(cls, handle: str, *nodes: str) -> str:
		"""Somebody who may see volunteers at these nodes and nowhere else.

		The user the picker is built for. Note what they are *not* given: a report
		or payment scope role. Being able to find a volunteer and being able to
		open a payment form are different grants, and a supervisor who held both
		would let a picker test pass for the wrong reason.
		"""
		user = fixtures.make_user(handle)
		fixtures.grant_scope(user, fixtures.VOLUNTEER_SCOPE_ROLE, *nodes)

		return user

	@classmethod
	def viewer(cls, handle: str, role: str, *nodes: str) -> str:
		"""Somebody who may see one kind of record at these nodes."""
		user = fixtures.make_user(handle)
		fixtures.grant_scope(user, role, *nodes)

		return user

	def volunteer_at(self, node: str, first_name: str = "Ada", last_name: str | None = None):
		"""A volunteer placed at a node, with an identity of their own.

		The surname is generated unless a test names one, so two volunteers made by
		the same test are two people rather than one profile reused.
		"""
		profile = fixtures.make_profile(first_name, last_name or f"Case{frappe.generate_hash(length=4)}")

		return fixtures.make_volunteer(profile, node)

	# --- helpers ----------------------------------------------------------

	def reload_report(self, name: str):
		return frappe.get_doc(fixtures.REPORT_DOCTYPE, name)

	def reload_form(self, name: str):
		return frappe.get_doc(fixtures.PAYMENT_DOCTYPE, name)

	def approval_state(self, doctype: str, name: str) -> str:
		return frappe.db.get_value(doctype, name, "approval_state")

	def candidate_names(self, result: dict) -> list[str]:
		return [row["volunteer"] for row in result["candidates"]]

	def email_of(self, volunteer) -> str:
		return frappe.db.get_value("Red Profile", volunteer.red_profile, "email")
