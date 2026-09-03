# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Volunteer API — explicit DTOs, and no second door into an approval.

Every endpoint names its arguments, checks permission through Frappe (which
brings core's geo scoping with it), and returns a dict this module builds field
by field. None of them returns a Document or a raw query result.

Deciding a volunteer application is deliberately **not** here. A routed
application is acted on through `vmmsx/api/approvals.py`, the generic engine
endpoint, because the person-gate lives there and a second door into the same
decision would be a second place to get it wrong.

**The volunteer reaches their own record without a doctype-read role.** `my_volunteer()`
takes no arguments and answers from the session, and `_readable` admits the
person a volunteer record is *about* alongside anybody the ordinary permission
layer already allows. Core's geo scoping fails closed for somebody holding no
scope role, which is right for the register and wrong for the person in it.
"""

import frappe
from frappe.utils import cint

from vmmsx.registration.services import declarations, questions
from vmmsx.registration.services import society as registration_society
from vmmsx.volunteer.services import application as application_service
from vmmsx.volunteer.services import certification, timelog
from vmmsx.volunteer.services import volunteer as volunteer_service

APPLICATION_DOCTYPE = "VMMS Volunteer Application"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"
TIME_LOG_DOCTYPE = "VMMS Time Log"


@frappe.whitelist()
def apply_to_volunteer(
	red_profile: str,
	geo_node: str,
	skills: list | None = None,
	languages: list | None = None,
	availability: list | None = None,
	motivation: list | None = None,
	prior_experience: str | None = None,
	declarations_accepted: list | dict | None = None,
	emergency_contacts: list | None = None,
	guardian_consents: list | None = None,
) -> dict:
	"""Create an application and put it into motion.

	`geo_node` is the requested Serving Branch and the only location stored on
	the application. Citizenship, residence and identification are validated
	from the linked Red Profile when the application is submitted.

	`skills`, `languages`, `availability` and `motivation` are plain lists of
	keys — `["first_aid", "driving"]`, not the child-table row shape those
	fields store internally. Shaping that translation is this endpoint's job,
	not something every caller should have to know.

	**The clerk's door carries the declarations too, and it has to.**
	`assert_ready` refuses a submission with a required declaration unaccepted
	whichever door it came through — deliberately, because a society that asks
	its applicants to agree to something has not stopped asking merely because
	the form arrived on paper. So a coordinator entering an application records
	what the applicant signed, exactly as the wizard records what they ticked.
	Without this parameter the clerk's door could not satisfy a rule the
	self-service door could, which is a difference no society asked for.

	`emergency_contacts` and `guardian_consents` are here for the same reason,
	and they are shaped through the same allow-list the portal uses — so a
	coordinator can no more mark a guardian's consent verified from this
	endpoint than an applicant can. Verification is a tick on the application
	itself, by whoever actually checked, and it is stamped with their name.
	"""
	from vmmsx.api.registration import (
		EMERGENCY_CONTACT_FIELDS,
		GUARDIAN_CONSENT_FIELDS,
		GUARDIAN_CONSENT_FILE_FIELDS,
		rows_from,
		secure_row_files,
	)
	from vmmsx.registration.services import declarations

	frappe.has_permission(APPLICATION_DOCTYPE, ptype="create", throw=True)

	application = frappe.get_doc(
		{
			"doctype": APPLICATION_DOCTYPE,
			"red_profile": red_profile,
			"geo_node": geo_node,
			"skills": selector_rows(skills, "skill"),
			"languages": selector_rows(languages, "language"),
			"availability": selector_rows(availability, "availability_slot"),
			"motivation": selector_rows(motivation, "motivation"),
			"prior_experience": prior_experience,
			"emergency_contacts": rows_from(emergency_contacts, EMERGENCY_CONTACT_FIELDS),
			"guardian_consents": rows_from(
				guardian_consents, GUARDIAN_CONSENT_FIELDS, GUARDIAN_CONSENT_FILE_FIELDS
			),
		}
	)
	declarations.apply(application, declarations_accepted)
	application.insert()

	# After the insert, because a file can only be tied to a document that has a
	# name — the same reason `questions.anchor_files` runs there.
	secure_row_files(application, "guardian_consents", GUARDIAN_CONSENT_FILE_FIELDS)

	return application_service.submit(application)


def selector_rows(values: list | None, link_field: str) -> list[dict]:
	"""Plain key values from a caller, shaped into the rows a Table MultiSelect stores."""
	return [{link_field: value} for value in (values or []) if value]


@frappe.whitelist()
def geo_node_levels() -> dict:
	"""Geo Levels a new application's Serving Branch may sit at (ACC-03).

	The twin of `api/member.py::geo_node_levels`, and it intersects for the same
	reason: two configuration surfaces will judge this one field, at two
	different moments, and a picker built from one of them can still offer a
	level the other goes on to reject.

	The two are further apart here than they are for a membership, which is
	exactly why the intersection matters. The governing `VMMS Approval
	Workflow`'s `allowed_anchor_levels` is checked at **Submit**, by
	`engine.submit()`. National Society Settings' `vmms_volunteer_anchor_level`
	is checked when the **volunteer record is created**, by
	`VMMSVolunteer.validate()` through `society.assert_anchor_level()` — and the
	application's Serving Branch is what becomes that record's `home_geo_node`
	(`application.accept()`). So a level only the second one forbids would let an
	application be submitted, reviewed and approved, and fail at the moment of
	acceptance, in front of the approver rather than the applicant.

	`unconstrained` is True only when neither surface narrows it. Where both
	narrow it but agree on nothing, `levels` is empty: a misconfiguration a
	society has to resolve, and not this endpoint's place to guess past.
	"""
	from vmmsx.approvals.services import config as approval_config
	from vmmsx.volunteer.services import society

	workflow_levels = approval_config.allowed_anchor_levels_for(APPLICATION_DOCTYPE)
	settings_level = society.volunteer_anchor_level()

	if workflow_levels and settings_level:
		levels = [settings_level] if settings_level in workflow_levels else []
	elif workflow_levels:
		levels = workflow_levels
	elif settings_level:
		levels = [settings_level]
	else:
		levels = []

	return {"levels": levels, "unconstrained": not levels}


def _select_options(field) -> list[str]:
	"""A Select field's own options, as a list.

	A Select's options are newline separated and a leading or trailing blank line
	is ordinary in one, so the empties are dropped rather than rendered as a
	nameless choice. Absent field, empty list: a site mid-migrate has no options
	to offer and that is not an error.
	"""
	if not field:
		return []

	return [option.strip() for option in (field.options or "").split("\n") if option.strip()]


@frappe.whitelist()
def application_options() -> dict:
	"""Every vocabulary a volunteer registration form has to draw, in one call.

	The desk gets these for free. A Link field asks the framework what it may
	point at and a Table MultiSelect draws its own chips, so the Web Form never
	has to be told what a skill is. A single-page frontend has neither, and its
	only two alternatives are both wrong: hardcode the lists, which puts a
	society's configuration into a source file, or make six round trips for six
	controls.

	So this is one read of the configuration, filtered to what is active and
	shaped field by field. A society retiring a skill or adding an ID type
	changes the form with no deploy, which is the whole reason these are records
	rather than constants.

	`residency_types` comes from the doctype's own Select, not from a list typed
	again here, so the toggle a person sees can never offer a value the field
	would refuse.

	**No elevation, and none needed.** Every doctype read below grants `read` to
	`All`: a vocabulary is what a form may offer, and it says nothing about any
	person.
	"""
	profile = frappe.get_meta("Red Profile")
	residency = profile.get_field("residency_type")
	citizenship = profile.get_field("citizenship_status")

	return {
		"skills": _vocabulary("VMMS Skill", "skill_name"),
		"languages": _languages(),
		"availability": _vocabulary("VMMS Availability Slot", "slot_name"),
		"motivations": _vocabulary("VMMS Motivation", "motivation_name"),
		"id_types": _id_types(),
		"countries": [row["name"] for row in frappe.get_all("Country", order_by="name asc")],
		# A Select's options are newline separated and a leading or trailing
		# blank line is ordinary in one, so the empties are dropped rather than
		# rendered as a nameless third choice.
		"residency_types": _select_options(residency),
		# What kind of standing a person has in the country they are applying in.
		# The form asks it as "are you a citizen of X?", which answers this field
		# for everybody who says yes and leaves the four other words to whoever
		# says no — and they are the field's own words, read off the Select, so the
		# form can never offer a standing the profile would refuse to store.
		"citizenship_statuses": _select_options(citizenship),
		"default_country_of_citizenship": _default_citizenship(),
		# The society's own questions, if it has written any. Same call the
		# membership options endpoint makes, so both wizards draw an added
		# question the same way and neither knows what one is about.
		"questions": questions.asked_on(APPLICATION_DOCTYPE),
		# What the applicant has to agree to, in the society's own current
		# wording. Served rather than written into the bundle for the reason
		# every other list here is: the text is a record an administrator edits,
		# and a copy in a browser bundle would be the version nobody updated.
		"declarations": declarations.shown_on(APPLICATION_DOCTYPE),
		# The age this society treats as adult, so the form knows when to ask for
		# a guardian rather than guessing. `None` means the society has not
		# configured minor handling and the guardian step is never drawn — the
		# same answer `application.is_minor` reaches on the server.
		"minor_age": registration_society.minor_age(),
		# How a guardian's consent can be verified. Only ever shown to whoever is
		# recording the verification, but served with the rest of the vocabulary
		# because it is configuration like everything else in this payload.
		"guardian_verification_methods": _vocabulary("VMMS Guardian Verification Method", "method_name"),
	}


def _vocabulary(doctype: str, label_field: str) -> list[dict]:
	"""An active-only configured vocabulary, as `{key, label, description}` rows.

	The key is the docname, because that is what the Link field stores and what
	`apply_to_volunteer` expects back. These doctypes all autoname from their own
	`*_key` field, so the key is stable across a relabelling: renaming a skill on
	screen never invalidates an application that already chose it.
	"""
	rows = frappe.get_all(
		doctype,
		filters={"is_active": 1},
		fields=["name", label_field, "description"],
		order_by=f"{label_field} asc",
	)

	return [
		{"key": row["name"], "label": row[label_field] or row["name"], "description": row["description"]}
		for row in rows
	]


def _id_types() -> list[dict]:
	"""The identification types on offer, each carrying what this society asks of it.

	`_vocabulary`'s three keys plus the society's own rules, so a form can mark a
	document as required and ask for the copy the rule insists on rather than
	discovering at submission that the server wanted one. The two readings never
	disagree, because `application._required_document_types()` reads the very same
	fields off the very same rows.

	**Empty rules on a site that has not run the patch yet.** The Custom Fields
	are installed by `patches/install_identity_document_rules.py`, and between
	syncing this module and running it the columns are not there. `_vocabulary`'s
	answer is still correct — these are the types — and the form simply asks for
	none of them in particular, which is what an unconfigured society means.
	"""
	types = _vocabulary("Identification Type", "identification_type_name")
	meta = frappe.get_meta("Identification Type")

	if not meta.has_field(application_service.REQUIRED_DOCUMENT_FIELD):
		return types

	rules = {
		row["name"]: row
		for row in frappe.get_all(
			"Identification Type",
			filters={"is_active": 1},
			fields=[
				"name",
				application_service.REQUIRED_DOCUMENT_FIELD,
				application_service.DOCUMENT_ATTACHMENT_FIELD,
				application_service.DOCUMENT_MINIMUM_AGE_FIELD,
			],
		)
	}

	return [
		{
			**row,
			"is_required": bool(rules.get(row["key"], {}).get(application_service.REQUIRED_DOCUMENT_FIELD)),
			"requires_attachment": bool(
				rules.get(row["key"], {}).get(application_service.DOCUMENT_ATTACHMENT_FIELD)
			),
			"minimum_age": cint(rules.get(row["key"], {}).get(application_service.DOCUMENT_MINIMUM_AGE_FIELD))
			or None,
		}
		for row in types
	]


def _languages() -> list[dict]:
	"""Frappe's own Language list, whole.

	**`enabled` is deliberately not filtered on, and that is a correction.** It
	means "offered as a language this site's interface is translated into", which
	is a different question from "languages this applicant speaks". Frappe ships
	its list with most rows disabled — Kiswahili among them — so filtering on it
	told a Kenyan volunteer that the language half the country speaks was not on
	the form. A society that wants more than the shipped list adds Language rows,
	the same way it adds a skill.

	Shaped identically to `_vocabulary` so the frontend renders one kind of
	control rather than one per vocabulary, and carries no description because
	the doctype has none.
	"""
	rows = frappe.get_all(
		"Language",
		fields=["name", "language_name"],
		order_by="language_name asc",
	)

	return [
		{"key": row["name"], "label": row["language_name"] or row["name"], "description": None}
		for row in rows
	]


def _default_citizenship() -> str | None:
	"""What the citizenship question should already be answered with.

	The same society setting `application_service.default_country_of_citizenship`
	applies on insert, read here so the form shows the answer rather than leaving
	a required field blank and filling it in silently afterwards.
	"""
	from vmmsx.volunteer.services import society

	return society.default_citizenship_country()


@frappe.whitelist()
def get_application(name: str) -> dict:
	"""Where an application stands, and where its approval stands.

	Two DTOs rather than one merged dict: the second is the engine's own, and it
	decides for itself how much of the approver list this caller may see.
	"""
	application = _readable(APPLICATION_DOCTYPE, name)

	return {
		**application_service.status(application),
		"approval": application_service.approval_dto(application),
	}


@frappe.whitelist()
def get_decision(name: str) -> dict:
	"""The coordinator's structured decision picture for one application.

	Everything Part 4 asks a coordinator to see in one queryable dict — identity,
	citizenship, residency, Serving Branch, skills, languages, availability,
	motivation, prior experience and the mandatory identification — rather than
	a wall of free text. Permission is the ordinary read check on the
	application itself; there is no second door into it.
	"""
	application = _readable(APPLICATION_DOCTYPE, name)

	return application_service.decision_dto(application)


@frappe.whitelist()
def get_volunteer(name: str) -> dict:
	"""Who a volunteer is — assembled from Red Profile at the moment of asking."""
	return volunteer_service.profile_dto(_readable(VOLUNTEER_DOCTYPE, name))


@frappe.whitelist()
def get_verification(name: str) -> dict:
	"""How this volunteer came to be one, read from their application right now.

	The volunteer page's approval trail. Separate from `get_volunteer` rather
	than folded into it because the two answer different questions from
	different records — who this person is, and what the society decided about
	them — and a caller wanting only the first should not pay for the second.
	"""
	return application_service.verification_dto(_readable(VOLUNTEER_DOCTYPE, name))


@frappe.whitelist()
def get_dossier(name: str, as_of: str | None = None) -> dict:
	"""Everything a coordinator needs about one volunteer, in one read.

	The complete current picture plus the history behind it, so that deciding
	about somebody does not mean opening their application in one tab, their
	certifications in another and a deployment list in a third. Seven blocks:

	    identity          who they are, live from Red Profile, plus where they
	                      serve and where they live, under names that differ
	    capabilities      what they can do now, from the volunteer's own record
	    certifications    what they hold, with the lapse derived per row
	    deployability     whether they may be sent, derived from the two above
	    deployments       what they have been sent on, from the roster
	    time              what they have given, totalled and recent
	    application       what they said when they applied, and who verified it

	**One call rather than seven**, and that is not only about round trips: every
	block is derived, and blocks derived at seven different instants can
	contradict each other. A page that showed a certification as current beside a
	deployability indicator computed a second later, after midnight passed, would
	be wrong in the way that is hardest to notice. Here `as_of` is resolved once
	and every derived answer on the screen is answered as at the same moment.

	**Composed, never merged.** Each block is the DTO its own service already
	builds, nested under its own key, so nothing here re-derives anything and no
	block can quietly overwrite a field of another's. In particular the
	volunteer's current skills and the skills they declared when applying are in
	two different blocks and are never reconciled: one is what is true, the other
	is what was claimed, and a coordinator comparing them is the point.

	Permission is the ordinary read check on the volunteer, through `_readable`
	— which is Frappe's roles, core's geo scoping, and the holder's own bypass.
	There is no second door: everything below is about a volunteer the caller
	has already been allowed to open.
	"""
	from frappe.utils import getdate, today

	from vmmsx.api import person
	from vmmsx.deployment.services import participation
	from vmmsx.volunteer.services import capabilities
	from vmmsx.volunteer.services import card as volunteer_card

	volunteer = _readable(VOLUNTEER_DOCTYPE, name)
	# Resolved once, here, and passed to every derivation below so the whole
	# page answers as at one instant.
	as_of = getdate(as_of or today())

	return {
		"volunteer": volunteer.name,
		"as_of": as_of,
		"identity": volunteer_service.profile_dto(volunteer, as_of=as_of),
		"capabilities": capabilities.current(volunteer),
		"certifications": _certification_rows(volunteer.name, as_of),
		"deployability": certification.deployability(volunteer, as_of=as_of),
		# The roster is the deployment module's, and so is the join back to it.
		"deployments": participation.history_of(volunteer.name),
		"time": timelog.summary(volunteer.name),
		"application": application_service.verification_dto(volunteer),
		# Which of the society's registers this person is in — so the page can
		# say "also a member" instead of sending a coordinator to search the
		# other register for the name. Composed here rather than in the
		# volunteer module, which must not know the member module exists; see
		# `api/person.py`. A person in no other register is the ordinary case.
		"registers": person.registers(volunteer.red_profile),
		# Whether there is a card to reprint at all, asked of the same function
		# `cards.download_card` asserts on. `card.assert_holds`'s own docstring
		# asks for this: shared by the screen and the download so the two cannot
		# come to disagree about who has one. A screen offering a button the
		# server would refuse is worse than no button.
		"holds_card": volunteer_card.holds_card(volunteer),
		# Whether the reader may work the acts, answered by the same check the
		# acts make. A surface draws its buttons from this and decides nothing
		# itself; see `_can_act`. The holder reading their own dossier gets
		# `False` here, which is the `_readable` / `_writable` split showing
		# through to the screen.
		"can_act": _can_act(volunteer),
	}


@frappe.whitelist()
def find_volunteers(
	skills: list | None = None,
	languages: list | None = None,
	availability: list | None = None,
	geo_node: str | None = None,
	status: str | None = None,
	search: str | None = None,
	limit: int = 100,
	offset: int = 0,
) -> dict:
	"""Find volunteers by what they can do, **inside the caller's own scope**.

	The question a coordinator staffing something actually asks: who has this
	skill, speaks one of these languages, is free at these times, and is
	somewhere I am responsible for. It is answerable at all because those three
	are structured vocabularies on the volunteer record rather than sentences.

	**Scope is not a filter this endpoint applies; it is the floor it stands
	on.** `capabilities.search()` ends in `frappe.get_list`, which runs core's
	permission query condition for `VMMS Volunteer`. Every capability argument
	narrows that result and none of them widens it, so a coordinator cannot
	reach a volunteer outside their geo scope by naming a skill — or by naming
	`geo_node`, which narrows further still.

	`search` is the same question asked the other way round — by a person's name
	or a volunteer's docname, for a coordinator who knows who they mean and not
	what the record is called. It narrows the same scoped read, so it is not a
	way to reach somebody outside the caller's own area either.

	`offset` pages through the same scoped result and `total` says how many there
	are to page through. **`count` is the rows on this page and `total` is the
	whole match**, which is why they are two fields rather than one: a pager
	labelled with the page's own length would report "1 of 1" on every page.

	Returns explicit rows built field by field, not the documents.
	"""
	from vmmsx.volunteer.services import capabilities

	criteria = {
		"skills": skills,
		"languages": languages,
		"availability": availability,
		"geo_node": geo_node,
		"status": status,
		"search": search,
	}

	names = capabilities.search(**criteria, limit=limit, offset=offset)

	return {
		"count": len(names),
		# Counted through the same scoped read and the same filters — see
		# `capabilities.count`, which shares `_search_filters` with the page
		# above so the two cannot describe different questions.
		"total": capabilities.count(**criteria),
		"volunteers": [_match_row(frappe.get_doc(VOLUNTEER_DOCTYPE, name)) for name in names],
	}


def _match_row(volunteer) -> dict:
	"""One search result: enough to choose somebody, and nothing more.

	Deliberately thinner than the dossier. A list of candidates is a list of
	people a coordinator is deciding *between*, and handing back everybody's
	full certification history to answer "who could do this" would disclose far
	more than the question needs. Opening one of them is a second, checked read.
	"""
	from vmmsx.volunteer.services import capabilities, certification, identity

	return {
		"volunteer": volunteer.name,
		"red_profile": volunteer.red_profile,
		"full_name": identity.display_name(volunteer),
		# The face belongs to "enough to choose somebody" just as much as the
		# name does: a list of candidates is a list a coordinator is *scanning*,
		# and a photograph is how they pick out the person they already know
		# from the four others with a similar name. Read through the same
		# allow-list as everything else and stored nowhere. None is ordinary —
		# the surface draws initials.
		"photo": identity.read(volunteer, ("profile_photo",)).get("profile_photo"),
		"status": volunteer.status,
		# When they joined. On the row rather than only in the dossier because
		# the active register shows it as a column: a coordinator scanning a
		# branch's volunteers is reading standing and length of service
		# together, and a column that made them open each record to find the
		# second is a column that is not there.
		"joined_on": volunteer.joined_on,
		**capabilities.placement(volunteer),
		**capabilities.current(volunteer),
		# Derived per row, from the same function the dossier uses, so a person
		# is never offered as a candidate by one screen and shown as
		# undeployable by another.
		"deployable": certification.is_deployable(volunteer),
	}


@frappe.whitelist()
def get_deployability(name: str, as_of: str | None = None) -> dict:
	"""Whether this volunteer may be deployed, derived now rather than looked up.

	`as_of` is honoured, so a caller may ask the question about the day of a
	deployment rather than only about today. Nothing about the answer is stored,
	which is what makes asking about another date meaningful at all.
	"""
	return certification.deployability(_readable(VOLUNTEER_DOCTYPE, name), as_of=as_of)


@frappe.whitelist()
def get_certifications(name: str, as_of: str | None = None) -> dict:
	"""What this volunteer holds, with the lapse derived per row.

	`lapsed` on each row is computed here from the expiry date and the date being
	asked about. It is not read from the record, because it is not on the record.
	"""
	volunteer = _readable(VOLUNTEER_DOCTYPE, name)

	return {
		"volunteer": volunteer.name,
		"as_of": as_of,
		"certifications": _certification_rows(volunteer.name, as_of),
	}


# --- the coordinator's acts -----------------------------------------------
#
# Three verbs over a volunteer's standing. Each wraps a service in
# `volunteer/services/volunteer.py` that was already idempotent and already
# owned the write; what was missing was any way to reach one. `status` is
# derived and `read_only` on the doctype, so there was no form field to expose
# and no button anywhere in the app: suspending somebody was a bench console
# call. These are that missing door, and they are deliberately thin — the
# argument for what each one *means* is in the service, not here.


@frappe.whitelist()
def suspend_volunteer(name: str, reason: str | None = None) -> dict:
	"""Stop somebody volunteering without ending their relationship. Idempotent."""
	return volunteer_service.suspend(_writable(VOLUNTEER_DOCTYPE, name), reason)


@frappe.whitelist()
def reinstate_volunteer(name: str, reason: str | None = None) -> dict:
	"""Undo a suspension or an exit, and let the derivation take over again.

	This does not set somebody Active. The service clears the explicit status and
	lets the applications behind the record decide again, which is why a person
	reinstated with no approved application is Prospective rather than Active.
	"""
	return volunteer_service.reinstate(_writable(VOLUNTEER_DOCTYPE, name), reason)


@frappe.whitelist()
def set_volunteer_notes(name: str, notes: str | None = None) -> dict:
	"""The branch's own note about this volunteer.

	**A coordinator's field, which is why it goes through `_writable`.**
	`VMMS Volunteer.notes` has been on the doctype since it was written and no
	DTO carried it, so a note made at the desk could not be read back on the
	register and nobody working from the console could make one. It is the
	register's margin: why somebody is placed where they are, what a branch
	agreed with them, what to remember before deploying them again.

	Not the holder's own field. `_writable` refuses the person the record is
	about, exactly as it does for suspension — a note a coordinator makes about
	somebody is not a note that person may rewrite.

	Blank clears it, deliberately: a note that is no longer true should be
	removable, and the alternative is a field that can only ever grow.
	"""
	volunteer = _writable(VOLUNTEER_DOCTYPE, name)
	volunteer.notes = (notes or "").strip()
	volunteer.save()

	return {"volunteer": volunteer.name, "notes": volunteer.notes}


@frappe.whitelist()
def set_volunteer_capabilities(
	name: str,
	skills: list | None = None,
	languages: list | None = None,
	availability: list | None = None,
) -> dict:
	"""Record what a volunteer can do now, as the branch knows it.

	**The volunteer's own copy, not the application's claim.** That distinction
	is `volunteer/services/capabilities.py`'s whole reason for existing: what
	somebody said when they applied is a claim made once, and what they can do
	now is a fact a branch maintains. The record has always had the second and
	nothing but acceptance ever wrote it — so a volunteer who qualified as a
	first-aider in March had no way to have it recorded, and every search that
	filters on skills went on missing them.

	Each list replaces its table wholesale, and `None` leaves it alone: a screen
	saving one control must not empty the other two. Same shape the registration
	endpoints take, through the same `selector_rows`.

	`_writable`, not `_readable`. Editing what somebody is recorded as being
	able to do is a coordinator's act; a volunteer keeps their own availability
	through `set_my_availability`, which is the possessive door and checks
	ownership instead.
	"""
	from vmmsx.volunteer.services import capabilities

	volunteer = _writable(VOLUNTEER_DOCTYPE, name)

	for field, link_field, supplied in (
		("skills", "skill", skills),
		("languages", "language", languages),
		("availability", "availability_slot", availability),
	):
		if supplied is None:
			continue

		if isinstance(supplied, str):
			supplied = frappe.parse_json(supplied or "[]")

		volunteer.set(field, selector_rows(supplied, link_field))

	volunteer.save()

	return capabilities.current(volunteer)


@frappe.whitelist()
def record_volunteer_exit(name: str, on_date: str | None = None, reason: str | None = None) -> dict:
	"""The person has stopped volunteering. Terminal, and idempotent.

	`on_date` defaults to today inside the service. It is accepted because an
	exit is often recorded after the fact, and dating it the day somebody got
	round to the paperwork would misreport the hours and deployments either side
	of it.
	"""
	return volunteer_service.record_exit(_writable(VOLUNTEER_DOCTYPE, name), on_date, reason)


@frappe.whitelist()
def my_certifications() -> dict | None:
	"""What the logged-in person holds, and whether it still counts. Today.

	The volunteer's own answer to "is my training still current, and may I be
	deployed" — derived on every call, because there is nothing stored to look
	up. `lapsed` on each row and `deployable` above them are both computed here
	from `expiry_date` and today's date; neither is read from any record,
	because neither is on any record.

	**It takes no arguments, including no `as_of`.** The possessive endpoints
	are the shape `my_volunteer` and `my_memberships` already use, and the
	guarantee is that a caller cannot name anybody. A date would not break that
	— but it is not the question a person has about their own training, and a
	coordinator who genuinely needs to ask about the day of a deployment has
	`get_deployability(name, as_of)` and `get_certifications(name, as_of)`,
	which are permission-checked because they name somebody.

	This is also why the workspace shortcut is a URL rather than a list view of
	`VMMS Certification`. A list view can show the completion and expiry dates,
	because those are columns. It cannot show whether the certification has
	lapsed, because that is not a column and deliberately never will be. The
	list is still there, on the workspace's card, for the records themselves.

	None rather than an error for somebody who is not a volunteer, matching
	`my_volunteer`: a logged-in person who has not been accepted yet is an
	ordinary visitor, not a failure.
	"""
	name = _my_volunteer()

	if not name:
		return None

	volunteer = frappe.get_doc(VOLUNTEER_DOCTYPE, name)
	deployability = certification.deployability(volunteer)

	return {
		"volunteer": volunteer.name,
		"as_of": deployability["as_of"],
		"status": volunteer.status,
		# Derived alongside the rows and from the same function matching uses, so
		# a person is never told they are deployable by one screen and excluded
		# from a candidate list by another.
		"deployable": deployability["deployable"],
		"blocking_reasons": deployability["reasons"],
		"certifications": _certification_rows(volunteer.name, deployability["as_of"]),
	}


@frappe.whitelist()
def my_registration_prefill() -> dict | None:
	"""What the registration form's identity section should already show.

	None for somebody core has never met: there is nothing to prefill, and the
	ordinary blank fields are exactly right. For somebody who already has a Red
	Profile — the cross-registration case, a member registering as a volunteer
	too — this is their existing name, phone, gender and date of birth, read
	live and returned so the form can prefill and lock them: don't re-ask who
	they are. Typing something different would change nothing regardless, since
	`registration/services/intake.py` never overwrites what core already knows;
	this is what makes that true on the screen as well as in the database.
	"""
	user = frappe.session.user

	if not user or user == "Guest":
		return None

	profile = frappe.db.get_value("Red Profile", {"user": user}, "name")

	if not profile:
		return None

	person = frappe.db.get_value(
		"Red Profile",
		profile,
		["first_name", "last_name", "phone", "gender", "date_of_birth"],
		as_dict=True,
	)

	return {
		"applicant_first_name": person.first_name,
		"applicant_last_name": person.last_name,
		"applicant_phone": person.phone,
		"applicant_gender": person.gender,
		"applicant_date_of_birth": person.date_of_birth,
	}


@frappe.whitelist()
def my_volunteer() -> dict | None:
	"""The logged-in person's own volunteer record, or None if they have none.

	**Derived from the session on every call, and it takes no arguments.** That
	is the point of the endpoint rather than an implementation detail: a
	`my_volunteer(name)` that accepted a name would be an endpoint for reading
	*anybody's* record wearing a possessive name, and the check stopping that
	would be one more thing to get right. There is nothing to get right here,
	because the caller cannot name anybody. This is the shape `my_memberships`
	and `my_queue` already use.

	None rather than an error for somebody who is not a volunteer: a logged-in
	person who has not been accepted yet is an ordinary visitor, not a failure.

	The approval trail comes back with it, because the first thing an applicant
	wants after registering is to know where their application got to, and asking
	them to call a second endpoint with a name they have not been told is not an
	answer.
	"""
	name = _my_volunteer()

	if not name:
		return None

	volunteer = frappe.get_doc(VOLUNTEER_DOCTYPE, name)

	return {
		**volunteer_service.profile_dto(volunteer),
		"verification": application_service.verification_dto(volunteer),
	}


@frappe.whitelist()
def my_availability() -> dict | None:
	"""When the logged-in person has said they can serve. Takes no person.

	Possessive, like `my_volunteer` above and for the same reason: a volunteer
	holds no Geo Assignment, so every coordinator endpoint fails closed for them,
	and their own availability is the last thing they should have to ask
	permission to see. There is no argument by which a caller could name anybody
	else.

	The society's own windows come back with it, because the screen this serves
	is a grid of days against windows and it cannot draw its own columns.

	None rather than an error for somebody who is not a volunteer, matching
	`my_volunteer`.
	"""
	from vmmsx.volunteer.services import availability

	name = _my_volunteer()

	if not name:
		return None

	return {
		**availability.dto(name),
		"slots": availability.slots(),
	}


@frappe.whitelist()
def set_my_availability(
	days: list | str | None = None,
	available_on_holidays: bool | int | str = False,
	valid_from: str | None = None,
	valid_to: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Write the logged-in person's own weekly availability. Takes no person.

	**Replaces the whole pattern**, because the screen is a grid of tick boxes:
	what arrives is the entire answer, and a box somebody un-ticked has to
	disappear. Merging would make un-ticking impossible, which is the one thing a
	grid has to be able to do.

	The volunteer comes from the session, so there is no argument by which
	somebody could write another person's availability. That is what admits the
	elevated save inside the service — a volunteer holds no permission on their
	own schedule, and granting every volunteer write on the doctype so they could
	edit their own would be far wider than the thing being permitted.
	"""
	from vmmsx.volunteer.services import availability

	name = _my_volunteer()

	if not name:
		frappe.throw(
			frappe._("You do not have a volunteer record, so there is no availability to set."),
			frappe.PermissionError,
		)

	return availability.set_schedule(
		name,
		days=_rows(days),
		available_on_holidays=_availability_flag(available_on_holidays),
		valid_from=valid_from,
		valid_to=valid_to,
		notes=notes,
	)


def _rows(value: list | str | None) -> list[dict]:
	"""The grid's ticked boxes as they arrive over HTTP.

	Frappe hands a whitelisted method either a real list or the JSON it was sent
	as, depending on how the caller framed the request. Anything that is not a
	dict is dropped here rather than reaching the service, which filters again on
	the two keys it actually writes.
	"""
	if isinstance(value, str):
		value = frappe.parse_json(value or "[]")

	if not isinstance(value, list):
		return []

	return [row for row in value if isinstance(row, dict)]


def _availability_flag(value: bool | int | str) -> bool:
	"""A checkbox as it arrives over HTTP.

	`"false"` is a truthy string, so a volunteer un-ticking "available on
	holidays" would otherwise be recorded as having ticked it.
	"""
	if isinstance(value, str):
		return value.strip().lower() not in ("", "0", "false", "no")

	return bool(value)


@frappe.whitelist()
def my_time_logs(limit: int = 30) -> dict | None:
	"""What the logged-in person has logged, totalled and listed. Takes no person.

	The read half of `log_time`, and the same shape as `my_volunteer` and
	`my_memberships`: derived from the session, so there is no argument naming
	somebody and therefore no check to get wrong. The coordinator's view of the
	same information is `get_dossier`, which takes a name and is permission
	checked; this one cannot be pointed at anybody.

	None for somebody who is not a volunteer, matching `my_volunteer`. A person
	whose application has not been accepted yet has no logs and is not a failure.

	`timelog.summary` is the same service the dossier reads, so a volunteer's own
	total and their branch's view of it come from one implementation and cannot
	drift into disagreeing. What is added here is what a *person* needs and a
	report does not: the branch each log was served at, spelled out through core's
	adapter, and the society's own label for the category, because the docname is
	an opaque key and showing somebody `first-aid-duty` is not showing them what
	they did.
	"""
	name = _my_volunteer()

	if not name:
		return None

	summary = timelog.summary(name, limit=_bounded_limit(limit))

	return {**summary, "recent": [_my_log_row(row) for row in summary["recent"]]}


#: The most logs one call returns. A person's own history is browsed, not paged
#: through, and an unbounded read is one somebody eventually runs against a
#: ten-year volunteer.
MAX_LOG_ROWS = 100


def _bounded_limit(limit) -> int:
	try:
		value = int(limit)
	except TypeError, ValueError:
		return 30

	return max(1, min(value, MAX_LOG_ROWS))


def _my_log_row(row: dict) -> dict:
	"""One of the caller's own logs, with the two opaque keys resolved to words.

	Built on top of the service's row rather than replacing it, so the fields a
	log *is* stay defined in one place. `log_type` is deliberately passed through
	untouched and unbranched on: the screen groups by whatever values come back
	and this module compares it to nothing, which is the discipline
	`services/timelog.py` states for the whole app.
	"""
	from onerc_core.geo.services import adapter

	return {
		**row,
		"geo_path": adapter.get_full_path(row["geo_node"]) if row["geo_node"] else None,
		"category_label": (
			frappe.db.get_value("VMMS Time Log Category", row["log_category"], "category_name")
			or row["log_category"]
		)
		if row["log_category"]
		else None,
	}


@frappe.whitelist()
def time_log_options() -> dict:
	"""The society's own vocabulary for classifying time. Configuration, read as-is.

	`VMMS Time Log Category` is an open list a society extends freely and on which
	**no code branches** — this endpoint hands it to the form so a volunteer can
	say what kind of work it was, and that is the whole of its use. The structural
	`log_type` is not offered: the portal files general volunteering, and a
	deployment log names a deployment whose roster the server checks.

	Inactive rows are left out. A category a society has retired should not be
	offered on a new log, and it stays readable on the logs that already carry it.

	`_vocabulary` is the same reader `application_options` uses for skills and
	motivations, because this is the same kind of thing: an active-only list of
	configured rows, keyed by the docname the Link field stores.
	"""
	return {"categories": _vocabulary("VMMS Time Log Category", "category_name")}


@frappe.whitelist()
def log_time(
	volunteer: str,
	geo_node: str,
	activity_date: str,
	hours: float,
	log_type: str = timelog.TYPE_GENERAL,
	log_category: str | None = None,
	deployment: str | None = None,
	notes: str | None = None,
) -> dict:
	"""File one time log.

	`log_type` defaults to the general kind. A caller asking for the deployment
	kind names a deployment, and the ownership rule is enforced by the controller
	— deliberately at the same place a desk user is checked, rather than by a
	second check here that could drift from it. Naming a deployment this
	volunteer is not on is refused, whatever this caller holds: the rule is about
	whether the record is true, not about the caller's authority.
	"""
	frappe.has_permission(TIME_LOG_DOCTYPE, ptype="create", throw=True)

	log = frappe.get_doc(
		{
			"doctype": TIME_LOG_DOCTYPE,
			"volunteer": volunteer,
			"geo_node": geo_node,
			"activity_date": activity_date,
			"hours": hours,
			"log_type": log_type,
			"log_category": log_category,
			"deployment": deployment,
			"notes": notes,
		}
	)
	log.insert()

	return timelog.log_dto(log)


def _certification_rows(volunteer: str, as_of) -> list[dict]:
	"""One explicit row per held certification, with the lapse derived per row.

	Built field by field and shared by both certification endpoints, so that the
	view a volunteer gets of their own training and the view a coordinator gets
	of it cannot drift into disagreeing about what a certification is.

	`certification_type_name` is read live through the service rather than stored
	here, because the key is what code refers to and the name is what a person
	reads, and showing somebody an opaque key is not showing them their
	certification.

	`blocks_deployment` says whether a lapse of this row's type *costs* anything,
	which is what turns a list of dates into something a coordinator can act on:
	a lapsed certification the society holds as a record is a reminder, and a
	lapsed one it holds as a requirement is the reason this person cannot be
	sent. Both are read from the type's own configuration, and both are derived
	here rather than stored, because neither is on the record.
	"""
	return [
		{
			"name": row["name"],
			"certification_type": row["certification_type"],
			"certification_type_name": certification.type_name(row["certification_type"]),
			"completion_date": row["completion_date"],
			"expiry_date": row["expiry_date"],
			"reference_number": row["reference_number"],
			"lapsed": certification.is_lapsed(row, as_of),
			"blocks_deployment": certification.blocks_deployment(row["certification_type"]),
		}
		for row in certification.held(volunteer)
	]


def _readable(doctype: str, name: str):
	"""Load a document the caller is allowed to see. Two ways to be allowed.

	1. **It is theirs.** The session user is the login on the volunteer's Red
	   Profile. A person is entitled to their own record, and requiring a society
	   to hand every volunteer a role that reads the register in order for them
	   to see themselves in it would grant far more than it withholds.
	2. **The ordinary permission layer**, which is Frappe's roles *and* core's
	   geo scoping, because `VMMS Volunteer` is registered as scopeable.

	**Recognised through `Red Profile.user`, never through `owner`.** They are
	different people: a volunteer record is created by the approval that accepted
	the application, so its owner is the approver. Gating on `owner` would give
	the approver a self-service view of everybody they ever accepted and give the
	volunteer nothing.

	Only `VMMS Volunteer` has a holder. An application's access rule is the
	approval engine's person-gate, and it is deliberately not scopeable, so
	nothing here second-guesses it.
	"""
	doc = frappe.get_doc(doctype, name)

	if doctype == VOLUNTEER_DOCTYPE and _is_holder(doc):
		return doc

	doc.check_permission("read")

	return doc


def _writable(doctype: str, name: str):
	"""Load a document the caller may **act on**, as a coordinator.

	The ordinary permission layer and nothing else: Frappe's roles plus core's
	geo scoping, because `VMMS Volunteer` is registered as scopeable.

	**Deliberately not `_readable`, and this is the whole point of it being a
	second function.** `_readable` admits the person the record is *about*,
	which is right for reading and wrong for every verb behind this door. A
	volunteer is entitled to see their own standing; they are not entitled to
	lift their own suspension. Routing the acts through the read helper would
	have handed each of them exactly that, quietly, and it would have looked
	like reuse.

	`write` rather than `read`, because everything here changes the record.
	Mirrors `api/tasks.py::_writable`, which draws the same distinction between
	a door checked by permission and a door checked by ownership.
	"""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")

	return doc


def _can_act(doc) -> bool:
	"""May this caller work the acts above, on **this** record?

	`doc=` is passed, not just the doctype, so the question asked here is exactly
	the one `_writable` enforces: Frappe's roles *and* core's geo scoping applied
	to this document. A doctype-level check would have been almost right, and the
	case it gets wrong is the one worth drawing a button for — somebody who holds
	the society's role but not this branch would have been shown controls that
	then refused them.

	The flag decides what is *painted*; the endpoint re-asks on every call
	regardless. This is the shape `can_edit` on a content surface and `can_act`
	on an approval already use, and it is why no role name reaches either
	surface.
	"""
	return bool(frappe.has_permission(doc.doctype, ptype="write", doc=doc))


def _is_holder(volunteer) -> bool:
	"""Is the session user the person this volunteer record is about?

	The Guest session is refused before anything is looked up: an unauthenticated
	caller is nobody, and letting one fall through to a comparison that would
	"almost certainly" not match is not a check.
	"""
	from vmmsx.volunteer.services import identity

	user = frappe.session.user

	if not user or user == "Guest":
		return False

	return identity.user_of(volunteer) == user


def _my_volunteer() -> str | None:
	"""The VMMS Volunteer record of whoever is logged in, or None.

	Two hops, both a lookup on a unique column: the Red Profile carrying this
	login, and the volunteer satellite hanging off that profile. Neither is
	permitted to be ambiguous — core makes `Red Profile.user` unique and this app
	makes `VMMS Volunteer.red_profile` unique — so there is no tie-breaking to
	specify. The mirror of `api/member.py::_my_member`.
	"""
	user = frappe.session.user

	if not user or user == "Guest":
		return None

	profile = frappe.db.get_value("Red Profile", {"user": user}, "name")

	if not profile:
		return None

	return frappe.db.get_value(VOLUNTEER_DOCTYPE, {"red_profile": profile}, "name")


# How many rows the distinct-branch read will take before it gives up. A ceiling
# on work rather than a page size; past it the figure is `None` and the screen
# omits the tile rather than showing one computed from a truncated read.
_SUMMARY_CEILING = 20_000


@frappe.whitelist()
def register_summary() -> dict:
	"""The active volunteer register's own figures, **inside the caller's scope**.

	Four aggregates, each computed over the whole scoped register rather than
	over a page of it — which is the entire reason this exists. The registry
	screen used to label its page's `total` as a headline figure; a page is not
	a total and a screen that says it is will be believed.

	    active        volunteers whose standing is Active
	    joined_month  of those, the ones whose `joined_on` falls in this month
	    branches      how many distinct serving branches they sit across
	    deployed      how many people are out on an Active deployment right now

	**Scope is the floor, not a filter.** Every read is `frappe.get_list`, which
	runs core's permission query condition; `frappe.get_all` appears nowhere in
	this function. It takes no arguments, so there is nothing a caller could send
	that would widen it.

	`deployed` is counted from the *deployment* side — the assignments on Active
	deployments this caller may read — because that is where the fact lives. It
	is the same `counts_for_many` every deployment listing uses, so this figure
	and the operations screens cannot disagree.
	"""
	from frappe.utils import get_first_day, getdate, today

	from vmmsx.deployment.services import assignment as assignment_service

	active = {"status": "Active"}
	month_start = get_first_day(getdate(today()))

	nodes = frappe.get_list(
		VOLUNTEER_DOCTYPE,
		filters=active,
		limit_page_length=_SUMMARY_CEILING + 1,
		pluck="home_geo_node",
	)
	capped = len(nodes) > _SUMMARY_CEILING

	# **Asked before the read, not caught after it.** `get_list` raises on a
	# doctype the caller has no read permission for at all, and a membership
	# clerk who may see volunteers and may not see deployments must get the three
	# figures they are entitled to rather than an error page. `None` says "not
	# something you can be told" and the screen draws a dash; a zero would say
	# "nobody is deployed", which is a different and false claim. The same rule
	# `api/person.py::registers` follows.
	if frappe.has_permission("VMMS Deployment", "read"):
		running = frappe.get_list(
			"VMMS Deployment",
			filters={"status": "Active"},
			limit_page_length=0,
			pluck="name",
		)
		tallies = assignment_service.counts_for_many(running) if running else {}
		deployed = sum(tally.get("on_deployment", 0) for tally in tallies.values())
		deployments = len(running)
	else:
		deployed = None
		deployments = None

	return {
		"active": _register_count(VOLUNTEER_DOCTYPE, active),
		"joined_month": _register_count(
			VOLUNTEER_DOCTYPE, {**active, "joined_on": (">=", month_start)}
		),
		# None rather than a wrong number: see `_SUMMARY_CEILING`.
		"branches": None if capped else len({node for node in nodes if node}),
		"deployed": deployed,
		"deployments": deployments,
		"capped": capped,
	}


def _register_count(doctype: str, filters: dict) -> int:
	"""How many rows match, through the scoped listing rather than around it.

	`frappe.db.count` would skip core's permission query condition; `get_list`
	runs it. The aggregate is the dict form because Frappe rejects a SQL function
	written as a string in a SELECT.
	"""
	rows = frappe.get_list(doctype, filters=filters, fields=[{"COUNT": "name"}], as_list=True)

	return frappe.utils.cint(rows[0][0]) if rows else 0
