# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Addressing a branch's own people, on three channels resolved from one audience.

`test_announce.py` proves the fan-out: who hears an announcement, once, and
where the geo boundary is. This suite is the console's layer on top —
`api/communication.py` — and the properties it holds are different ones:

1. **One audience, three reaches.** The in-app copy needs a login, the email
   needs an address and the SMS needs a number with a country code. Those are
   three overlapping sets of people, and a screen that showed one figure for all
   three would tell a branch it had reached people it had not. The preview
   counts each separately from the same resolved set.

2. **The preview and the send agree.** They call the same resolver with the same
   arguments, so the number somebody reads before pressing send is the number
   that gets sent to. A preview computed by a different path is a preview that
   can be wrong exactly when it matters.

3. **Scope is checked on the anchor, not on the doctype.** Holding the
   announcement role does not make somebody entitled to address a branch on the
   other side of the country, and the check is `frappe.has_permission` against
   the proposed document — which is core's geo scoping, not a rule written in
   the endpoint.

4. **SMS is filed, never sent.** onerc_sms owns an approval workflow, and this
   console composes a Draft campaign for it rather than reaching around it. A
   campaign that came back already sent would be this app overruling another
   app's policy.

Nothing here is mocked. Geo comes from core's fixtures, the announcement is the
real doctype and its real fan-out, and the campaign is onerc_sms's own document.
"""

import frappe

from vmmsx.api import communication
from vmmsx.notifications.services import campaign
from vmmsx.notifications.tests.test_announce import AnnouncementFixture

EXTRA_TEST_RECORD_DEPENDENCIES = []

SCOPE_ROLE_SETTING = "vmms_announcement_scope_role"


class CommunicationFixture(AnnouncementFixture):
	"""The announcement suite's arrangement, plus people reachable three ways."""

	def make_member(self, handle: str, node: str, **profile_overrides) -> tuple[str, str]:
		"""Somebody with an active membership at `node`.

		Through the membership rather than through `VMMS Member`, because the
		membership is the record that carries a place — the same reason
		`audience._members` resolves that way.
		"""
		user, profile = self.make_person(handle)

		if profile_overrides:
			frappe.db.set_value("Red Profile", profile, profile_overrides)

		member = frappe.get_doc(
			{"doctype": "VMMS Member", "red_profile": profile, "status": "Active"}
		).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "VMMS Membership",
				"member": member.name,
				"membership_type": self.membership_type(),
				"geo_node": node,
				"membership_status": "Active",
			}
		).insert(ignore_permissions=True)

		return user, profile

	def membership_type(self) -> str:
		"""One free type for the whole suite. Made once, reused by every test."""
		key = "COMMTEST-free"

		if not frappe.db.exists("VMMS Membership Type", key):
			frappe.get_doc(
				{
					"doctype": "VMMS Membership Type",
					"membership_type_key": key,
					"membership_type_name": "Commtest Free",
					# A fee, because `auto_on_payment` with nothing to pay is
					# refused by the type's own validate — a membership that
					# activates on payment and charges nothing would never have
					# anything to wait for. What this suite needs is a member at
					# a branch, and the fee is incidental to that.
					"approval_mode": "auto_on_payment",
					"fee_amount": 100,
					"duration_days": 365,
					"is_active": 1,
				}
			).insert(ignore_permissions=True)

		return key


class TestTheReachIsCountedPerChannel(CommunicationFixture):
	def test_the_three_channels_are_three_different_numbers(self):
		"""The whole reason the preview exists, and the failure it prevents.

		Three people: one reachable every way, one with no login (enrolled at a
		counter and never signed in), one with no phone number. A single "reach"
		figure would be wrong for two of the three channels whichever number it
		chose.
		"""
		self.make_volunteer("everything", self.branch)
		frappe.db.set_value(
			"Red Profile",
			frappe.db.get_value("Red Profile", {"first_name": "everything"}, "name"),
			"phone",
			"+255700000001",
		)

		# No login at all: reachable by email and by phone, and by nothing in the
		# portal. This is the person a single figure always gets wrong.
		counter = frappe.get_doc(
			{
				"doctype": "Red Profile",
				"first_name": "counter",
				"last_name": "Tester",
				"email": f"{self.tag}-counter@example.invalid".lower(),
				"phone": "+255700000002",
			}
		).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "VMMS Volunteer",
				"red_profile": counter.name,
				"status": "Active",
				"home_geo_node": self.branch,
			}
		).insert(ignore_permissions=True)

		reach = communication.preview(self.branch, "volunteers")

		self.assertEqual(reach["addressed"], 2)
		self.assertEqual(reach["notification"], 1, "the counter enrolment has no login")
		self.assertEqual(reach["email"], 2)
		self.assertEqual(reach["sms"], 2)

	def test_a_number_without_a_country_code_is_not_counted_as_reachable(self):
		"""onerc_sms skips it at send time, so it must not be promised here.

		The rule is the other app's; applying it in only one of the two places
		is how a campaign reports nine hundred recipients and texts six hundred.
		"""
		self.make_volunteer("local-number", self.branch)
		frappe.db.set_value(
			"Red Profile",
			frappe.db.get_value("Red Profile", {"first_name": "local-number"}, "name"),
			"phone",
			"0700000003",
		)

		reach = communication.preview(self.branch, "volunteers")

		self.assertEqual(reach["addressed"], 1)
		self.assertEqual(reach["sms"], 0)

	def test_the_audience_narrows_who_is_counted(self):
		self.make_volunteer("a-volunteer", self.branch)
		self.make_member("a-member", self.branch)

		self.assertEqual(communication.preview(self.branch, "volunteers")["addressed"], 1)
		self.assertEqual(communication.preview(self.branch, "members")["addressed"], 1)
		self.assertEqual(communication.preview(self.branch, "everyone")["addressed"], 2)

	def test_the_preview_respects_the_same_boundary_the_send_does(self):
		"""A branch's preview does not count the region above it."""
		self.make_volunteer("above", self.region)
		self.make_volunteer("below", self.branch)

		self.assertEqual(communication.preview(self.branch, "volunteers")["addressed"], 1)
		self.assertEqual(communication.preview(self.region, "volunteers")["addressed"], 2)


class TestSending(CommunicationFixture):
	def test_it_publishes_one_announcement_and_fans_it_out(self):
		user, _ = self.make_volunteer("reader", self.branch)

		report = communication.send(
			title=f"{self.tag} Branch meeting moved",
			body="Saturday, ten o'clock.",
			geo_node=self.branch,
			who="volunteers",
			channels=["notification"],
		)

		self.assertIsNotNone(report["announcement"])
		self.assertEqual(report["announcement"]["delivered"], 1)
		self.assertEqual(self.copies(report["announcement"]["announcement"]), [user])
		# Nothing was filed with onerc_sms, because nobody asked for SMS.
		self.assertIsNone(report["sms"])

	def test_email_and_notification_are_one_announcement_not_two(self):
		"""One record of having said it, not two that can be edited apart."""
		self.make_volunteer("both-ways", self.branch)

		report = communication.send(
			title=f"{self.tag} Both ways",
			body="Said once.",
			geo_node=self.branch,
			who="volunteers",
			channels=["notification", "email"],
		)

		name = report["announcement"]["announcement"]

		self.assertTrue(report["notification_sent"])
		self.assertTrue(report["email_sent"])
		self.assertEqual(frappe.db.get_value("VMMS Announcement", name, "also_email"), 1)
		self.assertEqual(
			frappe.db.count("VMMS Announcement", {"title": f"{self.tag} Both ways"}),
			1,
			"two channels produced two announcements",
		)

	def test_a_channel_this_society_cannot_send_on_is_refused_not_dropped(self):
		"""A channel silently ignored is a message somebody thinks they sent."""
		self.make_volunteer("nobody", self.branch)

		with self.assertRaises(frappe.ValidationError):
			communication.send(
				title=f"{self.tag} Carrier pigeon",
				body="…",
				geo_node=self.branch,
				who="volunteers",
				channels=["pigeon"],
			)

	def test_sending_on_no_channel_at_all_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			communication.send(
				title=f"{self.tag} Nothing",
				body="…",
				geo_node=self.branch,
				who="volunteers",
				channels=[],
			)

	def test_an_announcement_with_no_anchor_is_refused(self):
		"""ACC-02 at the boundary. A fan-out with no anchor resolves everybody."""
		with self.assertRaises(frappe.ValidationError):
			communication.send(
				title=f"{self.tag} Unanchored",
				body="…",
				geo_node="",
				who="everyone",
				channels=["notification"],
			)


class TestTheSmsChannelIsFiledNotSent(CommunicationFixture):
	def setUp(self):
		super().setUp()

		if not campaign.installed():
			self.skipTest("onerc_sms is not installed on this site")

	def test_a_campaign_is_created_as_a_draft_for_approval(self):
		self.make_volunteer("textable", self.branch)
		frappe.db.set_value(
			"Red Profile",
			frappe.db.get_value("Red Profile", {"first_name": "textable"}, "name"),
			"phone",
			"+255700000004",
		)

		filed = campaign.draft(
			name=f"{self.tag} Meeting",
			message="Branch meeting Saturday, ten o'clock.",
			geo_node=self.branch,
			who="volunteers",
		)

		self.assertEqual(filed["recipients"], 1)

		doc = frappe.get_doc("SMS Campaign", filed["campaign"])

		self.assertEqual(doc.status, "Draft")
		self.assertEqual(doc.docstatus, 0, "a filed campaign must not be submitted")
		# The resolved list, written down — not a query re-run at send time. An
		# approver approves a list of people, not a filter.
		self.assertEqual(doc.source_type, "Manual")
		self.assertIn("+255700000004", doc.phone_numbers)

	def test_numbers_without_a_country_code_are_left_out_and_counted(self):
		"""Reported rather than silently skipped, which is what onerc_sms does."""
		self.make_volunteer("good-number", self.branch)
		self.make_volunteer("bad-number", self.branch)
		frappe.db.set_value(
			"Red Profile",
			frappe.db.get_value("Red Profile", {"first_name": "good-number"}, "name"),
			"phone",
			"+255700000005",
		)
		frappe.db.set_value(
			"Red Profile",
			frappe.db.get_value("Red Profile", {"first_name": "bad-number"}, "name"),
			"phone",
			"0700000006",
		)

		filed = campaign.draft(
			name=f"{self.tag} Partly reachable",
			message="…",
			geo_node=self.branch,
			who="volunteers",
		)

		self.assertEqual(filed["recipients"], 1)
		self.assertEqual(filed["malformed"], 1)
		self.assertEqual(filed["addressed"], 2)

	def test_an_audience_with_no_numbers_files_nothing(self):
		"""Refused out loud rather than filing an empty campaign somebody approves."""
		self.make_volunteer("unreachable", self.branch)

		with self.assertRaises(frappe.ValidationError):
			campaign.draft(
				name=f"{self.tag} Nobody",
				message="…",
				geo_node=self.branch,
				who="volunteers",
			)
