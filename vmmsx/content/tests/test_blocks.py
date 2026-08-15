# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The editable-wording layer: what it serves, to whom, and what it refuses.

Three properties are worth a test each, because each one is a promise something
else in the system relies on:

- **A seed never overwrites.** `setup_content_module` runs on every migrate. If
  `seed()` refreshed the shipped defaults, every deploy would silently revert a
  society's rewritten home page, and nobody would connect the two events.
- **A private surface is private to a guest.** The landing page is served to
  signed-out visitors, which means one endpoint in this app is `allow_guest`.
  What stops it becoming a hole is the `is_public` flag, and a test that a guest
  is refused the coordinator's surface is what stops a later refactor removing
  the check.
- **A link is refused unless it is one of ours or an ordinary web address.**
  `link_href` is administrator-supplied and lands in an `href` served to the
  public. A `javascript:` URI there is stored cross-site scripting.

The partial-update test guards a subtler promise: the pencil beside a caption
sends only a caption, and must not blank the photograph beside it.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.api import content as content_api
from vmmsx.content.services import blocks as block_service

EXTRA_TEST_RECORD_DEPENDENCIES = []

SURFACE_DOCTYPE = "VMMS Content Surface"
BLOCK_DOCTYPE = "VMMS Content Block"

PUBLIC_SURFACE = "CONTENT-TEST-public"
PRIVATE_SURFACE = "CONTENT-TEST-private"
TEST_KEY = "content-test.slot.one"


def make_surface(key: str, public: bool) -> None:
	if frappe.db.exists(SURFACE_DOCTYPE, key):
		frappe.delete_doc(SURFACE_DOCTYPE, key, force=True)

	frappe.get_doc(
		{
			"doctype": SURFACE_DOCTYPE,
			"surface_key": key,
			"surface_name": key,
			"is_public": 1 if public else 0,
		}
	).insert(ignore_permissions=True)


def make_block(key: str = TEST_KEY, surface: str = PUBLIC_SURFACE, **overrides):
	if frappe.db.exists(BLOCK_DOCTYPE, key):
		frappe.delete_doc(BLOCK_DOCTYPE, key, force=True)

	values = {
		"doctype": BLOCK_DOCTYPE,
		"content_key": key,
		"label": "A test slot",
		"surface": surface,
		"text_value": "Original wording",
	}
	values.update(overrides)

	return frappe.get_doc(values).insert(ignore_permissions=True)


class TestContentBlocks(IntegrationTestCase):
	def setUp(self):
		make_surface(PUBLIC_SURFACE, public=True)
		make_surface(PRIVATE_SURFACE, public=False)
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	# --- the DTO ----------------------------------------------------------

	def test_surface_dto_is_keyed_by_content_key(self):
		make_block()

		dto = block_service.surface_dto(PUBLIC_SURFACE)

		self.assertIn(TEST_KEY, dto)
		self.assertEqual(dto[TEST_KEY]["text"], "Original wording")

	def test_dto_carries_only_the_reviewed_fields(self):
		"""An explicit DTO, so a schema change is never silently an API change."""
		make_block()

		row = block_service.surface_dto(PUBLIC_SURFACE)[TEST_KEY]

		self.assertEqual(
			set(row.keys()),
			{"key", "label", "text", "href", "image", "image_alt", "image_credit"},
		)

	# --- seeding ----------------------------------------------------------

	def test_seed_creates_what_is_missing(self):
		key = "content-test.seeded.new"
		frappe.delete_doc(BLOCK_DOCTYPE, key, force=True, ignore_missing=True)

		report = block_service.seed(
			[{"content_key": key, "label": "Seeded", "surface": PUBLIC_SURFACE, "text_value": "Hello"}]
		)

		self.assertEqual(report["created"], 1)
		self.assertTrue(frappe.db.exists(BLOCK_DOCTYPE, key))

	def test_seed_never_overwrites_an_edited_slot(self):
		"""The promise that lets `setup_content_module` run on every migrate."""
		make_block(text_value="What the society wrote")

		report = block_service.seed(
			[
				{
					"content_key": TEST_KEY,
					"label": "A test slot",
					"surface": PUBLIC_SURFACE,
					"text_value": "The shipped default",
				}
			]
		)

		self.assertEqual(report["created"], 0)
		self.assertEqual(report["existed"], 1)
		self.assertEqual(frappe.db.get_value(BLOCK_DOCTYPE, TEST_KEY, "text_value"), "What the society wrote")

	def test_overwrite_does_what_seed_will_not(self):
		"""The Kenya seed's path: run deliberately, get the worked example."""
		make_block(text_value="What the society wrote")

		block_service.overwrite([{"content_key": TEST_KEY, "text_value": "The Kenya wording"}])

		self.assertEqual(frappe.db.get_value(BLOCK_DOCTYPE, TEST_KEY, "text_value"), "The Kenya wording")

	# --- writing ----------------------------------------------------------

	def test_a_partial_write_leaves_the_other_fields_alone(self):
		"""The pencil beside a caption sends a caption, and nothing else moves."""
		make_block(image="/files/somewhere.jpg", image_credit="A photographer")

		block_service.write_block(TEST_KEY, text_value="Reworded")

		row = block_service.surface_dto(PUBLIC_SURFACE)[TEST_KEY]
		self.assertEqual(row["text"], "Reworded")
		self.assertEqual(row["image"], "/files/somewhere.jpg")
		self.assertEqual(row["image_credit"], "A photographer")

	def test_a_field_outside_the_editable_set_is_ignored(self):
		make_block()

		block_service.write_block(TEST_KEY, label="Renamed by a caller", text_value="Reworded")

		self.assertEqual(frappe.db.get_value(BLOCK_DOCTYPE, TEST_KEY, "label"), "A test slot")

	# --- links ------------------------------------------------------------

	def test_a_javascript_uri_is_refused(self):
		make_block()

		with self.assertRaises(frappe.ValidationError):
			block_service.write_block(TEST_KEY, link_href="javascript:alert(1)")

	def test_a_data_uri_is_refused(self):
		make_block()

		with self.assertRaises(frappe.ValidationError):
			block_service.write_block(TEST_KEY, link_href="data:text/html;base64,PHNjcmlwdD4=")

	def test_ordinary_destinations_are_accepted(self):
		make_block()

		for href in ("/portal/join", "#events", "https://example.org", "mailto:a@b.c", "tel:+100"):
			block_service.write_block(TEST_KEY, link_href=href)
			self.assertEqual(frappe.db.get_value(BLOCK_DOCTYPE, TEST_KEY, "link_href"), href)

	def test_a_protocol_relative_link_is_refused(self):
		"""`//evil.example` inherits the page's scheme and leaves the site."""
		make_block()

		with self.assertRaises(frappe.ValidationError):
			block_service.write_block(TEST_KEY, link_href="//evil.example/phish")


class TestContentApi(IntegrationTestCase):
	def setUp(self):
		make_surface(PUBLIC_SURFACE, public=True)
		make_surface(PRIVATE_SURFACE, public=False)
		make_block(key=TEST_KEY, surface=PUBLIC_SURFACE)
		make_block(key="content-test.private.one", surface=PRIVATE_SURFACE)
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_a_guest_may_read_a_public_surface(self):
		frappe.set_user("Guest")

		result = content_api.surface(PUBLIC_SURFACE)

		self.assertIn(TEST_KEY, result["blocks"])
		self.assertFalse(result["can_edit"])

	def test_a_guest_may_not_read_a_private_surface(self):
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			content_api.surface(PRIVATE_SURFACE)

	def test_a_private_surface_cannot_ride_along_with_a_public_one(self):
		"""Every named surface is checked, not just the first."""
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			content_api.surface(f"{PUBLIC_SURFACE},{PRIVATE_SURFACE}")

	def test_several_surfaces_merge_into_one_dictionary(self):
		result = content_api.surface(f"{PUBLIC_SURFACE},{PRIVATE_SURFACE}")

		self.assertIn(TEST_KEY, result["blocks"])
		self.assertIn("content-test.private.one", result["blocks"])

	def test_a_guest_may_not_enumerate_the_catalogue(self):
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			content_api.catalogue()

	def test_an_administrator_may_edit(self):
		result = content_api.surface(PUBLIC_SURFACE)

		self.assertTrue(result["can_edit"])

	def test_update_block_returns_the_slot_as_it_now_reads(self):
		row = content_api.update_block(TEST_KEY, text_value="Changed through the API")

		self.assertEqual(row["text"], "Changed through the API")
		self.assertEqual(row["key"], TEST_KEY)
