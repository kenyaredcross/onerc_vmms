import frappe
from frappe.model.document import Document
from frappe import _


def validate(doc: Document, method: str) -> None:
    child_meta = frappe.get_meta("Supporting Document")
    attachment_field = child_meta.get_field("attachment")
    if attachment_field and attachment_field.reqd:
        attachment_field.reqd = 0

    if doc.opportunity_type == "Internal" and doc.designation:
        designation = frappe.get_doc("Designation", doc.designation)
        if not designation.skills or len(designation.skills) == 0:
            frappe.throw(
                _("The selected Designation must have at least one Skill entry.")
            )
