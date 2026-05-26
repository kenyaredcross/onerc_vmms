# Copyright (c) 2025, Kenya Red Cross Society and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document

from ...api.volunteer import create_volunteer


class VMMember(Document):
    def onload(self):
        """Load address and contacts in `__onload`"""
        load_address_and_contact(self)

    def validate(self):
        if self.email_id:
            self.validate_email_type(self.email_id)

    def validate_email_type(self, email):
        from frappe.utils import validate_email_address

        validate_email_address(email.strip(), True)

    @frappe.whitelist()
    def make_customer_and_link(self):
        if self.customer:
            return

        customer = create_customer(
            frappe._dict(
                {"fullname": self.member_name, "email": self.email_id, "phone": None}
            )
        )

        self.customer = customer
        self.save(ignore_permissions=True)
        frappe.msgprint(
            _("Customer {0} has been created succesfully.").format(self.customer)
        )

    @frappe.whitelist()
    def make_volunteer_and_link(self):
        if self.volunteer:
            frappe.msgprint(_("A volunteer is already linked to this Member"))

        volunteer = create_volunteer(
            frappe._dict(
                {"fullname": self.member_name, "email": self.email_id, "phone": None}
            )
        )

        self.volunteer = volunteer
        self.save(ignore_permissions=True)
        frappe.msgprint(
            _("Volunteer {0} has been created succesfully.").format(self.volunteer)
        )


def get_or_create_member(user_details):
    member_list = frappe.get_all(
        "VM Member",
        filters={"email": user_details.email, "membership_type": user_details.plan_id},
    )
    if member_list and member_list[0]:
        return member_list[0]["name"]
    else:
        return create_member(user_details)


def create_member(user_details):
    user_details = frappe._dict(user_details)
    member = frappe.new_doc("VM Member")
    member.update(
        {
            "member_name": user_details.fullname,
            "email_id": user_details.email,
            "pan_number": user_details.pan or None,
            "membership_type": user_details.plan_id,
            "customer_id": user_details.customer_id or None,
            "subscription_id": user_details.subscription_id or None,
            "subscription_status": user_details.subscription_status or "",
        }
    )

    member.insert(ignore_permissions=True)
    member.customer = create_customer(user_details, member.name)
    member.save(ignore_permissions=True)

    return member


def create_customer(user_details, member=None):
    customer = frappe.new_doc("Customer")
    customer.customer_name = user_details.fullname
    customer.customer_type = "Individual"
    customer.customer_group = frappe.db.get_single_value(
        "Selling Settings", "customer_group"
    )
    customer.territory = frappe.db.get_single_value("Selling Settings", "territory")
    customer.flags.ignore_mandatory = True
    customer.insert(ignore_permissions=True)

    try:
        frappe.db.savepoint("contact_creation")
        contact = frappe.new_doc("Contact")
        contact.first_name = user_details.fullname
        if user_details.mobile:
            contact.add_phone(
                user_details.mobile, is_primary_phone=1, is_primary_mobile_no=1
            )
        if user_details.email:
            contact.add_email(user_details.email, is_primary=1)
        contact.insert(ignore_permissions=True)

        contact.append(
            "links", {"link_doctype": "Customer", "link_name": customer.name}
        )

        if member:
            contact.append("links", {"link_doctype": "VM Member", "link_name": member})

        contact.save(ignore_permissions=True)

    except frappe.DuplicateEntryError:
        return customer.name

    except Exception as e:
        frappe.db.rollback(save_point="contact_creation")
        frappe.log_error(frappe.get_traceback(), _("Contact Creation Failed"))
        pass

    return customer.name
