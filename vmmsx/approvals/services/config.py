# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Reading the workflow configuration, and the anchor rules it enforces.

One `VMMS Approval Workflow` per approvable doctype. Everything a society can
decide differently lives on that record — the stages, who they need, how many
must act, how long they have, which levels of the hierarchy an application may
be anchored at. Nothing a society can decide lives in a source file.

This module is the only reader of that configuration. Stages come back **sorted
by sequence and never by label**, and a stage is looked up by its opaque row
name, so relabelling "Branch Endorsement" to "Branch Review" changes a screen
and nothing else.
"""

import frappe
from frappe import _
from onerc_core.geo.services import adapter

WORKFLOW_DOCTYPE = "VMMS Approval Workflow"


def for_doctype(doctype: str):
	"""The workflow governing `doctype`. Throws if there is none.

	Read through the document cache — this is hit on every submission, decision
	and SLA sweep, and it is configuration that changes a few times a year.
	Callers must treat the result as read-only; it is a shared object.
	"""
	name = workflow_name(doctype)

	if not name:
		frappe.throw(
			_("No approval workflow is configured for {0}. Create a {1} record for it.").format(
				frappe.bold(doctype), frappe.bold(WORKFLOW_DOCTYPE)
			),
			title=_("No Approval Workflow"),
		)

	return frappe.get_cached_doc(WORKFLOW_DOCTYPE, name)


def workflow_name(doctype: str) -> str | None:
	"""Docname of the workflow governing `doctype`, or None. Does not throw."""
	if not doctype:
		return None

	return frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": doctype}, "name")


def is_approvable(doctype: str) -> bool:
	return bool(workflow_name(doctype))


def governed_doctypes() -> list[str]:
	"""Every doctype under an approval workflow, sorted. What the sweeps iterate."""
	return sorted(frappe.get_all(WORKFLOW_DOCTYPE, pluck="workflow_for"))


# --- stages ---------------------------------------------------------------


def stages(workflow) -> list:
	"""Every stage, in sequence order. The only ordering anything may rely on."""
	return sorted(workflow.stages, key=lambda row: row.sequence)


def stages_after(workflow, sequence: int | None) -> list:
	"""Stages that come after `sequence`; all of them when it is None."""
	if sequence is None:
		return stages(workflow)

	return [row for row in stages(workflow) if row.sequence > sequence]


def stage_by_name(workflow, stage_name: str | None):
	"""One stage by its opaque row name, or None if it is gone.

	Gone is a real case: an administrator may delete a stage while an
	application sits in it. Callers decide what that means rather than being
	handed an exception from inside a lookup.
	"""
	if not stage_name:
		return None

	for row in workflow.stages:
		if row.name == stage_name:
			return row

	return None


# --- the anchor: ACC-02 and ACC-03 ----------------------------------------


def anchor(doc, workflow) -> str:
	"""The document's Geo Node. Throws when it has none — ACC-02.

	There are no unplaced records. An unplaced application is invisible to geo
	scoping (core's list filter is an `IN`, which excludes NULL) and unroutable
	by approvals, so it would exist without anybody able to see or act on it.
	Refusing it at submission is the whole rule.
	"""
	field = workflow.geo_node_field
	node = doc.get(field)

	if node:
		return node

	frappe.throw(
		_(
			"{0} {1} has no {2}. Every operational record is anchored to a Geo Node before it can move."
		).format(doc.doctype, frappe.bold(doc.name), frappe.bold(field)),
		frappe.MandatoryError,
		title=_("Missing Geo Anchor"),
	)


def assert_anchor_allowed(doc, workflow) -> None:
	"""ACC-03 — the anchor must sit at a level this society permits.

	Empty configuration means any active level: a society that has not narrowed
	it has not thereby forbidden everything. Which levels those are is never
	hardcoded — Kenya may anchor at county, another society at ward, and the
	only difference is rows in this table.
	"""
	allowed = allowed_anchor_levels(workflow)

	if not allowed:
		return

	node = anchor(doc, workflow)
	level = adapter.get_level(node)

	if level["key"] in allowed:
		return

	frappe.throw(
		_("{0} is at {1} level. {2} may only be anchored at: {3}.").format(
			frappe.bold(adapter.get_full_path(node)),
			frappe.bold(level["name"]),
			frappe.bold(doc.doctype),
			", ".join(_level_names(allowed)),
		),
		title=_("Anchor Level Not Permitted"),
	)


def allowed_anchor_levels(workflow) -> list[str]:
	"""Geo Level keys this workflow permits, in configured order."""
	return [row.geo_level for row in workflow.allowed_anchor_levels or [] if row.geo_level]


def allowed_anchor_levels_for(doctype: str) -> list[str]:
	"""Geo Level keys `doctype` may anchor at, read the same way Submit does.

	Empty means unconstrained — either no workflow governs `doctype` yet, or
	its workflow names no levels. Built for a geo_node picker: a Link field
	filtered to this set can never offer a level `assert_anchor_allowed` would
	reject at Submit, because both read the very same row. Never throws — an
	ungoverned doctype simply has nothing to narrow it, which is a UI question
	rather than the refusal `for_doctype()` gives a caller that expected one.
	"""
	name = workflow_name(doctype)

	if not name:
		return []

	return allowed_anchor_levels(frappe.get_cached_doc(WORKFLOW_DOCTYPE, name))


def _level_names(keys: list[str]) -> list[str]:
	"""Readable level names, via the adapter — never a `tabGeo Level` query."""
	labels = {level["key"]: level["name"] for level in adapter.level_labels()}

	return [labels.get(key, key) for key in keys]


# --- the applicant, for the cooldown --------------------------------------


def applicant(doc, workflow) -> tuple[str, str]:
	"""(fieldname, value) identifying who applied.

	Configurable, because "the applicant" is a different field in every module:
	a volunteer application points at a Red Profile, a staff-entered membership
	may only have its owner. Unset falls back to `owner`, which every document
	has.
	"""
	field = workflow.applicant_field or "owner"

	return field, doc.get(field)
