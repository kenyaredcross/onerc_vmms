"""Certificate configuration and the finite set of values it may print."""

from pathlib import Path

import frappe
from frappe import _
from frappe.utils import cint

SETTINGS = "VMMS Service Certificate Settings"
REQUEST = "VMMS Service Certificate Request"
TEMPLATE_KEY = "service_certificate"
SCOPE_FIELD = "vmms_service_certificate_scope_role"
SOURCES = {
	"issue_date",
	"applicant_name",
	"id_number",
	"engagement_date",
	"position",
	"signatory",
	"branch",
	"service_period",
	"service_hours",
	"certificate_number",
	"service_summary",
	"custom_value",
}
DEFAULT_FIELDS = (
	("issue_date", "Date", "Header"),
	("applicant_name", "Name", "Body"),
	("id_number", "ID number", "Body"),
	("engagement_date", "Date of engagement", "Body"),
	("position", "Position", "Body"),
	("signatory", "County Coordinator", "Signature"),
	("branch", "Branch name", "Signature"),
)


def validate(doc):
	counts = {"Header": 0, "Body": 0, "Signature": 0}
	for row in doc.certificate_fields:
		if row.source not in SOURCES or row.placement not in counts:
			frappe.throw(_("Choose a supported certificate value and placement."))
		if not (row.label or "").strip() or len(row.label) > 60:
			frappe.throw(_("Printed labels must contain between 1 and 60 characters."))
		if row.enabled:
			counts[row.placement] += 1
	for area, limit in {"Header": 1, "Body": 8, "Signature": 2}.items():
		if counts[area] > limit:
			frappe.throw(_("The certificate design allows at most {0} fields in {1}.").format(limit, area))
	if not counts["Body"]:
		frappe.throw(_("Enable at least one body field."))
	if len(doc.certificate_title or "") > 70 or len(doc.footer_text or "") > 180:
		frappe.throw(_("Use a title of at most 70 characters and a footer of at most 180 characters."))
	if len(doc.tagline or "") > 80:
		frappe.throw(_("Use a tagline of at most 80 characters."))
	if doc.certificate_logo:
		logo_data(doc.certificate_logo)
	if doc.template and frappe.db.get_value("VMMS Template", doc.template, "output_format") != "html":
		frappe.throw(_("The certificate layout must be an HTML template."))


def logo_data(url):
	"""Freeze the uploaded image bytes; a later replacement cannot change an issue."""
	from base64 import b64encode
	from io import BytesIO

	from PIL import Image

	if not url:
		return ""
	if not url.startswith(("/files/", "/private/files/")):
		frappe.throw(_("Upload a PNG or JPEG for the certificate logo."))
	# Only administrator-controlled certificate configuration reaches here.
	# Its private logo must render for applicants without granting them access
	# to the settings document (find_file_by_url enforces that document access).
	name = frappe.db.get_value("File", {"file_url": url}, "name")
	if not name:
		frappe.throw(_("The certificate logo file could not be found."))
	file = frappe.get_doc("File", name)
	content = file.get_content()
	if len(content) > 5 * 1024 * 1024:
		frappe.throw(_("The certificate logo must be smaller than 5 MB."))
	try:
		with Image.open(BytesIO(content)) as img:
			if img.format not in ("PNG", "JPEG"):
				raise ValueError("Unsupported image")
			mime = "image/png" if img.format == "PNG" else "image/jpeg"
			img.verify()
	except Exception:
		frappe.throw(_("Upload a valid PNG or JPEG for the certificate logo."))
	return f"data:{mime};base64,{b64encode(content).decode()}"


def snapshot(doc=None):
	doc = doc or frappe.get_single(SETTINGS)
	validate(doc)
	template = frappe.get_doc("VMMS Template", doc.template)
	if not template.is_active:
		frappe.throw(_("The service certificate template is inactive."))
	# The logo was checked when the administrator configured it. Applicants may
	# use the certificate design without being granted access to its private logo.
	return {
		"title": doc.certificate_title,
		"logo": logo_data(doc.certificate_logo),
		"footer": doc.footer_text or "",
		"tagline": doc.tagline or "",
		"identity_source": doc.identity_source,
		"template": template.name,
		"template_modified": str(template.modified),
		"body": template.body,
		"fields": [
			{
				"key": row.name,
				"source": row.source,
				"label": row.label,
				"placement": row.placement,
				"required": bool(row.required),
				"hide_if_empty": bool(row.hide_if_empty),
			}
			for row in doc.certificate_fields
			if cint(row.enabled)
		],
	}


def install():
	"""Seed once; never overwrite a society's fields, artwork or approval policy."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	from vmmsx.staff.services.permissions import _grant

	if not frappe.db.exists("DocType", SETTINGS):
		return
	create_custom_field(
		"National Society Settings",
		{
			"fieldname": SCOPE_FIELD,
			"label": "Service Certificate Review Role",
			"fieldtype": "Link",
			"options": "Role",
			"insert_after": "vmms_volunteer_scope_role",
			"description": "Role that reviews service certificates within its Geo Assignments.",
		},
		ignore_validate=True,
	)
	society = frappe.get_single("National Society Settings")
	if not society.get(SCOPE_FIELD) and society.get("vmms_volunteer_scope_role"):
		frappe.db.set_single_value(
			"National Society Settings", SCOPE_FIELD, society.vmms_volunteer_scope_role
		)
	role = frappe.db.get_single_value("National Society Settings", SCOPE_FIELD)
	if role and frappe.db.exists("Role", role):
		_grant(REQUEST, role, {"read": 1, "write": 1})
	if not frappe.db.exists("VMMS Template Category", "certificate"):
		frappe.get_doc(
			{
				"doctype": "VMMS Template Category",
				"category_key": "certificate",
				"category_name": "Certificate",
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("VMMS Template", TEMPLATE_KEY):
		frappe.get_doc(
			{
				"doctype": "VMMS Template",
				"template_key": TEMPLATE_KEY,
				"template_name": "Service Certificate",
				"template_category": "certificate",
				"is_active": 1,
				"output_format": "html",
				"subject": "Certificate of Service",
				"body": Path(
					frappe.get_app_path("vmmsx", "templating", "seeds", "service_certificate.html")
				).read_text(),
			}
		).insert(ignore_permissions=True)
	if not frappe.db.get_single_value(SETTINGS, "template"):
		doc = frappe.get_single(SETTINGS)
		doc.template = TEMPLATE_KEY
		for source, label, placement in DEFAULT_FIELDS:
			doc.append(
				"certificate_fields",
				{
					"source": source,
					"label": label,
					"placement": placement,
					"enabled": 1,
					"required": 1,
					"hide_if_empty": 1,
				},
			)
		doc.save(ignore_permissions=True)
	if role and not frappe.db.exists("VMMS Approval Workflow", {"workflow_for": REQUEST}):
		frappe.get_doc(
			{
				"doctype": "VMMS Approval Workflow",
				"workflow_for": REQUEST,
				"geo_node_field": "geo_node",
				"applicant_field": "red_profile",
				"allow_withdrawal": 0,
				"stages": [
					{
						"sequence": 1,
						"stage_label": "Service history review",
						"required_role": role,
						"resolution_rule": "nearest_ancestor",
						"completion_rule": "any_of",
						"can_reject": 1,
						"is_optional": 0,
						"sla_days": 5,
						"on_sla_breach": "notify_only",
					}
				],
			}
		).insert(ignore_permissions=True)
	frappe.clear_cache()
