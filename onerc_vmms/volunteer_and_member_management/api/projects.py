import frappe

from .volunteer import get_current_volunteer


@frappe.whitelist()
def get_projects():
    return frappe.get_all(
        "Project",
        fields=[
            "name",
            "project_name",
            "status",
            "project_type",
            "is_active",
            "percent_complete",
            "priority",
            "expected_start_date",
            "expected_end_date",
        ],
    )


@frappe.whitelist()
def fetch_assigned_projects():
    volunteer = get_current_volunteer()

    assignees = frappe.get_all(
        "Personnel Deployment Assignment",
        filters={
            "employee": volunteer,
            "status": "Pending",
            "docstatus": 1,
        },
        fields=["name", "deployment"],
    )

    if not assignees:
        return []

    projects = []
    for assignee in assignees:
        deployment_name = assignee.deployment
        assignee_name = assignee.name

        deployment = frappe.get_doc("Personnel Deployment Request", deployment_name)
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
def get_project_details(project_name):

    project = frappe.db.get_value(
        "Project",
        project_name,
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

    project["notes"] = (
        frappe.utils.strip_html_tags(project["notes"])
        if project and project.get("notes")
        else ""
    )

    return project


@frappe.whitelist()
def get_assignment_details(assignment_name):

    assignment = frappe.get_doc(
        "Personnel Deployment Assignment",
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

    deployment = frappe.get_doc("Personnel Deployment Request", assignment.deployment)

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
    assignment["term_details"] = (
        frappe.utils.strip_html_tags(assignment["term_details"])
        if assignment.get("term_details")
        else ""
    )

    return assignment


@frappe.whitelist()
def accept_assignment(name, accepted=True, contract_name=None):

    try:

        if frappe.db.exists("Contract", contract_name):
            frappe.db.set_value("Contract", contract_name, {"is_signed": 1})

        assignee = frappe.get_doc(
            "Personnel Deployment Assignment", name, ignore_permissions=True
        )
        assignee.status = "Accepted" if accepted else "Rejected"
        assignee.save(ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Accept Assignment Error")
        frappe.throw("Accept Assignment Error")


@frappe.whitelist()
def get_all_deployed_projects(**kwargs):

    volunteer = get_current_volunteer()

    accepted_filters = {"status": "Accepted"}
    rejected_filters = {"status": "Rejected"}

    deployments = frappe.get_all(
        "Volunteer Deployment Assignee",
        (
            {"volunteer": volunteer} | accepted_filters
            if kwargs.get("accepted")
            else {} | rejected_filters if kwargs.get("rejected") else {}
        ),
        ["parent"],
    )

    project = None
    projects = []
    projects_details = []

    for deployment in deployments:

        project = frappe.db.get_value(
            "Volunteer Deployment", deployment.parent, "project", as_dict=True
        )

        if project:
            projects.append(project)

    for project in projects:
        project_details = frappe.db.get_value(
            "Project",
            project.project,
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
            as_dict=True,
        )
        if project_details:
            projects_details.append(project_details)

    return projects_details
