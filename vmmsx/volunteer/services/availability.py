# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Is this volunteer free between these two dates?

The question `matching.py` has carried in `PENDING_CRITERIA` since it was
written — "availability is a structured selector on the volunteer register, but
nothing here asks it a question yet" — and this is the module that asks it.

What it reads, and what it deliberately does not
------------------------------------------------

**`VMMS Availability Schedule`**, one per volunteer: a weekly pattern of
day-and-window rows plus the period over which the pattern holds. Not
`VMMS Volunteer.availability`, which is the Table MultiSelect of named slots a
person picks at intake. Those are two different facts and this app keeps both:
the multi-select is a self-description a coordinator can search on ("who calls
themselves a weekend volunteer"), and the schedule is a claim about days that a
deployment's own dates can be tested against. `capabilities.search` reads the
first; this reads the second.

**Silence is not a no.** A volunteer with no schedule is `unknown`, never
`unavailable`. Most registers will have almost nobody filled in for a long time
after this ships, and a matcher that quietly dropped everybody who had not yet
answered a question nobody had asked them would look exactly like a broken
search. The three-way answer is the whole point of the shape below, and callers
are expected to treat `unknown` as "show them, say we do not know".

**A pattern, expanded on read.** The schedule holds "Saturdays, afternoons", not
one row per Saturday. `weekdays_between` walks the span and asks which weekdays
it touches, which is a handful of integers rather than a table scan. A deployment
running longer than a week touches all seven and the answer is decided by the
pattern alone.

**Whole days, not hours.** A deployment has a start date and an end date, not a
start time, so the hours on a slot are carried into the answer for a coordinator
to read and are not used to accept or refuse anybody. A society whose slots have
no hours at all loses nothing here. When a deployment learns to say "afternoons
of the 3rd and 4th", the hours are already on the record waiting for it.

**Coverage is per weekday, and every weekday must be covered.** A deployment
from Friday to Monday needs somebody free on Friday, Saturday, Sunday *and*
Monday. Anything weaker — "free on at least one of these days" — would put
people on deployments they had said they could not do most of, which is worse
than not asking at all.
"""

import frappe
from frappe.utils import add_days, date_diff, getdate

SCHEDULE_DOCTYPE = "VMMS Availability Schedule"
SLOT_DOCTYPE = "VMMS Availability Slot"

# Monday first, matching `datetime.weekday()`, so a day's name is an index into
# this tuple rather than a lookup somebody has to keep in step with the Select
# on `VMMS Availability Day`. The two lists are the same seven strings in the
# same order, and `assert_days_match` below is what stops them drifting apart.
DAYS = (
	"Monday",
	"Tuesday",
	"Wednesday",
	"Thursday",
	"Friday",
	"Saturday",
	"Sunday",
)

# The three answers. `unknown` is a first-class one, not an error state: a
# register where nobody has filled a schedule in yet must not read as a register
# where nobody is free.
AVAILABLE = "available"
UNAVAILABLE = "unavailable"
UNKNOWN = "unknown"

# Past this many days a span covers every weekday, so there is nothing to be
# gained by walking it. Seven, and not a guess: any seven consecutive dates
# touch all seven weekdays exactly once.
FULL_WEEK = 7


def schedule_of(volunteer: str):
	"""This volunteer's schedule, or None if they have not written one.

	Read through the document cache: a candidate search asks this once per
	volunteer on the page, and a schedule changes a few times a year.
	"""
	if not volunteer or not frappe.db.exists(SCHEDULE_DOCTYPE, volunteer):
		return None

	return frappe.get_cached_doc(SCHEDULE_DOCTYPE, volunteer)


def weekdays_between(start, end) -> set[int]:
	"""Which weekdays a span of dates touches, as `datetime.weekday()` integers.

	A span of a week or more touches all seven, and is answered without walking.
	A shorter one is walked, which is at most six iterations.

	An end before the start is treated as the single day the start names, rather
	than as an empty set: an empty set would make `assess` answer `available` for
	nonsense input, and the most conservative reading of a malformed span is the
	one day we can be sure about.
	"""
	first, last = getdate(start), getdate(end)

	if last < first:
		last = first

	if date_diff(last, first) >= FULL_WEEK - 1:
		return set(range(FULL_WEEK))

	days, cursor = set(), first

	while cursor <= last:
		days.add(cursor.weekday())
		cursor = getdate(add_days(cursor, 1))

	return days


def covered_weekdays(schedule) -> dict[int, list[str]]:
	"""Which weekdays this schedule covers, and with which windows.

	Keyed by `datetime.weekday()` integer so it can be compared directly against
	`weekdays_between`. The slot keys come along because a coordinator reading
	"free Saturday" wants to know whether that means the morning.

	A row naming a day outside the seven is skipped rather than raised on: the
	Select refuses one, and a row that got there another way should not take down
	a candidate search.
	"""
	covered: dict[int, list[str]] = {}

	for row in schedule.available_days or []:
		if row.day not in DAYS:
			continue

		covered.setdefault(DAYS.index(row.day), []).append(row.availability_slot)

	return covered


def holds_over(schedule, start, end) -> bool:
	"""Does this schedule describe the span being asked about?

	A schedule with no period holds always, which is what somebody filling in a
	weekly grid means. Where a period is set, it has to cover the whole span:
	a pattern that expires halfway through a deployment does not describe that
	deployment, and treating a partial overlap as a yes would put somebody on the
	second week of a fortnight they had said they were only free for the first of.
	"""
	first, last = getdate(start), getdate(end)

	if schedule.valid_from and getdate(schedule.valid_from) > first:
		return False

	if schedule.valid_to and getdate(schedule.valid_to) < last:
		return False

	return True


def assess(volunteer: str, start, end) -> dict:
	"""Whether this volunteer is free across a span, as an explicit dict.

	Three-way, and every branch says why in words a screen can put in front of a
	coordinator without composing a sentence of its own:

	    unknown      no schedule, or one that does not cover these dates
	    unavailable  a schedule that covers them and does not offer some weekday
	    available    a schedule that covers them and offers every weekday

	`missing_days` names the weekdays that were not offered, so a coordinator
	sees "not free on Sunday" rather than a bare no.
	"""
	if not (volunteer and start and end):
		return _answer(UNKNOWN, "This deployment has no dates to ask about.")

	schedule = schedule_of(volunteer)

	if not schedule:
		return _answer(
			UNKNOWN,
			"This volunteer has not filled in when they are available, so nothing is known either way.",
		)

	if not holds_over(schedule, start, end):
		return _answer(
			UNKNOWN,
			"This volunteer's availability does not describe these dates, so nothing is known about them.",
		)

	needed = weekdays_between(start, end)
	covered = covered_weekdays(schedule)
	missing = sorted(needed - set(covered))

	if missing:
		return _answer(
			UNAVAILABLE,
			"This volunteer has not said they are free on {0}.".format(
				_and_list([DAYS[day] for day in missing])
			),
			missing_days=[DAYS[day] for day in missing],
			available_on_holidays=bool(schedule.available_on_holidays),
		)

	return _answer(
		AVAILABLE,
		"This volunteer is free on every day this deployment runs.",
		slots=sorted({slot for day in needed for slot in covered.get(day, [])}),
		available_on_holidays=bool(schedule.available_on_holidays),
	)


def assess_many(volunteers: list[str], start, end) -> dict[str, dict]:
	"""`assess`, for a whole page of volunteers, in two queries rather than N.

	The candidate search asks this once per volunteer on a page of fifty, and
	`assess` on its own would be a document load each. Two `get_all` calls — the
	schedules, then their day rows — and the same pure logic applied to what came
	back.

	Every name asked about comes back, so a caller never has to decide what a
	missing key means. Somebody with no schedule gets the same `unknown` answer
	`assess` gives them.
	"""
	if not volunteers:
		return {}

	if not (start and end):
		return {name: _answer(UNKNOWN, "This deployment has no dates to ask about.") for name in volunteers}

	schedules = {
		row["name"]: row
		for row in frappe.get_all(
			SCHEDULE_DOCTYPE,
			filters={"volunteer": ("in", volunteers)},
			fields=["name", "volunteer", "available_on_holidays", "valid_from", "valid_to"],
			# Reading whether people are free, for a coordinator who has already
			# been shown these volunteers by a scoped search. A schedule carries no
			# geo anchor of its own, so there is nothing here for core to scope and
			# an ordinary read would refuse the lot.
			ignore_permissions=True,
		)
	}

	rows: dict[str, list] = {}

	if schedules:
		for row in frappe.get_all(
			"VMMS Availability Day",
			filters={"parenttype": SCHEDULE_DOCTYPE, "parent": ("in", list(schedules))},
			fields=["parent", "day", "availability_slot"],
			ignore_permissions=True,
		):
			rows.setdefault(row["parent"], []).append(row)

	needed = weekdays_between(start, end)
	answers = {}

	for volunteer in volunteers:
		schedule = schedules.get(volunteer)

		if not schedule:
			answers[volunteer] = _answer(
				UNKNOWN,
				"This volunteer has not filled in when they are available, so nothing is known either way.",
			)
			continue

		held = frappe._dict(schedule)
		held.available_days = [frappe._dict(row) for row in rows.get(volunteer, [])]

		if not holds_over(held, start, end):
			answers[volunteer] = _answer(
				UNKNOWN,
				"This volunteer's availability does not describe these dates, so nothing is"
				" known about them.",
			)
			continue

		covered = covered_weekdays(held)
		missing = sorted(needed - set(covered))

		if missing:
			answers[volunteer] = _answer(
				UNAVAILABLE,
				"This volunteer has not said they are free on {0}.".format(
					_and_list([DAYS[day] for day in missing])
				),
				missing_days=[DAYS[day] for day in missing],
				available_on_holidays=bool(held.available_on_holidays),
			)
			continue

		answers[volunteer] = _answer(
			AVAILABLE,
			"This volunteer is free on every day this deployment runs.",
			slots=sorted({slot for day in needed for slot in covered.get(day, [])}),
			available_on_holidays=bool(held.available_on_holidays),
		)

	return answers


def _answer(state: str, why: str, **extra) -> dict:
	"""One assessment, in the shape every caller gets.

	The booleans are derived here rather than left to each caller to work out
	from the state, so that no screen and no service holds its own copy of what
	the three words mean. `is_available` is deliberately **not** true for
	`unknown`: a caller wanting "do not rule this person out" asks
	`not is_unavailable`, and having to choose between the two is the point.
	"""
	return {
		"state": state,
		"is_available": state == AVAILABLE,
		"is_unavailable": state == UNAVAILABLE,
		"is_known": state != UNKNOWN,
		"why": why,
		"missing_days": extra.get("missing_days", []),
		"slots": extra.get("slots", []),
		"available_on_holidays": extra.get("available_on_holidays"),
	}


def _and_list(words: list[str]) -> str:
	"""`["Saturday", "Sunday"]` as "Saturday and Sunday".

	Small enough to write and worth writing: the alternative is a comma-joined
	list that reads like a machine wrote it, in a sentence a coordinator is meant
	to act on.
	"""
	from frappe import _

	if not words:
		return ""

	if len(words) == 1:
		return _(words[0])

	return _("{0} and {1}").format(", ".join(_(word) for word in words[:-1]), _(words[-1]))


# --- writing one ----------------------------------------------------------


def set_schedule(
	volunteer: str,
	days: list | None = None,
	available_on_holidays: bool = False,
	valid_from: str | None = None,
	valid_to: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Write a volunteer's weekly pattern, replacing whatever was there.

	**Replaces rather than merges**, because the screen this serves is a grid of
	tick boxes: what arrives is the whole answer, and a row the volunteer
	un-ticked has to disappear. Merging would make un-ticking impossible, which
	is the one thing a grid must be able to do.

	One schedule per volunteer, so this creates or updates the same record rather
	than accumulating one per edit. The docname *is* the volunteer.
	"""
	rows = [
		{"day": row.get("day"), "availability_slot": row.get("availability_slot")}
		for row in (days or [])
		if isinstance(row, dict) and row.get("day") in DAYS and row.get("availability_slot")
	]

	if frappe.db.exists(SCHEDULE_DOCTYPE, volunteer):
		doc = frappe.get_doc(SCHEDULE_DOCTYPE, volunteer)
	else:
		doc = frappe.new_doc(SCHEDULE_DOCTYPE)
		doc.volunteer = volunteer

	doc.available_on_holidays = 1 if available_on_holidays else 0
	doc.valid_from = valid_from or None
	doc.valid_to = valid_to or None
	doc.notes = notes
	doc.set("available_days", rows)

	# **Elevated, and the volunteer is the reason.** This is somebody writing
	# their own availability from the portal. A volunteer holds no Geo Assignment
	# and no role on the register, so an ordinary save refuses the only person
	# whose answer this is. The caller — `api/volunteer.py::set_my_availability`
	# — resolves the volunteer from the session and takes no argument naming
	# anybody else, which is what replaces the permission check.
	doc.save(ignore_permissions=True)

	return dto(volunteer)


def dto(volunteer: str) -> dict:
	"""One volunteer's schedule, as an explicit dict. Built field by field.

	An empty pattern rather than None for somebody who has not written one, so
	the screen that renders a grid of tick boxes has the same shape to render
	either way.
	"""
	schedule = schedule_of(volunteer)

	if not schedule:
		return {
			"volunteer": volunteer,
			"exists": False,
			"available_on_holidays": False,
			"valid_from": None,
			"valid_to": None,
			"notes": None,
			"days": [],
		}

	return {
		"volunteer": volunteer,
		"exists": True,
		"available_on_holidays": bool(schedule.available_on_holidays),
		"valid_from": schedule.valid_from,
		"valid_to": schedule.valid_to,
		"notes": schedule.notes,
		"days": [
			{"day": row.day, "availability_slot": row.availability_slot}
			for row in (schedule.available_days or [])
		],
	}


def slots() -> list[dict]:
	"""The society's own availability windows, for the grid's columns.

	**Only the ones that carry hours**, and that filter is the whole seam between
	the two things this app calls availability.

	`VMMS Volunteer.availability` is a self-description picked at intake, and the
	windows a society seeds for it are often day-scoped — "Weekday Mornings",
	"Weekend Evenings". Those are fine as a tag a coordinator searches on, and
	they are nonsense as a column in a grid whose rows are already the seven days:
	"Weekday Mornings" against Sunday means nothing anybody could act on.

	A window with an opening and a closing time is a different kind of thing: it
	is a span of the day, day-agnostic by construction, and it is exactly what a
	row of the weekly pattern needs. So the hours are what promote a slot from a
	label to a schedulable window, and a society that has not given a slot hours
	keeps every behaviour it had while staying out of this grid.

	Ordered by when the window opens rather than by name, so the columns read
	across the day the way a person expects.
	"""
	rows = frappe.get_all(
		SLOT_DOCTYPE,
		filters={"is_active": 1, "start_time": ("is", "set"), "end_time": ("is", "set")},
		fields=["name", "slot_name", "start_time", "end_time", "description"],
	)

	# Sorted on the value, never on `str()` of it. A Time comes back as a
	# `timedelta`, whose string form has no leading zero — so "8:00:00" sorts
	# after "12:00:00" and the morning column lands at the end of the day.
	# Comparing the timedeltas themselves is both correct and obvious; the name is
	# the tie-break so two windows opening at the same hour keep a stable order.
	return sorted(rows, key=lambda row: (row["start_time"], row["slot_name"]))


def assert_days_match() -> None:
	"""The seven days here are the seven on `VMMS Availability Day`, in order.

	A guard for the tests rather than for runtime. `DAYS` is indexed by
	`datetime.weekday()` and the doctype's Select is what a volunteer picks from;
	if somebody reorders one and not the other, every schedule silently starts
	meaning a different day of the week, and nothing else in this app would
	notice.
	"""
	options = frappe.get_meta("VMMS Availability Day").get_field("day").options or ""
	declared = tuple(line.strip() for line in options.split("\n") if line.strip())

	if declared == DAYS:
		return

	frappe.throw(
		"VMMS Availability Day's days are {0}; availability.DAYS is {1}. They are indexed"
		" against each other by position, so they have to be the same list in the same"
		" order.".format(declared, DAYS)
	)
