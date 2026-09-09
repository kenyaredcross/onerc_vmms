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

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.approvals.services import config as approval_config
from vmmsx.registration.services import desk, workspaces
from vmmsx.seed import kenya
from vmmsx.seed import kenya_geography as geography

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

	def test_it_builds_every_county_and_the_sub_counties_under_them(self):
		root = kenya.national()

		self.assertTrue(root)

		counties = frappe.get_all(
			"Geo Node",
			filters={"geo_level": kenya.LEVELS[1]["key"], "parent_geo_node": root},
			pluck="name",
		)

		self.assertEqual(len(counties), len(kenya.COUNTY_NODES))
		self.assertEqual(len(counties), 47)

		subs = frappe.db.count("Geo Node", {"geo_level": kenya.LEVELS[2]["key"]})

		self.assertEqual(subs, geography.total_sub_counties())

	def test_a_sub_county_sits_under_its_own_county(self):
		"""A count can be right while the parentage is wrong, so one is walked."""
		county = kenya.primary_county()
		sub = kenya.sub_county(kenya.PRIMARY_COUNTY, 0)

		self.assertTrue(county)
		self.assertTrue(sub)
		self.assertEqual(frappe.db.get_value("Geo Node", sub, "parent_geo_node"), county)

	def test_the_county_is_the_rung_this_society_records_at(self):
		"""The deepest rung is not the lowest one, and that is the whole design.

		**Asserted on `allowed_anchor_levels`, which is where the rule is
		enforced, and not on `is_lowest_level`, which is a hint** a picker reads.
		The two say the same thing on a site carrying only this seed and come
		apart on a shared bench, because `_geo_levels` deliberately declines to
		take the lowest marker off an incumbent it did not create.

		**Two assertions, and only one of them is unconditional.** The sub-county
		must never be anchorable — that is the requirement, it is what the 290 of
		them not being places records live means, and it holds on every site. The
		exact county-only list is asserted only where this seed actually wrote the
		workflow: `_workflows()` skips a doctype another society already governs,
		correctly, because a workflow is a society's governance and a seed must
		not overwrite one. On a bench seeded for Tanzania first, the anchor levels
		are Tanzania's until `kenya_operations._reconcile_workflows` widens them by
		the county — which is a different module's job and a different test's.
		"""
		self.assertFalse(frappe.db.get_value("Geo Level", kenya.LEVELS[2]["key"], "is_lowest_level"))

		# Read off the workflow this seed's own report names, by docname, rather
		# than through `allowed_anchor_levels_for(doctype)`. That helper resolves
		# `{"workflow_for": doctype}` with no ordering, so on a bench carrying two
		# societies it answers for whichever row the database hands back first —
		# a fine contract for the running app, which has one society, and useless
		# for a test that means "the workflow this run wrote".
		written = [row for row in self.report["workflows"] if row["status"] == "created"]

		if not written:
			self.skipTest("every approvable doctype was already governed; this run wrote no workflow")

		for row in written:
			workflow = frappe.get_doc(kenya.WORKFLOW_DOCTYPE, row["name"])
			levels = [entry.geo_level for entry in workflow.allowed_anchor_levels]

			self.assertEqual(levels, [kenya.LEVELS[1]["key"]], row["key"])

	def test_the_county_takes_the_lowest_marker_when_nothing_else_holds_it(self):
		"""The other half of the rule above, on the site this seed is written for.

		Skipped rather than failed where another society's level holds the marker,
		because declining to overrule it is the documented behaviour and not a
		defect — see `_geo_levels`. Without this test the assertion above would
		pass for a seed that never set the flag at all.
		"""
		incumbent = frappe.db.get_value(
			"Geo Level",
			{"is_active": 1, "is_lowest_level": 1, "name": ("!=", kenya.LEVELS[1]["key"])},
			"name",
		)

		if incumbent:
			self.skipTest(f"{incumbent} holds the lowest marker; this seed does not overrule it")

		self.assertTrue(frappe.db.get_value("Geo Level", kenya.LEVELS[1]["key"], "is_lowest_level"))

	def test_no_county_routes_to_nobody(self):
		"""46 of the 47 counties have no coordinator, and none of them is a dead end.

		Routing is nearest-ancestor, so a county with no coordinator of its own
		walks up to the national root. The seeded approver is placed there as well
		as at Nairobi for exactly this reason: without it, an application filed in
		Kisumu is accepted and then sits in nobody's queue — no error, no ToDo, and
		nothing to notice.
		"""
		from onerc_core.geo.services import adapter

		holders = set(
			frappe.get_all(
				"Geo Assignment",
				filters={"role": kenya.ROLE_VOLUNTEER_APPROVER, "is_active": 1},
				pluck="geo_node",
			)
		)

		self.assertTrue(holders)

		unrouted = [
			label
			for label in kenya.COUNTY_NODES
			if (node := kenya.county_named(label))
			and not adapter.resolve_upward(node, lambda candidate: candidate in holders)
		]

		self.assertEqual(unrouted, [])

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

	def test_the_approver_holds_both_roles_at_nairobi_and_at_the_root(self):
		"""Two placements, and the second one is not redundant.

		Nairobi is where the demo's own content is set and where an application
		filed there resolves without climbing. The national root is what keeps the
		other 46 counties from being dead ends — see `_national_fallback`.
		"""
		for node in (kenya.primary_county(), kenya.national()):
			self.assertTrue(node)

			for role in (kenya.ROLE_VOLUNTEER_APPROVER, kenya.ROLE_MEMBERSHIP_APPROVER):
				self.assertIn(role, frappe.get_roles(kenya.APPROVER_USER), role)
				self.assertTrue(
					frappe.db.exists(
						"Geo Assignment",
						{"user": kenya.APPROVER_USER, "role": role, "geo_node": node, "is_active": 1},
					),
					f"{role} at {node}",
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
		removed = kenya.sub_county(kenya.PRIMARY_COUNTY, 1)

		self.assertTrue(removed)

		frappe.delete_doc("Geo Node", removed, force=True, ignore_permissions=True)

		again = kenya.main(commit=False)
		statuses = {row["key"]: row["status"] for row in again["geo_nodes"]}

		# Sub-counties are reported under "County / Sub-County", because three of
		# the 290 share a name with the county they sit in.
		gone = f"{kenya.PRIMARY_COUNTY} / {kenya.SUB_COUNTY_NODES[1]}"
		kept = f"{kenya.PRIMARY_COUNTY} / {kenya.SUB_COUNTY_NODES[0]}"

		self.assertEqual(statuses[gone], "created")
		self.assertEqual(statuses[kept], "exists")
		self.assertEqual(statuses[kenya.PRIMARY_COUNTY], "exists")
		self.assertEqual(statuses[kenya.NATIONAL_NODE], "exists")


class TestAJourneyThroughTheSeededSociety(SeedTestCase):
	def _require_this_society_governs_applications(self) -> None:
		"""Skip, with a reason, where another society's workflow governs the doctype.

		**Why a skip and not a failure.** `kenya._workflows()` creates a workflow
		for an approvable doctype only if one does not exist, and skips otherwise —
		correctly, because a workflow is a society's governance and a seed must not
		overwrite one. So on a bench seeded for another society first, volunteer
		applications are governed by *their* workflow, and this journey is refused
		before it starts:

		    Nairobi — Kenya Red Cross Society is at County level.
		    VMMS Volunteer Application may only be anchored at: Branch, Sub-Branch.

		That refusal is the anchor rule working, on the configuration the site
		actually has. It is not a defect in this seed and there is nothing this
		test can do about it: registering somewhere the governing workflow accepts
		would be a journey through the other society, which is not what this suite
		is named for. On a site carrying only this seed — which is what
		`seed/kenya_install.py` builds — the check below passes and the journey
		runs.

		`kenya_operations._reconcile_workflows` is what widens a foreign workflow
		by the Kenyan county, and it is deliberately not called here: this class
		tests `kenya.py`.
		"""
		levels = approval_config.allowed_anchor_levels_for(kenya.APPLICATION_DOCTYPE)

		if levels and kenya.LEVELS[1]["key"] not in levels:
			self.skipTest(
				f"{kenya.APPLICATION_DOCTYPE} is governed by a workflow anchoring at {levels},"
				f" which does not admit {kenya.LEVELS[1]['key']} — another society was seeded"
				" on this bench first. Run vmmsx.seed.kenya_operations.main to widen it, or use"
				" a site carrying only the Kenya seed."
			)

	def test_a_person_registers_and_the_seeded_approver_accepts_them(self):
		from vmmsx.api import approvals as approvals_api
		from vmmsx.api import registration as registration_api
		from vmmsx.api import volunteer as volunteer_api

		self._require_this_society_governs_applications()

		applicant = self._website_account()
		# The county, because that is the only rung this society records at. The
		# residence answer below is a sub-county under it, which is what the 290
		# of them are for.
		county = kenya.primary_county()
		home = kenya.sub_county(kenya.PRIMARY_COUNTY, 0)
		id_type = self._identification_type()

		frappe.set_user(applicant)

		try:
			registered = registration_api.register_as_volunteer(
				first_name="Amina",
				last_name="Otieno",
				date_of_birth="1990-01-01",
				geo_node=county,
				country_of_citizenship=kenya.COUNTRY,
				residency_type="Local",
				home_geo_node=home,
				id_type=id_type,
				id_number="SEED-TEST-0001",
				# Required of every volunteer applicant, and "Prefer not to say" is
				# an answer. Passed here for the reason the registration fixtures
				# default it in: a real browser sends it, and this suite is about
				# the seeded society rather than about that requirement.
				disability_status="Prefer not to say",
				declarations_accepted=self._required_declarations(),
				emergency_contacts=[
					{
						"contact_name": "Mercy Otieno",
						"relationship": "Sister",
						"primary_phone": "+254700000001",
						"may_contact_in_emergency": 1,
					}
				],
			)
		finally:
			frappe.set_user("Administrator")

		application = frappe.get_doc(kenya.APPLICATION_DOCTYPE, registered["name"])

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

	def _required_declarations(self) -> list[str]:
		"""Every declaration this society requires, as a browser would send them.

		Read from the live list rather than named, so this suite is about the
		seeded society rather than about which four declarations the app ships.
		"""
		from vmmsx.registration.services import declarations

		return [
			row["name"] for row in declarations.shown_on("VMMS Volunteer Application") if row["is_required"]
		]

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
