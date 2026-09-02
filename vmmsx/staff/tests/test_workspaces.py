# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The staff desk cluster: nesting, the System Manager floor, and idempotency.

Two failure directions matter here, and they are opposite to each other:

* A child that nobody but a configured coordinator can see would defeat the
  point — on a fresh site an administrator must see the whole cluster without
  configuring anything, exactly the way ERPNext's Accounting is there on day
  one. That is `test_every_surface_names_system_manager` below.
* A workspace with no roles at all is visible to *every* desk user (Frappe's
  own fallback in `Workspace.is_permitted()`), so `test_none_is_role_less`
  guards the other direction: System Manager must actually be named, not
  merely intended.

Visibility itself is exercised in `registration/tests/test_workspaces.py`
through Frappe's own `get_workspaces()`; this suite stays at the data level —
roles, nesting, content — because nothing about this cluster is conditional on
a person's own registration journey the way the self-service surfaces are.
"""

import json

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.staff.services import workspaces

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestTheClusterIsBuilt(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		workspaces.install()

	def test_the_parent_and_all_five_children_exist(self):
		for label in (workspaces.PARENT, *workspaces.CHILDREN):
			self.assertTrue(frappe.db.exists("Workspace", label), label)

	def test_every_child_is_nested_under_the_parent(self):
		for label in workspaces.CHILDREN:
			parent_page = frappe.db.get_value("Workspace", label, "parent_page")
			self.assertEqual(parent_page, workspaces.PARENT, label)

	def test_the_parent_itself_has_no_parent(self):
		self.assertEqual(frappe.db.get_value("Workspace", workspaces.PARENT, "parent_page"), "")

	def test_every_surface_is_mounted_onto_vmmsx(self):
		"""Without `app`, a custom workspace hangs off no apps-screen dock at all."""
		for label in (workspaces.PARENT, *workspaces.CHILDREN):
			self.assertEqual(frappe.db.get_value("Workspace", label, "app"), "vmmsx", label)

	def test_every_surface_names_system_manager(self):
		"""The floor: an admin sees the whole cluster with nothing configured."""
		for label in (workspaces.PARENT, *workspaces.CHILDREN):
			roles = frappe.get_all(
				"Has Role", filters={"parent": label, "parenttype": "Workspace"}, pluck="role"
			)
			self.assertIn(workspaces.SYSTEM_MANAGER, roles, label)

	def test_none_is_role_less(self):
		"""The other direction: a workspace with no roles is visible to everybody."""
		for label in (workspaces.PARENT, *workspaces.CHILDREN):
			roles = frappe.get_all(
				"Has Role", filters={"parent": label, "parenttype": "Workspace"}, pluck="role"
			)
			self.assertTrue(roles, label)

	def test_each_childs_shortcuts_name_doctypes_that_exist(self):
		for label in workspaces.CHILDREN:
			shortcuts = frappe.get_all(
				"Workspace Shortcut",
				filters={"parent": label, "parenttype": "Workspace", "type": "DocType"},
				pluck="link_to",
			)
			self.assertTrue(shortcuts, label)
			for doctype in shortcuts:
				self.assertTrue(frappe.db.exists("DocType", doctype), f"{label}: {doctype}")

	def test_the_membership_child_covers_exactly_its_doctypes(self):
		self._assert_shortcuts(
			workspaces.MEMBERSHIP,
			{"VMMS Member", "VMMS Membership", "VMMS Membership Type", "VMMS Membership Benefit"},
		)

	def test_the_volunteers_child_covers_exactly_its_doctypes(self):
		self._assert_shortcuts(
			workspaces.VOLUNTEERS,
			{
				"VMMS Volunteer",
				"VMMS Volunteer Application",
				"VMMS Certification",
				"VMMS Certification Type",
				"VMMS Course Mapping",
				"VMMS Time Log",
			},
		)

	def test_the_deployments_child_covers_exactly_its_doctypes(self):
		self._assert_shortcuts(
			workspaces.DEPLOYMENTS,
			{
				"Project",
				"VMMS Deployment",
				# One person's deployment. A list view of these answers "what has
				# this volunteer been asked and what did they say" across
				# deployments, which a roster on one record cannot.
				"VMMS Deployment Assignment",
				"VMMS Deployment Request",
				"VMMS Terms of Reference",
				"VMMS Branch Transfer",
			},
		)

	def test_the_stipend_child_covers_exactly_its_doctypes(self):
		self._assert_shortcuts(
			workspaces.STIPEND, {"VMMS Stipend Progress Report", "VMMS Stipend Payment Form"}
		)

	def test_the_society_and_setup_child_covers_exactly_its_doctypes(self):
		self._assert_shortcuts(
			workspaces.SOCIETY_SETUP,
			{
				"Geo Level",
				"Geo Node",
				"Geo Assignment",
				"National Society Settings",
				"Affiliation Type",
				"VMMS Membership Type",
				"VMMS Certification Type",
				"VMMS Course Mapping",
				"VMMS Time Log Category",
				"VMMS Skill",
				# The two vocabularies a weekly availability grid and a mission's
				# approach are written from. Configuration a society sets once,
				# which is what this workspace is for.
				"VMMS Availability Slot",
				"VMMS TOR Methodology",
				"VMMS Announcement Type",
				# The WhatsApp gateway. Optional in a way the rest of this list is
				# not — a society without one is an ordinary society — but it is
				# still configuration set once before the channel works, and the
				# checklist is where somebody goes looking for it.
				"VMMS WhatsApp Settings",
				"VMMS Approval Workflow",
				"VMMS Template Category",
				"VMMS Template",
				"VMMS Application Question",
				# The policies an applicant agrees to, and the versions of them.
				# Configuration a society's legal officer owns — and unreachable
				# from the desk until they were listed here, which is not a state
				# a privacy notice should be in.
				"VMMS Declaration",
				"VMMS Declaration Version",
			},
		)

	def test_the_setup_checklist_covers_the_same_doctypes(self):
		"""The onboarding steps `install()` builds should name the exact same
		doctypes as the shortcut grid above — one checklist, one source of truth."""
		module_onboarding = frappe.get_doc("Module Onboarding", workspaces.SOCIETY_SETUP)
		step_doctypes = {
			frappe.db.get_value("Onboarding Step", row.step, "reference_document")
			for row in module_onboarding.steps
		}
		shortcut_doctypes = set(
			frappe.get_all(
				"Workspace Shortcut",
				filters={"parent": workspaces.SOCIETY_SETUP, "parenttype": "Workspace", "type": "DocType"},
				pluck="link_to",
			)
		)
		self.assertEqual(step_doctypes, shortcut_doctypes)

	def test_the_setup_workspace_points_at_the_checklist(self):
		module_onboarding = frappe.db.get_value("Workspace", workspaces.SOCIETY_SETUP, "module_onboarding")
		self.assertEqual(module_onboarding, workspaces.SOCIETY_SETUP)

	def test_the_parents_shortcuts_are_the_five_children_and_nothing_else(self):
		shortcuts = frappe.get_all(
			"Workspace Shortcut",
			filters={"parent": workspaces.PARENT, "parenttype": "Workspace"},
			fields=["label", "type", "url"],
		)
		self.assertEqual({row["label"] for row in shortcuts}, set(workspaces.CHILDREN))
		for row in shortcuts:
			self.assertEqual(row["type"], "URL")
			self.assertTrue(row["url"].startswith("/desk/"), row["url"])

	def test_the_content_blocks_name_shortcuts_that_are_really_there(self):
		for label in (workspaces.PARENT, *workspaces.CHILDREN):
			content = json.loads(frappe.db.get_value("Workspace", label, "content") or "[]")
			named = {block["data"]["shortcut_name"] for block in content if block["type"] == "shortcut"}
			defined = set(
				frappe.get_all(
					"Workspace Shortcut",
					filters={"parent": label, "parenttype": "Workspace"},
					pluck="label",
				)
			)
			self.assertEqual(named - defined, set(), label)

	def test_installing_twice_changes_nothing(self):
		before = {
			label: frappe.db.get_value("Workspace", label, "content")
			for label in (workspaces.PARENT, *workspaces.CHILDREN)
		}
		result = workspaces.install()
		after = {
			label: frappe.db.get_value("Workspace", label, "content")
			for label in (workspaces.PARENT, *workspaces.CHILDREN)
		}

		self.assertEqual(before, after)
		for label in (workspaces.PARENT, *workspaces.CHILDREN):
			self.assertEqual(result[label], "updated", label)

	def test_installing_twice_creates_no_duplicates(self):
		workspaces.install()
		for label in (workspaces.PARENT, *workspaces.CHILDREN):
			count = frappe.db.count("Workspace", {"label": label})
			self.assertEqual(count, 1, label)

	def _assert_shortcuts(self, label, expected_doctypes):
		shortcuts = frappe.get_all(
			"Workspace Shortcut",
			filters={"parent": label, "parenttype": "Workspace", "type": "DocType"},
			pluck="link_to",
		)
		self.assertEqual(set(shortcuts), expected_doctypes, label)


class TestTheSelfServiceSurfacesAreUntouched(IntegrationTestCase):
	def test_the_three_self_service_workspaces_are_unaffected(self):
		"""Additive only: this module must not delete or rename what registration built."""
		from vmmsx.registration.services import workspaces as self_service

		before = {
			label: frappe.db.exists("Workspace", label)
			for label in (self_service.LANDING, self_service.VOLUNTEER, self_service.MEMBERSHIP)
		}

		workspaces.install()

		for label, existed_before in before.items():
			self.assertEqual(frappe.db.exists("Workspace", label), existed_before, label)


class TestAnOptionalCoordinatorRole(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.role = "VMMSTEST Volunteer Coordinator"
		if not frappe.db.exists("Role", self.role):
			frappe.get_doc({"doctype": "Role", "role_name": self.role, "desk_access": 1}).insert(
				ignore_permissions=True
			)

	def tearDown(self):
		from vmmsx.volunteer.services.society import SCOPE_ROLE_FIELD

		frappe.db.set_single_value("National Society Settings", SCOPE_ROLE_FIELD, None)
		workspaces.install()
		super().tearDown()

	def test_a_configured_scope_role_is_added_without_dropping_system_manager(self):
		from vmmsx.volunteer.services.society import SCOPE_ROLE_FIELD

		frappe.db.set_single_value("National Society Settings", SCOPE_ROLE_FIELD, self.role)
		workspaces.install()

		child_roles = frappe.get_all(
			"Has Role", filters={"parent": workspaces.VOLUNTEERS, "parenttype": "Workspace"}, pluck="role"
		)
		parent_roles = frappe.get_all(
			"Has Role", filters={"parent": workspaces.PARENT, "parenttype": "Workspace"}, pluck="role"
		)

		self.assertEqual(set(child_roles), {workspaces.SYSTEM_MANAGER, self.role})
		self.assertIn(self.role, parent_roles)
		self.assertIn(workspaces.SYSTEM_MANAGER, parent_roles)

	def test_an_unset_scope_role_leaves_only_system_manager(self):
		workspaces.install()

		child_roles = frappe.get_all(
			"Has Role", filters={"parent": workspaces.VOLUNTEERS, "parenttype": "Workspace"}, pluck="role"
		)

		self.assertEqual(set(child_roles), {workspaces.SYSTEM_MANAGER})


class TestHasDeskAccess(IntegrationTestCase):
	"""`has_desk_access()` is the `has_permission` gate behind the VMMS apps-screen
	icon (`hooks.py`'s `add_to_apps_screen`) — whether it agrees with the Roles
	table `install()` actually wrote is what decides whether that icon exists for
	a given person."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		workspaces.install()

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")

	def test_system_manager_passes_even_before_the_cluster_exists(self):
		"""The literal role check, not just the derived one — see the docstring."""
		frappe.delete_doc("Workspace", workspaces.PARENT, force=True, ignore_permissions=True)
		self.addCleanup(workspaces.install)

		frappe.set_user("Administrator")

		self.assertTrue(workspaces.has_desk_access())

	def test_a_configured_scope_role_holder_passes(self):
		from vmmsx.volunteer.services.society import SCOPE_ROLE_FIELD

		role = "VMMSTEST Desk Access Coordinator"
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)

		email = "vmmstest.deskaccess@example.com"
		user = (
			frappe.get_doc("User", email)
			if frappe.db.exists("User", email)
			else frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "Desk Access", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		)
		user.add_roles(role)

		frappe.db.set_single_value("National Society Settings", SCOPE_ROLE_FIELD, role)

		def _reset():
			frappe.db.set_single_value("National Society Settings", SCOPE_ROLE_FIELD, None)
			workspaces.install()

		self.addCleanup(_reset)
		workspaces.install()

		frappe.set_user(email)
		frappe.clear_cache(user=email)

		self.assertTrue(workspaces.has_desk_access())

	def test_a_role_with_nothing_to_do_with_vmms_fails(self):
		role = "VMMSTEST Nothing To Do With VMMS"
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)

		email = "vmmstest.unrelated@example.com"
		user = (
			frappe.get_doc("User", email)
			if frappe.db.exists("User", email)
			else frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "Unrelated", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		)
		user.add_roles(role)

		frappe.set_user(email)
		frappe.clear_cache(user=email)

		self.assertFalse(workspaces.has_desk_access())
