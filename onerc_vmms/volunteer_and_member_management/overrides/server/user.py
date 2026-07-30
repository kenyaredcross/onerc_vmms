import frappe
from frappe.model.document import Document

from ...utils.utils import disable_energy_point_email_notifications


def on_update(doc: Document, method: str) -> None:
	settings = frappe.get_doc("VM Settings")
	if settings.disable_energy_point_email_notifications:
		disable_energy_point_email_notifications(doc.name)
