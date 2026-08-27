# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Volunteer section of the guide (phase 1, plus what stage 4 finished here).

Field tables are generated from the doctype JSON; every other claim names the
file or function it describes.

One thing in this section changed after it was written, and is corrected rather
than left: the deployment time log, which this module shipped as an explicit
stub, is live. The rule that finished it belongs to the Deployment module, so
this section says what the seam is and the Deployment section describes the
rule. A guide is only worth reading if it is accurate, so a claim that has
stopped being true is corrected in place.

Phase 2 (stipend documents) is not in this section because it is not built.
"""

from vmmsx.docs import doctypes

TITLE = "Volunteer"
SUMMARY = "The volunteer register, its application, certifications, time logs, and the LMS and HR seams."

VOLUNTEER = "VMMS Volunteer"
APPLICATION = "VMMS Volunteer Application"
SKILL = "VMMS Skill"
MOTIVATION = "VMMS Motivation"
AVAILABILITY_SLOT = "VMMS Availability Slot"
CERTIFICATION = "VMMS Certification"
CERTIFICATION_TYPE = "VMMS Certification Type"
COURSE_MAPPING = "VMMS Course Mapping"
TIME_LOG = "VMMS Time Log"
TIME_LOG_CATEGORY = "VMMS Time Log Category"


def render(w) -> None:
	w.h1(TITLE)

	_what_it_is(w)
	_volunteer(w)
	_application(w)
	_application_vocabularies(w)
	_certification_type(w)
	_certification(w)
	_course_mapping(w)
	_time_log(w)
	_time_log_category(w)
	_the_engine_again(w)
	_living_and_historical(w)
	_the_volunteer_page(w)
	_queryable_capabilities(w)
	_two_providers(w)
	_derived_lapse(w)
	_learning_seam(w)
	_log_types_and_ownership(w)
	_hr_seam(w)
	_scoping(w)
	_configuration(w)
	_not_here_yet(w)
	_what_is_tested(w)


# --- what it is ------------------------------------------------------------


def _what_it_is(w) -> None:
	w.h2("What the Volunteer module is")

	w.lead(
		"Volunteering is what most national societies are actually made of, and this module is the"
		" register of it: who volunteers, where they belong in the organisation, what they are"
		" qualified to do, and how much time they have given."
	)
	w.p(
		"Like Member before it, it owns very little on its own. Identity belongs to onerc_core's"
		" Red Profile. Routing and the approval gate belong to the approval engine. Training"
		" belongs to whichever learning system the society runs. Employment records belong to"
		" Frappe HR. What is left, and what this module is, is the answer to two questions: is this"
		" person a volunteer of this society, and may they be deployed."
	)
	w.p(
		"Seven doctypes carry that. The services are in vmmsx/volunteer/services/, and every one of"
		" them is idempotent and takes documents rather than names."
	)

	w.h3("Acceptance is a predicate, not a sequence")

	w.p(
		"A volunteer application becomes a volunteer when two things are true: the approval engine"
		" has settled the application as Approved, and no volunteer has been created from it yet."
		" Both are questions about the record rather than about which code path happened to run, so"
		" application.try_accept() is safe to call after any event and in any order. It is called"
		" from the controller's on_update, which runs after every save, which is how a decision"
		" recorded by the approval engine becomes a volunteer without the engine knowing that"
		" volunteers exist. This is the same shape membership activation has, deliberately."
	)

	w.h3("Three things are seams, and each is exactly one file")

	w.bullets(
		[
			"The learning system, in volunteer/services/learning.py. It reads one fact out of the"
			" LMS and writes one record of ours. No LMS model exists anywhere else in the app.",
			"Frappe HR, in volunteer/services/hr.py. One nullable link, pointing outward, carrying"
			" nothing back. No employment model crosses it in either direction.",
			"Money, which is not here at all. Volunteer stipends are phase 2 and will go through"
			" onerc_payments exactly as membership fees do.",
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


def _volunteer(w) -> None:
	w.h2(VOLUNTEER)

	_doctype_block(
		w,
		VOLUNTEER,
		[
			"A person's volunteering identity: one record per person who has ever been accepted. It"
			" links to a Red Profile, records where it sits in the geo tree, holds what that person"
			" can currently do, and holds its own derived state.",
			"It stores no name, no email and no phone, and there is no fetch_from on it either,"
			" which would be a stored copy wearing a different hat. Every name in a queue and every"
			" field handed to HR is read through vmmsx/volunteer/services/identity.py, which reads"
			" Red Profile at the moment of asking.",
			"What it does hold, since the coordinator's view, is the volunteer-owned attributes:"
			" skills, languages, availability, citizenship and residency. Those are facts about"
			" somebody's volunteering that change while they volunteer, and the dividing line"
			" against identity is ownership rather than convenience. The living-versus-historical"
			" section below states the test that decides which side a field falls on.",
			"home_geo_node is the Serving Branch and the ACC-02 anchor: the fieldname is historical"
			" and predates the two placement questions being told apart, and the label is what it"
			" holds. Where somebody lives is a different question, it belongs to the person rather"
			" than to their volunteering, and core already answers it as Red Profile.home_geo_node.",
			"The seven HTML fields on it — identity_card, deployability_indicator,"
			" certifications_held, deployment_history, time_served, verification_outcome and"
			" declared_at_application — back no column and hold nothing. They are where the form"
			" script paints what it has just read; see the section on the coordinator's view below.",
			"In core's Design 2 this record is the satellite, which means it is the truth. The row"
			" on the person's Red Profile affiliation index is a summary written from here through"
			" set_affiliation(); nothing anywhere reads that row back to decide anything.",
			"Its status is derived where it can be and explicit where it must be. Prospective and"
			" Active are read off the volunteer's approved applications by"
			" volunteer.derive_status(). Suspended and Exited are acts of the society, recorded by"
			" volunteer.suspend() and volunteer.record_exit(), and a derivation must never undo one"
			" by finding an old approved application still lying there.",
		],
	)


def _application(w) -> None:
	w.h2(APPLICATION)

	_doctype_block(
		w,
		APPLICATION,
		[
			"The operational record that becomes a volunteer on approval, and the approval engine's"
			" third consumer after the engine's own test doctype and VMMS Membership.",
			"It satisfies the engine's document contract: approval_state, approval_stage,"
			" approval_stage_entered_on, a Table of VMMS Approval Decision, and a mandatory Link to"
			" Geo Node (Serving Branch, below). Those four engine fields are declared here and"
			" written only by the engine; this module never touches them except to read the state.",
			"docstatus is not used. The application stays at docstatus 0 for its whole life and"
			" approval_state is its lifecycle, which is the engine's rule for every approvable"
			" doctype.",
			"There are no desk workflow buttons on it. A decision is made through"
			" vmmsx/api/approvals.py, the generic engine endpoint, because the person-gate lives"
			" there and a second door into the same decision would be a second place to get it"
			" wrong.",
		],
	)

	w.h3("Structured declarations, and why skills stopped being a sentence")

	w.p(
		"skills, languages, availability and motivation are all Table MultiSelects of a society's"
		" own vocabulary rather than free text. skills points at VMMS Skill, motivation at"
		" VMMS Motivation and availability at VMMS Availability Slot — three doctypes shaped"
		" identically (a name, a stable key, is_active, a description) and seeded with a starting"
		" set by vmmsx.patches.setup_volunteer_application_module. languages points at Frappe's own"
		" Language doctype, reused rather than reinvented: core already links to it from Red Profile"
		" and National Society Settings, and a second list of the world's languages would be a"
		" second thing to keep in sync with the first."
	)
	w.p(
		"Each is a real Link, not a sentence, so a coordinator can filter volunteers by a skill —"
		" frappe.get_all('VMMS Skill Selector', filters={'skill': ..., 'parenttype': 'VMMS Volunteer"
		" Application'}) — which a Small Text field never allowed. Nothing in this app branches on a"
		" skill, motivation or availability key: the vocabulary is the society's, extended freely,"
		" and adding a row makes it selectable with no code change. prior_experience alone stays"
		" free text, a narrative the approver reads and nobody parses."
	)

	w.h3("Citizenship and residency, decoupled on purpose")

	w.p(
		"country_of_citizenship is always asked, and defaults at creation to the society's own"
		" configured country — National Society Settings.country, read through"
		" vmmsx.volunteer.services.society.default_citizenship_country(), never a literal. It is"
		" freely changeable: a foreign national volunteering locally answers it as honestly as a"
		" citizen does."
	)
	w.p(
		"residency_type is a Local/Abroad toggle, Local by default, and it asks an entirely"
		" different question from citizenship. Local shows home_geo_node ('Home Area'), captured"
		" through the same cascading picker Serving Branch uses — vmmsx.api.geo, a thin whitelisted"
		" door onto onerc_core's adapter, walking the tree one rung at a time so the client never"
		" assumes a level name or a depth. Abroad shows country_of_residence and residence_address"
		" instead: there is no Geo Node to anchor an overseas address to. reconcile_residency(),"
		" called from validate(), clears whichever half the current toggle does not use, so a"
		" record never carries a stale answer to the question it is no longer asking."
	)
	w.bullets(
		[
			"A citizen of this society's own country living abroad, and a foreign national living"
			" and volunteering locally, both save correctly: citizenship and residency are two"
			" columns, and neither constrains the other.",
			"assert_ready() — called from application.submit(), not validate() — refuses submission"
			" until whichever half residency_type selected is actually complete: Local without a"
			" Home Area, or Abroad without both a country and an address, is refused with a stage"
			" name in the error, not a generic one.",
		]
	)

	w.h3("Home Area is not Serving Branch")

	w.p(
		"geo_node — relabelled Serving Branch on the form — is the ACC-02 anchor: where this"
		" volunteer will serve, and the place the approval engine routes from. home_geo_node is"
		" where they live. The two are deliberately different fields answering deliberately"
		" different questions, because conflating 'where you are' with 'where you will work' is"
		" exactly the ambiguity a coordinator most needs the form not to have."
	)
	w.p(
		"default_serving_branch(), called from validate() before the ACC-02 anchor check, fills"
		" Serving Branch from Home Area when residency is Local and Serving Branch is still blank —"
		" most people serve near home, and this is what stops the form asking the same question"
		" twice. It never overwrites a value a coordinator already chose, and it never fires for"
		" Abroad: an applicant living abroad has no home area to default from, and the ordinary"
		" ACC-02 reqd check refuses the save until Serving Branch is given explicitly. No extra code"
		" was needed for that half; the anchor rule already does it."
	)

	w.h3("Identification: optional there, mandatory here")

	w.p(
		"id_type (Link to core's Identification Type) and id_number are both optional at the field"
		" level — a desk clerk building a paper application up over several saves may leave them"
		" blank, the same allowance ACC-02's own anchor does not get. What is new is that submission"
		" itself refuses to proceed without them: application_service.assert_ready(), called at the"
		" top of submit(), throws a MandatoryError naming exactly what is missing. Once present,"
		" _sync_identification_to_profile() writes them onto the applicant's Red Profile"
		" identifications table — core's own table, reused rather than duplicated — idempotently, so"
		" resubmitting an application already in review does not pile up a second row."
	)
	w.p(
		"Red Profile itself is untouched by this rule: identification stays optional there, because"
		" not every person core knows has been asked for one. The asymmetry is the whole point —"
		" this application is where a society draws the line, not the identity spine everything"
		" else shares."
	)

	w.h3("The portal journey: engaging questions first, identity last")

	w.p(
		"/portal/join?path=volunteer orders its steps skills/languages/availability/motivation, then"
		" where you would serve, then citizenship and residency, then personal details, then"
		" identification last — the onboarding-funnel pattern of asking for invested effort before"
		" personal data. A returning applicant who already has a Red Profile — the cross-registration"
		" case — is not asked their name a second time: vmmsx.api.volunteer.my_registration_prefill()"
		" reads it live and the form prefills and locks those fields, because"
		" registration/services/intake.py would silently ignore anything typed over them anyway."
	)

	w.h3("The coordinator's view")

	w.p(
		"Opening an application, a coordinator sees an Applicant Identity card — full name, email,"
		" phone, read live through identity.py and stored nowhere on this record — above the same"
		" structured fields above: citizenship, residency (whichever half applies), Serving Branch,"
		" skills, languages, availability, motivation, prior experience, and the identification the"
		" application required to reach this screen. vmmsx.api.volunteer.get_decision() assembles"
		" the same picture for any caller with read access, field by field, as an explicit dict — the"
		" DTO rule holding here exactly as it does everywhere else in this app."
	)


def _application_vocabularies(w) -> None:
	w.h2("The application's own vocabularies")

	w.p(
		"Three doctypes, one shape, seeded by vmmsx.patches.setup_volunteer_application_module and"
		" owned by the society from the moment they land. Each pairs a display name with a stable"
		" business key an application points at, so relabelling a row never rewrites history, and"
		" none of them is ever compared against in code — grep finds every key below only in this"
		" patch and in test fixtures."
	)

	_doctype_block(
		w,
		SKILL,
		[
			"What an applicant can do. Seeded with first_aid, driving, logistics, counselling, it and translation."
		],
	)
	_doctype_block(
		w,
		MOTIVATION,
		[
			"Why an applicant wants to volunteer. Seeded with community_service, skill_building,"
			" career_development, faith and personal_growth."
		],
	)
	_doctype_block(
		w,
		AVAILABILITY_SLOT,
		[
			"When an applicant says they can serve — a doctype rather than a Select for the same"
			" reason Skill and Motivation are: this module already has a proven shape for a"
			" society-editable multi-select vocabulary, and a bespoke one for availability would be a"
			" second answer to a question already answered twice. Seeded with weekday_mornings,"
			" weekday_evenings, weekend_mornings, weekend_evenings, public_holidays and on_call."
		],
	)

	w.p(
		"Four child doctypes exist only to give Table MultiSelect a row shape to store — VMMS Skill"
		" Selector, VMMS Motivation Selector, VMMS Availability Selector and VMMS Language Selector,"
		" each one Link field and nothing else. None of the four names an autoname: a child row's"
		" name is Frappe's own generated one, deliberately, because the value it links to is not"
		" unique across every application that might select it — two applicants both declaring"
		" first_aid must produce two rows, not a collision."
	)


def _certification_type(w) -> None:
	w.h2(CERTIFICATION_TYPE)

	_doctype_block(
		w,
		CERTIFICATION_TYPE,
		[
			"A society's own list of the qualifications it recognises, and the source of every"
			" expiry date in the module. Keyed by its stable business key, following core's rule"
			" that configuration vocabularies are keyed by the identifier code refers to while"
			" records about people and places get opaque IDs.",
			"No certification name appears in any source file in this app. First aid, psychosocial"
			" support and water and sanitation are rows a society writes; the code knows only that"
			" a type has a validity period and a policy about what a lapse costs.",
		],
	)


def _certification(w) -> None:
	w.h2(CERTIFICATION)

	_doctype_block(
		w,
		CERTIFICATION,
		[
			"A qualification a volunteer holds. One row per volunteer per type: a renewal moves the"
			" dates on the row that is already there rather than adding a second, so 'which of"
			" these two is current' is a question the schema does not allow anybody to ask.",
			"Two dates are stored. completion_date is entered by a human or written by the learning"
			" seam; expiry_date is computed from it and the type's configured validity period by"
			" certification.apply_expiry(), on every save, so a society correcting a validity period"
			" brings the certifications already held along with it.",
			"What is deliberately absent is any record of whether the certification has lapsed. See"
			" the section on derived lapse below.",
		],
	)


def _course_mapping(w) -> None:
	w.h2(COURSE_MAPPING)

	_doctype_block(
		w,
		COURSE_MAPPING,
		[
			"One row per course a society treats as a qualification: complete that course, hold that"
			" certification. This doctype is the whole of the learning seam's configuration. There"
			" is no dictionary in a source file, and no course name in any of this app's code.",
			"external_course is Data rather than a Link, deliberately. A Link would put an LMS"
			" doctype name inside a vmmsx doctype and make this app fail to install on a site with"
			" no learning system. The same reasoning made VMMS Membership's payment_transaction a"
			" Data field: a seam is a contract between apps, not a shared schema.",
		],
	)


def _time_log(w) -> None:
	w.h2(TIME_LOG)

	_doctype_block(
		w,
		TIME_LOG,
		[
			"A record that a volunteer served time somewhere on some day. Both kinds are live: a"
			" general log stands on its own, and a deployment log names a VMMS Deployment and is"
			" accepted only if that deployment's roster lists this volunteer. See the section on"
			" log types below.",
			"Every log carries a geo anchor, whatever kind it is (ACC-02), and the anchor is checked"
			" before the kind's own rule runs, so a deployment log with no anchor is refused for the"
			" anchor rather than for anything about deployments.",
		],
	)


def _time_log_category(w) -> None:
	w.h2(TIME_LOG_CATEGORY)

	_doctype_block(
		w,
		TIME_LOG_CATEGORY,
		[
			"How a society classifies volunteered time for its own reporting: training, community"
			" event, office support. An open vocabulary, seeded by"
			" vmmsx/patches/setup_volunteer_module.py and owned by the society from the moment it"
			" lands.",
			"No code anywhere branches on a category value, which is exactly what distinguishes it"
			" from log_type on the time log itself. log_type names a validation rule and is"
			" therefore code; a category names nothing and is therefore configuration. Both live on"
			" the same record on purpose, so the difference is visible on the form.",
		],
	)


# --- how it works ----------------------------------------------------------


def _the_engine_again(w) -> None:
	w.h2("The approval engine, consumed for the third time")

	w.lead(
		"The interesting thing about a third consumer is that it needed nothing new. Volunteer"
		" Application declares the contract fields, a society writes one VMMS Approval Workflow"
		" naming the doctype, and everything else is the engine as it already was."
	)
	w.p(
		"Nothing under vmmsx/volunteer/ resolves an approver, queries the geo tree, or decides who"
		" may act. application.submit() calls engine.submit(), which enforces the anchor rules,"
		" resolves people through core's resolve_approvers, moves the state through states.py and"
		" puts the document in the resolved approvers' queues. A decision goes through"
		" engine.decide(), which recomputes the authorised set from Geo Assignment on every single"
		" call and refuses anybody who is not in it."
	)
	w.p(
		"That refusal is the point of the whole design, and it is worth stating precisely: holding"
		" the role a stage names is not enough. Being a Volunteer Approver somewhere does not make"
		" you this application's Volunteer Approver. Frappe's native Workflow can only ask the first"
		" question, which is why the engine exists."
	)
	w.p(
		"The delegation is enforced against the source rather than remembered."
		" volunteer/tests/test_delegation.py walks the AST of every file under volunteer/ and fails"
		" if one of them calls resolve_approvers or get_user_geo_scope, or names Geo Assignment or"
		" the geo tables in a query. It also asserts the positive half: some file does read geo, and"
		" only through core's adapter, so the scan cannot pass by the module having quietly stopped"
		" using geo at all."
	)

	w.h3("What acceptance does, in order")

	w.steps(
		[
			"The engine settles the application as Approved and saves it.",
			"on_update fires; application.try_accept() finds the predicate true.",
			"volunteer.ensure() creates the satellite, anchored where the application was"
			" anchored, or returns the existing one for somebody who has volunteered before.",
			"The application records the volunteer it produced, which is what makes acceptance"
			" idempotent rather than something that could run twice.",
			"volunteer.refresh() derives the status from the applications and reports it to core's"
			" affiliation index through set_affiliation().",
			"hr.provision() runs last and cannot fail the acceptance.",
		]
	)


def _living_and_historical(w) -> None:
	w.h2("What lives on the volunteer, and what stays on the application")

	w.lead(
		"An application is a statement made on a day. A volunteer is a standing relationship. Some of"
		" what an applicant writes down is true of the day and stays true of it forever; the rest is"
		" true of the person and stops being true the moment the person changes. Those are different"
		" kinds of fact, and the register keeps them in different places."
	)

	w.p(
		"The test that decides which side a field falls on is one question, and it is stated at the"
		" top of vmmsx/volunteer/services/capabilities.py: if this changed tomorrow, would the"
		" application have been wrong? A volunteer who learns to drive does not make last year's"
		" application false, so skills are current facts and belong on the volunteer. Why somebody"
		" applied is a fact about the applying, and editing it later would be rewriting history"
		" rather than recording a change, so motivation stays where it was said."
	)

	w.table(
		("Fact", "Where it lives", "Why"),
		[
			[
				"Skills, languages, availability",
				"On the volunteer, editable. Seeded from the application at acceptance.",
				"Current capabilities. They change while somebody volunteers, and a register that"
				" could only read them from a settled application could never record the change.",
			],
			[
				"Citizenship and residency",
				"On the volunteer, editable. Seeded from the application at acceptance.",
				"Facts about the person that core's spine does not hold. A naturalisation is a"
				" correction to make, not a reason to reopen an application.",
			],
			[
				"Serving Branch",
				"On the volunteer, as home_geo_node, its ACC-02 anchor.",
				"Where somebody works for the society. A Branch Transfer moves it, geo scoping"
				" filters on it, and an approval routes from it.",
			],
			[
				"Home Area",
				"On the person's Red Profile. Read, never copied.",
				"Where somebody lives is a fact about the person, not about their volunteering, and"
				" core already owns it. A second copy would be a second answer.",
			],
			[
				"Motivation, prior experience",
				"On the application. Shown as declared.",
				"Facts about the applying. There is deliberately no current-state field for either,"
				" because a field somebody could edit is a way of rewriting what was said.",
			],
			[
				"The identification captured at intake",
				"On the application, and on the applicant's Red Profile.",
				"Evidence of who somebody was on the day. The register holds neither an id_type nor"
				" an id_number, and a test asserts it.",
			],
		],
		(1.55, 1.95, 3.00),
	)

	w.h3("Seeding fills blanks; it never overwrites")

	w.p(
		"capabilities.seed() runs from application.accept(), once per acceptance, between the"
		" satellite being written and core's affiliation index being refreshed from it. It writes a"
		" field only where the volunteer's own is empty, and it returns what it wrote, so the"
		" acceptance DTO can say what happened rather than implying it."
	)
	w.p(
		"That rule matters for the second acceptance. Somebody who volunteered, exited and applied"
		" again years later is the same person, and their current skills are the ones the society has"
		" been maintaining, not the ones on a form they filled in last week. It is the same doctrine"
		" volunteer.ensure() already applies to placement. It also makes seeding idempotent in the"
		" strong sense: the second call observes the work is done and writes nothing, which is"
		" asserted by comparing the whole database row."
	)

	w.note(
		"Nothing is read live from the application, and that is the point rather than an omission."
		" The two are meant to diverge. Editing the volunteer's skills does not rewrite what the"
		" applicant declared, and correcting a settled application does not silently change what"
		" somebody is qualified for today. Both directions are asserted in"
		" test_coordinator_view.py."
	)


def _queryable_capabilities(w) -> None:
	w.h2("Finding volunteers by what they can do, inside geo scope")

	w.lead(
		"Because skills, languages and availability are Table MultiSelects of a society's own"
		" vocabularies rather than sentences, the register can answer the question a coordinator"
		" staffing something actually asks: who has this skill, speaks one of these languages, is"
		" free at these times, and is somewhere I am responsible for."
	)

	w.p(
		"capabilities.search() answers it. Any-of within a vocabulary and all-of across them, which"
		" is what somebody means by a first aider who speaks either of these and can do weekends. The"
		" whitelisted endpoint is api/volunteer.py::find_volunteers, and it returns rows built field"
		" by field that are deliberately thinner than the coordinator's view: a candidate list is a"
		" list of people somebody is deciding between, and handing back everybody's full"
		" certification history to answer who could do this would disclose far more than the question"
		" needs."
	)

	w.h3("The filter narrows the scope; it never widens it")

	w.p(
		"The final read is frappe.get_list, which runs core's permission query condition for VMMS"
		" Volunteer. frappe.get_all would skip it and is not used. So a capability filter can only"
		" ever narrow what the caller could already see, and naming a Geo Node narrows further still"
		" rather than being a way in. If a society has not configured its volunteer scope role, core"
		" fails closed and the search returns nothing, which is the correct answer rather than a bug."
	)
	w.p(
		"The child-table lookup that gathers candidates is filtered by both parenttype and"
		" parentfield. The same three selectors hang off VMMS Volunteer Application, so a query"
		" filtered only by the skill would return applicants as though they were volunteers. That"
		" lookup is a candidate list and never an answer: it is turned into a name-in filter on the"
		" scoped read, which is why reading it unscoped is not a way around the scope."
	)
	w.p(
		"The desk list view needs no code for any of this. A Table MultiSelect is filterable from the"
		" sidebar natively, and the same permission query condition applies underneath it. A test"
		" builds exactly the filter the desk builds and asserts an out-of-scope holder does not come"
		" back."
	)

	w.note(
		"This is the structured, queryable data the deployment matching service was waiting on, and"
		" it is deliberately not wired into matching yet. Matching decides things about a"
		" deployment's requirements that are not the register's to decide, and un-stubbing it is its"
		" own piece of work. What has changed is that the data it needs now exists and is queryable."
	)


def _the_volunteer_page(w) -> None:
	w.h2("The coordinator's view, and why none of it is stored")

	w.lead(
		"The register was correct and unusable. A coordinator opening a volunteer saw a Red Profile"
		" docname, a status and a geo node, and had to open a second tab to find out whose record they"
		" were looking at; the page heading read RP-00042, which was the least readable thing on the"
		" screen. The page now answers everything a coordinator decides from, on one surface, and"
		" answers all of it by reading it at the moment somebody looks."
	)

	w.table(
		("Block", "What it shows", "Where it comes from"),
		[
			[
				"Identity card",
				"Photo, name, email, phone, gender, date of birth and preferred language; then"
				" citizenship, residency, Home Area and Serving Branch, each under its own label"
				" because the last two are different questions.",
				"volunteer.profile_dto(), which reads Red Profile and capabilities.placement()",
			],
			[
				"Current capabilities",
				"Skills, languages and availability. Not an HTML block: these are the record's own"
				" editable fields, painted by Frappe's own grid, because they are current truth and"
				" a coordinator has to be able to change them.",
				"The volunteer record itself",
			],
			[
				"Deployability",
				"One indicator, green or red, with the blocking reasons beneath it when it is red.",
				"certification.deployability(), derived on read",
			],
			[
				"Certifications held",
				"Each certification with its completion and expiry dates and a derived status:"
				" current, lapsed, or lapsed and blocking deployment.",
				"certification.is_lapsed() and blocks_deployment(), per row",
			],
			[
				"Deployment history",
				"Every deployment this volunteer has been on, with dates, status, terms of reference"
				" and the date they left if they left early.",
				"participation.history_of(), which is the deployment module's roster",
			],
			[
				"Time served",
				"Total hours, the number of logs, a breakdown by kind, and the most recent logs.",
				"timelog.summary()",
			],
			[
				"Verification outcome",
				"The approval state, the application reference, and who decided what, when, at which stage.",
				"application.verification_dto()",
			],
			[
				"Declared at application",
				"Motivation, prior experience and the identification captured at intake, plus the"
				" skills, languages and availability as declared on the day, all labelled as a point"
				" in time declaration.",
				"The same call, from the same application",
			],
		],
		(1.35, 3.05, 2.10),
	)

	w.h3("One call, because a derived page needs one instant")

	w.p(
		"api/volunteer.py::get_dossier returns every block above in a single read, and that is not"
		" only about round trips. Every block is derived. Blocks derived at seven different instants"
		" can contradict each other, and a page showing a certification as current beside a"
		" deployability indicator computed a second later, after midnight passed, would be wrong in"
		" the way that is hardest to notice. The as-of date is resolved once and handed to every"
		" derivation, and a test asserts the deployability block reports the same instant the page"
		" does."
	)
	w.p(
		"The blocks are composed, never merged. Each is the DTO its own service already builds,"
		" nested under its own key, so nothing in the endpoint re-derives anything. In particular the"
		" volunteer's current skills and the skills they declared when applying sit in two different"
		" blocks and are never reconciled: one is what is true, the other is what was claimed, and a"
		" coordinator comparing them is the point of showing both."
	)

	w.p(
		"Seven of the blocks are HTML fields on VMMS Volunteer, which means they back no database"
		" column at all, and they are filled by"
		" vmms_volunteer/doctype/vmms_volunteer/vmms_volunteer.js. That file is"
		" the app's first client-side script and it is committed alongside the doctype rather than"
		" created as a desk Client Script record: a Client Script is a row in one site's database,"
		" invisible to review, absent from every other site and gone the day somebody deletes it."
		" Frappe loads a form script from the doctype's own folder, so the committed file is the"
		" mechanism, and a test asserts the desk actually serves it rather than merely that it exists."
	)
	w.p(
		"Nothing derived or borrowed is persisted onto the volunteer. There is no name column, no"
		" email column, no fetch_from, no approval state of its own, and no stored answer to whether"
		" somebody is deployable. Correcting somebody's phone number on their Red Profile corrects"
		" every volunteer page in the society on next open, because there is nothing anywhere to go"
		" and update. The tests assert the whole row is byte-identical before and after a page"
		" render, not merely that modified did not move."
	)
	w.p(
		"The register did gain columns for the first time, and the guard against that becoming a"
		" slide is that the tests name what was added rather than only what was not. The"
		" volunteer-owned attributes are written out as a list, and a thirteenth column fails the"
		" suite. Home Area in particular was the nearest miss: it is Red Profile's, it is read"
		" through identity.py, and there is a test that moves somebody's home on their profile and"
		" asserts the volunteer's whole row is unchanged."
	)

	w.h3("The readable surface was widened, deliberately, and each time by naming the field")

	w.p(
		"identity._READABLE is the explicit allow-list of what this app will read off core's identity"
		" spine, and it exists so that a new field appearing on Red Profile never starts flowing"
		" through a vmmsx DTO because nobody noticed it had arrived. It gained gender, date of birth,"
		" preferred language and the profile photo, and the reason is recorded in the source rather"
		" than in a commit message: the photo and the name confirm the right person, the language says"
		" how to contact them, and the two HR facts are what a volunteering office is asked for"
		" constantly."
	)
	w.p(
		"It gained a twelfth, home_geo_node, for the coordinator's view, and that one is worth"
		" recording because the alternative was tempting and wrong. Home Area is where somebody"
		" lives, and the obvious way to put it on the page was to copy it onto the volunteer at"
		" acceptance alongside the skills. That would have been a second answer to where somebody"
		" lives, wrong the first time one of the two was corrected. Reading it is the whole point of"
		" having an allow-list: surfacing a field of core's is cheap and safe, and storing one is"
		" neither."
	)
	w.p(
		"This is not a general opening, and two things keep it from becoming one. The first is that"
		" the tests assert the tuple as a whole, so a thirteenth field fails the suite and its author"
		" has to come and say why. The second is that the sensitive set core holds back for a gated"
		" extension — blood group, medical conditions, next of kin, disability — is named in"
		" identity._WITHHELD and refused out loud: asking for one raises rather than quietly returning"
		" a dict with the key missing, because a caller handed a missing key renders an empty row and"
		" nobody learns anything."
	)
	w.p(
		"Surfacing a field is also not the same decision as exporting one. What vmmsx hands to Frappe"
		" HR is hr._OUTBOUND, which did not widen and is asserted to remain a strict subset. See the"
		" HR seam below."
	)

	w.h3("The heading shows a person, without the record holding one")

	w.p(
		"title_field is still red_profile, and Frappe's toolbar reads that field's raw value, so the"
		" heading would read RP-00042. The client script overrides it with the full name the DTO just"
		" read, and keeps the opaque docname as the sub-title, where it stays visible and copyable for"
		" an audit trail, a report or a support conversation. Frappe's refresh_header() runs before"
		" the refresh trigger, so the override wins."
	)
	w.p(
		"A virtual title field holding the name was the other option and was rejected for two"
		" reasons. It would put an identity value on this doctype's meta, which is the thing the"
		" module refuses; and Frappe's list view adds title_field to its query, so a computed one"
		" risks selecting a column that does not exist. The list view already shows names without"
		" help, because Red Profile sets show_title_field_in_link and the desk resolves link titles"
		" for list columns on its own."
	)

	w.h3("Declared at application is a snapshot, and is labelled as one")

	w.p(
		"What an applicant said about themselves on the day they applied is not what the volunteer can"
		" do today, and the page must not let a reader mistake the second for the first. The block is"
		" set apart visually, it names the date it was declared on, and it says in as many words that"
		" this is not what the volunteer is currently able to do."
	)
	w.p(
		"The declared skills, languages and availability now appear on this page twice: once above as"
		" the volunteer's current capabilities, and once here labelled as declared. That is not"
		" duplication, it is the comparison. The difference between the two is what somebody has"
		" learned since they applied, and it is only visible side by side. The labels in the declared"
		" block say declared, in the field label itself rather than only in a footnote, so the two"
		" cannot be read as one list."
	)
	w.note(
		"The three are never merged, reconciled or averaged: one is a claim made once, the other is"
		" what the society maintains, and VMMS Certification is a third thing again — what the"
		" society has verified, and the only one of the three deployability reads."
	)


def _two_providers(w) -> None:
	w.h2("Two affiliation providers, and removal that stays isolated")

	w.lead(
		"vmmsx now registers two providers with core: vmmsx.member.affiliations.provide and"
		" vmmsx.volunteer.affiliations.provide. A person may be both a member and a volunteer, and"
		" this is the first point in the build where core's rebuild has more than one satellite"
		" speaking about the same profile."
	)
	w.p(
		"Core's removal rule is one sentence: a row is deleted only when a registered provider owns"
		" its reference_doctype and did not claim it. Each provider declares only what it owns"
		" — Member declares VMMS Member, Volunteer declares VMMS Volunteer — and that declaration is"
		" what keeps the two independent. Deleting somebody's volunteer record makes the volunteer"
		" provider stop claiming a volunteer row, and leaves the member row untouched because no"
		" provider that owns VMMS Member declined to claim it. The isolation is a property of the"
		" declarations, not of anybody remembering to be careful."
	)
	w.p(
		"Deleting a satellite is handled in VMMSVolunteer.on_trash, which calls core's"
		" rebuild_affiliations() rather than removing a row directly, because core has exactly one"
		" removal path. The timing is delicate and the controller's docstring explains it: the"
		" affiliation row holds a Dynamic Link to the volunteer, so it has to go during on_trash,"
		" before Frappe's link check runs, and a request-scoped mark tells the provider to stop"
		" speaking for a volunteer that is on its way out. This is the same handshake"
		" VMMSMember.on_trash uses; the two do not interfere because each marks only its own."
	)


def _derived_lapse(w) -> None:
	w.h2("Lapse is derived, and nothing anywhere stores it")

	w.lead(
		"Whether a certification has lapsed is a comparison between its expiry date and the date you"
		" are asking about. certification.is_lapsed() performs that comparison at the point it"
		" matters and stores nothing."
	)
	w.code("lapsed  ==  expiry_date < the date you are asking about")
	w.p(
		"There is no lapsed field on VMMS Certification, no status column with 'Lapsed' among its"
		" options, and no scheduled job that flips anything: vmmsx has scheduler_events, but not one"
		" of them reaches into this module."
	)
	w.p(
		"That is not a stylistic preference. A stored flag has three failure modes this design does"
		" not have. It is wrong between midnight and whenever the job runs. It cannot answer a"
		" historical question at all, and 'was this volunteer certified on the day of the"
		" deployment' is exactly the question an inquiry asks. And it is silently wrong forever if"
		" the job stops, which is the worst of the three because nothing announces it."
	)

	w.h3("What a lapse costs")

	w.p(
		"certification.deployability() derives the answer on every call from two things: the"
		" volunteer's own status, and the certifications they hold. A volunteer whose certification"
		" has lapsed is not deployable, and stays Active while that is true. Lapsing is not a"
		" disciplinary event and does not end somebody's volunteering; it makes them ineligible for"
		" the work that needed the certification until they renew it. Conflating the two would mean"
		" a first-aid refresher falling due quietly removed somebody from the register."
	)
	w.p(
		"Which types count is configuration: blocks_deployment_when_lapsed on VMMS Certification"
		" Type, on by default. A society may hold a certification as a record rather than a"
		" requirement, and then its lapsing blocks nothing. Note where that field lives — on the"
		" type, not on the held certification. It is a policy switch that is the same for every"
		" holder, which is precisely what makes it not a stored lapse."
	)
	w.note(
		"If lapse notifications are ever wanted, they are a future scheduled sweep that reads"
		" is_lapsed() and sends messages. Even then the deployment decision must keep reading"
		" deployability() rather than anything the sweep wrote down."
	)

	w.h3("Who reads it")

	w.p(
		"Three callers, and all three derive rather than look up, which is what stops a volunteer"
		" being told one thing by one screen and excluded by another."
	)
	w.table(
		("Caller", "What it asks", "What derives the answer"),
		[
			[
				"deployment/services/matching.py",
				"is this person a candidate, on the date this work starts",
				"deployability() plus _current_certifications(), both at as_of",
			],
			[
				"api/volunteer.py::get_deployability",
				"may this volunteer be deployed, on a date a coordinator names",
				"deployability(volunteer, as_of)",
			],
			[
				"api/volunteer.py::my_certifications",
				"is my own training still current, today",
				"deployability(volunteer) and is_lapsed() per row",
			],
		],
		(2.05, 2.35, 2.15),
	)

	w.h3("Why the volunteer's own surface is an endpoint and not a list view")

	w.p(
		"A volunteer's self-service workspace could point at an ordinary VMMS Certification list"
		" view: the doctype is not geo-registered, the User Permission created with their role"
		" narrows it to their own rows, and registration/services/permissions.py grants the read."
		" That list exists and is on the workspace's card. It is not the shortcut, and the reason is"
		" the whole of this section: a list view can only display stored columns, and it would show"
		" a completion date and an expiry date with no indication of whether anything had lapsed."
	)
	w.p(
		"api/volunteer.py::my_certifications() computes that instead. It takes no arguments at all,"
		" the same shape as my_volunteer and my_memberships, so a caller cannot name anybody; the"
		" lapse on each row and the deployability above them are worked out in the response. A"
		" coordinator who needs to ask about a different date has get_certifications(name, as_of)"
		" and get_deployability(name, as_of), which are permission-checked because they name"
		" somebody."
	)


def _learning_seam(w) -> None:
	w.h2("The learning seam")

	w.lead(
		"vmmsx/volunteer/services/learning.py is the only file in this app that knows a learning"
		" system exists. Everything it depends on is gathered in one labelled block at the top of"
		" it, so the surface can be read at a glance and swapped in one place."
	)
	w.p(
		"What crosses the boundary, and in which direction: the seam reads one fact out of the"
		" learning system — this person finished that course — and writes one record of ours, a"
		" VMMS Certification. Nothing goes the other way. There is no enrollment, no lesson, no"
		" quiz, no batch and no LMS certificate anywhere in the vmmsx domain."
	)
	w.p(
		"It is wired through doc_events in hooks.py, which is what that hook is for: reaching into"
		" another app's document without that app knowing we exist. The learning system is not"
		" modified and does not import vmmsx. That single registration line is the only other place"
		" in the app where an LMS doctype is written down, and"
		" volunteer/tests/test_delegation.py asserts it is exactly one."
	)

	w.h3("The mapping is configuration")

	w.p(
		"Which course produces which certification is a VMMS Course Mapping row an administrator"
		" wrote. Pointing an existing row at a different VMMS Certification Type changes what every"
		" future completion of that course awards, with no code change anywhere, and the new"
		" certification carries the new type's validity period because the type is what expiry is"
		" computed from. A course nobody mapped awards nothing, which is the ordinary case: most"
		" courses a society runs are not certifications."
	)

	w.h3("Identity crosses through Red Profile, never around it")

	w.p(
		"The learning system knows a User. This app knows a volunteer. The path between them is"
		" User to Red Profile to VMMS Volunteer, because Red Profile is core's identity spine and"
		" resolving people any other way would be a second answer to who somebody is. A learner with"
		" no Red Profile, or a profile with no volunteer record, is not an error: it is somebody"
		" doing a course who is not a volunteer, and the seam has nothing to say about them."
	)
	w.p(
		"learning.sync_volunteer() exists for the cases the hook cannot cover — a course finished"
		" before the society wrote the mapping, or before the person became a volunteer. It is"
		" idempotent, like everything else here, and on a site with no learning system it reports"
		" that it read nothing rather than raising."
	)

	w.h3("How a completion is detected")

	w.p(
		"The learning system records progress as a percentage of a course's lessons and does not"
		" emit a completion event of its own, so the seam watches the fact rather than an"
		" announcement. on_enrollment_update() fires from doc_events on every save of an LMS"
		" Enrollment and asks one question: has progress reached the end. Finished is finished; a"
		" course 99 per cent done has not been completed."
	)
	w.p(
		"Because it fires on every save, including the many saves after a course was already"
		" finished, it has to be idempotent and is: the award goes through"
		" certification.record(), which updates the one row a volunteer holds of that type rather"
		" than adding a second."
	)
	w.p(
		"The completion date is the enrollment's own modified date, which is the moment the save"
		" that completed it is happening. That is stated plainly here because it is an"
		" approximation — the learning system does not record when progress reached the end — and a"
		" society reconciling a certificate against a training register should know which date it is"
		" looking at. Everything downstream, the expiry included, is computed from it by our"
		" configuration and not by anything the learning system said."
	)

	w.h3("A society with no learning system")

	w.p(
		"vmmsx declares required_apps = ['onerc_core'] and not the LMS. A national society running"
		" volunteering without one is ordinary rather than degraded, and the whole of the difference"
		" is that the automation is dormant."
	)
	w.bullets(
		[
			"Certifications are recorded, renewed and read exactly as they are here. A coordinator"
			" typing one in from a paper register is a first-class way to hold one, not a fallback.",
			"The doc_events hook names a doctype that does not exist on such a site, so it simply"
			" never fires. Nothing is raised and nothing has to be configured off.",
			"learning.is_available() answers from frappe.get_installed_apps() rather than by trying"
			" an import and catching the failure — an app can sit in the bench without being"
			" installed on this site, which is the case that actually bites, and a question answered"
			" by an exception cannot be asked at configuration time. This is the same guard shape"
			" member/services/payment.py uses for the payments app.",
			"sync_volunteer() asks that question first and returns its empty summary, so the"
			" catch-up path reports that it read nothing instead of querying a table that is not"
			" there.",
			"VMMS Course Mapping is still writable and readable, because it is a vmmsx record about"
			" an identifier in another system. That is exactly why external_course is Data rather"
			" than a Link: a Link would make the mapping unsaveable, and the doctype uninstallable,"
			" on the very site this paragraph is about.",
		]
	)
	w.p(
		"volunteer/tests/test_lms_absent.py asserts all of it against a mocked absence, patching"
		" frappe.get_installed_apps to the real list minus the learning app — which is exactly the"
		" surface the guard reads."
	)


def _log_types_and_ownership(w) -> None:
	w.h2("Time log types, and the ownership rule the second kind carries")

	w.lead(
		"log_type says which structural kind a log is, and it is the only field on the record that"
		" changes what the server will accept."
	)
	w.bullets(
		[
			"general — volunteering that stands on its own: training, an open day, office support."
			" It may never name a deployment. This is the kind phase 2's stipend work will be built"
			" on.",
			"deployment — time served on a specific deployment. It names one, and the volunteer must"
			" be on that deployment's roster. This kind was an explicit stub in the volunteer spine"
			" and the Deployment section describes the rule that finished it.",
		]
	)
	w.p(
		"The set of kinds is code rather than a society's vocabulary, because each value names a"
		" different validation rule and a society adding a third value would produce a log that"
		" nothing knows how to check. That is the same split the approval engine makes between"
		" states, which are code, and stages, which are configuration. What a society genuinely"
		" wants to vary is how it classifies volunteering for its own reporting, and that is VMMS"
		" Time Log Category, on which no code branches."
	)
	w.p(
		"Nothing branches on log_type with a scattered comparison either. volunteer/services/"
		"timelog.py holds one dispatch table keyed by the value, exactly as"
		" member/services/approval.py keys its two tables by approval_mode. Adding a kind is adding"
		" an entry there and writing its rule; it is never adding an if to a caller, and a test"
		" walks the AST of every file outside that module and fails if one compares log_type to"
		" anything."
	)

	w.h3("The stub this module shipped, and what replaced it")

	w.p(
		"For one stage the deployment kind was refused outright. There was no Deployment doctype,"
		" so the link had no target and the rule that matters had nothing to read, and the two"
		" alternatives were both worse than a refusal: wiring the link to a stand-in doctype would"
		" have left a link nobody could validate and a migration to unpick later, and letting the"
		" log save unchecked would have shipped exactly the hole the ownership rule exists to"
		" close, silently."
	)
	w.p(
		"The Deployment module removed the stub. VMMS Time Log.deployment is now a Link to VMMS"
		" Deployment, and timelog._deployment() asks deployment/services/participation.py whether"
		" the volunteer filing the log is on that deployment's roster. The refusal that is left is"
		" the ownership rule's, and the module's own tests assert that no message here still names"
		" the stage that has since happened."
	)

	w.h3("Ownership is not geo scoping")

	w.p(
		"A deployment log is constrained to deployments the volunteer actually participated in."
		" That is ownership scoping, the actor's own records, and it is not geo scoping. Being"
		" correctly placed in the right county does not make somebody a participant, and no geo"
		" filter can express the difference. The picker filters for convenience; the server rejects"
		" a log whose deployment does not list this volunteer as a participant, so fabricating"
		" participation is impossible rather than merely hidden by a filtered link field. The rule"
		" is stated as participation.OWNERSHIP_RULE and described in full in the Deployment"
		" section."
	)
	w.p(
		"The two refusals a time log can carry remain deliberately different messages for"
		" deliberately different reasons. A general log naming a deployment is wrong permanently,"
		" because general volunteering is by definition not deployment time, and adding the"
		" volunteer to a roster does not make it right. A deployment log naming a deployment they"
		" were not on is wrong until somebody is added to that roster, or until the log is filed"
		" against the deployment they were actually on."
	)


def _hr_seam(w) -> None:
	w.h2("The HR seam")

	w.lead(
		"VMMS Volunteer.employee is a Link to Frappe HR's Employee. vmmsx points at HR; HR does not"
		" point back, does not import this app, and is not modified by it. Everything about the seam"
		" lives on our side of it, which is what makes it removable: uninstall HR and a nullable"
		" link goes unused."
	)

	w.h3("Identity never moves")

	w.p(
		"Red Profile is the spine and stays the spine. Nothing in this app reads employee_name,"
		" personal_email, company or any other field on an Employee as the answer to who somebody"
		" is. The flow is strictly outward: identity is given to HR when a record is created, and"
		" never taken back. A fetch_from pointing at Employee would be the whole principle undone in"
		" one JSON attribute, and there is none — a test walks every doctype JSON in the app to"
		" confirm it."
	)
	w.p(
		"No employment model crosses either. Payroll, salary structures, attendance, leave and"
		" timesheets are HR's. A volunteer is not an employee; the link exists because a society's"
		" HR office may need a record for a person who holds a badge and appears in an emergency"
		" roster, not because volunteering is employment. VMMS Time Log is this app's own record of"
		" volunteered hours and has nothing to do with Timesheet."
	)

	w.h3("Provisioning is off unless a society switches it on")

	w.p(
		"Two settings govern it, both Custom Fields vmmsx owns:"
		" vmms_volunteer_provision_employee and vmms_volunteer_employee_company. With the switch off"
		" — the shipped state — accepting a volunteer creates no Employee at all. With it on,"
		" hr.provision() adopts an Employee HR already holds for that person before it considers"
		" creating one, because a duplicate Employee is a worse outcome than no Employee. The"
		" adoption matches on the Red Profile's user, never on a name: two people share a name, and"
		" matching identity by string is how a volunteer ends up linked to somebody else's record."
	)
	w.p(
		"And vmmsx will not invent identity to satisfy another app's schema. HR requires a gender and"
		" a date of birth on every Employee. Core's Red Profile carries both, and the volunteer page"
		" now displays both, but this seam still hands over neither. What it hands over is"
		" hr._OUTBOUND: first name, middle name, last name, email, phone and the login. Nothing else"
		" crosses, so vmmsx has nothing to give HR for those two fields, and it does not guess,"
		" default or fabricate either value."
	)
	w.p(
		"That list is deliberately narrower than identity._READABLE, and the difference between the"
		" two is the point. Showing somebody's date of birth to a coordinator who may already see"
		" their record is one decision. Writing it into an employment register, where a payroll run"
		" and a leave policy will read it, is a different one. They were the same decision only for"
		" as long as the two lists were the same list. When the readable surface was widened for the"
		" volunteer page, this one was not, and a test asserts _OUTBOUND stays a strict subset of"
		" _READABLE so that widening a card can never quietly widen what reaches payroll."
	)
	w.p(
		"Where HR refuses a record for want of data this app does not pass on, the refusal is logged"
		" with HR's own complaint and the volunteer is entirely unaffected. Refusing to provision is"
		" the correct outcome, not a bug to be worked around by filling in a placeholder date of"
		" birth. Widening _OUTBOUND so that provisioning can succeed is a decision about what a"
		" volunteer record may push into an employment register, and about consent; it is a later"
		" enrichment rather than an oversight."
	)
	w.p(
		"hr.provision() never raises into its caller either. A volunteer who could not be"
		" provisioned is still a volunteer, and an HR misconfiguration must not be able to fail an"
		" approval."
	)


def _scoping(w) -> None:
	w.h2("Who may see a volunteer")

	w.p(
		"VMMS Volunteer is registered with core through onerc_scopeable_doctypes, on its ACC-02"
		" anchor home_geo_node, naming its role with role_from_setting rather than a literal. Which"
		" of a society's roles may see the volunteer register is that society's decision, and a"
		" literal in hooks.py would hardcode exactly what the access model forbids. Core reads"
		" vmms_volunteer_scope_role at enforcement time and generates all three enforcement layers"
		" from the one declaration."
	)
	w.p(
		"The field ships empty, which means no role resolves and core fails closed: until a society"
		" chooses the role, no non-administrator can read a volunteer record. That is the intended"
		" pre-portal state. The register holds personal data about people the society has no"
		" employment relationship with, and guessing a default would be this app inventing an access"
		" policy. Core logs every unresolved read, so the closed state is visible rather than looking"
		" like nobody having been granted anything yet, and the framework exemption means an"
		" administrator can always get in to set it."
	)
	w.p(
		"Scoping filters on the same field the anchor rule makes mandatory, and that pairing"
		" matters: core's list filter is an IN, which excludes NULL, so a scopeable doctype with a"
		" nullable anchor would have records that exist and that nobody can see. VMMSVolunteer"
		" refuses to save without one."
	)
	w.p(
		"VMMS Volunteer Application is deliberately not registered. Its access is the approval"
		" engine's person-gate — who this specific document routed to, right now — and the engine"
		" already calls core's guard on the governed doctype before every decision. Scoping the"
		" application as well would put two different answers to 'may you touch this' in front of"
		" one document."
	)


def _configuration(w) -> None:
	w.h2("What a society configures")

	w.p(
		"Four settings fields, all Custom Fields vmmsx installs on core's National Society Settings"
		" through its own patches. Core's doctype is not edited: a product pushing its fields into"
		" the shared foundation's source is how the foundation stops being shared."
	)

	w.table(
		("Setting", "What it decides", "Shipped as"),
		[
			[
				"vmms_volunteer_anchor_level",
				"ACC-03. The geo level a volunteer may be anchored at. Read by"
				" society.assert_anchor_level() on every save.",
				"Empty, meaning any level",
			],
			[
				"vmms_volunteer_scope_role",
				"Which role may see volunteer records, combined with that role's Geo Assignments.",
				"Empty, meaning closed",
			],
			[
				"vmms_volunteer_provision_employee",
				"Whether accepting a volunteer links or creates an HR Employee record.",
				"Off",
			],
			[
				"vmms_volunteer_employee_company",
				"Which company a provisioned Employee is created under. HR cannot make one without"
				" it, and vmmsx will not guess it.",
				"Empty",
			],
		],
		(2.05, 3.25, 1.20),
	)

	w.p(
		"Beyond settings, everything a society could do differently is a record it writes. Which"
		" certifications exist and how long each lasts is VMMS Certification Type. Which course"
		" awards which certification is VMMS Course Mapping. How volunteered time is classified is"
		" VMMS Time Log Category. Which stages an application passes through, who they need and how"
		" many must act is a VMMS Approval Workflow. No country, currency, role name, geo level"
		" name, certification name or course name appears in any executable line of this module."
	)
	w.p(
		"The patch seeds three time-log categories and the volunteer Affiliation Type, and stops"
		" there. It deliberately seeds no certification type and no course mapping: those name real"
		" qualifications and real courses, and this app has no business inventing either."
	)


def _not_here_yet(w) -> None:
	w.h2("What the register deliberately does not hold")

	w.p(
		"The register is thin on purpose, and the things it does not carry are listed here rather"
		" than left to be discovered. None of the fields below exists on any doctype in this"
		" module; a society looking for one is not looking in the wrong place, it is looking for"
		" something that has not been built."
	)

	w.table(
		("Not here", "Why, and what would have to be decided first"),
		[
			[
				"Skill matching on a deployment",
				"The structured skills exist now, on the volunteer, and capabilities.search() finds"
				" people by them inside geo scope. What has not been done is wiring that into"
				" deployment matching, which still matches on certifications and reports skills as a"
				" pending criterion. Matching decides things about a deployment's requirements that"
				" the register is not entitled to decide, so un-stubbing it is its own piece of work"
				" rather than a side effect of the data arriving.",
			],
			[
				"Volunteer type",
				"status is a plain Select of four values that are states of a relationship, not"
				" categories a society invents. A volunteer *type* is society-variable and would"
				" arrive as a configured vocabulary in the shape VMMS Skill and VMMS Availability"
				" Slot already use, never as a Select in a JSON file. Availability itself is no"
				" longer on this list: it is a structured vocabulary on the volunteer, and it is"
				" filterable.",
			],
			[
				"Emergency contacts and next of kin",
				"Person-facts, so they belong on onerc_core's Red Profile rather than here, next to"
				" the sensitive set core is holding back for a gated extension. Duplicating them onto"
				" the volunteer would be the identity-duplication this module is built to avoid.",
			],
			[
				"Department",
				"Organisational placement is already answered by the Serving Branch, and the"
				" volunteer DTO is asserted in test_hr_seam.py to carry no department, designation,"
				" salary or company. A second placement axis would give two answers to where somebody"
				" belongs.",
			],
			[
				"A stored deployability flag, or a lapse column",
				"Not an omission and never arriving. Both are derived on read, and the coordinator's"
				" view is built on that: a lapsed mandatory certification flips the indicator with"
				" nothing written anywhere, which is asserted by comparing the volunteer's and the"
				" certification's whole database rows before and after.",
			],
			[
				"Stipends and any other money",
				"Phase 2, and through onerc_payments exactly as membership fees are. No money model"
				" exists in this module in any form.",
			],
		],
		(1.55, 4.95),
	)


def _what_is_tested(w) -> None:
	w.h2("What is tested")

	w.p(
		"Nothing in this module's tests is mocked. Geo comes from core's geo fixtures, identity from"
		" core's Red Profile, authority from real Geo Assignment rows, approval from a real VMMS"
		" Approval Workflow driving the real engine, and the learning seam from a real LMS Course"
		" and a real LMS Enrollment whose save fires the real hook. Two differently-shaped"
		" hierarchies are built, so that no assertion about behaviour can quietly depend on a level"
		" being called a county."
	)

	w.table(
		("Suite", "What it establishes"),
		[
			[
				"test_engine.py",
				"An application routes to the person core resolved, in both hierarchies. A holder of"
				" the same role elsewhere is refused, and the refusal changes no state, no stage, no"
				" audit row, no queue and creates no volunteer. That refused user can still read the"
				" document, which is what proves the refusal was the person-gate and not a"
				" permission. Approval produces an Active volunteer placed where they applied;"
				" rejection produces none. ACC-02 refuses an unplaced application at creation, and"
				" ACC-03 through the workflow's permitted levels refuses one anchored too high.",
			],
			[
				"test_delegation.py",
				"Walks the AST and text of every file under volunteer/. No resolve_approvers, no"
				" get_user_geo_scope, no geo or authority table named in a query, and geo reached"
				" only through core's adapter. Only learning.py names an LMS doctype and only hr.py"
				" names Employee; no file anywhere names HR's employment model. No vmmsx doctype"
				" Links to an LMS doctype or fetches identity from an Employee. The scanners are"
				" themselves tested against a planted leak, because a scanner that finds nothing"
				" because it is broken proves nothing.",
			],
			[
				"test_affiliations.py",
				"A person who is both a member and a volunteer holds both rows, each pointing at its"
				" own satellite. Wiping the index and rebuilding reconstructs both and loses"
				" nothing. Trashing the volunteer removes only the volunteer row and leaves the"
				" member row byte-identical, not merely present; trashing the member is the mirror"
				" image. An index row edited behind core's back is corrected by a rebuild rather"
				" than believed.",
			],
			[
				"test_certification.py",
				"Expiry is completion plus the type's configured period, and changing that period"
				" moves it. The same untouched record reads as valid on one date and lapsed on the"
				" next, with modified and the Version count both proved unchanged, so no write"
				" happened. No field in the app is a lapse flag under any spelling, and no scheduled"
				" job touches this module. A lapsed certification makes an Active volunteer"
				" non-deployable while leaving them Active and affiliated, and a type configured not"
				" to block does not block. my_certifications() takes no arguments, answers from the"
				" session, never returns a second volunteer's training, derives the lapse per row"
				" and the deployability above them in the response, and writes nothing doing it.",
			],
			[
				"test_learning.py",
				"Completing a mapped course through the real LMS awards a certification of the"
				" mapped type with the right expiry, via the hook rather than a call the test made."
				" Repointing the mapping changes what the same course awards. An unmapped course, an"
				" unfinished one, an inactive mapping, a learner with no Red Profile and a profile"
				" with no volunteer all award nothing. Completing twice awards once.",
			],
			[
				"test_lms_absent.py",
				"With the learning app mocked absent, recording, renewing, the derived lapse and the"
				" deployability answer all work unchanged, and a course mapping is still writable"
				" and readable. sync_volunteer() reports reading nothing rather than raising, and"
				" awards nothing even where a mapping and a completion exist. The mock is itself"
				" tested, and detection is shown not to depend on an import failing: the LMS is"
				" still importable under it and the guard must still say unavailable. The learning"
				" app is asserted absent from required_apps, which is what makes the whole state"
				" reachable.",
			],
			[
				"test_time_log.py",
				"A general log saves with its anchor and no deployment link; one naming a deployment"
				" is refused, with its own message rather than the ownership rule's. A log with no"
				" anchor is refused for both kinds. The deployment kind is structurally known in the"
				" Select and the dispatch table, its field is a Link to VMMS Deployment, a log"
				" naming nothing or naming an unverifiable deployment is refused with nothing saved,"
				" and the stage-4 stub is asserted absent from the module. The ownership rule itself"
				" is exercised in deployment/tests/test_ownership.py, where the rosters are.",
			],
			[
				"test_hr_seam.py",
				"The link points from the volunteer to the Employee and HR holds no link back. With"
				" the switch off nothing is created, through the service and through acceptance. An"
				" existing HR record is adopted rather than duplicated, matched on the login. When"
				" the two disagree, the volunteer's name is Red Profile's answer, not HR's. Gender"
				" and date of birth are asserted absent from hr._OUTBOUND and absent from what the"
				" seam reads even for a profile that has both set on the spine — while the same test"
				" asserts the page still receives them, so it cannot start passing because the"
				" display widening was reverted. Where HR refuses for want of them, the refusal is"
				" logged and the volunteer is unaffected.",
			],
			[
				"test_volunteer_page.py",
				"identity._READABLE is asserted as a whole tuple, so widening it again fails rather"
				" than passing quietly, and the gated-sensitive set is asserted refused out loud"
				" rather than merely absent. No identity field, no column and no fetch_from exists"
				" for anything the page displays, all seven display blocks are asserted HTML backing"
				" no column, and the volunteer's whole database row is byte-identical before and"
				" after a render. The heading resolves to the profile's full name rather than either"
				" docname, the desk is asserted to actually serve the in-repo form script, and"
				" title_field is asserted still to be the link. Correcting a decision on the"
				" application changes what the page reports and leaves the volunteer row untouched."
				" Motivation, prior experience and the intake identification are asserted to have no"
				" field on the register at all.",
			],
			[
				"test_coordinator_view.py",
				"Approving an application copies skills, languages, availability, citizenship and"
				" residency onto the volunteer, and seeding twice writes nothing the second time,"
				" proved against the whole row. A second application does not overwrite what the"
				" society has been maintaining. Editing the volunteer's skills leaves the"
				" application's declaration untouched and correcting the application leaves the"
				" volunteer's skills untouched, which is the divergence the split exists to produce."
				" The living three are asserted editable and the historical three asserted to have"
				" no field. No identity column was added, only the volunteer-owned attributes"
				" persist, and Home Area is proved read from Red Profile by moving somebody's home"
				" and asserting the volunteer row did not change. Every section of the coordinator's"
				" view resolves, the whole view reports one as-of instant, and rendering it writes"
				" nothing. A lapsed mandatory certification flips deployability with both database"
				" rows byte-identical, a non-blocking one does not, and the same certification reads"
				" differently on two dates. A capability search returns the in-scope holder and not"
				" the out-of-scope one — who is separately proved to hold the skill, so the test"
				" fails for the scope rather than for the data — and the desk's own child-table"
				" filter is held to the same bar.",
			],
			[
				"test_application_fields.py",
				"Adding a VMMS Skill, VMMS Motivation or VMMS Availability Slot row makes it"
				" selectable with no code change, and the seeded starting set is asserted installed."
				" A skill on an application is queryable through its own selector child table — the"
				" property a coordinator's filter depends on. An application without both an ID Type"
				" and an ID Number is refused at submission with a MandatoryError; with them, it"
				" submits and the identification lands on the applicant's Red Profile idempotently"
				" across a resubmit, while a bare Red Profile is asserted to still allow none."
				" Citizenship defaults from National Society Settings.country and is freely"
				" changeable; Local without a Home Area and Abroad without both a country and an"
				" address are both refused at submission; a citizen of elsewhere living locally and a"
				" citizen of here living abroad both save. Serving Branch defaults from Home Area for"
				" Local and is overridable; Abroad has nothing to default from and must be given"
				" explicitly, which the ordinary ACC-02 check already enforces. An AST scan of the"
				" stage's own files, docstrings stripped, asserts no country, geo-level or vocabulary"
				" key reaches executable logic, and the scan is proven against a planted leak.",
			],
			[
				"test_scoping.py",
				"With a role configured a holder reaches their own area and not another's, through"
				" all three enforcement layers. Pointing the setting at a different role changes who"
				" sees what with no code diff. With the setting empty every non-administrator is"
				" denied, the layer returns deny-all rather than no filter, the denial is logged,"
				" and an administrator can still get in to configure it. The membership scope role"
				" does not stand in for the volunteer one.",
			],
		],
		(1.55, 4.95),
	)

	w.p("The suite for this module is run with the rest of the app:")
	w.code("bench --site vmms.localhost run-tests --app vmmsx")
	w.note(
		"The HR adoption and creation paths require a Company, and skip with a stated reason on a"
		" site where ERPNext or HR setup has not been completed. That is a property of the site"
		" rather than of the seam, and it is skipped loudly rather than worked around: fabricating"
		" an Employee past HR's own validation is precisely what this module refuses to do in"
		" production."
	)
