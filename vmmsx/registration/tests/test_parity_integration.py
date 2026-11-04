# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Structured legacy facts survive the real registration APIs and database."""

from unittest.mock import patch

import frappe

from vmmsx.api import registration as registration_api
from vmmsx.registration.services import parity
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestParityIntegration(RegistrationTestCase):
	def setUp(self):
		super().setUp()
		self.policy_snapshot = {
			field: frappe.db.get_single_value("National Society Settings", field)
			for field in parity.POLICY_FIELDS.values()
		}
		self.addCleanup(self.restore_policy)
		self.set_policy(**{field: 0 for field in parity.POLICY_FIELDS.values()})

	def set_policy(self, **values):
		for field, value in values.items():
			frappe.db.set_single_value("National Society Settings", field, value)
		frappe.clear_document_cache("National Society Settings", "National Society Settings")

	def restore_policy(self):
		self.set_policy(**self.policy_snapshot)

	def make_document_type(self, handle, required=False):
		name = f"{fixtures.TEST_PREFIX} {handle}"
		doc = frappe.get_doc(
			{
				"doctype": "Supporting Document Type",
				"__newname": name,
				"vmms_required_for_volunteers": int(required),
			}
		).insert()
		if required:
			self.addCleanup(
				frappe.db.set_value, "Supporting Document Type", name, "vmms_required_for_volunteers", 0
			)
		return doc.name

	def test_volunteer_details_roundtrip_after_reload_and_profile_correction(self):
		values = {
			"middle_name": "Achieng",
			"marital_status": "Other",
			"number_of_dependants": 0,
			"blood_group": "O+",
			"has_insurance": "No",
			"access_to_internet": "Sometimes",
			"mpesa_mobile_phone": "+254700009999",
			"place_of_work": "Community hospital",
			"linkedin": "https://linkedin.com/in/registration-example",
			"github": "https://github.com/registration-example",
			"county": "Home county",
			"sub_county": "Home sub-county",
			"ward": "Home ward",
			"administrative_location": "Home location",
			"sub_location": "Home sub-location",
			"additional_skills": [{"additional_skill": "Community radio translation"}],
			"allergies": [{"allergy": "Penicillin"}, {"allergy": "Peanuts"}],
		}
		user, _ = self.register_as_volunteer("parity.volunteer.roundtrip", personal_details=values)
		with fixtures.acting_as(user):
			self.assertEqual(
				registration_api.my_profile()["personal_details"], {**values, "supporting_documents": []}
			)
			registration_api.update_my_profile(personal_details={"number_of_dependants": "", "allergies": []})
			stored = registration_api.my_profile()["personal_details"]
		self.assertIsNone(stored["number_of_dependants"])
		self.assertEqual(stored["allergies"], [])
		self.assertEqual(stored["mpesa_mobile_phone"], "+254700009999")
		self.assertEqual(stored["sub_location"], "Home sub-location")

	def test_member_draft_keeps_identity_details_on_the_shared_person(self):
		user = fixtures.website_account("parity.member.draft")
		with fixtures.acting_as(user):
			registration_api.save_my_member_draft(
				membership_type=fixtures.TYPE_ROUTED,
				geo_node=self.branch(),
				first_name="Amina",
				last_name="Otieno",
				personal_details={"middle_name": "Achieng", "number_of_dependants": 2},
			)
			stored = registration_api.my_profile()
		self.assertEqual(stored["personal_details"]["middle_name"], "Achieng")
		self.assertEqual(stored["personal_details"]["number_of_dependants"], 2)
		self.assertEqual(self.profile_count(user), 1)

	def test_background_retains_grade_subject_work_location_and_certification_expiry(self):
		user, _ = self.register_as_volunteer(
			"parity.background",
			background={
				"education": [
					{"institution": "Community college", "class_per": "A-", "maj_opt_subj": "Nursing"}
				],
				"work_experience": [{"organization": "Community hospital", "location": "Naivasha"}],
				"certifications": [
					{
						"certification_name": "First aid",
						"organization": "Training college",
						"description": "External qualification",
						"expire": 1,
						"issue_date": "2024-01-01",
						"expiration_date": "2027-01-01",
					}
				],
			},
		)
		with fixtures.acting_as(user):
			stored = registration_api.my_profile()
		self.assertEqual(stored["education"][0]["class_per"], "A-")
		self.assertEqual(stored["education"][0]["maj_opt_subj"], "Nursing")
		self.assertEqual(stored["work_experience"][0]["location"], "Naivasha")
		self.assertEqual(stored["certifications"][0]["organization"], "Training college")
		self.assertEqual(str(stored["certifications"][0]["expiration_date"]), "2027-01-01")

	def test_required_supporting_document_blocks_submission(self):
		required = self.make_document_type("required-evidence", required=True)
		with self.assertRaises(frappe.MandatoryError) as caught:
			self.register_as_volunteer("parity.missing.document")
		self.assertIn(required, str(caught.exception))

	def test_supporting_document_is_private_and_tied_to_the_applicants_profile(self):
		document_type = self.make_document_type("supporting-file")
		user = fixtures.website_account("parity.supporting.file")
		with fixtures.acting_as(user):
			file = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": "parity-supporting-evidence.txt",
					"content": b"registration evidence",
					"is_private": 0,
				}
			).insert(ignore_permissions=True)
			application = fixtures.submit_volunteer_form(
				self.branch(),
				personal_details={
					"supporting_documents": [
						{
							"type": document_type,
							"document_name": "Reference letter",
							"attachment": file.file_url,
						}
					]
				},
			)
			stored = registration_api.my_profile()["personal_details"]["supporting_documents"][0]
		self.assertTrue(stored["attachment"].startswith("/private/files/"))
		file_record = frappe.db.get_value(
			"File",
			{"file_url": stored["attachment"]},
			["name", "is_private", "attached_to_doctype", "attached_to_name"],
			as_dict=True,
		)
		self.assertTrue(file_record.is_private)
		self.assertEqual(file_record.attached_to_doctype, "Red Profile")
		self.assertEqual(file_record.attached_to_name, self.profile_of(user))
		with fixtures.acting_as(self.approver):
			registration_api.download_evidence(
				fixtures.APPLICATION_DOCTYPE, application.name, stored["attachment"]
			)
			self.assertEqual(frappe.local.response.filecontent, "registration evidence")
		stranger = fixtures.website_account("parity.supporting.stranger")
		with fixtures.acting_as(stranger):
			self.assertFalse(frappe.has_permission("File", doc=file_record.name, ptype="read"))
			with self.assertRaises(frappe.PermissionError):
				registration_api.download_evidence(
					fixtures.APPLICATION_DOCTYPE, application.name, stored["attachment"]
				)

	def _private_upload(self, user, name):
		with fixtures.acting_as(user):
			return (
				frappe.get_doc(
					{"doctype": "File", "file_name": name, "content": b"certificate scan", "is_private": 0}
				)
				.insert(ignore_permissions=True)
				.file_url
			)

	def test_background_file_is_listed_and_opens_for_the_reviewer(self):
		"""Every attached file reaches the review, and opens through the application."""
		from vmmsx.volunteer.services import application as application_service

		user = fixtures.website_account("parity.background.file")
		upload = self._private_upload(user, "parity-degree.txt")
		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(
				self.branch(),
				background={"education": [{"institution": "KCA", "attachment": upload}]},
			)
		files = application_service.decision_dto(
			frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name)
		)["attachments"]
		education = next(row for row in files if row["table"] == "education")
		self.assertEqual(education["index"], 0)
		self.assertIn("download_evidence", education["url"])
		with fixtures.acting_as(self.approver):
			registration_api.download_evidence(
				fixtures.APPLICATION_DOCTYPE, application.name, education["attachment"], inline=1
			)
			self.assertEqual(frappe.local.response.filecontent, "certificate scan")
			self.assertEqual(frappe.local.response.display_content_as, "inline")
			# A file the application does not list is refused, whatever it is.
			with self.assertRaises(frappe.PermissionError):
				registration_api.download_evidence(
					fixtures.APPLICATION_DOCTYPE, application.name, "/private/files/something-else.txt"
				)

	def test_audit_trail_shows_profile_changes_to_readers_only(self):
		user = fixtures.website_account("parity.audit.trail")
		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(self.branch())
		# Frappe records no versions while testing unless a save asks for one.
		profile = frappe.get_doc("Red Profile", self.profile_of(user))
		profile.vmms_place_of_work = "Community hospital"
		profile.save(ignore_permissions=True, ignore_version=False)
		with fixtures.acting_as(self.approver):
			trail = registration_api.audit_trail(fixtures.APPLICATION_DOCTYPE, application.name)
		self.assertTrue(
			any(entry["kind"] == "created" and entry["record"] == "Application" for entry in trail)
		)
		changes = [change for entry in trail for change in entry["changes"]]
		self.assertIn({"field": "Place of Work", "from": None, "to": "Community hospital"}, changes)
		stranger = fixtures.website_account("parity.audit.stranger")
		with fixtures.acting_as(stranger), self.assertRaises(frappe.PermissionError):
			registration_api.audit_trail(fixtures.APPLICATION_DOCTYPE, application.name)

	def test_an_end_date_before_its_start_is_refused(self):
		user = fixtures.website_account("parity.date.order")
		row = {
			"certification_name": "First aid",
			"organization": "Training college",
			"issue_date": "2026-05-01",
			"expiration_date": "2026-01-01",
		}
		with fixtures.acting_as(user):
			fixtures.submit_volunteer_form(self.branch())
			with self.assertRaises(frappe.ValidationError) as caught:
				registration_api.update_my_profile(background={"certifications": [{**row, "expire": 1}]})
			self.assertIn("Expires cannot be before Issued", str(caught.exception))
			# A certification that does not expire has no end to compare.
			registration_api.update_my_profile(background={"certifications": [{**row, "expire": 0}]})

	def test_optional_age_policy_is_checked_when_enabled(self):
		self.set_policy(vmms_volunteer_min_age=25)
		with self.assertRaises(frappe.ValidationError):
			self.register_as_volunteer("parity.age.refused", date_of_birth="2010-01-01")

	def test_opt_in_member_identity_gate_needs_identification_and_home(self):
		from vmmsx.member.services import membership as membership_service

		self.set_policy(vmms_member_requires_identity=1)
		profile = fixtures.make_profile("Amina", "Otieno")
		member = frappe.get_doc({"doctype": "VMMS Member", "red_profile": profile}).insert()
		membership = frappe.get_doc(
			{
				"doctype": "VMMS Membership",
				"member": member.name,
				"membership_type": fixtures.TYPE_ROUTED,
				"geo_node": self.branch(),
			}
		).insert()
		with self.assertRaises(frappe.MandatoryError):
			parity.assert_member_ready(membership)

	def test_an_applicant_cannot_claim_another_persons_uploaded_evidence(self):
		document_type = self.make_document_type("owned-file")
		owner = fixtures.website_account("parity.file.owner")
		with fixtures.acting_as(owner):
			file = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": "owner-evidence.txt",
					"content": b"private owner evidence",
					"is_private": 1,
				}
			).insert(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			self.register_as_volunteer(
				"parity.file.attacker",
				personal_details={
					"supporting_documents": [
						{
							"type": document_type,
							"document_name": "Claimed evidence",
							"attachment": file.file_url,
						}
					]
				},
			)

	def test_required_evidence_must_reference_a_real_uploaded_file(self):
		document_type = self.make_document_type("missing-file")
		with self.assertRaises(frappe.ValidationError):
			self.register_as_volunteer(
				"parity.file.missing",
				personal_details={
					"supporting_documents": [
						{
							"type": document_type,
							"document_name": "Missing evidence",
							"attachment": "/private/files/nonexistent-registration-evidence.txt",
						}
					]
				},
			)

	def test_kenya_age_limits_apply_to_member_and_volunteer_submissions(self):
		self.set_policy(
			vmms_member_min_age=7,
			vmms_member_max_age=150,
			vmms_volunteer_min_age=7,
			vmms_volunteer_max_age=150,
		)
		profile = fixtures.make_profile("Age", "Boundaries")
		member = frappe.get_doc({"doctype": "VMMS Member", "red_profile": profile}).insert()
		checks = (
			lambda: parity.assert_member_ready({"member": member.name}),
			lambda: parity.assert_ready({"red_profile": profile}),
		)
		with patch.object(parity, "today", return_value="2026-11-02"):
			for birth in ("2019-11-02", "1876-11-02", "1875-11-03"):
				frappe.db.set_value("Red Profile", profile, "date_of_birth", birth)
				for check in checks:
					with self.subTest(birth=birth, path=check):
						check()
			for birth in ("2019-11-03", "1875-11-02"):
				frappe.db.set_value("Red Profile", profile, "date_of_birth", birth)
				for check in checks:
					with self.subTest(birth=birth, path=check), self.assertRaises(frappe.ValidationError):
						check()
