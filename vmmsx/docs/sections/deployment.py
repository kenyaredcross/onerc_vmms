# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Deployment section of the guide (stage 4).

Field tables are generated from the doctype JSON; every other claim names the
file or function it describes.

Three things in this section are decisions rather than descriptions, and each is
argued rather than asserted: why participation is a child table, why matching
can never leak scope, and what a branch transfer does and does not touch. The
open questions branch transfer raises are listed as open, because a design
document that reads as though every question were settled is worse than one that
says which are not.

What is pending is marked pending. Certification matching is real and works;
skill matching is not, because there is no structured record of what a volunteer
can do, and the module reports that in every result rather than in a footnote.
"""

from vmmsx.docs import doctypes

TITLE = "Deployment"
SUMMARY = (
	"Terms of reference, deployments and their rosters, deployment requests, the matching service,"
	" and branch transfer."
)

TERMS = "VMMS Terms of Reference"
REQUIREMENT = "VMMS Deployment Requirement"
DEPLOYMENT = "VMMS Deployment"
PARTICIPANT = "VMMS Deployment Participant"
REQUEST = "VMMS Deployment Request"
TRANSFER = "VMMS Branch Transfer"


def render(w) -> None:
	w.h1(TITLE)

	_what_it_is(w)
	_terms(w)
	_requirement(w)
	_deployment(w)
	_participant(w)
	_request(w)
	_transfer(w)
	_the_participant_model(w)
	_the_ownership_rule(w)
	_matching(w)
	_the_scope_guarantee(w)
	_matching_criteria(w)
	_the_opportunity_board(w)
	_branch_transfer(w)
	_the_history_rule(w)
	_transfer_open_questions(w)
	_approval_is_configuration(w)
	_scoping(w)
	_configuration(w)
	_not_here_yet(w)
	_what_is_tested(w)


# --- what it is ------------------------------------------------------------


def _what_it_is(w) -> None:
	w.h2("What the Deployment module is")

	w.lead(
		"This is the module that makes volunteers do things. The register says who somebody is and"
		" what they are qualified for; this says what the society sent them to do, where, when, and"
		" with whom."
	)
	w.p(
		"Six doctypes carry it, and they divide cleanly into configuration and operation. VMMS"
		" Terms of Reference is the specification of a kind of work, written once and pointed at"
		" many times. VMMS Deployment is an instance of that work at a place over a period, with a"
		" roster. VMMS Deployment Request is somebody asking for volunteers, which may or may not"
		" need authorising. VMMS Branch Transfer moves a volunteer from one branch to another. The"
		" other two are child tables."
	)
	w.p(
		"The services are in vmmsx/deployment/services/, and every one of them is idempotent and"
		" takes documents rather than names. Nothing here resolves an approver, walks the geo tree,"
		" or decides that somebody may act because they hold a role: routing is the approval"
		" engine's, geo is core's adapter's, and authority is the engine's person-gate."
		" deployment/tests/test_delegation.py walks the AST of every file in the module and fails"
		" if one of those grows here."
	)

	w.h3("Three pieces of work, and how they connect")

	w.bullets(
		[
			"A request is raised, and if its terms of reference say so it is routed to an approver."
			" When its approval requirement is settled it becomes a deployment, carrying the"
			" request's terms, place and dates. Nobody is put on the roster by that: who goes is a"
			" coordinator's judgement.",
			"The matching service answers who could go. It is a service over the geo adapter and"
			" core's scope service, callable from an endpoint, and it never returns a volunteer the"
			" caller may not already see.",
			"Once somebody is on a deployment's roster they can log time against it, and only"
			" against it. That is the rule the volunteer spine shipped as an explicit stub and this"
			" module finished.",
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


def _terms(w) -> None:
	w.h2(TERMS)

	_doctype_block(
		w,
		TERMS,
		[
			"The specification a deployment is run against: what the work is, who is qualified for"
			" it, where it may be used, and whether asking for volunteers to do it needs"
			" authorising. Configuration, written by a society, pointed at by many deployments.",
			"It is keyed by a stable business key rather than an opaque series, which is the same"
			" rule VMMS Certification Type and VMMS Time Log Category follow: a configuration"
			" vocabulary is referred to by its key, while records about people and places get"
			" opaque IDs. Relabelling the terms next year therefore never rewrites what happened"
			" this year.",
			"Three fields on it are read by code and each is a society's answer rather than this"
			" app's: geo_scope narrows where the terms may be used, approval_mode decides whether a"
			" request under them is routed, and required_certifications is what matching filters"
			" and ranks by. Everything else on the record is for the people involved, and no code"
			" reads it.",
			"deployment/services/terms.py is the only reader. It hands back certification keys and"
			" a mode; it never hands back a row, so no caller can start depending on a field this"
			" module has not decided is meaningful.",
		],
	)


def _requirement(w) -> None:
	w.h2(REQUIREMENT)

	_doctype_block(
		w,
		REQUIREMENT,
		[
			"One certification a terms of reference asks for, and how hard it asks. A mandatory row"
			" is a hard filter; a row that is not mandatory is a preference that ranks a candidate"
			" higher and excludes nobody.",
			"The row itself carries no rules. What it means is decided where it is read, in"
			" matching, which is what lets a society move a requirement from desirable to required"
			" without anything being migrated.",
		],
	)


def _deployment(w) -> None:
	w.h2(DEPLOYMENT)

	_doctype_block(
		w,
		DEPLOYMENT,
		[
			"An actual deployment: these terms, at this place, over these dates, with these people."
			" It is the record the society's work is reported from and the record a deployment time"
			" log is checked against.",
			"ACC-02 holds here as it does everywhere: geo_node is a Link, mandatory at creation, and"
			" refused rather than filled in later. An unplaced deployment is invisible to geo"
			" scoping, because core's list filter is an IN and that excludes NULL, so it would exist"
			" with nobody able to see it or report on it. ACC-03 is the society's own"
			" vmms_deployment_anchor_level, read from settings on every save, and there is a second"
			" narrowing on top of it: the terms of reference's own geo_scope, which is whoever wrote"
			" the terms saying where they apply.",
			"Its status is a closed, code-owned set with a fixed transition table in"
			" deployment/services/deployment.py, for the same reason approval states are code: each"
			" value means something the server enforces. Completed and Cancelled are terminal, so a"
			" deployment that ended cannot be reopened by editing a field.",
			"What the status deliberately does not govern is time logging. A participant may file"
			" the hours they served after the deployment has closed, which is the ordinary case;"
			" refusing them would punish accurate record keeping. Ownership is the roster, and only"
			" the roster.",
		],
	)


def _participant(w) -> None:
	w.h2(PARTICIPANT)

	_doctype_block(
		w,
		PARTICIPANT,
		[
			"One volunteer on one deployment. This row is the evidence the ownership rule reads: a"
			" deployment time log is accepted only if the volunteer filing it appears here.",
			"left_on records that somebody went early. It does not remove them, and that is"
			" deliberate: taking somebody off the roster would make the time they actually served"
			" unfilable, which is precisely backwards.",
		],
	)


def _request(w) -> None:
	w.h2(REQUEST)

	_doctype_block(
		w,
		REQUEST,
		[
			"Somebody asking for volunteers: this work, at this place, over these days, this many"
			" people. It carries the approval engine's document contract, so a society that wants"
			" requests authorised gets the same routing, the same person-gate and the same audit"
			" trail a volunteer application or a membership gets.",
			"Fulfilment is a predicate, not a sequence. request.try_fulfil() asks whether the"
			" approval requirement is settled and whether a deployment has been created already,"
			" and both are answered from the record and from configuration rather than from which"
			" code path ran. It is called from the controller's on_update, which is how a decision"
			" recorded by the engine becomes a deployment without the engine knowing deployments"
			" exist. This is the same shape membership activation and volunteer acceptance have.",
			"What fulfilment creates is the deployment, and not the roster. A request that quietly"
			" deployed the first N people who matched would be this software deciding who serves.",
		],
	)


def _transfer(w) -> None:
	w.h2(TRANSFER)

	_doctype_block(
		w,
		TRANSFER,
		[
			"A volunteer moving from one branch to another. The whole of what that means in this"
			" app is that VMMS Volunteer.home_geo_node stops naming one Geo Node and starts naming"
			" another, and transfer._move_placement() is the only write in the module.",
			"from_geo_node is snapshotted from the volunteer at before_insert and read-only"
			" thereafter, so a transfer records where somebody actually was rather than where"
			" whoever raised it believed they were. It is also the ACC-02 anchor for geo scoping"
			" and, by default, for approval routing.",
			"Applying is a predicate. transfer.try_apply() asks four questions of the record: is it"
			" still pending, is its approval settled, has its effective date arrived, and is the"
			" volunteer still where this transfer says they were. It is therefore safe to call after"
			" any event and in any order, and the daily sweep that catches a future-dated transfer"
			" is the same function.",
		],
	)


# --- the decisions ---------------------------------------------------------


def _the_participant_model(w) -> None:
	w.h2("Why participation is a child table")

	w.lead(
		"Both shapes answer both questions, so the choice came down to what each makes true rather"
		" than to what each makes possible."
	)

	w.table(
		("The question", "How the chosen shape answers it"),
		[
			[
				"Who is on this deployment?",
				"It is the roster, and a roster is a property of the deployment. As a child table it"
				" is edited as one list on one form, saved in one act, and checked against one"
				" permission: the permission to write the deployment. As a separate doctype it"
				" becomes N records that can drift from their parent's state, and adding somebody"
				" needs its own permission story.",
			],
			[
				"Which deployments was this volunteer on?",
				"One indexed read either way. A child table is a real table, so"
				" participation.deployments_of() reads it by volunteer and returns parent. That"
				" query lives in exactly one place, because reading a child table by a field other"
				" than parent is unusual enough that scattering it would invite somebody to write it"
				" without parenttype, which would quietly match rows from another doctype.",
			],
			[
				"What does a time log point at?",
				"The deployment, not the participation row. That is what settles it. Had the log"
				" needed a stable per-person identity to point at, a child row would have been the"
				" wrong thing to hand it, because a child row's name is not something a caller"
				" should ever have to hold.",
			],
			[
				"What is the editing surface?",
				"Frappe's grid on the deployment form, which is a native desk surface this stage was"
				" asked to build on rather than around.",
			],
		],
		(1.85, 4.65),
	)

	w.p(
		"What the shape costs, stated plainly: a participation cannot itself be approved, cannot be"
		" geo-scoped separately from its deployment, and cannot carry an independent lifecycle."
		" None of those is wanted today. If one becomes wanted, the migration is a real one, and it"
		" is bought by everything above rather than avoided by guessing now. The argument is kept"
		" in deployment/services/participation.py, next to the code it justifies."
	)


def _the_ownership_rule(w) -> None:
	w.h2("The deployment time log's ownership rule")

	w.lead(
		"A volunteer may log time against a deployment only if they are on its roster. The check is"
		" on the server, at save, on every path a log can arrive by."
	)
	w.p(
		"The volunteer spine shipped this kind of log as an explicit stub. It refused with a message"
		" naming stage 4, because the Deployment doctype did not exist and there was therefore"
		" nothing to check participation against, and the rule that had to exist was written down"
		" so it would not be reinvented from memory. This module built the doctype and enforced the"
		" rule; the stub and its constants are gone, and the module's tests assert that no refusal"
		" left in volunteer/services/timelog.py names a stage that has since happened."
	)

	w.h3("Ownership is not geo scoping, and the difference is the substance")

	w.p(
		"Geo scoping answers where somebody may act: it is a property of a record's anchor, and core"
		" owns it. Ownership answers whose record this is. Being correctly placed in the right"
		" county does not make somebody a participant on a deployment run there, and no amount of"
		" geo authority ever will. The two tests that make this concrete both use a volunteer"
		" anchored at the very same Geo Node as the deployment, and both are refused."
	)

	w.h3("It is a ValidationError, not a PermissionError, and that is deliberate")

	w.p(
		"participation.assert_participant() throws a ValidationError. The refusal is not about the"
		" acting user's authority: a branch coordinator holding every permission there is may not"
		" file a deployment log for somebody who was not on the deployment either, because the"
		" record would be false. It is a rule about whether the document describes something that"
		" happened. The test suite proves it by filing the refused logs as Administrator, who"
		" bypasses core's geo scoping outright; if the rule were expressed as a permission, that"
		" would save."
	)

	w.h3("Where the rule lives")

	w.p(
		"In deployment/services/participation.py, with the roster it reads, and stated as"
		" participation.OWNERSHIP_RULE. volunteer/services/timelog.py asks; it holds no second copy"
		" of what participation means, and a test asserts that it does not name the participant"
		" doctype at all. The roster is read from the database at the moment of asking rather than"
		" from a document the caller handed in, so removing somebody from a roster stops their logs"
		" immediately."
	)


def _matching(w) -> None:
	w.h2("The matching service")

	w.lead(
		"Given a need — a terms of reference and a Geo Node — matching returns the volunteers who"
		" fit, within the searcher's own area. It is a service, not a page."
	)

	w.code(
		"matching.candidates(terms_of_reference, geo_node, as_of=None, limit=None) -> dict\n"
		"matching.candidates_for(doc, as_of=None, limit=None) -> dict"
	)

	w.p(
		"The second form takes a document that already carries a need. A VMMS Deployment Request and"
		" a VMMS Deployment both name a terms of reference and a Geo Node and both know when their"
		" work starts, so neither caller has to take those apart by hand. The date defaults to the"
		" day the work begins rather than to today: a request raised in March for work in June wants"
		" the people who will still be certified in June, and asking about today would answer a"
		" different question."
	)
	w.p(
		"There is no desk page, no client bundle and no portal route. vmmsx/api/deployment.py exposes"
		" find_candidates and find_candidates_for_request, and anything that wants a list calls one"
		" of them. The result is an explicit dict built field by field, never a Document and never a"
		" raw query result."
	)


def _the_scope_guarantee(w) -> None:
	w.h2("Why matching can never leak scope")

	w.lead(
		"A searcher can never be shown a volunteer they are not allowed to see, and there is no"
		" argument by which they could ask to be. Three things make that true, and each is"
		" load-bearing."
	)

	w.table(
		("What holds", "Why it holds"),
		[
			[
				"The scope is derived from the session and cannot be passed in.",
				"candidates() has no user parameter and no nodes parameter, and neither does the"
				" endpoint. A caller supplies what they are looking for, never who they are or where"
				" they may look. An endpoint that accepted a scope override would be an endpoint for"
				" reading anybody's register wearing a search-shaped name, and the check stopping"
				" that would be one more thing to get right. There is nothing to get right here, and"
				" the test that says so asserts on the signature.",
			],
			[
				"The scope comes from core, through the registration core's own enforcement uses.",
				"_searchable_nodes() asks core's registry which role scopes VMMS Volunteer — the"
				" society's vmms_volunteer_scope_role setting, resolved by core, never a role name"
				" written in this app — and then asks scope.get_user_geo_scope for that role's"
				" nodes. That is the identical pair of calls behind the list view's WHERE ... IN, so"
				" a volunteer this service returns is by construction a volunteer the searcher could"
				" already open, and the two cannot drift into disagreeing.",
			],
			[
				"It fails closed at every step.",
				"No resolvable role, no assignment, or a need anchored outside the searcher's area"
				" all produce an empty node set, and an empty node set produces no candidates. Empty"
				" is never read as unfiltered: the intersection is computed first and the query is"
				" not run at all when it is empty, because filters={'home_geo_node': ('in', [])} is"
				" the kind of thing a framework is entitled to treat as no filter.",
			],
		],
		(2.10, 4.40),
	)

	w.p(
		"The need's own subtree narrows it further, and the answer is an intersection in both"
		" directions. A national coordinator searching for a branch's work gets that branch's"
		" volunteers, not the country's. A branch coordinator searching for the region's work gets"
		" their branch, not the region. There is exactly one caller of get_user_geo_scope in this"
		" module and a test fails on the second, because two would be the beginning of a second"
		" scope model."
	)


def _matching_criteria(w) -> None:
	w.h2("What matching matches on, and what it does not")

	w.p(
		"The criteria that are real are enforced; the ones that are not are reported in every"
		" result. A candidate list that quietly omitted its own limitations would be read as these"
		" are the people who fit, and somebody would deploy on that reading."
	)

	w.h3("Real, and enforced")

	w.bullets(
		[
			"Geo scope, as the hard filter described above. This one is not negotiable by any"
			" other criterion: a volunteer outside the searcher's area who holds every required"
			" certification is still not returnable.",
			"The volunteer's own status. A Suspended or Exited volunteer is not a candidate,"
			" answered by certification.deployability(), which derives it.",
			"Certifications, with the lapse computed on the date being asked about. A mandatory"
			" requirement the volunteer does not hold, or holds lapsed, excludes them. A lapse of"
			" any type the society marked as blocking excludes them even if these particular terms"
			" did not ask for it. Nothing reads a stored flag, because there is no stored flag: the"
			" same volunteer reads as a candidate today and not as one on the deployment's start"
			" date, with no write in between, and a test asserts exactly that.",
			"Desirable certifications, which rank rather than exclude. Ranking is deliberately"
			" shallow — most desirable certifications held, then docname for a stable order —"
			" because sorting candidates by anything cleverer would be this app expressing an"
			" opinion about which volunteer a society ought to send.",
		]
	)

	w.h3("Pending, and reported in every result")

	w.p(
		"matching.PENDING_CRITERIA is returned with every search. Each entry names the criterion,"
		" whether it is pending or merely proposed, and why."
	)

	w.table(
		("Criterion", "Status and why"),
		[
			[
				"Skills",
				"Pending. There is no structured record of what a volunteer can do. A volunteer"
				" application collects declared skills as free text which no code reads, and the"
				" register holds no skill of its own. Matching on that text would be a substring"
				" search wearing a capability check's name, which is worse than not having one, so"
				" it is not done at all. A test strips docstrings from matching.py and fails if the"
				" free-text fields are read anywhere in its code.",
			],
			[
				"Availability",
				"Pending, for the same reason. Days, hours and shift patterns are society-variable"
				" and belong in a configured vocabulary that does not exist yet.",
			],
			[
				"Training in progress",
				"Pending. The learning seam awards a certification when a course completes, so"
				" somebody part way through the training these terms require is simply not yet"
				" certified and is not a candidate. Whether a society wants to see them anyway,"
				" marked as qualifying soon, is a decision nobody has taken.",
			],
			[
				"Already deployed elsewhere",
				"Proposed. Nothing excludes a volunteer who is already on another deployment over"
				" the same days. Whether double-booking should exclude somebody, warn about them,"
				" or be allowed outright is a society's policy and has not been decided, so no rule"
				" is invented.",
			],
		],
		(1.55, 4.95),
	)


def _the_opportunity_board(w) -> None:
	w.h2("The opportunity board, and why it reads a flag rather than a scope")

	w.p(
		"Matching runs one way: a coordinator asks who could do this work. The portal's"
		" Opportunities screen runs the other way, and it is a different question with a different"
		" answer. vmmsx.api.opportunities.browse() serves it, and it is the only read in this"
		" module that does not go through the permission layer."
	)

	w.p(
		"It cannot go through it. A volunteer holds no role on VMMS Deployment Request, and"
		" granting every volunteer read on that doctype so they could see a notice board would open"
		" a society's whole deployment planning to its entire volunteer body. So the boundary is a"
		" field on the record instead, the same shape VMMS Content Surface's is_public gives the"
		" public content read:"
	)

	w.bullets(
		[
			"is_published ships off. Nothing at all is visible until somebody who could already see"
			" a request decides to advertise it. No source file decides which requests a society"
			" would have wanted published, and there is no default that guesses.",
			"The DTO is built field by field and justification is not in it. That field is written"
			" for an approver; publishing a need is not publishing the internal case for it.",
			"Work whose needed_until has passed is dropped whatever the flag still says.",
		]
	)

	w.p(
		"Whether a published request is still worth offering is three predicates, in"
		" opportunities._is_offered(), and every one of them is asked of the service that owns it:"
		" approval.is_refused(), request.is_settled(), and the deployment's own status against"
		" deployment.OPEN_STATUSES where the request has produced one. Work that is Completed or"
		" Cancelled is not an opportunity, whatever flag is still set on the request that asked"
		" for it."
	)

	w.p(
		"The second of those is worth stating on its own, because the obvious implementation is"
		" wrong and looks right. Filtering the query on approval_state = 'Approved' would hide"
		" every advertisement a society using the direct mode ever published: such a request owes"
		" nobody an approval, so it never enters the engine and sits at Draft forever, and it is"
		" settled the moment it exists. The predicate answers that; a state comparison cannot."
		" This is the same rule membership activation and request fulfilment already follow, and"
		" the board follows it for the same reason."
	)

	w.p(
		"The elevation is therefore justified by what the query selects rather than by the call"
		" that makes it: every filter is fixed inside opportunities._published(), no caller can"
		" widen them, and the two that matter are decisions a permitted person already recorded on"
		" the record. The location facet narrows to a node and its subtree through core's adapter,"
		" so the portal's cascading selects mean the same thing on this screen as they do on a"
		" registration form."
	)

	w.p(
		"There is no way to answer an advertisement, and that is not an oversight. This app has no"
		" record of a volunteer offering themselves for a deployment: a coordinator matches people"
		" through find_candidates and adds them to a roster, which is the ownership rule above. The"
		" screen says so on every card rather than drawing a button that would have nowhere to"
		" write."
	)


def _branch_transfer(w) -> None:
	w.h2("Branch transfer")

	w.lead(
		"A volunteer moves from one branch to another. One field changes on one other record, and"
		" the design is mostly an argument about what must not change with it."
	)

	w.p(
		"A transfer names the volunteer, where they are, where they are going, when it takes"
		" effect and why. from_geo_node is snapshotted rather than typed. effective_date decides"
		" when: a date today or in the past applies on the next save once approval is settled, and"
		" a future date waits for the daily sweep, so a transfer arranged in advance happens on the"
		" day it was arranged for rather than the day it was typed."
	)
	w.p(
		"Two lifecycles run alongside each other, exactly as they do on a membership."
		" approval_state is the engine's and is written only by the engine; transfer_status is the"
		" operational one and says whether anybody has actually moved. A transfer under a society"
		" that does not route them stays at Draft forever and still applies, because the absence of"
		" an approval is not an approval and writing Approved onto a record nobody approved would be"
		" a lie in an audit trail."
	)

	w.h3("Rules on raising one")

	w.bullets(
		[
			"A transfer to where somebody already is is refused. Saved, it would sit in the"
			" register looking like a move that happened, and it would route to an approver with"
			" nothing to decide.",
			"One open transfer per volunteer. Two would each have snapshotted the same origin and"
			" would each expect to move the volunteer from it; whichever applied second would"
			" either move somebody who had already moved or sit there looking unexplained.",
			"The destination must satisfy the level rule a volunteer's placement always did"
			" (ACC-03), asked of the Volunteer module's own vmms_volunteer_anchor_level rather than"
			" of a second setting here. Where a volunteer may be placed is one question with one"
			" answer, and two settings meaning it would let a transfer put somebody somewhere they"
			" could not have been registered.",
			"A reason is required. A change to who can see somebody and who approves for them, with"
			" no reason recorded, is one nobody can review afterwards.",
			"A transfer that has taken effect cannot be cancelled or deleted. Moving somebody back"
			" is another transfer, with its own reason and its own approval, rather than the undoing"
			" of this one.",
		]
	)


def _the_history_rule(w) -> None:
	w.h2("A transfer does not rewrite history")

	w.lead(
		"A volunteer who was deployed at their old branch was deployed at their old branch. Only"
		" their current placement moves."
	)

	w.p(
		"Stated as a consequence rather than as an intention: there is no code in"
		" deployment/services/transfer.py that touches a deployment, a time log or a certification,"
		" and no code anywhere else that rewrites one when a volunteer moves. Past deployments keep"
		" the Geo Node they were run at, time logs keep the Geo Node the time was served at, and"
		" certifications are not about a place at all. The rule is stated as transfer.HISTORY_RULE"
		" and a test records every anchor and date a volunteer's history carries, runs a transfer,"
		" and asserts each one is what it was."
	)

	w.h3("The scope consequence falls out of core's model, and needed no code")

	w.bullets(
		[
			"The old branch keeps seeing the records anchored beneath it, because geo scope is a"
			" question about a record's own anchor and those anchors did not move.",
			"The new branch sees the volunteer, because the volunteer's anchor is the one thing"
			" that did, and VMMS Volunteer is scoped on exactly that field.",
			"The old branch stops seeing the volunteer as one of theirs, for the same reason and at"
			" the same instant.",
			"The transfer record itself stays with the old branch, because it is anchored on"
			" from_geo_node and it is a record about the branch that lost somebody.",
		]
	)

	w.p(
		"Nothing had to be written to make any of that true, which is the argument for storing a"
		" placement in exactly one place. The tests assert it through core's own is_in_scope, so"
		" what they observe is the verdict a list view, a document read and an API guard would each"
		" reach, rather than a fourth opinion assembled for the occasion."
	)

	w.h3("A volunteer stays on the deployments they served")

	w.p(
		"Including deployments that are still running. A transfer applied mid-deployment writes a"
		" comment naming what was in flight, and changes nothing about it: the deployment keeps its"
		" own anchor and its own roster, the volunteer stays on it, and they may still log time"
		" against it afterwards, because ownership is the roster and the roster did not change."
	)


def _transfer_open_questions(w) -> None:
	w.h2("Branch transfer: what is still open")

	w.p(
		"This part of the module is new, and the decisions below were made in order to have"
		" something reviewable rather than because they are settled. Each one is a proposal, and"
		" each is cheap to change because the alternative is a configuration value or a single"
		" predicate."
	)

	w.table(
		("Question", "What was built, and the alternative"),
		[
			[
				"Should a transfer be approved at all?",
				"It is configuration, vmms_transfer_approval_mode, shipped empty. Empty reads as the"
				" direct mode, so a site migrating into this module does not discover that every"
				" transfer now throws for want of a workflow it has never been asked to create. The"
				" recommended posture is routed, and the field's own description says so: moving a"
				" volunteer between branches changes who can see them and who approves for them.",
			],
			[
				"Which branch approves it?",
				"The one the volunteer is leaving, because the record is anchored on from_geo_node"
				" and the engine routes from whichever field the workflow names. A society that"
				" would rather the receiving branch decide points its workflow's geo_node_field at"
				" to_geo_node, which needs no code change at all. What is not built is both"
				" branches having to agree, which would be a two-stage workflow and is expressible"
				" today by configuring two stages.",
			],
			[
				"What happens to an in-flight deployment?",
				"Nothing. It is reported on the transfer and in the get_transfer DTO, and the"
				" volunteer stays on it. The alternatives are refusing the transfer while somebody"
				" is deployed, or deferring it to the deployment's end. Recording it is the only one"
				" of the three that does not invent a rule, but it is the one most likely to be"
				" wrong for a particular society.",
			],
			[
				"What if the volunteer moved by other means first?",
				"The transfer is not applied. Moving somebody from a place they are no longer in is"
				" a silent overwrite, so the transfer stays Pending and the daily sweep counts it as"
				" overtaken and logs it. The alternative is applying it anyway. The risk with what"
				" was built is that a transfer nobody looks at sits Pending indefinitely.",
			],
			[
				"Do open applications and requests move with the volunteer?",
				"No. Nothing re-anchors any other record, which is the same rule as the history"
				" one. Whether an open volunteer application anchored at the old branch should"
				" follow somebody is genuinely arguable and has not been decided.",
			],
		],
		(2.10, 4.40),
	)


def _approval_is_configuration(w) -> None:
	w.h2("Approval, where a society wants it, is the engine's and nothing else's")

	w.lead(
		"Two records here can be gated by an approval, and neither is gated by default. Both read"
		" the same two values and dispatch through the same two tables."
	)

	w.bullets(
		[
			"direct — there is no approver. The requirement is settled the moment it is asked"
			" about, and what happens next is governed by the operational predicate.",
			"routed — the VMMS approval engine routes it to a resolved person, who approves or"
			" rejects it, exactly as it routes a volunteer application or a membership.",
		]
	)

	w.p(
		"A deployment request reads its mode from its terms of reference, so a society may route"
		" international deployments and wave through a branch first-aid duty. A branch transfer"
		" reads one society-wide setting, because a transfer has no type to hang it off. The two"
		" tables in deployment/services/approval.py are keyed by the configuration value itself, so"
		" adding a mode is adding an entry, and a society switching one piece of work under an"
		" approval is a settings change that no source file knows happened. This is the shape"
		" member/services/approval.py proved with approval_mode on a membership type, reused rather"
		" than reinvented."
	)
	w.p(
		"There is no shadow approval anywhere in this module. Nothing here decides that somebody"
		" may act because they hold a role — that is the mistake Frappe's native Workflow makes and"
		" the reason this app does not use it — and a test fails if any file in the module calls"
		" frappe.get_roles. The behavioural half is tested too: a user who holds the required role,"
		" at the wrong place, with every permission needed to open the record, is refused by the"
		" engine's person-gate, and nothing is deployed and nobody is moved when they are."
	)
	w.p(
		"Choosing routed with no workflow configured for the doctype is refused loudly rather than"
		" quietly deploying unapproved. That is the intended failure: a misconfiguration that"
		" silently removed an approval would be the worst outcome available."
	)


def _scoping(w) -> None:
	w.h2("Geo scoping: three doctypes, three questions, three settings")

	w.p(
		"All three of this module's own operational doctypes are registered with core through"
		" onerc_scopeable_doctypes, and each names its role with role_from_setting rather than a"
		" literal, because which of a society's roles may see what is that society's decision."
	)

	w.table(
		("Doctype", "Anchor field", "Settings field"),
		[
			[DEPLOYMENT, "geo_node", "vmms_deployment_scope_role"],
			[REQUEST, "geo_node", "vmms_deployment_request_scope_role"],
			[TRANSFER, "from_geo_node", "vmms_branch_transfer_scope_role"],
		],
		(2.30, 1.70, 2.50),
	)

	w.p(
		"Three settings rather than one, because these are three questions. A society may well let"
		" every coordinator see the deployments running in their area while keeping who asked for"
		" what, and who is being moved between branches, narrower. Folding them together would make"
		" that a choice nobody could express, and the tests assert that holding one grant does not"
		" confer another."
	)
	w.p(
		"All three ship empty, which means no role resolves and core fails closed: until a society"
		" chooses each role, no non-administrator can read one of these records. That is the correct"
		" pre-portal state for records naming where the society is working, who it sent, and who is"
		" being moved. Core logs every unresolved read, so the closed state is visible rather than"
		" looking like nobody having been granted anything yet."
	)

	w.h3("Why a deployment request is scoped and a volunteer application is not")

	w.p(
		"The volunteer application is deliberately not registered: its access is the approval"
		" engine's person-gate, and scoping it as well would put two different answers to may you"
		" touch this in front of one document. A deployment request is different, because a request"
		" under terms of reference configured as direct never reaches the engine at all, so the"
		" person-gate is not an access model for it and scoping is the only answer it has. Where a"
		" society does route one, the two agree by construction rather than competing: routing only"
		" ever names holders whose scope covers the node, which is the same property that lets VMMS"
		" Membership be both approvable and scopeable."
	)


def _configuration(w) -> None:
	w.h2("What a society configures")

	w.table(
		("Setting", "What it decides, and what empty means"),
		[
			[
				"vmms_deployment_anchor_level",
				"ACC-03. The geo level a deployment and a deployment request must be anchored at."
				" Empty means any level, which is unconstrained rather than forbidden. One setting"
				" governs both, because they are two views of the same piece of work and anchoring"
				" them at different levels would leave a request unable to become the deployment it"
				" asked for.",
			],
			[
				"vmms_transfer_approval_mode",
				"Whether a branch transfer needs authorising. Empty reads as direct, which is the"
				" shipped state and changes nothing about a site migrating into this module. Most"
				" societies will want routed.",
			],
			[
				"vmms_deployment_scope_role, vmms_deployment_request_scope_role,"
				" vmms_branch_transfer_scope_role",
				"Which role may see each kind of record, combined with that role's Geo Assignments."
				" All three ship empty and empty means closed, which is the one place in this module"
				" where empty is a refusal rather than an absence of constraint.",
			],
			[
				"VMMS Terms of Reference records",
				"What the society deploys volunteers to do: the purpose, the responsibilities, the"
				" certifications a candidate needs, where the terms apply, and whether a request"
				" under them is routed. No terms of reference is shipped, because they name real"
				" work a society does and this app has no business inventing one.",
			],
			[
				"VMMS Approval Workflow records",
				"Only needed for a doctype a society has chosen to route. The stages, the roles they"
				" require, how many must act and how long they have are all the engine's ordinary"
				" configuration and are described in the Approval Engine section.",
			],
		],
		(2.05, 4.45),
	)

	w.p(
		"All five settings fields are Custom Fields vmmsx owns on core's National Society Settings,"
		" installed by vmmsx.patches.setup_deployment_module and"
		" vmmsx.patches.install_deployment_scope_roles. Core's doctype is not edited: a product"
		" pushing its own fields into the shared foundation's schema is how the foundation stops"
		" being shared."
	)


def _not_here_yet(w) -> None:
	w.h2("What this module deliberately does not hold")

	w.table(
		("Not here", "Why, and what would have to be decided first"),
		[
			[
				"Skill-based matching",
				"Described above and reported in every search result. It is waiting on a structured"
				" record of what a volunteer can do, which neither this module nor the volunteer"
				" register has invented. Both are waiting on the same decision, and neither has"
				" guessed at it.",
			],
			[
				"Automatic rostering",
				"Nothing puts anybody on a deployment. Matching answers who could go; a coordinator"
				" decides who does, with facts this app does not hold. A request that deployed the"
				" first N matches would be this software deciding who serves.",
			],
			[
				"Deployment cost, per diem and stipend",
				"Money is phase 2 and goes through onerc_payments exactly as membership fees do."
				" Nothing here holds an amount, a rate or a currency.",
			],
			[
				"Equipment, transport and accommodation",
				"A deployment records who was sent and when. What they were given is a logistics"
				" model, and it would be a module of its own rather than fields on this one.",
			],
			[
				"A deployment report or after-action record",
				"What happened on a deployment, as a structured record. Time logs capture the hours;"
				" the narrative is a society's own paperwork today. What such a record would need to"
				" hold, and who signs it, has not been decided.",
			],
			[
				"Double-booking rules",
				"Listed as a proposed matching criterion above. Whether a volunteer on two"
				" overlapping deployments is an error, a warning or ordinary is a society's policy.",
			],
		],
		(2.05, 4.45),
	)


def _what_is_tested(w) -> None:
	w.h2("What is tested, and what each suite is written to catch")

	w.p(
		"Integration tests against a real site. Geo comes from core's geo fixtures, identity from"
		" core's Red Profile, authority from real Geo Assignment rows, and approval from a real"
		" VMMS Approval Workflow driving the real engine. Two hierarchies are built, shaped and"
		" named differently, so that no level name and no role name can be relied on by accident."
	)

	w.table(
		("Suite", "What it proves"),
		[
			[
				"test_deployment.py",
				"ACC-02: a deployment or a request with no Geo Node is refused at creation and"
				" nothing is saved. ACC-03: with no level configured any level is accepted, a"
				" configured level refuses another, and a second society narrows to a differently"
				" named level with the same code. The terms of reference's own geo scope refuses a"
				" node outside its subtree and an ancestor of it. A period running backwards is"
				" refused, a volunteer listed twice on a roster is refused, and the status"
				" transition table refuses reopening a completed deployment while still allowing an"
				" ordinary save that does not change the status.",
			],
			[
				"test_ownership.py",
				"A participant's deployment log saves, counts towards their hours, and saves after"
				" the deployment has completed. A non-participant's is refused at save with nothing"
				" written, including for a volunteer anchored at the very same Geo Node, including"
				" as Administrator, and including when the deployment does not exist. Removing"
				" somebody from a roster stops their logs. The general path is unchanged and a"
				" general log naming a deployment is still refused for its own reason. One volunteer"
				" on two deployments at two nodes may log against both and each log is attributable"
				" to the right one, while a volunteer on only one is refused against the other. The"
				" stage-4 stub, its constants and the old Data field are all asserted gone.",
			],
			[
				"test_matching.py",
				"An out-of-scope volunteer is never returned, including one holding every mandatory"
				" certification, anchored inside the need's subtree, whom a wider searcher does see."
				" A searcher with no assignment and a society with no scope role configured both get"
				" nothing. The signature is asserted to have no user, nodes or scope parameter, on"
				" the service and on the endpoint. The need narrows a wide searcher and does not"
				" widen a narrow one, and another society is never reached. Certification matching"
				" is exercised for a missing requirement, a lapsed one, a lapse of a type the"
				" society does not treat as blocking, and the same volunteer reading differently on"
				" two dates with no write in between. The pending criteria are asserted present in"
				" every result, and a docstring-stripped scan asserts no free-text declaration is"
				" read by the code.",
			],
			[
				"test_request.py",
				"A direct request becomes a deployment on submission, carrying the terms, place and"
				" dates, with nobody on the roster, without touching the approval state and without"
				" any workflow existing; submitting twice creates one deployment. A routed request"
				" enters review, routes to the person the engine resolved, lands in their queue, and"
				" becomes a deployment when they approve. The wrong approver is refused although"
				" they hold the role and can open the record, and nothing is deployed when they are."
				" A rejected request never becomes a deployment, including when it is saved again"
				" afterwards. Two requests differing only in one configuration value take the two"
				" different paths.",
			],
			[
				"test_transfer.py",
				"An effective transfer moves home_geo_node and stamps itself; applying twice moves"
				" nobody twice; a future-dated one waits and the daily sweep applies it"
				" idempotently. Every geo anchor and date the volunteer's history carries is"
				" recorded before the move and asserted unchanged after it, and the module's source"
				" is asserted not to name a time log or a certification at all. Core's own is_in_scope"
				" answers the before-and-after questions for both branches. The routed mode is"
				" exercised end to end, including the wrong approver and a rejection, and the shipped"
				" empty setting is asserted to apply directly. A transfer to where somebody already"
				" is, a second open one, a destination at the wrong level and a missing reason are"
				" all refused; an effective one cannot be cancelled or deleted; an overtaken one is"
				" counted rather than applied.",
			],
			[
				"test_scoping.py",
				"All three doctypes are registered, each on a field its doctype actually has, and"
				" none names a role literally. An unconfigured role denies everybody and an unplaced"
				" record is inside nobody's scope. Scope is subtree-shaped: a viewer sees beneath"
				" themselves and not a sibling, not above, and not another society. Holding one of"
				" the three grants does not confer another, and each viewer does see their own.",
			],
			[
				"test_delegation.py",
				"No file in the module resolves approvers or queries Geo Node or Geo Assignment"
				" directly, while geo is asserted to be read through core's adapter so the negative"
				" tests are not passing vacuously. get_user_geo_scope has exactly one caller and the"
				" scan fails on a second. No file decides authority from role membership, and none"
				" writes the engine's contract fields. The stage-branching scan is asserted to cover"
				" this module's files, and no role name, certification key or geo node name from the"
				" fixtures appears in any source file.",
			],
		],
		(1.55, 4.95),
	)
