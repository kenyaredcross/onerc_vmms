# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, get_link_to_form, getdate, pretty_date
from hrms.hr.utils import validate_bulk_tool_fields

from ...utils.utils import get_company_descendants

EMPLOYEE = "Employee"
USER = "User"

EMPLOYEE_FIELDS = (
	"name",
	"company",
	"date_of_joining",
	"department",
	"designation",
	"employment_type",
	"employee",
	"employee_name",
	"status",
	"user_id",
)

EMPLOYEE_FILTERS = (
	("region", "company", "company"),
	("branch", "company", "company"),
	("employment_type", "employment_type", "employment_type"),
	("designation", "designation", "designation"),
)

USER_FILTERS = (
	("county", "county", "county"),
	("sub_county", "sub_county", "sub_county"),
	("ward", "ward", "ward"),
	("administrative_location", "location", "location"),
)


class DeploymentRequestTool(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from hrms.hr.doctype.designation_skill.designation_skill import DesignationSkill
		from lms.lms.doctype.related_courses.related_courses import RelatedCourses

		from onerc_vmms.volunteer_and_member_management.doctype.administrative_location_table.administrative_location_table import (
			AdministrativeLocationTable,
		)
		from onerc_vmms.volunteer_and_member_management.doctype.company_item.company_item import (
			CompanyItem,
		)
		from onerc_vmms.volunteer_and_member_management.doctype.county_table.county_table import (
			CountyTable,
		)
		from onerc_vmms.volunteer_and_member_management.doctype.department_item.department_item import (
			DepartmentItem,
		)
		from onerc_vmms.volunteer_and_member_management.doctype.designation_item.designation_item import (
			DesignationItem,
		)
		from onerc_vmms.volunteer_and_member_management.doctype.employment_type_item.employment_type_item import (
			EmploymentTypeItem,
		)
		from onerc_vmms.volunteer_and_member_management.doctype.notification_channel_item.notification_channel_item import (
			NotificationChannelItem,
		)
		from onerc_vmms.volunteer_and_member_management.doctype.personnel_licence_item.personnel_licence_item import (
			PersonnelLicenceItem,
		)
		from onerc_vmms.volunteer_and_member_management.doctype.sub_county_table.sub_county_table import (
			SubCountyTable,
		)
		from onerc_vmms.volunteer_and_member_management.doctype.ward_table.ward_table import (
			WardTable,
		)

		administrative_location: DF.TableMultiSelect[AdministrativeLocationTable]
		branch: DF.TableMultiSelect[CompanyItem]
		company: DF.Link
		county: DF.TableMultiSelect[CountyTable]
		courses: DF.TableMultiSelect[RelatedCourses]
		department: DF.TableMultiSelect[DepartmentItem]
		designation: DF.TableMultiSelect[DesignationItem]
		email_template: DF.Link | None
		employment_type: DF.TableMultiSelect[EmploymentTypeItem]
		expected_end_date: DF.Datetime
		expected_start_date: DF.Datetime
		filter_criteria: DF.Link | None
		future_deployment: DF.Check
		future_deployment_date: DF.Date | None
		is_future_deployed: DF.Check
		licences: DF.TableMultiSelect[PersonnelLicenceItem]
		location: DF.Link | None
		notes: DF.TextEditor | None
		notification_channels: DF.TableMultiSelect[NotificationChannelItem]
		number_of_volunteers_required: DF.Int
		project: DF.Link
		region: DF.TableMultiSelect[CompanyItem]
		require_contract_before_deployment: DF.Check
		skills: DF.TableMultiSelect[DesignationSkill]
		sub_county: DF.TableMultiSelect[SubCountyTable]
		task: DF.Link | None
		terms_of_reference: DF.Link
		title: DF.Data
		tor_attachment: DF.Attach | None
		tor_url: DF.SmallText | None
		ward: DF.TableMultiSelect[WardTable]

	# end: auto-generated types
	def validate(self):
		self.validate_deployment_dates()
		if self.future_deployment:
			self.validate_future_deployment()

	def validate_deployment_dates(self):
		start_date = getdate(self.expected_start_date)
		end_date = getdate(self.expected_end_date)
		if start_date and end_date:
			if end_date < start_date:
				frappe.throw("Expected end date cannot be before expected start date.")
			elif start_date < getdate():
				frappe.throw("Expected start date cannot be in the past.")

	def validate_future_deployment(self):
		self.validate_future_deployment_date()
		if not self.fetch_eligible_employees():
			frappe.throw(
				"This is a future deployment but no employees match the criteria. Please adjust the criteria"
			)
		frappe.msgprint(
			f"This deployment is marked as a future deployment."
			f"On the specified future deployment date {frappe.bold(self.future_deployment_date)} the system will attempt to deploy personnel matching the criteria."
		)

	def validate_future_deployment_date(self):
		future_date = getdate(self.future_deployment_date)
		if future_date < getdate() or future_date > getdate(self.expected_start_date):
			frappe.throw("Future deployment date cannot be in the past.")

	def validate_fields(self, employees: list):
		mandatory_fields = [
			"project",
			"expected_start_date",
			"expected_end_date",
		]
		validate_bulk_tool_fields(
			self,
			mandatory_fields,
			employees,
			"expected_start_date",
			"expected_end_date",
		)

		number_of_volunteers_required = int(self.number_of_volunteers_required or 0)
		assigned_count = frappe.db.count(
			"Personnel Deployment Request",
			{"deployment": self.name, "deployment_status": "Accepted"},
		)
		if assigned_count >= number_of_volunteers_required:
			frappe.throw(
				f"Cannot deploy personnel. The number of personnel required ({number_of_volunteers_required}) has already been met."
			)

	@frappe.whitelist()
	def deploy_employees(self, employees: list):
		self.validate_fields(employees)
		return self.create_deployment_assignments(employees)

	def create_deployment_assignments(self, employees: list) -> dict:
		failure = []
		success = []
		savepoint = "before_deployment_creation"

		for employee in employees:
			try:
				existing = frappe.get_all(
					"Personnel Deployment Request",
					filters={
						"employee": employee,
						"deployment": self.name,
						"deployment_status": ["in", ["Pending", "Accepted"]],
					},
					fields=["name", "deployment_status"],
				)

				if existing:
					failure.append(
						{
							"employee": employee,
							"reason": f"Existing {existing[0].deployment_status} assignment (<a href='{frappe.utils.get_url_to_form('Personnel Deployment Request', existing[0].name)}' target='_blank'>{existing[0].name}</a>) found.",
						}
					)
					continue

				frappe.db.savepoint(savepoint)
				assignment = frappe.new_doc("Personnel Deployment Request")

				fields_to_copy = {
					"project": self.project,
					"task": self.task,
					"location": self.location,
					"company": self.company,
					"expected_start_date": self.expected_start_date,
					"expected_end_date": self.expected_end_date,
					"notes": self.notes,
					"require_contract_before_deployment": self.require_contract_before_deployment,
					"terms_of_reference": self.terms_of_reference,
					"tor_url": self.tor_url,
				}

				if self.get("deployment_request_term_template"):
					fields_to_copy["deployment_request_term_template"] = self.deployment_request_term_template

				assignment.employee = employee
				assignment.deployment = self.name
				assignment.status = "Pending"

				for field, value in fields_to_copy.items():
					assignment.set(field, value)

				assignment.insert()

				success.append(
					{
						"doc": get_link_to_form("Personnel Deployment Request", assignment.name),
						"employee": employee,
					}
				)

			except Exception as e:
				frappe.db.rollback(save_point=savepoint)
				frappe.log_error(
					f"Personnel Deployment Request failed for employee {employee}.",
					str(e),
				)
				failure.append({"employee": employee, "reason": str(e)})

		return {"success": success, "failure": failure}

	@frappe.whitelist()
	def fetch_eligible_employees(self) -> list[dict]:
		employees = self.fetch_employees()
		if not employees:
			return []

		allowed_users = self.get_allowed_user_ids()
		if allowed_users is not None:
			employees = [emp for emp in employees if emp.user_id in allowed_users]

		skilled_employees = self.get_employees_with_skills()
		if skilled_employees is not None:
			employees = [emp for emp in employees if emp.name in skilled_employees]

		return employees

	def get_filter_values(self, table_field: str, row_field: str) -> list[str]:
		return [value for row in (self.get(table_field) or []) if (value := row.get(row_field))]

	def fetch_employees(self) -> list[dict]:
		filters = [[EMPLOYEE, "status", "=", "Active"]]

		for table_field, row_field, employee_field in EMPLOYEE_FILTERS:
			values = self.get_filter_values(table_field, row_field)
			if values:
				filters.append([EMPLOYEE, employee_field, "in", values])

		return frappe.get_list(
			EMPLOYEE,
			filters=filters,
			fields=list(EMPLOYEE_FIELDS),
			limit_page_length=0,
		)

	def get_allowed_user_ids(self) -> set[str] | None:
		allowed = None

		user_filters = [
			[USER, user_field, "in", values]
			for table_field, row_field, user_field in USER_FILTERS
			if (values := self.get_filter_values(table_field, row_field))
		]
		if user_filters:
			allowed = set(frappe.get_list(USER, filters=user_filters, pluck="name", limit_page_length=0))

		courses = self.get_filter_values("courses", "course")
		if courses:
			enrolled = set(
				frappe.get_list(
					"LMS Enrollment",
					filters={"course": ["in", courses]},
					pluck="member",
					limit_page_length=0,
				)
			)
			allowed = enrolled if allowed is None else allowed & enrolled

		licences = self.get_filter_values("licences", "licence")
		if licences:
			holders = set(
				frappe.get_all(
					"Personnel Licence",
					filters={"license_type": ["in", licences], "parenttype": USER},
					pluck="parent",
				)
			)
			allowed = holders if allowed is None else allowed & holders

		return allowed

	def get_employees_with_skills(self) -> set[str] | None:
		skills = self.get_filter_values("skills", "skill")
		if not skills:
			return None

		skill_maps = frappe.get_all(
			"Employee Skill",
			filters={"skill": ["in", skills], "parenttype": "Employee Skill Map"},
			pluck="parent",
		)
		if not skill_maps:
			return set()

		return set(
			frappe.get_all(
				"Employee Skill Map",
				filters={"name": ["in", skill_maps]},
				pluck="employee",
			)
		)


def deploy_future_requests() -> None:
	deployments = frappe.get_all(
		"Deployment Request Tool",
		filters={
			"future_deployment": 1,
			"future_deployment_date": getdate(),
			"is_future_deployed": 0,
		},
		pluck="name",
	)

	if not deployments:
		return

	for deployment in deployments:
		try:
			doc: DeploymentRequestTool = frappe.get_doc("Deployment Request Tool", deployment)

			employees = doc.fetch_eligible_employees()
			if not employees:
				return

			doc.deploy_employees(employees)
		except Exception:
			frappe.log_error(
				f"Error processing future deployment request: {deployment}",
				frappe.get_traceback(),
			)
		else:
			doc.db_set("is_future_deployed", 1, update_modified=False)


# def filter_by_availability(self, employees: list, expected_start_date, expected_end_date) -> list:
#     if not employees:
#         return []

#     expected_start_date = frappe.utils.getdate(expected_start_date)
#     expected_end_date = frappe.utils.getdate(expected_end_date)
#     final_employees = []

#     for emp in employees:
#         emp_name = emp.get("name")

#         pas = frappe.get_all(
#             "Personnel Availability Schedule",
#             filters={"employee": emp_name},
#             fields=["name", "start_date", "end_date"],
#         )

#         if not pas:
#             final_employees.append(emp)
#             continue

#         available = False

#         for sched in pas:
#             sched_start = frappe.utils.getdate(sched.start_date)
#             sched_end = frappe.utils.getdate(sched.end_date)

#             if sched_end < expected_start_date or sched_start > expected_end_date:
#                 continue

#             schedule_rows = frappe.get_all(
#                 "Schedule",
#                 filters={
#                     "parent": sched.name,
#                     "parenttype": "Personnel Availability Schedule",
#                 },
#                 fields=["day", "shift_type"],
#             )

#             for row in schedule_rows:
#                 day = (row.get("day") or "").lower()
#                 shift_type = row.get("shift_type")

#                 if not shift_type:
#                     continue

#                 shift = frappe.get_value(
#                     "Shift Type",
#                     shift_type,
#                     ["start_time", "end_time"],
#                     as_dict=True,
#                 )
#                 if not shift:
#                     continue

#                 current_day = expected_start_date
#                 while current_day <= expected_end_date:
#                     if current_day.strftime("%A").lower() == day:
#                         available = True
#                         break
#                     current_day += timedelta(days=1)

#                 if available:
#                     break

#             if available:
#                 break

#         if available:
#             final_employees.append(emp)

#     return final_employees
