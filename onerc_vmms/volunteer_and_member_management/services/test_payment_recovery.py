"""Regressions from the October delayed-payment recovery incident."""

import json
import unittest
from unittest.mock import MagicMock, patch

import frappe

from . import event_payments
from . import membership_payments as payments


def reject(message):
	raise frappe.ValidationError(message)


class TestStoredVerification(unittest.TestCase):
	def setUp(self):
		self.express = frappe._dict(
			name="EXP-1",
			checkout_request_id="CHECKOUT-1",
			amount=500,
			reference_doctype="Payment Request",
			reference_name="PR-1",
			settings="Shared Paybill",
		)
		self.success = {"ResultCode": "0", "CheckoutRequestID": "CHECKOUT-1"}
		self.context = dict(
			checkout_request_id="CHECKOUT-1",
			reference_doctype="Payment Request",
			reference_name="PR-1",
			settings="Shared Paybill",
			amount="500",
		)
		self.output = {"verified_query": self.success, "verified_context": self.context}
		self.fake = MagicMock()
		self.fake.db.get_value.side_effect = lambda *a, **k: json.dumps(self.output)
		self.fake.get_doc.return_value = frappe._dict(business_shortcode="10000", sandbox=0)
		self.fake.get_all.return_value = []
		p = patch.object(payments, "frappe", self.fake)
		p.start()
		self.addCleanup(p.stop)

	def test_bound_server_verification_is_reused(self):
		self.assertEqual(payments._get_stored_verification(self.express), self.success)

	def test_non_success_or_different_checkout_is_not_reused(self):
		for response in (
			{"ResultCode": "1032", "CheckoutRequestID": "CHECKOUT-1"},
			{"ResultCode": "0", "CheckoutRequestID": "OTHER"},
		):
			self.output["verified_query"] = response
			self.assertIsNone(payments._get_stored_verification(self.express))

	def test_callback_success_alone_is_not_verification(self):
		self.output = {"callback_result": self.success}
		self.assertIsNone(payments._get_stored_verification(self.express))

	def test_changed_payment_binding_is_rejected(self):
		for field, value in (
			("amount", 501),
			("reference_name", "PR-2"),
			("settings", "Other Paybill"),
			("checkout_request_id", "OTHER"),
		):
			with self.subTest(field=field):
				changed = frappe._dict(self.express)
				changed[field] = value
				self.assertIsNone(payments._get_stored_verification(changed))

	def test_malformed_stored_confirmation_is_ignored(self):
		self.fake.db.get_value.side_effect = None
		for value in ("not-json", "[]", None):
			self.fake.db.get_value.return_value = value
			self.assertIsNone(payments._get_stored_verification(self.express))

	def legacy_logs(self):
		return [
			frappe._dict(
				request_description="Mpesa STK Push",
				url="https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
				data=json.dumps({"BusinessShortCode": "10000", "Amount": 500}),
				output=str({"CheckoutRequestID": "CHECKOUT-1"}),
			),
			frappe._dict(
				request_description="VMMS Payment Verification",
				url="https://api.safaricom.co.ke/mpesa/stkpushquery/v1/query",
				data=json.dumps({"BusinessShortCode": "10000", "CheckoutRequestID": "CHECKOUT-1"}),
				output=str(self.success),
			),
		]

	def test_legacy_proof_requires_original_initiation_and_successful_query(self):
		self.output.pop("verified_context")
		self.fake.get_all.return_value = self.legacy_logs()
		self.assertEqual(payments._get_stored_verification(self.express), self.success)

	def test_legacy_proof_rejects_wrong_amount_environment_or_checkout(self):
		self.output.pop("verified_context")
		for change in ("amount", "environment", "checkout", "missing_initiation"):
			with self.subTest(change=change):
				logs = self.legacy_logs()
				if change == "amount":
					logs[0].data = json.dumps({"BusinessShortCode": "10000", "Amount": 501})
				elif change == "environment":
					logs[1].url = logs[1].url.replace("api.safaricom", "sandbox.safaricom")
				elif change == "checkout":
					logs[1].output = str({"ResultCode": "0", "CheckoutRequestID": "OTHER"})
				else:
					logs.pop(0)
				self.fake.get_all.return_value = logs
				self.assertIsNone(payments._get_stored_verification(self.express))

	def test_recovery_with_stored_success_does_not_requery_provider(self):
		with (
			patch.object(payments, "_get_stored_verification", return_value=self.success),
			patch.object(payments, "_query_provider_status", side_effect=AssertionError("Do not requery")),
			patch.object(payments, "_finish_accounting", return_value={"status": "Completed"}) as finish,
		):
			self.assertEqual(payments._recover_confirmed_payment(self.express)["status"], "Completed")
			finish.assert_called_once()


class TestDelayedAccountingCompletion(unittest.TestCase):
	def setUp(self):
		self.fake = MagicMock()
		self.fake.throw.side_effect = reject
		self.invoice = MagicMock()
		self.invoice.name = "INV-1"
		self.invoice.company = "Nairobi"
		self.invoice.currency = "KES"
		self.invoice.docstatus = 0
		self.invoice.posting_date = "2026-10-27"
		self.invoice.due_date = "2026-10-27"
		self.invoice.set_posting_time = 0
		self.invoice.outstanding_amount = 500
		self.invoice.membership = "MEM-1"
		self.invoice.get.side_effect = lambda key: "MEM-1" if key == "membership" else None
		self.express = frappe._dict(
			name="EXP-1",
			docstatus=1,
			reference_name="PR-1",
			amount=500,
			transaction_id=None,
			checkout_request_id="CHECKOUT-1",
		)
		self.request = MagicMock()
		self.request.name = "PR-1"
		self.request.docstatus = 1
		self.request.currency = "KES"
		self.request.grand_total = 500
		self.request.outstanding_amount = 500
		self.request.get.return_value = None
		self.existing = None
		self.fake.get_doc.side_effect = (
			lambda dt, *a, **k: self.express if dt == payments.EXPRESS else self.request
		)
		self.fake.db.get_value.return_value = None
		self.fake.get_all.side_effect = (
			lambda dt, **k: [frappe._dict(allocated_amount=500)]
			if dt == "Payment Entry Reference"
			else [
				frappe._dict(company="Nairobi", debit=500, credit=0),
				frappe._dict(company="Nairobi", debit=0, credit=500),
			]
		)
		self.invoice.submit.side_effect = self.submit_invoice
		self.request.create_payment_entry.side_effect = self.create_payment
		self.patches = [
			patch.object(payments, "frappe", self.fake),
			patch.object(payments, "_", lambda s: s),
			patch.object(payments, "get_vmms_invoice", return_value=self.invoice),
			patch.object(payments, "get_existing_payment", side_effect=lambda *a: self.existing),
			patch.object(payments, "_confirm_membership_payment"),
			patch.object(event_payments, "validate_event_booking"),
			patch.object(event_payments, "confirm_event_booking"),
		]
		for p in self.patches:
			p.start()
			self.addCleanup(p.stop)

	def submit_invoice(self):
		self.assertEqual(self.invoice.set_posting_time, 1)
		self.assertEqual(self.invoice.posting_date, "2026-10-27")
		self.assertEqual(self.invoice.due_date, "2026-10-27")
		self.invoice.docstatus = 1

	def create_payment(self):
		self.existing = "PAY-1"
		self.invoice.outstanding_amount = 0

	def test_delayed_invoice_preserves_dates_before_payment_posting(self):
		self.assertEqual(payments._finish_accounting(self.express)["status"], "Completed")
		self.invoice.submit.assert_called_once()
		self.request.create_payment_entry.assert_called_once()

	def test_existing_paid_entry_is_finalized_without_posting_twice(self):
		self.invoice.docstatus = 1
		self.invoice.outstanding_amount = 0
		self.existing = "PAY-1"
		payments._finish_accounting(self.express)
		payments._finish_accounting(self.express)
		self.invoice.submit.assert_not_called()
		self.request.create_payment_entry.assert_not_called()
		self.fake.db.set_value.assert_any_call(
			payments.EXPRESS,
			"EXP-1",
			{"status": "Completed", "result_desc": "Verified by M-Pesa; accounting completed"},
		)

	def test_unsettled_existing_entry_cannot_mark_payment_completed(self):
		self.invoice.docstatus = 1
		self.existing = "PAY-1"
		with self.assertRaises(frappe.ValidationError):
			payments._finish_accounting(self.express)

	def test_cancelled_invoice_cannot_be_completed(self):
		self.invoice.docstatus = 2
		with self.assertRaises(frappe.ValidationError):
			payments._finish_accounting(self.express)
		self.request.create_payment_entry.assert_not_called()

	def test_delayed_event_invoice_uses_same_date_preservation(self):
		self.invoice.membership = None
		self.invoice.get.side_effect = lambda key: "BOOK-1" if key == "event_booking" else None
		payments._finish_accounting(self.express)
		self.invoice.submit.assert_called_once()
		event_payments.confirm_event_booking.assert_called_once_with(self.invoice)

	def test_wrong_allocation_cannot_finalize_an_existing_entry(self):
		self.invoice.docstatus = 1
		self.invoice.outstanding_amount = 0
		self.existing = "PAY-1"
		original = self.fake.get_all.side_effect
		self.fake.get_all.side_effect = (
			lambda dt, **k: [frappe._dict(allocated_amount=100)]
			if dt == "Payment Entry Reference"
			else original(dt, **k)
		)
		with self.assertRaises(frappe.ValidationError):
			payments._finish_accounting(self.express)


class TestMembershipPaymentRecognition(unittest.TestCase):
	def test_unpaid_invoice_cannot_mark_membership_paid(self):
		fake = MagicMock()
		fake.throw.side_effect = frappe.ValidationError
		with patch.object(payments, "frappe", fake), patch.object(payments, "_", lambda s: s):
			with self.assertRaises(frappe.ValidationError):
				payments._confirm_membership_payment(
					frappe._dict(membership="MEM-1", docstatus=1, outstanding_amount=500)
				)
		fake.get_doc.assert_not_called()

	def test_membership_company_mismatch_requires_review(self):
		fake = MagicMock()
		fake.throw.side_effect = frappe.ValidationError
		membership = MagicMock(company="Bomet")
		fake.get_doc.return_value = membership
		with patch.object(payments, "frappe", fake), patch.object(payments, "_", lambda s: s):
			with self.assertRaises(frappe.ValidationError):
				payments._confirm_membership_payment(
					frappe._dict(company="Nairobi", membership="MEM-1", docstatus=1, outstanding_amount=0)
				)
		membership.db_set.assert_not_called()

	def test_paid_recognition_keeps_approval_status_and_is_idempotent(self):
		for status in ("Pending", "Active", "Rejected", "Expired"):
			with self.subTest(status=status):
				fake = MagicMock()
				membership = MagicMock()
				membership.company = "Nairobi"
				membership.status = status
				membership.paid = 0
				membership.db_set.side_effect = lambda field, value: setattr(membership, field, value)
				fake.get_doc.return_value = membership
				invoice = frappe._dict(
					name="INV-1", company="Nairobi", membership="MEM-1", docstatus=1, outstanding_amount=0
				)
				with patch.object(payments, "frappe", fake):
					payments._confirm_membership_payment(invoice)
					payments._confirm_membership_payment(invoice)
				self.assertEqual(membership.status, status)
				membership.db_set.assert_called_once_with("paid", 1)
				membership.validate_membership_period.assert_not_called()

	def test_draft_membership_uses_native_period_logic(self):
		fake = MagicMock()
		membership = MagicMock(company="Nairobi", status="Draft", paid=0)
		fake.get_doc.return_value = membership
		with patch.object(payments, "frappe", fake):
			payments._confirm_membership_payment(
				frappe._dict(company="Nairobi", membership="MEM-1", docstatus=1, outstanding_amount=0)
			)
		membership.validate_membership_period.assert_called_once()
		membership.db_set.assert_called_once_with("paid", 1)
