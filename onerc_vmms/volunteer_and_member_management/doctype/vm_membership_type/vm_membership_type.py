# Copyright (c) 2025, Kenya Red Cross Society and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class VMMembershipType(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from onerc_vmms.vm_payments.doctype.vm_payment_gateway.vm_payment_gateway import VMPaymentGateway
        from onerc_vmms.volunteer_and_member_management.doctype.membership_benefit.membership_benefit import MembershipBenefit

        amount: DF.Float
        benefits: DF.Table[MembershipBenefit]
        billing_cycle: DF.Literal["", "Monthly", "Yearly", "One Off"]
        currency: DF.Link | None
        linked_item: DF.Link | None
        lower_age_limit: DF.Int
        membership_package: DF.Link | None
        membership_type: DF.Data
        payment_gateways: DF.Table[VMPaymentGateway]
        requires_age_requirement: DF.Check
        template: DF.Link | None
        upper_age_limit: DF.Int
    # end: auto-generated types

    def validate(self):
        self.created_linked_item()
        if self.linked_item:
            is_stock_item = frappe.db.get_value(
                "Item", self.linked_item, "is_stock_item"
            )
            if is_stock_item:
                frappe.throw(_("The Linked Item should be a service item"))

    def created_linked_item(self):
        if not self.linked_item:
            item = frappe.db.exists("Item", "Membership")

            if item:
                item = frappe.get_doc("Item", "Membership")

            else:
                item = frappe.get_doc(
                    {
                        "doctype": "Item",
                        "item_name": "Membership",
                        "item_code": "Membership",
                        "is_stock_item": 0,
                        "item_group": "Services",
                        "stock_uom": "Nos",
                    }
                )

                item.insert(ignore_permissions=True)

            self.linked_item = item.name
