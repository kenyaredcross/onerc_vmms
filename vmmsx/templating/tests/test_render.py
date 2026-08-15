# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The shared render service — generic, config-driven, and sandboxed.

These tests deliberately use no membership at all. The renderer is shared
infrastructure that volunteer agreements and notifications will reuse, so it is
proven against contexts it invents on the spot: if a test here needed a
membership, the renderer would not be generic.

The sandbox tests are the ones that matter most. A template body is written by a
society administrator through the desk, which makes it untrusted input running
on the server. Frappe's Jinja environment is a `SandboxedEnvironment`, and these
assert that the classic escape — walking `__class__` / `__mro__` /
`__subclasses__` from any object to reach the interpreter — is refused rather
than executed.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.templating.services import render

EXTRA_TEST_RECORD_DEPENDENCIES = []

TEMPLATE_DOCTYPE = "VMMS Template"
TEST_KEY = "TEMPLATING-TEST-generic"
CATEGORY_KEY = "certificate"


def make_template(key: str = TEST_KEY, **overrides):
	if frappe.db.exists(TEMPLATE_DOCTYPE, key):
		frappe.delete_doc(TEMPLATE_DOCTYPE, key, force=True)

	values = {
		"doctype": TEMPLATE_DOCTYPE,
		"template_key": key,
		"template_name": "Generic Test Template",
		"template_category": CATEGORY_KEY,
		"subject": "Hello {{ who }}",
		"body": "Dear {{ who }}, you are {{ role }}.",
		"output_format": "html",
		"is_active": 1,
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


class TestRenderService(IntegrationTestCase):
	def tearDown(self):
		super().tearDown()

		for key in (TEST_KEY, f"{TEST_KEY}-alt"):
			if frappe.db.exists(TEMPLATE_DOCTYPE, key):
				frappe.delete_doc(TEMPLATE_DOCTYPE, key, force=True)

	def test_it_renders_a_configured_template_against_a_context(self):
		make_template()
		result = render.render_template(TEST_KEY, {"who": "Amina", "role": "a volunteer"})

		self.assertEqual(result["body"], "Dear Amina, you are a volunteer.")
		self.assertEqual(result["subject"], "Hello Amina")

	def test_the_result_is_an_explicit_dict_not_a_document(self):
		make_template()
		result = render.render_template(TEST_KEY, {"who": "X", "role": "y"})

		self.assertEqual(
			sorted(result), ["body", "category", "format", "subject", "template_key", "template_name"]
		)
		self.assertNotIsInstance(result, frappe.model.document.Document)

	def test_editing_the_template_changes_the_output_with_no_code_change(self):
		"""The whole reason the body is configuration."""
		make_template()
		first = render.render_template(TEST_KEY, {"who": "Amina", "role": "a member"})

		template = frappe.get_doc(TEMPLATE_DOCTYPE, TEST_KEY)
		template.body = "{{ who }} — {{ role }} — revised wording"
		template.save()
		frappe.clear_document_cache(TEMPLATE_DOCTYPE, TEST_KEY)

		second = render.render_template(TEST_KEY, {"who": "Amina", "role": "a member"})

		self.assertNotEqual(first["body"], second["body"])
		self.assertEqual(second["body"], "Amina — a member — revised wording")

	def test_the_category_is_returned_as_data_and_never_acted_on(self):
		"""Two templates, different categories, identical treatment."""
		make_template()
		make_template(f"{TEST_KEY}-alt", template_category="notification")

		one = render.render_template(TEST_KEY, {"who": "A", "role": "b"})
		two = render.render_template(f"{TEST_KEY}-alt", {"who": "A", "role": "b"})

		self.assertEqual(one["category"], CATEGORY_KEY)
		self.assertEqual(two["category"], "notification")
		# Same context, same body template, same output — the category changed
		# nothing about how it was rendered.
		self.assertEqual(one["body"], two["body"])

	def test_an_unknown_template_key_is_refused(self):
		with self.assertRaises(frappe.DoesNotExistError):
			render.render_template("no-such-template-key", {})

	def test_an_inactive_template_refuses_to_render(self):
		make_template(is_active=0)

		with self.assertRaises(frappe.ValidationError):
			render.render_template(TEST_KEY, {})

	def test_a_missing_context_key_does_not_throw(self):
		"""An administrator editing a template should see the gap, not a traceback."""
		make_template()
		result = render.render_template(TEST_KEY, {"who": "Amina"})

		self.assertIn("Amina", result["body"])

	def test_it_knows_nothing_about_any_domain(self):
		"""Rendered with a context this test invented. No membership involved."""
		make_template(body="{{ animal }} weighs {{ kilos }}kg")
		result = render.render_template(TEST_KEY, {"animal": "Elephant", "kilos": 4000})

		self.assertEqual(result["body"], "Elephant weighs 4000kg")


class TestTheSandbox(IntegrationTestCase):
	"""A template is untrusted input. Code execution must be neutralised."""

	def tearDown(self):
		super().tearDown()

		if frappe.db.exists(TEMPLATE_DOCTYPE, TEST_KEY):
			frappe.delete_doc(TEMPLATE_DOCTYPE, TEST_KEY, force=True)

	# The classic Jinja escapes: walk from any object to the interpreter.
	ESCAPES = (
		"{{ ''.__class__.__mro__[1].__subclasses__() }}",
		"{{ ''.__class__.__base__.__subclasses__() }}",
		"{{ [].__class__.__base__.__subclasses__() }}",
		"{{ ().__class__.__bases__[0].__subclasses__() }}",
		"{{ config.__class__.__init__.__globals__ }}",
	)

	def test_every_escape_attempt_is_refused(self):
		for attempt in self.ESCAPES:
			with self.assertRaises(frappe.PermissionError, msg=f"{attempt} was not refused"):
				render.render_string(attempt, {})

	def test_the_escape_does_not_execute_before_it_is_refused(self):
		"""Refused, not half-run: no output comes back at all."""
		result = None

		try:
			result = render.render_string(self.ESCAPES[0], {})
		except frappe.PermissionError:
			pass

		self.assertIsNone(result)

	def test_a_saved_template_containing_an_escape_is_refused_at_save_time(self):
		"""Caught while the author is still looking at the form."""
		with self.assertRaises(frappe.PermissionError):
			make_template(body=self.ESCAPES[0])

		self.assertFalse(frappe.db.exists(TEMPLATE_DOCTYPE, TEST_KEY))

	def test_ordinary_templates_still_render(self):
		"""The sandbox refuses escapes, not Jinja itself."""
		body = "{% for item in items %}{{ item|upper }} {% endfor %}"

		self.assertEqual(render.render_string(body, {"items": ["a", "b"]}).strip(), "A B")

	def test_a_template_cannot_reach_the_database_through_an_escape(self):
		"""The escape that would matter most: reading records it was not given."""
		attempt = "{{ ''.__class__.__mro__[1].__subclasses__() }}"

		with self.assertRaises(frappe.PermissionError):
			render.render_string(attempt, {})

	def test_the_attr_filter_route_is_refused_too(self):
		"""An escape does not have to be written with a dot.

		`{{ ''|attr('__class__') }}` reaches the same place without `.__`, which
		is what Frappe's own guard screens for. This module's screen looks for
		the dunder anywhere in the body, so both spellings are refused.
		"""
		with self.assertRaises(frappe.PermissionError):
			render.render_string("{{ ''|attr('__class__') }}", {})

	def test_context_values_are_still_usable_normally(self):
		"""Refusing escapes must not break ordinary reads of the same objects."""
		self.assertEqual(render.render_string("{{ mapping.a }}", {"mapping": {"a": 1}}), "1")
		self.assertEqual(render.render_string("{{ items|length }}", {"items": [1, 2, 3]}), "3")

	def test_broken_syntax_is_an_error_not_a_refusal(self):
		"""The two failures are told apart, because they mean different things."""
		with self.assertRaises(frappe.ValidationError):
			render.render_string("{% for x in %}", {})


class TestTheSeededDefault(IntegrationTestCase):
	"""The shipped membership certificate exists, works, and is editable."""

	def test_it_was_seeded_by_the_patch(self):
		self.assertTrue(frappe.db.exists(TEMPLATE_DOCTYPE, "membership_certificate"))

	def test_its_body_is_not_hardcoded_in_python(self):
		"""Seeded from a file into a record. No Python file holds the wording."""
		import ast
		from pathlib import Path

		patch = Path(frappe.get_app_path("vmmsx")) / "patches" / "setup_member_module.py"
		tree = ast.parse(patch.read_text())

		for node in ast.walk(tree):
			if isinstance(node, ast.Constant) and isinstance(node.value, str):
				self.assertNotIn(
					"Certificate of Membership</", node.value, "template markup belongs in a seed file"
				)

	def test_it_renders_with_a_membership_shaped_context(self):
		result = render.render_template(
			"membership_certificate",
			{
				"member_name": "Amina Otieno",
				"membership_type": "Life",
				"geo_path": "Highland > Meru",
				"membership_id": "MSHIP-00001",
				"valid_from": "2026-01-01",
				"valid_to": "2026-12-31",
				"issued_on": "2026-01-01",
				"society_name": "Test Society",
				"benefits": ["Clinic access"],
			},
		)

		self.assertIn("Amina Otieno", result["body"])
		self.assertIn("Life", result["body"])

	def test_it_renders_without_a_receipt(self):
		"""A society on the Manual driver may never have one."""
		result = render.render_template(
			"membership_certificate",
			{"member_name": "No Receipt", "membership_type": "Ordinary", "geo_path": "X"},
		)

		self.assertIn("No Receipt", result["body"])
		self.assertNotIn("Receipt</td>", result["body"])
