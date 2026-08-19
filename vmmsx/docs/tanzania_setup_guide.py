# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A from-scratch setup, content and dry-run guide, using Tanzania Red Cross as
the real worked example.

    bench --site vmms.localhost execute vmmsx.docs.tanzania_setup_guide.main

Modelled on `gambia_setup_guide.py`'s shape — assume nothing, write against
real field names verified on a live site, one day's work top to bottom — with
two differences. First, this one opens with Part 0: the commands that take a
brand-new bench with no site at all to the point Part 1 can start, because
"set up a new site from scratch" was the explicit ask this guide answers.
Second, it adds a part Gambia's guide could not have: bringing the site to
life with real content — Buzz events, HRMS job openings and sourced news
stories — none of which existed as a seeded feature when that guide was
written.

Every command in this guide was actually run against `vmms.localhost` while
writing it — including the two failures worth knowing about in advance (a
route collision from reusing one job title across three locations, and
ERPNext's first-ever Company insert needing a `Warehouse Type` record nobody
had reason to create yet) — not typed from memory.

Written to `docs/`, which is git-ignored, exactly like the other two artefacts.
"""

from datetime import datetime
from pathlib import Path

from vmmsx.docs.writer import Writer

APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = APP_ROOT / "docs" / "tanzania-red-cross-setup-guide.docx"

TITLE = "Tanzania Red Cross Society"
SUBTITLE = "VMMS Setup, Content & Dry-Run Guide"

BLURB = (
	"From an empty bench to a site that looks lived-in: society setup, real events, real job"
	" openings, real sourced stories, and a dry run of the two ways in — member and volunteer."
	" Part 0 is the part most guides skip: the commands that get you a site to configure at all."
)

SITE = "vmms.localhost"

# --- the worked Tanzania configuration, named once and used throughout ----

ORG_NAME = "Tanzania Red Cross Society"
ORG_SHORT = "TRCS"
COUNTRY = "Tanzania"
CURRENCY = "TZS"
LANGUAGE = "sw (Swahili)"

LEVEL_NATIONAL = "National"
LEVEL_REGION = "Region"

NATIONAL_NODE = ORG_NAME
REGION_COUNT = 31
DEMO_REGION = "Dar es Salaam"

ROLE_APPLICANT = "Society Applicant"
ROLE_VOLUNTEER = "Volunteer"
ROLE_MEMBER = "Member"
ROLE_VOL_APPROVER = "Volunteer Approver"
ROLE_MEM_APPROVER = "Membership Approver"
ROLE_COORDINATOR = "Branch Coordinator"
ROLE_DEPLOYMENT = "Deployment Manager"
ROLE_STIPEND = "Stipend Manager"

APPROVER_NAME = "Amina Mwakalinga"
APPROVER_USER = "approver@trcs.demo"
APPROVER_PASSWORD = "trcs-demo-2026"

TYPE_YOUTH = "Youth Member"
TYPE_ORDINARY = "Ordinary Member"
TYPE_LIFE = "Life Member"

CERT_TEMPLATE = "membership_certificate"

MEMBER_NAME = "Grace Mushi"
VOLUNTEER_NAME = "Baraka Kimaro"


def main(path: str | None = None, site: str | None = None) -> str:
	target = Path(path) if path else OUTPUT
	generated_on = datetime.now().strftime("%d %B %Y")

	collected = _render(generated_on, site or SITE, outline=None).outline
	writer = _render(generated_on, site or SITE, outline=collected)

	target.parent.mkdir(parents=True, exist_ok=True)
	writer.doc.save(str(target))

	return str(target)


def _render(generated_on: str, site: str, outline: list | None) -> Writer:
	w = Writer()

	w.cover(
		TITLE,
		SUBTITLE,
		[
			("Generated", generated_on),
			("Site used to verify every field and command", site),
			("Built from", "vmmsx/docs/tanzania_setup_guide.py — regenerate, do not edit the .docx"),
			("Scope", "Part 0: fresh bench. Part 1: society setup. Part 2: content. Part 3: dry run. Part 4: the shortcut."),
			("Depends on", "onerc_core (required). onerc_payments, buzz, hrms are optional, per feature."),
		],
		blurb=BLURB,
	)

	if outline is not None:
		w.contents(outline)

	_part0_intro(w)
	_p0_new_site(w, site)
	_p0_apps(w, site)
	w.page_break()

	_part1_intro(w)
	_p1_settings(w, site)
	_p1_geo(w)
	_p1_roles_assignments(w, site)
	_p1_membership_types(w)
	_p1_workflows(w)
	_p1_workspaces(w, site)
	_p1_enable_signup(w)
	w.page_break()

	_part2_intro(w)
	_p2_events(w, site)
	_p2_jobs(w, site)
	_p2_stories(w, site)
	w.page_break()

	_part3_intro(w)
	_p3_member(w, site)
	_p3_volunteer(w, site)
	_p3_browse(w, site)
	w.page_break()

	_part4(w, site)
	w.page_break()

	_not_built(w)
	w.page_break()
	_checklist(w, site)

	return w


# ============================================================================
# PART 0 — A FRESH BENCH TO A SITE YOU CAN CONFIGURE
# ============================================================================


def _part0_intro(w) -> None:
	w.h1("Part 0 — From a Fresh Bench to a Site You Can Configure")
	w.lead(
		"Everything here happens once, before there is a National Society Settings record to open."
		" If a site already exists with vmmsx installed and migrated, skip to Part 1."
	)


def _p0_new_site(w, site: str) -> None:
	w.h2("Create the site")

	w.p("From inside an existing bench directory (bench init is its own, longer, one-time step):")
	w.code(
		f"bench new-site {site} --db-root-password <root-password>\n"
		f"bench --site {site} set-config developer_mode 1   # optional, useful while configuring"
	)
	w.note(
		"A site is a database plus a sites/SITE-NAME folder. Nothing below this line is app-specific"
		" — the same two commands apply whatever the society's name will turn out to be."
	)


def _p0_apps(w, site: str) -> None:
	w.h2("Install the apps, in dependency order")

	w.table(
		("App", "Why", "Required?"),
		[
			["frappe", "the framework every site already has", "always"],
			["onerc_core", "Geo Level, Geo Node, Geo Assignment, National Society Settings, Article", "yes — vmmsx declares it in required_apps"],
			["vmmsx", "everything this guide configures", "yes"],
			["onerc_payments", "collects a membership fee; the Manual driver needs no credentials", "no, but Part 1's membership types assume it"],
			["erpnext, hrms", "Company, Department, Designation, Branch, Job Opening — Part 2's job board", "no — skip if the society will not publish job openings"],
			["buzz", "Buzz Event — Part 2's events calendar", "no — skip if the society will not publish events"],
			["onerc_sms", "the SMS campaign door on the admin console", "no"],
		],
		(1.35, 3.55, 1.60),
	)

	w.code(
		f"bench --site {site} install-app onerc_core\n"
		f"bench --site {site} install-app vmmsx\n"
		f"bench --site {site} install-app onerc_payments\n"
		f"bench --site {site} install-app erpnext\n"
		f"bench --site {site} install-app hrms\n"
		f"bench --site {site} install-app buzz\n"
		f"bench --site {site} migrate"
	)

	w.note(
		"migrate matters even when nothing above just changed: it is what runs every after_migrate"
		" step this app owns — the six core roles (vmmsx.setup.core_roles.install), the VMMS desk"
		" workspace cluster, the self-service workspaces, and the shipped content-block defaults."
		" Run it again any time a setting below does not seem to have taken effect."
	)
	w.note(
		"erpnext is a real dependency of hrms, not an accident above — hrms's Job Opening doctype"
		" links to erpnext's Company, Department and Designation, and none of the three exists on a"
		" site that has never installed erpnext."
	)
	w.note(
		"The very first Company record created on a bench that never ran ERPNext's setup wizard can"
		" fail with \"Could not find Warehouse Type: Transit\" — ERPNext's own on_update handler"
		" builds a default warehouse tree, one branch of which is typed \"Transit\", and nothing"
		" seeded that Warehouse Type record. This guide's own job-openings seed"
		" (tanzania_jobs.py::_company) creates it first for exactly this reason; if configuring by"
		" hand instead, create a Warehouse Type named Transit before the society's first Company."
	)


# ============================================================================
# PART 1 — SOCIETY SETUP
# ============================================================================


def _part1_intro(w) -> None:
	w.h1("Part 1 — Society Setup")
	w.lead(
		"Everything here is done once, by an administrator with System Manager, before anybody"
		" registers. Order matters: roles before Geo Assignments and workflows that name one, Geo"
		" Levels before Geo Nodes, both before National Society Settings' Validation tab."
	)


def _p1_settings(w, site: str) -> None:
	w.h2("National Society Settings")

	w.p(
		"A Single doctype — one record, no list. Desk > VMMS > VMMS Setup > National Society"
		f" Settings, or http://{site}/app/national-society-settings directly."
	)

	w.h3("Society tab — required to save at all")
	w.table(
		("Field", "Value for Tanzania"),
		[
			["Organization Name", ORG_NAME],
			["Organization Short Name", ORG_SHORT],
			["Country", f'{COUNTRY} — Link to Country, must already exist (it does)'],
			["Primary Language", LANGUAGE],
			["Logo", "upload the society mark (Attach Image) — none ships with this seed, see the note below"],
		],
		(2.20, 4.30),
	)
	w.note(
		"No TRCS logo file is committed to this repository — unlike Gambia's and Kenya's seeds,"
		" which each ship a real mark under public/images/seed_SOCIETY/. Uploading the real crest"
		" here is the first manual step on a Tanzania site, and every certificate this society issues"
		" renders correctly but with a blank space where it belongs until somebody does."
	)

	w.h3("Locale tab")
	w.table(("Field", "Value"), [["Currency", f"{CURRENCY} — Tanzanian Shilling"]], (2.20, 4.30))

	w.h3("Validation tab — the vmms_* settings")
	w.lead(
		"Every field below is reqd=0 in the schema, which is exactly what makes this tab dangerous:"
		" it saves happily blank, and blank means CLOSED for most of these, not unrestricted."
	)
	w.table(
		("Setting", "Value for Tanzania", "Blank means"),
		[
			["Volunteer Scope Role", ROLE_VOL_APPROVER, "FAIL-CLOSED. Nobody but Administrator reads a VMMS Volunteer record."],
			["Volunteer Self-Service Role", ROLE_VOLUNTEER, "an accepted volunteer's login is granted nothing."],
			["Membership Scope Role", ROLE_MEM_APPROVER, "FAIL-CLOSED. Nobody but Administrator reads a VMMS Membership record."],
			["Member Self-Service Role", ROLE_MEMBER, "an active member's login is granted nothing."],
			["Certificate Print Role", ROLE_MEM_APPROVER, "literally nobody but the member themself may print a certificate."],
			["Self-Registration Role", ROLE_APPLICANT, "FAIL-CLOSED. The Registration workspace is never built."],
			["Announcement / Task / Content Editor / Branch Location Scope Role", ROLE_COORDINATOR, "each fails closed independently — see the note below."],
			["Deployment / Deployment Request / Branch Transfer Scope Role", ROLE_DEPLOYMENT, "fails closed the same way."],
			["Stipend Report / Payment Scope Role", ROLE_STIPEND, "fails closed the same way."],
		],
		(2.10, 1.60, 2.70),
	)
	w.note(
		"None of these role names exist yet on a fresh site — create the eight roles in the next"
		" section first, then come back and fill in this tab. A Link field refuses a role that does"
		" not already exist; it will not accept one by typo."
	)


def _p1_geo(w) -> None:
	w.h2("Geo Levels and Geo Nodes")

	w.p("Desk > VMMS > VMMS Setup > Geo Level, then New. Create exactly two, in this order:")
	w.steps(
		[
			f'Geo Level Name "{LEVEL_NATIONAL}", Geo Level Key "trcs-national". Order 1. Leave Is Lowest'
			" Level and Requires Parent both unchecked.",
			f'Geo Level Name "{LEVEL_REGION}", Geo Level Key "trcs-region". Order 2. Check Requires'
			" Parent and check Is Lowest Level.",
		]
	)
	w.note(
		"Two rungs, not three or four. TRCS's own published figures say 31+ regional branches and"
		" 1,250+ sub-branches, but the sub-branches are not named anywhere public — this guide does"
		" not invent 1,250 names to fill a third level, the same restraint the Gambia seed takes with"
		" people it has no register for. A society that has its own sub-branch list adds a third Geo"
		" Level (Requires Parent checked, Is Lowest Level moved onto it) and files each sub-branch"
		" under its region."
	)

	w.h2(f"Geo Nodes — the national root and {REGION_COUNT} regions")
	w.p(
		f'Desk > VMMS > VMMS Setup > Geo Node, then New. One root, "{NATIONAL_NODE}", Geo Level'
		" National, no parent. Then one node per region, Geo Level Region, parent the national root —"
		" Tanzania's own administrative regions, all 31 of them, mainland and Zanzibar:"
	)
	w.p(
		"Arusha, Dar es Salaam, Dodoma, Geita, Iringa, Kagera, Katavi, Kigoma, Kilimanjaro, Lindi,"
		" Manyara, Mara, Mbeya, Morogoro, Mtwara, Mwanza, Njombe, Pwani, Rukwa, Ruvuma, Shinyanga,"
		" Simiyu, Singida, Songwe, Tabora, Tanga — the 26 mainland regions — plus Kaskazini Unguja,"
		" Kusini Unguja, Mjini Magharibi, Kaskazini Pemba and Kusini Pemba in Zanzibar."
	)
	w.note(
		"31 regions is also TRCS's own published branch count — one regional branch per region is the"
		" real structure, not a subset chosen for a shorter guide. tanzania.py::REGIONS in the seed"
		" carries the same 31 names as a tuple, so a tree built by hand here should match it exactly."
	)


def _p1_roles_assignments(w, site: str) -> None:
	w.h2("Roles and Geo Assignments — who can approve, and where")

	w.h3("Create the roles")
	w.p("Desk > Role List > New, for each of these eight:")
	w.table(
		("Role", "What it is for"),
		[
			[ROLE_APPLICANT, "held by a brand-new self-registered account, until approved as anything"],
			[ROLE_VOLUNTEER, "granted automatically when a volunteer becomes Active"],
			[ROLE_MEMBER, "granted automatically when a membership becomes Active"],
			[ROLE_VOL_APPROVER, "the approver role a Volunteer Application workflow stage names"],
			[ROLE_MEM_APPROVER, "the approver role the Membership workflow stage names, and the certificate print role"],
			[ROLE_COORDINATOR, "runs a region: tasks, announcements, offices and page content"],
			[ROLE_DEPLOYMENT, "sends people out: deployments, deployment requests, branch transfers"],
			[ROLE_STIPEND, "handles stipend paperwork"],
		],
		(2.30, 4.20),
	)
	w.note(
		f"The first six of these are created automatically on every migrate by"
		" vmmsx.setup.core_roles.install (an after_migrate step) — a fresh site already has them the"
		f" moment vmmsx is installed. Only {ROLE_COORDINATOR} and {ROLE_STIPEND} still need creating"
		" by hand, or by tanzania.py's own _roles() step."
	)

	w.h3("Create the demo approver")
	w.p(
		f"Desk > User List > New: {APPROVER_NAME}, email {APPROVER_USER}. Give the account"
		f" {ROLE_VOL_APPROVER}, {ROLE_MEM_APPROVER} and {ROLE_COORDINATOR} on the Roles tab. Set a"
		" password:"
	)
	w.code(f"bench --site {site} set-password {APPROVER_USER} {APPROVER_PASSWORD}")
	w.note(
		f'This account, at this password, already exists on {site} — it is the demo approver'
		" tanzania.py::place_approver() creates. Signing in as them is the fastest way to see the"
		" admin console without configuring anything else first."
	)

	w.h3('Geo Assignment — the "where" half')
	w.lead(
		f"Holding {ROLE_VOL_APPROVER} does nothing by itself. Desk > VMMS > VMMS Setup > Geo"
		f" Assignment > New, twice at {DEMO_REGION} and twice again at the national root — the"
		" national placement is not optional, see the note below."
	)
	w.table(
		("Field", "Row 1", "Row 2", "Row 3", "Row 4"),
		[
			["User", APPROVER_USER, APPROVER_USER, APPROVER_USER, APPROVER_USER],
			["Role", ROLE_VOL_APPROVER, ROLE_MEM_APPROVER, ROLE_VOL_APPROVER, ROLE_MEM_APPROVER],
			["Geo Node", DEMO_REGION, DEMO_REGION, NATIONAL_NODE, NATIONAL_NODE],
		],
		(1.20, 1.20, 1.20, 1.20, 1.20),
	)
	w.note(
		"The national placement is the routing backstop, not decoration. Both approval workflows"
		" below resolve at_level with the regional stage optional — a region with nobody named simply"
		" skips that stage and escalates straight to whoever holds the role at the national node."
		" Skip this pair and an application from any region other than Dar es Salaam resolves nobody"
		" at all: not the applicant, not an approver, not an administrator. This is the exact failure"
		" the Gambia seed hit in production before place_approver() was fixed to place both."
	)


def _p1_membership_types(w) -> None:
	w.h2("Membership Types")

	w.p("Desk > VMMS > VMMS Setup, or Desk > VMMS > Membership > VMMS Membership Type > New.")
	w.table(
		("Field", TYPE_YOUTH, TYPE_ORDINARY, TYPE_LIFE),
		[
			["Type Key (docname)", "youth-member", "ordinary-member", "life-member"],
			["Fee", f"{CURRENCY} 5,000", f"{CURRENCY} 10,000", f"{CURRENCY} 100,000"],
			["Is Lifetime", "unchecked", "unchecked", "checked"],
			["Duration (Days)", "365", "365", "leave it, the field hides"],
			["Approval Mode", "routed", "routed", "routed"],
			["Certificate Template", CERT_TEMPLATE, CERT_TEMPLATE, CERT_TEMPLATE],
		],
		(1.55, 1.55, 1.55, 1.55),
	)
	w.note(
		"These three fees are a worked example, not a sourced TRCS price list — no published fee"
		" schedule was found while researching this seed. Replace them with the society's real,"
		" published figures before this stops being a demo; tanzania.py::MEMBERSHIP_TYPES is the one"
		" place that value lives in the seed."
	)
	w.note(
		f'"{CERT_TEMPLATE}" is the default VMMS Template this app seeds on every install. A type left'
		" with no Certificate Template fails the moment somebody tries to download a certificate, not"
		" at save time."
	)


def _p1_workflows(w) -> None:
	w.h2("Approval Workflows — Volunteer Application and Membership")

	w.p(
		"Desk > VMMS > VMMS Setup > VMMS Approval Workflow > New. One per governed doctype — Workflow"
		" For is unique."
	)
	w.table(
		("Field", "Volunteer Application", "Membership"),
		[
			["Workflow For", "VMMS Volunteer Application", "VMMS Membership"],
			["Geo Node Field", "geo_node (default)", "geo_node (default)"],
			["Applicant Field", "red_profile", "member"],
			["Allowed Anchor Levels", "one row: Region", "one row: Region"],
			["Stage 1: Label / Role / Level / Optional", "Regional Coordinator / " + ROLE_VOL_APPROVER + " / Region / optional", "Regional Coordinator / " + ROLE_MEM_APPROVER + " / Region / optional"],
			["Stage 2: Label / Role / Level / Optional", "National Desk / " + ROLE_VOL_APPROVER + " / National / required", "National Desk / " + ROLE_MEM_APPROVER + " / National / required"],
		],
		(2.10, 2.10, 2.10),
	)
	w.note(
		"Two rungs, matching the two-rung geo tree. The regional stage can skip — engine._advance"
		" skips an optional stage that resolves nobody — and the national stage cannot, because"
		" nothing above it exists to escalate to. This is why the national Geo Assignment pair in"
		" the previous section is required rather than a nicety."
	)


def _p1_workspaces(w, site: str) -> None:
	w.h2("The VMMS desk workspaces")

	w.p(
		"Nothing to configure — built automatically by after_migrate, floor System Manager always."
		" Find it at Desk > VMMS, or http://" + site + "/app/vmms directly."
	)
	w.table(
		("Workspace", "What is on it"),
		[
			["VMMS", "the landing tile grid, one shortcut per child below"],
			["Membership", "VMMS Member, VMMS Membership, VMMS Membership Type, VMMS Membership Benefit"],
			["Volunteers", "VMMS Volunteer, VMMS Volunteer Application, VMMS Certification, VMMS Certification Type, VMMS Course Mapping, VMMS Time Log"],
			["Deployments", "VMMS Deployment, VMMS Deployment Request, VMMS Terms of Reference, VMMS Branch Transfer"],
			["Stipend", "VMMS Stipend Progress Report, VMMS Stipend Payment Form"],
			["Places", "VMMS Branch Location"],
			["VMMS Setup", "Geo Level, Geo Node, Geo Assignment, National Society Settings, plus every type/category doctype and its own onboarding checklist"],
		],
		(1.55, 4.95),
	)


def _p1_enable_signup(w) -> None:
	w.h2("Enable self-registration")

	w.table(
		("Record", "Field", "Value for Tanzania"),
		[
			["Website Settings", "Disable Signup", "unchecked — signup must stay offered"],
			["Portal Settings", "Default Role", ROLE_APPLICANT],
		],
		(2.00, 1.60, 2.90),
	)
	w.note(
		"Default Role is what a brand-new signup is given, and Society Applicant is what the"
		" Self-Registration Role setting above expects to see arrive. Point the two at the same role."
	)


# ============================================================================
# PART 2 — BRINGING THE SITE TO LIFE
# ============================================================================


def _part2_intro(w) -> None:
	w.h1("Part 2 — Bringing the Site to Life")
	w.lead(
		"A society with no events, no openings and no news is technically configured and reads as"
		" abandoned. This part is what makes a demo, or a real launch, look like somewhere staffed by"
		" people who showed up this month — real events, real job openings, real sourced stories, none"
		" of it invented."
	)


def _p2_events(w, site: str) -> None:
	w.h2("Events — Buzz's own doctype")

	w.p(
		"vmmsx does not own an event doctype: the portal's Events and Calendar tabs read Buzz's"
		f" Buzz Event through a one-way seam (vmmsx/buzz/services/events.py). Desk > Buzz > Event, or"
		f" http://{site}/app/buzz-event, once the buzz app is installed."
	)
	w.table(
		("Field", "Notes"),
		[
			["Title", "reqd. Avoid a dash — Buzz builds the public route from the title, and a dash"
				" survives into the URL unrecognised."],
			["Category", "Link to Event Category — Training, Community, Blood Donation, Fundraising are"
				" a reasonable starting set."],
			["Venue", "Link to Event Venue, mandatory unless Medium is Online. A venue needs an address"
				" to save."],
			["Host", "Link to Event Host — one per society is enough."],
			["Start Date / Start Time / End Time", "all reqd."],
			["Is Published", "the whole of the guest-read gate. Unchecked, an event exists and nobody"
				" outside the desk sees it."],
			["the geo anchor (BUZZ-01)", "one optional custom field vmmsx adds to Buzz Event — a Geo"
				" Node. Left blank, the event shows to everybody, which is correct for an online"
				" session."],
		],
		(1.90, 4.60),
	)
	w.note(
		f"{site} carries seven published events today, one of them real rather than invented: World"
		" First Aid Day, the second Saturday of September (12 September 2026), an observance every"
		" Red Cross and Red Crescent society is expected to mark. The other six are ordinary branch"
		" activity — training, a blood drive, an open day — dated forward from the day the seed runs"
		" so the diary never looks stale."
	)


def _p2_jobs(w, site: str) -> None:
	w.h2("Job Openings — HRMS's own doctype")

	w.p(
		"The live opportunities board (vmmsx/api/opportunities.py, HR-01) reads HRMS's Job Opening"
		" directly, not vmmsx's own VMMS Terms of Reference / VMMS Deployment Request pair — that"
		" older pattern is what the board used to read, before recruitment moved into HRMS. Seed the"
		" newer doctype, or a real vacancy will sit on the desk and never appear on the public board."
	)

	w.h3("Prerequisites — none of these exist on a bench that has never run ERPNext's setup wizard")
	w.table(
		("Doctype", "Tanzania's values"),
		[
			["Company", f'{ORG_NAME}, abbr {ORG_SHORT}, currency {CURRENCY}, country {COUNTRY}'],
			["Department", "Organizational Development, Disaster Management, Health Services — one per"
				" job family the society hires into"],
			["Designation", "the job title itself: IT Officer, Vocational Training Centre Supervisor,"
				" Disaster Risk Reduction Programme Officer, Community Health Officer"],
			["Branch (HRMS's own, not a Geo Node)", "Dar es Salaam, Shinyanga, Kigoma, Tabora, Mbeya,"
				" Zanzibar — Job Opening's Location field links here, a different concept from vmmsx's"
				" own regions"],
		],
		(1.90, 4.60),
	)

	w.h3("The Job Opening record")
	w.table(
		("Field", "Notes"),
		[
			["Job Title", "reqd. Must be unique per Company — see the warning below."],
			["Designation, Company", "both reqd Links."],
			["Department, Location, Employment Type", "all optional but worth setting; the board reads"
				" and shows every one."],
			["Publish", "the guest-read gate, same idea as Buzz's Is Published."],
			["Posted On / Closes On", "Closes On drives the board's closing-soon flag."],
		],
		(1.90, 4.60),
	)
	w.note(
		"Job Title has to be unique per Company, not just per Designation: HRMS builds the public"
		" route as jobs/COMPANY/JOB-TITLE, with no location in it. Three Vocational Training"
		" Centre Supervisor openings at three different branches collide on the exact same route"
		" unless the title itself carries the branch — Vocational Training Centre Supervisor,"
		" Shinyanga and so on. This was found by hitting the collision while seeding the real"
		" openings below, not anticipated in advance."
	)
	w.p(
		f"{site} carries six published openings today: an IT Officer in Dar es Salaam and three"
		" Vocational Training Centre Supervisors, modelled on roles TRCS has genuinely advertised"
		" (Organizational Development department, the PMERL unit, Shinyanga / Kigoma / Tabora), plus"
		" a Disaster Risk Reduction Programme Officer in Mbeya and a Community Health Officer in"
		" Zanzibar, a typical shape for TRCS's own published department structure rather than a"
		" specific advertised vacancy — see tanzania_jobs.py's own module docstring for exactly which"
		" is which."
	)


def _p2_stories(w, site: str) -> None:
	w.h2("Stories — core's Article doctype")

	w.p(
		"The portal's Stories tab reads onerc_core's Article. Desk > Article, or"
		f" http://{site}/app/article."
	)
	w.table(
		("Field", "Notes"),
		[
			["Article Type, Category", "both reqd Links to Localisation Type / Localisation Category."
				" Both autoname from their own label field — passing name= directly on insert silently"
				" produces an empty-named, refused record; set the label field instead."],
			["Slug", "read-only, generated from Title."],
			["Summary, Body", "both reqd."],
			["Status", "Draft / Scheduled / Published / Archived."],
			["docstatus (submit)", "Article is submittable, and the guest-read API"
				" (onerc_core/api/article.py::get_articles) filters on docstatus = 1 as well as"
				" status = Published. Saving without submitting produces an article that looks"
				" published on the desk and is invisible on the portal — the single most likely"
				" mistake here."],
		],
		(1.90, 4.60),
	)
	w.note(
		"Every story on the live site should carry Source Name and Source URL if it did not"
		" originate with the society itself — that is what lets a reader check a claim, and it is the"
		" difference between a newsroom and a wall of unverifiable text."
	)
	w.p(
		f"{site} carries four published, submitted stories today, each sourced from a real TRCS,"
		" EU or European Commission report: the Rungwe/Kyela flood response (EU-funded, over 2,600"
		" people reached), a shorter companion piece on the Mbarali flood response, a heatwave and"
		" albinism-awareness campaign that reached over 4,000 people around Zanzibar, and a"
		" founding-history feature drawing on TRCS's own published facts. Each carries its"
		" source_url — see tanzania_stories.py for the sources themselves."
	)


# ============================================================================
# PART 3 — THE DRY RUN
# ============================================================================


def _part3_intro(w) -> None:
	w.h1("Part 3 — The Dry Run")
	w.lead(
		"Register and approve as a real person would, then confirm the content from Part 2 is"
		" actually reachable by somebody who is not signed in as Administrator."
	)


def _p3_member(w, site: str) -> None:
	w.h2(f"Register as a member: {MEMBER_NAME}")

	w.steps(
		[
			f"Private browser window, http://{site}/login, sign up as"
			f" grace.mushi@example.com. Set a password from the terminal if mail is not configured:",
		]
	)
	w.code(f"bench --site {site} set-password grace.mushi@example.com")
	w.steps(
		[
			f"Log in, click Register as a Member, or go directly to http://{site}/register-as-a-member.",
			f'First Name "Grace", Last Name "Mushi", Branch or Area "{DEMO_REGION}", Membership Type'
			f' "{TYPE_ORDINARY}". Submit.',
		]
	)
	w.p(
		f"Ordinary Member is routed, not auto_on_payment, so the membership enters the approval"
		f" engine at Draft and is confirmed for payment separately through the Manual gateway"
		f" (onerc_payments.gateways.manual.confirm_payment), exactly the sequence the Gambia guide"
		" walks through in full."
	)


def _p3_volunteer(w, site: str) -> None:
	w.h2(f"Register as a volunteer: {VOLUNTEER_NAME}")

	w.steps(
		[
			"Second private browser window, sign up as baraka.kimaro@example.com, set a password the"
			" same way.",
			f"Log in, click Register as a Volunteer, or http://{site}/register-as-a-volunteer.",
			f'First Name "Baraka", Last Name "Kimaro", Branch or Area "Mwanza". Submit.',
		]
	)
	w.p(
		f'The application resolves at_level: nobody holds "{ROLE_VOL_APPROVER}" at Mwanza itself, so'
		f" it escalates straight to the national stage, where {APPROVER_NAME} holds the role at the"
		" national root."
	)

	w.h3("Approve it")
	w.code(
		f"bench --site {site} console\n"
		f">>> frappe.set_user('{APPROVER_USER}')\n"
		">>> from vmmsx.api import approvals\n"
		">>> approvals.decide(doctype='VMMS Volunteer Application', name='VAPP-00001',\n"
		"...                  decision='Approved', reason='Karibu TRCS')\n"
		">>> frappe.db.commit()"
	)
	w.note(
		"Tried as Administrator without the set_user line, this is refused: routed to a specific"
		" resolved approver, and Administrator is not one of them."
	)


def _p3_browse(w, site: str) -> None:
	w.h2("Confirm the content is actually public")

	w.bullets(
		[
			f"Signed out, or in a private window: http://{site}/api/method/vmmsx.api.opportunities.browse"
			" returns the six job openings from Part 2 with no login at all — allow_guest is on the"
			" whole opportunities API.",
			f"http://{site}/api/method/onerc_core.api.article.get_articles returns the four stories,"
			" each with its source_url.",
			"The portal's own Events, Opportunities and Stories tabs (signed in as either demo account)"
			" show the same records through the product's own screens rather than the raw API.",
		]
	)


# ============================================================================
# PART 4 — THE ONE-COMMAND SHORTCUT
# ============================================================================


def _part4(w, site: str) -> None:
	w.h1("Part 4 — The One-Command Shortcut, and Doing This for a New Country")

	w.lead(
		"Everything in Parts 1 and 2 is also a Python module, in the same shape Gambia's and Kenya's"
		" seeds already use. Running it is faster than the desk; reading it is what this whole guide"
		" is a narrated version of."
	)

	w.h2("Run it")
	w.code(
		f"bench --site {site} backup\n"
		f"bench --site {site} execute vmmsx.seed.tanzania_install.main\n"
		"# on a bench that already carries another society's data:\n"
		f"bench --site {site} execute vmmsx.seed.tanzania_install.main --kwargs \"{{'purge': True}}\"\n"
		"# check first, writes nothing:\n"
		f"bench --site {site} execute vmmsx.seed.tanzania_install.main --kwargs \"{{'dry_run': True, 'purge': True}}\""
	)
	w.note(
		"purge.py does not touch User records or HRMS/Buzz doctypes (Company, Job Opening, Buzz"
		" Event) — those either predate the doctypes it was written against, or are core Frappe"
		" records nobody wants deleted by a society-switch. A bench that has seeded another society's"
		" job openings or events keeps them; delete those by hand on the desk if starting genuinely"
		" clean matters."
	)
	w.note(
		"Every step is idempotent — re-running reports exists against everything and changes nothing,"
		" except the landing page copy (tanzania_content.py), which deliberately overwrites every"
		" time: running this seed is asking for the Tanzania page."
	)

	w.h2("Doing this for a different country")
	w.p(
		"Copy the five tanzania_*.py files in vmmsx/seed/ and the docs generator, rename the copies,"
		" and change what is genuinely different — the same relationship gambia.py and kenya.py"
		" already have to each other:"
	)
	w.table(
		("File", "What changes for a new country"),
		[
			["COUNTRY.py", "org identity, currency, geo levels/regions, roles, membership types,"
				" approval workflow shape, demo approver"],
			["COUNTRY_content.py", "landing page wording and statistics — real ones, sourced,"
				" per the module's own rule against inventing a figure"],
			["COUNTRY_operations.py", "vocabularies, branch locations, event categories/venues"],
			["COUNTRY_jobs.py", "Company/Department/Designation/Branch and the openings themselves"],
			["COUNTRY_stories.py", "sourced news, each carrying its source_url — see this file's own"
				" module docstring for what sourced means in practice"],
			["COUNTRY_install.py", "three renamed imports; the shape does not change"],
		],
		(2.00, 4.50),
	)
	w.note(
		"Nothing outside vmmsx/seed/ and vmmsx/docs/ should ever need to change to add a country —"
		" that is the whole point of the split this app is built on, proved three times now."
	)


# ============================================================================
# WHAT IS NOT BUILT
# ============================================================================


def _not_built(w) -> None:
	w.h1("What is still stubbed or absent")

	w.lead("Checked against the code as it stands today, not copied from an older document.")

	w.bullets(
		[
			"**Notifications.** Nobody is emailed when an application is approved or a membership"
			" activates.",
			"**Any custom portal UI beyond what already ships.** Every page a registrant sees is"
			" Frappe's own native rendering of a Web Form or Workspace, or the vmmsx React portal"
			" where it exists — no bespoke page was added by this seed.",
			"**Payment from the member's own screen.** Settling a fee-bearing membership is"
			" onerc_payments' business through its own driver; there is no pay button in vmmsx.",
			"**Withdrawing a role.** Once granted, Volunteer or Member is never taken away by this app.",
			"**A real TRCS logo, and real TRCS photography.** Both are placeholders — see Part 1's note"
			" on the logo and tanzania_content.py's own docstring on the reused, credited Kenya"
			" photography standing in for it.",
			"**A published TRCS membership fee schedule.** The three fees in Part 1 are a worked"
			" example, not a sourced document — see tanzania.py's own module docstring.",
		]
	)


# ============================================================================
# PART 5 — CHECKLIST
# ============================================================================


def _checklist(w, site: str) -> None:
	w.h1("Checklist")
	w.lead("Once the parts above make sense, run the whole setup from this page alone.")

	w.h2("Fresh bench")
	w.bullets(
		[
			"[ ] Site created. onerc_core and vmmsx installed and migrated.",
			"[ ] onerc_payments installed, if the society will take a membership fee.",
			"[ ] erpnext and hrms installed, if the society will publish job openings.",
			"[ ] buzz installed, if the society will publish events.",
		]
	)

	w.h2("Society setup")
	w.bullets(
		[
			f"[ ] National Society Settings — Society tab: name, short name, country ({COUNTRY}),"
			f" language. Locale tab: currency ({CURRENCY}). Logo uploaded.",
			f"[ ] Roles: the six core ones exist automatically; {ROLE_COORDINATOR} and {ROLE_STIPEND}"
			" created by hand if not seeded.",
			"[ ] National Society Settings — Validation tab: every vmms_* role setting filled in. NONE"
			" left blank unless the fail-closed consequence is intended.",
			"[ ] Two Geo Levels: National, Region (requires parent, is lowest).",
			f"[ ] Geo Node tree: 1 national root, {REGION_COUNT} regions under it.",
			"[ ] Demo approver created, holding the approver and coordinator roles.",
			"[ ] Four Geo Assignment rows for the approver: both approver roles, at one region AND at"
			" the national root.",
			"[ ] Three Membership Types, all routed, all pointing Certificate Template at"
			f" {CERT_TEMPLATE}.",
			"[ ] Two Approval Workflows, each with a regional (optional) and a national (required)"
			" stage.",
			"[ ] Website Settings: Disable Signup unchecked. Portal Settings: Default Role ="
			f" {ROLE_APPLICANT}.",
		]
	)

	w.h2("Content")
	w.bullets(
		[
			"[ ] Event Host, at least one Event Category and Event Venue created; a handful of"
			" published Buzz Events, one of them a real observance.",
			"[ ] Company, Department(s), Designation(s), Branch(es) created; a handful of published"
			" Job Openings, each with a Job Title unique per Company.",
			"[ ] A Localisation Type and Category exist; a handful of Articles, submitted (not just"
			" saved), each with a source.",
		]
	)

	w.h2("Dry run")
	w.bullets(
		[
			"[ ] Registered as a member; payment confirmed via the Manual driver.",
			"[ ] Registered as a volunteer; approved by the demo approver through the API.",
			"[ ] Job openings, events and stories confirmed reachable with no login at all.",
		]
	)

	w.h2("Before calling it live")
	w.bullets(
		[
			'[ ] Read "What is still stubbed or absent" so nobody discovers a gap live.',
			"[ ] Real logo and real photography uploaded, replacing every placeholder.",
			"[ ] Real membership fee schedule set, replacing the worked-example figures.",
			"[ ] Demo/seed records — the approver account, any placeholder job openings or events not"
			" genuinely open — reviewed and removed or replaced with the society's own.",
			"[ ] Manual payment gateway replaced with a real one, if taking money online.",
		]
	)

	w.p(f"To start over on a scratch site: bench --site {site} reinstall, then repeat from Part 0.")


if __name__ == "__main__":
	print(main())
