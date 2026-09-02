# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The programme of work is ERPNext's `Project`, and vmmsx owns three things on it.

`VMMS Project` was retired. What replaced it is not a rename: it is ERPNext's own
record, with its identity, type, priority, progress, Company, cost centre and
dashboard, plus a Custom Field block this app owns — the owning Geo Node, the
donor, and the risks and assumptions. `setup/project_fields.py` is the whole of
that list and `deployment/services/project.py` is the whole of the behaviour.

Three things are worth asserting rather than believing:

1. **Company and Geo Node are different questions.** ERPNext's Company is the
   legal entity; `vmms_geo_node` is ACC-02, the branch that owns the programme.
   Both are mandatory and neither substitutes for the other.
2. **A coordinator may only file a programme where they run.** Enforced on the
   server, through core's own enforcement layer rather than a second scope model,
   and enforced on the doctype itself so the desk form meets the same rule the
   endpoint does.
3. **A reliable default, or none at all.** Somebody with one live assignment gets
   their node filled in. Somebody with two gets nothing, and is asked — because
   guessing which of a person's areas they meant is how a programme lands in the
   wrong branch's register.
"""

import frappe

from vmmsx.deployment.services import project as project_service
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase
from vmmsx.setup.project_fields import FIELDS, GEO_NODE_FIELD

EXTRA_TEST_RECORD_DEPENDENCIES = []


class ProjectTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.grant_doctype_access(project_service.PROJECT_DOCTYPE, fixtures.DEPLOYMENT_SCOPE_ROLE)

	def open_project(self, geo_node: str | None = None, **values):
		"""A programme at a node, made as Administrator. Scenery, not the rule."""
		return project_service.create(
			project_name=f"{fixtures.TEST_PREFIX} {frappe.generate_hash(length=8)}",
			geo_node=geo_node or self.society_a["branch"],
			**values,
		)


class TestTheRetirementIsComplete(ProjectTestCase):
	"""`VMMS Project` is gone, and what it did is done by something that exists."""

	def test_the_old_doctype_is_not_on_the_site(self):
		self.assertFalse(frappe.db.exists("DocType", "VMMS Project"))

	def test_every_field_this_app_adds_is_installed(self):
		"""The installer runs on every migrate, so a missing one is a real fault.

		It is not cosmetic: `hooks.py` registers `Project` as scopeable on
		`vmms_geo_node`, and core throws on every Project list view if the
		registration names a field that is not there.
		"""
		meta = frappe.get_meta(project_service.PROJECT_DOCTYPE)

		for field in FIELDS:
			self.assertTrue(meta.get_field(field["fieldname"]), field["fieldname"])

	def test_the_anchor_is_the_field_core_was_told_to_scope_on(self):
		from onerc_core.access.services import registry

		self.assertEqual(
			registry.geo_node_field(project_service.PROJECT_DOCTYPE), GEO_NODE_FIELD
		)

	def test_no_terms_of_reference_still_points_at_the_old_doctype(self):
		"""The link was repointed rather than blanked. `adopt_standard_project` says why."""
		self.assertEqual(
			frappe.get_meta(fixtures.TERMS_DOCTYPE).get_field("project").options,
			project_service.PROJECT_DOCTYPE,
		)


class TestThePlacementIsTwoQuestions(ProjectTestCase):
	def test_a_programme_carries_both_a_company_and_a_geo_node(self):
		project = self.open_project()

		self.assertTrue(project.company)
		self.assertEqual(project.get(GEO_NODE_FIELD), self.society_a["branch"])

	def test_an_unanchored_programme_is_refused_before_the_mandatory_check(self):
		with self.assertRaises(frappe.MandatoryError):
			project_service.create(project_name=f"{fixtures.TEST_PREFIX} nowhere", geo_node=None)

	def test_the_doctype_itself_refuses_one_too(self):
		"""Not only the endpoint. The desk form goes through the controller hook."""
		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc(
				{
					"doctype": project_service.PROJECT_DOCTYPE,
					"project_name": f"{fixtures.TEST_PREFIX} formless",
					"company": fixtures.company(),
				}
			).insert()


class TestTheStatusIsERPNextsOwn(ProjectTestCase):
	def test_an_open_programme_takes_new_terms_of_reference(self):
		project = self.open_project()

		self.assertTrue(project_service.is_open(project))
		project_service.assert_open(project.name)

	def test_a_paused_programme_does_not(self):
		"""On hold means paused, and writing new work under it is what pausing stops."""
		project = self.open_project()
		project_service.set_status(project, project_service.STATUS_ON_HOLD)

		with self.assertRaises(frappe.ValidationError):
			project_service.assert_open(project.name)

	def test_a_completed_programme_does_not(self):
		project = self.open_project()
		project_service.set_status(project, project_service.STATUS_COMPLETED)

		with self.assertRaises(frappe.ValidationError):
			project_service.assert_open(project.name)

	def test_a_completed_programme_keeps_the_work_already_run_under_it(self):
		"""Closing a programme must not erase the record that it happened."""
		project = self.open_project()
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}",
			project=project.name)
		project_service.set_status(project, project_service.STATUS_COMPLETED)

		self.assertEqual(
			frappe.db.get_value(fixtures.TERMS_DOCTYPE, terms.name, "project"), project.name
		)

	def test_a_status_outside_the_four_is_refused(self):
		project = self.open_project()

		with self.assertRaises(frappe.ValidationError):
			project_service.set_status(project, "Whenever")

	def test_setting_the_status_it_already_has_writes_nothing(self):
		project = self.open_project()
		before = frappe.db.get_value(project_service.PROJECT_DOCTYPE, project.name, "modified")

		project_service.set_status(project, project_service.STATUS_OPEN)

		self.assertEqual(
			frappe.db.get_value(project_service.PROJECT_DOCTYPE, project.name, "modified"), before
		)


class TestWhoMayOpenAProgrammeWhere(ProjectTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# One coordinator, one branch. The whole point of the rule is what they
		# cannot do, so they are given exactly one area and nothing else.
		cls.coordinator = cls.viewer(
			"project_coordinator", fixtures.DEPLOYMENT_SCOPE_ROLE, cls.society_a["branch"]
		)
		# Two areas, and therefore no reliable default.
		cls.regional = cls.viewer(
			"project_regional",
			fixtures.DEPLOYMENT_SCOPE_ROLE,
			cls.society_a["branch"],
			cls.society_a["other_branch"],
		)
		# The same role, and nowhere at all.
		cls.unplaced = fixtures.make_user("project_unplaced")
		frappe.get_doc("User", cls.unplaced).add_roles(fixtures.DEPLOYMENT_SCOPE_ROLE)

	def test_a_coordinator_may_open_one_in_their_own_area(self):
		self.assertTrue(project_service.may_anchor(self.society_a["branch"], self.coordinator))

	def test_and_beneath_it(self):
		"""Somebody who runs a branch runs its posts. Scope grants downward."""
		self.assertTrue(project_service.may_anchor(self.society_a["post"], self.coordinator))

	def test_but_not_in_a_sibling_branch(self):
		self.assertFalse(project_service.may_anchor(self.society_a["other_branch"], self.coordinator))

	def test_and_not_above_themselves(self):
		self.assertFalse(project_service.may_anchor(self.society_a["region"], self.coordinator))

	def test_the_refusal_is_a_permission_error_naming_their_own_areas(self):
		frappe.set_user(self.coordinator)

		with self.assertRaises(frappe.PermissionError):
			project_service.assert_may_anchor(self.society_a["other_branch"])

	def test_somebody_placed_nowhere_is_refused_everything(self):
		frappe.set_user(self.unplaced)

		with self.assertRaises(frappe.PermissionError):
			project_service.assert_may_anchor(self.society_a["branch"])

	def test_creating_one_outside_their_area_is_refused_on_the_server(self):
		"""A filtered picker is a convenience. This is the control."""
		frappe.set_user(self.coordinator)

		with self.assertRaises(frappe.PermissionError):
			project_service.create(
				project_name=f"{fixtures.TEST_PREFIX} elsewhere",
				geo_node=self.society_a["other_branch"],
			)

	def test_moving_one_outside_their_area_is_refused_too(self):
		"""Re-anchoring is the same act as anchoring, and meets the same rule."""
		project = self.open_project()
		frappe.set_user(self.coordinator)

		doc = frappe.get_doc(project_service.PROJECT_DOCTYPE, project.name)
		doc.set(GEO_NODE_FIELD, self.society_a["other_branch"])

		with self.assertRaises(frappe.PermissionError):
			doc.save()

	def test_an_unrestricted_user_is_unrestricted(self):
		self.assertTrue(project_service.may_anchor(self.society_b["ward"], "Administrator"))


class TestTheDefaultIsReliableOrAbsent(ProjectTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.one_area = cls.viewer(
			"project_one_area", fixtures.DEPLOYMENT_SCOPE_ROLE, cls.society_a["branch"]
		)
		cls.two_areas = cls.viewer(
			"project_two_areas",
			fixtures.DEPLOYMENT_SCOPE_ROLE,
			cls.society_a["branch"],
			cls.society_a["other_branch"],
		)

	def test_one_live_assignment_is_a_default(self):
		self.assertEqual(project_service.default_node(self.one_area), self.society_a["branch"])

	def test_two_are_a_question_rather_than_a_default(self):
		self.assertIsNone(project_service.default_node(self.two_areas))

	def test_but_both_are_offered_as_choices(self):
		self.assertEqual(
			project_service.authorised_nodes(self.two_areas),
			sorted([self.society_a["branch"], self.society_a["other_branch"]]),
		)

	def test_an_unrestricted_user_gets_no_default_because_they_need_none(self):
		self.assertIsNone(project_service.default_node("Administrator"))


class TestWhatACallerIsToldAboutOne(ProjectTestCase):
	def test_the_summary_is_erpnexts_notes_with_the_markup_taken_off(self):
		"""Every reader of `summary` wants a sentence, not a fragment of HTML."""
		project = self.open_project(summary="<p>Coastal flood response.</p>")

		self.assertEqual(project_service.dto(project)["summary"], "Coastal flood response.")

	def test_the_planning_note_is_this_apps_own_field_and_not_erpnexts(self):
		"""They swapped homes on migration, and the two mean different things."""
		project = self.open_project(summary="The programme.", notes="Waiting on the budget.")
		answer = project_service.dto(project)

		self.assertEqual(answer["summary"], "The programme.")
		self.assertEqual(answer["notes"], "Waiting on the budget.")

	def test_the_funding_block_comes_back(self):
		project = self.open_project(
			donor="Netherlands Red Cross", funding_reference="MDRTZ011", funding_status="Committed"
		)
		answer = project_service.dto(project)

		self.assertEqual(answer["donor"], "Netherlands Red Cross")
		self.assertEqual(answer["funding_reference"], "MDRTZ011")
		self.assertEqual(answer["funding_status"], "Committed")

	def test_the_risks_and_assumptions_come_back_row_by_row(self):
		project = self.open_project()
		project.append("vmms_risks", {"risk": "The road floods.", "impact": "High"})
		project.append("vmms_assumptions", {"assumption": "The ferry runs.", "still_holds": 0})
		project.save()

		answer = project_service.dto(project)

		self.assertEqual(answer["risks"][0]["risk"], "The road floods.")
		self.assertEqual(answer["risks"][0]["impact"], "High")
		self.assertEqual(answer["assumptions"][0]["assumption"], "The ferry runs.")
		self.assertFalse(answer["assumptions"][0]["still_holds"])

	def test_a_deleted_anchor_is_a_docname_rather_than_an_exception(self):
		"""One odd-looking row, not a register that refuses to open."""
		project = self.open_project()
		frappe.db.set_value(
			project_service.PROJECT_DOCTYPE, project.name, GEO_NODE_FIELD, "GEO-99999",
			update_modified=False,
		)
		project.reload()

		self.assertEqual(project_service.dto(project)["geo_path"], "GEO-99999")
