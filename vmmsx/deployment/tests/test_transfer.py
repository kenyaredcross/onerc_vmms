# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""PART C — branch transfer, and the history it does not rewrite.

The design claim this suite exists to hold to account is a negative one: **a
transfer changes `VMMS Volunteer.home_geo_node` and nothing else.** A negative
claim is exactly the kind that rots quietly, because nothing fails when somebody
adds a well-meaning line that also updates the volunteer's past deployments. So
`TestHistoryIsNotRewritten` records every geo anchor a volunteer's history
carries, runs a transfer, and asserts each one is byte for byte what it was.

The access consequence is tested next, and separately, because it is the part
that is easy to *assume*. After a transfer the old branch keeps seeing the
records anchored beneath it and stops seeing the volunteer; the new branch sees
the volunteer and not the old records. `TestTheScopeConsequenceFallsOut` asserts
that through core's own `is_in_scope`, which is the same verdict the list view
and the API guard reach — so what it observes is what a coordinator would
observe, and no special-case code was written to produce it.

The approval half is configuration, and it is tested both ways: with the
society's setting empty (the shipped state, where a transfer applies directly)
and set to `routed` (where the engine gates it, and the wrong approver is
refused by the person-gate).
"""

import frappe
from frappe.utils import add_days, today
from onerc_core.access.services.enforcement import is_in_scope

from vmmsx.approvals import states
from vmmsx.approvals.services import engine
from vmmsx.deployment.services import transfer as transfer_service
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase
from vmmsx.volunteer.services import timelog

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TransferTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.terms = fixtures.make_terms()

	def volunteer_at(self, node: str, handle: str):
		return fixtures.make_volunteer(fixtures.make_profile(handle, "Moving"), node)


class TestATransferMovesThePlacement(TransferTestCase):
	def test_an_effective_transfer_moves_the_home_geo_node(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Alpha")
		transfer = fixtures.make_transfer(volunteer.name, self.society_a["other_branch"])

		transfer_service.submit(transfer)

		self.assertEqual(self.home_of(volunteer.name), self.society_a["other_branch"])
		self.assertEqual(transfer.transfer_status, transfer_service.STATUS_EFFECTIVE)
		self.assertTrue(transfer.applied_on)

	def test_the_origin_is_snapshotted_rather_than_typed(self):
		"""A transfer records where somebody was, not where the caller believed."""
		volunteer = self.volunteer_at(self.society_a["post"], "Beta")
		transfer = fixtures.make_transfer(volunteer.name, self.society_a["other_branch"])

		self.assertEqual(transfer.from_geo_node, self.society_a["post"])

	def test_the_origin_field_is_read_only_in_the_schema(self):
		field = frappe.get_meta(fixtures.TRANSFER_DOCTYPE).get_field("from_geo_node")

		self.assertTrue(field.read_only)
		self.assertTrue(field.reqd)

	def test_applying_twice_moves_nobody_twice(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Gamma")
		transfer = fixtures.make_transfer(volunteer.name, self.society_a["other_branch"])

		transfer_service.submit(transfer)
		stamp = transfer.applied_on

		self.assertIsNone(transfer_service.try_apply(transfer))
		self.assertEqual(transfer.applied_on, stamp)
		self.assertEqual(self.home_of(volunteer.name), self.society_a["other_branch"])

	def test_a_future_transfer_waits_for_its_date(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Delta")
		transfer = fixtures.make_transfer(
			volunteer.name, self.society_a["other_branch"], effective_date=add_days(today(), 30)
		)

		transfer_service.submit(transfer)

		self.assertEqual(transfer.transfer_status, transfer_service.STATUS_PENDING)
		self.assertEqual(self.home_of(volunteer.name), self.society_a["branch"])

	def test_the_daily_sweep_applies_it_when_the_day_comes(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Epsilon")
		transfer = fixtures.make_transfer(
			volunteer.name, self.society_a["other_branch"], effective_date=add_days(today(), 30)
		)
		transfer_service.submit(transfer)

		summary = transfer_service.apply_due(on_date=add_days(today(), 30))

		# At least this one: the sweep is site-wide, and the transaction rolls
		# back once per class, so a sibling test's pending transfer may be due on
		# the same day. What this test is about is that *this* one was applied.
		self.assertGreaterEqual(summary["applied"], 1)
		self.assertEqual(self.home_of(volunteer.name), self.society_a["other_branch"])
		self.assertEqual(
			self.reload_transfer(transfer.name).transfer_status, transfer_service.STATUS_EFFECTIVE
		)

	def test_the_sweep_is_idempotent(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Zeta")
		transfer = fixtures.make_transfer(
			volunteer.name, self.society_a["other_branch"], effective_date=add_days(today(), 10)
		)
		transfer_service.submit(transfer)

		transfer_service.apply_due(on_date=add_days(today(), 10))
		second = transfer_service.apply_due(on_date=add_days(today(), 10))

		self.assertEqual(second["applied"], 0)
		self.assertEqual(self.home_of(volunteer.name), self.society_a["other_branch"])


class TestHistoryIsNotRewritten(TransferTestCase):
	"""The claim the whole design rests on, asserted rather than asserted-to.

	Everything the volunteer's history carries a Geo Node on is recorded before
	the transfer and compared afterwards. A future author who adds a well-meaning
	"and update their past records" line breaks this and nothing else.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.volunteer = fixtures.make_volunteer(
			fixtures.make_profile("Historic", "Volunteer"), cls.society_a["branch"]
		)

		# A deployment they served on at the old branch, and time logged on it.
		cls.deployment = fixtures.make_deployment(
			cls.terms.name,
			cls.society_a["branch"],
			participants=[cls.volunteer.name],
			start_date=add_days(today(), -30),
			end_date=add_days(today(), -20),
		)
		cls.deployment_log = fixtures.make_time_log(
			cls.volunteer.name,
			cls.society_a["branch"],
			log_type=timelog.TYPE_DEPLOYMENT,
			deployment=cls.deployment.name,
			activity_date=add_days(today(), -25),
		)
		cls.general_log = fixtures.make_time_log(
			cls.volunteer.name, cls.society_a["post"], activity_date=add_days(today(), -10)
		)

		fixtures.make_certification_type(fixtures.CERT_RADIO)
		cls.certification = fixtures.make_certification(cls.volunteer.name, fixtures.CERT_RADIO)

		# Everything the history carries, recorded *before* the transfer runs.
		# The transfer happens once, here, rather than once per method: a
		# volunteer can only be moved out of a branch they are still in, and each
		# assertion below is about the same single move.
		cls.before = cls.snapshot()

		cls.transfer = fixtures.make_transfer(cls.volunteer.name, cls.society_a["other_branch"])
		transfer_service.submit(cls.transfer)

	@classmethod
	def snapshot(cls) -> dict:
		"""Every geo anchor and date this volunteer's history carries."""
		return {
			"deployment_anchor": frappe.db.get_value(
				fixtures.DEPLOYMENT_DOCTYPE, cls.deployment.name, "geo_node"
			),
			"deployment_log_anchor": frappe.db.get_value(
				fixtures.TIME_LOG_DOCTYPE, cls.deployment_log.name, "geo_node"
			),
			"general_log_anchor": frappe.db.get_value(
				fixtures.TIME_LOG_DOCTYPE, cls.general_log.name, "geo_node"
			),
			"deployment_log_link": frappe.db.get_value(
				fixtures.TIME_LOG_DOCTYPE, cls.deployment_log.name, "deployment"
			),
			"certification": frappe.db.get_value(
				fixtures.CERTIFICATION_DOCTYPE,
				cls.certification.name,
				["completion_date", "expiry_date"],
			),
		}

	def test_the_placement_moved(self):
		self.assertEqual(self.home_of(self.volunteer.name), self.society_a["other_branch"])
		self.assertEqual(self.transfer.transfer_status, transfer_service.STATUS_EFFECTIVE)

	def test_and_nothing_in_the_history_did(self):
		"""Every recorded anchor and date, compared to what it was before the move."""
		self.assertEqual(self.snapshot(), self.before)

	def test_the_history_is_still_anchored_at_the_old_branch(self):
		"""Stated positively, so the comparison above cannot pass on two empties."""
		after = self.snapshot()

		self.assertEqual(after["deployment_anchor"], self.society_a["branch"])
		self.assertEqual(after["deployment_log_anchor"], self.society_a["branch"])
		self.assertEqual(after["general_log_anchor"], self.society_a["post"])

	def test_the_volunteer_stays_on_the_deployments_they_served(self):
		from vmmsx.deployment.services import participation

		self.assertIn(self.volunteer.name, participation.participants_of(self.deployment.name))
		self.assertIn(self.deployment.name, participation.deployments_of(self.volunteer.name))

	def test_their_certifications_are_untouched(self):
		"""A certification is not about a place, and a move does not renew or lapse one."""
		self.assertEqual(self.snapshot()["certification"], self.before["certification"])

	def test_the_rule_is_written_down_where_the_write_is(self):
		rule = transfer_service.HISTORY_RULE.lower()

		self.assertIn("home_geo_node", rule)
		self.assertIn("nothing else", rule)
		self.assertIn("time logs", rule)

	def test_the_module_makes_exactly_one_kind_of_write_to_a_volunteers_history(self):
		"""None. The service names no historical doctype at all.

		Asserted against the source, because the guarantee is that the code has
		no opportunity to rewrite history rather than that it currently chooses
		not to.
		"""
		from pathlib import Path

		source = Path(frappe.get_app_path("vmmsx"), "deployment", "services", "transfer.py").read_text()
		code = _code_only(source)

		self.assertNotIn(fixtures.TIME_LOG_DOCTYPE, code)
		self.assertNotIn(fixtures.CERTIFICATION_DOCTYPE, code)


class TestTheScopeConsequenceFallsOut(TransferTestCase):
	"""Who sees what afterwards, asked of core rather than asserted about.

	No code in this module produces any of these answers. They are what geo scope
	already means, applied to one field that moved and several that did not.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.old_branch = cls.society_a["branch"]
		cls.new_branch = cls.society_a["other_branch"]

		cls.old_coordinator = fixtures.make_user("old_branch_coordinator")
		fixtures.grant_scope(cls.old_coordinator, fixtures.VOLUNTEER_SCOPE_ROLE, cls.old_branch)
		fixtures.grant_scope(cls.old_coordinator, fixtures.DEPLOYMENT_SCOPE_ROLE, cls.old_branch)

		cls.new_coordinator = fixtures.make_user("new_branch_coordinator")
		fixtures.grant_scope(cls.new_coordinator, fixtures.VOLUNTEER_SCOPE_ROLE, cls.new_branch)
		fixtures.grant_scope(cls.new_coordinator, fixtures.DEPLOYMENT_SCOPE_ROLE, cls.new_branch)

	def sees_volunteer(self, user: str, node: str) -> bool:
		return is_in_scope(fixtures.VOLUNTEER_DOCTYPE, node, user)

	def test_before_the_transfer_the_old_branch_sees_the_volunteer_and_the_new_does_not(self):
		volunteer = self.volunteer_at(self.old_branch, "Beforehand")

		self.assertTrue(self.sees_volunteer(self.old_coordinator, self.home_of(volunteer.name)))
		self.assertFalse(self.sees_volunteer(self.new_coordinator, self.home_of(volunteer.name)))

	def test_after_the_transfer_the_new_branch_sees_them_as_current(self):
		volunteer = self.volunteer_at(self.old_branch, "Afterwards")
		transfer_service.submit(fixtures.make_transfer(volunteer.name, self.new_branch))

		self.assertTrue(self.sees_volunteer(self.new_coordinator, self.home_of(volunteer.name)))

	def test_after_the_transfer_the_old_branch_no_longer_sees_them_as_theirs(self):
		volunteer = self.volunteer_at(self.old_branch, "Departed")
		transfer_service.submit(fixtures.make_transfer(volunteer.name, self.new_branch))

		self.assertFalse(self.sees_volunteer(self.old_coordinator, self.home_of(volunteer.name)))

	def test_the_old_branch_keeps_seeing_the_deployment_it_ran(self):
		"""The record's own anchor did not move, so neither did who may see it."""
		volunteer = self.volunteer_at(self.old_branch, "Servedhere")
		deployment = fixtures.make_deployment(self.terms.name, self.old_branch, participants=[volunteer.name])

		transfer_service.submit(fixtures.make_transfer(volunteer.name, self.new_branch))

		self.assertTrue(is_in_scope(fixtures.DEPLOYMENT_DOCTYPE, deployment.geo_node, self.old_coordinator))

	def test_the_new_branch_does_not_inherit_the_old_branchs_deployments(self):
		volunteer = self.volunteer_at(self.old_branch, "Nothanded")
		deployment = fixtures.make_deployment(self.terms.name, self.old_branch, participants=[volunteer.name])

		transfer_service.submit(fixtures.make_transfer(volunteer.name, self.new_branch))

		self.assertFalse(is_in_scope(fixtures.DEPLOYMENT_DOCTYPE, deployment.geo_node, self.new_coordinator))

	def test_the_transfer_record_stays_with_the_branch_it_is_about(self):
		"""Anchored on `from_geo_node`, so the branch that lost somebody keeps the record."""
		volunteer = self.volunteer_at(self.old_branch, "Recorded")
		transfer = fixtures.make_transfer(volunteer.name, self.new_branch)
		transfer_service.submit(transfer)

		fixtures.grant_scope(self.old_coordinator, fixtures.TRANSFER_SCOPE_ROLE, self.old_branch)

		self.assertTrue(is_in_scope(fixtures.TRANSFER_DOCTYPE, transfer.from_geo_node, self.old_coordinator))


class TestTheRulesOnRaisingOne(TransferTestCase):
	def test_a_transfer_to_where_they_already_are_is_refused(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Stationary")

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_transfer(volunteer.name, self.society_a["branch"])

	def test_a_second_open_transfer_is_refused(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Twice")
		fixtures.make_transfer(
			volunteer.name, self.society_a["other_branch"], effective_date=add_days(today(), 30)
		)

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_transfer(
				volunteer.name, self.society_a["post"], effective_date=add_days(today(), 40)
			)

	def test_a_destination_at_the_wrong_level_is_refused(self):
		"""ACC-03, asked of the *volunteer's* setting rather than a second one.

		A transfer may not put somebody somewhere they could not have been
		registered, and the rule that says so is the one the register already
		uses.
		"""
		fixtures.set_volunteer_anchor_level(self.society_a["levels"]["branch"])
		self.addCleanup(fixtures.set_volunteer_anchor_level, None)

		volunteer = fixtures.make_volunteer(
			fixtures.make_profile("Levelled", "Volunteer"), self.society_a["branch"]
		)

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_transfer(volunteer.name, self.society_a["post"])

	def test_a_reason_is_required(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Unexplained")

		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_transfer(volunteer.name, self.society_a["other_branch"], reason=None)


class TestCancellingAndOvertaking(TransferTestCase):
	def test_a_pending_transfer_can_be_cancelled(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Cancelled")
		transfer = fixtures.make_transfer(
			volunteer.name, self.society_a["other_branch"], effective_date=add_days(today(), 30)
		)

		transfer_service.cancel(transfer, "Changed their mind.")

		self.assertEqual(transfer.transfer_status, transfer_service.STATUS_CANCELLED)
		self.assertEqual(self.home_of(volunteer.name), self.society_a["branch"])

	def test_a_cancelled_transfer_never_applies(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Neverapplied")
		transfer = fixtures.make_transfer(
			volunteer.name, self.society_a["other_branch"], effective_date=add_days(today(), 5)
		)
		transfer_service.cancel(transfer)

		transfer_service.apply_due(on_date=add_days(today(), 10))

		self.assertEqual(self.home_of(volunteer.name), self.society_a["branch"])

	def test_an_effective_transfer_cannot_be_cancelled(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Alreadygone")
		transfer = fixtures.make_transfer(volunteer.name, self.society_a["other_branch"])
		transfer_service.submit(transfer)

		with self.assertRaises(frappe.ValidationError):
			transfer_service.cancel(transfer)

	def test_an_effective_transfer_cannot_be_deleted(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Undeletable")
		transfer = fixtures.make_transfer(volunteer.name, self.society_a["other_branch"])
		transfer_service.submit(transfer)

		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc(fixtures.TRANSFER_DOCTYPE, transfer.name)

	def test_a_transfer_overtaken_by_another_move_is_not_applied(self):
		"""Moving somebody from a place they are no longer in is a silent overwrite.

		The transfer sits Pending and the sweep counts it, so it is visible rather
		than quietly stalled.
		"""
		volunteer = self.volunteer_at(self.society_a["branch"], "Overtaken")
		transfer = fixtures.make_transfer(
			volunteer.name, self.society_a["other_branch"], effective_date=add_days(today(), 20)
		)
		transfer_service.submit(transfer)

		# Something else moves them in the meantime.
		volunteer.home_geo_node = self.society_a["post"]
		volunteer.save(ignore_permissions=True)

		summary = transfer_service.apply_due(on_date=add_days(today(), 20))

		self.assertEqual(summary["applied"], 0)
		self.assertEqual(summary["overtaken"], 1)
		self.assertEqual(self.home_of(volunteer.name), self.society_a["post"])
		self.assertEqual(self.reload_transfer(transfer.name).transfer_status, transfer_service.STATUS_PENDING)


class TestTheRoutedMode(TransferTestCase):
	"""With `routed` configured, the engine gates the move. Nothing else does."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.grant_doctype_access(fixtures.TRANSFER_DOCTYPE, fixtures.TRANSFER_APPROVER_ROLE)
		fixtures.make_workflow(
			fixtures.TRANSFER_DOCTYPE, fixtures.TRANSFER_APPROVER_ROLE, geo_node_field="from_geo_node"
		)

		cls.approver = fixtures.make_user("transfer_approver")
		fixtures.grant_scope(cls.approver, fixtures.TRANSFER_APPROVER_ROLE, cls.society_a["branch"])
		fixtures.grant_scope(cls.approver, fixtures.TRANSFER_SCOPE_ROLE, cls.society_a["region"])
		frappe.get_doc("User", cls.approver).add_roles(fixtures.TRANSFER_APPROVER_ROLE)

		cls.other_approver = fixtures.make_user("wrong_transfer_approver")
		fixtures.grant_scope(
			cls.other_approver, fixtures.TRANSFER_APPROVER_ROLE, cls.society_a["other_branch"]
		)
		fixtures.grant_scope(cls.other_approver, fixtures.TRANSFER_SCOPE_ROLE, cls.society_a["region"])
		frappe.get_doc("User", cls.other_approver).add_roles(fixtures.TRANSFER_APPROVER_ROLE)

	def setUp(self):
		super().setUp()
		fixtures.set_transfer_mode("routed")
		self.addCleanup(fixtures.set_transfer_mode, None)

	def routed_transfer(self, handle: str):
		volunteer = fixtures.make_volunteer(fixtures.make_profile(handle, "Routed"), self.society_a["post"])
		transfer = fixtures.make_transfer(volunteer.name, self.society_a["other_branch"])
		transfer_service.submit(transfer)

		return volunteer, transfer

	def test_a_routed_transfer_does_not_move_anybody_until_it_is_approved(self):
		volunteer, transfer = self.routed_transfer("Waiting")

		self.assertEqual(self.approval_state(fixtures.TRANSFER_DOCTYPE, transfer.name), states.IN_REVIEW)
		self.assertEqual(self.home_of(volunteer.name), self.society_a["post"])

	def test_it_routes_from_the_branch_the_volunteer_is_leaving(self):
		"""The default: the branch currently responsible authorises the release."""
		_volunteer, transfer = self.routed_transfer("Released")

		self.assertEqual(engine.authorised(transfer)["approvers"], [self.approver])

	def test_approving_it_moves_the_volunteer(self):
		volunteer, transfer = self.routed_transfer("Approved")

		with fixtures.acting_as(self.approver):
			engine.decide(transfer, states.DECISION_APPROVED)

		self.assertEqual(self.home_of(volunteer.name), self.society_a["other_branch"])
		self.assertEqual(
			self.reload_transfer(transfer.name).transfer_status, transfer_service.STATUS_EFFECTIVE
		)

	def test_the_wrong_approver_is_refused_even_holding_the_role(self):
		volunteer, transfer = self.routed_transfer("Refused")

		self.assertIn(fixtures.TRANSFER_APPROVER_ROLE, frappe.get_roles(self.other_approver))

		with fixtures.acting_as(self.other_approver), self.assertRaises(frappe.PermissionError):
			engine.decide(transfer, states.DECISION_APPROVED)

		self.assertEqual(self.home_of(volunteer.name), self.society_a["post"])

	def test_a_rejected_transfer_never_moves_anybody(self):
		volunteer, transfer = self.routed_transfer("Rejected")

		with fixtures.acting_as(self.approver):
			engine.decide(transfer, states.DECISION_REJECTED, reason="Not now.")

		self.assertEqual(self.home_of(volunteer.name), self.society_a["post"])
		self.assertFalse(transfer_service.is_applicable(self.reload_transfer(transfer.name)))

	def test_the_shipped_default_applies_directly(self):
		"""Empty configuration is the direct mode, and it changes nothing about a site."""
		fixtures.set_transfer_mode(None)

		volunteer = fixtures.make_volunteer(
			fixtures.make_profile("Default", "Mode"), self.society_a["branch"]
		)
		transfer = fixtures.make_transfer(volunteer.name, self.society_a["other_branch"])
		transfer_service.submit(transfer)

		self.assertEqual(transfer_service.mode(), "direct")
		self.assertEqual(self.home_of(volunteer.name), self.society_a["other_branch"])
		self.assertEqual(self.approval_state(fixtures.TRANSFER_DOCTYPE, transfer.name), states.DRAFT)


class TestMidDeploymentIsRecordedNotDecided(TransferTestCase):
	"""A transfer while somebody is deployed is reported, and changes nothing.

	Whether it should be refused, deferred, or allowed is a society's policy
	nobody has chosen. Recording it is the only one of the three that does not
	invent a rule, and the choice is flagged in the module's own docstring.
	"""

	def test_an_in_flight_deployment_is_reported(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Deployed")
		deployment = fixtures.make_deployment(
			self.terms.name,
			self.society_a["branch"],
			participants=[volunteer.name],
			start_date=add_days(today(), -1),
			end_date=add_days(today(), 5),
		)

		transfer = fixtures.make_transfer(volunteer.name, self.society_a["other_branch"])

		self.assertEqual(transfer_service.in_flight_deployments(transfer), [deployment.name])

	def test_the_transfer_still_applies_and_the_deployment_is_untouched(self):
		volunteer = self.volunteer_at(self.society_a["branch"], "Stilldeployed")
		deployment = fixtures.make_deployment(
			self.terms.name,
			self.society_a["branch"],
			participants=[volunteer.name],
			start_date=add_days(today(), -1),
			end_date=add_days(today(), 5),
		)

		transfer_service.submit(fixtures.make_transfer(volunteer.name, self.society_a["other_branch"]))

		self.assertEqual(self.home_of(volunteer.name), self.society_a["other_branch"])
		self.assertEqual(
			self.anchor_of(fixtures.DEPLOYMENT_DOCTYPE, deployment.name), self.society_a["branch"]
		)
		self.assertEqual(
			frappe.db.get_value(fixtures.DEPLOYMENT_DOCTYPE, deployment.name, "status"), "Planned"
		)

	def test_the_volunteer_may_still_log_time_against_it_afterwards(self):
		"""Ownership is the roster, and the roster did not change."""
		volunteer = self.volunteer_at(self.society_a["branch"], "Logsafter")
		deployment = fixtures.make_deployment(
			self.terms.name,
			self.society_a["branch"],
			participants=[volunteer.name],
			start_date=add_days(today(), -1),
			end_date=add_days(today(), 5),
		)

		transfer_service.submit(fixtures.make_transfer(volunteer.name, self.society_a["other_branch"]))

		log = fixtures.make_time_log(
			volunteer.name,
			self.society_a["branch"],
			log_type=timelog.TYPE_DEPLOYMENT,
			deployment=deployment.name,
		)

		self.assertTrue(log.name)


def _code_only(source: str) -> str:
	"""The source with docstrings removed."""
	import ast

	tree = ast.parse(source)
	docstrings = set()

	for node in ast.walk(tree):
		if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
			continue

		if node.body and isinstance(node.body[0], ast.Expr):
			value = node.body[0].value

			if isinstance(value, ast.Constant) and isinstance(value.value, str):
				docstrings.add(id(value))

	class StripDocstrings(ast.NodeTransformer):
		def visit_Expr(self, node):
			if isinstance(node.value, ast.Constant) and id(node.value) in docstrings:
				return None

			return node

	return ast.unparse(StripDocstrings().visit(tree))
