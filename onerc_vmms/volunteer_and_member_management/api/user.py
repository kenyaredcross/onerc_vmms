import frappe
from frappe import _
from frappe.utils import add_to_date

from ..utils import set_field_value


@frappe.whitelist(allow_guest=True)
def create_user(**kwargs):

    try:
        frappe.db.begin()
        if frappe.db.exists("User", {"email": kwargs.get("email")}):
            frappe.throw("User already exists with this email")

        # if frappe.db.get_creation_count("User", 60) > 300:
        #     return frappe.respond_as_web_page(
        #         _("Temporarily Disabled"),
        #         _(
        #             "Too many users signed up recently, so the registration is disabled. Please try back in an hour"
        #         ),
        #         http_status_code=429,
        #     )

        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": kwargs.get("email") or "",
                "first_name": kwargs.get("first_name") or "",
                "last_name": kwargs.get("last_name") or "",
                "full_name": f'{kwargs.get("first_name") or ""} {kwargs.get("last_name") or ""}',
                "phone": kwargs.get("phone") or "",
                "gender": kwargs.get("gender") or "",
                "enabled": 1,
                "default_app": "onerc_vmms",
            }
        )

        user.insert(ignore_permissions=True)

        user.add_roles("Vmms Guest")

        user_permission = frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": user.name,
                "allow": "User",
                "for_value": user.name,
                "is_default": 1,
            }
        )

        user_permission.insert(ignore_permissions=True)

        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Error signing up")
        frappe.throw("Error signing up")


@frappe.whitelist(allow_guest=True)
def create_membership(**kwargs):

    try:
        frappe.db.begin()

        member = None
        membership = None
        branch = kwargs.get("branch")

        if frappe.db.exists("Member", {"email_id": kwargs.get("email_id")}):
            member = frappe.db.get_value(
                "Member", {"email_id": kwargs.get("email_id")}, "name"
            )

            membership = frappe.db.exists(
                "Membership", {"member": member, "company": branch}
            )
        if member and membership:
            frappe.throw("Membership already exists for this member")

        if not member:
            member = frappe.get_doc(
                {
                    "doctype": "Member",
                    "member_name": kwargs.get("member_name"),
                    "email_id": kwargs.get("email_id"),
                    "membership_type": kwargs.get("membership_type"),
                }
            )
            member.insert(ignore_permissions=True)
        else:
            member = frappe.get_doc("Member", member)

        if kwargs.get("membership_type"):
            doc_name = kwargs.get("membership_type")
            from_date = frappe.utils.today()
            to_date = add_to_date(from_date, years=1)

            membership = frappe.get_doc(
                {
                    "doctype": "Membership",
                    "member": member.name,
                    "membership_type": doc_name,
                    "company": kwargs.get("branch"),
                    "status": "Pending",
                    "from_date": from_date,
                    "to_date": to_date,
                    "member_since_date": from_date,
                }
            )

            membership.insert(ignore_permissions=True)

        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Error creating membership")
        frappe.throw("Error creating membership")


@frappe.whitelist(allow_guest=True)
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
        as_dict=1,
    )

    roles = frappe.get_roles(user.name)
    user["roles"] = roles

    job_applicant = frappe.db.get_value(
        "Job Applicant",
        {"email_id": user.email, "is_volunteer": 1},
        ["name", "status"],
        as_dict=True,
    )

    if job_applicant and job_applicant.get("docstatus") == 1:
        user["is_pending_approval"] = True
    else:
        user["is_pending_approval"] = False

    employee_name = employee_company = None
    employee_is_volunteer = False

    if frappe.db.exists("Employee", {"user_id": user.name, "status": "Active"}):

        employee = frappe.db.get_value(
            "Employee",
            {"user_id": user.name},
            ["name", "company", "is_volunteer"],
            as_dict=True,
        )
        if employee:

            employee_name = employee.get("name")
            employee_company = employee.get("company")
            employee_is_volunteer = True if employee.get("is_volunteer") else False

        user["non_profit_member"] = "Non Profit Member" in roles
        user["employee"] = employee_name
        user["company"] = employee_company
        user["is_volunteer"] = employee_is_volunteer

    if frappe.db.exists("Member", {"email_id": user.email}):
        member = frappe.db.get_value(
            "Member",
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
        frappe.throw(
            _("You must be logged in to access user details"), frappe.PermissionError
        )

    user_doc = frappe.get_doc("User", frappe.session.user)
    user_info = user_doc.as_dict()

    return user_info


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
            if user_doc.meta.has_field(fieldname):
                fieldtype = user_doc.meta.get_field(fieldname).fieldtype
                set_field_value(user_doc, fieldname, value, fieldtype)

        user_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {"message": _("Profile updated successfully")}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error("User Profile Update Error", str(e))
