# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Shared arrangement for the Deployment module's integration tests.

Frappe rolls the test transaction back once per class, not per method, so
authority — users, roles and Geo Assignments — is arranged in `setUpClass`. A
method that granted somebody a role would still have granted it for the next
method, and the test that then passed would be lying.

Each method makes its own deployment, request or transfer. They are cheap, and
one per test is what keeps a lifecycle test from inheriting state another one
left behind.

The four scope roles are configured here so that suites which are about
ownership, matching criteria or approval fail or pass on the thing they are
actually testing. Scoping itself is tested in `test_scoping.py`, which arranges
its own users and clears these settings where it needs to.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.deployment.tests import fixtures

EXTRA_TEST_RECORD_DEPENDENCIES = []


class DeploymentTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.reset()

		cls.society_a = fixtures.build_society_a()
		cls.society_b = fixtures.build_society_b()

		fixtures.set_volunteer_scope_role(fixtures.VOLUNTEER_SCOPE_ROLE)
		fixtures.set_deployment_scope_role(fixtures.DEPLOYMENT_SCOPE_ROLE)
		fixtures.set_request_scope_role(fixtures.REQUEST_SCOPE_ROLE)
		fixtures.set_transfer_scope_role(fixtures.TRANSFER_SCOPE_ROLE)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		fixtures.teardown()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")

	# --- users ------------------------------------------------------------

	@classmethod
	def searcher(cls, handle: str, *nodes: str) -> str:
		"""Somebody who may see volunteers at these nodes and nowhere else.

		The user matching is built for. Note what they are *not* given: a
		deployment or transfer scope role. Being able to find a volunteer and
		being able to open a deployment are different grants, and a searcher who
		held both would let a matching test pass for the wrong reason.
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

	# --- helpers ----------------------------------------------------------

	def reload_transfer(self, name: str):
		return frappe.get_doc(fixtures.TRANSFER_DOCTYPE, name)

	def reload_request(self, name: str):
		return frappe.get_doc(fixtures.REQUEST_DOCTYPE, name)

	def home_of(self, volunteer: str) -> str:
		return frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, volunteer, "home_geo_node")

	def anchor_of(self, doctype: str, name: str, field: str = "geo_node") -> str:
		return frappe.db.get_value(doctype, name, field)

	def approval_state(self, doctype: str, name: str) -> str:
		return frappe.db.get_value(doctype, name, "approval_state")

	def candidate_names(self, result: dict) -> list[str]:
		return [row["volunteer"] for row in result["candidates"]]
