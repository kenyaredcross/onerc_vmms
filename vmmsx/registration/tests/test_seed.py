# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Kenya seed, run for real, and a journey driven through what it produced.

A seed nobody runs is a script that used to work. This suite runs the actual
`vmmsx.seed.kenya.main()` — every role, level, node, type, workflow, setting and
workspace it creates — and then registers a person against that configuration
and has the *seeded* approver accept them.

`commit=False`, so the seed writes inside the transaction the test runner rolls
back. That matters: a seeded demo society appearing on whichever site somebody
ran the suite against would be a test with a side effect nobody asked for.

**This suite arranges its own society only to the extent of getting out of the
way.** It does not build geo or roles: the seed does that, which is the thing
under test.
"""

import json

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.registration.services import desk, workspaces
from vmmsx.seed import kenya

EXTRA_TEST_RECORD_DEPENDENCIES = []

APPLICANT = "seed.applicant@registration.test"


class SeedTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.report = kenya.main(commit=False)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")


class TestWhatTheSeedCreates(SeedTestCase):
	def test_it_creates_every_role_the_society_needs(self):
		for name, _, _desk in kenya.ROLES:
			self.assertTrue(frappe.db.exists("Role", name), name)

	def test_each_role_reaches_the_surface_it_is_for(self):
		"""The seed's third column is the difference between the desk and the portal.

		An approver works on the society's records and is shown a workspace, which
		needs desk access. A volunteer, a member and an applicant are shown the
		portal, and desk access would hand them `/app` — see
		`registration/services/desk.py`, which holds the same line on every
		migrate for whichever roles a society has named.
		"""
		for name, _, desk_access in kenya.ROLES:
			self.assertEqual(frappe.db.get_value("Role", name, "desk_access"), int(desk_access), name)

	def test_a_portal_role_has_somewhere_in_the_portal_to_land(self):
		"""Without it, signing in falls through to Portal Settings and reaches /desk."""
		for name, _, desk_access in kenya.ROLES:
			if desk_access:
				continue

			self.assertEqual(frappe.db.get_value("Role", name, "home_page"), desk.PORTAL_HOME, name)

	def test_it_creates_the_three_level_ladder_in_order(self):
		orders = [frappe.db.get_value("Geo Level", level["key"], "geo_level_order") for level in kenya.LEVELS]

		self.assertEqual(orders, [1, 2, 3])

	def test_only_the_top_level_may_stand_alone(self):
		flags = [frappe.db.get_value("Geo Level", level["key"], "requires_parent") for level in kenya.LEVELS]

		self.assertEqual(flags, [0, 1, 1])

	def test_it_builds_a_tree_two_branches_deep_under_one_county(self):
		county = kenya.county(0)
		branch = kenya.branch(0)

		self.assertTrue(county)
		self.assertTrue(branch)
		self.assertEqual(frappe.db.get_value("Geo Node", branch, "parent_geo_node"), county)

	def test_it_creates_one_fee_bearing_auto_type_and_one_routed_type(self):
		auto = frappe.get_doc("VMMS Membership Type", kenya.TYPE_ORDINARY)
		routed = frappe.get_doc("VMMS Membership Type", kenya.TYPE_LIFE)

		self.assertEqual(auto.approval_mode, "auto_on_payment")
		self.assertGreater(auto.fee_amount, 0)
		self.assertEqual(auto.duration_days, 365)
		self.assertEqual(routed.approval_mode, "routed")

	def test_the_fee_is_in_the_society_currency_rather_than_an_assumed_one(self):
		auto = frappe.get_doc("VMMS Membership Type", kenya.TYPE_ORDINARY)

		self.assertEqual(auto.fee_currency, kenya.CURRENCY)

	def test_both_types_point_at_a_certificate_template_that_exists(self):
		for key in (kenya.TYPE_ORDINARY, kenya.TYPE_LIFE):
			template = frappe.db.get_value("VMMS Membership Type", key, "template_key")

			self.assertTrue(template, key)
			self.assertTrue(frappe.db.exists("VMMS Template", template), key)

	def test_it_creates_a_workflow_for_each_approvable_doctype(self):
		for doctype in (kenya.APPLICATION_DOCTYPE, kenya.MEMBERSHIP_DOCTYPE):
			self.assertTrue(frappe.db.exists("VMMS Approval Workflow", {"workflow_for": doctype}), doctype)

	def test_each_workflow_has_a_stage_resolving_to_a_role_by_nearest_ancestor(self):
		for doctype, role in (
			(kenya.APPLICATION_DOCTYPE, kenya.ROLE_VOLUNTEER_APPROVER),
			(kenya.MEMBERSHIP_DOCTYPE, kenya.ROLE_MEMBERSHIP_APPROVER),
		):
			name = frappe.db.get_value("VMMS Approval Workflow", {"workflow_for": doctype}, "name")
			workflow = frappe.get_doc("VMMS Approval Workflow", name)

			self.assertEqual(len(workflow.stages), 1, doctype)
			self.assertEqual(workflow.stages[0].required_role, role, doctype)
			self.assertEqual(workflow.stages[0].resolution_rule, "nearest_ancestor", doctype)
			self.assertTrue(workflow.stages[0].can_reject, doctype)

	def test_each_workflow_narrows_where_a_record_may_be_anchored(self):
		"""ACC-03 in data, which is the only place it may be."""
		for doctype in (kenya.APPLICATION_DOCTYPE, kenya.MEMBERSHIP_DOCTYPE):
			name = frappe.db.get_value("VMMS Approval Workflow", {"workflow_for": doctype}, "name")
			workflow = frappe.get_doc("VMMS Approval Workflow", name)

			self.assertTrue(workflow.allowed_anchor_levels, doctype)

	def test_the_approver_holds_both_roles_at_a_county(self):
		county = kenya.county(0)

		for role in (kenya.ROLE_VOLUNTEER_APPROVER, kenya.ROLE_MEMBERSHIP_APPROVER):
			self.assertIn(role, frappe.get_roles(kenya.APPROVER_USER), role)
			self.assertTrue(
				frappe.db.exists(
					"Geo Assignment",
					{"user": kenya.APPROVER_USER, "role": role, "geo_node": county, "is_active": 1},
				),
				role,
			)

	def test_every_role_setting_this_app_owns_names_a_role_that_exists(self):
		"""Nothing may be left fail-closed in a demo, and nothing may be invented."""
		from vmmsx.member.services.society import MEMBER_ROLE_FIELD as MEMBERSHIP_MEMBER_ROLE
		from vmmsx.member.services.society import PRINT_ROLE_FIELD
		from vmmsx.registration.services.society import SELF_SERVICE_ROLE_FIELD
		from vmmsx.volunteer.services.society import MEMBER_ROLE_FIELD as VOLUNTEER_MEMBER_ROLE

		settings = frappe.get_cached_doc(kenya.SETTINGS_DOCTYPE)

		for field in (
			"vmms_volunteer_scope_role",
			"vmms_membership_scope_role",
			PRINT_ROLE_FIELD,
			VOLUNTEER_MEMBER_ROLE,
			MEMBERSHIP_MEMBER_ROLE,
			SELF_SERVICE_ROLE_FIELD,
		):
			value = settings.get(field)

			self.assertTrue(value, field)
			self.assertTrue(frappe.db.exists("Role", value), f"{field} -> {value}")

	def test_signup_is_open_and_a_new_account_gets_the_self_service_role(self):
		self.assertFalse(frappe.db.get_single_value("Website Settings", "disable_signup"))
		self.assertEqual(frappe.db.get_single_value("Portal Settings", "default_role"), kenya.ROLE_APPLICANT)

	def test_it_installs_the_three_workspaces(self):
		for label in (workspaces.LANDING, workspaces.VOLUNTEER, workspaces.MEMBERSHIP):
			self.assertTrue(frappe.db.exists("Workspace", label), label)

	def test_it_says_out_loud_what_it_will_not_do(self):
		"""The logo is a real file and a seed may not invent one."""
		self.assertTrue(any("logo" in step for step in self.report["manual_steps"]))

	def test_the_logo_is_reported_as_manual_rather_than_faked(self):
		logo = next(row for row in self.report["society"] if row["key"] == "logo")

		self.assertIn("manual", logo["status"])
		self.assertFalse(frappe.db.get_single_value(kenya.SETTINGS_DOCTYPE, "logo"))


class TestItIsIdempotent(SeedTestCase):
	def test_a_second_run_creates_nothing(self):
		again = kenya.main(commit=False)

		for section in ("roles", "geo_levels", "geo_nodes", "membership_types", "workflows"):
			statuses = {row["status"] for row in again[section]}

			self.assertEqual(statuses, {"exists"}, section)

	def test_a_second_run_leaves_the_geo_tree_the_same_size(self):
		before = frappe.db.count("Geo Node")
		kenya.main(commit=False)

		self.assertEqual(frappe.db.count("Geo Node"), before)

	def test_it_can_tell_a_creation_from_a_find(self):
		"""Without this, the two tests above would pass for a seed that did nothing.

		A seed reporting `exists` unconditionally and writing nothing would look
		perfectly idempotent. So one seeded row is removed and the seed run again:
		that row has to come back reported as created, and its neighbours have to
		still report exists.

		A leaf geo node is used because nothing links to one, so removing it
		cannot fail for a reason that has nothing to do with what is being
		tested.
		"""
		removed = kenya.branch(1)

		self.assertTrue(removed)

		frappe.delete_doc("Geo Node", removed, force=True, ignore_permissions=True)

		again = kenya.main(commit=False)
		statuses = {row["key"]: row["status"] for row in again["geo_nodes"]}

		self.assertEqual(statuses[kenya.BRANCH_NODES[1]], "created")
		self.assertEqual(statuses[kenya.BRANCH_NODES[0]], "exists")
		self.assertEqual(statuses[kenya.NATIONAL_NODE], "exists")


class TestAJourneyThroughTheSeededSociety(SeedTestCase):
	def test_a_person_registers_and_the_seeded_approver_accepts_them(self):
		from frappe.website.doctype.web_form.web_form import accept

		from vmmsx.api import approvals as approvals_api
		from vmmsx.api import volunteer as volunteer_api

		applicant = self._website_account()
		branch = kenya.branch(0)
		id_type = self._identification_type()

		frappe.set_user(applicant)

		try:
			application = accept(
				web_form="register-as-a-volunteer",
				data=json.dumps(
					{
						"applicant_first_name": "Amina",
						"applicant_last_name": "Otieno",
						"geo_node": branch,
						"country_of_citizenship": kenya.COUNTRY,
						"residency_type": "Local",
						"home_geo_node": branch,
						"id_type": id_type,
						"id_number": "SEED-TEST-0001",
					}
				),
			)
		finally:
			frappe.flags.in_web_form = False
			frappe.set_user("Administrator")

		self.assertEqual(application.approval_state, "In Review")

		queued = frappe.get_all(
			"ToDo",
			filters={
				"reference_type": kenya.APPLICATION_DOCTYPE,
				"reference_name": application.name,
				"status": ("in", ("Open", "Overdue")),
			},
			pluck="allocated_to",
		)

		self.assertEqual(queued, [kenya.APPROVER_USER])

		frappe.set_user(kenya.APPROVER_USER)

		try:
			approvals_api.decide(
				doctype=kenya.APPLICATION_DOCTYPE,
				name=application.name,
				decision="Approved",
				reason="Welcome",
			)
		finally:
			frappe.set_user("Administrator")

		application.reload()

		self.assertEqual(application.approval_state, "Approved")
		self.assertEqual(frappe.db.get_value("VMMS Volunteer", application.volunteer, "status"), "Active")

		frappe.clear_cache(user=applicant)

		self.assertIn(kenya.ROLE_VOLUNTEER, frappe.get_roles(applicant))

		frappe.set_user(applicant)

		try:
			mine = volunteer_api.my_volunteer()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(mine["volunteer"], application.volunteer)
		self.assertEqual(mine["full_name"], "Amina Otieno")

	def _website_account(self) -> str:
		"""What Frappe's signup produces, once Portal Settings names a default role."""
		if frappe.db.exists("User", APPLICANT):
			frappe.delete_doc("User", APPLICANT, force=True)

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": APPLICANT,
				"first_name": "Seed Applicant",
				"send_welcome_email": 0,
			}
		).insert()
		user.add_roles(frappe.db.get_single_value("Portal Settings", "default_role"))
		frappe.clear_cache(user=APPLICANT)

		return APPLICANT

	def _identification_type(self) -> str:
		"""An Identification Type, required to submit — created as Administrator,
		before the session switches to the applicant, who holds no create
		permission on it.
		"""
		key = "seed-test-national-id"

		if not frappe.db.exists("Identification Type", key):
			frappe.get_doc(
				{
					"doctype": "Identification Type",
					"identification_type_key": key,
					"identification_type_name": "Seed Test National ID",
					"is_active": 1,
				}
			).insert()

		return key
