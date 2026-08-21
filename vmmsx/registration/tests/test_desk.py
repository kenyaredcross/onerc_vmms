# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Volunteers, members and applicants are portal people, and stay that way.

The failure this suite exists for is silent in both directions. A self-service
role left with `desk_access` promotes everybody holding it to a System User, and
the symptom is not an error — it is a volunteer who can open `/app` and browse
the society's doctypes, which looks like nothing at all until somebody notices.
And closing the role without moving where those accounts *land* trades that for
the opposite failure: a volunteer who signs in successfully and is dropped on a
desk they cannot open.

So the properties asserted here are the three `desk.install()` has to hold
together — the role is closed, accounts already promoted come back down, and
there is somewhere real to arrive — plus the two rules that keep it from being
destructive: it never touches a role a society did not name, and it never
overwrites a home page somebody chose.

Nothing is mocked. `user_type` is read back off the `User` record, because the
demotion is Frappe's own `Role.update_user_type_on_change` reacting to the save,
and a test that re-derived it would pass for an implementation the framework
disagreed with.
"""

import frappe

from vmmsx.registration.services import desk, workspaces
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestClosingTheDesk(RegistrationTestCase):
	def setUp(self):
		super().setUp()

		# The suite's transaction rolls back once per class, so a method that
		# closed the roles would leave them closed for the next one. Every method
		# starts from "the desk is open", which is also the state a site upgrading
		# to this release is in.
		for role in (fixtures.SELF_SERVICE_ROLE, fixtures.VOLUNTEER_ROLE, fixtures.MEMBER_ROLE):
			frappe.db.set_value("Role", role, {"desk_access": 1, "home_page": None})
			frappe.clear_document_cache("Role", role)

	def test_it_closes_exactly_the_three_roles_the_society_named(self):
		desk.install()

		for role in (fixtures.SELF_SERVICE_ROLE, fixtures.VOLUNTEER_ROLE, fixtures.MEMBER_ROLE):
			self.assertEqual(frappe.db.get_value("Role", role, "desk_access"), 0, role)

	def test_it_does_not_touch_a_role_the_society_did_not_name(self):
		"""The approver works on the desk, and nothing here may take that away."""
		desk.install()

		self.assertEqual(frappe.db.get_value("Role", fixtures.APPROVER_ROLE, "desk_access"), 1)

	def test_every_closed_role_lands_somewhere_in_the_portal(self):
		desk.install()

		for role in (fixtures.SELF_SERVICE_ROLE, fixtures.VOLUNTEER_ROLE, fixtures.MEMBER_ROLE):
			self.assertEqual(frappe.db.get_value("Role", role, "home_page"), desk.PORTAL_HOME, role)

	def test_a_home_page_the_society_chose_is_left_alone(self):
		frappe.db.set_value("Role", fixtures.VOLUNTEER_ROLE, "home_page", "/home")
		frappe.clear_document_cache("Role", fixtures.VOLUNTEER_ROLE)

		desk.install()

		self.assertEqual(frappe.db.get_value("Role", fixtures.VOLUNTEER_ROLE, "home_page"), "/home")

	def test_running_it_twice_changes_nothing_the_second_time(self):
		desk.install()
		again = {row["role"]: row["status"] for row in desk.install()}

		self.assertTrue(again)
		self.assertEqual(set(again.values()), {"exists"})

	def test_a_role_the_setting_names_but_nobody_has_created_is_reported_not_raised(self):
		"""A deleted role is a configuration fault, not a reason to fail a migrate."""
		self.assertEqual(
			desk.close("VMMSX No Such Role"), {"role": "VMMSX No Such Role", "status": "missing"}
		)


class TestWhatHappensToAccounts(RegistrationTestCase):
	# The roles this suite is measuring. Anything else an account picks up is
	# another app's, and `_account()` neutralises it — see that docstring.
	OURS = (
		fixtures.SELF_SERVICE_ROLE,
		fixtures.VOLUNTEER_ROLE,
		fixtures.MEMBER_ROLE,
		fixtures.APPROVER_ROLE,
	)

	def setUp(self):
		super().setUp()

		for role in (fixtures.SELF_SERVICE_ROLE, fixtures.VOLUNTEER_ROLE, fixtures.MEMBER_ROLE):
			frappe.db.set_value("Role", role, {"desk_access": 1, "home_page": None})
			frappe.clear_document_cache("Role", role)

	def _account(self, handle: str, roles: list[str]) -> str:
		"""An account whose desk access depends on this society's roles alone.

		**Other installed apps grant desk roles of their own on `after_insert`.**
		On the bench this was written against, Raven ships a role carrying
		`desk_access` and adds it to any account that is a System User when it is
		created — which `fixtures.make_user` always is, because it builds staff.
		A self-registered account never meets that condition, so this is an
		artefact of the fixture rather than something production hits; but left
		alone it would make every assertion below a statement about which apps
		happen to be installed rather than about this one.

		So a role the society did not name has its desk access removed for the
		length of the test, which the runner rolls back. `set_value` rather than a
		save, deliberately: saving another app's Role would fire its own
		`update_user_type_on_change` and start demoting accounts that have nothing
		to do with this suite.
		"""
		user = fixtures.make_user(handle, roles)

		held = frappe.get_all("Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role")

		for role in held:
			if role not in self.OURS:
				frappe.db.set_value("Role", role, "desk_access", 0)
				frappe.clear_document_cache("Role", role)

		return user

	def test_an_account_holding_only_a_self_service_role_is_demoted(self):
		user = self._account("desk.volunteer", [fixtures.VOLUNTEER_ROLE])

		self.assertEqual(frappe.db.get_value("User", user, "user_type"), "System User")

		desk.install()

		self.assertEqual(frappe.db.get_value("User", user, "user_type"), "Website User")

	def test_somebody_who_also_works_for_the_society_keeps_their_desk(self):
		"""A coordinator who also volunteers is one person with two jobs."""
		user = self._account("desk.both", [fixtures.VOLUNTEER_ROLE, fixtures.APPROVER_ROLE])

		desk.install()

		self.assertEqual(frappe.db.get_value("User", user, "user_type"), "System User")

	def test_a_demoted_account_is_offered_no_desk_tile_to_land_on(self):
		"""The apps screen decides where a website account goes after signing in.

		A tile routing to `/desk` would send them to a permission error, so both
		of this app's gates have to answer no once the account is a website one.
		"""
		user = self._account("desk.tile", [fixtures.VOLUNTEER_ROLE])
		desk.install()

		frappe.set_user(user)

		self.assertFalse(workspaces.has_self_service_access())


class TestTheFirstThingANewAccountIsToldToDo(RegistrationTestCase):
	"""`on_user_insert` — where the welcome email's link puts somebody afterwards."""

	def _make(self, handle: str, user_type: str, **extra) -> str:
		email = f"{handle}{fixtures.USER_DOMAIN}"

		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True)

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": handle,
				"enabled": 1,
				"user_type": user_type,
				"send_welcome_email": 0,
				**extra,
			}
		)
		user.flags.ignore_permissions = True
		user.insert()

		return email

	def test_a_new_website_account_is_pointed_at_the_portal(self):
		user = self._make("redirect.website", "Website User")

		self.assertEqual(frappe.db.get_value("User", user, "redirect_url"), desk.PORTAL_HOME)

	def test_a_desk_account_is_left_to_the_framework(self):
		"""Frappe derives `user_type` from the roles, so this one has to hold one."""
		user = self._make("redirect.desk", "System User", roles=[{"role": fixtures.APPROVER_ROLE}])

		self.assertEqual(frappe.db.get_value("User", user, "user_type"), "System User")
		self.assertFalse(frappe.db.get_value("User", user, "redirect_url"))

	def test_a_destination_somebody_set_deliberately_is_not_overwritten(self):
		user = self._make("redirect.chosen", "Website User", redirect_url="/home")

		self.assertEqual(frappe.db.get_value("User", user, "redirect_url"), "/home")


class TestWhereSigningInLands(RegistrationTestCase):
	"""`on_session_creation` — the one lever that beats every role's home page.

	**The failure this holds shut is not visible from this app's own source.**
	`get_home_page()` walks `frappe.get_roles()` and takes the first role that
	carries a home page, in the order the `Has Role` rows happen to have been
	written. A companion app that grants every new account a role of its own —
	Buzz does exactly that from a `User` `after_insert` hook, with a fixture
	carrying `home_page = /dashboard`, which Buzz then redirects to `/b` — wins
	that walk for every volunteer, member and coordinator on the site. No amount
	of correctness on `close()`'s own roles can out-vote it, which is why the
	answer is a request-local flag set before the walk happens rather than
	another write to a Role.

	**Asserted on the flag rather than through `get_home_page()`, and that is
	the framework's doing rather than a shortcut.** `get_home_page()` reads
	`if frappe.local.flags.home_page and not frappe.in_test` — it deliberately
	ignores the flag under test, so calling it here would assert the *absence*
	of the mechanism this suite exists to prove. What is left to hold is that the
	hook sets the flag, for the right people, with the right value; that the
	framework then honours it is Frappe's own contract and its own tests'.
	"""

	def setUp(self):
		super().setUp()

		self.addCleanup(setattr, frappe.local.flags, "home_page", None)
		frappe.local.flags.home_page = None

	def landing_for(self, user: str):
		"""Where the login round trip would put this person, or None for none."""
		frappe.set_user(user)
		frappe.local.flags.home_page = None
		desk.on_session_creation()

		return frappe.local.flags.home_page

	def test_a_role_with_its_own_home_page_does_not_win(self):
		"""The Buzz case, reproduced with a role of this suite's own.

		Named nothing after Buzz on purpose: the property is "a competing home
		page loses", not "Buzz loses", and a test that needed Buzz installed
		would silently stop testing anything on a site without it.
		"""
		competitor = f"{fixtures.TEST_PREFIX} Competing App User"

		if not frappe.db.exists("Role", competitor):
			frappe.get_doc(
				{"doctype": "Role", "role_name": competitor, "desk_access": 0}
			).insert(ignore_permissions=True)

		frappe.db.set_value("Role", competitor, "home_page", "/somewhere-else")

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"landing.competing{fixtures.USER_DOMAIN}",
				"first_name": "Landing",
				"send_welcome_email": 0,
				"user_type": "Website User",
				"roles": [{"role": competitor}],
			}
		)
		user.flags.ignore_permissions = True
		user.insert()
		frappe.clear_cache(user=user.name)

		self.assertEqual(self.landing_for(user.name), desk.PORTAL_HOME)

	def test_an_ordinary_website_account_lands_in_the_portal(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"landing.ordinary{fixtures.USER_DOMAIN}",
				"first_name": "Landing",
				"send_welcome_email": 0,
				"user_type": "Website User",
			}
		)
		user.flags.ignore_permissions = True
		user.insert()

		self.assertEqual(self.landing_for(user.name), desk.PORTAL_HOME)

	def test_the_administrator_is_sent_to_the_desk_by_name(self):
		"""Named rather than left to the framework, which is the whole point.

		An early `return` here would look like the conservative choice and be the
		bug: the Administrator holds every role on the site, including the
		companion app's, so falling through to the role walk sends the account a
		society is configured from into somebody else's dashboard.
		"""
		self.assertEqual(self.landing_for(desk.DESK_ACCOUNT), desk.DESK_HOME)

	def test_the_portal_tile_is_shown_to_everybody_but_the_desk_account(self):
		"""`has_portal_access` — the apps-screen gate, and why it is wide.

		A tile is where a Website User's login is *sent*: `get_default_path()`
		reads the apps screen before `get_home_page()` for those accounts, so a
		missing tile is not a missing icon, it is a login that lands in whichever
		other app has one. Every person of this society has a portal, coordinator
		included, so the only account this refuses is the framework's own.
		"""
		frappe.set_user(desk.DESK_ACCOUNT)
		self.assertFalse(desk.has_portal_access())

		frappe.set_user("Guest")
		self.assertFalse(desk.has_portal_access())
