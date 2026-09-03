# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Naming *which* disability, from core's own register.

`install_disability_fields` asked the question — No / Yes / Prefer not to say —
and kept the answer in a Select with a free-text box beside it. That is enough
to know somebody should be asked about adjustments and enough for nothing else:
a society cannot count how many of its volunteers are Deaf, and the one
description on file is a sentence somebody typed.

`install_disability_vocabulary` points a table on the same profile at core's
`Disability` register, which shipped in onerc_core with no reader anywhere in
this app. What this suite exists to hold still is the relationship between the
two, because the obvious simplification is wrong in both directions:

* **The list does not replace the answer.** An empty table is the correct
  storage for "No" *and* for "Prefer not to say" *and* for a form nobody filled
  in, so the Select stays the required question and stays the only thing any
  reader branches on.
* **The answer does not fill in the list.** Nothing derives one from the other.
  Somebody may disclose and decline to say more, which is why naming one is
  optional whatever was answered.

Everything here runs through the real self-service endpoints, so the person
writing holds what a self-registered applicant holds: no write permission on Red
Profile at all.
"""

import frappe

from vmmsx.api import registration as registration_api
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

DISABILITIES_FIELD = "vmms_disabilities"
DISABILITY_DOCTYPE = "Disability"
TYPE_DOCTYPE = "Disability Type"


class TestTheDisabilityRegister(RegistrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# Two rows of this suite's own, rather than the seeded ones. A test that
		# asserted on "Deafness" would be asserting on a starting vocabulary a
		# society is invited to delete, and the patch that seeds it says so.
		cls.hearing = cls.make_type("Hearing")
		cls.deafness = cls.make_disability("Deafness", cls.hearing)
		cls.low_vision = cls.make_disability("Low vision", cls.make_type("Vision"))

	@classmethod
	def make_type(cls, label: str) -> str:
		name = f"{fixtures.TEST_PREFIX} {label}"

		if not frappe.db.exists(TYPE_DOCTYPE, name):
			frappe.get_doc({"doctype": TYPE_DOCTYPE, "disability_type": name}).insert(ignore_permissions=True)

		return name

	@classmethod
	def make_disability(cls, label: str, disability_type: str) -> str:
		name = f"{fixtures.TEST_PREFIX} {label}"

		if not frappe.db.exists(DISABILITY_DOCTYPE, name):
			frappe.get_doc(
				{
					"doctype": DISABILITY_DOCTYPE,
					"disability_name": name,
					"disability_type": disability_type,
				}
			).insert(ignore_permissions=True)

		return name

	def named_on(self, profile: str) -> list[str]:
		"""What the profile holds, read off the table rather than through the API."""
		frappe.clear_document_cache(fixtures.PROFILE_DOCTYPE, profile)

		return frappe.get_all(
			"VMMS Disability Selector",
			filters={
				"parenttype": fixtures.PROFILE_DOCTYPE,
				"parent": profile,
				"parentfield": DISABILITIES_FIELD,
			},
			order_by="idx asc",
			pluck="disability",
		)

	# --- the vocabulary a form has to draw --------------------------------

	def test_an_applicant_can_read_the_register_before_they_are_anybody(self):
		"""Core ships both registers as System Manager only; the patch widens it.

		Asserted from a website account rather than as Administrator, because the
		person who has to draw this control is somebody who has just signed up and
		holds one self-service role. A vocabulary they could not read would be a
		question with no answers under it.
		"""
		user = fixtures.website_account("reads.the.register")

		with fixtures.acting_as(user):
			offered = registration_api.identity_options()["disabilities"]

		by_key = {row["key"]: row for row in offered}

		self.assertIn(self.deafness, by_key)
		self.assertEqual(
			by_key[self.deafness]["description"],
			self.hearing,
			"the type belongs in the description slot, so a long list stays scannable",
		)

	# --- writing it -------------------------------------------------------

	def test_a_registration_stores_what_was_named_on_the_profile(self):
		user, _ = self.register_as_volunteer(
			"names.two",
			disability_status="Yes",
			disabilities=[self.deafness, self.low_vision],
		)

		self.assertEqual(self.named_on(self.profile_of(user)), [self.deafness, self.low_vision])

	def test_the_profile_reads_back_what_it_stored(self):
		user, _ = self.register_as_volunteer(
			"reads.back", disability_status="Yes", disabilities=[self.deafness]
		)

		with fixtures.acting_as(user):
			mine = registration_api.my_profile()

		self.assertEqual(mine["disabilities"], [self.deafness])
		self.assertEqual(mine["disability_status"], "Yes")

	def test_saying_nothing_leaves_the_table_alone(self):
		"""`None` is "I am not talking about this", and it has to stay that way.

		Every endpoint here takes a dozen optional arguments and a browser sends
		the three it is currently asking about. An omitted table that emptied
		itself would mean correcting a phone number silently withdrew what
		somebody had disclosed.
		"""
		user, _ = self.register_as_volunteer(
			"leaves.alone", disability_status="Yes", disabilities=[self.deafness]
		)
		profile = self.profile_of(user)

		with fixtures.acting_as(user):
			registration_api.update_my_profile(phone="+254700000111")

		self.assertEqual(self.named_on(profile), [self.deafness])

	def test_an_empty_list_is_a_withdrawal_and_empties_it(self):
		user, _ = self.register_as_volunteer(
			"withdraws", disability_status="Yes", disabilities=[self.deafness]
		)
		profile = self.profile_of(user)

		with fixtures.acting_as(user):
			registration_api.update_my_profile(disabilities=[])

		self.assertEqual(self.named_on(profile), [])

	def test_the_whole_set_is_replaced_rather_than_added_to(self):
		user, _ = self.register_as_volunteer(
			"replaces", disability_status="Yes", disabilities=[self.deafness]
		)
		profile = self.profile_of(user)

		with fixtures.acting_as(user):
			registration_api.update_my_profile(disabilities=[self.low_vision])

		self.assertEqual(self.named_on(profile), [self.low_vision])

	# --- what arrives from a browser --------------------------------------

	def test_a_key_naming_no_row_is_dropped_rather_than_stored(self):
		"""A society that retired a row must not turn somebody's form into an error.

		The alternative is core's own link validation refusing the save, which
		would show an applicant a message about a vocabulary they never chose
		from — and on a Link column a bad key stored is a row pointing at nothing.
		"""
		user, _ = self.register_as_volunteer(
			"unknown.key",
			disability_status="Yes",
			disabilities=[self.deafness, "Something Nobody Configured"],
		)

		self.assertEqual(self.named_on(self.profile_of(user)), [self.deafness])

	def test_saying_the_same_thing_twice_says_it_once(self):
		user, _ = self.register_as_volunteer(
			"says.twice",
			disability_status="Yes",
			disabilities=[self.deafness, self.deafness],
		)

		self.assertEqual(self.named_on(self.profile_of(user)), [self.deafness])

	# --- the relationship with the question above it ----------------------

	def test_naming_one_does_not_answer_the_question(self):
		"""The Select is the requirement, and a list underneath it is not an answer.

		`assert_ready` refuses a volunteer application whose profile has no
		disability answer. Somebody who ticked a row and never touched the Select
		has not been asked — this checks the requirement is unmoved by the table,
		rather than quietly satisfied by it.
		"""
		user = fixtures.website_account("named.but.unanswered")

		with fixtures.acting_as(user), self.assertRaises(frappe.ValidationError):
			fixtures.submit_volunteer_form(
				self.branch(),
				disability_status=None,
				disabilities=[self.deafness],
			)

	def test_answering_no_is_stored_as_an_answer_with_an_empty_table(self):
		"""The two states an empty table cannot tell apart, and what does tell them.

		"No" and "Prefer not to say" both leave nothing named. That is exactly why
		the Select was kept: it is the only place the difference between them —
		and the difference between either of them and a form nobody filled in —
		can be recorded at all.
		"""
		user, _ = self.register_as_volunteer("answers.no", disability_status="No", disabilities=[])
		profile = self.profile_of(user)

		self.assertEqual(self.named_on(profile), [])
		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "vmms_disability_status"),
			"No",
		)
