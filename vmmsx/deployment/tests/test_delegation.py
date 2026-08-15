# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Deployment module owns no routing, no geo walk and no second approval.

Four rules that are easy to state, easy to believe, and easy to break by
accident under deadline — so they are asserted against the source itself rather
than remembered. This is the same bar `member/tests/test_delegation.py` and
`volunteer/tests/test_delegation.py` hold their modules to, with one addition
this module needs and they did not.

1. **Routing is the approval engine's.** Nothing under `vmmsx/deployment/` calls
   core's `resolve_approvers`, and nothing walks Geo Assignment. If it did,
   there would be two resolvers, and the day they disagreed a deployment request
   would route to people who cannot open it.
2. **Geo is core's.** Nothing here queries `Geo Node` or `Geo Assignment`. Geo
   reaches this module only through core's adapter, and authority only through
   the engine or core's scope service.
3. **There is no shadow approval.** No file here decides that somebody may
   approve because they hold a role. That is the mistake Frappe's native
   Workflow makes and the reason this app does not use it, and it is one `if`
   away at all times.
4. **`get_user_geo_scope` has exactly one caller, and it is matching.** This is
   the addition. The other product modules may not call it at all, because their
   access is core's enforcement layers doing the asking. Matching is different:
   it is a service that *returns* people, so it has to ask the question itself.
   One caller is defensible; two is the beginning of a second scope model, and
   the scan below fails on the second.

The scan walks the AST for calls and attribute names, and the raw text for
doctype names, because a `frappe.get_all("Geo Assignment", ...)` is a string
argument rather than an identifier. Docstrings are stripped before the text
checks: prose is allowed to explain what is absent, and a scan that flagged the
sentence saying so would be unusable.
"""

import ast
from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

EXCLUDED_PARTS = {"tests", "__pycache__"}

# Names that would mean this module had grown its own resolver.
FORBIDDEN_CALLS = ("resolve_approvers",)

# Doctypes this module may not query directly. Geo Node is core's and reached
# through the adapter; Geo Assignment is authority, and the engine's business.
FORBIDDEN_DOCTYPES = ("Geo Assignment", "tabGeo Assignment", "tabGeo Node", "Geo Node")

# The one call that is permitted in exactly one file, and the file.
SCOPE_CALL = "get_user_geo_scope"
SCOPE_CALLER = "matching.py"

# What a shadow approval looks like: deciding authority from role membership
# rather than from who this document routed to.
ROLE_CHECK_CALLS = ("get_roles", "has_role")


def module_files(package: str) -> list[Path]:
	root = Path(frappe.get_app_path("vmmsx")) / package

	return sorted(
		path for path in root.rglob("*.py") if not EXCLUDED_PARTS & set(path.relative_to(root).parts)
	)


def called_names(source: str) -> set[str]:
	"""Every function and attribute name the source calls, plus what it imports."""
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


def _code_only(source: str) -> str:
	"""The source with docstrings removed.

	Prose is allowed to name what the module deliberately does not touch — that
	is documentation. Code is not, because code that names it has coupled to it.
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


class TestTheScanIsReal(IntegrationTestCase):
	def test_the_scan_actually_reads_the_module(self):
		"""A scan matching nothing at all would pass every test below."""
		scanned = {path.name for path in module_files("deployment")}

		for expected in (
			"deployment.py",
			"participation.py",
			"matching.py",
			"request.py",
			"transfer.py",
			"approval.py",
			"terms.py",
			"society.py",
		):
			self.assertIn(expected, scanned)

	def test_the_scanner_would_catch_a_leak_that_was_really_there(self):
		leaked = 'def f():\n\t"""Prose may say Geo Assignment."""\n\tx = "Geo Assignment"\n\treturn x\n'
		clean = 'def f():\n\t"""Prose may say Geo Assignment freely."""\n\treturn 1\n'

		self.assertIn("Geo Assignment", _code_only(leaked))
		self.assertNotIn("Geo Assignment", _code_only(clean))

	def test_the_call_scanner_sees_a_call_that_is_really_there(self):
		self.assertIn("resolve_approvers", called_names("resolve_approvers(1, 2)"))
		self.assertNotIn("resolve_approvers", called_names("x = 1"))


class TestRoutingIsDelegated(IntegrationTestCase):
	def test_no_file_resolves_approvers_itself(self):
		offenders = []

		for path in module_files("deployment"):
			names = called_names(path.read_text())

			for forbidden in FORBIDDEN_CALLS:
				if forbidden in names:
					offenders.append(f"{path.name}: {forbidden}")

		self.assertEqual(
			offenders, [], "routing belongs to the approval engine; this module must delegate to it"
		)

	def test_no_file_queries_geo_or_authority_directly(self):
		offenders = []

		for path in module_files("deployment"):
			code = _code_only(path.read_text())

			for doctype in FORBIDDEN_DOCTYPES:
				if f'"{doctype}"' in code or f"'{doctype}'" in code:
					offenders.append(f"{path.name}: {doctype}")

		self.assertEqual(offenders, [], "geo is core's, reached through the adapter")

	def test_geo_arrives_only_through_cores_adapter(self):
		"""The positive half: this module does read geo, and only one way.

		Without this, the two tests above would also pass for a module that had
		quietly stopped using geo at all.
		"""
		importers = [
			path.name for path in module_files("deployment") if "onerc_core.geo.services" in path.read_text()
		]

		self.assertTrue(importers, "no file reads geo at all — the delegation tests prove nothing")

	def test_the_api_layer_delegates_too(self):
		"""The endpoints are as much a place to grow a resolver as the services are."""
		source = (Path(frappe.get_app_path("vmmsx")) / "api" / "deployment.py").read_text()
		names = called_names(source)

		self.assertNotIn("resolve_approvers", names)
		self.assertNotIn(SCOPE_CALL, names)


class TestTheScopeQuestionHasOneCaller(IntegrationTestCase):
	def test_only_matching_asks_core_for_a_scope_set(self):
		"""One caller is a service that returns people. Two is a second scope model."""
		callers = [
			path.name for path in module_files("deployment") if SCOPE_CALL in called_names(path.read_text())
		]

		self.assertEqual(callers, [SCOPE_CALLER])

	def test_matching_does_ask(self):
		"""Guards the test above: the exemption is exempting something real."""
		seam = [path for path in module_files("deployment") if path.name == SCOPE_CALLER]

		self.assertEqual(len(seam), 1)
		self.assertIn(SCOPE_CALL, called_names(seam[0].read_text()))

	def test_matching_resolves_the_role_through_cores_registry(self):
		"""And never names one. The role is the society's, resolved by core."""
		source = (Path(frappe.get_app_path("vmmsx")) / "deployment" / "services" / "matching.py").read_text()
		names = called_names(source)

		self.assertIn("resolve_role", names)
		self.assertIn("for_doctype", names)


class TestThereIsNoShadowApproval(IntegrationTestCase):
	def test_no_file_decides_authority_from_role_membership(self):
		"""Holding a role is not being the person a document routed to.

		This is the whole reason the app does not use Frappe's native Workflow,
		and it is the mistake somebody would make while wiring a second approval
		path into this module.
		"""
		offenders = []

		for path in module_files("deployment"):
			names = called_names(path.read_text())

			for forbidden in ROLE_CHECK_CALLS:
				if forbidden in names:
					offenders.append(f"{path.name}: {forbidden}")

		self.assertEqual(offenders, [], "authority is the engine's person-gate, not role membership")

	def test_the_approval_state_is_only_ever_written_by_the_engine(self):
		"""No file here sets the contract's fields. It calls the engine, which does."""
		offenders = []

		for path in module_files("deployment"):
			code = _code_only(path.read_text())

			for field in ("approval_state", "approval_stage", "approval_stage_entered_on"):
				if f".{field} =" in code or f'"{field}"' in code:
					offenders.append(f"{path.name}: {field}")

		self.assertEqual(offenders, [], "the approval fields belong to the engine")

	def test_both_gated_doctypes_go_through_the_one_engine(self):
		"""The positive half: they are gated, and by the engine that already exists."""
		callers = [
			path.name for path in module_files("deployment") if "vmmsx.approvals.services" in path.read_text()
		]

		self.assertIn("approval.py", callers)


class TestTheApprovalEngineIsNotReimplemented(IntegrationTestCase):
	def test_no_file_branches_on_an_approval_stage_label(self):
		"""The engine's own rule, restated for its fourth and fifth consumers.

		`approvals/tests/test_no_stage_branching.py` already walks every source
		file in the app, so this asserts the scan covers this module's files
		rather than repeating the walk — a rule enforced by a test that never
		looked at these files would not be enforced here.
		"""
		from vmmsx.approvals.tests import test_no_stage_branching as scan

		scanned = {Path(path).as_posix() for path in scan.source_files()}
		ours = {path.as_posix() for path in module_files("deployment")}

		self.assertTrue(ours <= scanned, "the stage-branching scan does not cover deployment/")

	def test_no_source_file_names_a_society_role_or_a_geo_level(self):
		"""Roles and levels arrive as configuration, never as literals.

		Asserted against the words the fixtures chose, which are deliberately
		concrete: if any of them appears in the app's source, something that
		should have been read from settings was typed in instead.
		"""
		from vmmsx.deployment.tests import fixtures

		offenders = []
		vocabulary = (
			*fixtures.TEST_ROLES,
			fixtures.CERT_SWIFT_WATER,
			fixtures.TOR_FLOOD,
			"Karura",
			"Limuru",
			"Estuary",
		)

		for path in module_files("deployment"):
			code = _code_only(path.read_text())

			for word in vocabulary:
				if word in code:
					offenders.append(f"{path.name}: {word}")

		self.assertEqual(offenders, [], "a society's own vocabulary has reached a source file")
