from typing import Any

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

from ..services import membership_service as service


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method -- public price list
def get_membership_types():
	return service.list_membership_types()


@frappe.whitelist()
def get_current_membership():
	return service.get_current_memberships()


@frappe.whitelist()
@rate_limit(limit=20, seconds=60)
def download_membership_certificate(membership: str) -> None:
	filename, pdf = service.render_certificate(membership)

	if not pdf:
		return

	frappe.local.response.filename = filename
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def confirm_payment(invoice_name: str) -> str:
	return service.get_payment_status(invoice_name)


@frappe.whitelist()
@rate_limit(limit=10, seconds=60 * 5)
def initiate_membership_registration(
	phone: str | None = None,
	membership_type: str | None = None,
	branch: str | None = None,
	is_existing_member: bool = False,
	proof_attachment: Any = None,
) -> str:
	try:
		frappe.db.begin()
		result = service.register(
			phone=phone,
			membership_type=membership_type,
			branch=branch,
			is_existing_member=bool(cint(is_existing_member)),
			proof_attachment=proof_attachment,
		)
	except frappe.ValidationError:
		frappe.db.rollback()
		raise
	except Exception:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "Error initiating membership registration")
		frappe.throw(_("Error initiating membership registration"))

	return result


@frappe.whitelist()
@rate_limit(limit=10, seconds=60 * 5)
def renew_membership(**kwargs):
	return service.renew(kwargs.get("id"), kwargs.get("phone_number"))


@frappe.whitelist()
def validate_membership_eligibility():
	return service.check_eligibility()


@frappe.whitelist()
def create_member_from_employee(employee: str) -> str:
	return service.create_member_from_employee(employee)


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method -- HMAC-verified QR
@rate_limit(limit=30, seconds=60 * 5)
def verify_membership_qr(membership: str | None = None, token: str | None = None) -> dict:
	return service.verify_qr(membership, token)
