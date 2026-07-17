import frappe
from frappe import _

from ..utils.utils import log_throw_error
from .volunteer import get_current_volunteer


@frappe.whitelist()
def fetch_assigned_projects():
	volunteer = get_current_volunteer()

	assignees = frappe.get_all(
		"Personnel Deployment Request",
		filters={
			"employee": volunteer,
			"deployment_status": "Pending",
			"docstatus": 0,
		},
		fields=["name", "deployment"],
	)

	if not assignees:
		return []

	projects = []
	for assignee in assignees:
		deployment_name = assignee.deployment
		assignee_name = assignee.name

		deployment = frappe.get_doc("Deployment Request Tool", deployment_name)
		if not deployment or not deployment.project:
			continue

		project = frappe.db.get_value(
			"Project",
			deployment.project,
			[
				"name",
				"project_name",
				"status",
				"project_type",
				"is_active",
				"percent_complete",
				"priority",
				"expected_start_date",
				"expected_end_date",
				"priority",
				"notes",
			],
			as_dict=1,
		)
		if project:
			project["deployment_name"] = assignee_name
			if getattr(deployment, "task", None):
				task = frappe.db.get_value(
					"Task",
					deployment.task,
					[
						"name",
						"subject",
						"status",
						"priority",
						"exp_start_date",
						"exp_end_date",
						"project",
						"description",
					],
					as_dict=1,
				)
				project["task"] = task
			else:
				project["task"] = None
			projects.append(project)

	return projects


@frappe.whitelist()
def get_assignment_details(assignment_name: str):
	from ..utils.permission import validate_session_user

	assignment = frappe.get_doc(
		"Personnel Deployment Request",
		assignment_name,
	).as_dict()

	if not assignment:
		return {}

	validate_session_user(assignment.get("user"))

	if assignment.get("require_contract_before_deployment") == 1:
		contract = None
		if frappe.db.exists("Contract", {"personnel_deployment_assignment": assignment["name"]}):
			contract = frappe.get_doc(
				"Contract",
				{"personnel_deployment_assignment": assignment["name"]},
			).as_dict()
		assignment["contract"] = contract

	deployment = frappe.get_doc("Deployment Request Tool", assignment.deployment)

	project = frappe.db.get_value(
		"Project",
		deployment.project,
		[
			"name",
			"project_name",
			"status",
			"project_type",
			"is_active",
			"percent_complete",
			"priority",
			"expected_start_date",
			"expected_end_date",
			"priority",
			"notes",
		],
		as_dict=1,
	)

	if project:
		project["notes"] = frappe.utils.strip_html_tags(project["notes"]) if project.get("notes") else ""

	assignment["project"] = project
	assignment["deployment_details"] = deployment.as_dict()
	tor = frappe.get_doc("Personnel Terms of Reference", deployment.terms_of_reference)
	assignment["term_details"] = tor.as_dict()

	return assignment


@frappe.whitelist()
def accept_assignment(name: str, accepted: bool = True, contract_name: str | None = None):
	PDR_DOC = "Personnel Deployment Request"

	PDR_id = frappe.db.exists(PDR_DOC, name)
	if not PDR_id:
		frappe.throw(_("Personnel Deployment Request not found"), frappe.DoesNotExistError)

	from ..utils.permission import validate_session_user

	assignee = frappe.get_doc("Personnel Deployment Request", PDR_id, ignore_permissions=True)
	validate_session_user(assignee.user)

	assignee.deployment_status = "Accepted" if accepted else "Rejected"

	try:
		assignee.save(ignore_permissions=True)
	except Exception:
		frappe.db.rollback()
		log_throw_error("Erro Accepting Assignment")

	if contract_name:
		linked_pdr = frappe.db.get_value("Contract", contract_name, "personnel_deployment_assignment")
		if linked_pdr != assignee.name:
			frappe.throw_permission_error()
		frappe.db.set_value("Contract", contract_name, {"is_signed": 1})


@frappe.whitelist()
def get_all_deployed_projects():
	volunteer = get_current_volunteer()

	filters = {"employee": volunteer, "docstatus": ["!=", 2]}

	deployments = frappe.get_all(
		"Personnel Deployment Request",
		filters=filters,
		fields=["name"],
	)

	result = []

	for dep in deployments:
		deployment_doc = frappe.get_doc("Personnel Deployment Request", dep.name)
		try:
			project_doc = frappe.get_doc("Project", deployment_doc.project)
			deployment_record = frappe.get_doc("Deployment Request Tool", deployment_doc.deployment)
		except frappe.DoesNotExistError:
			continue

		deployment_dict = deployment_doc.as_dict()
		deployment_dict["project"] = project_doc.as_dict()
		deployment_dict["deployment"] = deployment_record.as_dict()

		result.append(deployment_dict)

	return result
