import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import time_diff_in_seconds


def validate(doc: Document, method: str) -> None:
    child_meta = frappe.get_meta("Supporting Document")
    attachment_field = child_meta.get_field("attachment")
    if attachment_field and attachment_field.reqd:
        attachment_field.reqd = 0

    if doc.posted_on and doc.closes_on:
        doc.duration = time_diff_in_seconds(doc.closes_on, doc.posted_on)
