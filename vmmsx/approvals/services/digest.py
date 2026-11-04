# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The weekly approval summaries: one for each late approver, one for national.

A stage whose breach action is `weekly_digest` does not alert on each late
application every day. Once a week, on the society's chosen morning, each person
it routes to gets **one** email (and an in-app notification) counting what is
waiting, provided something they hold is past the stage's SLA. Nothing late,
nothing sent.

The approver's summary covers the area they hold the stage's role in:

- what is waiting for *their* decision, by place, with how many are late and
  how long the oldest has waited;
- the week's totals at their stage: arrived, approved, rejected, returned;
- what is still with the earlier stage and past its own SLA, by place, so
  somebody overseeing a region can follow it up with the county;
- **separately**, applications sent back for more information. Those wait on
  the applicant, not on anybody here, and they are never counted as waiting
  for approval.

The national summary goes to whoever holds the society's regional oversight
role at the top of the geographic tree. It counts every registration in review
for longer than the society's oversight threshold (14 days in Kenya) at its
current stage, country-wide, by region and stage, and again lists what is
waiting on applicants separately. It too is sent only when something is past
the threshold.

**Sent once per person per week.** The in-app notification is the record: its
subject carries the week, and a person who already has this week's notification
is not sent another, so the hourly job can run as often as it likes.

**It reads with `frappe.get_all`, deliberately**, unlike the analytics service.
It runs as the scheduler, not as a person, and every set it builds is narrowed
explicitly to the recipient's own assigned area through core's scope service
before anything is counted.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, get_url, getdate, now_datetime

from vmmsx.approvals import states
from vmmsx.approvals.services import config, contract, routing, sla

SETTINGS_DOCTYPE = "National Society Settings"
WEEKDAY_FIELD = "vmms_approval_digest_weekday"
OVERSIGHT_DAYS_FIELD = "vmms_approval_oversight_days"

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
DEFAULT_WEEKDAY = "Monday"
DEFAULT_OVERSIGHT_DAYS = 14
# "Morning": the hourly job sends from this hour onwards on the chosen day.
SEND_FROM_HOUR = 7

# The registrations the national summary counts.
NATIONAL_DOCTYPES = ("VMMS Membership", "VMMS Volunteer Application")

# What each list is called on screen.
TITLES = {
	"VMMS Membership": "Membership applications",
	"VMMS Volunteer Application": "Volunteer applications",
}

QUEUE_PATHS = {
	"VMMS Membership": "/portal/admin/queue/members",
	"VMMS Volunteer Application": "/portal/admin/queue/volunteers",
}

DECISION_DOCTYPE = contract.DECISION_DOCTYPE


# --- the job ---------------------------------------------------------------


def hourly() -> dict | None:
	"""Scheduler entry. Sends on the chosen weekday, from the morning onwards."""
	now = now_datetime()

	if WEEKDAYS[now.weekday()] != weekday() or now.hour < SEND_FROM_HOUR:
		return None

	return send(now)


def send(now=None) -> dict:
	"""Build and send every summary due this week. Safe to call repeatedly."""
	now = now or now_datetime()
	sent = {"approvers": [], "national": []}

	for user, summary in approver_summaries(now).items():
		if _deliver(user, summary, now):
			sent["approvers"].append(user)

	national = national_summary(now)

	if national:
		for user in national_recipients():
			if _deliver(user, national, now):
				sent["national"].append(user)

	return sent


# --- settings -----------------------------------------------------------------


def weekday() -> str:
	value = frappe.db.get_single_value(SETTINGS_DOCTYPE, WEEKDAY_FIELD) if _has(WEEKDAY_FIELD) else None
	return value if value in WEEKDAYS else DEFAULT_WEEKDAY


def oversight_days() -> int:
	value = cint(frappe.db.get_single_value(SETTINGS_DOCTYPE, OVERSIGHT_DAYS_FIELD)) if _has(OVERSIGHT_DAYS_FIELD) else 0
	return value if value > 0 else DEFAULT_OVERSIGHT_DAYS


def _has(fieldname: str) -> bool:
	return frappe.get_meta(SETTINGS_DOCTYPE).has_field(fieldname)


# --- the approver's summary ----------------------------------------------------


def approver_summaries(now=None) -> dict[str, dict]:
	"""{user: summary} for every person holding something late at a digest stage."""
	now = now or now_datetime()
	out = {}

	for doctype in config.governed_doctypes():
		workflow = config.for_doctype(doctype)

		for stage in config.stages(workflow):
			if stage.on_sla_breach != sla.BREACH_WEEKLY_DIGEST:
				continue

			for user, waiting in _routed_waiting(doctype, workflow, stage, now).items():
				if not any(row["late"] for row in waiting):
					continue

				section = _approver_section(doctype, workflow, stage, user, waiting, now)
				out.setdefault(user, {"kind": "approver", "sections": []})["sections"].append(section)

	return out


def _routed_waiting(doctype, workflow, stage, now) -> dict[str, list[dict]]:
	"""Each person this stage routes to, and the applications waiting on them."""
	field = workflow.geo_node_field
	rows = frappe.get_all(
		doctype,
		filters={contract.STATE_FIELD: states.IN_REVIEW, contract.STAGE_FIELD: stage.name},
		fields=["name", field, contract.STAGE_ENTERED_FIELD],
	)
	by_node: dict[str, list[str]] = {}
	waiting = defaultdict(list)

	for row in rows:
		node = row.get(field)

		if node not in by_node:
			by_node[node] = routing.routed(stage, node) if node else []

		days = _days(row.get(contract.STAGE_ENTERED_FIELD), now)

		for user in by_node[node]:
			waiting[user].append(
				{"name": row.name, "node": node, "days": days, "late": days >= cint(stage.sla_days)}
			)

	return waiting


def _approver_section(doctype, workflow, stage, user, waiting, now) -> dict:
	area = _area(user, stage.required_role)
	week_ago = add_days(now, -7)

	return {
		"doctype": doctype,
		"title": _(TITLES.get(doctype, doctype)),
		"stage": _(stage.stage_label),
		"sla_days": cint(stage.sla_days),
		"queue_url": get_url(QUEUE_PATHS.get(doctype, "/portal/admin") + "/assigned"),
		"waiting": _by_place(waiting),
		"waiting_total": len(waiting),
		"late_total": sum(1 for row in waiting if row["late"]),
		"oldest_days": max((row["days"] for row in waiting), default=0),
		"week": _week_at_stage(doctype, workflow, stage, area, week_ago, now),
		"earlier": _earlier_stages(doctype, workflow, stage, area, now),
		"with_applicant": _with_applicant(doctype, workflow, area, now),
	}


def _area(user: str, role: str) -> set[str] | None:
	"""The nodes `user` holds `role` over. None would mean everywhere; never returned here."""
	from onerc_core.access.services import scope

	return set(scope.get_user_geo_scope(user, role))


def _week_at_stage(doctype, workflow, stage, area, since, now) -> dict:
	"""Arrived at this stage, and decided at it, in the last seven days, in `area`."""
	field = workflow.geo_node_field
	arrived = frappe.get_all(
		doctype,
		filters={
			contract.STAGE_FIELD: stage.name,
			contract.STAGE_ENTERED_FIELD: (">=", since),
			field: ("in", list(area) or [""]),
		},
		pluck="name",
	)
	decisions = frappe.get_all(
		DECISION_DOCTYPE,
		filters={
			"parenttype": doctype,
			"stage": stage.name,
			"decided_on": (">=", since),
		},
		fields=["parent", "decision"],
	)
	parents = _anchors(doctype, field, {row.parent for row in decisions})
	counts = defaultdict(int)

	for row in decisions:
		if parents.get(row.parent) in area:
			counts[row.decision] += 1

	return {
		"arrived": len(arrived),
		"approved": counts[states.DECISION_APPROVED],
		"rejected": counts[states.DECISION_REJECTED],
		"returned": counts[states.DECISION_MORE_INFO],
	}


def _earlier_stages(doctype, workflow, stage, area, now) -> dict:
	"""Applications in `area` still at an earlier stage and past that stage's SLA."""
	field = workflow.geo_node_field
	earlier = {row.name: row for row in config.stages(workflow) if row.sequence < stage.sequence}

	if not earlier:
		return {"places": [], "total": 0, "oldest_days": 0}

	rows = frappe.get_all(
		doctype,
		filters={
			contract.STATE_FIELD: states.IN_REVIEW,
			contract.STAGE_FIELD: ("in", list(earlier)),
			field: ("in", list(area) or [""]),
		},
		fields=["name", field, contract.STAGE_FIELD, contract.STAGE_ENTERED_FIELD],
	)
	late = []

	for row in rows:
		days = _days(row.get(contract.STAGE_ENTERED_FIELD), now)

		if days >= cint(earlier[row.get(contract.STAGE_FIELD)].sla_days):
			late.append({"name": row.name, "node": row.get(field), "days": days, "late": True})

	return {"places": _by_place(late), "total": len(late), "oldest_days": max((r["days"] for r in late), default=0)}


def _with_applicant(doctype, workflow, area, now) -> dict:
	"""Sent back for more information and not yet resubmitted, in `area` (None: everywhere)."""
	field = workflow.geo_node_field
	filters = {contract.STATE_FIELD: states.DRAFT}

	if area is not None:
		filters[field] = ("in", list(area) or [""])

	drafts = {row.name: row.get(field) for row in frappe.get_all(doctype, filters=filters, fields=["name", field])}

	if not drafts:
		return {"places": [], "total": 0, "oldest_days": 0, "rows": []}

	latest = {}

	for row in frappe.get_all(
		DECISION_DOCTYPE,
		filters={"parenttype": doctype, "parent": ("in", list(drafts))},
		fields=["parent", "decision", "decided_on"],
		order_by="decided_on asc",
	):
		latest[row.parent] = row

	returned = [
		{"name": name, "node": drafts[name], "days": _days(row.decided_on, now), "late": False}
		for name, row in latest.items()
		if row.decision == states.DECISION_MORE_INFO
	]

	return {
		"places": _by_place(returned),
		"total": len(returned),
		"oldest_days": max((r["days"] for r in returned), default=0),
		"rows": returned,
	}


# --- the national summary --------------------------------------------------------


def national_recipients() -> list[str]:
	"""Holders of the regional oversight role at the top of the tree."""
	from onerc_core.access.services import scope
	from onerc_core.geo.services import adapter

	from vmmsx.setup.regional_oversight import role

	name = role()

	if not name:
		return []

	users = set()

	for root in adapter.get_root_regions():
		users.update(scope.holders_at(root["name"], name))

	return sorted(users)


def national_summary(now=None) -> dict | None:
	"""Everything in review past the oversight threshold, country-wide. None when nothing is."""
	now = now or now_datetime()
	threshold = oversight_days()
	sections = []

	for doctype in NATIONAL_DOCTYPES:
		workflow = config.optional(doctype)

		if not workflow:
			continue

		field = workflow.geo_node_field
		labels = {row.name: _(row.stage_label) for row in config.stages(workflow)}
		rows = frappe.get_all(
			doctype,
			filters={contract.STATE_FIELD: states.IN_REVIEW},
			fields=["name", field, contract.STAGE_FIELD, contract.STAGE_ENTERED_FIELD],
		)
		overdue = []

		for row in rows:
			days = _days(row.get(contract.STAGE_ENTERED_FIELD), now)

			if days >= threshold:
				overdue.append(
					{
						"name": row.name,
						"node": _region_of(row.get(field)),
						"stage": labels.get(row.get(contract.STAGE_FIELD), ""),
						"days": days,
						"late": True,
					}
				)

		with_applicant = _with_applicant(doctype, workflow, None, now)
		with_applicant_old = [r for r in with_applicant["rows"] if r["days"] >= threshold]

		sections.append(
			{
				"doctype": doctype,
				"title": _(TITLES.get(doctype, doctype)),
				"queue_url": get_url(QUEUE_PATHS.get(doctype, "/portal/admin")),
				"overdue_total": len(overdue),
				"oldest_days": max((r["days"] for r in overdue), default=0),
				"by_region": _by_place([{**r, "node": r["node"]} for r in overdue]),
				"by_stage": _count_by(overdue, "stage"),
				"with_applicant_total": with_applicant["total"],
				"with_applicant_old": len(with_applicant_old),
			}
		)

	if not any(section["overdue_total"] for section in sections):
		return None

	return {"kind": "national", "threshold": threshold, "sections": sections}


def _region_of(node: str | None) -> str | None:
	"""The ancestor directly below the top of the tree (a region, in Kenya)."""
	if not node:
		return None

	from onerc_core.geo.services import adapter

	chain = [node, *(row["name"] for row in adapter.get_ancestors(node))]

	return chain[-2] if len(chain) >= 2 else chain[0]


# --- delivery ---------------------------------------------------------------------


def week_label(now=None) -> str:
	"""The Monday of the week, as a date: what makes a summary this week's."""
	today = getdate(now or now_datetime())
	return str(add_days(today, -today.weekday()))


def subject_for(summary: dict, now=None) -> str:
	if summary["kind"] == "national":
		return _("Approvals waiting more than {0} days, week of {1}").format(summary["threshold"], week_label(now))

	return _("Approvals waiting for you, week of {0}").format(week_label(now))


def _deliver(user: str, summary: dict, now) -> bool:
	"""Email and in-app notification, once per person per week per kind."""
	subject = subject_for(summary, now)

	if frappe.db.exists("Notification Log", {"for_user": user, "subject": subject}):
		return False

	email = frappe.db.get_value("User", {"name": user, "enabled": 1}, "email")

	if not email:
		return False

	template = "templates/emails/approval_digest.html"
	message = frappe.render_template(template, {"summary": summary, "subject": subject})

	frappe.sendmail(recipients=[email], subject=subject, message=message, reference_doctype=None)

	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"type": "Alert",
			"subject": subject,
			"email_content": message,
		}
	).insert(ignore_permissions=True)

	return True


# --- shared shapes ---------------------------------------------------------------------


def _days(when, now) -> int:
	if not when:
		return 0
	return max((get_datetime(now) - get_datetime(when)).days, 0)


def _by_place(rows: list[dict]) -> list[dict]:
	"""[{place, count, late, oldest_days}], busiest first."""
	from vmmsx.places import place_name

	groups = defaultdict(list)

	for row in rows:
		groups[row["node"]].append(row)

	places = [
		{
			"place": place_name(node) if node else _("No place recorded"),
			"count": len(items),
			"late": sum(1 for item in items if item["late"]),
			"oldest_days": max(item["days"] for item in items),
		}
		for node, items in groups.items()
	]

	return sorted(places, key=lambda row: (-row["count"], row["place"]))


def _count_by(rows: list[dict], key: str) -> list[dict]:
	counts = defaultdict(int)

	for row in rows:
		counts[row[key]] += 1

	return [{"label": label, "count": count} for label, count in sorted(counts.items(), key=lambda item: -item[1])]


def _anchors(doctype: str, field: str, names: set[str]) -> dict[str, str]:
	if not names:
		return {}

	return dict(frappe.get_all(doctype, filters={"name": ("in", list(names))}, fields=["name", field], as_list=True))
