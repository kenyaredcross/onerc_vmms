# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""PART A — the deployment time log's ownership rule, finished and enforced.

The volunteer spine shipped this kind of log as an explicit stub: it refused
with a message naming stage 4, because there was no Deployment doctype and
therefore nothing to check participation against. This suite is what that stub
was waiting for, and it is written to break the rule rather than to demonstrate
it.

Four things are asserted, and each of them can fail independently:

1. **A participant's log saves.** Otherwise the rule is just a refusal.
2. **A non-participant's log is refused at save**, not hidden. The check is on
   the server, so it holds for a document built in code with no form, no picker
   and no client script anywhere near it — which is exactly how somebody would
   fabricate participation if they could.
3. **The general path is unchanged.** A rule that broke the kind of log that was
   already working would be a regression wearing a feature's name.
4. **The stub is gone**, from the code and from the message. A refusal that
   still said "stage 4" would mean the log was refused for the old reason.

**Authority is deliberately not the variable.** The user filing the logs below
is an administrator: the point of the ownership rule is that it is not a
permission check, and a test where the refusal could have come from the
permission layer would prove nothing about ownership. See
`participation.assert_participant`, which throws a ValidationError for exactly
that reason.
"""

import ast
from pathlib import Path

import frappe
from frappe.utils import add_days, today

from vmmsx.deployment.services import participation
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase
from vmmsx.volunteer.services import timelog

EXTRA_TEST_RECORD_DEPENDENCIES = []


class OwnershipTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.terms = fixtures.make_terms()

		cls.insider = fixtures.make_volunteer(
			fixtures.make_profile("Wanjiru", "Onthedeployment"), cls.society_a["branch"]
		)
		cls.outsider = fixtures.make_volunteer(
			fixtures.make_profile("Kioko", "Notonit"), cls.society_a["branch"]
		)

		cls.deployment = fixtures.make_deployment(
			cls.terms.name, cls.society_a["branch"], participants=[cls.insider.name]
		)

	def deployment_log(self, volunteer: str, deployment: str, **overrides):
		return fixtures.make_time_log(
			volunteer,
			overrides.pop("geo_node", self.society_a["branch"]),
			log_type=timelog.TYPE_DEPLOYMENT,
			deployment=deployment,
			**overrides,
		)


class TestAParticipantMayLogAgainstTheirDeployment(OwnershipTestCase):
	def test_a_participants_deployment_log_saves(self):
		log = self.deployment_log(self.insider.name, self.deployment.name)

		self.assertEqual(log.log_type, timelog.TYPE_DEPLOYMENT)
		self.assertEqual(log.deployment, self.deployment.name)
		self.assertEqual(log.volunteer, self.insider.name)

	def test_it_counts_towards_the_hours_served(self):
		"""The total names no kind, so the new kind joined it without a change."""
		volunteer = fixtures.make_volunteer(
			fixtures.make_profile("Summed", "Ondeployment"), self.society_a["branch"]
		)
		deployment = fixtures.make_deployment(
			self.terms.name, self.society_a["branch"], participants=[volunteer.name]
		)

		fixtures.make_time_log(volunteer.name, self.society_a["branch"], hours=3)
		self.deployment_log(volunteer.name, deployment.name, hours=5)

		self.assertEqual(timelog.hours_served(volunteer.name), 8)

	def test_a_participant_may_log_after_the_deployment_has_completed(self):
		"""Filing late is filing accurately, so status does not gate ownership.

		The rule the stub specified was about participation, and only about
		participation. Refusing a participant's own hours because the deployment
		has since been closed would punish the person who kept records properly.
		"""
		volunteer = fixtures.make_volunteer(fixtures.make_profile("Late", "Filer"), self.society_a["branch"])
		deployment = fixtures.make_deployment(
			self.terms.name,
			self.society_a["branch"],
			participants=[volunteer.name],
			start_date=add_days(today(), -30),
			end_date=add_days(today(), -20),
		)
		deployment.status = "Completed"
		deployment.save()

		log = self.deployment_log(volunteer.name, deployment.name, activity_date=add_days(today(), -25))

		self.assertTrue(log.name)


class TestANonParticipantIsRefusedAtSave(OwnershipTestCase):
	def test_a_log_against_a_deployment_they_are_not_on_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.deployment_log(self.outsider.name, self.deployment.name)

	def test_nothing_is_saved_when_the_ownership_rule_fires(self):
		before = frappe.db.count(fixtures.TIME_LOG_DOCTYPE)

		with self.assertRaises(frappe.ValidationError):
			self.deployment_log(self.outsider.name, self.deployment.name)

		self.assertEqual(frappe.db.count(fixtures.TIME_LOG_DOCTYPE), before)

	def test_being_correctly_placed_does_not_make_somebody_a_participant(self):
		"""The whole distinction, in one test.

		The outsider is anchored at the same Geo Node as the deployment, so every
		geo question about them answers yes. They are still not on it.
		"""
		self.assertEqual(self.outsider.home_geo_node, self.deployment.geo_node)

		with self.assertRaises(frappe.ValidationError):
			self.deployment_log(self.outsider.name, self.deployment.name)

	def test_the_refusal_survives_an_administrator(self):
		"""It is not a permission check, so holding every permission does not help.

		Frappe's Administrator bypasses core's geo scoping outright. If the
		ownership rule were expressed as a permission, this would save.
		"""
		self.assertEqual(frappe.session.user, "Administrator")

		with self.assertRaises(frappe.ValidationError):
			self.deployment_log(self.outsider.name, self.deployment.name)

	def test_naming_a_deployment_that_does_not_exist_is_refused(self):
		"""A caller who invents a docname is refused by the roster, not by a Link.

		Asserted separately because a Link's own existence check and the roster
		check are two different refusals, and only the second is the rule.
		"""
		self.assertFalse(participation.is_participant("DEP-NOPE", self.insider.name))

		with self.assertRaises(frappe.ValidationError):
			self.deployment_log(self.insider.name, "DEP-NOPE")

	def test_a_deployment_log_with_no_deployment_is_refused(self):
		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_time_log(
				self.insider.name, self.society_a["branch"], log_type=timelog.TYPE_DEPLOYMENT
			)

	def test_withdrawing_somebody_stops_their_logs(self):
		"""The rule reads the register now, not the roster the caller once saw.

		Withdrawing is what taking somebody off looks like since the roster became
		a register of documents: the assignment stays, so the society keeps the
		record that this person was on the deployment and was taken off it, and
		the ownership rule stops admitting their logs from that moment.
		"""
		from vmmsx.deployment.services import assignment

		volunteer = fixtures.make_volunteer(fixtures.make_profile("Was", "Onit"), self.society_a["branch"])
		deployment = fixtures.make_deployment(
			self.terms.name, self.society_a["branch"], participants=[volunteer.name]
		)

		self.assertTrue(self.deployment_log(volunteer.name, deployment.name).name)

		assignment.withdraw(assignment.open_assignment(deployment.name, volunteer.name))

		with self.assertRaises(frappe.ValidationError):
			self.deployment_log(volunteer.name, deployment.name)


class TestTheAnchorStillHoldsOnEveryKind(OwnershipTestCase):
	"""ACC-02 is checked before the dispatch, so it outranks the ownership rule."""

	def test_a_deployment_log_with_no_anchor_is_refused_for_the_anchor(self):
		with self.assertRaises(frappe.MandatoryError):
			self.deployment_log(self.insider.name, self.deployment.name, geo_node=None)

	def test_a_general_log_with_no_anchor_is_still_refused(self):
		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_time_log(self.insider.name, None)


class TestTheGeneralPathIsUnchanged(OwnershipTestCase):
	def test_a_general_log_still_saves(self):
		log = fixtures.make_time_log(self.outsider.name, self.society_a["branch"], hours=6)

		self.assertEqual(log.log_type, timelog.TYPE_GENERAL)
		self.assertEqual(log.hours, 6)

	def test_a_general_log_needs_no_deployment_and_no_participation(self):
		"""The outsider is on nothing, and files a general log without difficulty."""
		self.assertEqual(participation.deployments_of(self.outsider.name), [])
		self.assertTrue(fixtures.make_time_log(self.outsider.name, self.society_a["branch"]).name)

	def test_a_general_log_naming_a_deployment_is_still_refused(self):
		"""Permanent, and not the ownership rule: the insider *is* a participant."""
		self.assertTrue(participation.is_participant(self.deployment.name, self.insider.name))

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_time_log(
				self.insider.name, self.society_a["branch"], deployment=self.deployment.name
			)


class TestTwoDeploymentsAtTwoPlaces(OwnershipTestCase):
	"""One volunteer, two deployments, two Geo Nodes, and no bleed between them.

	The failure this is written to catch is an ownership check that answers "is
	this volunteer on *a* deployment" rather than "on *this* deployment". That
	implementation passes every single-deployment test above and is wrong the
	moment somebody serves in two places, which for an active volunteer is the
	ordinary case rather than an edge one.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.roamer = fixtures.make_volunteer(
			fixtures.make_profile("Njeri", "Twoplaces"), cls.society_a["branch"]
		)
		cls.homebody = fixtures.make_volunteer(
			fixtures.make_profile("Otieno", "Oneplace"), cls.society_a["branch"]
		)

		# Two deployments, at two different nodes in two different subtrees.
		cls.here = fixtures.make_deployment(
			cls.terms.name, cls.society_a["post"], participants=[cls.roamer.name, cls.homebody.name]
		)
		cls.there = fixtures.make_deployment(
			cls.terms.name, cls.society_a["other_post"], participants=[cls.roamer.name]
		)

	def test_the_volunteer_on_both_may_log_against_both(self):
		# Measured as a delta: the transaction rolls back once per class, so
		# another method in this class may already have logged hours for them.
		before = timelog.hours_served(self.roamer.name)

		first = self.deployment_log(self.roamer.name, self.here.name, geo_node=self.society_a["post"])
		second = self.deployment_log(self.roamer.name, self.there.name, geo_node=self.society_a["other_post"])

		self.assertEqual(first.deployment, self.here.name)
		self.assertEqual(second.deployment, self.there.name)
		self.assertEqual(timelog.hours_served(self.roamer.name) - before, 8)

	def test_the_volunteer_on_one_is_refused_against_the_other(self):
		"""Being a participant somewhere is not being a participant here."""
		self.assertTrue(participation.is_participant(self.here.name, self.homebody.name))
		self.assertFalse(participation.is_participant(self.there.name, self.homebody.name))

		self.assertTrue(self.deployment_log(self.homebody.name, self.here.name).name)

		with self.assertRaises(frappe.ValidationError):
			self.deployment_log(self.homebody.name, self.there.name)

	def test_each_roster_answers_only_for_itself(self):
		self.assertEqual(
			set(participation.participants_of(self.here.name)),
			{self.roamer.name, self.homebody.name},
		)
		self.assertEqual(participation.participants_of(self.there.name), [self.roamer.name])

	def test_the_reverse_question_returns_both_and_only_both(self):
		"""Which deployments was this volunteer on: the query the shape had to serve."""
		self.assertEqual(
			set(participation.deployments_of(self.roamer.name)), {self.here.name, self.there.name}
		)
		self.assertEqual(participation.deployments_of(self.homebody.name), [self.here.name])

	def test_the_logs_are_attributable_to_the_right_deployment_afterwards(self):
		"""Reporting per deployment is the point of storing the link at all."""

		def hours_on(deployment: str) -> float:
			return sum(
				frappe.get_all(
					fixtures.TIME_LOG_DOCTYPE,
					filters={"volunteer": self.roamer.name, "deployment": deployment},
					pluck="hours",
				)
			)

		# Deltas, because the transaction rolls back once per class rather than
		# once per method and a sibling test may already have logged for them.
		before = (hours_on(self.here.name), hours_on(self.there.name))

		self.deployment_log(self.roamer.name, self.here.name, hours=2)
		self.deployment_log(self.roamer.name, self.there.name, hours=6)

		self.assertEqual(hours_on(self.here.name) - before[0], 2)
		self.assertEqual(hours_on(self.there.name) - before[1], 6)


class TestTheStubIsGone(OwnershipTestCase):
	def test_the_service_no_longer_names_stage_4(self):
		source = Path(frappe.get_app_path("vmmsx"), "volunteer", "services", "timelog.py").read_text()

		self.assertNotIn("DEPLOYMENT_LOGS_AWAIT_STAGE_4", source)
		self.assertNotIn("PENDING_OWNERSHIP_RULE", source)
		self.assertNotIn("stage 4", source.lower())

	def test_the_constants_are_gone_from_the_module(self):
		self.assertFalse(hasattr(timelog, "DEPLOYMENT_LOGS_AWAIT_STAGE_4"))
		self.assertFalse(hasattr(timelog, "PENDING_OWNERSHIP_RULE"))

	def test_the_deployment_field_is_a_real_link_now(self):
		field = frappe.get_meta(fixtures.TIME_LOG_DOCTYPE).get_field("deployment")

		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, fixtures.DEPLOYMENT_DOCTYPE)

	def test_the_old_data_field_is_gone(self):
		self.assertIsNone(frappe.get_meta(fixtures.TIME_LOG_DOCTYPE).get_field("deployment_reference"))

	def test_the_rule_that_replaced_it_says_what_it_is(self):
		"""The specification moved from the stub to the module that enforces it.

		Asserted against the named constant rather than against prose, so the
		test cannot drift from the rule, and the words that mattered in the
		original specification are the words that survive.
		"""
		rule = participation.OWNERSHIP_RULE.lower()

		self.assertIn("ownership", rule)
		self.assertIn("participant", rule)
		self.assertIn("server", rule)
		self.assertIn("not geo scoping", rule)


class TestTheDiscriminatorIsStillDispatched(OwnershipTestCase):
	"""No scattered comparisons. One table, in one module, still.

	The rule survived the kind becoming real, which is the moment it was most
	likely to be broken: an author wiring up a deployment log is one `if` away
	from putting `log_type == "deployment"` in a caller.
	"""

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

	def test_every_kind_still_has_exactly_one_rule(self):
		self.assertEqual(set(timelog._VALIDATE), set(timelog.LOG_TYPES))


def _is_log_type(node) -> bool:
	"""`something.log_type` or `something["log_type"]`."""
	if isinstance(node, ast.Attribute):
		return node.attr == "log_type"

	if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
		return node.slice.value == "log_type"

	return False
