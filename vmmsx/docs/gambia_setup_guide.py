# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A one-day setup and dry-run guide for a real national society: Gambia Red Cross.

    bench --site vmms.localhost execute vmmsx.docs.gambia_setup_guide.main

Deliberately not the living reference guide (`vmmsx/docs/build.py`) and not the
Kenya walkthrough (`vmmsx/docs/walkthrough.py`, which assumes `seed/kenya.py`
has already run). This one assumes nothing: it is the sequence a society admin
runs by hand, once, the day they stand up their own site, written against the
real field names on this app as it exists today — including the two things
that shipped since the Kenya walkthrough was last generated, Proof-of-Membership
and renewal, which that document still lists as absent. Every field, option and
default named here was read from the doctype JSON or the live site, not
recalled.

Written to `docs/`, which is git-ignored, exactly like the other two artefacts.
"""

from datetime import datetime
from pathlib import Path

from vmmsx.docs.writer import Writer

APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = APP_ROOT / "docs" / "gambia-red-cross-setup-and-dry-run.docx"

TITLE = "Gambia Red Cross Society"
SUBTITLE = "VMMS Setup & Dry-Run Guide — Day One"

BLURB = (
	"A short, sequential, executable-in-a-day setup for one real national society. Not the 90-page"
	" reference guide: click-paths, real field names, and the fail-closed settings that bite first."
	" Follow it top to bottom once, then use Part 3 alone on the next site."
)

SITE = "vmms.localhost"

# --- the worked Gambia configuration, named once and used throughout ------

ORG_NAME = "Gambia Red Cross Society"
ORG_SHORT = "GRCS"
COUNTRY = "Gambia"
CURRENCY = "GMD"
LANGUAGE = "en (English)"

LEVEL_NATIONAL = "National"
LEVEL_REGION = "Region"
LEVEL_BRANCH = "Branch"

NATIONAL_NODE = "Banjul (National HQ)"
REGIONS = [
	"West Coast Region",
	"Lower River Region",
	"North Bank Region",
	"Central River Region",
	"Upper River Region",
]
DEMO_REGION = "West Coast Region"
BRANCHES = ["Brikama", "Gunjur"]

ROLE_APPLICANT = "Applicant"
ROLE_VOLUNTEER = "Volunteer"
ROLE_MEMBER = "Member"
ROLE_VOL_COORD = "Regional Coordinator"
ROLE_MEM_OFFICER = "Regional Membership Officer"

APPROVER_NAME = "Isatou Jallow"
APPROVER_USER = "isatou.jallow@grcs.gm"

TYPE_ORDINARY = "Ordinary Membership"
TYPE_ORDINARY_KEY = "ordinary"
TYPE_HONORARY = "Honorary Membership"
TYPE_HONORARY_KEY = "honorary"

CERT_TEMPLATE = "membership_certificate"

MEMBER_NAME = "Fatou Sanyang"
VOLUNTEER_NAME = "Lamin Ceesay"


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
			("Site used to verify every field", site),
			("Built from", "vmmsx/docs/gambia_setup_guide.py — regenerate, do not edit the .docx"),
			(
				"Scope",
				"Part 1: society setup. Part 2: dry run. Part 3: checklist. ~20 pages, not the 90-page guide.",
			),
			("Depends on", "onerc_core, onerc_payments (Manual driver is enough for day one)"),
		],
		blurb=BLURB,
	)

	if outline is not None:
		w.contents(outline)

	_part1_intro(w)
	_p1_prereqs(w, site)
	_p1_settings(w, site)
	_p1_geo_levels(w)
	_p1_geo_nodes(w)
	_p1_roles_assignments(w, site)
	_p1_membership_types(w)
	_p1_workflows(w)
	_p1_workspaces(w, site)
	_p1_enable_signup(w, site)
	w.page_break()

	_part2_intro(w)
	_p2_member(w, site)
	_p2_volunteer(w, site)
	_p2_cross(w)
	_p2_scoping(w)
	_p2_optional(w)
	w.page_break()

	_not_built(w)
	w.page_break()
	_checklist(w, site)

	return w


# ============================================================================
# PART 1 — SOCIETY SETUP
# ============================================================================


def _part1_intro(w) -> None:
	w.h1("Part 1 — Society Setup")
	w.lead(
		"Everything here is done once, by a society administrator with System Manager, before anybody"
		" registers. Order matters: Geo Levels before Geo Nodes, Geo Nodes before Geo Assignments and"
		" workflows, roles before anything that names one."
	)


def _p1_prereqs(w, site: str) -> None:
	w.h2("Before you start")

	w.p(f"A bench with a site that has onerc_core and vmmsx installed:")
	w.code(
		f"bench --site {site} install-app onerc_core\n"
		f"bench --site {site} install-app vmmsx\n"
		f"bench --site {site} migrate"
	)
	w.p(
		"migrate matters even on a site that already has vmmsx installed: it is what rebuilds the VMMS"
		" staff workspace cluster and the self-service workspaces from whatever this guide has"
		" configured so far, every time it runs."
	)
	w.p(
		"onerc_payments is optional for day one — the Ordinary Membership type below is"
		" auto_on_payment and the Manual driver needs no gateway credentials, only the app installed:"
	)
	w.code(f"bench --site {site} install-app onerc_payments")


def _p1_settings(w, site: str) -> None:
	w.h2("National Society Settings")

	w.p(
		"A Single doctype — one record, no list. Open it from Desk > VMMS > Society & Setup >"
		f" National Society Settings, or go to http://{site}/app/national-society-settings directly."
	)

	w.h3("Society tab — required to save at all")

	w.table(
		("Field", "Value for Gambia"),
		[
			["Organization Name", ORG_NAME],
			["Organization Short Name", ORG_SHORT],
			["Country", f'{COUNTRY} — Link to Country, must already exist (it does, as "Gambia")'],
			["Primary Language", LANGUAGE],
			["Logo", "upload the society mark (Attach Image) — see the warning below"],
		],
		(2.20, 4.30),
	)
	w.note(
		"Organization Name, Organization Short Name, Country and Primary Language are the doctype's"
		" own mandatory fields (reqd=1). The form will not save without them. Currency is on the"
		" Locale tab and is NOT marked mandatory by the schema, but membership fee logic falls back to"
		f" it when a type names no currency of its own — set it to {CURRENCY} anyway."
	)
	w.note(
		"Logo is optional in the schema but not in practice: it is an Attach Image, and a membership"
		" certificate's template guards it with {% if society_logo %} — upload nothing and every"
		" certificate this society issues renders correctly but with a blank space where the crest"
		" should be. Nobody is warned; it just looks unfinished."
	)

	w.h3("Locale tab")
	w.table(("Field", "Value"), [["Currency", f"{CURRENCY} — Gambian Dalasi"]], (2.20, 4.30))

	w.h3("Validation tab — the vmms_* settings, and why this section is the one that bites")

	w.lead(
		"Every field below lives at the bottom of the Validation tab, appended after Phone Number"
		" Example — not on the Society tab, wherever a scan of the form might suggest. None of them is"
		" schema-mandatory (reqd=0 on all of them), which is exactly what makes them dangerous: the"
		' form saves happily with every one blank, and blank does not mean "unrestricted" for most of'
		' them — it means CLOSED. This is the single most common cause of "nothing works" on a fresh'
		" site."
	)

	w.table(
		("Setting", "Value for Gambia", "Blank means"),
		[
			[
				"Volunteer Anchor Level",
				LEVEL_BRANCH,
				"unconstrained — any active Geo Level accepts a volunteer application (not closed, just wide open)",
			],
			[
				"Volunteer Scope Role",
				ROLE_VOL_COORD,
				"FAIL-CLOSED. Nobody but Administrator can read a VMMS Volunteer record at all.",
			],
			[
				"Volunteer Self-Service Role",
				ROLE_VOLUNTEER,
				"an accepted volunteer's login is granted nothing, and the My Volunteering workspace is not built.",
			],
			[
				"Membership Scope Role",
				ROLE_MEM_OFFICER,
				"FAIL-CLOSED. Nobody but Administrator can read a VMMS Membership record at all.",
			],
			[
				"Membership Anchor Level",
				LEVEL_BRANCH,
				"unconstrained, same as the volunteer anchor level.",
			],
			[
				"Member Self-Service Role",
				ROLE_MEMBER,
				"an active member's login is granted nothing, and the My Membership workspace is not built.",
			],
			[
				"Certificate Print Role",
				ROLE_MEM_OFFICER,
				"closed door: literally nobody but the member themself may print a certificate — not even an administrator's counter staff.",
			],
			[
				"Self-Registration Role",
				ROLE_APPLICANT,
				"FAIL-CLOSED. The Registration workspace is not built, so a brand-new account has nowhere to land.",
			],
		],
		(1.85, 1.70, 2.85),
	)
	w.note(
		"Deployment Anchor Level, Deployment Scope Role, Deployment Request Scope Role, Branch"
		" Transfer Scope Role, Stipend Anchor Level, Stipend Report Scope Role, Stipend Payment Scope"
		" Role, and Branch Transfer Approval also live on this tab. They gate the Deployments and"
		" Stipend modules (Part 2.5) and follow the identical fail-closed pattern. Left blank for this"
		" one-day guide — set them the same way if the society uses those modules."
	)
	w.note(
		"None of these role names exist yet. Create the five roles (Applicant, Volunteer,"
		f" Member, {ROLE_VOL_COORD}, {ROLE_MEM_OFFICER}) first — see 1.5 — then come back and fill in"
		" this tab. The form accepts a role name that does not exist yet only by typo; the Link field"
		" will refuse anything not already a Role record."
	)


def _p1_geo_levels(w) -> None:
	w.h2("Geo Levels — National, Region, Branch")

	w.p(
		"Desk > VMMS > Society & Setup > Geo Level, then New. Create exactly three, in this order,"
		" because the order field auto-fills from whatever already exists."
	)

	w.steps(
		[
			f'Geo Level Name "{LEVEL_NATIONAL}", Geo Level Key "NAT". Geo Level Order arrives pre-filled'
			" with 1 — a JS onload calls next_available_order() and fills the field, but only while it"
			" is blank on a new record; typing over it is always allowed. Leave Is Lowest Level and"
			" Requires Parent both unchecked.",
			f'Geo Level Name "{LEVEL_REGION}", Geo Level Key "RGN". Order pre-fills to 2. Check Requires'
			" Parent — a Region must be filed under something shallower, which the National level is.",
			f'Geo Level Name "{LEVEL_BRANCH}", Geo Level Key "BRN". Order pre-fills to 3. Check Requires'
			" Parent, and check Is Lowest Level.",
		]
	)

	w.note(
		"Geo Level Order is presentation and a data-entry guide only — the description says so"
		' outright: "nothing about ancestry, routing or scope reads this number." The Geo Node tree'
		" (parent_geo_node links) is the actual structure. Reusing a number only warns; it never"
		" refuses."
	)
	w.note(
		"Is Lowest Level marks the deepest rung a society still registers records at, and the marker"
		" moves: checking it on Branch would silently uncheck it on Region if Region had been marked"
		" first. At most one active level carries it."
	)

	w.p(
		"Open any one of the three again and look at the Hierarchy Overview (bottom of the form). It"
		" reads: National — top; Region; Branch — lowest. That line is derived live from the lowest"
		" active order, not stored anywhere — there is deliberately no is_highest field."
	)


def _p1_geo_nodes(w) -> None:
	w.h2("Geo Nodes — the Gambia tree")

	w.p(
		"Desk > VMMS > Society & Setup > Geo Node, then New for each. Geo Node is a tree doctype"
		" (is_tree), so a Tree View is also available from the list's menu if preferred to the form."
	)

	w.table(
		("Field", "Notes"),
		[
			["Geo Node Name", "the place, e.g. Brikama"],
			["Geo Level", "Link to Geo Level — National, Region or Branch"],
			["Parent Geo Node", "Link to Geo Node — blank only for the root"],
			["Geo Code", "optional, free text"],
		],
		(2.05, 4.45),
	)

	w.p("Build this tree, eight nodes, root first:")

	w.table(
		("Node", "Level", "Parent"),
		[
			[NATIONAL_NODE, LEVEL_NATIONAL, "(none — the root)"],
			["West Coast Region", LEVEL_REGION, NATIONAL_NODE],
			["Lower River Region", LEVEL_REGION, NATIONAL_NODE],
			["North Bank Region", LEVEL_REGION, NATIONAL_NODE],
			["Central River Region", LEVEL_REGION, NATIONAL_NODE],
			["Upper River Region", LEVEL_REGION, NATIONAL_NODE],
			["Brikama", LEVEL_BRANCH, "West Coast Region"],
			["Gunjur", LEVEL_BRANCH, "West Coast Region"],
		],
		(2.20, 1.20, 3.10),
	)

	w.note(
		"West Coast, Lower River, North Bank, Central River and Upper River are the Gambia's real"
		" administrative regions; Brikama and Gunjur are real towns in West Coast Region. Only West"
		" Coast gets branches here — enough to prove the geo walk and the scoping demo in Part 2.4"
		" without typing forty nodes for a one-day guide."
	)
	w.p(
		'This is the point of ACC-03: nothing above names "county" or "ward". A society with a'
		" four-rung ladder, or one that anchors at Region instead of Branch, changes this tree and the"
		" one setting in 1.2 — no source file."
	)


def _p1_roles_assignments(w, site: str) -> None:
	w.h2("Roles & Geo Assignments — who can approve, and where")

	w.h3("Create the roles")

	w.p(
		"Desk > Role List > New, for each of these five. Frappe framework roles are exempt from the"
		' "no hardcoded role" rule this app follows everywhere else — these five are not framework roles,'
		" they are this society's own configuration:"
	)

	w.table(
		("Role", "What it is for"),
		[
			[ROLE_APPLICANT, "held by a brand-new self-registered account, until approved as anything"],
			[ROLE_VOLUNTEER, "granted automatically when a volunteer becomes Active"],
			[ROLE_MEMBER, "granted automatically when a membership becomes Active"],
			[ROLE_VOL_COORD, "the approver role a Volunteer Application workflow stage names"],
			[
				ROLE_MEM_OFFICER,
				"the approver role the Membership workflow stage names, and the certificate print role",
			],
		],
		(2.30, 4.20),
	)
	w.p(
		"Leave Desk Access checked (the default) on all five — a role with no desk access can never"
		" open a Workspace, which is how a self-registered account reaches its own surfaces at all."
	)

	w.h3("Create the demo approver, and give them nothing yet")

	w.p(
		f"Desk > User List > New: {APPROVER_NAME}, email {APPROVER_USER}. Give the account the roles"
		f" {ROLE_VOL_COORD} and {ROLE_MEM_OFFICER} on the Roles tab. Set a password:"
	)
	w.code(f"bench --site {site} set-password {APPROVER_USER}")

	w.h3('Geo Assignment — the "where" half')

	w.lead(
		f"Holding {ROLE_VOL_COORD} does nothing by itself. Desk > VMMS > Society & Setup >"
		f" Geo Assignment > New, twice, both for {APPROVER_NAME} at {DEMO_REGION}:"
	)

	w.table(
		("Field", "Row 1", "Row 2"),
		[
			["User", APPROVER_USER, APPROVER_USER],
			["Role", ROLE_VOL_COORD, ROLE_MEM_OFFICER],
			["Geo Node", DEMO_REGION, DEMO_REGION],
			["Is Active", "checked (default)", "checked (default)"],
		],
		(1.55, 2.30, 2.30),
	)
	w.note(
		f'"Role + Geo Assignment = who can approve where; role alone does nothing." {APPROVER_NAME}'
		f" now holds authority over {DEMO_REGION} and everything beneath it — both branches — for both"
		" roles. Valid From / Valid To are optional and left blank, meaning unbounded."
	)


def _p1_membership_types(w) -> None:
	w.h2("Membership Types")

	w.p("Desk > VMMS > Society & Setup, or Desk > VMMS > Membership > VMMS Membership Type > New.")

	w.table(
		("Field", TYPE_ORDINARY, TYPE_HONORARY),
		[
			["Type Key (docname)", TYPE_ORDINARY_KEY, TYPE_HONORARY_KEY],
			["Fee", f"{CURRENCY} 100", f"{CURRENCY} 0"],
			["Is Lifetime", "unchecked", "checked"],
			["Duration (Days)", "365", "leave it, the field hides"],
			["Approval Mode", "auto_on_payment", "routed"],
			["Certificate Template", CERT_TEMPLATE, CERT_TEMPLATE],
		],
		(1.75, 2.20, 2.20),
	)
	w.note(
		f'"{CERT_TEMPLATE}" is not something you write — it is the default VMMS Template this app'
		" seeds on every install (Category: certificate, Is Active checked). Point Certificate"
		" Template at it on every membership type. A type left with no Certificate Template does not"
		" fail at save time — it fails the moment somebody tries to download a certificate, with"
		' "Membership type ... has no certificate template configured", which is a worse time to find'
		" out."
	)
	w.note(
		"Is Lifetime is why the honorary type has no duration. An honorary membership conferred for"
		" life does not expire, so it activates with a start date and no end date and the daily"
		" expiry sweep never selects it. Ticking it hides Duration (Days) and clears whatever was"
		" there — a duration standing in for a lifetime, however large, is a membership that lapses"
		" on a date nobody is watching for."
	)
	w.note(
		"approval_mode is the whole of MEM-02: auto_on_payment never enters the approval engine at"
		" all — it activates the instant the fee is confirmed, with no approver anywhere. routed hands"
		" the membership to the engine exactly like a volunteer application. A type that is"
		" auto_on_payment AND charges nothing is refused at save time, on the grounds that every"
		" application on it would activate the instant it was submitted."
	)


def _p1_workflows(w) -> None:
	w.h2("Approval Workflows — Volunteer Application and Membership")

	w.p(
		"Desk > VMMS > Society & Setup > VMMS Approval Workflow > New. One per governed doctype —"
		" Workflow For is unique, so a second workflow naming the same doctype is refused."
	)

	w.h3("Workflow 1 — VMMS Volunteer Application")

	w.table(
		("Field", "Value"),
		[
			["Workflow For", "VMMS Volunteer Application"],
			["Geo Node Field", "geo_node (the default, and correct here)"],
			["Applicant Field", "red_profile"],
			["Allow Withdrawal", "checked (default)"],
			["Allowed Anchor Levels", f"one row: {LEVEL_BRANCH}"],
		],
		(2.20, 4.30),
	)
	w.p("One stage, in the Stages table:")
	w.table(
		("Field", "Value"),
		[
			["Sequence", "1"],
			["Stage Label", "Regional Review"],
			["Required Role", ROLE_VOL_COORD],
			["Resolution Rule", "nearest_ancestor (default)"],
			["Completion Rule", "single (default)"],
			["Can Reject", "checked (default) — required: at least one stage must be able to reject"],
			["SLA Days", "5 (default)"],
			["On SLA Breach", "escalate_up (default)"],
		],
		(2.20, 4.30),
	)

	w.h3("Workflow 2 — VMMS Membership")

	w.p(
		"Same shape, and it governs every membership regardless of type — auto_on_payment memberships"
		" simply never reach it, because approval.py never calls the engine for that mode."
	)
	w.table(
		("Field", "Value"),
		[
			["Workflow For", "VMMS Membership"],
			["Geo Node Field", "geo_node (default)"],
			["Applicant Field", "leave blank — falls back to the document's owner"],
			["Allowed Anchor Levels", f"one row: {LEVEL_BRANCH}"],
			["Stage: Required Role", ROLE_MEM_OFFICER],
			["Stage: everything else", "same defaults as the volunteer workflow's stage"],
		],
		(2.20, 4.30),
	)
	w.note(
		"The workflow refuses to save if the doctype does not satisfy the approval contract"
		" (approval_state, approval_stage, approval_stage_entered_on, an Approval Decisions table, and"
		" the Geo Node field named above). Both VMMS Volunteer Application and VMMS Membership already"
		" do — that is a property of this app's own doctypes, not something you configure."
	)


def _p1_workspaces(w, site: str) -> None:
	w.h2("The VMMS desk workspaces — one parent, five children")

	w.p(
		"Nothing to configure here — this cluster is built automatically by after_migrate, and its"
		" floor is System Manager, always present. It is where 1.2 to 1.7 above actually happen."
	)

	w.table(
		("Workspace", "What is on it"),
		[
			["VMMS", "the landing tile grid — five shortcuts, one per child below"],
			["Membership", "VMMS Member, VMMS Membership, VMMS Membership Type, VMMS Membership Benefit"],
			[
				"Volunteers",
				"VMMS Volunteer, VMMS Volunteer Application, VMMS Certification, VMMS Certification"
				" Type, VMMS Course Mapping, VMMS Time Log",
			],
			[
				"Deployments",
				"VMMS Deployment, VMMS Deployment Request, VMMS Terms of Reference, VMMS Branch Transfer",
			],
			["Stipend", "VMMS Stipend Progress Report, VMMS Stipend Payment Form"],
			[
				"Society & Setup",
				"Geo Level, Geo Node, National Society Settings (core's, all three), plus VMMS"
				" Approval Workflow, VMMS Template, Affiliation Type, Geo Assignment",
			],
		],
		(1.75, 4.75),
	)
	w.p(f"Find it at Desk > VMMS in the sidebar, or http://{site}/app/vmms directly.")
	w.note(
		'A society may layer a narrower role onto one child — e.g. giving "Regional Membership'
		" Officer\" its own reduced view of Membership — by pointing that child's own scope-role"
		" setting at a role (the same settings from 1.2). System Manager always sees every child"
		" regardless; this narrows who else does. Re-run after changing a scope role:"
	)
	w.code(f"bench --site {site} execute vmmsx.staff.services.workspaces.install")


def _p1_enable_signup(w, site: str) -> None:
	w.h2("Enable self-registration")

	w.p(
		"Two native Frappe records, not vmmsx's to set, and both must be right before Part 2's web"
		" forms are reachable by a member of the public:"
	)
	w.table(
		("Record", "Field", "Value for Gambia"),
		[
			["Website Settings", "Disable Signup", "unchecked — signup must stay offered"],
			["Portal Settings", "Default Role", ROLE_APPLICANT],
		],
		(2.00, 1.60, 2.90),
	)
	w.note(
		f"Default Role is what a brand-new signup is given, and Applicant is what 1.2's"
		" Self-Registration Role setting expects to see arrive. Point the two at the same role, or a"
		" new account is granted a role the Registration workspace was never built to be shown to."
	)


# ============================================================================
# PART 2 — THE DRY RUN
# ============================================================================


def _part2_intro(w) -> None:
	w.h1("Part 2 — The Dry Run")
	w.lead(
		"Register and approve as a real person would: two accounts, two web forms, one payment"
		" confirmation, one approval decision. This is the core of the day — the rest of Part 2 is"
		" brief on purpose."
	)


def _p2_member(w, site: str) -> None:
	w.h2(f"Register as a member: {MEMBER_NAME}")

	w.steps(
		[
			f"Open a private browser window, go to http://{site}/login, sign up with"
			f" {MEMBER_NAME.lower().replace(' ', '.')}@example.com. Set a password from the terminal if"
			" mail is not configured on this bench:",
		]
	)
	w.code(f"bench --site {site} set-password fatou.sanyang@example.com")
	w.steps(
		[
			f"Log in. The desk opens on Registration (it carries a negative sequence id, so it sorts"
			" first for a brand-new account). Click Register as a Member, or go directly to"
			f" http://{site}/register-as-a-member.",
			f'Fill in First Name "Fatou", Last Name "Sanyang", Branch or Area "Brikama", Membership Type'
			f' "{TYPE_ORDINARY}". Submit.',
		]
	)
	w.p(
		"The membership is created with Membership Status Awaiting Payment. Because Ordinary"
		" Membership is auto_on_payment, approval_state stays at Draft for its whole life — there is"
		" no approver in this path at all."
	)

	w.h3("Confirm the payment — Manual driver")

	w.p(
		"As Administrator: OneRC Payment Settings (Single doctype) needs Active Gateway set to Manual"
		' — the "Manual" gateway record already exists as a fixture; this app never configures the'
		" gateway app's own settings for you."
	)
	w.p("Find the transaction name on the membership's Payment Transaction field, then:")
	w.code(
		"bench --site "
		+ site
		+ " execute onerc_payments.gateways.manual.confirm_payment \\\n"
		+ "  --kwargs \"{'transaction_name': 'PAY-...', 'receipt_number': 'MANUAL-DEMO-1'}\""
	)
	w.p(
		"Confirmation is the universal trigger, whatever gateway resolved it: on_payment_confirmed"
		" fires, the membership records the payment and re-evaluates activation, and — because"
		" approval was never in the picture for this type — it goes straight to Active."
	)

	w.h3("Download the certificate")

	w.p(
		f"Log back in as Fatou. Desk now opens on My Membership (sequence -2.0). Click Download My"
		" Certificate — /api/method/vmmsx.api.member.download_my_certificate, no arguments, answered"
		" from the session. If the logo was uploaded in 1.2, it is embedded in the PDF; if not, the"
		" certificate renders correctly with a blank space where it belongs."
	)
	w.note(
		"Registering by proof instead of payment — for a member who paid before this system existed"
		f" — is a real, separate self-service path: http://{site}/proof-of-membership. It is the same"
		" routed approval any Honorary application goes through, with the approver verifying an"
		" attachment instead of a gateway confirming a fee. Not exercised in this walkthrough; worth"
		" knowing it exists."
	)


def _p2_volunteer(w, site: str) -> None:
	w.h2(f"Register as a volunteer: {VOLUNTEER_NAME}")

	w.steps(
		[
			"Second private browser window, sign up as lamin.ceesay@example.com, set a password the"
			" same way.",
			f"Log in, click Register as a Volunteer, or go to http://{site}/register-as-a-volunteer.",
			'First Name "Lamin", Last Name "Ceesay", Branch or Area "Gunjur". The four narrative fields'
			" (motivation, declared skills, availability, prior experience) are optional and read by"
			" nobody in code — fill them in or skip them, it changes nothing.",
			"Submit.",
		]
	)
	w.p(
		f'The application routes by nearest_ancestor from Gunjur: nobody holds "{ROLE_VOL_COORD}" at'
		f" Gunjur itself, so the walk continues up to West Coast Region, where {APPROVER_NAME} does —"
		" and lands in her ToDo queue."
	)

	w.h3("Approve it")

	w.p(
		"There is no desk workflow button. Approving goes through the API, which checks that the"
		" acting user is one of the resolved approvers for the current stage — not merely a holder of"
		" the role:"
	)
	w.code(
		f"bench --site {site} console\n"
		f">>> frappe.set_user('{APPROVER_USER}')\n"
		">>> from vmmsx.api import approvals\n"
		">>> approvals.decide(doctype='VMMS Volunteer Application', name='VAPP-00001',\n"
		"...                  decision='Approved', reason='Welcome to GRCS')\n"
		">>> frappe.db.commit()"
	)
	w.note(
		"Try it as Administrator without the set_user line and it is refused: routed to a specific"
		" approver, and Administrator is not one of them. That refusal is worth showing — it is the"
		" whole reason this layer exists instead of a native Frappe Workflow."
	)
	w.p(
		f"A VMMS Volunteer record is created for Lamin at Gunjur, Status Active. His login is granted"
		f' "{ROLE_VOLUNTEER}", and a User Permission narrows his desk to exactly his own VMMS Volunteer'
		" row. Log back in as Lamin: the desk now opens on My Volunteering (sequence -3.0, sorts ahead"
		" of My Membership)."
	)


def _p2_cross(w) -> None:
	w.h2("Cross-registration")

	w.p(
		"Either Fatou or Lamin can register for the other affiliation — the Registration workspace"
		" stays visible after approval precisely so this works. Log in as one of them, open Registration"
		" again (it is still in the sidebar), and fill in the other web form. One Red Profile is"
		" resolved, not created twice: registering again reuses the profile the first registration"
		" made, matched on the login."
	)
	w.bullets(
		[
			"Still exactly one Red Profile for that login.",
			"Two affiliation rows now, volunteer and member, both Active, written independently by each"
			" satellite.",
			"Both roles held, both workspaces shown.",
			"My Volunteer Record and My Memberships each still answer for their own side; being both"
			" does not merge the two records into one.",
		]
	)


def _p2_scoping(w) -> None:
	w.h2("Confirm geo scoping")

	w.p(
		f"Log in as {APPROVER_NAME} ({APPROVER_USER}). Open Desk > VMMS > Volunteers, or > Membership."
		f" Her Geo Assignment covers {DEMO_REGION} and everything beneath it — Brikama and Gunjur — so"
		" she sees Lamin's volunteer record and Fatou's membership. That is the whole of core's geo"
		" scoping at work: role + Geo Assignment decides the query filter, with no code in this app"
		" doing the narrowing."
	)
	w.note(
		"To see the fail-closed direction from the other side: create a Geo Assignment for a second"
		' user at "Lower River Region" instead, holding the same two roles, and log in as them. They'
		" see an empty Volunteers list and an empty Membership list — correct, because nobody has"
		" registered anywhere under Lower River yet, and the query genuinely excludes everything"
		" outside their scope rather than merely hiding it."
	)


def _p2_optional(w) -> None:
	w.h2("Optional, if there is time")

	w.p(
		"Three more modules exist under Desk > VMMS: Deployments (VMMS Deployment, VMMS Deployment"
		" Request, VMMS Terms of Reference, VMMS Branch Transfer), Certifications (VMMS Certification,"
		" VMMS Certification Type, under Volunteers), and Stipend (VMMS Stipend Progress Report, VMMS"
		" Stipend Payment Form). Each follows the same ACC-02/ACC-03 anchor-and-scope-role pattern as"
		" Part 1 — an anchor Geo Node field, a configurable anchor level, and a scope role that fails"
		" closed until set on National Society Settings (the Deployment and Stipend rows noted at the"
		" end of 1.2)."
	)
	w.p(
		"Out of scope for a one-day guide to walk through field by field — the reference guide covers"
		" them in full. The member-and-volunteer register-and-approve loop above is the core dry run,"
		" and everything else in the app is built on the same two ideas it just exercised: an opaque"
		" ACC-02 anchor, and a role resolved through Geo Assignment."
	)


# ============================================================================
# WHAT IS NOT BUILT
# ============================================================================


def _not_built(w) -> None:
	w.h1("What is still stubbed or absent")

	w.lead(
		"Checked against the code as it stands today, not copied from an older document. Two things"
		" the Kenya walkthrough lists as unbuilt have since shipped — Proof-of-Membership and renewal"
		" — and are exercised or mentioned above. What follows is genuinely absent right now."
	)

	w.bullets(
		[
			"**Notifications.** Nobody is emailed or notified when an application is approved or a"
			" membership activates. Grepping the app for frappe.sendmail finds nothing outside the"
			" test suite. The templating engine renders certificates only; nothing wires it to a"
			" notification event.",
			"**Any custom portal UI.** vmmsx/templates/pages/ and vmmsx/www/ both contain nothing but"
			" an __init__.py. Every page a registrant or member sees is Frappe's own native rendering"
			" of a Web Form or a Workspace — no bespoke page, no client bundle.",
			"**Payment from the member's own screen.** A fee-bearing membership creates a payment"
			" transaction; settling it is onerc_payments' business through its own driver. There is no"
			" pay button anywhere in vmmsx.",
			"**Withdrawing a role.** Once granted, Volunteer or Member is never taken away by this app."
			" Exit, suspension and lapse leave the login holding what it was granted; off-boarding is a"
			" society's own act.",
			"**Deployment matching, certifications and stipend workflows are built but not exercised in"
			" this guide.** The doctypes and desk views exist (2.5); walking through fresh field-level"
			" setup for each is left to the full reference guide to keep this one to a day.",
		]
	)


# ============================================================================
# PART 3 — CHECKLIST
# ============================================================================


def _checklist(w, site: str) -> None:
	w.h1("Part 3 — One-Page Checklist")
	w.lead("Once Parts 1 and 2 make sense, run the whole setup from this page alone.")

	w.h2("Society setup")
	w.bullets(
		[
			f"[ ] National Society Settings — Society tab: Organization Name, Short Name, Country"
			f" ({COUNTRY}), Primary Language. Locale tab: Currency ({CURRENCY}). Logo uploaded.",
			"[ ] Five roles created: Applicant, Volunteer, Member, Regional Coordinator, Regional"
			" Membership Officer.",
			"[ ] National Society Settings — Validation tab: all eight vmms_* role/level settings"
			" filled in (list in 1.2). NONE left blank unless the fail-closed consequence is intended.",
			"[ ] Three Geo Levels: National (order 1), Region (order 2, requires parent), Branch (order"
			" 3, requires parent, is lowest).",
			"[ ] Geo Node tree built: 1 National root, 5 Regions under it, 2+ Branches under one Region.",
			"[ ] Demo approver user created, given both approver roles.",
			"[ ] Two Geo Assignment rows for the approver, both at the same Region node, one per role.",
			"[ ] Two Membership Types: one auto_on_payment with a fee, one routed. Both point Certificate"
			f" Template at {CERT_TEMPLATE}.",
			"[ ] Two VMMS Approval Workflows: one for VMMS Volunteer Application, one for VMMS"
			" Membership. Each has one stage naming the matching approver role.",
			f"[ ] Website Settings: Disable Signup left unchecked. Portal Settings: Default Role ="
			f" Applicant.",
			"[ ] VMMS desk workspace cluster visible at Desk > VMMS (automatic — just confirm it is there).",
		]
	)

	w.h2("Dry run")
	w.bullets(
		[
			"[ ] Registered as a member through the web form; paid via the Manual driver; membership"
			" reached Active; certificate downloaded.",
			"[ ] Registered as a volunteer through the web form; approved by the demo approver through"
			" the API (not a desk button); volunteer reached Active.",
			"[ ] One of the two registered for the other affiliation too; one Red Profile, two"
			" affiliation rows, both workspaces visible.",
			"[ ] Confirmed the approver sees only people under their own Geo Assignment.",
		]
	)

	w.h2("Before calling it done")
	w.bullets(
		[
			'[ ] Read "What is still stubbed or absent" so nobody discovers a gap live.',
			"[ ] If going further than this guide: onerc_payments needs a real gateway configured"
			" (M-Pesa Daraja fields are on OneRC Payment Settings) before anyone but an administrator"
			" can confirm a payment.",
		]
	)

	w.p(f"To start over on a scratch site: bench --site {site} reinstall, then repeat from the top.")


if __name__ == "__main__":
	print(main())
