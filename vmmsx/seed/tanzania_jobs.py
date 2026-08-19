# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Real-shaped job openings for the Tanzania Red Cross Society, in HRMS.

Part of the Tanzania seed. `api/opportunities.py` (HR-01) reads the live
opportunities board from HRMS's own `Job Opening`, not from `VMMS Terms of
Reference` — Gambia's and Kenya's operations seeds predate that switch and
still create the older doctype pair. This module is the first seed in this
app to create `Job Opening` records, and the first to need HRMS's own
`Company`, `Department`, `Designation` and `Branch` as prerequisites, so it
creates those too rather than assuming an administrator already has.

**What is sourced, and what is a typical shape.** Two role types were found
genuinely advertised by TRCS while researching this seed: an IT Officer under
the Organizational Development department's PMERL unit in Dar es Salaam, and
Vocational Training Centre Supervisors in Shinyanga, Kigoma and Tabora. Those
four openings below are modelled on those real, published roles — titles,
department and duty stations are real, though the posting itself is redated
to look current rather than reproduced verbatim from an old listing. The
remaining two openings are a typical shape for TRCS's own published
department structure (Disaster Management; Health Services) rather than a
specific advertised vacancy, the same "worked example" label `tanzania.py`
gives its membership fees.

Idempotent, and it says what it did. Skips whole, gracefully, if HRMS is not
installed on the site — the same absence `vmmsx/hr/services/openings.py`
already tolerates at read time.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.seed import tanzania

COMPANY_NAME = tanzania.ORGANIZATION_NAME
COMPANY_ABBR = "TRCS"

DEPARTMENTS = (
	"Organizational Development",
	"Disaster Management",
	"Health Services",
)

DESIGNATIONS = (
	"IT Officer",
	"Vocational Training Centre Supervisor",
	"Disaster Risk Reduction Programme Officer",
	"Community Health Officer",
)

# HRMS's own Branch doctype — a different concept from the Geo Node regions
# above, and the one `location` on a Job Opening actually links to.
BRANCHES = ("Dar es Salaam", "Shinyanga", "Kigoma", "Tabora", "Mbeya", "Zanzibar")

# (key, title, designation, department, branch, employment_type, closes_in_days, description)
#
# `closes_in_days` is days from the day this seed runs, the same forward-dating
# `gambia_operations.py::EVENTS` uses for the diary, so the board never looks
# like nobody has touched it in months.
OPENINGS = (
	{
		"key": "it-officer-dar",
		"title": "IT Officer",
		"designation": "IT Officer",
		"department": "Organizational Development",
		"branch": "Dar es Salaam",
		"employment_type": "Contract",
		"closes_in": 30,
		"description": (
			"<p>Reporting to the Head of Planning, Monitoring, Evaluation, Reporting and Learning"
			" (PMERL) Unit within the Organizational Development department, the IT Officer"
			" maintains and enhances TRCS's network infrastructure, desk and field systems, and"
			" data security across the national headquarters and regional branches.</p>"
			"<p><strong>Duty station:</strong> Dar es Salaam. <strong>Contract:</strong> two years,"
			" renewable.</p>"
			"<ul>"
			"<li>Maintain and support network, hardware and software infrastructure at headquarters"
			" and regional branches.</li>"
			"<li>Support the PMERL unit's own data systems and reporting tools.</li>"
			"<li>Provide first-line IT support to headquarters staff and coordinate with regional"
			" branch focal points.</li>"
			"</ul>"
		),
	},
	{
		"key": "vtc-supervisor-shinyanga",
		"title": "Vocational Training Centre Supervisor, Shinyanga",
		"designation": "Vocational Training Centre Supervisor",
		"department": "Organizational Development",
		"branch": "Shinyanga",
		"employment_type": "Full-time",
		"closes_in": 21,
		"description": (
			"<p>Supervises day-to-day running of the TRCS vocational training centre in Shinyanga"
			" region: instructor coordination, enrolment, workshop safety and the centre's own"
			" record-keeping.</p>"
		),
	},
	{
		"key": "vtc-supervisor-kigoma",
		"title": "Vocational Training Centre Supervisor, Kigoma",
		"designation": "Vocational Training Centre Supervisor",
		"department": "Organizational Development",
		"branch": "Kigoma",
		"employment_type": "Full-time",
		"closes_in": 21,
		"description": (
			"<p>Supervises day-to-day running of the TRCS vocational training centre in Kigoma"
			" region: instructor coordination, enrolment, workshop safety and the centre's own"
			" record-keeping.</p>"
		),
	},
	{
		"key": "vtc-supervisor-tabora",
		"title": "Vocational Training Centre Supervisor, Tabora",
		"designation": "Vocational Training Centre Supervisor",
		"department": "Organizational Development",
		"branch": "Tabora",
		"employment_type": "Full-time",
		"closes_in": 21,
		"description": (
			"<p>Supervises day-to-day running of the TRCS vocational training centre in Tabora"
			" region: instructor coordination, enrolment, workshop safety and the centre's own"
			" record-keeping.</p>"
		),
	},
	{
		"key": "drr-programme-officer-mbeya",
		"title": "Disaster Risk Reduction Programme Officer",
		"designation": "Disaster Risk Reduction Programme Officer",
		"department": "Disaster Management",
		"branch": "Mbeya",
		"employment_type": "Contract",
		"closes_in": 25,
		"description": (
			"<p>Coordinates community-level disaster risk reduction and emergency response"
			" activities in Mbeya region, including the branch's ongoing flood response work in"
			" Rungwe, Kyela and Mbarali Districts.</p>"
		),
	},
	{
		"key": "community-health-officer-zanzibar",
		"title": "Community Health Officer",
		"designation": "Community Health Officer",
		"department": "Health Services",
		"branch": "Zanzibar",
		"employment_type": "Full-time",
		"closes_in": 28,
		"description": (
			"<p>Leads community-based health outreach in Zanzibar, including school, madrasa and"
			" market awareness sessions of the kind run during the Society's heatwave and albinism"
			" protection campaign.</p>"
		),
	},
)


def main(commit: bool = True) -> dict:
	if not frappe.db.exists("DocType", "Job Opening"):
		return {"job_openings": [{"key": "hrms", "status": "skipped: HRMS is not installed"}]}

	report = {
		"company": _company(),
		"departments": _departments(),
		"designations": _designations(),
		"branches": _branches(),
		"job_openings": _job_openings(),
	}

	if commit:
		frappe.db.commit()

	return report


def _company() -> list[dict]:
	if frappe.db.exists("Company", COMPANY_NAME):
		return [{"key": COMPANY_NAME, "status": "exists"}]

	rows = []

	# ERPNext's own `Company.on_update` creates a default warehouse tree,
	# including one typed "Transit" — a `Warehouse Type` record, not a literal.
	# This bench never ran ERPNext's setup wizard, which is what normally seeds
	# it, so the very first Company created on it fails with a link validation
	# error unless something creates that record first.
	if not frappe.db.exists("Warehouse Type", "Transit"):
		frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)
		rows.append({"key": "Warehouse Type Transit", "status": "created"})

	frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": COMPANY_NAME,
			"abbr": COMPANY_ABBR,
			"default_currency": tanzania.CURRENCY if frappe.db.exists("Currency", tanzania.CURRENCY) else "TZS",
			"country": tanzania.COUNTRY if frappe.db.exists("Country", tanzania.COUNTRY) else None,
		}
	).insert(ignore_permissions=True)

	rows.append({"key": COMPANY_NAME, "status": "created"})

	return rows


def _departments() -> list[dict]:
	rows = []

	for name in DEPARTMENTS:
		if frappe.db.exists("Department", {"department_name": name, "company": COMPANY_NAME}):
			rows.append({"key": name, "status": "exists"})
			continue

		frappe.get_doc(
			{"doctype": "Department", "department_name": name, "company": COMPANY_NAME}
		).insert(ignore_permissions=True)

		rows.append({"key": name, "status": "created"})

	return rows


def _designations() -> list[dict]:
	rows = []

	for name in DESIGNATIONS:
		if frappe.db.exists("Designation", name):
			rows.append({"key": name, "status": "exists"})
			continue

		frappe.get_doc({"doctype": "Designation", "designation_name": name}).insert(ignore_permissions=True)

		rows.append({"key": name, "status": "created"})

	return rows


def _branches() -> list[dict]:
	rows = []

	for name in BRANCHES:
		if frappe.db.exists("Branch", name):
			rows.append({"key": name, "status": "exists"})
			continue

		frappe.get_doc({"doctype": "Branch", "branch": name}).insert(ignore_permissions=True)

		rows.append({"key": name, "status": "created"})

	return rows


def _job_openings() -> list[dict]:
	rows = []

	for opening in OPENINGS:
		if frappe.db.exists("Job Opening", {"job_title": opening["title"], "location": opening["branch"]}):
			rows.append({"key": opening["key"], "status": "exists"})
			continue

		if not frappe.db.exists("Department", {"department_name": opening["department"], "company": COMPANY_NAME}):
			rows.append({"key": opening["key"], "status": f"skipped: no {opening['department']} department"})
			continue

		department = frappe.db.get_value(
			"Department", {"department_name": opening["department"], "company": COMPANY_NAME}, "name"
		)

		job = frappe.get_doc(
			{
				"doctype": "Job Opening",
				"job_title": opening["title"],
				"designation": opening["designation"],
				"company": COMPANY_NAME,
				"department": department,
				"location": opening["branch"],
				"employment_type": opening["employment_type"],
				"status": "Open",
				"posted_on": today(),
				"closes_on": add_days(today(), opening["closes_in"]),
				"description": opening["description"],
				"publish": 1,
				"publish_applications_received": 1,
			}
		)
		job.insert(ignore_permissions=True)

		rows.append({"key": opening["key"], "status": "created", "at": opening["branch"], "route": job.route})

	return rows
