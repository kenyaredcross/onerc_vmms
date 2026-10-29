import frappe
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest

from ...services.membership_payments import (
	get_existing_payment,
	get_receiving_account,
	get_vmms_invoice,
	validate_existing_payment,
)


class VMMSPaymentRequest(PaymentRequest):
	def create_payment_entry(self, submit=True):
		invoice = get_vmms_invoice(self)
		if not invoice:
			return super().create_payment_entry(submit=submit)
		# Serialize callbacks and recovery against the same payment intent.
		outstanding = frappe.db.get_value("Payment Request", self.name, "outstanding_amount", for_update=True)
		invoice = get_vmms_invoice(self)
		existing = get_existing_payment(self, invoice)
		if existing:
			validate_existing_payment(existing, invoice.company)
			return frappe.get_doc("Payment Entry", existing)
		if invoice.docstatus != 1 or invoice.outstanding_amount <= 0:
			frappe.throw("The invoice must be submitted and outstanding before posting payment")
		if outstanding is not None:
			self.outstanding_amount = outstanding
		original_account = self.payment_account
		self.payment_account = get_receiving_account(
			original_account, self.mode_of_payment, invoice.company, self.currency
		)
		try:
			return super().create_payment_entry(submit=submit)
		finally:
			self.payment_account = original_account
