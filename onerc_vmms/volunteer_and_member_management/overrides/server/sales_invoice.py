import frappe
from frappe import _
from frappe.model.document import Document

from ...utils.utils import check_and_renew_membership


def on_update(doc: Document, method: str) -> None:
	check_and_renew_membership(doc.name)
