# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Memberships are geo-scoped, and which role scopes them is a society's choice.

`VMMS Membership` is registered with core through `onerc_scopeable_doctypes`,
naming its role with `role_from_setting` rather than a literal — because *which*
of a society's roles may see membership records is that society's decision, and
a literal in `hooks.py` would hardcode exactly what the access model forbids.

These tests exercise core's capability end to end **from the satellite side**:
the registration is the real one from `hooks.py`, the setting is the real Custom
Field vmmsx installs, and enforcement is core's, unmocked.

Three things are proved:

1. **It scopes.** With a role configured, a holder sees their area and not
   anybody else's — through all three enforcement layers, not one.
2. **The empty default is safe.** Shipping with no role chosen denies every
   non-administrator rather than exposing memberships to everyone. Memberships
   carry personal data; the safe direction is closed.
3. **A bad value is refused at config time.** That guard lives in core, but it
   only fires for registrations core can see — so this proves vmmsx's
   registration actually participates in it.
"""

import frappe

from vmmsx.member.services import approval
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

NONEXISTENT_ROLE = f"{fixtures.TEST_PREFIX} No Such Role"


class ScopingTestCase(MemberTestCase):
	"""Two memberships in two different counties, and users placed in each."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_FREE, approval.MODE_ROUTED, fee=0)

		# The scope role needs desk permission on the doctype as well as geo
		# authority: scoping narrows what a role may reach, it does not grant
		# the role access in the first place.
		fixtures.grant_membership_access(fixtures.SCOPE_ROLE)

		# A holder placed in society A's county, and one in society B's district.
		cls.here = fixtures.make_user("scope_here", [fixtures.SCOPE_ROLE])
		cls.elsewhere = fixtures.make_user("scope_elsewhere", [fixtures.SCOPE_ROLE])
		# Holds no scope role at all — a plain desk user.
		cls.outsider = fixtures.make_user("scope_outsider", [fixtures.APPLICANT_ROLE])

		fixtures.make_assignment(cls.here, fixtures.SCOPE_ROLE, cls.society_a["county"])
		fixtures.make_assignment(cls.elsewhere, fixtures.SCOPE_ROLE, cls.society_b["district"])

		cls.membership_here = cls.membership_at(cls.society_a["ward"])
		cls.membership_elsewhere = cls.membership_at(cls.society_b["ward"])

	@classmethod
	def membership_at(cls, node: str) -> str:
		profile = fixtures.make_profile("Scoped", "Applicant")

		return fixtures.make_membership(profile, fixtures.TYPE_FREE, node).name

	def setUp(self):
		super().setUp()
		# Every test states the scope role it wants; put it back afterwards so
		# the class-level default does not leak between them.
		self.addCleanup(fixtures.set_scope_role, fixtures.SCOPE_ROLE)

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
			return set(frappe.get_list(fixtures.MEMBERSHIP_DOCTYPE, pluck="name", limit_page_length=0))
		except frappe.PermissionError:
			return set()

	def may_read(self, user: str, membership: str) -> bool:
		doc = frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership)

		return frappe.has_permission(fixtures.MEMBERSHIP_DOCTYPE, doc=doc, user=user, ptype="read")

	def guard_permits(self, user: str, membership: str) -> bool:
		from onerc_core.access.services.enforcement import guard

		try:
			guard(fixtures.MEMBERSHIP_DOCTYPE, membership, user=user)
		except frappe.PermissionError:
			return False

		return True

	def assert_reachable(self, user: str, membership: str, label: str):
		self.assertIn(membership, self.listed_by(user), f"{label}: missing from list query")
		self.assertTrue(self.may_read(user, membership), f"{label}: document read denied")
		self.assertTrue(self.guard_permits(user, membership), f"{label}: guard denied")

	def assert_unreachable(self, user: str, membership: str, label: str):
		self.assertNotIn(membership, self.listed_by(user), f"{label}: LEAKED via list query")
		self.assertFalse(self.may_read(user, membership), f"{label}: LEAKED via document read")
		self.assertFalse(self.guard_permits(user, membership), f"{label}: LEAKED via guard")


class TestTheRegistration(ScopingTestCase):
	def test_membership_is_registered_with_core(self):
		"""Read from the real hook, not from a fixture."""
		from onerc_core.access.services import registry

		registration = registry.for_doctype(fixtures.MEMBERSHIP_DOCTYPE)

		self.assertIsNotNone(registration, "VMMS Membership is not registered as scopeable")
		self.assertEqual(registration["geo_node_field"], "geo_node")
		self.assertEqual(registration["role_from_setting"], fixtures.SCOPE_ROLE_SETTING)

	def test_it_names_no_literal_role(self):
		"""A literal here would hardcode a society's access policy."""
		from onerc_core.access.services import registry

		registration = registry.for_doctype(fixtures.MEMBERSHIP_DOCTYPE)

		self.assertNotIn("role", registration)

	def test_the_registered_field_is_the_acc_02_anchor(self):
		"""Scoping must read the same field the anchor rule makes mandatory."""
		field = frappe.get_meta(fixtures.MEMBERSHIP_DOCTYPE).get_field("geo_node")

		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Geo Node")
		self.assertTrue(field.reqd)

	def test_the_settings_field_exists_and_links_to_role(self):
		field = frappe.get_meta(fixtures.SETTINGS_DOCTYPE).get_field(fixtures.SCOPE_ROLE_SETTING)

		self.assertIsNotNone(field, "the patch did not install the settings field")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Role")


class TestScopingWithARoleConfigured(ScopingTestCase):
	"""The capability, working: a configured role scopes by geo."""

	def setUp(self):
		super().setUp()
		fixtures.set_scope_role(fixtures.SCOPE_ROLE)

	def test_a_holder_reaches_their_own_area(self):
		self.assert_reachable(self.here, self.membership_here, "own county")

	def test_a_holder_cannot_reach_another_area(self):
		"""The gate. Same role, different place."""
		self.assert_unreachable(self.here, self.membership_elsewhere, "other society")

	def test_the_other_holder_sees_the_mirror_image(self):
		self.assert_reachable(self.elsewhere, self.membership_elsewhere, "own district")
		self.assert_unreachable(self.elsewhere, self.membership_here, "other society")

	def test_a_user_without_the_role_is_denied_everywhere(self):
		"""Holding no scope role grants nothing, wherever they are."""
		self.assert_unreachable(self.outsider, self.membership_here, "no role")
		self.assert_unreachable(self.outsider, self.membership_elsewhere, "no role")

	def test_pointing_the_setting_at_another_role_changes_who_sees_what(self):
		"""Zero code diff: the society's choice of role is the whole mechanism."""
		self.assert_reachable(self.here, self.membership_here, "under the scope role")

		# The applicant role is real, but nobody holds a Geo Assignment under it.
		fixtures.set_scope_role(fixtures.APPLICANT_ROLE)

		self.assert_unreachable(self.here, self.membership_here, "after the role changed")

	def test_an_administrator_is_unaffected(self):
		self.assert_reachable("Administrator", self.membership_here, "admin")
		self.assert_reachable("Administrator", self.membership_elsewhere, "admin")


class TestTheEmptyDefaultIsSafe(ScopingTestCase):
	"""The shipped state: no role chosen, so nobody but an administrator reads one.

	This is the pre-portal state a society installs into. Memberships carry
	personal data, so "not configured yet" has to mean closed — and the
	assertion pairs the denial with the administrator still getting through,
	because a default that locked everybody out including the person who has to
	fix it would be a different bug.
	"""

	def setUp(self):
		super().setUp()
		fixtures.set_scope_role(None)

	def test_the_setting_ships_empty(self):
		"""The patch installs the field without choosing a value."""
		from onerc_core.access.services import registry

		registration = registry.for_doctype(fixtures.MEMBERSHIP_DOCTYPE)

		self.assertIsNone(registry.resolve_role(registration))

	def test_a_role_holder_is_denied(self):
		"""Even the user who would be in scope, were a role configured."""
		self.assert_unreachable(self.here, self.membership_here, "empty setting")

	def test_everyone_non_admin_is_denied(self):
		self.assert_unreachable(self.elsewhere, self.membership_elsewhere, "empty setting")
		self.assert_unreachable(self.outsider, self.membership_here, "empty setting")

	def test_an_administrator_can_still_get_in_to_configure_it(self):
		"""Otherwise the safe default would be an unrecoverable one."""
		self.assert_reachable("Administrator", self.membership_here, "admin under empty setting")

	def test_it_fails_closed_rather_than_open(self):
		"""Asserted at the layer itself: deny-all, not "no filter"."""
		from onerc_core.access.services.enforcement import DENY_ALL, get_permission_query_conditions

		self.assertEqual(get_permission_query_conditions(self.here, fixtures.MEMBERSHIP_DOCTYPE), DENY_ALL)

	def test_the_denial_is_logged_not_silent(self):
		"""Core's detectable signal, reached through vmmsx's registration.

		The whole reason `role_from_setting` was worth building: an unconfigured
		scope role denies everybody, and that must be visible rather than looking
		like "nobody has been granted anything yet".
		"""
		from onerc_core.access.services.registry import UNRESOLVED_ROLE_LOG_TITLE

		before = frappe.db.count("Error Log", {"method": UNRESOLVED_ROLE_LOG_TITLE})

		self.assert_unreachable(self.here, self.membership_here, "empty setting")

		self.assertGreater(
			frappe.db.count("Error Log", {"method": UNRESOLVED_ROLE_LOG_TITLE}),
			before,
			"an unconfigured scope role denied everybody silently",
		)


class TestABadRoleIsRefusedAtConfigTime(ScopingTestCase):
	"""Core's config-time guard fires for vmmsx's registration specifically.

	The guard iterates settings-backed registrations. If vmmsx's registration
	were malformed, or named a field core could not see, the guard would simply
	not fire for it — so this proves participation, not just that core has a
	guard somewhere.
	"""

	def save_settings_with(self, role: str | None):
		settings = frappe.get_doc(fixtures.SETTINGS_DOCTYPE)

		for fieldname in ("organization_name", "organization_short_name"):
			if not settings.get(fieldname):
				settings.set(fieldname, f"{fixtures.TEST_PREFIX} Society")

		if not settings.get("primary_language"):
			settings.set("primary_language", frappe.db.get_value("Language", {"name": "en"}) or "en")

		settings.set(fixtures.SCOPE_ROLE_SETTING, role)
		settings.save()
		frappe.clear_document_cache(fixtures.SETTINGS_DOCTYPE, fixtures.SETTINGS_DOCTYPE)

	def test_a_nonexistent_role_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_settings_with(NONEXISTENT_ROLE)

	def test_the_refusal_names_the_bad_role(self):
		"""Whichever layer refuses it, the message has to say what was wrong."""
		with self.assertRaises(frappe.ValidationError):
			self.save_settings_with(NONEXISTENT_ROLE)

		message = frappe.as_json(frappe.message_log[-1] if frappe.message_log else {})

		self.assertIn(NONEXISTENT_ROLE, message)

	def test_the_link_fieldtype_is_the_first_line_of_defence(self):
		"""Two layers, and this one gets there first.

		Because vmmsx installs the setting as a **Link to Role**, Frappe's own
		link validation rejects an unknown role before core's scope-role guard
		is reached. That is why the message above is Frappe's rather than core's,
		and it is a better outcome than either alone: the desk offers only real
		roles, and core still catches a value that got in another way — a role
		deleted after it was chosen, or a migration writing the field directly.
		"""
		field = frappe.get_meta(fixtures.SETTINGS_DOCTYPE).get_field(fixtures.SCOPE_ROLE_SETTING)

		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Role")

	def test_vmmsx_registration_participates_in_cores_config_guard(self):
		"""The participation assertion, made directly rather than inferred.

		Core's guard iterates the settings-backed registrations it can see. If
		vmmsx's registration were malformed, or used a literal role, it would
		simply not appear here and the guard would never fire for memberships —
		silently. So the membership entry is asserted to be in that list, by the
		key core reads it under.
		"""
		from onerc_core.access.services import registry

		backed = {
			entry["doctype"]: entry[registry.ROLE_SETTING_KEY]
			for entry in registry.settings_backed_registrations()
		}

		self.assertIn(fixtures.MEMBERSHIP_DOCTYPE, backed)
		self.assertEqual(backed[fixtures.MEMBERSHIP_DOCTYPE], fixtures.SCOPE_ROLE_SETTING)

	def test_cores_guard_is_what_refuses_once_link_validation_is_out_of_the_way(self):
		"""Core's guard, reached by taking the earlier layer away.

		Frappe's link validation runs before the controller's `validate` on this
		doctype, so for a Link field it always gets there first — core's
		scope-role guard is genuinely the *second* line here, not the first.
		`ignore_links` removes the first line, which is the only way to observe
		the second one working, and is also exactly what a migration writing
		settings programmatically would do.

		The message names the doctype, which is what makes it core's guard and
		not Frappe's: link validation knows only the field.
		"""
		fixtures.set_scope_role(NONEXISTENT_ROLE)

		settings = frappe.get_doc(fixtures.SETTINGS_DOCTYPE)
		settings.flags.ignore_links = True

		with self.assertRaises(frappe.ValidationError):
			settings.save()

		message = frappe.as_json(frappe.message_log[-1] if frappe.message_log else {})

		self.assertIn(NONEXISTENT_ROLE, message)
		self.assertIn(fixtures.MEMBERSHIP_DOCTYPE, message)

	def test_a_real_role_saves(self):
		"""Guards the test above: the save works when the role is real."""
		self.save_settings_with(fixtures.SCOPE_ROLE)

		self.assertEqual(
			frappe.db.get_single_value(fixtures.SETTINGS_DOCTYPE, fixtures.SCOPE_ROLE_SETTING),
			fixtures.SCOPE_ROLE,
		)

	def test_leaving_it_empty_saves(self):
		"""Not yet configured is not a misconfiguration."""
		self.save_settings_with(None)

		self.assertFalse(frappe.db.get_single_value(fixtures.SETTINGS_DOCTYPE, fixtures.SCOPE_ROLE_SETTING))
