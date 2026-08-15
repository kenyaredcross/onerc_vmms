# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""MEM-01 — the payment seam, proven on the Manual driver.

Every payment in these tests goes through the real `onerc_payments` app: a real
`OneRC Payment Transaction` is created by `initiate_payment()`, and it is
settled by the payments app's own `confirm_payment()`, which writes a real
`Manual Payment` detail row and then calls `on_payment_confirmed` on this
membership by name. Nothing is stubbed and no hook is invoked by hand.

The Manual driver is the whole point of choosing it: it is what a society uses
for a bank transfer or cash, it needs no credentials, and — critically — it may
never deliver a separate receipt at all. A membership module that only worked
when a gateway volunteered a receipt would be an M-Pesa module wearing a
generic name.
"""

import frappe

from vmmsx.approvals import states
from vmmsx.approvals.services import engine
from vmmsx.member.services import approval, payment
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

TRANSACTION_DOCTYPE = "OneRC Payment Transaction"


class TestAutoApproveOnPayment(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=1500)

	def apply(self):
		profile = fixtures.make_profile("Auto", "Payer")
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, self.society_a["ward"])
		membership_service.submit(membership)

		return membership.name

	def test_a_real_transaction_is_created_through_the_payments_app(self):
		membership = self.apply()
		transaction = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, membership, "payment_transaction")

		self.assertTrue(transaction)
		self.assertTrue(frappe.db.exists(TRANSACTION_DOCTYPE, transaction))

		row = frappe.get_doc(TRANSACTION_DOCTYPE, transaction)

		self.assertEqual(row.source_app, "vmmsx")
		self.assertEqual(row.source_doctype, fixtures.MEMBERSHIP_DOCTYPE)
		self.assertEqual(row.source_document, membership)
		self.assertEqual(row.amount, 1500)
		self.assertEqual(row.direction, "Inbound")

	def test_it_does_not_activate_before_the_payment_is_confirmed(self):
		"""The application exists and is waiting. Nobody is a member yet."""
		membership = self.apply()

		self.assertEqual(self.membership_status(membership), membership_service.STATUS_AWAITING_PAYMENT)

		member = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, membership, "member")
		self.assertEqual(self.member_status(member), "Prospective")

	def test_confirmation_through_the_manual_driver_activates_it(self):
		"""The whole path: payments confirms, calls our hook, membership activates."""
		membership = self.apply()
		fixtures.confirm_payment_through_manual_driver(self.reload(membership))

		self.assertEqual(self.membership_status(membership), membership_service.STATUS_ACTIVE)

		member = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, membership, "member")
		self.assertEqual(self.member_status(member), "Active")

	def test_activation_sets_validity_from_the_type_s_configured_duration(self):
		from frappe.utils import add_days, getdate

		membership = self.apply()
		fixtures.confirm_payment_through_manual_driver(self.reload(membership))

		row = self.reload(membership)
		duration = frappe.db.get_value(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO, "duration_days")

		self.assertEqual(getdate(row.valid_to), getdate(add_days(row.valid_from, duration)))

	def test_no_gateway_was_ever_touched(self):
		"""The Manual driver resolved it — there is no Mpesa Payment anywhere."""
		membership = self.apply()
		fixtures.confirm_payment_through_manual_driver(self.reload(membership))

		transaction = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, membership, "payment_transaction")
		detail_doctype = frappe.db.get_value(TRANSACTION_DOCTYPE, transaction, "gateway_detail_doctype")

		self.assertEqual(detail_doctype, "Manual Payment")

	def test_confirming_twice_activates_once(self):
		"""A retried gateway, or an administrator pressing confirm again."""
		membership = self.apply()
		row = self.reload(membership)

		row.on_payment_confirmed(amount=1500, receipt="R-1", transaction_id=row.payment_transaction)
		first_paid_on = self.reload(membership).paid_on

		self.reload(membership).on_payment_confirmed(
			amount=1500, receipt="R-1", transaction_id=row.payment_transaction
		)

		self.assertEqual(self.reload(membership).paid_on, first_paid_on)
		self.assertEqual(self.membership_status(membership), membership_service.STATUS_ACTIVE)
		self.assertEqual(len(frappe.get_all(fixtures.MEMBERSHIP_DOCTYPE, filters={"name": membership})), 1)


class TestTheHookSignaturesMatchThePaymentsApp(MemberTestCase):
	"""payments calls these by name through `hasattr`. A mismatch is silent."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=100)

	def membership(self):
		profile = fixtures.make_profile("Sig", "Check")

		return fixtures.make_membership(profile, fixtures.TYPE_AUTO, self.society_a["ward"])

	def test_both_hooks_exist_on_the_document(self):
		"""`hasattr` is exactly how payments decides whether to call them."""
		doc = self.membership()

		self.assertTrue(hasattr(doc, "on_payment_confirmed"))
		self.assertTrue(hasattr(doc, "on_payment_receipt"))

	def test_the_signatures_accept_exactly_what_payments_passes(self):
		"""Called with the payments app's own keyword arguments, verbatim.

		`_notify_source_app` passes amount/receipt/transaction_id;
		`_notify_source_receipt` passes receipt/transaction_id. If either
		signature drifted, these calls would raise TypeError.
		"""
		import inspect

		doc = self.membership()

		confirmed = inspect.signature(doc.on_payment_confirmed).parameters
		self.assertEqual(list(confirmed), ["amount", "receipt", "transaction_id"])

		receipt = inspect.signature(doc.on_payment_receipt).parameters
		self.assertEqual(list(receipt), ["receipt", "transaction_id"])

	def test_they_are_callable_with_no_arguments_at_all(self):
		"""Every parameter defaults, because a driver may know none of them."""
		doc = self.membership()
		membership_service.submit(doc)

		self.reload(doc.name).on_payment_receipt()

		# Did not raise, and did not invent a payment.
		self.assertFalse(self.reload(doc.name).payment_receipt)


class TestReceiptIsOptionalEnrichment(MemberTestCase):
	"""Activation never depends on a receipt arriving."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=200)

	def apply(self):
		profile = fixtures.make_profile("Receipt", "Case")
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, self.society_a["ward"])
		membership_service.submit(membership)

		return membership.name

	def test_activation_works_with_no_receipt_ever(self):
		"""Confirmed with receipt=None. The Manual driver's ordinary case."""
		membership = self.apply()
		row = self.reload(membership)

		row.on_payment_confirmed(amount=200, receipt=None, transaction_id=row.payment_transaction)

		self.assertEqual(self.membership_status(membership), membership_service.STATUS_ACTIVE)
		self.assertFalse(self.reload(membership).payment_receipt)

	def test_a_late_receipt_is_absorbed_without_re_activating(self):
		membership = self.apply()
		row = self.reload(membership)
		row.on_payment_confirmed(amount=200, receipt=None, transaction_id=row.payment_transaction)

		activated_at = self.reload(membership).valid_from

		self.reload(membership).on_payment_receipt(receipt="LATE-123", transaction_id=row.payment_transaction)

		after = self.reload(membership)

		self.assertEqual(after.payment_receipt, "LATE-123")
		self.assertEqual(after.membership_status, membership_service.STATUS_ACTIVE)
		self.assertEqual(after.valid_from, activated_at)

	def test_a_late_receipt_never_overwrites_one_already_held(self):
		membership = self.apply()
		row = self.reload(membership)
		row.on_payment_confirmed(amount=200, receipt="FIRST", transaction_id=row.payment_transaction)

		self.reload(membership).on_payment_receipt(receipt="SECOND")

		self.assertEqual(self.reload(membership).payment_receipt, "FIRST")


class TestFreeAndRoutedTogether(MemberTestCase):
	"""A routed type that also charges waits for both, in either order."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.approver = cls.scoped_user("both_approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])
		fixtures.make_workflow()
		# An approver saves the membership when they decide, so the
		# society's role needs write access to it.
		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)
		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_ROUTED, approval.MODE_ROUTED, fee=750)
		fixtures.make_type(fixtures.TYPE_FREE, approval.MODE_ROUTED, fee=0)

	def apply(self, type_key):
		profile = fixtures.make_profile("Both", "Ways")
		membership = fixtures.make_membership(profile, type_key, self.society_a["ward"])
		membership_service.submit(membership)

		return membership.name

	def test_approval_first_then_payment(self):
		membership = self.apply(fixtures.TYPE_ROUTED)

		with fixtures.acting_as(self.approver):
			engine.decide(self.reload(membership), states.DECISION_APPROVED)

		self.assertEqual(self.membership_status(membership), membership_service.STATUS_AWAITING_PAYMENT)

		fixtures.confirm_payment_through_manual_driver(self.reload(membership))

		self.assertEqual(self.membership_status(membership), membership_service.STATUS_ACTIVE)

	def test_payment_first_then_approval(self):
		"""The other order. Same code — activation is a predicate, not a sequence."""
		membership = self.apply(fixtures.TYPE_ROUTED)

		fixtures.confirm_payment_through_manual_driver(self.reload(membership))

		self.assertNotEqual(self.membership_status(membership), membership_service.STATUS_ACTIVE)

		with fixtures.acting_as(self.approver):
			engine.decide(self.reload(membership), states.DECISION_APPROVED)

		self.assertEqual(self.membership_status(membership), membership_service.STATUS_ACTIVE)

	def test_a_free_routed_type_never_initiates_a_payment(self):
		membership = self.apply(fixtures.TYPE_FREE)

		self.assertFalse(self.reload(membership).payment_transaction)
		self.assertEqual(self.membership_status(membership), membership_service.STATUS_AWAITING_APPROVAL)

		with fixtures.acting_as(self.approver):
			engine.decide(self.reload(membership), states.DECISION_APPROVED)

		self.assertEqual(self.membership_status(membership), membership_service.STATUS_ACTIVE)

	def test_payment_alone_does_not_activate_a_routed_membership(self):
		"""The auto path must not leak into the routed one."""
		membership = self.apply(fixtures.TYPE_ROUTED)
		fixtures.confirm_payment_through_manual_driver(self.reload(membership))

		row = self.reload(membership)

		self.assertTrue(row.paid_on)
		self.assertEqual(row.approval_state, states.IN_REVIEW)
		self.assertNotEqual(row.membership_status, membership_service.STATUS_ACTIVE)

	def test_the_seam_reports_settlement_from_configuration(self):
		"""`payment.is_settled` answers from the type, not from a code path."""
		membership = self.reload(self.apply(fixtures.TYPE_FREE))
		free_type = membership_service.type_of(membership)

		self.assertFalse(payment.is_payable(free_type))
		self.assertTrue(payment.is_settled(membership, free_type))
