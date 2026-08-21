# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Reading a Terms of Reference — the few things on it that code reads.

A `VMMS Terms of Reference` is a society's mission document: one per piece of
work it deploys volunteers to do. Most of what is on it — the background, the
objectives, the outputs, the approach, the itinerary, the stakeholders, the
resources — is for the people involved, and this module deliberately decides
nothing from any of it. Four fields govern behaviour:

    geo_scope                where these terms may be used. Empty means anywhere
    approval_mode            whether a request under them needs an approver
    required_certifications  what a candidate must, or would ideally, hold
    expected_start_date      what a deployment set up under them defaults to

**Submitted, then offered.** Accepting a deployment assignment is accepting
these terms — there is no separate contract, because the terms are the contract
— so the wording is frozen on submit and only submitted terms take new work.
`assert_offered` is the one predicate that asks both questions; `assert_active`
and `assert_submitted` answer half of it each, for callers that genuinely want
one half.

**No qualification is named here or anywhere else in this app.** A requirement
is a Link to the society's own `VMMS Certification Type`, and whether a lapse of
it blocks deployment is that type's own configured answer. This module hands
back keys; `matching.py` asks `volunteer/services/certification.py` what they
mean on a given date.

**Containment is core's, never a depth assumption.** `assert_within_scope` calls
the geo adapter's `matches_scope`, which compares nested-set bounds, so a
society whose tree is four levels deep and one whose tree is two behave the same
and neither is written down.
"""

import frappe
from frappe import _

from vmmsx.deployment.services import approval
from vmmsx.deployment.services import project as project_service

TERMS_DOCTYPE = "VMMS Terms of Reference"


def read(terms_of_reference: str):
	"""The terms record, through the document cache.

	Configuration read on every deployment, every request and every candidate
	search, and changed a few times a year. Callers must treat the result as
	read-only; it is a shared object.
	"""
	return frappe.get_cached_doc(TERMS_DOCTYPE, terms_of_reference)


# --- the approval mode ----------------------------------------------------


def approval_mode(terms_of_reference: str) -> str:
	"""Whether a request under these terms is routed for approval, or direct."""
	terms = read(terms_of_reference)

	return approval.assert_mode(terms.approval_mode, _describe(terms))


def assert_approval_mode(terms) -> None:
	"""Refuse a mode nobody wrote a rule for. Called from the controller's validate.

	Takes the document rather than a name because it runs while the document is
	being saved, and the cached copy is the one before this edit.
	"""
	approval.assert_mode(terms.approval_mode, _describe(terms))


def _describe(terms) -> str:
	"""How a message refers to these terms: the society's own words for them."""
	return terms.tor_name or terms.name


# --- where they may be used -----------------------------------------------


def assert_within_scope(terms_of_reference: str, geo_node: str) -> None:
	"""Throw unless `geo_node` falls inside these terms' own geo scope.

	Empty scope is unconstrained, which is what a society that has not narrowed
	its terms means. Where a scope is set, the node must be that node or beneath
	it: an ancestor is not inside it, which is why `allow_ancestor` is off.
	Anchoring a deployment at the region when its terms are a particular branch's
	would put the work outside the very place the terms describe.
	"""
	from onerc_core.geo.services import adapter

	if not (terms_of_reference and geo_node):
		return

	terms = read(terms_of_reference)

	if not terms.geo_scope:
		return

	if adapter.matches_scope(geo_node, terms.geo_scope, allow_ancestor=False):
		return

	frappe.throw(
		_("{0} applies within {1}. {2} is outside it.").format(
			frappe.bold(_describe(terms)),
			frappe.bold(adapter.get_full_path(terms.geo_scope)),
			frappe.bold(adapter.get_full_path(geo_node)),
		),
		frappe.ValidationError,
		title=_("Outside These Terms"),
	)


def assert_active(terms_of_reference: str) -> None:
	"""Throw unless these terms are still offered for new work.

	Checked when a deployment or a request is created and never afterwards. An
	inactive terms of reference keeps everything already run under it, because
	retiring a piece of work must not erase the record that it happened.
	"""
	terms = read(terms_of_reference)

	if terms.is_active:
		return

	frappe.throw(
		_("{0} is not active and cannot take new deployments or requests.").format(
			frappe.bold(_describe(terms))
		),
		frappe.ValidationError,
		title=_("Inactive Terms of Reference"),
	)


def assert_submitted(terms_of_reference: str) -> None:
	"""Throw unless these terms have been submitted.

	A draft is still being written. Somebody who accepts a deployment under it
	would be accepting wording that can change afterwards, which is the one thing
	submitting exists to prevent, so draft terms take no deployments and no
	requests. A cancelled one is refused by the same check and for a blunter
	reason: it is a document the society has withdrawn entirely.
	"""
	terms = read(terms_of_reference)

	if terms.docstatus == 1:
		return

	if terms.docstatus == 2:
		frappe.throw(
			_("{0} has been cancelled and cannot take new deployments or requests.").format(
				frappe.bold(_describe(terms))
			),
			frappe.ValidationError,
			title=_("Cancelled Terms of Reference"),
		)

	frappe.throw(
		_(
			"{0} is still a draft. Submit it before deploying anybody under it — a volunteer"
			" accepting an assignment is accepting these terms, and terms that can still be"
			" edited are not terms anybody can agree to."
		).format(frappe.bold(_describe(terms))),
		frappe.ValidationError,
		title=_("Terms of Reference Not Submitted"),
	)


def assert_offered(terms_of_reference: str) -> None:
	"""Throw unless these terms take new work: submitted, and still active.

	The one predicate the deployment and request services ask. Submitted first,
	because "this is still a draft" is the more useful thing to hear about a
	terms of reference that is both a draft and inactive.
	"""
	assert_submitted(terms_of_reference)
	assert_active(terms_of_reference)


# --- what a candidate needs -----------------------------------------------


def requirements(terms_of_reference: str) -> dict:
	"""The certification requirements, split by how hard they are.

	    mandatory  keys a candidate must hold, unlapsed, to be a candidate at all
	    desirable  keys that rank a candidate higher but exclude nobody

	Returned as two lists of `VMMS Certification Type` keys rather than as rows,
	so a caller cannot accidentally start reading a field off a requirement that
	this module has not decided is meaningful.
	"""
	terms = read(terms_of_reference)
	mandatory, desirable = [], []

	for row in terms.required_certifications or []:
		if not row.certification_type:
			continue

		(mandatory if row.is_mandatory else desirable).append(row.certification_type)

	return {"mandatory": mandatory, "desirable": desirable}


def create(
	tor_name: str,
	project: str | None = None,
	purpose: str | None = None,
	mission_background: str | None = None,
	responsibilities: str | None = None,
	geo_scope: str | None = None,
	expected_start_date: str | None = None,
	expected_end_date: str | None = None,
	default_duration_days: int | None = None,
	approval_mode: str | None = None,
	required_certifications: list | None = None,
	stakeholders: list | None = None,
	objectives: list | None = None,
	expected_outputs: list | None = None,
	approach_methods: list | None = None,
	itinerary: list | None = None,
	resources: list | None = None,
	notes: str | None = None,
	submit: bool = False,
):
	"""Write a terms of reference. An ordinary insert, like every other creation here.

	**The key is derived, never asked for.** `tor_key` is the docname and a
	society writing one on a screen has no reason to invent a slug, so this makes
	one from the name and disambiguates it against what the site already holds.
	The name it derives from is display text and may be rewritten next year; the
	key it produced is what deployments point at, and never moves afterwards.

	`approval_mode` defaults to direct because a society that has not configured
	an approval workflow for deployment requests would otherwise write terms that
	refuse every request raised under them. Choosing routed is a deliberate act
	and the controller checks it.

	**It is left as a draft unless the caller asks otherwise.** A mission document
	is written over several sittings — the background one day, the itinerary once
	the branch has answered — and submitting it is the deliberate act that says
	the wording is final and people may now be asked to agree to it. The screens
	draw those as two buttons for exactly that reason.

	Every child list is normalised here rather than passed through, so a caller
	that hands over an extra key does not silently write a field nobody reviewed.
	"""
	if project:
		# Refused before the insert rather than after it, so a closed programme
		# never leaves a half-written terms of reference behind.
		project_service.assert_open(project)

	doc = frappe.get_doc(
		{
			"doctype": TERMS_DOCTYPE,
			"tor_key": _unique_key(tor_name),
			"tor_name": tor_name,
			"project": project or None,
			"is_active": 1,
			"purpose": purpose,
			"mission_background": mission_background,
			"responsibilities": responsibilities,
			"geo_scope": geo_scope or None,
			"expected_start_date": expected_start_date or None,
			"expected_end_date": expected_end_date or None,
			"default_duration_days": frappe.utils.cint(default_duration_days),
			"approval_mode": approval_mode or approval.MODE_DIRECT,
			"notes": notes,
			"required_certifications": [
				{
					"certification_type": row.get("certification_type"),
					"is_mandatory": 1 if row.get("is_mandatory") else 0,
				}
				for row in (required_certifications or [])
				if row.get("certification_type")
			],
			**mission_rows(
				stakeholders=stakeholders,
				objectives=objectives,
				expected_outputs=expected_outputs,
				approach_methods=approach_methods,
				itinerary=itinerary,
				resources=resources,
			),
		}
	)
	doc.insert()

	if submit:
		doc.submit()

	return doc


# The six mission tables, each with the keys this app will copy off a caller's
# row and no others. Kept as data rather than as six near-identical loops so
# that adding a column to a mission table is one line here, and so that no
# caller can write a field by guessing its name.
_MISSION_TABLES: dict[str, tuple[str, ...]] = {
	"stakeholders": ("designation", "full_name", "phone_number", "email"),
	"objectives": ("objective",),
	"expected_outputs": ("output",),
	"approach_methods": ("methodology", "notes"),
	"itinerary": ("activity_date", "activity_time", "activity", "person_responsible"),
	"resources": ("resource", "needed_on", "quantity", "unit", "unit_cost", "donor"),
}

# The column of each mission table that makes a row worth keeping. A row whose
# one substantive field is blank is a grid row somebody tabbed through, not an
# objective they meant to write, and it is dropped rather than saved empty.
_MISSION_REQUIRED: dict[str, str] = {
	"stakeholders": "designation",
	"objectives": "objective",
	"expected_outputs": "output",
	"approach_methods": "methodology",
	"itinerary": "activity",
	"resources": "resource",
}


def mission_rows(**tables: list | None) -> dict[str, list[dict]]:
	"""Normalise the mission tables a caller passed, dropping the empty rows.

	Shared by `create` and by `update` so that writing a terms of reference and
	editing one cannot disagree about which columns exist. `total_cost` is
	deliberately not among them: it is derived on the parent's validate, and a
	caller that could set it could make it disagree with the two numbers it comes
	from.
	"""
	written: dict[str, list[dict]] = {}

	for field, rows in tables.items():
		if rows is None:
			continue

		columns = _MISSION_TABLES[field]
		required = _MISSION_REQUIRED[field]

		written[field] = [
			{key: row.get(key) for key in columns}
			for row in rows
			if isinstance(row, dict) and str(row.get(required) or "").strip()
		]

	return written


def _unique_key(tor_name: str) -> str:
	"""A stable business key derived from the society's own words for the work.

	Slugged rather than scrubbed of anything in particular: a society writing in
	a non-Latin script gets a key of digits, which is opaque and unique and reads
	no worse than an invented one. The suffix loop is what makes two branches
	naming their terms the same thing two records rather than a clash on save.
	"""
	base = frappe.scrub(frappe.utils.strip_html(tor_name or "")).strip("_") or "terms"
	candidate, suffix = base, 1

	while frappe.db.exists(TERMS_DOCTYPE, candidate):
		suffix += 1
		candidate = f"{base}_{suffix}"

	return candidate


def _project_name(project: str | None) -> str | None:
	"""What the project is called, or None. Never raises on a deleted link."""
	if not project:
		return None

	return frappe.db.get_value("VMMS Project", project, "project_name")


def dto(terms_of_reference: str) -> dict:
	"""One terms of reference in summary, as an explicit dict. Built field by field.

	Never the Document: that would leak every field on the record, including ones
	nobody reviewed, and turn a schema change into an API change.

	**The mission tables are not here, and that is deliberate.** This shape is
	embedded verbatim inside every `deployment_dto()`, so anything added to it is
	paid for on every deployment read in the app. The stakeholders, objectives,
	outputs, approach, itinerary and resources — and the background, which is a
	whole rich-text document — belong to whoever is reading the mission itself,
	and they get them from `mission_dto` at the one call site that wants them.
	What is here is the summary a list row, a breadcrumb or a deployment header
	needs, plus the four fields code actually branches on.
	"""
	from onerc_core.geo.services import adapter

	terms = read(terms_of_reference)
	needed = requirements(terms_of_reference)

	return {
		"name": terms.name,
		"tor_key": terms.tor_key,
		"tor_name": terms.tor_name,
		"is_active": bool(terms.is_active),
		# The submit state, split into the two questions a screen actually asks
		# rather than handed over as a docstatus integer for every caller to
		# remember the meaning of. A draft may still be edited and takes no
		# deployments; a submitted one is frozen and does.
		"docstatus": terms.docstatus,
		"is_draft": terms.docstatus == 0,
		"is_submitted": terms.docstatus == 1,
		"is_cancelled": terms.docstatus == 2,
		"is_offered": terms.docstatus == 1 and bool(terms.is_active),
		"amended_from": terms.amended_from,
		"expected_start_date": terms.expected_start_date,
		"expected_end_date": terms.expected_end_date,
		# How much of the mission document has been written, so a list row can say
		# "4 objectives, 6 itinerary days" without reading six tables per row. Free
		# to compute: the document is already loaded and cached by `read`.
		"section_counts": {field: len(terms.get(field) or []) for field in _MISSION_TABLES},
		"project": terms.project,
		# The project's own words, read here so a listing of terms can be grouped
		# by programme without a second call per row. `None` where the terms belong
		# to no project, which is an ordinary answer and not a missing one.
		"project_name": _project_name(terms.project),
		"purpose": terms.purpose,
		"responsibilities": terms.responsibilities,
		"geo_scope": terms.geo_scope,
		"geo_scope_path": adapter.get_full_path(terms.geo_scope) if terms.geo_scope else None,
		"default_duration_days": terms.default_duration_days,
		"approval_mode": terms.approval_mode,
		"requires_approver": approval.requires_approver(terms.approval_mode, _describe(terms)),
		"required_certifications": needed["mandatory"],
		"desirable_certifications": needed["desirable"],
	}


def mission_dto(terms_of_reference: str) -> dict:
	"""The whole mission document: the summary, plus the six tables and the background.

	The counterpart of `dto`, and the reason `dto` stays lean. Only the screens
	that display a terms of reference in full — the mission page and the printed
	document — ask for this, so the cost of reading six child tables is paid at
	the one place that needs them rather than on every deployment read in the app.

	Each row is rebuilt key by key from the same column lists `create` writes
	through, so a field added to a child doctype and not reviewed here does not
	silently become part of this app's API.
	"""
	terms = read(terms_of_reference)

	return {
		**dto(terms_of_reference),
		"mission_background": terms.mission_background,
		"notes": terms.notes,
		**{
			field: [{key: row.get(key) for key in columns} for row in (terms.get(field) or [])]
			for field, columns in _MISSION_TABLES.items()
		},
		# Written back with the rows rather than left for a reader to total, so
		# the screen and the printed document cannot arrive at two figures. Still
		# only the mission's own resource lines: nothing here reaches across a
		# project or compares this against what was actually spent.
		"resources_total": sum(frappe.utils.flt(row.total_cost) for row in (terms.resources or [])),
	}


def update(terms_of_reference: str, **values) -> dict:
	"""Edit a terms of reference that is still a draft.

	**Only a draft.** Submitting is what freezes the wording, and the whole
	reason it is frozen is that somebody accepting a deployment under these terms
	is accepting exactly this document. Frappe would refuse a write to a
	submitted record anyway; this refuses it in words that say why.

	Unknown keys are ignored rather than written, and a table the caller did not
	mention is left alone rather than emptied — the editor sends one tab at a
	time, and a screen that saves the mission tab must not silently delete the
	itinerary the other tab holds.
	"""
	doc = frappe.get_doc(TERMS_DOCTYPE, terms_of_reference)
	doc.check_permission("write")

	if doc.docstatus != 0:
		frappe.throw(
			_(
				"{0} has been submitted and its wording is fixed. Amend it instead: that makes a new"
				" document, and leaves everything already agreed under this one exactly as it is."
			).format(frappe.bold(_describe(doc))),
			frappe.ValidationError,
			title=_("Terms of Reference Already Submitted"),
		)

	for field in _EDITABLE:
		if field in values:
			doc.set(field, values[field] or None)

	if "default_duration_days" in values:
		doc.default_duration_days = frappe.utils.cint(values["default_duration_days"])

	if "is_active" in values:
		doc.is_active = 1 if values["is_active"] else 0

	if "required_certifications" in values:
		doc.set(
			"required_certifications",
			[
				{
					"certification_type": row.get("certification_type"),
					"is_mandatory": 1 if row.get("is_mandatory") else 0,
				}
				for row in (values["required_certifications"] or [])
				if isinstance(row, dict) and row.get("certification_type")
			],
		)

	for field, rows in mission_rows(
		**{field: values[field] for field in _MISSION_TABLES if field in values}
	).items():
		doc.set(field, rows)

	doc.save()

	return mission_dto(doc.name)


# The scalar fields an editor may write. `tor_key` is not among them: it is the
# docname and set once, because a deployment points at it. Nor is `total_cost`,
# which is derived, or `amended_from`, which is Frappe's own.
_EDITABLE = (
	"tor_name",
	"project",
	"purpose",
	"mission_background",
	"responsibilities",
	"geo_scope",
	"expected_start_date",
	"expected_end_date",
	"approval_mode",
	"notes",
)


def submit(terms_of_reference: str) -> dict:
	"""Freeze the wording. The deliberate act that makes terms agreeable to.

	Separate from `create` because a mission document is written over several
	sittings and submitting says the writing is finished — that people may now be
	asked to agree to this exact text. Idempotent on terms already submitted,
	which is what makes a double-clicked button harmless; a cancelled one is left
	to Frappe to refuse, because "already submitted" and "withdrawn" must not
	both come back as quiet success.
	"""
	doc = frappe.get_doc(TERMS_DOCTYPE, terms_of_reference)
	doc.check_permission("submit")

	if doc.docstatus != 1:
		doc.submit()

	return dto(doc.name)
