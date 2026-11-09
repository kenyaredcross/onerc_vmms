# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A paid membership fee lands in ERPNext's books, balanced, on the branch's cost centre.

The payment goes through the real Manual gateway, which calls the membership's
`on_payment_confirmed` exactly as M-Pesa's callback does; posting then runs
(synchronously under test) and must leave a submitted Sales Invoice with nothing
outstanding and a submitted Payment Entry against it.
"""

from unittest.mock import patch

import frappe
from frappe.utils import add_days, flt, today

from vmmsx.finance.services import geo_cost_center, membership_posting
from vmmsx.member.services import methods, receipt
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase
from vmmsx.setup import membership_accounting
from vmmsx.setup.geo_cost_center_fields import POSTING_FIELD

EXTRA_TEST_RECORD_DEPENDENCIES = []

SETTINGS = "VMMS Accounting Settings"


class TestMembershipPosting(RegistrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value(
			"Company", {"is_group": 0}, "name"
		)
		if not company:
			raise cls.skipTest(cls, "This site has no ERPNext company to post to.")
		frappe.db.set_single_value("Global Defaults", "default_company", company)
		cls.company = company

		geo_cost_center.backfill()

		# The Manual gateway the suite pays through, offered and mapped to Cash.
		gateway = fixtures._manual_gateway_name()
		settings = frappe.get_single(methods.SETTINGS_DOCTYPE)
		if not any(row.gateway == gateway for row in settings.get(methods.METHODS_FIELD) or []):
			settings.append(methods.METHODS_FIELD, {"gateway": gateway, "label": "Pay at a branch", "is_enabled": 1})
			settings.flags.ignore_permissions = True
			settings.save()
		cls.gateway = gateway

		membership_accounting.configure()
		frappe.db.set_single_value(SETTINGS, {"enabled": 1, "posting_starts_on": "2000-01-01"})
		frappe.clear_document_cache(SETTINGS, SETTINGS)

	def paid_membership(self, handle: str):
		# A distinct name each: two customers with one name is ordinary on MariaDB,
		# but ERPNext's de-duplicating suffix uses a function SQLite lacks.
		user, membership = self.register_as_member(
			handle,
			fixtures.TYPE_AUTO,
			payer_phone="+254711000222",
			applicant_last_name=handle.split(".")[-1].title(),
		)
		fixtures.confirm_payment_through_manual_driver(membership)
		membership.reload()
		return user, membership

	# --- the books ----------------------------------------------------------

	def test_a_paid_fee_is_invoiced_and_settled_on_the_branch_cost_centre(self):
		_, membership = self.paid_membership("posting.paid")

		self.assertEqual(membership.accounting_status, "Posted", membership.accounting_note)
		invoice = frappe.get_doc("Sales Invoice", membership.sales_invoice)
		entry = frappe.get_doc("Payment Entry", membership.payment_entry)
		branch_cost_center = frappe.db.get_value("Geo Node", membership.geo_node, POSTING_FIELD)

		self.assertEqual(invoice.docstatus, 1)
		self.assertEqual(invoice.company, self.company)
		self.assertEqual(flt(invoice.grand_total), 500)
		self.assertEqual(flt(invoice.outstanding_amount), 0, "the payment settles the invoice in full")
		self.assertEqual(invoice.items[0].cost_center, branch_cost_center)
		self.assertEqual(invoice.items[0].income_account, frappe.db.get_single_value(SETTINGS, "income_account"))
		self.assertEqual(invoice.vmms_membership, membership.name)

		self.assertEqual(entry.docstatus, 1)
		self.assertEqual(entry.mode_of_payment, "Cash")
		self.assertEqual(entry.cost_center, branch_cost_center)
		self.assertEqual(flt(entry.paid_amount), 500)
		self.assertEqual(entry.references[0].reference_name, invoice.name)
		self.assertTrue(entry.reference_no)

	def test_the_ledger_balances(self):
		_, membership = self.paid_membership("posting.balanced")

		for voucher in (membership.sales_invoice, membership.payment_entry):
			rows = frappe.get_all(
				"GL Entry", filters={"voucher_no": voucher, "is_cancelled": 0}, fields=["debit", "credit"]
			)
			self.assertTrue(rows)
			self.assertEqual(sum(flt(row.debit) for row in rows), sum(flt(row.credit) for row in rows))

	def test_the_member_is_one_customer(self):
		_, membership = self.paid_membership("posting.customer")

		customer = frappe.db.get_value("VMMS Member", membership.member, "customer")
		self.assertEqual(frappe.db.get_value("Sales Invoice", membership.sales_invoice, "customer"), customer)
		self.assertEqual(frappe.db.get_value("Customer", customer, "customer_type"), "Individual")

	def test_posting_twice_posts_once(self):
		_, membership = self.paid_membership("posting.twice")
		before = frappe.db.count("Sales Invoice", {"vmms_membership": membership.name})

		result = membership_posting.post(membership.name)

		self.assertFalse(result["posted"])
		self.assertEqual(frappe.db.count("Sales Invoice", {"vmms_membership": membership.name}), before)

	def test_a_code_that_arrives_after_posting_reaches_the_payment_entry(self):
		_, membership = self.paid_membership("posting.latecode")
		# As posted when the poll confirmed the payment before the callback came.
		frappe.db.set_value("Payment Entry", membership.payment_entry, "reference_no", membership.name)

		self.assertTrue(membership_posting.attach_receipt(membership, "TKB1A2C3D4"))

		entry = frappe.get_doc("Payment Entry", membership.payment_entry)
		self.assertEqual(entry.reference_no, "TKB1A2C3D4")
		self.assertIn("TKB1A2C3D4", entry.remarks)
		self.assertEqual(entry.docstatus, 1)
		self.assertTrue(
			frappe.db.exists(
				"Comment",
				{"reference_doctype": "Payment Entry", "reference_name": entry.name, "comment_type": "Info"},
			)
		)
		self.assertFalse(membership_posting.attach_receipt(membership, "TKB1A2C3D4"), "only once")

	# --- what is not posted -------------------------------------------------

	def test_nothing_is_posted_while_switched_off(self):
		frappe.db.set_single_value(SETTINGS, "enabled", 0)
		try:
			_, membership = self.paid_membership("posting.off")
		finally:
			frappe.db.set_single_value(SETTINGS, "enabled", 1)

		self.assertFalse(membership.sales_invoice)
		self.assertFalse(membership.accounting_status)

	def test_a_fee_paid_while_posting_was_off_is_posted_by_the_daily_job(self):
		frappe.db.set_single_value(SETTINGS, "enabled", 0)
		try:
			_, membership = self.paid_membership("posting.later")
		finally:
			frappe.db.set_single_value(SETTINGS, "enabled", 1)
		self.assertFalse(membership.accounting_status)
		self.assertIn(membership.name, membership_posting.outstanding(limit=None))

		# The job commits one membership at a time; keep it inside this test.
		with patch.object(frappe.db, "commit"):
			result = membership_posting.post_outstanding(limit=None)

		membership.reload()
		self.assertEqual(membership.accounting_status, "Posted", membership.accounting_note)
		self.assertGreaterEqual(result["posted"], 1)
		self.assertNotIn(membership.name, membership_posting.outstanding(limit=None))

	def test_a_fee_paid_before_posting_started_is_never_outstanding(self):
		frappe.db.set_single_value(SETTINGS, "enabled", 0)
		try:
			_, membership = self.paid_membership("posting.before")
		finally:
			frappe.db.set_single_value(SETTINGS, "enabled", 1)

		frappe.db.set_single_value(SETTINGS, "posting_starts_on", add_days(today(), 5))
		try:
			self.assertNotIn(membership.name, membership_posting.outstanding(limit=None))
		finally:
			frappe.db.set_single_value(SETTINGS, "posting_starts_on", "2000-01-01")

	def test_only_accounts_staff_are_offered_the_post_button(self):
		from vmmsx.member.services import membership as membership_service

		frappe.db.set_single_value(SETTINGS, "enabled", 0)
		try:
			user, membership = self.paid_membership("posting.button")
		finally:
			frappe.db.set_single_value(SETTINGS, "enabled", 1)

		self.assertTrue(membership_service.status(membership)["can_post_to_books"])
		with fixtures.acting_as(user):
			self.assertFalse(membership_service.status(membership)["can_post_to_books"])

		membership_posting.post(membership.name)
		membership.reload()
		self.assertFalse(membership_service.status(membership)["can_post_to_books"], "already posted")

	def test_a_failed_button_press_answers_with_the_reason(self):
		from vmmsx.api import member as member_api

		frappe.db.set_single_value(SETTINGS, "enabled", 0)
		try:
			_, membership = self.paid_membership("posting.press")
		finally:
			frappe.db.set_single_value(SETTINGS, "enabled", 1)

		with patch.object(membership_posting, "_cost_center", side_effect=frappe.ValidationError("No cost centre")):
			with patch.object(frappe.db, "commit"):
				result = member_api.post_membership_payment(membership.name)

		self.assertFalse(result["posted"])
		self.assertIn("No cost centre", result["reason"])
		self.assertEqual(frappe.db.get_value("VMMS Membership", membership.name, "accounting_status"), "Failed")

	def test_the_setup_check_names_what_stops_posting(self):
		switched_off = "Posting is switched off (VMMS Accounting Settings > Enabled)."
		self.assertNotIn(switched_off, membership_accounting.problems(self.company))

		frappe.db.set_single_value(SETTINGS, "enabled", 0)
		try:
			self.assertIn(switched_off, membership_accounting.problems(self.company))
		finally:
			frappe.db.set_single_value(SETTINGS, "enabled", 1)

	def test_a_payment_before_posting_started_is_not_posted(self):
		frappe.db.set_single_value(SETTINGS, "posting_starts_on", add_days(today(), 5))
		try:
			_, membership = self.paid_membership("posting.early")
		finally:
			frappe.db.set_single_value(SETTINGS, "posting_starts_on", "2000-01-01")

		self.assertFalse(membership.sales_invoice)

	def test_a_failure_is_recorded_and_the_member_still_paid(self):
		settings = frappe.get_single(methods.SETTINGS_DOCTYPE)
		for row in settings.get(methods.METHODS_FIELD):
			if row.gateway == self.gateway:
				row.mode_of_payment = None
		settings.flags.ignore_permissions = True
		settings.save()

		_, membership = self.paid_membership("posting.unmapped")

		self.assertEqual(membership.accounting_status, "Failed")
		self.assertIn("mode of payment", membership.accounting_note)
		self.assertTrue(membership.paid_on, "the payment itself is unaffected")
		self.assertFalse(frappe.db.exists("Sales Invoice", {"vmms_membership": membership.name, "docstatus": 1}))

		for row in settings.get(methods.METHODS_FIELD):
			if row.gateway == self.gateway:
				row.mode_of_payment = "Cash"
		settings.save()

		self.assertTrue(membership_posting.post(membership.name)["posted"])

	# --- the receipt --------------------------------------------------------

	def test_the_receipt_carries_the_payment_and_the_books(self):
		_, membership = self.paid_membership("posting.receipt")

		shown = receipt.build(membership)

		self.assertEqual(shown["receipt_number"], membership.payment_entry)
		self.assertEqual(shown["sales_invoice"], membership.sales_invoice)
		self.assertEqual(flt(shown["amount"]), 500)
		self.assertTrue(shown["gateway_receipt"])
		self.assertEqual(shown["member"]["member_number"], membership.member)
		self.assertEqual(shown["method"], methods.label_of(self.gateway), "the society's own name for the method")
		self.assertFalse(shown["by_phone"])

	def test_the_member_reads_their_own_receipt_and_nobody_else_does(self):
		from vmmsx.api import member as member_api

		user, membership = self.paid_membership("posting.mine")
		stranger = fixtures.website_account("posting.stranger")

		with fixtures.acting_as(user):
			self.assertEqual(member_api.membership_receipt(membership.name)["membership"]["name"], membership.name)

		with fixtures.acting_as(stranger), self.assertRaises(frappe.PermissionError):
			member_api.membership_receipt(membership.name)

	def test_an_unpaid_membership_has_no_receipt(self):
		_, membership = self.register_as_member("posting.unpaid", fixtures.TYPE_AUTO)

		with self.assertRaises(frappe.DoesNotExistError):
			receipt.build(membership)
