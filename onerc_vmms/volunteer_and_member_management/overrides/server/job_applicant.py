import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.html_utils import sanitize_html

from .job_opening import claim_rejection_notification, send_rejection_email

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
	"consent_to_use_of_bio_data",
	"linkedin",
	"github",
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
			row_data = {key: value for key, value in row.as_dict().items() if key not in SKIP_CHILD_FIELDS}
			user_doc.append(table_field, row_data)

	user_doc.flags.ignore_mandatory = True
	user_doc.save(ignore_permissions=True)


def update_screening_scores(doc: Document):
	total_score = 0
	max_total_score = 0
	knock_off_failed = False
	failed_knock_off_questions = []
	responses = doc.screening_question_responses

	for resp in responses:
		question_name = frappe.db.exists(
			"Job Application Screening Questions",
			{"question_id": resp.question_id, "parent": doc.job_title},
		)
		if not question_name:
			frappe.throw(
				_("Screening response refers to an unknown question: {0}").format(resp.question_id),
				title=_("Invalid Screening Response"),
			)

		question = frappe.get_doc("Job Application Screening Questions", question_name)

		score = 0
		max_score = question.max_score or 0

		if getattr(question, "enable_scoring", False):
			if question.is_required and not resp.answer:
				score = 0
			elif resp.answer and question.expected_answer:
				if question.question_type == "MultiSelect":
					user_answers = set(ans.strip() for ans in resp.answer.split("\n") if ans.strip())
					expected_answers = set(
						ans.strip() for ans in question.expected_answer.split("\n") if ans.strip()
					)

					if user_answers.intersection(expected_answers):
						score = min(max_score, question.weight)
					else:
						score = 0
				else:
					user_ans = resp.answer.strip()
					expected_ans = question.expected_answer.strip()
					score = min(max_score, question.weight) if user_ans == expected_ans else 0
		else:
			max_score = 0

		resp.score_obtained = score
		resp.max_score = max_score
		resp.expected_answer = question.expected_answer

		total_score += score
		max_total_score += max_score

		if getattr(question, "is_knock_off", False) and score == 0:
			knock_off_failed = True
			failed_knock_off_questions.append(question.question or resp.question_id)

	screening_score_percent = (total_score / max_total_score) * 100 if max_total_score > 0 else 0

	doc.total_score = total_score
	doc.screening_score_percent = screening_score_percent

	minimum_pass_score = frappe.get_value(
		"Job Opening",
		doc.job_title,
		"minimum_pass_score",
	) or frappe.get_value(
		"VM Settings",
		None,
		"minimum_pass_score",
	)

	try:
		min_pass = float(minimum_pass_score) if minimum_pass_score is not None else 70.0
		score = float(screening_score_percent) if screening_score_percent is not None else None
	except (TypeError, ValueError):
		min_pass = 70.0
		score = None

	if knock_off_failed:
		doc.eligibility_status = "Not Eligible"
		doc.status = "Rejected"

		questions_str = ", ".join(failed_knock_off_questions)
		doc.rejection_reason = (
			f"Failed critical knock-off requirements during screening. "
			f"Unmet criteria: [{questions_str}]. "
			f"Overall screening score achieved: {screening_score_percent:.1f}%."
		)
	else:
		if score is not None and min_pass is not None:
			if score >= min_pass:
				doc.eligibility_status = "Eligible"
			else:
				doc.eligibility_status = "Pending Review"
				doc.status = "Rejected"
				doc.rejection_reason = (
					f"Screening score of {score:.1f}% falls below the required minimum "
					f"passing threshold of {min_pass:.1f}%."
				)
		else:
			doc.eligibility_status = "Pending Review"


def validate_required_supporting_documents(doc: Document):
	required_types = frappe.get_all(
		"Supporting Document Type",
		filters={"is_required": 1},
		pluck="name",
		order_by="name asc",
	)
	if not required_types:
		return

	attached = {row.type for row in (doc.get("supporting_documents") or []) if row.type and row.attachment}

	missing = [doc_type for doc_type in required_types if doc_type not in attached]
	if missing:
		frappe.throw(
			_(f"Please attach the following required documents before submitting: {missing}"),
			title=_("Missing Required Documents"),
		)


def before_submit(doc, method):
	if doc.is_volunteer:
		validate_required_supporting_documents(doc)
	else:
		update_screening_scores(doc)


def on_submit(doc, method):
	"""Run after submit: prepare user updates (no save here)."""
	try:
		update_user_from_applicant(doc)
		job_opening = frappe.get_doc("Job Opening", doc.job_title)
		if (
			job_opening.send_rejection_email_immediately
			and doc.status == "Rejected"
			and claim_rejection_notification(doc.name)
		):
			frappe.enqueue(
				send_rejection_email,
				name=doc.name,
				queue="long",
			)

	except Exception:
		frappe.log_error("Job Applicant -> User Update Error", frappe.get_traceback())


def validate(doc, method):
	if doc.get("cover_letter"):
		doc.cover_letter = sanitize_html(doc.cover_letter)

	if doc.job_title:
		job_opening = frappe.get_doc("Job Opening", doc.job_title)
		if job_opening.job_title != doc.opportunity_name:
			doc.opportunity_name = job_opening.job_title
