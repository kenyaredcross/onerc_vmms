# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What somebody has already done, and the rules that make it safe to ask.

`install_background_fields` put seven fields on core's Red Profile — profession,
education, training, experience, licences, driving licences, referees — in place
of the one free-text box the registration used to offer for all of it.

Three things have to stay true, and none of them is obvious from the field list:

* **None of it is required.** No completion rule moved and `assert_ready` gained
  nothing. A registration that fills in none of this is as valid as one that
  fills in all of it, and the suite asserts that rather than trusting it.
* **A caller may only set what the allow-list names.** These arrive as loose
  dicts from a browser and land in `document.set` on a child table, which would
  otherwise take whatever was sent.
* **A key that is absent leaves that table alone; a key that is present replaces
  it.** One dict, six tables, and a browser that asks about education must not be
  able to empty somebody's referees by not mentioning them.

Everything runs through the real self-service endpoints, so the person writing
holds what a self-registered applicant holds: no write permission on Red Profile
at all.
"""

import frappe

from vmmsx.api import registration as registration_api
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

PROFESSION_FIELD = "vmms_profession"
OTHER_PROFESSION_FIELD = "vmms_other_profession"


class TestTheBackgroundBlock(RegistrationTestCase):
	def held(self, profile: str, key: str) -> list[dict]:
		"""One background table, read straight off the child doctype."""
		field, allowed, _files = registration_api.BACKGROUND_TABLES[key]
		frappe.clear_document_cache(fixtures.PROFILE_DOCTYPE, profile)

		return frappe.get_all(
			frappe.get_meta(fixtures.PROFILE_DOCTYPE).get_field(field).options,
			filters={
				"parenttype": fixtures.PROFILE_DOCTYPE,
				"parent": profile,
				"parentfield": field,
			},
			fields=list(allowed),
			order_by="idx asc",
		)

	# --- the vocabularies a form has to draw ------------------------------

	def test_an_applicant_can_read_every_register_the_step_needs(self):
		"""Four registers, two of them shared with recruitment.

		`Profession` and `Personnel License Type` shipped as System Manager only,
		because until now nothing but the desk drew them. An applicant who could
		not read them would be shown two empty pickers on a step that exists to
		let them say what they hold.
		"""
		user = fixtures.website_account("reads.the.registers")

		with fixtures.acting_as(user):
			offered = registration_api.identity_options()

		self.assertTrue(offered["education_levels"], "education levels should be seeded and readable")
		self.assertTrue(offered["driving_licence_classes"], "driving classes should be readable")
		self.assertIn("professions", offered)
		self.assertIn("licence_types", offered)

	def test_education_levels_come_back_in_their_configured_order(self):
		"""Sorted by `sequence`, which is the only thing that field is for.

		Alphabetical would put "Undergraduate degree" above "Vocational" and
		"Diploma" above "Primary" — a picker that reads as though somebody
		shuffled it.
		"""
		offered = registration_api.identity_options()["education_levels"]
		keys = [row["key"] for row in offered]

		if "primary" in keys and "postgraduate" in keys:
			self.assertLess(keys.index("primary"), keys.index("postgraduate"))

	# --- it stays optional ------------------------------------------------

	def test_a_registration_with_none_of_it_is_still_valid(self):
		"""The whole block empty, and the application submits.

		This is the assertion the rest of the feature rests on. Six tables on a
		registration form is exactly the shape that quietly acquires a required
		field, and a volunteer application is not a job application.
		"""
		user, application = self.register_as_volunteer("no.background")

		# Not the exact state, which is the workflow's to decide — this society
		# routes a new application straight into review. What matters is that it
		# left Draft, which is what `assert_ready` refusing would have prevented.
		self.assertNotEqual(application.approval_state, "Draft")
		self.assertEqual(self.held(self.profile_of(user), "education"), [])

	# --- writing it -------------------------------------------------------

	def test_a_registration_stores_the_whole_block_on_the_profile(self):
		user, _ = self.register_as_volunteer(
			"full.background",
			profession="Student",
			background={
				"education": [{"institution": "Kenyatta University", "qualification": "BSc Nursing"}],
				"training": [{"course_name": "First aid"}],
				"work_experience": [{"organization": "Mission Hospital", "role": "Nurse"}],
				"references": [{"reference_name": "Grace Wanjiru", "phone": "+254700000222"}],
			},
		)
		profile = self.profile_of(user)

		self.assertEqual(frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, PROFESSION_FIELD), "Student")
		self.assertEqual(self.held(profile, "education")[0]["institution"], "Kenyatta University")
		self.assertEqual(self.held(profile, "training")[0]["course_name"], "First aid")
		self.assertEqual(self.held(profile, "work_experience")[0]["role"], "Nurse")
		self.assertEqual(self.held(profile, "references")[0]["reference_name"], "Grace Wanjiru")

	def test_other_profession_keeps_the_applicants_own_words(self):
		user, _ = self.register_as_volunteer(
			"other.profession",
			profession="Other",
			other_profession="Community mobiliser",
		)
		profile = self.profile_of(user)

		self.assertEqual(frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, PROFESSION_FIELD), "Other")
		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, OTHER_PROFESSION_FIELD),
			"Community mobiliser",
		)

		with fixtures.acting_as(user):
			mine = registration_api.my_profile()

		self.assertEqual(mine["other_profession"], "Community mobiliser")

	def test_the_profile_reads_back_the_whole_block(self):
		user, _ = self.register_as_volunteer(
			"reads.background",
			profession="Student",
			background={"education": [{"institution": "Kenyatta University"}]},
		)

		with fixtures.acting_as(user):
			mine = registration_api.my_profile()

		self.assertEqual(mine["profession"], "Student")
		self.assertEqual(mine["education"][0]["institution"], "Kenyatta University")
		# Every table is in the payload, empty ones included: a browser that had
		# to tell "absent" from "empty" would be doing the server's job.
		for key in registration_api.BACKGROUND_TABLES:
			self.assertIn(key, mine)

	def test_a_table_nobody_mentioned_is_left_alone(self):
		"""The rule the whole dict turns on.

		A browser correcting somebody's education sends one key. If the five it
		did not send were emptied, editing a qualification would silently delete
		the referees.
		"""
		user, _ = self.register_as_volunteer(
			"leaves.tables.alone",
			background={
				"education": [{"institution": "Kenyatta University"}],
				"references": [{"reference_name": "Grace Wanjiru"}],
			},
		)
		profile = self.profile_of(user)

		with fixtures.acting_as(user):
			registration_api.update_my_profile(
				background={"education": [{"institution": "Nairobi Technical"}]}
			)

		self.assertEqual(self.held(profile, "education")[0]["institution"], "Nairobi Technical")
		self.assertEqual(self.held(profile, "references")[0]["reference_name"], "Grace Wanjiru")

	def test_an_empty_list_empties_that_table(self):
		user, _ = self.register_as_volunteer(
			"empties.one", background={"references": [{"reference_name": "Grace Wanjiru"}]}
		)
		profile = self.profile_of(user)

		with fixtures.acting_as(user):
			registration_api.update_my_profile(background={"references": []})

		self.assertEqual(self.held(profile, "references"), [])

	def test_a_row_with_nothing_in_it_is_dropped(self):
		"""A spare blank at the bottom of a form is a browser artefact.

		`rows_from` decides this and the tickbox rule is the subtlety: a checkbox
		always carries a value, so a row holding nothing but an unticked "still
		there" must not count as an answer.
		"""
		user, _ = self.register_as_volunteer(
			"blank.row",
			background={
				"work_experience": [
					{"organization": "Mission Hospital"},
					{"organization": "", "role": "", "is_current": False},
				]
			},
		)

		self.assertEqual(len(self.held(self.profile_of(user), "work_experience")), 1)

	# --- what a caller may not set ----------------------------------------

	def test_a_field_outside_the_allow_list_never_reaches_the_row(self):
		"""An allow-list, not a denial list.

		The fields that must not arrive from a browser are the ones nobody thinks
		about — a column added to one of these doctypes next year is refused by
		default here, and would have been accepted by a list of things to strip.
		"""
		user, _ = self.register_as_volunteer(
			"extra.field",
			background={
				"education": [
					{"institution": "Kenyatta University", "parent": "somebody-elses-profile", "idx": 99}
				]
			},
		)
		profile = self.profile_of(user)
		rows = self.held(profile, "education")

		self.assertEqual(len(rows), 1)
		self.assertEqual(
			frappe.db.get_value("VMMS Education", {"parent": profile}, "parent"),
			profile,
			"the row should belong to the caller's own profile, whatever they sent",
		)

	# --- what a coordinator is shown -------------------------------------

	def test_the_dossier_carries_what_the_applicant_said(self):
		"""Read live off Red Profile, and stored on the volunteer nowhere.

		A coordinator deciding who to send needs to know who is a nurse. The
		alternative was copying it onto the volunteer record at approval, where it
		would be a second answer that goes stale the first time somebody corrects
		their profile.
		"""
		from vmmsx.volunteer.services import volunteer as volunteer_service

		user, application = self.register_as_volunteer(
			"dossier.background",
			profession="Professional",
			background={
				"education": [{"institution": "Kenyatta University", "qualification": "BSc Nursing"}],
				"references": [{"reference_name": "Grace Wanjiru", "phone": "+254700000333"}],
			},
		)
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, {"red_profile": self.profile_of(user)})

		dossier = volunteer_service.profile_dto(volunteer)

		self.assertEqual(dossier["profession"], "Professional")
		self.assertEqual(dossier["background"]["education"][0]["institution"], "Kenyatta University")
		# The referee's number is here and is meant to be: the row exists so that
		# somebody deciding on an application can ring them.
		self.assertEqual(dossier["background"]["references"][0]["phone"], "+254700000333")

	def test_the_dossier_hands_out_no_attachment(self):
		"""The scans are private files anchored to the profile.

		A URL on this screen would look like evidence and resolve to a refusal for
		most of the people who can read the screen. They are opened on the desk,
		on the profile itself — so the field is not in the DTO at all rather than
		being present and empty.
		"""
		from vmmsx.volunteer.services import identity

		for table, fields in identity._BACKGROUND.items():
			self.assertNotIn("attachment", fields, f"{table} should hand out no file URL")

	def test_a_correction_reaches_the_dossier_with_nothing_to_migrate(self):
		"""Nothing is copied, so nothing has to be kept in step."""
		from vmmsx.volunteer.services import identity

		user, application = self.register_as_volunteer(
			"corrects.background",
			background={"education": [{"institution": "Kenyatta University"}]},
		)
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		profile = self.profile_of(user)

		with fixtures.acting_as(user):
			registration_api.update_my_profile(
				background={"education": [{"institution": "Nairobi Technical"}]}
			)

		self.assertEqual(identity.background(profile)["education"][0]["institution"], "Nairobi Technical")

	def test_a_table_this_endpoint_does_not_know_is_ignored(self):
		"""A key naming no table is dropped rather than raising.

		A browser one deploy ahead of the server sends a table this version has
		never heard of. Refusing the whole registration over it would break the
		form; storing it is not possible; ignoring it is the only honest answer.
		"""
		user = fixtures.website_account("unknown.table")

		with fixtures.acting_as(user):
			fixtures.submit_volunteer_form(
				self.branch(), background={"favourite_colours": [{"colour": "blue"}]}
			)

		self.assertIsNotNone(self.profile_of(user))
