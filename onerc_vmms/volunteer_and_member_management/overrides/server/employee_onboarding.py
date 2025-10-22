import frappe
from frappe import _
from frappe.model.document import Document


@frappe.whitelist()
def on_update(doc: Document, method: str) -> None:
    activities = doc.activities
    for activity in activities:
        course = activity.course
        if course:
            job_applicant = doc.job_applicant

            if job_applicant:
                applicant = frappe.get_doc("Job Applicant", job_applicant)

                existing_enrollment = frappe.db.exists(
                    "LMS Enrollment", {"member": job_applicant, "course": course}
                )
                if not existing_enrollment:
                    new_enrollment = frappe.new_doc("LMS Enrollment")
                    new_enrollment.member = applicant.email_id
                    new_enrollment.member_name = applicant.applicant_name
                    new_enrollment.course = course
                    new_enrollment.save(ignore_permissions=True)
                    frappe.db.commit()

                employee = frappe.db.get_value(
                    "Employee", {"job_applicant": job_applicant}, "name"
                )
                if employee:
                    employee_doc = frappe.get_doc("Employee", employee)

                    training_exists = False
                    for training in employee_doc.get("trainings", []):
                        if training.course == course:
                            training_exists = True
                            break

                    if not training_exists:
                        employee_doc.append("trainings", {"course": course})
                        employee_doc.save(ignore_permissions=True)
                        frappe.db.commit()


@frappe.whitelist()
def on_update_after_submit(doc: Document, method: str) -> None:
    if doc.boarding_status == "Completed":
        courses = [activity.course for activity in doc.activities if activity.course]

        incomplete_courses = []
        course_links = []
        for course in courses:
            enrollment = frappe.get_all(
                "LMS Enrollment",
                filters={"member": doc.job_applicant, "course": course},
                fields=["name", "progress"],
            )
            if enrollment and enrollment[0].get("progress", 0) < 100:
                incomplete_courses.append(course)
                enrollment_link = (
                    f'<a href="/app/lms-enrollment/{enrollment[0].name}">{course}</a>'
                )
                course_links.append(enrollment_link)

        if incomplete_courses:
            course_list = ", ".join(course_links)
            frappe.throw(
                _(
                    "Cannot complete onboarding. The following courses are not finished: {0}"
                ).format(course_list)
            )
