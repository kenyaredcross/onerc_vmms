# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The roster question, and the ownership rule that reads it.

**Ownership is not geo scoping, and this module is where the difference lives.**
Geo scoping answers *where* somebody may act: it is a property of a record's
anchor, and core owns it. Ownership answers *whose record this is*: being
correctly placed in the right county does not make you a participant on a
deployment run there, and no amount of geo authority ever will. A volunteer may
log time against a deployment only if they are on it, and that is checked on the
server at save. The picker filters for convenience; the refusal is what makes
fabricating participation impossible rather than merely hidden.

Where the roster now lives
--------------------------

It used to be `VMMS Deployment.participants`, a child table, and this module
argued that case at length. The argument was sound for as long as a roster row
was only a roster row: a roster is a property of the deployment, it is edited as
one list, and it is checked against one permission. It stopped holding once each
person's deployment needed a URL a volunteer could open, a reference an email
could point at, a lifecycle with a grammar, and somewhere to record which
submitted terms of reference they agreed to. `VMMS Deployment Assignment` is
that record, and `deployment/services/assignment.py` owns it.

**This module did not disappear into that one, and the split is deliberate.**
`assignment.py` owns the lifecycle: raising, asking, answering, withdrawing.
This owns the one question the rest of the app asks of a roster — *was this
person on this deployment* — and the refusal that hangs off it. The time-log
validator has no business importing a module full of state transitions to ask
one boolean, and the ownership rule is the kind of thing that should be findable
in one file with its reasoning next to it.

**Assigned and Accepted are what count.** They are the two statuses that mean
somebody is on the deployment. This is a change from the child-table model,
where a decline left participation untouched so that a record of service could
not be invalidated by an answer; `assignment.py`'s own docstring sets out why
that is no longer needed, and what replaced it.

**Leaving is recorded, never removed.** `left_on` says somebody went early; it
does not take them off. Removing them would make the time they actually served
unfilable, which is precisely backwards.
"""

import frappe
from frappe import _

from vmmsx.deployment.services import assignment

DEPLOYMENT_DOCTYPE = "VMMS Deployment"
ASSIGNMENT_DOCTYPE = assignment.ASSIGNMENT_DOCTYPE

# The refusal, named so tests assert on a fact rather than on prose that drifts.
OWNERSHIP_RULE = (
	"A deployment time log is constrained to deployments the volunteer actually participated in."
	" This is OWNERSHIP scoping, the actor's own records, and it is not geo scoping: being placed"
	" in the right county does not make somebody a participant. The picker filters for"
	" convenience; the server rejects a log whose deployment does not list this volunteer as a"
	" participant, so that fabricating participation is impossible rather than merely hidden."
)


# --- the question the ownership rule asks ---------------------------------


def is_participant(deployment: str, volunteer: str) -> bool:
	"""Is this volunteer on this deployment?

	Read from the database rather than from a document handed in, deliberately.
	The caller is validating a time log, and a roster the caller loaded earlier is
	a roster as it was earlier; the question has to be answered against the roster
	as it is.

	**`db.exists`, which does not scope.** That is right here: this is not asking
	whether the caller may see the assignment, it is asking whether a fact is
	true. A coordinator filing a log on somebody else's behalf, in a branch whose
	assignments they cannot list, must still get a truthful answer about whether
	that person served.
	"""
	if not (deployment and volunteer):
		return False

	return bool(
		frappe.db.exists(
			ASSIGNMENT_DOCTYPE,
			{
				"deployment": deployment,
				"volunteer": volunteer,
				"status": ("in", assignment.ON_DEPLOYMENT),
			},
		)
	)


def assert_participant(deployment: str, volunteer: str) -> None:
	"""Throw unless the volunteer is on the deployment.

	**A ValidationError rather than a PermissionError**, and the distinction is
	deliberate. This is not a question about the acting user's authority: a
	branch coordinator with every permission there is may not file a deployment
	log for somebody who was not on the deployment either, because the record
	would be false. It is a rule about whether the document describes something
	that happened.
	"""
	if is_participant(deployment, volunteer):
		return

	frappe.throw(
		_(
			"{0} is not on deployment {1}, so no time can be logged against it. Time is logged"
			" against a deployment somebody actually took part in. Assign them to it if they"
			" served on it, or file this as a general log."
		).format(frappe.bold(assignment.volunteer_label(volunteer)), frappe.bold(deployment)),
		frappe.ValidationError,
		title=_("Not A Participant"),
	)


# --- reading the roster both ways -----------------------------------------


def participants_of(deployment: str) -> list[str]:
	"""Every volunteer on this deployment, leaders first.

	Only those actually on it. Somebody who was asked and declined is on the
	deployment's *assignment* register, which `assignment.roster_of` returns in
	full, but they are not a participant and a caller asking this question wants
	the people who went.
	"""
	if not deployment:
		return []

	return [row["volunteer"] for row in assignment.roster_of(deployment) if row["is_on_deployment"]]


def roster_of(deployment: str) -> list[dict]:
	"""The whole assignment register for one deployment, settled rows included.

	Delegated rather than re-queried: `assignment.roster_of` owns the shape, and
	a second reader here would be a second chance for the two to disagree about
	what a roster row looks like.
	"""
	return assignment.roster_of(deployment)


def deployments_of(volunteer: str) -> list[str]:
	"""Every deployment this volunteer has been on, most recent first.

	Only the ones they were actually on. A volunteer's own history is what they
	did, not what they were asked; the questions they declined are theirs to see
	on their assignments, not entries in a service record.
	"""
	if not volunteer:
		return []

	return [
		row["deployment"] for row in assignment.assignments_of(volunteer, statuses=assignment.ON_DEPLOYMENT)
	]


def history_of(volunteer: str) -> list[dict]:
	"""Every deployment this volunteer served on, as explicit rows for a DTO.

	`deployments_of()` above answers "which ones"; this answers "which ones, and
	what were they". The coordinator's view on the volunteer register needs the
	second — a list of opaque docnames tells somebody nothing.

	Built field by field. Never the documents: a Deployment read in full would
	drag its own facts into a shape about one person, and a Terms of Reference
	read in full is a whole mission document.

	`joined_on` and `left_on` come off the assignment, so a volunteer who left a
	deployment early reads as having left it rather than as never having been
	there.
	"""
	if not volunteer:
		return []

	rows = assignment.assignments_of(volunteer, statuses=assignment.ON_DEPLOYMENT)

	if not rows:
		return []

	deployments = {
		row["name"]: row
		for row in frappe.get_all(
			DEPLOYMENT_DOCTYPE,
			filters={"name": ("in", [row["deployment"] for row in rows])},
			fields=["name", "status", "start_date", "end_date", "geo_node", "terms_of_reference"],
			# Resolving the facts about deployments this person demonstrably served
			# on, for their own record. A volunteer holds no Geo Assignment, so a
			# scoped read here would hand them an empty history of work they did.
			ignore_permissions=True,
		)
	}

	history = []

	for row in rows:
		deployment = deployments.get(row["deployment"])

		if not deployment:
			# The assignment outlived its deployment, which a cascade should
			# prevent and a partially-restored backup will not. Skipped rather
			# than rendered as a deployment with no facts on it.
			continue

		history.append(
			{
				"deployment": deployment["name"],
				"assignment": row["name"],
				"status": deployment["status"],
				"start_date": deployment["start_date"],
				"end_date": deployment["end_date"],
				"geo_node": deployment["geo_node"],
				"terms_of_reference": deployment["terms_of_reference"],
				# The society's own word for the terms, read live, because a
				# docname is not something to put in front of a coordinator.
				"tor_name": _tor_name(deployment["terms_of_reference"]),
				"role": row["role"],
				"is_leader": row["is_leader"],
				"joined_on": row["joined_on"],
				"left_on": row["left_on"],
				"notes": row["participation_notes"],
			}
		)

	# Ordered here rather than in the query: the sort key is the deployment's
	# date and the rows were read off the assignment register, so there is
	# nothing to order by until both have been put together.
	history.sort(key=_most_recent_first, reverse=True)

	return history


def _most_recent_first(row: dict) -> tuple:
	"""Sort key: dated deployments newest first, undated ones after them.

	The two-part key keeps a None out of a comparison with a date. Tuples are
	compared left to right and only fall through to the second element when the
	first is equal, so an undated row is ordered by the flag alone and never
	against a date it does not have.
	"""
	return (row["start_date"] is not None, row["start_date"])


def _tor_name(terms_of_reference: str | None) -> str | None:
	"""The society's own word for a terms of reference, or None if it names none.

	Read through `terms.TERMS_DOCTYPE` rather than a second spelling of the
	doctype name in this file: one typo in a string literal is a lookup that
	silently returns nothing.
	"""
	if not terms_of_reference:
		return None

	from vmmsx.deployment.services import terms

	return frappe.get_cached_value(terms.TERMS_DOCTYPE, terms_of_reference, "tor_name")


# --- writing it -----------------------------------------------------------


def add(deployment_doc, volunteer: str, **fields) -> bool:
	"""Place a volunteer on this deployment. Idempotent; returns whether anything changed.

	A coordinator saying somebody is going, which is the verb this app has always
	drawn apart from asking them. `assignment.create` holds the rules — the
	headcount cap, the refusal of a second open assignment, the terms check — and
	this is the name the rest of the app already calls it by.

	Unlike the child-table version this replaced, it **does** write: an assignment
	is its own document and there is no parent save to defer to. Callers placing
	several people at once want `assignment.deploy`, which wraps each insert in
	its own savepoint and reports which ones did not take.
	"""
	if assignment.open_assignment(deployment_doc.name, volunteer):
		return False

	assignment.create(
		deployment_doc,
		volunteer,
		status=assignment.STATUS_ASSIGNED,
		**fields,
	)

	return True
