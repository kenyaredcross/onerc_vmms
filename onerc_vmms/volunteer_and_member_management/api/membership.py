import frappe


@frappe.whitelist(allow_guest=True)
def get_membership_types():
    memberships = frappe.get_all(
        "Membership Type",
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
        "Member",
        {"email_id": frappe.session.user},
        ["name"],
        as_dict=True,
    )

    if not member:
        return []

    memberships = frappe.get_all(
        "Membership",
        filters={"member": member.name},
        fields=[
            "name",
        ],
        order_by="from_date desc",
    )

    if not memberships:
        return []

    result = []
    for membership_item in memberships:
        membership = frappe.get_doc("Membership", membership_item.name)
        membership_data = membership.as_dict()

        if membership.membership_type:
            membership_type_doc = frappe.get_doc(
                "Membership Type", membership.membership_type
            )
            membership_data["type_details"] = membership_type_doc.as_dict()

        result.append(membership_data)
    return result


@frappe.whitelist()
def create_member(name):
    volunteer_details = frappe.get_doc("Employee", name)
    member = frappe.new_doc("Member")
    member.member_name = volunteer_details.employee_name
    member.email_id = volunteer_details.personal_email
    member.volunteer = volunteer_details.name
    member.insert(ignore_permissions=True)
    return member.name
