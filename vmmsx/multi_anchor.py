# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Geo scoping for a record that is about more than one place.

Core's `onerc_scopeable_doctypes` scopes a doctype on **one** Geo Node field.
Some records are about two places at once — a branch transfer is released by
the branch a volunteer is leaving and accepted by the branch they are joining —
and anchoring one on either field alone hides it from the other branch.

So such a doctype is not registered with core (whose handlers then have no
opinion on it: `enforcement.get_permission_query_conditions` returns "" and
`has_permission` True, and Frappe ANDs every app's answer), and is declared
here instead, through this app's own hook:

    vmmsx_multi_anchor_doctypes = [
        {
            "doctype": "VMMS Branch Transfer",
            "read_fields": ("from_geo_node", "to_geo_node"),
            "write_field": "from_geo_node",
            "role_from_setting": "vmms_branch_transfer_scope_role",
        },
    ]

- **read** (and report, print, export, email, share): the caller holds the role
  at or above *any* of `read_fields`;
- **create, write, delete, submit, cancel**: at or above `write_field`.

Domain-agnostic infrastructure, outside every module package, for the reason
`elevation.py` is: it answers one question for whoever declares a doctype, and
no domain module grows a scope model of its own. It is built entirely from
core's reads — `scope.has_unrestricted_scope` and `scope.get_user_geo_scope`,
the same assignment query core's own scoping uses — so "holds the role at or
above this node" means exactly what it means everywhere else. onerc_core is not
changed.

The role is the society's setting, read on every call. Empty means nobody but an
unrestricted user, the fail-closed answer core gives.
"""

import frappe

HOOK = "vmmsx_multi_anchor_doctypes"
READ_TYPES = ("read", "report", "print", "export", "email", "share", None)


def registration(doctype: str | None) -> dict | None:
	for entry in frappe.get_hooks(HOOK) or []:
		if entry.get("doctype") == doctype:
			return entry

	return None


def role(doctype: str) -> str | None:
	from onerc_core.society.services import config

	entry = registration(doctype)

	if not entry:
		return None

	return config.settings().get(entry["role_from_setting"]) or None


def reach(doctype: str, user: str | None = None) -> set[str] | None:
	"""The nodes `user` covers for `doctype`. None means everywhere."""
	from onerc_core.access.services import scope

	user = user or frappe.session.user

	if scope.has_unrestricted_scope(user):
		return None

	held = role(doctype)

	if not held:
		return set()

	return set(scope.get_user_geo_scope(user, held))


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None, **kwargs) -> str:
	entry = registration(doctype)

	if not entry:
		return ""

	nodes = reach(doctype, user)

	if nodes is None:
		return ""

	if not nodes:
		return "1=0"

	allowed = ", ".join(frappe.db.escape(node) for node in sorted(nodes))
	clauses = [f"`tab{doctype}`.`{field}` IN ({allowed})" for field in entry["read_fields"]]

	return "(" + " OR ".join(clauses) + ")"


def has_permission(doc=None, ptype: str | None = None, user: str | None = None, **kwargs) -> bool:
	if doc is None:
		return True

	doctype = doc.get("doctype") if not isinstance(doc, str) else kwargs.get("doctype")
	entry = registration(doctype)

	if not entry:
		return True

	if isinstance(doc, str):
		doc = frappe.db.get_value(doctype, doc, list(entry["read_fields"]), as_dict=True) or {}

	nodes = reach(doctype, user)

	if nodes is None:
		return True

	if ptype in READ_TYPES:
		return any(doc.get(field) in nodes for field in entry["read_fields"])

	return doc.get(entry["write_field"]) in nodes
