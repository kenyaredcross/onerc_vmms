import frappe
from frappe.model.document import Document

SKIP_CHILD_FIELDS = [
    "name",
    "parent",
    "parentfield",
    "parenttype",
    "doctype",
    "idx",
    "docstatus",
    "creation",
    "modified",
    "modified_by",
    "owner",
]

FIELD_MAP = {
    "date_of_birth": "birth_date",
    "mpesa_mobile_phone": "mobile_no",
    "surname": "last_name",
    "other_names": "middle_name",
    "phone_number": "phone",
}

NORMAL_FIELDS = [
    "ward",
    "first_name",
    "identification_type",
    "id_number",
    "passport_number",
    "number_of_dependants",
    "marital_status",
    "blood_group",
    "citizenship",
    "country_of_citizenship",
    "administrative_location",
    "sub_county",
    "county",
    "access_to_internet",
    "profession",
    "reason_to_join_krcs",
    "gender",
]

TABLE_FIELDS = [
    "languages",
    "education",
    "disabilities",
    "driving_licence",
    "certification",
    "licences",
    "additional_skills",
    "allergies",
    "allergies",
    "allergies",
    "allergies",
    "certification",
    "work_references",
    "work_experience",
    "supporting_documents",
    "work_experience",
]


def update_user_from_applicant(doc: Document):
    """
    Sync Job Applicant data to User after submit.
    Updates normal fields, mapped fields, and child table fields.
    Returns the prepared User doc (does not save it).
    """
    email = getattr(doc, "email_id", None)
    if not email:
        return

    user_list = frappe.get_all("User", filters={"email": email}, limit=1)
    if not user_list:
        return

    user_doc = frappe.get_doc("User", user_list[0].name)

    for applicant_field, user_field in FIELD_MAP.items():
        value = getattr(doc, applicant_field, None)
        if value is not None:
            setattr(user_doc, user_field, value)

    for field in NORMAL_FIELDS:
        if field in SKIP_CHILD_FIELDS:
            continue
        value = getattr(doc, field, None)
        if value is not None:
            setattr(user_doc, field, value)

    for table_field in TABLE_FIELDS:
        if not hasattr(doc, table_field):
            continue
        applicant_table = getattr(doc, table_field) or []
        if not applicant_table:
            continue

        if not user_doc.meta.get_field(table_field):
            continue

        if hasattr(user_doc, table_field):
            user_doc.set(table_field, [])

        for row in applicant_table:
            row_data = {
                key: value
                for key, value in row.as_dict().items()
                if key not in SKIP_CHILD_FIELDS
            }
            user_doc.append(table_field, row_data)

    user_doc.flags.ignore_mandatory = True
    user_doc.save(ignore_permissions=True)


def update_screening_scores(doc: Document):
    """
    Calculate and update screening scores before submit.
    """
    try:
        total_score = 0
        max_total_score = 0
        knock_off_failed = False
        responses = doc.screening_question_responses

        for resp in responses:
            question = frappe.get_doc(
                "Job Application Screening Questions",
                {"question_id": resp.question_id, "parent": doc.job_title},
            )

            score = 0
            max_score = question.max_score or 0

            if question.is_required and not resp.answer:
                score = 0
            elif resp.answer and question.expected_answer:
                score = (
                    min(max_score, question.weight)
                    if resp.answer == question.expected_answer
                    else 0
                )

            resp.score_obtained = score
            resp.max_score = max_score
            resp.expected_answer = question.expected_answer

            total_score += score
            max_total_score += max_score

            if getattr(question, "is_knock_off", False) and score == 0:
                knock_off_failed = True

        screening_score_percent = (
            (total_score / max_total_score) * 100 if max_total_score > 0 else 0
        )

        doc.total_score = total_score
        doc.screening_score_percent = screening_score_percent

        if knock_off_failed:
            doc.eligibility_status = "Not Eligible"
            doc.status = "Rejected"
        else:
            doc.eligibility_status = (
                "Eligible" if screening_score_percent >= 70 else "Pending Review"
            )

    except Exception:
        frappe.log_error(
            "Job Applicant -> Screening Score Update Error", frappe.get_traceback()
        )


def before_submit(doc, method):
    """Run before submit: handle scoring and eligibility."""
    update_screening_scores(doc)


def on_submit(doc, method):
    """Run after submit: prepare user updates (no save here)."""
    try:
        update_user_from_applicant(doc)
    except Exception:
        frappe.log_error("Job Applicant -> User Update Error", frappe.get_traceback())
