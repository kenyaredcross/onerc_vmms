# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""No source file branches on a stage name.

States are code; **stages are configuration**. The moment one source file says
`if stage.stage_label == "County Approval"`, the engine has stopped being
generic: a society that renames the stage breaks the software, and a society
that adds one has to wait for a developer. That is precisely the trap this whole
design exists to avoid, and it is the kind of line that gets added innocently,
under deadline, in a hurry.

So it is asserted rather than remembered. Every `.py` file in the app is parsed
and its syntax tree walked for two offences:

1. a **comparison** whose operand is a stage's label — `==`, `!=`, `in`, or a
   `match` on one;
2. a **string literal** equal to a stage label a society configured in these
   tests, anywhere outside a docstring.

Prose may name a stage: docstrings explain, they do not execute, and comments
are not in the tree at all. Code may not.

The detector is itself tested against a snippet that *does* branch on a label —
a scanner that finds nothing because it is broken looks exactly like a clean
codebase.
"""

import ast
from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.approvals.services import contract
from vmmsx.approvals.tests import fixtures

EXTRA_TEST_RECORD_DEPENDENCIES = []

# The tests are excluded: they configure stages, so they name them by
# definition. Everything else in the app is fair game.
EXCLUDED_PARTS = {"tests", "__pycache__"}

LABEL_FIELD = "stage_label"

OFFENDING_SNIPPET = """
def route(stage):
	if stage.stage_label == "County Approval":
		return "the county"

	return "somewhere else"
"""

CLEAN_SNIPPET = """
def route(stage, workflow):
	'''Ordering is by sequence; the label is display only, as in "County Approval".'''
	next_stages = [row for row in workflow.stages if row.sequence > stage.sequence]

	return next_stages[0] if next_stages else None
"""


def source_files() -> list[Path]:
	root = Path(frappe.get_app_path("vmmsx"))

	return sorted(
		path for path in root.rglob("*.py") if not EXCLUDED_PARTS & set(path.relative_to(root).parts)
	)


def offences(source: str, filename: str = "<snippet>") -> list[str]:
	"""Every place this source branches on, or hardcodes, a stage label."""
	tree = ast.parse(source, filename=filename)
	docstrings = _docstring_nodes(tree)
	found = []

	for node in ast.walk(tree):
		if isinstance(node, ast.Compare):
			operands = [node.left, *node.comparators]

			if any(_is_label_reference(operand) for operand in operands):
				found.append(f"{filename}:{node.lineno}: comparison on {LABEL_FIELD}")

		elif isinstance(node, ast.Match) and _is_label_reference(node.subject):
			found.append(f"{filename}:{node.lineno}: match on {LABEL_FIELD}")

		elif isinstance(node, ast.Constant) and isinstance(node.value, str):
			if node.value in fixtures.STAGE_LABELS and node not in docstrings:
				found.append(f"{filename}:{node.lineno}: hardcoded stage label {node.value!r}")

	return found


def _is_label_reference(node) -> bool:
	"""`something.stage_label` or `something["stage_label"]`."""
	if isinstance(node, ast.Attribute):
		return node.attr == LABEL_FIELD

	if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
		return node.slice.value == LABEL_FIELD

	return False


def _docstring_nodes(tree) -> list:
	"""The Constant nodes that are docstrings, so prose is not mistaken for code."""
	nodes = []

	for node in ast.walk(tree):
		if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
			continue

		if not node.body:
			continue

		first = node.body[0]

		if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
			nodes.append(first.value)

	return nodes


class TestTheDetector(IntegrationTestCase):
	"""A scanner that finds nothing because it is broken proves nothing."""

	def test_it_catches_a_comparison_on_a_stage_label(self):
		self.assertTrue(any("comparison" in offence for offence in offences(OFFENDING_SNIPPET)))

	def test_it_catches_a_hardcoded_label(self):
		self.assertTrue(any("hardcoded" in offence for offence in offences(OFFENDING_SNIPPET)))

	def test_it_permits_ordering_by_sequence(self):
		self.assertEqual(offences(CLEAN_SNIPPET), [])

	def test_prose_may_name_a_stage(self):
		"""The clean snippet's docstring names one, and that is allowed."""
		self.assertIn("County Approval", CLEAN_SNIPPET)


class TestTheEngine(IntegrationTestCase):
	def test_no_source_file_branches_on_a_stage_name(self):
		found = []

		for path in source_files():
			found.extend(offences(path.read_text(), str(path)))

		self.assertEqual(found, [], "stages are configuration; nothing may branch on what one is called")

	def test_the_scan_actually_reads_the_engine(self):
		"""Guard against the scan quietly matching nothing at all."""
		scanned = {path.name for path in source_files()}

		self.assertIn("engine.py", scanned)
		self.assertIn("routing.py", scanned)
		self.assertIn("states.py", scanned)

	def test_the_label_field_is_the_one_being_guarded(self):
		"""If the field is ever renamed, this test must be updated with it."""
		self.assertIn(LABEL_FIELD, frappe.get_meta("VMMS Approval Stage").get_valid_columns())
		self.assertEqual(contract.DECISION_DOCTYPE, "VMMS Approval Decision")
