# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Approval Engine section of the guide.

Every claim in here names the file or function it describes, so a reader can go
and check it. The field tables and the state table are generated from the
doctype JSON and from `vmmsx/approvals/states.py` rather than typed, which is
what keeps them true after the next change.
"""

from vmmsx.approvals import states
from vmmsx.docs import doctypes

TITLE = "Approval Engine"
SUMMARY = "The generic engine every approval in vmmsx reuses — state, routing, and the person-gate."

WORKFLOW = "VMMS Approval Workflow"
STAGE = "VMMS Approval Stage"
DECISION = "VMMS Approval Decision"
ANCHOR_LEVEL = "VMMS Approval Anchor Level"

# Descriptions for fields whose JSON carries no help text of its own. A field
# missing from both fails the build — see vmmsx/docs/doctypes.py.
WORKFLOW_EXTRA = {
	"stages": (
		"The stages of review, as an ordered child table. Order comes from each row's"
		" sequence, never from the order the rows happen to sit in."
	),
}

DECISION_EXTRA = {
	"stage_sequence": (
		"The sequence of the stage this decision was taken at, snapshotted so the trail"
		" stays readable in order even if the workflow is reconfigured later."
	),
	"approver": "The user who decided. Written by the engine from the acting session, never chosen on a form.",
	"decision": "What they decided. One of the three the state machine recognises.",
	"decided_on": "When the decision was recorded.",
}


def render(w) -> None:
	w.h1(TITLE)

	_what_it_is(w)
	_the_states(w)
	_workflow(w)
	_stage(w)
	_decision(w)
	_anchor_level(w)
	_behind_the_scenes(w)
	_making_a_doctype_approvable(w)
	_worked_example(w)
	_what_is_tested(w)


# --- 1.1 -------------------------------------------------------------------


def _what_it_is(w) -> None:
	w.h2("What the approval engine is")

	w.lead(
		"An application is raised somewhere in the country, and somebody specific has to look at it."
		" The approval engine is the part of vmmsx that decides who that person is, puts the"
		" application in front of them, and refuses to let anybody else act on it."
	)
	w.p(
		"It is built once and reused unchanged. Volunteer applications, membership, deployment"
		" requests — none of them are named anywhere in the engine, and none of them need to be."
		" A module becomes approvable by carrying a few fields and having one configuration record"
		" created for it, which is covered in section 1.8."
	)
	w.p(
		"Everything a national society may decide differently is configuration: how many stages"
		" there are, what they are called, which role each one needs, how many approvers must act,"
		" how long they have, and which levels of the hierarchy an application may be anchored at."
		" Nothing a society may decide lives in a source file."
	)

	w.h3("Why not Frappe's built-in Workflow")

	w.p(
		"Frappe ships a Workflow feature, and it cannot express this system. Its transitions gate"
		" on a role plus a safe_eval condition that cannot call our code. It can ask whether the"
		" acting user holds a role — but never whether they are the specific person this document"
		" was routed to. Being a county coordinator does not make you this application's county"
		" coordinator, and in a national society with dozens of counties that difference is the"
		" whole point. So the engine does not try to force it, and there are no desk workflow"
		" buttons at all."
	)

	w.h3("State, routing, gate")

	w.p('Instead, "workflow" is split into three jobs that are kept apart on purpose:')
	w.bullets(
		[
			"State — vmmsx/approvals/states.py. A closed set of seven states and a fixed table of"
			" the moves allowed between them. This is code. No society may add an eighth state.",
			"Routing — vmmsx/approvals/services/routing.py. Turns a stage plus a place into named"
			" people, by asking onerc_core who holds the stage's role at or above the document's"
			" Geo Node, and puts the document in those people's desk queue.",
			"Gate — vmmsx/api/approvals.py, backed by engine.authorised(). Every action comes"
			" through an API endpoint that checks the acting user is among the people this"
			" document resolved to, at this stage, right now.",
		]
	)
	w.p(
		"The split matters because the three change for different reasons. States change when the"
		" lifecycle itself changes, which is close to never. Routing changes when a society"
		" reorganises. The gate never changes at all."
	)


# --- 1.2 -------------------------------------------------------------------


def _the_states(w) -> None:
	w.h2("The lifecycle states")

	w.p(
		"An application is always in exactly one of seven states. Three are open — it is still"
		" somebody's problem. Four are terminal — it is not, and nothing may move it again. A"
		" decided application is history, not a record to be reopened by editing a field."
	)

	rows = []

	for state in states.STATES:
		targets = states.TRANSITIONS[state]
		kind = "open" if states.is_open(state) else "terminal"
		moves = ", ".join(targets) if targets else "— nothing; it is decided"
		rows.append([state, kind, moves])

	w.table(("State", "Kind", "May move to"), rows, (1.6, 1.1, 3.8))
	w.caption(
		"Generated from states.TRANSITIONS. In Review appears in its own row of targets because"
		" advancing from one stage to the next is a real transition the engine performs — the"
		" state stays put and the stage moves."
	)
	w.p(
		"Every state change in the engine goes through contract.set_state(), which calls"
		" states.assert_transition(). That is the single chokepoint: if a move is not in the table"
		" above, no service can invent it locally."
	)
	w.p(
		"Frappe's own docstatus is deliberately unused. An approvable document stays at"
		" docstatus = 0 and its lifecycle is the state above. Mixing the two would put half the"
		" lifecycle somewhere states.py cannot see."
	)

	w.h3("What a decision may say")

	w.p(
		"A decision is one of three values, and this set is closed too: Approved, Rejected, and"
		" More info requested. The third is a lifecycle move, not a comment — it returns the"
		" application to the applicant as a draft, and when they resubmit, review restarts from"
		" the first stage, because what the earlier stages endorsed is not what is being"
		" resubmitted."
	)


# --- 1.3 to 1.6 ------------------------------------------------------------


def _doctype_block(w, doctype: str, represents: list[str], extra: dict | None = None) -> None:
	for paragraph in represents:
		w.p(paragraph)

	w.table(
		doctypes.FIELD_TABLE_HEADERS,
		doctypes.fields(doctype, extra),
		doctypes.FIELD_TABLE_WIDTHS,
	)
	w.caption(f"Naming — {doctypes.naming_of(doctype)}")


def _workflow(w) -> None:
	w.h2(WORKFLOW)

	_doctype_block(
		w,
		WORKFLOW,
		[
			"One record per approvable doctype: the whole of what a society has decided about how"
			" that kind of application is approved. It is the only place the engine reads"
			" configuration from, through vmmsx/approvals/services/config.py.",
			"Its docname is opaque — AWF-00001 and so on, assigned in autoname() — and renaming is"
			" switched off. workflow_for is the obvious candidate for a docname and is exactly why"
			" it must not be one: a governed doctype can be renamed, and mutable data never goes in"
			" a primary key. The doctype's title field shows workflow_for, so the desk still lists"
			" these records by the thing they govern.",
			"The record refuses to save if it cannot work. Those guardrails are in"
			" vmms_approval_workflow.py and are listed in section 1.7.",
		],
		WORKFLOW_EXTRA,
	)


def _stage(w) -> None:
	w.h2(STAGE)

	_doctype_block(
		w,
		STAGE,
		[
			"One step of review: who has to look at the application here, how many of them, how"
			" long they have, and what happens if they do not. A workflow's stages are its child"
			" rows, and the engine walks them in ascending sequence.",
			"A stage is identified by its opaque row name and ordered by its sequence. stage_label"
			" is display only — it is translatable, it is snapshotted onto every decision, and"
			' nothing in the engine reads it to decide anything. Renaming "Branch Endorsement" to'
			' "Branch Review" changes a screen and nothing else. This is enforced, not merely'
			" intended: tests/test_no_stage_branching.py walks the abstract syntax tree of every"
			" source file in the app and fails if a stage label ever reaches a comparison.",
		],
	)


def _decision(w) -> None:
	w.h2(DECISION)

	_doctype_block(
		w,
		DECISION,
		[
			"One line of an application's audit trail: who decided what, at which stage, when, and"
			" why. These rows live as a child table on the approvable document itself, so an"
			" application carries its own history rather than pointing at a log somewhere else.",
			"Every field is read-only and written only by the engine, in"
			" contract.record_decision(). A decision a user could type is not an audit trail.",
		],
		DECISION_EXTRA,
	)


def _anchor_level(w) -> None:
	w.h2(ANCHOR_LEVEL)

	_doctype_block(
		w,
		ANCHOR_LEVEL,
		[
			"A single permitted anchor level, as a row on the workflow. Together the rows answer"
			" ACC-03: which level of the hierarchy an application of this type may be anchored at.",
			"One society may allow a volunteer application to be anchored at county level, another"
			" requires ward level, a third anchors deployments at region and members at branch."
			" The difference between them is rows in this table. No source file in vmmsx contains"
			" the word county or ward, and none assumes a depth. An empty table means any active"
			" level is acceptable — a society that has not narrowed the rule has not thereby"
			" forbidden everything.",
		],
	)


# --- 1.7 -------------------------------------------------------------------


def _behind_the_scenes(w) -> None:
	w.h2("How it works behind the scenes")

	w.p(
		"The services are in vmmsx/approvals/services/. All of them take documents rather than"
		" names, and all of them are idempotent: calling one twice observes that the work is done"
		" and returns the same answer."
	)

	w.h3("Submission")

	w.p("engine.submit() is the entry point. In order, it:")
	w.steps(
		[
			"reads the workflow for the document's doctype (config.for_doctype);",
			"if the document is already in review, re-resolves and re-syncs the queue and changes"
			" no state — an assignment somebody closed by hand comes back;",
			"otherwise checks the anchor: config.anchor() throws if the Geo Node field is empty"
			" (ACC-02) and config.assert_anchor_allowed() throws if it sits at a level this"
			" society does not permit (ACC-03). Neither kind of document can be routed, so"
			" neither is allowed into review;",
			"checks the re-application cooldown (engine.assert_cooldown);",
			"moves the state to Submitted, then calls _advance() to enter the first stage that"
			" can be entered;",
			"saves the document once, and only then syncs the desk queue — so a save that fails"
			" leaves no ToDo pointing at an approval that did not happen.",
		]
	)
	w.p(
		"_advance() walks the stages in sequence and stops at the first one that resolves"
		" somebody. A stage that resolves nobody is skipped if it is optional, and entered anyway"
		" — blocked and escalated — if it is not. It never silently passes. That is the difference"
		' between "nobody needed to sign this" and "nobody could". Falling off the end of the'
		" stages means every remaining one was optional and empty, and the application is"
		" approved by a configuration that asked for no approvals."
	)

	w.h3("Routing — how the specific person is found")

	w.p(
		"routing.resolve() is a thin layer over onerc_core. It never queries tabGeo Node and never"
		" walks the tree itself; if routing and core's read scope ever disagreed about who holds"
		" what where, the product would route approvals to people who cannot open the document."
		" They read one table through one service, so they cannot."
	)
	w.code(
		"# vmmsx/approvals/services/routing.py\n"
		'resolve_approvers(geo_node, stage.required_role, rule="nearest_ancestor")\n'
		'resolve_approvers(geo_node, stage.required_role, rule="at_level", geo_level=stage.geo_level)\n'
		"holders_exactly_at(stage.fixed_geo_node, stage.required_role)   # the fixed_node rule"
	)
	w.p(
		"The third rule is this layer's addition — \"always the national desk, wherever the"
		' applicant lives" is not a question relative to the document — but it is still expressed'
		" through core: holders_exactly_at() asks the adapter for the node's own level and then"
		' asks core for holders at that level starting from that node, which is exactly "holders'
		' here, no walking up".'
	)
	w.p(
		"routing.routed() then narrows the list to the people the gate will actually admit. It"
		" differs from resolve() only for the single completion rule, which takes the first"
		" holder — core returns holders in a deterministic order, so re-resolving the same stage"
		" tomorrow lands on the same person rather than quietly moving the queue around."
	)
	w.p(
		"assignment.sync() then puts the document in those people's desk queue as a Frappe"
		" assignment (a ToDo plus _assign), so an approval arrives where the approver already"
		" looks. The assignment is a notification and never an authorisation — the gate does not"
		" read ToDos, or any desk user able to create an assignment could hand themselves an"
		" approval."
	)

	w.h3("The gate — how the acting user is checked")

	w.p(
		"engine.authorised() is the whole security story, and it is recomputed from Geo Assignment"
		" on every call. Nothing is trusted from the document, the session, or a ToDo. Caching the"
		" resolution when the application was routed would mean an approver whose assignment ended"
		" last week could still approve today, which is the failure the access model exists to"
		" prevent."
	)
	w.p("engine.decide() refuses, in this order, before any audit row is written:")
	w.bullets(
		[
			"the decision value is not one of the three (states.assert_decision);",
			"the application is not In Review — there is nothing to decide;",
			"the document points at a stage that no longer exists in its workflow;",
			"core's geo scoping refuses the user (enforcement.guard) — they cannot reach the record at all;",
			'the user is not among auth["approvers"] — this is the person-gate, and it raises'
			" frappe.PermissionError with a message that says holding the role is not enough;",
			"the decision is a rejection at a stage whose can_reject is off, or a rejection with"
			" no reason given.",
		]
	)
	w.p(
		"engine.may_act() is the same check as a predicate, for a screen that needs to show or"
		" hide a button. The public endpoints in vmmsx/api/approvals.py add two checks in front of"
		" all of this: the doctype must be governed by a workflow at all, and the caller must pass"
		" Frappe's own permission check for the document, which brings core's geo scoping with it."
		" Each endpoint names its arguments and returns an explicit dict built field by field by"
		" engine.status() — never a Document and never a raw query result."
	)
	w.note(
		"engine.status() shows approver names only to people in the chain — whoever may act now,"
		" whoever has already acted, and users with unrestricted scope. Everyone else, the"
		" applicant included, gets approver_count. That the application is with two people is"
		" theirs to know; which two is not automatically theirs to know."
	)

	w.h3("Completion rules — how many must act")

	w.p(
		"Core's resolve_approvers() produces the list of people and deliberately decides nothing"
		" about quantity, order, or what an empty list means. This layer owns that, in"
		" routing.is_complete():"
	)
	w.bullets(
		[
			"single — one named person owns the decision. Only they are routed, and their decision"
			" advances the stage.",
			"any_of — everybody resolved is routed and it sits in all their queues; the first"
			" decision advances it and the queue empties.",
			"all_of — everybody resolved is routed and every one of them must approve. As each"
			" approves, the queue shrinks to those who have not answered yet.",
		]
	)
	w.p(
		"An all_of stage that resolved nobody is never complete — is_complete() returns False for"
		" an empty routed list rather than trivially satisfying the subset test. That is the"
		" guardrail: without it, a stage nobody could act on would approve itself. Instead the"
		" stage is entered, blocked, and escalated, and engine.authorised() admits the escalation"
		" target as the effective approver so the application can still move."
	)

	w.h3("SLA and escalation")

	w.p(
		"Every stage has a clock — sla_days, at least one — because an application rotting in an"
		" absent approver's queue is the number-one failure mode of a system like this. It is not"
		" a crash, nothing is logged, and the first anybody hears of it is a volunteer asking why"
		" nobody replied for four months."
	)
	w.p(
		"sla.due_on() is the stage's entry timestamp plus its SLA days. sla.sweep() runs daily"
		" (registered in hooks.py under scheduler_events) over every open application of every"
		" governed doctype, and sla.apply_breach() acts on one document according to its stage's"
		" on_sla_breach setting. Two properties hold:"
	)
	w.bullets(
		[
			"Escalation never lands on the person who is already late. routing.escalate() is given"
			" the routed approvers to exclude and walks the ancestors nearest-first, skipping any"
			" node whose only holders are among them. Handing the same document back to somebody"
			" who has had their SLA is a loop with extra notifications, not an escalation.",
			"A breach widens authority; it never narrows it. The escalation target is added to the"
			" queue (assignment.add, not sync), and the late approver keeps the document and can"
			" still act. Taking it off their desk would hide the fact that they were late from the"
			" only people able to notice.",
		]
	)
	w.p(
		"Breach handling changes no state and saves no document. Who may act on a breached stage"
		" is computed from the clock inside engine.authorised(), which admits the escalation"
		" target when the stage resolved nobody, or when the stage is breached and the society"
		" chose escalate_up. So the gate is right whether or not last night's sweep ever ran; the"
		" sweep exists to notify people, not to grant anybody anything."
	)
	w.p(
		"If nobody above holds the role either, the application is stranded. No fallback approver"
		" is invented — appointing the site's administrator as approver of last resort is exactly"
		" the kind of decision software should not take on a society's behalf. It is written to"
		" the error log instead, under a named title, because an application nobody anywhere can"
		" act on is an operational fault rather than a quiet state."
	)

	w.h3("Withdrawal, cooldown, and expiry")

	w.bullets(
		[
			"engine.withdraw() lets the applicant take the application back, if the workflow's"
			" allow_withdrawal permits it. Only the document's owner may — an approver cannot"
			" withdraw somebody else's application.",
			"engine.assert_cooldown() refuses a re-application inside reapplication_cooldown_days"
			" of a previous rejection. The applicant is identified by whichever field the workflow"
			" names in applicant_field, falling back to the document's owner.",
			"engine.expire_stale() runs daily and closes open applications untouched for"
			" application_expiry_days. The default of 0 means never, so it does nothing at all"
			" until a society asks for it.",
		]
	)
	w.p(
		"A rejection, a withdrawal and an expiry all clear the desk queue and leave the"
		" applicant's own record untouched. A rejection ends the application, not the person."
	)

	w.h3("Guardrails on the configuration itself")

	w.p(
		"These are validations on VMMS Approval Workflow rather than checks in the engine, on"
		" purpose: a workflow that cannot work should be impossible to save, not merely impossible"
		" to run. An administrator finds out while looking at the form, not months later when the"
		" first application will not move."
	)
	w.bullets(
		[
			"The governed doctype must exist, must not be a child table or a single, and must"
			" satisfy the approvable contract.",
			"The anchor field must exist on it, must be a Link to Geo Node, and must be mandatory"
			" (ACC-02). A workflow may not anchor on free text or on a field a user could leave"
			" empty.",
			"There must be at least one stage; sequences must start at 1 and must not tie, because"
			" order would otherwise depend on row order.",
			"Each stage's rule must be a known one, and must carry what that rule needs — a Geo"
			" Level for at_level, a node for fixed_node.",
			"At least one stage must be able to reject. A workflow where every stage may only"
			" endorse is a rubber stamp with an audit trail, which is worse than no workflow at all"
			" because it looks like one.",
			"A stage that needs every approver, is not optional, and does nothing on breach is"
			" refused: an application reaching it could stall forever with nobody informed. Make it"
			" optional or give it an escalation.",
			"No anchor level may be listed twice.",
		]
	)


# --- 1.8 -------------------------------------------------------------------


def _making_a_doctype_approvable(w) -> None:
	w.h2("Making a doctype approvable")

	w.p(
		"The engine never names an approvable doctype — that inversion is what keeps it generic."
		" A module opts in by doing two things."
	)

	w.h3("Satisfy the document contract")

	w.p(
		"The contract is stated once, in vmmsx/approvals/services/contract.py, and checked by"
		" contract.assert_approvable(). An approvable doctype needs:"
	)
	w.table(
		("Field", "Type", "What it is for"),
		[
			["approval_state", "Select or Data", "The lifecycle state, from states.py."],
			["approval_stage", "Data", "The opaque row name of the stage under review."],
			[
				"approval_stage_entered_on",
				"Datetime",
				"When that stage was entered — the SLA clock for it.",
			],
			[
				"(any name)",
				f"Table → {DECISION}",
				"The audit trail. Found by its options rather than by a fixed"
				" fieldname, so a module may call it approval_history if it prefers.",
			],
			[
				"(named by the workflow)",
				"Link → Geo Node, required",
				"The ACC-02 anchor. Its fieldname goes in the workflow's geo_node_field.",
			],
		],
		doctypes.FIELD_TABLE_WIDTHS,
	)
	w.p(
		"The first three have fixed names because code reads them on doctypes it has never heard"
		" of, and one configurable fieldname per concept is one more thing that can be"
		" misconfigured into a silent no-op. All three are read-only to users and written only by"
		" the engine."
	)

	w.h3("Create one workflow record")

	w.p(
		f"One {WORKFLOW} naming the doctype, its anchor field, its permitted anchor levels and its"
		" stages. The workflow refuses to save if the doctype does not meet the contract, so a"
		" misconfiguration surfaces on the form rather than on the first application."
	)
	w.p(
		"Separately, and for a different reason, a product doctype registers itself with"
		" onerc_core for geo scoping through the onerc_scopeable_doctypes hook. Core never imports"
		" vmmsx; vmmsx registers itself. That hook governs who may read the record; the approval"
		" workflow governs who may decide it."
	)


# --- 1.9 -------------------------------------------------------------------


def _worked_example(w) -> None:
	w.h2("A worked example: one configuration, two societies")

	w.p(
		"This is the example the engine is built to satisfy, and it is a real test —"
		" vmmsx/approvals/tests/test_routing.py, class TestOneConfigTwoSocieties. Two national"
		" societies with differently shaped and differently named hierarchies, built through"
		" core's own geo fixtures:"
	)
	w.code(
		"A Kenya-shaped society                    A Gambia-shaped society\n"
		"\n"
		"Central ................. Region          North Bank .............. Region   <- Head C\n"
		"|- Kiambu ............... County  <- A    |- Kerewan .............. District <- Officer B\n"
		"|  |- Kihara ............ Ward            |  '- Illiassa ........... Village\n"
		"|  '- Ndenderu .......... Ward            '- Jokadu ............... District  (nobody)\n"
		"'- Nakuru ............... County             '- Kuntaur ........... Village\n"
		"   '- Bahati ............ Ward"
	)
	w.p(
		"Three people hold the same society-named role, each at one node, as core Geo Assignment"
		" rows: Coordinator A at Kiambu, Officer B at Kerewan, Head C at North Bank. There is one"
		" workflow with one stage, and it is not edited between any of the lines below:"
	)
	w.code(
		"stage:  sequence        = 1\n"
		"        required_role   = <the society's approver role>\n"
		"        resolution_rule = nearest_ancestor\n"
		"        completion_rule = single\n"
		"        sla_days        = 5\n"
		"        on_sla_breach   = escalate_up"
	)
	w.p("The same configuration then resolves to different people, correctly, in both societies:")
	w.table(
		("Application anchored at", "The walk", "Resolves to"),
		[
			["Kihara (ward)", "Kihara → Kiambu: a holder", "Coordinator A"],
			["Ndenderu (ward)", "Ndenderu → Kiambu: a holder", "Coordinator A"],
			["Illiassa (village)", "Illiassa → Kerewan: a holder", "Officer B"],
			[
				"Kuntaur (village)",
				"Kuntaur → Jokadu: nobody → North Bank: a holder",
				"Head C",
			],
			[
				"Bahati (ward)",
				"Bahati → Nakuru: nobody → Central: nobody",
				"nobody — and empty is an answer",
			],
		],
		(1.75, 2.65, 2.10),
	)
	w.p(
		"Nothing about county, district, ward or village appears anywhere in the engine. The walk"
		" finds whoever holds the role, wherever they sit, which is why the same configuration is"
		" correct in both places — and why standing up a new national society is a data-entry"
		" exercise rather than a fork of the code."
	)
	w.p(
		"The last row is deliberate. Where nobody holds the role at the node or anywhere above it,"
		" routing returns an empty list rather than inventing a fallback. Every plausible fallback"
		" — the administrator, the applicant's manager, the national desk — is a policy decision"
		" that belongs to a society, not to software."
	)

	w.h3("And the gate refuses everyone else")

	w.p(
		"Submit an application anchored at Kihara and it lands in Coordinator A's queue. The same"
		" arrangement in test_gate.py then puts four other people in front of it, each refused for"
		" a different reason, and each a failure that has shipped in systems like this:"
	)
	w.table(
		("Who", "What they have", "Result"),
		[
			[
				"The coordinator of another county",
				"The same role, held at Nakuru",
				"Refused. Right role, wrong place — the most plausible mistake in the whole system.",
			],
			[
				"A role holder with no assignment",
				"The role, granted and forgotten",
				"Refused. A role by itself grants nothing anywhere.",
			],
			[
				"The applicant",
				"Ownership of the document",
				"Refused, and they are not even told which approver holds it — only that one does.",
			],
			[
				"A System Manager",
				"Every permission in the system",
				"Refused. Core's scope layer lets them reach the record; routing does not name"
				" them, so they cannot decide it.",
			],
			[
				"A former approver",
				"An assignment that ended yesterday",
				"Refused today though they were the right person last week — the gate is"
				" recomputed, never remembered.",
			],
		],
		(1.55, 1.85, 3.10),
	)
	w.p(
		"Every one of those refusals raises frappe.PermissionError and changes nothing: no state"
		" moves, no audit row is written, and the application stays in Coordinator A's queue. This"
		" is the check Frappe's native Workflow cannot make — four of those five users would pass"
		" a role test."
	)


# --- 1.10 ------------------------------------------------------------------


def _what_is_tested(w) -> None:
	w.h2("What is tested")

	w.p(
		"185 integration tests, run against a real bench site with"
		" bench --site <site> run-tests --app vmmsx. Nothing about routing or the gate is mocked:"
		" geo data is built through onerc_core's own geo fixtures, authority is real Geo"
		" Assignment rows, and the queue is real ToDos."
	)
	w.p(
		"The approvable document is a stand-in — a genuine doctype created by the fixtures, with a"
		" genuine mandatory Link to Geo Node and a genuine decisions table. That the engine is"
		" proven against a doctype it has never heard of is the point: if it works there it works"
		" for Volunteer and Member, because there is nothing about it the engine could have been"
		" written around."
	)
	w.table(
		("Test file", "Tests", "What it proves"),
		[
			[
				"test_routing.py",
				"17",
				"One configuration resolves to a county coordinator in one society and a district"
				" officer in another; the walk keeps going up where a level holds nobody; at_level"
				" and fixed_node route by policy rather than proximity; every routed approver can"
				" actually reach the record.",
			],
			[
				"test_gate.py",
				"18",
				"The resolved approver may act and everyone else is refused — another county's"
				" coordinator, an unassigned role holder, the applicant, a System Manager, and an"
				" approver whose authority has ended. A refusal changes nothing. The same gate"
				" holds through the public API and the queue endpoint.",
			],
			[
				"test_completion.py",
				"21",
				"single routes to one person deterministically; any_of advances on the first"
				" decision; all_of waits for every approver and shrinks the queue as they answer;"
				" an all_of stage that resolves nobody escalates rather than passing itself; an"
				" optional stage that resolves nobody is skipped.",
			],
			[
				"test_sla.py",
				"26",
				"A fresh stage is not breached and an old one is; a breach escalates to the node"
				" above and never back to the person already late; the late approver keeps the"
				" document too; notify_only re-routes nobody; none is recorded, not reinterpreted;"
				" sweeping twice escalates once; nowhere to escalate is logged, not approved.",
			],
			[
				"test_lifecycle.py",
				"40",
				"The ordinary two-stage path end to end; idempotence of submission and of a"
				" repeated decision; rejection requires a reason, keeps it where the applicant can"
				" be told, and leaves their record intact; endorse-only stages; more-info returns"
				" it to the applicant; withdrawal where allowed and refused where not; the"
				" re-application cooldown; expiry.",
			],
			[
				"test_config.py",
				"38",
				"Every guardrail on the workflow record, the approvable contract, ACC-02 at both"
				" configuration and submission time, and ACC-03 — one engine, two societies,"
				" opposite anchor rules, no code difference.",
			],
			[
				"test_states.py",
				"18",
				"The state set is closed, open and terminal partition it, terminal states go"
				" nowhere, and the transition table is the whole grammar.",
			],
			[
				"test_no_stage_branching.py",
				"7",
				"No source file in the app branches on a stage name. The scan walks the AST of"
				" every file, and four of the seven tests check the scanner itself catches what it"
				" claims to — a detector that finds nothing because it is broken proves nothing.",
			],
		],
		(1.45, 0.55, 4.50),
	)
