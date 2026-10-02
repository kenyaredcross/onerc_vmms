"""Portal-owned requests and geographically scoped certificate review."""

import frappe
from frappe import _
from frappe.utils import cint

from vmmsx.service_certificate import service, settings
from vmmsx.templating.services import render


@frappe.whitelist()
def request_options():
	return service.options()


@frappe.whitelist(methods=["POST"])
def submit_request(
	kind: str,
	record: str,
	service_from: str,
	service_to: str,
	position: str | None = None,
	service_summary: str | None = None,
	custom_values: dict | str | None = None,
):
	return service.create(kind, record, service_from, service_to, position, service_summary, custom_values)


@frappe.whitelist()
def my_requests(offset: int = 0):
	profile = service.my_profile()
	names = (
		frappe.get_all(
			settings.REQUEST,
			filters={"red_profile": profile},
			pluck="name",
			order_by="creation desc, name desc",
			limit_start=max(0, cint(offset)),
			limit_page_length=21,
		)
		if profile
		else []
	)
	return {
		"requests": [service.dto(frappe.get_doc(settings.REQUEST, name)) for name in names[:20]],
		"has_more": len(names) > 20,
	}


@frappe.whitelist()
def review_requests(
	volunteer: str | None = None, member: str | None = None, status: str | None = None, offset: int = 0
):
	filters = {}
	if volunteer:
		filters["volunteer"] = volunteer
	if member:
		filters["member"] = member
	if status == "Pending":
		filters["approval_state"] = ["in", ["Submitted", "In Review"]]
	elif status in ("Approved", "Rejected"):
		filters["approval_state"] = status
	if not frappe.has_permission(settings.REQUEST, "read"):
		return {"requests": [], "has_more": False}
	names = frappe.get_list(
		settings.REQUEST,
		filters=filters,
		pluck="name",
		order_by="creation desc, name desc",
		limit_start=max(0, cint(offset)),
		limit_page_length=21,
	)
	return {
		"requests": [service.dto(frappe.get_doc(settings.REQUEST, name)) for name in names[:20]],
		"has_more": len(names) > 20,
	}


@frappe.whitelist()
def get_request(name: str):
	doc = service.readable(name)
	config = service.parsed(doc.configuration)
	answers = service.parsed(doc.custom_values)
	logs = service.history(doc)
	return {
		**service.dto(doc),
		"service_history": logs,
		"service_hours": sum(row.hours for row in logs),
		"additional_answers": [
			{"label": r["label"], "value": answers.get(r["key"], "")}
			for r in config["fields"]
			if r["source"] == "custom_value"
		],
		"certificate_html": doc.certificate_html
		or render.render_string(config["body"], service.context_for(doc, checking=True)),
	}


@frappe.whitelist(methods=["POST"])
def decide(name: str, decision: str, reason: str | None = None, review_note: str | None = None):
	return service.decide(name, decision, reason, review_note)


@frappe.whitelist(methods=["POST"])
def generate(name: str):
	doc = service.readable(name, review=True)
	doc.check_permission("write")
	if service.holder(doc) == frappe.session.user:
		frappe.throw(_("Only the reviewing office can generate a certificate."), frappe.PermissionError)
	service.generate(name)
	return service.dto(doc.reload())


@frappe.whitelist()
def download(name: str):
	doc = service.readable(name)
	if not doc.certificate_file or doc.approval_state != "Approved":
		frappe.throw(_("The certificate is not ready to download."))
	file = frappe.get_doc("File", doc.certificate_file)
	if (
		not file.is_private
		or file.attached_to_doctype != settings.REQUEST
		or file.attached_to_name != doc.name
	):
		frappe.throw(_("The certificate file does not belong to this request."), frappe.PermissionError)
	frappe.local.response.filename = f"service-certificate-{doc.name}.pdf"
	frappe.local.response.filecontent = file.get_content()
	frappe.local.response.type = "pdf"


@frappe.whitelist(methods=["POST"])
def preview(configuration: dict | str | None = None):
	doc = frappe.get_single(settings.SETTINGS)
	doc.check_permission("write")
	if configuration:
		values = service.parsed(configuration)
		for key in (
			"certificate_title",
			"certificate_logo",
			"template",
			"identity_source",
			"footer_text",
			"tagline",
			"certificate_fields",
		):
			if key in values:
				doc.set(key, values[key])
	config = settings.snapshot(doc)
	config["facts"] = {
		"applicant_name": "Alex Morgan",
		"id_number": "12345678",
		"engagement_date": "2022-01-10",
		"branch": "Central Branch",
	}
	sample = frappe._dict(
		name="CSR-PREVIEW",
		configuration=config,
		custom_values={r["key"]: "Sample value" for r in config["fields"] if r["source"] == "custom_value"},
		position="Community volunteer",
		service_summary="Community support and outreach",
		volunteer=None,
		service_from="2022-01-10",
		service_to="2026-01-10",
		issued_on=None,
		issued_by=None,
	)
	return {"html": render.render_string(config["body"], service.context_for(sample, checking=True))}
