# Copyright (c) 2025, Kenya Red Cross Society and Contributors
# See license.txt

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ...services import membership_payments
from . import vm_membership


class TestVMMembership(FrappeTestCase):
	pass


class TestMembershipPaymentRouting(unittest.TestCase):
	def setUp(self):
		self.membership = SimpleNamespace(name="MEM-1", company="Bomet", currency="KES", amount=500)
		self.member = SimpleNamespace(name="MEMBER-1", customer="CUSTOMER-1", email_id="test@example.com")
		self.plan = SimpleNamespace(name="Annual")
		self.invoice = SimpleNamespace(name="INV-1", outstanding_amount=500)
		self.request = MagicMock()
		self.stale_request = MagicMock()
		self.branch_gateway = {
			"name": "Bomet-Mpesa-KES",
			"payment_account": "Mpesa - BMT",
			"payment_gateway": "Mpesa",
		}
		self.gateway = "Mpesa"
		self.account_company = "Bomet"
		self.mode_account = "Mpesa - BMT"
		self.default_gateway = frappe._dict(
			name="HQ-Mpesa-KES", payment_account="Mpesa - HQ", payment_gateway="Mpesa"
		)
		self.created = []
		self.fake_frappe = MagicMock()
		self.fake_frappe.ValidationError = frappe.ValidationError
		self.fake_frappe.db.get_value.side_effect = self.get_value
		self.fake_frappe.get_doc.side_effect = self.get_doc
		self.fake_frappe.get_all.return_value = []
		self.fake_frappe.db.exists.return_value = None
		self.fake_frappe.throw.side_effect = lambda message: self.fail_validation(message)
		self.patches = patch.multiple(
			vm_membership,
			frappe=self.fake_frappe,
			_=lambda message: message,
			get_payment_gateway_from_mop=lambda *args: self.gateway,
			nowdate=lambda: "2026-10-27",
		)
		self.patches.start()
		self.addCleanup(self.patches.stop)
		payments_patch = patch.multiple(
			membership_payments, frappe=self.fake_frappe, _=lambda message: message
		)
		payments_patch.start()
		self.addCleanup(payments_patch.stop)

	@staticmethod
	def fail_validation(message):
		raise frappe.ValidationError(message)

	def get_value(self, doctype, filters, fields=None, **kwargs):
		if doctype == "VM Settings":
			return "Mpesa"
		if doctype == "Sales Invoice":
			return self.invoice.name
		if doctype == "Payment Gateway Account":
			if filters.get("currency", "KES") != "KES":
				return None
			# The shared default controls collection independently of branch ledgers.
			if filters.get("is_default"):
				return self.default_gateway
			if kwargs.get("as_dict"):
				return frappe._dict(self.branch_gateway) if self.branch_gateway else None
			return self.branch_gateway["name"] if self.branch_gateway else None
		if doctype == "Account":
			owner = "Kenya Red Cross Society" if filters == "Mpesa - HQ" else self.account_company
			if kwargs.get("as_dict"):
				return frappe._dict(company=owner, account_currency="KES", disabled=0, is_group=0)
			return owner
		if doctype == "Mode of Payment Account":
			return self.mode_account
		raise AssertionError(f"Unexpected lookup: {doctype}")

	def get_doc(self, doctype, name=None):
		if isinstance(doctype, dict):
			self.created.append(doctype)
			return self.request
		if doctype == "Sales Invoice":
			return self.invoice
		if doctype == "Payment Request":
			return self.stale_request
		raise AssertionError(f"Unexpected document: {doctype}")

	def test_shared_paybill_is_used_even_when_branch_gateway_exists(self):
		vm_membership.make_payment_request(self.membership, self.member, self.plan)
		self.assertEqual(self.created[0]["payment_gateway_account"], "HQ-Mpesa-KES")

	def test_central_collection_gateway_can_use_valid_branch_ledger_mapping(self):
		self.branch_gateway = None
		vm_membership.make_payment_request(self.membership, self.member, self.plan)
		self.assertEqual(self.created[0]["payment_gateway_account"], "HQ-Mpesa-KES")

	def test_explicit_company_gateway_remains_supported_without_default(self):
		self.default_gateway = None
		vm_membership.make_payment_request(self.membership, self.member, self.plan)
		self.assertEqual(self.created[0]["payment_gateway_account"], "Bomet-Mpesa-KES")

	def test_default_without_provider_is_rejected_before_request_creation(self):
		self.default_gateway.payment_gateway = None
		with self.assertRaises(frappe.ValidationError):
			vm_membership.make_payment_request(self.membership, self.member, self.plan)
		self.assertEqual(self.created, [])

	def test_central_gateway_without_branch_ledger_mapping_can_send_prompt(self):
		self.branch_gateway = None
		self.mode_account = None
		self.gateway = None
		vm_membership.make_payment_request(self.membership, self.member, self.plan, "254712345678")
		self.assertEqual(self.created[0]["payment_gateway_account"], "HQ-Mpesa-KES")
		self.assertEqual(self.created[0]["payment_gateway"], "Mpesa")
		self.request.insert.assert_called_once_with(ignore_permissions=True)
		self.request.submit.assert_called_once_with()

	def test_gateway_currency_must_match_membership(self):
		self.membership.currency = "USD"
		with self.assertRaises(frappe.ValidationError):
			vm_membership.make_payment_request(self.membership, self.member, self.plan)
		self.assertEqual(self.created, [])

	def test_collection_does_not_require_branch_account_ownership(self):
		self.account_company = "Kenya Red Cross Society"
		self.mode_account = None
		vm_membership.make_payment_request(self.membership, self.member, self.plan)
		self.request.submit.assert_called_once_with()

	def test_missing_gateway_is_rejected_before_request_creation(self):
		self.gateway = None
		self.default_gateway = None
		with self.assertRaises(frappe.ValidationError):
			vm_membership.make_payment_request(self.membership, self.member, self.plan)
		self.assertEqual(self.created, [])

	def test_confirmed_request_is_not_cancelled_when_member_retries(self):
		self.fake_frappe.get_all.return_value = ["OLD-PR"]
		self.fake_frappe.db.exists.side_effect = ["Mpesa Express Request", "CONFIRMED-EXPRESS"]
		with self.assertRaises(frappe.ValidationError):
			vm_membership.make_payment_request(self.membership, self.member, self.plan)
		self.stale_request.cancel.assert_not_called()
		self.assertEqual(self.created, [])
