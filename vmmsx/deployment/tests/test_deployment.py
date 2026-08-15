# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The deployment record itself: where it may exist, and how it may move.

ACC-02 and ACC-03 are the substance here. An unplaced deployment is invisible to
geo scoping, because core's list filter is an `IN` and that excludes NULL, so
refusing one at creation is the rule rather than a formality. Which *level* it
may be anchored at is a society's answer, and the two societies these fixtures
build are shaped and named differently on purpose: one anchors at a level it
calls Branch, the other at one it calls District, and the same code refuses and
accepts correctly in both without either word appearing in it.

The terms of reference's own geo scope is a second, independent narrowing. It is
written by whoever wrote the terms rather than by the society's settings, and it
is tested separately because the two can disagree and a record has to satisfy
both.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.deployment.services import deployment as deployment_service
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class DeploymentRecordTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.terms = fixtures.make_terms()


class TestACCO2TheAnchorIsMandatory(DeploymentRecordTestCase):
	def test_a_deployment_with_no_geo_node_is_refused_at_creation(self):
		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_deployment(self.terms.name, None)

	def test_the_field_itself_is_a_mandatory_link_in_the_schema(self):
		field = frappe.get_meta(fixtures.DEPLOYMENT_DOCTYPE).get_field("geo_node")

		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Geo Node")
		self.assertTrue(field.reqd)

	def test_a_request_with_no_geo_node_is_refused_too(self):
		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_request(self.terms.name, None)

	def test_nothing_is_saved_when_the_anchor_rule_fires(self):
		before = frappe.db.count(fixtures.DEPLOYMENT_DOCTYPE)

		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_deployment(self.terms.name, None)

		self.assertEqual(frappe.db.count(fixtures.DEPLOYMENT_DOCTYPE), before)

	def test_an_anchored_deployment_saves(self):
		"""The positive half: the rule refuses the unplaced, not everything."""
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"])

		self.assertEqual(deployment.geo_node, self.society_a["branch"])


class TestACC03TheAnchorLevelIsSocietyConfiguration(DeploymentRecordTestCase):
	def test_with_no_level_configured_any_level_is_accepted(self):
		"""Empty means unconstrained, never forbidden."""
		fixtures.set_deployment_anchor_level(None)
		self.addCleanup(fixtures.set_deployment_anchor_level, None)

		for node in (self.society_a["region"], self.society_a["branch"], self.society_a["post"]):
			self.assertTrue(fixtures.make_deployment(self.terms.name, node).name)

	def test_a_configured_level_refuses_a_node_at_another_level(self):
		fixtures.set_deployment_anchor_level(self.society_a["levels"]["branch"])
		self.addCleanup(fixtures.set_deployment_anchor_level, None)

		self.assertTrue(fixtures.make_deployment(self.terms.name, self.society_a["branch"]).name)

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_deployment(self.terms.name, self.society_a["post"])

	def test_a_second_society_narrows_to_a_different_level_with_the_same_code(self):
		"""The point of ACC-03: no level name is in a source file.

		Society B's ladder is Province, District, Ward. Configuring District here
		accepts a node that society A's configuration would have refused, and
		nothing about the code changed between the two assertions.
		"""
		fixtures.set_deployment_anchor_level(self.society_b["levels"]["district"])
		self.addCleanup(fixtures.set_deployment_anchor_level, None)

		self.assertTrue(fixtures.make_deployment(self.terms.name, self.society_b["district"]).name)

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_deployment(self.terms.name, self.society_b["ward"])

	def test_a_request_obeys_the_same_setting(self):
		"""One setting for both, so a request can always become its deployment."""
		fixtures.set_deployment_anchor_level(self.society_a["levels"]["branch"])
		self.addCleanup(fixtures.set_deployment_anchor_level, None)

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_request(self.terms.name, self.society_a["post"])


class TestTheTermsOwnScope(DeploymentRecordTestCase):
	def test_empty_scope_permits_anywhere(self):
		terms = fixtures.make_terms(fixtures.TOR_OPEN)

		self.assertTrue(fixtures.make_deployment(terms.name, self.society_b["ward"]).name)

	def test_a_scoped_terms_refuses_a_node_outside_its_subtree(self):
		terms = fixtures.make_terms(fixtures.TOR_OPEN, geo_scope=self.society_a["branch"])

		self.assertTrue(fixtures.make_deployment(terms.name, self.society_a["post"]).name)

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_deployment(terms.name, self.society_a["other_branch"])

	def test_an_ancestor_is_outside_the_scope_too(self):
		"""Work described for a branch is not work for the whole region."""
		terms = fixtures.make_terms(fixtures.TOR_OPEN, geo_scope=self.society_a["branch"])

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_deployment(terms.name, self.society_a["region"])

	def test_inactive_terms_take_no_new_deployment(self):
		terms = fixtures.make_terms(fixtures.TOR_OPEN, is_active=0)

		with self.assertRaises(frappe.ValidationError):
			from vmmsx.deployment.services import terms as terms_service

			terms_service.assert_active(terms.name)


class TestThePeriod(DeploymentRecordTestCase):
	def test_an_end_before_the_start_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			fixtures.make_deployment(
				self.terms.name,
				self.society_a["branch"],
				start_date=today(),
				end_date=add_days(today(), -1),
			)

	def test_a_single_day_deployment_is_ordinary(self):
		deployment = fixtures.make_deployment(
			self.terms.name, self.society_a["branch"], start_date=today(), end_date=today()
		)

		self.assertTrue(deployment.name)


class TestTheRoster(DeploymentRecordTestCase):
	def test_a_volunteer_listed_twice_is_refused(self):
		volunteer = fixtures.make_volunteer(
			fixtures.make_profile("Listed", "Twice"), self.society_a["branch"]
		)

		with self.assertRaises(frappe.DuplicateEntryError):
			fixtures.make_deployment(
				self.terms.name, self.society_a["branch"], participants=[volunteer.name, volunteer.name]
			)

	def test_adding_somebody_already_on_it_changes_nothing(self):
		from vmmsx.deployment.services import participation

		volunteer = fixtures.make_volunteer(fixtures.make_profile("Added", "Once"), self.society_a["branch"])
		deployment = fixtures.make_deployment(
			self.terms.name, self.society_a["branch"], participants=[volunteer.name]
		)

		self.assertFalse(participation.add(deployment, volunteer.name))
		self.assertEqual(len(deployment.participants), 1)

	def test_an_empty_roster_is_ordinary(self):
		"""A planned deployment nobody has been assigned to yet is a normal state."""
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"])

		self.assertEqual(deployment.participants, [])


class TestTheStatusLifecycle(DeploymentRecordTestCase):
	def test_the_statuses_are_a_closed_set(self):
		with self.assertRaises(frappe.ValidationError):
			fixtures.make_deployment(self.terms.name, self.society_a["branch"], status="Postponed")

	def test_planned_moves_to_active_and_on_to_completed(self):
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"])

		deployment_service.set_status(deployment, deployment_service.STATUS_ACTIVE)
		self.assertEqual(deployment.status, deployment_service.STATUS_ACTIVE)

		deployment_service.set_status(deployment, deployment_service.STATUS_COMPLETED)
		self.assertEqual(deployment.status, deployment_service.STATUS_COMPLETED)

	def test_a_completed_deployment_cannot_be_reopened(self):
		deployment = fixtures.make_deployment(
			self.terms.name, self.society_a["branch"], status=deployment_service.STATUS_COMPLETED
		)

		with self.assertRaises(frappe.ValidationError):
			deployment_service.set_status(deployment, deployment_service.STATUS_ACTIVE)

	def test_an_active_deployment_cannot_go_back_to_planned(self):
		"""People were there. Unhappening it is not a status change."""
		deployment = fixtures.make_deployment(
			self.terms.name, self.society_a["branch"], status=deployment_service.STATUS_ACTIVE
		)

		with self.assertRaises(frappe.ValidationError):
			deployment_service.set_status(deployment, deployment_service.STATUS_PLANNED)

	def test_setting_the_status_it_already_has_is_a_no_op(self):
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"])
		modified = deployment.modified

		deployment_service.set_status(deployment, deployment_service.STATUS_PLANNED)

		self.assertEqual(deployment.modified, modified)

	def test_saving_a_deployment_without_touching_its_status_is_allowed(self):
		"""The commonest thing that happens to a deployment must not be a transition error."""
		deployment = fixtures.make_deployment(
			self.terms.name, self.society_a["branch"], status=deployment_service.STATUS_ACTIVE
		)
		deployment.notes = "Edited without changing the status."
		deployment.save()

		self.assertEqual(deployment.status, deployment_service.STATUS_ACTIVE)
