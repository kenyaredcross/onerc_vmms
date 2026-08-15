# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Both membership paths, from a website account to a printed certificate.

MEM-02 says the type's `approval_mode` selects the path and nothing else does,
so the two journeys below are the same code reaching the same end by different
routes:

    auto_on_payment   the fee is confirmed through the real Manual driver, and
                      the membership activates with no approver anywhere
    routed            a resolved person approves it, and it activates with no
                      payment anywhere

Both end in the same place, which is the assertion that matters: an active
member, holding the society's member role, reading their own memberships and
printing their own certificate without any role that reads anybody else's.
"""

import frappe

from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestTheAutoOnPaymentJourney(RegistrationTestCase):
	def test_the_form_creates_a_membership_waiting_on_its_fee(self):
		_, membership = self.register_as_member("paying.applicant", fixtures.TYPE_AUTO)

		self.assertEqual(membership.membership_status, "Awaiting Payment")
		self.assertTrue(membership.payment_transaction)

	def test_the_member_satellite_is_created_and_linked_to_their_profile(self):
		user, membership = self.register_as_member("satellite.applicant", fixtures.TYPE_AUTO)

		self.assertTrue(membership.member)
		self.assertEqual(
			frappe.db.get_value(fixtures.MEMBER_DOCTYPE, membership.member, "red_profile"),
			self.profile_of(user),
		)

	def test_confirming_the_fee_activates_it(self):
		_, membership = self.register_as_member("confirmed.applicant", fixtures.TYPE_AUTO)

		fixtures.confirm_payment_through_manual_driver(membership)
		membership.reload()

		self.assertEqual(membership.membership_status, "Active")
		self.assertTrue(membership.valid_from)
		self.assertTrue(membership.valid_to)

	def test_nobody_approved_it(self):
		"""An auto-on-payment membership has no approval to be in."""
		_, membership = self.register_as_member("unapproved.applicant", fixtures.TYPE_AUTO)
		fixtures.confirm_payment_through_manual_driver(membership)
		membership.reload()

		self.assertEqual(membership.approval_state, "Draft")
		self.assertEqual(len(membership.approval_decisions), 0)

	def test_activation_grants_the_member_role(self):
		user, membership = self.register_as_member("promoted.applicant", fixtures.TYPE_AUTO)

		self.assertNotIn(fixtures.MEMBER_ROLE, self.roles_of(user))

		fixtures.confirm_payment_through_manual_driver(membership)

		self.assertIn(fixtures.MEMBER_ROLE, self.roles_of(user))


class TestTheRoutedJourney(RegistrationTestCase):
	def test_the_form_creates_a_membership_waiting_on_an_approver(self):
		_, membership = self.register_as_member("routed.applicant", fixtures.TYPE_ROUTED)

		self.assertEqual(membership.membership_status, "Awaiting Approval")
		self.assertEqual(membership.approval_state, "In Review")

	def test_it_routes_to_the_approver_above_the_branch(self):
		_, membership = self.register_as_member("queued.applicant", fixtures.TYPE_ROUTED)

		queued = frappe.get_all(
			"ToDo",
			filters={
				"reference_type": fixtures.MEMBERSHIP_DOCTYPE,
				"reference_name": membership.name,
				"status": ("in", ("Open", "Overdue")),
			},
			pluck="allocated_to",
		)

		self.assertEqual(queued, [self.approver])

	def test_approving_it_activates_it(self):
		_, membership = self.register_as_member("approved.applicant", fixtures.TYPE_ROUTED)

		self.approve(fixtures.MEMBERSHIP_DOCTYPE, membership.name)
		membership.reload()

		self.assertEqual(membership.membership_status, "Active")
		self.assertEqual(membership.approval_state, "Approved")

	def test_activation_grants_the_same_role_by_the_other_path(self):
		user, membership = self.register_as_member("routed.promoted", fixtures.TYPE_ROUTED)

		self.approve(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

		self.assertIn(fixtures.MEMBER_ROLE, self.roles_of(user))


class TestSelfAccess(RegistrationTestCase):
	def _active_member(self, handle: str):
		user, membership = self.register_as_member(handle, fixtures.TYPE_AUTO)
		fixtures.confirm_payment_through_manual_driver(membership)
		membership.reload()

		return user, membership

	def test_they_see_their_own_memberships(self):
		from vmmsx.api import member as member_api

		user, membership = self._active_member("reading.member")

		with fixtures.acting_as(user):
			rows = member_api.my_memberships()

		self.assertEqual([row["name"] for row in rows], [membership.name])
		self.assertEqual(rows[0]["membership_status"], "Active")

	def test_they_download_their_own_certificate_with_no_register_role(self):
		"""The gate that used to refuse them, and the reason it was wrong.

		This user holds the society's member role, which is not the membership
		scope role, so core's geo scoping denies them the register. Their own
		certificate is theirs all the same.
		"""
		from vmmsx.api import member as member_api

		user, membership = self._active_member("printing.member")

		with fixtures.acting_as(user):
			member_api.download_certificate(membership.name)
			content = frappe.local.response.filecontent
			filename = frappe.local.response.filename
			frappe.local.response = frappe._dict()

		self.assertTrue(content)
		self.assertEqual(filename, f"membership-certificate-{membership.name}.pdf")

	def test_the_possessive_download_needs_no_argument_at_all(self):
		"""What the workspace shortcut points at: a static URL cannot know a name."""
		from vmmsx.api import member as member_api

		user, membership = self._active_member("shortcut.member")

		with fixtures.acting_as(user):
			member_api.download_my_certificate()
			filename = frappe.local.response.filename
			frappe.local.response = frappe._dict()

		self.assertEqual(filename, f"membership-certificate-{membership.name}.pdf")

	def test_the_register_itself_is_still_closed_to_them(self):
		"""The bypass widens access to their own row, not to every membership.

		The refusal comes from Frappe before core's geo scoping is even
		consulted: this society granted the member role no permission on the
		membership register at all, and geo scoping would refuse them a second
		time if it did. Either refusal is the assertion; what must not happen is
		a list.
		"""
		user, _ = self._active_member("still.scoped.member")

		with fixtures.acting_as(user):
			try:
				visible = frappe.get_list(fixtures.MEMBERSHIP_DOCTYPE, pluck="name")
			except frappe.PermissionError:
				visible = []

		self.assertEqual(visible, [])

	def test_a_stranger_is_refused_somebody_elses_certificate(self):
		from vmmsx.api import member as member_api

		_, membership = self._active_member("private.member")
		stranger = fixtures.website_account("nosey.member")

		with fixtures.acting_as(stranger), self.assertRaises(frappe.PermissionError):
			member_api.download_certificate(membership.name)

	def test_a_stranger_is_refused_by_name_too(self):
		"""The possessive endpoint narrows; it never widens."""
		from vmmsx.api import member as member_api

		_, theirs = self._active_member("first.member")
		other_user, _ = self._active_member("second.member")

		with fixtures.acting_as(other_user), self.assertRaises(frappe.PermissionError):
			member_api.download_my_certificate(membership=theirs.name)

	def test_the_configured_print_role_may_still_print_somebody_elses(self):
		"""The admin path the bypass was added alongside, not instead of."""
		from vmmsx.api import member as member_api

		_, membership = self._active_member("officer.printed")

		with fixtures.acting_as(self.approver):
			member_api.download_certificate(membership.name)
			content = frappe.local.response.filecontent
			frappe.local.response = frappe._dict()

		self.assertTrue(content)

	def test_a_lapsed_membership_has_no_certificate_even_for_its_holder(self):
		"""A certificate is evidence of membership, and the gate is not the state."""
		from vmmsx.api import member as member_api
		from vmmsx.member.services import membership as membership_service

		user, membership = self._active_member("expired.member")
		membership_service.expire(membership)

		with fixtures.acting_as(user), self.assertRaises(frappe.ValidationError):
			member_api.download_certificate(membership.name)


class TestThePaperMember(RegistrationTestCase):
	def test_a_member_with_no_login_activates_and_is_granted_nothing(self):
		from vmmsx.member.services import member as member_service
		from vmmsx.member.services import membership as membership_service

		profile = fixtures.make_profile("Paper", "Member")
		member = member_service.ensure(profile)

		membership = frappe.get_doc(
			{
				"doctype": fixtures.MEMBERSHIP_DOCTYPE,
				"member": member.name,
				"membership_type": fixtures.TYPE_ROUTED,
				"geo_node": self.branch(),
			}
		).insert()

		membership_service.submit(membership)
		self.approve(fixtures.MEMBERSHIP_DOCTYPE, membership.name)
		membership.reload()

		self.assertEqual(membership.membership_status, "Active")
		self.assertFalse(frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "user"))
