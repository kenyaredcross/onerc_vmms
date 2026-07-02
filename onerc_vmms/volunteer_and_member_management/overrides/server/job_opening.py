import json
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, time_diff_in_seconds, today


@frappe.whitelist()
def send_opportunity_applicant_rejections() -> None:
	try:
		settings: Document = frappe.get_single("VM Settings")
		closed_openings = frappe.get_all(
			"Job Opening",
			filters={"status": "Closed"},
			fields=["name"],
		)

		for opening_data in closed_openings:
			opening: Document = frappe.get_doc("Job Opening", opening_data.name)
			if not is_auto_rejection_enabled(opening):
				continue

			config: dict[str, Any] = get_rejection_config(opening, settings)
			today_date = getdate(today())
			closing_date = getattr(opening, "closed_on", None) or getattr(opening, "closes_on", None)
			shortlisted_rejection_notification_date = config.get("shortlisted_rejection_notification_date")
			notify_unshortlisted_applicants_after = config.get("notify_unshortlisted_applicants_after")
			notify_unshortlisted_applicants_date = (
				add_days(closing_date, notify_unshortlisted_applicants_after)
				if closing_date and notify_unshortlisted_applicants_after
				else None
			)
			if (today_date == notify_unshortlisted_applicants_date) or (
				today_date == shortlisted_rejection_notification_date
			):
				applicants: list[dict[str, Any]] = get_rejected_applicants(job_opening=opening.name)
				if not applicants:
					continue

				send_rejection_emails(applicants, template_name=config["rejection_email_template"])

	except Exception:
		frappe.log_error("Job Applicant -> Send Rejections Error", frappe.get_traceback())
		frappe.throw("An error occurred while sending rejection notifications.")


def is_auto_rejection_enabled(opening: Document | None) -> bool:
	"""Check if automatic rejection notifications are enabled."""
	if opening and hasattr(opening, "enable_automatic_rejection_notifications"):
		return opening.enable_automatic_rejection_notifications
	return False


def get_rejection_config(opening: Document | None, settings: Document) -> dict[str, Any]:
	"""Fetch config values for rejection notifications from Job Opening or fallback to VM Settings."""
	return {
		"notify_unshortlisted_applicants_after": (
			opening.notify_unshortlisted_applicants_after
			if opening and hasattr(opening, "notify_unshortlisted_applicants_after")
			else settings.notify_unshortlisted_applicants_after
		),
		"shortlisted_rejection_notification_date": (
			opening.shortlisted_rejection_notification_date
			if opening and hasattr(opening, "shortlisted_rejection_notification_date")
			else None
		),
		"rejection_email_template": (
			opening.rejection_email_template
			if opening and hasattr(opening, "rejection_email_template")
			else settings.rejection_email_template
		),
	}


@frappe.whitelist()
def get_rejected_applicants(
	job_opening: str | None = None, job_applicant: str | None = None
) -> list[dict[str, Any]]:
	"""Fetch all rejected applicants matching given filters."""
	filters: dict[str, Any] = {
		"status": "Rejected",
		"applicant_notified_of_application_status": 0,
		"docstatus": 1,
	}
	if job_opening:
		filters["job_title"] = job_opening
	if job_applicant:
		filters["name"] = job_applicant

	return frappe.get_all(
		"Job Applicant",
		filters=filters,
		fields=[
			"name",
			"applicant_name",
			"email_id",
			"creation",
			"job_title",
			"applicant_notified_of_application_status",
		],
	)


def mark_applicant_notified(applicant_name: str) -> None:
	"""Mark the applicant as notified of rejection."""
	frappe.db.set_value(
		"Job Applicant",
		applicant_name,
		{
			"applicant_notified_of_application_status": 1,
		},
	)


@frappe.whitelist()
def send_rejection_emails(applicants: Any, template_name: str | None = None) -> None:
	"""
	Enqueue send_rejection_email tasks.
	Accepts applicants as a JSON string or a Python list/dict/str. Uses json.loads when a str is passed.
	Each item can be:
	  - a string (applicant name)
	  - a dict with a "name" key fallback)
	  - an object with a .name attribute
	"""

	parsed = applicants
	if isinstance(applicants, str):
		try:
			parsed = json.loads(applicants)
		except Exception:
			parsed = [applicants]

	if isinstance(parsed, dict):
		parsed = [parsed]
	if not isinstance(parsed, list | tuple):
		parsed = [parsed]

	for applicant in parsed:
		name = None
		if isinstance(applicant, str):
			name = applicant
		elif isinstance(applicant, dict):
			name = applicant.get("name")
		else:
			name = getattr(applicant, "name", None)

		if not name:
			continue

		frappe.enqueue(
			send_rejection_email,
			queue="default",
			name=name,
			template_name=template_name,
			timeout=600,
			job_name=f"send_rejection_email:{name}",
		)


@frappe.whitelist()
def send_rejection_email(name: str, template_name: str | None = None) -> bool:
	"""Send rejection email using a given Email Template."""
	try:
		app: Document = frappe.get_doc("Job Applicant", name)

		if not template_name:
			opening: Document = frappe.get_doc("Job Opening", app.job_title)
			if opening.rejection_email_template:
				template_name = opening.rejection_email_template
			else:
				settings: Document = frappe.get_single("VM Settings")
				template_name = settings.rejection_email_template

		template: Document = frappe.get_doc("Email Template", template_name)

		context: dict[str, Any] = {"doc": app}

		subject: str = frappe.render_template(template.subject or "Application Update", context)
		message: str = frappe.render_template(template.response or "", context)

		frappe.sendmail(
			recipients=[app.email_id],
			subject=subject,
			message=message,
			reference_doctype="Job Applicant",
			reference_name=app.name,
		)
		mark_applicant_notified(app.name)
		return True

	except Exception:
		frappe.log_error(
			f"Failed to send rejection email for Job Applicant {name}",
			frappe.get_traceback(),
		)
		return False


def validate(doc: Document, method: str) -> None:
	child_meta = frappe.get_meta("Supporting Document")
	attachment_field = child_meta.get_field("attachment")
	if attachment_field and attachment_field.reqd:
		attachment_field.reqd = 0

	if doc.posted_on and doc.closes_on:
		doc.duration = time_diff_in_seconds(doc.closes_on, doc.posted_on)
