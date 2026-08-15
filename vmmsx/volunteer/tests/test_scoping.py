# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Volunteers are geo-scoped, and which role scopes them is a society's choice.

`VMMS Volunteer` is registered with core through `onerc_scopeable_doctypes`,
naming its role with `role_from_setting` rather than a literal — because *which*
of a society's roles may see the volunteer register is that society's decision,
and a literal in `hooks.py` would hardcode exactly what the access model
forbids.

These tests exercise core's capability end to end **from the satellite side**:
the registration is the real one from `hooks.py`, the setting is the real Custom
Field vmmsx installs, and enforcement is core's, unmocked.

Three things are proved:

1. **It scopes.** With a role configured, a holder sees their area and not
   anybody else's — through all three enforcement layers, not one.
2. **The empty default is safe.** Shipping with no role chosen denies every
   non-administrator rather than exposing the register to everyone, and says so
   in a log rather than silently. Volunteer records carry personal data about
   people the society has no employment relationship with; the safe direction is
   closed.
3. **The registration reads the real ACC-02 anchor.** Scoping must filter on the
   same field the anchor rule makes mandatory — `home_geo_node`. A registration
   naming a field that was nullable, or a different field, would filter on
   something that can be NULL and quietly drop rows out of every list.
"""

import frappe

from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class ScopingTestCase(VolunteerTestCase):
	"""Two volunteers in two different societies, and users placed in each."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# The scope role needs desk permission on the doctype as well as geo
		# authority: scoping narrows what a role may reach, it does not grant the
		# role access in the first place.
		fixtures.grant_doctype_access(fixtures.VOLUNTEER_DOCTYPE, fixtures.SCOPE_ROLE)

		# A holder placed in society A's county, and one in society B's district.
		cls.here = fixtures.make_user("vscope_here", [fixtures.SCOPE_ROLE])
		cls.elsewhere = fixtures.make_user("vscope_elsewhere", [fixtures.SCOPE_ROLE])
		# Holds no scope role at all — a plain desk user.
		cls.outsider = fixtures.make_user("vscope_outsider", [fixtures.APPLICANT_ROLE])

		fixtures.make_assignment(cls.here, fixtures.SCOPE_ROLE, cls.society_a["county"])
		fixtures.make_assignment(cls.elsewhere, fixtures.SCOPE_ROLE, cls.society_b["district"])

		cls.volunteer_here = cls.volunteer_at(cls.society_a["ward"])
		cls.volunteer_elsewhere = cls.volunteer_at(cls.society_b["ward"])

	@classmethod
	def volunteer_at(cls, node: str) -> str:
		profile = fixtures.make_profile("Scoped", "Volunteer")

		return fixtures.make_volunteer(profile, node).name

	def setUp(self):
		super().setUp()
		# Every test states the scope role it wants; put it back afterwards so
		# the class-level default does not leak between them.
		self.addCleanup(fixtures.set_scope_role, fixtures.SCOPE_ROLE)

	def savable_settings(self):
		"""The settings single, with whatever it needs to be saveable at all.

		A site whose society settings have never been filled in cannot save the
		document, and a test about the scope role would then fail for a reason
		that has nothing to do with the scope role. Filling the mandatory fields
		is what an administrator would have done before ever choosing a role.
		"""
		settings = frappe.get_doc(fixtures.SETTINGS_DOCTYPE)

		for fieldname in ("organization_name", "organization_short_name"):
			if not settings.get(fieldname):
				settings.set(fieldname, f"{fixtures.TEST_PREFIX} Society")

		if not settings.get("primary_language"):
			settings.set("primary_language", frappe.db.get_value("Language", {"name": "en"}) or "en")

		return settings

	# --- the three layers -------------------------------------------------

	def listed_by(self, user: str) -> set[str]:
		"""What the query engine returns for this user — nothing, if it refuses.

		A user with no DocPerm on the doctype at all is stopped by Frappe before
		geo scoping is ever consulted, and `get_list` raises rather than
		returning an empty list. For this helper's purposes both are the same
		answer: they see nothing.
		"""
		frappe.set_user(user)

		try:
			return set(frappe.get_list(fixtures.VOLUNTEER_DOCTYPE, pluck="name", limit_page_length=0))
		except frappe.PermissionError:
			return set()

	def may_read(self, user: str, volunteer: str) -> bool:
		doc = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, volunteer)

		return frappe.has_permission(fixtures.VOLUNTEER_DOCTYPE, doc=doc, user=user, ptype="read")

	def guard_permits(self, user: str, volunteer: str) -> bool:
		from onerc_core.access.services.enforcement import guard

		try:
			guard(fixtures.VOLUNTEER_DOCTYPE, volunteer, user=user)
		except frappe.PermissionError:
			return False

		return True

	def assert_reachable(self, user: str, volunteer: str, label: str):
		self.assertIn(volunteer, self.listed_by(user), f"{label}: missing from list query")
		self.assertTrue(self.may_read(user, volunteer), f"{label}: document read denied")
		self.assertTrue(self.guard_permits(user, volunteer), f"{label}: guard denied")

	def assert_unreachable(self, user: str, volunteer: str, label: str):
		self.assertNotIn(volunteer, self.listed_by(user), f"{label}: LEAKED via list query")
		self.assertFalse(self.may_read(user, volunteer), f"{label}: LEAKED via document read")
		self.assertFalse(self.guard_permits(user, volunteer), f"{label}: LEAKED via guard")


class TestTheRegistration(ScopingTestCase):
	def test_the_volunteer_is_registered_with_core(self):
		"""Read from the real hook, not from a fixture."""
		from onerc_core.access.services import registry

		registration = registry.for_doctype(fixtures.VOLUNTEER_DOCTYPE)

		self.assertIsNotNone(registration, "VMMS Volunteer is not registered as scopeable")
		self.assertEqual(registration["geo_node_field"], "home_geo_node")
		self.assertEqual(registration["role_from_setting"], fixtures.SCOPE_ROLE_SETTING)

	def test_it_names_no_literal_role(self):
		"""A literal here would hardcode a society's access policy."""
		from onerc_core.access.services import registry

		registration = registry.for_doctype(fixtures.VOLUNTEER_DOCTYPE)

		self.assertNotIn("role", registration)

	def test_the_registered_field_is_the_acc_02_anchor(self):
		"""Scoping must read the same field the anchor rule makes mandatory.

		If it did not, the filter would be over a nullable column and core's
		`IN` would silently drop every row with a NULL in it — records that exist
		and that nobody can see.
		"""
		field = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE).get_field("home_geo_node")

		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Geo Node")
		self.assertTrue(field.reqd)

	def test_an_unplaced_volunteer_cannot_exist_to_be_dropped(self):
		"""The other half of the same argument, asserted rather than assumed."""
		profile = fixtures.make_profile("Unplaced", "Volunteer")

		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc(
				{
					"doctype": fixtures.VOLUNTEER_DOCTYPE,
					"red_profile": profile,
					"home_geo_node": None,
				}
			).insert()

	def test_the_settings_field_exists_and_links_to_role(self):
		field = frappe.get_meta(fixtures.SETTINGS_DOCTYPE).get_field(fixtures.SCOPE_ROLE_SETTING)

		self.assertIsNotNone(field, "the patch did not install the settings field")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Role")

	def test_both_of_this_apps_registrations_coexist(self):
		"""Membership was first; the volunteer register is the second, not a replacement."""
		from onerc_core.access.services import registry

		self.assertIsNotNone(registry.for_doctype("VMMS Membership"))
		self.assertIsNotNone(registry.for_doctype(fixtures.VOLUNTEER_DOCTYPE))

	def test_the_two_registrations_use_different_settings(self):
		"""A society may let one role see members and another see volunteers."""
		from onerc_core.access.services import registry

		self.assertNotEqual(
			registry.for_doctype("VMMS Membership")["role_from_setting"],
			registry.for_doctype(fixtures.VOLUNTEER_DOCTYPE)["role_from_setting"],
		)


class TestScopingWithARoleConfigured(ScopingTestCase):
	"""The capability, working: a configured role scopes by geo."""

	def setUp(self):
		super().setUp()
		fixtures.set_scope_role(fixtures.SCOPE_ROLE)

	def test_a_holder_reaches_their_own_area(self):
		self.assert_reachable(self.here, self.volunteer_here, "own county")

	def test_a_holder_cannot_reach_another_area(self):
		"""The gate. Same role, different place."""
		self.assert_unreachable(self.here, self.volunteer_elsewhere, "other society")

	def test_the_other_holder_sees_the_mirror_image(self):
		self.assert_reachable(self.elsewhere, self.volunteer_elsewhere, "own district")
		self.assert_unreachable(self.elsewhere, self.volunteer_here, "other society")

	def test_a_user_without_the_role_is_denied_everywhere(self):
		self.assert_unreachable(self.outsider, self.volunteer_here, "no role")
		self.assert_unreachable(self.outsider, self.volunteer_elsewhere, "no role")

	def test_pointing_the_setting_at_another_role_changes_who_sees_what(self):
		"""Zero code diff: the society's choice of role is the whole mechanism."""
		self.assert_reachable(self.here, self.volunteer_here, "under the scope role")

		# The applicant role is real, but nobody holds a Geo Assignment under it.
		fixtures.set_scope_role(fixtures.APPLICANT_ROLE)

		self.assert_unreachable(self.here, self.volunteer_here, "after the role changed")

	def test_an_administrator_is_unaffected(self):
		self.assert_reachable("Administrator", self.volunteer_here, "admin")
		self.assert_reachable("Administrator", self.volunteer_elsewhere, "admin")


class TestTheEmptyDefaultIsSafe(ScopingTestCase):
	"""The shipped state: no role chosen, so nobody but an administrator reads one."""

	def setUp(self):
		super().setUp()
		fixtures.set_scope_role(None)

	def test_the_setting_ships_empty(self):
		"""The patch installs the field without choosing a value."""
		from onerc_core.access.services import registry

		registration = registry.for_doctype(fixtures.VOLUNTEER_DOCTYPE)

		self.assertIsNone(registry.resolve_role(registration))

	def test_a_role_holder_is_denied(self):
		"""Even the user who would be in scope, were a role configured."""
		self.assert_unreachable(self.here, self.volunteer_here, "empty setting")

	def test_everyone_non_admin_is_denied(self):
		self.assert_unreachable(self.elsewhere, self.volunteer_elsewhere, "empty setting")
		self.assert_unreachable(self.outsider, self.volunteer_here, "empty setting")

	def test_an_administrator_can_still_get_in_to_configure_it(self):
		"""Otherwise the safe default would be an unrecoverable one."""
		self.assert_reachable("Administrator", self.volunteer_here, "admin under empty setting")

	def test_it_fails_closed_rather_than_open(self):
		"""Asserted at the layer itself: deny-all, not "no filter"."""
		from onerc_core.access.services.enforcement import DENY_ALL, get_permission_query_conditions

		self.assertEqual(get_permission_query_conditions(self.here, fixtures.VOLUNTEER_DOCTYPE), DENY_ALL)

	def test_the_denial_is_logged_not_silent(self):
		"""Core's detectable signal, reached through vmmsx's registration.

		An unconfigured scope role denies everybody, and that must be visible
		rather than looking like "nobody has been granted anything yet".
		"""
		from onerc_core.access.services.registry import UNRESOLVED_ROLE_LOG_TITLE

		before = frappe.db.count("Error Log", {"method": UNRESOLVED_ROLE_LOG_TITLE})

		self.assert_unreachable(self.here, self.volunteer_here, "empty setting")

		self.assertGreater(
			frappe.db.count("Error Log", {"method": UNRESOLVED_ROLE_LOG_TITLE}),
			before,
			"an unconfigured scope role denied everybody silently",
		)

	def test_the_membership_setting_does_not_stand_in_for_it(self):
		"""Two registrations, two settings, and one does not unlock the other."""
		frappe.db.set_single_value(
			fixtures.SETTINGS_DOCTYPE, "vmms_membership_scope_role", fixtures.SCOPE_ROLE
		)
		frappe.clear_document_cache(fixtures.SETTINGS_DOCTYPE, fixtures.SETTINGS_DOCTYPE)
		self.addCleanup(
			frappe.db.set_single_value, fixtures.SETTINGS_DOCTYPE, "vmms_membership_scope_role", None
		)

		self.assert_unreachable(self.here, self.volunteer_here, "membership role set, volunteer empty")


class TestABadRoleIsRefusedAtConfigTime(ScopingTestCase):
	"""Core's config-time guard fires for vmmsx's volunteer registration specifically.

	The guard iterates settings-backed registrations. If this registration were
	malformed, or named a field core could not see, the guard would simply not
	fire for it — so this proves participation, not just that core has a guard
	somewhere.
	"""

	NONEXISTENT_ROLE = f"{fixtures.TEST_PREFIX} No Such Role"

	def test_the_registration_participates_in_cores_config_guard(self):
		from onerc_core.access.services import registry

		backed = {
			entry["doctype"]: entry[registry.ROLE_SETTING_KEY]
			for entry in registry.settings_backed_registrations()
		}

		self.assertIn(fixtures.VOLUNTEER_DOCTYPE, backed)
		self.assertEqual(backed[fixtures.VOLUNTEER_DOCTYPE], fixtures.SCOPE_ROLE_SETTING)

	def test_cores_guard_refuses_a_role_that_does_not_exist(self):
		"""Reached by taking Frappe's link validation out of the way.

		Link validation runs first on a Link field and would refuse the value
		before core's guard sees it, which is a better outcome in the desk but
		hides the second line of defence. `ignore_links` removes the first —
		which is also exactly what a migration writing settings programmatically
		would do.
		"""
		fixtures.set_scope_role(self.NONEXISTENT_ROLE)

		settings = self.savable_settings()
		settings.flags.ignore_links = True

		with self.assertRaises(frappe.ValidationError):
			settings.save()

		message = frappe.as_json(frappe.message_log[-1] if frappe.message_log else {})

		self.assertIn(self.NONEXISTENT_ROLE, message)
		self.assertIn(fixtures.VOLUNTEER_DOCTYPE, message)

	def test_a_real_role_saves(self):
		"""Guards the test above: the save works when the role is real."""
		fixtures.set_scope_role(fixtures.SCOPE_ROLE)

		self.savable_settings().save()

		self.assertEqual(
			frappe.db.get_single_value(fixtures.SETTINGS_DOCTYPE, fixtures.SCOPE_ROLE_SETTING),
			fixtures.SCOPE_ROLE,
		)

	def test_leaving_it_empty_saves(self):
		"""Not yet configured is not a misconfiguration."""
		fixtures.set_scope_role(None)

		self.savable_settings().save()

		self.assertFalse(frappe.db.get_single_value(fixtures.SETTINGS_DOCTYPE, fixtures.SCOPE_ROLE_SETTING))
