import frappe

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
def get_assignment_details(assignment_name):

    assignment = frappe.get_doc(
        "Personnel Deployment Request",
        assignment_name,
    ).as_dict()

    if not assignment:
        return {}

    if assignment.get("require_contract_before_deployment") == 1:
        contract = None
        if frappe.db.exists(
            "Contract", {"personnel_deployment_assignment": assignment["name"]}
        ):
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
        project["notes"] = (
            frappe.utils.strip_html_tags(project["notes"])
            if project.get("notes")
            else ""
        )

    assignment["project"] = project
    assignment["deployment_details"] = deployment.as_dict()
    tor = frappe.get_doc("Personnel Terms of Reference", deployment.terms_of_reference)
    assignment["term_details"] = tor.as_dict()

    return assignment


@frappe.whitelist()
def accept_assignment(name, accepted=True, contract_name=None):

    try:

        if frappe.db.exists("Contract", contract_name):
            frappe.db.set_value("Contract", contract_name, {"is_signed": 1})

        assignee = frappe.get_doc(
            "Personnel Deployment Request", name, ignore_permissions=True
        )
        assignee.deployment_status = "Accepted" if accepted else "Rejected"
        assignee.save(ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Accept Assignment Error")
        frappe.throw("Accept Assignment Error")


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
            deployment_record = frappe.get_doc(
                "Deployment Request Tool", deployment_doc.deployment
            )
        except frappe.DoesNotExistError:
            continue

        deployment_dict = deployment_doc.as_dict()
        deployment_dict["project"] = project_doc.as_dict()
        deployment_dict["deployment"] = deployment_record.as_dict()

        result.append(deployment_dict)

    return result
