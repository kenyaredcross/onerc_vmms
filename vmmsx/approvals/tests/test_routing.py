# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Routing — one configuration, two societies, different people, both correct.

This is the worked example. A single `VMMS Approval Workflow`, unchanged and
unedited between the assertions, routes an application to:

- a **County Coordinator** where the society's hierarchy is Region → County →
  Ward and authority sits at the county;
- a **District Officer** where it is Region → District → Village and authority
  sits at the district;
- a **Region Head** in the same society, for a district where nobody holds the
  role at all.

Nothing about county, district, ward or village appears in the engine. The walk
finds whoever holds the role, wherever they sit, which is why the same
configuration is correct in both places — and why a new national society is a
data-entry exercise rather than a fork.
"""

import frappe
from onerc_core.access.services import scope
from onerc_core.geo.services import adapter

from vmmsx.approvals.services import config, engine, routing
from vmmsx.approvals.tests import fixtures
from vmmsx.approvals.tests.base import ApprovalTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestOneConfigTwoSocieties(ApprovalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county_coordinator = fixtures.make_user("kenya_county", [fixtures.APPROVER_ROLE])
		cls.district_officer = fixtures.make_user("gambia_district", [fixtures.APPROVER_ROLE])
		cls.region_head = fixtures.make_user("gambia_region", [fixtures.APPROVER_ROLE])

		fixtures.make_assignment(cls.county_coordinator, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])
		fixtures.make_assignment(cls.district_officer, fixtures.APPROVER_ROLE, cls.gambia["kerewan"])
		fixtures.make_assignment(cls.region_head, fixtures.APPROVER_ROLE, cls.gambia["region"])

		# One stage. One rule. No society named anywhere in it.
		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_BRANCH, fixtures.APPROVER_ROLE)]
		)

	def routed_for(self, node: str) -> list[str]:
		"""Who an application anchored at `node` lands with."""
		stage = config.stages(config.for_doctype(fixtures.APPROVABLE_DOCTYPE))[0]

		return routing.routed(stage, node)

	def test_a_kenyan_ward_resolves_to_the_county_coordinator(self):
		self.assertEqual(self.routed_for(self.kenya["kihara"]), [self.county_coordinator])

	def test_the_other_ward_of_that_county_resolves_the_same_way(self):
		self.assertEqual(self.routed_for(self.kenya["ndenderu"]), [self.county_coordinator])

	def test_a_gambian_village_resolves_to_the_district_officer(self):
		self.assertEqual(self.routed_for(self.gambia["illiassa"]), [self.district_officer])

	def test_a_village_whose_district_holds_nobody_resolves_to_the_region_head(self):
		"""Jokadu has no officer, so the walk keeps going up and finds the region."""
		self.assertEqual(self.routed_for(self.gambia["kuntaur"]), [self.region_head])

	def test_the_configuration_was_never_touched(self):
		"""The whole point: one record, four answers, zero edits.

		If this workflow had to be different for the second society, the engine
		would not be generic — it would be a Kenyan engine with a Gambian
		branch in it.
		"""
		workflow = config.for_doctype(fixtures.APPROVABLE_DOCTYPE)

		self.assertEqual(workflow.name, self.workflow.name)
		self.assertEqual(len(workflow.stages), 1)
		self.assertEqual(workflow.stages[0].resolution_rule, routing.RULE_NEAREST_ANCESTOR)
		self.assertEqual(workflow.stages[0].required_role, fixtures.APPROVER_ROLE)
		self.assertFalse(workflow.stages[0].geo_level)
		self.assertFalse(workflow.stages[0].fixed_geo_node)

	def test_a_county_with_nobody_anywhere_above_resolves_to_nobody(self):
		"""Nakuru holds nobody, and neither does the region above it.

		Empty is an answer. Core will not invent a fallback approver and neither
		will this layer — every plausible fallback is a policy decision.
		"""
		self.assertEqual(self.routed_for(self.kenya["bahati"]), [])

	# --- the whole path, not just the resolver -----------------------------

	def test_an_application_lands_in_the_resolved_persons_queue(self):
		application = self.application("kiambu ward volunteer", self.kenya["kihara"])
		status = engine.submit(self.reload(application))

		self.assertEqual(status["state"], "In Review")
		self.assertEqual(status["approvers"], [self.county_coordinator])
		self.assertIn(application, self.queue_of(self.county_coordinator))

	def test_the_same_workflow_lands_a_gambian_application_elsewhere(self):
		application = self.application("kerewan village volunteer", self.gambia["illiassa"])
		status = engine.submit(self.reload(application))

		self.assertEqual(status["approvers"], [self.district_officer])
		self.assertIn(application, self.queue_of(self.district_officer))
		self.assertNotIn(application, self.queue_of(self.county_coordinator))

	def test_the_status_names_the_place_in_the_society_s_own_words(self):
		application = self.application("path check", self.gambia["kuntaur"])
		status = engine.submit(self.reload(application))

		self.assertEqual(status["geo_path"], adapter.get_full_path(self.gambia["kuntaur"]))
		self.assertEqual(status["approvers"], [self.region_head])

	def test_every_routed_approver_can_reach_the_record(self):
		"""Routing and read scope answer from one table, so they cannot disagree.

		If they ever did, the product would route approvals to people who
		cannot open the document.
		"""
		for node in (
			self.kenya["kihara"],
			self.kenya["ndenderu"],
			self.gambia["illiassa"],
			self.gambia["kuntaur"],
		):
			for approver in self.routed_for(node):
				self.assertIn(
					node,
					scope.get_user_geo_scope(approver, fixtures.APPROVER_ROLE),
					f"{approver} was routed {node} but their scope excludes it",
				)


class TestAtLevelRule(ApprovalTestCase):
	"""Policy picks the tier, not proximity."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.at_county = fixtures.make_user("level_county", [fixtures.APPROVER_ROLE])
		cls.at_region = fixtures.make_user("level_region", [fixtures.APPROVER_ROLE])

		fixtures.make_assignment(cls.at_county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])
		fixtures.make_assignment(cls.at_region, fixtures.APPROVER_ROLE, cls.kenya["region"])

		cls.workflow = fixtures.make_workflow(
			[
				fixtures.stage(
					1,
					fixtures.LABEL_REGION,
					fixtures.APPROVER_ROLE,
					resolution_rule=routing.RULE_AT_LEVEL,
					geo_level=cls.kenya["levels"]["region"],
				)
			]
		)

	def stage(self):
		return config.stages(config.for_doctype(fixtures.APPROVABLE_DOCTYPE))[0]

	def test_it_skips_the_nearer_holder(self):
		self.assertEqual(routing.routed(self.stage(), self.kenya["kihara"]), [self.at_region])

	def test_a_level_from_another_society_resolves_to_nobody(self):
		"""A Gambian village has no Kenyan region in its chain. Not an error — empty."""
		self.assertEqual(routing.routed(self.stage(), self.gambia["illiassa"]), [])


class TestFixedNodeRule(ApprovalTestCase):
	"""Some decisions belong to one desk, wherever the applicant lives."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.national_desk = fixtures.make_user("national_desk", [fixtures.APPROVER_ROLE])
		cls.district_officer = fixtures.make_user("fixed_district", [fixtures.APPROVER_ROLE])

		fixtures.make_assignment(cls.national_desk, fixtures.APPROVER_ROLE, cls.kenya["region"])
		fixtures.make_assignment(cls.district_officer, fixtures.APPROVER_ROLE, cls.gambia["kerewan"])

		cls.workflow = fixtures.make_workflow(
			[
				fixtures.stage(
					1,
					fixtures.LABEL_NATIONAL,
					fixtures.APPROVER_ROLE,
					resolution_rule=routing.RULE_FIXED_NODE,
					fixed_geo_node=cls.kenya["region"],
				)
			]
		)

	def stage(self):
		return config.stages(config.for_doctype(fixtures.APPROVABLE_DOCTYPE))[0]

	def test_it_resolves_at_the_fixed_node_whatever_the_document_says(self):
		self.assertEqual(routing.routed(self.stage(), self.kenya["kihara"]), [self.national_desk])
		self.assertEqual(routing.routed(self.stage(), self.gambia["illiassa"]), [self.national_desk])

	def test_it_does_not_pick_up_the_nearer_holder(self):
		self.assertNotIn(self.district_officer, routing.routed(self.stage(), self.gambia["illiassa"]))

	def test_holders_exactly_at_does_not_walk_up(self):
		"""Exactly this node: the region's holder does not answer for the district."""
		self.assertEqual(
			routing.holders_exactly_at(self.gambia["kerewan"], fixtures.APPROVER_ROLE),
			[self.district_officer],
		)
		self.assertEqual(routing.holders_exactly_at(self.gambia["jokadu"], fixtures.APPROVER_ROLE), [])


class TestUnknownRules(ApprovalTestCase):
	"""Stand-in stage rows, never the cached configuration.

	`config.for_doctype` hands back a shared, cached document; editing a stage
	on it would quietly change the configuration for every later test in the
	process. A throwaway row is the honest way to ask "what does the resolver do
	with a rule nobody defined".
	"""

	def unknown_rule_stage(self):
		return frappe._dict(
			{
				"resolution_rule": "whoever_is_around",
				"required_role": fixtures.APPROVER_ROLE,
				"completion_rule": routing.COMPLETION_SINGLE,
			}
		)

	def test_an_invented_rule_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			routing.resolve(self.unknown_rule_stage(), self.kenya["kihara"])

	def test_no_node_resolves_to_nobody(self):
		stage = frappe._dict(
			{
				"resolution_rule": routing.RULE_NEAREST_ANCESTOR,
				"required_role": fixtures.APPROVER_ROLE,
				"completion_rule": routing.COMPLETION_SINGLE,
			}
		)

		self.assertEqual(routing.resolve(stage, None), [])
