# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What became of one person's deployment: the day itself, and the swaps before it.

The roster used to be able to say what somebody was asked and what they said.
This suite is about the four things it can now say afterwards:

1. **What happened on the day.** Participated, Partial Attendance, No Show —
   three answers to "did they go", which is a different question from "what did
   they say" and was previously unanswerable. The two that mean they were there
   keep them able to file their own hours; No Show does not.
2. **Expired is not Declined.** A question nobody answered in time and a person
   who said no look identical in a register that only has one of them, and only
   one of the two is worth chasing.
3. **A replacement keeps both records.** The original is never overwritten: it
   moves to Replaced and points at the assignment that took over. Editing the
   volunteer instead would erase the fact that anybody had ever been asked.
4. **Readiness is recorded and gates nothing.** Refusing somebody at the gate on
   a field nobody filled in is how a record-keeping gap becomes an operational
   failure.
"""

import frappe
from frappe.utils import add_days, now_datetime, today

from vmmsx.deployment.services import assignment as assignment_service
from vmmsx.deployment.services import participation
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class OutcomeTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.terms = fixtures.make_terms()

	def volunteer(self, handle: str | None = None):
		return fixtures.make_volunteer(
			fixtures.make_profile("Roster", handle or frappe.generate_hash(length=6)),
			self.society_a["branch"],
		)

	def placed(self, **overrides):
		"""One deployment and one person placed on it."""
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"], **overrides)
		volunteer = self.volunteer()
		doc = assignment_service.create(
			deployment, volunteer.name, status=assignment_service.STATUS_ASSIGNED
		)

		return deployment, doc

	def asked(self, **overrides):
		"""One deployment and one outstanding question."""
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"], **overrides)
		volunteer = self.volunteer()
		doc = assignment_service.create(
			deployment, volunteer.name, status=assignment_service.STATUS_PENDING
		)

		return deployment, doc


class TestWhatHappenedOnTheDay(OutcomeTestCase):
	def test_somebody_placed_can_be_marked_as_having_gone(self):
		_deployment, doc = self.placed()
		answer = assignment_service.record_attendance(doc, assignment_service.STATUS_PARTICIPATED)

		self.assertTrue(answer["has_outcome"])
		self.assertTrue(answer["attended"])

	def test_partial_attendance_is_its_own_answer(self):
		_deployment, doc = self.placed()
		assignment_service.record_attendance(doc, assignment_service.STATUS_PARTIAL)

		self.assertEqual(doc.status, assignment_service.STATUS_PARTIAL)

	def test_a_no_show_is_recorded_and_is_not_attendance(self):
		_deployment, doc = self.placed()
		answer = assignment_service.record_attendance(doc, assignment_service.STATUS_NO_SHOW)

		self.assertTrue(answer["has_outcome"])
		self.assertFalse(answer["attended"])

	def test_somebody_who_was_there_can_still_file_their_hours(self):
		"""The rule this outcome must not break: a register that recorded
		attendance and then refused the volunteer's own account of it would punish
		accurate record-keeping."""
		deployment, doc = self.placed()
		assignment_service.record_attendance(doc, assignment_service.STATUS_PARTICIPATED)

		self.assertTrue(participation.is_participant(deployment.name, doc.volunteer))

	def test_somebody_who_did_not_come_cannot(self):
		deployment, doc = self.placed()
		assignment_service.record_attendance(doc, assignment_service.STATUS_NO_SHOW)

		self.assertFalse(participation.is_participant(deployment.name, doc.volunteer))

	def test_the_verified_hours_record_who_verified_them(self):
		_deployment, doc = self.placed()
		assignment_service.record_attendance(doc, assignment_service.STATUS_PARTIAL, hours=4.5)

		self.assertEqual(doc.verified_hours, 4.5)
		self.assertEqual(doc.attendance_verified_by, frappe.session.user)
		self.assertTrue(doc.attendance_verified_on)

	def test_recording_the_same_outcome_twice_is_harmless(self):
		_deployment, doc = self.placed()
		assignment_service.record_attendance(doc, assignment_service.STATUS_PARTICIPATED)
		answer = assignment_service.record_attendance(doc, assignment_service.STATUS_PARTICIPATED)

		self.assertEqual(answer["status"], assignment_service.STATUS_PARTICIPATED)

	def test_one_outcome_does_not_become_another(self):
		"""Correcting a wrong entry is an amendment somebody can see, not a field
		quietly changing back."""
		_deployment, doc = self.placed()
		assignment_service.record_attendance(doc, assignment_service.STATUS_PARTICIPATED)

		with self.assertRaises(frappe.ValidationError):
			assignment_service.record_attendance(doc, assignment_service.STATUS_NO_SHOW)

	def test_an_outcome_that_is_not_one_of_the_three_is_refused(self):
		_deployment, doc = self.placed()

		with self.assertRaises(frappe.ValidationError):
			assignment_service.record_attendance(doc, "Turned up late")

	def test_a_declined_assignment_reaches_no_outcome(self):
		"""They said no. There is no day for them to have attended."""
		_deployment, doc = self.asked()
		assignment_service.respond(doc, accepted=False)

		with self.assertRaises(frappe.ValidationError):
			assignment_service.record_attendance(doc, assignment_service.STATUS_NO_SHOW)

	def test_the_roster_counts_the_outcomes(self):
		deployment, doc = self.placed()
		assignment_service.record_attendance(doc, assignment_service.STATUS_PARTICIPATED)

		counts = assignment_service.counts_for(deployment.name)

		self.assertEqual(counts["outcomes"], 1)
		self.assertEqual(counts["attended"], 1)


class TestExpiredIsNotDeclined(OutcomeTestCase):
	def test_an_invitation_with_no_answer_by_date_stands(self):
		"""A society that sets none has questions that stand until somebody
		answers them, which is what setting none means."""
		_deployment, doc = self.asked()
		assignment_service.expire_overdue()
		doc.reload()

		self.assertEqual(doc.status, assignment_service.STATUS_PENDING)

	def test_an_overdue_invitation_expires(self):
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"])
		doc = assignment_service.create(
			deployment,
			self.volunteer().name,
			status=assignment_service.STATUS_PENDING,
			invitation_expires_on=f"{add_days(today(), -1)} 09:00:00",
		)

		assignment_service.expire_overdue()
		doc.reload()

		self.assertEqual(doc.status, assignment_service.STATUS_EXPIRED)

	def test_an_invitation_still_in_time_does_not(self):
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"])
		doc = assignment_service.create(
			deployment,
			self.volunteer().name,
			status=assignment_service.STATUS_PENDING,
			invitation_expires_on=f"{add_days(today(), 5)} 09:00:00",
		)

		assignment_service.expire_overdue()
		doc.reload()

		self.assertEqual(doc.status, assignment_service.STATUS_PENDING)

	def test_the_sweep_is_safe_to_run_twice(self):
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"])
		assignment_service.create(
			deployment,
			self.volunteer().name,
			status=assignment_service.STATUS_PENDING,
			invitation_expires_on=f"{add_days(today(), -1)} 09:00:00",
		)

		self.assertEqual(len(assignment_service.expire_overdue()["expired"]), 1)
		self.assertEqual(assignment_service.expire_overdue()["expired"], [])

	def test_an_expired_invitation_is_settled_and_not_an_answer(self):
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"])
		doc = assignment_service.create(
			deployment,
			self.volunteer().name,
			status=assignment_service.STATUS_PENDING,
			invitation_expires_on=f"{add_days(today(), -1)} 09:00:00",
		)
		assignment_service.expire_overdue()
		doc.reload()

		answer = assignment_service.dto(doc)

		self.assertTrue(answer["is_settled"])
		self.assertFalse(answer["is_open"])
		self.assertNotEqual(answer["status"], assignment_service.STATUS_DECLINED)


class TestADeclineKeepsItsReason(OutcomeTestCase):
	def test_the_reason_is_findable_as_a_reason(self):
		_deployment, doc = self.asked()
		assignment_service.respond(doc, accepted=False, note="I am away that week.")

		self.assertEqual(doc.decline_reason, "I am away that week.")

	def test_an_acceptance_records_none(self):
		_deployment, doc = self.asked()
		assignment_service.respond(doc, accepted=True, note="Happy to help.")

		self.assertIsNone(doc.decline_reason)


class TestAReplacementKeepsBothRecords(OutcomeTestCase):
	def test_the_original_moves_to_replaced_and_points_forward(self):
		deployment, doc = self.placed()
		answer = assignment_service.replace(doc, self.volunteer().name, "Called to another response.")

		self.assertEqual(answer["replaced"]["status"], assignment_service.STATUS_REPLACED)
		self.assertEqual(answer["replaced"]["replaced_by"], answer["replacement"]["name"])

	def test_and_the_replacement_points_back(self):
		deployment, doc = self.placed()
		answer = assignment_service.replace(doc, self.volunteer().name, "Called to another response.")

		self.assertEqual(answer["replacement"]["replaces"], doc.name)
		self.assertEqual(answer["replacement"]["replacement_reason"], "Called to another response.")

	def test_the_original_volunteer_is_never_overwritten(self):
		"""Editing the volunteer instead would erase the fact that anybody had
		ever been asked."""
		deployment, doc = self.placed()
		was = doc.volunteer

		assignment_service.replace(doc, self.volunteer().name, "Called to another response.")
		doc.reload()

		self.assertEqual(doc.volunteer, was)

	def test_the_swap_records_who_authorised_it(self):
		deployment, doc = self.placed()
		answer = assignment_service.replace(doc, self.volunteer().name, "Called away.")

		self.assertEqual(answer["replacement"]["replacement_authorised_by"], frappe.session.user)

	def test_a_replacement_with_no_reason_is_refused(self):
		deployment, doc = self.placed()

		with self.assertRaises(frappe.MandatoryError):
			assignment_service.replace(doc, self.volunteer().name, "")

	def test_the_replacement_is_a_question_rather_than_a_placement(self):
		"""Somebody stepping in at short notice is being asked, not told."""
		deployment, doc = self.placed()
		answer = assignment_service.replace(doc, self.volunteer().name, "Called away.")

		self.assertEqual(answer["replacement"]["status"], assignment_service.STATUS_PENDING)

	def test_the_replacement_carries_the_role_across(self):
		deployment, doc = self.placed()
		assignment_service.set_role(doc, "leader")
		answer = assignment_service.replace(doc, self.volunteer().name, "Called away.")

		self.assertEqual(answer["replacement"]["role"], "leader")

	def test_a_settled_assignment_cannot_be_replaced(self):
		_deployment, doc = self.asked()
		assignment_service.respond(doc, accepted=False)

		with self.assertRaises(frappe.ValidationError):
			assignment_service.replace(doc, self.volunteer().name, "Too late.")


class TestReadinessIsRecordedAndGatesNothing(OutcomeTestCase):
	def test_briefing_and_safety_are_two_separate_facts(self):
		_deployment, doc = self.placed()
		assignment_service.mark_briefed(doc)

		self.assertTrue(doc.briefing_completed_on)
		self.assertIsNone(doc.safety_acknowledged_on)

	def test_a_stamp_is_written_once(self):
		"""A second call is a button pressed twice, not a second arrival."""
		_deployment, doc = self.placed()
		assignment_service.check_in(doc)
		first = doc.checked_in_at

		assignment_service.check_in(doc, when=now_datetime())

		self.assertEqual(doc.checked_in_at, first)

	def test_checking_out_without_checking_in_is_refused(self):
		_deployment, doc = self.placed()

		with self.assertRaises(frappe.ValidationError):
			assignment_service.check_out(doc)

	def test_an_unbriefed_person_can_still_check_in(self):
		"""Refusing somebody at the gate on a field nobody filled in is how a
		record-keeping gap becomes an operational failure."""
		_deployment, doc = self.placed()
		assignment_service.check_in(doc)

		self.assertTrue(doc.checked_in_at)
		self.assertIsNone(doc.briefing_completed_on)
