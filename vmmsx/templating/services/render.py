# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The render service — a template key plus a context, in; rendered output, out.

    render_template(template_key, context) -> dict

That is the whole public surface, and it is deliberately small. Nothing here
knows what a membership is. The caller builds the context — it is the caller
that understands its own domain — and this module resolves the configured
template, renders it, and hands back an explicit dict.

**The sandbox is the point.** A template body is written by a society
administrator through the desk, which makes it untrusted input in the same way a
form submission is. Frappe's `render_template` runs on a
`FrappeSandboxedEnvironment`, so the classic Jinja escape — walking
`__class__`/`__mro__`/`__subclasses__` from any object to reach the interpreter
— raises rather than executes. This module's job is to make sure that raise
becomes a clean, reported refusal instead of a traceback that half-rendered a
certificate.

**Undefined placeholders are not errors.** A context that is missing a key
leaves the placeholder visibly unfilled rather than throwing, because a society
editing a template should see what they got wrong on the page rather than
receive a stack trace. That is Frappe's `DebugUndefined`, and it is the
behaviour we want.
"""

import frappe
from frappe import _
from jinja2 import TemplateError
from jinja2.sandbox import SecurityError

TEMPLATE_DOCTYPE = "VMMS Template"

# Dunder access is how every classic Jinja escape begins — `__class__`,
# `__mro__`, `__subclasses__`, `__globals__` — and no template a society writes
# has any legitimate use for it.
#
# There are three layers here, deliberately. Frappe itself refuses a template
# containing `.__`, and the sandbox refuses an escape that gets past that. This
# screen sits in front of both so that *this app* gives one consistent answer:
# without it, an escape written as `''.__class__` surfaces as Frappe's generic
# "Illegal template" ValidationError while one written another way surfaces as a
# SecurityError, and a caller would have to know which layer caught it.
UNSAFE_MARKER = "__"


def render_template(template_key: str, context: dict | None = None) -> dict:
	"""Render the configured template `template_key` against `context`.

	Returns::

	    {
	        "template_key": "membership_certificate",
	        "template_name": "Membership Certificate",
	        "category": "certificate",
	        "format": "html",
	        "subject": "Certificate of Membership",
	        "body": "<h1>...</h1>",
	    }

	An explicit dict built field by field — never the Document, which would leak
	every field on the record to whatever rendered it.

	The category is returned as data, not acted on. No branch anywhere in vmmsx
	reads it: a society may add a category and nothing needs to know.
	"""
	template = _active_template(template_key)
	context = dict(context or {})

	return {
		"template_key": template.template_key,
		"template_name": template.template_name,
		"category": template.template_category,
		"format": template.output_format,
		"subject": _render_one(template.subject, context, template.template_key, "subject"),
		"body": _render_one(template.body, context, template.template_key, "body"),
	}


def render_string(body: str, context: dict | None = None) -> str:
	"""Render an arbitrary template string through the same sandbox.

	For a caller holding a body it has not saved yet — a preview screen, a test.
	It is the same sandbox and the same refusal; there is no unguarded path
	through this module.
	"""
	return _render_one(body, dict(context or {}), _("(unsaved)"), "body")


def _active_template(template_key: str):
	"""The template, if it exists and the society still uses it."""
	if not template_key:
		frappe.throw(
			_("No template was named. Configuration must point at a {0} by its key.").format(
				frappe.bold(TEMPLATE_DOCTYPE)
			),
			frappe.MandatoryError,
			title=_("No Template Configured"),
		)

	if not frappe.db.exists(TEMPLATE_DOCTYPE, template_key):
		frappe.throw(
			_("There is no {0} with the key {1}.").format(
				frappe.bold(TEMPLATE_DOCTYPE), frappe.bold(template_key)
			),
			frappe.DoesNotExistError,
			title=_("Unknown Template"),
		)

	template = frappe.get_cached_doc(TEMPLATE_DOCTYPE, template_key)

	if not template.is_active:
		frappe.throw(
			_("Template {0} is not active and cannot be rendered.").format(frappe.bold(template_key)),
			frappe.ValidationError,
			title=_("Inactive Template"),
		)

	return template


def _render_one(body: str | None, context: dict, template_key: str, part: str) -> str:
	"""Render one part of a template, turning any escape attempt into a refusal.

	`SecurityError` is the sandbox catching a template reaching for something it
	may not have. It is caught separately from every other template error because
	the two mean different things to whoever has to fix them: one is an
	administrator writing something dangerous, the other is an administrator
	writing something broken.
	"""
	if not body:
		return ""

	if UNSAFE_MARKER in body:
		_refuse(template_key, part, f"template contains {UNSAFE_MARKER!r}")

	try:
		return frappe.render_template(body, context)
	except SecurityError as exc:
		# The sandbox caught an escape this module's screen did not — calling a
		# mutating method, say. Neutralised, not executed: nothing ran.
		_refuse(template_key, part, str(exc))
	except TemplateError as exc:
		frappe.throw(
			_("Template {0} could not be rendered: {1}").format(frappe.bold(template_key), exc),
			frappe.ValidationError,
			title=_("Template Error"),
		)


def _refuse(template_key: str, part: str, reason: str) -> None:
	"""One refusal, whichever layer caught the attempt.

	Logged, because a template reaching for code execution is worth somebody
	noticing — an administrator account writing one is a bigger problem than the
	template.
	"""
	frappe.log_error(
		title="VMMS template attempted a sandbox escape",
		message=f"Template {template_key} ({part}) was refused: {reason}",
	)
	frappe.throw(
		_(
			"Template {0} tried to do something templates are not allowed to do, and was"
			" refused. A template may use the values it is given; it may not run code."
		).format(frappe.bold(template_key)),
		frappe.PermissionError,
		title=_("Template Refused"),
	)
