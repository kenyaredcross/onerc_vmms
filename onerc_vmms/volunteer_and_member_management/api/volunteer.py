import frappe
from frappe import _

from ..utils.utils import (
	get_current_fiscal_year,
	get_dates_for_day_of_week,
	get_shift_types,
)
from .doc import _convert_table_multiselect
from .user import get_user_info


def create_volunteer(user_details):
	volunteer = frappe.new_doc("Employee")
	volunteer.first_name = user_details.fullname
	volunteer.full_name = user_details.fullname
	volunteer.email = user_details.email
	volunteer.phone = user_details.phone
	volunteer.is_volunteer = 1
	volunteer.date_of_joining = frappe.utils.today()
	volunteer.insert(ignore_permissions=True)
	return volunteer.name


def get_current_volunteer():
	user = frappe.session.user

	volunteer = frappe.db.get_value("Employee", {"user_id": user}, "name")

	return volunteer


@frappe.whitelist()
def get_dashboard_stats():
	volunteer = get_current_volunteer()

	deployments = frappe.get_all(
		"Personnel Deployment Request",
		filters={"employee": volunteer},
		fields=["name", "deployment_status", "docstatus", "deployment"],
	)

	stats = {
		"total_projects_deployed": len(deployments),
		"pending_response": 0,
		"awaiting_deployment": 0,
		"declined_deployment": 0,
		"active": 0,
		"closed": 0,
	}

	def compute_status(d, project_status):
		"""Apply your JS logic in Python."""
		if d.docstatus == 0:
			if d.deployment_status == "Pending":
				return "Pending Response"
			if d.deployment_status == "Accepted":
				return "Awaiting Deployment"
			if d.deployment_status == "Rejected":
				return "Declined Deployment"

		if d.docstatus == 1 and d.deployment_status == "Accepted":
			return "Active" if project_status == "Open" else "Closed"

		return None

	for d in deployments:
		project_status = None

		if d.deployment:
			deployment_doc = frappe.get_doc("Deployment Request Tool", d.deployment)
			if deployment_doc.project:
				project_status = frappe.db.get_value("Project", deployment_doc.project, "status")

		final_status = compute_status(d, project_status)

		match final_status:
			case "Pending Response":
				stats["pending_response"] += 1
			case "Awaiting Deployment":
				stats["awaiting_deployment"] += 1
			case "Declined Deployment":
				stats["declined_deployment"] += 1
			case "Active":
				stats["active"] += 1
			case "Closed":
				stats["closed"] += 1

	return stats


@frappe.whitelist()
def get_availability_slots():
	user = get_user_info().get("employee")

	parent = frappe.db.get_value("Personnel Availability Schedule", {"employee": user}, "name")
	available_on_holidays = frappe.db.get_value(
		"Personnel Availability Schedule", parent, "available_on_holidays"
	)

	schedules = frappe.get_all(
		"Schedule",
		filters={"parent": parent},
		fields=["name", "day", "shift_type"],
	)

	return {
		"schedules": schedules,
		"available_on_holidays": available_on_holidays,
	}


@frappe.whitelist()
def get_present_slots():
	user = get_user_info().get("employee")

	slot = frappe.db.exists("Personnel Availability Schedule", {"employee": user})

	if slot:
		return True

	return None


def validate_volunteer(volunteer: str) -> None:
	vol_doc_name = frappe.db.exists("Employee", {"name": volunteer, "is_volunteer": 1})
	if not vol_doc_name:
		frappe.throw(_("Volunteer Does not Exist", frappe.DoesNotExistError))

	volunteer_user_id = frappe.db.get_value("Employee", vol_doc_name, "user_id")
	if not volunteer_user_id:
		frappe.throw(_("Error fethcing volunteer details", frappe.ValidationError))
	from ..utils.permission import validate_session_user

	validate_session_user(volunteer_user_id)


@frappe.whitelist()
def create_availability_slot(slot_data: dict):
	validate_volunteer(slot_data.get("employee"))
	try:
		if frappe.db.exists(
			"Volunteer Availability Slot",
			{
				"employee": slot_data.get("employee"),
				"starts_on": slot_data.get("starts_on"),
				"ends_on": slot_data.get("ends_on"),
			},
		):
			frappe.throw("You have already created this availability slot")

		employee = slot_data.get("employee")
		starts_on = slot_data.get("starts_on")
		ends_on = slot_data.get("ends_on")

		conflict_slots = frappe.db.get_all(
			"Volunteer Availability Slot",
			filters={
				"employee": employee,
				"starts_on": ["<", ends_on],
				"ends_on": [">", starts_on],
			},
			fields=["name", "starts_on", "ends_on"],
		)
		if conflict_slots:
			frappe.throw(
				"This slot conflicts with an existing availability slot. Please choose a different time range and check Calendar for existing slots.",
			)

		doc = frappe.get_doc({"doctype": "Volunteer Availability Slot", **slot_data})

		doc.insert(ignore_permissions=True)

		frappe.db.commit()

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Availability Slot Creation Error")

		frappe.throw("Availability Slot Creation Error")


@frappe.whitelist()
def create_availability_schedule(slot_data: dict):
	"""
	Creates Personnel Availability Schedule and generates Weekly Schedule Patterns
	"""
	try:
		employee = slot_data.get("employee")
		validate_volunteer(employee)
		fiscal_year = get_current_fiscal_year()
		weekly_availability = slot_data.get("weekly_availability", {})
		available_on_holidays = slot_data.get("available_on_holidays", False)

		if frappe.db.exists("Personnel Availability Schedule", {"employee": employee}):
			existing_doc = frappe.get_value("Personnel Availability Schedule", {"employee": employee}, "name")
			frappe.delete_doc("Personnel Availability Schedule", existing_doc, ignore_permissions=True)

		personal_schedule_name = create_personal_schedule(employee, fiscal_year, available_on_holidays)
		create_schedule(personal_schedule_name, weekly_availability)

		return {"employee": employee}
	except Exception as e:
		frappe.log_error("Availability Schedule Creation Error", frappe.get_traceback())
		frappe.throw("Availability Schedule Creation Error")


def create_personal_schedule(employee, fiscal_year, available_on_holidays=False):
	"""Create or get existing Personnel Availability Schedule"""
	existing = frappe.db.exists(
		"Personnel Availability Schedule",
		{"employee": employee, "fiscal_year": fiscal_year},
	)

	if existing:
		return existing

	schedule_doc = frappe.new_doc("Personnel Availability Schedule")
	schedule_doc.employee = employee
	schedule_doc.available_on_holidays = available_on_holidays
	schedule_doc.fiscal_year = fiscal_year
	schedule_doc.save(ignore_permissions=True)

	return schedule_doc.name


def generate_weekly_patterns(schedule_name, weekly_availability, fiscal_year):
	"""Generate individual date/shift records based on weekly pattern"""

	fy_doc = frappe.get_doc("Fiscal Year", fiscal_year)
	start_date = fy_doc.year_start_date
	end_date = fy_doc.year_end_date

	shifts = get_shift_types()

	for day_name, selected_shifts in weekly_availability.items():
		if not selected_shifts:
			continue

		day_dates = get_dates_for_day_of_week(start_date, end_date, day_name)

		for date in day_dates:
			for shift_name in selected_shifts:
				shift_info = next((s for s in shifts if s.name == shift_name), None)
				if shift_info:
					create_weekly_pattern_record(schedule_name, date, day_name, shift_info)


def create_weekly_pattern_record(schedule_name, date, day_name, shift_info):
	"""Create individual Weekly Schedule Pattern record"""

	pattern_doc = frappe.new_doc("Weekly Schedule Pattern")
	pattern_doc.parent = schedule_name
	pattern_doc.parenttype = "Personnel Availability Schedule"
	pattern_doc.parentfield = "available_days"
	pattern_doc.day = date
	pattern_doc.from_time = f"{date} {shift_info.start_time}"
	pattern_doc.to_time = f"{date} {shift_info.end_time}"
	pattern_doc.save(ignore_permissions=True)


def create_schedule(schedule_name, weekly_availability):
	schedule_doc = frappe.new_doc("Schedule")
	schedule_doc.parent = schedule_name
	schedule_doc.parenttype = "Personnel Availability Schedule"
	schedule_doc.parentfield = "schedules"
	for day_name, selected_shifts in weekly_availability.items():
		if not selected_shifts:
			continue
		for shift in selected_shifts:
			schedule_doc = frappe.new_doc("Schedule")
			schedule_doc.parent = schedule_name
			schedule_doc.parenttype = "Personnel Availability Schedule"
			schedule_doc.parentfield = "schedules"
			schedule_doc.day = day_name
			schedule_doc.shift_type = shift
			schedule_doc.insert(ignore_permissions=True)


@frappe.whitelist()
def get_my_volunteer_application():
	email = frappe.session.user
	if email == "Guest":
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	name = frappe.db.get_value("Job Applicant", {"email_id": email, "is_volunteer": 1}, "name")
	if not name:
		return None

	doc = frappe.get_doc("Job Applicant", name)
	return _convert_table_multiselect(doc)
