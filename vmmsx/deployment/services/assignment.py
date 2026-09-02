# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One person's deployment: the record of being placed or asked, and answering.

**Why this is a document and not a child row.** It used to be a row on
`VMMS Deployment.participants`, and `participation.py` argued the case for that
at length: a roster is a property of the deployment, it is edited as one list,
and it is checked against one permission. That argument held for as long as a
roster row was only a roster row. It stopped holding the moment each person's
deployment needed things a child row cannot carry:

* **Something to address.** An email and an SMS need a `reference_doctype` and
  a `reference_name`. A child row has neither, so a notification about one
  person's assignment had to point at the whole deployment and hope they worked
  out which part concerned them.
* **Something a volunteer can open.** Accepting is the volunteer's own act on
  their own record. A child row has no URL, no permission of its own, and no way
  to be shown to one person without showing them the whole roster.
* **A lifecycle.** Assigned, asked, answered, withdrawn — with a grammar that
  refuses the moves that make no sense. A child row's fields can each be set to
  anything by anybody editing the grid.
* **A place to put the terms they agreed to.** This is the one that settles it.
  There is no separate contract in this app: accepting an assignment *is*
  accepting the terms of reference, so the assignment has to record which
  document that was. An amendment to the terms afterwards must leave what
  somebody already agreed to exactly where it was.

What the change costs, stated as plainly as the old docstring stated its own
trade: a roster is now N records rather than one list, so placing five people is
five inserts and five permission checks rather than one save. `deploy()` below
is what makes that bearable — one call, one savepoint per person, and an honest
report of which ones did not take.

**Assigned and Accepted are the two that mean "on this deployment".** They fill
a place against the headcount, and they are what lets time be logged. Pending is
a question outstanding. Declined and Withdrawn are the record that somebody was
asked and is not going — kept, never deleted, because a register that erased the
people who said no would make the same coordinator ask them again next week.

**This is a change from how a decline used to behave**, and it is deliberate.
Under the child-table model a decline left `is_participant` untouched, so a
volunteer who said no could still file time against the deployment. That was the
only way to protect a record of service in a model where one field held both
"did you go" and "what did you say". Here they are two different facts on two
different fields: `status` says what they answered, `joined_on` and `left_on` say
what they actually did. A coordinator whose volunteer went anyway moves them to
Assigned, which is a true statement, rather than relying on a decline meaning
nothing.
"""

import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import getdate, now_datetime

from vmmsx.deployment.services import terms as terms_service

ASSIGNMENT_DOCTYPE = "VMMS Deployment Assignment"
DEPLOYMENT_DOCTYPE = "VMMS Deployment"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"

# --- the grammar ----------------------------------------------------------

STATUS_ASSIGNED = "Assigned"
STATUS_PENDING = "Pending"
STATUS_ACCEPTED = "Accepted"
STATUS_DECLINED = "Declined"
STATUS_WITHDRAWN = "Withdrawn"

# What happened to a question nobody answered, and what happened on the day.
# Added when the roster grew an outcome: "did they go" is a different fact from
# "what did they say", and a register that only had the second could never
# answer the first.
STATUS_EXPIRED = "Expired"
STATUS_PARTICIPATED = "Participated"
STATUS_PARTIAL = "Partial Attendance"
STATUS_NO_SHOW = "No Show"

# Somebody else went instead. The original is kept and points at the new one.
STATUS_REPLACED = "Replaced"

STATUSES = (
	STATUS_ASSIGNED,
	STATUS_PENDING,
	STATUS_ACCEPTED,
	STATUS_DECLINED,
	STATUS_WITHDRAWN,
	STATUS_EXPIRED,
	STATUS_PARTICIPATED,
	STATUS_PARTIAL,
	STATUS_NO_SHOW,
	STATUS_REPLACED,
)

# What actually happened on the day. A closed set, and the only three answers to
# "did they go": all of it, some of it, or none of it.
OUTCOMES = (STATUS_PARTICIPATED, STATUS_PARTIAL, STATUS_NO_SHOW)

# The two outcomes that mean they were there. `No Show` is deliberately not one:
# somebody who did not come did not serve, and nothing should let them log time
# against the deployment as though they had.
ATTENDED = (STATUS_PARTICIPATED, STATUS_PARTIAL)

# This person is, or was, on the deployment: they hold a place against the
# headcount, and this is what `participation.is_participant` reads. The two
# attendance outcomes are in it for a reason worth stating — a deployment that
# has been closed out and had its attendance recorded must not thereby stop its
# own participants filing the hours they served, which is exactly the rule
# `participation.OWNERSHIP_RULE` exists to protect.
ON_DEPLOYMENT = (STATUS_ASSIGNED, STATUS_ACCEPTED, *ATTENDED)

# Still somebody's problem — a coordinator's or a volunteer's.
OPEN_STATUSES = (STATUS_ASSIGNED, STATUS_PENDING, STATUS_ACCEPTED)

# Settled. Nothing moves out of these.
TERMINAL_STATUSES = (
	STATUS_DECLINED,
	STATUS_WITHDRAWN,
	STATUS_EXPIRED,
	STATUS_REPLACED,
	*OUTCOMES,
)

# The whole grammar, in the same shape as `deployment.py`'s own table and for
# the same reason: every legal move is written down once, and every move not
# written down is refused with a sentence saying why.
#
# Each status admits itself, because saving an assignment without changing its
# status is the commonest thing that happens to one.
TRANSITIONS: dict[str, tuple[str, ...]] = {
	# Placed directly. The coordinator may still decide to ask after all, and may
	# take it back or swap somebody in. It cannot become Declined: nobody was
	# asked, so there is no answer to record. It can reach an outcome, because a
	# person who was placed and never asked still either turned up or did not.
	STATUS_ASSIGNED: (
		STATUS_ASSIGNED,
		STATUS_PENDING,
		STATUS_WITHDRAWN,
		STATUS_REPLACED,
		*OUTCOMES,
	),
	# Asked. The volunteer answers, the coordinator takes the question back or
	# swaps somebody in, or the clock runs out. **Expired is not Declined** and
	# the difference is the point: one is a person who said no, the other is a
	# question nobody ever saw.
	STATUS_PENDING: (
		STATUS_PENDING,
		STATUS_ACCEPTED,
		STATUS_DECLINED,
		STATUS_WITHDRAWN,
		STATUS_EXPIRED,
		STATUS_REPLACED,
	),
	# Answered yes. A withdrawal or a replacement moves it, and so does the day
	# itself: somebody who accepted either turned up or did not. Changing their
	# mind after accepting is a withdrawal from a deployment that has been planned
	# around them, and it belongs in front of a coordinator rather than in a field
	# that changed underneath them.
	STATUS_ACCEPTED: (STATUS_ACCEPTED, STATUS_WITHDRAWN, STATUS_REPLACED, *OUTCOMES),
	STATUS_DECLINED: (STATUS_DECLINED,),
	STATUS_WITHDRAWN: (STATUS_WITHDRAWN,),
	STATUS_EXPIRED: (STATUS_EXPIRED,),
	STATUS_REPLACED: (STATUS_REPLACED,),
	# An outcome is a statement about a day that has happened. Each admits
	# itself, so re-recording the same one is harmless; none admits another,
	# because a coordinator who marked the wrong person is correcting a record
	# rather than moving a lifecycle, and that goes through an amendment where
	# somebody can see it.
	STATUS_PARTICIPATED: (STATUS_PARTICIPATED,),
	STATUS_PARTIAL: (STATUS_PARTIAL,),
	STATUS_NO_SHOW: (STATUS_NO_SHOW,),
}


def assert_status(status: str | None) -> None:
	"""Throw unless `status` is one of the ten."""
	if status in STATUSES:
		return

	frappe.throw(
		_("{0} is not an assignment status. Expected one of: {1}.").format(
			frappe.bold(status), ", ".join(STATUSES)
		),
		frappe.ValidationError,
		title=_("Unknown Assignment Status"),
	)


def can_transition(current: str | None, target: str) -> bool:
	"""Is `current` to `target` in the grammar? An unset status counts as Pending."""
	return target in TRANSITIONS.get(current or STATUS_PENDING, ())


def assert_transition(current: str | None, target: str) -> None:
	"""Throw unless the move is legal. The single chokepoint for status changes."""
	assert_status(target)

	if can_transition(current, target):
		return

	if current in TERMINAL_STATUSES:
		frappe.throw(
			_(
				"This assignment is {0} and cannot be moved again. Raise a new one if this person"
				" is going after all — that keeps the record of what they said the first time."
			).format(frappe.bold(_(current))),
			frappe.ValidationError,
			title=_("Assignment Already Settled"),
		)

	frappe.throw(
		_("An assignment cannot go from {0} to {1}.").format(
			frappe.bold(_(current or STATUS_PENDING)), frappe.bold(_(target))
		),
		frappe.ValidationError,
		title=_("Invalid Assignment Transition"),
	)


# --- the headcount --------------------------------------------------------


def filled(deployment: str, excluding: str | None = None) -> int:
	"""How many places on this deployment are taken.

	Assigned and Accepted, because those are the two that mean somebody is going.
	A Pending assignment holds no place: a deployment needing six people that has
	asked twenty has not filled anything yet, and counting the questions would
	stop it asking the twenty-first.
	"""
	filters = {"deployment": deployment, "status": ("in", ON_DEPLOYMENT)}

	if excluding:
		filters["name"] = ("!=", excluding)

	# Not `get_all`: this is a count the caller is about to act on, and it must
	# be the whole truth about the deployment rather than the part of it this
	# session may read. A coordinator who can see four of six assignments must
	# not be told there are two places left.
	return frappe.db.count(ASSIGNMENT_DOCTYPE, filters)


def assert_room(deployment_doc, excluding: str | None = None) -> None:
	"""Throw if this deployment is already full.

	**Locks the deployment row first.** Two coordinators accepting the last place
	at the same moment would each read five-of-six and each write the sixth
	without a lock, and the deployment would end up with seven people on a
	six-person job. The `for_update` read is what serialises them: the second one
	waits, re-counts, and is refused.

	A deployment that has not said how many people it needs is never full, which
	is what leaving the field at zero means.
	"""
	wanted = frappe.utils.cint(deployment_doc.volunteers_required)

	if wanted <= 0:
		return

	frappe.db.get_value(DEPLOYMENT_DOCTYPE, deployment_doc.name, "name", for_update=True)

	if filled(deployment_doc.name, excluding=excluding) < wanted:
		return

	frappe.throw(
		_(
			"This deployment asked for {0} volunteer(s) and that many are already on it. Raise the"
			" number it needs, or withdraw somebody, before adding another."
		).format(wanted),
		frappe.ValidationError,
		title=_("Deployment Already Full"),
	)


# --- raising one ----------------------------------------------------------


def create(
	deployment_doc,
	volunteer: str,
	status: str = STATUS_PENDING,
	role: str = "member",
	joined_on: str | None = None,
	notes: str | None = None,
	assignment_title: str | None = None,
	assignment_description: str | None = None,
	supervisor: str | None = None,
	invitation_expires_on: str | None = None,
) -> object:
	"""Raise one assignment against a deployment. Returns the document.

	**`status` is the caller's choice between the two verbs this app has always
	drawn apart.** `Assigned` is a coordinator saying somebody is going;
	`Pending` is a question that person can answer. Collapsing them would make
	"who fits", "who was asked" and "who is going" one field, and they are three.

	The terms of reference and the geo node are copied from the deployment rather
	than passed in. They are what the person is agreeing to and where the work
	is, and a caller that could name them separately could raise an assignment
	against terms the deployment is not being run under.

	Refuses a second open assignment for the same person on the same deployment.
	A settled one — declined, withdrawn — does not block a new one: asking again
	after a no is a real thing a coordinator does, and it produces a second
	record rather than overwriting what they said the first time.

	**Deployability is deliberately not re-checked here**, and it is worth saying
	so rather than leaving it to be noticed. `matching.candidates()` will not
	offer somebody who is suspended or whose required certification has lapsed, so
	the ordinary path never reaches this with one; but this call takes a list of
	names and does not re-ask. That is the same choice the roster made before it
	was a register — a coordinator may know something the certification dates do
	not, and refusing them here would mean the app overruling somebody with the
	facts in front of them. What it does still refuse is terms that no longer take
	work, because that is a fact about the *document* somebody is being asked to
	agree to rather than a judgement about the person.
	"""
	assert_status(status)

	if status not in (STATUS_ASSIGNED, STATUS_PENDING):
		frappe.throw(
			_("An assignment is raised as {0} or {1}, never as {2}.").format(
				frappe.bold(STATUS_ASSIGNED), frappe.bold(STATUS_PENDING), frappe.bold(status)
			),
			frappe.ValidationError,
			title=_("Cannot Raise That Assignment"),
		)

	existing = open_assignment(deployment_doc.name, volunteer)

	if existing:
		frappe.throw(
			_("{0} already has an assignment on this deployment, and it is {1}.").format(
				frappe.bold(volunteer_label(volunteer)), frappe.bold(_(existing.status))
			),
			frappe.DuplicateEntryError,
			title=_("Already Assigned"),
		)

	if status == STATUS_ASSIGNED:
		# Only a placement fills a place, so only a placement is capped here. A
		# question is capped when it is answered, in `respond`.
		assert_room(deployment_doc)

	doc = frappe.get_doc(
		{
			"doctype": ASSIGNMENT_DOCTYPE,
			"deployment": deployment_doc.name,
			"volunteer": volunteer,
			"terms_of_reference": deployment_doc.terms_of_reference,
			"geo_node": deployment_doc.geo_node,
			"status": status,
			"role": role or "member",
			"start_date": deployment_doc.start_date,
			"end_date": deployment_doc.end_date,
			"joined_on": joined_on,
			"notes": notes,
			"assignment_title": assignment_title,
			"assignment_description": assignment_description,
			"supervisor": supervisor,
			"invited_on": now_datetime() if status == STATUS_PENDING else None,
			# Who asked, so a volunteer opening the invitation knows whose
			# decision it was, and so a coordinator reading a roster months later
			# does not have to guess from the document's owner.
			"invited_by": frappe.session.user if status == STATUS_PENDING else None,
			# **No default expiry**, deliberately. How long a society leaves a
			# question standing is a society's answer, and inventing one here would
			# start expiring invitations on sites that never asked for it. Given a
			# date, `expire_overdue` acts on it; given none, the question stands.
			"invitation_expires_on": invitation_expires_on,
		}
	)
	doc.insert()

	return doc


def open_assignment(deployment: str, volunteer: str):
	"""This volunteer's unsettled assignment on this deployment, or None.

	Unsettled rather than any: a declined assignment from last month must not
	stop a coordinator asking again this month.
	"""
	name = frappe.db.get_value(
		ASSIGNMENT_DOCTYPE,
		{
			"deployment": deployment,
			"volunteer": volunteer,
			"status": ("in", OPEN_STATUSES),
		},
		"name",
	)

	return frappe.get_doc(ASSIGNMENT_DOCTYPE, name) if name else None


# --- raising many ---------------------------------------------------------


def deploy(
	deployment_doc,
	volunteers: list[str],
	status: str = STATUS_PENDING,
	notes: str | None = None,
) -> dict:
	"""Raise assignments for a list of volunteers. The bulk act, and an honest report.

	**One savepoint per person, and the report says who did not take.** Some of
	them will fail — already assigned, deployment full, no longer deployable,
	outside the caller's scope — and a bulk action that rolled the whole batch
	back for one bad row would make a coordinator hunt for it by bisection. So
	each insert is wrapped on its own, a failure rolls back only that person's,
	and the caller is handed both lists.

	The failure reason is the thrown message, not a code. These are refusals a
	human has to act on — ask somebody else, raise the headcount, wait for a
	certification — and the sentence the service threw is what says which.

	**Notifications are not sent here.** They are sent by the assignment's own
	`after_insert`, one per person, addressed to that person's record. Sending
	them in a loop here would mean a batch that failed halfway had already told
	people they were going.
	"""
	success, failure = [], []
	savepoint = "before_assignment"

	for volunteer in volunteers:
		try:
			frappe.db.savepoint(savepoint)
			doc = create(deployment_doc, volunteer, status=status, notes=notes)
		except Exception as problem:
			frappe.db.rollback(save_point=savepoint)
			failure.append(
				{
					"volunteer": volunteer,
					"full_name": volunteer_label(volunteer),
					"reason": _clean(problem),
				}
			)
		else:
			success.append(
				{
					"volunteer": volunteer,
					"full_name": volunteer_label(volunteer),
					"assignment": doc.name,
					"status": doc.status,
				}
			)

	return {
		"deployment": deployment_doc.name,
		"requested": len(volunteers),
		"raised": len(success),
		"refused": len(failure),
		"success": success,
		"failure": failure,
	}


def _clean(problem: Exception) -> str:
	"""The sentence a refusal threw, without the markup Frappe wraps it in.

	`frappe.throw` bolds names with HTML, which is right on a desk form and wrong
	in a list a React screen is about to render as text. Stripped here rather
	than in the screen, so every caller of `deploy` gets the same thing.
	"""
	message = getattr(problem, "message", None) or str(problem)

	return frappe.utils.strip_html(str(message)).strip() or _("It could not be raised.")


# --- answering one --------------------------------------------------------


def respond(assignment_doc, accepted: bool, note: str | None = None) -> dict:
	"""Record the volunteer's answer. Idempotent on the same answer.

	**The headcount is checked here, not when the question was asked.** A
	deployment may ask twenty people to fill six places — that is how a
	coordinator gets six — and refusing the seventh *question* would make that
	impossible. What is capped is the seventh yes.

	A caller changing their mind is refused by the grammar rather than here: an
	accepted assignment admits only Withdrawn, so a decline arriving after an
	acceptance is told to speak to whoever asked.
	"""
	target = STATUS_ACCEPTED if accepted else STATUS_DECLINED

	if assignment_doc.status == target:
		return dto(assignment_doc)

	assert_transition(assignment_doc.status, target)

	if accepted:
		assert_room(
			frappe.get_doc(DEPLOYMENT_DOCTYPE, assignment_doc.deployment),
			excluding=assignment_doc.name,
		)

	assignment_doc.status = target
	assignment_doc.responded_on = now_datetime()
	assignment_doc.response_note = note

	# The same words under a second name when the answer is no. `response_note`
	# is whatever somebody wrote either way; `decline_reason` is the field a
	# coordinator filters and reports on, and keeping them apart means "I can't,
	# I'm away that week" is findable as a reason rather than as a note that
	# happens to sit on a declined row.
	if not accepted:
		assignment_doc.decline_reason = note

	# **The one elevated write in this module, and the volunteer is the reason.**
	# A volunteer holds no Geo Assignment and no role on the deployment register,
	# both correctly: it is the society's record of work, not a personal one. An
	# ordinary save here would refuse the only person entitled to answer, and
	# granting every volunteer write permission on every assignment so they could
	# answer their own would be far wider than the thing being permitted.
	#
	# What replaces the permission check is the ownership check in
	# `api/deployment.py::respond_to_assignment`, which establishes that the
	# assignment being answered belongs to the caller's own volunteer record
	# before this is ever reached.
	assignment_doc.save(ignore_permissions=True)

	_tell_askers(assignment_doc, accepted)
	_note_in_feed(
		assignment_doc,
		_("{0} {1} their assignment.").format(
			volunteer_label(assignment_doc.volunteer),
			_("accepted") if accepted else _("declined"),
		),
	)

	return dto(assignment_doc)


def withdraw(assignment_doc, reason: str | None = None) -> dict:
	"""Take an assignment back. The coordinator's own act, at any open stage.

	Not a deletion. The person was asked, or was placed, and that happened; the
	register keeps it so the same coordinator does not ask again next week having
	forgotten. `left_on` is the other half of this: somebody who served part of a
	deployment and went home is recorded as having left, not withdrawn.
	"""
	if assignment_doc.status == STATUS_WITHDRAWN:
		return dto(assignment_doc)

	assert_transition(assignment_doc.status, STATUS_WITHDRAWN)

	assignment_doc.status = STATUS_WITHDRAWN
	assignment_doc.save()

	if reason:
		assignment_doc.add_comment("Comment", _("Withdrawn. {0}").format(reason))

	_note_in_feed(
		assignment_doc,
		_("{0} was withdrawn from this deployment.").format(volunteer_label(assignment_doc.volunteer))
		+ (f" {reason}" if reason else ""),
	)

	# **And tell them.** Being taken off a deployment is the one lifecycle move
	# somebody else makes about a volunteer's own week, and a register that
	# recorded it silently would leave people turning up. The notification points
	# at their own assignment, which is where the reason is.
	_tell_volunteer(assignment_doc, _("You are no longer on this deployment"))

	return dto(assignment_doc)


def _tell_volunteer(assignment_doc, subject: str) -> None:
	"""One in-app notification to the person an assignment is about, if they have a login.

	Quiet where they have none — somebody enrolled at a desk who has never signed
	in — because there is nowhere to send it and failing the withdrawal over it
	would be the wrong trade entirely.

	**`about` is passed whether or not there is a login**, and that is the point
	of it: a young volunteer enrolled from a paper form has no screen to show this
	on and a parent who still has to hear about it. `direct.tell` reads it and
	copies the guardian by email.
	"""
	from vmmsx.notifications.services import direct

	login = direct.login_of(assignment_doc.volunteer)

	direct.tell(
		[login] if login else [],
		subject,
		ASSIGNMENT_DOCTYPE,
		assignment_doc.name,
		about=assignment_doc.volunteer,
	)


# --- getting ready, being there, and what came of it ------------------------
#
# Four facts about one person on one deployment, and they are four fields rather
# than one status for the reason this module has drawn apart from the beginning:
# being briefed, acknowledging a safety brief, turning up, and going home are
# separate things that happen at separate times, and a status that tried to
# carry all four would be a status that could only ever say the last one.
#
# **None of them gates anything.** A volunteer who never acknowledged the safety
# brief is not thereby refused a check-in, because refusing somebody at the gate
# on a field that nobody filled in is how a record-keeping gap becomes an
# operational failure. Whether an unbriefed person deploys is a coordinator's
# decision, taken in front of the record rather than by it.


def mark_briefed(assignment_doc, when=None) -> dict:
	"""Record that this person completed the briefing. Idempotent."""
	return _stamp(assignment_doc, "briefing_completed_on", when)


def acknowledge_safety(assignment_doc, when=None) -> dict:
	"""Record that this person acknowledged the safety brief. Idempotent."""
	return _stamp(assignment_doc, "safety_acknowledged_on", when)


def check_in(assignment_doc, when=None) -> dict:
	"""Record arrival on site. Idempotent: the first check-in is the one that counts."""
	return _stamp(assignment_doc, "checked_in_at", when)


def check_out(assignment_doc, when=None) -> dict:
	"""Record leaving. Refused before a check-in, which would be a record of nothing."""
	if not assignment_doc.checked_in_at:
		frappe.throw(
			_("{0} has not checked in, so there is nothing to check out of.").format(
				frappe.bold(volunteer_label(assignment_doc.volunteer))
			),
			frappe.ValidationError,
			title=_("Not Checked In"),
		)

	return _stamp(assignment_doc, "checked_out_at", when)


def _stamp(assignment_doc, field: str, when=None) -> dict:
	"""Write one timestamp if it is not already written, and save. Idempotent.

	Idempotent because these are records of a moment, and a second call is a
	button pressed twice rather than a second arrival. Overwriting would move the
	moment, which is the one thing a timestamp must not do.
	"""
	if assignment_doc.get(field):
		return dto(assignment_doc)

	assignment_doc.set(field, when or now_datetime())
	assignment_doc.save()

	return dto(assignment_doc)


def record_attendance(
	assignment_doc, outcome: str, hours: float | None = None, notes: str | None = None
) -> dict:
	"""Say what happened on the day: all of it, some of it, or none of it.

	**A statement about the past, made once.** The grammar admits an outcome from
	Assigned and Accepted and admits no move out of one, so correcting a wrong
	entry is an amendment somebody can see rather than a field quietly changing
	back. Idempotent on the same outcome, which is what makes a double-clicked
	button harmless.

	`hours` is the coordinator's verified figure and is deliberately not the
	volunteer's time log. The two are different claims by different people, and a
	register that merged them would have no way to show a disagreement — which is
	the whole reason anybody verifies anything.
	"""
	if outcome not in OUTCOMES:
		frappe.throw(
			_("{0} is not something that happened on the day. Expected one of: {1}.").format(
				frappe.bold(outcome), ", ".join(OUTCOMES)
			),
			frappe.ValidationError,
			title=_("Unknown Outcome"),
		)

	if assignment_doc.status == outcome and hours is None and not notes:
		return dto(assignment_doc)

	if assignment_doc.status != outcome:
		assert_transition(assignment_doc.status, outcome)
		assignment_doc.status = outcome

	if hours is not None:
		assignment_doc.verified_hours = frappe.utils.flt(hours)
		assignment_doc.attendance_verified_by = frappe.session.user
		assignment_doc.attendance_verified_on = now_datetime()

	if notes:
		assignment_doc.participation_notes = notes

	assignment_doc.save()
	_note_in_feed(
		assignment_doc,
		_("{0}: {1}.").format(volunteer_label(assignment_doc.volunteer), _(outcome)),
	)

	return dto(assignment_doc)


# --- somebody else going instead --------------------------------------------


def replace(assignment_doc, volunteer: str, reason: str, authorised_by: str | None = None) -> dict:
	"""Swap somebody out and somebody in, keeping both records.

	**The original is never overwritten**, and that is the whole of the design.
	The person who was asked, what they were asked, and what became of it stay
	exactly where they were; the original moves to `Replaced` and points at the
	assignment that took over, which points back. A register that edited the
	volunteer field instead would erase the fact that anybody had ever been asked
	— and with it any way of telling a replacement from a typo.

	A reason is required, because a replacement is always somebody's decision and
	the next coordinator to open the record is entitled to know whose and why.

	Returns both sides, so a caller does not have to reload to find out who is
	going now.
	"""
	if not (reason or "").strip():
		frappe.throw(
			_("Say why somebody else is going instead. It is the one thing the record cannot infer."),
			frappe.MandatoryError,
			title=_("No Reason Given"),
		)

	assert_transition(assignment_doc.status, STATUS_REPLACED)

	deployment_doc = frappe.get_doc(DEPLOYMENT_DOCTYPE, assignment_doc.deployment)

	# The original steps aside first, so the replacement is not refused as a
	# second open assignment against a deployment the outgoing person still holds
	# a place on. `assert_room` counts the same set.
	assignment_doc.status = STATUS_REPLACED
	assignment_doc.replacement_reason = reason
	assignment_doc.replacement_authorised_by = authorised_by or frappe.session.user
	assignment_doc.save()

	replacement = create(
		deployment_doc,
		volunteer,
		status=STATUS_PENDING,
		role=assignment_doc.role,
		assignment_title=assignment_doc.assignment_title,
		assignment_description=assignment_doc.assignment_description,
		supervisor=assignment_doc.supervisor,
		invitation_expires_on=assignment_doc.invitation_expires_on,
	)
	replacement.db_set("replaces", assignment_doc.name, update_modified=False)
	replacement.db_set("replacement_reason", reason, update_modified=False)
	replacement.db_set(
		"replacement_authorised_by", assignment_doc.replacement_authorised_by, update_modified=False
	)
	replacement.reload()

	assignment_doc.db_set("replaced_by", replacement.name, update_modified=False)
	assignment_doc.reload()

	_note_in_feed(
		assignment_doc,
		_("{0} is going in place of {1}. {2}").format(
			volunteer_label(volunteer), volunteer_label(assignment_doc.volunteer), reason
		),
	)
	_tell_about_replacement(assignment_doc, replacement)

	return {"replaced": dto(assignment_doc), "replacement": dto(replacement)}


def _tell_about_replacement(original, replacement) -> None:
	"""Tell the person standing down. The person stepping in has already been told.

	**Only one notification is sent here, and that is not an omission.** The
	replacement is raised as a question, and the assignment controller's
	`after_insert` notifies whoever a question is put to — so sending a second
	one here would put two identical items in the same person's list for the same
	invitation. What nobody else tells is the person coming off, and that is the
	one this sends.
	"""
	_tell_volunteer(original, _("You are no longer on this deployment"))


# --- questions nobody answered ----------------------------------------------


def expire_overdue(now=None) -> dict:
	"""Expire every invitation whose answer-by date has passed. The scheduled sweep.

	**Expired is not Declined**, and keeping them apart is the point of the whole
	status. A coordinator looking at a roster needs to know the difference between
	"they said no" and "they never saw it": the first is an answer and the second
	is a message that did not land, and only one of them is worth chasing.

	Only invitations carrying a date are touched. A society that never sets one
	has questions that stand until somebody answers them, which is what not
	setting one means.

	Idempotent and safe to run as often as the scheduler likes: a row that has
	already expired is no longer Pending and is not selected again.
	"""
	moment = now or now_datetime()

	# A list rather than a dict: two conditions on one column, and a dict would
	# silently keep only the second of them.
	overdue = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters=[
			[ASSIGNMENT_DOCTYPE, "status", "=", STATUS_PENDING],
			[ASSIGNMENT_DOCTYPE, "invitation_expires_on", "is", "set"],
			[ASSIGNMENT_DOCTYPE, "invitation_expires_on", "<", moment],
		],
		pluck="name",
	)

	expired = []

	for name in overdue:
		doc = frappe.get_doc(ASSIGNMENT_DOCTYPE, name)
		doc.status = STATUS_EXPIRED
		doc.save(ignore_permissions=True)
		_note_in_feed(
			doc,
			_("The invitation to {0} expired unanswered.").format(volunteer_label(doc.volunteer)),
		)
		expired.append(name)

	return {"expired": expired}


def set_role(assignment_doc, role: str) -> dict:
	"""Name this person the deployment's leader, or return them to the ranks.

	The uniqueness rule lives on the controller's validate, which is where it can
	see the whole deployment; this is the door that gets you there.
	"""
	if role not in ("member", "leader"):
		frappe.throw(
			_("{0} is not a deployment role. Expected member or leader.").format(frappe.bold(role)),
			frappe.ValidationError,
			title=_("Unknown Role"),
		)

	if assignment_doc.role == role:
		return dto(assignment_doc)

	assignment_doc.role = role
	assignment_doc.save()

	return dto(assignment_doc)


def leader_of(deployment: str) -> str | None:
	"""The volunteer leading this deployment, or None.

	Only an assignment that is actually on the deployment counts: somebody named
	leader who then declined is not leading anything, and a screen that showed
	them as the leader would send people to the wrong person.
	"""
	return frappe.db.get_value(
		ASSIGNMENT_DOCTYPE,
		{"deployment": deployment, "role": "leader", "status": ("in", ON_DEPLOYMENT)},
		"volunteer",
	)


# --- telling people -------------------------------------------------------


def _tell_askers(assignment_doc, accepted: bool) -> None:
	"""Tell whoever is waiting on this answer what it was.

	The audience is derived rather than stored — see `invitation.askers`, which
	owns that question and reads it back off the requests pointing at the
	deployment plus the deployment's own owner.
	"""
	from vmmsx.deployment.services import invitation
	from vmmsx.notifications.services import direct

	deployment = frappe.get_doc(DEPLOYMENT_DOCTYPE, assignment_doc.deployment)

	direct.tell(
		invitation.askers(deployment),
		_("{0} has {1} their deployment assignment").format(
			volunteer_label(assignment_doc.volunteer),
			_("accepted") if accepted else _("declined"),
		),
		ASSIGNMENT_DOCTYPE,
		assignment_doc.name,
	)


def _note_in_feed(assignment_doc, sentence: str) -> None:
	"""Put a roster change into the deployment's own account of itself.

	Best-effort, and deliberately so: a feed entry is a convenience for whoever
	reads the deployment later, and it must never be the reason a volunteer's
	answer fails to save. The one thing that could throw here is a deployment
	that has been deleted out from under an assignment, which a cascade should
	prevent and a half-restored backup will not.
	"""
	from vmmsx.deployment.services import feed

	try:
		deployment = frappe.get_doc(DEPLOYMENT_DOCTYPE, assignment_doc.deployment)
	except frappe.DoesNotExistError:
		return

	feed.note_roster(deployment, sentence)


def volunteer_label(volunteer: str) -> str:
	"""What to call a volunteer in a message: their name, falling back to the docname.

	Two hops, because a volunteer's name lives on the Red Profile core owns and
	not on the volunteer record itself. Read with `get_cached_value` on both
	hops: this runs once per person in a bulk report.
	"""
	if not volunteer:
		return ""

	profile = frappe.get_cached_value(VOLUNTEER_DOCTYPE, volunteer, "red_profile")

	if not profile:
		return volunteer

	return frappe.get_cached_value("Red Profile", profile, "full_name") or volunteer


def volunteer_photo(volunteer) -> str | None:
	"""The volunteer's photograph, or None — the face half of `volunteer_label`.

	A roster is a list of people a coordinator is scanning for somebody they
	usually already know, and a face is how they find them faster than by
	reading a column of similar names. So it travels with the name rather than
	being fetched separately by whatever screen wants it.

	The same two cached hops for the same reason: a name and a photograph both
	live on the Red Profile core owns, never on the volunteer record, and this
	runs once per person on a roster.

	None is entirely ordinary — most people registered from a paper form have
	never uploaded one — and every surface draws initials for it rather than a
	silhouette or a broken image.
	"""
	if not volunteer:
		return None

	profile = frappe.get_cached_value(VOLUNTEER_DOCTYPE, volunteer, "red_profile")

	if not profile:
		return None

	return frappe.get_cached_value("Red Profile", profile, "profile_photo") or None


# --- reading them ---------------------------------------------------------


def dto(assignment_doc) -> dict:
	"""One assignment, as an explicit dict. Built field by field.

	Never the Document, for the reason every DTO in this app says: that would
	leak every field on the record, including ones nobody reviewed, and turn a
	schema change into an API change.
	"""
	return {
		"name": assignment_doc.name,
		"deployment": assignment_doc.deployment,
		"volunteer": assignment_doc.volunteer,
		"full_name": volunteer_label(assignment_doc.volunteer),
		"photo": volunteer_photo(assignment_doc.volunteer),
		"terms_of_reference": assignment_doc.terms_of_reference,
		"geo_node": assignment_doc.geo_node,
		"status": assignment_doc.status,
		# The three derived answers a screen actually branches on, so no screen
		# has to hold a copy of the status vocabulary to work them out.
		"is_on_deployment": assignment_doc.status in ON_DEPLOYMENT,
		"is_open": assignment_doc.status in OPEN_STATUSES,
		"is_settled": assignment_doc.status in TERMINAL_STATUSES,
		# Whether the day itself has been accounted for, and whether they were
		# there. Two questions rather than one, because a roster nobody has got
		# round to marking up is a different thing from a roster of no-shows.
		"has_outcome": assignment_doc.status in OUTCOMES,
		"attended": assignment_doc.status in ATTENDED,
		"role": assignment_doc.role,
		"is_leader": assignment_doc.role == "leader",
		"assignment_title": assignment_doc.assignment_title,
		"assignment_description": assignment_doc.assignment_description,
		"supervisor": assignment_doc.supervisor,
		"start_date": assignment_doc.start_date,
		"end_date": assignment_doc.end_date,
		"invited_on": assignment_doc.invited_on,
		"invited_by": assignment_doc.invited_by,
		"invitation_expires_on": assignment_doc.invitation_expires_on,
		"responded_on": assignment_doc.responded_on,
		"response_note": assignment_doc.response_note,
		"decline_reason": assignment_doc.decline_reason,
		"briefing_completed_on": assignment_doc.briefing_completed_on,
		"safety_acknowledged_on": assignment_doc.safety_acknowledged_on,
		"checked_in_at": assignment_doc.checked_in_at,
		"checked_out_at": assignment_doc.checked_out_at,
		"verified_hours": frappe.utils.flt(assignment_doc.verified_hours) or None,
		"attendance_verified_by": assignment_doc.attendance_verified_by,
		"attendance_verified_on": assignment_doc.attendance_verified_on,
		# The thread through a swap, both ways, so a reader of either record can
		# reach the other without knowing which end they started at.
		"replaces": assignment_doc.replaces,
		"replaced_by": assignment_doc.replaced_by,
		"replacement_reason": assignment_doc.replacement_reason,
		"replacement_authorised_by": assignment_doc.replacement_authorised_by,
		"joined_on": assignment_doc.joined_on,
		"left_on": assignment_doc.left_on,
		"participation_notes": assignment_doc.participation_notes,
		"notes": assignment_doc.notes,
	}


# The columns a listing reads. Named once so the two listings below cannot
# drift into asking for different things and rendering the same shape.
_ROW_FIELDS = (
	"name",
	"deployment",
	"volunteer",
	"terms_of_reference",
	"geo_node",
	"status",
	"role",
	"assignment_title",
	"assignment_description",
	"supervisor",
	"start_date",
	"end_date",
	"invited_on",
	"invited_by",
	"invitation_expires_on",
	"responded_on",
	"response_note",
	"decline_reason",
	"briefing_completed_on",
	"safety_acknowledged_on",
	"checked_in_at",
	"checked_out_at",
	"verified_hours",
	"attendance_verified_by",
	"attendance_verified_on",
	"replaces",
	"replaced_by",
	"replacement_reason",
	"replacement_authorised_by",
	"joined_on",
	"left_on",
	"participation_notes",
	"notes",
)


def _row(row: dict) -> dict:
	"""One listing row in the same shape `dto` returns, from a `get_all` dict."""
	return {
		**{field: row.get(field) for field in _ROW_FIELDS},
		"full_name": volunteer_label(row.get("volunteer")),
		"photo": volunteer_photo(row.get("volunteer")),
		"is_on_deployment": row.get("status") in ON_DEPLOYMENT,
		"is_open": row.get("status") in OPEN_STATUSES,
		"is_settled": row.get("status") in TERMINAL_STATUSES,
		"has_outcome": row.get("status") in OUTCOMES,
		"attended": row.get("status") in ATTENDED,
		"is_leader": row.get("role") == "leader",
	}


def roster_of(deployment: str, include_settled: bool = True) -> list[dict]:
	"""Every assignment on this deployment, leaders first, then by when they were raised.

	**Read with `get_all`, deliberately.** A roster is a property of the
	deployment, and somebody who may read the deployment may read who is on it —
	filtering these through the caller's own scope would show a coordinator four
	of the six people on a deployment they are looking straight at. The permission
	that matters was checked on the deployment before this was called.
	"""
	if not deployment:
		return []

	filters = {"deployment": deployment}

	if not include_settled:
		filters["status"] = ("in", OPEN_STATUSES)

	rows = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters=filters,
		fields=list(_ROW_FIELDS),
		order_by="creation asc",
	)

	# Leaders first, everybody else in the order they were raised. Sorted here
	# rather than in the query because ordering by a *value* of a column takes a
	# SQL function, and Frappe validates `order_by` against plain field names. A
	# roster is tens of rows, so the sort is free.
	return sorted((_row(row) for row in rows), key=lambda row: 0 if row["is_leader"] else 1)


def assignments_of(volunteer: str, statuses: tuple | None = None) -> list[dict]:
	"""Every assignment this volunteer holds, most recent deployment first.

	The reverse question. Also `get_all`: a volunteer reading their own history
	holds no geo scope at all, and scoping this would hand them an empty list of
	the deployments they personally served on.
	"""
	if not volunteer:
		return []

	filters = {"volunteer": volunteer}

	if statuses:
		filters["status"] = ("in", statuses)

	rows = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters=filters,
		fields=list(_ROW_FIELDS),
		order_by="start_date desc, creation desc",
	)

	return [_row(row) for row in rows]


def counts_for(deployment: str) -> dict:
	"""How this deployment's roster breaks down, one grouped query rather than five.

	Used by every listing that shows a deployment, so it must not be five counts
	per row.
	"""
	table = frappe.qb.DocType(ASSIGNMENT_DOCTYPE)

	rows = (
		frappe.qb.from_(table)
		.select(table.status, Count(table.name).as_("total"))
		.where(table.deployment == deployment)
		.groupby(table.status)
		.run(as_dict=True)
	)

	tally = {status: 0 for status in STATUSES}

	for row in rows:
		if row["status"] in tally:
			tally[row["status"]] = row["total"]

	return {
		**tally,
		"on_deployment": sum(tally[status] for status in ON_DEPLOYMENT),
		"open": sum(tally[status] for status in OPEN_STATUSES),
		# How much of the day has been accounted for, and how much of it was
		# attended. A coordinator closing a deployment out reads the first; a
		# report on turnout reads the second.
		"outcomes": sum(tally[status] for status in OUTCOMES),
		"attended": sum(tally[status] for status in ATTENDED),
		"total": sum(tally.values()),
	}


def counts_for_many(deployments: list[str]) -> dict[str, dict]:
	"""`counts_for`, for a whole listing, in one query rather than one per row.

	A listing of a hundred deployments asking `counts_for` a hundred times is the
	N+1 that makes a register feel broken at the size a national society actually
	runs at. One grouped query over the lot, bucketed here.

	Every name asked about comes back, including the ones with no assignments at
	all, so a caller never has to decide what a missing key means.
	"""
	empty = {
		**{status: 0 for status in STATUSES},
		"on_deployment": 0,
		"open": 0,
		"outcomes": 0,
		"attended": 0,
		"total": 0,
	}

	if not deployments:
		return {}

	tallies: dict[str, dict] = {name: dict(empty) for name in deployments}

	table = frappe.qb.DocType(ASSIGNMENT_DOCTYPE)

	rows = (
		frappe.qb.from_(table)
		.select(table.deployment, table.status, Count(table.name).as_("total"))
		.where(table.deployment.isin(deployments))
		.groupby(table.deployment, table.status)
		.run(as_dict=True)
	)

	for row in rows:
		tally = tallies.get(row["deployment"])

		if tally is None or row["status"] not in tally:
			continue

		tally[row["status"]] = row["total"]

	for tally in tallies.values():
		tally["on_deployment"] = sum(tally[status] for status in ON_DEPLOYMENT)
		tally["open"] = sum(tally[status] for status in OPEN_STATUSES)
		tally["outcomes"] = sum(tally[status] for status in OUTCOMES)
		tally["attended"] = sum(tally[status] for status in ATTENDED)
		tally["total"] = sum(tally[status] for status in STATUSES)

	return tallies


def assert_dates(assignment_doc) -> None:
	"""An assignment cannot end before it starts. Called from the controller."""
	if not (assignment_doc.start_date and assignment_doc.end_date):
		return

	if getdate(assignment_doc.end_date) >= getdate(assignment_doc.start_date):
		return

	frappe.throw(
		_("This assignment is set to end on {0}, before it begins on {1}.").format(
			frappe.bold(frappe.format(assignment_doc.end_date, {"fieldtype": "Date"})),
			frappe.bold(frappe.format(assignment_doc.start_date, {"fieldtype": "Date"})),
		),
		frappe.ValidationError,
		title=_("Assignment Ends Before It Begins"),
	)


def assert_terms_offered(assignment_doc) -> None:
	"""The terms this assignment is raised under must still take new work.

	Checked on the assignment as well as on the deployment, because an assignment
	can be raised months after the deployment was set up and a society may have
	retired the terms in between. Somebody must not be asked to agree to a
	specification the society has withdrawn.
	"""
	if assignment_doc.is_new():
		terms_service.assert_offered(assignment_doc.terms_of_reference)


def readiness_for_many(deployments: list[str]) -> dict[str, dict]:
	"""How ready each deployment's roster is, in one query rather than one per row.

	The four control fields an operations screen reads off a roster — who is
	leading, who has been briefed, who acknowledged the safety brief, and who has
	checked in — counted per deployment. `counts_for_many` answers *who is
	going*; this answers *how ready they are*, and the two are kept apart because
	a listing that only needs headcounts should not pay for the second.

	**Only assignments that are actually on the deployment are counted.** A
	person who was briefed and then declined is not somebody who will be there,
	and counting them would report a roster as readier than it is.

	Every name asked about comes back, so a caller never has to decide what a
	missing key means.
	"""
	empty = {"briefed": 0, "safety": 0, "checked_in": 0, "leaders": 0}

	if not deployments:
		return {}

	found: dict[str, dict] = {name: dict(empty) for name in deployments}

	table = frappe.qb.DocType(ASSIGNMENT_DOCTYPE)

	rows = (
		frappe.qb.from_(table)
		.select(
			table.deployment,
			table.briefing_completed_on,
			table.safety_acknowledged_on,
			table.checked_in_at,
			table.role,
		)
		.where(table.deployment.isin(deployments) & table.status.isin(ON_DEPLOYMENT))
		.run(as_dict=True)
	)

	for row in rows:
		tally = found.get(row["deployment"])

		if tally is None:
			continue

		if row.get("briefing_completed_on"):
			tally["briefed"] += 1

		if row.get("safety_acknowledged_on"):
			tally["safety"] += 1

		if row.get("checked_in_at"):
			tally["checked_in"] += 1

		if row.get("role") == "leader":
			tally["leaders"] += 1

	return found
