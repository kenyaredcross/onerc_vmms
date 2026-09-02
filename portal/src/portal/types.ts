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
	country_of_citizenship?: string | null;
	residency_type?: "Local" | "Abroad" | null;
	country_of_residence?: string | null;
	residence_address?: string | null;
	identifications?: Array<{
		id_type: string;
		id_type_name: string;
		id_number: string;
		attachment: string | null;
		is_primary: boolean;
	}>;
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
	/**
	 * Who this approval is *about*, resolved by `approvals/services/applicant.py`
	 * from the workflow's own `applicant_field` — one hop for an application
	 * that links a Red Profile, two for a membership that links a member.
	 *
	 * Null for a governed doctype whose subject is not a person, which is not an
	 * error and which every queue row has to survive. It is not null merely
	 * because a doctype has no decision view of its own: that was the old bug,
	 * where a membership reached the review screen as a docname and a stage
	 * label with no name attached to it.
	 */
	applicant: {
		doctype: string | null;
		name: string;
		red_profile: string | null;
		full_name: string;
		email: string | null;
		phone: string | null;
		photo: string | null;
	} | null;
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
	/**
	 * Null, not empty, when the caller is an onlooker. `engine.status` withholds
	 * both lists from anybody outside the decision — the applicant learns their
	 * application is with two people, not which two — and a caller who models
	 * that as `[]` cannot tell "nobody" from "not yours to see".
	 */
	approvers: string[] | null;
	escalated_to: string[] | null;
	allow_withdrawal: boolean;
	can_withdraw: boolean;
	/**
	 * The audit trail, oldest first — `engine.status`'s own rows.
	 *
	 * **Written out in full to match the server**, which it did not before: the
	 * shape here named `decided_by` where the DTO says `approver` and omitted
	 * `stage` and `stage_sequence` entirely, so a screen reading either got
	 * `undefined` with the compiler's blessing. `stage_label` is the label the
	 * stage carried *at the time* — snapshotted by `contract.record_decision`,
	 * so a society that relabels a stage next year does not rewrite what
	 * happened this year. Display only, like every stage label in this app.
	 */
	decisions: Array<{
		stage: string | null;
		stage_sequence: number | null;
		stage_label: string | null;
		approver: string;
		/** One of the three in `states.DECISIONS`. Shown, never branched on. */
		decision: string;
		reason: string | null;
		decided_on: string | null;
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
	country_of_citizenship: string | null;
	citizenship_status: string | null;
	residency_type: "Local" | "Abroad" | null;
	home_geo_node: string | null;
	country_of_residence: string | null;
	residence_address: string | null;
	identifications: Array<{
		id_type: string;
		id_number: string;
		attachment: string | null;
		is_primary: boolean;
	}>;
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
	/**
	 * The heading this question is asked under — a society's own word, empty
	 * when it did not group this one. Never compared against anything: it is
	 * drawn as a section on a form and as a tab on an approver's screen, and
	 * "Health information" is a string a national society typed rather than a
	 * case in this app.
	 */
	group: string;
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
	/** Live from Red Profile. Null for an applicant who uploaded none. */
	profile_photo: string | null;
	gender: string | null;
	date_of_birth: string | null;
	preferred_language: string | null;
	applied_on: string | null;
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
		attachment?: string | null;
		is_primary?: boolean;
	} | null;
	identifications: Array<{
		id_type: string;
		id_type_name: string | null;
		id_number: string;
		attachment: string | null;
		is_primary: boolean;
	}>;
	answers: SocietyAnswer[];
	/**
	 * The three things `application.assert_approvable` will refuse the decision
	 * over, so the approver can see them before pressing Approve rather than
	 * afterwards.
	 */
	emergency_contacts: EmergencyContact[];
	is_minor: boolean;
	/** Carries the reviewer's own verification, unlike the applicant's view. */
	guardian_consents: Array<
		GuardianConsent & {
			is_verified: boolean;
			verified_by: string | null;
			verified_on: string | null;
		}
	>;
	/** What was agreed to, in the wording that stood on the day. */
	declarations: Array<{
		declaration: string;
		title: string;
		version: string;
		declaration_version: string | null;
		/** See `Declaration.source`. `Link` acceptances have no body to show. */
		source: "Text" | "Link";
		body: string | null;
		external_url: string | null;
		accepted: boolean;
		accepted_on: string | null;
	}>;
}

/** One answer as an approver reads it, from `questions.answers_of`. */
export interface SocietyAnswer {
	question: string;
	label: string;
	/** The group as it was at the time of answering — a snapshot, like the label. */
	group: string;
	field_type: string;
	value: string;
	file_url: string;
	is_file: boolean;
}

/** `api/volunteer.py::application_options`. */
/**
 * One declaration a society asks an applicant to agree to, from
 * `registration/services/declarations.py::shown_on`.
 *
 * `body` is HTML the society wrote and is rendered as such. `version` travels
 * with it because what gets stored on the application is this exact wording at
 * this exact version — see `VMMS Declaration Acceptance`.
 */
export interface Declaration {
	name: string;
	title: string;
	version: string;
	/**
	 * Whether the wording is held here or published on the society's own site.
	 * A closed set this app owns — see `declarations.SOURCE_TEXT` — so a screen
	 * may branch on it. `body` carries the words for `Text`; `external_url`
	 * carries the address for `Link`, and exactly one of the two is filled.
	 */
	source: "Text" | "Link";
	body: string | null;
	external_url: string | null;
	/** The `VMMS Declaration Version` being shown, recorded on the acceptance. */
	declaration_version: string | null;
	is_required: boolean;
}

/**
 * An identification type, and what this society asks of it.
 *
 * The three rule fields come from vmmsx-owned Custom Fields on core's
 * `Identification Type`, and they are the same rows
 * `application._required_document_types` reads on the server — so a form built
 * from these can never ask for less than the submission will insist on.
 * `minimum_age` is null where the document exists for everybody.
 */
export interface IdentificationTypeRow extends VocabularyRow {
	is_required: boolean;
	requires_attachment: boolean;
	minimum_age: number | null;
}

/** One emergency contact, as the portal posts it and reads it back. */
export interface EmergencyContact {
	contact_name: string;
	relationship: string;
	primary_phone: string;
	alternative_phone: string | null;
	may_contact_in_emergency: boolean | number;
}

/**
 * A guardian's consent, in the applicant's half of the record.
 *
 * The reviewer's own three fields — `is_verified`, `verified_by`, `verified_on`
 * — are deliberately absent. The portal cannot send them and is not handed
 * them: an applicant who could set them could verify their own guardian's
 * consent, which is the single thing the feature exists to prevent.
 */
export interface GuardianConsent {
	guardian_name: string;
	relationship: string;
	phone: string;
	email: string | null;
	consent_given: boolean | number;
	consent_date: string | null;
	verification_method: string | null;
	consent_evidence: string | null;
}

export interface ApplicationOptions {
	questions: SocietyQuestion[];
	skills: VocabularyRow[];
	languages: VocabularyRow[];
	availability: VocabularyRow[];
	motivations: VocabularyRow[];
	id_types: IdentificationTypeRow[];
	countries: string[];
	residency_types: string[];
	default_country_of_citizenship: string | null;
	declarations: Declaration[];
	/**
	 * The age this society treats as adult, or null where it has not said. Null
	 * means the guardian step is never drawn — the same answer
	 * `application.is_minor` reaches on the server, so the form and the approval
	 * gate agree by construction rather than by a number written twice.
	 */
	minor_age: number | null;
	guardian_verification_methods: VocabularyRow[];
}

/**
 * `api/registration.py::my_open_registrations` — one entry per registration
 * kind the caller has undecided.
 *
 * **`reviewed` is what stops "Draft" meaning two opposite things.** A
 * registration nobody has submitted is a Draft; so is one an approver sent back
 * for more information. The dashboard read those as one state and told people
 * who had not finished their own form that their branch was waiting on them.
 * The server answers it off the approval trail rather than off `reason`, which
 * an approver may leave empty.
 */
export interface OpenRegistration {
	doctype: string;
	name: string;
	path: string;
	state: string;
	/** What the approver wrote when they sent it back, if they wrote anything. */
	reason?: string;
	/** Has this ever been in front of an approver? */
	reviewed?: boolean;
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
	/**
	 * HRMS's public page for this opening — its own `route`, which is the whole
	 * path. Null when HRMS has not filled one in yet.
	 */
	href: string | null;
	/**
	 * Where "Apply" goes: HRMS's application form for this opening, the same
	 * address HRMS's own page puts behind its Apply button. Always a
	 * destination, because it does not depend on the opening having a page.
	 */
	apply_href: string;
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
	due_at: string | null;
	assigned_on: string | null;
	/** A question the volunteer asked that nobody has answered. A flag, not a state. */
	open_question: boolean;
	is_open: boolean;
	/** The society's own words, both of them. Neither is a closed set this app owns. */
	priority: string | null;
	task_type: string | null;
	/**
	 * The volunteer's own estimate, written by `report_progress`. **Never derived
	 * here from the checklist** — the server refuses to do that for the same
	 * reason, because a number this app worked out would be its opinion wearing
	 * somebody else's name.
	 */
	percent_complete: number;
	/** Derived on every read from `due_at` and the state. Never stored, never re-derived here. */
	is_overdue: boolean;
}

/** One line of a task's checklist, as the volunteer ticks it. */
export interface TaskChecklistItem {
	idx: number;
	item: string;
	is_required: boolean;
	is_done: boolean;
	done_on: string | null;
	notes: string | null;
	evidence: string | null;
}

/** One place on a task, from `deployment/services/geocoding.py::dto`. */
export interface TaskPlace {
	name: string | null;
	address: string | null;
	latitude: number | null;
	longitude: number | null;
	/** Whether there is a coordinate pair to draw. Never inferred from `0.0`. */
	has_point: boolean;
	located_on: string | null;
	map: string | null;
	directions: string | null;
}

/**
 * `api/tasks.py::get_task` — one task in full, with its thread.
 *
 * Everything below `completion_notes` was already on the server's DTO and had
 * never been declared here, which is why the portal's task screen drew a third
 * of a record. Nothing in this block is new API surface.
 */
export interface TaskDetail extends TaskSummary {
	description: string;
	deployment: string | null;
	project: string | null;
	batch: string | null;
	accepted_on: string | null;
	submitted_on: string | null;
	closed_on: string | null;
	completion_notes: string | null;
	// --- when ---------------------------------------------------------------
	planned_start: string | null;
	planned_end: string | null;
	/** The moment an answer is wanted by, which is not the moment the work is due. */
	response_deadline: string | null;
	expected_hours: number | null;
	actual_hours: number | null;
	// --- what has to be done -------------------------------------------------
	checklist: TaskChecklistItem[];
	/** Required items still unticked. The server's list, and what blocks a submission. */
	checklist_outstanding: string[];
	/** The coordinator's own files, kept apart from the volunteer's evidence. */
	brief_files: Array<{ label: string | null; file: string | null; notes: string | null }>;
	// --- what comes first ----------------------------------------------------
	depends_on: string[];
	/** Only the prerequisites that are not finished. Empty means nothing is in the way. */
	blocking: Array<{ name: string; subject: string; status: string }>;
	blocked_override_reason: string | null;
	// --- where ---------------------------------------------------------------
	where: {
		work: TaskPlace;
		meeting_point: TaskPlace;
		travel_instructions: string | null;
		local_contact: { name: string | null; phone: string | null };
		/** Set when the place came from the deployment rather than the task. */
		inherited_from: string | null;
	};
	// --- how it ended --------------------------------------------------------
	outcome: string | null;
	final_evidence: string | null;
	return_reason: string | null;
	rework_count: number;
	manager_rating: number | null;
	lessons_learned: string | null;
	decline_reason: string | null;
	reassigned_to_task: string | null;
	reassigned_from_task: string | null;
	reassignment_reason: string | null;
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
	/**
	 * One of `DEPLOYMENT_STATUSES` — the doctype's own closed set of **six**.
	 *
	 * It used to be described here as four, and the two missing ones were the
	 * two a screen most needs: Suspended is work that has stopped and not
	 * finished, and Closed Out is the only thing that distinguishes a mission
	 * whose paperwork is done from one whose is not.
	 */
	status: string;
	/** Planned, Active or Suspended — still somebody's problem. The server's answer. */
	is_open: boolean;
	/** Completed, Closed Out or Cancelled — the work is over, whatever the paperwork says. */
	is_settled: boolean;
	is_closed_out: boolean;
	coordinator: string | null;
	start_date: string | null;
	end_date: string | null;
	/**
	 * The period to the hour, and the four other moments a deployment has.
	 * Separate from the two dates above rather than replacing them: registers
	 * window on days, and a volunteer needs to know what time to be there.
	 */
	planned_start: string | null;
	planned_end: string | null;
	briefing_on: string | null;
	check_in_deadline: string | null;
	expected_return: string | null;
	actual_start: string | null;
	actual_end: string | null;
	/**
	 * When the paperwork was filed, or null while it has not been. The date a
	 * closed mission file is filed under — distinct from `end_date`, which dates
	 * the work rather than the file.
	 */
	closed_out_on: string | null;
	volunteers_required: number;
	email_template: string | null;
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
	/**
	 * Their photograph, or null — read alongside the name by
	 * `assignment.volunteer_photo`, from the same Red Profile the name comes
	 * from. Null is ordinary and every surface draws initials for it.
	 */
	photo: string | null;
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
	/** Whether this society routes terms for approval at all. */
	is_governed: boolean;
	/**
	 * One of the seven exact states in `approvals/states.py`, or `null` on a
	 * site that routes nothing. Read straight off the field rather than through
	 * the engine's default, because "nobody has been asked" and "it is a draft
	 * awaiting an approver" are different answers and only the first is true
	 * there. Displayed and compared against the closed set — never against a
	 * stage label, which is a society's own wording.
	 */
	approval_state: string | null;
	amended_from: string | null;
	/** The terms this one replaces mid-mission. See `terms.supersede`. */
	supersedes: string | null;
	/** What still has to be written before the wording can be frozen. */
	missing: string[];
	has_no_resources: boolean;
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

export interface TermsCertificationRequirement {
	certification_type: string | null;
	is_mandatory: boolean;
	requirement_notes: string | null;
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
	certification_requirements: TermsCertificationRequirement[];
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
	/**
	 * False when the caller cannot read the volunteer register at all — they
	 * hold the deployment scope role but not the volunteer one. Distinguishes
	 * "nobody fits" from "you were never shown the register".
	 */
	register_readable: boolean;
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
	/** Why the branch is asking. The substance of the request, not a note on it. */
	justification: string | null;
	/**
	 * Whether volunteers can see this ask. An approved, unpublished request has
	 * nobody applying to it and looks identical to one nobody wants, so the flag
	 * is on the row rather than left to be inferred.
	 */
	is_published: boolean;
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
	} | null;
}

/** `deployment/services/participation.py::history_of` — one deployment served. */
export interface DeploymentHistoryRow {
	deployment: string;
	status: string | null;
	/**
	 * Whether the deployment itself is over — Completed, Closed Out or
	 * Cancelled. Derived by the module that owns what a status means, so a card
	 * counting completed deployments and a register filtering "past" cannot
	 * hold two answers to the same question.
	 */
	is_settled: boolean;
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
	/** `api/person.py::registers`. See `Registers` for what absent means. */
	registers: Registers;
}

/**
 * Which of the society's registers one person appears in — `api/person.py`.
 *
 * Composed above both satellites, because neither module may know the other
 * exists. A `null` under either key means the person is not in that register
 * *or* that their record there is outside this caller's scope, and the server
 * deliberately does not distinguish the two: a screen must render both as
 * nothing rather than as a failure.
 */
export interface RegisterEntry {
	kind: string;
	label: string;
	name: string;
	/** The register's own status word. Display only, never compared across registers. */
	status: string | null;
	joined_on: string | null;
}

export type Registers = Partial<Record<"volunteer" | "member", RegisterEntry | null>>;

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
	country_of_citizenship: string | null;
	citizenship_status: string | null;
	residency_type: "Local" | "Abroad" | null;
	home_geo_node: string | null;
	home_geo_path: string | null;
	country_of_residence: string | null;
	residence_address: string | null;
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
	/** `api/person.py::registers`. See `Registers` for what absent means. */
	registers: Registers;
}

/**
 * `member/services/review.py::decision_dto` — the membership half of a review.
 *
 * The counterpart of `ApplicationDecision`, and the reason a membership in the
 * review queue can now be read at all: before this existed the queue showed a
 * docname and two buttons, and an approver had no way to see whose membership
 * they were deciding.
 *
 * **There is no intake block, deliberately.** `VMMS Membership` carries
 * `applicant_first_name` and its neighbours, and they are blanked on every save
 * by `intake.clear_intake` once absorbed into the Red Profile — a transport into
 * identity, not a record. One answer to who somebody is, and it is `applicant`.
 */
export interface MembershipReview {
	name: string;
	member: string;
	as_of: string;
	applicant: MemberIdentity | null;
	membership: MembershipDossierRow;
	/** The attachment a proof-of-payment membership stands on, if there is one. */
	proof_attachment: string | null;
	membership_source: string | null;
	answers: SocietyAnswer[];
}

/* -------------------------------------------------------- notifications */

/**
 * One row of `notifications/services/delivery.py::feed`, which merges a
 * branch's own announcements with Frappe's `Notification Log`. The screen and
 * the header dropdown never branch on `source` — it travels back with `id`
 * when marking one read, and the pair is opaque to the frontend.
 */
export interface NotificationRow {
	id: string;
	source: string;
	title: string;
	summary: string;
	body: string;
	/** The closed set the server owns — `urgent`, `important`, or routine. */
	urgency: string;
	rank: number;
	/** The announcement's own type, a society's word. Display only, never styled. */
	label: string;
	geo_node: string;
	sent_on: string;
	read: boolean;
	link_label: string;
	/** Server-validated on save: site-relative, or http/https/mailto/tel. */
	href: string;
}

/* -------------------------------------------------------- communication */

/** `api/communication.py::options` — what this person may compose and send. */
export interface CommunicationOptions {
	audiences: string[];
	urgencies: string[];
	types: Array<{ name: string; description: string | null }>;
	/**
	 * Per caller, not per site: SMS needs onerc_sms installed *and* this
	 * person's own permission on it, so a coordinator without the role sees two
	 * channels rather than a third that would refuse them. WhatsApp is the same
	 * shape — it needs a gateway the society has stood up and linked to a phone.
	 */
	channels: { notification: boolean; email: boolean; sms: boolean; whatsapp: boolean };
	sms_templates: Array<{ name: string; template_name: string; category: string | null; message: string }>;
	sms_source_doctypes: Array<{ value: string; label: string }>;
	can_send: boolean;
}

/**
 * `api/communication.py::preview` — how far this would reach, per channel.
 *
 * Four different numbers from one audience, because the people with a login,
 * the people with an address and the people with a phone number are overlapping
 * sets. `addressed` is the denominator that makes a low reach read as a data gap
 * rather than as a small branch.
 *
 * `whatsapp` is the one figure that can be lower than `sms` without anything
 * being missing: it excludes everybody who replied STOP, and that gap is the
 * channel working rather than failing.
 */
export interface CommunicationReach {
	geo_node: string;
	audience: string;
	addressed: number;
	notification: number;
	email: number;
	sms: number;
	whatsapp: number;
}

/** `api/communication.py::send` — what each channel actually did. */
export interface CommunicationReport {
	announcement: {
		announcement: string;
		addressed: number;
		delivered: number;
		created: number;
	} | null;
	notification_sent?: boolean;
	email_sent?: boolean;
	/** Filed, never sent: onerc_sms's own approval workflow releases it. */
	sms: {
		campaign: string;
		recipients: number;
		malformed: number;
		addressed: number;
		url: string;
	} | null;
	/**
	 * Filed, never sent. Approving it is submitting the broadcast on the desk,
	 * and a worker then paces it out over minutes or hours rather than sending
	 * it in a burst.
	 */
	whatsapp: {
		broadcast: string;
		recipients: number;
		addressed: number;
		url: string;
	} | null;
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
	/** Groups already in use anywhere on the site, to offer rather than retype. */
	groups: string[];
	can_edit: boolean;
}

/** One question as the builder draws it, from `api/questions.py::_row`. */
export interface BuilderQuestion {
	name: string;
	asked_on: string;
	label: string;
	/** The tab this question is drawn under. Empty means "with the rest". */
	group: string;
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

/* ------------------------------------------------- people, in the aggregate */

/**
 * `api/people.py::summary` — the People overview's figures, in one scoped read.
 *
 * **Nothing here is a page's length.** Each figure is counted across the whole
 * of the caller's scope by the server; the screen that shows them may not
 * compute a total from a list it happens to hold, and the two fields that
 * cannot be computed affordably come back as `null` rather than as a number
 * from a truncated read. See `PeopleReach.capped`.
 */
export interface PeopleSummary {
	/** Keyed by governed doctype. What is routed to *this user* right now. */
	queue: Record<string, { waiting: number; overdue: number }>;
	intake: IntakeHealth[];
	registers: RegisterCount[];
	people: PeopleReach;
}

/** One door into the society, and what is stuck in it. */
export interface IntakeHealth {
	/** `volunteers` or `members` — the word the console already routes on. */
	kind: string;
	doctype: string;
	/**
	 * Whether this caller may read the register behind this door at all.
	 *
	 * Kept apart from `governed` because they are two different silences and a
	 * screen has to say the right one: a door with no workflow behind it and a
	 * door that is not yours to see both come back with `null` figures, and
	 * telling a membership clerk that volunteer applications are "not
	 * configured" is simply wrong.
	 */
	readable: boolean;
	/**
	 * False where no approval workflow governs this doctype yet — or where the
	 * caller cannot read it, in which case `readable` is what says so. The
	 * numbers are `null` either way rather than zero, because "nothing to do"
	 * is a claim neither case supports.
	 */
	governed: boolean;
	/** In the caller's whole scope, not only their own assignments. */
	in_review: number | null;
	/** Draft, *and* somebody recorded a "More info requested" decision on it. */
	changes_requested: number | null;
	/** Routed to this user, from the same `my_queue` the queue screen renders. */
	waiting: number;
	/** Of those, how many are past their stage's configured SLA. */
	overdue: number;
	/** Everything in scope past its SLA, whoever it is routed to. */
	breached: number | null;
}

export interface RegisterCount {
	kind: string;
	doctype: string;
	/** Whether this caller may read the register at all. See `IntakeHealth`. */
	readable: boolean;
	/**
	 * `null` where this caller may not read the register at all — a membership
	 * clerk with no volunteer permissions, say. Not being allowed to know is
	 * indistinguishable, on a screen, from there being nothing to know, so it is
	 * drawn as a dash rather than as a zero.
	 */
	active: number | null;
}

/**
 * The two registers counted as *people* rather than as records.
 *
 * A person with memberships at two branches is two rows and one human being.
 * `capped` is true when the read hit its ceiling and every figure here is
 * `null`: a screen must then omit the block rather than show a number derived
 * from a truncated read.
 */
export interface PeopleReach {
	unique: number | null;
	both: number | null;
	volunteers: number | null;
	members: number | null;
	capped: boolean;
}

/** `api/approvals.py::my_cases` — one band of a queue. */
export interface ApprovalCases {
	group: string;
	count: number;
	cases: ApprovalStatus[];
}

/** `api/volunteer.py::register_summary`. */
export interface VolunteerRegisterSummary {
	active: number;
	joined_month: number;
	/** `null` past the read ceiling — see `PeopleReach.capped` for the rule. */
	branches: number | null;
	/**
	 * How many of them are out on an active deployment, and on how many. Both
	 * `null` where this caller may not read deployments: a zero would say
	 * "nobody is deployed", which is a different and false claim.
	 */
	deployed: number | null;
	deployments: number | null;
	capped: boolean;
}

/**
 * `api/member.py::register_summary`.
 *
 * `lifetime` and `term` are split on `VMMS Membership Type.is_lifetime`, never
 * on a type's name: a society names its own types and "Annual" is one society's
 * word.
 */
export interface MemberRegisterSummary {
	as_of: string;
	active: number;
	lifetime: number;
	term: number;
	/** Term memberships falling due inside `renewal_window_days`. */
	renewing: number;
	renewal_window_days: number;
	capped: boolean;
}

/* ------------------------------------------------------ operations, in full */

/**
 * `api/deployment.py::operations_summary` — the command centre's figures.
 *
 * Counted across the whole scoped register rather than across one page of it,
 * which is the difference between a dashboard and a sample. `capped` says the
 * read hit its ceiling and the figures are a floor.
 */
export interface OperationsSummary {
	as_of: string;
	ongoing: number;
	/** Keyed by deployment status. Never indexed by a literal in a component. */
	by_status: Record<string, number>;
	people: number;
	starting_soon: number;
	starting_soon_days: number;
	unfilled_soon: number;
	pending: number;
	closing_out: number;
	/**
	 * Requests and terms are `null` where this caller may not read that register
	 * at all — a coordinator who runs deployments and cannot see requests. A zero
	 * would say "there are none", which is a different and false claim.
	 */
	requests: number | null;
	requests_open: number | null;
	terms: number | null;
	terms_awaiting: number | null;
	capped: boolean;
}

/** One place a deployment has, with the two links that open it — `geocoding.dto`. */
export interface DeploymentPlace {
	name: string | null;
	address: string | null;
	latitude: number | null;
	longitude: number | null;
	/** False where nobody has located it yet. The screen says so rather than guessing. */
	has_point: boolean;
	located_on: string | null;
	map: string | null;
	directions: string | null;
}

/** `deployment/services/deployment.py::where_dto`. */
export interface DeploymentWhere {
	site: DeploymentPlace;
	meeting_point: DeploymentPlace;
	travel_notes: string | null;
	local_contact: { name: string | null; phone: string | null };
}

/** `deployment/services/deployment.py::coordinator_dto`. */
export interface CoordinatorContact {
	user: string | null;
	full_name: string;
	email: string;
	phone: string;
}

/** `assignment.readiness_for_many` — how ready one roster is. */
export interface DeploymentReadiness {
	briefed: number;
	safety: number;
	checked_in: number;
	leaders: number;
}

/** One selectable deployment on the operations map — `api/deployment.py::_site_row`. */
export interface DeploymentSite extends DeploymentSummary {
	where: DeploymentWhere;
	coordinator_contact: CoordinatorContact;
	readiness: DeploymentReadiness;
}

/** `api/deployment.py::deployment_sites`. */
export interface DeploymentSites {
	deployments: DeploymentSite[];
	count: number;
	plotted: number;
	/** How many carry no coordinates, so the screen says so rather than drawing fewer pins. */
	unplotted: number;
	capped: boolean;
}

/** One file in the operations register — `api/deployment.py::operations_documents`. */
export interface OperationsFile {
	name: string;
	file_name: string;
	file_url: string;
	file_size: number | null;
	is_private: boolean | number;
	attached_to_doctype: string;
	attached_to_name: string;
	owner: string;
	creation: string;
	modified: string;
}

/** A record an upload may be attached to. Returned by the server, never guessed. */
export interface DocumentTarget {
	doctype: string;
	name: string;
}

export interface OperationsDocumentsAnswer {
	count: number;
	files: OperationsFile[];
	targets: DocumentTarget[];
	record_types: string[];
}
