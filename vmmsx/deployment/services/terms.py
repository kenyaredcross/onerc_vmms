# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Reading a Terms of Reference — the three things on it that code reads.

A `VMMS Terms of Reference` is configuration: one per kind of work a society
deploys volunteers to do. Most of what is on it is for the people involved, and
this module deliberately reads none of that. Three fields govern behaviour:

    geo_scope                where these terms may be used. Empty means anywhere
    approval_mode            whether a request under them needs an approver
    required_certifications  what a candidate must, or would ideally, hold

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
	responsibilities: str | None = None,
	geo_scope: str | None = None,
	default_duration_days: int | None = None,
	approval_mode: str | None = None,
	required_certifications: list | None = None,
	notes: str | None = None,
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
			"responsibilities": responsibilities,
			"geo_scope": geo_scope or None,
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
		}
	)
	doc.insert()

	return doc


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
	"""One terms of reference, as an explicit dict. Built field by field.

	Never the Document: that would leak every field on the record, including ones
	nobody reviewed, and turn a schema change into an API change.
	"""
	from onerc_core.geo.services import adapter

	terms = read(terms_of_reference)
	needed = requirements(terms_of_reference)

	return {
		"name": terms.name,
		"tor_key": terms.tor_key,
		"tor_name": terms.tor_name,
		"is_active": bool(terms.is_active),
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
