# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Applying for a volunteering opening, on HRMS's own `Job Applicant`.

Five properties, and each is the answer to a way this could have been built
worse:

1. **An employment opening is untouched.** Not "mostly untouched": this door
   refuses one outright and says HRMS's own form is the right one, so a society
   running recruitment finds nothing about it changed.
2. **Only an approved active volunteer applies for a volunteering role.** The
   refusal points at registration rather than at a permission error, because
   somebody who is not yet a volunteer is not being told off.
3. **One live application per person per opening.** A withdrawn or rejected one
   does not block a new attempt — applying again after a no is a real thing
   people do.
4. **The questions are snapshotted onto the answers.** An application decided
   next March against wording that changed in January must still read as the
   conversation it was.
5. **A withdrawal is not a rejection.** It is a pair of fields beside HRMS's
   status, never a sixth value, because marking somebody Rejected for changing
   their mind puts a decision the society never made into their record.

Plus the one that would be easiest to get wrong quietly: **conversion runs
once.** A double-clicked button must not put the same person on the same
deployment twice.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase
from vmmsx.hr.services import application as application_service
from vmmsx.hr.services import openings
from vmmsx.setup import job_applicant_fields as applicant_fields
from vmmsx.setup import job_opening_fields as opening_fields

EXTRA_TEST_RECORD_DEPENDENCIES = []

APPLICANT_DOCTYPE = "Job Applicant"
OPENING_DOCTYPE = "Job Opening"
DESIGNATION = "Volunteering Application Test Officer"


class ApplicationTestCase(DeploymentTestCase):
	def setUp(self):
		super().setUp()

		if not openings.is_available():
			self.skipTest("HRMS is not installed on this site")

		self.branch = self.society_a["branch"]

	def volunteer(self, active: bool = True):
		"""A volunteer with an email on their profile, which an application needs."""
		profile = fixtures.make_profile("Applicant", frappe.generate_hash(length=6))
		volunteer = fixtures.make_volunteer(profile, self.branch, active=active)

		if not frappe.db.get_value("Red Profile", profile, "email"):
			frappe.db.set_value(
				"Red Profile", profile, "email", f"{frappe.generate_hash(length=8)}@applicant.test",
				update_modified=False,
			)

		return volunteer

	def designation(self) -> str:
		"""HRMS makes it mandatory and reads it in its staffing-plan check."""
		if not frappe.db.exists("Designation", DESIGNATION):
			frappe.get_doc(
				{"doctype": "Designation", "designation_name": DESIGNATION}
			).insert(ignore_permissions=True)

		return DESIGNATION

	def opening(self, **overrides):
		values = {
			"doctype": OPENING_DOCTYPE,
			"job_title": f"Ward Health Volunteer {frappe.generate_hash(length=6)}",
			"company": fixtures.company(),
			"designation": self.designation(),
			"status": "Open",
			"publish": 1,
			"posted_on": add_days(today(), -10),
			opening_fields.PURPOSE_FIELD: opening_fields.PURPOSE_VOLUNTEER,
			"vmms_geo_node": self.branch,
		}
		values.update(overrides)

		return frappe.get_doc(values).insert(ignore_permissions=True)

	def asking(self, *questions, **overrides):
		"""An opening carrying screening questions, given as dicts."""
		return self.opening(screening_questions=list(questions), **overrides)


class TestAnEmploymentOpeningIsUntouched(ApplicationTestCase):
	def test_an_opening_with_no_purpose_is_employment(self):
		"""The direction every unset setting in this app takes. An opening created
		before the field existed keeps HRMS's own behaviour."""
		opening = self.opening(**{opening_fields.PURPOSE_FIELD: None})

		self.assertFalse(application_service.is_volunteering(opening))

	def test_applying_for_one_through_this_door_is_refused(self):
		opening = self.opening(**{opening_fields.PURPOSE_FIELD: opening_fields.PURPOSE_EMPLOYMENT})

		with self.assertRaises(frappe.ValidationError):
			application_service.apply(opening.name, self.volunteer().name)

	def test_and_the_refusal_points_at_the_right_door(self):
		"""Not a permission error somebody has to guess at: a sentence saying
		which form this post is applied for through."""
		opening = self.opening(**{opening_fields.PURPOSE_FIELD: opening_fields.PURPOSE_EMPLOYMENT})

		with self.assertRaises(frappe.ValidationError) as refusal:
			application_service.apply(opening.name, self.volunteer().name)

		self.assertIn("recruitment", str(refusal.exception))


class TestWhoMayApply(ApplicationTestCase):
	def test_an_approved_active_volunteer_may(self):
		opening = self.opening()
		applicant = application_service.apply(opening.name, self.volunteer().name)

		self.assertEqual(applicant.status, applicant_fields.STATUS_OPEN)

	def test_somebody_who_is_not_a_volunteer_may_not(self):
		opening = self.opening()

		with self.assertRaises(frappe.PermissionError):
			application_service.apply(opening.name, None)

	def test_a_volunteer_who_is_not_active_may_not(self):
		opening = self.opening()

		with self.assertRaises(frappe.PermissionError):
			application_service.apply(opening.name, self.volunteer(active=False).name)

	def test_a_closed_opening_takes_nobody(self):
		opening = self.opening(status="Closed")

		with self.assertRaises(frappe.ValidationError):
			application_service.apply(opening.name, self.volunteer().name)


class TestTheIdentityComesFromTheRegister(ApplicationTestCase):
	def test_the_name_and_email_are_copied_rather_than_asked_for(self):
		"""A form that made somebody retype their own name is a form that can
		disagree with the register."""
		volunteer = self.volunteer()
		applicant = application_service.apply(self.opening().name, volunteer.name)

		profile = frappe.db.get_value(
			"Red Profile", volunteer.red_profile, ["full_name", "email"], as_dict=True
		)

		self.assertEqual(applicant.applicant_name, profile.full_name)
		self.assertEqual(applicant.email_id, profile.email)

	def test_the_volunteer_and_profile_are_linked(self):
		volunteer = self.volunteer()
		applicant = application_service.apply(self.opening().name, volunteer.name)

		self.assertEqual(applicant.get(applicant_fields.VOLUNTEER_FIELD), volunteer.name)
		self.assertEqual(applicant.get(applicant_fields.PROFILE_FIELD), volunteer.red_profile)

	def test_the_application_is_anchored_where_the_opening_is(self):
		applicant = application_service.apply(self.opening().name, self.volunteer().name)

		self.assertEqual(applicant.get(applicant_fields.GEO_NODE_FIELD), self.branch)


class TestOneLiveApplicationPerPerson(ApplicationTestCase):
	def test_a_second_one_is_refused(self):
		opening, volunteer = self.opening(), self.volunteer()
		application_service.apply(opening.name, volunteer.name)

		with self.assertRaises(frappe.DuplicateEntryError):
			application_service.apply(opening.name, volunteer.name)

	def test_a_different_opening_is_not_a_duplicate(self):
		volunteer = self.volunteer()
		application_service.apply(self.opening().name, volunteer.name)

		self.assertTrue(application_service.apply(self.opening().name, volunteer.name).name)

	def test_applying_again_after_withdrawing_is_allowed(self):
		"""Applying again after a no is a real thing people do, and it produces a
		second record rather than overwriting the first."""
		opening, volunteer = self.opening(), self.volunteer()
		first = application_service.apply(opening.name, volunteer.name)
		application_service.withdraw(first, "Something came up.")

		second = application_service.apply(opening.name, volunteer.name)

		self.assertNotEqual(second.name, first.name)

	def test_applying_again_after_a_rejection_is_allowed(self):
		opening, volunteer = self.opening(), self.volunteer()
		first = application_service.apply(opening.name, volunteer.name)
		first.status = applicant_fields.STATUS_REJECTED
		first.save(ignore_permissions=True)

		self.assertTrue(application_service.apply(opening.name, volunteer.name).name)


class TestTheQuestionsAndTheAnswers(ApplicationTestCase):
	def question(self, **overrides):
		values = {
			"question_id": "Q1",
			"question": "Which ward can you work in?",
			"question_type": "Text",
			"is_required": 1,
		}
		values.update(overrides)

		return values

	def test_the_questions_come_back_in_order(self):
		opening = self.asking(
			self.question(question_id="Q1"), self.question(question_id="Q2", question="And when?")
		)

		self.assertEqual(
			[row["question_id"] for row in application_service.questions(opening.name)],
			["Q1", "Q2"],
		)

	def test_the_marking_scheme_is_not_offered_to_the_candidate(self):
		"""Somebody who could read `expected_answer` would be answering a
		different exam."""
		opening = self.asking(self.question(expected_answer="Kigamboni", weight=5))

		self.assertNotIn("expected_answer", application_service.questions(opening.name)[0])
		self.assertNotIn("weight", application_service.questions(opening.name)[0])

	def test_a_required_question_has_to_be_answered(self):
		opening = self.asking(self.question())

		with self.assertRaises(frappe.MandatoryError):
			application_service.apply(opening.name, self.volunteer().name, answers={})

	def test_an_optional_one_does_not(self):
		opening = self.asking(self.question(is_required=0))

		self.assertTrue(
			application_service.apply(opening.name, self.volunteer().name, answers={}).name
		)

	def test_the_answer_is_stored_with_the_question_as_it_was_asked(self):
		opening = self.asking(self.question())
		applicant = application_service.apply(
			opening.name, self.volunteer().name, answers={"Q1": "Kigamboni"}
		)
		row = applicant.get(applicant_fields.ANSWERS_FIELD)[0]

		self.assertEqual(row.answer, "Kigamboni")
		self.assertEqual(row.question, "Which ward can you work in?")
		self.assertEqual(row.question_type, "Text")

	def test_rewording_the_question_afterwards_does_not_rewrite_the_answer(self):
		opening = self.asking(self.question())
		applicant = application_service.apply(
			opening.name, self.volunteer().name, answers={"Q1": "Kigamboni"}
		)

		opening.screening_questions[0].question = "Where exactly?"
		opening.save(ignore_permissions=True)
		applicant.reload()

		self.assertEqual(
			applicant.get(applicant_fields.ANSWERS_FIELD)[0].question,
			"Which ward can you work in?",
		)

	def test_an_answer_to_a_question_that_was_not_asked_is_dropped(self):
		"""The rows are driven by the opening, never by the payload."""
		opening = self.asking(self.question())
		applicant = application_service.apply(
			opening.name,
			self.volunteer().name,
			answers={"Q1": "Kigamboni", "Q99": "Something nobody asked"},
		)

		self.assertEqual(len(applicant.get(applicant_fields.ANSWERS_FIELD)), 1)

	def test_a_number_question_refuses_words(self):
		opening = self.asking(self.question(question_type="Number"))

		with self.assertRaises(frappe.ValidationError):
			application_service.apply(
				opening.name, self.volunteer().name, answers={"Q1": "quite a lot"}
			)

	def test_a_select_question_refuses_an_option_it_does_not_offer(self):
		opening = self.asking(self.question(question_type="Select", options="Yes\nNo\nSometimes"))

		with self.assertRaises(frappe.ValidationError):
			application_service.apply(
				opening.name, self.volunteer().name, answers={"Q1": "Occasionally"}
			)

	def test_a_multiselect_answer_is_stored_as_written(self):
		opening = self.asking(
			self.question(question_type="MultiSelect", options="Mornings\nEvenings\nWeekends")
		)
		applicant = application_service.apply(
			opening.name, self.volunteer().name, answers={"Q1": ["Mornings", "Weekends"]}
		)

		self.assertEqual(
			applicant.get(applicant_fields.ANSWERS_FIELD)[0].answer, "Mornings, Weekends"
		)

	def test_a_yes_no_question_refuses_anything_else(self):
		opening = self.asking(self.question(question_type="Yes/No"))

		with self.assertRaises(frappe.ValidationError):
			application_service.apply(
				opening.name, self.volunteer().name, answers={"Q1": "Probably"}
			)

	def test_an_upload_question_refuses_something_that_is_not_an_uploaded_file(self):
		opening = self.asking(self.question(question_type="Upload"))

		with self.assertRaises(frappe.ValidationError):
			application_service.apply(
				opening.name, self.volunteer().name, answers={"Q1": "/etc/passwd"}
			)


class TestTheQuestionSetLocksOnceAnybodyHasAnswered(ApplicationTestCase):
	def asked(self):
		opening = self.asking(
			{
				"question_id": "Q1",
				"question": "Which ward can you work in?",
				"question_type": "Text",
				"is_required": 1,
			}
		)
		application_service.apply(opening.name, self.volunteer().name, answers={"Q1": "Kigamboni"})

		return opening

	def test_a_new_question_is_refused(self):
		"""It would make every application retrospectively incomplete against a
		question none of them was shown."""
		opening = self.asked()
		opening.append(
			"screening_questions",
			{"question_id": "Q2", "question": "And when?", "question_type": "Text"},
		)

		with self.assertRaises(frappe.ValidationError):
			opening.save(ignore_permissions=True)

	def test_removing_one_is_refused(self):
		opening = self.asked()
		opening.screening_questions = []

		with self.assertRaises(frappe.ValidationError):
			opening.save(ignore_permissions=True)

	def test_changing_a_type_is_refused(self):
		opening = self.asked()
		opening.screening_questions[0].question_type = "Number"

		with self.assertRaises(frappe.ValidationError):
			opening.save(ignore_permissions=True)

	def test_rewording_one_is_allowed(self):
		"""A typo in a question fifty people already answered is worth fixing, and
		the answers keep the wording they were asked under."""
		opening = self.asked()
		opening.screening_questions[0].question = "Which ward can you work in, exactly?"
		opening.save(ignore_permissions=True)

		self.assertTrue(opening.name)

	def test_before_anybody_answers_the_set_is_free(self):
		opening = self.asking(
			{"question_id": "Q1", "question": "Which ward?", "question_type": "Text"}
		)
		opening.append(
			"screening_questions",
			{"question_id": "Q2", "question": "And when?", "question_type": "Text"},
		)
		opening.save(ignore_permissions=True)

		self.assertEqual(len(opening.screening_questions), 2)


class TestAWithdrawalIsNotARejection(ApplicationTestCase):
	def test_it_records_when_and_why(self):
		applicant = application_service.apply(self.opening().name, self.volunteer().name)
		application_service.withdraw(applicant, "Something came up.")

		self.assertTrue(applicant.get(applicant_fields.WITHDRAWN_FIELD))
		self.assertEqual(applicant.get("vmms_withdrawal_reason"), "Something came up.")

	def test_the_status_is_never_rejected(self):
		"""Rejecting somebody who withdrew puts a decision nobody made into their
		record."""
		applicant = application_service.apply(self.opening().name, self.volunteer().name)
		application_service.withdraw(applicant, "Something came up.")

		self.assertNotEqual(applicant.status, applicant_fields.STATUS_REJECTED)
		self.assertEqual(applicant.status, applicant_fields.STATUS_HOLD)

	def test_withdrawing_twice_changes_nothing(self):
		applicant = application_service.apply(self.opening().name, self.volunteer().name)
		application_service.withdraw(applicant, "Something came up.")
		first = applicant.get(applicant_fields.WITHDRAWN_FIELD)

		application_service.withdraw(applicant, "Still something.")

		self.assertEqual(applicant.get(applicant_fields.WITHDRAWN_FIELD), first)


class TestAnAcceptedApplicationBecomesWork(ApplicationTestCase):
	def deployment(self):
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}")

		return fixtures.make_deployment(terms.name, self.branch)

	def accepted(self, **overrides):
		applicant = application_service.apply(self.opening(**overrides).name, self.volunteer().name)
		applicant.status = applicant_fields.STATUS_ACCEPTED
		applicant.save(ignore_permissions=True)

		return applicant

	def test_an_opening_that_staffs_a_deployment_produces_an_assignment(self):
		applicant = self.accepted(vmms_deployment=self.deployment().name)
		answer = application_service.convert(applicant)

		self.assertTrue(answer["deployment_assignment"])
		self.assertIsNone(answer["task"])

	def test_the_assignment_is_a_question_rather_than_a_placement(self):
		"""Accepting a role in the abstract is not agreeing to a particular
		mission document."""
		from vmmsx.deployment.services import assignment as assignment_service

		applicant = self.accepted(vmms_deployment=self.deployment().name)
		answer = application_service.convert(applicant)
		doc = frappe.get_doc(assignment_service.ASSIGNMENT_DOCTYPE, answer["deployment_assignment"])

		self.assertEqual(doc.status, assignment_service.STATUS_PENDING)

	def test_an_opening_that_names_no_deployment_produces_a_task(self):
		applicant = self.accepted()
		answer = application_service.convert(applicant)

		self.assertTrue(answer["task"])
		self.assertIsNone(answer["deployment_assignment"])

	def test_converting_twice_produces_nothing_the_second_time(self):
		"""A double-clicked button must not put the same person on the same
		deployment twice."""
		applicant = self.accepted(vmms_deployment=self.deployment().name)
		first = application_service.convert(applicant)
		second = application_service.convert(applicant)

		self.assertFalse(first["already"])
		self.assertTrue(second["already"])
		self.assertEqual(second["deployment_assignment"], first["deployment_assignment"])

	def test_an_application_nobody_accepted_does_not_convert(self):
		applicant = application_service.apply(self.opening().name, self.volunteer().name)

		with self.assertRaises(frappe.ValidationError):
			application_service.convert(applicant)

	def test_a_withdrawn_application_does_not_convert(self):
		applicant = self.accepted()
		application_service.withdraw(applicant, "Something came up.")
		applicant.status = applicant_fields.STATUS_ACCEPTED
		applicant.save(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			application_service.convert(applicant)


class TestWhatTheApplicantIsShownBack(ApplicationTestCase):
	def test_the_dto_carries_the_answers_and_not_the_recruiters_notes(self):
		opening = self.asking(
			{"question_id": "Q1", "question": "Which ward?", "question_type": "Text"}
		)
		applicant = application_service.apply(
			opening.name, self.volunteer().name, answers={"Q1": "Kigamboni"}
		)
		applicant.applicant_rating = 3
		applicant.notes = "Seemed nervous."
		applicant.save(ignore_permissions=True)

		answer = application_service.dto(applicant)

		self.assertEqual(answer["answers"][0]["answer"], "Kigamboni")
		self.assertNotIn("applicant_rating", answer)
		self.assertNotIn("notes", answer)

	def test_it_says_whether_the_applicant_withdrew(self):
		applicant = application_service.apply(self.opening().name, self.volunteer().name)

		self.assertFalse(application_service.dto(applicant)["is_withdrawn"])

		application_service.withdraw(applicant, "Something came up.")

		self.assertTrue(application_service.dto(applicant)["is_withdrawn"])
