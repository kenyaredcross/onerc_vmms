# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Kenya Red Cross Society opportunities board, in HRMS. Data, never behaviour.

    bench --site <site> execute vmmsx.seed.kenya_jobs.main

**Why this file has to exist at all.** `api/opportunities.py` (HR-01) reads the
live board from HRMS's own `Job Opening`, and `kenya_operations.py` predates that
switch — it seeds `VMMS Deployment Request`, which is the society's *internal*
record of needing people somewhere and has never been the board. So a
Kenya-seeded site had an Opportunities screen that worked perfectly and was
empty, which is the least useful thing a screen can be during acceptance
testing. This is the first Kenyan seed to create `Job Opening`, and therefore the
first to need HRMS's own `Company`, `Department`, `Designation` and `Branch`, so
it creates those too rather than assuming an administrator already has.

**Both kinds of post, because the board carries both.** `vmms_purpose`
distinguishes a **Volunteer** role — applied for through the volunteer portal by
somebody the society has already accepted — from **Employment**, which keeps
HRMS's ordinary public application behaviour untouched. A board with only jobs on
it never exercises the volunteering path, and a board with only volunteering
roles never exercises HRMS's. Eleven openings below: seven volunteering, four
employment.

**Every volunteering role is anchored at a county** through `vmms_geo_node`, the
same rule the rest of this society's records follow — see `_where` in
`kenya_operations.py` for why nothing is ever placed at a sub-county. HRMS's own
`location` links to its `Branch` doctype, which is a different concept from a Geo
Node and is the town the work is in; both are set, and they are not the same
field answering twice.

**What is a real posting and what is a typical shape.** KRCS advertises
professional posts of the kinds below — programme officers in disaster
management and health, county-level coordination, monitoring and evaluation —
and the departments named are its own. The four employment openings are modelled
on that published structure rather than reproduced from a live advertisement,
and the volunteering roles are the work its counties actually ask for. Nothing
here is a verbatim copy of a real vacancy, and every closing date is relative to
the day the seed runs, so the board never reads as though nobody has touched it
in months.

Idempotent, and it says what it did. Skips whole, gracefully, if HRMS is not
installed — the same absence `vmmsx/hr/services/openings.py` already tolerates
at read time.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.seed import kenya
from vmmsx.setup import job_opening_fields as opening_fields

OPENING_DOCTYPE = "Job Opening"
COMPANY_NAME = kenya.ORGANIZATION_NAME
COMPANY_ABBR = kenya.ORGANIZATION_SHORT_NAME

DEPARTMENTS = (
	"Disaster Management",
	"Health and Social Services",
	"Volunteer and Youth Development",
	"Planning, Monitoring and Evaluation",
)

DESIGNATIONS = (
	"County Volunteer Coordinator",
	"Emergency Response Team Member",
	"Community Health Volunteer",
	"First Aid Trainer",
	"Blood Donor Recruiter",
	"Psychosocial Support Volunteer",
	"Youth Programme Assistant",
	"Disaster Risk Reduction Officer",
	"Monitoring and Evaluation Officer",
	"Community Health Officer",
	"Logistics Officer",
)

# HRMS's own `Branch` doctype — the town the work is in, and a different concept
# from the Geo Node the post is owned by. Named for the offices KRCS actually
# runs rather than for the counties, because that is what this field is for.
BRANCHES = ("Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Garissa", "Lodwar", "Kakamega")

VOLUNTEER = opening_fields.PURPOSE_VOLUNTEER
EMPLOYMENT = opening_fields.PURPOSE_EMPLOYMENT

# (key, title, designation, department, branch, county, purpose, opening_type,
#  vacancies, employment_type, closes_in, description)
#
# `county` is resolved through `kenya.county_named` rather than stored as a
# docname: Geo Node names are opaque (`GEO-.#####`) and a second bench numbers
# them differently. `closes_in` is days from the day this seed runs.
OPENINGS = (
	# --- volunteering ------------------------------------------------------
	{
		"key": "ert-nairobi",
		"title": "Emergency Response Team Member, Nairobi",
		"designation": "Emergency Response Team Member",
		"department": "Disaster Management",
		"branch": "Nairobi",
		"county": "Nairobi",
		"purpose": VOLUNTEER,
		"opening_type": "Internal",
		"vacancies": 24,
		"employment_type": "Part-time",
		"closes_in": 30,
		"description": (
			"<p>Nairobi is building its emergency response roster back up to 60 trained members"
			" across the county's 17 sub-counties. Members are called out to fires, building"
			" collapses, road traffic collisions and displacement, and are expected to be"
			" reachable on a rota rather than on every incident.</p>"
			"<p><strong>What you will do</strong></p>"
			"<ul>"
			"<li>Respond on a published two-week rota, with a named reserve behind you.</li>"
			"<li>Run first aid, casualty handling and family reunification at the scene.</li>"
			"<li>Set up and staff a reception centre, including the registration desk that"
			" everything else depends on.</li>"
			"<li>Log your hours against the response, which is how the county knows what a"
			" response actually cost.</li>"
			"</ul>"
			"<p><strong>What you need</strong></p>"
			"<ul>"
			"<li>A current first aid certificate, or a place booked on the next sitting.</li>"
			"<li>Availability you can genuinely keep — two weekends a month is worth more here"
			" than every weekend for two months.</li>"
			"<li>To be an accepted volunteer of the society. Apply to volunteer first if you"
			" are not one yet.</li>"
			"</ul>"
			"<p><strong>What you get</strong> Full ERT training, personal protective equipment,"
			" and a debrief after every call-out you attend.</p>"
		),
	},
	{
		"key": "chv-kilifi",
		"title": "Community Health Volunteer, Kilifi",
		"designation": "Community Health Volunteer",
		"department": "Health and Social Services",
		"branch": "Mombasa",
		"county": "Kilifi",
		"purpose": VOLUNTEER,
		"opening_type": "Internal",
		"vacancies": 40,
		"employment_type": "Part-time",
		"closes_in": 45,
		"description": (
			"<p>The least dramatic work the society does and the largest part of it. Each"
			" community health volunteer holds a register of around 200 households and visits"
			" them twice a month.</p>"
			"<p><strong>What you will do</strong></p>"
			"<ul>"
			"<li>Weigh and measure children under five, and refer anybody falling off their"
			" growth chart to the dispensary.</li>"
			"<li>Track immunisations, mosquito net use and household water treatment.</li>"
			"<li>Keep the household register current, which is the whole of the job's value.</li>"
			"</ul>"
			"<p><strong>What you need</strong> To live in the sub-county you would cover, and"
			" two mornings a fortnight you can keep for two years rather than two months. No"
			" clinical background is required; the training is provided and takes two days.</p>"
			"<p>Nothing here is resolved and nothing is closed. A household is not a case; it is"
			" a household you will see again in a fortnight.</p>"
		),
	},
	{
		"key": "first-aid-trainer-national",
		"title": "First Aid Trainer (volunteer instructor)",
		"designation": "First Aid Trainer",
		"department": "Health and Social Services",
		"branch": "Nairobi",
		"county": "Nairobi",
		"purpose": VOLUNTEER,
		"opening_type": "Internal",
		"vacancies": 8,
		"employment_type": "Part-time",
		"closes_in": 38,
		"description": (
			"<p>The society trains more people in first aid than it could ever employ"
			" instructors for, which is why most of its instructors are volunteers who already"
			" hold the qualification and want to teach it.</p>"
			"<p><strong>What you will do</strong> Deliver the two-day certificate at"
			" headquarters and in counties that ask for a sitting; assess candidates on the"
			" second afternoon; keep your own instructor qualification current.</p>"
			"<p><strong>What you need</strong> A current first aid certificate held for at least"
			" two years, and the instructor course, which the society runs twice a year and will"
			" put you through.</p>"
			"<p>Expect roughly two sittings a quarter. Teaching sixteen-year-olds is, by common"
			" agreement among the current instructors, harder than any incident any of them has"
			" attended.</p>"
		),
	},
	{
		"key": "psychosocial-kisumu",
		"title": "Psychosocial Support Volunteer, Kisumu",
		"designation": "Psychosocial Support Volunteer",
		"department": "Health and Social Services",
		"branch": "Kisumu",
		"county": "Kisumu",
		"purpose": VOLUNTEER,
		"opening_type": "Internal",
		"vacancies": 12,
		"employment_type": "Part-time",
		"closes_in": 33,
		"description": (
			"<p>Kisumu has two people trained to run the first-hour conversation with somebody"
			" who has just come off a scene, and it needs more. This role is as much about"
			" supporting the society's own volunteers as the communities they work in.</p>"
			"<p><strong>What you will do</strong></p>"
			"<ul>"
			"<li>Provide psychological first aid at incidents and in reception centres.</li>"
			"<li>Run post-incident debriefs for response teams, including the awkward hour"
			" afterwards when there is nothing left to do.</li>"
			"<li>Refer on, to services that can carry what you cannot.</li>"
			"</ul>"
			"<p><strong>What you need</strong> The psychological first aid course, which the"
			" society provides, and the judgement to know the difference between listening and"
			" counselling. A background in social work, education, counselling or nursing helps"
			" and is not required.</p>"
		),
	},
	{
		"key": "blood-recruiter-mombasa",
		"title": "Blood Donor Recruiter, Mombasa",
		"designation": "Blood Donor Recruiter",
		"department": "Health and Social Services",
		"branch": "Mombasa",
		"county": "Mombasa",
		"purpose": VOLUNTEER,
		"opening_type": "Internal",
		"vacancies": 15,
		"employment_type": "Part-time",
		"closes_in": 27,
		"description": (
			"<p>Mombasa runs mobile blood drives with the Kenya National Blood Transfusion"
			" Service most weekends, and every one of them lives or dies on how many people"
			" were spoken to during the week before it.</p>"
			"<p><strong>What you will do</strong> Recruit donors in colleges, workplaces,"
			" mosques and churches; staff the reception and registration desks on the day;"
			" follow up first-time donors so that they come back a second time, which is the"
			" number the service actually cares about.</p>"
			"<p><strong>What you need</strong> To be comfortable approaching strangers and"
			" answering the same four questions about eligibility all day. Training is half a"
			" day. Screening desk goes first, before registration — you will be told why on"
			" your first drive.</p>"
		),
	},
	{
		"key": "youth-assistant-nakuru",
		"title": "Youth Programme Assistant, Nakuru",
		"designation": "Youth Programme Assistant",
		"department": "Volunteer and Youth Development",
		"branch": "Nakuru",
		"county": "Nakuru",
		"purpose": VOLUNTEER,
		"opening_type": "Internal",
		"vacancies": 6,
		"employment_type": "Part-time",
		"closes_in": 41,
		"description": (
			"<p>Supporting the county's school and college links: first aid clubs, road safety"
			" talks, and the annual county show duty that nine out of twelve volunteers are"
			" doing for the first time.</p>"
			"<p><strong>What you will do</strong> Run sessions in schools; coordinate the club"
			" leads across the county; pair every first-time volunteer on public event duty with"
			" somebody who is not, which is the only reason a busy first aid post runs"
			" calmly.</p>"
			"<p><strong>What you need</strong> To be between 18 and 30, to hold or be willing to"
			" take the first aid certificate, and to have sat the safeguarding session — which"
			" is required annually of every volunteer and is listed under events.</p>"
		),
	},
	{
		"key": "wash-turkana",
		"title": "Water and Sanitation Volunteer, Turkana",
		"designation": "Emergency Response Team Member",
		"department": "Disaster Management",
		"branch": "Lodwar",
		"county": "Turkana",
		"purpose": VOLUNTEER,
		"opening_type": "Internal",
		"vacancies": 20,
		"employment_type": "Part-time",
		"closes_in": 36,
		"description": (
			"<p>Turkana's drought response ran for eleven months and its own hour logs showed"
			" the problem plainly: nine people were staffing the water distribution points and"
			" four of them stopped. This recruitment is the answer to that number.</p>"
			"<p><strong>What you will do</strong> Staff water treatment and distribution points"
			" on fixed two-week blocks published a month ahead; run household hygiene promotion;"
			" monitor and report water quality at the point of distribution.</p>"
			"<p><strong>What you need</strong> The water and sanitation certificate, or a place"
			" on the refresher listed under events. Two sub-counties are barely covered at all,"
			" so applications from Turkana North and Turkana East are particularly wanted.</p>"
			"<p><strong>How this one is rostered</strong> No volunteer is put on more than two"
			" blocks in a row without being asked, and every long response gets a named deputy"
			" from the start. Both of those are lessons from the last one.</p>"
		),
	},
	# --- employment --------------------------------------------------------
	{
		"key": "drr-officer-garissa",
		"title": "Disaster Risk Reduction Officer, Garissa",
		"designation": "Disaster Risk Reduction Officer",
		"department": "Disaster Management",
		"branch": "Garissa",
		"county": "Garissa",
		"purpose": EMPLOYMENT,
		"opening_type": "Guest",
		"vacancies": 1,
		"employment_type": "Contract",
		"closes_in": 21,
		"description": (
			"<p>Reporting to the County Coordinator, the officer leads community-level disaster"
			" risk reduction and flood preparedness across Garissa's six sub-counties, including"
			" the pre-positioned volunteer register that made the last Tana flood response"
			" measurably faster.</p>"
			"<p><strong>Duty station</strong> Garissa. <strong>Contract</strong> two years,"
			" renewable.</p>"
			"<ul>"
			"<li>Lead county contingency planning with the county government and the National"
			" Drought Management Authority.</li>"
			"<li>Keep the county's trained volunteer register current by sub-county, and report"
			" coverage gaps as recruitment questions with numbers attached.</li>"
			"<li>Coordinate early warning dissemination and community-based early action.</li>"
			"</ul>"
			"<p><strong>Requirements</strong> A degree in disaster management, environmental"
			" science, development studies or a related field; at least four years in emergency"
			" programming; fluent Somali and Kiswahili.</p>"
		),
	},
	{
		"key": "county-coordinator-kakamega",
		"title": "County Volunteer Coordinator, Kakamega",
		"designation": "County Volunteer Coordinator",
		"department": "Volunteer and Youth Development",
		"branch": "Kakamega",
		"county": "Kakamega",
		"purpose": EMPLOYMENT,
		"opening_type": "Guest",
		"vacancies": 1,
		"employment_type": "Full-time",
		"closes_in": 24,
		"description": (
			"<p>The person who decides on every volunteer application filed in Kakamega and its"
			" twelve sub-counties, and who is accountable for the county's volunteer register"
			" being accurate.</p>"
			"<p><strong>What the job actually is</strong> Reviewing applications is most of it"
			" and almost none of the conversation about it — around forty a week in a county"
			" this size, of which the great majority are straightforward and take four minutes."
			" The rest is rostering, chasing lapsed certifications, and recruitment in the"
			" sub-counties the register shows are thin.</p>"
			"<ul>"
			"<li>Approve, refuse or return volunteer applications, with the reason written on"
			" the ones you return so the applicant can fix what is wrong and resubmit.</li>"
			"<li>Maintain the county register: placements, availability, certifications.</li>"
			"<li>Staff deployments and public event duty from that register.</li>"
			"<li>Handle guardian consent for applicants under 18, and transfers in and out.</li>"
			"</ul>"
			"<p><strong>Requirements</strong> A degree in social sciences, community development"
			" or a related field; at least three years managing volunteers; the judgement to know"
			" that if you can say what is missing from a form you have no business rejecting"
			" somebody for it.</p>"
		),
	},
	{
		"key": "me-officer-nairobi",
		"title": "Monitoring and Evaluation Officer",
		"designation": "Monitoring and Evaluation Officer",
		"department": "Planning, Monitoring and Evaluation",
		"branch": "Nairobi",
		"county": "Nairobi",
		"purpose": EMPLOYMENT,
		"opening_type": "Guest",
		"vacancies": 2,
		"employment_type": "Contract",
		"closes_in": 18,
		"description": (
			"<p>Based at headquarters, working across all 47 county registers. The post exists"
			" because of a finding: turnover is invisible in a situation report and obvious in an"
			" hour log, and nobody was reading the hour logs.</p>"
			"<ul>"
			"<li>Design and run monitoring for national programmes, with indicators that can"
			" actually be collected by a volunteer on a phone.</li>"
			"<li>Analyse volunteer hours, retention and certification currency by county and"
			" sub-county, and put the findings in front of the people who staff rotas.</li>"
			"<li>Support county coordinators to read their own data rather than to send it"
			" somewhere.</li>"
			"</ul>"
			"<p><strong>Requirements</strong> A degree in statistics, economics, public health or"
			" a related field; at least three years in monitoring and evaluation in the"
			" humanitarian or public sector; genuine competence in a statistical package.</p>"
		),
	},
	{
		"key": "logistics-officer-eldoret",
		"title": "Logistics Officer, Rift Valley",
		"designation": "Logistics Officer",
		"department": "Disaster Management",
		"branch": "Eldoret",
		"county": "Uasin Gishu",
		"purpose": EMPLOYMENT,
		"opening_type": "Guest",
		"vacancies": 1,
		"employment_type": "Full-time",
		"closes_in": 15,
		"description": (
			"<p>Warehousing, fleet and pre-positioned stock for the Rift Valley counties, out of"
			" Eldoret. The post covers procurement, stock rotation and the dispatch that turns a"
			" contingency plan into blankets in a hall at midnight.</p>"
			"<ul>"
			"<li>Manage the regional warehouse and pre-positioned non-food item stock.</li>"
			"<li>Run the fleet, including response vehicle readiness and driver rosters.</li>"
			"<li>Support county teams on procurement and on the paperwork that follows a"
			" dispatch.</li>"
			"</ul>"
			"<p><strong>Requirements</strong> A diploma or degree in supply chain management or"
			" logistics; at least three years in humanitarian logistics; a clean driving"
			" licence.</p>"
		),
	},
)


def main(commit: bool = True) -> dict:
	"""Seed the opportunities board and report what changed. Safe to re-run."""
	if not frappe.db.exists("DocType", OPENING_DOCTYPE):
		report = {"job_openings": [{"key": "hrms", "status": "skipped: HRMS is not installed"}]}
		_print(report)
		return report

	report = {
		"company": _company(),
		"departments": _departments(),
		"designations": _designations(),
		"branches": _branches(),
		"job_openings": _openings(),
	}

	if commit:
		frappe.db.commit()

	_print(report)

	return report


def _company() -> list[dict]:
	"""One `Company`, because a national society is one legal entity.

	The 47 counties are Geo Nodes, not Companies — see `vmms_geo_node`'s own
	description on `Job Opening`, which says exactly that.
	"""
	if frappe.db.exists("Company", COMPANY_NAME):
		return [{"key": COMPANY_NAME, "status": "exists"}]

	rows = []

	# ERPNext's own `Company.on_update` creates a default warehouse tree,
	# including one typed "Transit" — a `Warehouse Type` record, not a literal.
	# A bench that never ran ERPNext's setup wizard has no such record, which is
	# what normally seeds it, so the very first Company created on it fails with
	# a link validation error unless something creates it first. Lifted from
	# `tanzania_jobs.py`, where it was found the hard way.
	if not frappe.db.exists("Warehouse Type", "Transit"):
		frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)
		rows.append({"key": "Warehouse Type Transit", "status": "created"})

	frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": COMPANY_NAME,
			"abbr": COMPANY_ABBR,
			"default_currency": kenya.CURRENCY if frappe.db.exists("Currency", kenya.CURRENCY) else "KES",
			"country": kenya.COUNTRY if frappe.db.exists("Country", kenya.COUNTRY) else None,
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

		frappe.get_doc({"doctype": "Department", "department_name": name, "company": COMPANY_NAME}).insert(
			ignore_permissions=True
		)

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
	"""HRMS's `Branch` — the town, not the Geo Node. See the note above `BRANCHES`."""
	rows = []

	for name in BRANCHES:
		if frappe.db.exists("Branch", name):
			rows.append({"key": name, "status": "exists"})
			continue

		frappe.get_doc({"doctype": "Branch", "branch": name}).insert(ignore_permissions=True)

		rows.append({"key": name, "status": "created"})

	return rows


def _openings() -> list[dict]:
	"""Published, open job openings — both purposes.

	`publish` and `status` are HRMS's two flags and the board reads both: vmmsx
	invents no third notion of visibility, so an opening has to be published
	*and* open to appear. `route` is left for HRMS to generate; a seed writing
	that field would be this app deciding another app's URLs.
	"""
	rows = []

	for opening in OPENINGS:
		if frappe.db.exists(OPENING_DOCTYPE, {"job_title": opening["title"]}):
			rows.append({"key": opening["key"], "status": "exists"})
			continue

		department = frappe.db.get_value(
			"Department", {"department_name": opening["department"], "company": COMPANY_NAME}, "name"
		)

		if not department:
			rows.append({"key": opening["key"], "status": f"skipped: no {opening['department']} department"})
			continue

		node = kenya.county_named(opening["county"])

		if not node:
			rows.append({"key": opening["key"], "status": f"skipped: {opening['county']} not seeded"})
			continue

		job = frappe.get_doc(
			{
				"doctype": OPENING_DOCTYPE,
				"job_title": opening["title"],
				"designation": opening["designation"],
				"company": COMPANY_NAME,
				"department": department,
				"location": opening["branch"],
				"employment_type": opening["employment_type"],
				"vacancies": opening["vacancies"],
				"status": "Open",
				"posted_on": today(),
				"closes_on": add_days(today(), opening["closes_in"]),
				"description": opening["description"],
				"publish": 1,
				"publish_applications_received": 1,
				# vmmsx's own two, and the reason this board carries both kinds of
				# post. `opportunity_type` is mandatory on the doctype.
				"opportunity_type": opening["opening_type"],
				opening_fields.PURPOSE_FIELD: opening["purpose"],
				"vmms_geo_node": node,
			}
		)
		job.insert(ignore_permissions=True)

		rows.append(
			{
				"key": opening["key"],
				"status": "created",
				"purpose": opening["purpose"],
				"at": opening["county"],
				"route": job.route or "none",
			}
		)

	return rows


def _print(report: dict) -> None:
	print(f"\nKenya Red Cross Society opportunities board on {frappe.local.site}\n" + "=" * 62)

	for section, rows in report.items():
		print(f"\n{section.replace('_', ' ').title()}")

		for row in rows:
			extra = " ".join(f"{k}={v}" for k, v in row.items() if k not in ("key", "status"))
			print(f"  [{row['status']:<8}] {row['key']}{'  ' + extra if extra else ''}")

	print()
