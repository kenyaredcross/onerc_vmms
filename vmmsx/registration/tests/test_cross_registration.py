# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One person, two affiliations, one profile.

Somebody who volunteers in March and joins as a member in August is one person,
and core's Design 2 is built on that being true: the Red Profile is the spine,
the two satellites hang off it, and each writes its own summary row on the
affiliation index without disturbing the other's.

This suite drives that through the two public registration forms rather than
through the services, because the forms are where a second profile would be
created if anything about the resolution were wrong, and because a person who
holds nothing is the one this has to work for.
"""

import frappe

from vmmsx.api import registration as registration_api
from vmmsx.registration.services import workspaces
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestOnePersonTwoAffiliations(RegistrationTestCase):
	def _both(self, handle: str):
		"""Register as a volunteer, be accepted, then register as a member."""
		user, application = self.register_as_volunteer(handle)
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()

		with fixtures.acting_as(user):
			membership = fixtures.submit_membership_form(self.branch(), fixtures.TYPE_AUTO)

		membership = frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)
		fixtures.confirm_payment_through_manual_driver(membership)
		membership.reload()

		return user, application, membership

	def test_the_second_registration_reuses_the_first_profile(self):
		user, application, membership = self._both("both.affiliations")

		self.assertEqual(self.profile_count(user), 1)
		self.assertEqual(
			frappe.db.get_value(fixtures.MEMBER_DOCTYPE, membership.member, "red_profile"),
			application.red_profile,
		)

	def test_they_end_up_holding_both_roles(self):
		user, _, _ = self._both("both.roles")
		roles = self.roles_of(user)

		self.assertIn(fixtures.VOLUNTEER_ROLE, roles)
		self.assertIn(fixtures.MEMBER_ROLE, roles)

	def test_they_are_shown_both_workspaces(self):
		user, _, _ = self._both("both.workspaces")
		visible = self.workspaces_of(user)

		self.assertIn(workspaces.VOLUNTEER, visible)
		self.assertIn(workspaces.MEMBERSHIP, visible)

	def test_core_carries_both_affiliations_on_the_one_profile(self):
		"""Read only to assert that both were written.

		No production code in vmmsx reads this table to decide anything, and a
		test that used it to determine whether somebody volunteers would be
		testing the wrong thing. What it proves here is that two satellites
		reported to one spine without either overwriting the other.
		"""
		user, _, _ = self._both("both.indexed")
		profile = self.profile_of(user)
		frappe.clear_document_cache(fixtures.PROFILE_DOCTYPE, profile)

		rows = frappe.get_all(
			"Red Profile Affiliation",
			filters={"parent": profile, "parenttype": fixtures.PROFILE_DOCTYPE},
			fields=["affiliation_type", "status"],
		)

		self.assertEqual({row["affiliation_type"] for row in rows}, {"volunteer", "member"})
		self.assertEqual({row["status"] for row in rows}, {"Active"})

	def test_the_order_does_not_matter(self):
		"""Member first, volunteer second, and the same single profile."""
		user, membership = self.register_as_member("member.first", fixtures.TYPE_AUTO)
		fixtures.confirm_payment_through_manual_driver(membership)

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(self.branch())

		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		self.assertEqual(self.profile_count(user), 1)
		self.assertEqual(
			frappe.db.get_value(fixtures.APPLICATION_DOCTYPE, application.name, "red_profile"),
			self.profile_of(user),
		)
		self.assertEqual(
			self.roles_of(user) & {fixtures.VOLUNTEER_ROLE, fixtures.MEMBER_ROLE},
			{fixtures.VOLUNTEER_ROLE, fixtures.MEMBER_ROLE},
		)

	def test_each_side_still_sees_only_its_own(self):
		"""Being both does not merge the two: the records stay separate."""
		from vmmsx.api import member as member_api
		from vmmsx.api import volunteer as volunteer_api

		user, application, membership = self._both("both.separate")

		with fixtures.acting_as(user):
			mine = volunteer_api.my_volunteer()
			memberships = member_api.my_memberships()

		self.assertEqual(mine["volunteer"], application.volunteer)
		self.assertEqual([row["name"] for row in memberships], [membership.name])


class TestAnOpenApplicationOnlyBlocksItsOwnKind(RegistrationTestCase):
	"""Registering as a member while the volunteer application is still undecided.

	Every test above waits for an approval before registering the second time,
	which is the case that always worked. This is the one that did not: the two
	rules that refuse a second registration each ask about a single doctype —
	`registration._assert_nothing_open(doctype)` and `engine.assert_single_open`,
	which filters on `doc.doctype` — so an application nobody has answered yet
	has never had anything to say about a membership. The portal asked a
	narrower question than it needed ("is *anything* of yours open") and turned
	people away from a registration the server would have taken.

	These drive the SPA endpoints rather than the Web Forms, because that is
	where the pre-insert refusal lives and where the wizard's answer comes from.
	"""

	def _waiting_volunteer(self, handle: str):
		"""Register as a volunteer and leave the application undecided."""
		user, application = self.register_as_volunteer(handle)

		from vmmsx.approvals import states

		self.assertFalse(states.is_terminal(application.approval_state))

		return user, application

	def test_the_open_answer_is_given_per_kind(self):
		user, application = self._waiting_volunteer("open.per.kind")

		with fixtures.acting_as(user):
			answer = registration_api.my_open_registrations()

		self.assertEqual(answer["volunteer"]["name"], application.name)
		self.assertEqual(answer["volunteer"]["doctype"], fixtures.APPLICATION_DOCTYPE)
		self.assertIsNone(answer["member"])

	def test_they_may_register_as_a_member_while_it_waits(self):
		"""The regression. Nothing about the application blocks the membership."""
		user, application = self._waiting_volunteer("open.then.member")

		with fixtures.acting_as(user):
			membership = registration_api.register_as_member(
				membership_type=fixtures.TYPE_ROUTED, geo_node=self.branch()
			)

		self.assertTrue(frappe.db.exists(fixtures.MEMBERSHIP_DOCTYPE, membership["name"]))

		# One person, still one profile — the membership resolved back to the
		# same spine the application is hanging off, without either being decided.
		application.reload()
		self.assertEqual(
			frappe.db.get_value(fixtures.MEMBER_DOCTYPE, membership["member"], "red_profile"),
			application.red_profile,
		)

	def test_both_open_is_reported_as_both(self):
		user, application = self._waiting_volunteer("open.both")

		with fixtures.acting_as(user):
			registration_api.register_as_member(membership_type=fixtures.TYPE_ROUTED, geo_node=self.branch())
			answer = registration_api.my_open_registrations()

		self.assertEqual(answer["volunteer"]["name"], application.name)
		self.assertIsNotNone(answer["member"])

	def test_a_second_of_the_same_kind_is_still_refused(self):
		"""The rule this narrows, and it is untouched: one *volunteer* application."""
		user, _ = self._waiting_volunteer("open.same.kind")

		with fixtures.acting_as(user), self.assertRaises(frappe.ValidationError):
			registration_api.register_as_volunteer(geo_node=self.branch())

	def test_a_second_membership_is_refused_the_same_way(self):
		user = fixtures.website_account("open.same.membership")

		with fixtures.acting_as(user):
			registration_api.register_as_member(membership_type=fixtures.TYPE_ROUTED, geo_node=self.branch())

			with self.assertRaises(frappe.ValidationError):
				registration_api.register_as_member(
					membership_type=fixtures.TYPE_ROUTED, geo_node=self.branch()
				)
