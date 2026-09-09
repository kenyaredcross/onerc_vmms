# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Building a multi-stage approval ladder, and walking one application up it.

    bench --site vmms.localhost execute vmmsx.docs.approval_ladder.main

The third standalone artefact, alongside `walkthrough.py` (the KRCS setup and
registration journey) and `gambia_setup_guide.py` (one society's day one). This
one answers a narrower question than either: *how do I put three approvers in a
row, and how does an application get past all three?*

**Every step in it was run.** The sequence below — three roles, three users,
three Geo Assignments, three doctype permissions, a three-stage workflow, a
registration through the portal endpoint and three decisions — was executed
against a real site inside a transaction that was rolled back afterwards. The
refusal messages quoted in the troubleshooting section are the strings the code
actually threw, not paraphrases, and the DTOs are the dicts the endpoints
actually returned.

Society-specific names come from `vmmsx/seed/kenya.py`, the same way the
walkthrough takes them, so the guide cannot drift from the seed it tells people
to run. The three coordinator roles are this document's own worked example: a
society names its own, and that is the point being demonstrated.

Written to `docs/`, which is git-ignored, exactly like the other artefacts: it
is a build output and a committed binary is a file nobody can diff.
"""

from datetime import datetime
from pathlib import Path

from vmmsx.docs.writer import Writer
from vmmsx.seed import kenya
from vmmsx.seed import kenya_geography as geography

APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = APP_ROOT / "docs" / "multi-stage-approval-walkthrough.docx"

TITLE = kenya.ORGANIZATION_NAME
SUBTITLE = "Building a Multi-Stage Approval Ladder"

BLURB = (
	"Three approvers, one behind the other, and one volunteer application walked all the way up."
	" Create the roles, create the people, place them on the hierarchy, configure the stages, then"
	" register and approve. Every command, click-path, response and refusal message in this guide"
	" was run against a real site before it was written down."
)

SITE = "vmms.localhost"

APPLICATION_DOCTYPE = "VMMS Volunteer Application"
WORKFLOW_DOCTYPE = "VMMS Approval Workflow"

# --- the worked example ---------------------------------------------------
#
# Three roles this society decides it wants. They are named here, in a document
# module, for the same reason the Gambia guide names its own: a guide about
# configuration has to show a configuration. No behaviour reads them.

ROLE_BRANCH = "Branch Coordinator"
ROLE_COUNTY = "County Coordinator"
ROLE_NATIONAL = "National Volunteering Manager"

# The rungs. Each row: role, login, person, which seeded node they sit at, and
# the label of the stage that names the role.
LADDER = (
	{
		"role": ROLE_BRANCH,
		"user": "branch.coord@krcs.demo",
		"person": "Peter Mwangi",
		"node": kenya.SUB_COUNTY_NODES[0],
		"level": kenya.LEVELS[2]["name"],
		"stage": "Branch Review",
		"sequence": 1,
		"sla": 5,
		"can_reject": True,
	},
	{
		"role": ROLE_COUNTY,
		"user": "county.coord@krcs.demo",
		"person": "Esther Njeri",
		"node": kenya.PRIMARY_COUNTY,
		"level": kenya.LEVELS[1]["name"],
		"stage": "County Endorsement",
		"sequence": 2,
		"sla": 7,
		"can_reject": False,
	},
	{
		"role": ROLE_NATIONAL,
		"user": "national.vm@krcs.demo",
		"person": "Alice Odhiambo",
		"node": kenya.NATIONAL_NODE,
		"level": kenya.LEVELS[0]["name"],
		"stage": "National Approval",
		"sequence": 3,
		"sla": 10,
		"can_reject": True,
	},
)

APPLICANT_USER = "kevin.otieno@krcs.demo"
APPLICANT_PERSON = "Kevin Otieno"
APPLICANT_FIRST = "Kevin"
APPLICANT_LAST = "Otieno"

# What the verified run produced. Quoted rather than invented: an application
# name a reader sees in their own site will differ, and the guide says so.
EXAMPLE_APPLICATION = "VAPP-00002"
EXAMPLE_VOLUNTEER = "VOL-00004"


def main(path: str | None = None, site: str | None = None) -> str:
	"""Build the guide and return where it was written."""
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
			("Site used to verify every step", site),
			("Built from", "vmmsx/docs/approval_ladder.py — regenerate, do not edit the .docx"),
			("Assumes", "vmmsx.seed.kenya.main has been run on the site"),
			("Depends on", "onerc_core"),
		],
		blurb=BLURB,
	)

	if outline is not None:
		w.contents(outline)

	_what(w)
	w.page_break()
	_before(w, site)
	w.page_break()
	_roles(w, site)
	_people(w, site)
	w.page_break()
	_permissions(w, site)
	_workflow(w, site)
	w.page_break()
	_register(w, site)
	w.page_break()
	_approve(w, site)
	w.page_break()
	_after(w, site)
	_variations(w)
	w.page_break()
	_trouble(w, site)
	w.page_break()
	_script(w, site)

	return w


# --- what you are building -------------------------------------------------


def _what(w) -> None:
	w.h1("What you are building")

	w.lead(
		"A volunteer application that has to pass three people in order — the branch it was made"
		" at, the county above it, and the national office — where each of those three is a"
		" specific named person rather than anybody who happens to hold a role."
	)

	w.h2("The ladder")

	w.table(
		["Rung", "Stage", "Role it names", "Who holds it", "Where they sit"],
		[
			[
				str(rung["sequence"]),
				rung["stage"],
				rung["role"],
				f"{rung['person']} ({rung['user']})",
				f"{rung['node']} ({rung['level']})",
			]
			for rung in LADDER
		],
		[0.5, 1.4, 1.5, 1.9, 1.2],
	)

	w.caption(
		"An application made at "
		f"{kenya.SUB_COUNTY_NODES[0]} climbs all three. Nothing about the three is written in code:"
		" they are rows in one configuration record."
	)

	w.h2("The two questions, and why they are separate")

	w.p("Everything in this guide follows from one split, and if it is clear the rest is mechanical.")

	w.bullets(
		[
			"A Frappe Role answers what. Holding "
			f"{ROLE_COUNTY} is a set of permissions on doctypes: what you may read, write, create.",
			"A Geo Assignment answers where. Holding that same role at "
			f"{kenya.PRIMARY_COUNTY} grants authority over "
			f"{kenya.PRIMARY_COUNTY} and everything beneath it, and nowhere else.",
			"An approval stage names a role. The engine then asks core who holds that role"
			" nearest above this application's Geo Node, and routes to those people by name.",
		]
	)

	w.p(
		"So an approver needs both halves. A role with no Geo Assignment resolves to nobody; a Geo"
		" Assignment for a role the user does not hold grants nothing at all. Both are checked by"
		" the same SQL in core, so they cannot disagree, and both failures look identical from the"
		" outside: an application routed to nobody. Section 11 is mostly about telling them apart."
	)

	w.h2("There are no desk approval buttons, and there never will be")

	w.p(
		"Frappe's native Workflow gates a transition on a role plus a condition that cannot call"
		" this app's code. It can ask whether the acting user holds "
		f"{ROLE_COUNTY}. It cannot ask whether they are the specific "
		f"{ROLE_COUNTY} this application routed to. Those are different questions, and only the"
		" second one is authorisation here."
	)

	w.p(
		"Every decision therefore goes through vmmsx/api/approvals.py, which recomputes the routing"
		" from Geo Assignment on every call and refuses anybody who is not in the answer. The"
		" manager console at /portal/admin/queue is a screen over that endpoint, not a second"
		" way in. Administrator is refused too, which surprises people the first time and is"
		" correct: privilege is not the same as being the person a document was routed to."
	)


# --- before you start ------------------------------------------------------


def _before(w, site: str) -> None:
	w.h1("Before you start")

	w.lead(
		"Ten minutes of reading the site you actually have, so that nothing in the next six"
		" sections is a surprise."
	)

	w.h2("What must already be true")

	w.bullets(
		[
			"onerc_core and vmmsx are installed on the site and migrated.",
			"A society exists: geo levels, geo nodes, and National Society Settings filled in. If"
			" it does not, run the seed below and you have one.",
			"You can sign in as an administrator.",
		]
	)

	w.code(
		f"bench --site {site} execute vmmsx.seed.kenya.main\n"
		f"bench --site {site} execute vmmsx.seed.kenya_operations.main    # optional demo data"
	)

	w.p(
		f"The seed is idempotent and reports created or exists for every record, so running it on a"
		f" site that already has it changes nothing. It builds the hierarchy this guide uses:"
		f" {kenya.NATIONAL_NODE} at the top, all {len(kenya.COUNTY_NODES)} of Kenya's counties"
		f" beneath it, and {geography.total_sub_counties()} sub-counties beneath those. This guide"
		f" works down one branch of it: {kenya.NATIONAL_NODE}, then {kenya.PRIMARY_COUNTY}, then"
		f" {kenya.SUB_COUNTY_NODES[0]}."
	)

	w.h2("Geo Node names are opaque, and you will need the real ones")

	w.p(
		"A Geo Node is named GEO-00022, not "
		f"{kenya.SUB_COUNTY_NODES[0]}. That is deliberate — mutable data never goes in a primary key,"
		" because a society that renames a branch would otherwise break every record pointing at"
		" it. The desk shows you the label; scripts need the docname. Get both:"
	)

	w.code(
		f"bench --site {site} console\n"
		">>> frappe.get_all('Geo Node', fields=['name', 'geo_node_name', 'geo_level'],\n"
		"...                order_by='lft')"
	)

	w.note(
		"On the site this guide was verified against, the three nodes came back as GEO-00022"
		f" ({kenya.SUB_COUNTY_NODES[0]}), GEO-00020 ({kenya.PRIMARY_COUNTY}) and GEO-00019"
		f" ({kenya.NATIONAL_NODE}). Yours will differ if anything else was seeded first. Read them"
		" rather than copying these."
	)

	w.h2("One workflow per doctype — you are almost certainly editing, not creating")

	w.p(
		f"A {WORKFLOW_DOCTYPE} names the doctype it governs, and the engine looks one up by that"
		f" field. If {APPLICATION_DOCTYPE} already has a workflow, adding stages means opening that"
		" record and adding rows to its Stages table. A second workflow record for the same doctype"
		" is not a second ladder; it is an ambiguity, and which one wins is not something to find"
		" out on a live application."
	)

	w.code(
		f"bench --site {site} console\n"
		f">>> frappe.get_all('{WORKFLOW_DOCTYPE}', fields=['name', 'workflow_for'])"
	)

	w.p(
		"On a bench where another society was seeded first, the workflow you find is theirs: it"
		" permits their levels and names roles their approvers hold. Widening it is what"
		" kenya_operations.py's _reconcile_workflows does, and doing it by hand is the same job."
	)

	w.h2("A society this size is three records deep, and each one fails closed")

	w.table(
		["If this is missing", "What you see", "Where it is set"],
		[
			[
				"The Frappe role on the user",
				"Routed to nobody. The stage is blocked and waits for an escalation.",
				"User form, Roles table",
			],
			[
				"The Geo Assignment",
				"Identical symptom: routed to nobody.",
				"Geo Assignment, new record",
			],
			[
				"Read and write on the governed doctype",
				"The approver can be routed to, and then cannot open or save the record.",
				"Role Permissions Manager",
			],
		],
		[1.8, 2.7, 2.0],
	)


# --- step 1: roles ---------------------------------------------------------


def _roles(w, site: str) -> None:
	w.h1("Step 1 — Create the three roles")

	w.lead(
		"A role is a society's own word for a job. Nothing in this app ships one, and no source"
		" file names one."
	)

	w.h2("On the desk")

	w.steps(
		[
			"Go to /app/role/new.",
			f"Role Name: {ROLE_BRANCH}.",
			"Tick Desk Access. This matters more than it looks — Frappe derives a user's type from"
			" the roles they hold, and an account with no desk-access role is a Website User who"
			" cannot open a workspace or a form at all.",
			"Leave Disabled unticked. Save.",
			f"Repeat for {ROLE_COUNTY} and {ROLE_NATIONAL}.",
		]
	)

	w.h2("Or from the console")

	w.code(
		f"bench --site {site} console\n"
		">>> for role in (" + ", ".join(f"'{rung['role']}'" for rung in LADDER) + "):\n"
		"...     if not frappe.db.exists('Role', role):\n"
		"...         frappe.get_doc({'doctype': 'Role', 'role_name': role,\n"
		"...                         'desk_access': 1}).insert()\n"
		">>> frappe.db.commit()"
	)

	w.note(
		"Name them whatever your society calls these people. The three names here are an example"
		" and appear in no source file — that is the rule this app is built on, and the reason a"
		" second society is a second configuration rather than a second codebase."
	)


# --- step 2: people --------------------------------------------------------


def _people(w, site: str) -> None:
	w.h1("Step 2 — Create the approvers and place them")

	w.lead(
		"Each rung needs one person who holds the role and is assigned to a node. Two records per"
		" person, and both are required."
	)

	w.h2("The user")

	w.steps(
		[
			"Go to /app/user/new.",
			f"Email: {LADDER[0]['user']}. First and last name: {LADDER[0]['person']}.",
			"User Type: System User.",
			f"In the Roles table, add {ROLE_BRANCH}. Save.",
			f"Set a password: bench --site {site} set-password {LADDER[0]['user']}",
		]
	)

	w.p("The other two are the same, with their own role:")

	w.table(
		["Login", "Person", "Role", "Sits at"],
		[[rung["user"], rung["person"], rung["role"], rung["node"]] for rung in LADDER],
		[1.9, 1.3, 1.8, 1.5],
	)

	w.h2("The placement")

	w.p(
		"A Geo Assignment is core's answer to where. It is the record that turns holding a role"
		" into authority somewhere, and without it the role grants nothing anywhere."
	)

	w.steps(
		[
			"Go to /app/geo-assignment/new.",
			f"User: {LADDER[0]['user']}.",
			f"Role: {ROLE_BRANCH}. It must be the same role the stage will name.",
			f"Geo Node: {LADDER[0]['node']}.",
			"Is Active: ticked. Leave Valid From and Valid To empty unless the authority is"
			" genuinely time-boxed — an acting coordinator covering three months, for instance."
			" Both dates are honoured by routing on the day it runs.",
			"Save, and repeat for the other two at their own nodes.",
		]
	)

	w.note(
		"One row per role. A person doing two jobs at the same node needs two rows, because"
		" 'where may I approve volunteers' and 'where may I see members' are different questions"
		" with different answers, and the role is load-bearing in both."
	)

	w.h2("Check it before you go any further")

	w.p(
		"Core will tell you exactly who it thinks holds a role at a node. If this returns an empty"
		" list, stop here: nothing downstream can work, and every later symptom will point"
		" somewhere misleading."
	)

	w.code(
		f"bench --site {site} console\n"
		">>> from onerc_core.access.services import scope\n"
		f">>> scope.holders_at('GEO-00022', '{ROLE_BRANCH}')\n"
		f"['{LADDER[0]['user']}']"
	)

	w.p(
		"An empty list with the Geo Assignment plainly on screen means the user does not hold the"
		" role. Core's rule is one piece of SQL — the assignment must be active, inside its dates,"
		" and the user must hold the role in tabHas Role — and it is the same rule the read-scope"
		" query uses. That is on purpose: routing can never name somebody who would then be unable"
		" to open the document."
	)

	w.note(
		"This is the single most common failure when setting up a ladder by hand, and it looks"
		" nothing like its cause. On the site this guide was verified against, one demo user had a"
		f" Geo Assignment for {kenya.ROLE_VOLUNTEER_APPROVER} at a region and did not hold the"
		" role — applications there routed to nobody, with every record looking correct."
	)


# --- step 3: permissions ---------------------------------------------------


def _permissions(w, site: str) -> None:
	w.h1("Step 3 — Let each role act on the record")

	w.lead(
		"Recording a decision saves the application. A role that cannot write it can be routed to"
		" and then fails at the last moment, in front of the approver."
	)

	w.p(
		f"The shipped {APPLICATION_DOCTYPE} JSON grants only System Manager, deliberately: which"
		" society role may touch the register is configuration, not something this app decides for"
		" you. So each of the three roles needs read, write, create and share on it."
	)

	w.h2("On the desk")

	w.steps(
		[
			"Go to /app/permission-manager.",
			f"Document Type: {APPLICATION_DOCTYPE}. Role: {ROLE_BRANCH}. Level 0.",
			"Add a rule if none exists, then tick Read, Write, Create and Share.",
			f"Repeat for {ROLE_COUNTY} and {ROLE_NATIONAL}.",
		]
	)

	w.h2("Or from the console")

	w.code(
		f"bench --site {site} console\n"
		">>> from frappe.permissions import add_permission, update_permission_property\n"
		">>> for role in (" + ", ".join(f"'{rung['role']}'" for rung in LADDER) + "):\n"
		f"...     add_permission('{APPLICATION_DOCTYPE}', role, 0)\n"
		"...     for perm in ('read', 'write', 'create', 'share'):\n"
		f"...         update_permission_property('{APPLICATION_DOCTYPE}', role, 0, perm, 1)\n"
		f">>> frappe.clear_cache(doctype='{APPLICATION_DOCTYPE}')\n"
		">>> frappe.db.commit()"
	)

	w.note(
		"Create looks unnecessary for somebody who only approves, and it is there for the"
		" coordinator who types up a paper application on somebody's behalf. Drop it if that is not"
		" a job your coordinators do."
	)

	w.h2("What this does not need")

	w.p(
		f"{APPLICATION_DOCTYPE} is not registered for geo scoping, so there is no scope role setting"
		" to fill in for it. VMMS Volunteer — the record that exists after approval — is scoped, on"
		" vmms_volunteer_scope_role in National Society Settings, and that setting ships empty and"
		" fails closed. If your coordinators should see the volunteer register as well as the"
		" applications, name a role there. It is a separate decision and this guide does not need"
		" it."
	)


# --- step 4: the workflow --------------------------------------------------


def _workflow(w, site: str) -> None:
	w.h1("Step 4 — Build the ladder")

	w.lead(
		f"One {WORKFLOW_DOCTYPE} record, three rows in its Stages table. This is the whole of the"
		" multi-stage configuration."
	)

	w.h2("Open the workflow")

	w.p(
		f"Go to /app/vmms-approval-workflow and open the record whose Governs is"
		f" {APPLICATION_DOCTYPE}, or create one if there is none. The header fields:"
	)

	w.table(
		["Field", "Value", "Why"],
		[
			[
				"Governs",
				APPLICATION_DOCTYPE,
				"The doctype this ladder applies to. Checked against the approval contract when you"
				" save, so a doctype that cannot carry an approval is refused here rather than at the"
				" first application.",
			],
			[
				"Geo Node Field",
				"geo_node",
				"Which field holds the anchor. It must be a mandatory Link to Geo Node — the save"
				" refuses anything else, because an unplaced record is unroutable and invisible.",
			],
			[
				"Applicant Field",
				"red_profile",
				"Who the application is about. Set it: it is what makes one-open-application-per-person"
				" and the re-application cooldown work. Left empty, both fall back to the record's"
				" owner, which is the clerk who typed it and not the person it concerns.",
			],
			[
				"Allow Withdrawal",
				"Ticked",
				"Lets the applicant take it back while it is still open.",
			],
			[
				"Application Expiry Days",
				"0",
				"Zero means never. A number here lets the daily sweep close applications nobody moved.",
			],
			[
				"Reapplication Cooldown Days",
				"0",
				"How long after a rejection somebody must wait before applying again.",
			],
		],
		[1.4, 1.4, 3.7],
	)

	w.h2("Allowed anchor levels")

	w.p(
		"The table under Anchor names the geo levels an application may be anchored at. Empty means"
		" any active level. This guide uses one row:"
		f" {kenya.LEVELS[2]['name']}, so applications must be made at a sub-county and not at the"
		" county above it."
	)

	w.note(
		"That is this guide's own choice, and it is the opposite of what the Kenya seed configures."
		f" The seed names the {kenya.LEVELS[1]['name']} and only the {kenya.LEVELS[1]['name']},"
		" because that society decided approval happens there — see the note above LEVELS in"
		" seed/kenya.py. This guide overwrites the row on purpose, because a three-rung ladder"
		" needs an application that starts at the bottom of one, and rewriting a configuration"
		" record is exactly what the guide is demonstrating."
	)

	w.p(
		"This is configuration for a reason. One society lets a volunteer application sit at county"
		" level, another requires ward, a third anchors deployments at region and members at branch."
		" No source file in this app contains the word county, and adding a level here is the whole"
		" of expressing that policy."
	)

	w.h2("The three stages")

	w.p("Add three rows to Stages. Sequence is what orders them; row order is not.")

	w.table(
		["Column", "Rung 1", "Rung 2", "Rung 3"],
		[
			["Sequence", "1", "2", "3"],
			["Stage Label"] + [rung["stage"] for rung in LADDER],
			["Required Role"] + [rung["role"] for rung in LADDER],
			["Resolution Rule", "nearest_ancestor", "nearest_ancestor", "nearest_ancestor"],
			["Completion Rule", "single", "single", "single"],
			["Can Reject", "Yes", "No", "Yes"],
			["Is Optional", "No", "No", "No"],
			["SLA Days"] + [str(rung["sla"]) for rung in LADDER],
			["On SLA Breach", "escalate_up", "escalate_up", "escalate_up"],
		],
		[1.4, 1.7, 1.7, 1.7],
	)

	w.caption(
		"Rung 2 endorses only. That is a real policy — a county that may pass an application on or"
		" sit on it, but not kill it — and the workflow refuses to save unless at least one stage"
		" can say no."
	)

	w.h3("What each column decides")

	w.bullets(
		[
			"Sequence — the order. Gaps are fine, ties are refused, because order would then depend"
			" on row order and nothing may rely on that.",
			"Stage Label — display only. Nothing in this app compares a stage label to anything; a"
			" test walks the syntax tree of every source file and fails if one ever does. Rename"
			" freely.",
			"Required Role — the role routing looks for. This is the join between Step 1 and here.",
			"Resolution Rule — how to find holders of that role. nearest_ancestor walks up from the"
			" application's node and stops at the first node that has any, so authority granted high"
			" covers everything below without a row per branch.",
			"Completion Rule — how many must act. single routes to one named person; any_of routes"
			" to everybody and the first to answer decides; all_of needs every one of them.",
			"Can Reject — whether this rung may terminate the application, or only pass it on.",
			"Is Optional — whether the rung is skipped when it resolves nobody. A non-optional stage"
			" that resolves nobody is entered anyway, blocked and escalated, because 'nobody needed"
			" to sign this' and 'nobody could' must not look the same.",
			"SLA Days and On SLA Breach — the clock, and what being late does. Escalating widens who"
			" may act to the nearest holder above; it never removes the original approver's"
			" authority.",
		]
	)

	w.h3("The guardrails")

	w.p(
		"The workflow will refuse to save rather than let you build a ladder that cannot work. Each"
		" of these is a real refusal you may meet:"
	)

	w.bullets(
		[
			"Two stages sharing a sequence.",
			"A stage with an SLA under one day — a queue with no clock is a queue nobody is watching.",
			"A stage using at_level with no Geo Level, or fixed_node with no node.",
			"Every stage set to endorse only, so an application could only ever be approved.",
			"A stage that needs all_of, is not optional, and does nothing on breach — it can stall"
			" forever with nobody told. Make it optional or give it an escalation.",
			"A governing doctype that does not satisfy the approval contract, or a Geo Node Field"
			" that is free text or not mandatory.",
		]
	)

	w.h3("From the console instead")

	w.code(
		f"bench --site {site} console\n"
		f">>> wf = frappe.get_doc('{WORKFLOW_DOCTYPE}', {{'workflow_for': '{APPLICATION_DOCTYPE}'}})\n"
		">>> wf.stages = []\n"
		">>> for seq, label, role, sla, reject in (\n"
		+ "".join(
			f"...         ({rung['sequence']}, '{rung['stage']}', '{rung['role']}',"
			f" {rung['sla']}, {1 if rung['can_reject'] else 0}),\n"
			for rung in LADDER
		)
		+ "... ):\n"
		"...     wf.append('stages', {'sequence': seq, 'stage_label': label,\n"
		"...                          'required_role': role, 'resolution_rule': 'nearest_ancestor',\n"
		"...                          'completion_rule': 'single', 'can_reject': reject,\n"
		"...                          'is_optional': 0, 'sla_days': sla,\n"
		"...                          'on_sla_breach': 'escalate_up'})\n"
		">>> wf.allowed_anchor_levels = []\n"
		f">>> wf.append('allowed_anchor_levels', {{'geo_level': '{kenya.LEVELS[2]['key']}'}})\n"
		">>> wf.applicant_field = 'red_profile'\n"
		">>> wf.save()\n"
		">>> frappe.db.commit()"
	)

	w.note(
		"Each stage row gets an opaque name of its own, like b5lqp6h527, and that is what an"
		" application stores in approval_stage. Deleting a stage while an application sits in it"
		" leaves the application pointing at a stage that no longer exists, and the engine says so"
		" rather than guessing. Edit a live ladder in a quiet moment."
	)


# --- step 5: register ------------------------------------------------------


def _register(w, site: str) -> None:
	w.h1("Step 5 — Register as a volunteer")

	w.lead(
		"Three doors, one road. All of them end in the same insert, the same identity rules and the"
		" same call into the engine."
	)

	w.h2("Make an account")

	w.p(
		f"Somebody registering needs a login first. Either let them sign themselves up — Website"
		f" Settings, Disable Signup unticked, and Portal Settings' Default Role naming"
		f" {kenya.ROLE_APPLICANT} — or create one:"
	)

	w.code(
		f"bench --site {site} console\n"
		f">>> frappe.get_doc({{'doctype': 'User', 'email': '{APPLICANT_USER}',\n"
		f"...                 'first_name': '{APPLICANT_FIRST}', 'last_name': '{APPLICANT_LAST}',\n"
		"...                 'send_welcome_email': 0, 'user_type': 'System User',\n"
		f"...                 'roles': [{{'role': '{kenya.ROLE_APPLICANT}'}}]}}).insert()\n"
		">>> frappe.db.commit()\n"
		f"$ bench --site {site} set-password {APPLICANT_USER}"
	)

	w.note(
		"No Red Profile is created here, and none should be. It is claimed on the person's first"
		" registration, from their login, and there is exactly one per login ever — which is what"
		" makes somebody who volunteers and later joins as a member one person in the register"
		" rather than two."
	)

	w.h2("Door 1 — the portal wizard")

	w.steps(
		[
			f"Sign in as {APPLICANT_USER} and go to /portal/join.",
			"Choose the volunteer path.",
			f"Placement: one select per rung of the ladder. Choose {kenya.NATIONAL_NODE}, then"
			f" {kenya.PRIMARY_COUNTY}, then {kenya.SUB_COUNTY_NODES[0]}. The wizard will not let you"
			" hand the server a level the workflow would refuse.",
			"Identity: first name, last name, phone. The email is shown with a lock on it, because"
			" it is the login and not a form value.",
			"Skills, languages, availability, motivation: type-to-filter selects over whatever your"
			" society has configured.",
			"Identification: an ID type and number. Both are required to submit.",
			"Submit. The application is created and put into motion in one step.",
		]
	)

	w.note(
		"The legacy /register-as-a-volunteer Web Form is unpublished. Volunteer self-registration"
		" has one supported public door because the portal owns the Red Profile and application"
		" transaction together."
	)

	w.h2("Door 2 — the desk, for a paper application")

	w.p(
		f"A coordinator with create permission opens /app/{APPLICATION_DOCTYPE.lower().replace(' ', '-')}/new,"
		" links the applicant's Red Profile, fills in the Serving Branch and the rest, and saves. A"
		" desk insert deliberately creates a draft and waits — only a registration submits itself —"
		" so the coordinator can build it up over several saves and send it on when it is complete."
	)

	w.h2("What is required to submit, as against to exist")

	w.p(
		"Two different gates, and the difference is intentional. A draft may be incomplete; an"
		" application somebody has been asked to answer may not be."
	)

	w.table(
		["Required at creation", "Required at submission"],
		[
			[
				"Serving Branch (the Geo Node anchor), Red Profile, country of citizenship, residency type.",
				"An ID type and ID number. A home area if resident locally, or a country of"
				" residence and an address if abroad. An anchor at a permitted level. No other"
				" undecided application from the same person.",
			]
		],
		[3.2, 3.3],
	)

	w.h2("What comes back")

	w.p("The registration endpoint returns an explicit dict, built field by field. From the verified run:")

	w.code(
		"{\n"
		f'  "name": "{EXAMPLE_APPLICATION}",\n'
		'  "red_profile": "RP-00126",\n'
		'  "geo_node": "GEO-00022",\n'
		f'  "geo_path": "{kenya.SUB_COUNTY_NODES[0]} \u2014 {kenya.PRIMARY_COUNTY} \u2014'
		f' {kenya.NATIONAL_NODE}",\n'
		'  "applied_on": "2026-08-11",\n'
		'  "approval_state": "In Review",\n'
		'  "is_approved": false,\n'
		'  "is_open": true,\n'
		'  "volunteer": null\n'
		"}"
	)

	w.p(
		"In Review, not Submitted: submission resolves the first rung's approvers in the same"
		" transaction, and the application is already sitting in somebody's queue by the time this"
		" dict comes back."
	)

	w.h2("How the applicant follows it")

	w.p(
		"Not through the approvals API. That endpoint checks read permission on the governed"
		" doctype first, and an applicant holds no role that grants it — asked for their own"
		" application, it returns a permission error, which is correct. The portal reads their"
		" application through a possessive endpoint that takes no arguments and answers from the"
		" session, so there is no name to get wrong:"
	)

	w.code(
		">>> from vmmsx.api import registration\n"
		">>> registration.my_open_registrations()\n"
		"{'volunteer': {'doctype': '" + APPLICATION_DOCTYPE + "', 'name': '" + EXAMPLE_APPLICATION + "',\n"
		"                'path': 'volunteer', 'state': 'In Review'},\n"
		" 'member': None}"
	)

	w.p(
		"One entry per kind of registration, and the None is as much of the answer as the"
		" application is. An undecided volunteer application is not a reason to refuse somebody a"
		" membership — the rule that refuses a second registration asks its question of one"
		" doctype, here and in engine.assert_single_open — so the portal blocks only the road it"
		" has an open application on."
	)


# --- step 6: approve -------------------------------------------------------


def _approve(w, site: str) -> None:
	w.h1("Step 6 — Approve, one rung at a time")

	w.lead(
		"Three sign-ins, three decisions. Each one moves the application to the next rung and hands"
		" it to a different person."
	)

	w.h2("Where the work appears")

	w.p(
		"When a stage resolves, the engine assigns the document to those people through Frappe's"
		" own ToDo and assignment machinery, so it lands in a named queue rather than a role-wide"
		" pool. An approver finds it in three places:"
	)

	w.bullets(
		[
			"/portal/admin/queue — the manager console. Approve and Reject are drawn only when"
			" the server says the signed-in person may act, and the server re-asks the same question"
			" on the write.",
			"The desk's own assignment list and notifications.",
			"vmmsx.api.approvals.my_queue, which is what that console calls.",
		]
	)

	w.p(
		"The queue is not merely a list of ToDos. Every candidate is re-checked against routing"
		" before it is returned, so an approver whose Geo Assignment ended yesterday has an empty"
		" queue today whatever their ToDo list says. Here is rung one's queue from the verified"
		" run:"
	)

	w.code(
		"[\n"
		"  {\n"
		f'    "doctype": "{APPLICATION_DOCTYPE}",\n'
		f'    "name": "{EXAMPLE_APPLICATION}",\n'
		'    "state": "In Review",\n'
		'    "geo_node": "GEO-00022",\n'
		f'    "geo_path": "{kenya.SUB_COUNTY_NODES[0]} \u2014 {kenya.PRIMARY_COUNTY} \u2014'
		f' {kenya.NATIONAL_NODE}",\n'
		'    "stage": {\n'
		'      "name": "b5lqp6h527",\n'
		'      "sequence": 1,\n'
		f'      "label": "{LADDER[0]["stage"]}",\n'
		f'      "required_role": "{LADDER[0]["role"]}",\n'
		'      "completion_rule": "single",\n'
		'      "can_reject": true,\n'
		'      "is_optional": false,\n'
		'      "entered_on": "2026-08-11 12:13:06",\n'
		'      "due_on": "2026-08-16 12:13:06",\n'
		'      "is_breached": false,\n'
		'      "days_overdue": 0,\n'
		'      "is_blocked": false\n'
		"    },\n"
		'    "can_act": true,\n'
		'    "approver_count": 1,\n'
		f'    "approvers": ["{LADDER[0]["user"]}"],\n'
		'    "escalated_to": [],\n'
		'    "decisions": []\n'
		"  }\n"
		"]"
	)

	w.note(
		"is_blocked is worth knowing about: true means the stage resolved nobody and is waiting on"
		" an escalation rather than on an approver. A queue screen can then say so instead of"
		" showing an approval with no name against it."
	)

	w.h2("Rung 1 — the branch")

	w.p(
		f"Sign in as {LADDER[0]['user']}, open /portal/admin/queue, open the application and press"
		" Approve. Or, equivalently, from the browser console on any page while signed in as them:"
	)

	w.code(
		"frappe.call('vmmsx.api.approvals.decide', {\n"
		f"    doctype: '{APPLICATION_DOCTYPE}',\n"
		f"    name: '{EXAMPLE_APPLICATION}',\n"
		"    decision: 'Approved',\n"
		"    reason: 'Known to the branch.'\n"
		"})"
	)

	w.p("Or from the terminal, which is the quickest way to walk all three rungs while testing:")

	w.code(
		f"bench --site {site} console\n"
		f">>> frappe.set_user('{LADDER[0]['user']}')\n"
		">>> from vmmsx.api import approvals\n"
		f">>> approvals.decide('{APPLICATION_DOCTYPE}', '{EXAMPLE_APPLICATION}',\n"
		"...                  'Approved', 'Known to the branch.')\n"
		">>> frappe.db.commit()"
	)

	w.p("The response says where it went:")

	w.code(
		"state: In Review\n"
		f"stage: {LADDER[1]['stage']} (sequence 2, {LADDER[1]['role']}, can_reject False)\n"
		f"due_on: 2026-08-18\n"
		f"approvers: ['{LADDER[1]['user']}']"
	)

	w.note(
		"The frappe.set_user line is the whole point of this layer, not a convenience. bench runs"
		" as Administrator, and Administrator is refused: the gate asks whether you are one of the"
		" specific people this document routed to, and privilege is not an answer to that question."
	)

	w.h2("Rung 2 — the county")

	w.code(
		f">>> frappe.set_user('{LADDER[1]['user']}')\n"
		f">>> approvals.decide('{APPLICATION_DOCTYPE}', '{EXAMPLE_APPLICATION}', 'Approved')\n"
		">>> frappe.db.commit()"
	)

	w.p(
		f"No reason is required to endorse. Rung 2 cannot reject at all — it was configured to"
		f" endorse only — and trying returns: {LADDER[1]['stage']} may only endorse this application"
		" onward, not reject it."
	)

	w.h2("Rung 3 — the national office")

	w.code(
		f">>> frappe.set_user('{LADDER[2]['user']}')\n"
		f">>> approvals.decide('{APPLICATION_DOCTYPE}', '{EXAMPLE_APPLICATION}', 'Approved')\n"
		">>> frappe.db.commit()"
	)

	w.p(
		"There is no fourth stage, so the state moves to Approved, the stage is cleared, the"
		" assignments are closed and the volunteer record is created in the same transaction."
	)

	w.h2("The other two decisions")

	w.table(
		["Decision", "What it does", "Notes"],
		[
			[
				"Rejected",
				"Ends the application. State goes to Rejected, the stage is cleared, and no later"
				" rung sees it.",
				"A reason is mandatory: the applicant is entitled to know why. The person's record"
				" is untouched — a rejection ends an application, not a person.",
			],
			[
				"More info requested",
				"Returns the application to the applicant as a Draft.",
				"Review restarts from rung 1 when they resubmit, because what the earlier rungs"
				" endorsed is not what they will be resubmitting.",
			],
		],
		[1.5, 2.6, 2.4],
	)

	w.h2("Deciding twice")

	w.p(
		"Recording the same decision again returns the same answer and writes no second audit row,"
		" which is what makes a double-clicked button harmless. Recording a different one is"
		" refused: You already recorded Approved at this stage. A decision cannot be replaced."
		" Changing your mind is a new stage or a new application, not rewritten history."
	)


# --- step 7: what it produced ----------------------------------------------


def _after(w, site: str) -> None:
	w.h1("Step 7 — What the approval produced")

	w.lead("Approval is not a flag. It is the moment several records come into existence.")

	w.h2("On the site")

	w.bullets(
		[
			"The application's state is Approved, with three rows in its decisions table — one per"
			" rung, each carrying the stage, the approver, the decision, the reason and the"
			" timestamp.",
			f"A VMMS Volunteer record exists ({EXAMPLE_VOLUNTEER} in the verified run), status"
			f" Active, placed at {kenya.SUB_COUNTY_NODES[0]} — the node they applied at.",
			"What the applicant declared — skills, languages, availability, citizenship, residency —"
			" was seeded onto that volunteer record. From here the two are separate: editing one"
			" does not touch the other.",
			f"Their login was granted the {kenya.ROLE_VOLUNTEER} role, named in"
			" vmms_volunteer_member_role on National Society Settings. No role name appears in the"
			" code that grants it. Empty configuration means nothing is granted; no login means"
			" nothing happens.",
			"An affiliation row was written through core, so the register knows this person is a"
			" volunteer of this society. It is a summary of the volunteer record, not a second"
			" source of truth, and nothing branches on it.",
		]
	)

	w.h2("Check it")

	w.code(
		f"bench --site {site} console\n"
		f">>> app = frappe.get_doc('{APPLICATION_DOCTYPE}', '{EXAMPLE_APPLICATION}')\n"
		">>> app.approval_state, app.volunteer\n"
		f"('Approved', '{EXAMPLE_VOLUNTEER}')\n"
		">>> [(d.stage_label, d.approver, d.decision) for d in app.approval_decisions]\n"
		f">>> frappe.get_value('VMMS Volunteer', app.volunteer, ['status', 'home_geo_node'])\n"
		"('Active', 'GEO-00022')\n"
		f">>> frappe.get_roles('{APPLICANT_USER}')"
	)

	w.p(
		f"Signed in as {APPLICANT_USER}, /portal/dashboard now shows a volunteer rather than an"
		" applicant, and the desk shows their own workspace. Their serving branch, status and"
		" joined date are read-only on both, because those are what a branch decided; their name,"
		" phone, gender, date of birth and preferred language are editable, because those are facts"
		" about a person."
	)


# --- variations ------------------------------------------------------------


def _variations(w) -> None:
	w.h1("Changing the shape of the ladder")

	w.lead("Everything below is a different value in the same Stages table. None of it is a code change.")

	w.h2("More than one person on a rung")

	w.table(
		["Completion Rule", "Routes to", "Advances when"],
		[
			[
				"single",
				"One named person — the first of the resolved holders, deterministically, so"
				" re-resolving tomorrow lands on the same person.",
				"That person decides.",
			],
			[
				"any_of",
				"Everybody the rule resolved.",
				"The first of them decides. The others' copies disappear from their queues.",
			],
			[
				"all_of",
				"Everybody the rule resolved.",
				"Every one of them has approved. The queue shrinks as they answer, so somebody who"
				" has already acted stops seeing it.",
			],
		],
		[1.3, 2.7, 2.5],
	)

	w.p(
		"An all_of rung that resolves nobody is never complete, deliberately — returning otherwise"
		" would let a stage nobody could act on approve itself. That is why the workflow refuses to"
		" save an all_of stage that is neither optional nor escalating."
	)

	w.h2("Deciding where a rung resolves")

	w.table(
		["Resolution Rule", "Meaning", "Use it when"],
		[
			[
				"nearest_ancestor",
				"Walk up from the application's node and stop at the first node with any holder of"
				" the role. The node itself counts.",
				"Authority is delegated downward and whoever is closest should decide.",
			],
			[
				"at_level",
				"Resolve at a named Geo Level in this application's chain, however far away that is.",
				"A decision belongs to a tier by policy — the county approves, always, even if a"
				" branch officer holds the role.",
			],
			[
				"fixed_node",
				"Always the holders at one named node, wherever the applicant lives.",
				"A national desk signs everything: the training department, a safeguarding lead.",
			],
		],
		[1.4, 2.7, 2.4],
	)

	w.h2("Rungs that sometimes do not apply")

	w.p(
		"Tick Is Optional and the rung is skipped when it resolves nobody, which is what a society"
		" means by an optional step. Leave it unticked and a rung that resolves nobody is entered"
		" anyway, blocked, and escalated to the nearest holder above. The difference matters: one"
		" says nobody needed to sign this, the other says nobody could."
	)

	w.h2("Clocks and lateness")

	w.p(
		"Every rung has an SLA in days and an action on breach. The daily sweep applies it."
		" escalate_up widens who may act to the nearest holder of the same role above the"
		" application, skipping the people who are already late — handing the document back to them"
		" would be a loop, not an escalation. notify_only is a reminder and none is a deliberate"
		" decision to wait; neither hands anybody else authority, and the gate honours the same"
		" setting the notification does, so the two cannot say different things."
	)

	w.p("A breach only ever widens the set. Being late does not remove an approver's authority.")

	w.h2("Applying the same ladder to memberships")

	w.p(
		"VMMS Membership has its own workflow record, built the same way. One difference is worth"
		" knowing: a membership type carries an approval mode, routed or auto on payment, and a type"
		" set to activate on payment never enters this engine at all. Which one applies is that"
		" field, not a name anywhere in the code."
	)


# --- troubleshooting -------------------------------------------------------


def _trouble(w, site: str) -> None:
	w.h1("When it does not work")

	w.lead(
		"Every message below was produced by the code during the verified run, and is quoted as it"
		" was thrown."
	)

	w.h2("Nobody is in the queue")

	w.p(
		"The application is In Review, its stage is blocked, and approvers is empty. Work down"
		" this list; it is ordered by how often each one is the answer."
	)

	w.steps(
		[
			"Does the user hold the role? Open the User, look at the Roles table. A Geo Assignment"
			" for a role the user does not hold grants nothing, and this is the most common cause"
			" by a distance.",
			"Is the Geo Assignment active, and are its dates open? An assignment outside its"
			" validity window grants nothing today.",
			"Does the assignment name the same role the stage does? A stage naming"
			f" {ROLE_COUNTY} does not see somebody assigned as {ROLE_BRANCH}.",
			"Is the assignment at or above the application's node? nearest_ancestor walks upward"
			" only. Somebody assigned at a sibling branch is not above anything.",
			"Ask core directly, which settles it: scope.holders_at(node, role).",
		]
	)

	w.h2("The refusals, and what each one means")

	w.table(
		["Message", "What happened"],
		[
			[
				"This approval is routed to a specific approver and you are not one of them. Holding"
				" the role is not enough.",
				"You are not in the current rung's resolved set. Either you are the next rung's"
				" approver and it has not got there yet, or you are Administrator, or your"
				" assignment does not cover this node. The message names the role and the place it"
				" resolved against.",
			],
			[
				"Nairobi is at County level. VMMS Volunteer Application may only be anchored at: Branch.",
				"The anchor level rule. The workflow's allowed anchor levels do not include the"
				" level of the node the application was anchored at.",
			],
			[
				"An application cannot be submitted without an identification.",
				"An ID type and number are optional on a Red Profile and mandatory to submit an application.",
			],
			[
				"An applicant living locally must give a Home Area before this application can be submitted.",
				"The residency toggle's other half was not answered. Abroad needs a country of"
				" residence and an address instead.",
			],
			[
				"You already have an application with us that has not been decided yet.",
				"One open application per applicant. Withdraw the first, or decide it, before"
				" starting another.",
			],
			[
				"A rejection needs a reason. The applicant is entitled to know why.",
				"Reject was called with an empty reason.",
			],
			[
				"County Endorsement may only endorse this application onward, not reject it.",
				"That rung has Can Reject unticked.",
			],
			[
				"You already recorded Approved at this stage. A decision cannot be replaced.",
				"A different second decision from the same person at the same rung. The same"
				" decision again is accepted silently and writes nothing.",
			],
			[
				"No approval workflow is configured for VMMS Volunteer Application.",
				"There is no workflow record governing the doctype. Step 4.",
			],
			[
				"VMMS Volunteer Application is not under an approval workflow.",
				"The same thing, seen from the API, which checks the doctype is governed before it"
				" does anything else.",
			],
			[
				"A permission error with no message, when the applicant asks about their own application.",
				"Correct. The approvals API checks read permission on the governed doctype first."
				" The applicant's own view is registration.my_open_registrations, which takes no"
				" arguments.",
			],
		],
		[2.6, 3.9],
	)

	w.h2("Inspecting one application")

	w.p("Everything the engine thinks about a document, in one call:")

	w.code(
		f"bench --site {site} console\n"
		">>> from vmmsx.approvals.services import config, engine\n"
		f">>> doc = frappe.get_doc('{APPLICATION_DOCTYPE}', '{EXAMPLE_APPLICATION}')\n"
		f">>> wf = config.for_doctype('{APPLICATION_DOCTYPE}')\n"
		">>> auth = engine.authorised(doc, wf)\n"
		">>> auth['stage'].stage_label, auth['routed'], auth['escalated'], auth['breached']"
	)

	w.p(
		"routed is who the rung resolved. escalated is who has been admitted because the rung"
		" resolved nobody, or because it is breached and the society asked for escalation."
		" approvers is the union — everybody the gate will admit. None of it is cached: it is"
		" recomputed from Geo Assignment on every call, so an approver who lost their assignment"
		" last week cannot approve today."
	)

	w.h2("Starting over")

	w.p(
		"An approved or rejected application is terminal and nothing may move it again. To rehearse"
		" the ladder a second time, register a second applicant rather than editing the first"
		" application's state by hand — a decided application is history, and a state field edited"
		" in the desk leaves the decisions table, the assignments and the volunteer record"
		" disagreeing with it."
	)


# --- appendix --------------------------------------------------------------


def _script(w, site: str) -> None:
	w.h1("Appendix — the whole setup in one script")

	w.lead(
		"Steps 1 to 4, idempotent, for a demo bench you want standing in a minute. It creates no"
		" application: registering is step 5 and is worth doing through a real door."
	)

	w.p(
		"Save as setup_ladder.py somewhere on the bench, edit the three node names to the docnames"
		f" on your site, and run: bench --site {site} console, then exec(open('setup_ladder.py')"
		".read())."
	)

	w.code(
		"from frappe.permissions import add_permission, update_permission_property\n"
		"\n"
		"BRANCH, COUNTY, NATIONAL = 'GEO-00022', 'GEO-00020', 'GEO-00019'\n"
		"\n"
		"LADDER = (\n"
		+ "".join(
			f"    ({rung['sequence']}, '{rung['stage']}', '{rung['role']}',"
			f" '{rung['user']}',\n"
			f"     '{rung['person'].split()[0]}', '{rung['person'].split()[1]}',"
			f" {('BRANCH', 'COUNTY', 'NATIONAL')[rung['sequence'] - 1]},"
			f" {rung['sla']}, {1 if rung['can_reject'] else 0}),\n"
			for rung in LADDER
		)
		+ ")\n"
		"\n"
		f"DOCTYPE = '{APPLICATION_DOCTYPE}'\n"
		"\n"
		"for seq, label, role, email, first, last, node, sla, reject in LADDER:\n"
		"    if not frappe.db.exists('Role', role):\n"
		"        frappe.get_doc({'doctype': 'Role', 'role_name': role,\n"
		"                        'desk_access': 1}).insert()\n"
		"\n"
		"    if not frappe.db.exists('User', email):\n"
		"        frappe.get_doc({'doctype': 'User', 'email': email, 'first_name': first,\n"
		"                        'last_name': last, 'send_welcome_email': 0,\n"
		"                        'user_type': 'System User'}).insert()\n"
		"\n"
		"    user = frappe.get_doc('User', email)\n"
		"    if role not in frappe.get_roles(email):\n"
		"        user.add_roles(role)\n"
		"\n"
		"    if not frappe.db.exists('Geo Assignment',\n"
		"                            {'user': email, 'role': role, 'geo_node': node}):\n"
		"        frappe.get_doc({'doctype': 'Geo Assignment', 'user': email, 'role': role,\n"
		"                        'geo_node': node, 'is_active': 1}).insert()\n"
		"\n"
		"    add_permission(DOCTYPE, role, 0)\n"
		"    for perm in ('read', 'write', 'create', 'share'):\n"
		"        update_permission_property(DOCTYPE, role, 0, perm, 1)\n"
		"\n"
		"frappe.clear_cache(doctype=DOCTYPE)\n"
		"\n"
		f"workflow = frappe.get_doc('{WORKFLOW_DOCTYPE}', {{'workflow_for': DOCTYPE}})\n"
		"workflow.stages = []\n"
		"\n"
		"for seq, label, role, _e, _f, _l, _n, sla, reject in LADDER:\n"
		"    workflow.append('stages', {'sequence': seq, 'stage_label': label,\n"
		"                               'required_role': role,\n"
		"                               'resolution_rule': 'nearest_ancestor',\n"
		"                               'completion_rule': 'single', 'can_reject': reject,\n"
		"                               'is_optional': 0, 'sla_days': sla,\n"
		"                               'on_sla_breach': 'escalate_up'})\n"
		"\n"
		"workflow.allowed_anchor_levels = []\n"
		f"workflow.append('allowed_anchor_levels', {{'geo_level': '{kenya.LEVELS[2]['key']}'}})\n"
		"workflow.applicant_field = 'red_profile'\n"
		"workflow.allow_withdrawal = 1\n"
		"workflow.save()\n"
		"\n"
		"frappe.db.commit()\n"
		"\n"
		"from onerc_core.access.services import scope\n"
		"\n"
		"for _s, _lab, role, email, _f, _l, node, _sla, _r in LADDER:\n"
		"    print(role, node, scope.holders_at(node, role))\n"
	)

	w.p(
		"The last three lines are the check that matters. Each should print the login you just"
		" created. An empty list means the role and the assignment have not met, and no amount of"
		" configuring stages will fix it."
	)

	w.h2("Then set passwords and walk it")

	w.code(
		"\n".join(f"bench --site {site} set-password {rung['user']}" for rung in LADDER)
		+ f"\nbench --site {site} set-password {APPLICANT_USER}"
	)


if __name__ == "__main__":
	print(main())
