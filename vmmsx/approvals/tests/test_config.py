# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Configuration, and the guardrails that make a workflow impossible to break.

A workflow that cannot work should be impossible to **save**, not merely
impossible to run. Every rule below fires while an administrator is looking at
the form; none of them waits for the first application to get stuck.

The two anchor rules are here too, because both are configuration:

- **ACC-02** — every operational record is anchored to a Geo Node, by a Link,
  mandatory at creation. There are no unplaced records: an unplaced application
  is invisible to geo scoping and unroutable by approvals.
- **ACC-03** — *which* level it may be anchored at is per society. The same
  engine, with two different configurations, lets one society anchor at ward
  level and refuse county, and another do exactly the reverse. Neither word
  appears in a source file.
"""

import frappe

from vmmsx.approvals.services import config, contract, engine, routing, sla
from vmmsx.approvals.tests import fixtures
from vmmsx.approvals.tests.base import ApprovalTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestStageGuardrails(ApprovalTestCase):
	def workflow_with(self, *stages):
		return fixtures.make_workflow(list(stages))

	def valid_stage(self, **overrides) -> dict:
		row = fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)
		row.update(overrides)

		return row

	def test_a_workflow_needs_a_stage(self):
		with self.assertRaises(frappe.MandatoryError):
			self.workflow_with()

	def test_two_stages_may_not_share_a_sequence(self):
		"""Otherwise order depends on row order, which nothing may rely on."""
		with self.assertRaises(frappe.ValidationError):
			self.workflow_with(
				self.valid_stage(),
				fixtures.stage(1, fixtures.LABEL_REGION, fixtures.APPROVER_ROLE),
			)

	def test_a_sequence_starts_at_one(self):
		with self.assertRaises(frappe.ValidationError):
			self.workflow_with(self.valid_stage(sequence=0))

	def test_something_must_be_able_to_reject(self):
		"""A workflow of endorsements only is a rubber stamp with an audit trail."""
		with self.assertRaises(frappe.ValidationError):
			self.workflow_with(
				self.valid_stage(can_reject=0),
				fixtures.stage(2, fixtures.LABEL_REGION, fixtures.APPROVER_ROLE, can_reject=0),
			)

	def test_one_stage_being_able_to_reject_is_enough(self):
		workflow = self.workflow_with(
			self.valid_stage(can_reject=0),
			fixtures.stage(2, fixtures.LABEL_REGION, fixtures.APPROVER_ROLE, can_reject=1),
		)

		self.assertEqual(len(workflow.stages), 2)

	def test_every_stage_needs_a_clock(self):
		with self.assertRaises(frappe.ValidationError):
			self.workflow_with(self.valid_stage(sla_days=0))

	def test_an_unknown_resolution_rule_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.workflow_with(self.valid_stage(resolution_rule="ask_around"))

	def test_resolving_at_a_level_needs_the_level(self):
		with self.assertRaises(frappe.ValidationError):
			self.workflow_with(self.valid_stage(resolution_rule=routing.RULE_AT_LEVEL))

	def test_resolving_at_a_fixed_node_needs_the_node(self):
		with self.assertRaises(frappe.ValidationError):
			self.workflow_with(self.valid_stage(resolution_rule=routing.RULE_FIXED_NODE))

	def test_an_unknown_completion_rule_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.workflow_with(self.valid_stage(completion_rule="majority_ish"))

	def test_an_unknown_breach_action_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.workflow_with(self.valid_stage(on_sla_breach="phone_somebody"))

	def test_a_stage_that_can_stall_silently_is_refused(self):
		"""Needs everyone, not optional, and does nothing when late.

		An application that reaches such a stage can stop forever with nobody
		informed — the exact failure this system exists to make impossible.
		"""
		with self.assertRaises(frappe.ValidationError):
			self.workflow_with(
				self.valid_stage(completion_rule=routing.COMPLETION_ALL_OF, on_sla_breach=sla.BREACH_NONE)
			)

	def test_the_same_stage_is_fine_once_it_is_optional(self):
		workflow = self.workflow_with(
			self.valid_stage(
				completion_rule=routing.COMPLETION_ALL_OF, on_sla_breach=sla.BREACH_NONE, is_optional=1
			)
		)

		self.assertEqual(workflow.stages[0].completion_rule, routing.COMPLETION_ALL_OF)

	def test_or_once_it_escalates(self):
		workflow = self.workflow_with(
			self.valid_stage(completion_rule=routing.COMPLETION_ALL_OF, on_sla_breach=sla.BREACH_ESCALATE_UP)
		)

		self.assertEqual(workflow.stages[0].on_sla_breach, sla.BREACH_ESCALATE_UP)

	def test_an_anchor_level_may_not_be_listed_twice(self):
		with self.assertRaises(frappe.ValidationError):
			fixtures.make_workflow(
				[self.valid_stage()],
				allowed_anchor_levels=[
					{"geo_level": self.kenya["levels"]["ward"]},
					{"geo_level": self.kenya["levels"]["ward"]},
				],
			)


class TestTheApprovableContract(ApprovalTestCase):
	"""A doctype must be able to carry an approval before one may govern it."""

	def test_a_doctype_without_the_state_fields_is_refused(self):
		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_workflow(
				[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)], doctype="ToDo"
			)

	def test_a_child_table_cannot_carry_an_approval(self):
		with self.assertRaises(frappe.ValidationError):
			fixtures.make_workflow(
				[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)],
				doctype="VMMS Approval Stage",
			)

	def test_a_single_doctype_cannot_either(self):
		with self.assertRaises(frappe.ValidationError):
			fixtures.make_workflow(
				[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)],
				doctype="System Settings",
			)

	def test_the_stand_in_satisfies_the_contract(self):
		# No exception is the assertion.
		contract.assert_approvable(fixtures.APPROVABLE_DOCTYPE)

	def test_the_contract_describes_itself(self):
		"""The error a module author gets has to tell them what to add."""
		description = contract.describe()

		for field in ("approval_state", "approval_stage", "approval_stage_entered_on"):
			self.assertIn(field, description)

		self.assertIn(contract.DECISION_DOCTYPE, description)


class TestTheAnchorField(ApprovalTestCase):
	"""ACC-02, enforced where a workflow is configured."""

	def test_a_field_that_does_not_exist_is_refused(self):
		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_workflow(
				[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)],
				geo_node_field="wherever_they_said",
			)

	def test_free_text_is_not_an_anchor(self):
		with self.assertRaises(frappe.ValidationError):
			fixtures.make_workflow(
				[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)],
				geo_node_field="title",
			)

	def test_an_optional_link_is_not_an_anchor_either(self):
		"""There are no unplaced records, so the field cannot be one a user may skip."""
		with self.assertRaises(frappe.ValidationError):
			fixtures.make_workflow(
				[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)],
				geo_node_field=fixtures.OPTIONAL_GEO_FIELD,
			)

	def test_a_mandatory_link_to_geo_node_is(self):
		workflow = fixtures.make_workflow([fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)])

		self.assertEqual(workflow.geo_node_field, fixtures.GEO_FIELD)


class TestAnchorEnforcedAtSubmission(ApprovalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county = fixtures.make_user("anchor_county", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)]
		)

	def test_an_unplaced_application_cannot_enter_review(self):
		"""Belt and braces: the schema requires it, and the engine checks anyway.

		The check is not redundant. A record can lose its anchor through an
		import, a patch or a direct write, and the engine is the last place that
		can refuse to route something nobody could ever see.
		"""
		application = self.application("unplaced", self.kenya["kihara"])
		frappe.db.set_value(
			fixtures.APPROVABLE_DOCTYPE, application, fixtures.GEO_FIELD, None, update_modified=False
		)

		with self.assertRaises(frappe.MandatoryError):
			engine.submit(self.reload(application))

	def test_a_placed_application_enters_review(self):
		application = self.application("placed", self.kenya["kihara"])

		self.assertEqual(engine.submit(self.reload(application))["state"], "In Review")


class TestAnchorLevelsPerSociety(ApprovalTestCase):
	"""ACC-03. One engine, two societies, opposite answers — and no code changes.

	Each test configures the workflow the way a national society would, then
	submits the same two applications. Nothing about county, ward or depth is
	written anywhere but the configuration.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county_approver = fixtures.make_user("acc03_county", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.county_approver, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

	def configure(self, *levels):
		return fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)],
			allowed_anchor_levels=[{"geo_level": level} for level in levels],
		)

	def submit(self, title: str, node: str):
		return engine.submit(self.reload(self.application(title, node)))

	def test_a_society_that_anchors_at_ward_level(self):
		self.configure(self.kenya["levels"]["ward"])

		self.assertEqual(self.submit("ward ok", self.kenya["kihara"])["state"], "In Review")

		with self.assertRaises(frappe.ValidationError):
			self.submit("county refused", self.kenya["kiambu"])

	def test_a_society_that_anchors_at_county_level(self):
		"""The same engine, the opposite policy, one row of configuration apart."""
		self.configure(self.kenya["levels"]["county"])

		self.assertEqual(self.submit("county ok", self.kenya["kiambu"])["state"], "In Review")

		with self.assertRaises(frappe.ValidationError):
			self.submit("ward refused", self.kenya["kihara"])

	def test_a_society_that_allows_both(self):
		self.configure(self.kenya["levels"]["county"], self.kenya["levels"]["ward"])

		self.assertEqual(self.submit("both county", self.kenya["kiambu"])["state"], "In Review")
		self.assertEqual(self.submit("both ward", self.kenya["kihara"])["state"], "In Review")

	def test_no_configuration_means_any_active_level(self):
		"""Unset is not "forbid everything" — a society that has not narrowed it
		has not thereby refused every level."""
		self.configure()

		self.assertEqual(self.submit("open region", self.kenya["region"])["state"], "In Review")
		self.assertEqual(self.submit("open ward", self.kenya["kihara"])["state"], "In Review")

	def test_the_refusal_names_the_levels_that_are_allowed(self):
		"""In the society's own words, from the society's own Geo Levels."""
		self.configure(self.kenya["levels"]["ward"])

		with self.assertRaises(frappe.ValidationError):
			self.submit("named refusal", self.kenya["kiambu"])

		self.assertIn("Ward", frappe.message_log[-1].get("message", ""))


class TestConfigLookup(ApprovalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.workflow = fixtures.make_workflow(
			[
				fixtures.stage(3, fixtures.LABEL_REGION, fixtures.APPROVER_ROLE),
				fixtures.stage(1, fixtures.LABEL_BRANCH, fixtures.APPROVER_ROLE),
				fixtures.stage(2, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE),
			]
		)

	def test_stages_come_back_in_sequence_order_not_row_order(self):
		stages = config.stages(config.for_doctype(fixtures.APPROVABLE_DOCTYPE))

		self.assertEqual([row.sequence for row in stages], [1, 2, 3])

	def test_stages_after_skips_what_is_done(self):
		workflow = config.for_doctype(fixtures.APPROVABLE_DOCTYPE)

		self.assertEqual([row.sequence for row in config.stages_after(workflow, 1)], [2, 3])
		self.assertEqual([row.sequence for row in config.stages_after(workflow, 3)], [])
		self.assertEqual([row.sequence for row in config.stages_after(workflow, None)], [1, 2, 3])

	def test_a_stage_is_found_by_its_opaque_row_name(self):
		workflow = config.for_doctype(fixtures.APPROVABLE_DOCTYPE)
		stage = config.stages(workflow)[1]

		self.assertEqual(config.stage_by_name(workflow, stage.name).sequence, 2)

	def test_a_stage_that_was_deleted_resolves_to_nothing(self):
		"""An administrator may delete a stage while an application sits in it.
		The caller decides what that means; the lookup does not raise."""
		workflow = config.for_doctype(fixtures.APPROVABLE_DOCTYPE)

		self.assertIsNone(config.stage_by_name(workflow, "a-row-that-is-gone"))
		self.assertIsNone(config.stage_by_name(workflow, None))

	def test_an_ungoverned_doctype_says_so(self):
		self.assertFalse(config.is_approvable("ToDo"))

		with self.assertRaises(frappe.ValidationError):
			config.for_doctype("ToDo")

	def test_the_applicant_field_falls_back_to_the_owner(self):
		workflow = config.for_doctype(fixtures.APPROVABLE_DOCTYPE)
		application = self.application("owner fallback", self.kenya["kihara"])

		self.assertEqual(config.applicant(self.reload(application), workflow)[0], "owner")

	def test_and_is_used_when_the_workflow_names_one(self):
		# A stand-in rather than a saved workflow: this class's configuration is
		# arranged once in setUpClass, and a test that replaced it would change
		# what every later method in the class is testing.
		workflow = frappe._dict({"applicant_field": fixtures.APPLICANT_FIELD})
		application = self.application("named applicant", self.kenya["kihara"], applicant="RP-00042")

		self.assertEqual(
			config.applicant(self.reload(application), workflow),
			(fixtures.APPLICANT_FIELD, "RP-00042"),
		)
