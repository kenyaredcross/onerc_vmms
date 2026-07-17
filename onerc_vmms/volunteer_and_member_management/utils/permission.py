import frappe
from frappe import _


def validate_session_user(owner: str) -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)

	if frappe.session.user != owner:
		frappe.throw_permission_error()
