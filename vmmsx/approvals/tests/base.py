# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Shared arrangement for the engine's integration tests.

Frappe rolls the test transaction back **once per class**, not per method, so
authority — users and Geo Assignments — is arranged in `setUpClass` and never
inside a test. A method that granted somebody a role would still have granted it
for the next method, and the test that then passed would be lying.

Each method makes its own application instead. Applications are cheap, and one
document per test is what keeps a lifecycle test from inheriting the state
another one left behind.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.approvals.tests import fixtures

EXTRA_TEST_RECORD_DEPENDENCIES = []


class ApprovalTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# DDL, and it commits — so it happens before anything that must roll back.
		fixtures.ensure_approvable_doctype()
		fixtures.reset()

		cls.kenya = fixtures.build_kenya()
		cls.gambia = fixtures.build_gambia()

	@classmethod
	def tearDownClass(cls):
		# Roll the fixture data back before dropping the doctype, so the drop is
		# not fighting rows that are about to disappear anyway.
		frappe.db.rollback()
		fixtures.teardown()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")

	# --- helpers every lifecycle test needs --------------------------------

	def application(self, title: str, node: str, **kwargs) -> str:
		return fixtures.make_application(title, node, **kwargs)

	def reload(self, name: str):
		return fixtures.load(name)

	def state(self, name: str) -> str:
		return frappe.db.get_value(fixtures.APPROVABLE_DOCTYPE, name, "approval_state")

	def queue_of(self, user: str) -> set[str]:
		"""Applications sitting in this user's desk queue."""
		return set(
			frappe.get_all(
				"ToDo",
				filters={
					"allocated_to": user,
					"reference_type": fixtures.APPROVABLE_DOCTYPE,
					"status": ("in", ("Open", "Overdue")),
				},
				pluck="reference_name",
			)
		)
