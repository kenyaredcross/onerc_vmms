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

/** `api/opportunities.py::browse` — one advertised deployment need. */
export interface Opportunity {
	name: string;
	terms_of_reference: string;
	title: string;
	purpose: string | null;
	responsibilities: string | null;
	requirements: Array<{
		certification_type: string;
		label: string;
		is_mandatory: boolean;
		notes: string | null;
	}>;
	geo_node: string;
	geo_path: string;
	needed_from: string | null;
	needed_until: string | null;
	/**
	 * How many the branch asked for, and how many of those are already on the
	 * deployment. Served, and deliberately **not drawn** on either the card or
	 * the detail page: a job opening advertises the work, not how close it is to
	 * being filled, and a half-full progress bar tells a volunteer to look
	 * elsewhere. A coordinator reads these on the deployment itself.
	 */
	volunteers_requested: number;
	places_filled: number;
	/** The deployment this need produced, once somebody has created it. */
	deployment: string | null;
	/** `VMMS Deployment.status`. Null while no deployment exists yet. */
	deployment_status: string | null;
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
	deployment: string;
	/** The society's own word for the work. A docname is not a title. */
	title: string | null;
	status: string;
	start_date: string | null;
	end_date: string | null;
	geo_node: string;
	notes: string | null;
	/** `invited`, `accepted` or `declined`. Blank never reaches this DTO. */
	response: string;
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
	participant_count: number;
}

/** One row of a deployment's roster. */
export interface RosterRow {
	volunteer: string;
	joined_on: string | null;
	left_on: string | null;
	notes: string | null;
	/**
	 * `invited`, `accepted`, `declined`, or null for somebody a coordinator
	 * simply put on the roster without asking. An answer decides nothing about
	 * participation; taking somebody off is the coordinator's own act.
	 */
	response: string | null;
	responded_on: string | null;
}

/** `deployment/services/terms.py::dto`. */
export interface TermsOfReference {
	name: string;
	tor_key: string;
	tor_name: string;
	is_active: boolean;
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

/**
 * `api/deployment.py::get_terms` — the reviewed field list, the same terms
 * rendered through the society's own template, and the deployments run under
 * them. `document` is the identical markup the PDF is built from, which is
 * what stops the screen and the printer showing two different documents.
 */
export interface TermsDocument {
	terms: TermsOfReference;
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
	participants: RosterRow[];
	notes: string | null;
}

/** `deployment/services/matching.py::_assess` — one volunteer against one need. */
export interface Candidate {
	volunteer: string;
	red_profile: string | null;
	full_name: string;
	status: string;
	home_geo_node: string | null;
	geo_path: string | null;
	deployable: boolean;
	blocking_reasons: string[];
	missing_certifications: string[];
	desirable_certifications_held: string[];
	/** The one derived verdict, and the only field to branch on. */
	is_candidate: boolean;
}

/** `deployment/services/matching.py::candidates` — the ranked answer. */
export interface CandidateSearch {
	terms_of_reference: string;
	geo_node: string;
	geo_path: string | null;
	as_of: string;
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
