# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Society configuration for broadcasting: which role may address a branch.

One setting, and it is not new — `patches/setup_notification_module.py` has
installed `vmms_announcement_scope_role` as a vmmsx-owned Custom Field on
National Society Settings since the notification module was built, and
`hooks.py` registers `VMMS Announcement` as scopeable against it. What was
missing was a name for it anywhere but inside a patch, which meant the two
places that now need to read it — `staff/services/permissions.py`, to grant the
role its doctype permissions, and `staff/services/console.py`, to open the
Communication section — would each have had to spell the string again.

Mirrors `sms/services/society.py` exactly, including the rule that nothing
outside a patch reads the field *directly*: the grant is made against the
resolved role and every gate downstream asks `frappe.has_permission`, so which
role a society named stays configuration and never becomes a literal in a check.

**Left empty ships closed**, like every scope-role setting before it: until a
society chooses the role, no non-administrator can read an announcement, the
Communication section does not appear, and nobody can address anybody.
"""

SCOPE_ROLE_FIELD = "vmms_announcement_scope_role"
