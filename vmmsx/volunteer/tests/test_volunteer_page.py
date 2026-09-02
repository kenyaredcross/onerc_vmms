# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The volunteer page shows a person, and stores none of them.

The register was readable and unusable: a coordinator opening a volunteer saw a
Red Profile docname, a status and a geo node, and had to open a second tab to
find out whose record they were looking at. This suite covers making that page a
working surface, and it is organised around the one property that makes the
approach safe rather than convenient — **everything shown is read at display
time and written nowhere.**

Five things are established:

1. **The readable surface is exactly what was decided.** `identity._READABLE` is
   asserted as a whole tuple, so widening it again fails this suite rather than
   passing quietly. The sensitive set is asserted to be refused out loud.
2. **Nothing is persisted.** Not a column, not a `fetch_from`, not after a read.
   The four newly-surfaced fields are held to the same bar the name and email
   have always been held to.
3. **The heading resolves to the person's name**, and does so from the live DTO
   rather than from anything on the record.
4. **The verification outcome is read from the application every time.**
   Correcting the approval trail changes what the volunteer page says, and
   leaves the volunteer record byte-identical.
5. **The application's narrative fields are optional.** An application carrying
   none of them is valid, because what makes an application valid is a person
   and a place.

Nothing here is mocked. The volunteer that the verification tests read is
produced by the real approval engine, through a real workflow, decided by the
person core resolved.
"""

import json
from pathlib import Path

import frappe

from vmmsx.approvals import states
from vmmsx.approvals.services import contract
from vmmsx.volunteer.services import application as application_service
from vmmsx.volunteer.services import hr, identity
from vmmsx.volunteer.services import volunteer as volunteer_service
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

DECISION_DOCTYPE = "VMMS Approval Decision"

# The whole readable surface, written out. An assertEqual against this tuple is
# the guard the widening asked for: adding a twelfth field fails here, and the
# author has to come and say why, which is the entire point.
EXPECTED_READABLE = (
	"full_name",
	"first_name",
	"middle_name",
	"last_name",
	"email",
	"phone",
	"user",
	"gender",
	"date_of_birth",
	"preferred_language",
	"profile_photo",
	"home_geo_node",
	"country_of_citizenship",
	"citizenship_status",
	"residency_type",
	"country_of_residence",
	"residence_address",
	"vmms_disability_status",
)

# The four the page pass added, kept separately so the tests below can say which
# half of the surface they are about.
NEWLY_SURFACED = ("gender", "date_of_birth", "preferred_language", "profile_photo")

# The eighteenth, and the one that has to be argued for rather than listed.
#
# **It is not core's withheld `disability`.** Core keeps that name off the spine
# for a gated extension it has not built, and `_WITHHELD` still refuses it out
# loud — `test_asking_for_a_withheld_field_is_refused` below is unchanged and
# still passes. `vmms_disability_status` is a different field with a different
# owner: it is vmmsx's own Custom Field, installed by
# `patches/install_disability_fields.py`, and it holds an *answer* to a question
# the applicant was asked on the registration form and could decline.
#
# It is readable because the branch that has to arrange somebody's first shift
# is the one who needs to know whether to ask about adjustments. The free-text
# `vmms_disability_needs` beside it is deliberately **not** here: that is what a
# person chose to write about themselves, and a general reader has no use for
# it — it is read on the record itself, by whoever may open it.
DISCLOSED_WITH_CONSENT = "vmms_disability_status"

# The twelfth, added by the coordinator's view. Home Area is where a person
# *lives*, it is core's field on Red Profile, and the alternative to reading it
# was copying it onto the volunteer — which would have been a second answer to
# where somebody lives. It is held to exactly the same bar as the four above:
# surfaced, never stored. See `test_coordinator_view.py` for the other half.
HOME_AREA = "home_geo_node"

# Core's spelling, from its own Red Profile tests. These are held back for a
# gated extension and are not vmmsx's to show.
GATED_SENSITIVE = ("blood_group", "medical_conditions", "next_of_kin", "disability")

CLIENT_SCRIPT = (
	Path(frappe.get_app_path("vmmsx")) / "vmms_volunteer" / "doctype" / "vmms_volunteer" / "vmms_volunteer.js"
)


class VolunteerPageTestCase(VolunteerTestCase):
	def person(self, handle: str, **profile_values):
		"""A volunteer and the profile behind them, with no application."""
		profile = fixtures.make_profile("Page", handle.title(), **profile_values)
		volunteer = fixtures.make_volunteer(profile, self.society_a["ward"])

		return {"profile": profile, "volunteer": volunteer}

	def a_gender(self) -> str:
		"""Whatever this site calls a gender. The value is never asserted on."""
		existing = frappe.db.get_value("Gender", {}, "name")

		if existing:
			return existing

		return frappe.get_doc({"doctype": "Gender", "gender": "Other"}).insert(ignore_permissions=True).name


# --- 1. the readable surface ----------------------------------------------


class TestTheReadableSurfaceIsExactlyWhatWasDecided(VolunteerPageTestCase):
	def test_the_allow_list_is_the_agreed_set_and_no_more(self):
		"""Whole-tuple equality, deliberately. A superset is a failure too.

		The point of an allow-list is that widening it is a decision somebody
		takes. `assertIn` per field would let a twelfth arrive unnoticed, which
		is exactly the drift this guard exists to stop.
		"""
		self.assertEqual(identity._READABLE, EXPECTED_READABLE)

	def test_the_four_new_fields_are_in_it(self):
		"""Stated separately so the widening is legible in the suite, not just the diff."""
		for fieldname in NEWLY_SURFACED:
			self.assertIn(fieldname, identity._READABLE)

	def test_the_disability_answer_is_readable_and_the_free_text_is_not(self):
		"""Two different things, and only one of them is a general reader's.

		The answer says whether to ask about adjustments; the description is what
		somebody wrote about themselves. See `DISCLOSED_WITH_CONSENT`.
		"""
		self.assertIn(DISCLOSED_WITH_CONSENT, identity._READABLE)
		self.assertNotIn("vmms_disability_needs", identity._READABLE)

	def test_cores_withheld_disability_field_is_still_refused(self):
		"""Widening ours did not open core's. They are different names."""
		self.assertIn("disability", identity._WITHHELD)
		self.assertNotIn("disability", identity._READABLE)

	def test_the_sensitive_set_is_not_readable(self):
		for fieldname in GATED_SENSITIVE:
			self.assertNotIn(
				fieldname,
				identity._READABLE,
				f"{fieldname} belongs to core's gated extension and is not vmmsx's to surface",
			)

	def test_the_sensitive_set_is_named_rather_than_merely_absent(self):
		"""Absence is an omission; a named list is a decision."""
		self.assertEqual(identity._WITHHELD, GATED_SENSITIVE)

	def test_asking_for_a_withheld_field_is_refused_out_loud(self):
		"""Not silently dropped. A caller handed a dict with the key missing
		renders an empty row and nobody learns anything; a caller that is refused
		is told this is not vmmsx's data to show.
		"""
		person = self.person("withheld")

		for fieldname in GATED_SENSITIVE:
			with self.assertRaises(PermissionError):
				identity.read(person["volunteer"], (fieldname,))

	def test_a_withheld_field_smuggled_in_beside_a_readable_one_is_still_refused(self):
		person = self.person("smuggled")

		with self.assertRaises(PermissionError):
			identity.read(person["volunteer"], ("full_name", "next_of_kin"))

	def test_the_reader_returns_the_new_fields_from_the_spine(self):
		gender = self.a_gender()
		person = self.person("surfaced")

		frappe.db.set_value(
			"Red Profile",
			person["profile"],
			{"gender": gender, "date_of_birth": "1990-01-01", "preferred_language": "sw"},
		)

		read = identity.read(person["volunteer"])

		self.assertEqual(read["gender"], gender)
		self.assertEqual(str(read["date_of_birth"]), "1990-01-01")
		self.assertEqual(read["preferred_language"], "sw")

	def test_the_dto_carries_them_to_the_card(self):
		"""What the client script actually renders, asserted at its source."""
		gender = self.a_gender()
		person = self.person("card")

		frappe.db.set_value(
			"Red Profile",
			person["profile"],
			{"gender": gender, "date_of_birth": "1985-06-15", "preferred_language": "fr"},
		)
		person["volunteer"].reload()

		dto = volunteer_service.profile_dto(person["volunteer"])

		self.assertEqual(dto["full_name"], frappe.db.get_value("Red Profile", person["profile"], "full_name"))
		self.assertEqual(dto["gender"], gender)
		self.assertEqual(str(dto["date_of_birth"]), "1985-06-15")
		self.assertEqual(dto["preferred_language"], "fr")
		self.assertIn("profile_photo", dto)

	def test_a_correction_on_the_spine_is_visible_immediately(self):
		"""The whole reason the card is a live read rather than a copy."""
		person = self.person("corrected")

		frappe.db.set_value("Red Profile", person["profile"], "preferred_language", "en")
		self.assertEqual(volunteer_service.profile_dto(person["volunteer"])["preferred_language"], "en")

		frappe.db.set_value("Red Profile", person["profile"], "preferred_language", "sw")
		self.assertEqual(volunteer_service.profile_dto(person["volunteer"])["preferred_language"], "sw")


# --- 2. nothing is persisted ----------------------------------------------


class TestNothingIsPersistedOntoTheVolunteer(VolunteerPageTestCase):
	def test_no_identity_field_exists_on_the_doctype(self):
		"""The old guard, extended to cover everything the page now shows.

		Surfacing a field and storing it are different decisions, and this is the
		one that says the second was not taken. Every name below is a field the
		volunteer page renders; not one of them is a field on this record.
		"""
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)
		identity_names = (
			"first_name",
			"middle_name",
			"last_name",
			"full_name",
			"email",
			"phone",
			"employee_name",
			*NEWLY_SURFACED,
		)

		for fieldname in identity_names:
			self.assertIsNone(
				meta.get_field(fieldname), f"the volunteer has grown an identity field: {fieldname}"
			)

	def test_no_identity_column_exists_in_the_table(self):
		"""Below the meta, in the database itself.

		A Custom Field somebody added on a site would not show in the JSON but
		would show here, and a fetched copy would sit in this list just as
		comfortably as a typed one.
		"""
		columns = set(frappe.db.get_table_columns(fixtures.VOLUNTEER_DOCTYPE))

		for fieldname in ("full_name", "email", "phone", *NEWLY_SURFACED):
			self.assertNotIn(fieldname, columns, f"the volunteer stores {fieldname} in a column")

	def test_no_field_fetches_from_anywhere(self):
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)

		self.assertEqual(
			[field.fieldname for field in meta.fields if field.fetch_from],
			[],
			"the volunteer fetches a field from somewhere — identity by another name",
		)

	def test_the_display_blocks_are_html_and_back_no_column(self):
		"""Every block the client script fills holds nothing at all.

		Seven of them now rather than three. Each one is a derived or live-read
		answer, and the moment one acquired a column it would start being able to
		disagree with what it is derived from.
		"""
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)
		columns = set(frappe.db.get_table_columns(fixtures.VOLUNTEER_DOCTYPE))

		for fieldname in (
			"identity_card",
			"deployability_indicator",
			"certifications_held",
			"deployment_history",
			"time_served",
			"verification_outcome",
			"declared_at_application",
		):
			field = meta.get_field(fieldname)

			self.assertIsNotNone(field, f"the page block {fieldname} is missing")
			self.assertEqual(field.fieldtype, "HTML")
			self.assertNotIn(fieldname, columns, f"{fieldname} acquired a column")

	def test_rendering_the_card_writes_nothing_to_the_record(self):
		"""The assertion that makes 'live read' mean something.

		The whole row is compared, not just `modified`: a write that also touched
		the timestamp would be caught either way, but a write that did not would
		slip past a timestamp check alone.
		"""
		gender = self.a_gender()
		person = self.person("no_write")

		frappe.db.set_value(
			"Red Profile", person["profile"], {"gender": gender, "date_of_birth": "1975-03-02"}
		)
		person["volunteer"].reload()

		before = frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, person["volunteer"].name, "*", as_dict=True)
		versions_before = frappe.db.count(
			"Version", {"ref_doctype": fixtures.VOLUNTEER_DOCTYPE, "docname": person["volunteer"].name}
		)

		volunteer_service.profile_dto(person["volunteer"])
		identity.read(person["volunteer"])

		after = frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, person["volunteer"].name, "*", as_dict=True)

		self.assertEqual(dict(before), dict(after), "reading the person changed the volunteer record")
		self.assertEqual(
			frappe.db.count(
				"Version", {"ref_doctype": fixtures.VOLUNTEER_DOCTYPE, "docname": person["volunteer"].name}
			),
			versions_before,
		)


class TestTheHRSeamDidNotWidenWithTheDisplay(VolunteerPageTestCase):
	"""The interaction that had to be got right.

	Before this change, what kept gender and date of birth out of an employment
	register was their absence from `identity._READABLE`. The page needs both, so
	that guarantee had to move somewhere it still means something: `hr._OUTBOUND`,
	the list of what this app hands to HR. Showing a fact to a coordinator and
	writing it into a payroll system are different decisions, and only the first
	was taken.
	"""

	def test_the_outbound_list_is_narrower_than_the_readable_one(self):
		self.assertTrue(set(hr._OUTBOUND) < set(identity._READABLE))

	def test_the_two_fields_hr_wants_are_not_in_it(self):
		self.assertNotIn("gender", hr._OUTBOUND)
		self.assertNotIn("date_of_birth", hr._OUTBOUND)

	def test_the_seam_reads_only_the_outbound_set_even_though_more_is_readable(self):
		"""Narrowed at the read, not filtered afterwards.

		So there is no moment at which the HR path is holding a person-fact it
		has no business sending on.
		"""
		gender = self.a_gender()
		person = self.person("outbound")

		frappe.db.set_value(
			"Red Profile", person["profile"], {"gender": gender, "date_of_birth": "1990-01-01"}
		)
		person["volunteer"].reload()

		seam_read = identity.read(person["volunteer"], hr._OUTBOUND)
		page_read = identity.read(person["volunteer"])

		self.assertNotIn("gender", seam_read)
		self.assertNotIn("date_of_birth", seam_read)
		self.assertEqual(page_read["gender"], gender, "the page lost the field the seam withholds")


# --- 3. the heading --------------------------------------------------------


class TestTheHeadingIsThePersonsName(VolunteerPageTestCase):
	def test_the_name_the_heading_uses_is_the_profiles(self):
		"""The value the client script sets the title to, asserted at its source."""
		person = self.person("heading")
		expected = frappe.db.get_value("Red Profile", person["profile"], "full_name")

		self.assertEqual(volunteer_service.profile_dto(person["volunteer"])["full_name"], expected)
		self.assertNotEqual(
			volunteer_service.profile_dto(person["volunteer"])["full_name"],
			person["volunteer"].name,
			"the heading would show the volunteer's docname",
		)

	def test_the_name_is_not_the_red_profile_docname_either(self):
		"""The failure being fixed: the heading read RP-00042."""
		person = self.person("not_a_code")

		self.assertNotEqual(
			volunteer_service.profile_dto(person["volunteer"])["full_name"], person["profile"]
		)

	def test_renaming_the_person_renames_the_heading(self):
		person = self.person("renamed")

		profile = frappe.get_doc("Red Profile", person["profile"])
		profile.first_name = "Renamed"
		profile.save()

		self.assertEqual(
			volunteer_service.profile_dto(person["volunteer"])["full_name"],
			frappe.db.get_value("Red Profile", person["profile"], "full_name"),
		)

	def test_the_stored_title_field_is_not_an_identity_field(self):
		"""The mechanism is the script, and this is why.

		A virtual title field holding the name was the other option and was not
		taken: it would put an identity value on this doctype's meta, which is
		the thing the module refuses. `title_field` therefore still points at the
		link, and the readable heading is produced at display time from a value
		that was never stored.
		"""
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)

		self.assertEqual(meta.title_field, "red_profile")
		self.assertEqual(meta.get_field(meta.title_field).fieldtype, "Link")

	def test_the_client_script_sets_the_heading_from_the_live_name(self):
		source = CLIENT_SCRIPT.read_text()

		self.assertIn("set_title", source, "nothing in the script overrides the heading")
		self.assertIn("full_name", source, "the heading is not built from the person's name")
		self.assertIn("vmmsx.api.volunteer.get_dossier", source, "the name is not read from the DTO")

	def test_the_desk_actually_loads_the_in_repo_script(self):
		"""Not merely that the file exists — that Frappe serves it.

		An in-repo form script is loaded by path from the doctype's own folder
		(frappe/desk/form/meta.py). Asserting through that loader is what proves
		the mechanism is the committed file rather than a Client Script record
		somebody made on one site.
		"""
		from frappe.desk.form.meta import get_meta as get_form_meta

		served = get_form_meta(fixtures.VOLUNTEER_DOCTYPE, cached=False).get("__js") or ""

		self.assertIn("vmmsx_volunteer", served)
		self.assertIn("vmmsx.api.volunteer.get_dossier", served)

	def test_the_script_is_a_file_in_the_repository(self):
		self.assertTrue(CLIENT_SCRIPT.exists(), f"{CLIENT_SCRIPT} is missing")


# --- 4. the verification outcome ------------------------------------------


class VerifiedVolunteerTestCase(VolunteerPageTestCase):
	"""A volunteer produced by the real engine, so there is a real trail to read."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_workflow()
		fixtures.grant_doctype_access(fixtures.APPLICATION_DOCTYPE, fixtures.APPROVER_ROLE)

		cls.approver = cls.scoped_user("page_approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])

	def verified(self, handle: str, **application_values):
		"""An approved application and the volunteer it produced."""
		from vmmsx.approvals.services import engine

		profile = fixtures.make_profile("Verified", handle.title())
		application = fixtures.make_application(profile, self.society_a["ward"], **application_values)

		application_service.submit(application)

		with fixtures.acting_as(self.approver):
			engine.decide(
				frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name),
				states.DECISION_APPROVED,
			)

		application.reload()
		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, application.volunteer)

		return {"profile": profile, "application": application, "volunteer": volunteer}


class TestTheVerificationOutcomeIsReadLive(VerifiedVolunteerTestCase):
	def test_it_reports_the_application_that_verified_them(self):
		case = self.verified("reported")

		dto = application_service.verification_dto(case["volunteer"])

		self.assertEqual(dto["application"], case["application"].name)
		self.assertEqual(dto["approval_state"], states.APPROVED)
		self.assertEqual(dto["application_count"], 1)

	def test_it_reports_who_decided_and_when(self):
		case = self.verified("decided")

		dto = application_service.verification_dto(case["volunteer"])

		self.assertEqual(len(dto["decisions"]), 1)

		decision = dto["decisions"][0]

		self.assertEqual(decision["approver"], self.approver)
		self.assertEqual(decision["decision"], states.DECISION_APPROVED)
		self.assertIsNotNone(decision["decided_on"])

	def test_correcting_the_trail_changes_what_the_page_says(self):
		"""The live-read assertion. Nothing was re-derived and nothing re-saved.

		The reason on the decision is corrected on the application, which is
		where the approval trail lives, and the volunteer page reports the
		correction on the next read because that is the only place it ever reads
		it from.
		"""
		case = self.verified("corrected")
		row = frappe.db.get_value(
			DECISION_DOCTYPE,
			{"parent": case["application"].name, "parenttype": fixtures.APPLICATION_DOCTYPE},
			"name",
		)

		self.assertIsNone(application_service.verification_dto(case["volunteer"])["decisions"][0]["reason"])

		frappe.db.set_value(DECISION_DOCTYPE, row, "reason", "recorded after review")
		frappe.clear_document_cache(fixtures.APPLICATION_DOCTYPE, case["application"].name)

		self.assertEqual(
			application_service.verification_dto(case["volunteer"])["decisions"][0]["reason"],
			"recorded after review",
		)

	def test_the_correction_stored_nothing_on_the_volunteer(self):
		"""The other half: the page changed and the record did not."""
		case = self.verified("untouched")
		row = frappe.db.get_value(
			DECISION_DOCTYPE,
			{"parent": case["application"].name, "parenttype": fixtures.APPLICATION_DOCTYPE},
			"name",
		)

		application_service.verification_dto(case["volunteer"])
		before = frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, case["volunteer"].name, "*", as_dict=True)

		frappe.db.set_value(DECISION_DOCTYPE, row, "reason", "changed again")
		frappe.clear_document_cache(fixtures.APPLICATION_DOCTYPE, case["application"].name)
		application_service.verification_dto(case["volunteer"])

		after = frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, case["volunteer"].name, "*", as_dict=True)

		self.assertEqual(dict(before), dict(after))

	def test_the_state_it_reports_is_the_applications_own(self):
		"""Read through the engine's contract accessor, not from a copy."""
		case = self.verified("state")

		self.assertEqual(
			application_service.verification_dto(case["volunteer"])["approval_state"],
			contract.state(frappe.get_doc(fixtures.APPLICATION_DOCTYPE, case["application"].name)),
		)

	def test_the_volunteer_holds_no_approval_state_of_its_own(self):
		"""There is one answer to whether somebody was verified, and it is not here."""
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)

		for fieldname in (contract.STATE_FIELD, contract.STAGE_FIELD, "approval_decisions"):
			self.assertIsNone(meta.get_field(fieldname), f"the volunteer has grown {fieldname}")

	def test_a_volunteer_with_no_application_is_reported_as_such(self):
		"""Ordinary, not an error. A society's own data load produces these."""
		person = self.person("no_application")

		dto = application_service.verification_dto(person["volunteer"])

		self.assertIsNone(dto["application"])
		self.assertEqual(dto["application_count"], 0)
		self.assertEqual(dto["decisions"], [])
		self.assertIsNone(dto["declared"])

	def test_the_endpoint_returns_it_through_a_permission_check(self):
		case = self.verified("endpoint")

		from vmmsx.api import volunteer as volunteer_api

		dto = volunteer_api.get_verification(case["volunteer"].name)

		self.assertEqual(dto["application"], case["application"].name)


# --- 5. what the applicant declared ---------------------------------------


class TestTheDeclaredFields(VerifiedVolunteerTestCase):
	def test_all_are_optional(self):
		"""A thin application is a valid application.

		What makes one valid is a person, a place, and what submission itself
		requires (identification, a completed residency answer). What somebody
		declares about their volunteering is context for the approver, and a
		society that collects none of it still has a working register.
		"""
		profile = fixtures.make_profile("Thin", "Applicant")
		application = fixtures.make_application(profile, self.society_a["ward"])

		self.assertTrue(frappe.db.exists(fixtures.APPLICATION_DOCTYPE, application.name))
		self.assertEqual(application.skills, [])
		self.assertEqual(application.languages, [])
		self.assertEqual(application.availability, [])
		self.assertEqual(application.motivation, [])
		self.assertIsNone(application.prior_experience)

	def test_the_schema_agrees_that_they_are_optional(self):
		meta = frappe.get_meta(fixtures.APPLICATION_DOCTYPE)

		for fieldname in ("skills", "languages", "availability", "motivation", "prior_experience"):
			field = meta.get_field(fieldname)

			self.assertIsNotNone(field, f"{fieldname} is missing from the application")
			self.assertFalse(field.reqd, f"{fieldname} is required, and it must not be")

	def test_skills_languages_availability_and_motivation_are_structured_vocabularies(self):
		"""Table MultiSelects of a society's own doctypes, not free text.

		This replaces the free-text declared_skills the application used to
		carry: a coordinator can filter volunteers by one of these because each
		is a Link to a real, society-editable record, and a sentence never was.
		prior_experience alone stays narrative — see its own field description.
		"""
		meta = frappe.get_meta(fixtures.APPLICATION_DOCTYPE)

		expected_options = {
			"skills": "VMMS Skill Selector",
			"languages": "VMMS Language Selector",
			"availability": "VMMS Availability Selector",
			"motivation": "VMMS Motivation Selector",
		}

		for fieldname, options in expected_options.items():
			field = meta.get_field(fieldname)
			self.assertEqual(field.fieldtype, "Table MultiSelect")
			self.assertEqual(field.options, options)

		prior_experience = meta.get_field("prior_experience")
		self.assertEqual(prior_experience.fieldtype, "Small Text")
		self.assertFalse(prior_experience.options)

	def test_they_persist_what_was_written(self):
		skill = fixtures.make_skill()
		profile = fixtures.make_profile("Declaring", "Applicant")
		application = fixtures.make_application(
			profile,
			self.society_a["ward"],
			skills=[{"skill": skill.name}],
			prior_experience="Two floods with another society",
		)

		stored = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name)

		self.assertEqual([row.skill for row in stored.skills], [skill.name])
		self.assertEqual(stored.prior_experience, "Two floods with another society")

	def test_the_api_carries_them_in(self):
		"""The desk and the API can both collect them today; the registration
		form collects them through this same endpoint.
		"""
		from vmmsx.api import volunteer as volunteer_api

		skill = fixtures.make_skill()
		motivation = fixtures.make_motivation()
		profile = fixtures.make_profile("Api", "Applicant")
		person = frappe.get_doc("Red Profile", profile)
		person.country_of_citizenship = fixtures.test_country()
		person.residency_type = "Local"
		person.home_geo_node = self.society_a["ward"]
		person.append(
			"identifications",
			{
				"id_type": fixtures.make_identification_type(),
				"id_number": "API-TEST-0001",
				"is_primary": 1,
			},
		)
		person.save()

		result = volunteer_api.apply_to_volunteer(
			red_profile=profile,
			geo_node=self.society_a["ward"],
			skills=[skill.name],
			motivation=[motivation.name],
			prior_experience="School cadet",
			# What a coordinator transcribes off the signed form. The clerk's
			# door is held to the same standard as the browser, so it carries
			# the same two things.
			declarations_accepted=fixtures.required_declarations(),
			emergency_contacts=fixtures.emergency_contact(),
		)

		stored = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, result["name"])

		self.assertEqual([row.skill for row in stored.skills], [skill.name])
		self.assertEqual([row.motivation for row in stored.motivation], [motivation.name])
		self.assertEqual(stored.prior_experience, "School cadet")

	def test_the_volunteer_page_shows_them_as_declared(self):
		skill = fixtures.make_skill()
		case = self.verified(
			"declaring",
			skills=[{"skill": skill.name}],
			prior_experience="Ten years elsewhere",
		)

		declared = application_service.verification_dto(case["volunteer"])["declared"]

		self.assertEqual(declared["skills"], [{"key": skill.name, "label": skill.skill_name}])
		self.assertEqual(declared["prior_experience"], "Ten years elsewhere")

	def test_the_point_in_time_ones_are_not_stored_on_the_volunteer(self):
		"""Motivation and prior experience stay where they were said, and only there.

		**This test used to cover five fields and now covers two, and the
		narrowing is the decision rather than an erosion of it.** Skills,
		languages and availability moved onto the volunteer deliberately: they
		are current capabilities, they change while somebody volunteers, and
		keeping them readable only from a settled application made them
		uneditable. See `test_coordinator_view.py`, which asserts they are there
		and that editing them does not touch the application.

		These two did not move, and the rule that kept them is the one that
		moved the others: *if this changed tomorrow, would the application have
		been wrong?* Why somebody applied is a fact about the applying. A
		current-state copy of it on the register would be a field somebody could
		edit, and editing it would be rewriting history rather than recording a
		change.
		"""
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)

		for fieldname in ("motivation", "prior_experience"):
			self.assertIsNone(meta.get_field(fieldname), f"the volunteer has grown {fieldname}")

	def test_the_identification_is_not_stored_on_the_volunteer_either(self):
		"""Captured on Red Profile and read live wherever it is shown.

		Three places it legitimately is, and the volunteer register is not one of
		them. It is the applicant's evidence of who they were on the day, and
		core's Red Profile already holds the person's identifications.
		"""
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)

		for fieldname in ("id_type", "id_number", "identifications"):
			self.assertIsNone(meta.get_field(fieldname), f"the volunteer has grown {fieldname}")

	def test_the_page_labels_them_as_a_point_in_time_declaration(self):
		"""The distinction has to reach the screen, not just the docstrings.

		Once structured skills and certifications land, what the volunteer can do
		now supersedes what they said when they applied. A reader must not be
		able to mistake the second for the first.
		"""
		source = CLIENT_SCRIPT.read_text()

		self.assertIn("Declared by the applicant", source)
		self.assertIn("not what this volunteer is currently able to do", source)

	def test_the_form_says_so_too(self):
		definition = json.loads(
			(
				Path(frappe.get_app_path("vmmsx"))
				/ "vmms_volunteer"
				/ "doctype"
				/ "vmms_volunteer"
				/ "vmms_volunteer.json"
			).read_text()
		)
		labels = {
			field.get("fieldname"): field.get("label")
			for field in definition["fields"]
			if field.get("fieldtype") == "Section Break"
		}

		self.assertEqual(labels.get("declaration_section"), "Declared at Application")
