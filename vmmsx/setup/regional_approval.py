# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A second membership approval, by the region, after the county.

Kenya's membership goes: payment, the County Coordinator, then the Head of
Region, then Active. This adds that second stage to the society's existing
membership workflow. Volunteer applications keep their single county stage.

The stage:

- is routed to the society's **regional oversight role** at the region level
  (`at_level`), so a membership in Baringo goes to whoever holds the role over
  Baringo's region;
- is **optional**: where no region has anybody assigned yet, a membership
  approved by its county is not held at an empty desk; it is approved. A region
  is covered the moment somebody is assigned to it, and from then on its
  memberships wait for them;
- has a 5-day deadline and **weekly_digest** as its breach action: a late item
  is counted in the approver's Monday summary rather than alerted on daily or
  handed to somebody else.

Explicit, not run on migrate: it changes how a society approves memberships.
Idempotent: a workflow that already has a stage for that role is left alone.
"""

import frappe

from vmmsx.approvals.services import sla
from vmmsx.setup.regional_oversight import role

MEMBERSHIP = "VMMS Membership"
STAGE_LABEL = "Regional approval"


def add_membership_regional_stage(geo_level: str = "region", sla_days: int = 5) -> dict:
	frappe.only_for("System Manager")

	oversight = role()

	if not oversight:
		frappe.throw("Set the Regional Oversight Role in National Society Settings first.")

	if not frappe.db.exists("Geo Level", geo_level):
		frappe.throw(f"There is no Geo Level {geo_level!r}.")

	name = frappe.db.get_value("VMMS Approval Workflow", {"workflow_for": MEMBERSHIP}, "name")

	if not name:
		frappe.throw("There is no membership approval workflow to add the regional stage to.")

	workflow = frappe.get_doc("VMMS Approval Workflow", name)

	for stage in workflow.stages:
		if stage.required_role == oversight:
			return {"workflow": name, "status": "exists", "stage": stage.name}

	workflow.append(
		"stages",
		{
			"sequence": max((row.sequence for row in workflow.stages), default=0) + 1,
			"stage_label": STAGE_LABEL,
			"required_role": oversight,
			"resolution_rule": "at_level",
			"geo_level": geo_level,
			"completion_rule": "any_of",
			"can_reject": 1,
			"is_optional": 1,
			"sla_days": sla_days,
			"on_sla_breach": sla.BREACH_WEEKLY_DIGEST,
		},
	)
	workflow.save()

	return {"workflow": name, "status": "added", "stage": workflow.stages[-1].name}
