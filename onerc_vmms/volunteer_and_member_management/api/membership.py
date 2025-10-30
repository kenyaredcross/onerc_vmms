from datetime import datetime

import frappe
from frappe import _
from frappe.utils import add_to_date


@frappe.whitelist(allow_guest=True)
def get_membership_types():
    memberships = frappe.get_all(
        "VM Membership Type",
        fields=["name", "membership_type", "amount"],
        order_by="amount asc",
    )
    for membership in memberships:
        membership_benefits = frappe.get_all(
            "Membership Benefit", {"parent": membership.name}, ["benefit"]
        )

        if membership_benefits:
            membership["benefits"] = [b.benefit for b in membership_benefits]

    return memberships


@frappe.whitelist()
def get_current_membership():
    if frappe.session.user == "Guest":
        return []

    member = frappe.db.get_value(
        "VM Member",
        {"email_id": frappe.session.user},
        ["name"],
        as_dict=True,
    )

    if not member:
        return []

    memberships = frappe.get_all(
        "VM Membership",
        filters={"member": member.name},
        or_filters=[
            {"status": "Active"},
            {"status": "Expired"},
            {"status": "Pending"},
        ],
        fields=["name"],
        order_by="from_date desc",
    )

    if not memberships:
        return []

    result = []
    for membership_item in memberships:
        membership = frappe.get_doc("VM Membership", membership_item.name)
        membership_data = membership.as_dict()

        if membership.membership_type:
            membership_type_doc = frappe.get_doc(
                "VM Membership Type", membership.membership_type
            )
            membership_data["type_details"] = membership_type_doc.as_dict()

        result.append(membership_data)
    return result


@frappe.whitelist()
def create_member(name):
    volunteer_details = frappe.get_doc("Employee", name)
    member = frappe.new_doc("VM Member")
    member.member_name = volunteer_details.employee_name
    member.email_id = volunteer_details.personal_email
    member.volunteer = volunteer_details.name
    member.insert(ignore_permissions=True)
    return member.name


@frappe.whitelist()
def membership_certificate_template(membership_type: str) -> str:

    error_message = "Error printing membership certificate"
    if not membership_type:
        frappe.throw(error_message)

    try:
        membership_template = frappe.db.get_value(
            "VM Membership Type",
            {"name": membership_type},
            "template",
            as_dict=True,
        )

        if not membership_template:
            frappe.throw(error_message)
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(), "Membership Certificate Template Error"
        )
        frappe.throw(error_message)

    return membership_template.name


@frappe.whitelist()
def confirm_payment(invoice_name: str) -> str:

    error_message = "Error confirming payment"

    if not invoice_name:
        frappe.throw(_(error_message))

    try:
        invoice = frappe.get_doc("Sales Invoice", invoice_name)

        if invoice.status == "Paid" and invoice.outstanding_amount == 0:
            return "paid"

        return "unpaid"

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Confirm Payment Error")
        frappe.throw(_("Error confirming payment: {0}").format(str(e)))
        frappe.throw(_("Error confirming payment: {0}").format(str(e)))


@frappe.whitelist(allow_guest=True)
def create_membership(
    phone: str,
    amount: float,
    membership_type: str,
    branch: str,
) -> None:

    if not phone or not amount or not membership_type or not branch:
        frappe.throw("All fields are required")

    user = frappe.db.get_value(
        "User", frappe.session.user, ["full_name"], as_dict=1
    ).full_name

    try:
        frappe.db.begin()

        member = frappe.db.exists("VM Member", {"email_id": frappe.session.user})
        if not member:
            member = frappe.get_doc(
                {
                    "doctype": "VM Member",
                    "member_name": user,
                    "email_id": frappe.session.user,
                    "phone_number": phone,
                }
            )
            member.insert(ignore_permissions=True)

        else:
            member = frappe.get_doc("VM Member", member)

        if frappe.db.exists(
            "VM Membership",
            {"member": member.name, "status": "Active", "company": branch},
        ):
            frappe.throw("You already have an active membership for this branch")

        from_date = datetime.today().date()

        membership = frappe.get_doc(
            {
                "doctype": "VM Membership",
                "member": member.name,
                "membership_type": membership_type,
                "amount": amount,
                "company": branch,
                "status": "Draft",
                "from_date": from_date,
                "to_date": add_to_date(from_date, years=1, days=-1),
                "member_since_date": from_date,
            }
        )

        membership.insert(ignore_permissions=True)

        invoice = renew_membership(id=membership.name, phone_number=phone)

        frappe.db.commit()

        return invoice.name

    except Exception:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Error creating membership")
        frappe.throw("Error creating membership")


@frappe.whitelist(allow_guest=True)
def renew_membership(**kwargs):
    try:
        membership = frappe.get_doc("VM Membership", kwargs.get("id"))
        _, invoice = membership.initiate_payment(
            phone_number=kwargs.get("phone_number")
        )

        return invoice
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Error renewing membership")
        frappe.throw("Error creating membership")
        frappe.throw("Error creating membership")
