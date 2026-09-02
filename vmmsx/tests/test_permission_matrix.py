# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Seven identities against the surfaces the last five phases added.

Each module tests its own door. This asserts the property that only shows up
across them: that **the same person is refused the same things everywhere**, and
that the doors that were opened for one purpose did not quietly open for
another.

The identities, and what each is for:

    administrator        core's documented scope bypass. Must reach everything,
                         because a site where nobody can get in is unrecoverable
    coordinator          a scope role at one branch. The ordinary staff member
    outsider             the same role at a *different* branch. Everything about
                         them is right except where they are
    unplaced staff       the role and no assignment at all. Fails closed
    volunteer            no desk role and no assignment, and their own work
    other volunteer      the same, and somebody else's work
    guest                not signed in

**The two questions are deliberately separate.** Geo scope governs a
coordinator's door — may you act on records *here* — and ownership governs a
volunteer's — is this record *yours*. Neither is a way into the other, and the
cases below are arranged so that a failure says which one broke.
"""

import frappe

from vmmsx.deployment.services import project as project_service
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class MatrixTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.grant_doctype_access("Project", fixtures.DEPLOYMENT_SCOPE_ROLE)
		fixtures.grant_doctype_access(fixtures.DEPLOYMENT_DOCTYPE, fixtures.DEPLOYMENT_SCOPE_ROLE)
		fixtures.grant_doctype_access("VMMS Task", fixtures.DEPLOYMENT_SCOPE_ROLE)

		cls.coordinator = cls.viewer(
			"matrix_coordinator", fixtures.DEPLOYMENT_SCOPE_ROLE, cls.society_a["branch"]
		)
		cls.outsider = cls.viewer(
			"matrix_outsider", fixtures.DEPLOYMENT_SCOPE_ROLE, cls.society_a["other_branch"]
		)
		cls.unplaced = fixtures.make_user("matrix_unplaced")
		frappe.get_doc("User", cls.unplaced).add_roles(fixtures.DEPLOYMENT_SCOPE_ROLE)

	def setUp(self):
		super().setUp()

		self.branch = self.society_a["branch"]
		self.elsewhere = self.society_a["other_branch"]

	def project_here(self):
		return project_service.create(
			project_name=f"{fixtures.TEST_PREFIX} {frappe.generate_hash(length=8)}",
			geo_node=self.branch,
		)


class TestWhoMayOpenAProgrammeOfWork(MatrixTestCase):
	def test_an_administrator_may_anywhere(self):
		"""Core's documented bypass. A site where nobody can get in is
		unrecoverable, which is why this is a rule rather than an oversight."""
		self.assertTrue(project_service.may_anchor(self.society_b["ward"], "Administrator"))

	def test_a_coordinator_may_in_their_own_branch(self):
		self.assertTrue(project_service.may_anchor(self.branch, self.coordinator))

	def test_and_not_in_another(self):
		self.assertFalse(project_service.may_anchor(self.elsewhere, self.coordinator))

	def test_the_outsider_is_the_mirror_image(self):
		"""Everything about them is right except where they are, which is the only
		way to tell a scope rule from a role check."""
		self.assertTrue(project_service.may_anchor(self.elsewhere, self.outsider))
		self.assertFalse(project_service.may_anchor(self.branch, self.outsider))

	def test_somebody_holding_the_role_and_no_assignment_may_nowhere(self):
		"""Fails closed, which is core's direction and the right one for a record
		that says where a society is working."""
		self.assertFalse(project_service.may_anchor(self.branch, self.unplaced))

	def test_a_volunteer_may_nowhere(self):
		volunteer_user = fixtures.make_user("matrix_volunteer")

		self.assertFalse(project_service.may_anchor(self.branch, volunteer_user))


class TestWhoMaySeeAProgrammeOfWork(MatrixTestCase):
	def readable(self, user: str) -> list[str]:
		frappe.set_user(user)

		try:
			return frappe.get_list("Project", pluck="name", limit_page_length=0)
		finally:
			frappe.set_user("Administrator")

	def test_a_coordinator_sees_their_own_branch(self):
		project = self.project_here()

		self.assertIn(project.name, self.readable(self.coordinator))

	def test_and_not_another_branch(self):
		project = self.project_here()

		self.assertNotIn(project.name, self.readable(self.outsider))

	def test_the_query_filter_and_the_document_check_agree(self):
		"""Filtering a list is not access control if the detail view is reachable
		directly. Both layers are core's and both are asked here."""
		from onerc_core.access.services.enforcement import is_in_scope

		project = self.project_here()

		self.assertFalse(is_in_scope("Project", project.vmms_geo_node, self.outsider))
		self.assertNotIn(project.name, self.readable(self.outsider))


class TestWhoMayActOnADeployment(MatrixTestCase):
	def setUp(self):
		super().setUp()

		self.terms = fixtures.make_terms(
			f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}"
		)

	def deployment_here(self):
		return fixtures.make_deployment(self.terms.name, self.branch)

	def readable(self, user: str) -> list[str]:
		frappe.set_user(user)

		try:
			return frappe.get_list(
				fixtures.DEPLOYMENT_DOCTYPE, pluck="name", limit_page_length=0
			)
		finally:
			frappe.set_user("Administrator")

	def test_a_coordinator_sees_deployments_in_their_own_branch(self):
		deployment = self.deployment_here()

		self.assertIn(deployment.name, self.readable(self.coordinator))

	def test_a_coordinator_elsewhere_does_not(self):
		deployment = self.deployment_here()

		self.assertNotIn(deployment.name, self.readable(self.outsider))

	def test_somebody_with_no_assignment_sees_none(self):
		self.deployment_here()

		self.assertEqual(self.readable(self.unplaced), [])


class TestAVolunteersOwnWorkIsTheirs(MatrixTestCase):
	"""Ownership, not scope. A volunteer holds no assignment, correctly, so a
	scope check would refuse every one of them their own work."""

	def volunteer_with_login(self, handle: str):
		profile = fixtures.make_profile("Matrix", handle)
		volunteer = fixtures.make_volunteer(profile, self.branch)
		user = fixtures.make_user(f"matrix_{handle}")
		frappe.db.set_value("Red Profile", profile, "user", user, update_modified=False)

		return volunteer, user

	def test_a_volunteer_reaches_their_own_task_and_not_somebody_elses(self):
		from vmmsx.api import tasks as api
		from vmmsx.task.services import task as task_service

		mine, my_login = self.volunteer_with_login("owner")
		theirs, their_login = self.volunteer_with_login("other")

		task = task_service.assign(
			volunteer=mine.name,
			subject="Count the shelves",
			description="Count what is on the shelves.",
			geo_node=self.branch,
		)

		frappe.set_user(my_login)
		self.assertEqual(api.get_task(task.name)["name"], task.name)

		frappe.set_user(their_login)

		with self.assertRaises(frappe.PermissionError):
			api.accept_task(task.name)

		frappe.set_user("Administrator")

	def test_my_tasks_names_nobody_and_so_cannot_be_pointed_at_anybody(self):
		"""The signature is the guarantee: there is no argument to get wrong."""
		import inspect

		from vmmsx.api import tasks as api

		self.assertEqual(
			set(inspect.signature(api.my_tasks).parameters), {"include_closed"}
		)


class TestGuestReachesNothingOperational(MatrixTestCase):
	def test_a_signed_out_visitor_sees_no_deployment(self):
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}")
		fixtures.make_deployment(terms.name, self.branch)

		frappe.set_user("Guest")

		try:
			with self.assertRaises(frappe.PermissionError):
				frappe.get_list(fixtures.DEPLOYMENT_DOCTYPE, limit_page_length=0)
		finally:
			frappe.set_user("Administrator")

	def test_nor_any_programme_of_work(self):
		self.project_here()
		frappe.set_user("Guest")

		try:
			with self.assertRaises(frappe.PermissionError):
				frappe.get_list("Project", limit_page_length=0)
		finally:
			frappe.set_user("Administrator")
