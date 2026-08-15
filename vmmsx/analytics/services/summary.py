# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What a coordinator's own part of the society looks like, in numbers.

A read-only service over records other modules own. It writes nothing, it holds
no doctype of its own, and every figure in it is counted live rather than stored
on a summary record somewhere, because a stored total is a total that is wrong
between the thing happening and the job that recomputes it.

The scope guarantee
-------------------

**A coordinator can never be counted a record they are not allowed to open, and
there is no argument by which they could ask to be.** The same three properties
`deployment/services/matching.py` sets out, and for the same reason:

1. **The scope is derived from the session and cannot be passed in.** There is no
   `user` parameter and no `nodes` parameter anywhere in this module. `geo_node`
   narrows to one part of what the caller already holds; it never widens.
2. **Every count runs through `frappe.get_list`, never `frappe.get_all`.** Only
   the first applies core's permission query condition, which is the same filter
   behind the list view, so a figure here is by construction a count of rows the
   caller could open one at a time. The one place that rule is bent is hours, and
   it is bent in a documented, narrower way. See `_hours`.
3. **It fails closed.** No scope means no rows, which means zeroes. A zero is an
   honest answer for somebody who holds nothing, and it is the same answer core's
   list view gives them.

**Each doctype is scoped by its own role.** Volunteers are filtered by the
society's volunteer scope role, memberships by its membership scope role, and so
on, because that is how they are registered in `hooks.py`. So a coordinator who
holds one and not the other sees a panel with real volunteer numbers and zeroes
where the memberships would be, which is the truth about what they may see
rather than a refusal of the whole screen.

**The vocabularies are read from the schema, not written here.** `_by_status`
asks `frappe.get_meta` for the Select's options rather than listing them, so this
file names no status at all and a state added to a doctype appears in the
breakdown without anybody remembering to come here. That is the same discipline
the rest of the app applies to society vocabularies, applied to a code-owned one.

What is deliberately absent
---------------------------

* **Money.** A society's income is `onerc_payments`' record, not this app's, and
  a revenue figure assembled here would be a second answer to a question another
  app owns. The console says so rather than showing a number nobody can reconcile.
* **Applications waiting.** `VMMS Volunteer Application` is deliberately not
  registered as geo-scopeable (see `hooks.py`), so counting it here would produce
  a nationwide figure inside a panel labelled with one branch. The review queue
  already answers "what is waiting on you", person by person, which is the
  question a coordinator actually has.
"""

import frappe
from frappe.utils import add_months, getdate, nowdate

from vmmsx.task.services import states as task_states

VOLUNTEER_DOCTYPE = "VMMS Volunteer"
MEMBERSHIP_DOCTYPE = "VMMS Membership"
DEPLOYMENT_DOCTYPE = "VMMS Deployment"
TASK_DOCTYPE = "VMMS Task"
TIME_LOG_DOCTYPE = "VMMS Time Log"

# How far back the trend looks by default. A year, because a year is what makes
# a season visible, and a coordinator comparing this March with last March is
# asking the question the chart is for.
MONTHS = 12

# The ceiling on how many volunteers' hours are summed in one call. A branch with
# more than this has an analytics need that a page of tiles does not serve, and an
# unbounded `IN` clause is how a dashboard takes a site down.
HOURS_CEILING = 5000


def branch_summary(geo_node: str | None = None, months: int = MONTHS) -> dict:
	"""Every figure the console's analytics screen draws, in one call.

	One endpoint rather than six, deliberately: the screen shows them together
	and six requests would paint it in six stages, each with its own spinner and
	its own chance of a partial answer that reads as a real one.
	"""
	nodes = _narrowing(geo_node)

	volunteers = _names(VOLUNTEER_DOCTYPE, "home_geo_node", nodes)

	return {
		"geo_node": geo_node or "",
		"volunteers": {
			"total": len(volunteers),
			"by_status": _by_status(VOLUNTEER_DOCTYPE, "status", "home_geo_node", nodes),
		},
		"members": {
			"total": _count(MEMBERSHIP_DOCTYPE, "geo_node", nodes),
			"by_status": _by_status(MEMBERSHIP_DOCTYPE, "membership_status", "geo_node", nodes),
		},
		"deployments": {
			"total": _count(DEPLOYMENT_DOCTYPE, "geo_node", nodes),
			"by_status": _by_status(DEPLOYMENT_DOCTYPE, "status", "geo_node", nodes),
		},
		"tasks": _tasks(nodes),
		"hours": _hours(volunteers),
		"trend": _trend(nodes, months),
		"coverage": _coverage(geo_node, nodes),
	}


# --- the counts -----------------------------------------------------------


def _count(doctype: str, anchor_field: str, nodes: list[str] | None) -> int:
	"""How many rows of this doctype the caller can see, narrowed to `nodes`.

	`frappe.get_list` and never `frappe.db.count`, which takes no permission
	query condition at all and would silently answer for the whole site. Counted
	from names rather than with a SQL `COUNT`, because the permission layer is
	applied to the query that returns rows and this is the query that has it.
	"""
	return len(_names(doctype, anchor_field, nodes))


def _names(doctype: str, anchor_field: str, nodes: list[str] | None) -> list[str]:
	"""The names of the rows the caller can see, narrowed to `nodes`."""
	return [row["name"] for row in _rows(doctype, anchor_field, nodes, ["name"])]


def _rows(
	doctype: str, anchor_field: str, nodes: list[str] | None, fields: list[str], extra: dict | None = None
) -> list[dict]:
	"""Every row of `doctype` this caller may see, narrowed to `nodes`.

	**The single read in this module**, so the three properties it has to hold
	are written once rather than repeated at six call sites.

	`frappe.get_list`, never `frappe.get_all`: only the first applies core's
	permission query condition, and a count assembled with the second would
	answer for the whole site while looking identical.

	An empty `nodes` is nothing, never everything. A framework is entitled to
	treat `("in", [])` as no filter at all, which would turn "this branch" into
	"the whole country" precisely when the caller was entitled to neither.

	**A `PermissionError` is zero rows, not an exception.** A coordinator whose
	society has named its volunteer scope role but not its membership one holds
	no read permission on `VMMS Membership` at all, and Frappe refuses the query
	outright rather than returning nothing. Letting that escape would take the
	whole panel down over one unconfigured setting; caught here it renders as an
	honest zero beside the numbers that are real, which is what the screen says
	it does.
	"""
	if nodes is not None and not nodes:
		return []

	if not frappe.db.exists("DocType", doctype):
		# The module can be absent on a site mid-migrate. Zeroes rather than an
		# exception that takes the panel with it.
		return []

	filters: dict = dict(extra or {})

	if nodes is not None:
		filters[anchor_field] = ("in", nodes)

	try:
		return frappe.get_list(doctype, filters=filters, fields=fields, limit_page_length=0)
	except frappe.PermissionError:
		return []


def _by_status(doctype: str, status_field: str, anchor_field: str, nodes: list[str] | None) -> dict:
	"""How many sit in each state of a doctype's own Select.

	The states come from `frappe.get_meta`, so no status string appears in this
	file and one added to a doctype turns up here on its own. Every state is
	reported, including the ones at zero: a breakdown that omitted its empty
	states would redraw itself into a different shape as records moved, and a
	chart whose bars change identity between refreshes is unreadable.
	"""
	counts = {status: 0 for status in _options(doctype, status_field)}

	for row in _rows(doctype, anchor_field, nodes, [status_field]):
		status = row.get(status_field)

		if status in counts:
			counts[status] += 1

	return counts


def _tasks(nodes: list[str] | None) -> dict:
	"""The three things a coordinator's attention is for.

	Not a full status breakdown, unlike the doctypes above, because a task's
	states are a queue rather than a population: what somebody wants to know is
	how much is outstanding, how much is waiting on *them*, and how much is late.
	"""
	rows = _rows(
		TASK_DOCTYPE,
		"geo_node",
		nodes,
		["status", "due_on"],
		extra={"status": ("in", task_states.OPEN)},
	)

	today = getdate(nowdate())

	return {
		"open": len(rows),
		"awaiting_sign_off": sum(1 for row in rows if row.status == task_states.SUBMITTED),
		# Late, which is a thing for somebody to notice rather than a thing the
		# software refuses. A task with no date cannot be late.
		"overdue": sum(1 for row in rows if row.due_on and getdate(row.due_on) < today),
	}


def _hours(volunteers: list[str]) -> dict:
	"""Hours logged by the volunteers the caller can see.

	**The one place in this module that reads with permissions bypassed, and the
	narrowest form of it available.** `VMMS Time Log` is deliberately not
	registered as geo-scopeable: a log's own anchor is where the activity
	happened, which is not the same question as whose record it is, and scoping
	it would hide a volunteer's own hours from the coordinator who supervises
	them the moment they helped in the next county.

	So the scope is applied to the *volunteers* first, through the ordinary
	permission layer in `branch_summary`, and the logs are then read for exactly
	that set. The bypass therefore cannot widen anything: it reads logs belonging
	to people the caller has already been shown, and the set was computed before
	this function was called rather than from an argument it was handed.
	"""
	if not volunteers:
		return {"total": 0.0, "logged_by": 0, "truncated": False}

	truncated = len(volunteers) > HOURS_CEILING

	rows = frappe.get_all(
		TIME_LOG_DOCTYPE,
		filters={"volunteer": ("in", volunteers[:HOURS_CEILING])},
		fields=["volunteer", "hours"],
		limit_page_length=0,
		ignore_permissions=True,  # See the docstring: bounded by an already-scoped set.
	)

	return {
		"total": round(sum(row.hours or 0 for row in rows), 1),
		"logged_by": len({row.volunteer for row in rows}),
		# Reported rather than hidden. A figure that quietly stopped counting at
		# five thousand people would be a wrong number nobody could see was wrong.
		"truncated": truncated,
	}


def _trend(nodes: list[str] | None, months: int) -> list[dict]:
	"""New volunteers and new memberships, month by month, oldest first.

	Counted from `creation` rather than from `joined_on` or `valid_from`, and the
	choice is worth stating: those two are dates a society *sets*, so a branch
	back-filling last year's paperwork would redraw last year's chart. `creation`
	is when the record appeared, which is the question a growth chart asks.
	"""
	months = max(1, min(int(months or MONTHS), 36))

	buckets = _months(months)

	volunteers = _created_by_month(VOLUNTEER_DOCTYPE, "home_geo_node", nodes, buckets)
	members = _created_by_month(MEMBERSHIP_DOCTYPE, "geo_node", nodes, buckets)

	return [
		{
			"month": month,
			"volunteers": volunteers.get(month, 0),
			"members": members.get(month, 0),
		}
		for month in buckets
	]


def _created_by_month(
	doctype: str, anchor_field: str, nodes: list[str] | None, buckets: list[str]
) -> dict[str, int]:
	"""How many of this doctype appeared in each month, within scope."""
	counts: dict[str, int] = {}

	rows = _rows(
		doctype,
		anchor_field,
		nodes,
		["creation"],
		extra={"creation": (">=", f"{buckets[0]}-01 00:00:00")},
	)

	for row in rows:
		month = str(row.creation)[:7]
		counts[month] = counts.get(month, 0) + 1

	return counts


def _coverage(geo_node: str | None, nodes: list[str] | None) -> list[dict]:
	"""Volunteers and members per place, one rung down from where you are looking.

	The question behind "which of my branches is thin". One rung and not the
	whole subtree, because a county coordinator wants their branches rather than
	every ward in the county, and a national one wants regions rather than four
	thousand villages.

	Empty when the anchor has no children, which is the honest answer at the
	bottom of a society's ladder rather than a chart of one bar labelled with the
	place you are already looking at.
	"""
	from onerc_core.geo.services import adapter

	children = adapter.get_children(geo_node) if geo_node else adapter.get_root_regions()

	if not children:
		return []

	visible = set(nodes) if nodes is not None else None
	rows = []

	for child in children:
		beneath = [child["name"], *adapter.get_descendants(child["name"])]

		# Intersected with what the caller may see, so a coordinator looking at a
		# node they hold only part of gets their part rather than a total they
		# cannot open the records behind.
		within = beneath if visible is None else [node for node in beneath if node in visible]

		volunteers = _count(VOLUNTEER_DOCTYPE, "home_geo_node", within)
		members = _count(MEMBERSHIP_DOCTYPE, "geo_node", within)

		rows.append(
			{
				"geo_node": child["name"],
				# The society's own word for the place, from core's own
				# projection. No read of `tabGeo Node` in this app, here or
				# anywhere: the adapter already carries the label.
				"label": child.get("geo_node_name") or child["name"],
				"volunteers": volunteers,
				"members": members,
			}
		)

	# Busiest first, then alphabetically, so two branches with the same numbers
	# keep a stable order between refreshes rather than swapping places.
	rows.sort(key=lambda row: (-(row["volunteers"] + row["members"]), row["label"]))

	return rows


# --- scope and time -------------------------------------------------------


def _narrowing(geo_node: str | None) -> list[str] | None:
	"""The nodes to filter on, or None for "whatever the caller may see".

	None is the important case and it is not the same as an empty list. With no
	anchor named, no node filter is applied at all and core's permission query
	condition is the only thing bounding the result, which is exactly right: it
	is already the caller's own scope. An empty list means the caller asked for a
	place with nothing visible in it, and it must count nothing.
	"""
	if not geo_node:
		return None

	from onerc_core.geo.services import adapter

	try:
		return [geo_node, *adapter.get_descendants(geo_node)]
	except frappe.DoesNotExistError:
		return []


def _months(count: int) -> list[str]:
	"""The last `count` months as `YYYY-MM`, oldest first."""
	today = getdate(nowdate())

	return [str(add_months(today, -offset))[:7] for offset in range(count - 1, -1, -1)]


def _options(doctype: str, fieldname: str) -> list[str]:
	"""A Select's options, read from the schema so no state is written here."""
	field = frappe.get_meta(doctype).get_field(fieldname)

	if not field or not field.options:
		return []

	return [option for option in field.options.split("\n") if option]
