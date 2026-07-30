from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, flt, format_date, get_fullname

from ..api.user import get_user_details
from ..utils.permission import validate_session_user
from ..utils.utils import log_throw_error, system_session

MEMBERSHIP = "VM Membership"
MEMBERSHIP_TYPE = "VM Membership Type"
MEMBER = "VM Member"

UNPAYABLE_STATUSES = ("Pending", "Rejected")

REQUIRED_PROFILE_FIELDS = (
	"full_name",
	"phone",
	"id_number",
	"county",
	"sub_county",
	"birth_date",
	"gender",
	"citizenship",
	"identification_type",
)


def validate_membership_type(membership_type: str | None) -> str:
	if not membership_type or not frappe.db.exists(MEMBERSHIP_TYPE, membership_type):
		frappe.throw(_("Please select a valid membership type"))

	return membership_type


def validate_branch(branch: str | None) -> str:
	"""Only a real, non-group Company may be used as a branch."""
	if not branch:
		frappe.throw(_("Please select a branch or county"))

	company = frappe.db.get_value("Company", branch, ["name", "is_group"], as_dict=True)
	if not company or company.is_group:
		frappe.throw(_("Please select a valid branch or county"))

	return company.name


def validate_phone(phone: str | None) -> str:
	"""Reject anything the M-Pesa gateway would not accept before we create documents."""
	from frappe_mpsa_payments.utils.utils import validate_phone_number

	phone = (phone or "").strip()
	if not validate_phone_number(phone):
		frappe.throw(_("Please enter a valid phone number"))

	return phone


def validate_age_eligibility(membership_type_doc: Document) -> None:
	if not membership_type_doc.requires_age_requirement:
		return

	age = get_user_details().get("age", 0)
	lower = membership_type_doc.lower_age_limit
	upper = membership_type_doc.upper_age_limit

	if lower <= age <= upper:
		return

	if lower == 0:
		frappe.throw(_("You must be under {0} years to apply for this membership").format(upper))
	elif lower == 30:
		frappe.throw(_("You must be 30 years or older to apply for this membership"))
	else:
		frappe.throw(
			_(
				"Your age does not meet the requirements for this membership type. "
				"It should be between {0} and {1} years."
			).format(lower, upper)
		)


def check_conflicting_memberships(member_doc: Document, company: str) -> None:
	status = frappe.db.get_value(
		MEMBERSHIP,
		{
			"member": member_doc.name,
			"company": company,
			"status": ["in", ["Active", "Pending"]],
		},
		"status",
	)

	if status == "Active":
		frappe.throw(_("You already have an active membership for this branch."))
	elif status == "Pending":
		frappe.throw(_("You have a pending membership for this branch. Please complete the payment."))


def get_owned_membership(membership_id: str) -> Document:
	if not membership_id or not isinstance(membership_id, str):
		frappe.throw(_("Access Denied"), frappe.PermissionError)

	membership = frappe.db.get_value(MEMBERSHIP, membership_id, ["name", "member"], as_dict=True)

	if not membership or not membership.member:
		frappe.throw(_("Access Denied"), frappe.PermissionError)

	validate_session_user(frappe.db.get_value(MEMBER, membership.member, "email_id"))

	return frappe.get_doc(MEMBERSHIP, membership.name)


def get_session_member() -> str | None:
	return frappe.db.get_value(MEMBER, {"email_id": frappe.session.user}, "name")


def register(
	phone: str | None,
	membership_type: str | None,
	branch: str | None,
	is_existing_member: bool = False,
	proof_attachment=None,
) -> str:
	membership_type = validate_membership_type(membership_type)
	branch = validate_branch(branch)

	if not is_existing_member:
		phone = validate_phone(phone)

	membership_id = create_membership(membership_type, branch, is_existing_member)

	if is_existing_member:
		attach_membership_proof(membership_id, proof_attachment)
		return "Application Submitted"

	return start_payment(membership_id, phone)


def create_membership(membership_type: str, branch: str, is_existing_member: bool = False) -> str:
	membership_type_doc = frappe.get_doc(MEMBERSHIP_TYPE, membership_type)

	validate_age_eligibility(membership_type_doc)

	amount = flt(membership_type_doc.amount)
	if amount <= 0 and not is_existing_member:
		frappe.throw(_("Membership type {0} has no price configured").format(membership_type))

	currency = membership_type_doc.currency or frappe.get_cached_value("Company", branch, "default_currency")

	member = get_session_member()
	member = frappe.get_doc(MEMBER, member) if member else create_member()

	check_conflicting_memberships(member, branch)

	from_date = datetime.today().date()

	try:
		membership = frappe.get_doc(
			{
				"doctype": MEMBERSHIP,
				"member": member.name,
				"membership_type": membership_type,
				"amount": amount,
				"currency": currency,
				"company": branch,
				"status": "Pending" if is_existing_member else "Draft",
				"from_date": from_date,
				"to_date": add_to_date(from_date, years=1, days=-1),
				"member_since_date": from_date,
				"is_existing_member": is_existing_member,
			}
		)
		membership.insert(ignore_permissions=True)

	except frappe.ValidationError:
		raise
	except Exception:
		log_throw_error("Error creating membership")

	return membership.name


def create_member() -> Document:
	member = frappe.get_doc(
		{
			"doctype": MEMBER,
			"member_name": get_fullname(),
			"email_id": frappe.session.user,
		}
	)
	member.insert(ignore_permissions=True)

	return member


def create_member_from_employee(employee_id: str) -> str:
	if not employee_id or not isinstance(employee_id, str):
		frappe.throw(_("Please select an employee"))

	frappe.has_permission("Employee", "read", employee_id, throw=True)

	employee = frappe.db.get_value(
		"Employee",
		employee_id,
		["name", "employee_name", "personal_email", "user_id", "image"],
		as_dict=True,
	)
	if not employee:
		frappe.throw(_("Employee {0} not found").format(employee_id))

	user = employee.user_id
	if not user and employee.personal_email:
		user = frappe.db.get_value("User", {"email": employee.personal_email}, "name")

	if not user:
		frappe.throw(
			_("{0} has no user account yet. Set a Personal Email on the employee first.").format(
				employee.employee_name or employee_id
			)
		)

	existing = frappe.db.exists(MEMBER, {"volunteer": employee.name}) or frappe.db.exists(
		MEMBER, {"email_id": user}
	)
	if existing:
		return existing

	member = frappe.get_doc(
		{
			"doctype": MEMBER,
			"member_name": employee.employee_name,
			"email_id": user,
			"volunteer": employee.name,
			"image": employee.image,
		}
	)
	member.insert()

	return member.name


def attach_membership_proof(membership_id: str, proof_attachment) -> None:
	if not proof_attachment:
		return

	attachments = proof_attachment if isinstance(proof_attachment, list) else [proof_attachment]

	for attachment in attachments:
		file_url = attachment if isinstance(attachment, str) else (attachment or {}).get("file_url")
		if not file_url:
			continue

		file = frappe.db.get_value(
			"File",
			{"file_url": file_url, "owner": frappe.session.user},
			["name", "attached_to_doctype", "attached_to_name"],
			as_dict=True,
		)
		if not file:
			frappe.throw(_("The uploaded proof of membership could not be found"))

		if file.attached_to_doctype and file.attached_to_name:
			frappe.db.set_value(
				"File",
				file.name,
				{
					"attached_to_doctype": MEMBERSHIP,
					"attached_to_name": membership_id,
					"is_private": 1,
				},
			)
			continue

		frappe.get_doc(
			{
				"doctype": "File",
				"file_url": file_url,
				"attached_to_doctype": MEMBERSHIP,
				"attached_to_name": membership_id,
				"is_private": 1,
			}
		).insert(ignore_permissions=True)


def start_payment(membership_id: str, phone_number: str) -> str:
	"""Raise the accounting documents and trigger the STK push. Returns the payment token."""
	payment_request, _invoice = _initiate_payment(membership_id, phone_number)

	return payment_request.payment_token


def renew(membership_id: str, phone_number: str | None):
	"""Renew an existing membership belonging to the logged-in user. Returns the invoice."""
	_payment_request, invoice = _initiate_payment(membership_id, validate_phone(phone_number))

	return invoice


def _initiate_payment(membership_id: str, phone_number: str) -> tuple[Document, Document]:
	membership = get_owned_membership(membership_id)

	if membership.status in UNPAYABLE_STATUSES:
		frappe.throw(_("This membership is not awaiting payment"))

	try:
		with system_session():
			return membership.initiate_payment(phone_number=phone_number)

	except frappe.ValidationError:
		raise
	except Exception:
		log_throw_error("Error initiating membership payment")


def get_payment_status(invoice_name: str) -> str:
	"""Report whether the caller's own invoice has been settled."""
	if not invoice_name:
		frappe.throw(_("Access Denied"), frappe.PermissionError)

	invoice = frappe.db.get_value(
		"Sales Invoice",
		invoice_name,
		["name", "status", "outstanding_amount", "membership"],
		as_dict=True,
	)
	if not invoice or not invoice.membership:
		frappe.throw(_("Access Denied"), frappe.PermissionError)

	get_owned_membership(invoice.membership)

	return "paid" if invoice.status == "Paid" and invoice.outstanding_amount == 0 else "unpaid"


def list_membership_types() -> list[dict]:
	memberships = frappe.get_all(
		MEMBERSHIP_TYPE,
		fields=["name", "membership_type", "amount"],
		order_by="amount asc",
	)
	for membership in memberships:
		membership.update(frappe.get_doc(MEMBERSHIP_TYPE, membership.name).as_dict())

	return memberships


def get_current_memberships() -> list[dict]:
	"""Return the caller's memberships, hiding Expired rows superseded by a live one."""
	member = get_session_member()
	if not member:
		return []

	memberships = frappe.get_all(
		MEMBERSHIP,
		filters={"member": member},
		or_filters=[
			{"status": "Active"},
			{"status": "Expired"},
			{"status": "Pending"},
		],
		fields=["name", "membership_type", "company", "status"],
		order_by="from_date desc",
	)

	if not memberships:
		return []

	groups: dict[tuple, list] = {}
	for membership in memberships:
		groups.setdefault((membership.membership_type, membership.company), []).append(membership)

	result = []
	for group in groups.values():
		has_live = any(m.status in ("Active", "Pending") for m in group)
		relevant = [m for m in group if m.status != "Expired"] if has_live else group

		for membership in relevant:
			doc = frappe.get_doc(MEMBERSHIP, membership.name)
			data = doc.as_dict()

			if doc.membership_type:
				data["type_details"] = frappe.get_doc(MEMBERSHIP_TYPE, doc.membership_type).as_dict()

			result.append(data)

	return result


def get_certificate_template(membership_type: str) -> str:
	"""Return the print format configured on a membership type."""
	error_message = _("Error printing membership certificate")

	if not membership_type:
		frappe.throw(error_message)

	template = frappe.db.get_value(MEMBERSHIP_TYPE, membership_type, "template")
	if not template:
		frappe.respond_as_web_page("Membership cannot be printed right now.")
		return

	return template


def render_certificate(membership_id: str) -> tuple[str, bytes]:
	"""Render an active membership's certificate. Returns ``(filename, pdf)``."""
	membership = get_owned_membership(membership_id)

	if membership.status != "Active":
		frappe.throw(_("A certificate is only available for an active membership"))

	print_format = frappe.db.get_value(MEMBERSHIP_TYPE, membership.membership_type, "template")
	if not print_format:
		frappe.log_error(
			title=f"No certificate template set on {MEMBERSHIP_TYPE} {membership.membership_type}",
			message="Membership Certificate Template Missing",
			reference_doctype="VM Membership",
			reference_name=membership.membership_type,
		)
		frappe.respond_as_web_page(
			title="You cannot download the membership certificate right now",
			html="<b>Please Try Again Later</b>",
			indicator_color="red",
			primary_action="/vmms",
			fullpage=True,
		)
		return None, None

	previous_flag = frappe.flags.ignore_print_permissions
	frappe.flags.ignore_print_permissions = True
	try:
		pdf = frappe.get_print(
			MEMBERSHIP,
			membership.name,
			print_format,
			doc=membership,
			as_pdf=True,
		)
	finally:
		frappe.flags.ignore_print_permissions = previous_flag

	return f"{membership.name.replace('/', '-')}.pdf", pdf


def check_eligibility() -> dict:
	"""Report which profile fields the caller still needs before applying."""
	user_info = get_user_details()

	missing_fields = [
		field.replace("_", " ").title() for field in REQUIRED_PROFILE_FIELDS if not user_info.get(field)
	]

	return {"eligible": not missing_fields, "missing_fields": missing_fields}


def verify_qr(membership_id: str | None, token: str | None) -> dict:
	"""Verify a scanned membership QR code. Public - the HMAC token is the credential."""
	from ..doctype.vm_membership.vm_membership import verify_qr_token

	invalid_msg = _("This QR code or verification link is invalid")

	if not verify_qr_token(membership_id, token):
		frappe.throw(invalid_msg)

	data = frappe.db.get_value(
		MEMBERSHIP,
		membership_id,
		["member_name", "membership_type", "status", "from_date", "to_date"],
		as_dict=True,
	)
	if not data:
		frappe.throw(invalid_msg)

	return {
		"membership": membership_id,
		"member_name": data.member_name,
		"membership_type": data.membership_type,
		"status": data.status,
		"is_valid": data.status == "Active",
		"valid_from": format_date(data.from_date) if data.from_date else None,
		"valid_until": format_date(data.to_date) if data.to_date else None,
	}
