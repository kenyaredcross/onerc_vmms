# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Self-Service section of the guide.

Every claim here names the file or function it describes, so a reader can go and
check. Two things are documented that are *limits* rather than features: a
member's desk list of the register stays closed to them, and the other apps on a
bench put their own workspaces in front of a self-registered account. Both are
true, both would otherwise be discovered by somebody at a demo, and a guide that
omitted them would be the kind of prose this app does not ship.
"""

TITLE = "Self-Service"
SUMMARY = "How somebody registers themselves as a volunteer or a member, and what they can see afterwards."

VOLUNTEER_FORM = "Register as a Volunteer"
MEMBERSHIP_FORM = "Register as a Member"


def render(w) -> None:
	w.h1(TITLE)

	_what_it_is(w)
	_the_journey(w)
	_the_web_forms(w)
	_the_two_doctype_write(w)
	_the_intake_fields(w)
	_submission(w)
	_the_role_grant(w)
	_owner_bypass(w)
	_the_workspaces(w)
	_configuration(w)
	_the_seed(w)
	_limits(w)
	_what_is_tested(w)


# --- what it is ------------------------------------------------------------


def _what_it_is(w) -> None:
	w.h2("What the Self-Service layer is")

	w.lead(
		"Everything before this stage assumed somebody at a branch typing a record in. This stage is"
		" the other direction: a person who has never dealt with the society makes an account,"
		" registers themselves as a volunteer or a member, and afterwards can see their own record"
		" without anybody granting them access to anybody else's."
	)
	w.p(
		"It is built entirely out of records Frappe already has. Two native Web Forms, three native"
		" Workspaces, one native User Permission per approved person, and the ordinary role table."
		" There is no portal page, no template, no client bundle and no custom HTML anywhere in this"
		" stage. That is deliberate and it is the reason the layer is small: a society that wants a"
		" different question on the registration form edits a Web Form record, and a society that"
		" wants a different landing surface edits a Workspace."
	)
	w.p(
		"The code is in vmmsx/registration/services/: intake.py (the two-doctype write), roles.py"
		" (granting a configured role), workspaces.py (the three surfaces), permissions.py (what"
		" those surfaces need to be readable) and society.py (the one setting they all read)."
	)


def _the_journey(w) -> None:
	w.h2("The journey, end to end")

	w.steps(
		[
			"A person creates a website account through Frappe's own signup. Portal Settings names"
			" the role a new account is given; the society points it at the same role its landing"
			" workspace names.",
			"They log in and land on the Registration workspace, which offers exactly two things:"
			f" {VOLUNTEER_FORM} and {MEMBERSHIP_FORM}.",
			"They fill in one of the two native Web Forms. On insert, before the framework checks"
			" that the record names a person, vmmsx resolves or creates their Red Profile and links"
			" it. The same save puts the record into motion.",
			"A volunteer application routes to whoever holds the stage's role nearest above the"
			" branch they chose, and waits. A membership either waits for its fee or routes for"
			" approval, depending on the type's approval_mode.",
			"When the application is accepted, or the membership activates, the person's own login"
			" is granted the role the society configured, and a User Permission narrows their desk"
			" to their own record.",
			"They now land on My Volunteering or My Membership, where they can see their own record,"
			" their own applications, and print their own certificate.",
		]
	)

	w.note(
		"Somebody who registers as both keeps one Red Profile, holds both roles and is shown both"
		" surfaces. The Registration workspace stays visible after approval, because registering"
		" for the other affiliation is the same two buttons."
	)


# --- the web forms ---------------------------------------------------------


def _the_web_forms(w) -> None:
	w.h2("The two Web Forms")

	w.p(
		"Both are standard Web Forms, which means they ship as JSON in this app and are synced by"
		" every migrate rather than being typed into a site:"
	)

	w.table(
		("Form", "Target doctype", "Route"),
		[
			[
				VOLUNTEER_FORM,
				"VMMS Volunteer Application",
				"/register-as-a-volunteer",
			],
			[MEMBERSHIP_FORM, "VMMS Membership", "/register-as-a-member"],
		],
		(2.10, 2.45, 2.00),
	)
	w.caption(
		"vmmsx/vmms_volunteer/web_form/register_as_a_volunteer/ and"
		" vmmsx/vmms_member/web_form/register_as_a_member/"
	)

	w.h3("Login required, and not guest")

	w.p(
		"Both set login_required. A registration has to belong to somebody, and the whole two-doctype"
		" write hangs off frappe.session.user: a guest submission would have no login to bind a Red"
		" Profile to, and a form that collected an email address instead would let anybody claim"
		" anybody's identity. So a website account exists first, and the account is the answer to"
		" who this is."
	)

	w.h3("What each one asks for")

	w.bullets(
		[
			"Both: first and last name, phone, gender and date of birth, which go to the Red Profile;"
			" and the branch or area, which is the record's ACC-02 anchor.",
			f"{VOLUNTEER_FORM} additionally: motivation, declared skills, availability and prior"
			" experience. All four are free text, all four are optional, and none is read by code.",
			f"{MEMBERSHIP_FORM} additionally: the membership type, which is what selects the whole"
			" path the registration then takes.",
		]
	)
	w.p(
		"Neither asks for an email address. The login is the site's own answer to who the person is,"
		" and a claim typed into a public form must not be able to overrule it."
	)


def _the_two_doctype_write(w) -> None:
	w.h2("The two-doctype write")

	w.p(
		"A native Web Form writes exactly one document. A registration needs two: core's identity"
		" spine, and the vmmsx record hanging off it. The seam is a server hook, not a page."
	)

	w.p(
		"VMMSVolunteerApplication.before_insert and VMMSMembership.before_insert both call"
		" intake.claim_profile(self). That is the only moment which is both after the form's values"
		" have landed on the document and before the framework checks that red_profile (or member)"
		" is filled in, so it is the only window in which this app can supply one."
	)

	w.h3("One Red Profile per login, ever")

	w.p(
		"intake.for_user() has three outcomes, tried in this order: a profile whose user is this"
		" login already exists and is returned unchanged; a profile with this person's email exists"
		" but carries no login, and is adopted; or neither, and one is created. Core makes"
		" Red Profile.user unique, so the first outcome is what makes cross-registration work at all"
		" — somebody who volunteered in March and joins as a member in August is resolved, not"
		" created again."
	)
	w.p(
		"Adoption is deliberate and it is bounded. A Frappe account is reachable only by whoever"
		" controls its mailbox, so 'the login whose email is X' and 'the person who can read X's"
		" mail' are the same person by the time the hook runs. A profile already bound to a"
		" different login is never touched: that is two identities pointing at one person, it is an"
		" administrator's problem, and the registration is refused rather than resolving it by"
		" overwriting whichever it found."
	)

	w.h3("Registration adds; it never contradicts")

	w.p(
		"intake._enrich() fills in a profile field only when core does not have one. Somebody"
		" re-registering with a different phone number is not how a phone number gets corrected —"
		" that is an edit on their own profile — and letting a form silently replace identity core"
		" already holds would make the spine's value depend on who filled in a form last. The same"
		" rule governs intake.place(), which records where they said they live as their"
		" home_geo_node only if core does not know one."
	)
	w.p(
		"That edit on their own profile is api/registration.py::update_my_profile, and it is the"
		" only endpoint in this app that overwrites core's spine. The distinction it draws is"
		" between a form filled in again — a claim made in passing, which may not contradict what"
		" the society holds — and a person looking at their own details and saying that one of them"
		" is wrong. It is possessive like everything else in that file: no parameter names a"
		" person, the profile written is the one carrying the caller's own login, and email and"
		" user are absent from its signature because the email is the login and an endpoint that"
		" could move it could walk a profile onto somebody else's account. A name may not be"
		" emptied, since core refuses a profile without one; an optional field may. The write goes"
		" through the document's own save(), so the society's configured phone pattern, the"
		" recomposed full_name and core's affiliation guard all still run."
	)
	w.note(
		"registration/tests/test_self_correction.py asserts both halves at once: a correction"
		" survives a later registration, and a later registration still cannot contradict the"
		" profile."
	)
	w.p(
		"What place() is handed is the applicant's Home Area, and it falls back to the branch they"
		" chose to serve at only when they gave no home area at all, which is the case for somebody"
		" living abroad. Red Profile.home_geo_node is core's field for where a person lives, and the"
		" volunteer form now asks that question directly rather than inferring it from where somebody"
		" offered to serve. The membership form has only the one Geo Node to offer and passes it."
	)

	w.h3("The elevation, and how narrow it is")

	w.p(
		"A self-registering applicant holds no permission on Red Profile and must not be given any:"
		" it is core's identity spine and it holds every person the society knows. intake.as_system()"
		" wraps the single insert that creates the profile, bound to that applicant's own login, from"
		" values they themselves supplied. The membership form's before_insert uses the same context"
		" for one more write, the member satellite, and says so at the call site."
	)


def _the_intake_fields(w) -> None:
	w.h2("The intake fields, and why they are always empty")

	w.p(
		"A Web Form can only collect fields that exist on the doctype it targets, and the personal"
		" details a Red Profile needs do not exist on a vmmsx satellite — that is the rule the whole"
		" app is built on. So both governed doctypes carry a Registration Intake section:"
		" applicant_first_name, applicant_last_name, applicant_phone, applicant_gender and"
		" applicant_date_of_birth."
	)
	w.p(
		"They are a transient buffer between an HTTP POST and core's spine, never storage."
		" intake._take_intake() reads them and blanks them in one pass, so there is no path — an"
		" exception in the middle, a caller that returns early — on which a value survives onto the"
		" saved record. Both controllers additionally call intake.clear_intake() from validate(), so"
		" the guarantee holds for a desk user who typed into the section, for an import, and for any"
		" future path, not only for the registration one."
	)

	w.note(
		"A saved VMMS Volunteer Application and a saved VMMS Membership carry no name, no phone and"
		" no date of birth. That is asserted directly in"
		" registration/tests/test_two_doctype_write.py."
	)


def _submission(w) -> None:
	w.h2("Why a registration submits itself")

	w.p(
		"Every other way into this app inserts a record and then calls the module's own submit()"
		" deliberately: api/volunteer.py::apply_to_volunteer does, api/member.py::apply_for_membership"
		" does, and a desk clerk following up does. A web form has no second step and nobody to press"
		" a button, so a registration that did not enter its lifecycle on the save that created it"
		" would sit at Draft forever with nothing routed to anybody."
	)
	w.p(
		"intake.submit_once() is that step, and it is scoped as tightly as it can be: it acts only on"
		" a document claim_profile() actually claimed. An ordinary desk insert still creates a draft"
		" and waits, exactly as it always has, and both halves of that are tested. The submit"
		" callable is passed in by the controller rather than imported, so intake.py knows nothing"
		" about volunteering or membership."
	)
	w.p(
		"The single-page app registers through this too. api/registration.py::register_as_volunteer"
		" and register_as_member set intake.SELF_REGISTRATION_FLAG and insert, which is the same"
		" statement a web form makes with Frappe's in_web_form flag, so the claim, the blanking of"
		" the identity buffer and submit_once all run identically. There is no second submission"
		" path to keep in step with this one."
	)


# --- the grant -------------------------------------------------------------


def _the_role_grant(w) -> None:
	w.h2("Being approved grants a role")

	w.p(
		"volunteer/services/volunteer.py::grant_self_service runs from refresh(), which is already"
		" called after any application event; member/services/member.py::grant_self_service runs from"
		" its own refresh() the same way. Both are idempotent, both fire only for an Active"
		" satellite, and neither names a role."
	)

	w.table(
		("Setting", "Granted when", "Read by"),
		[
			[
				"vmms_volunteer_member_role",
				"a volunteer becomes Active",
				"volunteer/services/society.py::volunteer_member_role",
			],
			[
				"vmms_membership_member_role",
				"a member becomes Active",
				"member/services/society.py::membership_member_role",
			],
		],
		(2.10, 2.05, 2.40),
	)

	w.bullets(
		[
			"Nobody to grant to is ordinary. Red Profile.user is nullable by core's design, and a"
			" person the branch registered from a paper form has no login. Nothing is granted and"
			" nothing is raised.",
			"An unset setting, or one naming a role somebody has since deleted, grants nothing and"
			" logs why. It never falls back to a default: a default here would be this app inventing"
			" a society's access policy.",
			"The grant is not withdrawn on exit or lapse. Taking a role away has consequences"
			" elsewhere on a site and belongs to a society's off-boarding, not to a status"
			" derivation that runs on every save. A lapsed member is still refused a certificate,"
			" by certificate.assert_active, which is where that rule belongs.",
		]
	)

	w.h3("The grant also decides what kind of account this is")

	w.p(
		"Frappe's User.set_system_user() reads the roles a user holds and sets user_type to System"
		" User if any of them has desk_access. That is the mechanism rather than a side effect: a"
		" Workspace is a desk surface and a Website User cannot open one, so the society's roles"
		" having desk access is what makes a workspace showable at all. A society that would rather"
		" its applicants never reach the desk leaves the settings empty and drives registration from"
		" the two portal routes, which need none of this."
	)

	w.h3("And it narrows the lists the workspace shows")

	w.p(
		"roles.scope_to() creates Frappe User Permissions allowing exactly this person's own"
		" VMMS Volunteer, which is why the volunteer workspace can point at ordinary desk list"
		" views: their time logs and their certifications filter to their own rows with no query"
		" code at all."
	)
	w.p(
		"It writes one row per doctype, and the list of doctypes is a required argument rather than"
		" a default. That is the whole safety of the function. A User Permission with"
		" apply_to_all_doctypes narrows every doctype linking to the allowed record, for that user,"
		" everywhere and forever, and it would follow the person into whatever else they do for the"
		" society: a coordinator who also volunteers, or a registration clerk who is also a member,"
		" would quietly stop seeing the records their job needs. So the permission is bounded to"
		" exactly what the surface lists."
	)
	w.p(
		"The member grant writes none at all, deliberately. That surface points at no doctype —"
		" every membership a person can see comes back through my_memberships, which answers from"
		" the session — so there is nothing to narrow and narrowing anything would be pure damage."
	)


def _owner_bypass(w) -> None:
	w.h2("Owner bypass: seeing your own record")

	w.p(
		"VMMS Volunteer and VMMS Membership are both registered with core as geo-scopeable, and core"
		" fails closed: somebody holding no Geo Assignment for the configured scope role sees"
		" nothing. That is right for the register, which is not a volunteer's to browse, and wrong"
		" for the person in it."
	)
	w.p(
		"So both API modules admit two callers. api/member.py::_readable and"
		" api/volunteer.py::_readable return the document immediately when the session user is the"
		" person it belongs to, and otherwise fall through to check_permission('read'), which is"
		" Frappe's roles and core's scoping unchanged."
	)

	w.h3("Through Red Profile.user, never through owner")

	w.p(
		"They are different people and often are. A membership registered at a branch counter is"
		" owned by the clerk who typed it; a volunteer record is created by the approval that"
		" accepted the application, so its owner is the approver. Gating on owner would hand the"
		" clerk every certificate they ever entered and deny the member their own. The holder is"
		" resolved through certificate.owner_user() and volunteer identity.user_of(), both of which"
		" read core's Red Profile."
	)

	w.h3("The possessive endpoints")

	w.table(
		("Endpoint", "Takes", "Answers"),
		[
			[
				"api/member.py::my_memberships",
				"nothing",
				"every membership held by the logged-in person, at every branch",
			],
			[
				"api/volunteer.py::my_volunteer",
				"nothing",
				"their own volunteer record and its approval trail, or None",
			],
			[
				"api/volunteer.py::my_certifications",
				"nothing",
				"what they hold, whether each has lapsed, and whether they are deployable, all derived today",
			],
			[
				"api/member.py::download_my_certificate",
				"an optional membership",
				"their own certificate as a PDF; the argument narrows, never widens",
			],
		],
		(2.30, 1.55, 2.70),
	)
	w.p(
		"None of the four lets a caller name the person. That is the point of them rather than an"
		" implementation detail: an endpoint that accepted a name would be a general-purpose reader"
		" wearing a possessive name, and the check stopping that would be one more thing to get"
		" right. download_my_certificate exists because a workspace shortcut is a static URL and"
		" cannot know a membership's name; somebody holding several active memberships is told so,"
		" and told which."
	)
	w.p(
		"my_certifications takes no date either, though one would not let a caller name anybody. It"
		" is somebody's answer about their own training today, and a coordinator who genuinely needs"
		" to ask about the day a deployment starts has get_certifications(name, as_of) and"
		" get_deployability(name, as_of) — permission-checked, because they name somebody."
	)

	w.note(
		"The bypass is an identity match, not a scope. Somebody's own list of the register is still"
		" empty, and that is asserted in both journey suites."
	)


# --- the surfaces ----------------------------------------------------------


def _the_workspaces(w) -> None:
	w.h2("The three Workspaces")

	w.table(
		("Workspace", "Shown to", "What is on it"),
		[
			[
				"Registration",
				"vmms_self_service_role",
				"exactly two shortcuts, one per registration form",
			],
			[
				"My Volunteering",
				"vmms_volunteer_member_role",
				"their volunteer record, their applications, their time logs, their certifications",
			],
			[
				"My Membership",
				"vmms_membership_member_role",
				"their memberships and their own certificate",
			],
		],
		(1.70, 2.10, 2.70),
	)
	w.caption("Built by vmmsx/registration/services/workspaces.py::install")

	w.h3("Why they are built rather than shipped")

	w.p(
		"A standard Workspace ships as a file. These cannot, because each is shown to a role a"
		" society named in its own settings, and a file cannot carry that. So the structure is code"
		" and the role is configuration, and install() marries the two. It runs from the"
		" after_migrate hook in hooks.py, from the Kenya seed once it has chosen the roles, and by"
		" hand:"
	)
	w.code("bench --site <site> execute vmmsx.registration.services.workspaces.install")

	w.h3("No role, no surface")

	w.p(
		"A Frappe Workspace that names no roles is visible to every desk user on the site —"
		" Workspace.is_permitted() falls back to blocked modules when roles is empty. So install()"
		" refuses to build a surface whose role is unset or names a role somebody has deleted, and"
		" removes one it finds. Stripping the roles and leaving the workspace behind would make it"
		" visible to everybody, which is the exact opposite of what clearing a setting means."
	)

	w.h3("Why some shortcuts are URLs")

	w.p(
		"Two different reasons, and they are worth keeping apart. VMMS Volunteer and VMMS Membership"
		" are geo-registered and would show an empty list to somebody holding no Geo Assignment, so"
		" the person's own record is reached through the owner-bypassed endpoints instead and those"
		" shortcuts are URLs. That reason is about permission."
	)
	w.p(
		"VMMS Time Log and VMMS Certification are not geo-registered, so a DocType shortcut works for"
		" either, narrowed to the person's own rows by their User Permission and readable because"
		" registration/services/permissions.py grants the configured role read on exactly those two."
		" The time log shortcut is one. The certification shortcut is a URL anyway, for a reason"
		" about what can be shown rather than about permission: a list view can only display stored"
		" columns, and whether a certification has lapsed is derived at the moment of asking and is"
		" deliberately not a column. api/volunteer.py::my_certifications() computes it, along with"
		" whether the lapse costs them deployability. The list view is still on the workspace's"
		" card, because the records themselves are worth browsing; it is the answer that needs an"
		" endpoint. The Volunteer section describes the derivation in full."
	)

	w.h3("Where somebody lands")

	w.p(
		"The desk opens on the first workspace a user is permitted to see, ordered by sequence_id."
		" These three carry negative sequence ids so that the surface built for this person is the"
		" one they arrive at: My Volunteering, then My Membership, then Registration. A brand-new"
		" account can see only Registration and therefore lands there; an approved volunteer lands"
		" on their own."
	)
	w.note(
		"Frappe remembers a returning user's last workspace in the browser and reopens that"
		" instead, which is its behaviour rather than this app's. The ordering decides where"
		" somebody arrives the first time, and where they arrive after their permitted set changes"
		" — which is exactly the moment that matters here."
	)


def _configuration(w) -> None:
	w.h2("Configuration")

	w.p(
		"Three Custom Fields on core's National Society Settings, owned and installed by vmmsx"
		" (patches/install_self_service_roles.py). Core's doctype is not edited."
	)

	w.table(
		("Field", "What it decides", "Empty means"),
		[
			[
				"vmms_self_service_role",
				"what a self-registered account holds until it is approved as anything",
				"the Registration workspace is not installed",
			],
			[
				"vmms_volunteer_member_role",
				"what an accepted volunteer's own login is granted",
				"nothing is granted; My Volunteering is not installed",
			],
			[
				"vmms_membership_member_role",
				"what an active member's own login is granted",
				"nothing is granted; My Membership is not installed",
			],
		],
		(2.00, 2.50, 2.00),
	)

	w.p(
		"Two native records complete the loop and are a society's to set: Website Settings decides"
		" whether signup is offered at all, and Portal Settings' Default Role decides which role a"
		" self-registered account receives. Point the second at the same role vmms_self_service_role"
		" names."
	)


def _the_seed(w) -> None:
	w.h2("The Kenya seed")

	w.p(
		"vmmsx/seed/kenya.py is a worked configuration for one society, and it is data rather than"
		" behaviour: no source file outside that package names Kenya, County, Branch, Ordinary or"
		" any role it creates, and deleting the package would leave vmmsx working exactly as it does"
		" now."
	)
	w.code("bench --site <site> execute vmmsx.seed.kenya.main")
	w.p(
		"It creates the society's identity, a three-level geo ladder with a national root, two"
		" counties and two branches, two membership types (one fee-bearing auto-on-payment, one"
		" routed), an approval workflow per approvable doctype, five roles, a demo approver placed"
		" at a county by Geo Assignment, every role setting this app owns, and the three workspaces."
		" Every step checks before it writes and reports created or exists, so running it twice"
		" changes nothing."
	)
	w.p(
		"Three things it deliberately will not do, and reports every run: it does not invent a logo"
		" (an Attach Image is a real file), it does not set the demo approver's password, and it does"
		" not configure another app's payment gateway."
	)


def _limits(w) -> None:
	w.h2("What this layer does not do")

	w.bullets(
		[
			"There is no self-service proof-of-membership attachment. A registrant cannot upload a"
			" document with their registration and nothing asks them to.",
			"A member's or volunteer's desk list of the register stays empty. Core's geo scoping"
			" fails closed for somebody holding no Geo Assignment, deliberately, and vmmsx's owner"
			" bypass admits them to their own record rather than to a filtered register.",
			"Certifications a society has not configured do not exist. A volunteer's certification"
			" surface is real and derives the lapse live, but it can only show types the society"
			" wrote down and mappings it chose, and on a site with no learning system every"
			" certification is recorded by hand. That is a supported way to run, not a gap.",
			"A role is never taken away. Exit and lapse leave the person holding what they were"
			" granted, and off-boarding is a society's act.",
			"Other apps installed on the same bench ship workspaces that name no roles, so those are"
			" visible to any desk user including a self-registered one. vmmsx does not modify other"
			" apps' records; a society that wants a genuinely narrow desk uses Frappe's own Module"
			" Profile to block the modules its volunteers have no business in.",
		]
	)


def _what_is_tested(w) -> None:
	w.h2("What is tested")

	w.p(
		"vmmsx/registration/tests/ drives the real Frappe web form endpoint, the real approval"
		" engine, the real payments Manual driver and the real API gate. Nothing in it is mocked."
	)

	w.bullets(
		[
			"test_two_doctype_write.py — the profile is created and carries this login, the identity"
			" is on the profile and not on the record, registering again reuses it, a paper profile"
			" with the same email is adopted, one bound to another login is refused, and the desk"
			" path is untouched.",
			"test_volunteer_journey.py — form to routed application to accepted volunteer, the role"
			" grant and its User Permission, the paper case that grants nothing, and the owner"
			" reading their own record while a stranger and the register itself stay closed.",
			"test_member_journey.py — both approval modes to Active, the role grant by each path,"
			" the certificate downloaded by its holder, by name and by the possessive endpoint,"
			" refused for a stranger, refused when lapsed, and still allowed for the configured"
			" print role.",
			"test_cross_registration.py — one profile, both roles, both workspaces, both affiliation"
			" rows on core's index, in either order.",
			"test_workspaces.py — what is installed, that each names exactly the configured role,"
			" that an unset or deleted role installs nothing and removes what is there, and who"
			" lands where.",
			"test_seed.py — the Kenya seed run for real, asserted record by record, proved"
			" idempotent, and then a whole registration driven through the configuration it"
			" produced and accepted by the approver it seeded.",
		]
	)
