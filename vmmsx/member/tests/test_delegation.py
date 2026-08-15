# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Member module owns no routing, no geo query and no gateway.

Three rules that are easy to state, easy to believe, and easy to break by
accident under deadline — so they are asserted against the source itself rather
than remembered:

1. **Routing is the approval engine's.** Nothing under `vmmsx/member/` calls
   core's `resolve_approvers`. If it did, there would be two resolvers, and the
   day they disagreed memberships would route to people who cannot open them.
2. **Geo is core's.** Nothing here queries `Geo Node` or `Geo Assignment`. Geo
   reaches this module only through core's adapter, and authority only through
   the engine.
3. **Money is the payments app's.** No gateway name, no STK push, no shortcode
   appears anywhere in the module. Swapping M-Pesa for a bank transfer is a
   setting in another app.

The scan walks the AST for calls and attribute names, and the raw text for the
table and vocabulary names, because a `frappe.get_all("Geo Assignment", ...)` is
a string argument rather than an identifier.
"""

import ast
from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

EXCLUDED_PARTS = {"tests", "__pycache__"}

# Names that would mean this module had grown its own resolver.
FORBIDDEN_CALLS = ("resolve_approvers", "get_user_geo_scope")

# Doctypes this module may not query directly. Geo Node is core's and reached
# through the adapter; Geo Assignment is authority, and the engine's business.
FORBIDDEN_DOCTYPES = ("Geo Assignment", "tabGeo Assignment", "tabGeo Node")

# Gateway vocabulary. If any of this appears here, the payment seam has leaked.
FORBIDDEN_GATEWAY_TERMS = (
	"mpesa",
	"daraja",
	"stk",
	"shortcode",
	"safaricom",
	"passkey",
	"checkout_request_id",
)


def module_files(package: str) -> list[Path]:
	root = Path(frappe.get_app_path("vmmsx")) / package

	return sorted(
		path for path in root.rglob("*.py") if not EXCLUDED_PARTS & set(path.relative_to(root).parts)
	)


def called_names(source: str) -> set[str]:
	"""Every function and attribute name the source calls."""
	tree = ast.parse(source)
	names = set()

	for node in ast.walk(tree):
		if isinstance(node, ast.Call):
			func = node.func

			if isinstance(func, ast.Name):
				names.add(func.id)
			elif isinstance(func, ast.Attribute):
				names.add(func.attr)

		elif isinstance(node, ast.ImportFrom):
			for alias in node.names:
				names.add(alias.name)

	return names


class TestRoutingIsDelegated(IntegrationTestCase):
	def test_the_scan_actually_reads_the_module(self):
		"""A scan matching nothing at all would pass every test below."""
		scanned = {path.name for path in module_files("member")}

		self.assertIn("approval.py", scanned)
		self.assertIn("membership.py", scanned)
		self.assertIn("payment.py", scanned)

	def test_no_file_resolves_approvers_itself(self):
		offenders = []

		for path in module_files("member"):
			names = called_names(path.read_text())

			for forbidden in FORBIDDEN_CALLS:
				if forbidden in names:
					offenders.append(f"{path.name}: {forbidden}")

		self.assertEqual(
			offenders, [], "routing belongs to the approval engine; this module must delegate to it"
		)

	def test_no_file_queries_geo_or_authority_directly(self):
		offenders = []

		for path in module_files("member"):
			text = path.read_text()

			for doctype in FORBIDDEN_DOCTYPES:
				if f'"{doctype}"' in text or f"'{doctype}'" in text:
					offenders.append(f"{path.name}: {doctype}")

		self.assertEqual(offenders, [], "geo is core's, reached through the adapter")

	def test_no_gateway_vocabulary_leaked_into_the_module(self):
		offenders = []

		for path in module_files("member"):
			# Docstrings are stripped first. The prose in payment.py says "no STK
			# push, no shortcode" precisely to record that they are absent, and a
			# scan that flagged the sentence saying so would be unusable.
			code = _code_only(path.read_text()).lower()

			for term in FORBIDDEN_GATEWAY_TERMS:
				if term in code:
					offenders.append(f"{path.name}: {term}")

		self.assertEqual(offenders, [], "all money goes through onerc_payments; no driver is named here")

	def test_the_scan_would_catch_a_leak_that_was_really_there(self):
		"""A scanner that finds nothing because it is broken proves nothing."""
		leaked = 'def pay():\n\t"""Prose may say mpesa."""\n\tgateway = "mpesa_daraja"\n'
		clean = 'def pay():\n\t"""Prose may say mpesa and shortcode freely."""\n\treturn 1\n'

		self.assertIn("mpesa", _code_only(leaked).lower())
		self.assertNotIn("mpesa", _code_only(clean).lower())

	def test_the_templating_package_knows_nothing_about_members(self):
		"""The shared renderer is shared, not a certificate function in disguise."""
		offenders = []

		for path in module_files("templating"):
			# Prose may explain what the first consumer is; code may not name
			# it. Docstrings are stripped before looking.
			code = _code_only(path.read_text()).lower()

			for term in ("member", "membership", "certificate"):
				if term in code:
					offenders.append(f"{path.name}: {term}")

		self.assertEqual(offenders, [], "vmmsx/templating must not know what a membership is")


def _code_only(source: str) -> str:
	"""The source with docstrings and comments removed.

	Prose is allowed to name the first consumer — that is documentation. Code is
	not, because code that names it has coupled to it.
	"""
	tree = ast.parse(source)
	docstrings = set()

	for node in ast.walk(tree):
		if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
			continue

		if node.body and isinstance(node.body[0], ast.Expr):
			value = node.body[0].value

			if isinstance(value, ast.Constant) and isinstance(value.value, str):
				docstrings.add(id(value))

	class StripDocstrings(ast.NodeTransformer):
		def visit_Expr(self, node):
			if isinstance(node.value, ast.Constant) and id(node.value) in docstrings:
				return None

			return node

	return ast.unparse(StripDocstrings().visit(tree))
