# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The three surfaces: who sees them, what is on them, and what happens with no role.

The failure this suite is really about is the quiet one. A Frappe Workspace that
names no roles is visible to **every** desk user on the site, so a landing page
built from an unconfigured setting would put a public registration form in front
of the whole national society and look like a working install while doing it.
`install()` therefore refuses to build one, and removes one it finds, and both
halves are asserted below.

Visibility is read through Frappe's own `get_workspaces`, which is what the desk
calls. A test that re-derived the role check would pass for an implementation the
desk disagreed with.
"""

import json

import frappe

from vmmsx.registration.services import workspaces
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestWhatIsInstalled(RegistrationTestCase):
	def setUp(self):
		super().setUp()
		workspaces.install()

	def test_all_three_are_installed_when_the_roles_are_configured(self):
		for label in (workspaces.LANDING, workspaces.VOLUNTEER, workspaces.MEMBERSHIP):
			self.assertTrue(frappe.db.exists("Workspace", label), label)

	def test_all_three_are_mounted_onto_vmmsx(self):
		"""Without `app`, a custom workspace hangs off no apps-screen dock at all."""
		for label in (workspaces.LANDING, workspaces.VOLUNTEER, workspaces.MEMBERSHIP):
			self.assertEqual(frappe.db.get_value("Workspace", label, "app"), "vmmsx", label)

	def test_each_one_names_exactly_the_role_the_society_configured(self):
		expected = {
			workspaces.LANDING: fixtures.SELF_SERVICE_ROLE,
			workspaces.VOLUNTEER: fixtures.VOLUNTEER_ROLE,
			workspaces.MEMBERSHIP: fixtures.MEMBER_ROLE,
		}

		for label, role in expected.items():
			roles = frappe.get_all(
				"Has Role", filters={"parent": label, "parenttype": "Workspace"}, pluck="role"
			)

			self.assertEqual(roles, [role], label)

	def test_the_landing_workspace_offers_exactly_the_two_forms(self):
		shortcuts = frappe.get_all(
			"Workspace Shortcut",
			filters={"parent": workspaces.LANDING, "parenttype": "Workspace"},
			fields=["label", "type", "url"],
			order_by="idx asc",
		)

		self.assertEqual(len(shortcuts), 2)
		self.assertEqual(
			{row["url"] for row in shortcuts},
			{workspaces.VOLUNTEER_FORM_ROUTE, workspaces.MEMBERSHIP_FORM_ROUTE},
		)

	def test_the_landing_shortcuts_point_at_web_forms_that_exist_and_are_published(self):
		"""A shortcut to a route nobody published is a dead end on day one."""
		for route in (workspaces.VOLUNTEER_FORM_ROUTE, workspaces.MEMBERSHIP_FORM_ROUTE):
			published = frappe.db.get_value("Web Form", {"route": route.lstrip("/")}, "published")

			self.assertEqual(published, 1, route)

	def test_the_volunteer_workspace_links_only_doctypes_that_exist(self):
		"""A shortcut or card link naming a doctype nobody built is a dead end."""
		shortcuts = frappe.get_all(
			"Workspace Shortcut",
			filters={"parent": workspaces.VOLUNTEER, "parenttype": "Workspace", "type": "DocType"},
			pluck="link_to",
		)

		self.assertTrue(shortcuts)

		for doctype in shortcuts:
			self.assertTrue(frappe.db.exists("DocType", doctype), doctype)

	def test_the_certification_shortcut_is_the_endpoint_not_a_list_view(self):
		"""The one place the derived lapse could quietly stop being shown.

		A DocType shortcut to `VMMS Certification` would look right, open, and
		list the person's own rows — and show completion and expiry dates with no
		indication of whether anything had lapsed, because lapse is not a column
		and deliberately never will be. Only `my_certifications` derives it. If
		somebody ever swaps this back to a list view for tidiness, this fails.
		"""
		shortcuts = {
			row["label"]: row
			for row in frappe.get_all(
				"Workspace Shortcut",
				filters={"parent": workspaces.VOLUNTEER, "parenttype": "Workspace"},
				fields=["label", "type", "url", "link_to"],
			)
		}
		certifications = shortcuts["My Certifications"]

		self.assertEqual(certifications["type"], "URL")
		self.assertIn("vmmsx.api.volunteer.my_certifications", certifications["url"])

	def test_the_certification_list_is_still_reachable_from_the_card(self):
		"""The endpoint replaced the shortcut, not the records themselves.

		The permission and the User Permission that narrow that list to this
		person exist because the workspace lists the doctype, so dropping the
		link entirely would leave both granted for nothing.
		"""
		links = frappe.get_all(
			"Workspace Link",
			filters={"parent": workspaces.VOLUNTEER, "parenttype": "Workspace", "type": "Link"},
			pluck="link_to",
		)

		self.assertIn("VMMS Certification", links)
		self.assertIn("VMMS Time Log", links)

	def test_installing_twice_changes_nothing(self):
		before = frappe.db.get_value("Workspace", workspaces.LANDING, "content")
		result = workspaces.install()
		after = frappe.db.get_value("Workspace", workspaces.LANDING, "content")

		self.assertEqual(before, after)
		self.assertEqual(result[workspaces.LANDING], "updated")

	def test_the_content_blocks_name_shortcuts_that_are_really_there(self):
		"""A content block naming a shortcut nobody defined renders as a gap."""
		for label in (workspaces.LANDING, workspaces.VOLUNTEER, workspaces.MEMBERSHIP):
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


class TestFailingClosed(RegistrationTestCase):
	def tearDown(self):
		fixtures.configure_society(self.society)
		workspaces.install()
		super().tearDown()

	def test_an_unconfigured_role_installs_nothing(self):
		from vmmsx.registration.services.society import SELF_SERVICE_ROLE_FIELD

		frappe.delete_doc("Workspace", workspaces.LANDING, force=True, ignore_permissions=True)
		fixtures.set_settings(**{SELF_SERVICE_ROLE_FIELD: None})

		result = workspaces.install()

		self.assertFalse(frappe.db.exists("Workspace", workspaces.LANDING))
		self.assertIn("no role", result[workspaces.LANDING])

	def test_clearing_the_setting_removes_a_surface_rather_than_opening_it(self):
		"""The dangerous case, stated as a test.

		Stripping the roles and leaving the workspace behind would make it
		visible to everybody, which is the exact opposite of what clearing a
		setting means.
		"""
		from vmmsx.registration.services.society import SELF_SERVICE_ROLE_FIELD

		workspaces.install()
		self.assertTrue(frappe.db.exists("Workspace", workspaces.LANDING))

		fixtures.set_settings(**{SELF_SERVICE_ROLE_FIELD: None})
		workspaces.install()

		self.assertFalse(frappe.db.exists("Workspace", workspaces.LANDING))

	def test_a_deleted_role_is_treated_as_unconfigured(self):
		"""A setting pointing at a role somebody removed grants nothing."""
		from vmmsx.registration.services.society import SELF_SERVICE_ROLE_FIELD

		fixtures.set_settings(**{SELF_SERVICE_ROLE_FIELD: "REGTEST Role That Does Not Exist"})
		result = workspaces.install()

		self.assertFalse(frappe.db.exists("Workspace", workspaces.LANDING))
		self.assertIn("no role", result[workspaces.LANDING])


class TestWhoLandsWhere(RegistrationTestCase):
	def setUp(self):
		super().setUp()
		workspaces.install()

	def test_a_brand_new_account_lands_on_the_landing_workspace(self):
		"""First in the list is where the desk opens."""
		user = fixtures.website_account("brand.new")
		visible = self.workspaces_of(user)

		self.assertEqual(visible[0], workspaces.LANDING)

	def test_a_brand_new_account_is_shown_neither_self_service_surface(self):
		user = fixtures.website_account("nothing.yet")
		visible = self.workspaces_of(user)

		self.assertNotIn(workspaces.VOLUNTEER, visible)
		self.assertNotIn(workspaces.MEMBERSHIP, visible)

	def test_an_approved_volunteer_lands_on_their_own_surface(self):
		user, application = self.register_as_volunteer("landing.volunteer")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		visible = self.workspaces_of(user)

		self.assertEqual(visible[0], workspaces.VOLUNTEER)

	def test_an_active_member_lands_on_theirs(self):
		user, membership = self.register_as_member("landing.member", fixtures.TYPE_AUTO)
		fixtures.confirm_payment_through_manual_driver(membership)

		visible = self.workspaces_of(user)

		self.assertEqual(visible[0], workspaces.MEMBERSHIP)

	def test_the_landing_surface_stays_available_after_approval(self):
		"""Deliberate: registering for the *other* affiliation is the same two buttons."""
		user, application = self.register_as_volunteer("still.registering")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		self.assertIn(workspaces.LANDING, self.workspaces_of(user))

	def test_the_approver_is_shown_none_of_the_three(self):
		"""They are not a volunteer and not a member; these are not their surfaces."""
		visible = self.workspaces_of(self.approver)

		for label in (workspaces.LANDING, workspaces.VOLUNTEER, workspaces.MEMBERSHIP):
			self.assertNotIn(label, visible)


class TestTheAppsScreenGate(RegistrationTestCase):
	"""`has_self_service_access()` is the `has_permission` gate behind the second
	`add_to_apps_screen` entry in `hooks.py` — whether it agrees with the Roles
	tables `install()` actually wrote is what decides whether that icon exists
	for a given person."""

	def test_an_approved_volunteer_passes(self):
		user, application = self.register_as_volunteer("appsscreen.volunteer")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		with fixtures.acting_as(user):
			self.assertTrue(workspaces.has_self_service_access())

	def test_a_brand_new_account_with_only_the_landing_role_passes(self):
		"""Registration alone is one of the three surfaces, so it is enough."""
		user = fixtures.website_account("appsscreen.brandnew")

		with fixtures.acting_as(user):
			self.assertTrue(workspaces.has_self_service_access())

	def test_the_approver_holds_none_of_the_three_roles_and_fails(self):
		"""Being who applications route to is not a self-service role."""
		with fixtures.acting_as(self.approver):
			self.assertFalse(workspaces.has_self_service_access())


class TestThePermissionsBehindTheSurfaces(RegistrationTestCase):
	def test_the_volunteer_role_may_read_what_its_workspace_lists(self):
		"""A shortcut to a list the role cannot read is a permission error with an icon."""
		from vmmsx.registration.services import permissions

		result = permissions.install()

		self.assertEqual(result["role"], fixtures.VOLUNTEER_ROLE)

		for doctype in permissions.SELF_SERVICE_READABLE:
			self.assertTrue(frappe.db.exists("DocType", doctype), doctype)

			granted = frappe.get_all(
				"Custom DocPerm",
				filters={"parent": doctype, "role": fixtures.VOLUNTEER_ROLE, "read": 1},
				pluck="name",
			)

			self.assertTrue(granted, doctype)

	def test_it_grants_read_and_nothing_wider(self):
		"""Looking at the hours somebody recorded is not the same act as recording them."""
		from vmmsx.registration.services import permissions

		permissions.install()

		for doctype in permissions.SELF_SERVICE_READABLE:
			row = frappe.get_all(
				"Custom DocPerm",
				filters={"parent": doctype, "role": fixtures.VOLUNTEER_ROLE},
				fields=["read", "write", "create", "delete"],
			)[0]

			self.assertEqual(row["read"], 1, doctype)
			self.assertEqual((row["write"], row["create"], row["delete"]), (0, 0, 0), doctype)

	def test_an_unconfigured_role_grants_nothing(self):
		from vmmsx.registration.services import permissions
		from vmmsx.volunteer.services.society import MEMBER_ROLE_FIELD

		fixtures.set_settings(**{MEMBER_ROLE_FIELD: None})

		try:
			result = permissions.install()

			self.assertIsNone(result["role"])
			self.assertEqual(result["granted"], [])
		finally:
			fixtures.set_settings(**{MEMBER_ROLE_FIELD: fixtures.VOLUNTEER_ROLE})
