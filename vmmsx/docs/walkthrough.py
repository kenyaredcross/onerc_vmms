# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The KRCS setup and registration walkthrough, as a document somebody can follow.

    bench --site vmms.localhost execute vmmsx.docs.walkthrough.main

A separate artefact from the system guide, and deliberately a different kind of
writing. The guide describes what the software is; this describes what to *do*,
in order, on a real site, to see the self-service journey work end to end.

**Every step here has been run.** Routes are the web forms' own `route` fields
and the desk's own workspace slugs; commands are the ones this app exposes;
record names are the ones `vmmsx/seed/kenya.py` creates. Where something is not
built, or is built and only partly, the walkthrough says so in its own section
rather than letting somebody find out at a demo.

Written to `docs/`, which is git-ignored: like the guide, it is a build artefact
and a committed binary is a file nobody can diff that goes stale the moment a
route changes.
"""

from datetime import datetime
from pathlib import Path

from vmmsx.docs.writer import Writer
from vmmsx.registration.services import workspaces
from vmmsx.seed import kenya

APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = APP_ROOT / "docs" / "krcs-setup-and-registration-walkthrough.docx"

TITLE = "Kenya Red Cross Society"
SUBTITLE = "Setup & Registration Walkthrough"

BLURB = (
	"How to stand up a working society on a fresh site and walk a real person through registering"
	" as a volunteer and as a member. Every step is against real doctypes, real endpoints and the"
	" two native web forms this app ships. The last section lists what is not built and what is"
	" only partly built, so that nobody discovers either during a demonstration."
)

SITE = "vmms.localhost"


def main(path: str | None = None, site: str | None = None) -> str:
	"""Build the walkthrough and return where it was written."""
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
			("Site used", site),
			("Built from", "vmmsx/docs/walkthrough.py — regenerate, do not edit the .docx"),
			("Depends on", "onerc_core; onerc_payments for a fee-bearing membership type"),
		],
		blurb=BLURB,
	)

	if outline is not None:
		w.contents(outline)

	_before_you_start(w, site)
	w.page_break()
	_seed(w, site)
	w.page_break()
	_signup(w, site)
	_landing(w)
	w.page_break()
	_portal(w, site)
	w.page_break()
	_volunteer(w, site)
	w.page_break()
	_member(w, site)
	w.page_break()
	_cross(w)
	_troubleshooting(w, site)
	w.page_break()
	_not_built(w)

	return w


# --- before you start ------------------------------------------------------


def _before_you_start(w, site: str) -> None:
	w.h1("Before you start")

	w.lead(
		"You need a Frappe bench with a site that has onerc_core and vmmsx installed. Everything"
		" below is run against that site."
	)

	w.h2("Install and migrate")

	w.code(
		f"bench --site {site} install-app onerc_core\n"
		f"bench --site {site} install-app vmmsx\n"
		f"bench --site {site} migrate"
	)
	w.p(
		"The migrate matters even on a site that already has vmmsx: it installs the three settings"
		" this stage adds, syncs the two web forms, and runs the after_migrate hook that builds the"
		" self-service workspaces from whatever roles are configured. On a site with nothing"
		" configured yet, that hook correctly builds nothing, which is what the next section fixes."
	)

	w.h2("Optional, and needed only for the fee-bearing membership type")

	w.p(
		"The Ordinary membership type charges a fee, and a fee goes through onerc_payments. If that"
		" app is not installed, use the Life Member type instead: it is routed and free, so the"
		" whole membership journey works with no gateway anywhere. To use the fee-bearing one:"
	)
	w.code(f"bench --site {site} install-app onerc_payments")
	w.p(
		"Then open OneRC Payment Settings in the desk and set an active gateway. The Manual driver is"
		" enough for a demonstration: it lets an administrator confirm a payment by hand, and that"
		" confirmation is the same trigger a real gateway callback uses."
	)

	w.note(
		"The seed does not configure a payment gateway. That is another app's configuration and this"
		" app does not write it. The seed says so in its own report every run."
	)


# --- the seed --------------------------------------------------------------


def _seed(w, site: str) -> None:
	w.h1("Step 1 — seed the society")

	w.code(f"bench --site {site} execute vmmsx.seed.kenya.main")

	w.p(
		"It prints what it created and what it found already there, section by section. It is safe"
		" to run twice: the second run reports exists for everything and changes nothing."
	)

	w.h2("What it creates")

	w.table(
		("Records", "What"),
		[
			[
				"Society",
				f"National Society Settings: {kenya.ORGANIZATION_NAME} ({kenya.ORGANIZATION_SHORT_NAME}),"
				f" country {kenya.COUNTRY}, currency {kenya.CURRENCY}",
			],
			[
				"Geo Levels",
				"National (order 1, no parent), County (order 2), Branch (order 3, the lowest level)",
			],
			[
				"Geo Nodes",
				f"{kenya.NATIONAL_NODE} as the root; {' and '.join(kenya.COUNTY_NODES)} beneath it;"
				f" {' and '.join(kenya.BRANCH_NODES)} beneath {kenya.COUNTY_NODES[0]}",
			],
			[
				"Membership Types",
				f"{kenya.TYPE_ORDINARY} (auto on payment, KES 1,000, 365 days) and"
				f" {kenya.TYPE_LIFE} (routed, no fee, 3,650 days)",
			],
			[
				"Approval Workflows",
				"one for VMMS Volunteer Application and one for VMMS Membership, each with a single"
				" stage that resolves by nearest ancestor and may reject",
			],
			[
				"Roles",
				# Said out loud rather than listed flat, because which of them
				# reaches the desk is the difference between a coordinator and a
				# volunteer, and somebody following this in front of an audience
				# will be asked why the volunteer cannot see /app.
				", ".join(f"{name} ({'desk' if desk else 'portal only'})" for name, _, desk in kenya.ROLES),
			],
			[
				"Approver",
				f"{kenya.APPROVER_USER}, holding both approver roles, placed at"
				f" {kenya.COUNTY_NODES[0]} by Geo Assignment",
			],
			[
				"Settings",
				"the two scope roles, the certificate print role, the two member-facing roles and"
				" the self-registration role, each pointed at a role that exists",
			],
			[
				"Signup",
				"Website Settings signup enabled; Portal Settings Default Role set to"
				f" {kenya.ROLE_APPLICANT}",
			],
			[
				"Workspaces",
				f"{workspaces.LANDING}, {workspaces.VOLUNTEER} and {workspaces.MEMBERSHIP}, each"
				" shown to the role just configured",
			],
		],
		(1.45, 5.05),
	)

	w.h2("Two things you have to do by hand")

	w.steps(
		[
			"Upload the society logo. National Society Settings holds it as an Attach Image, and a"
			" seed cannot invent a file. Until it is uploaded, membership certificates render"
			" correctly but without a mark.",
			f"Give the approver a password: bench --site {site} set-password {kenya.APPROVER_USER}."
			" You will sign in as them in step 4.",
		]
	)

	w.h2("Check it worked")

	w.p(
		f"Sign in as Administrator, open the desk, and look at National Society Settings. The"
		f" organisation name should read {kenya.ORGANIZATION_NAME} and the six vmmsx role settings"
		" near the bottom of the Society tab should all be filled in. If any is empty, the workspace"
		" it governs will not have been built."
	)


# --- signing up ------------------------------------------------------------


def _signup(w, site: str) -> None:
	w.h1("Step 2 — somebody makes their own account")

	w.p(
		f"Open a private browser window and go to http://{site}/login. Because the seed enabled"
		" signup, the page offers a sign-up form. Enter a full name and an email address and submit"
		" it."
	)
	w.p(
		"Frappe creates a User with a random password and emails a link to set one. On a development"
		" bench with no outgoing mail configured, set the password from the terminal instead:"
	)
	w.code(f"bench --site {site} set-password newperson@example.com")

	w.h2("What the account is at this point")

	w.bullets(
		[
			f"It holds one role: {kenya.ROLE_APPLICANT}, because Portal Settings' Default Role names it.",
			"That role has desk access, so Frappe promotes the account to a System User. This is the"
			" mechanism that lets a workspace be shown to them at all: a Workspace is a desk"
			" surface, and a Website User cannot open one.",
			"It has no Red Profile yet. The society does not know this person; it knows an account exists.",
		]
	)


def _landing(w) -> None:
	w.h1("Step 3 — they land on the Registration workspace")

	w.p(
		f"Log in as the new account and go to /app. The desk opens on {workspaces.LANDING}, at"
		f" /app/{_slug(workspaces.LANDING)}, because it is the first workspace this person is"
		" permitted to see."
	)

	w.p("It offers exactly two things, and nothing else:")

	w.table(
		("Shortcut", "Goes to"),
		[
			["Register as a Volunteer", workspaces.VOLUNTEER_FORM_ROUTE],
			["Register as a Member", workspaces.MEMBERSHIP_FORM_ROUTE],
		],
		(2.60, 3.90),
	)

	w.note(
		"The sidebar will also list workspaces belonging to the other apps installed on the bench —"
		" ERPNext, HR, LMS and so on. Those ship with no role restrictions, so they are visible to"
		" any desk user, and vmmsx does not modify other apps' records. If you want a clean"
		" demonstration surface, use Frappe's own Module Profile to block those modules for the"
		f" {kenya.ROLE_APPLICANT} role's users before you start."
	)


# --- the portal ------------------------------------------------------------


def _portal(w, site: str) -> None:
	w.h1("Step 3b — the portal, if you would rather not show the desk")

	w.lead(
		"Everything from here on can be done on the desk, and the rest of this walkthrough shows"
		" it there because the desk is where a coordinator's full power lives. There is now also a"
		" React portal at /portal, and for an audience it is usually the better demonstration:"
		" nobody has to look at a doctype."
	)

	w.h2("Build it first")

	w.p(
		"The bundle is generated and is not committed, so a fresh clone has no portal until it is"
		" built. The page says so rather than throwing, which is a useful thing to know before you"
		" wonder why /portal is blank."
	)
	w.code("cd apps/vmmsx/portal\nnpm install\nnpm run build")

	w.h2("What is there")

	w.table(
		("Route", "Who", "What"),
		[
			[
				"/portal",
				"Anybody",
				"The public landing page. Signed in, it redirects to the dashboard instead.",
			],
			[
				"/portal/join",
				"Signed in",
				"A four-step registration wizard: path, identity, branch, confirm. It calls the"
				" same apply endpoints the web forms end in, through the same identity claim, so"
				" it is a second door onto one flow rather than a second flow.",
			],
			[
				"/portal/dashboard",
				"Signed in",
				"Volunteer status, memberships, deployability, quick actions.",
			],
			["/portal/membership", "Signed in", "Memberships, renewal, certificate download."],
			["/portal/hours", "A volunteer", "Log time given."],
			["/portal/profile", "A volunteer", "Identity, placement, certifications. Read-only."],
			[
				"/portal/admin/queue",
				"An approver",
				"The review queue and approve/decline, on the same gate the desk uses.",
			],
			["/portal/admin/registry", "A coordinator", "Members and volunteers within scope."],
			["/portal/admin/content", "A content editor", "Every editable slot on the site."],
		],
		(1.75, 1.30, 3.45),
	)

	w.h2("Editing the page in front of people")

	w.p(
		"Every word and every photograph on the landing page is a VMMS Content Block. Sign in as"
		" somebody who may edit them, and an Edit content switch appears at the bottom right of"
		" the page; turn it on and a pencil appears beside every slot. Click one, change the"
		" wording or upload a different photograph, save, and it is live."
	)
	w.p(
		"Who may do that is configuration: the Page Content Editor Role field on National Society"
		" Settings, which this seed leaves empty. Empty means only an administrator can, so if you"
		" want to demonstrate it as somebody other than Administrator, set that field to a role"
		" your demo user holds and run a bench migrate so the grant is applied."
	)
	w.note(
		f"The seed writes the Kenya wording and photography over the product's neutral defaults, so"
		f" a freshly seeded {site} shows a Kenya Red Cross landing page rather than a generic one."
		" The photographs are third-party pictures under their own licences, credited in an"
		" editable field on each image. Replace them before anything that is not a demonstration."
	)


# --- volunteer -------------------------------------------------------------


def _volunteer(w, site: str) -> None:
	w.h1("Step 4 — register as a volunteer, and be accepted")

	w.h2("Fill in the form")

	w.p(
		f"Click Register as a Volunteer, or go to http://{site}{workspaces.VOLUNTEER_FORM_ROUTE}"
		" directly. You must be logged in; the form requires it."
	)

	w.table(
		("Field", "What to enter"),
		[
			[
				"Skills, Languages, Availability, Motivation",
				"pick from the society's own lists (VMMS Skill, a Language, VMMS Availability Slot,"
				" VMMS Motivation). All optional, all structured, and queryable — this is what"
				" replaced a free-text guess.",
			],
			["Anything you have done before", "optional free text, read by nobody but the approver"],
			[
				"Branch or Area",
				f"choose {kenya.BRANCH_NODES[0]}. This is the record's organisational anchor (Serving"
				" Branch) and where the approval routes from — leave it blank and it defaults from"
				" Home Area below, for somebody who lives locally.",
			],
			[
				"Citizenship",
				"defaults to this society's own configured country; change it if it does not apply",
			],
			[
				"Where do you live?",
				f"Local (the default) shows Home Area — a cascading picker down the same tree as"
				f" Branch or Area, so choose {kenya.BRANCH_NODES[0]} there too. Abroad shows a Country"
				" of Residence and an address instead.",
			],
			["First Name / Last Name", "the person's real name; these go onto their Red Profile"],
			["Phone", "optional; it goes onto the profile too"],
			["Gender / Date of Birth", "optional"],
			[
				"ID Type / ID Number",
				"mandatory — the form will not submit without one. Written onto the applicant's Red"
				" Profile identifications table, which itself still allows nobody to have identification"
				" at all; only this application insists on it.",
			],
		],
		(2.05, 4.45),
	)

	w.p("Submit it. The page confirms that the application has been sent to the branch you chose.")

	w.h2("What happened on the server")

	w.steps(
		[
			"before_insert resolved this login to a Red Profile. There was none, so one was created"
			" with the name and phone from the form, the email from the login, and their Home Area"
			" recorded as core's home_geo_node — where they said they live, falling back to the"
			" branch they chose only for somebody living abroad, who gives no home area.",
			"The application was linked to that profile, and the intake fields were blanked, so the"
			" saved application carries no name and no phone of its own.",
			"on_update put it into motion: the approval engine enforced the anchor rules, resolved"
			f" who holds {kenya.ROLE_VOLUNTEER_APPROVER} nearest above {kenya.BRANCH_NODES[0]} —"
			f" which is {kenya.APPROVER_USER}, at {kenya.COUNTY_NODES[0]} — and put the application"
			" in their queue.",
		]
	)

	w.p(
		"Check it as Administrator: the VMMS Volunteer Application list shows one record, In Review,"
		" anchored at the branch, with a Red Profile that has the applicant's login on it."
	)

	w.h2("Approve it")

	w.p(
		f"Sign in as {kenya.APPROVER_USER}. The application is in their ToDo list. Approvals are not"
		" desk workflow buttons in this system: the decision goes through the API, which checks that"
		" the acting user is one of the people this document actually routed to, not merely somebody"
		" holding the role."
	)
	w.p("From the browser console while signed in as the approver, or from any client:")
	w.code(
		"frappe.call('vmmsx.api.approvals.decide', {\n"
		"    doctype: 'VMMS Volunteer Application',\n"
		"    name: 'VAPP-00001',\n"
		"    decision: 'Approved',\n"
		"    reason: 'Welcome'\n"
		"})"
	)
	w.p(
		"Or from the terminal. Note the frappe.set_user line: it is not a convenience, it is the"
		" whole point of this layer. bench execute runs as Administrator, and Administrator is"
		" refused, because the gate asks whether you are one of the specific people this document"
		" routed to rather than whether you are privileged."
	)
	w.code(
		f"bench --site {site} console\n"
		f">>> frappe.set_user('{kenya.APPROVER_USER}')\n"
		">>> from vmmsx.api import approvals\n"
		">>> approvals.decide(doctype='VMMS Volunteer Application', name='VAPP-00001',\n"
		"...                  decision='Approved', reason='Welcome')\n"
		">>> frappe.db.commit()"
	)

	w.note(
		"Try it as Administrator without the set_user and you get 'This approval is routed to a"
		" specific approver and you are not one of them.' That is correct and it is worth showing:"
		" role membership is not authorisation here, and there are no desk workflow buttons to"
		" press instead."
	)

	w.h2("What the approval did")

	w.bullets(
		[
			"The application's approval state moved to Approved.",
			"A VMMS Volunteer record was created for that Red Profile, placed at the branch they"
			" applied at, with status Active.",
			f"Their own login was granted {kenya.ROLE_VOLUNTEER}, the role named in"
			" vmms_volunteer_member_role.",
			"Two User Permissions were created, allowing exactly their own volunteer record, and"
			" applying to exactly the two lists their workspace shows: VMMS Time Log and"
			" VMMS Certification. Nothing else about what this person can see changed.",
			"What they declared about themselves was seeded onto the volunteer record: skills,"
			" languages, availability, citizenship and residency. From that moment the volunteer's"
			" copy is the current truth and is editable there, and the application keeps its own as"
			" history. Editing one does not change the other.",
			"An affiliation row was written on their Red Profile by core's index.",
		]
	)

	w.h2("Open the volunteer record as a coordinator")

	w.p(
		f"Sign in as {kenya.APPROVER_USER} again and open the VMMS Volunteer record the approval"
		" just created. This is the screen a coordinator decides from, and it is worth showing"
		" because everything on it except the editable fields is worked out when the page opens."
	)

	w.table(
		("What you see", "Where it comes from", "On a freshly seeded bench"),
		[
			[
				"Identity card: photo, name, contact, date of birth, citizenship, residency, Home"
				" Area and Serving Branch",
				"Red Profile, read live, plus the volunteer's own anchor. Home Area and Serving"
				" Branch are labelled separately on purpose.",
				"working; whatever the registrant typed",
			],
			[
				"Current Capabilities: skills, languages, availability",
				"the volunteer record's own fields. Editable, and the point of the whole split.",
				"working; seeded from the application. Change one and the application does not move",
			],
			[
				"Deployability: one green or red indicator",
				"derived from status and held certifications when the page opens",
				"green, because nothing has lapsed and nothing is held",
			],
			[
				"Certifications held, with current or lapsed per row",
				"derived per row from the expiry date and today",
				"empty: this seed writes no certification type, because those name real"
				" qualifications a society recognises",
			],
			[
				"Deployment history",
				"the roster on each VMMS Deployment",
				"empty: this seed writes no terms of reference and no deployment",
			],
			[
				"Time served: total, count and the most recent logs",
				"VMMS Time Log",
				"empty until somebody files one",
			],
			[
				"Verification outcome, and Declared at Application",
				"the application, read live: who approved and when, then motivation, prior"
				" experience and the identification captured at intake",
				"working; the decision you just made is on it",
			],
		],
		(2.05, 2.25, 2.20),
	)

	w.note(
		"Three of the empty blocks are empty because this seed deliberately writes no certification"
		" type, no terms of reference and no deployment: each names real work or a real qualification"
		" a society recognises, and inventing one would put a placeholder on somebody's training"
		" record. Create a VMMS Certification Type and record a lapsed one against this volunteer to"
		" watch the deployability indicator go red with nothing written to either record."
	)

	w.h2("They land on their own workspace")

	w.p(
		f"Log back in as the applicant and go to /app. The desk now opens on {workspaces.VOLUNTEER},"
		f" at /app/{_slug(workspaces.VOLUNTEER)}, because it sorts before the landing surface. If"
		" the browser has been here before, Frappe reopens whichever workspace it was last showing,"
		f" so go to /app/{_slug(workspaces.VOLUNTEER)} directly rather than being surprised by it."
		" It carries four shortcuts:"
	)

	w.table(
		("Shortcut", "What it is", "State"),
		[
			[
				"My Volunteer Record",
				"/api/method/vmmsx.api.volunteer.my_volunteer — their record and its approval trail,"
				" answered from the session",
				"working",
			],
			[
				"My Applications",
				f"{workspaces.VOLUNTEER_FORM_ROUTE}/list — the web form's own list of their submissions",
				"working",
			],
			[
				"My Time Logs",
				"the VMMS Time Log list, narrowed to their own rows",
				"partial: both kinds of log work, but a deployment log needs a deployment this"
				" volunteer is on the roster of, and this seed writes no terms of reference and no"
				" deployment",
			],
			[
				"My Certifications",
				"/api/method/vmmsx.api.volunteer.my_certifications — what they hold, when each runs"
				" out, whether any has lapsed and whether they are deployable",
				"working, but empty on a fresh bench: this seed writes no certification type,"
				" because those name real qualifications a society recognises",
			],
		],
		(1.60, 3.20, 1.70),
	)

	w.note(
		"The volunteer register itself stays closed to them, and that is correct. Core's geo scoping"
		" fails closed for somebody holding no Geo Assignment, so a volunteer cannot browse the"
		" register. What they can reach is their own record, through the endpoint above."
	)


# --- member ----------------------------------------------------------------


def _member(w, site: str) -> None:
	w.h1("Step 5 — register as a member")

	w.p(
		"There are two paths and the membership type decides which. Nothing in the software branches"
		" on a type's name: the type carries an approval_mode field, and that field is the whole of"
		" the decision."
	)

	w.h2(f"Path A — {kenya.TYPE_ORDINARY}: active on payment")

	w.p(
		f"Go to http://{site}{workspaces.MEMBERSHIP_FORM_ROUTE}. Fill in the personal fields, choose"
		f" {kenya.BRANCH_NODES[0]} as the branch, and choose the {kenya.TYPE_ORDINARY} membership"
		" type. Submit."
	)

	w.p(
		"The membership is created with status Awaiting Payment and a payment transaction against"
		" it. Nobody approves it, and its approval state stays at Draft, because an auto-on-payment"
		" membership has no approval to be in."
	)

	w.p("Confirm the fee through the Manual driver, as an administrator would at a counter:")
	w.code(
		f"bench --site {site} execute onerc_payments.gateways.manual.confirm_payment \\\n"
		"  --kwargs \"{'transaction_name': 'PAY-2026-00001',"
		" 'receipt_number': 'MANUAL-DEMO-1'}\""
	)
	w.p(
		"Take the transaction name from the membership's Payment Transaction field. Confirmation is"
		" the universal trigger: the payments app calls back into the membership, which records the"
		" payment and re-evaluates activation."
	)

	w.h2(f"Path B — {kenya.TYPE_LIFE}: reviewed, not bought")

	w.p(
		f"The same form, choosing {kenya.TYPE_LIFE} instead. It carries no fee, so there is nothing"
		" to pay; it is routed, so it goes to whoever holds"
		f" {kenya.ROLE_MEMBERSHIP_APPROVER} nearest above the branch. Its status is Awaiting"
		" Approval and its approval state is In Review."
	)
	w.p("Approve it as the approver, exactly as in step 4:")
	w.code(
		f"bench --site {site} console\n"
		f">>> frappe.set_user('{kenya.APPROVER_USER}')\n"
		">>> from vmmsx.api import approvals\n"
		">>> approvals.decide(doctype='VMMS Membership', name='MSHIP-00002',\n"
		"...                  decision='Approved', reason='Long service')\n"
		">>> frappe.db.commit()"
	)

	w.h2("Both paths end in the same place")

	w.bullets(
		[
			"The membership becomes Active, with validity running from today for the type's"
			" configured duration.",
			f"Their own login is granted {kenya.ROLE_MEMBER}, the role named in vmms_membership_member_role.",
			"No User Permission is created. The member surface points at no doctype list, so there"
			" is nothing to narrow, and a clerk who is also a member keeps seeing every membership"
			" their job needs.",
			"Their Red Profile carries a member affiliation row.",
		]
	)

	w.h2("They land on their membership workspace")

	w.p(
		f"Logged in as the member, /app now opens on {workspaces.MEMBERSHIP}, at"
		f" /app/{_slug(workspaces.MEMBERSHIP)}. It carries three shortcuts, all working:"
	)

	w.table(
		("Shortcut", "What it is"),
		[
			[
				"My Memberships",
				"/api/method/vmmsx.api.member.my_memberships — every membership they hold, with"
				" status, validity and whether a certificate is available",
			],
			[
				"Download My Certificate",
				"/api/method/vmmsx.api.member.download_my_certificate — their own certificate as a"
				" PDF, answered from the session with no arguments",
			],
			[
				"My Registrations",
				f"{workspaces.MEMBERSHIP_FORM_ROUTE}/list — the web form's own list of their submissions",
			],
		],
		(2.05, 4.45),
	)

	w.p(
		"The certificate is rendered from the template the membership type points at, and it is"
		" never stored: it is built from the membership every time it is asked for. If you uploaded"
		" a society logo in step 1, it is embedded in the PDF."
	)

	w.note(
		"Try it as somebody else and you are refused. A certificate belongs to the member it names,"
		" recognised through the login on their Red Profile rather than through whoever created the"
		f" record. The only other people who may print one hold {kenya.ROLE_MEMBERSHIP_APPROVER},"
		" because that is what the society put in vmms_certificate_print_role."
	)


def _cross(w) -> None:
	w.h1("Step 6 — cross-register")

	w.p(
		"Log in as the person who is already a volunteer, go back to"
		f" /app/{_slug(workspaces.LANDING)} — the landing workspace stays visible after approval,"
		" deliberately — and register as a member. Or the other way round; the order does not"
		" matter."
	)

	w.h2("What to check")

	w.bullets(
		[
			"There is still exactly one Red Profile for that login. The second registration resolved"
			" it rather than creating another.",
			"Their profile now carries two affiliation rows, volunteer and member, both Active."
			" Each satellite wrote its own and neither disturbed the other's.",
			"They hold both roles and are shown both workspaces.",
			"My Volunteer Record still returns their volunteer record and My Memberships still"
			" returns their memberships. Being both does not merge the two.",
		]
	)


def _troubleshooting(w, site: str) -> None:
	w.h1("If something does not work")

	w.table(
		("Symptom", "Cause", "Fix"),
		[
			[
				"A brand-new account lands on an ERPNext or HR workspace",
				"other apps ship workspaces with no role restrictions, so they are visible to every"
				" desk user",
				"use Frappe's Module Profile to block those modules, or demonstrate with"
				f" /app/{_slug(workspaces.LANDING)} directly",
			],
			[
				"The Registration workspace does not exist",
				"vmms_self_service_role is empty, or names a role that was deleted",
				"set it on National Society Settings and run vmmsx.registration.services.workspaces.install",
			],
			[
				"An approved volunteer sees no My Volunteering workspace",
				"vmms_volunteer_member_role is empty, so nothing was granted and nothing was built",
				"set it, run the installer, and re-run the approval or call volunteer.refresh on the record",
			],
			[
				"The approver cannot open the application routed to them",
				"vmms_volunteer_scope_role is empty, so core's geo scoping fails closed",
				"point it at a role the approver holds a Geo Assignment for",
			],
			[
				"Submitting the volunteer form is refused",
				"the branch chosen is at a level the workflow's Allowed Anchor Levels does not permit",
				"choose a county or a branch, or widen the workflow's anchor levels",
			],
			[
				"A fee-bearing membership will not submit",
				"onerc_payments is not installed, or no gateway is active",
				f"install it and set an active gateway, or use the {kenya.TYPE_LIFE} type, which is free",
			],
			[
				"A certificate has no logo",
				"no logo has been uploaded on National Society Settings",
				"upload one; nothing else changes",
			],
		],
		(1.85, 2.30, 2.35),
	)

	w.p(
		"To start again from a clean society on a scratch site:"
		f" bench --site {site} reinstall, then repeat from step 1."
	)


# --- limits ----------------------------------------------------------------


def _not_built(w) -> None:
	w.h1("What is not built, and what is only partly built")

	w.lead(
		"Read this before demonstrating. Everything above works; the following does not, or does not"
		" yet, and it is listed so that nobody finds out in front of an audience."
	)

	w.h2("Not built at all")

	w.bullets(
		[
			"**Self-service proof of membership.** A registrant cannot attach a document — an ID, a"
			" letter, a previous card — to their registration, and nothing asks them to. There is no"
			" upload step and no review of one.",
			"**Event registration inside this app.** The portal's Events screen is real and lists"
			" events a society has published in Buzz, but every card hands off: its button is a"
			" full navigation to Buzz's own event page, because Buzz owns ticket types, payment,"
			" confirmation and check-in. There is no roster, RSVP or check-in in vmmsx and there is"
			" no VMMS Event doctype. Demonstrate the browse, then follow the link and demonstrate"
			" the rest in Buzz. On a bench with no Buzz installed the screen says so on the page."
			" The events on the *landing* page are still wording somebody typed into content"
			" blocks, not records, so do not present those as a calendar.",
			"**Browsing open opportunities.** A volunteer can see the deployments they are on. No"
			" endpoint exposes open deployment requests to the volunteers who might answer them, so"
			" the matching shown on the landing page is a description of candidate matching, which"
			" runs the other way round: people for a deployment, not deployments for a person.",
			"**Branch analytics.** No aggregation endpoint exists. The counts on the portal's"
			" coordinator overview are real; growth, retention, revenue and leaderboards are not"
			" built at all.",
			"**Payment from the member's own screen.** A fee-bearing membership creates a payment"
			" transaction, and settling it is the payments app's business. There is no pay button on"
			" any vmmsx surface.",
			"**Renewal from the desk.** No desk surface offers to renew a lapsed membership;"
			" somebody registering again on a web form creates a second one, which is supported but"
			" is not a renewal. The portal's Membership screen *does* offer renewal, and only when"
			" the server says the membership is renewable, so this gap is now a desk gap rather"
			" than a product one.",
			"**Notification of a decision.** The Notifications module is real: a branch or the"
			" national office writes a VMMS Announcement and it reaches every volunteer and member"
			" at or beneath that node, in the portal's Notifications tab and optionally by email."
			" What is *not* wired is the lifecycle events — nobody is told automatically when their"
			" application is approved or their membership activates. Those still arrive only as"
			" Frappe's own assignment notifications, which the tab does show. So demonstrate an"
			" announcement being written and read; do not promise an automatic approval email.",
			"**Withdrawing a role.** Exit, suspension and lapse leave the person holding the role"
			" they were granted. Off-boarding is a society's act, deliberately.",
		]
	)

	w.h2("Built, and only partly")

	w.bullets(
		[
			"**Time logs.** The general kind of log works and is listed on the volunteer workspace."
			" The deployment kind works too, and its field is now a real Link to VMMS Deployment,"
			" but a deployment log is accepted only for a deployment whose roster lists the"
			" volunteer filing it. This seed writes no terms of reference and no deployment, because"
			" both name real work a society does, so on a freshly seeded bench there is nothing to"
			" log deployment time against until somebody creates one.",
			"**Certifications and the learning system.** Certifications are real and complete. A"
			" certification carries an expiry computed from its type's validity period, whether it"
			" has lapsed is derived every time it is asked rather than stored, a lapsed one a"
			" society treats as a requirement makes its holder non-deployable while leaving them"
			" Active, and deployment matching excludes such a volunteer on the date the work"
			" starts. Two ways to hold one: a coordinator records it, or a mapped course is"
			" completed in a learning system. Neither needs the other — on a bench with no LMS the"
			" seam is dormant and the manual path is untouched, which is a supported way to run"
			" rather than a broken integration.",
			"**What is empty here is what this seed does not write.** No certification type, no"
			" course mapping and no held certification, because each names a real qualification a"
			" society recognises and inventing one would put a placeholder on somebody's training"
			" record. So a freshly seeded volunteer opens My Certifications and sees nothing, and"
			" is deployable because nothing has lapsed. Create a VMMS Certification Type and record"
			" one against a volunteer to see the whole rule work.",
			"**The volunteer's own surfaces are read-only.** My Time Logs is a list view; My"
			" Certifications is an endpoint, because the lapse it reports is derived at the moment"
			" of asking and a list view can only show stored columns. Neither lets a volunteer"
			" write. A volunteer cannot file their own time from the workspace, because whether a"
			" society wants that is a policy decision and granting it by default would be this app"
			" making it.",
		]
	)

	w.h2("Working as designed, but worth explaining")

	w.bullets(
		[
			"**A member's list of memberships in the desk is empty.** Core's geo scoping fails"
			" closed, and a member holds no Geo Assignment. Their own memberships come from the"
			" possessive endpoint, which is what the workspace shortcut points at.",
			"**Registration stays visible after approval.** It is how somebody who is already a"
			" volunteer registers as a member.",
			"**A person registered from paper gets no role.** They have no login to grant one to."
			" The approval and the activation work exactly the same; only the grant is skipped.",
		]
	)


def _slug(label: str) -> str:
	"""How the desk routes to a workspace: lower case, spaces to dashes."""
	return label.lower().replace(" ", "-")


if __name__ == "__main__":
	print(main())
