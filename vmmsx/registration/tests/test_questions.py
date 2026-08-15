# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What a society may ask, and what an applicant may answer.

The claim in `registration/services/questions.py` is that a society can add a
question without anybody writing code, and that every answer is re-checked
against the question that asked for it — server-side, every time, whatever the
browser sent. Both halves are worth testing because both are the sort of thing
that works in the happy path and quietly does not in the one that matters.

The suite spends most of its time on the refusals: a choice the question never
offered, a file that was never uploaded here, and a required question left
blank. Those are the three ways a hand-made request would try to get past a form
that only exists in configuration.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.registration.services import questions

EXTRA_TEST_RECORD_DEPENDENCIES = []

APPLICATION = "VMMS Volunteer Application"


class QuestionTestCase(IntegrationTestCase):
	"""One of each interesting kind of question, asked on the application."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.letter = cls._ask("Letter from the area chief", "Attach", required=True)
		cls.camp = cls._ask("Which chief's camp?", "Select", options="Kalokol\nLodwar", required=True)
		cls.years = cls._ask("Years in the community", "Int")
		cls.consent = cls._ask("May we call you at night?", "Check")
		cls.retired = cls._ask("A question since withdrawn", "Data", active=False)

	@classmethod
	def _ask(cls, label, field_type, options=None, required=False, active=True):
		return frappe.get_doc(
			{
				"doctype": questions.QUESTION_DOCTYPE,
				"asked_on": APPLICATION,
				"question_label": label,
				"field_type": field_type,
				"options": options,
				"is_required": int(required),
				"is_active": int(active),
			}
		).insert(ignore_permissions=True)

	def draft(self):
		return frappe.new_doc(APPLICATION)


class TestWhatIsAsked(QuestionTestCase):
	def test_a_retired_question_is_not_asked_of_anybody_new(self):
		asked = [row["name"] for row in questions.asked_on(APPLICATION)]

		self.assertIn(self.letter.name, asked)
		self.assertNotIn(self.retired.name, asked)

	def test_a_question_is_only_asked_on_the_registration_it_names(self):
		"""`asked_on` is the whole of which form a question belongs to."""
		asked = [row["name"] for row in questions.asked_on("VMMS Membership")]

		self.assertNotIn(self.camp.name, asked)

	def test_a_list_question_carries_its_choices_and_others_carry_none(self):
		by_name = {row["name"]: row for row in questions.asked_on(APPLICATION)}

		self.assertEqual(by_name[self.camp.name]["choices"], ["Kalokol", "Lodwar"])
		self.assertEqual(by_name[self.years.name]["choices"], [])

	def test_a_list_question_with_no_choices_is_refused_at_source(self):
		"""Not left to the form: a seed or a patch would slip past a depends_on."""
		with self.assertRaises(frappe.MandatoryError):
			self._ask("Pick one of nothing", "Select")


class TestWhatIsStored(QuestionTestCase):
	def test_an_answer_snapshots_the_question_it_was_given_to(self):
		"""Rewording a question must not restate what somebody was already asked."""
		doc = self.draft()
		questions.apply(doc, {self.camp.name: "Lodwar"})

		row = doc.custom_answers[0]
		self.assertEqual(row.question_label, "Which chief's camp?")

		self.camp.question_label = "Which camp?"
		self.camp.save(ignore_permissions=True)

		self.assertEqual(
			questions.answers_of(doc)[0]["label"],
			"Which chief's camp?",
			"the answer must keep the wording it was given under",
		)

	def test_a_file_answer_goes_in_the_file_column_and_not_the_text_one(self):
		doc = self.draft()
		questions.apply(doc, {self.letter.name: "/private/files/chief.pdf"})

		row = doc.custom_answers[0]
		self.assertEqual(row.answer_file, "/private/files/chief.pdf")
		self.assertFalse(row.answer_value)
		self.assertTrue(questions.answers_of(doc)[0]["is_file"])

	def test_an_unticked_box_is_an_answer_rather_than_a_blank(self):
		"""False is a real answer, so a required tick answered "no" is answered."""
		doc = self.draft()
		questions.apply(doc, {self.consent.name: False})

		self.assertEqual(doc.custom_answers[0].answer_value, "0")

	def test_applying_again_replaces_rather_than_accumulates(self):
		"""A wizard sends the whole set, so a merge would keep a changed mind."""
		doc = self.draft()
		questions.apply(doc, {self.camp.name: "Lodwar"})
		questions.apply(doc, {self.camp.name: "Kalokol"})

		self.assertEqual(len(doc.custom_answers), 1)
		self.assertEqual(doc.custom_answers[0].answer_value, "Kalokol")

	def test_an_answer_to_a_retired_question_is_ignored_rather_than_refused(self):
		"""Deactivated mid-wizard is not the applicant's mistake."""
		doc = self.draft()
		written = questions.apply(doc, {self.retired.name: "anything"})

		self.assertEqual(written, [])
		self.assertEqual(len(doc.custom_answers), 0)


class TestWhatIsRefused(QuestionTestCase):
	def test_a_choice_the_question_never_offered_is_refused(self):
		"""The browser filters; the server decides. A hand-made request gets this."""
		with self.assertRaises(frappe.ValidationError):
			questions.apply(self.draft(), {self.camp.name: "Nairobi"})

	def test_a_file_not_uploaded_to_this_site_is_refused(self):
		"""Otherwise this field points an approver's browser at somebody's server."""
		with self.assertRaises(frappe.ValidationError):
			questions.apply(self.draft(), {self.letter.name: "https://elsewhere.example/x.pdf"})

	def test_a_required_question_left_blank_refuses_the_submission(self):
		doc = self.draft()
		questions.apply(doc, {self.years.name: "7"})

		with self.assertRaises(frappe.MandatoryError):
			questions.assert_answered(doc)

	def test_every_required_question_answered_passes(self):
		doc = self.draft()
		questions.apply(
			doc,
			{
				self.letter.name: "/private/files/chief.pdf",
				self.camp.name: "Lodwar",
			},
		)

		questions.assert_answered(doc)

	def test_a_doctype_with_no_answer_table_is_left_alone(self):
		"""A registration that has not opted in must not throw on a missing field."""
		self.assertFalse(questions.asks("Geo Node"))
		self.assertEqual(questions.apply(frappe.new_doc("Geo Node"), {"x": "y"}), [])
		self.assertEqual(questions.answers_of(frappe.new_doc("Geo Node")), [])
