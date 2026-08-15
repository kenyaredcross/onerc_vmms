# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Shared arrangement for the self-service journey's integration tests.

Frappe rolls the test transaction back once per class, not per method, so the
society — roles, settings, geo, workflows, types — is arranged in `setUpClass`.
A method that configured a setting would still have configured it for the next
method, and the test that then passed would be lying.

Each method makes its own website account and its own registration. Both are
cheap, and one per test is what stops a journey test from inheriting a role
another one granted.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.registration.services import permissions, workspaces
from vmmsx.registration.tests import fixtures

EXTRA_TEST_RECORD_DEPENDENCIES = []


class RegistrationTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.reset()
		fixtures.use_manual_gateway()

		# What this bench had configured before the suite touched it. Restored in
		# `tearDownClass`, which runs after the runner's rollback and therefore
		# writes for real: a suite that left the settings cleared would silently
		# un-configure whatever society was already set up here.
		cls.settings_snapshot = fixtures.snapshot_settings()

		cls.society = fixtures.build_society()
		fixtures.configure_society(cls.society)
		fixtures.make_types()
		fixtures.make_workflows([cls.society["levels"]["county"], cls.society["levels"]["branch"]])

		# Created here, as Administrator, rather than lazily inside the default
		# form payload: submit_volunteer_form() runs under the applicant's own
		# session, which holds no create permission on Identification Type.
		fixtures.make_identification_type()

		# The approver holds one role that does two jobs here: it is what the
		# workflow stages resolve against *and* what both scope settings name, so
		# the person routed to can also open what they were routed. A larger
		# society separates them; the app keeps them in different settings so it
		# can be separated, and this suite is not about that distinction.
		fixtures.grant_doctype_access(fixtures.APPLICATION_DOCTYPE, fixtures.APPROVER_ROLE)
		fixtures.grant_doctype_access(fixtures.MEMBERSHIP_DOCTYPE, fixtures.APPROVER_ROLE)

		cls.approver = fixtures.make_user("branch.approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society["county"])

		# The surfaces are built from the settings, so they are built after them.
		# Every suite needs them, not only the one that asserts on them: a
		# workspace naming this society's roles is what a test user is shown, and
		# the site's own workspaces name the site's own roles.
		workspaces.install()
		permissions.install()

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		fixtures.teardown(cls.settings_snapshot)
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")

	# --- helpers ----------------------------------------------------------

	def branch(self) -> str:
		return self.society["branch"]

	def register_as_volunteer(self, handle: str, **values):
		"""A brand-new website account fills in the volunteer form. Returns both."""
		user = fixtures.website_account(handle)

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(self.branch(), **values)

		return user, frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name)

	def register_as_member(self, handle: str, membership_type: str, **values):
		"""A brand-new website account fills in the membership form."""
		user = fixtures.website_account(handle)

		with fixtures.acting_as(user):
			membership = fixtures.submit_membership_form(self.branch(), membership_type, **values)

		return user, frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

	def approve(self, doctype: str, name: str, reason: str = "Looks right") -> dict:
		"""Decide through the real API gate, as the person it routed to."""
		from vmmsx.api import approvals as approvals_api

		with fixtures.acting_as(self.approver):
			return approvals_api.decide(doctype=doctype, name=name, decision="Approved", reason=reason)

	def profile_of(self, user: str) -> str | None:
		return frappe.db.get_value(fixtures.PROFILE_DOCTYPE, {"user": user}, "name")

	def profile_count(self, user: str) -> int:
		return frappe.db.count(fixtures.PROFILE_DOCTYPE, {"user": user})

	def roles_of(self, user: str) -> set[str]:
		frappe.clear_cache(user=user)

		return set(frappe.get_roles(user))

	def workspaces_of(self, user: str) -> list[str]:
		"""The workspaces this user would be shown, in the order the desk shows them.

		Read through Frappe's own `get_workspaces`, which is what the desk calls,
		so what the test sees is what a person sees rather than a re-derivation of
		the role check.

		**The request cache has to be dropped first, and only in a test.**
		`get_workspaces` is `@request_cache`d: in production one HTTP request
		belongs to one user and the memo is exactly right, but a test process is
		one long request in which several users take turns, so the second caller
		would silently be handed the first caller's workspaces. That is a test
		harness artefact rather than a product bug, and dropping the memo is what
		makes each assertion here about the user it names.
		"""
		from frappe.desk.desktop import get_workspaces

		with fixtures.acting_as(user):
			cache = getattr(frappe.local, "request_cache", None)

			if cache is not None:
				cache.clear()

			return [page["name"] for page in get_workspaces()["pages"]]
