# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Time logs, from the Volunteer module's side: the general kind, and the shared rules.

The general kind is complete and is tested here as a finished thing: it saves,
it requires its geo anchor, it refuses implausible hours, and it may never name
a deployment. So are the rules that hold whatever kind a log is, because those
are the ones a new kind is most likely to slip past.

**The deployment kind is live, and its own suite is elsewhere.** It was an
explicit stub in this module for one stage; stage 4 built the Deployment doctype
and finished it. What makes a deployment log acceptable is *ownership* — the
volunteer is on that deployment's roster — and both the rule and the roster it
reads belong to `deployment/services/participation.py`, so the tests that try to
break it live with it, in `deployment/tests/test_ownership.py`. What is asserted
here is the seam: that this module refuses one it cannot verify, and that the
general path did not change when the second kind became real.

**The discriminator is handled by dispatch, not by comparison.** That is
asserted against the source: no file outside `services/timelog.py` compares
`log_type` to anything.
"""

import ast
from pathlib import Path

import frappe
from frappe.utils import today

from vmmsx.volunteer.services import timelog
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TimeLogTestCase(VolunteerTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		profile = fixtures.make_profile("Time", "Logger")
		cls.volunteer = fixtures.make_volunteer(profile, cls.society_a["ward"])

	def log(self, **overrides):
		"""One time log, general by default, with anything overridable.

		`geo_node` is popped rather than passed through so that a test can ask
		for a log with no anchor at all — which is the ACC-02 case.
		"""
		node = overrides.pop("geo_node", self.society_a["ward"])

		return fixtures.make_time_log(self.volunteer.name, node, **overrides)


class TestTheGeneralKindIsLive(TimeLogTestCase):
	def test_a_general_log_saves(self):
		log = self.log(hours=6)

		self.assertEqual(log.log_type, timelog.TYPE_GENERAL)
		self.assertEqual(log.hours, 6)
		self.assertEqual(log.geo_node, self.society_a["ward"])

	def test_general_is_the_default_kind(self):
		field = frappe.get_meta(fixtures.TIME_LOG_DOCTYPE).get_field("log_type")

		self.assertEqual(field.default, timelog.TYPE_GENERAL)

	def test_it_carries_the_societys_own_category_and_nothing_branches_on_it(self):
		"""The configurable half of the vocabulary, next to the structural half."""
		category = frappe.get_all(fixtures.CATEGORY_DOCTYPE, limit=1, pluck="name")

		self.assertTrue(category, "the patch seeded no categories")

		log = self.log(log_category=category[0])

		self.assertEqual(log.log_category, category[0])

	def test_hours_are_summed_without_naming_a_kind(self):
		volunteer = fixtures.make_volunteer(fixtures.make_profile("Summed", "Logger"), self.society_a["ward"])
		fixtures.make_time_log(volunteer.name, self.society_a["ward"], hours=3)
		fixtures.make_time_log(volunteer.name, self.society_a["ward"], hours=4.5)

		self.assertEqual(timelog.hours_served(volunteer.name), 7.5)

	def test_a_log_of_no_time_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.log(hours=0)

	def test_a_log_of_more_hours_than_a_day_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.log(hours=25)

	def test_an_unknown_kind_is_refused(self):
		"""A value nobody wrote a rule for must not be quietly accepted."""
		with self.assertRaises(frappe.ValidationError):
			self.log(log_type="stipend")


class TestTheAnchorIsRequiredOnEveryKind(TimeLogTestCase):
	"""ACC-02, and it is checked before the kind's own rule."""

	def test_a_general_log_with_no_anchor_is_refused(self):
		with self.assertRaises(frappe.MandatoryError):
			self.log(geo_node=None)

	def test_a_deployment_log_with_no_anchor_is_refused_for_the_anchor(self):
		"""The anchor rule does not wait for stage 4.

		The message must be the anchor's, not the stub's: a rule that only
		applied to kinds that happen to be built is not a rule about records.
		"""
		with self.assertRaises(frappe.MandatoryError):
			self.log(log_type=timelog.TYPE_DEPLOYMENT, geo_node=None)

	def test_the_field_itself_is_mandatory_in_the_schema_too(self):
		field = frappe.get_meta(fixtures.TIME_LOG_DOCTYPE).get_field("geo_node")

		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Geo Node")
		self.assertTrue(field.reqd)


class TestAGeneralLogCarriesNoDeployment(TimeLogTestCase):
	def test_a_general_log_naming_a_deployment_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.log(deployment="DEP-00001")

	def test_the_refusal_is_the_general_rule_and_not_the_ownership_rule(self):
		"""Two different refusals for two different reasons, and they must not blur.

		A general log naming a deployment is refused because it is the wrong kind
		of log, whoever filed it and whatever roster the deployment has. A
		deployment log is refused because the volunteer was not on it. If the
		general rule started reporting the ownership rule's message, adding the
		volunteer to the roster would look like a way to fix a general log, and it
		is not.
		"""
		with self.assertRaises(frappe.ValidationError):
			self.log(deployment="DEP-00001")

		message = frappe.as_json(frappe.message_log[-1] if frappe.message_log else {})

		self.assertNotIn("roster", message.lower())

	def test_a_general_log_with_no_value_is_fine(self):
		"""Unset and empty are both "no deployment", not "a deployment".

		Anything else in the field is now the framework's problem before it is
		ours: a Link refuses a value naming no record, so the only strings that
		reach the general rule are the empty one and a real deployment.
		"""
		self.assertTrue(self.log(deployment="").name)
		self.assertTrue(self.log(deployment=None).name)


class TestTheDeploymentKindIsLiveAndVerified(TimeLogTestCase):
	"""The seam, from this side. The rule itself is tested where it lives.

	`deployment/tests/test_ownership.py` is the suite that tries to break the
	participation check, with real deployments and real rosters. What these
	assert is that this module hands the question over rather than answering it,
	and that it refuses a log it cannot verify.
	"""

	def test_the_kind_is_structurally_known(self):
		"""In the Select, in the tuple, and in the dispatch table."""
		field = frappe.get_meta(fixtures.TIME_LOG_DOCTYPE).get_field("log_type")

		self.assertIn(timelog.TYPE_DEPLOYMENT, (field.options or "").split("\n"))
		self.assertIn(timelog.TYPE_DEPLOYMENT, timelog.LOG_TYPES)
		self.assertIn(timelog.TYPE_DEPLOYMENT, timelog._VALIDATE)

	def test_the_deployment_doctype_exists_now(self):
		"""The stub was waiting for exactly this."""
		self.assertTrue(frappe.db.exists("DocType", "VMMS Deployment"))

	def test_the_field_is_a_link_to_it(self):
		field = frappe.get_meta(fixtures.TIME_LOG_DOCTYPE).get_field("deployment")

		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "VMMS Deployment")

	def test_a_deployment_log_naming_nothing_is_refused(self):
		"""There would be no roster to check it against, so it is incomplete."""
		with self.assertRaises(frappe.MandatoryError):
			self.log(log_type=timelog.TYPE_DEPLOYMENT)

	def test_a_deployment_log_naming_something_unverifiable_is_refused(self):
		"""And nothing is saved. Naming a docname is not participating."""
		before = frappe.db.count(fixtures.TIME_LOG_DOCTYPE)

		with self.assertRaises(frappe.ValidationError):
			self.log(log_type=timelog.TYPE_DEPLOYMENT, deployment="DEP-00001")

		self.assertEqual(frappe.db.count(fixtures.TIME_LOG_DOCTYPE), before)

	def test_this_module_does_not_answer_the_ownership_question_itself(self):
		"""It asks the module that owns the roster, and holds no copy of the rule."""
		source = Path(frappe.get_app_path("vmmsx"), "volunteer", "services", "timelog.py").read_text()

		self.assertIn("participation.assert_participant", source)
		self.assertNotIn("VMMS Deployment Participant", source)

	def test_the_stage_4_stub_is_gone(self):
		"""No refusal left in this module names a stage that has since happened."""
		source = Path(frappe.get_app_path("vmmsx"), "volunteer", "services", "timelog.py").read_text()

		self.assertNotIn("stage 4", source.lower())
		self.assertFalse(hasattr(timelog, "DEPLOYMENT_LOGS_AWAIT_STAGE_4"))
		self.assertFalse(hasattr(timelog, "PENDING_OWNERSHIP_RULE"))


class TestTheDiscriminatorIsDispatched(TimeLogTestCase):
	"""No scattered comparisons. One table, in one module."""

	def test_no_file_outside_the_service_compares_the_log_type(self):
		offenders = []
		root = Path(frappe.get_app_path("vmmsx"))

		for path in root.rglob("*.py"):
			parts = set(path.relative_to(root).parts)

			if {"tests", "__pycache__"} & parts or path.name == "timelog.py":
				continue

			for node in ast.walk(ast.parse(path.read_text())):
				if isinstance(node, ast.Compare) and any(
					_is_log_type(operand) for operand in (node.left, *node.comparators)
				):
					offenders.append(f"{path.name}:{node.lineno}")

		self.assertEqual(offenders, [], "log_type is being branched on outside its dispatch table")

	def test_the_service_dispatches_rather_than_branching(self):
		"""The positive half: one entry per kind, and every kind has one."""
		self.assertEqual(set(timelog._VALIDATE), set(timelog.LOG_TYPES))


def _is_log_type(node) -> bool:
	"""`something.log_type` or `something["log_type"]`."""
	if isinstance(node, ast.Attribute):
		return node.attr == "log_type"

	if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
		return node.slice.value == "log_type"

	return False
