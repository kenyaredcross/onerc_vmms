# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Restored applicant facts remain available through the authorised review door."""

import frappe

from vmmsx.api import volunteer as volunteer_api
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestRestoredReviewerDetails(RegistrationTestCase):
	def test_assigned_approver_reads_household_and_complete_background(self):
		licence_type = "REGTEST practice licence"
		if not frappe.db.exists("Personnel License Type", licence_type):
			frappe.get_doc({"doctype": "Personnel License Type", "__newname": licence_type}).insert()
		_, application = self.register_as_volunteer(
			"reviewer.parity",
			personal_details={
				"blood_group": "O+",
				"number_of_dependants": 0,
				"allergies": [{"allergy": "Penicillin"}],
			},
			background={
				"education": [
					{"institution": "County College", "class_per": "A-", "maj_opt_subj": "Nursing"}
				],
				"work_experience": [{"organization": "County hospital", "location": "Nakuru"}],
				"licences": [
					{
						"license_name": "Practice",
						"license_type": licence_type,
						"institution": "Registration council",
						"valid_from": "2025-01-01",
						"does_not_expire": 1,
						"qualification": "Registered nurse",
						"description": "Practice licence",
					}
				],
				"certifications": [
					{
						"certification_name": "First aid",
						"organization": "Training centre",
						"expire": 1,
						"issue_date": "2025-01-01",
						"expiration_date": "2027-01-01",
					}
				],
			},
		)
		with fixtures.acting_as(self.approver):
			held = volunteer_api.get_decision(application.name)
		self.assertEqual(held["personal_details"]["blood_group"], "O+")
		self.assertEqual(held["personal_details"]["number_of_dependants"], 0)
		self.assertEqual(held["personal_details"]["allergies"], [{"allergy": "Penicillin"}])
		self.assertEqual(held["background"]["education"][0]["class_per"], "A-")
		self.assertEqual(held["background"]["education"][0]["maj_opt_subj"], "Nursing")
		self.assertEqual(held["background"]["work_experience"][0]["location"], "Nakuru")
		self.assertEqual(held["background"]["licences"][0]["qualification"], "Registered nurse")
		self.assertEqual(held["background"]["certifications"][0]["certification_name"], "First aid")

	def test_another_applicant_cannot_read_the_restored_details(self):
		_, application = self.register_as_volunteer(
			"reviewer.private",
			personal_details={"blood_group": "O+", "allergies": [{"allergy": "Penicillin"}]},
		)
		stranger = fixtures.website_account("reviewer.stranger")
		with fixtures.acting_as(stranger), self.assertRaises(frappe.PermissionError):
			volunteer_api.get_decision(application.name)

	def test_member_health_details_need_membership_scope_as_well_as_member_read(self):
		from vmmsx.api import member as member_api
		from vmmsx.api import registration as registration_api

		user = fixtures.website_account("reviewer.member.details")
		with fixtures.acting_as(user):
			draft = registration_api.save_my_member_draft(
				membership_type=fixtures.TYPE_ROUTED,
				geo_node=self.branch(),
				personal_details={"blood_group": "O+", "allergies": [{"allergy": "Peanuts"}]},
			)
		with fixtures.acting_as(self.approver):
			review = member_api.get_review(draft["name"])
		self.assertEqual(review["applicant"]["personal_details"]["blood_group"], "O+")

		role = f"{fixtures.TEST_PREFIX} Unscoped Reader"
		fixtures.grant_doctype_access("VMMS Member", role, permissions=("read",))
		fixtures.grant_doctype_access("VMMS Membership", role, permissions=("read",))
		viewer = fixtures.make_user("reviewer.unscoped.member", [role])
		with fixtures.acting_as(viewer):
			dossier = member_api.get_dossier(review["member"])
		self.assertIsNone(dossier["identity"]["personal_details"])
		self.assertEqual(dossier["memberships"], [])
