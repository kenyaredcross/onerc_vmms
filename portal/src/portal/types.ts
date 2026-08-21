/**
 * The response shapes this frontend renders.
 *
 * Written from the Python DTO builders, not guessed: each interface names the
 * function that produces it, so a change on the server has one place to be
 * reflected here. Fields the UI does not use are deliberately omitted rather
 * than typed and ignored, which keeps this file a statement of what the screens
 * actually depend on.
 */

/** `volunteer/services/volunteer.py::profile_dto` + `application.py::verification_dto`. */
export interface VolunteerProfile {
	volunteer: string;
	red_profile: string;
	full_name: string | null;
	email: string | null;
	phone: string | null;
	gender: string | null;
	date_of_birth: string | null;
	preferred_language: string | null;
	profile_photo: string | null;
	status: string;
	joined_on: string | null;
	exited_on: string | null;
	geo_node: string | null;
	geo_path: string | null;
	home_geo_node: string | null;
	home_geo_path: string | null;
	deployability?: Deployability;
	verification?: Record<string, unknown>;
}

export interface Deployability {
	as_of: string;
	deployable: boolean;
	reasons: string[];
}

/** `api/volunteer.py::_certification_rows`. */
export interface CertificationRow {
	name: string;
	certification_type: string;
	certification_type_name: string;
	completion_date: string | null;
	expiry_date: string | null;
	reference_number: string | null;
	lapsed: boolean;
	blocks_deployment: boolean;
}

/**
 * One filed time log, as `api/volunteer.py::_my_log_row` builds it.
 *
 * `log_type` is the structural kind and is display-only here: no screen compares
 * it, the same rule stage labels and category keys follow. The breakdown on the
 * hours screen is built by grouping whatever values come back.
 */
export interface TimeLogRow {
	name: string;
	log_type: string;
	log_category: string | null;
	category_label: string | null;
	deployment: string | null;
	geo_node: string | null;
	geo_path: string | null;
	activity_date: string;
	hours: number;
	notes: string | null;
}

/** `volunteer/services/timelog.py::summary`, enriched by `api/volunteer.py::my_time_logs`. */
export interface MyTimeLogs {
	volunteer: string;
	total_hours: number;
	log_count: number;
	/** Keyed by whatever `log_type` values the rows carry. Never indexed by a literal. */
	hours_by_type: Record<string, number>;
	recent: TimeLogRow[];
}

/** `api/volunteer.py::my_certifications`. */
export interface MyCertifications {
	volunteer: string;
	as_of: string;
	status: string;
	deployable: boolean;
	blocking_reasons: string[];
	certifications: CertificationRow[];
}

/** `member/services/membership.py::status` plus the two flags `my_memberships` adds. */
export interface MembershipRow {
	name: string;
	member: string;
	member_name: string | null;
	membership_type: string;
	membership_type_name: string | null;
	membership_status: string;
	/**
	 * Whether this membership is in force now. The server's own comparison
	 * against its own vocabulary — never re-derived here from
	 * `membership_status`, which this app does not own the values of.
	 */
	is_active: boolean;
	approval_state: string | null;
	approval_settled: boolean;
	payment_settled: boolean;
	requires_approver: boolean;
	is_lifetime: boolean;
	/**
	 * `member/services/payment.py::fee` — an amount *and* its currency, never a
	 * bare number. This was typed as `number | null` and rendered straight into
	 * `formatMoney`, which put `[object Object]` on the membership screen. The
	 * currency is not decoration: a society's fee is in the currency it
	 * configured, and this app never assumes one.
	 */
	fee: { amount: number; currency: string | null } | null;
	geo_node: string | null;
	geo_path: string | null;
	valid_from: string | null;
	valid_to: string | null;
	paid_on: string | null;
	payment_receipt: string | null;
	payment_transaction: string | null;
	membership_source: string | null;
	certificate_available: boolean;
	renewable: boolean;
}

/** `approvals/services/engine.py::status`, as returned by `my_queue`. */
export interface ApprovalStatus {
	doctype: string;
	name: string;
	state: string;
	is_open: boolean;
	is_terminal: boolean;
	geo_node: string | null;
	geo_path: string | null;
	stage: {
		name: string;
		sequence: number;
		/** Display only. Never compared: stages are configuration. */
		label: string;
		required_role: string;
		completion_rule: string;
		can_reject: boolean;
		is_optional: boolean;
		entered_on: string | null;
		due_on: string | null;
		is_breached: boolean;
		days_overdue: number;
		is_blocked: boolean;
	} | null;
	can_act: boolean;
	approver_count: number;
	approvers: string[];
	escalated_to: string[];
	allow_withdrawal: boolean;
	can_withdraw: boolean;
	decisions: Array<{
		decision?: string;
		decided_by?: string;
		decided_on?: string;
		reason?: string;
		stage_label?: string;
	}>;
}

/** `api/registration.py::_profile_dto`. */
export interface RedProfile {
	red_profile: string;
	first_name: string | null;
	last_name: string | null;
	full_name: string;
	email: string | null;
	phone: string | null;
	gender: string | null;
	date_of_birth: string | null;
	preferred_language: string | null;
	/** A file URL on this site, or null. Set through `update_my_profile`. */
	profile_photo: string | null;
	/**
	 * Where core last recorded this person as living, written by whichever
	 * registration they filed first. Read-only — `update_my_profile` does not
	 * accept it — and served so a placement picker can open already answered.
	 */
	home_geo_node: string | null;
}

/**
 * One row of a configured vocabulary — a skill, a language, an availability
 * slot, a motivation, an ID type. `api/volunteer.py::_vocabulary`.
 *
 * `key` is the docname the Link field stores and the value
 * `apply_to_volunteer` expects back; `label` is display only, and is never
 * compared. The same rule stage labels follow.
 */
export interface VocabularyRow {
	key: string;
	label: string;
	description: string | null;
}

/**
 * One question a society added to a registration, from
 * `registration/services/questions.py::asked_on`.
 *
 * `field_type` is the server's own vocabulary and the frontend does not extend
 * it: a type this build has never seen is a question it declines to draw rather
 * than one it renders as a text box and stores wrongly. `choices` is empty for
 * everything but `Select`.
 */
export interface SocietyQuestion {
	name: string;
	label: string;
	field_type: "Data" | "Small Text" | "Select" | "Check" | "Date" | "Int" | "Attach";
	choices: string[];
	is_required: boolean;
	help_text: string;
}

/**
 * The full picture an approver reads before deciding, from
 * `volunteer/services/application.py::decision_dto`.
 *
 * Assembled live from the application and Red Profile every time it is asked
 * for, so nothing in it is a copy that can go stale.
 */
export interface ApplicationDecision {
	name: string;
	full_name: string;
	email: string | null;
	phone: string | null;
	country_of_citizenship: string | null;
	residency_type: string;
	home_geo_path: string | null;
	country_of_residence: string | null;
	residence_address: string | null;
	geo_path: string | null;
	skills: Array<{ key: string; label: string }>;
	languages: Array<{ key: string; label: string }>;
	availability: Array<{ key: string; label: string }>;
	motivation: Array<{ key: string; label: string }>;
	prior_experience: string | null;
	identification: {
		id_type: string | null;
		id_type_name: string | null;
		id_number: string | null;
	} | null;
	answers: SocietyAnswer[];
}

/** One answer as an approver reads it, from `questions.answers_of`. */
export interface SocietyAnswer {
	question: string;
	label: string;
	field_type: string;
	value: string;
	file_url: string;
	is_file: boolean;
}

/** `api/volunteer.py::application_options`. */
export interface ApplicationOptions {
	questions: SocietyQuestion[];
	skills: VocabularyRow[];
	languages: VocabularyRow[];
	availability: VocabularyRow[];
	motivations: VocabularyRow[];
	id_types: VocabularyRow[];
	countries: string[];
	residency_types: string[];
	default_country_of_citizenship: string | null;
}

/** `api/registration.py::identity_options`. */
export interface IdentityOptions {
	genders: string[];
}

/** `api/geo.py::browse`. */
export interface GeoNode {
	name: string;
	label: string;
	level: string;
	level_name: string;
	is_group?: boolean;
}

/**
 * `api/geo.py::ladder` — one rung of the society's configured hierarchy.
 *
 * How many of these there are is how many select fields a placement form draws.
 * Nothing in this app assumes a number, a name or a depth.
 */
export interface GeoLevel {
	key: string;
	name: string;
	order: number;
	is_lowest: boolean;
}

/**
 * `api/opportunities.py::browse` — one published job opening.
 *
 * The society's own `Job Opening` in HRMS, through the seam in
 * `vmmsx/hr/services/openings.py`, which is the only file that names that
 * doctype. This is not a deployment need: the board used to advertise
 * `VMMS Deployment Request` and the field names here changed with the source.
 */
export interface Opportunity {
	name: string;
	opening: string;
	title: string;
	/**
	 * The description as sanitised markup, for `dangerouslySetInnerHTML`.
	 *
	 * **Safe because the server made it safe.** HRMS stores this field as
	 * rich text — an HR officer's headings and bullet lists — and it arrives
	 * having been through Frappe's `sanitize_html`, which is what the framework
	 * runs before rendering user HTML anywhere else. Rendering it as text
	 * instead is what put escaped `<div class="ql-editor">` on the board.
	 */
	description_html: string;
	/** The same description flattened to one paragraph, for a card. */
	summary: string;
	department: string;
	designation: string;
	employment_type: string;
	/** HRMS's own Branch record, which is not a Geo Node and is not mapped to one. */
	location: string;
	places: number;
	posted_on: string;
	closes_on: string;
	closing_soon: boolean;
	/** HRMS's public page for this opening. Null when it has no route yet. */
	href: string | null;
	/** Where "Apply" goes: HRMS's application route, or the opening's own page. */
	apply_href: string | null;
}

/** `api/member.py::membership_type_pricing`. */
export interface PricedType {
	known: boolean;
	membership_type: string;
	membership_type_name: string;
	/** Who the type is for, in the society's own words. May be empty. */
	description: string | null;
	amount: number;
	currency: string;
	free: boolean;
	is_lifetime: boolean;
	duration_days: number;
	requires_approver: boolean;
	benefits: Array<{ key: string; label: string; description: string | null }>;
}

/**
 * `api/tasks.py::branch_tasks` and `my_tasks` — a task as it appears in a list.
 *
 * Deliberately thinner than `TaskDetail`: a list of thirty tasks each carrying
 * its whole conversation is a response nobody wanted and a disclosure nobody
 * reviewed, which is why the server has two DTOs rather than one it trims.
 */
export interface TaskSummary {
	name: string;
	subject: string;
	/** The closed set in `task/services/states.py`. Code, not configuration. */
	status: string;
	volunteer: string;
	geo_node: string;
	due_on: string | null;
	assigned_on: string | null;
	/** A question the volunteer asked that nobody has answered. A flag, not a state. */
	open_question: boolean;
	is_open: boolean;
}

/** `api/tasks.py::get_task` — one task in full, with its thread. */
export interface TaskDetail extends TaskSummary {
	description: string;
	deployment: string | null;
	accepted_on: string | null;
	submitted_on: string | null;
	closed_on: string | null;
	completion_notes: string | null;
	thread: Array<{
		/** Display only. Nothing in this app branches on it. */
		entry_type: string;
		author: string;
		posted_on: string;
		note: string | null;
		/** A file URL from Frappe's own upload endpoint, or null. */
		proof: string | null;
	}>;
}

/** `api/deployment.py::my_invitations` — one row of either list. */
export interface DeploymentInvitation {
	/**
	 * The `VMMS Deployment Assignment` this question lives on. Answering names
	 * this, not the deployment: the roster is a register of documents now, one
	 * per person, and the assignment records the exact submitted terms of
	 * reference this volunteer was asked to accept.
	 */
	assignment: string;
	deployment: string;
	/** The society's own word for the work. A docname is not a title. */
	title: string | null;
	terms_of_reference: string | null;
	/** The deployment's own state — Planned, Active, and so on. */
	deployment_status: string;
	/** This volunteer's own dates, which may be narrower than the deployment's. */
	start_date: string | null;
	end_date: string | null;
	geo_node: string;
	notes: string | null;
	/** `Pending`, `Accepted` or `Declined`. */
	response: string;
	role: string;
	invited_on: string | null;
	responded_on: string | null;
	response_note: string | null;
}

/** `api/locations.py` — one place, as a visitor sees it. */
export interface BranchLocation {
	name: string;
	location_name: string;
	geo_node: string;
	address: string;
	latitude: number | null;
	longitude: number | null;
	/** Whether there is a coordinate pair to draw. Never inferred from `0.0`. */
	has_point: boolean;
	phone: string;
	email: string;
	opening_hours: string;
	photo: string;
}

/* ---------------------------------------------------------- deployments */

/** `deployment/services/deployment.py::status_dto` — one deployment in summary. */
export interface DeploymentSummary {
	name: string;
	terms_of_reference: string | null;
	geo_node: string | null;
	geo_path: string | null;
	/** Planned, Active, Completed or Cancelled. The doctype's own closed set. */
	status: string;
	is_open: boolean;
	start_date: string | null;
	end_date: string | null;
	volunteers_required: number;
	/** Assigned + Accepted: who is actually going, not who was asked. */
	participant_count: number;
	assignment_counts: AssignmentCounts;
	/**
	 * How many places are still open, or `null` where the society has not said
	 * how many it needs. Null rather than zero, because a deployment that has
	 * not said needs no arithmetic and is never full.
	 */
	places_left: number | null;
}

/**
 * `deployment/services/assignment.py::dto` — one person's deployment.
 *
 * The roster is a register of `VMMS Deployment Assignment` documents rather
 * than a child table, because each person's deployment needed a URL they could
 * open, a reference a notification could point at, a lifecycle with a grammar,
 * and somewhere to record which submitted terms of reference they agreed to.
 */
export interface RosterRow {
	name: string;
	deployment: string;
	volunteer: string;
	full_name: string;
	/** The exact submitted document this person was asked to accept. */
	terms_of_reference: string;
	geo_node: string | null;
	/** `Assigned`, `Pending`, `Accepted`, `Declined` or `Withdrawn`. */
	status: string;
	/**
	 * The three derived answers, so no screen holds its own copy of what the
	 * five statuses mean. `is_on_deployment` is Assigned or Accepted — the two
	 * that fill a place and let time be logged.
	 */
	is_on_deployment: boolean;
	is_open: boolean;
	is_settled: boolean;
	role: string;
	is_leader: boolean;
	start_date: string | null;
	end_date: string | null;
	invited_on: string | null;
	responded_on: string | null;
	response_note: string | null;
	joined_on: string | null;
	left_on: string | null;
	participation_notes: string | null;
	notes: string | null;
}

/**
 * `api/deployment.py::deployment_map` — one area's share of the work.
 *
 * `latitude`/`longitude` are **absent, not null**, where the geo tree has no
 * point for the node: a caller iterating this gets only what it can draw, and
 * the screen reports `unplotted` rather than silently showing fewer pins than
 * there are places.
 */
export interface DeploymentArea {
	geo_node: string;
	geo_path: string | null;
	deployments: number;
	/** Assigned + Accepted. A question nobody answered is not somebody there. */
	people: number;
	waiting: number;
	latitude?: number;
	longitude?: number;
}

/** `api/deployment.py::deployment_map`. */
export interface DeploymentMapAnswer {
	areas: DeploymentArea[];
	deployed: number;
	/** How many areas carry no point, so the screen can say so plainly. */
	unplotted: number;
}

/** `assignment.counts_for` — how a deployment's register breaks down. */
export interface AssignmentCounts {
	Assigned: number;
	Pending: number;
	Accepted: number;
	Declined: number;
	Withdrawn: number;
	/** Assigned + Accepted: who is actually going. */
	on_deployment: number;
	open: number;
	total: number;
}

/** `assignment.deploy` — the bulk act's honest report. */
export interface AssignmentOutcome {
	deployment: string;
	requested: number;
	raised: number;
	refused: number;
	success: Array<{
		volunteer: string;
		full_name: string;
		assignment: string;
		status: string;
	}>;
	/** Per person, with the sentence the service threw. Never a code. */
	failure: Array<{ volunteer: string; full_name: string; reason: string }>;
}

/** `deployment/services/feed.py::_entry` — one line of a deployment's account. */
export interface FeedEntry {
	/** `deployment` for the deployment's own log, `task` for a volunteer's report. */
	source: string;
	entry_type: string;
	author: string;
	author_name: string | null;
	posted_on: string | null;
	note: string | null;
	proof: string | null;
	/** Set only on a task-sourced entry. */
	task: string | null;
	subject: string | null;
	volunteer: string | null;
}

/** `api/deployment.py::get_deployment_feed`. */
export interface DeploymentFeed {
	deployment: string;
	count: number;
	truncated: boolean;
	entries: FeedEntry[];
}

/** `api/deployment.py::get_my_assignment` — the volunteer's read before answering. */
export interface MyAssignment {
	assignment: RosterRow;
	/** The mission itself, read through the terms the assignment names. */
	terms: TermsMission;
	deployment: {
		name: string;
		status: string;
		start_date: string | null;
		end_date: string | null;
		geo_node: string | null;
		notes: string | null;
	};
}

/* ---------------------------------------------------------- availability */

/** One day-and-window pair on a volunteer's weekly pattern. */
export interface AvailabilityDay {
	day: string;
	availability_slot: string;
}

/** `volunteer/services/availability.py::slots` — the grid's columns. */
export interface AvailabilitySlot {
	name: string;
	slot_name: string;
	start_time: string | null;
	end_time: string | null;
	description: string | null;
}

/** `api/volunteer.py::my_availability`. */
export interface MyAvailability {
	volunteer: string;
	exists: boolean;
	available_on_holidays: boolean;
	valid_from: string | null;
	valid_to: string | null;
	notes: string | null;
	days: AvailabilityDay[];
	slots: AvailabilitySlot[];
}

/**
 * `volunteer/services/availability.py::assess` — three-way, and `unknown` is a
 * first-class answer rather than an error state.
 *
 * `is_available` is deliberately false for `unknown`: a caller meaning "do not
 * rule this person out" reads `!is_unavailable`, and having to choose between
 * the two is what stops a screen quietly treating silence as a yes.
 */
export interface AvailabilityAnswer {
	state: string;
	is_available: boolean;
	is_unavailable: boolean;
	is_known: boolean;
	why: string;
	missing_days: string[];
	slots: string[];
	available_on_holidays: boolean | null;
}

/** How much of each mission table has been written. `terms.dto::section_counts`. */
export interface TermsSectionCounts {
	stakeholders: number;
	objectives: number;
	expected_outputs: number;
	approach_methods: number;
	itinerary: number;
	resources: number;
}

/** `deployment/services/terms.py::dto` — the lean summary every caller gets. */
export interface TermsOfReference {
	name: string;
	tor_key: string;
	tor_name: string;
	is_active: boolean;
	/**
	 * The submit state, split into the questions a screen actually asks. A draft
	 * may still be edited and takes no deployments; a submitted one is frozen,
	 * which is the point — accepting an assignment is accepting this document,
	 * so its wording must not change underneath somebody afterwards.
	 */
	docstatus: number;
	is_draft: boolean;
	is_submitted: boolean;
	is_cancelled: boolean;
	/** Submitted *and* still active: the one predicate that means "takes new work". */
	is_offered: boolean;
	amended_from: string | null;
	expected_start_date: string | null;
	expected_end_date: string | null;
	section_counts: TermsSectionCounts;
	purpose: string | null;
	responsibilities: string | null;
	geo_scope: string | null;
	geo_scope_path: string | null;
	default_duration_days: number | null;
	approval_mode: string | null;
	requires_approver: boolean;
	required_certifications: string[];
	desirable_certifications: string[];
	/** The programme these terms were written under, or null for a standing duty. */
	project: string | null;
	project_name: string | null;
}

/** `deployment/services/project.py::dto` — one programme of work. */
export interface ProjectSummary {
	name: string;
	project_name: string;
	/** Planned, Active, Completed or Cancelled. The service's own closed set. */
	status: string;
	is_open: boolean;
	geo_node: string | null;
	geo_path: string | null;
	start_date: string | null;
	end_date: string | null;
	summary: string | null;
	notes: string | null;
	created_on: string | null;
}

/* ------------------------------------------- the mission tables on a ToR */

export interface TermsStakeholder {
	designation: string | null;
	full_name: string | null;
	phone_number: string | null;
	email: string | null;
}

export interface TermsObjective {
	objective: string | null;
}

export interface TermsOutput {
	output: string | null;
}

export interface TermsApproach {
	/** A `VMMS TOR Methodology` docname — the society's own register of methods. */
	methodology: string | null;
	notes: string | null;
}

export interface TermsItineraryRow {
	activity_date: string | null;
	activity_time: string | null;
	activity: string | null;
	person_responsible: string | null;
}

export interface TermsResource {
	resource: string | null;
	needed_on: string | null;
	quantity: number | null;
	unit: string | null;
	unit_cost: number | null;
	donor: string | null;
	/** Derived on the server from quantity × unit cost. Never sent back. */
	total_cost?: number | null;
}

/**
 * `deployment/services/terms.py::mission_dto` — the summary plus the six
 * mission tables and the background. Only the screens that show a terms of
 * reference *in full* ask for this; every other caller gets `TermsOfReference`,
 * which is why that one stays lean enough to embed in every deployment read.
 */
export interface TermsMission extends TermsOfReference {
	mission_background: string | null;
	notes: string | null;
	stakeholders: TermsStakeholder[];
	objectives: TermsObjective[];
	expected_outputs: TermsOutput[];
	approach_methods: TermsApproach[];
	itinerary: TermsItineraryRow[];
	resources: TermsResource[];
	/** The mission's own resource lines totalled. Nothing reaches across a project. */
	resources_total: number;
}

/** `api/deployment.py::tor_methodologies` — the approach tab's picker. */
export interface TermsMethodology {
	name: string;
	methodology_name: string;
	description: string | null;
}

/**
 * `api/deployment.py::get_terms` — the whole mission, the same terms rendered
 * through the society's own template, and the deployments run under them.
 * `document` is the identical markup the PDF is built from, which is what stops
 * the screen and the printer showing two different documents.
 */
export interface TermsDocument {
	terms: TermsMission;
	document: string;
	deployments: DeploymentSummary[];
}

/**
 * `api/deployment.py::get_project` — one project, and its whole history: the
 * terms of reference written under it and the deployments run under those,
 * composed server-side so the three pieces cannot disagree.
 */
export interface ProjectDossier {
	project: ProjectSummary;
	terms: TermsOfReference[];
	deployments: DeploymentSummary[];
}

/** `deployment/services/deployment.py::deployment_dto` — one deployment in full. */
export interface DeploymentDetail extends DeploymentSummary {
	terms: TermsOfReference | null;
	/** The whole assignment register, settled rows included — a coordinator
	 * needs to see who declined as much as who accepted, or they will ask the
	 * same person again next week. */
	participants: RosterRow[];
	/** The volunteer leading it, or null. Only an assignment actually on the
	 * deployment counts: somebody named leader who then declined is not leading. */
	leader: string | null;
	notes: string | null;
}

/** `deployment/services/matching.py::_assess` — one volunteer against one need. */
export interface Candidate {
	volunteer: string;
	red_profile: string | null;
	full_name: string;
	/**
	 * Their photograph, or null. Read in bulk with the rest of the page rather
	 * than per row, and null is the ordinary case rather than an error one — a
	 * volunteer registered at a branch desk on paper has none, and every screen
	 * falls back to initials.
	 */
	photo: string | null;
	status: string;
	home_geo_node: string | null;
	geo_path: string | null;
	deployable: boolean;
	blocking_reasons: string[];
	missing_certifications: string[];
	desirable_certifications_held: string[];
	/**
	 * Advisory, both of them: shown, ranked on, and never part of the verdict.
	 * Being deployable and holding what the terms require decides whether
	 * somebody *may* be sent; being free and being double-booked are judgements
	 * about whether they *should* be, and those belong to the coordinator.
	 */
	availability: AvailabilityAnswer;
	clash: {
		is_clashing: boolean;
		deployments: Array<{
			deployment: string;
			start_date: string | null;
			end_date: string | null;
		}>;
	};
	/** The one derived verdict, and the only field to branch on. */
	is_candidate: boolean;
}

/** `deployment/services/matching.py::candidates` — the ranked answer. */
export interface CandidateSearch {
	terms_of_reference: string;
	geo_node: string;
	geo_path: string | null;
	as_of: string;
	/** The span the availability and clash answers were computed over, echoed
	 * back so a screen says what it asked rather than assuming. */
	start_date: string | null;
	end_date: string | null;
	required_certifications: string[];
	desirable_certifications: string[];
	considered: number;
	candidate_count: number;
	/** True when `limit` bit. A silently shortened list reads as "all of them". */
	truncated: boolean;
	candidates: Candidate[];
	pending_criteria: Array<Record<string, unknown>>;
}

/** `deployment/services/request.py::status`. */
export interface DeploymentRequestRow {
	name: string;
	terms_of_reference: string | null;
	geo_node: string | null;
	geo_path: string | null;
	volunteers_requested: number | null;
	needed_from: string | null;
	needed_until: string | null;
	approval_mode: string | null;
	requires_approver: boolean;
	approval_settled: boolean;
	is_refused: boolean;
	deployment: string | null;
	is_fulfilled: boolean;
	approval: ApprovalStatus | null;
}

/* -------------------------------------------------------------- stipends */

/**
 * `stipend/services/approval.py::status`. `can_be_decided` is a constant false
 * and the screen draws what it says: departmental routing does not exist, so
 * nobody can approve this yet and `blocked_because` is the sentence explaining
 * it rather than something the frontend writes.
 */
export interface StipendApproval {
	doctype: string;
	name: string;
	approval_state: string;
	is_pending: boolean;
	can_be_decided: boolean;
	can_be_withdrawn: boolean;
	blocked_because: string | null;
	note: string | null;
	submitted_on: string | null;
	submitted_by: string | null;
}

/** One volunteer's line on a progress report. */
export interface ReportVolunteerRow {
	volunteer: string;
	activity: string | null;
	notes: string | null;
	department: string | null;
}

/** `stipend/services/report.py::status`. */
export interface StipendReport {
	report: string;
	geo_node: string | null;
	geo_path: string | null;
	period_from: string | null;
	period_to: string | null;
	volunteer_count: number;
	volunteers: ReportVolunteerRow[];
	approval: StipendApproval;
	pending_routing: unknown;
}

/** One volunteer's total on a payment form, summed from the attendance grid. */
export interface PerVolunteerRow {
	volunteer: string;
	days_recorded: number;
	days_attended: number;
	hours: number;
	total_payable: number;
}

/** `stipend/services/payment.py::status`. */
export interface StipendPaymentForm {
	payment_form: string;
	progress_report: string | null;
	geo_node: string | null;
	geo_path: string | null;
	period_from: string | null;
	period_to: string | null;
	currency: string | null;
	line_count: number;
	per_volunteer: PerVolunteerRow[];
	total_payable: number;
	approval: StipendApproval;
}

/* --------------------------------------------------------------- dossiers */

/**
 * The two coordinator's views, `api/volunteer.py::get_dossier` and
 * `api/member.py::get_dossier`.
 *
 * **Composed, never merged**, exactly as the endpoints build them: each block is
 * the DTO its own service produces, under its own key. In particular a
 * volunteer's `capabilities` (what is true now) and `application.declared`
 * (what they claimed on the day) are two blocks and are never reconciled — a
 * coordinator comparing them is the point, and a type that flattened them into
 * one would quietly invite a screen to.
 *
 * `as_of` is resolved once server-side and every derived answer below is
 * answered as at that instant, so nothing on a screen built from one of these
 * can contradict anything else on it.
 */

/** One `{key, label}` pair from `capabilities.selector_dto`. */
export interface SelectorRow {
	key: string;
	label: string;
}

/** `capabilities.current` — the vocabularies a volunteer's own record carries. */
export interface VolunteerCapabilities {
	skills: SelectorRow[];
	languages: SelectorRow[];
	availability: SelectorRow[];
}

/** One decision row, snapshotted by the engine. `stage_label` is display only. */
export interface DecisionRow {
	stage_label: string | null;
	approver: string | null;
	decision: string | null;
	decided_on: string | null;
	reason: string | null;
}

/** `volunteer/services/application.py::verification_dto`. */
export interface VolunteerVerification {
	volunteer: string;
	application: string | null;
	application_count: number;
	approval_state: string | null;
	applied_on: string | null;
	geo_node: string | null;
	decisions: DecisionRow[];
	declared: {
		skills: SelectorRow[];
		languages: SelectorRow[];
		availability: SelectorRow[];
		motivation: SelectorRow[];
		prior_experience: string | null;
		identification: Record<string, unknown> | null;
	} | null;
}

/** `deployment/services/participation.py::history_of` — one deployment served. */
export interface DeploymentHistoryRow {
	deployment: string;
	status: string | null;
	start_date: string | null;
	end_date: string | null;
	geo_node: string | null;
	terms_of_reference: string | null;
	tor_name: string | null;
	/** The assignment this service came through, and what they did on it. */
	assignment?: string | null;
	role?: string | null;
	is_leader?: boolean;
	joined_on: string | null;
	left_on: string | null;
	notes: string | null;
}

/** `volunteer/services/timelog.py::summary`. */
export interface TimeSummary {
	volunteer: string;
	total_hours: number;
	log_count: number;
	/** Keyed by whatever `log_type` values the rows carry. Never indexed by a literal. */
	hours_by_type: Record<string, number>;
	recent: TimeLogRow[];
}

/** `api/volunteer.py::get_dossier`. */
export interface VolunteerDossier {
	volunteer: string;
	as_of: string;
	identity: VolunteerProfile;
	capabilities: VolunteerCapabilities;
	certifications: CertificationRow[];
	deployability: Deployability;
	deployments: DeploymentHistoryRow[];
	time: TimeSummary;
	application: VolunteerVerification;
	/**
	 * Whether this caller may work the lifecycle acts, answered server-side by
	 * the same `write` check the endpoints enforce. A screen draws its buttons
	 * from this and decides nothing itself; the holder reading their own
	 * dossier gets `false`.
	 */
	can_act: boolean;
	/** Whether there is a card to reprint, from the same predicate the download asserts. */
	holds_card: boolean;
}

/** `member/services/dossier.py::identity_dto`. */
export interface MemberIdentity {
	member: string;
	red_profile: string;
	full_name: string | null;
	email: string | null;
	phone: string | null;
	gender: string | null;
	date_of_birth: string | null;
	preferred_language: string | null;
	profile_photo: string | null;
	nationality: string | null;
	citizenship_status: string | null;
	home_geo_node: string | null;
	home_geo_path: string | null;
}

/**
 * `member/services/dossier.py::standing`.
 *
 * `status` is over every membership; the counts are over the ones this caller
 * may see. They are named differently because they answer different questions.
 */
export interface MemberStanding {
	status: string;
	joined_on: string | null;
	as_of: string;
	visible_count: number;
	current_count: number;
	lapsed_count: number;
	current_geo_paths: string[];
}

/** `member/services/dossier.py::membership_dto` — `status()` plus the date-derived truths. */
export interface MembershipDossierRow extends MembershipRow {
	effective_status: string;
	lapsed: boolean;
	is_current: boolean;
	as_of: string;
	membership_geo_node: string | null;
	membership_geo_path: string | null;
	duration_days: number | null;
	/**
	 * `dossier._certificate_access` — three separate questions, and a screen
	 * offering the button needs all three. `available` is whether there is a
	 * certificate at all, `may_print` is whether *this* caller may have it, and
	 * `configured` is whether the type has a template to render.
	 */
	certificate: {
		available: boolean;
		may_print: boolean;
		configured: boolean;
	};
}

/** `member/services/dossier.py::history` — the trail across every membership shown. */
export interface MemberHistoryRow extends DecisionRow {
	membership: string;
	membership_type_name: string | null;
	geo_path: string | null;
	membership_source: string | null;
}

/** `api/member.py::get_dossier`. */
export interface MemberDossier {
	member: string;
	as_of: string;
	identity: MemberIdentity;
	standing: MemberStanding;
	memberships: MembershipDossierRow[];
	history: MemberHistoryRow[];
	/** See `VolunteerDossier.can_act`. */
	can_act: boolean;
}

/* --------------------------------------------------------- form builder */

/**
 * `api/questions.py` — the society's own questions on a registration.
 *
 * `asked_on` is a doctype name because the module names no registration: the
 * volunteer application and the membership are two rows in `targets`, derived
 * from which doctypes carry the answer table, rather than two cases in code.
 */
export interface QuestionTarget {
	doctype: string;
	label: string;
	/** Active questions on this registration, for the tab's own count. */
	count: number;
}

export interface QuestionTargets {
	targets: QuestionTarget[];
	/** Read from the doctype's own Select, so a new type appears without a deploy. */
	field_types: string[];
	can_edit: boolean;
}

/** One question as the builder draws it, from `api/questions.py::_row`. */
export interface BuilderQuestion {
	name: string;
	asked_on: string;
	label: string;
	field_type: string;
	/** The raw newline-separated list, which is what the editor writes back. */
	options: string;
	/** The same list split, which is what a preview draws. */
	choices: string[];
	is_required: boolean;
	is_active: boolean;
	help_text: string;
	sequence: number;
	/**
	 * How many applications already answered this. What makes "retire, never
	 * delete" legible to somebody looking for a delete button.
	 */
	answer_count: number;
}

export interface QuestionCatalogue {
	asked_on: string;
	questions: BuilderQuestion[];
	can_edit: boolean;
}

/* ---------------------------------------------------------------- events */

/**
 * `buzz/services/events.py::_as_card` — one published Buzz event.
 *
 * Every string field is normalised to `""` rather than null by the seam, and
 * `end_date` falls back to the start date, so no screen has to decide what an
 * absent end means. `href` is Buzz's own page: booking, tickets and check-in
 * are Buzz's, and the call to action is a full navigation there.
 */
export interface EventCard {
	event: string;
	title: string;
	summary: string;
	category: string;
	venue: string;
	medium: string;
	start_date: string;
	end_date: string;
	start_time: string;
	end_time: string;
	time_zone: string;
	image: string;
	geo_node: string;
	href: string | null;
	multi_day: boolean;
}
