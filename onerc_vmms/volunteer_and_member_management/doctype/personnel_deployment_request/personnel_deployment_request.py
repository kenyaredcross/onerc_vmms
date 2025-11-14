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
        self.validate_assignment_limit()

    def validate(self):
        self.validate_assignment_limit()

    def on_submit(self):
        if (
            self.project
            and self.user
            and not frappe.db.exists(
                "User Permission",
                {"user": self.user, "allow": "Project", "for_value": self.project},
            )
        ):
            frappe.permissions.add_user_permission("Project", self.project, self.user)

    def on_cancel(self):
        if (
            self.project
            and self.user
            and frappe.db.exists(
                "User Permission",
                {"user": self.user, "allow": "Project", "for_value": self.project},
            )
        ):
            frappe.permissions.remove_user_permission(
                "Project", self.project, self.user
            )

    def validate_assignment_limit(self):
        """Ensure that the number of accepted assignments does not exceed the number required"""
        if self.deployment_status == "Accepted" and (
            not self.get_doc_before_save()
            or self.get_doc_before_save().deployment_status != "Accepted"
        ):
            deployment_request = frappe.get_doc(
                "Deployment Request Tool", self.deployment
            )
            number_of_volunteers_required = int(
                deployment_request.number_of_volunteers_required or 0
            )
            assigned_count = frappe.db.count(
                "Personnel Deployment Request",
                {"deployment": self.deployment, "deployment_status": "Accepted"},
            )
            if assigned_count > number_of_volunteers_required - 1:
                frappe.throw(
                    f"Cannot accept this assignment. The number of personnel required ({number_of_volunteers_required}) has already been met."
                )
