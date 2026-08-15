# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Make every approval workflow on this bench routable, and only ever widen.

**Why this exists.** A bench that has been seeded for more than one society ends
up with workflows that were written for whichever society ran its seed first. A
`VMMS Approval Workflow` names one doctype, so the second society does not get
its own: it inherits the first one's `allowed_anchor_levels` (which permit only
the first society's ladder, so ACC-03 refuses the second society's records at
save) and the first one's stage roles (which nobody in the second society holds,
so a record that *is* saved routes to nobody and sits In Review forever).

That is the same failure `seed/kenya_operations.py::_reconcile_workflows`
handles, generalised: this one takes no society and reads the site as it is.

**It only ever adds.** Anchor levels are unioned, never replaced. A stage's role
is rewritten *only* when the role it names is unroutable — held by nobody
through a Geo Assignment anywhere on the site — and only ever to a role that
somebody does hold. A workflow that already works is left exactly as it is, and
running this twice changes nothing the second time.

**A framework role in `required_role` is the specific bug worth naming.**
`System Manager` is a Frappe primitive, not a society role: dozens of users hold
it directly and none of them holds it *at a place*, because nobody grants a
framework role through a Geo Assignment. A stage naming it therefore resolves to
an empty approver list no matter how the geo is configured. Repointing it at a
role the society actually assigns is the whole repair.

Run it:

    bench --site vmms.localhost execute vmmsx.seed.repair_workflows.main

Reports what it changed and what it left alone. Nothing here is society-specific
and no role, level or country is named in this file.
"""

import frappe

WORKFLOW_DOCTYPE = "VMMS Approval Workflow"
ASSIGNMENT_DOCTYPE = "Geo Assignment"


def main(roles: dict[str, str] | str | None = None) -> dict:
	"""Repair every workflow on the site. Idempotent.

	`roles` maps a governed doctype to the role its stages should require, and is
	how an operator says what the automatic choice cannot know. Which role
	approves a volunteer application is a society's decision, not a fact
	derivable from the site: the fallback below picks the most widely assigned
	role so a demo routes *somewhere*, but "most people hold it" is not the same
	claim as "this is the right approver". Naming it here keeps the role out of
	this file's source, which is the rule about society role names.

	    bench --site <site> execute vmmsx.seed.repair_workflows.main \\
	        --kwargs "{'roles': {'VMMS Volunteer Application': 'Volunteer Approver'}}"

	A role named here is used even when the stage's current role would have
	passed, because the operator is being more specific than the check is.
	"""
	report = {"workflows": [], "changed": 0}

	roles = frappe.parse_json(roles) if isinstance(roles, str) else (roles or {})
	assignable = _roles_held_somewhere()

	for doctype, role in roles.items():
		if role not in assignable:
			print(
				f"Warning: '{role}' (named for {doctype}) is held by nobody through an "
				f"active Geo Assignment, so records will route to nobody. Create the "
				f"assignment, or name a role from the list below."
			)

	if not assignable:
		print(
			"No active Geo Assignment on this site grants any role, so there is no "
			"role to route to. Create a Geo Assignment first: a person, a role, and "
			"the node they hold it at. Nothing changed."
		)
		return report

	for name in frappe.get_all(WORKFLOW_DOCTYPE, pluck="name"):
		workflow = frappe.get_doc(WORKFLOW_DOCTYPE, name)
		result = _repair(workflow, assignable, roles.get(workflow.workflow_for))
		report["workflows"].append(result)
		report["changed"] += 1 if result["changes"] else 0

	_print(report, assignable)

	return report


# --- the repair -----------------------------------------------------------


def _repair(workflow, assignable: dict[str, list[str]], wanted: str | None = None) -> dict:
	"""One workflow, widened where it is too narrow to work. Never narrowed."""
	changes: list[str] = []

	changes += _widen_anchor_levels(workflow)
	changes += _reroute_unroutable_stages(workflow, assignable, wanted)

	if changes:
		# The workflow's own validation refuses a doctype that does not satisfy
		# the approval contract, which is exactly the check we want to keep: a
		# repair must not be able to save a configuration the form would reject.
		workflow.save(ignore_permissions=True)
		frappe.db.commit()

	return {
		"workflow": workflow.name,
		"for": workflow.workflow_for,
		"changes": changes,
	}


def _widen_anchor_levels(workflow) -> list[str]:
	"""Permit every active level on the site, where the list is a strict subset.

	ACC-03 says which level a record may anchor at is configuration. This does
	not overrule that: it widens a list that was written for one society's ladder
	so a second society's records can be saved at all. A society that wants a
	narrower rule sets it on the form afterwards, and this will not narrow it
	back, because it only adds.

	An empty list already means "any active level" and is left alone.
	"""
	present = [row.geo_level for row in workflow.get("allowed_anchor_levels") or []]

	if not present:
		return []

	active = frappe.get_all("Geo Level", filters={"is_active": 1}, pluck="name")
	missing = [level for level in active if level not in present]

	if not missing:
		return []

	for level in missing:
		workflow.append("allowed_anchor_levels", {"geo_level": level})

	return [f"anchor levels widened by {', '.join(missing)}"]


def _reroute_unroutable_stages(
	workflow, assignable: dict[str, list[str]], wanted: str | None = None
) -> list[str]:
	"""Repoint a stage whose role nobody holds at a place.

	The test is not "does this role exist" — a role with no geo assignment exists
	and still routes to nobody. It is "does anybody hold this role through an
	active Geo Assignment", which is the question `resolve_approvers` will ask.

	`wanted` is the operator's answer and wins outright, including over a stage
	that would already have passed. Without one, the replacement is the most
	widely held assignable role, which is a heuristic and is reported as one: it
	is a bench repair so a demo routes somewhere, not a decision about who should
	approve.
	"""
	changes = []

	for stage in workflow.stages:
		if not wanted and stage.required_role in assignable:
			continue

		if wanted and stage.required_role == wanted:
			continue

		replacement = wanted or _most_held(assignable)
		was = stage.required_role
		stage.required_role = replacement

		# `at_level` needs a level to aim at, and a stage repaired onto a role
		# held on a different ladder will have the wrong one. `nearest_ancestor`
		# asks the question that works on any ladder: walk up from the record's
		# own anchor until somebody holding the role is found.
		if stage.resolution_rule != "nearest_ancestor":
			stage.resolution_rule = "nearest_ancestor"
			stage.geo_level = None
			stage.fixed_geo_node = None
			changes.append(
				f"stage {stage.sequence} '{stage.stage_label}': role {was} -> {replacement}, "
				f"resolution -> nearest_ancestor"
			)
		else:
			changes.append(f"stage {stage.sequence} '{stage.stage_label}': role {was} -> {replacement}")

	return changes


# --- reading the site -----------------------------------------------------


def _roles_held_somewhere() -> dict[str, list[str]]:
	"""Every role somebody holds through an active Geo Assignment, and who holds it.

	This is the set of roles that can route. A role held only through the user's
	role table, with no assignment behind it, is not in here and is exactly the
	case that produces an empty approver list.
	"""
	held: dict[str, list[str]] = {}

	for row in frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters={"is_active": 1},
		fields=["role", "user"],
		limit_page_length=0,
	):
		held.setdefault(row.role, []).append(row.user)

	return held


def _most_held(assignable: dict[str, list[str]]) -> str:
	"""The assignable role with the most distinct holders; ties broken by name.

	Sorted rather than "whichever came first" so two runs on the same site pick
	the same role.
	"""
	return sorted(assignable, key=lambda role: (-len(set(assignable[role])), role))[0]


def _print(report: dict, assignable: dict[str, list[str]]) -> None:
	print("Roles that can route (held through an active Geo Assignment):")
	for role in sorted(assignable):
		print(f"  {role}: {', '.join(sorted(set(assignable[role])))}")

	print("")

	for row in report["workflows"]:
		if not row["changes"]:
			print(f"{row['workflow']} ({row['for']}): already routable, unchanged")
			continue

		print(f"{row['workflow']} ({row['for']}): repaired")
		for change in row["changes"]:
			print(f"    - {change}")

	print(f"\n{report['changed']} workflow(s) changed.")
