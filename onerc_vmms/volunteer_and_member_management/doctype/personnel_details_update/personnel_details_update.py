# Copyright (c) 2025, Frappe and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PersonnelDetailsUpdate(Document):
    def on_submit(self):
        if not self.employee:
            frappe.throw(_("Please select an Employee to update"))

        employee = frappe.get_doc("Employee", self.employee)
        transfer_details = []

        for detail in self.update_details:
            fieldname = detail.fieldname
            new_value = detail.new
            current_value = detail.current

            if not fieldname:
                continue

            field_meta = frappe.get_meta("Employee").get_field(fieldname)
            if field_meta and field_meta.fieldtype == "Table":
                self.apply_child_table_change(employee, field_meta, detail)
            else:
                employee.set(fieldname, new_value)

            if str(new_value) != str(current_value):
                transfer_details.append(
                    {
                        "fieldname": fieldname,
                        "property": detail.property,
                        "current": current_value,
                        "new": new_value,
                    }
                )

        employee.save()

    def apply_child_table_change(self, employee, field_meta, detail):
        try:
            change = frappe.parse_json(detail.new)
        except Exception:
            frappe.throw(_("Invalid data format for child table update"))

        action = change.get("action")
        row_data = change.get("row_data")

        if action == "Add Row":
            employee.append(field_meta.fieldname, row_data or {})
        elif action == "Update Row":
            if not row_data or not row_data.get("name"):
                frappe.throw(_("Row 'name' is required for updating child table"))
            row = employee.get_one(field_meta.fieldname, {"name": row_data["name"]})
            if not row:
                frappe.throw(_("Row not found in {0}").format(field_meta.label))
            row.update(row_data)
        elif action == "Delete Row":
            if not row_data or not row_data.get("name"):
                frappe.throw(_("Row 'name' is required for deleting child table"))
            employee.set(
                field_meta.fieldname,
                [
                    r
                    for r in employee.get(field_meta.fieldname)
                    if r.name != row_data["name"]
                ],
            )
