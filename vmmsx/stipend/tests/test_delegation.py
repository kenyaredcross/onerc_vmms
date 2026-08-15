# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Stipend module owns no routing, no geo walk and no society vocabulary.

Rules that are easy to state, easy to believe, and easy to break by accident
under deadline — so they are asserted against the source itself rather than
remembered. This is the bar `member/`, `volunteer/` and `deployment/` are already
held to, with the additions this module needs.

1. **There is no routing here, and there is no half of it either.** Nothing under
   `vmmsx/stipend/` calls core's `resolve_approvers`, and nothing walks Geo
   Assignment. That matters more here than anywhere else in the app: the whole
   point of the stub is that stipend approval has *no* resolver, and the failure
   mode is somebody adding a plausible one that routes up the geo tree to a
   branch coordinator who is not a head of department. See
   `stipend/services/approval.py`.
2. **The approval engine is not imported.** Not even to read a state. These
   doctypes are deliberately outside the engine's contract, and an import would
   be the first step back towards geo routing.
3. **Geo is core's.** Nothing here queries `Geo Node` or `Geo Assignment`; geo
   reaches this module through core's adapter and authority through core's scope
   service.
4. **`get_user_geo_scope` has exactly one caller, and it is the picker.** The
   picker is a service that *returns* people, so it has to ask the question
   itself. One caller is defensible; two is the beginning of a second scope
   model, and the scan below fails on the second.
5. **There is no shadow approval.** No file here decides that somebody may
   approve because they hold a role. That is the mistake Frappe's native Workflow
   makes, and it is one `if` away at all times.
6. **No society vocabulary is written down.** Not a role name, not a geo level
   name, not a currency code, and not a department. Each of those is checked
   against what this *site* actually holds, so the assertion is about real names
   a real society configured rather than a list somebody typed.

The scan walks the AST for calls and attribute names, and the raw text for
doctype names and vocabulary, because a `frappe.get_all("Geo Assignment", ...)`
is a string argument rather than an identifier. Docstrings are stripped before
the text checks: prose is allowed to explain what is absent, and a scan that
flagged the sentence saying so would be unusable.
"""

import ast
from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

PACKAGE = "stipend"
EXCLUDED_PARTS = {"tests", "__pycache__"}

# Names that would mean this module had grown its own resolver.
FORBIDDEN_CALLS = ("resolve_approvers",)

# Doctypes this module may not query directly.
FORBIDDEN_DOCTYPES = ("Geo Assignment", "tabGeo Assignment", "tabGeo Node", "Geo Node")

# The one call that is permitted in exactly one file, and the file.
SCOPE_CALL = "get_user_geo_scope"
SCOPE_CALLER = "picker.py"

# What a shadow approval looks like: deciding authority from role membership
# rather than from who this document routed to.
ROLE_CHECK_CALLS = ("get_roles", "has_role")

# The approval engine package, which this module deliberately does not use at
# all — not the engine, not the states, not the contract.
ENGINE_PACKAGE = "vmmsx.approvals"

OFFENDING_SNIPPET = """
def approve(doc):
	from onerc_core.access.services.approvers import resolve_approvers

	return resolve_approvers(doc.geo_node, "Some Role", "nearest_ancestor")
"""

CLEAN_SNIPPET = """
def approve(doc):
	'''Refuses: departmental routing does not exist, so resolve_approvers is not called.'''
	raise NotImplementedError
"""


def module_files(package: str) -> list[Path]:
	root = Path(frappe.get_app_path("vmmsx")) / package

	return sorted(
		path for path in root.rglob("*.py") if not EXCLUDED_PARTS & set(path.relative_to(root).parts)
	)


def _code_only(source: str) -> str:
	"""The source with every docstring removed.

	Prose explains what this module does not do, and naming the thing it does not
	do is the clearest way to explain it. Only code is scanned.
	"""
	tree = ast.parse(source)
	spans = []

	for node in ast.walk(tree):
		if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
			continue

		body = getattr(node, "body", None)

		if not body:
			continue

		first = body[0]

		if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
			if isinstance(first.value.value, str):
				spans.append((first.lineno, first.end_lineno))

	lines = source.splitlines()
	kept = [
		line
		for number, line in enumerate(lines, start=1)
		if not any(start <= number <= end for start, end in spans)
	]

	return "\n".join(kept)


def _called_names(tree: ast.AST) -> list[str]:
	"""Every function name called anywhere in the tree, however it was reached."""
	names = []

	for node in ast.walk(tree):
		if not isinstance(node, ast.Call):
			continue

		func = node.func

		if isinstance(func, ast.Name):
			names.append(func.id)
		elif isinstance(func, ast.Attribute):
			names.append(func.attr)

	return names


class DelegationTestCase(IntegrationTestCase):
	def code_of(self, path: Path) -> str:
		return _code_only(path.read_text())

	def tree_of(self, path: Path):
		return ast.parse(path.read_text(), filename=str(path))


class TestThereIsNoRoutingHere(DelegationTestCase):
	def test_nothing_resolves_an_approver(self):
		offenders = []

		for path in module_files(PACKAGE):
			called = _called_names(self.tree_of(path))

			for name in FORBIDDEN_CALLS:
				if name in called:
					offenders.append(f"{path.name}: {name}")

		self.assertEqual(
			offenders, [], "the stipend module has grown a resolver; the whole stub says it must not"
		)

	def test_the_detector_finds_a_resolver_that_is_there(self):
		"""A scanner that finds nothing because it is broken looks exactly like clean code."""
		self.assertIn("resolve_approvers", _called_names(ast.parse(OFFENDING_SNIPPET)))
		self.assertNotIn("resolve_approvers", _called_names(ast.parse(CLEAN_SNIPPET)))

	def test_the_approval_engine_is_not_imported(self):
		offenders = [path.name for path in module_files(PACKAGE) if ENGINE_PACKAGE in self.code_of(path)]

		self.assertEqual(offenders, [], "the stipend module has reached for the geo approval engine")

	def test_no_file_here_decides_authority_from_a_role(self):
		"""A shadow approval is one `if` away at all times."""
		offenders = []

		for path in module_files(PACKAGE):
			called = _called_names(self.tree_of(path))

			for name in ROLE_CHECK_CALLS:
				if name in called:
					offenders.append(f"{path.name}: {name}")

		self.assertEqual(offenders, [], "authority is being read from role membership")


class TestGeoIsCores(DelegationTestCase):
	def test_no_file_queries_geo_directly(self):
		offenders = []

		for path in module_files(PACKAGE):
			code = self.code_of(path)

			for doctype in FORBIDDEN_DOCTYPES:
				if f'"{doctype}"' in code or f"'{doctype}'" in code:
					offenders.append(f"{path.name}: {doctype}")

		self.assertEqual(offenders, [], "geo is reached through core's adapter, never queried here")

	def test_the_scope_service_has_exactly_one_caller(self):
		callers = [
			path.name for path in module_files(PACKAGE) if SCOPE_CALL in _called_names(self.tree_of(path))
		]

		self.assertEqual(
			callers,
			[SCOPE_CALLER],
			f"{SCOPE_CALL} belongs in {SCOPE_CALLER} alone; a second caller is a second scope model",
		)


class TestNoSocietyVocabularyIsWrittenDown(DelegationTestCase):
	"""Checked against what this site holds, not against a list somebody typed."""

	def code(self) -> dict[str, str]:
		return {path.name: self.code_of(path) for path in module_files(PACKAGE)}

	def assert_absent(self, values, what: str):
		"""No value in `values` appears as a string literal in this module's code.

		Matched with its quotes, so this is about a name being *written down* rather
		than about the letters occurring somewhere inside a longer identifier.
		"""
		names = [value for value in values if value]
		offenders = []

		for filename, code in self.code().items():
			for value in names:
				if f'"{value}"' in code or f"'{value}'" in code:
					offenders.append(f"{filename}: {value}")

		self.assertEqual(offenders, [], f"a {what} is written into the stipend module's source")

	def names_on_site(self, doctype: str, field: str = "name") -> list[str]:
		if not frappe.db.exists("DocType", doctype):
			self.skipTest(f"{doctype} is not installed on this site")

		return frappe.get_all(doctype, pluck=field)

	def test_no_role_name_appears(self):
		"""Approvals resolve against a role a society named, never one written here."""
		self.assert_absent(self.names_on_site("Role"), "role name")

	def test_no_geo_level_name_appears(self):
		"""ACC-03: the anchor level is configuration, and no depth is assumed."""
		self.assert_absent(self.names_on_site("Geo Level", "geo_level_name"), "geo level name")

	def test_no_currency_code_appears(self):
		"""The society's currency is read, never named."""
		self.assert_absent(self.names_on_site("Currency"), "currency code")

	def test_no_department_name_appears(self):
		"""The routing target is captured and displayed. Nothing branches on it."""
		self.assert_absent(self.names_on_site("Department"), "department name")

	def test_the_detector_finds_a_name_that_is_there(self):
		"""Proof the scan is capable of failing."""
		sample = frappe.get_all("Role", pluck="name", limit=1)

		if not sample:
			self.skipTest("no roles on this site to prove the detector with")

		leaked = f'def f():\n\treturn "{sample[0]}"\n'

		self.assertIn(f'"{sample[0]}"', _code_only(leaked))
