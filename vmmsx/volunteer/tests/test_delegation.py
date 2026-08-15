# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Volunteer module owns no routing, no geo, no LMS model and no HR model.

Four rules that are easy to state, easy to believe, and easy to break by
accident under deadline — so they are asserted against the source itself rather
than remembered. This is the same bar `member/tests/test_delegation.py` holds
the Member module to, extended with the two seams this module adds.

1. **Routing is the approval engine's.** Nothing under `vmmsx/volunteer/` calls
   core's `resolve_approvers` or `get_user_geo_scope`. If it did, there would be
   two resolvers, and the day they disagreed applications would route to people
   who cannot open them.
2. **Geo is core's.** Nothing here queries `Geo Node` or `Geo Assignment`. Geo
   reaches this module only through core's adapter, and authority only through
   the engine.
3. **The learning system stops at the seam.** Exactly one file —
   `services/learning.py` — may name an LMS doctype, and everything it knows
   about that system is gathered in one block at the top of it. The only other
   place an LMS doctype is written down in this app is the `doc_events`
   registration in `hooks.py`, which is the seam being plugged in.
4. **HR stops at its seam too, and identity never crosses it.** Exactly one
   file — `services/hr.py` — may name `Employee`, and no file anywhere in the
   module may name HR's employment model: payroll, salary, timesheets,
   attendance, leave. A volunteer is not an employee.

The scan walks the AST for calls and attribute names, and the raw text for
doctype and vocabulary names, because a `frappe.get_all("Geo Assignment", ...)`
is a string argument rather than an identifier. Docstrings are stripped before
the vocabulary checks: prose is allowed to explain what is absent, and a scan
that flagged the sentence saying so would be unusable.
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

# The learning system's vocabulary. Permitted in exactly one file.
LMS_DOCTYPES = (
	"LMS Enrollment",
	"LMS Course",
	"LMS Certificate",
	"LMS Batch",
	"LMS Quiz",
	"Course Lesson",
	"LMS Course Progress",
)
LMS_SEAM_FILE = "learning.py"

# HR's own record, permitted in exactly one file.
HR_DOCTYPES = ("Employee",)
HR_SEAM_FILE = "hr.py"

# HR's *employment* model. Permitted nowhere at all, including the seam: the
# seam links a record, it does not import employment.
FORBIDDEN_HR_TERMS = (
	"salary",
	"payroll",
	"timesheet",
	"attendance",
	"leave_application",
	"leave allocation",
	"employee_advance",
	"appraisal",
	"shift_assignment",
)


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
		scanned = {path.name for path in module_files("volunteer")}

		for expected in (
			"application.py",
			"volunteer.py",
			"certification.py",
			"learning.py",
			"timelog.py",
			"hr.py",
			"affiliations.py",
		):
			self.assertIn(expected, scanned)

	def test_the_scanner_would_catch_a_leak_that_was_really_there(self):
		"""A scanner that finds nothing because it is broken proves nothing."""
		leaked = 'def f():\n\t"""Prose may say Employee."""\n\tx = "Employee"\n\treturn x\n'
		clean = 'def f():\n\t"""Prose may say Employee and salary freely."""\n\treturn 1\n'

		self.assertIn("Employee", _code_only(leaked))
		self.assertNotIn("Employee", _code_only(clean))

	def test_the_call_scanner_sees_a_call_that_is_really_there(self):
		self.assertIn("resolve_approvers", called_names("resolve_approvers(1, 2)"))
		self.assertNotIn("resolve_approvers", called_names("x = 1"))


class TestRoutingIsDelegated(IntegrationTestCase):
	def test_no_file_resolves_approvers_itself(self):
		offenders = []

		for path in module_files("volunteer"):
			names = called_names(path.read_text())

			for forbidden in FORBIDDEN_CALLS:
				if forbidden in names:
					offenders.append(f"{path.name}: {forbidden}")

		self.assertEqual(
			offenders, [], "routing belongs to the approval engine; this module must delegate to it"
		)

	def test_no_file_queries_geo_or_authority_directly(self):
		offenders = []

		for path in module_files("volunteer"):
			text = path.read_text()

			for doctype in FORBIDDEN_DOCTYPES:
				if f'"{doctype}"' in text or f"'{doctype}'" in text:
					offenders.append(f"{path.name}: {doctype}")

		self.assertEqual(offenders, [], "geo is core's, reached through the adapter")

	def test_geo_arrives_only_through_cores_adapter(self):
		"""The positive half: this module does read geo, and only one way.

		Without this, the two tests above would also pass for a module that had
		quietly stopped using geo at all.
		"""
		importers = [
			path.name for path in module_files("volunteer") if "onerc_core.geo.services" in path.read_text()
		]

		self.assertTrue(importers, "no file reads geo at all — the delegation tests prove nothing")


class TestTheLearningSeamIsContained(IntegrationTestCase):
	def test_only_the_seam_names_an_lms_doctype(self):
		offenders = []

		for path in module_files("volunteer"):
			if path.name == LMS_SEAM_FILE:
				continue

			code = _code_only(path.read_text())

			for doctype in LMS_DOCTYPES:
				if doctype in code:
					offenders.append(f"{path.name}: {doctype}")

		self.assertEqual(offenders, [], "an LMS model has leaked past the seam")

	def test_the_seam_does_name_one(self):
		"""Guards the test above: the exemption is exempting something real."""
		seam = [path for path in module_files("volunteer") if path.name == LMS_SEAM_FILE]

		self.assertEqual(len(seam), 1)
		self.assertIn("LMS Enrollment", _code_only(seam[0].read_text()))

	def test_no_vmmsx_doctype_json_links_to_an_lms_doctype(self):
		"""A Link in a JSON is a schema dependency, and would be the same leak.

		This is why `VMMS Course Mapping.external_course` is Data: a Link would
		put an LMS doctype name in a vmmsx doctype and make this app fail to
		install where no LMS is present.
		"""
		import json

		offenders = []
		root = Path(frappe.get_app_path("vmmsx"))

		for path in root.glob("*/doctype/*/*.json"):
			definition = json.loads(path.read_text())

			for field in definition.get("fields", []):
				if field.get("options") in LMS_DOCTYPES:
					offenders.append(f"{definition.get('name')}.{field['fieldname']}")

		self.assertEqual(offenders, [], "a vmmsx doctype links directly to an LMS doctype")

	def test_the_only_other_mention_is_the_hook_registration(self):
		"""hooks.py names the doctype once, to plug the seam in. Nowhere else.

		Registering a `doc_events` handler needs the doctype's name, so this one
		mention is unavoidable — but it should be exactly one, and it should point
		at the seam.
		"""
		hooks = (Path(frappe.get_app_path("vmmsx")) / "hooks.py").read_text()

		self.assertEqual(hooks.count('"LMS Enrollment"'), 1)
		self.assertIn("vmmsx.volunteer.services.learning.on_enrollment_update", hooks)


class TestTheHRSeamIsContained(IntegrationTestCase):
	def test_only_the_seam_names_the_employee_doctype(self):
		offenders = []

		for path in module_files("volunteer"):
			if path.name == HR_SEAM_FILE:
				continue

			code = _code_only(path.read_text())

			for doctype in HR_DOCTYPES:
				if f'"{doctype}"' in code or f"'{doctype}'" in code:
					offenders.append(f"{path.name}: {doctype}")

		self.assertEqual(offenders, [], "HR's record has leaked past the seam")

	def test_no_file_anywhere_names_hrs_employment_model(self):
		"""Not even the seam. The link is a link; employment does not cross it."""
		offenders = []

		for path in module_files("volunteer"):
			code = _code_only(path.read_text()).lower()

			for term in FORBIDDEN_HR_TERMS:
				if term in code:
					offenders.append(f"{path.name}: {term}")

		self.assertEqual(offenders, [], "a volunteer is not an employee; no employment model belongs here")

	def test_no_vmmsx_field_fetches_identity_from_an_employee(self):
		"""A `fetch_from` pointing at Employee would be the whole principle undone.

		Red Profile is the spine. The Employee link is provisioning-facing, and
		nothing may read a field off the far side of it as the answer to who
		somebody is.
		"""
		import json

		offenders = []
		root = Path(frappe.get_app_path("vmmsx"))

		for path in root.glob("*/doctype/*/*.json"):
			definition = json.loads(path.read_text())

			for field in definition.get("fields", []):
				fetch = field.get("fetch_from") or ""

				if fetch.split(".")[0] in ("employee",):
					offenders.append(f"{definition.get('name')}.{field['fieldname']} <- {fetch}")

		self.assertEqual(offenders, [], "identity is being fetched from HR")


class TestTheApprovalEngineIsNotReimplemented(IntegrationTestCase):
	def test_no_file_branches_on_an_approval_stage_label(self):
		"""The engine's own rule, restated for its third consumer.

		`approvals/tests/test_no_stage_branching.py` already walks every source
		file in the app, so this asserts the scan covers this module's files
		rather than repeating the walk — a rule enforced by a test that never
		looked at these files would not be enforced here.
		"""
		from vmmsx.approvals.tests import test_no_stage_branching as scan

		scanned = {Path(path).as_posix() for path in scan.source_files()}
		ours = {path.as_posix() for path in module_files("volunteer")}

		self.assertTrue(ours <= scanned, "the stage-branching scan does not cover volunteer/")
