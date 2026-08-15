# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Where stipend approval *will* route, recorded now and routed by nothing.

The stipend chain is **supervisor to head of department**, and the department is
the volunteer's, not the report's. That is a different question from every
routing question this app can currently answer: the approval engine resolves an
approver by walking *upward through geo* to find who holds a role at or above a
node, and a volunteer's head of department is not up the geo tree from them. A
county coordinator is a geo parent; a head of programmes is not. Routing stipend
paperwork through the geo engine would therefore resolve confidently to the
wrong person, which is worse than resolving to nobody, because nobody notices.

So departmental resolution is deliberately absent — see
`stipend/services/approval.py`, which refuses the decision out loud — and this
module does the one thing that is honest to do in the meantime: **it records the
target**, so that whoever builds the delegation subsystem inherits a real answer
to "route to whom" rather than having to reconstruct it from the paperwork.

What is captured, and what it costs
-----------------------------------

One value per volunteer on a report: the department their `Employee` record
carries, read through the volunteer module's HR seam and its `_INBOUND`
allow-list. Nothing else about employment crosses.

**It degrades at every step, and a blank is ordinary.** No HR app on the site, no
Employee linked to the volunteer, or an Employee with no department all produce
None. That is not an error and does not block anything: the paperwork is about
work that was done, and a society that does not run its volunteers through HR
still files it. `describe()` says so explicitly rather than returning a bare
empty list that reads as "no departments exist".

**It is a snapshot, and stored as text.** A `Data` field rather than a Link,
because a Link would make these doctypes unsyncable on a site without the app
that owns `Department`, and because a report describes a period that has already
happened: somebody who moved department in April did not move department in the
March report. When departmental routing is built it will resolve the current head
of department from the *current* record; this field is the record of what was
true when the paperwork was filed, and the two are different facts on purpose.

**Nothing branches on a department name.** No department appears as a literal
anywhere in this app, `routing_departments` is written and displayed and never
compared, and no code path changes because a volunteer is in one department
rather than another.
"""

import frappe

from vmmsx.volunteer.services import hr

VOLUNTEER_DOCTYPE = "VMMS Volunteer"

# The one field this module reads back through the seam. Named here so the
# allow-list in `hr._INBOUND` and the caller agree on the spelling, and so the
# grep for it lands on this docstring.
DEPARTMENT_FIELD = "department"

# What a caller is told when nothing could be captured, in place of an empty list
# that would read as a finding. Prose, never a value anything branches on.
NO_TARGET = (
	"No volunteer on this report has a department this site can see, so the eventual departmental"
	" approval has no target recorded. That is ordinary: a society that does not run its volunteers"
	" through an HR app has no departments to record, and the paperwork does not depend on one."
)


def of(volunteer: str) -> str | None:
	"""The department this volunteer belongs to, or None. Never throws.

	One read, through the seam that owns the HR link. A volunteer with no
	employment record, on a site with no HR app, or in a build of HR that names
	the field differently, all answer None.
	"""
	if not volunteer:
		return None

	doc = frappe.get_doc(VOLUNTEER_DOCTYPE, volunteer)

	return hr.read_back(doc, DEPARTMENT_FIELD)


def capture(doc) -> None:
	"""Write each row's department onto it, and the distinct set onto the report.

	Idempotent and recomputed from scratch on every save: the field is derived,
	so re-deriving it is the only way it stays true when a volunteer is added or
	an HR record changes. Never partial — a row whose volunteer has no department
	is blanked rather than left holding a stale value.
	"""
	for row in doc.get("volunteers") or []:
		row.department = of(row.volunteer)

	doc.routing_departments = "\n".join(targets(doc))


def targets(doc) -> list[str]:
	"""The distinct departments this report would route to, sorted.

	Sorted rather than in row order so that saving a report twice without
	changing it produces the same text, and a diff of the record shows a real
	change rather than a reshuffle.
	"""
	return sorted({row.department for row in doc.get("volunteers") or [] if row.department})


def describe(doc) -> dict:
	"""The pending routing target, as a DTO. For a reader, never for a branch.

	`routes_today` is False and is not computed: it is a constant statement that
	this app does not route stipend approval anywhere, returned with the target so
	that a caller cannot read a populated `departments` list as a live route.
	"""
	found = targets(doc)

	return {
		"chain": "supervisor to head of department",
		"departments": found,
		"volunteers_without_a_department": [
			row.volunteer for row in doc.get("volunteers") or [] if not row.department
		],
		"routes_today": False,
		"note": None if found else NO_TARGET,
	}
