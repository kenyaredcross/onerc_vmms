# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Reading a Terms of Reference — the few things on it that code reads.

A `VMMS Terms of Reference` is a society's mission document: one per piece of
work it deploys volunteers to do. Most of what is on it — the background, the
objectives, the outputs, the approach, the itinerary, the stakeholders, the
resources — is for the people involved, and this module deliberately decides
nothing from any of it. Four fields govern behaviour:

    geo_scope                where these terms may be used, and everything under it
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

**Complete before it is frozen.** `REQUIRED_AT_SUBMISSION` is the list a mission
document has to answer before its wording stops being editable — a programme, a
period, a place, a background, objectives, outputs, stakeholders, an itinerary,
and either resource lines or the explicit statement that it needs none. It is
checked at submission and never on save, because a draft is written over several
sittings and one that refused to save until it was finished would be a draft
nobody could use.

**Who freezes it is the society's answer, not this app's.** A society that has
configured a `VMMS Approval Workflow` for this doctype gets one: the writer sends
the document for approval, the engine routes it, and the document submits itself
the moment the last approver says yes — `try_freeze`, called from the
controller's `on_update`, which is the same predicate-not-sequence shape
`request.try_fulfil` uses. A society that has configured none gets the plainer
answer it asked for: anybody with submit permission submits it. Either way there
is exactly one approval status on the record — the engine's — and `docstatus` is
its consequence rather than a second opinion about it.

**Superseding is what amending cannot do.** Frappe's amend needs a cancel first,
and `on_cancel` refuses to cancel terms a deployment already points at, because
the deployments already agreed keep the wording they were agreed under. So a
mission that has to be respecified after people are in the field gets `supersede`
instead: a fresh draft carrying the whole mission across, with `supersedes`
pointing back, and the original left exactly as it is.
"""

import frappe
from frappe import _

from vmmsx.approvals import states
from vmmsx.approvals.services import config as approval_config
from vmmsx.approvals.services import contract, engine
from vmmsx.deployment.services import approval
from vmmsx.deployment.services import project as project_service

TERMS_DOCTYPE = "VMMS Terms of Reference"

# What must be on a terms of reference before its wording can be frozen, keyed
# by fieldname, with the sentence a writer is shown when it is missing.
#
# **A submission gate, never a save gate.** A mission document is written over
# several sittings — the background one day, the itinerary once the branch has
# answered — and a draft that refused to save until it was finished would be a
# draft nobody could use. Everything here is checked at the one moment the
# wording stops being editable and people start being asked to agree to it.
#
# Resources are not in the table because they are the one item with two right
# answers: lines, or an explicit declaration that the mission needs nothing.
# `_assert_resources_answered` holds that pair.
REQUIRED_AT_SUBMISSION: tuple[tuple[str, str], ...] = (
	("project", "the programme of work these terms are written under"),
	("expected_start_date", "when the mission is expected to begin"),
	("expected_end_date", "when the mission is expected to end"),
	("geo_scope", "where these terms apply"),
	("mission_background", "the mission background"),
	("objectives", "at least one specific objective"),
	("expected_outputs", "at least one expected output"),
	("stakeholders", "at least one stakeholder"),
	("itinerary", "at least one itinerary entry"),
)


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

	The node must be that node or beneath it: an ancestor is not inside it, which
	is why `allow_ancestor` is off. Anchoring a deployment at the region when its
	terms are a particular branch's would put the work outside the very place the
	terms describe. Terms meant for the whole society name the national node.

	**An empty scope is unconstrained, and that is history rather than a choice.**
	A scope is mandatory now — a mission document that applies nowhere in
	particular cannot be routed for approval — but records written before that
	rule may carry none, and a register that started refusing every deployment
	under a specification nobody can edit any more would be this rule applied
	retroactively.
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


# --- is it finished? --------------------------------------------------------


def missing_at_submission(terms) -> list[str]:
	"""What this document still has to answer, in the writer's words. Empty when finished.

	Takes the document rather than a name because it runs while the document is
	being submitted, and the cached copy is the one before this edit.

	Returned as a list rather than thrown, so a screen can grey out the submit
	button and say why without provoking an error, and so `assert_complete` has
	exactly one place the list is decided.
	"""
	missing = [label for field, label in REQUIRED_AT_SUBMISSION if not terms.get(field)]

	if not (terms.get("resources") or terms.get("has_no_resources")):
		missing.append(
			_("the resources this mission needs, or a tick to say it needs none")
		)

	return missing


def assert_complete(terms) -> None:
	"""Throw unless the mission document is finished.

	**Everything at once, never the first thing missing.** A writer told about one
	empty field at a time makes one edit at a time, and a nine-item document
	becomes nine round trips. The whole list comes back in one sentence.
	"""
	missing = missing_at_submission(terms)

	if not missing:
		return

	frappe.throw(
		_(
			"{0} is not finished. Somebody accepting a deployment under it is agreeing to"
			" exactly this document, so it has to say: {1}."
		).format(frappe.bold(_describe(terms)), ", ".join(str(item) for item in missing)),
		frappe.MandatoryError,
		title=_("Mission Document Not Finished"),
	)


# --- who freezes it ---------------------------------------------------------


def is_governed() -> bool:
	"""Has this society put terms of reference under an approval workflow?

	The one question that decides which of the two submission paths applies.
	Answered from configuration on every call rather than cached, so a society
	that configures a workflow this afternoon does not need a restart.
	"""
	return approval_config.is_approvable(TERMS_DOCTYPE)


def is_approved(terms) -> bool:
	"""Has the engine finished with this document, and said yes?"""
	return contract.state(terms) == states.APPROVED


def assert_may_freeze(terms) -> None:
	"""Throw unless this document may have its wording frozen now.

	Called from the controller's `before_submit`, which is the one door every
	submission goes through — the desk's own Submit button, the API, a test, and
	`try_freeze` alike. Putting the rule anywhere else would leave the desk form
	as a way round it.
	"""
	assert_complete(terms)

	if not is_governed():
		return

	if is_approved(terms):
		return

	frappe.throw(
		_(
			"{0} has to be approved before its wording can be frozen. This society routes terms"
			" of reference for approval, so send it for approval rather than submitting it here."
		).format(frappe.bold(_describe(terms))),
		frappe.PermissionError,
		title=_("Approval Required"),
	)


def send_for_approval(terms_of_reference: str, user: str | None = None) -> dict:
	"""Hand a finished draft to the society's approvers.

	Refuses where no workflow governs the doctype, rather than quietly submitting:
	the two paths are different acts with different audit trails, and a caller
	that asked for the routed one on a site that does not route would otherwise
	get a submitted document and no record of anybody having agreed to it.
	"""
	doc = frappe.get_doc(TERMS_DOCTYPE, terms_of_reference)
	doc.check_permission("submit")

	if not is_governed():
		frappe.throw(
			_(
				"This society has not configured an approval workflow for terms of reference, so"
				" there is nobody to send this to. Submit it instead."
			),
			frappe.ValidationError,
			title=_("Nothing To Route To"),
		)

	assert_complete(doc)

	return engine.submit(doc, user)


def try_freeze(terms) -> None:
	"""Submit an approved draft. Idempotent, and silent when there is nothing to do.

	A predicate, not a step in a sequence: it asks whether this document is a
	draft that the society's approvers have finished saying yes to, and both
	answers come off the record rather than off which code path happened to run.
	That is what makes it safe to call from `on_update`, after any event and in
	any order — the same shape `request.try_fulfil` has, and for the same reason.

	**Submitted through a freshly loaded copy.** This runs inside the save that
	recorded the final approval, so the row on disk already carries the new state
	while the in-memory document is mid-flight; re-reading it is what keeps this
	from saving a document that is still being saved. The reload sees docstatus 0
	and the approval, submits once, and the second `on_update` that its own submit
	fires finds docstatus 1 and returns here.

	**The submit bypasses permissions, and this is the justification** — the same
	one `request.fulfil` gives for inserting a deployment. The caller that matters
	is the approval engine: this runs inside whichever approver recorded the
	decision, and an approver holds no submit permission on the terms register and
	should not need any in order to approve one. The elevation is not a shortcut
	around a check, because the check already happened, in `engine.decide`, against
	the person this document routed to. `before_submit` still runs, so the document
	is still refused unless it is finished and approved.
	"""
	if terms.docstatus != 0:
		return

	if not (is_governed() and is_approved(terms)):
		return

	doc = frappe.get_doc(TERMS_DOCTYPE, terms.name)
	doc.flags.ignore_permissions = True
	doc.submit()


# --- respecifying work that is already in the field -------------------------


def references(terms_of_reference: str) -> dict[str, int]:
	"""How many deployments and requests point at these terms. Zero-valued, never empty.

	The question `on_cancel` and `supersede` both ask, in one place, so the two
	cannot come to different answers about whether a document is still in use.
	"""
	return {
		doctype: frappe.db.count(doctype, {"terms_of_reference": terms_of_reference})
		for doctype in ("VMMS Deployment", "VMMS Deployment Request")
	}


def is_referenced(terms_of_reference: str) -> bool:
	"""Has anything been raised under these terms — ever, in any state?

	Any, deliberately: a cancelled deployment is still a record of somebody
	having been asked to serve under this exact wording, and rewriting the
	wording underneath it would falsify what they agreed to.
	"""
	return any(references(terms_of_reference).values())


def supersede(terms_of_reference: str, **values) -> dict:
	"""Start a replacement for terms that are already in use.

	**What amending cannot do.** Frappe's amend needs a cancel first, and
	`on_cancel` refuses to cancel terms a deployment points at — the deployments
	already agreed keep the wording they were agreed under, and that refusal is
	the point rather than an obstacle. But a mission genuinely does get
	respecified while people are in the field, and without this the only answers
	were to falsify the original or to write the replacement from scratch with no
	thread back to it.

	So: the whole mission document is copied into a new draft, `supersedes` points
	at the original, and the original is left exactly as it is — still submitted,
	still the terms every existing deployment is governed by. Retiring it, if the
	society wants that, is `is_active` and a separate decision.

	`values` overrides any editable field on the copy, so a caller respecifying a
	period or a scope does not have to write it twice.
	"""
	original = frappe.get_doc(TERMS_DOCTYPE, terms_of_reference)
	original.check_permission("read")

	assert_submitted(terms_of_reference)

	replacement = create(
		tor_name=values.pop("tor_name", None) or original.tor_name,
		project=original.project,
		purpose=original.purpose,
		mission_background=original.mission_background,
		responsibilities=original.responsibilities,
		geo_scope=original.geo_scope,
		expected_start_date=original.expected_start_date,
		expected_end_date=original.expected_end_date,
		default_duration_days=original.default_duration_days,
		approval_mode=original.approval_mode,
		notes=original.notes,
		has_no_resources=original.has_no_resources,
		required_certifications=[row.as_dict() for row in (original.required_certifications or [])],
		**{
			field: [row.as_dict() for row in (original.get(field) or [])]
			for field in _MISSION_TABLES
		},
	)

	replacement.db_set("supersedes", original.name, update_modified=False)
	replacement.reload()

	if values:
		return update(replacement.name, **values)

	return mission_dto(replacement.name)


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
	is_active: bool | int | str = True,
	has_no_resources: bool | int | str = False,
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
			"is_active": 1 if frappe.utils.cint(is_active) else 0,
			"purpose": purpose,
			"mission_background": mission_background,
			"responsibilities": responsibilities,
			"geo_scope": geo_scope or None,
			"expected_start_date": expected_start_date or None,
			"expected_end_date": expected_end_date or None,
			"default_duration_days": frappe.utils.cint(default_duration_days),
			"approval_mode": approval_mode or approval.MODE_DIRECT,
			"has_no_resources": 1 if frappe.utils.cint(has_no_resources) else 0,
			"notes": notes,
			"required_certifications": [
				{
					"certification_type": row.get("certification_type"),
					"is_mandatory": 1 if row.get("is_mandatory") else 0,
					"requirement_notes": row.get("requirement_notes"),
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
	"resources": (
		"resource",
		"description",
		"needed_on",
		"quantity",
		"unit",
		"currency",
		"unit_cost",
		"funding_status",
		"donor",
	),
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

	return frappe.db.get_value(project_service.PROJECT_DOCTYPE, project, "project_name")


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
		# The thread back through a mission that had to be respecified while
		# people were already in the field. `supersede` says why this is not an
		# amendment.
		"supersedes": terms.supersedes,
		# What still has to be written before the wording can be frozen. Empty on
		# a finished document, and on every submitted one — a screen greys out its
		# own submit button from this rather than from a rule of its own.
		"missing": missing_at_submission(terms),
		"has_no_resources": bool(terms.has_no_resources),
		# The society's own approval, where it configured one. Read straight off
		# the field rather than through `contract.state`, which reads an empty one
		# as Draft: on a site that routes nothing, "nobody has been asked" and "it
		# is a draft awaiting an approver" are different answers and only the first
		# is true.
		"is_governed": is_governed(),
		"approval_state": terms.approval_state or None,
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
		"certification_requirements": [
			{
				"certification_type": row.certification_type,
				"is_mandatory": bool(row.is_mandatory),
				"requirement_notes": row.requirement_notes,
			}
			for row in (terms.required_certifications or [])
		],
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

	if "has_no_resources" in values:
		doc.has_no_resources = 1 if values["has_no_resources"] else 0

	if "required_certifications" in values:
		doc.set(
			"required_certifications",
			[
				{
					"certification_type": row.get("certification_type"),
					"is_mandatory": 1 if row.get("is_mandatory") else 0,
					"requirement_notes": row.get("requirement_notes"),
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

	**The direct path.** On a site whose society routes terms of reference for
	approval this refuses, in `before_submit`, and `send_for_approval` is the door
	instead. The refusal lives in the controller rather than here so that the desk
	form's own Submit button meets the same rule as this function does.
	"""
	doc = frappe.get_doc(TERMS_DOCTYPE, terms_of_reference)
	doc.check_permission("submit")

	if doc.docstatus != 1:
		doc.submit()

	return dto(doc.name)
