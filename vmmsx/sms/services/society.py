# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Society configuration for sending SMS, which vmmsx does not own.

Every other row in `staff/services/permissions.py::role_grants()` hands a
scope role permissions on a doctype this app defines. `SMS Campaign` belongs
to `onerc_sms`, an optional companion app vmmsx neither requires nor bundles —
sending is deliberately left to onerc_sms's own generic "Doctype Query"
builder rather than vmmsx growing a wrapper doctype for it, and geo scoping
comes for free because `SMS Campaign.resolve_from_doctype()` reads a
volunteer's own already-scoped doctype with the campaign's owner's
permissions, not from anything registered here.

**`vmms_sms_scope_role` is the one thing vmmsx still owns**: which society
role, if any, may open onerc_sms's own campaign builder at all. Left empty,
same as every scope-role setting before it, so no non-administrator reaches
it until a society chooses the role.

`staff/services/console.py::sms_access()` reads the *result* of granting this
role — `frappe.has_permission("SMS Campaign", ...)` — rather than this field
directly, the same indirection every gated console section already goes
through.
"""

SCOPE_ROLE_FIELD = "vmms_sms_scope_role"
