# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The portal's terms panel: what the caller still has to accept, and accepting it.

Both are possessive and take no person: the caller is always the session user,
so neither can be used to read or write somebody else's consent. The rules are
in `registration/services/consent.py`.
"""

import frappe

from vmmsx.registration.services import consent


@frappe.whitelist()
def my_outstanding_declarations() -> list[dict]:
	"""The required declarations the caller has not accepted at their current version."""
	return consent.outstanding(frappe.session.user)


@frappe.whitelist(methods=["POST"])
def accept_my_declarations(declarations: str | list | None = None) -> list[dict]:
	"""Accept every outstanding declaration. Returns what is left, which is empty on success.

	`declarations` is a list of `{declaration, declaration_version}`, one per box
	the caller ticked.
	"""
	return consent.accept(frappe.session.user, declarations)
