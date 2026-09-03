# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The recruiter's half of an opening — advertising one, and deciding on it.

`openings.py` is the volunteer's board: browse here, apply there, and every card
leads outward. `application.py` is the applying. This is the third side, and it
is the one the console was missing entirely: a coordinator could publish an
opening only by going to the Frappe desk, and could read the people who answered
it only there too.

**The record stays HRMS's, and that is the whole point.** Nothing below invents
a vmmsx opening, a vmmsx applicant, a second status set or a second pipeline. It
writes `Job Opening` and `Job Applicant` through the ordinary document API, so a
society that also uses HRMS's own desk views sees exactly one truth, and an
interview scheduled there shows up here as the status it set. The console is a
better-shaped window onto HRMS's records for the one job a volunteer
coordinator actually does with them; it is not a fork of recruitment.

**What this file adds over `frappe.client` is a shape, and a bounded one.** Two
things a generic form cannot do: it counts the pipeline per opening in one read
rather than one per card, and it hands back a *curated* applicant — the fields a
volunteer coordinator decides on, with the snapshotted questions beside the
answers — rather than the whole `Job Applicant`, which carries a salary range
and a recruiter's private rating.

**Permission is HRMS's, asked through the framework.** Every listing is
`frappe.get_list` and every act is `check_permission`, so whoever a society has
made an HR Manager or Recruiter reaches these and nobody else does. This app
adds **no** geo scoping to either doctype: HRMS ships none, `vmms_geo_node` on an
opening is a label vmmsx puts there for its own board, and quietly turning it
into a permission boundary here would mean the console and the desk disagreeing
about who may see an opening. Where a coordinator should only see their own
branch's openings, that is a permission rule for the site to set on the doctype,
in one place, for both surfaces.

**Absent when HRMS is.** Every reader answers empty and every writer refuses in
a sentence, the same graceful-absence contract `openings.py` keeps: a society
running without HRMS has no recruitment tab, not a broken one.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from vmmsx.hr.services import openings as board
from vmmsx.setup import job_applicant_fields as applicant_fields
from vmmsx.setup import job_opening_fields as opening_fields

OPENING_DOCTYPE = "Job Opening"
APPLICANT_DOCTYPE = "Job Applicant"

#: HRMS's own statuses for an opening.
OPENING_STATUSES = ("Open", "Closed")

#: The pipeline, in the order a recruiter moves somebody through it. Withdrawn
#: is deliberately not among them — it is not a status HRMS holds, it is a date
#: field vmmsx adds, because a person taking themselves out is not a decision
#: the society made. See `setup/job_applicant_fields.py`.
PIPELINE = (
	applicant_fields.STATUS_OPEN,
	applicant_fields.STATUS_SHORTLISTED,
	applicant_fields.STATUS_HOLD,
	applicant_fields.STATUS_ACCEPTED,
	applicant_fields.STATUS_REJECTED,
)

#: A listing is a listing.
MAX_ROWS = 100

#: The fields the console's opening form owns. Anything else on `Job Opening` —
#: HRMS's salary range, its own notification plumbing — is edited on the desk.
#: Named as a tuple rather than accepting whatever the client sends, so this
#: endpoint cannot become a way to write an arbitrary field on somebody else's
#: doctype.
#:
#: **The screening block is here now, and it is vmmsx's own.** `enable_
#: autograding` and its neighbours are Custom Fields this app installs — see
#: `setup/job_opening_fields.py`, ported field for field from `onerc_vmms` — so
#: a coordinator writing an opening in the console was setting up half of one
#: and going to the desk for the half that decides who gets shortlisted. They
#: are ordinary scalars on the same document and they belong on the same form.
WRITABLE = (
	"job_title",
	"designation",
	"company",
	"department",
	"status",
	"publish",
	"description",
	"closes_on",
	"job_application_route",
	"location",
	"vacancies",
	"employment_type",
	opening_fields.PURPOSE_FIELD,
	# vmmsx's own description of the post, beyond HRMS's four link fields.
	"opportunity_type",
	"profession",
	"job_location",
	"vmms_geo_node",
	"vmms_project",
	"vmms_deployment",
	"vmms_available_from",
	"vmms_available_to",
	# --- what the opening screens for, and how hard ---------------------------
	"enable_autograding",
	"minimum_pass_score",
	"disqualify_if_requirement_not_met",
	"minimum_qualification_level",
	"allow_equivalent_experience",
	"required_gpa__grade",
	"preferred_field_of_study",
	"minimum_years_of_experience",
	"experience_area",
	"disqualify_if_below_minimum",
	# --- what happens to the people it turns down -----------------------------
	"enable_automatic_rejection_notifications",
	"send_rejection_email_immediately",
	"rejection_email_template",
	"notify_unshortlisted_applicants_after",
	"shortlisted_rejection_notification_date",
)

#: Numeric fields, so a blank box clears the number rather than storing "".
NUMERIC = (
	"minimum_pass_score",
	"minimum_years_of_experience",
)

#: Whole-number fields, same rule.
#:
#: `duration` is deliberately not among them and not in `WRITABLE`. It is
#: `read_only` on the doctype and documented as derived from `posted_on` and
#: `closes_on` — see `setup/job_opening_fields.py` — so a form control on it
#: would invite a coordinator to contradict a field nothing fills. `read_only`
#: is a form hint and the column stays writable, which is exactly why the
#: allow-list has to leave it out rather than rely on the flag.
INTEGER = (
	"vacancies",
	"notify_unshortlisted_applicants_after",
)

#: Tickboxes, which arrive from a browser as booleans.
CHECKS = (
	"publish",
	"enable_autograding",
	"disqualify_if_requirement_not_met",
	"allow_equivalent_experience",
	"disqualify_if_below_minimum",
	"enable_automatic_rejection_notifications",
	"send_rejection_email_immediately",
)

#: Dates.
DATES = (
	"closes_on",
	"vmms_available_from",
	"vmms_available_to",
	"shortlisted_rejection_notification_date",
)

#: The two child tables the console edits, and the field on each row that
#: carries the value. Both are Table MultiSelects, which is what makes the
#: screen's skill and language pickers the same control the volunteer
#: application uses.
MULTISELECT = {
	"vmms_desired_skills": "skill",
	"vmms_desired_languages": "language",
}

#: The child tables the console edits as rows rather than as chips, and the
#: columns of each that a coordinator fills in.
#:
#: Both are vmmsx's own doctypes, which is why they are here and
#: `required_skills`, `required_certification` and `required_licences` are not:
#: those three point at HRMS's `Designation Skill`, LMS's `Certification` and a
#: person-shaped `Personnel Licence` whose row marks an institution, a
#: qualification and a validity date mandatory. A requirement on an opening has
#: none of those, so a console form for it could only produce rows a coordinator
#: had to invent values for. They stay on the desk.
ROW_TABLES = {
	# What a candidate should hold, ranked rather than required — the same shape
	# a terms of reference uses for the same question.
	"vmms_desired_certifications": ("certification_type", "is_mandatory", "requirement_notes"),
	# What an applicant has to upload before the form will take their answer.
	"required_attachments": ("type", "document_name"),
}

#: The tickbox on a row, so it is stored as a flag rather than as `true`.
ROW_CHECKS = ("is_mandatory",)


def _absent() -> bool:
	return not board.is_available()


def _refuse_when_absent() -> None:
	if _absent():
		frappe.throw(
			_("Recruitment is not set up on this site."),
			title=_("Not Available"),
		)


# --- the openings ------------------------------------------------------------


def openings(
	search: str | None = None,
	status: str | None = None,
	purpose: str | None = None,
	limit: int = MAX_ROWS,
) -> dict:
	"""Every opening this person may read, with its pipeline counted.

	**Counted in one read, not one per card.** A board of twenty openings asking
	twenty count queries is how a list page becomes slow enough that somebody
	stops opening it. The counts come back from a single applicant listing keyed
	by opening, which also means the number on a card and the number on the
	pipeline behind it are the same number.
	"""
	if _absent():
		return {"available": False, "openings": [], "statuses": [], "totals": {}}

	filters: list[list] = []

	if status in OPENING_STATUSES:
		filters.append(["status", "=", status])
	if purpose in (opening_fields.PURPOSE_EMPLOYMENT, opening_fields.PURPOSE_VOLUNTEER):
		filters.append([opening_fields.PURPOSE_FIELD, "=", purpose])
	if search:
		filters.append(["job_title", "like", f"%{search.strip()}%"])

	rows = frappe.get_list(
		OPENING_DOCTYPE,
		filters=filters,
		fields=[
			"name",
			"job_title",
			"status",
			"publish",
			"designation",
			"department",
			"company",
			"location",
			"vacancies",
			"closes_on",
			"route",
			"creation",
			"modified",
			opening_fields.PURPOSE_FIELD,
			"vmms_geo_node",
			"vmms_project",
			"vmms_deployment",
		],
		order_by="modified desc",
		limit_page_length=_bounded(limit),
	)

	counts = _pipeline_counts([row["name"] for row in rows])

	openings_out = [
		{
			**row,
			"creation": str(row.get("creation") or ""),
			"modified": str(row.get("modified") or ""),
			"closes_on": str(row["closes_on"]) if row.get("closes_on") else None,
			"purpose": row.get(opening_fields.PURPOSE_FIELD),
			"is_published": bool(row.get("publish")),
			"is_closing": _is_closing(row.get("closes_on")),
			"url": board.opening_url(row.get("route")),
			"pipeline": counts.get(row["name"], _empty_pipeline()),
		}
		for row in rows
	]

	return {
		"available": True,
		"openings": openings_out,
		"statuses": list(OPENING_STATUSES),
		# The board's own headline figures, counted from the rows already
		# fetched so a card and the number above it cannot disagree.
		"totals": {
			"openings": len(openings_out),
			"published": len([row for row in openings_out if row["is_published"]]),
			"open": len([row for row in openings_out if row["status"] == "Open"]),
			"applicants": sum(row["pipeline"]["total"] for row in openings_out),
			"waiting": sum(row["pipeline"].get(applicant_fields.STATUS_OPEN, 0) for row in openings_out),
		},
	}


def detail(name: str) -> dict:
	"""One opening in full, as the console's own form edits it.

	Read through `get_doc` after a permission check rather than through
	`get_list`, because the form needs the child tables and a listing cannot
	carry them.
	"""
	_refuse_when_absent()

	doc = frappe.get_doc(OPENING_DOCTYPE, name)
	doc.check_permission("read")

	return {
		**{field: doc.get(field) for field in WRITABLE},
		"name": doc.name,
		"route": doc.get("route"),
		"url": board.opening_url(doc.get("route")),
		"apply_url": board.apply_url(doc.name, doc.get("job_application_route")),
		"purpose": doc.get(opening_fields.PURPOSE_FIELD),
		# Every date as a `YYYY-MM-DD` string, because a browser puts one straight
		# into a date input and a `datetime.date` reaching JSON is a shape it has
		# to unpick. Sliced rather than merely stringified: `closes_on` is a
		# *Datetime* — see `job_opening_fields.PROPERTIES` — and its
		# "2026-09-02 00:00:00" renders as an empty date input, so amending any
		# other field on an opening silently cleared its closing date.
		**{field: (str(doc.get(field))[:10] if doc.get(field) else None) for field in DATES},
		# Every tickbox as a boolean, for the same reason: a `checked` prop takes
		# one, and 0/1 through JSON is a value a form has to keep coercing.
		**{field: bool(doc.get(field)) for field in CHECKS},
		"is_published": bool(doc.get("publish")),
		**{
			table: [row.get(value_field) for row in doc.get(table) or []]
			for table, value_field in MULTISELECT.items()
		},
		**{
			table: [
				{
					column: (
						bool(row.get(column)) if column in ROW_CHECKS else row.get(column)
					)
					for column in columns
				}
				for row in doc.get(table) or []
			]
			for table, columns in ROW_TABLES.items()
		},
		# The screening questions as HRMS holds them — read-only here. They are
		# edited on the desk, and an application already decided against them
		# must not have its wording changed underneath it; see
		# `application.assert_questions_unlocked`.
		"screening_questions": [
			{
				"question_id": row.get("question_id"),
				"question": row.get("question"),
				"question_type": row.get("question_type"),
				"is_required": bool(row.get("is_required")),
			}
			for row in doc.get("screening_questions") or []
		],
		"pipeline": _pipeline_counts([doc.name]).get(doc.name, _empty_pipeline()),
		"can_write": bool(doc.has_permission("write")),
	}


def save(payload: dict, name: str | None = None) -> dict:
	"""Create an opening, or amend one. Returns the saved detail.

	One function for both, because the console draws one form for both and a
	second endpoint would be a second place for the field list to drift.

	**Only `WRITABLE` is written.** A key the client sends that is not on that
	tuple is dropped in silence rather than refused: the console posts the whole
	form back, and a society that adds a custom field to `Job Opening` on the
	desk should not find this endpoint throwing at it.
	"""
	_refuse_when_absent()

	payload = frappe.parse_json(payload) if isinstance(payload, str) else (payload or {})

	if name:
		doc = frappe.get_doc(OPENING_DOCTYPE, name)
		doc.check_permission("write")
	else:
		frappe.has_permission(OPENING_DOCTYPE, ptype="create", throw=True)
		doc = frappe.new_doc(OPENING_DOCTYPE)

	for field in WRITABLE:
		if field in payload:
			doc.set(field, _clean(field, payload[field]))

	for table, value_field in MULTISELECT.items():
		if table not in payload:
			continue

		doc.set(table, [])
		for value in payload[table] or []:
			if value:
				doc.append(table, {value_field: value})

	for table, columns in ROW_TABLES.items():
		if table not in payload:
			continue

		doc.set(table, [])
		for row in payload[table] or []:
			if not isinstance(row, dict):
				continue

			# The first column is what makes the row a row. A grid line somebody
			# tabbed through and left is dropped rather than saved empty, which
			# is the same bargain every other row editor in this app strikes.
			if not str(row.get(columns[0]) or "").strip():
				continue

			doc.append(
				table,
				{
					column: (
						(1 if cint(row.get(column)) else 0)
						if column in ROW_CHECKS
						else row.get(column)
					)
					for column in columns
				},
			)

	doc.save()

	return detail(doc.name)


def set_status(name: str, status: str) -> dict:
	"""Open or close an opening.

	Its own act rather than a field on `save`, because it is the one change to
	an opening that changes what the public sees, and a screen should be able to
	offer it as a button with a confirmation rather than as a select buried in a
	form.
	"""
	_refuse_when_absent()

	if status not in OPENING_STATUSES:
		frappe.throw(_("{0} is not a status an opening can be in.").format(status))

	doc = frappe.get_doc(OPENING_DOCTYPE, name)
	doc.check_permission("write")
	doc.status = status
	doc.save()

	return {"name": doc.name, "status": doc.status, "is_published": bool(doc.get("publish"))}


def set_published(name: str, published: bool) -> dict:
	"""Put an opening on the society's website, or take it off.

	Separate from `status` because they are genuinely different questions and
	HRMS keeps them apart: `status` is whether the society is still recruiting,
	`publish` is whether the advertisement is on the site at all. An opening can
	honestly be Open and unpublished — filled by invitation — and the board
	shows neither state as the other.
	"""
	_refuse_when_absent()

	doc = frappe.get_doc(OPENING_DOCTYPE, name)
	doc.check_permission("write")
	doc.publish = 1 if cint(published) else 0
	doc.save()

	return {
		"name": doc.name,
		"status": doc.status,
		"is_published": bool(doc.publish),
		"url": board.opening_url(doc.get("route")),
	}


# --- the applicants ----------------------------------------------------------


def applicants(
	opening: str | None = None,
	status: str | None = None,
	search: str | None = None,
	limit: int = MAX_ROWS,
) -> dict:
	"""The pipeline — everybody who has answered, in one list.

	`opening` narrows to one; without it this is every application the caller
	may read, which is the screen somebody opens on a Monday to see what came in
	over the weekend.
	"""
	if _absent():
		return {"available": False, "applicants": [], "counts": _empty_pipeline()}

	filters: list[list] = []

	if opening:
		filters.append(["job_title", "=", opening])
	if status in PIPELINE:
		filters.append(["status", "=", status])
	if search:
		filters.append(["applicant_name", "like", f"%{search.strip()}%"])

	rows = frappe.get_list(
		APPLICANT_DOCTYPE,
		filters=filters,
		fields=[
			"name",
			"applicant_name",
			"email_id",
			"phone_number",
			"status",
			"job_title",
			"creation",
			"modified",
			applicant_fields.VOLUNTEER_FIELD,
			applicant_fields.GEO_NODE_FIELD,
			applicant_fields.WITHDRAWN_FIELD,
		],
		order_by="creation desc",
		limit_page_length=_bounded(limit),
	)

	titles = _opening_titles({row["job_title"] for row in rows if row.get("job_title")})

	out = [
		{
			"name": row["name"],
			"applicant_name": row.get("applicant_name"),
			"email": row.get("email_id"),
			"phone": row.get("phone_number"),
			"status": row.get("status"),
			"opening": row.get("job_title"),
			"opening_title": titles.get(row.get("job_title")) or row.get("job_title"),
			"applied_on": str(row.get("creation") or ""),
			"modified": str(row.get("modified") or ""),
			"volunteer": row.get(applicant_fields.VOLUNTEER_FIELD),
			"geo_node": row.get(applicant_fields.GEO_NODE_FIELD),
			# A withdrawal is a date, not a status — so it is reported as its own
			# flag and the row keeps whatever status the society had reached.
			# A screen that overwrote "Shortlisted" with "Withdrawn" would lose
			# the fact that the society had said yes before the person left.
			"is_withdrawn": bool(row.get(applicant_fields.WITHDRAWN_FIELD)),
		}
		for row in rows
	]

	return {
		"available": True,
		"applicants": out,
		"statuses": list(PIPELINE),
		"counts": _count(out),
	}


def applicant(name: str) -> dict:
	"""One application, as the person deciding it needs to read it.

	**A curated document, never the raw one.** `Job Applicant` carries a salary
	range, a recruiter's rating and HRMS's own resume parsing; none of that is
	what a volunteer coordinator is deciding on, and passing the whole doc
	through would put a colleague's private note on a screen that was asked for
	an answer to a screening question.
	"""
	_refuse_when_absent()

	doc = frappe.get_doc(APPLICANT_DOCTYPE, name)
	doc.check_permission("read")

	opening_title = (
		frappe.db.get_value(OPENING_DOCTYPE, doc.job_title, "job_title") if doc.job_title else None
	)

	return {
		"name": doc.name,
		"applicant_name": doc.get("applicant_name"),
		"email": doc.get("email_id"),
		"phone": doc.get("phone_number"),
		"country": doc.get("country"),
		"status": doc.get("status"),
		"opening": doc.get("job_title"),
		"opening_title": opening_title or doc.get("job_title"),
		"applied_on": str(doc.creation) if doc.creation else None,
		"cover_letter": doc.get("cover_letter"),
		"resume_attachment": doc.get("resume_attachment"),
		"volunteer": doc.get(applicant_fields.VOLUNTEER_FIELD),
		"geo_node": doc.get(applicant_fields.GEO_NODE_FIELD),
		"is_withdrawn": bool(doc.get(applicant_fields.WITHDRAWN_FIELD)),
		"withdrawn_on": str(doc.get(applicant_fields.WITHDRAWN_FIELD) or "") or None,
		"withdrawal_reason": doc.get("vmms_withdrawal_reason"),
		# The questions as they were asked at the time, beside the answers. The
		# snapshot is the reason a decision made in March against wording
		# changed in January still reads correctly — see `application.py`.
		"answers": [
			{
				"question_id": row.get("question_id"),
				"question": row.get("question"),
				"question_type": row.get("question_type"),
				"answer": row.get("answer"),
				"answer_file": row.get("answer_file"),
			}
			for row in doc.get(applicant_fields.ANSWERS_FIELD) or []
		],
		# What accepting this application already produced, if anything. Present
		# so the screen can say "already placed" rather than offering a second
		# Convert that `application.convert` would refuse.
		"deployment_assignment": doc.get("vmms_deployment_assignment"),
		"task": doc.get("vmms_task"),
		"statuses": list(PIPELINE),
		"can_write": bool(doc.has_permission("write")),
	}


def set_applicant_status(name: str, status: str) -> dict:
	"""Move somebody along the pipeline.

	The one act this file performs on an application, and it is HRMS's own
	`status` field — not a parallel vmmsx state. Turning an accepted application
	into actual work is `application.convert`, deliberately a separate and
	idempotent act: saying yes and placing somebody are two decisions, and a
	society that says yes on Tuesday and places on Friday should be able to.
	"""
	_refuse_when_absent()

	if status not in PIPELINE:
		frappe.throw(_("{0} is not a status an application can be in.").format(status))

	doc = frappe.get_doc(APPLICANT_DOCTYPE, name)
	doc.check_permission("write")

	if doc.get(applicant_fields.WITHDRAWN_FIELD):
		frappe.throw(
			_("This person has withdrawn their application."),
			title=_("Withdrawn"),
		)

	doc.status = status
	doc.save()

	return {"name": doc.name, "status": doc.status}


# --- what the form offers ----------------------------------------------------


def options() -> dict:
	"""Every list the opening form draws a control from.

	One read for the whole form, like `api/volunteer.py::application_options`:
	six selects each fetching their own vocabulary is six chances for a form to
	render half-populated.
	"""
	if _absent():
		return {"available": False}

	return {
		"available": True,
		"statuses": list(OPENING_STATUSES),
		"purposes": [opening_fields.PURPOSE_VOLUNTEER, opening_fields.PURPOSE_EMPLOYMENT],
		"pipeline": list(PIPELINE),
		"designations": _vocabulary("Designation"),
		"departments": _vocabulary("Department", field="department_name"),
		"companies": _vocabulary("Company"),
		"employment_types": _vocabulary("Employment Type"),
		"skills": _vocabulary("VMMS Skill"),
		"languages": _vocabulary("Language", field="language_name"),
		"projects": _vocabulary("Project", field="project_name"),
		# vmmsx's own vocabularies for the fields it installs on the opening.
		"professions": _vocabulary("Profession"),
		"locations": _vocabulary("Location"),
		"certification_types": _vocabulary(
			"VMMS Certification Type", field="certification_type_name"
		),
		"document_types": _vocabulary("Supporting Document Type"),
		"email_templates": _vocabulary("Email Template"),
		# The two Selects vmmsx installs, read off the fields themselves so a
		# society that edits either edits the form with it.
		"opening_types": _select_options("opportunity_type"),
		"qualification_levels": _select_options("minimum_qualification_level"),
	}


def _select_options(fieldname: str) -> list[str]:
	"""A Select field's own words, or nothing before its patch has run.

	These are Custom Fields, so a site between syncing this module and running
	`patches/install_job_opening_fields.py` has the doctype and not the field —
	the same graceful absence `_vocabulary` keeps, for the same reason.
	"""
	field = frappe.get_meta(OPENING_DOCTYPE).get_field(fieldname)

	if not field:
		return []

	return [option.strip() for option in (field.options or "").split("\n") if option.strip()]


def _vocabulary(doctype: str, field: str | None = None) -> list[dict]:
	"""A link field's options, or nothing when the doctype is not on this site.

	Graceful absence again: `Project` is ERPNext's, `Language` is the
	framework's, `Designation` is HRMS's. A society missing one gets a control
	with no options rather than a form that fails to load.
	"""
	if not frappe.db.exists("DocType", doctype):
		return []

	try:
		rows = frappe.get_all(
			doctype,
			fields=["name"] + ([field] if field else []),
			order_by="name asc",
			limit_page_length=500,
		)
	except frappe.PermissionError:
		return []

	return [
		{"value": row["name"], "label": (row.get(field) if field else None) or row["name"]} for row in rows
	]


# --- counting ----------------------------------------------------------------


def _pipeline_counts(names: list[str]) -> dict[str, dict]:
	"""Every named opening's pipeline, from one applicant listing."""
	if not names:
		return {}

	rows = frappe.get_list(
		APPLICANT_DOCTYPE,
		filters=[["job_title", "in", names]],
		fields=["job_title", "status", applicant_fields.WITHDRAWN_FIELD],
		limit_page_length=0,
	)

	counts: dict[str, dict] = {name: _empty_pipeline() for name in names}

	for row in rows:
		bucket = counts.setdefault(row["job_title"], _empty_pipeline())
		bucket["total"] += 1

		if row.get(applicant_fields.WITHDRAWN_FIELD):
			bucket["withdrawn"] += 1
			continue

		status = row.get("status")
		if status in bucket:
			bucket[status] += 1

	return counts


def _count(rows: list[dict]) -> dict:
	"""The same shape as `_pipeline_counts`, over rows already in hand."""
	bucket = _empty_pipeline()

	for row in rows:
		bucket["total"] += 1

		if row.get("is_withdrawn"):
			bucket["withdrawn"] += 1
			continue

		if row.get("status") in bucket:
			bucket[row["status"]] += 1

	return bucket


def _empty_pipeline() -> dict:
	return {"total": 0, "withdrawn": 0, **{status: 0 for status in PIPELINE}}


def _opening_titles(names: set[str]) -> dict[str, str]:
	if not names:
		return {}

	return {
		row["name"]: row.get("job_title") or row["name"]
		for row in frappe.get_all(
			OPENING_DOCTYPE,
			filters={"name": ("in", list(names))},
			fields=["name", "job_title"],
			ignore_permissions=True,
		)
	}


def _is_closing(closes_on) -> bool:
	"""Is this opening's closing date within the week?

	A flag rather than a number of days, so the screen decides how to say it and
	this file does not end up owning a phrase.
	"""
	if not closes_on:
		return False

	return 0 <= (getdate(closes_on) - getdate()).days <= 7


def _clean(field: str, value):
	"""One field's value, as the doctype wants it.

	Blank clears rather than storing an empty string: a `Float` holding "" is a
	column the desk cannot read back, and a coordinator emptying a pass score is
	saying there is no pass score rather than saying it is nothing.
	"""
	if field in CHECKS:
		return 1 if cint(value) else 0
	if field in INTEGER:
		return cint(value) or None
	if field in NUMERIC:
		return flt(value) if str(value or "").strip() else None
	if field in DATES:
		return getdate(value) if value else None

	return value


def _bounded(limit) -> int:
	try:
		asked = int(limit)
	except TypeError, ValueError:
		return MAX_ROWS

	return max(1, min(asked, MAX_ROWS))
