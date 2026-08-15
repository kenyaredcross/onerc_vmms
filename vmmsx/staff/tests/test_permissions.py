# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Doctype permissions behind the staff cluster: a shortcut a scope role can see
must be a shortcut it can open.

Kept close to `TestAnOptionalCoordinatorRole` in `staff/tests/test_workspaces.py`
— one throwaway role, one setting, asserted through the real `Custom DocPerm`
rows Frappe's own permission check reads, the same way that suite asserts
through the real `Has Role` rows the desk reads for workspace visibility.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.staff.services import permissions


class TestAScopeRoleGetsItsDoctypePermissions(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.role = "VMMSTEST Membership Permissions Coordinator"
		if not frappe.db.exists("Role", self.role):
			frappe.get_doc({"doctype": "Role", "role_name": self.role, "desk_access": 1}).insert(
				ignore_permissions=True
			)

	def tearDown(self):
		from vmmsx.staff.services.workspaces import MEMBERSHIP_SCOPE_ROLE_FIELD

		frappe.db.set_single_value("National Society Settings", MEMBERSHIP_SCOPE_ROLE_FIELD, None)
		super().tearDown()

	def test_a_configured_role_is_granted_read_write_create_on_its_doctypes(self):
		from vmmsx.staff.services.workspaces import MEMBERSHIP_SCOPE_ROLE_FIELD

		frappe.db.set_single_value("National Society Settings", MEMBERSHIP_SCOPE_ROLE_FIELD, self.role)
		result = permissions.install()

		self.assertIn(self.role, result)
		for doctype in ("VMMS Member", "VMMS Membership", "VMMS Membership Type", "VMMS Membership Benefit"):
			self.assertIn(doctype, result[self.role], doctype)

			row = frappe.get_all(
				"Custom DocPerm",
				filters={"parent": doctype, "role": self.role},
				fields=["read", "write", "create", "delete"],
			)[0]

			self.assertEqual((row["read"], row["write"], row["create"]), (1, 1, 1), doctype)
			self.assertEqual(row["delete"], 0, doctype)

	def test_an_unconfigured_role_grants_nothing(self):
		result = permissions.install()

		self.assertNotIn(self.role, result)

	def test_installing_twice_creates_no_duplicate_rows(self):
		from vmmsx.staff.services.workspaces import MEMBERSHIP_SCOPE_ROLE_FIELD

		frappe.db.set_single_value("National Society Settings", MEMBERSHIP_SCOPE_ROLE_FIELD, self.role)
		permissions.install()
		permissions.install()

		count = frappe.db.count("Custom DocPerm", {"parent": "VMMS Membership", "role": self.role})
		self.assertEqual(count, 1)


class TestVolunteerApplicationIsReadOnly(IntegrationTestCase):
	"""The one deliberate widening — see the module docstring. A scope role may
	browse the queue; only `engine.decide()`, through the resolved-approver
	gate, may act on one, and this grant has no power to change that."""

	def setUp(self):
		super().setUp()
		self.role = "VMMSTEST Volunteer Application Reader"
		if not frappe.db.exists("Role", self.role):
			frappe.get_doc({"doctype": "Role", "role_name": self.role, "desk_access": 1}).insert(
				ignore_permissions=True
			)

	def tearDown(self):
		from vmmsx.volunteer.services.society import SCOPE_ROLE_FIELD

		frappe.db.set_single_value("National Society Settings", SCOPE_ROLE_FIELD, None)
		super().tearDown()

	def test_the_volunteer_scope_role_reads_but_cannot_write_applications(self):
		from vmmsx.volunteer.services.society import SCOPE_ROLE_FIELD

		frappe.db.set_single_value("National Society Settings", SCOPE_ROLE_FIELD, self.role)
		permissions.install()

		row = frappe.get_all(
			"Custom DocPerm",
			filters={"parent": "VMMS Volunteer Application", "role": self.role},
			fields=["read", "write", "create", "delete"],
		)[0]

		self.assertEqual(row["read"], 1)
		self.assertEqual((row["write"], row["create"], row["delete"]), (0, 0, 0))


class TestASharedRoleAcrossTwoSettingsKeepsBothGrants(IntegrationTestCase):
	"""Two scope-role settings a society names the same role must not collide —
	see the module docstring on why `install()` never keys a dict by role."""

	def setUp(self):
		super().setUp()
		self.role = "VMMSTEST One Coordinator For Two Jobs"
		if not frappe.db.exists("Role", self.role):
			frappe.get_doc({"doctype": "Role", "role_name": self.role, "desk_access": 1}).insert(
				ignore_permissions=True
			)

	def tearDown(self):
		from vmmsx.deployment.services.society import DEPLOYMENT_SCOPE_ROLE_FIELD, REQUEST_SCOPE_ROLE_FIELD

		frappe.db.set_single_value("National Society Settings", DEPLOYMENT_SCOPE_ROLE_FIELD, None)
		frappe.db.set_single_value("National Society Settings", REQUEST_SCOPE_ROLE_FIELD, None)
		super().tearDown()

	def test_the_same_role_named_on_two_settings_gets_both_clusters_doctypes(self):
		from vmmsx.deployment.services.society import DEPLOYMENT_SCOPE_ROLE_FIELD, REQUEST_SCOPE_ROLE_FIELD

		frappe.db.set_single_value("National Society Settings", DEPLOYMENT_SCOPE_ROLE_FIELD, self.role)
		frappe.db.set_single_value("National Society Settings", REQUEST_SCOPE_ROLE_FIELD, self.role)

		result = permissions.install()

		self.assertIn("VMMS Deployment", result[self.role])
		self.assertIn("VMMS Deployment Request", result[self.role])
		self.assertIn("VMMS Terms of Reference", result[self.role])
