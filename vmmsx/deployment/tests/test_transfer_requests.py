# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A volunteer asks to move; the branch they leave releases them; the branch
they join accepts them.

Driven through the endpoints the portal and the console call, with a two-stage
workflow whose second stage is routed from `to_geo_node`
(`VMMS Approval Stage.anchor_field`), and with the transfer's own scoping
(`vmmsx/multi_anchor.py`) deciding who can open it.
"""

import frappe

from vmmsx.api import deployment as deployment_api
from vmmsx.api import transfers as transfers_api
from vmmsx.approvals import states
from vmmsx.approvals.services import engine
from vmmsx.deployment.services import transfer as transfer_service
from vmmsx import multi_anchor
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

ROLE = fixtures.TRANSFER_SCOPE_ROLE


class TestTransferRequests(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		from vmmsx.notifications.services import lifecycle

		lifecycle.install()

		branch_level = cls.society_a["levels"]["branch"]
		fixtures.grant_doctype_access(fixtures.TRANSFER_DOCTYPE, ROLE)
		# Opening a volunteer's record, which the console's move action stands on.
		fixtures.grant_doctype_access("VMMS Volunteer", fixtures.VOLUNTEER_SCOPE_ROLE)

		stage = {
			"required_role": ROLE,
			"resolution_rule": "at_level",
			"geo_level": branch_level,
			"completion_rule": "single",
			"can_reject": 1,
			"is_optional": 0,
			"sla_days": 5,
			"on_sla_breach": "notify_only",
		}
		fixtures.make_workflow(
			fixtures.TRANSFER_DOCTYPE,
			ROLE,
			geo_node_field="from_geo_node",
			applicant_field="volunteer",
			allow_withdrawal=1,
			stages=[
				{**stage, "sequence": 1, "stage_label": "Release"},
				{**stage, "sequence": 2, "stage_label": "Acceptance", "anchor_field": "to_geo_node"},
			],
		)

		cls.leaving = fixtures.make_user("transfer_leaving_cc")
		fixtures.grant_scope(cls.leaving, ROLE, cls.society_a["branch"])

		cls.joining = fixtures.make_user("transfer_joining_cc")
		fixtures.grant_scope(cls.joining, ROLE, cls.society_a["other_branch"])

		cls.elsewhere = fixtures.make_user("transfer_elsewhere_cc")
		fixtures.grant_scope(cls.elsewhere, ROLE, cls.society_b["district"])

	def setUp(self):
		super().setUp()
		fixtures.set_transfer_mode("routed")
		self.addCleanup(fixtures.set_transfer_mode, None)
		fixtures.set_volunteer_anchor_level(self.society_a["levels"]["branch"])
		self.addCleanup(fixtures.set_volunteer_anchor_level, None)

	def volunteer(self, handle: str):
		user = fixtures.make_user(f"transfer_{handle}")
		profile = fixtures.make_profile(handle.title(), "Mover", user=user, email=user)
		return user, fixtures.make_volunteer(profile, self.society_a["branch"])

	def ask(self, handle: str):
		user, volunteer = self.volunteer(handle)

		with fixtures.acting_as(user):
			row = transfers_api.request_my_transfer(self.society_a["other_branch"], "Moving for work.")

		return user, volunteer, frappe.get_doc(fixtures.TRANSFER_DOCTYPE, row["name"])

	def decide(self, user, transfer, decision=states.DECISION_APPROVED, reason=None):
		from vmmsx.api import approvals as approvals_api

		with fixtures.acting_as(user):
			approvals_api.decide(fixtures.TRANSFER_DOCTYPE, transfer.name, decision, reason)

		transfer.reload()

	def home(self, volunteer):
		return frappe.db.get_value("VMMS Volunteer", volunteer.name, "home_geo_node")

	# --- the volunteer asks ----------------------------------------------

	def test_the_request_goes_to_the_branch_they_are_leaving_first(self):
		_, volunteer, transfer = self.ask("first")

		self.assertTrue(transfer.requested_by_volunteer)
		self.assertEqual(transfer.from_geo_node, self.society_a["branch"])
		self.assertEqual(frappe.db.get_value(transfer.doctype, transfer.name, "approval_state"), states.IN_REVIEW)
		self.assertEqual(engine.authorised(transfer)["approvers"], [self.leaving])
		self.assertEqual(self.home(volunteer), self.society_a["branch"])

	def test_the_volunteer_is_told_it_was_received(self):
		_, _, transfer = self.ask("told")

		self.assertTrue(
			frappe.db.exists("Email Queue", {"reference_name": transfer.name}),
			"the acknowledgement was not queued",
		)

	def test_released_it_goes_to_the_branch_they_are_joining(self):
		_, volunteer, transfer = self.ask("released")

		self.decide(self.leaving, transfer)

		self.assertEqual(transfer.approval_state, states.IN_REVIEW)
		self.assertEqual(engine.authorised(transfer)["approvers"], [self.joining])
		self.assertEqual(self.home(volunteer), self.society_a["branch"])

	def test_accepted_by_both_it_moves_them(self):
		_, volunteer, transfer = self.ask("accepted")

		self.decide(self.leaving, transfer)
		self.decide(self.joining, transfer)

		self.assertEqual(transfer.transfer_status, transfer_service.STATUS_EFFECTIVE)
		self.assertEqual(self.home(volunteer), self.society_a["other_branch"])
		self.assertEqual(
			frappe.db.count("Email Queue", {"reference_name": transfer.name}),
			2,
			"expected the acknowledgement and the approval, once each",
		)

	def test_the_joining_branch_cannot_decide_out_of_turn(self):
		_, _, transfer = self.ask("out.of.turn")

		with fixtures.acting_as(self.joining), self.assertRaises(frappe.PermissionError):
			engine.decide(transfer, states.DECISION_APPROVED)

	def test_declined_it_moves_nobody_and_says_why(self):
		_, volunteer, transfer = self.ask("declined")

		self.decide(self.leaving, transfer)
		self.decide(self.joining, transfer, states.DECISION_REJECTED, "No space in the unit this month.")

		self.assertEqual(transfer.approval_state, states.REJECTED)
		self.assertEqual(self.home(volunteer), self.society_a["branch"])
		messages = frappe.get_all("Email Queue", filters={"reference_name": transfer.name}, pluck="message")
		self.assertTrue(any("No space in the unit this month." in (message or "") for message in messages))

	def test_the_volunteer_can_take_it_back(self):
		user, volunteer, transfer = self.ask("withdrawn")

		with fixtures.acting_as(user):
			transfers_api.withdraw_my_transfer(transfer.name)

		transfer.reload()
		self.assertEqual(transfer.transfer_status, transfer_service.STATUS_CANCELLED)
		self.assertEqual(transfer.approval_state, states.WITHDRAWN)

	def test_they_see_their_own_request(self):
		user, _, transfer = self.ask("mine")

		with fixtures.acting_as(user):
			answer = transfers_api.my_transfer()

		mine = answer["transfer"]
		self.assertTrue(answer["can_request"])
		self.assertEqual(mine["name"], transfer.name)
		self.assertEqual(mine["waiting_on"], "Karura")
		self.assertEqual(mine["to_place"], "Limuru")

	def test_nobody_can_ask_where_transfers_are_not_decided_by_anyone(self):
		"""Direct mode would move them the moment they asked."""
		fixtures.set_transfer_mode(None)
		user, volunteer = self.volunteer("direct")

		with fixtures.acting_as(user):
			self.assertFalse(transfers_api.my_transfer()["can_request"])

			with self.assertRaises(frappe.ValidationError):
				transfers_api.request_my_transfer(self.society_a["other_branch"], "Because.")

		self.assertEqual(self.home(volunteer), self.society_a["branch"])

	def test_somebody_who_is_not_a_volunteer_cannot_ask(self):
		user = fixtures.make_user("transfer_nobody")

		with fixtures.acting_as(user), self.assertRaises(frappe.PermissionError):
			transfers_api.request_my_transfer(self.society_a["other_branch"], "Because.")

	def test_a_move_to_where_they_already_are_is_refused(self):
		user, _ = self.volunteer("same.place")

		with fixtures.acting_as(user), self.assertRaises(frappe.ValidationError):
			transfers_api.request_my_transfer(self.society_a["branch"], "Because.")

	def test_one_open_request_at_a_time(self):
		user, _, _ = self.ask("twice")

		with fixtures.acting_as(user), self.assertRaises(frappe.ValidationError):
			transfers_api.request_my_transfer(self.society_a["other_branch"], "Again.")

	# --- a coordinator raises it -----------------------------------------

	def test_a_transfer_the_branch_raises_is_already_released(self):
		_, volunteer = self.volunteer("raised")

		with fixtures.acting_as(self.leaving):
			row = deployment_api.request_transfer(
				volunteer.name, self.society_a["other_branch"], frappe.utils.today(), "Asked at the office."
			)

		transfer = frappe.get_doc(fixtures.TRANSFER_DOCTYPE, row["name"])
		self.assertFalse(transfer.requested_by_volunteer)
		self.assertEqual(engine.authorised(transfer)["approvers"], [self.joining])
		self.assertEqual(transfer.approval_decisions[0].approver, self.leaving)

	def test_the_record_offers_the_move_to_the_branch_they_are_at(self):
		_, volunteer = self.volunteer("record")
		fixtures.grant_scope(self.joining, fixtures.VOLUNTEER_SCOPE_ROLE, self.society_a["region"])
		fixtures.grant_scope(self.leaving, fixtures.VOLUNTEER_SCOPE_ROLE, self.society_a["branch"])

		with fixtures.acting_as(self.leaving):
			self.assertTrue(transfers_api.volunteer_transfer(volunteer.name)["can_raise"])

		with fixtures.acting_as(self.joining):
			self.assertFalse(
				transfers_api.volunteer_transfer(volunteer.name)["can_raise"],
				"only the branch they are at may raise their transfer",
			)

	def test_the_record_reports_a_transfer_already_open(self):
		_, volunteer, transfer = self.ask("record.open")
		fixtures.grant_scope(self.leaving, fixtures.VOLUNTEER_SCOPE_ROLE, self.society_a["branch"])

		with fixtures.acting_as(self.leaving):
			answer = transfers_api.volunteer_transfer(volunteer.name)

		self.assertFalse(answer["can_raise"])
		self.assertEqual(answer["transfer"]["name"], transfer.name)

	# --- who sees what ----------------------------------------------------

	def test_both_branches_can_open_it_and_nobody_else(self):
		_, _, transfer = self.ask("seen")

		self.assertTrue(multi_anchor.has_permission(transfer, "read", self.leaving))
		self.assertTrue(multi_anchor.has_permission(transfer, "read", self.joining))
		self.assertFalse(multi_anchor.has_permission(transfer, "read", self.elsewhere))

		with fixtures.acting_as(self.joining):
			self.assertIn(transfer.name, frappe.get_list(fixtures.TRANSFER_DOCTYPE, pluck="name"))

		with fixtures.acting_as(self.elsewhere):
			self.assertNotIn(transfer.name, frappe.get_list(fixtures.TRANSFER_DOCTYPE, pluck="name"))

	def test_only_the_branch_they_are_leaving_may_change_it(self):
		_, _, transfer = self.ask("changed")

		self.assertTrue(multi_anchor.has_permission(transfer, "write", self.leaving))
		self.assertFalse(multi_anchor.has_permission(transfer, "write", self.joining))

	def test_outgoing_and_incoming_are_each_branchs_own(self):
		_, _, transfer = self.ask("lists")

		with fixtures.acting_as(self.leaving):
			outgoing = transfers_api.branch_transfers("outgoing")["rows"]
			incoming = transfers_api.branch_transfers("incoming")["rows"]

		self.assertIn(transfer.name, [row["name"] for row in outgoing])
		self.assertNotIn(transfer.name, [row["name"] for row in incoming])
		self.assertTrue(next(row for row in outgoing if row["name"] == transfer.name)["can_act"])

		with fixtures.acting_as(self.joining):
			incoming = transfers_api.branch_transfers("incoming")["rows"]

		row = next(row for row in incoming if row["name"] == transfer.name)
		self.assertFalse(row["can_act"], "not theirs to decide until it is released")
		self.assertEqual(row["volunteer_name"], "Lists Mover")


class TestAStageRoutedFromAnotherField(DeploymentTestCase):
	def test_the_field_must_be_a_link_to_a_place(self):
		with self.assertRaises(frappe.ValidationError):
			fixtures.make_workflow(
				fixtures.TRANSFER_DOCTYPE,
				ROLE,
				geo_node_field="from_geo_node",
				stages=[
					{
						"sequence": 1,
						"stage_label": "Odd",
						"required_role": ROLE,
						"resolution_rule": "nearest_ancestor",
						"completion_rule": "single",
						"can_reject": 1,
						"sla_days": 5,
						"on_sla_breach": "none",
						"anchor_field": "reason",
					}
				],
			)
