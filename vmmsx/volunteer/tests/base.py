# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Shared arrangement for the Volunteer module's integration tests.

Frappe rolls the test transaction back once per class, not per method, so
authority — users, roles and Geo Assignments — is arranged in `setUpClass`. A
method that granted somebody a role would still have granted it for the next
method, and the test that then passed would be lying.

Each method makes its own application or volunteer. They are cheap, and one per
test is what keeps a lifecycle test from inheriting state another one left
behind.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.volunteer.tests import fixtures

EXTRA_TEST_RECORD_DEPENDENCIES = []


class VolunteerTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.reset()

		cls.society_a = fixtures.build_society_a()
		cls.society_b = fixtures.build_society_b()

		# VMMS Volunteer is registered as geo-scopeable, so reading one depends
		# on the society having chosen a scope role. Most of these suites are
		# about approval, certification and the seams rather than about scoping,
		# so the role is configured here and `scoped_user` grants it — leaving
		# each test to fail or pass on the thing it is actually testing.
		#
		# Scoping itself is tested in test_scoping.py, which arranges its own
		# users and clears this setting where it needs to.
		fixtures.set_scope_role(fixtures.SCOPE_ROLE)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		fixtures.teardown()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")

	@classmethod
	def scoped_user(cls, handle: str, roles: list[str] | None = None) -> str:
		"""A user who can *see* volunteers anywhere in both test societies.

		Whether they may *decide* an application is a different question,
		answered by the approval engine's person-gate — which is the point.
		Without the scope grant, a test asserting that the wrong person is
		refused would pass because geo scoping stopped them at the door, and the
		person-gate would never be exercised at all.
		"""
		user = fixtures.make_user(handle, roles)
		fixtures.grant_volunteer_scope(user, cls.society_a["region"], cls.society_b["region"])

		return user

	# --- helpers ----------------------------------------------------------

	def reload_application(self, name: str):
		return frappe.get_doc(fixtures.APPLICATION_DOCTYPE, name)

	def approval_state(self, name: str) -> str:
		return frappe.db.get_value(fixtures.APPLICATION_DOCTYPE, name, "approval_state")

	def volunteer_of(self, application: str) -> str | None:
		return frappe.db.get_value(fixtures.APPLICATION_DOCTYPE, application, "volunteer")

	def volunteer_status(self, volunteer: str) -> str:
		return frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, volunteer, "status")

	def decision_count(self, application: str) -> int:
		return frappe.db.count(
			"VMMS Approval Decision",
			{"parent": application, "parenttype": fixtures.APPLICATION_DOCTYPE},
		)

	def queue_of(self, user: str) -> set[str]:
		"""Applications sitting in this user's desk queue."""
		return set(
			frappe.get_all(
				"ToDo",
				filters={
					"allocated_to": user,
					"reference_type": fixtures.APPLICATION_DOCTYPE,
					"status": ("in", ("Open", "Overdue")),
				},
				pluck="reference_name",
			)
		)

	def visible_affiliations(self, profile: str) -> list[dict]:
		"""The affiliation index through core's supported read path.

		`read_gate.get_affiliations()` is what core says code must use — a direct
		child-table query bypasses the gate by design. The removal tests read
		through it so that what they observe is what a caller would observe.

		The document cache is dropped first: `rebuild_affiliations` edits the
		profile, and a stale cached copy would show rows that are already gone —
		which is precisely the failure the test is trying to detect.
		"""
		from onerc_core.identity.services.read_gate import get_affiliations

		frappe.clear_document_cache("Red Profile", profile)

		return get_affiliations(profile)

	def affiliation_rows(self, profile: str) -> list[dict]:
		"""Core's derived index for a profile.

		Read here **only to assert that it was written**. No production code in
		vmmsx reads this table to decide anything, and a test that used it to
		determine whether somebody volunteers would be testing the wrong thing.
		"""
		frappe.clear_document_cache("Red Profile", profile)

		return frappe.get_all(
			"Red Profile Affiliation",
			filters={"parent": profile, "parenttype": "Red Profile"},
			fields=["affiliation_type", "status", "reference_doctype", "reference_name"],
		)

	def affiliation_types(self, profile: str) -> set[str]:
		return {row["affiliation_type"] for row in self.affiliation_rows(profile)}
