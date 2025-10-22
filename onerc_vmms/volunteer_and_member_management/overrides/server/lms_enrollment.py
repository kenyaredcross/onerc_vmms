import frappe
from frappe import _
from frappe.model.document import Document


@frappe.whitelist()
def on_update(doc: Document, method: str) -> None:
    if doc.doctype != "LMS Enrollment":
        return

    if not doc.progress or doc.progress < 100:
        return

    course = frappe.get_doc("LMS Course", doc.course)
    course_skills = [row.skill for row in course.skills]
    if not course_skills:
        return

    existing_skills = {
        skill.skill for skill in frappe.get_all("User Skill", fields=["skill"])
    }
    for skill in course_skills:
        if skill not in existing_skills:
            skill_doc = frappe.get_doc({"doctype": "User Skill", "skill": skill})
            skill_doc.insert(ignore_permissions=True)

    user_doc = frappe.get_doc("User", doc.member)
    existing_user_skills = {row.skill_name for row in getattr(user_doc, "skill", [])}

    for skill in course_skills:
        if skill not in existing_user_skills:
            user_doc.append(
                "skill",
                {
                    "skill_name": skill,
                },
            )

    user_doc.save(ignore_permissions=True)

    employee = frappe.db.get_value("Employee", {"user_id": doc.member}, "name")
    if not employee:
        return

    employee_doc = frappe.get_doc("Employee", employee)
    existing_employee_skills = {
        row.skill for row in getattr(employee_doc, "skills", [])
    }

    added_to_employee = False
    for skill in course_skills:
        if skill not in existing_employee_skills:
            employee_doc.append("skills", {"skill": skill})
            added_to_employee = True

    if added_to_employee:
        employee_doc.save(ignore_permissions=True)

    skill_maps = frappe.get_all(
        "Employee Skill Map", filters={"employee": employee}, fields=["name"]
    )

    if not skill_maps:
        skill_map_doc = frappe.get_doc(
            {"doctype": "Employee Skill Map", "employee": employee}
        )
        skill_map_doc.insert(ignore_permissions=True)
        skill_maps = [{"name": skill_map_doc.name}]

    existing_emp_skills = set()
    for sm in skill_maps:
        sm_doc = frappe.get_doc("Employee Skill Map", sm.get("name"))
        for row in sm_doc.employee_skills:
            existing_emp_skills.add(row.skill)

    target_map = frappe.get_doc("Employee Skill Map", skill_maps[0].get("name"))

    added = False
    for skill in course_skills:
        if skill not in existing_emp_skills:
            target_map.append("employee_skills", {"skill": skill, "proficiency": 5})
            added = True

    if added:
        target_map.save(ignore_permissions=True)
