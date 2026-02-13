import frappe
from frappe.model.document import Document
from frappe.utils import random_string

def before_validate(doc: Document, method: str) -> None:
    language_name = doc.language_name or doc.name
    
    if not language_name:
        return

    existing = frappe.db.get_value("Language", {"language_name": language_name}, ["name", "language_code"], as_dict=True)
    if existing:
        doc.language_name = existing.name
        doc.language_code = existing.language_code or existing.name
        return

    base = language_name[:3].lower()
    code = base
    while frappe.db.exists("Language", code):
        code = f"{base}{random_string(2).lower()}"

    doc.language_name = language_name
    doc.language_code = code
