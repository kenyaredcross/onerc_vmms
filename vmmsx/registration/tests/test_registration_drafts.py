# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Applicant-owned drafts across both self-registration journeys."""

import frappe

from vmmsx.api import approvals as approvals_api
from vmmsx.api import registration as registration_api
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestVolunteerDrafts(RegistrationTestCase):
	def _save(self, user: str, **changes) -> dict:
		values = {
			"geo_node": self.branch(),
			"first_name": "Amina",
			"last_name": "Otieno",
			"date_of_birth": fixtures.DEFAULT_DATE_OF_BIRTH,
			"country_of_citizenship": fixtures.test_country(),
			"residency_type": "Local",
			"home_geo_node": self.branch(),
			"id_type": fixtures.make_identification_type(),
			"id_number": f"{fixtures.TEST_PREFIX}-{frappe.generate_hash(length=8)}",
		}
		values.update(changes)

		with fixtures.acting_as(user):
			return registration_api.save_my_volunteer_draft(**values)

	def test_save_keeps_the_application_out_of_the_approval_queue(self):
		user = fixtures.website_account("saved.volunteer.draft")
		draft = self._save(user, prior_experience="Still writing this")

		self.assertEqual(draft["state"], "Draft")
		self.assertTrue(draft["can_edit"])
		self.assertEqual(draft["prior_experience"], "Still writing this")
		self.assertEqual(
			frappe.get_all(
				"ToDo",
				filters={
					"reference_type": fixtures.APPLICATION_DOCTYPE,
					"reference_name": draft["name"],
				},
				pluck="name",
			),
			[],
		)

	def test_saving_again_updates_the_same_draft(self):
		user = fixtures.website_account("updated.volunteer.draft")
		first = self._save(user, prior_experience="First version")
		second = self._save(user, prior_experience="Corrected version", phone="+254700123456")

		self.assertEqual(second["name"], first["name"])
		self.assertEqual(second["prior_experience"], "Corrected version")
		self.assertEqual(
			frappe.db.count(fixtures.APPLICATION_DOCTYPE, {"red_profile": self.profile_of(user)}), 1
		)
		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, self.profile_of(user), "phone"),
			"+254700123456",
		)

	def test_another_account_cannot_load_the_draft(self):
		owner = fixtures.website_account("private.volunteer.draft")
		stranger = fixtures.website_account("draft.stranger")
		self._save(owner)

		with fixtures.acting_as(stranger):
			self.assertIsNone(registration_api.my_registration("volunteer"))

	def test_submit_moves_the_saved_draft_into_review(self):
		user = fixtures.website_account("submitted.volunteer.draft")
		draft = self._save(user)

		with fixtures.acting_as(user):
			status = registration_api.submit_my_registration("volunteer")

		self.assertEqual(status["name"], draft["name"])
		self.assertEqual(status["approval_state"], "In Review")
		self.assertEqual(
			frappe.get_all(
				"ToDo",
				filters={
					"reference_type": fixtures.APPLICATION_DOCTYPE,
					"reference_name": draft["name"],
					"status": ("in", ("Open", "Overdue")),
				},
				pluck="allocated_to",
			),
			[self.approver],
		)

	def test_an_unsent_draft_is_not_reported_as_waiting_on_the_applicant(self):
		"""Draft means two opposite things, and only the audit trail separates them.

		The portal reads `reviewed` to decide between "you have not finished
		this" and "your branch has asked you for something". Before the flag
		existed it had only the state, and told somebody who had never pressed
		Submit that their branch was waiting on them.
		"""
		user = fixtures.website_account("unsent.volunteer.draft")
		self._save(user)

		with fixtures.acting_as(user):
			answer = registration_api.my_open_registrations()["volunteer"]
			resumed = registration_api.my_registration("volunteer")

		self.assertEqual(answer["state"], "Draft")
		self.assertFalse(answer["reviewed"])
		self.assertFalse(resumed["reviewed"])

	def test_a_returned_draft_is_reported_as_having_been_reviewed(self):
		"""The same state, the other meaning — and this one really is waiting."""
		user = fixtures.website_account("reviewed.volunteer.draft")
		draft = self._save(user)

		with fixtures.acting_as(user):
			registration_api.submit_my_registration("volunteer")

		with fixtures.acting_as(self.approver):
			approvals_api.decide(
				fixtures.APPLICATION_DOCTYPE,
				draft["name"],
				"More info requested",
				"Send us your first-aid certificate.",
			)

		with fixtures.acting_as(user):
			answer = registration_api.my_open_registrations()["volunteer"]

		self.assertEqual(answer["state"], "Draft")
		self.assertTrue(answer["reviewed"])

	def test_more_information_reopens_the_same_record_for_edit_and_resubmit(self):
		user = fixtures.website_account("returned.volunteer.draft")
		draft = self._save(user, prior_experience="Too short")

		with fixtures.acting_as(user):
			registration_api.submit_my_registration("volunteer")

		with fixtures.acting_as(self.approver):
			approvals_api.decide(
				fixtures.APPLICATION_DOCTYPE,
				draft["name"],
				"More info requested",
				"Please describe your first-aid experience.",
			)

		with fixtures.acting_as(user):
			returned = registration_api.my_registration("volunteer")

		self.assertEqual(returned["name"], draft["name"])
		self.assertTrue(returned["can_edit"])
		self.assertEqual(returned["reason"], "Please describe your first-aid experience.")

		updated = self._save(user, prior_experience="Three years with the school first-aid club")
		with fixtures.acting_as(user):
			registration_api.submit_my_registration("volunteer")

		self.assertEqual(updated["name"], draft["name"])
		self.assertEqual(
			frappe.db.get_value(fixtures.APPLICATION_DOCTYPE, draft["name"], "approval_state"),
			"In Review",
		)

	def test_an_application_under_review_cannot_be_edited(self):
		user = fixtures.website_account("locked.volunteer.draft")
		self._save(user)

		with fixtures.acting_as(user):
			registration_api.submit_my_registration("volunteer")

		with self.assertRaises(frappe.ValidationError):
			self._save(user, prior_experience="Changed after submit")


class TestMemberDrafts(RegistrationTestCase):
	def _save(self, user: str, **changes) -> dict:
		values = {
			"membership_type": fixtures.TYPE_ROUTED,
			"geo_node": self.branch(),
			"first_name": "Amina",
			"last_name": "Otieno",
		}
		values.update(changes)

		with fixtures.acting_as(user):
			return registration_api.save_my_member_draft(**values)

	def test_save_keeps_membership_as_a_draft_until_submit(self):
		user = fixtures.website_account("saved.member.draft")
		draft = self._save(user)

		self.assertEqual(draft["state"], "Draft")
		self.assertEqual(draft["membership_status"], "Draft")
		self.assertFalse(
			frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, draft["name"], "payment_transaction")
		)

		with fixtures.acting_as(user):
			status = registration_api.submit_my_registration("member")

		self.assertEqual(status["name"], draft["name"])
		self.assertEqual(status["approval_state"], "In Review")
		self.assertEqual(status["membership_status"], "Awaiting Approval")

	def test_member_draft_is_resumed_instead_of_duplicated(self):
		user = fixtures.website_account("updated.member.draft")
		first = self._save(user)
		second = self._save(user, phone="+254711222333")

		with fixtures.acting_as(user):
			loaded = registration_api.my_registration("member")

		self.assertEqual(second["name"], first["name"])
		self.assertEqual(loaded["name"], first["name"])
		self.assertEqual(loaded["membership_type"], fixtures.TYPE_ROUTED)
