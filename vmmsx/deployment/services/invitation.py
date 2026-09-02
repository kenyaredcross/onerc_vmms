# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Asking a volunteer to go, and carrying their answer back.

`assignment.py` owns the record and its grammar. `participation.py` owns the one
question the rest of the app asks of a roster. This owns the **conversation**:
the volunteer's own view of what they have been asked, and the derivation of who
hears what they said.

**What is left here after the roster became a register of documents.** Not much
of the mechanism, and that is the point — asking somebody is now
`assignment.create(..., status=Pending)` and answering is
`assignment.respond`, both of which write a real record with a URL the volunteer
can open and a reference an email can point at. What could not move into
`assignment.py` is this module's two remaining jobs:

* **The volunteer's own side.** `pending_for` and `answered_for` read a
  volunteer's assignments together with the deployments they are for, with
  `ignore_permissions` and the argument for it written down, because a volunteer
  holds no Geo Assignment and a scoped read would hand them an empty list of the
  questions they were personally asked.
* **Who hears the answer.** `askers` derives the audience by reading back the
  requests pointing at a deployment, plus the deployment's own owner. Storing a
  "notify this person" field instead would be a second answer to a question the
  link already answers, and it would be wrong the first time a deployment served
  two requests.

**An invitation still does not decide who is on the deployment.** It decides
what the assignment's status is, which is a different sentence than it used to
be and a truer one: `Pending` is a question outstanding, `Accepted` and
`Declined` are the answer, and only `Assigned` and `Accepted` mean somebody is
going. Under the child-table model all of that lived in one nullable field and
"blank" had to carry the weight of "placed directly, never asked".
"""

import frappe
from frappe import _

from vmmsx.deployment.services import assignment
from vmmsx.deployment.services import deployment as deployment_service

DEPLOYMENT_DOCTYPE = "VMMS Deployment"
REQUEST_DOCTYPE = "VMMS Deployment Request"

# Kept as this module's public vocabulary for what a volunteer was told, mapped
# onto the assignment statuses that carry it. Nothing outside compares against
# the strings; screens read the booleans on the DTO.
INVITED = assignment.STATUS_PENDING
ACCEPTED = assignment.STATUS_ACCEPTED
DECLINED = assignment.STATUS_DECLINED

RESPONSES = (INVITED, ACCEPTED, DECLINED)


def invite(
	deployment_doc,
	volunteer: str,
	joined_on: str | None = None,
	answer_by: str | None = None,
	assignment_title: str | None = None,
	assignment_description: str | None = None,
	supervisor: str | None = None,
) -> dict:
	"""Ask a volunteer to join this deployment. Idempotent.

	Re-asking somebody who already has an open assignment does **not** ask again
	and does not notify them again: the question is already in front of them.
	Asking again after a decline is a different act and a real one — it raises a
	*new* assignment, so the register keeps both what they said the first time
	and what they were asked the second. That is the behaviour a child row could
	not have, because there was only ever one row to overwrite.
	"""
	existing = assignment.open_assignment(deployment_doc.name, volunteer)

	if existing:
		return {
			"deployment": deployment_doc.name,
			"volunteer": volunteer,
			"assignment": existing.name,
			"status": existing.status,
			"notified": False,
		}

	doc = assignment.create(
		deployment_doc,
		volunteer,
		status=assignment.STATUS_PENDING,
		joined_on=joined_on,
		assignment_title=assignment_title,
		assignment_description=assignment_description,
		supervisor=supervisor,
		invitation_expires_on=answer_by,
	)

	return {
		"deployment": deployment_doc.name,
		"volunteer": volunteer,
		"assignment": doc.name,
		"status": doc.status,
		# The controller's `after_insert` sent it, on the record it is about.
		"notified": True,
	}


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
	"""This volunteer's unanswered questions, as explicit rows for a DTO."""
	return _rows_for(volunteer, (assignment.STATUS_PENDING,))


def answered_for(volunteer: str) -> list[dict]:
	"""The same volunteer's assignments they have already answered."""
	return _rows_for(volunteer, (assignment.STATUS_ACCEPTED, assignment.STATUS_DECLINED))


def _rows_for(volunteer: str, statuses: tuple[str, ...]) -> list[dict]:
	"""One volunteer's assignments in the given states, with the deployment each is for.

	Built field by field, and never the deployment document: a Deployment read in
	full would drag facts about the work into a shape about one person's question.

	**`ignore_permissions`, with the argument stated rather than assumed.** The
	volunteer is resolved from the session by the endpoint above this and is never
	an argument, so this cannot read anybody else's. Requiring read permission
	instead would mean granting every volunteer sight of the deployment register
	so they could see the one question addressed to them.
	"""
	if not volunteer:
		return []

	rows = frappe.get_all(
		assignment.ASSIGNMENT_DOCTYPE,
		filters={"volunteer": volunteer, "status": ("in", statuses)},
		fields=[
			"name",
			"deployment",
			"terms_of_reference",
			"status",
			"role",
			"assignment_title",
			"assignment_description",
			"supervisor",
			"start_date",
			"end_date",
			"invited_on",
			"invitation_expires_on",
			"responded_on",
			"response_note",
			"briefing_completed_on",
			"safety_acknowledged_on",
		],
		ignore_permissions=True,
	)

	if not rows:
		return []

	deployments = {
		row["name"]: row
		for row in frappe.get_all(
			DEPLOYMENT_DOCTYPE,
			filters={"name": ("in", [row["deployment"] for row in rows])},
			# Everything an invitation has to carry. The list is long because the
			# thing being answered is long: somebody deciding whether they can go
			# needs to know when to be where, how to get there, who to ring at
			# either end, and what the road is like. An invitation that gave them
			# the dates and made them find the rest is the one piece of paper they
			# actually needed and did not get.
			fields=[
				"name",
				"status",
				"start_date",
				"end_date",
				"geo_node",
				"notes",
				"coordinator",
				"planned_start",
				"planned_end",
				"briefing_on",
				"check_in_deadline",
				"expected_return",
				"site_name",
				"site_address",
				"site_latitude",
				"site_longitude",
				"site_located_on",
				"meeting_point",
				"meeting_address",
				"meeting_latitude",
				"meeting_longitude",
				"meeting_located_on",
				"travel_notes",
				"local_contact_name",
				"local_contact_phone",
			],
			ignore_permissions=True,  # Same argument as above.
		)
	}

	invitations = []

	for row in rows:
		deployment = deployments.get(row["deployment"])

		if not deployment:
			# The assignment outlived its deployment. Skipped rather than rendered
			# as an invitation to nothing, exactly as `participation.history_of` does.
			continue

		invitations.append(
			{
				"assignment": row["name"],
				"deployment": deployment["name"],
				"title": _tor_name(row["terms_of_reference"]),
				"terms_of_reference": row["terms_of_reference"],
				"deployment_status": deployment["status"],
				# The volunteer's own dates, which may be narrower than the
				# deployment's: somebody joining a fortnight-long response for its
				# last three days is being asked about those three days.
				"start_date": row["start_date"] or deployment["start_date"],
				"end_date": row["end_date"] or deployment["end_date"],
				"geo_node": deployment["geo_node"],
				"notes": deployment["notes"],
				# When to be there, where, how to get there, and who to ring. Built
				# by the deployment service from the row above rather than restated
				# here, so an invitation and a deployment page cannot describe the
				# same place differently.
				"schedule": {
					"planned_start": deployment["planned_start"],
					"planned_end": deployment["planned_end"],
					"briefing_on": deployment["briefing_on"],
					"check_in_deadline": deployment["check_in_deadline"],
					"expected_return": deployment["expected_return"],
				},
				"where": deployment_service.where_dto(deployment),
				"coordinator_contact": deployment_service.coordinator_dto(deployment),
				"response": row["status"],
				"role": row["role"],
				"assignment_title": row["assignment_title"],
				"assignment_description": row["assignment_description"],
				"supervisor": row["supervisor"],
				"invited_on": row["invited_on"],
				"answer_by": row["invitation_expires_on"],
				"responded_on": row["responded_on"],
				"response_note": row["response_note"],
				"briefing_completed_on": row["briefing_completed_on"],
				"safety_acknowledged_on": row["safety_acknowledged_on"],
			}
		)

	invitations.sort(key=lambda row: (row["start_date"] is not None, row["start_date"]), reverse=True)

	return invitations


def _tor_name(terms_of_reference: str | None) -> str | None:
	"""The society's own word for a terms of reference, or None if it names none."""
	if not terms_of_reference:
		return None

	from vmmsx.deployment.services import terms

	return frappe.get_cached_value(terms.TERMS_DOCTYPE, terms_of_reference, "tor_name")
