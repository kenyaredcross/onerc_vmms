# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Approval Decision — one line of an application's audit trail.

Lives as a child table on the *approvable document*, so an application carries
its own history: who decided what, at which stage, when, and why. Every field
is read-only and written only by the engine — a decision a user could type is
not an audit trail.

`stage` holds the opaque row name of the stage; `stage_label` is a snapshot of
what that stage was called at the time. Relabelling a stage next year must not
rewrite what happened this year, and nothing in the engine reads either field
to decide anything.
"""

from frappe.model.document import Document


class VMMSApprovalDecision(Document):
	pass
