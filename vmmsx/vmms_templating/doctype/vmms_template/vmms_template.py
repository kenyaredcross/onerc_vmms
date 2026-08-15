# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Template — a society-authored document, stored as configuration.

The body is written by administrators through the desk, which makes it untrusted
input. It is rendered through Frappe's sandboxed Jinja by
`vmmsx.templating.services.render`, and this controller's job is to catch what
the sandbox would catch *at save time* rather than at render time — so a broken
or dangerous template is refused while its author is still looking at it, not
weeks later when somebody's certificate fails to print.

The check renders against an empty context deliberately. Undefined placeholders
are not errors (Frappe uses `DebugUndefined`), so an empty context still
exercises the syntax and still trips the sandbox on an escape attempt, without
this doctype needing to know what context any particular caller will supply.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class VMMSTemplate(Document):
	def validate(self):
		self.validate_renders()

	def validate_renders(self):
		"""Refuse a template that cannot render, or that tries to break out.

		`render_string` raises a clean error for both cases — a PermissionError
		for a sandbox escape, a ValidationError for bad syntax — so this method
		simply lets those surface against the form.
		"""
		from vmmsx.templating.services.render import render_string

		for part, body in (("Subject", self.subject), ("Body", self.body)):
			if not body:
				continue

			try:
				render_string(body, {})
			except frappe.PermissionError:
				# The sandbox refused it. Re-raised as-is: the render service's
				# message already says what happened and it is the right one.
				raise
			except frappe.ValidationError as exc:
				frappe.throw(
					_("The {0} of this template does not render: {1}").format(_(part), exc),
					frappe.ValidationError,
					title=_("Template Does Not Render"),
				)
