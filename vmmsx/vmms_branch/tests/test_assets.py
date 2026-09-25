"""Branch stock balances, geo authority and volunteer ownership."""

import frappe

from vmmsx.api import assets
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase
from vmmsx.notifications.services import delivery
from vmmsx.setup.core_roles import ROLE_ASSET_MANAGER


class TestAssets(DeploymentTestCase):
	def setUp(self):
		super().setUp()
		self.branch = self.society_a["branch"]
		self.other = self.society_a["other_branch"]
		self.volunteer = fixtures.make_volunteer(fixtures.make_profile(), self.branch).name
		self.stock = assets.create_asset("Safety helmet " + frappe.generate_hash(length=6), self.branch)[
			"name"
		]

	def test_receive_issue_and_partial_return_keep_balances(self):
		assets.receive(self.stock, 5)
		issued = assets.issue(self.stock, self.volunteer, 3)
		self.assertFalse(issued["notification_queued"])
		self.assertEqual(frappe.db.get_value(assets.ASSET, self.stock, "available_quantity"), 2)
		assets.return_asset(issued["name"], 2)
		self.assertEqual(frappe.db.get_value(assets.ASSET, self.stock, "available_quantity"), 4)
		self.assertEqual(assets.outstanding(self.branch)[0]["outstanding"], 1)
		with self.assertRaises(frappe.ValidationError):
			assets.return_asset(issued["name"], 2)
		with self.assertRaises(frappe.ValidationError):
			assets.issue(self.stock, self.volunteer, 5)

	def test_manager_sees_only_assigned_branch(self):
		remote = assets.create_asset("Remote helmet " + frappe.generate_hash(length=6), self.other)["name"]
		remote_volunteer = fixtures.make_volunteer(fixtures.make_profile(), self.other).name
		assets.receive(remote, 1)
		remote_issue = assets.issue(remote, remote_volunteer, 1)["name"]
		manager = fixtures.make_user("asset_manager", [ROLE_ASSET_MANAGER])
		fixtures.make_assignment(manager, ROLE_ASSET_MANAGER, self.branch)
		frappe.set_user(manager)
		self.assertIn(self.stock, [row["name"] for row in assets.stock()["assets"]])
		self.assertNotIn(remote, [row["name"] for row in assets.stock()["assets"]])
		with self.assertRaises(frappe.PermissionError):
			assets.receive(remote, 1)
		with self.assertRaises(frappe.PermissionError):
			assets.remind(remote_issue)

	def test_issue_stays_in_asset_branch_even_with_wider_manager_scope(self):
		other_volunteer = fixtures.make_volunteer(fixtures.make_profile(), self.other).name
		manager = fixtures.make_user("regional_asset_manager", [ROLE_ASSET_MANAGER])
		fixtures.make_assignment(manager, ROLE_ASSET_MANAGER, self.society_a["region"])
		assets.receive(self.stock, 2)
		frappe.set_user(manager)
		self.assertNotIn(
			other_volunteer, [row["name"] for row in assets.search_volunteers(self.branch, "Amina")]
		)
		with self.assertRaises(frappe.PermissionError):
			assets.issue(self.stock, other_volunteer, 1)

	def test_volunteer_can_return_only_own_issue(self):
		holder = fixtures.make_user("asset_holder")
		profile = fixtures.make_profile("Asset", "Holder", user=holder)
		volunteer = fixtures.make_volunteer(profile, self.branch).name
		assets.receive(self.stock, 2)
		issued = assets.issue(self.stock, volunteer, 1)
		frappe.set_user(holder)
		self.assertEqual(assets.my_assets()[0]["name"], issued["name"])
		assets.return_my_asset(issued["name"], 1)
		self.assertEqual(assets.my_assets(), [])
		with self.assertRaises(frappe.ValidationError):
			assets.return_my_asset(issued["name"], 1)

	def test_volunteer_cannot_return_another_persons_issue(self):
		holder = fixtures.make_user("asset_other_holder")
		profile = fixtures.make_profile("Other", "Holder", user=holder)
		fixtures.make_volunteer(profile, self.branch)
		assets.receive(self.stock, 1)
		issued = assets.issue(self.stock, self.volunteer, 1)
		frappe.set_user(holder)
		self.assertEqual(assets.my_assets(), [])
		with self.assertRaises(frappe.PermissionError):
			assets.return_my_asset(issued["name"], 1)
		self.assertEqual(frappe.db.get_value(assets.ASSET, self.stock, "available_quantity"), 0)

	def test_search_narrows_assets_and_volunteers_on_the_server(self):
		other_asset = assets.create_asset("Radio " + frappe.generate_hash(length=6), self.branch)["name"]
		self.assertEqual(assets.search_assets(self.branch, "Radio")[0]["name"], other_asset)
		self.assertEqual(assets.search_assets(self.branch, "R"), [])
		self.assertIn(self.volunteer, [row["name"] for row in assets.search_volunteers(self.branch, "Amina")])
		self.assertEqual(assets.search_volunteers(self.branch, "A"), [])
		self.assertEqual(assets.stock(self.branch, "Radio")["assets"][0]["name"], other_asset)

	def test_issue_notifies_and_manager_can_remind_only_while_outstanding(self):
		holder = fixtures.make_user("asset_notice_holder")
		profile = fixtures.make_profile("Notice", "Holder", user=holder)
		volunteer = fixtures.make_volunteer(profile, self.branch).name
		assets.receive(self.stock, 1)
		issued = assets.issue(self.stock, volunteer, 1)
		self.assertTrue(issued["notification_queued"])
		reminder = assets.remind(issued["name"])
		self.assertTrue(reminder["notification_queued"])
		self.assertEqual(reminder["outstanding"], 1)
		self.assertEqual(frappe.db.get_value(assets.TRANSACTION, issued["name"], "reminder_count"), 1)
		logs = frappe.get_all(
			"Notification Log",
			filters={"for_user": holder, "document_name": issued["name"]},
			fields=["subject", "link"],
			order_by="creation asc",
		)
		self.assertEqual(len(logs), 2)
		self.assertTrue(all(row.link == "/portal/assets" for row in logs))
		frappe.set_user(holder)
		self.assertTrue(any(row["href"] == "/portal/assets" for row in delivery.feed()))
		frappe.set_user("Administrator")
		assets.return_asset(issued["name"], 1)
		with self.assertRaises(frappe.ValidationError):
			assets.remind(issued["name"])
