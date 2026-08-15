# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The roster: who is on a deployment, and the ownership rule that reads it.

**Ownership is not geo scoping, and this module is where the difference lives.**
Geo scoping answers *where* somebody may act: it is a property of a record's
anchor, and core owns it. Ownership answers *whose record this is*: being
correctly placed in the right county does not make you a participant on a
deployment run there, and no amount of geo authority ever will. A volunteer may
log time against a deployment only if they are on its roster, and that is
checked on the server at save. The picker filters for convenience; the refusal
is what makes fabricating participation impossible rather than merely hidden.

Why participation is a child table, and not a doctype of its own
---------------------------------------------------------------

Both shapes answer both questions this module was asked to serve, so the choice
came down to what each makes true rather than what each makes possible.

* **"Who is on this deployment"** is the roster, and a roster is a property of
  the deployment. As a child table it is edited as one list on one form, saved
  in one act, and checked against one permission: the permission to write the
  deployment. As a separate doctype it becomes N records that can drift from
  their parent's state, and adding somebody needs its own permission story.
* **"Which deployments was this volunteer on"** is one indexed read either way.
  A child table is a real table; `deployments_of()` below reads it by
  `volunteer` and returns `parent`. Nothing else in the app writes that query,
  which is why it lives here.
* **The time log links to the deployment, not to a participation row.** That is
  what settles it. Had the log needed a stable per-person identity to point at,
  a child row would have been the wrong thing to hand it, because a child row's
  name is not something a caller should ever have to hold. It does not: the log
  names a deployment and a volunteer, and this module answers whether that pair
  is on the roster.
* **No custom UI.** Frappe's grid on the deployment form is the roster editor,
  which is the surface this stage was asked to build on.

What the shape costs, stated plainly: a participation cannot itself be approved,
cannot be geo-scoped separately from its deployment, and cannot carry an
independent lifecycle. None of those is wanted today. If one becomes wanted, the
migration is a real one, and it is bought by all of the above rather than
avoided by guessing now.

**Leaving is recorded, never removed.** `left_on` says somebody went early; it
does not take them off the roster. Removing them would make the time they
actually served unfilable, which is precisely backwards.
"""

import frappe
from frappe import _

DEPLOYMENT_DOCTYPE = "VMMS Deployment"
PARTICIPANT_DOCTYPE = "VMMS Deployment Participant"

# The field on VMMS Deployment holding the roster. Named once, here, because
# every query below has to identify the child rows by their parent field and a
# second spelling of it would silently return nothing.
ROSTER_FIELD = "participants"

# The refusal, named so tests assert on a fact rather than on prose that drifts.
# This is the rule the volunteer spine's stage-4 stub was written to wait for.
OWNERSHIP_RULE = (
	"A deployment time log is constrained to deployments the volunteer actually participated in."
	" This is OWNERSHIP scoping, the actor's own records, and it is not geo scoping: being placed"
	" in the right county does not make somebody a participant. The picker filters for"
	" convenience; the server rejects a log whose deployment does not list this volunteer as a"
	" participant, so that fabricating participation is impossible rather than merely hidden."
)


def _roster_filters(deployment: str) -> dict:
	"""The child rows belonging to one deployment's roster.

	`parenttype` and `parentfield` are both given. A child table is one physical
	table per doctype, and filtering only by `parent` would match a row from any
	other doctype that happened to share a docname.
	"""
	return {
		"parenttype": DEPLOYMENT_DOCTYPE,
		"parentfield": ROSTER_FIELD,
		"parent": deployment,
	}


# --- the question the ownership rule asks ---------------------------------


def is_participant(deployment: str, volunteer: str) -> bool:
	"""Is this volunteer on this deployment's roster?

	Read from the database rather than from a document handed in, deliberately.
	The caller is validating a time log, and a roster the caller loaded earlier
	is a roster as it was earlier; the question has to be answered against the
	roster as it is.
	"""
	if not (deployment and volunteer):
		return False

	return bool(
		frappe.db.exists(PARTICIPANT_DOCTYPE, {**_roster_filters(deployment), "volunteer": volunteer})
	)


def assert_participant(deployment: str, volunteer: str) -> None:
	"""Throw unless the volunteer is on the deployment's roster.

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
			"{0} is not on the roster of deployment {1}, so no time can be logged against it. Time"
			" is logged against a deployment somebody actually took part in. Add them to the"
			" deployment's participants if they served on it, or file this as a general log."
		).format(frappe.bold(volunteer), frappe.bold(deployment)),
		frappe.ValidationError,
		title=_("Not A Participant"),
	)


# --- reading the roster both ways -----------------------------------------


def participants_of(deployment: str) -> list[str]:
	"""Every volunteer on this deployment, in roster order."""
	if not deployment:
		return []

	return frappe.get_all(
		PARTICIPANT_DOCTYPE,
		filters=_roster_filters(deployment),
		order_by="idx asc",
		pluck="volunteer",
	)


def roster_of(deployment: str) -> list[dict]:
	"""The roster as explicit rows, for a DTO. Built field by field."""
	if not deployment:
		return []

	rows = frappe.get_all(
		PARTICIPANT_DOCTYPE,
		filters=_roster_filters(deployment),
		fields=[
			"volunteer",
			"joined_on",
			"left_on",
			"participation_notes",
			"response",
			"responded_on",
		],
		order_by="idx asc",
	)

	return [
		{
			"volunteer": row["volunteer"],
			"joined_on": row["joined_on"],
			"left_on": row["left_on"],
			"notes": row["participation_notes"],
			# The invitation's answer, carried so a coordinator can see who was
			# asked and what they said. It decides nothing: `is_participant` is
			# untouched by a reply, so a declined row is still on the roster
			# until a coordinator takes it off. Blank is "never asked", which is
			# a different thing from "asked and silent" (`invited`).
			"response": row["response"] or None,
			"responded_on": row["responded_on"],
		}
		for row in rows
	]


def deployments_of(volunteer: str) -> list[str]:
	"""Every deployment this volunteer has been on, most recent first.

	The reverse of the roster question, and the one place it is asked. Reading a
	child table by a field other than `parent` is unusual enough that scattering
	the query would invite somebody to write it without `parenttype`, which would
	quietly match rows from another doctype.

	Ordered by the deployments themselves rather than by the child rows, because
	"most recent" is a property of the deployment and a roster row has no date of
	its own that every society fills in.
	"""
	if not volunteer:
		return []

	names = frappe.get_all(
		PARTICIPANT_DOCTYPE,
		filters={
			"parenttype": DEPLOYMENT_DOCTYPE,
			"parentfield": ROSTER_FIELD,
			"volunteer": volunteer,
		},
		pluck="parent",
	)

	if not names:
		return []

	return frappe.get_all(
		DEPLOYMENT_DOCTYPE,
		filters={"name": ("in", names)},
		order_by="start_date desc, creation desc",
		pluck="name",
	)


def history_of(volunteer: str) -> list[dict]:
	"""Every deployment this volunteer has been on, as explicit rows for a DTO.

	`deployments_of()` above answers "which ones"; this answers "which ones, and
	what were they". The coordinator's view on the volunteer register needs the
	second — a list of opaque docnames tells somebody nothing — and it must come
	from here rather than from the volunteer module, because the join between a
	roster row and its parent deployment is this module's business and a second
	copy of it would be a second chance to forget `parenttype`.

	Built field by field. Never the documents: a Deployment carries its whole
	roster, and handing that back would disclose every other participant to
	anybody who could read one volunteer.

	`joined_on` and `left_on` come off the roster row, so a volunteer who left a
	deployment early reads as having left it rather than as never having been
	there. Removing them from the roster instead would make the time they
	actually served unfilable, which is precisely backwards.
	"""
	if not volunteer:
		return []

	rows = frappe.get_all(
		PARTICIPANT_DOCTYPE,
		filters={
			"parenttype": DEPLOYMENT_DOCTYPE,
			"parentfield": ROSTER_FIELD,
			"volunteer": volunteer,
		},
		fields=["parent", "joined_on", "left_on", "participation_notes"],
	)

	if not rows:
		return []

	deployments = {
		row["name"]: row
		for row in frappe.get_all(
			DEPLOYMENT_DOCTYPE,
			filters={"name": ("in", [row["parent"] for row in rows])},
			fields=["name", "status", "start_date", "end_date", "geo_node", "terms_of_reference"],
		)
	}

	history = []

	for row in rows:
		deployment = deployments.get(row["parent"])

		if not deployment:
			# The roster row outlived its parent, which a cascade should prevent
			# and a partially-restored backup will not. Skipped rather than
			# rendered as a deployment with no facts on it.
			continue

		history.append(
			{
				"deployment": deployment["name"],
				"status": deployment["status"],
				"start_date": deployment["start_date"],
				"end_date": deployment["end_date"],
				"geo_node": deployment["geo_node"],
				"terms_of_reference": deployment["terms_of_reference"],
				# The society's own word for the terms, read live, because a
				# docname is not something to put in front of a coordinator.
				"tor_name": _tor_name(deployment["terms_of_reference"]),
				"joined_on": row["joined_on"],
				"left_on": row["left_on"],
				"notes": row["participation_notes"],
			}
		)

	# Ordered here rather than in the query: the sort key is the deployment's
	# date and the rows were read off the child table, so there is nothing to
	# order by until both have been put together.
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


def add(deployment, volunteer: str, **fields) -> bool:
	"""Put a volunteer on the roster. Idempotent; returns whether anything changed.

	Takes the deployment document, not a name, and does not save: the caller
	owns the transaction, and a roster change that saved itself would make
	adding five people five saves and five revisions.
	"""
	if any(row.volunteer == volunteer for row in deployment.participants or []):
		return False

	deployment.append(ROSTER_FIELD, {"volunteer": volunteer, **fields})

	return True
