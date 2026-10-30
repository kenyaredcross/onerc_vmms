import inspect
import json
import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest

from ..overrides.server.payment_request import VMMSPaymentRequest
from . import membership_payments as payments


def reject(message, *args, **kwargs):
	raise frappe.ValidationError(message)


class TestMembershipPaymentEntry(unittest.TestCase):
	def setUp(self):
		self.fake = MagicMock()
		self.fake.throw.side_effect = reject
		self.invoice = frappe._dict(
			name="INV-1", membership="MEM-1", company="Bomet", docstatus=1, outstanding_amount=500
		)
		self.request = object.__new__(VMMSPaymentRequest)
		self.request.__dict__.update(
			name="PR-1",
			reference_doctype="Sales Invoice",
			reference_name="INV-1",
			payment_account="HQ",
			mode_of_payment="Mpesa",
			currency="KES",
			outstanding_amount=500,
		)
		self.generated_accounts = []
		self.existing = None
		self.fake.get_doc.side_effect = lambda *args, **kwargs: self.invoice
		self.fake.db.get_value.side_effect = self.lookup
		self.fake.db.exists.return_value = None
		self.fake.get_all.return_value = [
			frappe._dict(company="Bomet", debit=500, credit=0),
			frappe._dict(company="Bomet", debit=0, credit=500),
		]
		self.base = patch.object(
			PaymentRequest, "create_payment_entry", autospec=True, side_effect=self.generate
		)
		self.base.start()
		self.addCleanup(self.base.stop)
		for module in (payments, __import__(VMMSPaymentRequest.__module__, fromlist=["*"])):
			p = patch.object(module, "frappe", self.fake)
			p.start()
			self.addCleanup(p.stop)
			translation_patch = patch.object(module, "_", lambda message: message)
			translation_patch.start()
			self.addCleanup(translation_patch.stop)

	def lookup(self, doctype, name, fields="name", **kwargs):
		if doctype == "Payment Entry Reference":
			return self.existing
		if doctype == "Payment Entry":
			return None
		if doctype == "Mode of Payment Account":
			return "BMT"
		if doctype == "Account":
			return frappe._dict(
				company="Bomet" if name == "BMT" else "Kenya Red Cross Society",
				account_currency="KES",
				disabled=0,
				is_group=0,
			)
		return None

	def generate(self, request, submit=True):
		self.generated_accounts.append(request.payment_account)
		self.existing = "PAY-1"
		return frappe._dict(name="PAY-1", docstatus=int(submit))

	def test_membership_uses_branch_account_without_changing_collection_gateway(self):
		self.request.create_payment_entry()
		self.assertEqual(self.generated_accounts, ["BMT"])
		self.assertEqual(self.request.payment_account, "HQ")

	def test_request_validation_does_not_require_branch_ledger_for_stk(self):
		for kind in ("membership", "event"):
			with self.subTest(kind=kind):
				self.invoice.membership = "MEM-1" if kind == "membership" else None
				self.invoice.event_booking = "BOOK-1" if kind == "event" else None
				with (
					patch.object(PaymentRequest, "validate", autospec=True) as validate,
					patch(
						f"{VMMSPaymentRequest.__module__}.get_receiving_account",
						side_effect=AssertionError("Accounting must not block STK initiation"),
					),
				):
					self.request.validate()
				validate.assert_called_once_with(self.request)

	def test_missing_branch_ledger_still_blocks_accounting(self):
		original_lookup = self.lookup

		def lookup(doctype, *args, **kwargs):
			if doctype == "Mode of Payment Account":
				return None
			return original_lookup(doctype, *args, **kwargs)

		self.fake.db.get_value.side_effect = lookup
		with self.assertRaises(frappe.ValidationError):
			self.request.create_payment_entry()
		self.assertEqual(self.generated_accounts, [])

	def test_retry_returns_existing_payment_without_posting_again(self):
		self.request.create_payment_entry()
		self.request.create_payment_entry()
		self.assertEqual(len(self.generated_accounts), 1)

	def test_manually_paid_invoice_is_not_paid_again(self):
		self.invoice.outstanding_amount = 0
		with self.assertRaises(frappe.ValidationError):
			self.request.create_payment_entry()
		self.assertEqual(self.generated_accounts, [])

	def test_other_invoices_keep_standard_erpnext_behavior(self):
		self.invoice.membership = None
		self.request.create_payment_entry()
		self.assertEqual(self.generated_accounts, ["HQ"])

	def test_event_invoice_also_uses_company_account(self):
		self.invoice.membership = None
		self.invoice.event_booking = "BOOK-1"
		self.request.create_payment_entry()
		self.assertEqual(self.generated_accounts, ["BMT"])

	def test_event_invoice_retry_does_not_post_twice(self):
		self.invoice.membership = None
		self.invoice.event_booking = "BOOK-1"
		self.request.create_payment_entry()
		self.request.create_payment_entry()
		self.assertEqual(len(self.generated_accounts), 1)

	def test_incomplete_existing_ledger_requires_review_without_reposting(self):
		self.existing = "OLD-PAY"
		self.fake.get_all.return_value = [frappe._dict(company="Bomet", debit=0, credit=500)]
		with self.assertRaises(frappe.ValidationError):
			self.request.create_payment_entry()
		self.assertEqual(self.generated_accounts, [])


class TestMembershipCallback(unittest.TestCase):
	def test_ambiguous_dry_run_input_cannot_enable_posting(self):
		for value in (True, "true", "True", "", None, "unexpected"):
			with self.subTest(value=value):
				self.assertTrue(payments._is_dry_run(value))
		for value in (False, 0, "0", "false"):
			with self.subTest(value=value):
				self.assertFalse(payments._is_dry_run(value))

	def setUp(self):
		session_patch = patch.object(payments, "system_session", side_effect=nullcontext)
		session_patch.start()
		self.addCleanup(session_patch.stop)
		self.express = frappe._dict(
			name="EXP-1",
			amount=500,
			reference_name="PR-1",
			transaction_id=None,
			checkout_request_id="CHECKOUT-1",
		)
		self.payload = {
			"Body": {
				"stkCallback": {
					"CheckoutRequestID": "CHECKOUT-1",
					"ResultCode": 0,
					"ResultDesc": "Success",
					"CallbackMetadata": {
						"Item": [
							{"Name": "Amount", "Value": 500},
							{"Name": "MpesaReceiptNumber", "Value": "RECEIPT-1"},
						]
					},
				}
			}
		}

	def test_nonmembership_callback_is_delegated(self):
		with (
			patch.object(payments, "_find_vmms_request", return_value=None),
			patch.object(payments, "_original_callback", return_value="delegated") as original,
		):
			result = inspect.unwrap(payments.stk_push_callback)(**self.payload)
		self.assertEqual(result, "delegated")
		original.assert_called_once_with(**self.payload)

	def test_confirmation_is_saved_before_attempting_accounting(self):
		order = []
		fake = MagicMock()
		fake._dict = frappe._dict
		with (
			patch.object(payments, "frappe", fake),
			patch.object(payments, "_find_vmms_request", return_value=self.express),
			patch.object(payments, "_store_confirmation", side_effect=lambda *a: order.append("stored")),
			patch.object(
				payments, "_recover_confirmed_payment", side_effect=lambda *a: order.append("recover")
			),
		):
			inspect.unwrap(payments.stk_push_callback)(**self.payload)
		self.assertEqual(order, ["stored", "recover"])

	def test_wrong_callback_amount_cannot_reach_accounting(self):
		self.payload["Body"]["stkCallback"]["CallbackMetadata"]["Item"][0]["Value"] = 1
		fake = MagicMock()
		fake.throw.side_effect = reject
		with (
			patch.object(payments, "frappe", fake),
			patch.object(payments, "_", lambda message: message),
			patch.object(payments, "_find_vmms_request", return_value=self.express),
			patch.object(payments, "_recover_confirmed_payment") as recover,
		):
			with self.assertRaises(frappe.ValidationError):
				inspect.unwrap(payments.stk_push_callback)(**self.payload)
		recover.assert_not_called()

	def test_unconfirmed_provider_response_never_posts(self):
		with (
			patch.object(payments, "frappe", MagicMock()),
			patch.object(payments, "_query_provider_status", return_value={"ResultCode": "1032"}),
			patch.object(payments, "_finish_accounting") as finish,
		):
			result = payments._recover_confirmed_payment(self.express)
		self.assertEqual(result["status"], "Unconfirmed")
		finish.assert_not_called()

	def test_success_for_a_different_checkout_cannot_post(self):
		with (
			patch.object(payments, "frappe", MagicMock()),
			patch.object(
				payments,
				"_query_provider_status",
				return_value={"ResultCode": "0", "CheckoutRequestID": "OTHER-CHECKOUT"},
			),
			patch.object(payments, "_finish_accounting") as finish,
		):
			result = payments._recover_confirmed_payment(self.express)
		self.assertEqual(result["status"], "Unconfirmed")
		finish.assert_not_called()

	def test_status_query_does_not_erase_callback_receipt_evidence(self):
		fake = MagicMock()
		fake.db.get_value.side_effect = ["LOG-1", json.dumps({"callback_result": {"receipt": "RECEIPT-1"}})]
		fake.as_json.side_effect = json.dumps
		with patch.object(payments, "frappe", fake):
			payments._confirmation_log(self.express, {"verified_query": {"ResultCode": "0"}})
		stored = json.loads(fake.db.set_value.call_args.args[3])
		self.assertEqual(stored["callback_result"]["receipt"], "RECEIPT-1")
		self.assertEqual(stored["verified_query"]["ResultCode"], "0")

	def test_accounting_failure_rolls_back_but_keeps_confirmation(self):
		fake = MagicMock()
		with (
			patch.object(payments, "frappe", fake),
			patch.object(
				payments,
				"_query_provider_status",
				return_value={"ResultCode": "0", "CheckoutRequestID": "CHECKOUT-1"},
			),
			patch.object(payments, "_store_query_confirmation") as store,
			patch.object(payments, "_finish_accounting", side_effect=frappe.ValidationError("bad account")),
		):
			result = payments._recover_confirmed_payment(self.express)
		self.assertEqual(result["status"], "Accounting Pending")
		store.assert_called_once()
		fake.db.rollback.assert_called_once_with(save_point="vmms_membership_payment")

	def test_recovery_requires_finance_permission(self):
		fake = MagicMock()
		fake.only_for.side_effect = frappe.PermissionError
		with patch.object(payments, "frappe", fake):
			with self.assertRaises(frappe.PermissionError):
				inspect.unwrap(payments.recover_membership_payment)("EXP-1", dry_run=False)
		fake.get_doc.assert_not_called()
