from datetime import datetime

import frappe
from frappe import _
from frappe.utils import add_to_date, get_fullname
from ...volunteer_and_member_management.utils import log_throw_error

from onerc_vmms.volunteer_and_member_management.doctype.vm_membership.vm_membership import (
    VMMembership,
)
from ..api.user import get_user_details
from frappe.model.document import Document
from ..utils import log_throw_error


@frappe.whitelist(allow_guest=True)
def get_membership_types():
    memberships = frappe.get_all(
        "VM Membership Type",
        fields=["name", "membership_type", "amount"],
        order_by="amount asc",
    )
    for membership in memberships:
        membership_doc = frappe.get_doc(
            "VM Membership Type", membership, fields=["benefits"]
        )
        membership.update(membership_doc.as_dict())

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
        fields=["name", "membership_type", "company", "status"],
        order_by="from_date desc",
    )

    if not memberships:
        return []

    membership_groups = {}
    for membership_item in memberships:
        key = (membership_item.membership_type, membership_item.company)
        if key not in membership_groups:
            membership_groups[key] = []
        membership_groups[key].append(membership_item)

    filtered_memberships = []
    for key, group in membership_groups.items():
        statuses = [m.status for m in group]

        if "Active" in statuses or "Pending" in statuses:
            filtered_memberships.extend([m for m in group if m.status != "Expired"])
        else:
            filtered_memberships.extend(group)

    result = []
    for membership_item in filtered_memberships:
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


@frappe.whitelist()
def initiate_membership_registration(
    amount: float, membership_type: str, branch: str, payment_gateway: str
) -> str:

    membership = create_membership(amount, membership_type, branch)

    payment_link = get_payment_link(membership, payment_gateway)

    return payment_link


@frappe.whitelist(allow_guest=True)
def create_membership(
    amount: float,
    membership_type: str,
    branch: str,
) -> VMMembership:

    if not frappe.db.exists("VM Membership Type", membership_type):
        frappe.throw(_("The specified membership type does not exist"))

    membership_type_doc = frappe.get_cached_doc("VM Membership Type", membership_type)

    validate_membership_age_eligibility(membership_type_doc)

    try:

        member = frappe.db.exists("VM Member", {"email_id": frappe.session.user})
        if not member:
            member = create_member()

        else:
            member = frappe.get_doc("VM Member", member)

        check_conflicting_memberships(member, branch)

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
        return membership

    except Exception:
        log_throw_error("Error creating membership")


def validate_membership_age_eligibility(membership_type_doc: Document) -> None:
    age = get_user_details().get("age", 0)

    if membership_type_doc.requires_age_requirement:
        if (
            age < membership_type_doc.lower_age_limit
            or age > membership_type_doc.upper_age_limit
        ):
            if membership_type_doc.lower_age_limit == 0:
                frappe.throw(
                    _(
                        "You must be under {0} years to apply for this membership"
                    ).format(membership_type_doc.upper_age_limit)
                )
            elif membership_type_doc.lower_age_limit == 30:
                frappe.throw(
                    _("You must be 30 years or older to apply for this membership")
                )
            else:
                frappe.throw(
                    _(
                        "Your age does not meet the requirements for this membership type. It should be between {0} and {1} years.".format(
                            membership_type_doc.lower_age_limit,
                            membership_type_doc.upper_age_limit,
                        )
                    )
                )


def create_member() -> "Document":

    member = frappe.get_doc(
        {
            "doctype": "VM Member",
            "member_name": get_fullname(),
            "email_id": frappe.session.user,
        }
    )
    member.insert(ignore_permissions=True)

    return member


def check_conflicting_memberships(member_doc: "Document", company: str) -> None:
    membership = frappe.db.get_value(
        "VM Membership",
        {
            "member": member_doc.name,
            "company": company,
            "status": ["in", ["Active", "Pending"]],
        },
        "status",
    )

    if membership == "Active":
        frappe.throw(_("You already have an active membership for this branch."))
    elif membership == "Pending":
        frappe.throw(
            _(
                "You have a pending membership for this branch. Please complete the payment."
            )
        )


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
        frappe.throw("Error renewing membership")


@frappe.whitelist()
def validate_membership_eligibility():

    user_info = get_user_details()

    missing_fields = []
    required_fields = [
        "full_name",
        "phone",
        "id_number",
        "county",
        "sub_county",
        "birth_date",
        "gender",
        "citizenship",
        "identification_type",
    ]

    def convert_missing_fields(field_name):
        return field_name.replace("_", " ").title()

    for field in required_fields:
        if not user_info.get(field):
            missing_fields.append(convert_missing_fields(field))
    if missing_fields:
        return {
            "eligible": False,
            "missing_fields": missing_fields,
        }

    return {
        "eligible": True,
        "missing_fields": [],
    }


@frappe.whitelist()
def get_membership_type_pgws(membership_type: str) -> list[str]:
    from ...volunteer_and_member_management.doctype.vm_membership_type.vm_membership_type import (
        VMMembershipType,
    )

    if not frappe.db.exists("VM Membership Type", membership_type):
        frappe.throw(_("The specified membership type does not exist"))

    try:
        pgw: VMMembershipType = frappe.get_cached_doc(
            "VM Membership Type",
            membership_type,
        )
        if not pgw.payment_gateways:
            frappe.log_error(
                f"No payment gateways configured for membership type: {membership_type}",
                "Membership Type Payment Gateway Error",
            )
            frappe.throw(_("This membership type cannot be paid for at the moment"))

        result = [gateway.gateway for gateway in pgw.payment_gateways]

        return result

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Error fetching payment gateways for membership type",
        )
        frappe.throw(_("Error fetching payment gateways for membership type"))


def get_payment_link(membership_doc: "VMMembership", payment_gateway: str) -> str:
    from erpnext.accounts.doctype.payment_request.payment_request import (
        _get_payment_gateway_controller,
    )

    data = {
        "payment_gateway": payment_gateway,
        "reference_doctype": "VM Membership",
        "reference_docname": membership_doc.name,
        "title": "Membership Payment",
        "transaction_description": f"Payment for {membership_doc.membership_type} membership",
        "redirect_to": "/vmms/membership",
        "amount": membership_doc.amount,
    }
    if not frappe.db.exists("Payment Gateway", payment_gateway):
        log_throw_error("The specified payment gateway does not exist")

    try:

        gateway_controller = _get_payment_gateway_controller(payment_gateway)
    except Exception:
        log_throw_error("Error fetching payment gateway controller")
    else:

        if not hasattr(gateway_controller, "get_payment_url"):
            frappe.throw(
                _("The selected payment gateway does not support payment links")
            )

        payment_url = gateway_controller.get_payment_url(**data)

        if not payment_url:
            log_throw_error("Error generating payment URL")
        return payment_url


@frappe.whitelist()
def get_pgw_for_company(company: str) -> bool:
    if not frappe.db.exists("Payment Gateway Account", {"company": company}):
        frappe.throw(
            _(
                "Payment cannot be processed for this branch at the moment. Please contact support."
            )
        )
    return True
