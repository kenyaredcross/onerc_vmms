# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The People overview's figures, as one permission-scoped aggregate.

The question this answers
-------------------------

A coordinator opening People Management is asking three things at once: what is
waiting on me, what is stuck coming in, and how many people are actually on the
books here. Until now the screen answered the third by asking each register for
one row and reading its `total`, which is honest but costs two round trips to
learn two numbers — and it could not answer "how many *people*", because a
person who is both a volunteer and a member is two rows in two registers and one
human being.

So this module exists to compute the overview's figures **once, on the server,
inside the caller's own scope**, and hand back a flat DTO. It derives nothing a
screen could not already read; it just reads it in one place, correctly.

Scope is the floor, not a filter
--------------------------------

Every read below is `frappe.get_list`, which runs core's permission query
condition for the doctype it names. `frappe.get_all` is used nowhere in this
module. Nothing here takes an argument from the caller, so there is no parameter
that could widen a result: the answer is a fact about who is asking.

A coordinator with no geo assignment gets zeroes. That is the correct render,
not a failure — the same rule the registers themselves follow.

Where a figure is not available, it is `None`
---------------------------------------------

Two of these figures need the set of distinct Red Profiles behind each register,
which is a column read rather than a count. That is fine at branch and county
size and wrong at national size, so it is bounded: past `_DISTINCT_CEILING` rows
the unique-people and both-registers figures come back as `None` and the screen
omits the block rather than showing a number computed from a truncated read.

**A capped read is never labelled a total.** That rule is the whole reason this
module is not a page of `len(rows)` calls.
"""

import frappe

from vmmsx.approvals import states
from vmmsx.approvals.services import config, contract, sla

# How many rows the distinct-profile reads will take before they give up. Above
# this the two cross-register figures are `None`; see the module docstring.
_DISTINCT_CEILING = 20_000

# The two registers this overview counts, and the two intakes that feed them.
#
# A row, not a branch: a third register — the day a society adds one — is a row
# here and a tile on the screen, and no code in between learns what it is. The
# `kind` is the word the frontend already routes on.
_REGISTERS = (
	{
		"kind": "volunteers",
		"doctype": "VMMS Volunteer",
		# What the register's own status field is called, and the one value of
		# it this overview counts. Named per row rather than assumed, because a
		# volunteer's standing and a membership's standing are two different
		# closed Selects owned by two different modules; nothing here compares
		# them or maps one onto the other.
		"status_field": "status",
		"active_status": "Active",
		"profile_field": "red_profile",
		"intake_doctype": "VMMS Volunteer Application",
	},
	{
		"kind": "members",
		"doctype": "VMMS Membership",
		"status_field": "membership_status",
		"active_status": "Active",
		# A membership names a member, not a profile — the hop to Red Profile is
		# one batched read further on. See `_people`.
		"profile_field": "member",
		"intake_doctype": "VMMS Membership",
	},
)


@frappe.whitelist()
def summary() -> dict:
	"""Everything the People overview shows, in one scoped read.

	Four blocks:

	    queue       what is routed to **this user** right now, per intake, with
	                how many of those have passed their stage's SLA
	    intake      the health of each door into the society, inside the
	                caller's scope: under review, sent back, overdue
	    registers   how many people are actually active in each register
	    people      the same two registers counted as *people* rather than as
	                records, where that is affordable — see the module docstring

	Nothing here is a client-supplied filter, so nothing here can be widened.
	"""
	queue = _queue_by_intake()

	return {
		"queue": queue,
		"intake": [_intake(register, queue) for register in _REGISTERS],
		"registers": _registers(),
		"people": _people(),
	}


# --- what is waiting on this user ------------------------------------------


def _queue_by_intake() -> dict:
	"""`my_queue`, split by the doctype each row came from.

	The same answer `api/approvals.py::my_queue` gives, grouped — so the
	overview's "waiting for your decision" and the queue screen's own list can
	never disagree about how many there are. Re-checked against routing per row
	by the engine, exactly as the queue screen's read is.
	"""
	from vmmsx.api import approvals

	found: dict[str, dict] = {}

	for row in approvals.my_queue():
		bucket = found.setdefault(row["doctype"], {"waiting": 0, "overdue": 0})
		bucket["waiting"] += 1

		if (row.get("stage") or {}).get("is_breached"):
			bucket["overdue"] += 1

	return found


# --- the health of one door -------------------------------------------------


def _intake(register: dict, queue: dict) -> dict:
	"""One route into the society: what is in it, and what is stuck.

	`in_review` and `changes_requested` are counted over the caller's whole
	scope rather than over their own assignments, because that is the question
	the block asks — a branch with eleven applications nobody has picked up is
	the thing worth seeing, and an approver's personal queue cannot show it.
	`waiting` and `overdue` beside them *are* personal, and are the same figures
	`my_queue` produced above.

	A doctype no workflow governs yet is answered with `governed: False` and no
	numbers, rather than with zeroes that would read as "nothing to do".
	"""
	doctype = register["intake_doctype"]
	readable = frappe.has_permission(doctype, "read")

	# **Two different silences, told apart.** A door with no approval workflow
	# behind it and a door this caller may not read both come back with `None`
	# figures — a zero would say "nothing to do", which is false in either case —
	# but they are *different* facts and a screen has to say the right one.
	# Folding them together made the overview tell a membership clerk that
	# volunteer applications were "not configured", which they were not.
	if not readable or not config.is_approvable(doctype):
		return {
			"kind": register["kind"],
			"doctype": doctype,
			"readable": readable,
			"governed": readable and config.is_approvable(doctype),
			"in_review": None,
			"changes_requested": None,
			"waiting": 0,
			"overdue": 0,
			"breached": None,
		}

	mine = queue.get(doctype) or {}

	return {
		"kind": register["kind"],
		"doctype": doctype,
		"readable": True,
		"governed": True,
		"in_review": _count(doctype, {"approval_state": states.IN_REVIEW}),
		# Sent back to the applicant: state is exactly Draft *and* somebody
		# recorded a "More info requested" decision on it. A draft nobody ever
		# submitted is not a correction anybody is waiting on.
		"changes_requested": _returned_count(doctype),
		"waiting": mine.get("waiting", 0),
		"overdue": mine.get("overdue", 0),
		# Everything in the caller's scope that is past its stage's SLA, not
		# only what is routed to them. Derived by the SLA service per document,
		# which is the same function the sweep and the queue badge use.
		"breached": _breached_count(doctype),
	}


def _returned_count(doctype: str) -> int:
	"""How many of this doctype's drafts were sent back for corrections."""
	drafts = frappe.get_list(
		doctype,
		filters={"approval_state": states.DRAFT},
		limit_page_length=_DISTINCT_CEILING,
		pluck="name",
	)

	if not drafts:
		return 0

	return len(
		set(
			frappe.get_all(
				contract.DECISION_DOCTYPE,
				filters={
					"parenttype": doctype,
					"parent": ("in", drafts),
					"decision": states.DECISION_MORE_INFO,
				},
				pluck="parent",
			)
		)
	)


def _breached_count(doctype: str) -> int:
	"""Applications in review whose current stage is past its configured SLA.

	Derived per document through `sla.is_breached`, which is where the rule
	lives — a screen comparing dates itself would be a second answer to "is this
	late", and the two would drift the first time a society changed its working
	calendar. Bounded by the same ceiling as everything else here.
	"""
	workflow = config.for_doctype(doctype)
	names = frappe.get_list(
		doctype,
		filters={"approval_state": states.IN_REVIEW},
		limit_page_length=_DISTINCT_CEILING,
		pluck="name",
	)

	late = 0

	for name in names:
		doc = frappe.get_doc(doctype, name)
		stage = config.stage_by_name(workflow, contract.stage(doc))

		if stage and sla.is_breached(doc, stage):
			late += 1

	return late


# --- how many people are actually on the books ------------------------------


def _registers() -> list[dict]:
	"""Active records in each register, counted through the scoped listing."""
	return [
		{
			"kind": register["kind"],
			"doctype": register["doctype"],
			"readable": frappe.has_permission(register["doctype"], "read"),
			# `None` for a register this caller may not read at all, and a screen
			# draws a dash for it. Asked before the read rather than caught after
			# it: `get_list` raises on a doctype with no DocPerm, and a membership
			# clerk with no volunteer permissions must get their own figures
			# rather than an error page. The same rule `api/person.py::registers`
			# follows, and for the same reason — not being allowed to know is
			# indistinguishable, on a screen, from there being nothing to know.
			"active": _count(register["doctype"], _active_filter(register))
			if frappe.has_permission(register["doctype"], "read")
			else None,
		}
		for register in _REGISTERS
	]


def _active_filter(register: dict) -> dict:
	"""The one filter that means "currently on the books" for this register."""
	return {register["status_field"]: register["active_status"]}


def _people() -> dict:
	"""The two registers counted as people rather than as records.

	A person holding memberships at two branches is two rows in one register and
	one human being; somebody who is both a volunteer and a member is two rows in
	two registers and still one. Both registers hang off the same Red Profile, so
	the honest count is the size of the union of their profile sets.

	`None` above the ceiling, and the screen omits the block. See the module
	docstring: a figure computed from a truncated read is worse than no figure.
	"""
	by_kind = {register["kind"]: register for register in _REGISTERS}
	volunteer_register = by_kind["volunteers"]
	member_register = by_kind["members"]

	volunteers = _profiles(
		volunteer_register["doctype"],
		_active_filter(volunteer_register),
		field=volunteer_register["profile_field"],
	)
	members = _profiles(
		member_register["doctype"],
		_active_filter(member_register),
		field=member_register["profile_field"],
	)

	# A caller who may read only one of the two registers cannot be told how many
	# distinct people are in both, and `capped` is the honest word for that too:
	# the screen omits the block either way. Distinguishing "too many to count"
	# from "not yours to count" would tell somebody the other register exists and
	# is populated, which is precisely what `api/person.py` refuses to disclose.

	if volunteers is None or members is None:
		return {"unique": None, "both": None, "volunteers": None, "members": None, "capped": True}

	# A membership names a member, and a member names a profile. The hop is one
	# batched read rather than one per row.
	member_profiles = _profiles_of_members(members)

	return {
		"unique": len(volunteers | member_profiles),
		"both": len(volunteers & member_profiles),
		"volunteers": len(volunteers),
		"members": len(member_profiles),
		"capped": False,
	}


def _profiles(doctype: str, filters: dict, field: str = "red_profile") -> set | None:
	"""Distinct linking values off a scoped listing, or None where there is no answer.

	`None` for two different reasons that a caller must not be able to tell
	apart: the read went past its ceiling, or this register is not one the caller
	may read at all. See `_people`.
	"""
	if not frappe.has_permission(doctype, "read"):
		return None

	rows = frappe.get_list(
		doctype,
		filters=filters,
		# One past the ceiling, so hitting it is distinguishable from filling it.
		limit_page_length=_DISTINCT_CEILING + 1,
		pluck=field,
	)

	if len(rows) > _DISTINCT_CEILING:
		return None

	return {value for value in rows if value}


def _profiles_of_members(members: set) -> set:
	"""Every Red Profile behind a set of member docnames, in one read."""
	if not members:
		return set()

	return {
		value
		for value in frappe.get_all(
			"VMMS Member",
			filters={"name": ("in", sorted(members))},
			pluck="red_profile",
		)
		if value
	}


def _count(doctype: str, filters: dict) -> int:
	"""How many rows match, through the scoped listing rather than around it.

	`frappe.get_list` with an aggregate field builds the same query the register
	pages run — permission query condition included — so this is the register's
	own size and not a number reached by a different route. `frappe.db.count`
	would skip that condition and is not used.

	The aggregate goes in as `{"COUNT": "name"}` rather than as the string
	`"count(name)"`: Frappe rejects SQL functions written as strings in a SELECT,
	and the dict form is what its query builder accepts.
	"""
	rows = frappe.get_list(doctype, filters=filters, fields=[{"COUNT": "name"}], as_list=True)

	return frappe.utils.cint(rows[0][0]) if rows else 0
