# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The volunteer's door, and the fact that it opens for exactly one person.

`api/tasks.py` checks the coordinator's verbs with permissions, which brings
core's geo scoping with it, and the volunteer's verbs with ownership, which is a
different question. These tests are about the second: a volunteer holds no Geo
Assignment, so a permission check would refuse all of them, and what stands in
its place has to be *narrower* than a permission check rather than wider.

The other half is that `my_tasks` names nobody. There is no argument to get
wrong, which is the same shape as `my_memberships` and `my_volunteer`, so what
is asserted here is that the session is genuinely what selects the rows.
"""

import frappe

from vmmsx.api import tasks as api
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase
from vmmsx.task.services import states
from vmmsx.task.services import task as task_service


class TestTaskOwnership(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.branch = cls.society_a["branch"]

		# Two volunteers, each with a login, because the whole question here is
		# whether one can reach the other's work.
		cls.owner_user = fixtures.make_user("task-owner")
		cls.other_user = fixtures.make_user("task-other")

		cls.owner = cls.volunteer_for(cls.owner_user)
		cls.other = cls.volunteer_for(cls.other_user)

	@classmethod
	def volunteer_for(cls, user: str) -> str:
		"""A volunteer whose Red Profile carries this login.

		The two-hop walk the app itself uses: a task reaches a person through
		`VMMS Volunteer -> Red Profile -> user`, and there is no other way from
		one to the other in this app.
		"""
		profile = fixtures.make_profile(email=user, user=user)

		return fixtures.make_volunteer(profile, cls.branch).name

	def assign_to(self, volunteer: str):
		return task_service.assign(
			volunteer=volunteer,
			subject="Deliver the kits",
			description="Take the kits to the ward office.",
		)

	# --- reaching your own ------------------------------------------------

	def names(self, answer) -> list[str]:
		"""The docnames in a listing.

		Assertions in this suite ask about *membership* rather than about the
		whole list, because Frappe rolls the test transaction back once per
		class: a task another method created is still there when this one runs,
		and an exact-list assertion would be testing the execution order rather
		than the endpoint.
		"""
		return [row["name"] for row in answer["tasks"]]

	def test_my_tasks_returns_only_the_callers_own(self):
		mine = self.assign_to(self.owner)
		theirs = self.assign_to(self.other)

		with fixtures.acting_as(self.owner_user):
			answer = api.my_tasks()

		self.assertIn(mine.name, self.names(answer))
		self.assertNotIn(theirs.name, self.names(answer))
		# The property in full: not one row in the answer belongs to anybody
		# else, however many rows earlier methods left behind.
		self.assertTrue(all(row["volunteer"] == self.owner for row in answer["tasks"]))

	def test_my_tasks_hides_finished_work_by_default(self):
		task = self.assign_to(self.owner)
		task_service.accept(task)
		task_service.submit(task)
		task_service.sign_off(task)

		with fixtures.acting_as(self.owner_user):
			open_only = api.my_tasks()
			everything = api.my_tasks(include_closed=1)

		self.assertNotIn(task.name, self.names(open_only))
		self.assertIn(task.name, self.names(everything))

	def test_include_closed_is_read_as_a_flag_not_as_a_truthy_string(self):
		"""`"false"` arrives from HTTP as a non-empty string. Read naively it is
		true, and the screen would silently show finished work."""
		task = self.assign_to(self.owner)
		task_service.accept(task)
		task_service.submit(task)
		task_service.sign_off(task)

		with fixtures.acting_as(self.owner_user):
			answer = api.my_tasks(include_closed="false")

		self.assertNotIn(task.name, self.names(answer))

	def test_somebody_with_no_volunteer_record_gets_none(self):
		stranger = fixtures.make_user("task-stranger")

		with fixtures.acting_as(stranger):
			self.assertIsNone(api.my_tasks())

	# --- not reaching anybody else's -------------------------------------

	def test_another_volunteer_cannot_accept_your_task(self):
		task = self.assign_to(self.owner)

		with fixtures.acting_as(self.other_user), self.assertRaises(frappe.PermissionError):
			api.accept_task(task.name)

	def test_another_volunteer_cannot_submit_your_task(self):
		task = self.assign_to(self.owner)

		with fixtures.acting_as(self.other_user), self.assertRaises(frappe.PermissionError):
			api.submit_task(task.name)

	def test_the_holder_can_accept_their_own(self):
		task = self.assign_to(self.owner)

		with fixtures.acting_as(self.owner_user):
			outcome = api.accept_task(task.name)

		self.assertTrue(outcome["moved"])
		self.assertEqual(outcome["status"], states.ACCEPTED)

	def test_the_holder_can_read_their_own_without_any_scope(self):
		"""The case a permission check would get wrong. A volunteer holds no Geo
		Assignment, so geo scoping refuses them, and ownership is what admits
		them to the one task that is theirs."""
		task = self.assign_to(self.owner)

		with fixtures.acting_as(self.owner_user):
			answer = api.get_task(task.name)

		self.assertEqual(answer["name"], task.name)

	def test_a_stranger_cannot_read_a_task_at_all(self):
		task = self.assign_to(self.owner)
		stranger = fixtures.make_user("task-outsider")

		with fixtures.acting_as(stranger), self.assertRaises(frappe.PermissionError):
			api.get_task(task.name)
