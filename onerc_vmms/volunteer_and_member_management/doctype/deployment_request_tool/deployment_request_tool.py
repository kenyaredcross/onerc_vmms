# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import get_link_to_form
from hrms.hr.utils import validate_bulk_tool_fields

from ...utils import get_company_descendants


class DeploymentRequestTool(Document):
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
            {"deployment": self.name, "docstatus": 1, "status": "Accepted"},
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
                        "status": ["in", ["Pending", "Accepted"]],
                        "docstatus": 1,
                    },
                    fields=["name", "status"],
                )

                if existing:
                    failure.append(
                        {
                            "employee": employee,
                            "reason": f"Existing {existing[0].status} assignment (<a href='{frappe.utils.get_url_to_form('Personnel Deployment Request', existing[0].name)}' target='_blank'>{existing[0].name}</a>) found.",
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
                    fields_to_copy["deployment_request_term_template"] = (
                        self.deployment_request_term_template
                    )

                assignment.employee = employee
                assignment.deployment = self.name
                assignment.status = "Pending"

                for field, value in fields_to_copy.items():
                    assignment.set(field, value)

                assignment.insert()
                assignment.submit()

                success.append(
                    {
                        "doc": get_link_to_form(
                            "Personnel Deployment Request", assignment.name
                        ),
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
    def get_employees(self, advanced_filters: list = None) -> list:
        if advanced_filters is None:
            advanced_filters = []

        base_filters = self.get_base_filters()
        all_filters = base_filters + advanced_filters

        employees = frappe.get_list(
            "Employee",
            filters=all_filters,
            fields=[
                "name",
                "employee",
                "employee_name",
                "company",
                "department",
                "designation",
                "employment_type",
                "date_of_joining",
                "status",
                "user_id",
            ],
        )

        filtered_employees = self.apply_multiselect_filters(employees)

        return filtered_employees

    def get_base_filters(self):
        filters = [["status", "=", "Active"]]

        return filters

    def _extract_multiselect_values(
        self, table_field: str, field_to_extract: str
    ) -> list:
        rows = self.get(table_field) or []
        vals = []
        for row in rows:
            val = None
            if isinstance(row, dict):
                val = row.get(field_to_extract)
            else:
                val = getattr(row, field_to_extract, None)

            if val:
                s = str(val).strip()
                if s:
                    vals.append(s)

        return list(dict.fromkeys(vals))

    def _get_location_filters(self) -> dict:
        return {
            "county": self._extract_multiselect_values("county", "county"),
            "sub_county": self._extract_multiselect_values("sub_county", "sub_county"),
            "administrative_location": self._extract_multiselect_values(
                "administrative_location", "location"
            ),
            "ward": self._extract_multiselect_values("ward", "ward"),
        }

    def _get_course_filters(self) -> list:
        return self._extract_multiselect_values("courses", "course")

    def _get_skill_filters(self) -> list:
        return self._extract_multiselect_values("skills", "skill")

    def _get_licence_filters(self) -> list:
        return self._extract_multiselect_values("licences", "licence")

    def _get_user_location_data(self, user_ids: list) -> dict:
        if not user_ids:
            return {}

        users_data = frappe.get_all(
            "User",
            filters={"name": ["in", user_ids]},
            fields=[
                "name",
                "county",
                "sub_county",
                "ward",
                "administrative_location",
            ],
            as_list=False,
        )

        return {user["name"]: user for user in users_data}

    def _get_user_licence_data(self, user_ids: list) -> dict:
        if not user_ids:
            return {}

        licences = frappe.get_all(
            "Personnel Licence",
            filters={"parent": ["in", user_ids], "parenttype": "User"},
            fields=["license_type", "parent"],
            as_list=False,
        )

        user_licences = {}
        for row in licences:
            user_licences.setdefault(row.parent, set()).add(row.license_type)

        return user_licences

    def _get_user_courses_data(self, user_ids: list) -> dict:
        if not user_ids:
            return {}

        enrollments = frappe.get_all(
            "LMS Enrollment",
            filters={"member": ["in", user_ids]},
            fields=["member", "course"],
            as_list=False,
        )

        user_courses = {}
        for row in enrollments:
            user_courses.setdefault(row.member, set()).add(row.course)

        return user_courses

    def _get_employee_skills_data(self, employees: list) -> dict:
        employee_map = {emp.employee: emp.user_id for emp in employees if emp.user_id}
        employee_names = list(employee_map.keys())

        if not employee_names:
            return {}

        skill_map_parents = frappe.get_all(
            "Employee Skill Map",
            filters={"employee": ["in", employee_names]},
            pluck="name",
        )

        if not skill_map_parents:
            return {}

        skill_details = frappe.get_all(
            "Employee Skill",
            filters={"parent": ["in", skill_map_parents]},
            fields=["parent", "skill"],
            as_list=False,
        )

        skill_map_data = frappe.get_all(
            "Employee Skill Map",
            filters={"name": ["in", skill_map_parents]},
            fields=["name", "employee"],
            as_list=False,
        )

        skill_map_to_employee = {row["name"]: row["employee"] for row in skill_map_data}
        employee_skills = {}

        for detail in skill_details:
            employee = skill_map_to_employee.get(detail.parent)
            if employee:
                user_id = employee_map.get(employee)
                if user_id:
                    employee_skills.setdefault(user_id, set()).add(detail.skill)

        return employee_skills

    def apply_multiselect_filters(self, employees: list) -> list:
        if not employees:
            return []

        filtered_employees = employees

        if self.get("branch") or self.get("region"):
            company_list = []
            if self.get("branch"):
                company_list.extend(
                    self._extract_multiselect_values("branch", "company")
                )
            if not self.get("branch") and self.get("region"):
                company_list.extend(
                    self._extract_multiselect_values("region", "company")
                )

            if company_list:
                company_tree = get_company_descendants(company_list=company_list)
                filtered_employees = [
                    emp for emp in filtered_employees if emp.company in company_tree
                ]

        dept_list = self._extract_multiselect_values("department", "department")
        if dept_list:
            filtered_employees = [
                emp for emp in filtered_employees if emp.department in dept_list
            ]

        emp_type_list = self._extract_multiselect_values(
            "employment_type", "employment_type"
        )
        if emp_type_list:
            filtered_employees = [
                emp
                for emp in filtered_employees
                if emp.employment_type in emp_type_list
            ]

        designation_list = self._extract_multiselect_values(
            "designation", "designation"
        )
        if designation_list:
            filtered_employees = [
                emp for emp in filtered_employees if emp.designation in designation_list
            ]

        user_ids = [emp.user_id for emp in filtered_employees if emp.user_id]

        location_filters = self._get_location_filters()
        course_filters = self._get_course_filters()
        skill_filters = self._get_skill_filters()
        licence_filters = self._get_licence_filters()

        user_location_data = {}
        user_courses_data = {}
        user_licence_data = {}
        employee_skills_data = {}

        if any(location_filters.values()):
            user_location_data = self._get_user_location_data(user_ids)

        if course_filters:
            user_courses_data = self._get_user_courses_data(user_ids)

        if skill_filters:
            employee_skills_data = self._get_employee_skills_data(filtered_employees)

        if licence_filters:
            user_licence_data = self._get_user_licence_data(user_ids)

        final_filtered_employees = []

        for emp in filtered_employees:
            user_id = emp.get("user_id")

            if not user_id:
                if not any(
                    [any(location_filters.values()), course_filters, skill_filters]
                ):
                    final_filtered_employees.append(emp)
                continue

            location_match = True
            if any(location_filters.values()):
                user_doc = user_location_data.get(user_id)
                if not user_doc:
                    location_match = False
                else:
                    for field in [
                        "county",
                        "sub_county",
                        "ward",
                        "administrative_location",
                    ]:
                        filter_values = location_filters.get(field)
                        user_value = user_doc.get(field)
                        if filter_values and user_value not in filter_values:
                            location_match = False
                            break

            if not location_match:
                continue

            course_match = True
            if course_filters:
                user_courses = user_courses_data.get(user_id, set())
                if not any(c in user_courses for c in course_filters):
                    course_match = False

            if not course_match:
                continue

            licence_match = True
            if licence_filters:
                user_licences = user_licence_data.get(user_id, set())
                if not any(c in user_licences for c in licence_filters):
                    licence_match = False

            if not licence_match:
                continue

            skill_match = True
            if skill_filters:
                user_skills = employee_skills_data.get(user_id, set())
                if not any(s in user_skills for s in skill_filters):
                    skill_match = False

            if not skill_match:
                continue

            final_filtered_employees.append(emp)

        if (
            self.get("filter_criteria")
            and self.expected_start_date
            and self.expected_end_date
        ):
            if self.filter_criteria == "Availability":
                final_filtered_employees = self.filter_by_availability(
                    final_filtered_employees,
                    self.expected_start_date,
                    self.expected_end_date,
                )

        return final_filtered_employees

    def filter_by_availability(
        self, employees: list, expected_start_date, expected_end_date
    ) -> list:
        if not employees:
            return []

        expected_start_date = frappe.utils.getdate(expected_start_date)
        expected_end_date = frappe.utils.getdate(expected_end_date)
        final_employees = []

        for emp in employees:
            emp_name = emp.get("name")

            pas = frappe.get_all(
                "Personnel Availability Schedule",
                filters={"employee": emp_name},
                fields=["name", "start_date", "end_date"],
            )

            if not pas:
                final_employees.append(emp)
                continue

            available = False

            for sched in pas:
                sched_start = frappe.utils.getdate(sched.start_date)
                sched_end = frappe.utils.getdate(sched.end_date)

                if sched_end < expected_start_date or sched_start > expected_end_date:
                    continue

                schedule_rows = frappe.get_all(
                    "Schedule",
                    filters={
                        "parent": sched.name,
                        "parenttype": "Personnel Availability Schedule",
                    },
                    fields=["day", "shift_type"],
                )

                for row in schedule_rows:
                    day = (row.get("day") or "").lower()
                    shift_type = row.get("shift_type")

                    if not shift_type:
                        continue

                    shift = frappe.get_value(
                        "Shift Type",
                        shift_type,
                        ["start_time", "end_time"],
                        as_dict=True,
                    )
                    if not shift:
                        continue

                    current_day = expected_start_date
                    while current_day <= expected_end_date:
                        if current_day.strftime("%A").lower() == day:

                            available = True
                            break
                        current_day += timedelta(days=1)

                    if available:
                        break

                if available:
                    break

            if available:
                final_employees.append(emp)

        return final_employees
