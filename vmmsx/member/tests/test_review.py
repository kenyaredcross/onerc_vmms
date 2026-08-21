# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What an approver reads before deciding a membership — and that it names them.

**The bug this suite exists to hold shut.** The review queue is one screen over
`approvals.my_queue`, and it drew a docname, a stage label and two buttons. For
a volunteer application that was survivable — `api/volunteer.py::get_decision`
filled the panel beside it — and for a membership it was not: an approver was
being asked to approve `MSHIP-00042` with no name anywhere on the screen. Two
things fix it and both are tested here:

1. `approvals/services/applicant.py` puts the person on **every** approval
   status, resolved from the workflow's own `applicant_field`, so the *queue*
   lists people rather than docnames — for any governed doctype, including ones
   with no decision view of their own.
2. `member/services/review.py` is the membership's decision view, so the
   *record* can be read once it is opened.

Nothing here is mocked. The workflow is real, the approval is real, and the
identity is core's Red Profile read live.
"""

import frappe

from vmmsx.api import approvals as approvals_api
from vmmsx.api import member as member_api
from vmmsx.approvals.services import config, engine
from vmmsx.member.services import approval
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


def _member_for(profile: str) -> str:
	"""The member satellite for a profile, made if it does not exist yet."""
	from vmmsx.member.services import member as member_service

	return member_service.ensure(profile).name


class TestTheApplicantIsNamed(MemberTestCase):
	"""The person, on the approval status, for a doctype two links away.

	`VMMS Membership.member` points at `VMMS Member`, which points at Red
	Profile — two hops, where a volunteer application's `red_profile` is one.
	The resolver follows the schema rather than knowing either shape, and this
	is the harder of the two, so it is the one worth testing end to end.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# The user first: `make_user` is what creates the society's role, and
		# `make_workflow` names it on a stage — a workflow built before the role
		# exists fails its own Link validation.
		cls.approver = cls.scoped_user("review.approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])
		fixtures.make_type(fixtures.TYPE_ROUTED, approval.MODE_ROUTED, fee=0)
		# `applicant_field` named the way the shipped seeds name it. The module
		# fixture leaves it empty, which is a real configuration and has its own
		# test below — it is not the one a society actually runs.
		fixtures.make_workflow(applicant_field="member")
		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)
		fixtures.grant_member_access(fixtures.APPROVER_ROLE)

	def test_the_status_carries_the_person_behind_the_membership(self):
		profile = fixtures.make_profile(first_name="Grace", last_name="Mushi")
		membership = fixtures.make_membership(profile, fixtures.TYPE_ROUTED, self.society_a["ward"])
		membership_service.submit(membership)

		status = engine.status(frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name))

		self.assertIsNotNone(status["applicant"], "a membership reached the queue with no person")
		self.assertEqual(status["applicant"]["full_name"], "Grace Mushi")
		# Two hops, and the far end is named: the member is what the workflow
		# points at, the Red Profile is where the name lives.
		self.assertEqual(status["applicant"]["doctype"], fixtures.MEMBER_DOCTYPE)
		self.assertEqual(status["applicant"]["red_profile"], profile)

	def test_the_name_is_read_live_and_never_copied(self):
		"""Correcting the Red Profile corrects the queue, with no second write.

		The property the whole identity model rests on. If this ever fails it
		means a name has been copied onto the membership or onto the DTO's
		source, and the two will disagree the first time somebody is married,
		corrected or transliterated differently.
		"""
		profile = fixtures.make_profile(first_name="Amina", last_name="Otieno")
		membership = fixtures.make_membership(profile, fixtures.TYPE_ROUTED, self.society_a["ward"])
		membership_service.submit(membership)

		frappe.db.set_value("Red Profile", profile, "full_name", "Amina Otieno-Wekesa")

		status = engine.status(frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name))

		self.assertEqual(status["applicant"]["full_name"], "Amina Otieno-Wekesa")

	def test_the_queue_lists_people(self):
		"""The whole point, asked of the endpoint the screen actually calls."""
		profile = fixtures.make_profile(first_name="Neema", last_name="Kileo")
		membership = fixtures.make_membership(profile, fixtures.TYPE_ROUTED, self.society_a["ward"])
		membership_service.submit(membership)

		with fixtures.acting_as(self.approver):
			queue = approvals_api.my_queue(doctype=fixtures.MEMBERSHIP_DOCTYPE)

		names = {row["name"]: row["applicant"] for row in queue}

		self.assertIn(membership.name, names)
		self.assertEqual(names[membership.name]["full_name"], "Neema Kileo")

	def test_the_queue_can_be_asked_for_one_registration_at_a_time(self):
		"""What splitting the screen into two lists rests on.

		`my_queue` has always taken a `doctype`; the console never passed one.
		Asserted here because the two lists are now two calls, and a filter that
		silently ignored its argument would put memberships in the volunteer
		queue.
		"""
		profile = fixtures.make_profile(first_name="Hassan", last_name="Juma")
		membership = fixtures.make_membership(profile, fixtures.TYPE_ROUTED, self.society_a["ward"])
		membership_service.submit(membership)

		with fixtures.acting_as(self.approver):
			mine = approvals_api.my_queue(doctype=fixtures.MEMBERSHIP_DOCTYPE)

		self.assertTrue(mine, "the membership queue came back empty")
		self.assertEqual({row["doctype"] for row in mine}, {fixtures.MEMBERSHIP_DOCTYPE})

	def test_an_unset_applicant_field_falls_back_to_the_owner(self):
		"""What a society that configured no applicant field gets.

		`config.applicant_of()` has always read `applicant_field or "owner"` for
		the re-application cooldown, and the doctype's own field description says
		so. The queue follows the same rule rather than showing nothing: a
		workflow somebody set up in a hurry must not put an approver back in
		front of a docname, which is the state this whole change exists to end.
		"""
		clerk = fixtures.make_user("review.clerk")
		profile = fixtures.make_profile(first_name="Furaha", last_name="Magesa", user=clerk)
		# The member satellite is made as Administrator; only the *membership*
		# needs to be owned by the person, because `owner` is what the fallback
		# reads.
		member = _member_for(profile)

		with fixtures.acting_as(clerk):
			owned = frappe.get_doc(
				{
					"doctype": fixtures.MEMBERSHIP_DOCTYPE,
					"member": member,
					"membership_type": fixtures.TYPE_ROUTED,
					"geo_node": self.society_a["ward"],
				}
			).insert(ignore_permissions=True)

		workflow = config.for_doctype(fixtures.MEMBERSHIP_DOCTYPE)
		workflow.applicant_field = ""

		status = engine.status(
			frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, owned.name), workflow=workflow
		)

		self.assertEqual(status["applicant"]["red_profile"], profile)
		self.assertEqual(status["applicant"]["full_name"], "Furaha Magesa")

	def test_an_applicant_field_that_is_not_a_link_falls_back_to_the_docname(self):
		"""A governed doctype whose subject is not a person still renders.

		The graceful-absence case, and it has to be graceful rather than empty:
		an approver looking at a queue needs something to tell two rows apart,
		and a blank cell is not it.
		"""
		profile = fixtures.make_profile(first_name="Rehema", last_name="Shija")
		membership = fixtures.make_membership(profile, fixtures.TYPE_ROUTED, self.society_a["ward"])
		membership_service.submit(membership)

		workflow = config.for_doctype(fixtures.MEMBERSHIP_DOCTYPE)
		# Not saved: the workflow document is the caller's, and `status()` takes
		# it as an argument precisely so a caller can hold one.
		workflow.applicant_field = "membership_status"

		status = engine.status(
			frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name), workflow=workflow
		)

		self.assertIsNotNone(status["applicant"])
		self.assertIsNone(status["applicant"]["red_profile"])
		self.assertEqual(status["applicant"]["full_name"], membership.membership_status)


class TestTheMembershipCanBeRead(MemberTestCase):
	"""The decision view itself: composed from the services that own each half."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.approver = cls.scoped_user("review.reader", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])
		fixtures.make_type(fixtures.TYPE_ROUTED, approval.MODE_ROUTED, fee=0)
		# `applicant_field` named the way the shipped seeds name it. The module
		# fixture leaves it empty, which is a real configuration and has its own
		# test below — it is not the one a society actually runs.
		fixtures.make_workflow(applicant_field="member")
		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)
		fixtures.grant_member_access(fixtures.APPROVER_ROLE)

	def test_it_names_the_applicant_and_what_they_applied_for(self):
		profile = fixtures.make_profile(first_name="Zainab", last_name="Omary")
		membership = fixtures.make_membership(profile, fixtures.TYPE_ROUTED, self.society_a["ward"])
		membership_service.submit(membership)

		with fixtures.acting_as(self.approver):
			review = member_api.get_review(membership.name)

		self.assertEqual(review["applicant"]["full_name"], "Zainab Omary")
		self.assertEqual(review["membership"]["membership_type"], fixtures.TYPE_ROUTED)
		self.assertEqual(review["membership"]["membership_geo_node"], self.society_a["ward"])

	def test_the_intake_fields_are_never_a_second_answer_to_who_somebody_is(self):
		"""The comparison an approver would like to make, and cannot.

		`intake.clear_intake` blanks `applicant_first_name` and its neighbours on
		every save, having absorbed them into the Red Profile — they are a
		transport into identity, not a record. So there is one name on this
		screen and it is core's. Asserted here rather than left implicit, because
		"show what the clerk typed beside what we hold" is a reasonable-sounding
		feature request that this model has already answered.
		"""
		profile = fixtures.make_profile(first_name="Salma", last_name="Rashid")
		membership = fixtures.make_membership(
			profile,
			fixtures.TYPE_ROUTED,
			self.society_a["ward"],
			applicant_first_name="Selma",
			applicant_last_name="Rashidi",
		)
		membership_service.submit(membership)

		with fixtures.acting_as(self.approver):
			review = member_api.get_review(membership.name)

		self.assertEqual(review["applicant"]["full_name"], "Salma Rashid")
		self.assertNotIn("intake", review)
		self.assertIsNone(
			frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, membership.name, "applicant_first_name")
		)

	def test_reading_it_needs_permission_on_the_membership(self):
		"""No second door. The gate is the record's own read check."""
		profile = fixtures.make_profile(first_name="Elia", last_name="Chusi")
		membership = fixtures.make_membership(profile, fixtures.TYPE_ROUTED, self.society_a["ward"])
		membership_service.submit(membership)

		stranger = fixtures.make_user("review.stranger")

		with fixtures.acting_as(stranger):
			with self.assertRaises(frappe.PermissionError):
				member_api.get_review(membership.name)
