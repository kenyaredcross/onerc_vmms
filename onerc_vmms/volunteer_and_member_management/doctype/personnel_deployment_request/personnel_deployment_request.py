# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today


class PersonnelDeploymentRequest(Document):
    def before_save(self):
        if not self.date:
            self.date = today()

    def before_update_after_submit(self):
        self.number_of_volunteers_required()

    def validate(self):
        self.number_of_volunteers_required()

    def number_of_volunteers_required(self):
        """Ensure that the number of accepted assignments does not exceed the number required"""
        if self.status == "Accepted" and (
            not self.get_doc_before_save()
            or self.get_doc_before_save().status != "Accepted"
        ):
            deployment_request = frappe.get_doc(
                "Deployment Request Tool", self.deployment
            )
            number_of_volunteers_required = int(
                deployment_request.number_of_volunteers_required or 0
            )
            assigned_count = frappe.db.count(
                "Personnel Deployment Request",
                {"deployment": self.deployment, "docstatus": 1, "status": "Accepted"},
            )
            if assigned_count > number_of_volunteers_required - 1:
                frappe.throw(
                    f"Cannot accept this assignment. The number of personnel required ({number_of_volunteers_required}) has already been met."
                )
