# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Asking a volunteer to go, and carrying their answer back.

`participation.py` owns the roster and the ownership rule that reads it. This
module owns the conversation that sometimes precedes a roster row: a coordinator
invites, the volunteer accepts or declines, and whoever raised the need is told
what they said.

**An invitation does not decide who is on the roster.** The row is written when
the invitation is sent, and it stays there whatever the answer is. That is the
same principle as `left_on` next door: leaving is recorded, never removed,
because a roster that erased people would make the time they actually served
unfilable. Here the case is a shade stronger. A coordinator adding somebody who
*did* go must not have that record invalidated by a reply that never came, so
`participation.is_participant` is untouched by this module and a blank or
declined response blocks nothing. What a decline buys is that the coordinator
knows, and can take the person off themselves.

**Blank is not `invited`.** `add_participant` puts somebody on a roster
directly, and that is a coordinator saying they are going, not a question. Only
`invite()` writes `invited`, so "waiting on an answer" is a state the roster can
actually express rather than one inferred from a field nobody set.

**Who hears the answer is derived, never stored.** A deployment is created by
`request.fulfil()` from a `VMMS Deployment Request`, and the person who wants to
know that a volunteer declined is whoever raised that request. So the audience is
resolved by reading back the requests pointing at this deployment, plus the
deployment's own owner. Storing a "notify this person" field instead would be a
second answer to a question the link already answers, and it would be wrong the
first time a deployment served two requests.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

from vmmsx.deployment.services import participation
from vmmsx.notifications.services import direct

DEPLOYMENT_DOCTYPE = "VMMS Deployment"
REQUEST_DOCTYPE = "VMMS Deployment Request"

INVITED = "invited"
ACCEPTED = "accepted"
DECLINED = "declined"

# The closed set. A response is one of these or blank, and blank means nobody
# was asked. Nothing outside this module compares against the strings.
RESPONSES = (INVITED, ACCEPTED, DECLINED)


def invite(deployment, volunteer: str, joined_on: str | None = None) -> dict:
	"""Ask a volunteer to join this deployment. Idempotent.

	Takes the document, like every service here, and saves it: unlike
	`participation.add`, this is one deliberate act per person rather than a
	roster being edited as a list, and the notification must not go out before
	the row it points at is committed.

	Re-inviting somebody who has already answered does **not** reopen their
	answer, and does not notify them again. A coordinator who wants to ask again
	after a decline is asking a new question, and the honest way to record that
	is a conversation, not a silent reset of the field holding what they said
	last time.
	"""
	row = _row(deployment, volunteer)

	if row and row.response:
		return _outcome(deployment, volunteer, invited=False)

	if not row:
		participation.add(deployment, volunteer)
		row = _row(deployment, volunteer)

	row.response = INVITED
	row.invited_on = now_datetime()

	if joined_on:
		row.joined_on = joined_on

	deployment.save()

	direct.tell(
		[login for login in [direct.login_of(volunteer)] if login],
		_("You have been invited to a deployment starting {0}").format(
			frappe.format_value(deployment.start_date, {"fieldtype": "Date"})
		),
		DEPLOYMENT_DOCTYPE,
		deployment.name,
	)

	return _outcome(deployment, volunteer, invited=True)


def respond(deployment, volunteer: str, accepted: bool, note: str | None = None) -> dict:
	"""Record a volunteer's answer and tell whoever asked. Idempotent.

	The second call with the same answer observes it is already recorded and
	returns without notifying again. A caller changing their mind is refused
	rather than quietly overwritten: an accepted invitation that becomes a
	decline is a withdrawal from a deployment somebody has already planned
	around, and it belongs in front of a coordinator rather than in a field that
	changed underneath them.
	"""
	row = _row(deployment, volunteer)

	if not row:
		frappe.throw(
			_("{0} has not been invited to this deployment.").format(frappe.bold(volunteer)),
			frappe.ValidationError,
			title=_("Not Invited"),
		)

	answer = ACCEPTED if accepted else DECLINED

	if row.response == answer:
		return _outcome(deployment, volunteer, invited=False)

	if row.response in (ACCEPTED, DECLINED):
		frappe.throw(
			_(
				"You have already answered this invitation. Speak to whoever asked you if that"
				" needs to change, so the deployment can be re-planned rather than changed"
				" underneath them."
			),
			frappe.ValidationError,
			title=_("Already Answered"),
		)

	row.response = answer
	row.responded_on = now_datetime()
	row.response_note = note

	# **The one elevated write in this module, and the volunteer is the reason.**
	# A volunteer holds no Geo Assignment and no role on `VMMS Deployment`, both
	# correctly: the deployment register is the society's record of work, not a
	# personal one. An ordinary `save()` here would refuse the only person
	# entitled to answer, and the alternative — granting every volunteer write
	# permission on every deployment so they could answer one invitation —
	# would be catastrophically wider than the thing being permitted.
	#
	# What replaces the permission check is the ownership check in
	# `api/deployment.py::respond_to_invitation`, which has already established
	# that the roster row being answered belongs to the caller's own volunteer
	# record. `invite()` above deliberately does not do this: it is reached only
	# through a door that checked `write` on the deployment first.
	deployment.save(ignore_permissions=True)

	direct.tell(
		askers(deployment),
		_("A volunteer has {0} their invitation to deployment {1}").format(
			_("accepted") if accepted else _("declined"), deployment.name
		),
		DEPLOYMENT_DOCTYPE,
		deployment.name,
	)

	return _outcome(deployment, volunteer, invited=False)


def askers(deployment) -> list[str]:
	"""Who should hear how an invitation was answered.

	Whoever raised a request this deployment fulfils, and the person who created
	the deployment itself. Both, because they are often two people and sometimes
	one: a request raised by a branch and fulfilled by a county coordinator
	leaves the branch waiting on an answer they never see otherwise.

	`doc.owner` is right here, and it is worth saying why, because the
	self-service rules elsewhere in this app say the opposite. There the bypass
	had to be `Red Profile.user`, because a membership's owner is the clerk who
	filed it and not the person it is about. This is not an identity question at
	all: it asks who *did the filing*, and `owner` is exactly that.
	"""
	people = {deployment.owner}

	people.update(
		frappe.get_all(
			REQUEST_DOCTYPE,
			filters={"deployment": deployment.name},
			pluck="owner",
			# Resolving who to notify, not disclosing anything: the answer is used
			# to address a notification and is never returned to a caller. A
			# coordinator recording a decline holds no read permission on another
			# branch's request, and requiring one would silently drop the
			# notification that request exists to receive.
			ignore_permissions=True,
		)
	)

	return sorted(person for person in people if person and person != "Administrator")


def pending_for(volunteer: str) -> list[dict]:
	"""This volunteer's unanswered invitations, as explicit rows for a DTO.

	Read straight off the child table by `volunteer`, the same unusual-but-
	correct query `participation.deployments_of` documents, with `parenttype` and
	`parentfield` both given so a docname shared with another child doctype
	cannot match.
	"""
	return _rows_for(volunteer, (INVITED,))


def answered_for(volunteer: str) -> list[dict]:
	"""The same volunteer's invitations they have already answered."""
	return _rows_for(volunteer, (ACCEPTED, DECLINED))


def _rows_for(volunteer: str, responses: tuple[str, ...]) -> list[dict]:
	"""Invitation rows for one volunteer in the given response states.

	Built field by field, and never the deployment document: a Deployment carries
	its whole roster, and handing one to a volunteer would disclose every other
	participant to somebody entitled only to their own invitation.
	"""
	if not volunteer:
		return []

	rows = frappe.get_all(
		participation.PARTICIPANT_DOCTYPE,
		filters={
			"parenttype": DEPLOYMENT_DOCTYPE,
			"parentfield": participation.ROSTER_FIELD,
			"volunteer": volunteer,
			"response": ("in", responses),
		},
		fields=["parent", "response", "invited_on", "responded_on", "response_note"],
		# A volunteer reading their own invitations. The volunteer is resolved
		# from the session by the endpoint above this and is never an argument, so
		# this cannot read anybody else's; requiring read permission on the
		# roster would mean granting every volunteer sight of every deployment.
		ignore_permissions=True,
	)

	if not rows:
		return []

	deployments = {
		row["name"]: row
		for row in frappe.get_all(
			DEPLOYMENT_DOCTYPE,
			filters={"name": ("in", [row["parent"] for row in rows])},
			fields=["name", "status", "start_date", "end_date", "geo_node", "terms_of_reference", "notes"],
			ignore_permissions=True,  # Same argument as above.
		)
	}

	invitations = []

	for row in rows:
		deployment = deployments.get(row["parent"])

		if not deployment:
			# The roster row outlived its parent. Skipped rather than rendered as
			# an invitation to nothing, exactly as `participation.history_of` does.
			continue

		invitations.append(
			{
				"deployment": deployment["name"],
				"title": _tor_name(deployment["terms_of_reference"]),
				"status": deployment["status"],
				"start_date": deployment["start_date"],
				"end_date": deployment["end_date"],
				"geo_node": deployment["geo_node"],
				"notes": deployment["notes"],
				"response": row["response"],
				"invited_on": row["invited_on"],
				"responded_on": row["responded_on"],
				"response_note": row["response_note"],
			}
		)

	invitations.sort(key=lambda row: (row["start_date"] is not None, row["start_date"]), reverse=True)

	return invitations


def _row(deployment, volunteer: str):
	"""This volunteer's roster row on a loaded deployment, or None.

	Read off the document rather than the database, unlike
	`participation.is_participant`, and for the opposite reason: the caller is
	about to write to this row and save the document, so it must be the row the
	document is holding.
	"""
	for row in deployment.participants or []:
		if row.volunteer == volunteer:
			return row

	return None


def _outcome(deployment, volunteer: str, invited: bool) -> dict:
	"""What a caller is told, built field by field.

	`notified` reports whether this call was the one that sent something, which
	is the visible form of the idempotence guarantee: a repeated invite answers
	with the same response and `notified` false.
	"""
	row = _row(deployment, volunteer)

	return {
		"deployment": deployment.name,
		"volunteer": volunteer,
		"response": (row.response if row else None) or "",
		"invited_on": row.invited_on if row else None,
		"responded_on": row.responded_on if row else None,
		"notified": invited,
	}


def _tor_name(terms_of_reference: str | None) -> str | None:
	"""The society's own word for the work, because a docname is not a title."""
	if not terms_of_reference:
		return None

	from vmmsx.deployment.services import terms

	return frappe.get_cached_value(terms.TERMS_DOCTYPE, terms_of_reference, "tor_name")
