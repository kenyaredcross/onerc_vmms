# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from datetime import timedelta
from urllib.parse import quote

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, get_link_to_form, getdate, pretty_date
from hrms.hr.utils import validate_bulk_tool_fields
from pypika import Criterion

from ...utils import get_company_descendants


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
		from onerc_vmms.volunteer_and_member_management.doctype.company_item.company_item import CompanyItem
		from onerc_vmms.volunteer_and_member_management.doctype.county_table.county_table import CountyTable
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
		from onerc_vmms.volunteer_and_member_management.doctype.ward_table.ward_table import WardTable

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
		terms_of_reference: DF.Link | None
		title: DF.Data
		tor_attachment: DF.Attach | None
		tor_url: DF.SmallText | None
		ward: DF.TableMultiSelect[WardTable]

	# end: auto-generated types
	def validate(self):
		self.validate_deployment_dates()
		if self.future_deployment:
			self.validate_future_deployment()
		if not self.terms_of_reference and not self.tor_attachment:
			frappe.throw("Please provide either Terms of Reference or TOR Attachment.")
		else:
			if self.tor_attachment:
				self.tor_url = (
					frappe.utils.get_url(self.tor_attachment)
					if self.tor_attachment.startswith("/")
					else self.tor_attachment
				)
			else:
				base_url = frappe.utils.get_url()

				self.tor_url = (
					f"{base_url}/api/method/"
					f"onerc_vmms.volunteer_and_member_management.utils.download_pdf"
					f"?doctype=Personnel%20Terms%20of%20Reference"
					f"&name={quote(self.terms_of_reference)}"
				)

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
		if not self._get_employees():
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
					"tor_attachment": self.tor_attachment,
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
	def _get_employees(self) -> list[dict]:
		query = self.build_employee_query()

		result = query.run(as_dict=True)
		return result

	def filters_registry(self) -> list[dict[str, str] | str]:
		filters = [
			{"region": "company"},
			{"branch": "company"},
			"employment_type",
			"designation",
			"county",
			"sub_county",
			"ward",
			{"administrative_location": "location"},
			{"courses": "course"},
			{"skills": "skill"},
			{"licences": "licence"},
		]

		return filters

	def build_filters(self) -> list[dict]:
		result = []

		try:
			for filter_field in self.filters_registry():
				if isinstance(filter_field, dict):
					for self_field, doctype_field in filter_field.items():
						dict_values = getattr(self, self_field, None)
						if dict_values:
							result.append({self_field: [getattr(val, doctype_field) for val in dict_values]})
				else:
					str_values = getattr(self, filter_field, None)
					if str_values:
						result.append({filter_field: [getattr(val, filter_field) for val in str_values]})
		except Exception:
			frappe.log_error(
				"Error building filters for Deployment Request Tool",
				frappe.get_traceback(),
			)
			frappe.throw("An error occurred while building filters.")
		else:
			return result

	def match_filters_to_doctype(self) -> list[dict]:
		result = [
			{
				"Employee": [
					"region",
					"branch",
					"employment_type",
					"designation",
				]
			},
			{
				"User": [
					"county",
					"sub_county",
					"ward",
					"administrative_location",
				]
			},
			{"LMS Enrollment": ["courses"]},
			{"Employee Skill": ["skills"]},
			{"Personnel Licence": ["licences"]},
		]

		return result

	def build_employee_query(self):
		from frappe.query_builder import DocType

		employee = DocType("Employee")
		user = DocType("User")
		lms_enrollment = DocType("LMS Enrollment")
		emp_skill_map = DocType("Employee Skill Map")
		emp_skill = DocType("Employee Skill")
		emp_licence = DocType("Personnel Licence")

		doctype_criteria = set()
		for val in self.match_filters_to_doctype():
			for doctype, fields in val.items():
				if any(getattr(self, field, None) for field in fields):
					doctype_criteria.add(doctype)

		query = (
			frappe.qb.from_(employee)
			.select(
				employee.name,
				employee.company,
				employee.date_of_joining,
				employee.department,
				employee.designation,
				employee.employment_type,
				employee.employee,
				employee.employee_name,
				employee.status,
				employee.user_id,
			)
			.distinct()
		)

		if "User" in doctype_criteria:
			query = query.join(user).on(employee.user_id == user.name)

		if "LMS Enrollment" in doctype_criteria:
			if "User" not in doctype_criteria:
				query = query.join(user).on(employee.user_id == user.name)
			query = query.join(lms_enrollment).on(lms_enrollment.member == user.name)

		if "Employee Skill" in doctype_criteria:
			query = (
				query.join(emp_skill_map)
				.on(emp_skill_map.employee == employee.name)
				.join(emp_skill)
				.on(emp_skill.parent == emp_skill_map.name)
			)

		if "Personnel Licence" in doctype_criteria:
			if "User" not in doctype_criteria and "LMS Enrollment" not in doctype_criteria:
				query = query.join(user).on(employee.user_id == user.name)
			query = query.join(emp_licence).on(emp_licence.parent == user.name)

		field_to_table = {
			"region": employee.company,
			"branch": employee.company,
			"employment_type": employee.employment_type,
			"designation": employee.designation,
			"county": user.county,
			"sub_county": user.sub_county,
			"ward": user.ward,
			"administrative_location": user.location,
			"courses": lms_enrollment.course,
			"skills": emp_skill.skill,
			"licences": emp_licence.license_type,
		}

		query = query.where(employee.status == "Active")

		conditions = self.build_condition_list(field_to_table)
		if conditions:
			query = query.where(Criterion.all(conditions))

		return query

	def build_condition_list(self, field_to_table_map: dict) -> list[Criterion]:
		conditions = []

		try:
			filters = self.build_filters()
			if not filters:
				return conditions

			for filter_dict in filters:
				for field, values in filter_dict.items():
					table_field = field_to_table_map.get(field)
					if table_field and values:
						conditions.append(table_field.isin(values))
		except Exception:
			frappe.log_error(
				"Error building condition list for Deployment Request Tool",
				frappe.get_traceback(),
			)
			frappe.throw("An error occurred while building condition list.")

		else:
			return conditions


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

			employees = doc._get_employees()
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
