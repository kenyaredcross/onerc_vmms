# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Content and Portal section of the guide.

Two things that are really one thing: a doctype pair that makes every sentence
in the product configuration, and a React frontend built so that a volunteer or
a coordinator never has to open the desk. The frontend is documented here rather
than in its own section because almost everything worth saying about it is a
consequence of the content layer beneath it.

Field tables are generated from the doctype JSON, as everywhere else in this
guide. Every claim about the frontend names the file it describes.
"""

from vmmsx.docs import doctypes

TITLE = "Content and the Portal"
SUMMARY = "Every sentence and picture as configuration, and a React portal so nobody needs the desk."

CONTENT_DOCTYPES = ("VMMS Content Surface", "VMMS Content Block")


def render(w) -> None:
	w.h1(TITLE)

	_what_it_is(w)
	_the_doctypes(w)
	_the_read_boundary(w)
	_seed_versus_overwrite(w)
	_who_may_edit(w)
	_safety(w)
	_the_frontend(w)
	_not_built(w)
	_what_is_tested(w)


def _what_it_is(w) -> None:
	w.h2("What this layer is")

	w.lead(
		"Every heading, paragraph, button label, statistic, photograph and photo credit in this"
		" product is a record. Not a string in a template, not a translation key: a VMMS Content"
		" Block with an opaque content_key, which an administrator rewrites in place with a pencil"
		" that appears on the page itself."
	)
	w.p(
		"The reason is the same rule the rest of this app is built on. A national society is not"
		" this app's to assume, and wording is where that assumption hides most easily. A hero"
		" headline that says Kenya, a card that quotes a fee in KES, a statistic that says 47"
		" county branches: each is a hardcoded country or currency wearing a friendlier coat, and"
		" each would need a code change and a deploy to correct. Making them records makes"
		" changing them a Tuesday afternoon rather than a release."
	)
	w.p(
		"So vmmsx/content/seeds/default_content.py ships society-neutral wording and no images at"
		" all, and vmmsx/seed/kenya_content.py layers the Kenya copy and photography on top. That"
		" package remains the only place in the app that knows what a county is."
	)


def _the_doctypes(w) -> None:
	w.h2("The two doctypes")

	w.p(
		"A surface is a screen's worth of slots and a read boundary. A block is one slot. Both are"
		" named by a stable key that is also the docname, the same shape VMMS Template already"
		" uses, so renaming a label never blanks a page."
	)

	for doctype in CONTENT_DOCTYPES:
		w.h3(doctype)
		w.table(
			doctypes.FIELD_TABLE_HEADERS,
			doctypes.fields(doctype),
			doctypes.FIELD_TABLE_WIDTHS,
		)
		w.caption(f"Naming — {doctypes.naming_of(doctype)}")

	w.p(
		"No source file branches on which surface it got, or on a block's key, in exactly the way"
		" no source file branches on a template category or an approval stage label. A component"
		" in the frontend asks for the key it wants and renders whatever comes back; a key nobody"
		" seeded renders the component's own fallback rather than a hole in the page."
	)


def _the_read_boundary(w) -> None:
	w.h2("is_public is the whole guest rule")

	w.p(
		"The landing page has to render before anybody has signed in, so vmmsx/api/content.py"
		" carries the only allow_guest endpoint in this app. What stops that being a hole is that"
		" it decides nothing itself: surface() serves a signed-out visitor only a surface whose"
		" Readable By Guests flag is set, and refuses everything else."
	)
	w.bullets(
		[
			"Opening a screen to the public is therefore a settings change on a document, with an"
			" audit trail, rather than an allow_guest somebody has to find in a source file.",
			"A surface that is not public and a surface that does not exist give a guest the same"
			" message, so probing for surface keys tells nobody which guesses were right.",
			"Several surfaces may be requested in one call, because nearly every page needs its"
			" own slots and the shared chrome, and two round trips before the hero paints is two"
			" too many. Every named surface is checked, so a public key cannot smuggle a private"
			" one alongside it.",
			"catalogue(), which enumerates every slot on the site for the bulk editor, is a"
			" separate endpoint requiring read permission. It is separate deliberately: an"
			" argument that turned the guest endpoint into give-me-everything is an argument"
			" somebody would eventually pass from a signed-out browser.",
		]
	)


def _seed_versus_overwrite(w) -> None:
	w.h2("Why there are two seed functions")

	w.p(
		"blocks.seed() creates what is missing and never touches what exists. blocks.overwrite()"
		" writes regardless. The difference is the reason both exist, and getting it wrong would"
		" produce a bug nobody would connect to its cause."
	)
	w.table(
		("Function", "Used by", "Why"),
		[
			[
				"seed()",
				"patches/setup_content_module.py",
				"Runs on every migrate. If it refreshed the shipped defaults, every deploy would"
				" silently revert a society's rewritten home page and nobody would associate the"
				" two events. New slots added in a later release still appear, because those are"
				" the ones that are missing.",
			],
			[
				"overwrite()",
				"seed/kenya_content.py",
				"Runs only when somebody executes the Kenya seed deliberately. They are asking to"
				" see the Kenya page, and a page half in the product's neutral voice would be"
				" nobody's idea of a worked example.",
			],
		],
		(1.15, 1.95, 3.40),
	)


def _who_may_edit(w) -> None:
	w.h2("Who may reword a page")

	w.p(
		"vmms_content_editor_role, a Custom Field vmmsx owns on core's National Society Settings,"
		" installed by patches/setup_content_module.py. No role name appears in any source file,"
		" for the reason the access model gives: which of a society's roles may rewrite the public"
		" home page is that society's decision."
	)
	w.p(
		"The grant itself is vmmsx/content/services/permissions.py, wired into after_migrate"
		" rather than into the patch. A patch runs once per site by name, but a society that names"
		" a different role a year later needs the grant to follow it, and a patch that has already"
		" run never will. Read and write, never create or delete: an editor rewords the slots the"
		" product defines. Nothing is ever revoked, because a migrate that quietly locked out a"
		" society's editors would be a worse failure than a stale grant."
	)
	w.note(
		"The field ships empty, and empty means only System Manager can edit, which is the"
		" framework exemption rather than a policy this app invented. The pencil simply does not"
		" appear for anybody else. An unconfigured site therefore fails towards a page nobody can"
		" edit rather than one anybody can rewrite."
	)


def _safety(w) -> None:
	w.h2("Two things the controller refuses")

	w.p(
		"A content block is written by an administrator through a form and rendered into a page"
		" served to the public, which makes it untrusted input on a trusted surface. Two"
		" protections, and the moment to apply both is while the author is still looking at the"
		" form rather than weeks later on somebody's browser."
	)
	w.bullets(
		[
			"The text is text. text_value is plain and the frontend renders it as a string, never"
			" as markup, so a heading cannot carry a script into the landing page. There is"
			" nothing to sanitise because it is never treated as HTML.",
			"The link goes somewhere sane. VMMSContentBlock.validate_link refuses link_href unless"
			" it is a path within this site, an anchor, or an http, https, mailto or tel address."
			" Schemes are allow-listed rather than the dangerous ones being named, so a scheme"
			" nobody thought of is refused too. A javascript: URI in an editable field is stored"
			" cross-site scripting wearing a settings form.",
		]
	)


def _the_frontend(w) -> None:
	w.h2("The portal")

	w.p(
		"portal/ is a React, TypeScript and Vite single-page app, built into vmmsx/public/portal"
		" and served by vmmsx/www/portal.html through vmmsx/spa.py, which reads the Vite manifest"
		" server-side so the page always points at the current hashed bundle. The"
		" website_route_rules entry in hooks.py sends /portal/<path> to the same page, so"
		" react-router owns the client-side routes and a deep link survives a refresh."
	)

	w.h3("Three audiences, three chunks")

	w.table(
		("Surface", "Route", "What it is"),
		[
			[
				"Guest landing",
				"/portal",
				"The public page, composed from option 7a of the design: full-bleed photo bands,"
				" an overlay card on the hero, a four-up card row. Not one sentence of it is in"
				" the source; the composition is, and nothing else.",
			],
			[
				"Join wizard",
				"/portal/join",
				"Four steps for a member, seven for a volunteer, asking for exactly what the two"
				" Web Forms ask for. One call: register_as_member or register_as_volunteer."
				" Sign-in comes first, always.",
			],
			[
				"Volunteer portal",
				"/portal/dashboard and below",
				"Dashboard, membership, hours, profile, training. Navy sidebar.",
			],
			[
				"Manager console",
				"/portal/admin and below",
				"Review queue, registry, page content. Near-black sidebar, which is the design's"
				" way of saying you are acting on other people's records now.",
			],
		],
		(1.30, 1.55, 3.65),
	)

	w.h3("Rules the frontend keeps")

	w.bullets(
		[
			"No role name appears anywhere in portal/src/, and no screen decides what somebody may"
			" do. can_edit on a content surface and can_act on an approval are computed"
			" server-side against the same check the write would make; the frontend draws a button"
			" from the flag and the server re-asks on every write. A browser that forges a flag"
			" gains an inert button and a refusal.",
			"lib/api.ts names every whitelisted method the frontend calls, in one object. If a"
			" method is not in it, no screen calls it, and the app's real dependency on the"
			" backend is readable in one file.",
			"The possessive endpoints are used as possessive endpoints. my_volunteer,"
			" my_memberships, my_certifications and my_queue take no arguments, so nothing on a"
			" self-service screen can be pointed at somebody else and there is no check in the"
			" frontend to get wrong.",
			"Registry and queue screens send no scope filter, because scope is the floor those"
			" endpoints stand on rather than a parameter. An empty registry for somebody with no"
			" Geo Assignment is the correct render, not a failure.",
			"Stage labels are displayed and never compared, the same discipline the Python side"
			" enforces with an AST test. Colour on a badge keys off the engine's closed state set,"
			" which is code, never off a stage, which is configuration.",
		]
	)

	w.h3("Identity is the server's, once")

	w.p(
		"A Web Form gets a before_insert window in which to call intake.claim_profile, and a"
		" single-page app has no such window. So vmmsx/api/registration.py sets the flag"
		" intake.SELF_REGISTRATION_FLAG, which that module already documents as how a caller that"
		" means it and is not a form says so, and the insert then runs down the same road: the"
		" profile is claimed by intake.for_user, the identity buffer is emptied onto it and blanked,"
		" the person is placed, and submit_once puts the record into motion. The SPA registers"
		" through the same code as the desk rather than a second copy of it."
	)
	w.p(
		"That is what keeps one Red Profile per login, ever, true for both paths at once: found,"
		" adopted or created, with the same refusal to overwrite a profile bound to somebody else,"
		" and the same rule that registration adds and never contradicts. Neither endpoint takes a"
		" person, and the email is never a parameter, because the login is the identity. The two"
		" Web Forms stay installed and untouched."
	)

	w.h3("The details on the identity step are the person's own")

	w.p(
		"Every field on the wizard's About You step is editable, including for somebody the"
		" society already has a record for, and the email is the single exception: it is drawn"
		" with a lock beside it because it is the account they signed in with. A correction is"
		" posted to api/registration.py::update_my_profile before the registration itself, because"
		" registration is additive by design — a new surname travelling in the intake buffer would"
		" be read by intake._enrich, found to contradict what core holds, and dropped. The call is"
		" skipped entirely when nothing changed, so an ordinary registration still writes nothing"
		" to the spine it did not create."
	)

	w.h3("Four questions, and the length of the list picks the control")

	w.p(
		"The volunteering step asks for skills, languages, availability and motivation, all four"
		" of them configured vocabularies this app never names. ui/form.tsx draws the first, third"
		" and fourth as OptionCards — a short curated list where every row's configured description"
		" belongs on the page rather than behind a hover — and languages as MultiCombo, a"
		" type-to-filter multi select, because that list is Frappe's own and far too long to read."
		" Both echo what was chosen through the same TokenTray, so the two never read as different"
		" questions, and neither can tell a skill from a motivation."
	)
	w.p(
		"api/volunteer.py::_languages() deliberately does not filter on Language.enabled. That flag"
		" means 'this site's interface is offered in this language', which is a different question"
		" from what an applicant speaks, and Frappe ships its list with most rows off — Kiswahili"
		" among them. A society wanting more than the shipped list adds Language rows, the same way"
		" it adds a skill; seed/kenya.py adds the ones spoken here."
	)

	w.h3("Two doors, and why they are not one")

	w.p(
		"register_as_volunteer and register_as_member are the self-service door and name nobody:"
		" the record can only ever attach to the Red Profile carrying the session's own login."
		" api/volunteer.py::apply_to_volunteer and api/member.py::apply_for_membership are the"
		" clerk's door, name a red_profile so a coordinator can enter a paper application for"
		" somebody else, and check create permission because a clerk is somebody a society has"
		" granted something to."
	)
	w.p(
		"The split is what makes the elevation safe to have. A person registering for the first"
		" time holds no role at all, which is what registering means, so the create permission"
		" cannot be theirs; Frappe's own Web Form has the same problem and resolves it the same way"
		" (web_form.py::accept inserts with ignore_permissions). Because the self-service endpoints"
		" accept no argument naming a person, that bypass can never be pointed at anybody. Every"
		" business rule still runs untouched: ACC-02's anchor and ACC-03's levels in validate(),"
		" identification and residency in application.assert_ready(), and the whole approval engine"
		" in submit."
	)


def _not_built(w) -> None:
	w.h2("What is not built, and says so on the page")

	w.p(
		"The design canvas covers more ground than this app does. Where a screen has nothing"
		" behind it, it renders a NotBuilt panel naming the missing doctype and inventing no"
		" rows. The rule is the walkthrough's: a screen that reads as though everything works is"
		" worse than none, because somebody will demonstrate it in front of an audience."
	)
	w.table(
		("Screen", "State", "What is missing"),
		[
			[
				"Events",
				"Nothing exists",
				"No VMMS Event doctype, no roster, no RSVP, no check-in, no API. The events on the"
				" public landing page are wording an administrator typed into content blocks,"
				" which is the honest answer to having no event records.",
			],
			[
				"Opportunity browsing",
				"Half",
				"deployments_of_volunteer is real and shows a volunteer their own deployments. No"
				" endpoint exposes open deployment requests to the people who might answer them;"
				" find_candidates runs the other way round.",
			],
			[
				"Hours history",
				"Half",
				"log_time is real and the form writes through it. There is no possessive endpoint"
				" returning a volunteer their own time logs, only the coordinator dossier which"
				" takes a name.",
			],
			[
				"Deployments and stipends consoles",
				"Backend only",
				"api/deployment.py and api/stipend.py are complete and permission-checked. Only"
				" the interface over them is missing, which is different work from the rows above"
				" and worth distinguishing.",
			],
			[
				"Branch analytics",
				"Nothing exists",
				"No aggregation endpoint. Revenue in particular would have to come from"
				" onerc_payments rather than from this app.",
			],
		],
		(1.50, 0.95, 4.05),
	)


def _what_is_tested(w) -> None:
	w.h2("What is tested")

	w.p("18 integration tests, in vmmsx/content/tests/test_blocks.py.")
	w.table(
		("Group", "Tests", "What it proves"),
		[
			[
				"The DTO",
				"2",
				"A surface comes back keyed by content key, and carries only the seven reviewed"
				" fields, so a schema change is never silently an API change.",
			],
			[
				"Seeding",
				"3",
				"seed() creates what is missing, and leaves an edited slot exactly as the society"
				" left it even when the shipped default differs. overwrite() does what seed will"
				" not, which is the Kenya seed's path.",
			],
			[
				"Writing",
				"2",
				"A partial write leaves the other fields alone, so the pencil beside a caption"
				" cannot blank the photograph next to it. A field outside the editable set is"
				" ignored however the request is shaped.",
			],
			[
				"Links",
				"4",
				"javascript:, data: and protocol-relative //host links are all refused; ordinary"
				" site paths, anchors, http, https, mailto and tel are all accepted.",
			],
			[
				"The API and the guest boundary",
				"7",
				"A guest reads a public surface and gets can_edit false; is refused a private one;"
				" is refused a private one requested alongside a public one; and is refused the"
				" catalogue entirely. Several surfaces merge into one dictionary. An administrator"
				" may edit, and update_block returns the slot as it now reads.",
			],
		],
		(1.85, 0.55, 4.10),
	)
