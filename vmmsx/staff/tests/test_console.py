# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Which console tabs a person is drawn, and the one that matters is absence.

The console used to show all nine tabs to everybody. The failure that produced
was not a leak — every screen behind a tab was permission-checked and answered
empty — it was that "coordinator" came to mean "everything", because the
interface said so and nobody could tell from looking which of the nine they were
actually meant to use.

So the assertions here are mostly negative. A person holding the society's
deployment role must get the Deployments tab **and not the Stipends one**, and a
volunteer who follows a stale link must get no console at all rather than a
shell of empty screens. A test that only checked what somebody *can* see would
have passed against the old file.

Real roles, real Custom DocPerm rows, real users. `frappe.has_permission` is
what the service asks and it is what these tests set up, rather than a mock of
it: the whole point of the design is that the tab and the write ask the same
question of the same layer.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.content.services import permissions as content_permissions
from vmmsx.staff.services import console, permissions

PREFIX = "CONSOLETEST"

DEPLOYMENT_SETTING = "vmms_deployment_scope_role"
STIPEND_SETTING = "vmms_stipend_report_scope_role"

SETTINGS_DOCTYPE = "National Society Settings"


def make_role(name: str) -> str:
	if not frappe.db.exists("Role", name):
		frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": 1}).insert(
			ignore_permissions=True
		)

	return name


def make_user(email: str, *roles: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": PREFIX,
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		).insert(ignore_permissions=True)

	user = frappe.get_doc("User", email)

	for role in roles:
		if role not in frappe.get_roles(email):
			user.add_roles(role)

	frappe.clear_cache(user=email)

	return email


class TestTheSectionTableIsHonest(IntegrationTestCase):
	"""The table names real doctypes and accounts for every section it orders."""

	def test_every_gated_doctype_exists(self):
		"""A section naming a doctype nobody has is a tab nobody can ever open,
		and it would fail silently — `_readable` skips what is not installed."""
		for entry in (*console.GATED_SECTIONS, *console.ADMIN_SECTIONS):
			for doctype in entry["doctypes"]:
				self.assertTrue(frappe.db.exists("DocType", doctype), doctype)

	def test_the_order_accounts_for_every_section_and_invents_none(self):
		"""`ORDER` is what the sidebar is drawn from, so a section missing from it
		is a tab that can never appear however the permissions fall."""
		named = (
			{entry["section"] for entry in console.GATED_SECTIONS}
			| {entry["section"] for entry in console.ADMIN_SECTIONS}
			| {entry["section"] for entry in console.COMPANION_SECTIONS}
			| set(console.UNGATED_SECTIONS)
		)

		self.assertEqual(set(console.ORDER), named)
		self.assertEqual(len(console.ORDER), len(named), "a section is listed twice")

	def test_a_gated_doctype_is_one_some_installer_grants(self):
		"""A section gated on a doctype no configurable role is ever granted would
		be a tab only an administrator could open, and a society would have no way
		to hand it to anybody.

		Both installers, because there are two: the staff cluster grants from the
		per-doctype scope roles, and the content module grants its own two from
		`vmms_content_editor_role` — a separate setting because who rewrites the
		society's home page is a different question from who runs its register.
		"""
		granted = set(content_permissions.CONTENT_DOCTYPES)

		for _role, doctypes in permissions.role_grants(resolve=False):
			granted.update(doctypes)

		for entry in console.GATED_SECTIONS:
			for doctype in entry["doctypes"]:
				self.assertIn(doctype, granted, f"{entry['section']} -> {doctype}")

	def test_an_admin_section_is_one_no_installer_grants(self):
		"""The mirror of the test above, and the reason `ADMIN_SECTIONS` is a
		separate tuple rather than an exemption inside `GATED_SECTIONS`.

		A section lands there precisely because no configurable role is meant to
		reach it: the form builder changes what every future applicant is asked,
		which is an administrator's act rather than a coordinator's. If an
		installer ever *did* grant one of these doctypes, the section would be
		reachable by a scope role and would belong in `GATED_SECTIONS` — where
		the test above would then hold it to the opposite bar. Asserting it here
		is what stops the two tables drifting into meaning the same thing.
		"""
		granted = set(content_permissions.CONTENT_DOCTYPES)

		for _role, doctypes in permissions.role_grants(resolve=False):
			granted.update(doctypes)

		for entry in console.ADMIN_SECTIONS:
			for doctype in entry["doctypes"]:
				self.assertNotIn(
					doctype,
					granted,
					f"{entry['section']} -> {doctype} is granted to a scope role, so it is not admin-only",
				)

	def test_no_section_is_both_gated_and_admin(self):
		"""One answer to who reaches a tab, not two that could disagree."""
		gated = {entry["section"] for entry in console.GATED_SECTIONS}
		admin = {entry["section"] for entry in console.ADMIN_SECTIONS}
		companion = {entry["section"] for entry in console.COMPANION_SECTIONS}

		self.assertEqual(gated & admin, set())
		self.assertEqual(gated & companion, set())
		self.assertEqual(admin & companion, set())

	def test_a_companion_section_names_a_doctype_this_app_does_not_own(self):
		"""The point of the third tuple.

		`COMPANION_SECTIONS` exists so a section may be gated on a register an
		optional app owns — which is exactly the case `test_every_gated_doctype_
		exists` above cannot cover, because the doctype legitimately does not
		exist on a site without that app. A vmmsx doctype landing here would be
		one escaping that assertion for no reason, so it is refused.
		"""
		for entry in console.COMPANION_SECTIONS:
			for doctype in entry["doctypes"]:
				self.assertFalse(
					doctype.startswith("VMMS "),
					f"{doctype} is this app's own, so it belongs in GATED_SECTIONS",
				)


class TestWhoGetsWhichTabs(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.deployment_role = make_role(f"{PREFIX} Deployment Manager")
		cls.stipend_role = make_role(f"{PREFIX} Stipend Manager")

		frappe.db.set_single_value(SETTINGS_DOCTYPE, DEPLOYMENT_SETTING, cls.deployment_role)
		frappe.db.set_single_value(SETTINGS_DOCTYPE, STIPEND_SETTING, cls.stipend_role)

		# The real installer, so the Custom DocPerm rows these tests read are the
		# ones a society's own migrate would have produced.
		permissions.install()

		cls.deployer = make_user(f"{PREFIX.lower()}-deploy@example.com", cls.deployment_role)
		cls.nobody = make_user(f"{PREFIX.lower()}-nobody@example.com")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def test_the_deployment_role_opens_deployments(self):
		self.assertIn("deployments", console.visible(self.deployer))

	def test_the_deployment_role_does_not_open_stipends(self):
		"""The whole point. Sending people somewhere and paying them for it are
		two jobs, and a society that separated them must see them separated."""
		self.assertNotIn("stipends", console.visible(self.deployer))

	def test_a_scope_role_does_not_open_the_form_builder(self):
		"""The negative that makes the form builder administrator-only real.

		A coordinator holding the society's deployment role runs a register; they
		do not decide what every future applicant is asked. The tab is gated on a
		doctype no installer grants, so this holds without any role name being
		written down anywhere.
		"""
		self.assertNotIn("questions", console.visible(self.deployer))

	def test_the_ungated_sections_ride_along(self):
		"""Overview, the queue, events and analytics have no register of their own
		and are drawn for anybody the console admits at all."""
		sections = console.visible(self.deployer)

		for section in console.UNGATED_SECTIONS:
			self.assertIn(section, sections, section)

	def test_the_sections_come_back_in_sidebar_order(self):
		sections = console.visible(self.deployer)

		self.assertEqual(sections, [key for key in console.ORDER if key in set(sections)])

	def test_somebody_holding_nothing_gets_no_console(self):
		"""Not an empty console — none. A volunteer following a stale link is sent
		back to their own portal rather than shown nine screens that look broken."""
		self.assertEqual(console.visible(self.nobody), [])
		self.assertFalse(console.available(self.nobody))

	def test_an_ungated_section_alone_is_never_a_console(self):
		"""The queue is personal and analytics reports honest zeroes, so either
		would happily answer for a volunteer. Neither is a reason to give somebody
		the console, which is why they do not stand on their own."""
		self.assertFalse(set(console.UNGATED_SECTIONS) & set(console.visible(self.nobody)))

	def test_an_administrator_sees_everything(self):
		"""The framework exemption, and the reason a fresh site is administrable
		before anybody has configured a single scope role."""
		self.assertEqual(console.visible("Administrator"), list(console.ORDER))


class TestTheEndpoint(IntegrationTestCase):
	def test_it_answers_for_the_session_and_takes_no_arguments(self):
		"""Same shape as `approvals.my_queue`: a caller cannot name anybody, so
		there is no check to get wrong."""
		from inspect import signature

		from vmmsx.api import console as endpoint

		self.assertEqual(list(signature(endpoint.sections).parameters), [])

	def test_the_dto_is_built_field_by_field(self):
		from vmmsx.api import console as endpoint

		answer = endpoint.sections()

		self.assertEqual(set(answer), {"available", "sections", "desk", "sms"})
		self.assertIsInstance(answer["available"], bool)
