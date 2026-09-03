# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The deployment's own lifecycle, and what a caller is told about one.

**Statuses are code; the work is configuration.** The six values below are a
closed set with a fixed transition table, for the same reason approval states
are code: each one means something the server acts on, so a society adding a
seventh would produce a deployment nothing knows how to handle. What a society
genuinely varies is *what it deploys people to do*, and that is
`VMMS Terms of Reference` — an open set of records on which **no code anywhere
branches**.

**Every status change goes through `assert_transition`.** The table is the whole
grammar. Closed Out and Cancelled are final: a deployment that finished is
history, and reopening it by editing a field would silently change what its time
logs were logged against.

**Suspended is a pause, not an ending**, and that is why it is a status rather
than a note. Work that has stopped because of a security incident or a road that
is under water is still somebody's problem, still has people assigned to it, and
still has to be told apart from work that finished. It goes back to Active when
the reason clears.

**Closed Out is Completed plus the paperwork**, and closing out waits for
nothing. `close_out` takes optional lessons and an optional report and records
who did it and when; there is deliberately no reconciliation of assignments,
tasks, incidents or hours in the way, because a close-out that can be blocked is
a close-out that never happens and leaves the register full of work that ended
months ago.

**The status deliberately does not gate time logs.** Ownership does, and only
ownership: somebody who served on a deployment may file the hours afterwards,
which is the ordinary case, and a Completed deployment refusing its own
participants' logs would be a rule that punishes accurate record-keeping. See
`participation.OWNERSHIP_RULE`.

**The period is a datetime, and the two Date fields are derived from it.** A
deployment genuinely starts at an hour — a briefing at seven, a check-in
deadline at noon — and everything in this app that windows on a period does so
by day. So `planned_start`/`planned_end` are what somebody writes and
`start_date`/`end_date` are read-only and computed from them in the controller,
which keeps one source of truth and leaves every existing reader alone. A record
written before that carries only the dates, and `derive_period` fills the
datetimes from them rather than refusing the record.
"""

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, now_datetime, today

from vmmsx.deployment.services import change

DEPLOYMENT_DOCTYPE = "VMMS Deployment"

STATUS_PLANNED = "Planned"
STATUS_ACTIVE = "Active"
STATUS_SUSPENDED = "Suspended"
STATUS_COMPLETED = "Completed"
STATUS_CLOSED_OUT = "Closed Out"
STATUS_CANCELLED = "Cancelled"

STATUSES = (
	STATUS_PLANNED,
	STATUS_ACTIVE,
	STATUS_SUSPENDED,
	STATUS_COMPLETED,
	STATUS_CLOSED_OUT,
	STATUS_CANCELLED,
)

# Open: the deployment is still somebody's problem — including a suspended one,
# which is precisely work that has not finished. Terminal: nothing moves it
# again. Completed is in neither, because it is the one status that is over and
# still has a move left in it: closing out.
OPEN_STATUSES = (STATUS_PLANNED, STATUS_ACTIVE, STATUS_SUSPENDED)
TERMINAL_STATUSES = (STATUS_CLOSED_OUT, STATUS_CANCELLED)

# Over, whatever happens to the paperwork afterwards. What a register filters on
# when it wants "not current work".
SETTLED_STATUSES = (STATUS_COMPLETED, STATUS_CLOSED_OUT, STATUS_CANCELLED)

TRANSITIONS: dict[str, tuple[str, ...]] = {
	# Planned to Planned, and Active to Active, are in the table because saving a
	# deployment without changing its status is the commonest thing that happens
	# to one. They are real transitions, not omissions.
	STATUS_PLANNED: (
		STATUS_PLANNED,
		STATUS_ACTIVE,
		STATUS_SUSPENDED,
		STATUS_COMPLETED,
		STATUS_CANCELLED,
	),
	# A deployment that has begun may be paused or called off; what it may not do
	# is go back to having been merely planned, because people were there.
	STATUS_ACTIVE: (STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_COMPLETED, STATUS_CANCELLED),
	# Paused. It resumes, it is written off as finished, or it is called off —
	# and it does not go back to Planned, for the same reason Active does not.
	STATUS_SUSPENDED: (STATUS_SUSPENDED, STATUS_ACTIVE, STATUS_COMPLETED, STATUS_CANCELLED),
	# The one move left after the work is over: the paperwork.
	STATUS_COMPLETED: (STATUS_COMPLETED, STATUS_CLOSED_OUT),
	STATUS_CLOSED_OUT: (STATUS_CLOSED_OUT,),
	STATUS_CANCELLED: (STATUS_CANCELLED,),
}


def assert_status(status: str | None) -> None:
	"""Throw unless `status` is one of the six."""
	if status in STATUSES:
		return

	frappe.throw(
		_("{0} is not a deployment status. Expected one of: {1}.").format(
			frappe.bold(status), ", ".join(STATUSES)
		),
		frappe.ValidationError,
		title=_("Unknown Deployment Status"),
	)


def can_transition(current: str | None, target: str) -> bool:
	"""Is `current` to `target` in the grammar?

	An unset status counts as Planned: a deployment that has never been moved is
	a planned one, whatever its field happens to hold.
	"""
	return target in TRANSITIONS.get(current or STATUS_PLANNED, ())


def assert_transition(current: str | None, target: str) -> None:
	"""Throw unless the move is legal. The single chokepoint for status changes."""
	assert_status(target)

	if can_transition(current, target):
		return

	if current in TERMINAL_STATUSES:
		frappe.throw(
			_("This deployment is {0}. A deployment that has ended cannot be moved again.").format(
				frappe.bold(_(current))
			),
			frappe.ValidationError,
			title=_("Deployment Already Ended"),
		)

	frappe.throw(
		_("A deployment cannot go from {0} to {1}.").format(
			frappe.bold(_(current or STATUS_PLANNED)), frappe.bold(_(target))
		),
		frappe.ValidationError,
		title=_("Invalid Deployment Transition"),
	)


def set_status(deployment, target: str, reason: str | None = None) -> dict:
	"""Move a deployment's status and save it. Idempotent.

	Idempotent because the table admits every status to itself: asking for the
	status a deployment already has writes nothing and records nothing.
	"""
	if deployment.status == target:
		return status_dto(deployment)

	assert_transition(deployment.status, target)
	deployment.status = target
	deployment.save()

	if reason:
		deployment.add_comment("Comment", _("{0}. {1}").format(_(target), reason))

	# Into the feed as well as onto the field, so that somebody reading an account
	# of the deployment sees when it started and when it ended in the same list as
	# everything that happened in between. The comment above is the desk's audit
	# trail and this is the account people read; they answer different questions
	# and both are cheap.
	from vmmsx.deployment.services import feed

	feed.note_status(deployment, target, reason)

	return status_dto(deployment)


# --- the period -------------------------------------------------------------


def derive_period(deployment) -> None:
	"""Keep the datetimes and the dates saying the same thing. Called from `validate`.

	One fact, written once. `planned_start` and `planned_end` are what somebody
	authors; `start_date` and `end_date` are read-only and derived from them, so
	no screen can put a start on Tuesday and a start date on Wednesday.

	**It fills backwards as well**, and that is not symmetry for its own sake: a
	deployment written before this field existed carries only the dates, and a
	rule that refused to save one until somebody retyped its period as a datetime
	would make every historical record unopenable. A date with no time is taken
	as the start of that day and the end of the other, which is what a period
	given in days has always meant.
	"""
	if not deployment.planned_start and deployment.start_date:
		deployment.planned_start = f"{getdate(deployment.start_date)} 00:00:00"

	if not deployment.planned_end and deployment.end_date:
		deployment.planned_end = f"{getdate(deployment.end_date)} 23:59:59"

	deployment.start_date = getdate(deployment.planned_start) if deployment.planned_start else None
	deployment.end_date = getdate(deployment.planned_end) if deployment.planned_end else None


def assert_schedule(deployment) -> None:
	"""Refuse a schedule that runs backwards. Each pair only where both are given.

	Four pairs, all optional, all checked the same way, because a society plans
	as much of a deployment as it knows about and the rest arrives later. What is
	never allowed is a briefing after the work ends or a return before it starts:
	those are typos, and they are the kind that quietly send somebody to the
	wrong place on the wrong day.
	"""
	pairs = (
		("planned_start", "planned_end", _("the planned start"), _("the planned end")),
		("actual_start", "actual_end", _("the actual start"), _("the actual end")),
		("briefing_on", "planned_end", _("the briefing"), _("the planned end")),
		("planned_start", "expected_return", _("the planned start"), _("the expected return")),
	)

	for earlier, later, earlier_label, later_label in pairs:
		if not (deployment.get(earlier) and deployment.get(later)):
			continue

		if get_datetime(deployment.get(later)) >= get_datetime(deployment.get(earlier)):
			continue

		frappe.throw(
			_("{0} falls before {1}.").format(
				frappe.bold(later_label.capitalize()), frappe.bold(earlier_label)
			),
			frappe.ValidationError,
			title=_("Schedule Runs Backwards"),
		)


# --- closing it out ---------------------------------------------------------


def close_out(deployment, lessons: str | None = None, report: str | None = None) -> dict:
	"""Move a completed deployment to Closed Out, and record who did it.

	**Nothing blocks it.** Not an unreconciled roster, not an open task, not a
	volunteer who never filed their hours. A close-out that can be refused is one
	that does not happen, and a register full of work that ended in March is
	worse than one whose paperwork is thin. Both fields are optional and stay
	optional.

	The transition table is what refuses a close-out on work that is not finished
	yet, which is the one rule here: Completed is the only status this move is
	reachable from.
	"""
	assert_transition(deployment.status, STATUS_CLOSED_OUT)

	deployment.status = STATUS_CLOSED_OUT
	deployment.closed_out_on = now_datetime()
	deployment.closed_out_by = frappe.session.user

	if lessons:
		deployment.lessons_learned = lessons

	if report:
		deployment.mission_report = report

	deployment.save()

	from vmmsx.deployment.services import feed

	feed.note_status(deployment, STATUS_CLOSED_OUT, None)

	return status_dto(deployment)


def create(
	terms_of_reference: str,
	geo_node: str,
	start_date,
	end_date,
	volunteers_required: int | None = None,
	status: str | None = None,
	email_template: str | None = None,
	notes: str | None = None,
	coordinator: str | None = None,
	**place,
):
	"""Insert a deployment directly, without a request in front of it.

	The other way in is `request.fulfil`, which is the approval engine making a
	request real and elevates for a reason it states at length. This is the
	coordinator who is not asking anybody: a branch running its own duty under
	its own terms. So it is an **ordinary insert** — core's query condition runs
	on the anchor and refuses a deployment filed outside the coordinator's own
	area, which is exactly the check `fulfil` cannot use and this one must.

	The two coherence rules are checked here rather than left to the first save,
	so a caller is told which of them refused: these terms are retired, or this
	place is outside them.

	`volunteers_required` is how many people the deployment needs, and it is the
	cap `assignment.assert_room` measures the roster against. Optional, and zero
	means the society has not said — a deployment that has not said how many it
	needs is never full, which is the right default for a branch duty nobody has
	put a number on.
	"""
	from vmmsx.deployment.services import terms

	if not geo_node:
		# ACC-02 restated at the boundary, so a caller gets a sentence about
		# placement rather than a mandatory-field name.
		frappe.throw(
			_("A deployment must be anchored to a place in the organisation before it can be saved."),
			frappe.MandatoryError,
			title=_("Where Is This Deployment?"),
		)

	terms.assert_offered(terms_of_reference)
	terms.assert_within_scope(terms_of_reference, geo_node)

	deployment = frappe.get_doc(
		{
			"doctype": DEPLOYMENT_DOCTYPE,
			"terms_of_reference": terms_of_reference,
			"geo_node": geo_node,
			# The two Date fields are derived in `validate`; what is written here
			# is the period as a datetime. A caller that has only days gets the
			# whole of the first day and the whole of the last, which is what a
			# period given in days has always meant.
			"planned_start": f"{getdate(start_date)} 00:00:00",
			"planned_end": f"{getdate(end_date)} 23:59:59",
			"status": status or STATUS_PLANNED,
			"volunteers_required": frappe.utils.cint(volunteers_required),
			"email_template": email_template or None,
			"notes": notes,
			# Whoever is opening it, unless a caller names somebody else. The
			# field is mandatory and this is the honest default: the coordinator
			# filing a deployment is the coordinator running it until somebody
			# says otherwise.
			"coordinator": coordinator or frappe.session.user,
			**{field: value for field, value in place.items() if field in PLACE_FIELDS},
		}
	)
	deployment.insert()

	return deployment


# Everything about where the work is and how to reach it. Named as a set so
# `create` can take them through `**place` without a caller being able to write
# a field nobody reviewed, and so `change.py` and the DTO read the same list.
PLACE_FIELDS = (
	"site_name",
	"site_address",
	"site_latitude",
	"site_longitude",
	"meeting_point",
	"meeting_address",
	"meeting_latitude",
	"meeting_longitude",
	"travel_notes",
	"local_contact_name",
	"local_contact_phone",
	"briefing_on",
	"check_in_deadline",
	"expected_return",
)


# What a coordinator may correct on a deployment that already exists, beyond the
# place. Deliberately narrow, and deliberately not the whole document:
#
# - `terms_of_reference` and `geo_node` are not here. Both were checked against
#   each other at creation — `terms.assert_within_scope` — and changing either
#   afterwards is a different deployment under a different mission, not an edit.
# - `status` is not here. `set_status` is its own act with its own reason, and a
#   select buried in a form is how a deployment gets cancelled by accident.
# - The two `Date` fields are not here. They are derived in `validate` from the
#   planned period, and a caller that could set them could make them disagree
#   with the datetimes they come from.
EDITABLE_FIELDS = (
	"coordinator",
	"volunteers_required",
	"email_template",
	"notes",
	"planned_start",
	"planned_end",
	"actual_start",
	"actual_end",
)


def update(deployment, values: dict):
	"""Correct a deployment that already exists, and record why where it matters.

	**Through the document's own `save`, which is the whole point.** A deployment
	moving its meeting point is not a private edit: `change.on_validate` compares
	the material fields against what was stored, insists on a reason where one is
	owed, records the change and announces it to everybody already on the roster.
	A writer that reached past `save` would skip all of it, and the first anybody
	on the deployment would hear of the new meeting point is when they arrived at
	the old one.

	`change_reason` is written before the comparison runs, because that is what
	`change.assert_reason` reads — a coordinator supplies it in the same save as
	the change it explains, rather than in a second one after being refused.
	"""
	writable = PLACE_FIELDS + EDITABLE_FIELDS + (change.REASON_FIELD,)

	for field, value in values.items():
		if field in writable:
			deployment.set(field, value)

	deployment.save()

	return deployment


def is_open(deployment) -> bool:
	return deployment.status in OPEN_STATUSES


def covers(deployment, on_date=None) -> bool:
	"""Was this deployment running on `on_date`? A question about its period only.

	Used to describe a deployment, never to accept or refuse a time log: what a
	log needs is the roster, and a volunteer filing late is filing accurately.
	"""
	as_of = getdate(on_date or today())

	return getdate(deployment.start_date) <= as_of <= getdate(deployment.end_date)


def in_flight(deployment, on_date=None) -> bool:
	"""Is this deployment both open and currently running?"""
	return is_open(deployment) and covers(deployment, on_date)


# --- the DTOs -------------------------------------------------------------


def status_dto(deployment, counts: dict | None = None) -> dict:
	"""Where a deployment stands, as an explicit dict. Built field by field.

	Never the Document: that would leak every field on the record, including ones
	nobody reviewed, and turn every schema change into an API change.

	**`counts` is passed in by listings and computed here only for one-offs.**
	The roster lives in `VMMS Deployment Assignment` now, so the headcount is a
	query rather than `len()` on a child table, and a listing that let this run
	its own query per row would be the N+1 that makes the register crawl at the
	size a national society actually runs at. `assignment.counts_for_many` answers
	the whole page in one grouped query; callers reading a single deployment can
	leave it out and pay for one.
	"""
	from vmmsx.deployment.services import assignment
	from vmmsx.deployment.services.placement import geo_path

	tally = counts if counts is not None else assignment.counts_for(deployment.name)

	return {
		"name": deployment.name,
		"terms_of_reference": deployment.terms_of_reference,
		"geo_node": deployment.geo_node,
		# Through `placement.geo_path`, so a deployment whose anchor was deleted
		# underneath it is one odd-looking row rather than a register that refuses
		# to open. That module says why the case is real.
		"geo_path": geo_path(deployment.geo_node),
		"status": deployment.status,
		"is_open": is_open(deployment),
		"is_settled": deployment.status in SETTLED_STATUSES,
		"is_closed_out": deployment.status == STATUS_CLOSED_OUT,
		"coordinator": deployment.coordinator,
		"start_date": deployment.start_date,
		"end_date": deployment.end_date,
		# The period to the hour, and the four other moments a deployment has.
		# Separate from the two dates above rather than replacing them: every
		# register in this app windows on days, and every volunteer needs to know
		# what time to be at the meeting point.
		"planned_start": deployment.planned_start,
		"planned_end": deployment.planned_end,
		"briefing_on": deployment.briefing_on,
		"check_in_deadline": deployment.check_in_deadline,
		"expected_return": deployment.expected_return,
		"actual_start": deployment.actual_start,
		"actual_end": deployment.actual_end,
		# When the paperwork was filed. On the summary rather than only on the
		# full record because the past register is a shelf of *closed* mission
		# files and the date one was closed is the thing it is filed under — a
		# register that had to derive it from `end_date` would be dating the work
		# rather than the file.
		"closed_out_on": deployment.closed_out_on,
		"volunteers_required": deployment.volunteers_required or 0,
		"email_template": deployment.email_template,
		# Who is actually going: Assigned plus Accepted. The name is kept from
		# when the roster was a child table, because every screen and every test
		# reads it and renaming it would buy nothing.
		"participant_count": tally["on_deployment"],
		# The rest of the register in the same breath, so a listing row can say
		# "4 of 6, 3 still to answer" without a second call.
		"assignment_counts": tally,
		"places_left": max(frappe.utils.cint(deployment.volunteers_required) - tally["on_deployment"], 0)
		if frappe.utils.cint(deployment.volunteers_required) > 0
		else None,
	}


def where_dto(deployment) -> dict:
	"""The two places a deployment has, and how somebody gets to them.

	Its own function because two different callers want exactly this and nothing
	else: the deployment page, and every invitation. An invitation that told
	somebody the date and not the meeting point would be the one piece of paper
	they actually needed and did not get.
	"""
	from vmmsx.deployment.services import geocoding

	return {
		"site": geocoding.dto(deployment, geocoding.SITE),
		# The one field a prefix cannot derive: a society calls this the meeting
		# point, not the meeting name.
		"meeting_point": geocoding.dto(deployment, geocoding.MEETING, name_field="meeting_point"),
		"travel_notes": deployment.travel_notes,
		"local_contact": {
			"name": deployment.local_contact_name,
			"phone": deployment.local_contact_phone,
		},
	}


def coordinator_dto(deployment) -> dict:
	"""Who to ring, in the words a volunteer needs rather than as a login.

	Built from the `User` the deployment names. Empty strings rather than `None`
	where the account carries no phone number, so an invitation template's `{% if
	%}` guards read the same whether the society fills that in or not.
	"""
	if not deployment.coordinator:
		return {"user": None, "full_name": "", "email": "", "phone": ""}

	row = frappe.db.get_value(
		"User", deployment.coordinator, ["full_name", "email", "mobile_no", "phone"], as_dict=True
	)

	if not row:
		return {"user": deployment.coordinator, "full_name": "", "email": "", "phone": ""}

	return {
		"user": deployment.coordinator,
		"full_name": row.full_name or "",
		"email": row.email or "",
		"phone": row.mobile_no or row.phone or "",
	}


def deployment_dto(deployment) -> dict:
	"""Everything about one deployment: its terms, its period, its place and who is on it."""
	from vmmsx.deployment.services import assignment, terms

	return {
		**status_dto(deployment),
		"terms": terms.dto(deployment.terms_of_reference),
		"where": where_dto(deployment),
		"coordinator_contact": coordinator_dto(deployment),
		"close_out": {
			"closed_out_on": deployment.closed_out_on,
			"closed_out_by": deployment.closed_out_by,
			"lessons_learned": deployment.lessons_learned,
			"mission_report": deployment.mission_report,
		},
		"change_reason": deployment.change_reason,
		# The whole assignment register, settled rows included: a coordinator
		# looking at a deployment needs to see who declined as much as who
		# accepted, or they will ask the same person again next week.
		"participants": assignment.roster_of(deployment.name),
		"leader": assignment.leader_of(deployment.name),
		"notes": deployment.notes,
	}
