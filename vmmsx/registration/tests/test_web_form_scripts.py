# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A Web Form's client script is a Jinja template, and it must survive being one.

**The trap.** A desk client script is served to the browser as a static asset.
A Web Form's is not: `web_form.py::add_custom_context_and_script` reads the
`.js` file off disk and passes it through `frappe.render_template` before the
page is sent. That renderer's sandbox guard tests the *raw source text* for a
full stop followed by two underscores, anywhere in it — code or comment — and
throws `Illegal template` when it finds one.

**Why that is worth a test.** The failure has none of the properties that make a
bug easy: it is not a runtime error in the browser, it is a 417 on the page
itself, so the whole registration form is simply gone. The message names no
file, no line and no offending token. And the thing that causes it — naming a
scratch property on a dialog with a dunder prefix — is ordinary JavaScript that
looks completely correct in review, works in every other file in this app, and
is exactly what the near-identical desk copy of the same picker is free to do.

So the rule is asserted against the source, the same way this app asserts that
no stage label reaches a comparison and that Member delegates its routing. Two
checks, because passing one and failing the other would still take the page
down:

1. no web form script contains the forbidden sequence at all; and
2. every web form script actually renders, which is the real question and
   catches anything else the sandbox objects to.

Note this file states the rule without ever containing it, which is the same
constraint the scripts are under.
"""

from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

# The full stop and the two underscores, assembled rather than written, so this
# test file is not itself an illegal template if it is ever read as one.
FORBIDDEN = "." + "__"

APP_ROOT = Path(__file__).resolve().parents[2]


def _web_form_scripts() -> list[Path]:
	"""Every client script belonging to a Web Form in this app."""
	return sorted(APP_ROOT.glob("*/web_form/*/*.js"))


class TestWebFormScripts(IntegrationTestCase):
	def test_there_are_web_form_scripts_to_check(self):
		"""A scan that silently matched nothing would pass forever and prove nothing."""
		self.assertTrue(_web_form_scripts(), "No web form client scripts found to check")

	def test_no_script_contains_the_sandbox_trigger(self):
		"""The guard is textual, so the check is textual."""
		offenders = []

		for script in _web_form_scripts():
			source = script.read_text(encoding="utf-8")

			if FORBIDDEN in source:
				line = next(
					number
					for number, text in enumerate(source.splitlines(), start=1)
					if FORBIDDEN in text
				)
				offenders.append(f"{script.relative_to(APP_ROOT)}:{line}")

		self.assertEqual(
			offenders,
			[],
			"A web form client script contains the sequence frappe.render_template refuses,"
			" so its page will fail to render with 'Illegal template'. Rename the property"
			f" (a plain vmmsx_ prefix does the same job): {offenders}",
		)

	def test_every_web_form_page_renders_its_script(self):
		"""The end the rule exists for: the page builds.

		Runs the exact call that raised in production, rather than trusting that
		the textual check above is the only thing the sandbox dislikes.
		"""
		for name in frappe.get_all("Web Form", filters={"module": ("like", "VMMS%")}, pluck="name"):
			with self.subTest(web_form=name):
				form = frappe.get_doc("Web Form", name)
				context = frappe._dict(doc=form, web_form_doc=form)

				form.add_custom_context_and_script(context)
