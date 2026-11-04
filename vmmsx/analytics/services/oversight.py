# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A region, or the whole country, county by county.

What the console's Region and National tabs draw. The questions behind them
are a regional head's: which county is falling behind, what is waiting on me,
what do we have and where. So every figure is given **per county** (the map
and the comparison table) and summed for the area, and the selected county
gets its breakdowns.

The scope guarantees are `summary.py`'s and for the same reasons: every
register is read through `frappe.get_list`, so a figure here is a count of
records the caller could open one at a time. A regional head reads their region
through the reading role core grants them; a national head reads the country
the same way; System Manager reads everything. Nobody can widen it by naming
an area: the area only picks which counties are *laid out*, and the counts
inside them are still whatever the caller may read.

Profile attributes (gender, age, disability) are read with permissions
bypassed for exactly the profiles behind the volunteers and memberships the
caller has already been shown, the narrow bend `summary._hours` documents.
"""

from collections import defaultdict

import frappe
from frappe.utils import add_days, cint, date_diff, getdate, now_datetime, nowdate

from vmmsx.analytics.services import summary
from vmmsx.approvals import states
from vmmsx.approvals.services import config, contract

VOLUNTEER = "VMMS Volunteer"
APPLICATION = "VMMS Volunteer Application"
MEMBERSHIP = "VMMS Membership"
ASSET = "VMMS Branch Asset"
TRANSACTION = "VMMS Asset Transaction"
DEPLOYMENT = "VMMS Deployment"
PROFILE = "Red Profile"
DISABILITY_FIELD = "vmms_disability_status"

# Names are read in pieces, so a national `in (...)` stays a size every
# database accepts. The same figure `api/analytics.py` uses.
CHUNK = 1000

REGISTRATIONS = (APPLICATION, MEMBERSHIP)

NEW_DAYS = 30
EXPIRING_DAYS = 60

# Kenya's constitution defines youth as 18 to 35, which is the band a branch
# reports on; the others follow from it.
AGE_BANDS = (("Under 18", 0, 17), ("18–35", 18, 35), ("36–59", 36, 59), ("60 and over", 60, 200))
NOT_RECORDED = "Not recorded"

FIGURES = (
	"volunteers",
	"members",
	"new_30d",
	"expiring_60d",
	"waiting",
	"waiting_late",
	"with_applicant",
	"deployments",
	"materials_items",
	"materials_total",
	"materials_lent",
)


def overview(area: str, place: str | None = None) -> dict:
	"""Everything the tab draws for `area`, with `place` as the selected county."""
	from onerc_core.geo.services import adapter

	tree = _tree(area)
	units = _units(tree, area)
	unit_of = _within(tree, units)
	rows_by_unit = {unit["name"]: _blank(unit) for unit in units}
	children = adapter.get_children(area)
	child_of = _within(tree, children)

	# At the top of the tree "under the area" is everything, and naming every
	# ward in an `in (...)` would only slow the query down. Scope still applies.
	nodes = None if _is_root(area) else list(unit_of)

	_count_people(rows_by_unit, unit_of, nodes)
	_count_registrations(rows_by_unit, unit_of, nodes)
	_count_materials(rows_by_unit, unit_of, nodes)
	_count_deployments(rows_by_unit, unit_of, nodes)
	_mark_approvers(rows_by_unit)

	unit_rows = sorted(rows_by_unit.values(), key=lambda row: row["label"])
	# On a region the children are the counties; on the country they are the
	# regions, and the comparison table is drawn a level up.
	# An area that is itself a county is drawn as that county.
	rolled = bool(units) and all(child_of.get(unit["name"]) not in (None, unit["name"]) for unit in units)
	rows = _roll_up(unit_rows, children, child_of) if rolled else unit_rows

	selected = place if place and place in {row["name"] for row in rows} else None
	focus = selected or area
	focus_nodes = None if _is_root(focus) else list(_within(tree, [_bounds_of(tree, focus)]))

	return {
		"as_of": nowdate(),
		"area": _node(area),
		"units": unit_rows,
		"rows": rows,
		"totals": _sum(unit_rows),
		"selected": _node(selected) if selected else None,
		"selected_totals": next((row for row in rows if row["name"] == selected), None),
		"breakdown": _breakdown(focus_nodes),
		"attention": _attention(rows, children, area),
	}


# --- the layout ----------------------------------------------------------------


def _tree(area: str) -> list[dict]:
	"""Every node at or under `area`, read once by its nested-set bounds."""
	bounds = frappe.db.get_value("Geo Node", area, ["lft", "rgt"], as_dict=True)

	if not bounds:
		frappe.throw(frappe._("That place does not exist."), frappe.DoesNotExistError)

	return frappe.get_all(
		"Geo Node",
		filters={"lft": (">=", bounds.lft), "rgt": ("<=", bounds.rgt)},
		fields=["name", "geo_node_name", "geo_code", "geo_level", "parent_geo_node", "lft", "rgt", "latitude", "longitude"],
		order_by="lft asc",
		ignore_permissions=True,  # the place tree is not a register; nothing here is a count
	)


def _units(tree: list[dict], area: str) -> list[dict]:
	"""The counties (the society's registration level) at or under `area`."""
	level = config_level()
	rows = [node for node in tree if node.geo_level == level] if level else []

	if not rows:
		rows = [node for node in tree if node.parent_geo_node == area]

	return sorted(
		(
			{
				"name": row.name,
				"label": row.geo_node_name,
				"code": row.geo_code,
				"parent": row.parent_geo_node,
				"lft": row.lft,
				"rgt": row.rgt,
				"point": {"latitude": row.latitude, "longitude": row.longitude}
				if row.latitude and row.longitude
				else None,
			}
			for row in rows
		),
		key=lambda unit: unit["label"],
	)


def config_level() -> str | None:
	"""The level registrations anchor at: the county, in Kenya."""
	from onerc_core.society.services import config as society

	settings = society.settings()

	return settings.get("vmms_volunteer_anchor_level") or settings.get("vmms_membership_anchor_level") or None


def _within(tree: list[dict], parents: list[dict]) -> dict[str, str]:
	"""Every node of the tree mapped to the one of `parents` it sits in."""
	lookup = {}

	for node in tree:
		for parent in parents:
			if parent["lft"] <= node.lft and node.rgt <= parent["rgt"]:
				lookup[node.name] = parent["name"]
				break

	return lookup


def _blank(unit: dict) -> dict:
	row = {key: value for key, value in unit.items() if key not in ("lft", "rgt")}
	return {**row, **{key: 0 for key in FIGURES}, "oldest_days": 0, "has_approver": True}


def _node(name: str | None) -> dict | None:
	if not name:
		return None

	row = frappe.db.get_value("Geo Node", name, ["name", "geo_node_name", "geo_level", "geo_code"], as_dict=True)

	return {"name": row.name, "label": row.geo_node_name, "level": row.geo_level, "code": row.geo_code} if row else None


def _bounds_of(tree: list[dict], name: str) -> dict:
	node = next(node for node in tree if node.name == name)
	return {"name": node.name, "lft": node.lft, "rgt": node.rgt}


# --- the counts ------------------------------------------------------------------


def _count_people(rows: dict, unit_of: dict, nodes: list[str] | None) -> None:
	for row in summary._rows(VOLUNTEER, "home_geo_node", nodes, ["home_geo_node"], {"status": "Active"}):
		_bump(rows, unit_of, row.home_geo_node, "volunteers")

	today = getdate(nowdate())
	soon = add_days(today, EXPIRING_DAYS)

	for row in summary._rows(
		MEMBERSHIP, "geo_node", nodes, ["geo_node", "valid_to"], {"membership_status": "Active"}
	):
		_bump(rows, unit_of, row.geo_node, "members")

		if row.valid_to and today <= getdate(row.valid_to) <= soon:
			_bump(rows, unit_of, row.geo_node, "expiring_60d")


def _count_registrations(rows: dict, unit_of: dict, nodes: list[str] | None) -> None:
	"""New in the last 30 days; waiting for a decision; waiting on the applicant."""
	since = add_days(now_datetime(), -NEW_DAYS)
	now = now_datetime()

	for doctype in REGISTRATIONS:
		workflow = config.optional(doctype)
		sla_days = {stage.name: cint(stage.sla_days) for stage in config.stages(workflow)} if workflow else {}
		records = summary._rows(
			doctype,
			"geo_node",
			nodes,
			["name", "geo_node", "creation", contract.STATE_FIELD, contract.STAGE_FIELD, contract.STAGE_ENTERED_FIELD],
		)
		drafts = []

		for row in records:
			state = row.get(contract.STATE_FIELD) or states.DRAFT

			if state != states.DRAFT and row.creation and row.creation >= since:
				_bump(rows, unit_of, row.geo_node, "new_30d")

			if state == states.IN_REVIEW:
				days = max(date_diff(now, row.get(contract.STAGE_ENTERED_FIELD)), 0) if row.get(contract.STAGE_ENTERED_FIELD) else 0
				unit = unit_of.get(row.geo_node)

				if unit:
					rows[unit]["waiting"] += 1
					rows[unit]["oldest_days"] = max(rows[unit]["oldest_days"], days)

					if days >= sla_days.get(row.get(contract.STAGE_FIELD), 10**6):
						rows[unit]["waiting_late"] += 1
			elif state == states.DRAFT:
				drafts.append(row)

		for row in _returned(doctype, drafts):
			_bump(rows, unit_of, row.geo_node, "with_applicant")


def _returned(doctype: str, drafts: list) -> list:
	"""Drafts whose latest decision asked for more information.

	The decision rows are read for exactly the drafts the caller was shown.
	"""
	if not drafts:
		return []

	latest = {}

	for names in _chunks([row.name for row in drafts]):
		for row in frappe.get_all(
			contract.DECISION_DOCTYPE,
			filters={"parenttype": doctype, "parent": ("in", names)},
			fields=["parent", "decision"],
			order_by="decided_on asc",
			ignore_permissions=True,
		):
			latest[row.parent] = row.decision

	return [row for row in drafts if latest.get(row.name) == states.DECISION_MORE_INFO]


def _count_materials(rows: dict, unit_of: dict, nodes: list[str] | None) -> None:
	for row in summary._rows(
		ASSET, "geo_node", nodes, ["geo_node", "total_quantity", "available_quantity"], {"is_active": 1}
	):
		unit = unit_of.get(row.geo_node)

		if not unit:
			continue

		total = cint(row.total_quantity)
		rows[unit]["materials_items"] += 1
		rows[unit]["materials_total"] += total
		rows[unit]["materials_lent"] += max(total - cint(row.available_quantity), 0)


def _count_deployments(rows: dict, unit_of: dict, nodes: list[str] | None) -> None:
	for row in summary._rows(DEPLOYMENT, "geo_node", nodes, ["geo_node"], {"status": "Active"}):
		_bump(rows, unit_of, row.geo_node, "deployments")


def _mark_approvers(rows: dict) -> None:
	"""A county with nobody to approve its volunteers or its members."""
	from onerc_core.access.services import scope
	from onerc_core.society.services import config as society

	settings = society.settings()
	roles = [settings.get("vmms_volunteer_scope_role"), settings.get("vmms_membership_scope_role")]

	for unit, row in rows.items():
		row["has_approver"] = all(scope.holders_at(unit, role) for role in roles if role)


def _bump(rows: dict, unit_of: dict, node: str | None, key: str) -> None:
	unit = unit_of.get(node)

	if unit:
		rows[unit][key] += 1


def _roll_up(units: list[dict], children: list[dict], child_of: dict) -> list[dict]:
	"""County rows summed into the area's children: regions, on the national tab."""
	grouped = defaultdict(list)

	for unit in units:
		grouped[child_of.get(unit["name"])].append(unit)

	out = []

	for child in children:
		members = grouped.get(child["name"], [])
		row = {
			"name": child["name"],
			"label": child.get("geo_node_name") or child["name"],
			"code": child.get("geo_code"),
			"parent": child.get("parent_geo_node"),
			"point": None,
			**_sum(members),
			"counties": [unit["name"] for unit in members],
		}
		out.append(row)

	return sorted(out, key=lambda row: row["label"])


def _sum(rows: list[dict]) -> dict:
	total = {key: sum(row.get(key, 0) for row in rows) for key in FIGURES}
	total["oldest_days"] = max((row.get("oldest_days", 0) for row in rows), default=0)
	total["without_approver"] = sum(1 for row in rows if not row.get("has_approver", True))
	return total


# --- what needs attention -----------------------------------------------------------


def _attention(rows: list[dict], children: list[dict], area: str) -> dict:
	from onerc_core.access.services import scope

	from vmmsx.api import approvals
	from vmmsx.setup.regional_oversight import role

	mine = 0

	for doctype in REGISTRATIONS:
		try:
			mine += len(approvals.my_queue(doctype))
		except frappe.PermissionError:
			pass

	oversight = role()
	without_head = []

	if oversight and area in {row["name"] for row in _roots()}:
		without_head = [
			{"name": child["name"], "label": child.get("geo_node_name")}
			for child in children
			if not scope.holders_at(child["name"], oversight)
		]

	return {
		"mine": mine,
		"late": [
			{"name": row["name"], "label": row["label"], "count": row["waiting_late"], "oldest_days": row["oldest_days"]}
			for row in sorted(rows, key=lambda row: -row["waiting_late"])
			if row["waiting_late"]
		],
		"without_approver": [
			{"name": row["name"], "label": row["label"]}
			for row in rows
			if row.get("without_approver") or not row.get("has_approver", True)
		],
		"without_head": without_head,
		"lent_out": sum(row["materials_lent"] for row in rows),
	}


def _roots() -> list[dict]:
	from onerc_core.geo.services import adapter

	return adapter.get_root_regions()


# --- breakdowns for the selected place -----------------------------------------------


def _breakdown(nodes: list[str] | None) -> dict:
	volunteers = summary._rows(VOLUNTEER, "home_geo_node", nodes, ["red_profile"], {"status": "Active"})
	memberships = summary._rows(
		MEMBERSHIP, "geo_node", nodes, ["member", "membership_type"], {"membership_status": "Active"}
	)
	member_profiles = _values("VMMS Member", {row.member for row in memberships if row.member}, "red_profile")

	return {
		"volunteers": _people({row.red_profile for row in volunteers if row.red_profile}),
		"members": _people({profile for profile in member_profiles.values() if profile}),
		"plans": _plans(memberships),
		"materials": _materials(nodes),
		"trend": summary._trend(nodes, summary.MONTHS),
	}


def _people(profiles: set[str]) -> dict:
	"""Gender, age band and disability, for profiles already in the caller's view."""
	fields = ["gender", "date_of_birth"]

	if frappe.get_meta(PROFILE).has_field(DISABILITY_FIELD):
		fields.append(DISABILITY_FIELD)

	rows = []

	for names in _chunks(sorted(profiles)):
		rows += frappe.get_all(
			PROFILE,
			filters={"name": ("in", names)},
			fields=fields,
			ignore_permissions=True,  # bounded by profiles the caller was shown; see module docstring
		)

	today = getdate(nowdate())
	ages = defaultdict(int)

	for row in rows:
		ages[_band(row.date_of_birth, today)] += 1

	return {
		"total": len(rows),
		"gender": _count(row.gender or NOT_RECORDED for row in rows),
		"age": [{"label": label, "count": ages.get(label, 0)} for label, *_ in AGE_BANDS]
		+ [{"label": NOT_RECORDED, "count": ages.get(NOT_RECORDED, 0)}],
		"disability": _count(row.get(DISABILITY_FIELD) or NOT_RECORDED for row in rows),
	}


def _band(dob, today) -> str:
	if not dob:
		return NOT_RECORDED

	dob = getdate(dob)
	age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

	for label, low, high in AGE_BANDS:
		if low <= age <= high:
			return label

	return NOT_RECORDED


def _materials(nodes: list[str]) -> list[dict]:
	categories = defaultdict(lambda: {"items": 0, "total": 0, "lent": 0})

	for row in summary._rows(ASSET, "geo_node", nodes, ["category", "total_quantity", "available_quantity"], {"is_active": 1}):
		bucket = categories[row.category or NOT_RECORDED]
		total = cint(row.total_quantity)
		bucket["items"] += 1
		bucket["total"] += total
		bucket["lent"] += max(total - cint(row.available_quantity), 0)

	return sorted(({"category": key, **value} for key, value in categories.items()), key=lambda row: -row["total"])


def _count(values) -> list[dict]:
	counts = defaultdict(int)

	for value in values:
		counts[value or NOT_RECORDED] += 1

	return [{"label": label, "count": count} for label, count in sorted(counts.items(), key=lambda item: -item[1])]


def _plans(memberships: list) -> list[dict]:
	"""Active memberships by plan, under the plan's own name."""
	titles = _values("VMMS Membership Type", {row.membership_type for row in memberships if row.membership_type}, "membership_type_name")
	return _count(titles.get(row.membership_type) or row.membership_type for row in memberships)


def _values(doctype: str, names: set, fieldname: str) -> dict:
	values = {}

	for chunk in _chunks(sorted(names)):
		values.update(
			frappe.get_all(
				doctype, filters={"name": ("in", chunk)}, fields=["name", fieldname], as_list=True, ignore_permissions=True
			)
		)

	return values


def _chunks(names: list[str]):
	for start in range(0, len(names), CHUNK):
		yield names[start : start + CHUNK]


def _is_root(name: str) -> bool:
	return not frappe.db.get_value("Geo Node", name, "parent_geo_node")


# --- who may open which tab ------------------------------------------------------------


def national_allowed(user: str | None = None) -> bool:
	"""National staff: anybody assigned at the top of the tree, and System Manager.

	Any role counts. The national tab is the country's figures, and somebody the
	society has placed at national level is national staff whatever they hold.
	What they then *see* is still their own scope, through `get_list`.
	"""
	user = user or frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True

	from frappe.utils import today
	from onerc_core.onerc_core.doctype.geo_assignment.geo_assignment import GRANTS_AUTHORITY_SQL

	return bool(
		frappe.db.sql(
			f"""
			SELECT 1
			FROM `tabGeo Assignment` assignment
			INNER JOIN `tabGeo Node` node ON node.name = assignment.geo_node
			WHERE assignment.user = %(user)s
				AND IFNULL(node.parent_geo_node, '') = ''
				AND {GRANTS_AUTHORITY_SQL}
			LIMIT 1
			""",
			{"user": user, "on_date": today()},
		)
	)


def regions_for(user: str | None = None) -> list[dict]:
	"""The areas this person may open on the region tab.

	Their own: wherever they hold the society's regional oversight role. National
	staff may open any of the country's regions (the level under the top).
	"""
	from onerc_core.access.services import scope
	from onerc_core.geo.services import adapter

	from vmmsx.setup.regional_oversight import role

	user = user or frappe.session.user

	if national_allowed(user):
		names = [child.name for root in adapter.get_root_regions() for child in adapter.get_children(root.name)]
	else:
		oversight = role()
		names = [node for node in scope.live_assignment_nodes(user, oversight) if not _is_root(node)] if oversight else []

	if not names:
		return []

	rows = frappe.get_all(
		"Geo Node",
		filters={"name": ("in", names)},
		fields=["name", "geo_node_name", "geo_level"],
		order_by="geo_node_name asc",
		ignore_permissions=True,
	)

	return [{"name": row.name, "label": row.geo_node_name, "level": row.geo_level} for row in rows]


def counties(area: str) -> list[dict]:
	"""The counties under `area`, with their codes and saved coordinates."""
	return _units(_tree(area), area)


def access_pending(user: str | None = None) -> bool:
	"""True for somebody whose only view of the region is the oversight role,
	on a site whose onerc_core cannot yet admit that role to any record."""
	from vmmsx.setup.regional_oversight import core_reads_through_oversight_role, role

	user = user or frappe.session.user

	if core_reads_through_oversight_role() or user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return False

	oversight = role()

	return bool(oversight and oversight in frappe.get_roles(user))


def national_area() -> str | None:
	"""The top of the tree. One root is a society; several is a tree to fix."""
	from onerc_core.geo.services import adapter

	roots = adapter.get_root_regions()

	return roots[0].name if roots else None
