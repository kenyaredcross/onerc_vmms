/**
 * Every whitelisted method this frontend calls, named once.
 *
 * A string literal scattered through components is a rename waiting to break a
 * screen nobody opened during testing. Collecting them here also makes the
 * app's real dependency on the backend readable in one file: if a method is not
 * in this list, no page calls it.
 *
 * Each entry is verified against the Python source. Where a screen has no
 * method to call, there is no entry and the screen says so on the page rather
 * than inventing one. See `NotBuilt` in `ui/primitives.tsx`.
 */
export const API = {
	// onerc_core/api/article.py — stories and news, and they are *core's*.
	// Called directly rather than proxied through a vmmsx endpoint, because
	// wrapping them would be this app holding a second answer to what an article
	// is. The same reason nothing here re-implements geo or Red Profile. Core
	// already serves these to guests, which is what the landing page needs.
	articles: "onerc_core.api.article.get_articles",
	article: "onerc_core.api.article.get_article",
	articleCategories: "onerc_core.api.article.get_categories",

	// vmmsx/api/society.py — the society's own name and logo, for the lockup.
	// Guest-readable, like `contentSurface`, because the landing page carries it.
	societyBranding: "vmmsx.api.society.branding",
	// The numbers the landing page's statistics strip used to have typed into it.
	// Guest-readable and already rounded: the endpoint decides how approximate a
	// public figure is, so no screen can publish an exact headcount by accident.
	societyFigures: "vmmsx.api.society.figures",

	// vmmsx/api/content.py
	contentSurface: "vmmsx.api.content.surface",
	contentCatalogue: "vmmsx.api.content.catalogue",
	contentUpdate: "vmmsx.api.content.update_block",

	// vmmsx/api/registration.py — the self-service door, and the only one this
	// app may use. Every method here is possessive: none takes a person, so a
	// caller cannot register or claim anybody but themselves.
	// `apply_to_volunteer` / `apply_for_membership` are the *clerk's* door, name
	// a red_profile and check create permission. They are deliberately absent
	// from this file: no screen here acts on somebody else's behalf.
	myProfile: "vmmsx.api.registration.my_profile",
	// The one endpoint here that overwrites rather than adds, and it is named for
	// it. Registering can never rewrite what the society already holds; a person
	// looking at their own details and correcting them is a different act, and
	// this is the only door to it. The email is not a parameter: it is the login.
	updateMyProfile: "vmmsx.api.registration.update_my_profile",
	identityOptions: "vmmsx.api.registration.identity_options",
	// What the caller has open, one answer per kind of registration. The wizard
	// reads it before drawing a step, so "you have already applied" is said on
	// arrival rather than discovered on submit — and per kind, because an
	// undecided volunteer application is not a reason to refuse a membership.
	myOpenRegistrations: "vmmsx.api.registration.my_open_registrations",
	// The editable body of the caller's one open registration, and the three
	// explicit applicant actions around it. Draft writes are possessive and stay
	// out of every approver queue until `submitMyRegistration` is called.
	myRegistration: "vmmsx.api.registration.my_registration",
	saveMyVolunteerDraft: "vmmsx.api.registration.save_my_volunteer_draft",
	saveMyMemberDraft: "vmmsx.api.registration.save_my_member_draft",
	submitMyRegistration: "vmmsx.api.registration.submit_my_registration",
	registerAsVolunteer: "vmmsx.api.registration.register_as_volunteer",
	registerAsMember: "vmmsx.api.registration.register_as_member",

	// vmmsx/api/volunteer.py
	applicationOptions: "vmmsx.api.volunteer.application_options",
	// When the caller can serve, and the society's own windows to draw the grid
	// from. Possessive like every `my*` endpoint: the volunteer comes from the
	// session and there is no argument naming anybody else, which is what admits
	// the elevated save on a record a volunteer holds no permission over.
	// Distinct from the availability *slots* a volunteer picks at intake: those
	// are a self-description a coordinator can search on, this is a claim about
	// days that a deployment's own dates can be tested against.
	myAvailability: "vmmsx.api.volunteer.my_availability",
	setMyAvailability: "vmmsx.api.volunteer.set_my_availability",
	// The whole of what an approver reads before deciding: identity, placement,
	// what was declared, the identification the application required, and the
	// society's own questions. Ordinary read permission on the application, so
	// this is not a second door into one.
	applicationDecision: "vmmsx.api.volunteer.get_decision",

	// vmmsx/api/cards.py — possessive like the rest: neither takes a person, so
	// neither can be pointed at anybody else's card. `verify` is deliberately
	// absent from this list and called by name in `guest/Verify.tsx`, because it
	// is the one endpoint here a signed-out stranger reaches.
	myVolunteerCard: "vmmsx.api.cards.my_volunteer_card",
	myMemberCard: "vmmsx.api.cards.my_member_card",
	volunteerGeoLevels: "vmmsx.api.volunteer.geo_node_levels",
	myVolunteer: "vmmsx.api.volunteer.my_volunteer",
	myCertifications: "vmmsx.api.volunteer.my_certifications",
	// The read half of `logTime`, and possessive like the rest: it takes no
	// person, so the hours screen cannot be pointed at anybody else's history.
	myTimeLogs: "vmmsx.api.volunteer.my_time_logs",
	timeLogOptions: "vmmsx.api.volunteer.time_log_options",
	logTime: "vmmsx.api.volunteer.log_time",
	findVolunteers: "vmmsx.api.volunteer.find_volunteers",
	volunteerDossier: "vmmsx.api.volunteer.get_dossier",
	// Where one volunteer has served. The coordinator's endpoint: it checks read
	// on the volunteer and then filters the deployments through core's scoping,
	// so a volunteer calling it about themselves would get nothing — they have
	// `myDeployments` instead. Fetched lazily by the candidate hover card, one
	// volunteer at a time, rather than fattening every row of a search that was
	// deliberately made cheap.
	deploymentsOfVolunteer: "vmmsx.api.deployment.deployments_of_volunteer",
	// The coordinator's acts over a volunteer's standing. `status` is derived and
	// read-only on the doctype, so these endpoints are the only way to move it —
	// there is no field to write. Each is gated on `write`, which is *not* the
	// gate the dossier read uses: a volunteer may open their own record and may
	// not suspend themselves. `can_act` on the dossier says which case a caller
	// is in, and the server re-asks on every one of these regardless.
	suspendVolunteer: "vmmsx.api.volunteer.suspend_volunteer",
	reinstateVolunteer: "vmmsx.api.volunteer.reinstate_volunteer",
	recordVolunteerExit: "vmmsx.api.volunteer.record_volunteer_exit",

	// vmmsx/api/member.py
	myMemberships: "vmmsx.api.member.my_memberships",
	renewMembership: "vmmsx.api.member.renew_membership",
	membershipTypes: "vmmsx.api.member.membership_types",
	memberGeoLevels: "vmmsx.api.member.geo_node_levels",
	findMembers: "vmmsx.api.member.find_members",
	memberDossier: "vmmsx.api.member.get_dossier",
	// The membership half of a review, and the counterpart of
	// `applicationDecision` above. Its absence is why a membership reached the
	// queue as a docname with two buttons under it: there was no endpoint that
	// would say whose membership an approver was being asked to decide.
	membershipReview: "vmmsx.api.member.get_review",
	// The membership half of the same acts. Cancel ends one early and records
	// why; expire closes one whose validity has already run out and is refused
	// on anything still current, so the two are not interchangeable.
	cancelMembership: "vmmsx.api.member.cancel_membership",
	expireMembership: "vmmsx.api.member.expire_membership",

	// vmmsx/api/person.py
	//
	// Which of the society's registers one person is in, resolved through the
	// Red Profile both hang off. The dossiers carry this block already; this
	// endpoint is for the review queue, which holds an applicant rather than a
	// dossier. A register the caller may not read comes back as `null`,
	// indistinguishable from the person not being in it — deliberately, so a
	// missing permission costs a chip rather than the page.
	personRegisters: "vmmsx.api.person.get_registers",

	// vmmsx/api/approvals.py
	myQueue: "vmmsx.api.approvals.my_queue",
	approvalStatus: "vmmsx.api.approvals.get_status",
	decide: "vmmsx.api.approvals.decide",
	withdraw: "vmmsx.api.approvals.withdraw",

	// vmmsx/api/communication.py — addressing a branch's own people, on three
	// channels resolved from one audience. `preview` exists because a broadcast
	// is the one act in this product that cannot be undone: the number of people
	// it will reach is something to read before pressing send, not after. `send`
	// publishes one announcement for the in-app and email channels and files a
	// *draft* SMS campaign for onerc_sms's own approval workflow to release — the
	// console never dispatches an SMS itself.
	communicationOptions: "vmmsx.api.communication.options",
	communicationReach: "vmmsx.api.communication.preview",
	communicationSend: "vmmsx.api.communication.send",
	smsDoctypeFields: "onerc_sms.api.campaign.get_doctype_fields",
	smsFilterFields: "onerc_sms.api.campaign.get_filter_fields",

	// vmmsx/api/geo.py — `ladder` is how many select fields a placement form
	// draws, `browse` is what goes in each of them. Neither this file nor any
	// screen knows how deep a society's hierarchy is or what it calls a rung.
	geoLadder: "vmmsx.api.geo.ladder",
	geoBrowse: "vmmsx.api.geo.browse",
	// One node with its whole ancestry, root first — what restores a cascading
	// picker that already has an answer. The join wizard opens its placement step
	// with this, so somebody registering a second time is not asked to walk back
	// down to the branch they already gave the society.
	geoChain: "vmmsx.api.geo.path",

	// vmmsx/api/deployment.py — the possessive one. `deployments_of_volunteer`
	// is the coordinator's: it checks read on the volunteer and then geo-scopes
	// the deployments, both of which fail closed for somebody holding no Geo
	// Assignment, which every volunteer correctly is. No screen here calls it.
	myDeployments: "vmmsx.api.deployment.my_deployments",
	// Invitations. `myInvitations` is possessive like the line above it;
	// `respondToInvitation` names a deployment and is the one endpoint in that
	// pair that has to check something, so it checks ownership of the roster row
	// rather than geo scope, which every volunteer would fail. `inviteVolunteer`
	// is the coordinator's half and is gated on write permission.
	myInvitations: "vmmsx.api.deployment.my_invitations",
	// Answering names an **assignment**, not a deployment, because the roster is
	// a register of `VMMS Deployment Assignment` documents now — one per person,
	// with its own URL, and carrying the exact submitted terms of reference that
	// person was shown. Accepting is accepting those terms: there is no separate
	// contract in this app, which is why the terms are submittable and why
	// `getMyAssignment` hands the whole mission document to whoever is deciding.
	getMyAssignment: "vmmsx.api.deployment.get_my_assignment",
	respondToAssignment: "vmmsx.api.deployment.respond_to_assignment",
	inviteVolunteer: "vmmsx.api.deployment.invite_volunteer",
	// The bulk act. One call, one savepoint per person on the server, and a
	// `{success, failure}` report naming who did not take and why — because some
	// will fail (already assigned, deployment full, terms retired since) and a
	// screen that refused the batch or dropped them silently would be worse than
	// one that says so. `ask` is the fork between this app's two verbs and is
	// deliberately not merged: on, each person is asked; off, each is placed.
	assignVolunteers: "vmmsx.api.deployment.assign_volunteers",
	setAssignmentRole: "vmmsx.api.deployment.set_assignment_role",
	withdrawAssignment: "vmmsx.api.deployment.withdraw_assignment",
	// The manager's console. Both listings are `frappe.get_list`, so the
	// caller's Geo Assignment is the floor the answer stands on and no argument
	// on the screen widens it. A coordinator holding no assignment sees an empty
	// console, which is the honest answer rather than an error.
	branchDeployments: "vmmsx.api.deployment.branch_deployments",
	branchRequests: "vmmsx.api.deployment.branch_requests",
	getDeployment: "vmmsx.api.deployment.get_deployment",
	setDeploymentStatus: "vmmsx.api.deployment.set_deployment_status",
	addParticipant: "vmmsx.api.deployment.add_participant",
	// The deployment's own account of itself: its updates merged at read time
	// with the task reports written against tasks linked to it. Merged rather
	// than copied, so there is one record of each report and it stays with the
	// task it belongs to. Reading needs read; posting needs write, because a
	// feed anybody who could open the deployment could write to would not be a
	// record of anything.
	// Where this coordinator's people are, by area, with a point where the geo
	// tree carries one. Every area comes back whether or not it can be plotted,
	// and `unplotted` counts the ones that cannot — a tree is filled in from the
	// top down over months, and a map that silently omitted them would
	// under-report exactly where the gaps are.
	deploymentMap: "vmmsx.api.deployment.deployment_map",
	getDeploymentFeed: "vmmsx.api.deployment.get_deployment_feed",
	postDeploymentUpdate: "vmmsx.api.deployment.post_deployment_update",
	// Matching. `findCandidatesForRequest` is the same question asked of a
	// document that already carries the need, so the screen does not take the
	// terms and the date apart by hand.
	findCandidates: "vmmsx.api.deployment.find_candidates",
	findCandidatesForRequest: "vmmsx.api.deployment.find_candidates_for_request",
	requestDeployment: "vmmsx.api.deployment.request_deployment",
	// The paperwork a deployment stands on: a programme of work, a specification
	// written under it, and then the deployment. Every listing is `get_list`, so
	// the same geo floor holds, and `mine` on each one narrows further to what
	// this person filed. It can only narrow — the owner filter is applied on top
	// of a result the permission layer has already bounded.
	createProject: "vmmsx.api.deployment.create_project",
	branchProjects: "vmmsx.api.deployment.branch_projects",
	setProjectStatus: "vmmsx.api.deployment.set_project_status",
	// One project in full: its own fields, the terms of reference written under
	// it, and the deployments run under those — composed server-side, the same
	// reason `getTerms` composes its own document and roster.
	getProject: "vmmsx.api.deployment.get_project",
	createTerms: "vmmsx.api.deployment.create_terms",
	branchTerms: "vmmsx.api.deployment.branch_terms",
	// `getTerms` returns the reviewed field list, the society's own template
	// rendered against it, and the deployments run under it, so what a
	// coordinator reads on the screen is the same markup the PDF is made from
	// and cannot drift apart from either.
	getTerms: "vmmsx.api.deployment.get_terms",
	// Editing and freezing a mission. A terms of reference is written over
	// several sittings and then **submitted**, which is the deliberate act that
	// says the wording is final and people may now be asked to agree to it.
	// `updateTerms` refuses a submitted one, in words that say why; amending is
	// a new document, so what somebody already agreed to is never rewritten.
	updateTerms: "vmmsx.api.deployment.update_terms",
	submitTerms: "vmmsx.api.deployment.submit_terms",
	torMethodologies: "vmmsx.api.deployment.tor_methodologies",
	createDeployment: "vmmsx.api.deployment.create_deployment",

	// vmmsx/api/tasks.py — two doors into one doctype, checked differently.
	// Everything under `my` is the volunteer's and is checked by ownership: the
	// task has to be assigned to the caller's own volunteer record. The rest is
	// the coordinator's and is checked by write permission, which brings core's
	// geo scoping with it. No screen decides which door it is using; each one
	// calls the endpoint for the person it is drawn for, and the server re-asks.
	myTasks: "vmmsx.api.tasks.my_tasks",
	acceptTask: "vmmsx.api.tasks.accept_task",
	askAboutTask: "vmmsx.api.tasks.ask_about_task",
	reportTaskProgress: "vmmsx.api.tasks.report_progress",
	submitTask: "vmmsx.api.tasks.submit_task",
	branchTasks: "vmmsx.api.tasks.branch_tasks",
	getTask: "vmmsx.api.tasks.get_task",
	assignTask: "vmmsx.api.tasks.assign_task",
	answerTaskQuestion: "vmmsx.api.tasks.answer_question",
	requestTaskProgress: "vmmsx.api.tasks.request_progress",
	signOffTask: "vmmsx.api.tasks.sign_off",
	sendTaskBack: "vmmsx.api.tasks.send_back",
	cancelTask: "vmmsx.api.tasks.cancel_task",

	// vmmsx/api/stipend.py — the paperwork console. One listing over both
	// doctypes, because "what is in my area" is the same question asked twice.
	//
	// `stipendDecide` is named here and the screen calls it, but it always
	// refuses: departmental routing does not exist, so nobody can approve this
	// paperwork yet. That refusal travels in the payload as `can_be_decided:
	// false` with the sentence explaining it, and the screen draws what the
	// server said rather than hiding a button and inventing its own reason.
	branchPaperwork: "vmmsx.api.stipend.branch_paperwork",
	createStipendReport: "vmmsx.api.stipend.create_report",
	createPaymentForm: "vmmsx.api.stipend.create_payment_form",
	getStipendReport: "vmmsx.api.stipend.get_report",
	getPaymentForm: "vmmsx.api.stipend.get_payment_form",
	addVolunteerToReport: "vmmsx.api.stipend.add_volunteer_to_report",
	removeVolunteerFromReport: "vmmsx.api.stipend.remove_volunteer_from_report",
	recordAttendance: "vmmsx.api.stipend.record_attendance",
	findStipendVolunteers: "vmmsx.api.stipend.find_volunteers",
	submitStipendForApproval: "vmmsx.api.stipend.submit_for_approval",
	withdrawStipend: "vmmsx.api.stipend.withdraw",

	// vmmsx/api/analytics.py — one method, and it takes no scope. Every figure is
	// counted through the doctype's own registered role, so a coordinator holding
	// one and not another sees real numbers beside honest zeroes rather than a
	// refusal of the whole screen.
	branchSummary: "vmmsx.api.analytics.branch_summary",

	// vmmsx/api/console.py — which sections of the manager console this person
	// may open. Takes no arguments and names no role: the answer is about the
	// session and nothing else, and the keys it returns are this app's vocabulary
	// rather than a society's. Drawing a tab from it is a convenience — every
	// screen behind one re-asks the permission layer on its own.
	consoleSections: "vmmsx.api.console.sections",

	// vmmsx/api/locations.py — where the society can be found. `publishedLocations`
	// is this app's third guest-readable method, after `contentSurface` and
	// `societyBranding`, and the boundary is `is_published` on each location and
	// nothing else. `branchLocations` is the coordinator's, geo-scoped, and carries
	// the internal notes the public one does not have.
	publishedLocations: "vmmsx.api.locations.published",
	branchLocations: "vmmsx.api.locations.branch_locations",

	// vmmsx/api/opportunities.py — the notice board, and browsing only. There is
	// no method here to answer an advertisement because this app has no record of
	// a volunteer answering one: a coordinator matches people to a need and adds
	// them to a roster. The screen says so rather than drawing a button.
	opportunitiesBrowse: "vmmsx.api.opportunities.browse",
	opportunityFilters: "vmmsx.api.opportunities.filters",
	// One advertisement in full. Re-asks the board's own three predicates, so a
	// guessed docname and an unpublished need both answer with nothing.
	opportunityDetail: "vmmsx.api.opportunities.detail",

	// vmmsx/api/events.py — browsing only. Buzz owns registration, tickets,
	// payment and check-in, so a card's call to action is a full navigation to
	// Buzz's own page and there is deliberately no booking method to name here.
	eventsUpcoming: "vmmsx.api.events.upcoming",
	eventFilters: "vmmsx.api.events.filters",
	// Three events for the public landing page, and the only guest-readable call
	// in this group. It is a teaser rather than the calendar — no search, no
	// filters, no paging — and every row is already published by Buzz to the
	// world. Everything else here still refuses a signed-out visitor.
	eventsTeaser: "vmmsx.api.events.teaser",
	// One event in full, behind the same `is_published` boundary as the listing.
	// Booking is still a navigation to Buzz; this screen only has more room for
	// the same call to action.
	eventDetail: "vmmsx.api.events.detail",
	// Saying you mean to be there, and it is not the same thing as a ticket.
	// These write the society's own record of an intention, which is what a
	// coordinator plans around; they hold no seat and take no money, and no
	// screen calling them may say otherwise. Possessive like the `my_*` methods
	// above: none takes a person, so none can answer on somebody's behalf.
	eventsAttending: "vmmsx.api.events.attending",
	attendEvent: "vmmsx.api.events.attend",
	cancelEventAttendance: "vmmsx.api.events.cancel_attendance",
	// The month grid's one read. Everything published in a window, plus which of
	// it is the caller's, in a single answer — a day cannot be drawn correctly
	// until both are known, and two requests would mean markings that appear
	// after the calendar has rendered.
	eventsCalendar: "vmmsx.api.events.calendar",

	// vmmsx/api/notifications.py — possessive, like the member and volunteer
	// endpoints above. None of them takes a person, so no screen can ask for
	// somebody else's notifications. Sending is absent on purpose: an
	// announcement is written on the desk, where the geo scope role decides who
	// may speak for a branch.
	myNotifications: "vmmsx.api.notifications.my_notifications",
	unreadCount: "vmmsx.api.notifications.unread_count",
	markNotificationRead: "vmmsx.api.notifications.mark_read",
	markAllNotificationsRead: "vmmsx.api.notifications.mark_all_read",

	// vmmsx/api/companions.py — which of the neighbouring apps are installed on
	// this site and where they are mounted. The sidebar draws what this returns
	// and decides nothing: a tab missing from the answer is an app that is not
	// installed or not open to this person, and either way there is nowhere for
	// the tab to lead.
	companionApps: "vmmsx.api.companions.available",

	// vmmsx/api/questions.py — the form builder. Every method is gated on write
	// permission for `VMMS Application Question`, which no configurable scope
	// role is granted, so these resolve to the administrator until a society
	// deliberately widens them. No role name appears here or on the screen: the
	// tab is drawn from `console.sections` like every other one, and `can_edit`
	// on each answer decides the controls.
	//
	// There is deliberately no delete: a question is retired with
	// `setQuestionActive`, because every answer already given was part of an
	// application somebody decided.
	questionTargets: "vmmsx.api.questions.targets",
	questionCatalogue: "vmmsx.api.questions.catalogue",
	saveQuestion: "vmmsx.api.questions.save_question",
	setQuestionActive: "vmmsx.api.questions.set_question_active",
	reorderQuestions: "vmmsx.api.questions.reorder_questions",
} as const;

/** The download endpoint is a file response, so it is a URL rather than a call. */
export const myCertificateUrl = (membership: string): string =>
	`/api/method/vmmsx.api.member.download_my_certificate?membership=${encodeURIComponent(membership)}`;

/**
 * The coordinator's companions to the two above, for reprinting somebody's
 * certificate or card at a counter.
 *
 * URLs for the same reason: both are file responses rather than JSON. Each
 * endpoint checks `read` on the record named, which is core's geo scoping as
 * well as Frappe's roles, so a link built here for a record outside the
 * caller's scope is refused by the server rather than by this file.
 */
export const certificateUrl = (membership: string): string =>
	`/api/method/vmmsx.api.member.download_certificate?membership=${encodeURIComponent(membership)}`;

export const cardUrl = (kind: "volunteer" | "member", name: string): string =>
	`/api/method/vmmsx.api.cards.download_card?kind=${kind}&name=${encodeURIComponent(name)}`;

/**
 * The printed terms of reference, on the society's own letterhead. A URL for the
 * same reason the certificate is one: it is a file response rather than JSON.
 * The endpoint checks read permission on the terms, which is the same check that
 * let the screen show them in the first place.
 */
export const termsPdfUrl = (name: string): string =>
	`/api/method/vmmsx.api.deployment.download_terms?name=${encodeURIComponent(name)}`;

/**
 * The one place a server failure is turned into something a person may read.
 *
 * **Nobody outside this file gets to decide that.** Every screen in the portal
 * funnels its errors through here, so the rule about what an applicant is
 * allowed to be shown is a rule in one function rather than a habit eighty-five
 * call sites have to keep.
 *
 * **The rule: only sentences somebody wrote for a person survive.** Frappe puts
 * those in `_server_messages` — they are what `frappe.throw` was given, written
 * in this codebase to be read at a counter ("You already have an application
 * with us that has not been decided yet"). Everything else — `exception`, the
 * HTTP status text, the bare `message` a framework built — is machinery. It was
 * being rendered under form fields, four times over, in the wizard a member of
 * the public uses to register:
 *
 *     You are not permitted to access this resource. Login to access
 *     Function vmmsx.api.geo.browse is not whitelisted.
 *
 * That sentence is addressed to whoever wrote the endpoint. The person reading
 * it had come to volunteer.
 *
 * **It is not thrown away, it is moved.** The whole error object goes to
 * `console.error` on the way past, which is where a developer looks for it and
 * where the browser was already carrying the network failure anyway. Nothing is
 * harder to debug than it was; it is just no longer debugged on the page.
 *
 * **A signed-out session is the one machine failure worth naming**, because it
 * is the only one the reader can act on, and "something went wrong" while every
 * control on the page silently fails is worse than being told to sign in again.
 */
export function errorMessage(error: unknown, fallback = "Something went wrong."): string {
	if (!error) return fallback;

	// The developer's copy, always, whatever the reader ends up seeing.
	console.error("[vmms]", error);

	const candidate = error as {
		message?: string;
		exception?: string;
		exc_type?: string;
		_server_messages?: string;
		httpStatus?: number;
		httpStatusText?: string;
	};

	if (isSignedOut(candidate)) {
		return "You have been signed out. Sign in again to carry on.";
	}

	if (candidate._server_messages) {
		try {
			const parsed = JSON.parse(candidate._server_messages) as string[];

			for (const entry of parsed) {
				const text = stripHtml((JSON.parse(entry) as { message?: string })?.message ?? "");
				if (text && !isMachinery(text)) return text;
			}
		} catch {
			// Not the shape we hoped for; the fallback below is the answer.
		}
	}

	return fallback;
}

/**
 * Has the session gone? Frappe says so in several voices, none of them plain.
 *
 * `exc_type` is the reliable one when the framework sets it; the 401/403 status
 * and the "login to access" wording are the same statement arriving from the
 * layers that do not.
 */
function isSignedOut(candidate: {
	exc_type?: string;
	httpStatus?: number;
	message?: string;
	_server_messages?: string;
}): boolean {
	if (candidate.exc_type === "PermissionError" || candidate.exc_type === "AuthenticationError") {
		return true;
	}

	if (candidate.httpStatus === 401 || candidate.httpStatus === 403) return true;

	const said = `${candidate.message ?? ""} ${candidate._server_messages ?? ""}`.toLowerCase();

	return said.includes("login to access") || said.includes("session expired");
}

/**
 * Does this sentence name a part of the machine?
 *
 * A short deny-list rather than a clever one, and it errs towards the generic
 * fallback: showing "Something went wrong" where a human sentence would have
 * done costs a little clarity, and the reverse costs a member of the public an
 * endpoint name under a dropdown.
 */
const MACHINERY = [
	"not whitelisted",
	"traceback",
	"internal server error",
	"<class",
	"frappe.exceptions",
	"vmmsx.api.",
	"onerc_core.",
	"does not exist in the database",
	"integrityerror",
	"operationalerror",
];

function isMachinery(text: string): boolean {
	const lowered = text.toLowerCase();

	return MACHINERY.some((mark) => lowered.includes(mark));
}

function stripHtml(value: string): string {
	return value
		.replace(/<[^>]*>/g, " ")
		.replace(/\s+/g, " ")
		.trim();
}
