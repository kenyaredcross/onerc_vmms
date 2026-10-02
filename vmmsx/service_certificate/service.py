"""Owned requests, scoped review and immutable certificate issues."""

import json
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import cint, flt, format_date, get_datetime, getdate, nowdate
from onerc_core.geo.services import adapter

from vmmsx.approvals import states
from vmmsx.approvals.services import contract, engine
from vmmsx.notifications.services import direct
from vmmsx.service_certificate import settings
from vmmsx.templating.services import render
from vmmsx.volunteer.services import identity

REQUEST = settings.REQUEST
FROZEN = (
	"red_profile",
	"applicant_name",
	"applicant_kind",
	"volunteer",
	"member",
	"membership",
	"geo_node",
	"request_date",
	"service_from",
	"service_to",
	"position",
	"service_summary",
	"custom_values",
	"configuration",
)
ISSUED = (
	"issued_on",
	"issued_by",
	"certificate_context",
	"certificate_html",
	"certificate_file",
	"generation_status",
	"service_evidence",
)


def parsed(value):
	return frappe.parse_json(value) if isinstance(value, str) else (value or {})


def comparable(doc, field):
	value = doc.get(field)
	kind = doc.meta.get_field(field).fieldtype
	if kind == "JSON":
		return parsed(value)
	if kind == "Date" and value:
		return getdate(value)
	if kind == "Datetime" and value:
		return get_datetime(value)
	return value or ""


@contextmanager
def writing():
	previous = frappe.flags.service_certificate_write
	frappe.flags.service_certificate_write = True
	try:
		yield
	finally:
		frappe.flags.service_certificate_write = previous


def my_profile():
	if frappe.session.user == "Guest":
		frappe.throw(_("Sign in to request a certificate."), frappe.PermissionError)
	return frappe.db.get_value("Red Profile", {"user": frappe.session.user}, "name")


def holder(doc):
	return frappe.db.get_value("Red Profile", doc.red_profile, "user")


def readable(name, review=False):
	doc = frappe.get_doc(REQUEST, name)
	if not review and holder(doc) == frappe.session.user and frappe.session.user != "Guest":
		return doc
	doc.check_permission("read")
	return doc


def options():
	profile = my_profile()
	choices = []
	if profile:
		for row in frappe.get_all(
			"VMMS Volunteer",
			filters={"red_profile": profile, "status": ["!=", "Prospective"]},
			fields=["name", "home_geo_node", "joined_on"],
		):
			if row.home_geo_node:
				choices.append(
					{
						"kind": "Volunteer",
						"record": row.name,
						"branch": adapter.get_full_path(row.home_geo_node),
						"joined_on": row.joined_on,
					}
				)
		member = frappe.db.get_value("VMMS Member", {"red_profile": profile}, "name")
		if member:
			for row in frappe.get_all(
				"VMMS Membership",
				filters={"member": member, "membership_status": ["in", ["Active", "Expired", "Cancelled"]]},
				fields=["name", "geo_node", "valid_from"],
			):
				if row.geo_node and row.valid_from:
					choices.append(
						{
							"kind": "Member",
							"record": row.name,
							"branch": adapter.get_full_path(row.geo_node),
							"joined_on": row.valid_from,
						}
					)
	doc = frappe.get_single(settings.SETTINGS)
	return {
		"choices": choices,
		"applicant_name": frappe.db.get_value("Red Profile", profile, "full_name") if profile else "",
		"today": nowdate(),
		"custom_fields": [
			{"key": row.name, "label": row.label, "required": bool(row.required)}
			for row in doc.certificate_fields
			if row.enabled and row.source == "custom_value"
		],
	}


def create(kind, record, service_from, service_to, position=None, service_summary=None, custom_values=None):
	profile = my_profile()
	if not profile:
		frappe.throw(_("A registered member or volunteer profile is required."), frappe.PermissionError)
	# Serialize submissions by the actual applicant, including two browser tabs.
	frappe.db.get_value("Red Profile", profile, "name", for_update=True)
	choice = next((c for c in options()["choices"] if c["kind"] == kind and c["record"] == record), None)
	if not choice:
		frappe.throw(_("Choose one of your own member or volunteer registrations."), frappe.PermissionError)
	if frappe.db.exists(
		REQUEST, {"red_profile": profile, "approval_state": ["in", list(states.OPEN_STATES)]}
	):
		frappe.throw(_("You already have a certificate request awaiting a decision."))
	if frappe.db.exists(
		REQUEST,
		{
			"red_profile": profile,
			"service_from": service_from,
			"service_to": service_to,
			"approval_state": states.APPROVED,
		},
	):
		frappe.throw(
			_("A certificate for this period is already approved. Download it from your request history.")
		)
	volunteer = frappe.db.get_value("VMMS Volunteer", {"red_profile": profile}, "name")
	member = frappe.db.get_value("VMMS Member", {"red_profile": profile}, "name")
	if kind == "Volunteer":
		geo_node = frappe.db.get_value("VMMS Volunteer", record, "home_geo_node")
	else:
		geo_node = frappe.db.get_value("VMMS Membership", record, "geo_node")
	configuration = settings.snapshot()
	identifications = identity.identifications(frappe._dict(red_profile=profile))
	configuration["facts"] = {
		"applicant_name": frappe.db.get_value("Red Profile", profile, "full_name"),
		"id_number": record
		if configuration["identity_source"] == "Registration number"
		else (identifications[0]["id_number"] if identifications else ""),
		"engagement_date": str(choice["joined_on"] or ""),
		"branch": adapter.get_full_path(geo_node),
	}
	allowed = {row["key"] for row in configuration["fields"] if row["source"] == "custom_value"}
	answers = parsed(custom_values)
	if not isinstance(answers, dict) or set(answers) - allowed:
		frappe.throw(_("The additional certificate fields have changed. Reopen the request form."))
	if any(not isinstance(value, str) or len(value) > 160 for value in answers.values()):
		frappe.throw(_("Additional certificate answers must be text of at most 160 characters."))
	doc = frappe.get_doc(
		{
			"doctype": REQUEST,
			"red_profile": profile,
			"applicant_kind": kind,
			"volunteer": volunteer,
			"member": member,
			"membership": record if kind == "Member" else None,
			"applicant_name": configuration["facts"]["applicant_name"],
			"geo_node": geo_node,
			"request_date": nowdate(),
			"service_from": service_from,
			"service_to": service_to,
			"position": (position or "").strip(),
			"service_summary": (service_summary or "").strip(),
			"custom_values": json.dumps(answers),
			"configuration": json.dumps(configuration),
		}
	)
	with writing():
		doc.insert(ignore_permissions=True)
	# Establishing ownership is the permission to submit this one document.
	doc.flags.ignore_permissions = True
	engine.submit(doc)
	return dto(doc)


def validate(doc):
	before = doc.get_doc_before_save()
	if doc.is_new():
		if not frappe.flags.service_certificate_write or doc.approval_state != states.DRAFT:
			frappe.throw(
				_("Submit certificate requests through the member or volunteer portal."),
				frappe.PermissionError,
			)
	else:
		for field in FROZEN:
			if comparable(doc, field) != comparable(before, field):
				frappe.throw(_("Submitted certificate request details cannot be changed."))
		approval_fields = ("approval_state", "approval_stage", "approval_stage_entered_on")
		decision_fields = ("stage", "stage_label", "stage_sequence", "approver", "decision", "reason", "decided_on")
		decisions_changed = [[comparable(r, f) for f in decision_fields] for r in doc.approval_decisions] != [
			[comparable(r, f) for f in decision_fields] for r in before.approval_decisions
		]
		if decisions_changed or any(comparable(doc, f) != comparable(before, f) for f in approval_fields):
			if frappe.flags.vmms_approval_transition != (doc.doctype, doc.name):
				frappe.throw(
					_("Use the certificate review actions to record a decision."), frappe.PermissionError
				)
		if (
			decisions_changed
			and len(doc.approval_decisions) > len(before.approval_decisions)
			and holder(doc) == frappe.session.user
		):
			frappe.throw(_("You cannot decide your own certificate request."), frappe.PermissionError)
		if not frappe.flags.service_certificate_write and any(
			comparable(doc, f) != comparable(before, f) for f in (*ISSUED, "review_note")
		):
			frappe.throw(_("Certificate issue details are maintained by the system."), frappe.PermissionError)
	if getdate(doc.service_from) > getdate(doc.service_to) or getdate(doc.service_to) > getdate(nowdate()):
		frappe.throw(_("Choose a valid service period ending on or before today."))
	if len(doc.position or "") > 140 or len(doc.service_summary or "") > 1000:
		frappe.throw(_("Use at most 140 characters for the position and 1,000 for supporting information."))
	if contract.state(doc) == states.APPROVED and (not before or contract.state(before) != states.APPROVED):
		if holder(doc) == frappe.session.user:
			frappe.throw(_("You cannot approve your own certificate request."), frappe.PermissionError)
		if not doc.approval_decisions or doc.approval_decisions[-1].decision != states.DECISION_APPROVED:
			frappe.throw(_("A service certificate requires a recorded reviewer approval."))
		if not (doc.review_note or "").strip():
			frappe.throw(_("Record how you verified the applicant's service before approving."))
		doc.issued_on = nowdate()
		doc.issued_by = frappe.session.user
		doc.service_evidence = frappe.as_json(history(doc))
		context = context_for(doc)
		doc.certificate_context = json.dumps(context)
		doc.certificate_html = render.render_string(parsed(doc.configuration)["body"], context)
		doc.generation_status = "Generating"
	elif doc.is_new():
		# Catch missing required identity/position/custom values while the applicant
		# can still correct the form. Issue-time values are placeholders for this check.
		context_for(doc, checking=True)


def on_update(doc):
	before = doc.get_doc_before_save()
	previous = contract.state(before) if before else states.DRAFT
	current = contract.state(doc)
	if current == previous:
		return
	if current == states.APPROVED:
		frappe.enqueue(
			"vmmsx.service_certificate.service.generate",
			name=doc.name,
			enqueue_after_commit=True,
			job_id=f"service-certificate-{doc.name}",
		)
	if current in (states.REJECTED, states.APPROVED):
		direct.tell(
			[holder(doc)],
			_("Your service certificate request was {0}.").format(current.lower()),
			REQUEST,
			doc.name,
			link=portal_link(doc),
		)


def prevent_delete(doc):
	if contract.state(doc) != states.DRAFT:
		frappe.throw(_("Submitted service certificate requests are retained as a service record."))


def portal_link(doc):
	return "/portal/profile" if doc.applicant_kind == "Volunteer" else "/portal/membership"


def history(doc):
	"""Only service in the request's branch and requested period is certified."""
	if doc.get("service_evidence"):
		return [frappe._dict(row) for row in parsed(doc.service_evidence)]
	if not doc.volunteer:
		return []
	return frappe.get_all(
		"VMMS Time Log",
		filters={
			"volunteer": doc.volunteer,
			"geo_node": doc.geo_node,
			"activity_date": ["between", [doc.service_from, doc.service_to]],
		},
		fields=["name", "activity_date", "hours", "log_category", "deployment", "source_assignment", "notes"],
		order_by="activity_date asc, name asc",
	)


def context_for(doc, checking=False):
	config = parsed(doc.configuration)
	answers = parsed(doc.custom_values)
	facts = config["facts"]
	values = {
		**facts,
		"engagement_date": format_date(facts["engagement_date"]) if facts["engagement_date"] else "",
		"issue_date": format_date(doc.issued_on or nowdate()),
		"position": doc.position or "",
		"service_period": f"{format_date(doc.service_from)} - {format_date(doc.service_to)}",
		"service_hours": str(flt(sum(flt(row.hours) for row in history(doc)))),
		"certificate_number": doc.name or "Preview",
		"service_summary": doc.service_summary or "",
		"signatory": "Reviewer"
		if checking
		else (frappe.db.get_value("User", doc.issued_by, "full_name") or doc.issued_by or ""),
	}
	rows = {"Header": [], "Body": [], "Signature": []}
	for field in config["fields"]:
		value = (
			answers.get(field["key"], "")
			if field["source"] == "custom_value"
			else values.get(field["source"], "")
		)
		if field["required"] and not str(value or "").strip():
			frappe.throw(_("A value is required for certificate field: {0}.").format(field["label"]))
		if not value and field["hide_if_empty"]:
			continue
		rows[field["placement"]].append({"label": field["label"], "value": str(value or "")})
	return {
		"title": config["title"],
		"logo": config["logo"],
		"footer": config["footer"],
		"tagline": config["tagline"],
		"header_fields": rows["Header"],
		"body_fields": rows["Body"],
		"signature_fields": rows["Signature"],
		"certificate_number": doc.name or "Preview",
	}


def dto(doc):
	state = contract.state(doc)
	owner = holder(doc) == frappe.session.user
	return {
		"name": doc.name,
		"applicant_name": doc.applicant_name,
		"applicant_kind": doc.applicant_kind,
		"branch": parsed(doc.configuration)["facts"]["branch"],
		"request_date": doc.request_date,
		"service_from": doc.service_from,
		"service_to": doc.service_to,
		"position": doc.position,
		"service_summary": doc.service_summary,
		"review_note": doc.review_note,
		"status": "Pending" if state in states.OPEN_STATES else state,
		"generation_status": doc.generation_status,
		"can_review": not owner and state == states.IN_REVIEW and engine.may_act(doc),
		"can_generate": not owner
		and state == states.APPROVED
		and not doc.certificate_file
		and doc.has_permission("write"),
		"can_download": bool(doc.certificate_file),
		"decisions": [
			{"decision": r.decision, "reason": r.reason, "decided_on": r.decided_on}
			for r in doc.approval_decisions
		],
	}


def decide(name, decision, reason=None, review_note=None):
	frappe.db.get_value(REQUEST, name, "name", for_update=True)
	doc = readable(name, review=True)
	doc.check_permission("write")
	if holder(doc) == frappe.session.user:
		frappe.throw(_("You cannot decide your own certificate request."), frappe.PermissionError)
	if decision not in (states.DECISION_APPROVED, states.DECISION_REJECTED):
		frappe.throw(_("Choose Approve or Reject."))
	with writing():
		if decision == states.DECISION_APPROVED:
			doc.review_note = (review_note or "").strip()
		engine.decide(doc, decision, reason)
	return dto(doc)


def generate(name):
	"""Worker/retry implementation. Locked and idempotent; the HTTP API gates retry."""
	from frappe.utils.file_manager import save_file
	from frappe.utils.pdf import get_pdf

	frappe.db.get_value(REQUEST, name, "name", for_update=True)
	doc = frappe.get_doc(REQUEST, name)
	if contract.state(doc) != states.APPROVED or not doc.certificate_html:
		frappe.throw(_("Only an approved request can produce a certificate."))
	if doc.certificate_file:
		return doc.certificate_file
	try:
		pdf = get_pdf(
			doc.certificate_html,
			options={
				"page-size": "Letter",
				"orientation": "Landscape",
				"margin-top": "0",
				"margin-bottom": "0",
				"margin-left": "0",
				"margin-right": "0",
			},
		)
		file = save_file(f"service-certificate-{doc.name}.pdf", pdf, REQUEST, doc.name, is_private=1)
		frappe.db.set_value(REQUEST, doc.name, {"certificate_file": file.name, "generation_status": "Ready"})
	except Exception:
		frappe.log_error(title="Service certificate generation failed", message=frappe.get_traceback())
		frappe.db.set_value(REQUEST, doc.name, "generation_status", "Failed")
		return None
	direct.tell(
		[holder(doc)],
		_("Your Certificate of Service is ready to download."),
		REQUEST,
		doc.name,
		link=portal_link(doc),
	)
	return file.name
