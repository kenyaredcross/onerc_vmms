# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Count
from frappe.utils import today

from onerc_vmms.volunteer_and_member_management.doctype.deployment_request_tool.deployment_request_tool import (
	DeploymentRequestTool,
)


class PersonnelDeploymentRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		date: DF.Date | None
		deployment: DF.Link | None
		deployment_status: DF.Literal["Pending", "Accepted", "Rejected", "Cancelled"]
		employee: DF.Link
		employee_name: DF.Data | None
		expected_end_date: DF.Datetime | None
		expected_start_date: DF.Datetime
		location: DF.Link | None
		notes: DF.TextEditor | None
		project: DF.Link
		task: DF.Link | None
		terms_of_reference: DF.Link
		tor_url: DF.SmallText | None
		user: DF.Link | None

	# end: auto-generated types
	@property
	def get_linked_deployment(self) -> DeploymentRequestTool:
		return frappe.get_cached_doc("Deployment Request Tool", self.deployment)

	def before_save(self):
		if not self.date:
			self.date = today()

	def before_update_after_submit(self):
		self.validate_assignment_limit()

	def validate(self):
		self.validate_assignment_limit()

	def after_insert(self):
		self.send_email_notification()
		self.send_sms_notification()

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

		if self.project and self.user:
			project_doc = frappe.get_doc("Project", self.project)
			exists = any(row.user == self.user for row in project_doc.users)
			if not exists:
				project_doc.append("users", {"user": self.user})
				project_doc.save(ignore_permissions=True)

	def on_cancel(self):
		if (
			self.project
			and self.user
			and frappe.db.exists(
				"User Permission",
				{"user": self.user, "allow": "Project", "for_value": self.project},
			)
		):
			frappe.permissions.remove_user_permission("Project", self.project, self.user)

		if self.project and self.user:
			project_doc = frappe.get_doc("Project", self.project)
			updated_rows = [row for row in project_doc.users if row.user != self.user]
			if len(updated_rows) != len(project_doc.users):
				project_doc.set("users", updated_rows)
				project_doc.save(ignore_permissions=True)

	def validate_assignment_limit(self):
		"""Ensure that the number of accepted assignments does not exceed the number required"""
		if self.deployment_status == "Accepted" and (
			not self.get_doc_before_save() or self.get_doc_before_save().deployment_status != "Accepted"
		):
			if not self.deployment:
				return

			frappe.db.get_value("Deployment Request Tool", self.deployment, "name", for_update=True)

			deployment_request = frappe.get_doc("Deployment Request Tool", self.deployment)
			number_of_volunteers_required = int(deployment_request.number_of_volunteers_required or 0)

			pdr = frappe.qb.DocType("Personnel Deployment Request")
			assigned_count = (
				frappe.qb.from_(pdr)
				.select(Count(pdr.name))
				.where(pdr.deployment == self.deployment)
				.where(pdr.deployment_status == "Accepted")
				.where(pdr.name != self.name)
				.for_update()
				.run()
			)[0][0]

			if assigned_count > number_of_volunteers_required - 1:
				frappe.throw(
					f"Cannot accept this assignment. The number of personnel required ({number_of_volunteers_required}) has already been met."
				)

	def send_email_notification(self) -> None:
		try:
			deployment_doc = self.get_linked_deployment

			subject = "New Deployment Request"
			args = {"doc": self}

			if deployment_doc.email_template:
				from frappe.email.doctype.email_template.email_template import (
					get_email_template,
				)

				email_template = get_email_template(deployment_doc.email_template, args)
				subject = email_template.get("subject")
				content = email_template.get("message")

		except Exception:
			frappe.log_error(
				message=frappe.get_traceback(),
				title=f"An error occurred while preparing email notification for PDR {self.name}",
			)
		else:
			frappe.sendmail(
				recipients=self.user,
				subject=subject,
				content=content if deployment_doc.email_template else None,
				template=("deployment_email" if not deployment_doc.email_template else None),
				args=args,
				reference_doctype=self.doctype,
				reference_name=self.name,
			)

	def send_sms_notification(self) -> None:
		try:
			deployment_doc = self.get_linked_deployment
			sms = ("SMS", "sms")

			if any(row.notification_channel in sms for row in deployment_doc.notification_channels):
				from frappe.core.doctype.sms_settings.sms_settings import send_sms
				from frappe.utils import get_url

				url = get_url("/vmms/assignment/" + self.name)

				message = f"""Hello, you have received a new deployment request. View details: {url}"""
				mobile_contact: dict = frappe.db.get_value(
					"User", self.user, ["phone", "mobile_no"], as_dict=True
				)
				send_sms(
					receiver_list=[mobile_contact.get("phone") or mobile_contact.get("mobile_no")],
					msg=message,
				)
		except Exception:
			frappe.log_error(
				message=frappe.get_traceback(),
				title=f"SMS Notification Error for Personnel Deployment Request {self.name}",
			)
