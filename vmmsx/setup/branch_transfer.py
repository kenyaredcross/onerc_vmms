# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Turn on two-branch approval for branch transfers.

A transfer is released by the branch the volunteer is leaving, then accepted by
the branch they are joining. This writes that as the society's approval
workflow for `VMMS Branch Transfer`:

1. **Release** — routed from `from_geo_node` (the workflow's anchor) at the
   society's registration level;
2. **Accept** — routed from `to_geo_node` (the stage's own `anchor_field`), at
   the same level.

Both stages go to the society's **branch transfer role** —
`vmms_branch_transfer_scope_role`, the role that already decides who may see a
transfer — so the people who approve a transfer are exactly the people who can
open it. A 5-day deadline, and a reminder to the same person when it passes.

It also sets `vmms_transfer_approval_mode` to `routed`; until then every
transfer applies on its date with nobody deciding it.

Explicit, not run on migrate: it changes how a society moves volunteers.
Idempotent: a workflow that already exists for transfers is left alone.
"""

import frappe

from vmmsx.approvals.services import sla
from vmmsx.deployment.services import society

TRANSFER = "VMMS Branch Transfer"
WORKFLOW = "VMMS Approval Workflow"
RELEASE = "Release by current branch"
ACCEPT = "Acceptance by new branch"


def plan() -> dict:
	"""What `configure` would do on this site, changing nothing."""
	from onerc_core.society.services import config

	from vmmsx.analytics.services import oversight

	settings = config.settings()

	return {
		"role": settings.get(society.TRANSFER_SCOPE_ROLE_FIELD) or None,
		"level": oversight.config_level(),
		"mode": settings.get(society.TRANSFER_APPROVAL_MODE_FIELD) or "direct",
		"workflow": frappe.db.get_value(WORKFLOW, {"workflow_for": TRANSFER}, "name"),
	}


def configure(sla_days: int = 5) -> dict:
	"""Create the two-stage workflow and switch transfers to routed."""
	frappe.only_for("System Manager")

	current = plan()

	if not current["role"]:
		frappe.throw("Set the Branch Transfer Scope Role in National Society Settings first.")

	if not current["level"]:
		frappe.throw("Set the volunteer anchor level in National Society Settings first.")

	workflow = current["workflow"]

	if not workflow:
		stage = {
			"required_role": current["role"],
			"resolution_rule": "at_level",
			"geo_level": current["level"],
			"completion_rule": "single",
			"can_reject": 1,
			"sla_days": sla_days,
			"on_sla_breach": sla.BREACH_NOTIFY_ONLY,
		}
		doc = frappe.get_doc(
			{
				"doctype": WORKFLOW,
				"workflow_for": TRANSFER,
				"geo_node_field": "from_geo_node",
				"applicant_field": "volunteer",
				"allow_withdrawal": 1,
				"stages": [
					{**stage, "sequence": 1, "stage_label": RELEASE},
					{**stage, "sequence": 2, "stage_label": ACCEPT, "anchor_field": "to_geo_node"},
				],
			}
		).insert(ignore_permissions=True)
		workflow = doc.name

	from onerc_core.society.services import config

	frappe.db.set_single_value(config.SETTINGS_DOCTYPE, society.TRANSFER_APPROVAL_MODE_FIELD, "routed")
	frappe.clear_document_cache(config.SETTINGS_DOCTYPE, config.SETTINGS_DOCTYPE)

	return {**plan(), "workflow": workflow}
