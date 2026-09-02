# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Changing a deployment people have already been asked to go on.

Before anybody is invited, a deployment is a draft and editing it is editing a
draft. After, it is an arrangement other people have made their week around, and
this suite is about the three rules that arrive with the first invitation:

1. **A reason, written for this change.** Not one left in the field from last
   month — the field has to have changed in the same save, which is the only
   version of "give a reason" that cannot be satisfied by doing nothing.
2. **In the feed, field by field.** "This deployment changed" is not something
   anybody can act on; "the meeting point moved from the branch office to the bus
   stand" is.
3. **To the people still on it.** Placed, asked or accepted. Not the ones who
   declined, who are not going.

And the rule that says when none of it applies: a deployment nobody is on.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.deployment.services import change, feed, invitation
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class ChangeTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.terms = fixtures.make_terms()

	def deployment(self, **overrides):
		return fixtures.make_deployment(self.terms.name, self.society_a["branch"], **overrides)

	def with_somebody_asked(self, **overrides):
		"""A deployment with one outstanding invitation. Where the rules begin."""
		deployment = self.deployment(**overrides)
		volunteer = fixtures.make_volunteer(
			fixtures.make_profile("Asked", frappe.generate_hash(length=6)),
			self.society_a["branch"],
		)
		invitation.invite(deployment, volunteer.name)

		return deployment, volunteer


class TestADraftIsJustADraft(ChangeTestCase):
	def test_a_deployment_nobody_is_on_needs_no_reason(self):
		deployment = self.deployment()
		deployment.meeting_point = "Branch office car park"
		deployment.save()

		self.assertEqual(deployment.meeting_point, "Branch office car park")

	def test_and_leaves_no_feed_entry(self):
		deployment = self.deployment()
		before = feed.of(deployment.name)["count"]

		deployment.meeting_point = "Branch office car park"
		deployment.save()

		self.assertEqual(feed.of(deployment.name)["count"], before)

	def test_an_immaterial_edit_needs_no_reason_even_with_people_on_it(self):
		"""The notes and the headcount are a coordinator tidying up."""
		deployment, _volunteer = self.with_somebody_asked()
		deployment.notes = "Tidied up."
		deployment.volunteers_required = 12
		deployment.save()

		self.assertEqual(deployment.notes, "Tidied up.")


class TestAChangePeopleArrangedTheirWeekAroundNeedsAReason(ChangeTestCase):
	def test_moving_the_meeting_point_without_a_reason_is_refused(self):
		deployment, _volunteer = self.with_somebody_asked()
		deployment.meeting_point = "The bus stand"

		with self.assertRaises(frappe.MandatoryError):
			deployment.save()

	def test_moving_the_dates_without_a_reason_is_refused(self):
		deployment, _volunteer = self.with_somebody_asked()
		deployment.planned_start = f"{add_days(today(), 4)} 07:00:00"
		deployment.planned_end = f"{add_days(today(), 9)} 18:00:00"

		with self.assertRaises(frappe.MandatoryError):
			deployment.save()

	def test_changing_the_coordinator_without_a_reason_is_refused(self):
		deployment, _volunteer = self.with_somebody_asked()
		deployment.coordinator = fixtures.make_user("new_coordinator")

		with self.assertRaises(frappe.MandatoryError):
			deployment.save()

	def test_a_reason_lets_it_through(self):
		deployment, _volunteer = self.with_somebody_asked()
		deployment.meeting_point = "The bus stand"
		deployment.change_reason = "The car park is flooded."
		deployment.save()

		self.assertEqual(deployment.meeting_point, "The bus stand")

	def test_last_months_reason_is_not_a_reason(self):
		"""The failure mode of every mandatory justification field that is checked
		for emptiness rather than for freshness."""
		deployment, _volunteer = self.with_somebody_asked()
		deployment.meeting_point = "The bus stand"
		deployment.change_reason = "The car park is flooded."
		deployment.save()

		deployment.meeting_point = "The market"

		with self.assertRaises(frappe.MandatoryError):
			deployment.save()


class TestTheChangeIsWrittenDownAndSent(ChangeTestCase):
	def test_the_feed_names_what_moved_and_to_what(self):
		deployment, _volunteer = self.with_somebody_asked(meeting_point="Branch office car park")
		deployment.meeting_point = "The bus stand"
		deployment.change_reason = "The car park is flooded."
		deployment.save()

		notes = " ".join(row["note"] or "" for row in feed.of(deployment.name)["entries"])

		self.assertIn("Branch office car park", notes)
		self.assertIn("The bus stand", notes)
		self.assertIn("The car park is flooded.", notes)

	def test_everybody_still_on_it_is_told(self):
		deployment, volunteer = self.with_somebody_asked()
		deployment.meeting_point = "The bus stand"
		deployment.change_reason = "The car park is flooded."
		deployment.save()

		self.assertEqual([row["volunteer"] for row in change.affected(deployment.name)], [volunteer.name])

	def test_somebody_who_declined_is_not_affected(self):
		"""Telling them the briefing moved is noise that trains people to stop
		reading."""
		from vmmsx.deployment.services import assignment as assignment_service

		deployment, volunteer = self.with_somebody_asked()
		assignment_service.respond(
			assignment_service.open_assignment(deployment.name, volunteer.name), accepted=False
		)

		self.assertEqual(change.affected(deployment.name), [])

	def test_a_change_with_nobody_left_on_it_needs_no_reason_again(self):
		from vmmsx.deployment.services import assignment as assignment_service

		deployment, volunteer = self.with_somebody_asked()
		assignment_service.respond(
			assignment_service.open_assignment(deployment.name, volunteer.name), accepted=False
		)

		# Answering an assignment writes the deployment's own feed, so the copy
		# this test is holding is a version behind. A screen re-reads between
		# requests; a test holding one object across both acts has to say so.
		deployment.reload()

		deployment.meeting_point = "The bus stand"
		deployment.save()

		self.assertEqual(deployment.meeting_point, "The bus stand")


class TestWhatCountsAsMaterial(ChangeTestCase):
	def test_the_list_is_where_the_judgement_lives(self):
		"""Not a heuristic. Where it is, when it is, how to get there, who is in
		charge, and what it is run under."""
		for field in ("planned_start", "meeting_point", "coordinator", "travel_notes"):
			self.assertIn(field, change.MATERIAL_FIELDS)

		for field in ("notes", "volunteers_required", "email_template", "status"):
			self.assertNotIn(field, change.MATERIAL_FIELDS)

	def test_a_change_reports_what_it_was_and_what_it_became(self):
		deployment = self.deployment(meeting_point="Branch office car park")
		deployment.meeting_point = "The bus stand"

		changed = change.material_changes(deployment)

		self.assertEqual(len(changed), 1)
		self.assertEqual(changed[0]["was"], "Branch office car park")
		self.assertEqual(changed[0]["now"], "The bus stand")

	def test_a_blank_reads_as_nothing_rather_than_as_none(self):
		deployment = self.deployment()
		deployment.travel_notes = "The last two kilometres are unpaved."

		self.assertEqual(change.material_changes(deployment)[0]["was"], "nothing")
