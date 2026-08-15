# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A fresh install has to do what a migrate does, and nothing here may be silent.

Frappe does not run an app's patches on a fresh install: `install_app()` calls
`set_all_patches_as_completed()`, which writes every line of `patches.txt` into
the Patch Log without executing any of it. For schema that is correct — the
doctypes are synced from their JSON. For everything else this app keeps in a
patch it is a site that looks installed and is not: no scope-role Custom Fields,
so no access model; no geo anchor on `Buzz Event`; no content surfaces; and no
society, so the sign-up page tells visitors the society is not taking accounts.

All of that was seen on real sites before `vmmsx/install.py` existed, and none
of it announced itself. So what is asserted here is the wiring rather than the
outcome: that the hook is declared, that every patch it will run can actually be
called, and that the bootstrap decides from the site's own state rather than
from a log of what has been attempted.
"""

import frappe
from frappe.modules.patch_handler import PatchType, get_patches_from_app
from frappe.tests import IntegrationTestCase

APP = "vmmsx"


class TestTheInstallHookIsWired(IntegrationTestCase):
	def test_after_install_is_declared(self):
		"""Commenting this out is how a fresh site silently gets nothing."""
		self.assertIn("vmmsx.install.after_install", frappe.get_hooks("after_install") or [])

	def test_every_post_model_sync_patch_can_be_called(self):
		"""`after_install` calls each one by dotted path. A patch module without an
		`execute` would fail one step of an install and be found by whoever
		notices the thing it was supposed to set up is missing."""
		patches = get_patches_from_app(APP, PatchType.post_model_sync)

		self.assertTrue(patches, "patches.txt lists no post-model-sync patches")

		for patch in patches:
			module = patch.split(maxsplit=1)[0]

			self.assertTrue(callable(frappe.get_attr(f"{module}.execute")), module)

	def test_the_patch_list_is_read_rather_than_restated(self):
		"""The list `after_install` runs comes from `patches.txt` itself, so a
		patch added later needs nothing remembered here. This asserts the source,
		because a hand-kept copy would drift and drift silently."""
		import inspect

		from vmmsx import install

		source = inspect.getsource(install._run_setup_patches)

		self.assertIn("get_patches_from_app", source)
		self.assertIn("post_model_sync", source)

	def test_the_buzz_seam_is_reinstalled_on_every_migrate(self):
		"""Install order is not ours to control. A site that installed vmmsx
		before Buzz ran that patch against an absent app, where it correctly did
		nothing — and a patch is spent. It has to be asked again."""
		self.assertIn(
			"vmmsx.patches.setup_buzz_seam.install_geo_anchor_field",
			frappe.get_hooks("after_migrate") or [],
		)

	def test_the_society_bootstrap_runs_on_every_migrate(self):
		self.assertIn("vmmsx.setup.bootstrap.ensure_society", frappe.get_hooks("after_migrate") or [])


class TestTheBootstrapDecidesFromTheSite(IntegrationTestCase):
	"""Seeded or not is a question about the site, never a marker somebody set."""

	def test_a_site_naming_no_society_is_left_alone(self):
		from vmmsx.setup import bootstrap

		previous = frappe.conf.get("vmmsx_seed_society")
		frappe.conf.vmmsx_seed_society = None
		self.addCleanup(setattr, frappe.conf, "vmmsx_seed_society", previous)

		self.assertIsNone(bootstrap.ensure_society())

	def test_a_society_already_on_the_site_is_not_seeded_again(self):
		"""What makes this safe to run on every deploy forever."""
		from vmmsx.seed import gambia
		from vmmsx.setup import bootstrap

		if not frappe.db.exists("Geo Node", {"geo_node_name": gambia.NATIONAL_NODE}):
			self.skipTest("this bench does not carry the Gambia society")

		self.assertTrue(bootstrap.is_seeded("gambia"))

		previous = frappe.conf.get("vmmsx_seed_society")
		frappe.conf.vmmsx_seed_society = "gambia"
		self.addCleanup(setattr, frappe.conf, "vmmsx_seed_society", previous)

		self.assertIsNone(bootstrap.ensure_society())

	def test_a_seed_whose_root_node_is_absent_reports_unseeded(self):
		"""The other direction, and the one that decides whether a new site gets
		a society at all."""
		from vmmsx.setup import bootstrap

		self.assertFalse(bootstrap.is_seeded("there_is_no_such_seed"))

	def test_every_seed_declares_the_node_the_check_reads(self):
		"""`is_seeded` treats a seed with no `NATIONAL_NODE` as never seeded, which
		is safe but means it would re-run on every deploy. Every seed this app
		ships declares one."""
		import importlib

		for society in ("gambia", "kenya"):
			module = importlib.import_module(f"vmmsx.seed.{society}")

			self.assertTrue(getattr(module, "NATIONAL_NODE", None), society)
