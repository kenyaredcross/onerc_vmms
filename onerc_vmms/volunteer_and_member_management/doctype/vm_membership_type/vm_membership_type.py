# Copyright (c) 2025, Kenya Red Cross Society and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class VMMembershipType(Document):

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
