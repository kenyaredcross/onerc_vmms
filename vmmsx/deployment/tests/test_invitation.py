# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Inviting a volunteer, and what their answer does and does not change.

The load-bearing claim in `deployment/services/invitation.py` is that an
invitation records a conversation without deciding who is on the roster. These
tests are mostly about that: a decline is remembered, and it leaves
`participation.is_participant` exactly where it was, because a coordinator who
lists somebody who actually served must not have that record invalidated by a
reply that never came.
"""

import frappe

from vmmsx.api import deployment as api
from vmmsx.deployment.services import invitation, participation
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

	# --- inviting ---------------------------------------------------------

	def test_inviting_puts_them_on_the_roster_as_invited(self):
		deployment = self.deployment()

		outcome = invitation.invite(deployment, self.volunteer)

		self.assertEqual(outcome["response"], invitation.INVITED)
		self.assertTrue(outcome["notified"])
		self.assertIsNotNone(outcome["invited_on"])
		self.assertTrue(participation.is_participant(deployment.name, self.volunteer))

	def test_inviting_twice_does_not_notify_twice(self):
		deployment = self.deployment()

		invitation.invite(deployment, self.volunteer)
		second = invitation.invite(frappe.get_doc(deployment.doctype, deployment.name), self.volunteer)

		self.assertFalse(second["notified"])
		self.assertEqual(second["response"], invitation.INVITED)

	def test_a_roster_row_added_directly_is_not_an_invitation(self):
		"""Blank is not `invited`, which is the distinction the field exists for."""
		deployment = self.deployment(participants=[self.volunteer])

		row = next(row for row in deployment.participants if row.volunteer == self.volunteer)

		self.assertFalse(row.response)
		self.assertIsNone(row.invited_on)

	def test_inviting_somebody_already_on_the_roster_asks_them(self):
		deployment = self.deployment(participants=[self.volunteer])

		outcome = invitation.invite(deployment, self.volunteer)

		self.assertEqual(outcome["response"], invitation.INVITED)
		self.assertEqual(len(participation.participants_of(deployment.name)), 1)

	# --- answering --------------------------------------------------------

	def test_accepting_records_the_answer(self):
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)

		outcome = invitation.respond(deployment, self.volunteer, accepted=True)

		self.assertEqual(outcome["response"], invitation.ACCEPTED)
		self.assertIsNotNone(outcome["responded_on"])

	def test_declining_records_the_answer_and_the_reason(self):
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)

		invitation.respond(deployment, self.volunteer, accepted=False, note="Sitting exams.")

		row = next(row for row in deployment.participants if row.volunteer == self.volunteer)

		self.assertEqual(row.response, invitation.DECLINED)
		self.assertEqual(row.response_note, "Sitting exams.")

	def test_declining_leaves_them_on_the_roster(self):
		"""The claim the module docstring makes, asserted rather than described.

		A decline is a message to the coordinator, not a deletion. Taking
		somebody off is the coordinator's own act, so that a person who did in
		fact go can still have their time logged against the deployment.
		"""
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)
		invitation.respond(deployment, self.volunteer, accepted=False)

		self.assertTrue(participation.is_participant(deployment.name, self.volunteer))

	def test_answering_the_same_way_twice_is_a_no_op(self):
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)
		invitation.respond(deployment, self.volunteer, accepted=True)

		outcome = invitation.respond(deployment, self.volunteer, accepted=True)

		self.assertEqual(outcome["response"], invitation.ACCEPTED)

	def test_changing_an_answer_is_refused(self):
		"""Not overwritten silently: somebody has planned around the first answer."""
		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)
		invitation.respond(deployment, self.volunteer, accepted=True)

		with self.assertRaises(frappe.ValidationError):
			invitation.respond(deployment, self.volunteer, accepted=False)

	def test_answering_without_an_invitation_is_refused(self):
		deployment = self.deployment()

		with self.assertRaises(frappe.ValidationError):
			invitation.respond(deployment, self.volunteer, accepted=True)

	# --- through the volunteer's own door ---------------------------------

	def test_a_volunteer_can_answer_their_own_invitation(self):
		"""The case an ordinary `save()` gets wrong.

		A volunteer holds no Geo Assignment and no role on VMMS Deployment, so
		the permission layer refuses the only person entitled to answer. What
		admits them is the ownership check in `api/deployment.py`, and this is
		the test that fails if the elevated write in `respond()` is removed.
		"""
		user = fixtures.make_user("invited-volunteer")
		volunteer = fixtures.make_volunteer(
			fixtures.make_profile(email=user, user=user), self.branch
		).name

		deployment = self.deployment()
		invitation.invite(deployment, volunteer)

		with fixtures.acting_as(user):
			outcome = api.respond_to_invitation(deployment.name, accept=1)

		self.assertEqual(outcome["response"], invitation.ACCEPTED)

	def test_a_volunteer_cannot_answer_somebody_elses(self):
		user = fixtures.make_user("uninvited-volunteer")
		fixtures.make_volunteer(fixtures.make_profile(email=user, user=user), self.branch)

		deployment = self.deployment()
		invitation.invite(deployment, self.volunteer)

		with fixtures.acting_as(user), self.assertRaises(frappe.PermissionError):
			api.respond_to_invitation(deployment.name, accept=1)

	def test_decline_arrives_as_a_decline_over_http(self):
		"""`"false"` is a truthy string. Read naively, a volunteer declining
		would be recorded as accepting, which is the worst direction for this
		particular field to be wrong in."""
		user = fixtures.make_user("declining-volunteer")
		volunteer = fixtures.make_volunteer(
			fixtures.make_profile(email=user, user=user), self.branch
		).name

		deployment = self.deployment()
		invitation.invite(deployment, volunteer)

		with fixtures.acting_as(user):
			outcome = api.respond_to_invitation(deployment.name, accept="false")

		self.assertEqual(outcome["response"], invitation.DECLINED)

	# --- reading ----------------------------------------------------------

	def test_waiting_and_answered_are_separate_lists(self):
		waiting = self.deployment()
		answered = self.deployment()

		invitation.invite(waiting, self.volunteer)
		invitation.invite(answered, self.volunteer)
		invitation.respond(answered, self.volunteer, accepted=True)

		pending = [row["deployment"] for row in invitation.pending_for(self.volunteer)]
		settled = [row["deployment"] for row in invitation.answered_for(self.volunteer)]

		self.assertEqual(pending, [waiting.name])
		self.assertEqual(settled, [answered.name])

	def test_a_directly_added_participant_is_in_neither_list(self):
		"""Blank is not a response, so it appears in no invitation list at all."""
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
