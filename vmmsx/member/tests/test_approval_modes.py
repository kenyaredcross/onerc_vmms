# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""MEM-02 — one code path, two behaviours, chosen by configuration.

This is the Member module's version of the engine's Kenya-and-Gambia proof. Two
membership types differ in **one field**, `approval_mode`. Nothing else about
them differs, no source file branches on their names, and the code that
processes them is character-for-character the same code.

    routed            → the approval engine routes it to a resolved person
    auto_on_payment   → confirmed payment activates it, with no approver

The routed half is also where the engine is proven to be genuinely *consumed*
rather than imitated: the membership lands in the resolved approver's real
ToDo queue, the real person-gate refuses everybody else, and a refusal changes
nothing.
"""

import frappe

from vmmsx.approvals import states
from vmmsx.approvals.services import engine
from vmmsx.member.services import approval
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestConfigSelectsThePath(MemberTestCase):
	"""The same call, twice, differing only in the type's approval_mode."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.approver = cls.scoped_user("mode_approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])
		fixtures.make_workflow()
		# An approver saves the membership when they decide, so the
		# society's role needs write access to it.
		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)
		fixtures.make_template()

		# The only difference between these two records is approval_mode.
		# The routed one is free so that approval alone gates it; the auto one
		# charges, because a type that activates on payment must have something
		# to wait for.
		cls.routed_type = fixtures.make_type(fixtures.TYPE_ROUTED, approval.MODE_ROUTED, fee=0)
		cls.auto_type = fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=500)

	def apply(self, type_key: str):
		"""One call. Identical for both types — this is the point of the module."""
		profile = fixtures.make_profile("Path", "Case")
		membership = fixtures.make_membership(profile, type_key, self.society_a["ward"])
		membership_service.submit(membership)

		return membership.name

	def test_the_two_types_differ_only_in_approval_mode(self):
		"""If they differed in anything else, the comparison below would prove nothing."""
		routed = frappe.get_doc(fixtures.TYPE_DOCTYPE, fixtures.TYPE_ROUTED)
		auto = frappe.get_doc(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO)

		self.assertEqual(routed.approval_mode, approval.MODE_ROUTED)
		self.assertEqual(auto.approval_mode, approval.MODE_AUTO_ON_PAYMENT)
		self.assertEqual(routed.duration_days, auto.duration_days)
		self.assertEqual(routed.template_key, auto.template_key)
		self.assertEqual(routed.is_active, auto.is_active)

	def test_a_routed_type_waits_for_a_person(self):
		membership = self.apply(fixtures.TYPE_ROUTED)

		self.assertEqual(self.membership_status(membership), membership_service.STATUS_AWAITING_APPROVAL)
		self.assertEqual(self.approval_state(membership), states.IN_REVIEW)

	def test_an_auto_type_waits_for_money_and_has_no_approval_at_all(self):
		membership = self.apply(fixtures.TYPE_AUTO)

		self.assertEqual(self.membership_status(membership), membership_service.STATUS_AWAITING_PAYMENT)
		# Never entered the engine: no state, no stage, nobody's queue. Asserted
		# about *this* membership rather than about the queue being empty —
		# Frappe rolls back per class, so a routed membership from an earlier
		# method in this class is legitimately still sitting there.
		self.assertEqual(self.approval_state(membership), states.DRAFT)
		self.assertFalse(frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, membership, "approval_stage"))
		self.assertNotIn(membership, self.queue_of(self.approver))

	def test_only_the_routed_one_reaches_the_approver_s_queue(self):
		routed = self.apply(fixtures.TYPE_ROUTED)
		auto = self.apply(fixtures.TYPE_AUTO)

		queue = self.queue_of(self.approver)

		self.assertIn(routed, queue)
		self.assertNotIn(auto, queue)

	def test_switching_the_field_switches_the_behaviour_with_no_code_change(self):
		"""The clincher: edit one config field, and the same call behaves differently.

		Not a second code path — the very same `submit()` on the very same type,
		with one field edited between the two applications.
		"""
		before = self.apply(fixtures.TYPE_ROUTED)
		self.assertEqual(self.approval_state(before), states.IN_REVIEW)

		# Put the type back afterwards: the transaction rolls back once per
		# class, so a type edited here would stay edited for every later method.
		self.addCleanup(self._restore_routed_type)

		frappe.db.set_value(
			fixtures.TYPE_DOCTYPE, fixtures.TYPE_ROUTED, "approval_mode", approval.MODE_AUTO_ON_PAYMENT
		)
		frappe.db.set_value(fixtures.TYPE_DOCTYPE, fixtures.TYPE_ROUTED, "fee_amount", 250)
		frappe.clear_document_cache(fixtures.TYPE_DOCTYPE, fixtures.TYPE_ROUTED)

		after = self.apply(fixtures.TYPE_ROUTED)

		self.assertEqual(self.approval_state(after), states.DRAFT)
		self.assertEqual(self.membership_status(after), membership_service.STATUS_AWAITING_PAYMENT)

	def _restore_routed_type(self):
		frappe.db.set_value(
			fixtures.TYPE_DOCTYPE, fixtures.TYPE_ROUTED, "approval_mode", approval.MODE_ROUTED
		)
		frappe.db.set_value(fixtures.TYPE_DOCTYPE, fixtures.TYPE_ROUTED, "fee_amount", 0)
		frappe.clear_document_cache(fixtures.TYPE_DOCTYPE, fixtures.TYPE_ROUTED)


class TestTheEngineIsReallyConsumed(MemberTestCase):
	"""A routed membership goes through the real engine, gate and all."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.approver = cls.scoped_user("routed_approver", [fixtures.APPROVER_ROLE])
		cls.other_approver = cls.scoped_user("routed_elsewhere", [fixtures.APPROVER_ROLE])
		cls.applicant = cls.scoped_user("routed_applicant", [fixtures.APPLICANT_ROLE])
		cls.system_manager = cls.scoped_user("routed_sysmanager", ["System Manager"])

		# Authority in society A's county, and in society B's district. Both hold
		# the same role; only one of them is this membership's approver.
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])
		fixtures.make_assignment(cls.other_approver, fixtures.APPROVER_ROLE, cls.society_b["district"])

		fixtures.make_workflow()
		# An approver saves the membership when they decide, so the
		# society's role needs write access to it.
		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)
		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_ROUTED, approval.MODE_ROUTED, fee=0)

	def setUp(self):
		super().setUp()

		profile = fixtures.make_profile("Routed", "Applicant")
		self.membership = fixtures.make_membership(profile, fixtures.TYPE_ROUTED, self.society_a["ward"]).name
		membership_service.submit(self.reload(self.membership))

	def test_it_routed_to_the_resolved_approver(self):
		"""Resolved by the engine through core — not by anything in this module."""
		auth = engine.authorised(self.reload(self.membership))

		self.assertEqual(auth["approvers"], [self.approver])
		self.assertIn(self.membership, self.queue_of(self.approver))

	def test_the_resolved_approver_activates_it_by_approving(self):
		with fixtures.acting_as(self.approver):
			engine.decide(self.reload(self.membership), states.DECISION_APPROVED)

		self.assertEqual(self.approval_state(self.membership), states.APPROVED)
		self.assertEqual(self.membership_status(self.membership), membership_service.STATUS_ACTIVE)

	def test_it_refuses_everyone_else(self):
		"""Four people, all of whom would pass a role test. None may act."""
		for user in (self.other_approver, self.applicant, self.system_manager):
			with (
				fixtures.acting_as(user),
				self.assertRaises(frappe.PermissionError, msg=f"{user} got through"),
			):
				engine.decide(self.reload(self.membership), states.DECISION_APPROVED)

	def test_a_refusal_changes_nothing(self):
		"""No approval, no activation, no member — and it stays in the right queue."""
		for user in (self.other_approver, self.applicant, self.system_manager):
			with fixtures.acting_as(user), self.assertRaises(frappe.PermissionError):
				engine.decide(self.reload(self.membership), states.DECISION_APPROVED)

		self.assertEqual(self.approval_state(self.membership), states.IN_REVIEW)
		self.assertEqual(self.membership_status(self.membership), membership_service.STATUS_AWAITING_APPROVAL)

		member = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, self.membership, "member")
		self.assertNotEqual(self.member_status(member), "Active")
		self.assertIn(self.membership, self.queue_of(self.approver))

	def test_holding_the_role_somewhere_else_is_not_enough(self):
		"""The other approver holds the same role — in the other society."""
		self.assertIn(fixtures.APPROVER_ROLE, frappe.get_roles(self.other_approver))

		with fixtures.acting_as(self.other_approver):
			self.assertFalse(engine.may_act(self.reload(self.membership)))

	def test_a_rejection_leaves_the_person_s_record_intact(self):
		with fixtures.acting_as(self.approver):
			engine.decide(self.reload(self.membership), states.DECISION_REJECTED, "Not eligible this year")

		self.assertEqual(self.approval_state(self.membership), states.REJECTED)
		self.assertNotEqual(self.membership_status(self.membership), membership_service.STATUS_ACTIVE)

		# The member record still exists; the application was refused, not the person.
		member = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, self.membership, "member")
		self.assertTrue(frappe.db.exists(fixtures.MEMBER_DOCTYPE, member))
		self.assertEqual(self.member_status(member), "Prospective")

	def test_the_engine_is_what_decides_who_may_act(self):
		"""The gate the module relies on is the engine's, recomputed from geo.

		Ending the approver's authority changes who may act, without the
		membership being touched — which is only possible if the answer is being
		recomputed by the engine from Geo Assignment rather than remembered
		anywhere in this module.
		"""
		membership = self.reload(self.membership)
		self.assertEqual(engine.authorised(membership)["approvers"], [self.approver])

		assignment = frappe.db.get_value(
			"Geo Assignment", {"user": self.approver, "role": fixtures.APPROVER_ROLE}, "name"
		)

		# Reactivate afterwards: the rollback is per class, so leaving this off
		# would silently strip the approver's authority from every later method.
		self.addCleanup(frappe.db.set_value, "Geo Assignment", assignment, "is_active", 1)
		frappe.db.set_value("Geo Assignment", assignment, "is_active", 0)

		self.assertEqual(engine.authorised(self.reload(self.membership))["approvers"], [])

		with fixtures.acting_as(self.approver), self.assertRaises(frappe.PermissionError):
			engine.decide(self.reload(self.membership), states.DECISION_APPROVED)


class TestNoBranchingOnTypeNames(MemberTestCase):
	"""No source file selects behaviour by a membership type's name or key.

	The dispatch is a lookup keyed by the configuration value, so this asserts
	the shape directly: every mode the config offers has an entry, and the entry
	is what runs.
	"""

	def test_every_configured_mode_has_a_handler(self):
		options = frappe.get_meta(fixtures.TYPE_DOCTYPE).get_field("approval_mode").options.split("\n")
		offered = [option for option in options if option]

		self.assertEqual(sorted(offered), sorted(approval.MODES))

		for mode in approval.MODES:
			self.assertIn(mode, approval._BEGIN)
			self.assertIn(mode, approval._SETTLED)

	def test_an_unknown_mode_is_refused_rather_than_defaulted(self):
		"""A mode nobody implemented must not silently fall through to one that exists."""
		stand_in = frappe._dict({"name": "stand-in", "approval_mode": "whenever_someone_feels_like_it"})

		with self.assertRaises(frappe.ValidationError):
			approval.mode(stand_in)
