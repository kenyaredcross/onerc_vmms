import frappe
from frappe import _
from frappe.model.document import Document
from ...utils import check_and_renew_membership


@frappe.whitelist()
def on_update(doc: Document, method: str) -> None:
    if doc.against_voucher_type == "Sales Invoice" and doc.against_voucher:
        check_and_renew_membership(doc.against_voucher)
