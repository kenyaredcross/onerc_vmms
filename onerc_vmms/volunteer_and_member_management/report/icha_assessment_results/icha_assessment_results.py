import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = _get_columns()
	data, summary = _get_data(filters)
	chart = _get_chart(summary)
	return columns, data, None, chart, summary


def _get_columns():
	return [
		{
			"label": _("Full Name"),
			"fieldtype": "Data",
			"fieldname": "full_name",
			"width": 200,
		},
		{
			"label": _("Email"),
			"fieldtype": "Data",
			"fieldname": "email",
			"width": 230,
		},
		{
			"label": _("Status"),
			"fieldtype": "Data",
			"fieldname": "attempt_status",
			"width": 130,
		},
		{
			"label": _("Score"),
			"fieldtype": "Data",
			"fieldname": "score_display",
			"width": 90,
		},
		{
			"label": _("Percentage"),
			"fieldtype": "Percent",
			"fieldname": "percentage",
			"width": 110,
		},
		{
			"label": _("Pass / Fail"),
			"fieldtype": "Data",
			"fieldname": "pass_fail",
			"width": 100,
		},
		{
			"label": _("Submitted On"),
			"fieldtype": "Datetime",
			"fieldname": "submitted_on",
			"width": 160,
		},
	]


def _get_data(filters):
	# All users with profession = Research Assistant
	users = frappe.get_all(
		"User",
		filters={"profession": "Research Assistant", "enabled": 1},
		fields=["name", "full_name", "email"],
	)

	if not users:
		return [], []

	# Filter by name if provided
	if filters.get("user"):
		users = [u for u in users if u.name == filters["user"]]

	user_emails = [u.name for u in users]

	attempts = frappe.get_all(
		"ICHA Assessment Attempt",
		filters={"user": ["in", user_emails], "status": "Completed"},
		fields=["user", "score", "total_questions", "percentage", "passed", "submitted_on"],
	)
	attempt_map = {a.user: a for a in attempts}

	passed_count = 0
	failed_count = 0
	pending_count = 0
	rows = []

	for u in users:
		attempt = attempt_map.get(u.name)
		if attempt:
			passed = bool(attempt.passed)
			if passed:
				passed_count += 1
			else:
				failed_count += 1

			indicator = "green" if passed else "red"
			pass_fail_label = f"<span style='color:{'#28a745' if passed else '#dc3545'};font-weight:600'>{'Pass' if passed else 'Fail'}</span>"

			rows.append({
				"full_name": u.full_name,
				"email": u.email,
				"attempt_status": "Completed",
				"score_display": f"{attempt.score}/{attempt.total_questions}",
				"percentage": attempt.percentage,
				"pass_fail": "Pass" if passed else "Fail",
				"submitted_on": attempt.submitted_on,
			})
		else:
			pending_count += 1
			rows.append({
				"full_name": u.full_name,
				"email": u.email,
				"attempt_status": "Not Attempted",
				"score_display": "-",
				"percentage": None,
				"pass_fail": "-",
				"submitted_on": None,
			})

	# Apply pass_fail filter
	if filters.get("pass_fail"):
		f = filters["pass_fail"]
		if f == "Not Attempted":
			rows = [r for r in rows if r["attempt_status"] == "Not Attempted"]
		else:
			rows = [r for r in rows if r["pass_fail"] == f]

	# Sort: Pass first, then Fail, then Not Attempted; alphabetically within each group
	order = {"Pass": 0, "Fail": 1, "-": 2}
	rows.sort(key=lambda r: (order.get(r["pass_fail"], 2), r["full_name"]))

	total = len(rows)
	completed = passed_count + failed_count
	pass_rate = round((passed_count / completed) * 100, 1) if completed else 0

	summary = [
		{"label": _("Total Research Assistants"), "value": total, "datatype": "Int", "color": "#6c757d"},
		{"label": _("Completed"), "value": completed, "datatype": "Int", "color": "#007bff"},
		{"label": _("Passed"), "value": passed_count, "datatype": "Int", "color": "#28a745"},
		{"label": _("Failed"), "value": failed_count, "datatype": "Int", "color": "#dc3545"},
		{"label": _("Not Attempted"), "value": pending_count, "datatype": "Int", "color": "#ffc107"},
		{"label": _("Pass Rate"), "value": f"{pass_rate}%", "datatype": "Data", "color": "#17a2b8"},
	]

	return rows, summary


def _get_chart(summary):
	values = {s["label"]: s["value"] for s in summary}
	passed = values.get(_("Passed"), 0)
	failed = values.get(_("Failed"), 0)
	not_attempted = values.get(_("Not Attempted"), 0)

	return {
		"data": {
			"labels": [_("Passed"), _("Failed"), _("Not Attempted")],
			"datasets": [{"values": [passed, failed, not_attempted]}],
		},
		"type": "donut",
		"colors": ["#28a745", "#dc3545", "#ffc107"],
		"height": 280,
	}
