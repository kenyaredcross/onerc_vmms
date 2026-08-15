# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Approval Stage — a child row of VMMS Approval Workflow's configuration.

Validation lives on the parent, not here: Frappe does not call a child
controller's `validate`, and a rule that only fires sometimes is worse than
one written where it always runs. See `vmms_approval_workflow.py`.
"""

from frappe.model.document import Document


class VMMSApprovalStage(Document):
	pass
