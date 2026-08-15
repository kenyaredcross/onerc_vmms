# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Stipend section of the guide (stage 5).

Field tables are generated from the doctype JSON; every other claim names the
file or function it describes.

Three things in this section are decisions rather than descriptions, and each is
argued rather than asserted: why the attendance grid is one row per volunteer per
day, why the picker cannot leak scope, and why stipend approval is deliberately a
dead end.

The last of those is the reason this section exists in the shape it does. The
approval feature is present and its routing is absent, on purpose, and a guide
that described it as working would send somebody to a demonstration where it does
not. It is written up as what it is: submittable, visibly stuck, and refusing to
guess at an approver.
"""

from vmmsx.docs import doctypes

TITLE = "Stipend"
SUMMARY = (
	"Progress reports, payment forms with a daily attendance grid, the geo-scoped volunteer picker,"
	" and an approval that is deliberately a dead end."
)

REPORT = "VMMS Stipend Progress Report"
REPORT_VOLUNTEER = "VMMS Stipend Report Volunteer"
PAYMENT = "VMMS Stipend Payment Form"
LINE = "VMMS Stipend Attendance Line"


def render(w) -> None:
	w.h1(TITLE)

	_what_it_is(w)
	_report(w)
	_report_volunteer(w)
	_payment(w)
	_line(w)
	_the_grid_shape(w)
	_the_pairing(w)
	_the_picker(w)
	_the_scope_guarantee(w)
	_typing_a_name(w)
	_the_stub(w)
	_why_not_the_engine(w)
	_the_routing_target(w)
	_the_lifecycle(w)
	_scoping(w)
	_configuration(w)
	_not_here_yet(w)
	_what_is_tested(w)


# --- what it is ------------------------------------------------------------


def _what_it_is(w) -> None:
	w.h2("What the Stipend module is")

	w.lead(
		"This is the paperwork a society fills in when it pays volunteers a daily stipend: a"
		" narrative of what a place did over a period, and a form recording who turned up on which"
		" day and what each day was worth."
	)
	w.p(
		"Four doctypes carry it, and they are two documents and their two tables. VMMS Stipend"
		" Progress Report is one period, one place, and many volunteers, with the narrative that"
		" says what they did. VMMS Stipend Payment Form is paired with a report and holds the daily"
		" attendance grid. VMMS Stipend Report Volunteer and VMMS Stipend Attendance Line are the"
		" tables."
	)
	w.p(
		"The services are in vmmsx/stipend/services/, and every one of them is idempotent and takes"
		" documents rather than names. Nothing here resolves an approver, walks the geo tree, or"
		" decides that somebody may act because they hold a role. That matters more in this module"
		" than anywhere else in the app, because the approval this paperwork needs is one the app"
		" cannot route, and the failure mode is a plausible resolver being added that routes it to"
		" the wrong person. stipend/tests/test_delegation.py walks the AST of every file in the"
		" module and fails if one appears."
	)

	w.h3("What is finished, and the one thing that is not")

	w.bullets(
		[
			"The paperwork is finished. Both documents, both tables, the pairing between them, the"
			" grid and its rules, and every total are built and tested.",
			"The volunteer picker is finished. It is geo-scoped to whoever is searching, through the"
			" same core calls the volunteer list view uses, and it cannot be told where to look.",
			"The approval is a stub, deliberately and visibly. Paperwork can be submitted and then"
			" sits in Pending Departmental Approval, which nobody can move, including an"
			" administrator. See 'The approval stub' below before demonstrating this module.",
		]
	)


# --- the doctypes ----------------------------------------------------------


def _doctype_block(w, doctype: str, represents: list[str]) -> None:
	for paragraph in represents:
		w.p(paragraph)

	w.table(
		doctypes.FIELD_TABLE_HEADERS,
		doctypes.fields(doctype),
		doctypes.FIELD_TABLE_WIDTHS,
	)
	w.caption(f"Naming — {doctypes.naming_of(doctype)}")


def _report(w) -> None:
	w.h2(REPORT)

	_doctype_block(
		w,
		REPORT,
		[
			"One period, one place, one narrative, and the people it was about. The narrative is the"
			" report; the table below it says who it covers.",
			"It covers many volunteers, and that is the point of the shape. Filed per person, a"
			" month of a branch's work becomes a stack of documents nobody reads together, and the"
			" payment form would have nothing single to pair with.",
			"geo_node is the ACC-02 anchor, required at creation and checked in"
			" VMMSStipendProgressReport.validate_anchor(). An unplaced report is invisible to geo"
			" scoping, because core's query filter uses IN and IN excludes NULL, so it would exist"
			" with nobody able to see it. Which level it may sit at is ACC-03, the society's"
			" vmms_stipend_anchor_level, and no level name appears anywhere in this module.",
			"routing_departments is derived on every save by stipend/services/department.py and"
			" routed on by nothing. It is described under 'The pending routing target' below.",
		],
	)


def _report_volunteer(w) -> None:
	w.h2(REPORT_VOLUNTEER)

	_doctype_block(
		w,
		REPORT_VOLUNTEER,
		[
			"One volunteer's line on a report. It carries what they did, in the supervisor's own"
			" words, and the department captured for the eventual routing.",
			"The row holds no identity: no name, no email, no phone. Who somebody is stays core's"
			" Red Profile's answer, read through volunteer/services/identity.py, and this row names"
			" a volunteer record rather than describing a person. That is the same rule VMMS Member"
			" and VMMS Deployment Participant follow.",
			"Rows are added through stipend/services/picker.py, which refuses a volunteer the"
			" person adding them may not already see. There is no other door: report.add_volunteer()"
			" calls picker.resolve() before it appends anything.",
		],
	)


def _payment(w) -> None:
	w.h2(PAYMENT)

	_doctype_block(
		w,
		PAYMENT,
		[
			"The money half of a period somebody already described. It is paired with a progress"
			" report, and the pairing is what makes it safe: the report says which days the period"
			" covers, where it happened and who was involved, so the form may pay only those people,"
			" only for those days, and only at that place.",
			"The period is copied from the report on every save by payment._adopt_period() and is"
			" read-only here, so a report whose dates are corrected does not leave a form paying for"
			" days the report no longer covers. The anchor is the exception: geo_node is held on the"
			" form itself, because core filters each doctype on a field of its own and a form scoped"
			" through a link would be a form nobody could scope. It is checked against the report's"
			" anchor on every save, so holding it twice cannot mean holding two different answers.",
			"The currency is the society's, read from National Society Settings through"
			" stipend/services/society.py. No currency code appears in this module. It is set at"
			" creation and left alone afterwards, because a form's amounts were typed in the"
			" currency it carried at the time and a society changing its answer next year is not a"
			" repricing of last year's paperwork.",
			"total_payable is derived from the rows on every save. Per-volunteer totals are not"
			" stored at all; they are computed from the same rows on request. A stored total is a"
			" number that will one day disagree with the rows it claims to add up, and on that day"
			" nobody can tell which of the two is the truth.",
		],
	)


def _line(w) -> None:
	w.h2(LINE)

	_doctype_block(
		w,
		LINE,
		[
			"One volunteer, one day, one amount. The grid is these rows, and the shape is argued in"
			" the next section rather than assumed here.",
			"Nothing computes the amount. There is no rate, no hours-times-rate and no default:"
			" what a society pays for a day is a society's decision, and an app that invented one"
			" would be paying people a number nobody chose. hours is recorded and multiplied by"
			" nothing.",
			"stipend_amount is a Currency field whose options name the parent's currency field, so"
			" a line is always denominated in the form's currency and never in the site's.",
		],
	)


# --- the decisions ---------------------------------------------------------


def _the_grid_shape(w) -> None:
	w.h2("Why the grid is tall and not wide")

	w.p(
		"A payment form has to answer two questions, and they pull in opposite directions. What is"
		" payable to one volunteer for the period? And who attended on a given day?"
	)
	w.p(
		"Modelled tall, as one row per volunteer per day, both are a filter and a sum over the same"
		" table. The first filters on volunteer, the second on attendance_date, and the second works"
		" across payment forms as well as within one, because a date is a value in a column rather"
		" than the name of a column. stipend/services/attendance.py holds both:"
		" per_volunteer() answers the first, on_date() and register_on() answer the second."
	)
	w.p(
		"Modelled wide, as a row per volunteer with a column per day, the first question is easy and"
		" the second is not a query at all. 'Who attended on the fourteenth' becomes 'read the"
		" column called day_14', which cannot be indexed, cannot be asked across a period boundary,"
		" and stops working the moment a society runs a period longer than whatever number of"
		" columns somebody guessed at. It also puts the calendar in the schema: a table of thirty"
		" one columns is a February with seven empty ones, and a migration every time a society"
		" moves to a fortnightly cycle."
	)
	w.note(
		"The wide shape is the one people draw on paper, because on paper a month fits across the"
		" page. The grid a supervisor sees on the form is Frappe's own child-table grid over the"
		" tall rows, so nothing is lost by storing it the way the questions want it stored."
	)

	w.h3("The rules the grid enforces")

	w.p(
		"Every one of these holds for every society, which is why they are code rather than"
		" configuration. They are enforced in attendance.assert_lines(), on every save, so a form"
		" cannot be built wrong and discovered wrong later."
	)
	w.bullets(
		[
			"A volunteer the paired report never mentions cannot be paid. The narrative is what the"
			" money is for, and a payment with nothing behind it is the one shape of mistake this"
			" form exists to make impossible.",
			"A day outside the report's period cannot be paid.",
			"One volunteer has one line per day. That is what makes a day's total the day's total.",
			"An amount is never negative.",
			"A day marked absent carries no stipend. The absence may still be recorded, which is"
			" what the row is for, but a daily stipend is paid for attending.",
			"And the rule read backwards: a volunteer cannot be taken off a progress report while a"
			" paired payment form still pays them. report.remove_volunteer() asks"
			" payment.forms_paying() first, because otherwise the removal would leave every paired"
			" form holding a line the form's own rules forbid: valid on disk, refused the next time"
			" anybody saves it, and confusing at exactly the moment somebody is trying to correct"
			" something.",
		]
	)


def _the_pairing(w) -> None:
	w.h2("What pairing a form with a report actually does")

	w.p(
		"payment.sync() runs from VMMSStipendPaymentForm.validate, so it runs on every save and"
		" there is no state in which the two documents disagree. The order is deliberate: the"
		" pairing is checked first, because every rule after it is stated in terms of a period and a"
		" roster that have to be the report's."
	)
	w.steps(
		[
			"The report is loaded. A form naming none is refused: without one there is no period, no"
			" place, and nobody it is allowed to pay.",
			"The two anchors are compared. A form and its report describe one period of work in one"
			" place, so a mismatch is refused rather than silently preferred one way.",
			"The period is copied from the report onto the form.",
			"The currency is filled from society configuration, at creation only.",
			"Every line of the grid is checked against the roster and the period.",
			"The total is recomputed from the rows.",
		]
	)


def _the_picker(w) -> None:
	w.h2("The volunteer picker")

	w.p(
		"Stipend paperwork names people, and the moment an app lets somebody browse a list of people"
		" it has to answer which people. stipend/services/picker.py is that answer, and it is the"
		" only way a volunteer gets onto a progress report or a payment form."
	)
	w.p(
		"candidates() returns the in-scope register, optionally narrowed by a search term matching a"
		" person's name or email or the volunteer docname. resolve() turns a single identifier into"
		" a volunteer. is_in_scope() and assert_in_scope() are the predicate and the refusal every"
		" write path goes through. api/stipend.py exposes the first two as find_volunteers and"
		" resolve_volunteer, and neither endpoint adds anything the service does not already do."
	)


def _the_scope_guarantee(w) -> None:
	w.h2("The scope guarantee, and the four things that make it hold")

	w.lead(
		"A supervisor can never be shown, or given, a volunteer they are not allowed to see, and"
		" there is no argument by which they could ask to be."
	)

	w.bullets(
		[
			"A Frappe role says whether the register may be read at all. Roles answer what and geo"
			" answers where, and both are asked. This one is asked first because the queries beneath"
			" it use frappe.get_all, which checks no permissions.",
			"The scope is derived from the session and cannot be passed in. Neither candidates() nor"
			" resolve() takes a user, a nodes or a geo_node parameter. A caller supplies what they"
			" are looking for, never who they are or where they may look, so there is no check here"
			" that could be forgotten or got wrong. The signatures are asserted, on the service and"
			" on the endpoints.",
			"The scope comes from core, through the same registration core's own enforcement uses."
			" picker._searchable_nodes() asks registry which role scopes VMMS Volunteer, which is"
			" the society's vmms_volunteer_scope_role setting resolved by core and never a role name"
			" written here, and then asks scope.get_user_geo_scope for that role's nodes. That is"
			" the identical pair of calls behind the volunteer list view's WHERE ... IN, so a"
			" volunteer this service returns is by construction one the supervisor could already"
			" open. This is the same pair deployment/services/matching.py makes, and for the same"
			" reason: neither service computes a scope, both ask core for one.",
			"The search term is applied after the geo filter, never before. Filtering by name and"
			" then checking scope would make the picker a probe: a supervisor could type an email"
			" and learn from the shape of the answer whether that person is on the register at all.",
			"It fails closed at every step. No resolvable role, no assignment, or a term matching"
			" nobody in scope all produce an empty result, and an empty node set is never read as"
			" unfiltered: the query is not run at all, because a filter of IN with an empty list is"
			" the kind of thing a framework is entitled to treat as no filter.",
		]
	)


def _typing_a_name(w) -> None:
	w.h2("Typing a name instead of browsing")

	w.p(
		"resolve() is the stricter mode: a supervisor who already knows exactly who they mean gives"
		" a volunteer docname, a Red Profile docname or an email address rather than scrolling a"
		" list. It is not a way around the scope. The identifier is turned into a volunteer by"
		" picker._identified(), which is allowed to find anybody, and then put through the same"
		" check, which is the only thing allowed to act on what it found."
	)
	w.note(
		"The refusal is one message for both 'there is no such volunteer' and 'that volunteer is not"
		" yours'. Two different messages would turn the picker into an oracle for the existence of"
		" anybody's email address on the register, and the test asserts the two exceptions carry"
		" identical text."
	)


# --- the stub --------------------------------------------------------------


def _the_stub(w) -> None:
	w.h2("The approval stub")

	w.lead(
		"Stipend paperwork can be submitted. It then sits in Pending Departmental Approval, and"
		" nobody can approve it, including an administrator. This is the feature as built, not a"
		" defect, and it is written up here so that nobody demonstrates it expecting otherwise."
	)

	w.p(
		"The chain a society actually runs is supervisor to head of department, and the head of"
		" department is the head of the volunteer's department. vmmsx cannot resolve that today, so"
		" it does not pretend to. stipend/services/approval.py holds the whole of it: a two-value"
		" lifecycle, submit() and withdraw(), and decide(), which always refuses."
	)

	w.h3("What happens at each step")

	w.table(
		("Action", "What the app does"),
		[
			[
				"Submit",
				"Really submits. The state moves to Pending Departmental Approval, submitted_on and"
				" submitted_by are stamped, and the document's substance is frozen against edits"
				" until it is withdrawn. All of that is true today and none of it depends on there"
				" being an approver.",
			],
			[
				"Approve or reject",
				"Refused, for everybody, with a message naming the chain, saying that departmental"
				" routing is not built, and saying that it is deliberately not being routed through"
				" the geo approval engine instead. There is no administrator path and no override"
				" argument, because what is missing is not permission.",
			],
			[
				"Withdraw",
				"Returns it to Draft and clears the submission stamps, so it can be corrected. This"
				" is the only move out, and it exists because the alternative is paperwork that can"
				" be neither approved nor corrected.",
			],
		],
		(1.55, 4.95),
	)

	w.p(
		"There is no terminal state, and that is the honest shape rather than an omission. The only"
		" ways out of Pending Departmental Approval are approval and rejection, neither of which"
		" exists, and adding an Approved value nobody can reach would put a lie in a Select. The"
		" test asserts the Select offers exactly the two states."
	)


def _why_not_the_engine(w) -> None:
	w.h2("Why this is not routed through the approval engine")

	w.p(
		"vmmsx/approvals resolves approvers by walking upward through geo: it asks core who holds a"
		" named role at, or above, the document's Geo Node. A department is not a place, and a head"
		" of department is not up the geo tree from a volunteer."
	)
	w.p(
		"Point this module at the engine and every stipend report would route successfully,"
		" promptly, and to the wrong person: a branch or county coordinator standing above the"
		" report in the geo tree, who is not the head of anybody's department. A wrong approver who"
		" approves is far worse than no approver at all. The paperwork comes back signed, the audit"
		" trail says a decision was taken, and nothing anywhere records that the person who took it"
		" had no standing to."
	)

	w.h3("How that is stopped, rather than merely intended")

	w.bullets(
		[
			"No VMMS Approval Workflow governs either doctype, and the test asserts it.",
			"Neither doctype satisfies the engine's document contract. There is no approval_stage,"
			" no approval_stage_entered_on and no decisions table on either of them. A workflow"
			" cannot be pointed at a doctype that does not meet the contract, because"
			" approvals/services/contract.py refuses it when the workflow is saved, so nobody can"
			" wire this to geo routing by configuration alone.",
			"Nothing in vmmsx/stipend/ imports vmmsx/approvals at all, and the delegation scan"
			" fails if it starts to.",
			"api/stipend.py has its own submit, withdraw and decide rather than sending callers to"
			" api/approvals.py, which is the engine's door and would refuse these doctypes with a"
			" message about the wrong thing.",
		]
	)

	w.note(
		"Departmental resolution belongs to the delegation subsystem, which does not exist. Building"
		" half of it here, as a settings field naming a head-of-department role resolved against"
		" geo, would produce exactly the confident wrong answer described above."
	)


def _the_routing_target(w) -> None:
	w.h2("The pending routing target")

	w.p(
		"The one thing that is honest to do in the meantime is to record where this will eventually"
		" route, so that whoever builds the delegation subsystem inherits a real answer to 'route to"
		" whom' rather than having to reconstruct it from the paperwork."
	)
	w.p(
		"stipend/services/department.py captures, for each volunteer on a report, the department"
		" their Employee record carries, and writes the distinct set onto the report's"
		" routing_departments. It is recomputed from scratch on every save, so a stale value is"
		" blanked rather than left behind, and describe() returns it with routes_today set to False"
		" so that a populated list can never be read as a live route."
	)
	w.p(
		"The read goes through the Volunteer module's HR seam, volunteer/services/hr.py, and its"
		" _INBOUND allow-list, which names one field. That is the whole of what vmmsx reads back off"
		" an employment register: a department is an organisational placement HR owns and this app"
		" does not model, it is recorded as a routing target and never as an answer to who somebody"
		" is, and asking the seam for anything else is refused out loud."
	)

	w.h3("It degrades, and a blank is ordinary")

	w.bullets(
		[
			"No HR app on the site, no Employee linked to the volunteer, or an Employee with no"
			" department all produce nothing, and nothing blocks anything. The paperwork is about"
			" work that was done, and a society that does not run its volunteers through HR still"
			" files it.",
			"describe() says so in words rather than returning a bare empty list, because an empty"
			" list reads as a finding.",
			"The field is Data rather than a Link, so these doctypes still sync on a site without"
			" the app that owns Department, and because a report describes a period that has already"
			" happened: somebody who moved department in April did not move department in the March"
			" report.",
			"Nothing branches on a department. No department name appears anywhere in this app, and"
			" the test asserts it against the names this site actually holds.",
		]
	)


def _the_lifecycle(w) -> None:
	w.h2("The lifecycle, and why the state cannot be set by hand")

	w.p(
		"Two states, in code, closed: Draft and Pending Departmental Approval. approval.TRANSITIONS"
		" is the whole grammar, and every move goes through approval.assert_transition()."
		" docstatus is deliberately unused, as it is everywhere else in this app."
	)
	w.p(
		"Both controllers call approval.assert_stored_transition() from validate. The field is"
		" read-only on the form, so this is not about the desk: it is about a script assigning"
		" approval_state and saving, which would otherwise walk straight past submit() and the"
		" precondition it checks, which is that a report covers somebody. A state change arriving"
		" without the flag submit() and withdraw() set for the duration of their own save is"
		" refused."
	)
	w.p(
		"approval.assert_unchanged_while_pending() is the other half. Submitted paperwork is"
		" somebody else's to decide, so its substance is frozen: the people on a report and every"
		" line of a form's grid. It compares a signature rather than a fieldname, because the fields"
		" that matter are child tables and two lists of freshly loaded child rows never compare"
		" equal by identity however unchanged they are."
	)


# --- wiring ----------------------------------------------------------------


def _scoping(w) -> None:
	w.h2("Who may see stipend paperwork")

	w.p(
		"Both doctypes are registered with core through onerc_scopeable_doctypes in hooks.py, each"
		" on its own geo_node and each naming its own National Society Settings field rather than a"
		" role literal. Core resolves the field's value at enforcement time."
	)
	w.p(
		"They are two registrations because they are two questions. A narrative of what a branch did"
		" over a month and the money paid for it are read by different people in most societies, and"
		" folding them into one setting would make that impossible to express, in the wrong"
		" direction: a society that wanted every coordinator to read the narrative would have to"
		" show them the payments as well."
	)
	w.note(
		"Both settings ship empty, so core fails closed and no non-administrator can read either"
		" record until a society chooses the roles. That matters more here than elsewhere: geo"
		" scoping is the whole of the access model for these two doctypes, because the approval"
		" engine's person-gate deliberately does not govern them, and a payment form names people"
		" and the sums paid to them."
	)


def _configuration(w) -> None:
	w.h2("What a society configures")

	w.table(
		("Setting", "What it decides"),
		[
			[
				"vmms_stipend_anchor_level",
				"ACC-03. The geo level a progress report and a payment form must be anchored at. One"
				" setting governs both, because a form pays for the report it is paired with and the"
				" two are one place. Empty means any level; it narrows, it does not enable.",
			],
			[
				"vmms_stipend_report_scope_role",
				"Which role may read progress reports, combined with that role's Geo Assignments."
				" Empty means nobody but an administrator.",
			],
			[
				"vmms_stipend_payment_scope_role",
				"Which role may read payment forms. A separate question, and usually a narrower"
				" answer. Empty means nobody but an administrator.",
			],
			[
				"vmms_volunteer_scope_role",
				"The Volunteer module's own setting, read here rather than duplicated: it is what"
				" the picker resolves to decide which volunteers a supervisor may put on paperwork."
				" Empty closes the picker entirely.",
			],
			[
				"currency",
				"Core's own field on National Society Settings, read and never written. It is what a"
				" new payment form is denominated in, and it beats the site's global default, which"
				" is another app's answer for the whole site.",
			],
		],
		(2.35, 4.15),
	)

	w.p(
		"The first three are Custom Fields vmmsx owns, installed by patches/setup_stipend_module.py"
		" and patches/install_stipend_scope_roles.py. Core's National Society Settings doctype is"
		" not edited: a product pushing its own fields into the shared foundation's schema is how"
		" the foundation stops being shared."
	)
	w.note(
		"What is deliberately not a setting: anything naming who approves a stipend. Installing a"
		" field for a role nothing can resolve would be this app inviting a society to configure a"
		" route that goes nowhere."
	)


def _not_here_yet(w) -> None:
	w.h2("What is not built")

	w.p("Stated plainly, because a section that reads as though everything worked is worse than none at all.")

	w.table(
		("Not built", "Why, and what it waits for"),
		[
			[
				"Departmental approval routing",
				"The one deferred piece, and the reason for the stub. Resolving the head of a"
				" volunteer's department is the delegation subsystem's job and that subsystem does"
				" not exist. Until it does, submitted paperwork sits in Pending Departmental"
				" Approval and every attempt to decide it is refused with a message that says so."
				" The department each volunteer belongs to is captured on the report so the eventual"
				" routing has a target.",
			],
			[
				"Paying anybody",
				"This module produces paperwork. It records what is payable and moves no money."
				" Money in this app goes through onerc_payments, as MEM-01 requires, and no seam to"
				" it is built here: a disbursement is a decision somebody has to have approved, and"
				" nobody can approve one yet.",
			],
			[
				"A stipend rate",
				"No rate exists and none is derived. What a society pays for a day, and whether it"
				" varies by role, place or hours, is a society's decision, and an app that invented"
				" a rate would be paying people a number nobody chose. hours is recorded and"
				" multiplied by nothing.",
			],
			[
				"Any relationship to a deployment",
				"A progress report is not linked to a VMMS Deployment and attendance is not derived"
				" from VMMS Time Log. Whether a society's stipend paperwork should be generated from"
				" the deployments and hours it already holds is a real question and an unanswered"
				" one, and guessing at it would make two modules depend on an assumption nobody"
				" made.",
			],
			[
				"A desk surface of its own",
				"There is no workspace, no portal page and no client bundle. The doctypes and their"
				" child-table grids are the interface, and the services are reached through"
				" api/stipend.py.",
			],
		],
		(1.95, 4.55),
	)


def _what_is_tested(w) -> None:
	w.h2("What is tested, and what each suite is written to catch")

	w.p(
		"Integration tests against a real site. Geo comes from core's geo fixtures, identity from"
		" core's Red Profile, authority from real Geo Assignment rows, and volunteers from the"
		" Volunteer module's own service. Two hierarchies are built, shaped and named differently,"
		" so that no level name and no role name can be relied on by accident."
	)

	w.table(
		("Suite", "What it proves"),
		[
			[
				"test_paperwork.py",
				"ACC-02: a report or a form with no Geo Node is refused at creation, nothing is"
				" saved, and the refusal explains what an unplaced record would mean. ACC-03: with"
				" no level configured any level is accepted, a configured level refuses another, a"
				" second society with a differently named ladder narrows to its own, and one setting"
				" governs both documents. A report holds every volunteer it names, refuses the same"
				" volunteer twice, refuses a period that runs backwards, and cannot be submitted"
				" covering nobody. A form takes its period from its report and re-adopts a corrected"
				" one, refuses a different anchor, and refuses to exist without a report. The"
				" currency is the society's, beats the site's global default, is empty rather than"
				" guessed when unconfigured, and is not rewritten on an existing form.",
			],
			[
				"test_grid.py",
				"Each volunteer is totalled over their own days, days recorded and days attended are"
				" kept as different numbers, hours are summed and multiplied by nothing, and the"
				" form total is the sum of every line and is overwritten when typed. Who attended on"
				" a day is answered within a form and across the register, and a day nobody worked"
				" returns nobody rather than everybody. Every grid rule is exercised for its own"
				" refusal: somebody not on the report, a day outside the period on both sides, two"
				" lines for one volunteer on one day, a negative amount, and a stipend on a day"
				" marked absent. Adding a line through the service is idempotent and replaces a day"
				" rather than doubling it. A volunteer a paired form pays cannot be taken off the"
				" report, one it does not pay can, and the state that rule prevents is demonstrated"
				" by removing them behind its back and watching the form refuse to save. The shape is"
				" asserted against the schema, including that the line carries no day columns, and a"
				" forty-day period is run end to end.",
			],
			[
				"test_picker.py",
				"A supervisor sees their own subtree and never a sibling branch or another society."
				" An out-of-scope volunteer is never returned, including when searched for by their"
				" exact full name, their exact email, or their exact docname. Naming one outright is"
				" refused, and the refusal is asserted to be character-for-character the same as the"
				" refusal for an identifier matching nobody at all. The write path is refused and"
				" nothing is appended. No assignment, no configured scope role, and a scope role"
				" nobody holds each close the picker completely. The signatures of the services and"
				" the endpoints are asserted to have no user, nodes, geo_node, scope or"
				" ignore_permissions parameter.",
			],
			[
				"test_stub.py",
				"A submitted report and a submitted form both sit in Pending Departmental Approval,"
				" with who and when recorded, and submitting twice changes nothing. Approving is"
				" refused, rejecting is refused, deciding a draft is refused, and the refusal is"
				" asserted to carry the message that says why, including as Administrator through"
				" the endpoint, with the state surviving the attempt. No workflow governs either"
				" doctype, neither satisfies the engine's contract, neither carries its fields, and"
				" the engine's own endpoint refuses them. Withdrawing returns to Draft and clears"
				" the stamps; a submitted document cannot have its people or its grid changed,"
				" through the service or at the document; the state cannot be set by hand. The"
				" routing target degrades to nothing without HR, says so rather than returning a"
				" bare empty list, never claims to route, and is re-derived rather than topped up.",
			],
			[
				"test_delegation.py",
				"No file in the module resolves approvers, queries Geo Node or Geo Assignment"
				" directly, imports the approval engine, or decides authority from role membership,"
				" and the scanners are themselves tested against source that does. get_user_geo_scope"
				" has exactly one caller and the scan fails on a second. No role name, geo level"
				" name, currency code or department name that this site actually holds appears as a"
				" string literal anywhere in the module.",
			],
		],
		(1.55, 4.95),
	)
