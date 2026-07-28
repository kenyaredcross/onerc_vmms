import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime

from ..utils.permission import validate_session_user
from ..utils.utils import set_field_value

PROTECTED_APPLICANT_FIELDS = frozenset(
	{
		"name",
		"owner",
		"docstatus",
		"status",
		"is_volunteer",
		"applicant_notified_of_application_status",
		"job_title",
		"company",
	}
)


def _apply_application_fields(application, fields: dict) -> None:
	"""Write only non-protected, real fields onto a Job Applicant document."""
	for fieldname, value in fields.items():
		if fieldname in PROTECTED_APPLICANT_FIELDS:
			continue

		if application.meta.has_field(fieldname):
			fieldtype = application.meta.get_field(fieldname).fieldtype
			set_field_value(application, fieldname, value, fieldtype)


@frappe.whitelist(
	allow_guest=True
)  # nosemgrep: guest-whitelisted-method -- public job board listing, read-only
def get_job_openings(filters=None, orFilters=None):
	if not filters:
		filters = {}
	filters["publish"] = 1
	filters["status"] = "Open"
	now = now_datetime()
	filters["posted_on"] = ["<=", now]

	or_filters = orFilters or []

	user = frappe.session.user

	# employee_exists = frappe.db.exists(
	#     "Employee", {"user_id": user, "status": "Active"}
	# )

	# if not employee_exists:
	#     filters["opportunity_type"] = "Guest"

	regions = None
	if "region" in filters:
		region_value = filters.pop("region")
		if isinstance(region_value, list) and region_value and isinstance(region_value[0], dict):
			regions = [item.get("value") for item in region_value if item.get("value")]
		else:
			regions = region_value

	companies = None
	if "company" in filters:
		companies_value = filters.pop("company")
		if isinstance(companies_value, list) and companies_value and isinstance(companies_value[0], dict):
			companies = [item.get("value") for item in companies_value if item.get("value")]
		else:
			companies = companies_value

	company_list = []

	if regions:
		children = []

		if isinstance(regions, list):
			for region in regions:
				region_children = frappe.get_all(
					"Company",
					filters={"parent_company": region},
					pluck="name",
				)
				children.extend(region_children)
		else:
			children = frappe.get_all(
				"Company",
				filters={"parent_company": regions},
				pluck="name",
			)

		if companies:
			company_list = regions + companies
		else:
			company_list = regions + children

		filters["company"] = ["in", company_list]
	elif companies:
		filters["company"] = ["in", companies]

	job_names = frappe.get_all(
		"Job Opening",
		filters=filters,
		or_filters=or_filters,
		fields=["name"],
		order_by="creation desc",
	)

	jobs = []
	for j in job_names:
		try:
			jobs.append(frappe.get_doc("Job Opening", j.name).as_dict())
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Failed to fetch Job Opening doc")

	if user != "Guest":
		user_email = frappe.db.get_value("User", user, "email")
		if user_email:
			applied_jobs = frappe.get_all(
				"Job Applicant",
				filters={"email_id": user_email},
				pluck="job_title",
			)
			jobs = [job for job in jobs if job.name not in applied_jobs]

	for job in jobs:
		job.description = frappe.utils.strip_html_tags(job.description) if job.description else ""
		job.applicants = frappe.db.count("Job Applicant", {"job_title": job.name})

	return jobs


@frappe.whitelist(allow_guest=True)  # nosemgrep:
def get_job_details(job: str):
	is_public = frappe.db.exists(
		"Job Opening",
		{
			"name": job,
			"publish": 1,
			"status": "Open",
			"posted_on": ["<=", now_datetime()],
		},
	)
	if not is_public:
		user = frappe.session.user
		user_email = frappe.db.get_value("User", user, "email") if user != "Guest" else None
		has_applied = bool(user_email) and frappe.db.exists(
			"Job Applicant", {"job_title": job, "email_id": user_email}
		)
		if not has_applied:
			frappe.throw(_("Job Opening not found"), frappe.DoesNotExistError)

	job_doc = frappe.get_doc("Job Opening", job)

	if not job_doc:
		return {}

	job_details = job_doc.as_dict()

	if not job_details:
		return {}

	job_details["applicant_count"] = frappe.db.count("Job Applicant", {"job_title": job_details["name"]})

	job_details["designation"] = frappe.get_doc("Designation", job_details["designation"]).as_dict()

	if job_details.get("company"):
		company = frappe.db.get_value(
			"Company",
			job_details["company"],
			[
				"company_name",
				"company_logo",
				"website",
				"email",
				"phone_no",
			],
			as_dict=1,
		)
		job_details.update(company or {})

	return job_details


def _update_application(application_id: str, fields: dict) -> dict:
	"""Internal: apply allowed fields to an existing application and save it."""

	application = frappe.get_doc("Job Applicant", application_id)
	validate_session_user(application.email_id)
	_apply_application_fields(application, fields)
	application.save(ignore_permissions=True)
	frappe.db.commit()
	return {
		"success": True,
		"message": "Application updated successfully",
		"name": application.name,
	}


@frappe.whitelist()
@rate_limit(limit=30, seconds=60 * 5)
def update_job_application(id: str, **kwargs) -> dict:
	try:
		return _update_application(id, kwargs)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Job Application Update Error")
		return {"success": False, "error": _("Could not update the application.")}


@frappe.whitelist()
@rate_limit(limit=20, seconds=60 * 5)
def submit_job_application(id: str | None = None) -> dict:
	try:
		if not id or not frappe.db.exists("Job Applicant", id):
			return {"error": "Invalid Job Application ID"}

		application = frappe.get_doc("Job Applicant", id)
		validate_session_user(application.email_id)
		if application.docstatus in (1, 2):
			return

		application.flags.ignore_permissions = True
		application.submit()

		frappe.db.commit()
		return {"message": "Application submitted successfully"}

	except frappe.ValidationError:
		raise

	except Exception:
		frappe.log_error(frappe.get_traceback(), "Job Application Submission Error")
		return {"error": _("Could not submit the application.")}


@frappe.whitelist()
@rate_limit(limit=20, seconds=60 * 5)
def create_job_application(job_opening: str | None = None, id: str | None = None, **kwargs) -> dict:
	try:
		if id and frappe.db.exists("Job Applicant", id):
			return _update_application(id, kwargs)

		company = kwargs.get("company")

		if job_opening:
			job_opening_data = frappe.db.get_value("Job Opening", job_opening, ["company"])
			if job_opening_data:
				company = job_opening_data or company

		if not company:
			frappe.throw("Company is required")

		user_id = frappe.session.user
		user_doc = None
		if user_id != "Guest":
			user_doc = frappe.get_doc("User", user_id)
			if not kwargs.get("surname"):
				kwargs["surname"] = user_doc.last_name or ""
			if not kwargs.get("other_names"):
				first_name = user_doc.first_name or ""
				middle_name = user_doc.middle_name or ""
				kwargs["other_names"] = f"{first_name} {middle_name}".strip()
			if not kwargs.get("email_id"):
				kwargs["email_id"] = user_doc.email or ""
			if not kwargs.get("gender"):
				kwargs["gender"] = user_doc.gender or ""
			if not kwargs.get("phone_number"):
				kwargs["phone_number"] = user_doc.phone or user_doc.mobile_no or ""

		email_id = kwargs.get("email_id")
		validate_session_user(email_id)
		if email_id and job_opening:
			frappe.db.get_value("Job Opening", job_opening, "name", for_update=True)
			if frappe.db.exists("Job Applicant", {"job_title": job_opening, "email_id": email_id}):
				return {
					"success": False,
					"message": "You have already applied for this position.",
				}

		update_fields = kwargs.copy()
		update_fields.pop("email_id", None)
		update_fields.pop("surname", None)
		update_fields.pop("other_names", None)

		if not job_opening and email_id:
			if user_id and user_id != "Guest":
				frappe.db.get_value("User", user_id, "name", for_update=True)

			existing = frappe.get_all(
				"Job Applicant",
				filters={"email_id": email_id, "is_volunteer": 1, "docstatus": ("!=", 2)},
				fields=["name", "docstatus"],
				order_by="docstatus asc, modified desc",
				limit=1,
			)
			if existing:
				if existing[0].docstatus == 0:
					return _update_application(existing[0].name, update_fields)
				return {
					"success": False,
					"message": "You have already submitted a volunteer application.",
				}

		surname = kwargs.get("surname", "")
		other_names = kwargs.get("other_names", "")
		name_to_use = f"{other_names} {surname}".strip()

		minimal_doc_data = {
			"doctype": "Job Applicant",
			"applicant_name": name_to_use,
			"email_id": email_id,
			"company": company,
			"status": "Open",
			"is_volunteer": 0 if job_opening else 1,
		}

		if job_opening:
			minimal_doc_data["job_title"] = job_opening

		job_application = frappe.get_doc(minimal_doc_data)
		job_application.insert(ignore_permissions=True)

		return _update_application(job_application.name, update_fields)

	except frappe.DuplicateEntryError:
		# A racing insert beat us to it (or a future unique constraint fired);
		# respond idempotently instead of surfacing a hard error.
		frappe.db.rollback()
		return {
			"success": False,
			"message": "You have already applied for this position.",
		}
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "Job Application Submission Error")
		return {
			"success": False,
			"message": "Failed to submit job application",
		}


@frappe.whitelist()
def fetch_applications(email: str):
	"""
	Fetch all job applications (Job Applicant) for a given email,
	along with related Job Opening details. If applicant_notified_of_application_status
	is not set (truthy), set the returned status to "Submitted" (without saving).
	"""
	if not email:
		frappe.throw(_("Email is required to fetch job applications."))

	session_email = frappe.db.get_value("User", frappe.session.user, "email")
	if frappe.session.user != "Administrator" and email != session_email:
		frappe.throw(
			_("You are not permitted to view these applications."),
			frappe.PermissionError,
		)

	applicants = frappe.get_all(
		"Job Applicant",
		filters={"email_id": email, "job_title": ("!=", None), "is_volunteer": 0},
		fields=["name"],
		order_by="creation desc",
	)

	if not applicants:
		return []

	results = []
	for app in applicants:
		try:
			app_doc = frappe.get_doc("Job Applicant", app.get("name")).as_dict()
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Failed to fetch Job Applicant")
			continue

		if not app_doc.get("applicant_notified_of_application_status") and app_doc.get("docstatus") == 1:
			app_doc["status"] = "Submitted"

		job_opening_details = {}
		job_title = app_doc.get("job_title")
		if job_title:
			try:
				job_opening_details = frappe.get_doc("Job Opening", job_title).as_dict()
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Failed to fetch Job Opening")

		app_doc["job_opening_details"] = job_opening_details
		results.append(app_doc)

	return results


@frappe.whitelist()
def get_job_application(name=None):
	if not name:
		return {"error": "Application ID is required"}

	try:
		job_application = frappe.get_doc("Job Applicant", name).as_dict()

		if frappe.session.user != "Administrator" and job_application.get("email_id") != frappe.session.user:
			return {"error": "You don't have permission to access this application"}

		if job_application.get("job_title"):
			job_opening = frappe.get_doc(
				"Job Opening", job_application.get("job_title"), ignore_permissions=True
			).as_dict()
			job_application["job_opening_details"] = job_opening

		return job_application

	except Exception as e:
		frappe.log_error(str(e), "Error fetching job application")
		return {"error": "Failed to retrieve application details"}


@frappe.whitelist()
def get_required_supporting_document_types() -> list[str]:
	return frappe.get_all(
		"Supporting Document Type",
		filters={"is_required": 1},
		pluck="name",
		order_by="name asc",
	)
