# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Pure regression checks for information preserved by the registration contract."""

import unittest
from unittest.mock import patch

from vmmsx.registration.services import parity


class TestRegistrationParity(unittest.TestCase):
	def test_kenya_age_policy_applies_when_site_settings_are_unset(self):
		from onerc_core.society.services import config

		for missing in (None, 0):
			settings = {"country": "Kenya", **{field: missing for field in parity.POLICY_FIELDS.values()}}
			with (
				patch.object(config, "settings", return_value=settings),
				patch.object(parity, "supporting_document_types", return_value=[]),
				patch.object(parity, "identification_patterns", return_value={}),
			):
				policy = parity.options()
				self.assertEqual(
					(
						policy["member_min_age"],
						policy["member_max_age"],
						policy["volunteer_min_age"],
						policy["volunteer_max_age"],
					),
					(7, 150, 7, 150),
				)

	def test_other_societies_keep_their_configured_age_policy(self):
		from onerc_core.society.services import config

		with (
			patch.object(config, "settings", return_value={"country": "Tanzania"}),
			patch.object(parity, "supporting_document_types", return_value=[]),
			patch.object(parity, "identification_patterns", return_value={}),
		):
			policy = parity.options()
			self.assertEqual(
				(
					policy["member_min_age"],
					policy["member_max_age"],
					policy["volunteer_min_age"],
					policy["volunteer_max_age"],
				),
				(0, 0, 0, 0),
			)

	def test_household_zero_is_distinct_from_unanswered(self):
		self.assertEqual(
			parity.normalise_personal_details({"number_of_dependants": 0}), {"number_of_dependants": 0}
		)
		self.assertEqual(
			parity.normalise_personal_details({"number_of_dependants": ""}), {"number_of_dependants": None}
		)
		self.assertEqual(parity.normalise_personal_details({}), {})

	def test_dependants_refuse_negative_or_fractional_values(self):
		for invalid in [-1, 1.5, "2.5", True, "many"]:
			with self.subTest(invalid=invalid), self.assertRaises(ValueError):
				parity.normalise_personal_details({"number_of_dependants": invalid})

	def test_person_facts_do_not_accept_account_or_reviewer_fields(self):
		answer = parity.normalise_personal_details(
			{
				"middle_name": " Amina ",
				"roles": ["System Manager"],
				"user": "other@example.test",
				"is_verified": 1,
			}
		)
		self.assertEqual(answer, {"middle_name": "Amina"})

	def test_health_and_contact_fields_keep_their_original_meaning(self):
		values = {
			"marital_status": "Married",
			"blood_group": "O+",
			"has_insurance": "No",
			"access_to_internet": "Sometimes",
			"mpesa_mobile_phone": "+254700000222",
			"place_of_work": "County hospital",
		}
		self.assertEqual(parity.normalise_personal_details(values), values)

	def test_enum_values_are_checked(self):
		for key, invalid in [
			("has_insurance", "Perhaps"),
			("access_to_internet", "Usually"),
			("marital_status", "invented"),
		]:
			with self.subTest(key=key), self.assertRaises(ValueError):
				parity.normalise_personal_details({key: invalid})

	def test_social_links_only_accept_http_or_https(self):
		for invalid in ["javascript:alert(1)", "data:text/html,hello", "//evil.test", "https://"]:
			with self.subTest(invalid=invalid), self.assertRaises(ValueError):
				parity.normalise_personal_details({"linkedin": invalid})
		self.assertEqual(
			parity.normalise_personal_details({"github": "https://github.com/example"}),
			{"github": "https://github.com/example"},
		)

	def test_document_table_preserves_type_name_and_file_but_strips_privileged_fields(self):
		values = {
			"supporting_documents": [
				{
					"type": "Other",
					"document_name": "Reference letter",
					"attachment": "/private/files/reference.pdf",
					"owner": "Administrator",
					"is_verified": 1,
				}
			]
		}
		answer = parity.normalise_personal_details(values)
		self.assertEqual(
			answer["supporting_documents"],
			[
				{
					"type": "Other",
					"document_name": "Reference letter",
					"attachment": "/private/files/reference.pdf",
				}
			],
		)

	def test_document_file_must_be_a_local_upload(self):
		with self.assertRaises(ValueError):
			parity.normalise_personal_details(
				{"supporting_documents": [{"type": "CV", "attachment": "https://elsewhere.test/cv.pdf"}]}
			)

	def test_missing_table_key_leaves_it_alone_and_explicit_empty_clears_it(self):
		self.assertNotIn("allergies", parity.normalise_personal_details({"blood_group": "O+"}))
		self.assertEqual(parity.normalise_personal_details({"allergies": []})["allergies"], [])
		self.assertNotIn("allergies", parity.normalise_personal_details({"allergies": None}))

	def test_allergies_preserve_separate_rows(self):
		self.assertEqual(
			parity.normalise_personal_details(
				{"allergies": [{"allergy": "Penicillin"}, {"allergy": "Peanuts"}]}
			)["allergies"],
			[{"allergy": "Penicillin"}, {"allergy": "Peanuts"}],
		)

	def test_document_requiredness_needs_the_attachment_not_only_a_row(self):
		types = [
			{"key": "CV", "is_required": True},
			{"key": "Good Conduct", "is_required": True},
			{"key": "Other", "is_required": False},
		]
		rows = [
			{"type": "CV", "attachment": "/private/files/cv.pdf"},
			{"type": "Good Conduct", "attachment": ""},
		]
		self.assertEqual(parity.missing_required_documents(rows, types), ["Good Conduct"])

	def test_age_bounds_are_inclusive_and_configurable(self):
		for birth in ["2019-11-02", "1876-11-02", "1875-11-03"]:
			with self.subTest(birth=birth):
				self.assertIsNone(parity.age_error(birth, 7, 150, "2026-11-02"))
		for birth in ["2019-11-03", "1875-11-02", "2026-11-03"]:
			with self.subTest(birth=birth):
				self.assertIsNotNone(parity.age_error(birth, 7, 150, "2026-11-02"))
		self.assertIsNone(parity.age_error("1875-11-02", 0, 0, "2026-11-02"))

	def test_id_pattern_checks_the_entire_number(self):
		self.assertIsNone(parity.identification_error("12345678", r"\d{7,9}"))
		self.assertIsNotNone(parity.identification_error("A12345678", r"\d{7,9}"))
		self.assertIsNone(parity.identification_error("arbitrary", ""))
		self.assertIsNotNone(parity.identification_error("123", "["))

	def test_profile_roundtrip_preserves_zero_and_the_unanswered_state(self):
		class Meta:
			def has_field(self, field):
				return True

		class Profile(dict):
			meta = Meta()

			def set(self, key, value):
				self[key] = value

		profile = Profile()
		parity.write_profile(profile, {"number_of_dependants": 0})
		self.assertEqual(parity.profile_dto(profile)["number_of_dependants"], 0)
		parity.write_profile(profile, {"number_of_dependants": ""})
		self.assertIsNone(parity.profile_dto(profile)["number_of_dependants"])

	def test_residence_details_survive_a_coarse_geographic_anchor(self):
		values = {
			"county": "Nakuru",
			"sub_county": "Naivasha",
			"ward": "Lake View",
			"administrative_location": "Township",
			"sub_location": "Kariandusi",
		}
		self.assertEqual(parity.normalise_personal_details(values), values)


if __name__ == "__main__":
	unittest.main()
