# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The fan-out: who hears an announcement, once, and what stops it going twice.

The properties worth testing here are the ones that are expensive to get wrong
in production and cheap to get wrong in code:

- **idempotence**, because the realistic ways `publish()` gets called twice are
  a retried job and somebody pressing a button again, and the visible failure is
  fifty thousand people receiving an urgent advisory twice;
- **the geo boundary**, because an announcement leaking upward is a branch
  addressing the whole country;
- **one copy per person**, because somebody who is both a volunteer and a member
  is exactly the person most involved in the society and the one who would
  notice;
- **audience dispatch**, because those are the queries the closed Select
  promises the server knows how to run.

Real geo levels and nodes through core's fixtures, real volunteers and real
memberships. Nothing about the resolution or the delivery is mocked.

**Each test gets its own subtree.** Frappe rolls the test transaction back once
per class rather than once per method, so a volunteer made in one method is
still there in the next — and every count in this file is a count of who heard
something. Rather than trying to clean up between methods, `setUp` builds a
fresh region and two branches per test, and every assertion is scoped to nodes
only that test knows about. That is the same reasoning `volunteer/tests/base.py`
records for arranging authority in `setUpClass`, applied to the other direction:
what must not leak here is data, not roles.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.notifications.services import announce, audience, delivery

EXTRA_TEST_RECORD_DEPENDENCIES = []

PREFIX = "ANNTEST"


class AnnouncementFixture(IntegrationTestCase):
	"""Arrangement only. Carries no test methods, deliberately.

	A test class that inherited from one holding tests would re-run every one of
	them under a second name, which reads as twice the coverage and is none.
	"""

	# Distinguishes one test's subtree from the next within a class, since the
	# rollback that would have separated them happens only at the end.
	counter = 0

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		from onerc_core.geo.tests import fixtures as geo_fixtures

		# The ladder is shared: a level carries no records and two tests using
		# the same rung cannot see each other through it.
		cls.region_level = geo_fixtures.make_level(f"{PREFIX}-1", "Region", 1)
		cls.branch_level = geo_fixtures.make_level(f"{PREFIX}-2", "Branch", 2, is_lowest=True)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")

		from onerc_core.geo.tests import fixtures as geo_fixtures

		AnnouncementFixture.counter += 1
		self.tag = f"{PREFIX}{AnnouncementFixture.counter}"

		# Two rungs and a sibling, so "at or beneath" is a real question rather
		# than one node answering itself, and so the boundary has something to
		# hold against.
		self.region = geo_fixtures.make_node(f"{self.tag} Region", self.region_level, None)
		self.branch = geo_fixtures.make_node(f"{self.tag} Branch", self.branch_level, self.region)
		self.other = geo_fixtures.make_node(f"{self.tag} Other", self.branch_level, self.region)

	# ------------------------------------------------------------- fixtures

	def make_person(self, handle: str) -> tuple[str, str]:
		"""A login and a Red Profile bound to it. Returns (user, profile).

		The email carries the per-test tag because core makes `Red Profile.user`
		unique: two tests reusing one login would be two profiles fighting over
		the same row rather than two independent people.
		"""
		email = f"{self.tag}-{handle}@example.invalid".lower()

		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": handle,
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		profile = frappe.get_doc(
			{
				"doctype": "Red Profile",
				"first_name": handle,
				"last_name": "Tester",
				"email": email,
				"user": email,
			}
		).insert(ignore_permissions=True)

		return email, profile.name

	def make_volunteer(self, handle: str, node: str) -> tuple[str, str]:
		user, profile = self.make_person(handle)

		frappe.get_doc(
			{
				"doctype": "VMMS Volunteer",
				"red_profile": profile,
				"status": "Active",
				"home_geo_node": node,
			}
		).insert(ignore_permissions=True)

		return user, profile

	def make_announcement(self, node: str, **overrides):
		values = {
			"doctype": "VMMS Announcement",
			"title": f"{self.tag} advisory",
			"urgency": "routine",
			"geo_node": node,
			"audience": "everyone",
			"body": "Body of the announcement.",
			"status": "Published",
			"also_email": 0,
		}
		values.update(overrides)

		return frappe.get_doc(values).insert(ignore_permissions=True)

	def copies(self, announcement: str) -> list[str]:
		return sorted(
			frappe.get_all(
				"VMMS Notification", filters={"announcement": announcement}, pluck="recipient"
			)
		)


class TestAnnouncementFanOut(AnnouncementFixture):
	def test_reaches_the_node_and_everything_beneath_it(self):
		"""A region's announcement reaches its branches; a branch's does not leak up."""
		at_region, _ = self.make_volunteer("region-vol", self.region)
		at_branch, _ = self.make_volunteer("branch-vol", self.branch)

		from_region = self.make_announcement(self.region)
		self.assertEqual(self.copies(from_region.name), sorted([at_region, at_branch]))

		from_branch = self.make_announcement(self.branch)
		self.assertEqual(
			self.copies(from_branch.name),
			[at_branch],
			"a branch announcement must not reach the region above it",
		)

	def test_a_sibling_branch_hears_nothing(self):
		"""The boundary is real, not an accident of there being one node."""
		mine, _ = self.make_volunteer("mine", self.branch)
		theirs, _ = self.make_volunteer("theirs", self.other)

		sent = self.make_announcement(self.branch)

		self.assertIn(mine, self.copies(sent.name))
		self.assertNotIn(theirs, self.copies(sent.name))

	def test_publishing_twice_delivers_nothing_twice(self):
		"""The guarantee the whole fan-out rests on."""
		self.make_volunteer("idem", self.branch)

		sent = self.make_announcement(self.branch)
		first = self.copies(sent.name)

		second = announce.publish(sent)

		self.assertEqual(self.copies(sent.name), first)
		self.assertEqual(second["created"], 0, "a second publish must create no copies")
		self.assertEqual(second["delivered"], len(first))

	def test_a_partial_fan_out_is_finished_rather_than_restarted(self):
		"""Resuming is the case idempotence actually buys, not the double press."""
		self.make_volunteer("resume-a", self.branch)
		sent = self.make_announcement(self.branch)

		# Somebody joins after the first publish, as they would in the days
		# between an announcement going out and being corrected.
		later, _ = self.make_volunteer("resume-b", self.branch)

		result = announce.publish(sent)

		self.assertEqual(result["created"], 1, "only the new person should be written")
		self.assertIn(later, self.copies(sent.name))
		self.assertEqual(len(self.copies(sent.name)), 2)

	def test_somebody_who_is_both_gets_one_copy(self):
		"""Resolved as a set of profiles, so the union happens before any write."""
		user, profile = self.make_volunteer("both", self.branch)

		member = frappe.get_doc(
			{"doctype": "VMMS Member", "red_profile": profile, "status": "Active"}
		).insert(ignore_permissions=True)

		membership_type = frappe.get_all("VMMS Membership Type", limit=1, pluck="name")
		self.assertTrue(membership_type, "this test needs a membership type to be meaningful")

		frappe.get_doc(
			{
				"doctype": "VMMS Membership",
				"member": member.name,
				"membership_type": membership_type[0],
				"geo_node": self.branch,
				"membership_status": "Active",
			}
		).insert(ignore_permissions=True)

		sent = self.make_announcement(self.branch, audience="everyone")

		self.assertEqual(
			self.copies(sent.name).count(user), 1, "one person, one copy, however many hats"
		)

	def test_audience_narrows_to_volunteers(self):
		volunteer, _ = self.make_volunteer("only-vol", self.branch)
		outsider, _ = self.make_person("not-vol")

		sent = self.make_announcement(self.branch, audience="volunteers")

		self.assertEqual(self.copies(sent.name), [volunteer])
		self.assertNotIn(outsider, self.copies(sent.name))

	def test_an_unknown_audience_reaches_nobody(self):
		"""The asymmetry is deliberate: a missing message is noticed, an
		unrecallable one is not."""
		self.make_volunteer("unknown-aud", self.branch)

		self.assertEqual(audience.profiles(self.branch, "not-a-real-audience"), set())

	def test_a_person_with_no_login_is_not_delivered_to(self):
		"""Ordinary, not an error: a clerk-enrolled member has no `user`."""
		profile = frappe.get_doc(
			{
				"doctype": "Red Profile",
				"first_name": "Loginless",
				"last_name": "Tester",
				"email": f"{self.tag}-loginless@example.invalid".lower(),
			}
		).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "VMMS Volunteer",
				"red_profile": profile.name,
				"status": "Active",
				"home_geo_node": self.branch,
			}
		).insert(ignore_permissions=True)

		sent = self.make_announcement(self.branch)

		self.assertIn(profile.name, audience.profiles(self.branch, "everyone"))
		self.assertEqual(self.copies(sent.name), [], "nowhere to deliver an in-app copy to")
		# The email channel is what reaches them, and it is resolved separately.
		self.assertIn(profile.email, audience.emails({profile.name}))

	def test_a_suspended_volunteer_stops_hearing_from_the_branch(self):
		user, profile = self.make_volunteer("suspended", self.branch)

		volunteer = frappe.db.get_value("VMMS Volunteer", {"red_profile": profile}, "name")
		frappe.db.set_value("VMMS Volunteer", volunteer, "status", "Suspended")

		sent = self.make_announcement(self.branch)

		self.assertNotIn(user, self.copies(sent.name))

	def test_a_draft_is_delivered_to_nobody(self):
		self.make_volunteer("draft-aud", self.branch)

		draft = self.make_announcement(self.branch, status="Draft")

		self.assertEqual(self.copies(draft.name), [])

	def test_a_published_announcement_cannot_be_unsent(self):
		sent = self.make_announcement(self.branch)
		sent.reload()
		sent.status = "Draft"

		with self.assertRaises(frappe.ValidationError):
			sent.save(ignore_permissions=True)

	def test_an_unsafe_link_is_refused_and_a_site_relative_one_is_not(self):
		sent = self.make_announcement(self.branch)

		sent.reload()
		sent.link_href = "javascript:alert(1)"
		with self.assertRaises(frappe.ValidationError):
			sent.save(ignore_permissions=True)

		sent.reload()
		sent.link_href = "/portal/events"
		sent.save(ignore_permissions=True)
		self.assertEqual(sent.link_href, "/portal/events")

	def test_delivered_count_records_the_reach(self):
		self.make_volunteer("counted-a", self.branch)
		self.make_volunteer("counted-b", self.branch)

		sent = self.make_announcement(self.branch)
		sent.reload()

		self.assertEqual(sent.delivered_count, 2)
		self.assertTrue(sent.published_on)

	def test_one_person_cannot_hold_two_copies_by_any_route(self):
		"""Enforced on the doctype as well as checked in the service."""
		user, _ = self.make_volunteer("dupe", self.branch)
		sent = self.make_announcement(self.branch)

		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(
				{
					"doctype": "VMMS Notification",
					"announcement": sent.name,
					"recipient": user,
				}
			).insert(ignore_permissions=True)

	def test_urgency_dispatches_rather_than_being_compared(self):
		"""The table is the behaviour; an unknown value ranks lowest and mails not."""
		self.assertGreater(announce.rank("urgent"), announce.rank("important"))
		self.assertGreater(announce.rank("important"), announce.rank("routine"))
		self.assertEqual(announce.rank("invented-by-a-society"), 0)

		self.assertTrue(announce.emails_by_default("urgent"))
		self.assertFalse(announce.emails_by_default("routine"))


class TestOnePersonsFeed(AnnouncementFixture):
	"""The read side, from inside the recipient's own session."""

	def test_the_feed_is_only_ever_your_own(self):
		mine, _ = self.make_volunteer("feed-mine", self.branch)
		theirs, _ = self.make_volunteer("feed-theirs", self.other)

		self.make_announcement(self.branch)

		frappe.set_user(theirs)
		self.assertEqual(delivery.feed(), [], "another branch's announcement is not yours")

		frappe.set_user(mine)
		self.assertEqual(len(delivery.feed()), 1)

	def test_unread_counts_and_marking_read_clears_it(self):
		user, _ = self.make_volunteer("feed-unread", self.branch)
		self.make_announcement(self.branch)

		frappe.set_user(user)

		self.assertEqual(delivery.unread(), 1)

		row = delivery.feed()[0]
		self.assertTrue(delivery.mark_read(row["source"], row["id"]))
		self.assertEqual(delivery.unread(), 0)

		# Idempotent: marking it again is fine and changes nothing.
		self.assertTrue(delivery.mark_read(row["source"], row["id"]))
		self.assertEqual(delivery.unread(), 0)

	def test_marking_somebody_elses_notification_read_does_nothing(self):
		mine, _ = self.make_volunteer("mark-mine", self.branch)
		self.make_volunteer("mark-theirs", self.other)

		sent = self.make_announcement(self.other)
		row = frappe.get_all(
			"VMMS Notification", filters={"announcement": sent.name}, pluck="name"
		)[0]

		frappe.set_user(mine)

		self.assertFalse(
			delivery.mark_read("announcement", row),
			"a name that belongs to somebody else must not match",
		)

		frappe.set_user("Administrator")
		self.assertFalse(
			frappe.db.get_value("VMMS Notification", row, "is_read"),
			"and it must not have been marked read",
		)

	def test_an_unknown_source_is_false_rather_than_an_exception(self):
		user, _ = self.make_volunteer("bad-source", self.branch)
		frappe.set_user(user)

		self.assertFalse(delivery.mark_read("nonsense", "whatever"))

	def test_an_expired_announcement_leaves_the_feed_but_not_the_record(self):
		user, _ = self.make_volunteer("expired", self.branch)

		sent = self.make_announcement(self.branch, expires_on="2020-01-01")

		frappe.set_user(user)
		self.assertEqual(delivery.feed(), [], "an expired advisory is noise")

		frappe.set_user("Administrator")
		self.assertEqual(
			len(self.copies(sent.name)), 1, "the record of having been told survives expiry"
		)

	def test_urgent_sorts_above_routine(self):
		user, _ = self.make_volunteer("sorting", self.branch)

		self.make_announcement(self.branch, title=f"{self.tag} routine", urgency="routine")
		self.make_announcement(self.branch, title=f"{self.tag} urgent", urgency="urgent")

		frappe.set_user(user)

		self.assertEqual(delivery.feed()[0]["urgency"], "urgent")

	def test_mark_all_read_clears_the_feed(self):
		user, _ = self.make_volunteer("mark-all", self.branch)

		self.make_announcement(self.branch, title=f"{self.tag} one")
		self.make_announcement(self.branch, title=f"{self.tag} two")

		frappe.set_user(user)

		self.assertEqual(delivery.unread(), 2)
		self.assertEqual(delivery.mark_all_read(), 2)
		self.assertEqual(delivery.unread(), 0)

	def test_the_wording_is_read_through_the_link_not_copied(self):
		"""Correcting an announcement corrects every copy of it at once."""
		user, _ = self.make_volunteer("corrected", self.branch)

		sent = self.make_announcement(self.branch, title=f"{self.tag} original")

		sent.reload()
		sent.title = f"{self.tag} corrected"
		sent.save(ignore_permissions=True)

		frappe.set_user(user)

		self.assertEqual(delivery.feed()[0]["title"], f"{self.tag} corrected")
