# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Recording a fee that was handed over at a counter.

`api/member.py::record_membership_payment` is the only door in this app through
which a person settles a membership fee, and it exists because a society taking
cash had no way to move a membership off Awaiting Payment at all: the payments
app ships the manual driver's confirmation as an API call with no button on any
form, and nothing called it.

**What these tests are really guarding is that it did not become an activate
button.** The endpoint confirms the *payment* and nothing else; activation stays
a predicate re-derived from approval and payment together. So the routed case
below is the important one — the fee lands, the membership moves to Awaiting
Approval, and it stops there until somebody decides it.

Everything goes through the real payments app, as in `test_payment_seam`: a real
transaction, the real manual driver, and the real `on_payment_confirmed`
callback. Nothing is stubbed.
"""

import frappe

from vmmsx.api import member as api
from vmmsx.member.services import approval
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestRecordingAFeeTakenInPerson(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# The clerk is made first: `make_user` is what creates the society's role,
		# and `make_workflow` links to it by name.
		cls.clerk = cls.scoped_user("clerk", [fixtures.APPROVER_ROLE])
		fixtures.make_workflow()
		# Recording a fee saves the membership, so the role has to be able to
		# write one — which is also exactly what `_writable` will check.
		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)
		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=1500)
		fixtures.make_type(fixtures.TYPE_ROUTED, approval.MODE_ROUTED, fee=2000)
		# Routed rather than auto-on-payment: the type's own validation refuses a
		# free type that activates on payment, because nothing would ever have to
		# happen for it to become active.
		fixtures.make_type(fixtures.TYPE_FREE, approval.MODE_ROUTED, fee=0)

	def apply(self, type_key: str, first_name: str = "Cash"):
		profile = fixtures.make_profile(first_name, "Payer")
		membership = fixtures.make_membership(profile, type_key, self.society_a["ward"])
		membership_service.submit(membership)

		return membership.name

	# --- the act itself ---------------------------------------------------

	def test_a_fee_taken_at_the_counter_settles_the_membership(self):
		membership = self.apply(fixtures.TYPE_AUTO)
		self.assertEqual(self.membership_status(membership), "Awaiting Payment")

		frappe.set_user(self.clerk)
		answer = api.record_membership_payment(membership, receipt="RCPT-001")

		self.assertTrue(answer["confirmed"])
		self.assertTrue(answer["settled"])
		self.assertIsNotNone(self.reload(membership).paid_on)

	def test_the_receipt_is_recorded_against_the_membership(self):
		membership = self.apply(fixtures.TYPE_AUTO)

		frappe.set_user(self.clerk)
		api.record_membership_payment(membership, receipt="RCPT-002")

		self.assertEqual(self.reload(membership).payment_receipt, "RCPT-002")

	def test_a_branch_that_wrote_nothing_down_can_still_record_the_money(self):
		"""No receipt is not a refusal. A counter that keeps no book still took it."""
		membership = self.apply(fixtures.TYPE_AUTO)

		frappe.set_user(self.clerk)

		self.assertTrue(api.record_membership_payment(membership)["confirmed"])
		self.assertIsNotNone(self.reload(membership).paid_on)

	def test_it_goes_through_the_payments_app_rather_than_writing_paid_on(self):
		"""MEM-01: the transaction is what moved, and the membership followed."""
		membership = self.apply(fixtures.TYPE_AUTO)
		transaction = self.reload(membership).payment_transaction

		frappe.set_user(self.clerk)
		api.record_membership_payment(membership, receipt="RCPT-003")

		self.assertEqual(
			frappe.db.get_value("OneRC Payment Transaction", transaction, "status"), "Completed"
		)

	def test_pressing_it_twice_records_one_payment(self):
		membership = self.apply(fixtures.TYPE_AUTO)

		frappe.set_user(self.clerk)
		api.record_membership_payment(membership, receipt="RCPT-004")
		first = self.reload(membership).paid_on

		second = api.record_membership_payment(membership, receipt="RCPT-004")

		self.assertFalse(second["confirmed"])
		self.assertEqual(second["reason"], "already_settled")
		self.assertEqual(self.reload(membership).paid_on, first)

	# --- what it deliberately does not do ---------------------------------

	# The whole point of the endpoint being about money rather than about
	# standing. A society that wanted "make this person a member" would have
	# been given a way around its own approver.

	def test_a_routed_membership_stops_at_its_approver(self):
		membership = self.apply(fixtures.TYPE_ROUTED)

		frappe.set_user(self.clerk)
		api.record_membership_payment(membership, receipt="RCPT-005")

		self.assertIsNotNone(self.reload(membership).paid_on)
		self.assertNotEqual(self.membership_status(membership), "Active")
		self.assertEqual(self.membership_status(membership), "Awaiting Approval")

	def test_an_auto_on_payment_membership_activates_because_nothing_else_was_owed(self):
		"""The contrast that proves the test above is about approval, not about payment."""
		membership = self.apply(fixtures.TYPE_AUTO)

		frappe.set_user(self.clerk)
		api.record_membership_payment(membership, receipt="RCPT-006")

		self.assertEqual(self.membership_status(membership), "Active")

	# --- refusals ---------------------------------------------------------

	def test_a_free_membership_has_nothing_to_record(self):
		membership = self.apply(fixtures.TYPE_FREE)

		frappe.set_user(self.clerk)

		with self.assertRaises(frappe.ValidationError):
			api.record_membership_payment(membership)

	def test_the_member_cannot_record_their_own_fee(self):
		"""`_writable`, not `_readable`. The holder may read their standing and not move it."""
		membership = self.apply(fixtures.TYPE_AUTO, first_name="Selfpay")
		holder = fixtures.make_user("selfpay", [])

		profile = frappe.db.get_value(
			fixtures.MEMBER_DOCTYPE, self.reload(membership).member, "red_profile"
		)
		frappe.db.set_value("Red Profile", profile, "user", holder)

		frappe.set_user(holder)

		with self.assertRaises(frappe.PermissionError):
			api.record_membership_payment(membership)
