from datetime import date

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from ..services.user import create_vmms_user
from ..utils.utils import set_field_value

SELF_EDITABLE_USER_FIELDS = frozenset(
	{
		"first_name",
		"middle_name",
		"last_name",
		"phone",
		"mobile_no",
		"gender",
		"birth_date",
		"marital_status",
		"blood_group",
		"citizenship",
		"country_of_citizenship",
		"identification_type",
		"id_number",
		"passport_number",
		"number_of_dependants",
		"administrative_location",
		"sub_county",
		"county",
		"ward",
		"access_to_internet",
		"profession",
		"user_image",
		"location",
		"language",
		"time_zone",
		"supporting_documents",
	}
)


@frappe.whitelist(
	allow_guest=True
)  # nosemgrep: guest-whitelisted-method -- public signup; rate-limited & validated
@rate_limit(limit=5, seconds=60 * 5)
def create_user(**kwargs):
	try:
		frappe.db.begin()
		create_vmms_user(
			email=kwargs.get("email"),
			first_name=kwargs.get("first_name"),
			last_name=kwargs.get("last_name"),
			phone=kwargs.get("phone"),
			gender=kwargs.get("gender"),
		)
	except frappe.ValidationError:
		frappe.db.rollback()
		raise
	except Exception:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "Error signing up")
		frappe.throw(_("Error signing up"))
	else:
		frappe.db.commit()


@frappe.whitelist(
	allow_guest=True
)  # nosemgrep: guest-whitelisted-method -- returns Guest for anonymous; self-scoped otherwise
def get_user_info():
	if frappe.session.user == "Guest":
		return "Guest"

	user = frappe.db.get_value(
		"User",
		frappe.session.user,
		[
			"name",
			"email",
			"enabled",
			"user_image",
			"full_name",
			"user_type",
			"username",
			"phone",
			"ward",
			"first_name",
			"last_name",
			"middle_name",
			"birth_date",
			"identification_type",
			"id_number",
			"passport_number",
			"number_of_dependants",
			"marital_status",
			"blood_group",
			"citizenship",
			"country_of_citizenship",
			"administrative_location",
			"sub_county",
			"county",
			"access_to_internet",
			"profession",
			"gender",
		],
		as_dict=True,
	)

	roles = frappe.get_roles(user.name)
	user["roles"] = roles

	vol_applicant = frappe.db.get_value(
		"Job Applicant",
		{"email_id": user.email, "is_volunteer": 1},
		["name", "docstatus"],
		as_dict=True,
	)

	if vol_applicant:
		user["vol_applicant"] = vol_applicant.get("name")
		if vol_applicant.get("docstatus") == 1:
			user["is_pending_approval"] = True
		else:
			user["is_pending_approval"] = False

	employee_name = employee_company = None
	employee_is_volunteer = False
	employee = None
	if frappe.db.exists("Employee", {"user_id": user.name, "status": "Active"}):
		employee = frappe.db.get_value(
			"Employee",
			{"user_id": user.name, "status": "Active"},
			["name", "company", "is_volunteer"],
			as_dict=True,
		)
	elif vol_applicant and frappe.db.exists(
		"Employee", {"job_applicant": vol_applicant.get("name"), "status": "Active"}
	):
		employee = frappe.db.get_value(
			"Employee",
			{"job_applicant": vol_applicant.get("name"), "status": "Active"},
			["name", "company", "is_volunteer"],
			as_dict=True,
		)
	if employee:
		employee_name = employee.get("name")
		employee_company = employee.get("company")
		employee_is_volunteer = True if employee.get("is_volunteer") else False

	user["employee"] = employee_name if employee_name else None
	user["company"] = employee_company if employee_company else None
	user["is_volunteer"] = employee_is_volunteer

	if frappe.db.exists("VM Member", {"email_id": user.email}):
		member = frappe.db.get_value(
			"VM Member",
			{"email_id": user.email},
			["name"],
			as_dict=True,
		)
		if member:
			user["member"] = member.get("name")
			user["is_member"] = True

	if frappe.db.exists("Job Applicant", {"email_id": user.email}):
		applicant = frappe.db.get_value(
			"Job Applicant",
			{"email_id": user.email},
			["name", "status"],
			as_dict=True,
		)
		if applicant:
			user["job_applicant"] = applicant.get("name")
			user["application_status"] = applicant.get("status")
			user["applied_for"] = applicant.get("job_title")

	return user


@frappe.whitelist()
def get_user_details():
	"""
	Returns the logged-in user's details.
	"""
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in to access user details"), frappe.PermissionError)

	user_doc = frappe.get_doc("User", frappe.session.user)
	user_info = user_doc.as_dict()
	user_info["age"] = calculate_age(user_info.get("birth_date"))

	return user_info


def calculate_age(birth_date: date) -> int:
	"""Calculate age from a date object."""
	if not birth_date:
		return 0

	today = date.today()
	age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
	return age


@frappe.whitelist()
def update_user_details(**data):
	"""
	Updates the logged-in user's details.
	`data` should be a dict of fields to update.
	"""
	try:
		if not frappe.session.user or frappe.session.user == "Guest":
			frappe.throw(
				_("You must be logged in to update your profile"),
				frappe.PermissionError,
			)

		if isinstance(data, str):
			import json

			try:
				data = json.loads(data)
			except Exception:
				frappe.throw(_("Invalid data format"))

		user_doc = frappe.get_doc("User", frappe.session.user)

		for fieldname, value in data.items():
			# Only allow a fixed set of self-service profile fields. This is the security
			# boundary: without it, a user could set `roles`, `role_profile_name` or
			# `user_type` and escalate to System Manager (save uses ignore_permissions).
			if fieldname not in SELF_EDITABLE_USER_FIELDS:
				continue
			if user_doc.meta.has_field(fieldname):
				fieldtype = user_doc.meta.get_field(fieldname).fieldtype
				set_field_value(user_doc, fieldname, value, fieldtype)

		user_doc.save(ignore_permissions=True)
		frappe.db.commit()

		return {"message": _("Profile updated successfully")}

	except Exception:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "User Profile Update Error")
		frappe.throw(_("Could not update your profile. Please try again."))
