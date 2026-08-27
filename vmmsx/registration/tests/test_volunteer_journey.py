# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The whole volunteer journey, from a website account to a volunteer.

Nothing is stubbed anywhere along it: the registration goes through Frappe's own
web form endpoint, the routing through core's `resolve_approvers`, the decision
through this app's API gate as the person the document actually routed to, and
the acceptance through the ordinary `on_update` predicate.

The last two tests are the ones that matter most, because they are about a
person who holds nothing: an approved volunteer can read their own record
without a role that reads the register, and somebody else cannot read it at all.
"""

import frappe

from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestTheVolunteerJourney(RegistrationTestCase):
	def test_a_website_account_can_reach_the_desk_at_all(self):
		"""A Workspace is a desk surface, and a Website User cannot open one.

		Frappe derives `user_type` from whether any held role has desk access, so
		the society's self-registration role having it is what makes the landing
		workspace reachable. If this ever stops holding, every workspace in the
		journey becomes unreachable and nothing else in this suite would notice.
		"""
		user = fixtures.website_account("desk.reacher")

		self.assertEqual(frappe.db.get_value("User", user, "user_type"), "System User")

	def test_the_form_creates_an_application_that_is_under_review(self):
		_, application = self.register_as_volunteer("journey.applicant")

		self.assertEqual(application.approval_state, "In Review")
		self.assertEqual(application.geo_node, self.branch())

	def test_it_routes_to_the_approver_holding_the_role_above_the_branch(self):
		"""Nearest ancestor: the applicant is at a branch, the approver a level up."""
		_, application = self.register_as_volunteer("routed.applicant")

		queued = frappe.get_all(
			"ToDo",
			filters={
				"reference_type": fixtures.APPLICATION_DOCTYPE,
				"reference_name": application.name,
				"status": ("in", ("Open", "Overdue")),
			},
			pluck="allocated_to",
		)

		self.assertEqual(queued, [self.approver])

	def test_approving_it_makes_them_an_active_volunteer(self):
		_, application = self.register_as_volunteer("accepted.applicant")

		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		application.reload()

		self.assertEqual(application.approval_state, "Approved")
		self.assertTrue(application.volunteer)
		self.assertEqual(
			frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, application.volunteer, "status"), "Active"
		)

	def test_the_volunteer_is_placed_where_they_applied(self):
		_, application = self.register_as_volunteer("placed.volunteer")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()

		self.assertEqual(
			frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, application.volunteer, "home_geo_node"),
			self.branch(),
		)

	def test_the_volunteer_record_holds_no_identity_of_its_own(self):
		"""The satellite rule, asserted at the end of the journey that creates one."""
		_, application = self.register_as_volunteer("thin.volunteer")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()

		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, application.volunteer)
		fieldnames = {field.fieldname for field in volunteer.meta.fields}

		self.assertEqual(fieldnames & {"first_name", "last_name", "email", "phone"}, set())


class TestTheRoleGrant(RegistrationTestCase):
	def test_acceptance_grants_the_role_the_society_configured(self):
		user, application = self.register_as_volunteer("granted.applicant")

		self.assertNotIn(fixtures.VOLUNTEER_ROLE, self.roles_of(user))

		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		self.assertIn(fixtures.VOLUNTEER_ROLE, self.roles_of(user))

	def test_no_role_is_granted_while_the_application_is_still_open(self):
		user, _ = self.register_as_volunteer("waiting.applicant")

		self.assertNotIn(fixtures.VOLUNTEER_ROLE, self.roles_of(user))

	def test_an_unconfigured_role_grants_nothing_and_does_not_break_acceptance(self):
		"""Fail-closed. Empty configuration means nothing is granted, never everything."""
		from vmmsx.volunteer.services.society import MEMBER_ROLE_FIELD

		user, application = self.register_as_volunteer("unconfigured.applicant")
		fixtures.set_settings(**{MEMBER_ROLE_FIELD: None})

		try:
			self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
			application.reload()

			self.assertEqual(application.approval_state, "Approved")
			self.assertTrue(application.volunteer)
			self.assertNotIn(fixtures.VOLUNTEER_ROLE, self.roles_of(user))
		finally:
			fixtures.set_settings(**{MEMBER_ROLE_FIELD: fixtures.VOLUNTEER_ROLE})

	def test_the_grant_narrows_the_lists_its_workspace_shows(self):
		"""A User Permission, which is Frappe's own answer to "only mine"."""
		from vmmsx.registration.services import permissions

		user, application = self.register_as_volunteer("narrowed.applicant")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()

		rows = frappe.get_all(
			"User Permission",
			filters={"user": user, "allow": fixtures.VOLUNTEER_DOCTYPE},
			fields=["for_value", "applicable_for"],
		)

		self.assertEqual({row["applicable_for"] for row in rows}, set(permissions.SELF_SERVICE_READABLE))

		for row in rows:
			self.assertEqual(row["for_value"], application.volunteer)

	def test_it_narrows_nothing_the_workspace_does_not_show(self):
		"""The failure this shape exists to prevent, stated as a test.

		A User Permission with apply_to_all_doctypes narrows every doctype that
		links to the allowed record, for that user, everywhere and forever. It
		follows a person into whatever else they do for the society: a
		coordinator who also volunteers would quietly stop seeing anybody else's
		records, and nothing would say why. So every row this grant writes names
		exactly one doctype, and it is one the self-service workspace lists.
		"""
		from vmmsx.registration.services import permissions

		user, application = self.register_as_volunteer("bounded.applicant")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		rows = frappe.get_all(
			"User Permission",
			filters={"user": user},
			fields=["applicable_for", "apply_to_all_doctypes"],
		)

		self.assertTrue(rows)

		for row in rows:
			self.assertEqual(row["apply_to_all_doctypes"], 0)
			self.assertIn(row["applicable_for"], permissions.SELF_SERVICE_READABLE)

	def test_becoming_a_member_narrows_nothing_at_all(self):
		"""The member surface points at no doctype, so there is nothing to narrow.

		A clerk who is also a member must keep seeing every membership their job
		requires, and a User Permission written here would take that away.
		"""
		user, membership = self.register_as_member("unnarrowed.member", fixtures.TYPE_ROUTED)
		self.approve(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

		self.assertIn(fixtures.MEMBER_ROLE, self.roles_of(user))
		self.assertEqual(frappe.get_all("User Permission", filters={"user": user}, pluck="name"), [])


class TestThePaperRegistration(RegistrationTestCase):
	def test_a_volunteer_with_no_login_is_accepted_and_granted_nothing(self):
		"""`Red Profile.user` is nullable by core's design, and this is why.

		Somebody the branch registered from a paper form has no account. The
		approval has to work anyway, and the grant has to do nothing rather than
		raise.
		"""
		profile = fixtures.make_profile("Paper", "Volunteer")
		person = frappe.get_doc(fixtures.PROFILE_DOCTYPE, profile)
		person.country_of_citizenship = fixtures.test_country()
		person.residency_type = "Local"
		person.home_geo_node = self.branch()
		person.append(
			"identifications",
			{
				"id_type": fixtures.make_identification_type(),
				"id_number": f"{fixtures.TEST_PREFIX}-paper-0001",
				"is_primary": 1,
			},
		)
		person.save()

		application = frappe.get_doc(
			{
				"doctype": fixtures.APPLICATION_DOCTYPE,
				"red_profile": profile,
				"geo_node": self.branch(),
			}
		).insert()

		from vmmsx.volunteer.services import application as application_service

		application_service.submit(application)
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		application.reload()

		self.assertEqual(application.approval_state, "Approved")
		self.assertEqual(
			frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, application.volunteer, "status"), "Active"
		)
		self.assertFalse(frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "user"))


class TestSelfAccess(RegistrationTestCase):
	def test_the_volunteer_reads_their_own_record_holding_no_register_role(self):
		"""Owner bypass, and the whole point of it.

		This user holds the self-service role and the society's volunteer role,
		neither of which is the scope role, so core's geo scoping denies them the
		register. Their own record is theirs all the same.
		"""
		from vmmsx.api import volunteer as volunteer_api

		user, application = self.register_as_volunteer("self.reader")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()

		with fixtures.acting_as(user):
			mine = volunteer_api.my_volunteer()

			self.assertEqual(mine["volunteer"], application.volunteer)
			self.assertEqual(mine["status"], "Active")
			self.assertEqual(
				volunteer_api.get_volunteer(application.volunteer)["volunteer"], application.volunteer
			)

	def test_the_register_itself_is_still_closed_to_them(self):
		"""The bypass widens access to one person's own row, not to the register.

		Without this, a bypass that accidentally granted a scope would look
		identical to a working one in every other test here.

		The refusal comes from Frappe before core's geo scoping is even
		consulted: this society granted the self-service role no permission on
		the register at all, and geo scoping would refuse them a second time if
		it did. Either refusal is the assertion; what must not happen is a list.
		"""
		user, application = self.register_as_volunteer("still.scoped")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		with fixtures.acting_as(user):
			try:
				visible = frappe.get_list(fixtures.VOLUNTEER_DOCTYPE, pluck="name")
			except frappe.PermissionError:
				visible = []

		self.assertEqual(visible, [])

	def test_somebody_else_cannot_read_it(self):
		from vmmsx.api import volunteer as volunteer_api

		_, application = self.register_as_volunteer("private.volunteer")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()

		stranger = fixtures.website_account("nosey.stranger")

		with fixtures.acting_as(stranger), self.assertRaises(frappe.PermissionError):
			volunteer_api.get_volunteer(application.volunteer)

	def test_a_stranger_asking_for_their_own_gets_nothing_rather_than_an_error(self):
		"""Somebody logged in who is not a volunteer is a visitor, not a failure."""
		from vmmsx.api import volunteer as volunteer_api

		stranger = fixtures.website_account("not.a.volunteer")

		with fixtures.acting_as(stranger):
			self.assertIsNone(volunteer_api.my_volunteer())


class TestFormOrderingAndPrefill(RegistrationTestCase):
	"""The onboarding-funnel ordering, and not re-asking somebody who they are."""

	def test_the_legacy_native_form_is_not_a_second_registration_door(self):
		"""The React portal owns the two-record registration transaction."""
		web_form = frappe.get_doc("Web Form", "register-as-a-volunteer")
		application_meta = frappe.get_meta(fixtures.APPLICATION_DOCTYPE)

		self.assertFalse(web_form.published)
		for fieldname in (
			"country_of_citizenship",
			"residency_type",
			"home_geo_node",
			"country_of_residence",
			"residence_address",
			"id_type",
			"id_number",
		):
			self.assertIsNone(application_meta.get_field(fieldname))

	def test_a_first_time_registrant_has_nothing_to_prefill(self):
		from vmmsx.api import volunteer as volunteer_api

		user = fixtures.website_account("nothing.to.prefill")

		with fixtures.acting_as(user):
			self.assertIsNone(volunteer_api.my_registration_prefill())

	def test_cross_registration_prefills_from_the_profile_already_on_file(self):
		"""Somebody who registered once is not asked who they are a second time.

		Registering as a volunteer creates the Red Profile; a second look — the
		member web form, or this endpoint standing in for it — reads the same
		identity back rather than presenting blank fields.
		"""
		from vmmsx.api import volunteer as volunteer_api

		user, application = self.register_as_volunteer(
			"already.known.applicant", applicant_phone="+254700111222"
		)

		with fixtures.acting_as(user):
			prefill = volunteer_api.my_registration_prefill()

		self.assertIsNotNone(prefill)
		self.assertEqual(prefill["applicant_first_name"], "Amina")
		self.assertEqual(prefill["applicant_last_name"], "Otieno")
		self.assertEqual(prefill["applicant_phone"], "+254700111222")

		# And it is the identity path, not a second copy: the same Red Profile
		# the application itself resolved to.
		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, {"user": user}, "name"), application.red_profile
		)
