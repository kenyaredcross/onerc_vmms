# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Site Setup page: the step list, its data, and the runner's promises."""

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

from . import geography, kenya, roles, steps
from . import vmms_site_setup as api


class TestTheStepList(IntegrationTestCase):
	def test_every_step_reads_only_settings_the_form_has(self):
		known = set(steps.defaults())
		for step in steps.STEPS:
			self.assertTrue(set(step.uses) <= known, step.key)

	def test_the_steps_are_unique_and_the_readiness_check_is_last_and_check_only(self):
		keys = [step.key for step in steps.STEPS]
		self.assertEqual(len(keys), len(set(keys)))
		self.assertEqual(steps.STEPS[-1].key, "verify")
		self.assertTrue(steps.STEPS[-1].check_only)

	def test_the_bundled_geography_is_kenya(self):
		counts = geography.validate_dataset(geography.without_region_prefix(geography.load()))

		self.assertEqual((counts["national"], counts["region"], counts["county"]), (1, 8, 47))
		self.assertTrue(counts.get("sub_county"))

	def test_the_regions_hang_under_the_society_s_own_root_whatever_its_name(self):
		with patch.object(
			frappe,
			"get_all",
			return_value=[frappe._dict(geo_node_name="Kenya Red Cross", geo_code=None)],
		):
			data = geography.under_the_existing_root(frappe, geography.load())

		national = [row for row in data["nodes"] if row["level"] == "national"]
		self.assertEqual(national[0]["label"], "Kenya Red Cross")

	def test_the_county_map_ships_with_the_app(self):
		self.assertTrue(kenya.COUNTY_MAP.is_file())


class TestWhatTheFormHolds(IntegrationTestCase):
	def test_old_counters_raise_the_floors_and_never_lower_them(self):
		floors = kenya.parse_series("VM-MEM-2026-=1500\nVM-MSH-2026-=10")

		self.assertEqual(floors["VM-MEM-2026-"], 1500)
		self.assertEqual(floors["VM-MSH-2026-"], kenya.OLD_SERIES["VM-MSH-2026-"])

	def test_a_counter_line_that_is_not_one_is_refused(self):
		with self.assertRaises(ValueError):
			kenya.parse_series("VOL-2026=12")

	def test_nsd_coordinators_may_be_typed_one_per_line_or_with_commas(self):
		self.assertEqual(roles.emails("a@x.org\nb@x.org, c@x.org"), ["a@x.org", "b@x.org", "c@x.org"])
		self.assertEqual(roles.emails(""), [])

	def test_saved_settings_keep_only_what_the_form_has(self):
		saved = steps.save_settings({"mpesa_shortcode": "174379", "unknown": "x"})

		self.assertEqual(saved["mpesa_shortcode"], "174379")
		self.assertNotIn("unknown", steps.settings())
		self.assertEqual(steps.settings()["currency"], "KES")


class TestTheRunner(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.set_global(steps.RESULTS_KEY, "{}")

	def fake(self, work, check_only=False):
		step = steps.Step("fake", "Fake", "A step for the test.", work, check_only=check_only)
		return patch.dict(steps.BY_KEY, {"fake": step})

	def test_a_check_rolls_back_and_a_run_commits(self):
		with (
			self.fake(lambda frappe, settings, apply: {"did": apply}),
			patch.object(frappe.db, "commit") as commit,
			patch.object(frappe.db, "rollback") as rollback,
		):
			steps.execute("fake", False, "Administrator")
			self.assertEqual(rollback.call_count, 1)
			self.assertEqual(steps.results()["fake"]["mode"], "check")

			steps.execute("fake", True, "Administrator")
			self.assertEqual(rollback.call_count, 1)
			self.assertGreaterEqual(commit.call_count, 2)

		row = steps.results()["fake"]
		self.assertEqual((row["status"], row["mode"], row["result"]), ("done", "run", {"did": True}))

	def test_a_step_that_fails_is_kept_with_what_it_said(self):
		def broken(frappe, settings, apply):
			raise ValueError("Fill in the shortcode first.")

		with self.fake(broken), patch.object(frappe.db, "commit"), patch.object(frappe.db, "rollback"):
			steps.execute("fake", True, "Administrator")

		row = steps.results()["fake"]
		self.assertEqual(row["status"], "failed")
		self.assertEqual(row["error"], "Fill in the shortcode first.")

	def test_the_job_runs_as_administrator_and_gives_the_session_back(self):
		seen = {}

		def who(frappe, settings, apply):
			seen["user"] = frappe.session.user
			return {}

		frappe.set_user("Guest")
		try:
			with self.fake(who), patch.object(frappe.db, "commit"), patch.object(frappe.db, "rollback"):
				steps.execute("fake", False, "someone@example.org")
			self.assertEqual(frappe.session.user, "Guest")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(seen["user"], "Administrator")

	def test_one_step_at_a_time(self):
		frappe.db.set_global(
			steps.RESULTS_KEY, json.dumps({"geography": {"status": "running", "at": str(now_datetime())}})
		)

		with self.assertRaises(frappe.ValidationError):
			steps.start("roles", True)

	def test_a_job_that_died_is_reported_failed_and_frees_the_page(self):
		long_ago = add_to_date(now_datetime(), seconds=-(steps.JOB_TIMEOUT + 600))
		frappe.db.set_global(
			steps.RESULTS_KEY, json.dumps({"geography": {"status": "running", "at": str(long_ago)}})
		)

		self.assertEqual(steps.results()["geography"]["status"], "failed")
		self.assertIsNone(steps.running())

	def test_the_readiness_check_never_applies(self):
		with patch.object(frappe, "enqueue") as enqueue, patch.object(frappe.db, "commit"):
			steps.start("verify", True)

		self.assertFalse(enqueue.call_args.kwargs["apply"])


class TestWhoMayUseIt(IntegrationTestCase):
	def test_only_a_system_manager(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				api.state()
		finally:
			frappe.set_user("Administrator")

	def test_the_page_lists_every_step(self):
		state = api.state()

		self.assertEqual([row["key"] for row in state["steps"]], [step.key for step in steps.STEPS])
		self.assertIn("settings", state)


class TestTheSocietyStep(IntegrationTestCase):
	"""For a site whose setup wizard ran before vmmsx was installed."""

	def forget_the_society(self):
		frappe.db.set_single_value("National Society Settings", "organization_name", "")

	def test_a_society_already_set_up_is_left_alone(self):
		from vmmsx.setup import wizard

		if not wizard._already_configured():
			self.skipTest("this site's society is not set up")
		with patch.object(wizard, "setup_national_society") as setup:
			result = kenya.society(frappe, steps.settings(), True)

		self.assertTrue(result["already_set_up"])
		setup.assert_not_called()

	def test_a_check_says_what_it_would_set_and_writes_nothing(self):
		self.forget_the_society()
		with patch.object(kenya, "_upload_logo") as upload:
			result = kenya.society(frappe, steps.settings(), False)

		upload.assert_not_called()
		self.assertFalse(result["already_set_up"])
		self.assertEqual(result["levels"], kenya.LEVELS)
		self.assertEqual(result["applications_taken_at"], "County")
		self.assertEqual(frappe.db.get_single_value("National Society Settings", "organization_name"), "")

	def test_a_run_sets_the_society_up_through_the_wizard_s_own_code(self):
		from vmmsx.setup import wizard

		self.forget_the_society()
		with patch.object(kenya, "_upload_logo", return_value="/files/krcs-logo.png"):
			result = kenya.society(frappe, steps.settings(), True)

		self.assertTrue(result["set_up"])
		self.assertTrue(wizard._already_configured())
		nss = frappe.get_single("National Society Settings")
		self.assertEqual(nss.organization_name, "Kenya Red Cross Society")
		self.assertEqual(nss.logo, "/files/krcs-logo.png")
		self.assertEqual(
			frappe.db.get_value("Geo Level", nss.get(wizard.VOLUNTEER_ANCHOR_FIELD), "geo_level_name"),
			"County",
		)

	def test_what_was_typed_into_the_settings_by_hand_is_kept(self):
		self.forget_the_society()
		frappe.db.set_single_value("National Society Settings", "organization_name", "Kenya Red Cross")
		frappe.db.set_single_value("National Society Settings", "logo", "/files/our-logo.png")

		with patch.object(kenya, "_upload_logo") as upload:
			kenya.society(frappe, steps.settings(), True)

		upload.assert_not_called()
		nss = frappe.get_single("National Society Settings")
		self.assertEqual(nss.organization_name, "Kenya Red Cross")
		self.assertEqual(nss.logo, "/files/our-logo.png")

	def test_the_name_is_required(self):
		self.forget_the_society()
		steps.save_settings({"society_name": " "})
		frappe.db.set_single_value("National Society Settings", "organization_name", "")

		with self.assertRaises(ValueError):
			kenya.society(frappe, steps.settings(), True)
