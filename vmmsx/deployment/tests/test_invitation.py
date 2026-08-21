# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Asking a volunteer to go, and what their answer does.

The roster is a register of `VMMS Deployment Assignment` documents, so an
invitation is an assignment raised as `Pending` and an answer is that assignment
moving to `Accepted` or `Declined`. These tests are about the distinctions that
model exists to keep straight:

* **Placed is not asked.** `Assigned` is a coordinator saying somebody is going;
  `Pending` is a question. Under the child table this was blank-versus-`invited`
  in one nullable field, and it survives the move intact.
* **Answering is answering.** A decline now takes somebody off the deployment,
  where it used to leave them on it. `assignment.py`'s docstring sets out why:
  the old behaviour existed only because one field had to carry both "did you
  go" and "what did you say", and those are now two fields.
* **Asking again after a no is a new question.** It raises a second assignment
  rather than overwriting the first, which is the thing a single child row could
  never do.
"""

import frappe

from vmmsx.api import deployment as api
from vmmsx.deployment.services import assignment, invitation, participation
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase


class TestInvitation(DeploymentTestCase):
	def setUp(self):
		super().setUp()

		self.terms = fixtures.make_terms()
		self.branch = self.society_a["branch"]
		self.volunteer = fixtures.make_volunteer(fixtures.make_profile(), self.branch).name

	def deployment(self, participants=None):
		return fixtures.make_deployment(self.terms.name, self.branch, participants=participants)

	def assignment_for(self, deployment, volunteer=None):
		return assignment.open_assignment(deployment.name, volunteer or self.volunteer)

	# --- asking -----------------------------------------------------------

	def test_asking_raises_a_pending_assignment(self):
		deployment = self.deployment()

		outcome = invitation.invite(deployment, self.volunteer)

		self.assertEqual(outcome["status"], assignment.STATUS_PENDING)
		self.assertTrue(outcome["notified"])
		self.assertIsNotNone(self.assignment_for(deployment).invited_on)

	def test_a_pending_assignment_is_not_yet_on_the_deployment(self):
		"""A question outstanding holds no place and permits no time log.

		This is the sharpest difference from the child-table model, where the row
		existed the moment somebody was asked and `is_participant` was true from
		then on.
		"""
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)

		self.assertFalse(participation.is_participant(deployment.name, self.volunteer))

	def test_asking_twice_does_not_ask_twice(self):
		deployment = self.deployment()

		invitation.invite(deployment, self.volunteer)
		second = invitation.invite(frappe.get_doc(deployment.doctype, deployment.name), self.volunteer)

		self.assertFalse(second["notified"])
		self.assertEqual(second["status"], assignment.STATUS_PENDING)
		self.assertEqual(len(assignment.roster_of(deployment.name)), 1)

	def test_being_placed_is_not_being_asked(self):
		"""`Assigned` is not `Pending`, which is the distinction the two exist for."""
		deployment = self.deployment(participants=[self.volunteer])

		row = self.assignment_for(deployment)

		self.assertEqual(row.status, assignment.STATUS_ASSIGNED)
		self.assertIsNone(row.invited_on)
		self.assertTrue(participation.is_participant(deployment.name, self.volunteer))

	def test_asking_somebody_already_placed_is_refused(self):
		"""They already have an open assignment; asking would be a second one."""
		deployment = self.deployment(participants=[self.volunteer])

		outcome = invitation.invite(deployment, self.volunteer)

		self.assertEqual(outcome["status"], assignment.STATUS_ASSIGNED)
		self.assertFalse(outcome["notified"])
		self.assertEqual(len(assignment.roster_of(deployment.name)), 1)

	# --- answering --------------------------------------------------------

	def test_accepting_records_the_answer(self):
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)

		outcome = assignment.respond(self.assignment_for(deployment), accepted=True)

		self.assertEqual(outcome["status"], assignment.STATUS_ACCEPTED)
		self.assertIsNotNone(outcome["responded_on"])
		self.assertTrue(participation.is_participant(deployment.name, self.volunteer))

	def test_declining_records_the_answer_and_the_reason(self):
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)

		assignment.respond(self.assignment_for(deployment), accepted=False, note="Sitting exams.")

		row = frappe.get_doc(
			assignment.ASSIGNMENT_DOCTYPE,
			{"deployment": deployment.name, "volunteer": self.volunteer},
		)

		self.assertEqual(row.status, assignment.STATUS_DECLINED)
		self.assertEqual(row.response_note, "Sitting exams.")

	def test_declining_takes_them_off_the_deployment(self):
		"""The behaviour change from the child-table model, asserted rather than described.

		A decline used to leave `is_participant` untouched, because one field had
		to carry both what somebody said and whether they went. Those are separate
		facts now — `status` and `joined_on` — so a decline can mean what it says.
		"""
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)
		assignment.respond(self.assignment_for(deployment), accepted=False)

		self.assertFalse(participation.is_participant(deployment.name, self.volunteer))

	def test_the_declined_assignment_is_kept(self):
		"""Not deleted: the register remembers that this person was asked."""
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)
		assignment.respond(self.assignment_for(deployment), accepted=False)

		roster = assignment.roster_of(deployment.name)

		self.assertEqual(len(roster), 1)
		self.assertEqual(roster[0]["status"], assignment.STATUS_DECLINED)

	def test_asking_again_after_a_decline_raises_a_second_assignment(self):
		"""The thing one child row could never do: keep both answers."""
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)
		assignment.respond(self.assignment_for(deployment), accepted=False)

		invitation.invite(frappe.get_doc(deployment.doctype, deployment.name), self.volunteer)

		statuses = sorted(row["status"] for row in assignment.roster_of(deployment.name))

		self.assertEqual(statuses, [assignment.STATUS_DECLINED, assignment.STATUS_PENDING])

	def test_answering_the_same_way_twice_is_a_no_op(self):
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)
		row = self.assignment_for(deployment)
		assignment.respond(row, accepted=True)

		outcome = assignment.respond(row, accepted=True)

		self.assertEqual(outcome["status"], assignment.STATUS_ACCEPTED)

	def test_changing_an_answer_is_refused(self):
		"""Not overwritten silently: somebody has planned around the first answer."""
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)
		row = self.assignment_for(deployment)
		assignment.respond(row, accepted=True)

		with self.assertRaises(frappe.ValidationError):
			assignment.respond(row, accepted=False)

	# --- the headcount ----------------------------------------------------

	def test_a_deployment_can_ask_more_people_than_it_needs(self):
		"""Asking twenty to fill six is how a coordinator fills six."""
		deployment = fixtures.make_deployment(self.terms.name, self.branch, volunteers_required=1)
		second = fixtures.make_volunteer(fixtures.make_profile(), self.branch).name

		invitation.invite(deployment, self.volunteer)
		invitation.invite(frappe.get_doc(deployment.doctype, deployment.name), second)

		self.assertEqual(assignment.counts_for(deployment.name)["Pending"], 2)

	def test_the_place_after_the_last_one_cannot_be_accepted(self):
		"""What is capped is the seventh yes, not the seventh question."""
		deployment = fixtures.make_deployment(self.terms.name, self.branch, volunteers_required=1)
		second = fixtures.make_volunteer(fixtures.make_profile(), self.branch).name

		invitation.invite(deployment, self.volunteer)
		invitation.invite(frappe.get_doc(deployment.doctype, deployment.name), second)

		assignment.respond(self.assignment_for(deployment), accepted=True)

		with self.assertRaises(frappe.ValidationError):
			assignment.respond(self.assignment_for(deployment, second), accepted=True)

	def test_a_deployment_that_has_not_said_how_many_is_never_full(self):
		deployment = self.deployment()
		second = fixtures.make_volunteer(fixtures.make_profile(), self.branch).name

		invitation.invite(deployment, self.volunteer)
		invitation.invite(frappe.get_doc(deployment.doctype, deployment.name), second)
		assignment.respond(self.assignment_for(deployment), accepted=True)
		assignment.respond(self.assignment_for(deployment, second), accepted=True)

		self.assertEqual(assignment.counts_for(deployment.name)["on_deployment"], 2)

	# --- the leader -------------------------------------------------------

	def test_a_deployment_admits_one_leader(self):
		second = fixtures.make_volunteer(fixtures.make_profile(), self.branch).name
		deployment = self.deployment(participants=[self.volunteer, second])

		first, other = assignment.roster_of(deployment.name)
		assignment.set_role(frappe.get_doc(assignment.ASSIGNMENT_DOCTYPE, first["name"]), "leader")

		with self.assertRaises(frappe.ValidationError):
			assignment.set_role(frappe.get_doc(assignment.ASSIGNMENT_DOCTYPE, other["name"]), "leader")

	def test_a_leader_who_declines_is_not_leading_anything(self):
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)
		row = self.assignment_for(deployment)
		assignment.respond(row, accepted=True)
		assignment.set_role(row, "leader")

		self.assertEqual(assignment.leader_of(deployment.name), self.volunteer)

		assignment.withdraw(row)

		self.assertIsNone(assignment.leader_of(deployment.name))

	# --- through the volunteer's own door ---------------------------------

	def test_a_volunteer_can_answer_their_own_assignment(self):
		"""The case an ordinary `save()` gets wrong.

		A volunteer holds no Geo Assignment and no role on the deployment
		register, so the permission layer refuses the only person entitled to
		answer. What admits them is the ownership check in `api/deployment.py`,
		and this is the test that fails if the elevated write in
		`assignment.respond` is removed.
		"""
		user = fixtures.make_user("invited-volunteer")
		volunteer = fixtures.make_volunteer(fixtures.make_profile(email=user, user=user), self.branch).name

		deployment = self.deployment()
		invitation.invite(deployment, volunteer)
		row = self.assignment_for(deployment, volunteer)

		with fixtures.acting_as(user):
			outcome = api.respond_to_assignment(row.name, accept=1)

		self.assertEqual(outcome["status"], assignment.STATUS_ACCEPTED)

	def test_a_volunteer_cannot_answer_somebody_elses(self):
		user = fixtures.make_user("uninvited-volunteer")
		fixtures.make_volunteer(fixtures.make_profile(email=user, user=user), self.branch)

		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)
		row = self.assignment_for(deployment)

		with fixtures.acting_as(user), self.assertRaises(frappe.PermissionError):
			api.respond_to_assignment(row.name, accept=1)

	def test_decline_arrives_as_a_decline_over_http(self):
		"""`"false"` is a truthy string. Read naively, a volunteer declining
		would be recorded as accepting, which is the worst direction for this
		particular field to be wrong in."""
		user = fixtures.make_user("declining-volunteer")
		volunteer = fixtures.make_volunteer(fixtures.make_profile(email=user, user=user), self.branch).name

		deployment = self.deployment()
		invitation.invite(deployment, volunteer)
		row = self.assignment_for(deployment, volunteer)

		with fixtures.acting_as(user):
			outcome = api.respond_to_assignment(row.name, accept="false")

		self.assertEqual(outcome["status"], assignment.STATUS_DECLINED)

	def test_the_volunteers_own_read_carries_the_whole_mission(self):
		"""Accepting is accepting the terms, so the terms have to be in front of them."""
		user = fixtures.make_user("reading-volunteer")
		volunteer = fixtures.make_volunteer(fixtures.make_profile(email=user, user=user), self.branch).name

		deployment = self.deployment()
		invitation.invite(deployment, volunteer)
		row = self.assignment_for(deployment, volunteer)

		with fixtures.acting_as(user):
			answer = api.get_my_assignment(row.name)

		self.assertEqual(answer["assignment"]["name"], row.name)
		self.assertIn("objectives", answer["terms"])
		self.assertEqual(answer["terms"]["name"], self.terms.name)

	# --- reading ----------------------------------------------------------

	def test_waiting_and_answered_are_separate_lists(self):
		waiting = self.deployment()
		answered = self.deployment()

		invitation.invite(waiting, self.volunteer)
		invitation.invite(answered, self.volunteer)
		assignment.respond(self.assignment_for(answered), accepted=True)

		pending = [row["deployment"] for row in invitation.pending_for(self.volunteer)]
		settled = [row["deployment"] for row in invitation.answered_for(self.volunteer)]

		self.assertEqual(pending, [waiting.name])
		self.assertEqual(settled, [answered.name])

	def test_somebody_placed_directly_is_in_neither_list(self):
		"""They were never asked, so they appear in no list of questions."""
		self.deployment(participants=[self.volunteer])

		self.assertEqual(invitation.pending_for(self.volunteer), [])
		self.assertEqual(invitation.answered_for(self.volunteer), [])

	def test_the_requester_is_told_as_well_as_the_deployment_owner(self):
		"""Whoever raised the need hears the answer, not only whoever filed the
		deployment. The two are often different people, and the branch waiting on
		an answer is usually the first of them.

		Both records are attributed to real users rather than to Administrator,
		because `askers` deliberately drops the system account: notifying it
		would put every invitation in the inbox of whoever installed the site.
		The ownership is set afterwards rather than by creating the records as
		those users, so this test arranges the one fact it is about instead of a
		pair of role grants that have nothing to do with it.
		"""
		filer = fixtures.make_user("deployment-filer")
		asker = fixtures.make_user("need-raiser")

		deployment = self.deployment()
		request = fixtures.make_request(self.terms.name, self.branch)

		frappe.db.set_value(deployment.doctype, deployment.name, "owner", filer)
		frappe.db.set_value(request.doctype, request.name, "owner", asker)
		request.db_set("deployment", deployment.name, update_modified=False)

		deployment.reload()

		self.assertEqual(invitation.askers(deployment), sorted([filer, asker]))

	def test_the_system_account_is_never_told(self):
		"""A deployment filed by Administrator notifies nobody, rather than
		notifying the account nobody reads."""
		deployment = self.deployment()

		self.assertNotIn("Administrator", invitation.askers(deployment))
