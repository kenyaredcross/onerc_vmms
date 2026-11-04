# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Paying for a membership with M-Pesa: pay first, then the branch decides.

The old VMMS order, kept: the applicant pays on their phone, the payment is
recorded, and only then does the membership reach the branch's approval queue,
with the M-Pesa receipt on it. An unpaid application never sits in front of an
approver.

Everything runs through the real payments app — `initiate_payment`, the real
`OneRC Payment Transaction`, `check_payment_status` and its call back into
`on_payment_confirmed`. Only Safaricom is stood in for: the two calls the
Daraja driver makes over the network (the STK push and the status query).

A fee paid at a branch office keeps its own order and is covered by
`test_record_payment`: that application goes to the branch straight away,
because the office records the payment from the review screen.
"""

from typing import ClassVar
from unittest.mock import patch

import frappe

from vmmsx.approvals import states
from vmmsx.approvals.services import repair
from vmmsx.member.services import approval, methods, payment, review
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

MPESA = "Mpesa Daraja"
DRIVER = "onerc_payments.gateways.mpesa_daraja.MpesaDarajaGateway"
TRANSACTION_DOCTYPE = "OneRC Payment Transaction"


class Safaricom:
	"""The two answers Daraja gives, set by each test."""

	pushes = 0
	answer: ClassVar[dict] = {"status": "Pending"}
	initiate_with = None

	@classmethod
	def initiate(cls, driver, transaction):
		if cls.initiate_with:
			return cls.initiate_with(driver, transaction)
		cls.pushes += 1
		return {
			"success": True,
			"gateway_reference": f"ws_CO_vmmsx_{frappe.generate_hash(length=10)}",
			"merchant_request_id": "vmmsx-test",
			"message": "Check your phone and enter your M-Pesa PIN to complete the payment.",
		}

	@classmethod
	def check_status(cls, driver, transaction):
		return dict(cls.answer)


def _use_mpesa() -> None:
	"""An active M-Pesa gateway, offered by the society alongside the branch office."""
	if frappe.db.exists("OneRC Payment Gateway", MPESA):
		frappe.db.set_value(
			"OneRC Payment Gateway",
			MPESA,
			{"is_active": 1, "supports_inbound": 1, "driver_class": DRIVER},
		)
	else:
		frappe.get_doc(
			{
				"doctype": "OneRC Payment Gateway",
				"gateway_name": MPESA,
				"label": "M-Pesa",
				"driver_class": DRIVER,
				"is_active": 1,
				"supports_inbound": 1,
			}
		).insert(ignore_permissions=True)

	settings = frappe.get_single(methods.SETTINGS_DOCTYPE)
	settings.set(
		methods.METHODS_FIELD,
		[
			{"gateway": MPESA, "label": "M-Pesa", "is_enabled": 1},
			{"gateway": methods.MANUAL, "label": methods.MANUAL_LABEL, "is_enabled": 1},
		],
	)
	settings.save(ignore_permissions=True)


class TestPayWithMpesaThenApproval(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.approver = cls.scoped_user("mpesa_approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])
		fixtures.make_workflow()
		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)
		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_ROUTED, approval.MODE_ROUTED, fee=1000)
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=2500)
		fixtures.make_type(fixtures.TYPE_FREE, approval.MODE_ROUTED, fee=0)
		_use_mpesa()

	def setUp(self):
		super().setUp()
		Safaricom.pushes = 0
		Safaricom.answer = {"status": "Pending"}
		Safaricom.initiate_with = None

		for name, stand_in in (("initiate", Safaricom.initiate), ("check_status", Safaricom.check_status)):
			patcher = patch(f"{DRIVER}.{name}", autospec=True, side_effect=stand_in)
			patcher.start()
			self.addCleanup(patcher.stop)

	def apply(self) -> str:
		profile = fixtures.make_profile("Wanjiru", "Kamau")
		membership = fixtures.make_membership(
			profile,
			fixtures.TYPE_ROUTED,
			self.society_a["ward"],
			payment_method=MPESA,
			payer_phone="0712345678",
		)
		membership_service.submit(membership)

		return membership.name

	def paid(self, receipt: str = "TJK4ABC123") -> None:
		Safaricom.answer = {
			"status": "Completed",
			"gateway_receipt": receipt,
			"result_code": "0",
			"result_description": "The service request is processed successfully.",
		}

	def test_the_payment_prompt_goes_to_the_payer_s_phone(self):
		membership = self.reload(self.apply())
		transaction = frappe.get_doc(TRANSACTION_DOCTYPE, membership.payment_transaction)

		self.assertEqual(Safaricom.pushes, 1)
		self.assertEqual(transaction.gateway, MPESA)
		self.assertEqual(transaction.phone_number, "254712345678")
		self.assertEqual(transaction.amount, 1000)
		self.assertEqual(transaction.status, "Pending")

	def test_an_unpaid_application_is_not_in_front_of_the_branch(self):
		name = self.apply()

		self.assertEqual(self.membership_status(name), membership_service.STATUS_AWAITING_PAYMENT)
		# Received and held, not a draft: the person cannot apply twice, and
		# nobody has been asked to decide it.
		self.assertEqual(self.approval_state(name), states.SUBMITTED)
		self.assertNotIn(name, self.queue_of(self.approver))

	def test_staff_are_told_it_is_awaiting_payment_not_submitted(self):
		from vmmsx.approvals.services import engine

		name = self.apply()

		held = engine.status(self.reload(name))
		self.assertTrue(held["held"])
		self.assertEqual(held["held_for"]["label"], "Awaiting payment")
		self.assertFalse(held["can_act"])

		self.paid()
		payment.progress(self.reload(name))

		routed = engine.status(self.reload(name))
		self.assertFalse(routed["held"])
		self.assertIsNone(routed["held_for"])

	def test_once_paid_it_goes_to_the_branch_with_the_receipt(self):
		name = self.apply()
		self.paid("TJK4ABC123")

		answer = payment.progress(self.reload(name))

		self.assertEqual(answer["status"], "Completed")
		self.assertEqual(answer["receipt"], "TJK4ABC123")
		self.assertEqual(answer["membership_status"], membership_service.STATUS_AWAITING_APPROVAL)

		self.assertEqual(self.approval_state(name), states.IN_REVIEW)
		self.assertIn(name, self.queue_of(self.approver))

		# What the approver reads on the review.
		row = review.decision_dto(self.reload(name))["membership"]
		self.assertEqual(row["payment_receipt"], "TJK4ABC123")
		self.assertTrue(row["paid_on"])
		self.assertEqual(row["payment"]["gateway_receipt"], "TJK4ABC123")
		self.assertEqual(row["payment"]["paid_from"], "254712345678")
		self.assertEqual(row["payment"]["amount_paid"], 1000)

	def test_a_cancelled_prompt_can_be_sent_again_and_then_paid(self):
		name = self.apply()
		Safaricom.answer = {
			"status": "Failed",
			"failure_reason": "Request cancelled by user",
			"result_code": "1032",
		}

		answer = payment.progress(self.reload(name))

		self.assertEqual(answer["status"], "Failed")
		self.assertEqual(answer["failure"], "Request cancelled by user")
		self.assertTrue(answer["can_retry"])
		self.assertNotIn(name, self.queue_of(self.approver))

		first = self.reload(name).payment_transaction
		Safaricom.answer = {"status": "Pending"}
		payment.retry(self.reload(name), "0722000111")

		membership = self.reload(name)
		self.assertNotEqual(membership.payment_transaction, first)
		self.assertEqual(membership.payer_phone, "0722000111")
		self.assertEqual(Safaricom.pushes, 2)

		self.paid("TJK4RETRY1")
		payment.progress(membership)

		self.assertEqual(self.reload(name).payment_receipt, "TJK4RETRY1")
		self.assertIn(name, self.queue_of(self.approver))

	def test_a_prompt_still_open_is_not_sent_twice(self):
		name = self.apply()

		self.assertFalse(payment.can_retry(self.reload(name)))
		with self.assertRaises(frappe.ValidationError):
			payment.retry(self.reload(name))

		self.assertEqual(Safaricom.pushes, 1)

	def test_the_daily_repair_does_not_route_an_unpaid_application(self):
		name = self.apply()

		repair.resync_pending(fixtures.MEMBERSHIP_DOCTYPE)

		self.assertEqual(self.approval_state(name), states.SUBMITTED)
		self.assertNotIn(name, self.queue_of(self.approver))

	def test_a_payment_that_cannot_start_says_what_to_do(self):
		profile = fixtures.make_profile("Otieno", "Ochieng")
		membership = fixtures.make_membership(
			profile,
			fixtures.TYPE_ROUTED,
			self.society_a["ward"],
			payment_method=MPESA,
			payer_phone="0712345678",
		)

		def unreachable(driver, transaction):
			frappe.throw("M-Pesa consumer key or secret is not configured.")

		Safaricom.initiate_with = unreachable
		with self.assertRaises(frappe.ValidationError) as refused:
			membership_service.submit(membership)

		self.assertIn("The payment could not be started", str(refused.exception))
		self.assertNotIn("consumer key", str(refused.exception))

	def test_a_fee_paid_at_the_branch_still_goes_straight_to_the_branch(self):
		profile = fixtures.make_profile("Akinyi", "Odhiambo")
		membership = fixtures.make_membership(
			profile,
			fixtures.TYPE_ROUTED,
			self.society_a["ward"],
			payment_method=methods.MANUAL,
		)
		membership_service.submit(membership)

		self.assertEqual(self.approval_state(membership.name), states.IN_REVIEW)
		self.assertIn(membership.name, self.queue_of(self.approver))
		self.assertEqual(Safaricom.pushes, 0)

	def test_the_default_currency_on_a_new_membership_does_not_make_it_free(self):
		"""A Currency link arrives filled with the site's default. That is not a fee."""
		profile = fixtures.make_profile("Muthoni", "Njeri")
		membership = fixtures.make_membership(
			profile,
			fixtures.TYPE_ROUTED,
			self.society_a["ward"],
			payment_method=MPESA,
			payer_phone="0712345678",
			currency=frappe.db.get_default("currency") or "KES",
		)
		membership_service.submit(membership)

		membership = self.reload(membership.name)
		self.assertEqual(membership.amount, 1000)
		self.assertTrue(membership.payment_transaction)
		self.assertEqual(self.membership_status(membership.name), membership_service.STATUS_AWAITING_PAYMENT)

	# --- changing type before paying ----------------------------------------

	def cancelled(self, name: str) -> None:
		Safaricom.answer = {"status": "Failed", "failure_reason": "Request cancelled by user", "result_code": "1032"}
		payment.progress(self.reload(name))

	def test_an_unpaid_membership_can_switch_type_and_is_charged_the_new_fee(self):
		name = self.apply()
		self.cancelled(name)
		self.assertTrue(membership_service.can_change_type(self.reload(name)))

		membership_service.change_type(self.reload(name), fixtures.TYPE_AUTO)

		membership = self.reload(name)
		self.assertEqual(membership.membership_type, fixtures.TYPE_AUTO)
		self.assertEqual(membership.amount, 2500)
		self.assertFalse(membership.payment_transaction)
		self.assertEqual(membership.membership_status, membership_service.STATUS_AWAITING_PAYMENT)
		self.assertNotIn(name, self.queue_of(self.approver))

		Safaricom.answer = {"status": "Pending"}
		payment.retry(membership)

		transaction = frappe.get_doc(TRANSACTION_DOCTYPE, self.reload(name).payment_transaction)
		self.assertEqual(transaction.amount, 2500)

	def test_the_type_cannot_change_while_a_prompt_is_open(self):
		name = self.apply()

		self.assertFalse(membership_service.can_change_type(self.reload(name)))
		with self.assertRaises(frappe.ValidationError):
			membership_service.change_type(self.reload(name), fixtures.TYPE_AUTO)

		self.assertEqual(self.reload(name).membership_type, fixtures.TYPE_ROUTED)

	def test_the_type_cannot_change_once_paid(self):
		name = self.apply()
		self.paid()
		payment.progress(self.reload(name))

		with self.assertRaises(frappe.ValidationError):
			membership_service.change_type(self.reload(name), fixtures.TYPE_AUTO)

	def test_switching_to_a_free_type_sends_it_to_the_branch(self):
		name = self.apply()
		self.cancelled(name)

		membership_service.change_type(self.reload(name), fixtures.TYPE_FREE)

		self.assertEqual(self.membership_status(name), membership_service.STATUS_AWAITING_APPROVAL)
		self.assertEqual(self.approval_state(name), states.IN_REVIEW)
		self.assertIn(name, self.queue_of(self.approver))

	def test_a_type_outside_the_applicant_s_age_is_neither_offered_nor_accepted(self):
		youth = f"{fixtures.TEST_PREFIX}-youth"
		fixtures.make_type(
			youth,
			approval.MODE_ROUTED,
			fee=100,
			requires_age_requirement=1,
			lower_age_limit=0,
			upper_age_limit=17,
		)
		self.addCleanup(frappe.delete_doc, fixtures.TYPE_DOCTYPE, youth, force=True)

		name = self.apply()
		self.cancelled(name)

		offered = membership_service.switchable_types(self.reload(name))
		self.assertNotIn(youth, offered)
		self.assertIn(fixtures.TYPE_AUTO, offered)
		self.assertNotIn(fixtures.TYPE_ROUTED, offered)

		with self.assertRaises(frappe.ValidationError):
			membership_service.change_type(self.reload(name), youth)

		self.assertEqual(self.reload(name).membership_type, fixtures.TYPE_ROUTED)

	def test_nothing_is_offered_while_a_prompt_is_open(self):
		name = self.apply()

		self.assertEqual(membership_service.switchable_types(self.reload(name)), [])

	def test_m_pesa_is_offered_with_its_logo_and_asks_for_a_phone(self):
		offered = {row["gateway"]: row for row in methods.offered()}

		self.assertEqual(offered[MPESA]["logo"], "/assets/vmmsx/images/payments/mpesa.png")
		self.assertTrue(offered[MPESA]["by_phone"])
		self.assertIsNone(offered[methods.MANUAL]["logo"])
		self.assertFalse(offered[methods.MANUAL]["by_phone"])

		name = self.apply()
		self.assertEqual(payment.progress(self.reload(name))["logo"], "/assets/vmmsx/images/payments/mpesa.png")

	def test_the_form_is_sent_the_logo_and_never_the_gateway_s_own_description(self):
		from vmmsx.api.member import payment_methods

		offered = {row["gateway"]: row for row in payment_methods()["methods"]}

		self.assertEqual(offered[MPESA]["logo"], "/assets/vmmsx/images/payments/mpesa.png")
		self.assertTrue(offered[MPESA]["by_phone"])
		self.assertNotIn("description", offered[MPESA])
