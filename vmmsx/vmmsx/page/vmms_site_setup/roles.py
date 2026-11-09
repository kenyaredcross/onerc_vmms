# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Step: Kenya's three leadership roles — County Coordinator, Head of Region, NSD Coordinator.

Moved from `VMMS-Kenya scripts/configure_roles.py`, unchanged in what it does:

- creates County Coordinator and points every county setting and approval stage
  that named one of the four roles it replaces (Branch Coordinator, Volunteer
  Approver, Membership Approver, VMMS Asset Manager) at it;
- moves each person holding one of those at a county onto a County Coordinator
  assignment there, and switches the old assignment off (nothing is deleted);
- gives NSD Coordinator to the existing users named on the setup form;
- reruns the installers that grant permissions and workspaces from those
  settings, and moves approvals already waiting to the new holders.

Assignments above county level are left alone and listed. Idempotent.
"""

import re

SETTINGS = "National Society Settings"
COUNTY_COORDINATOR = "County Coordinator"
COUNTY_DESCRIPTION = (
	"Runs one county: approves volunteer applications and memberships, sends people out,"
	" handles transfers, tasks, announcements, materials, service certificates and stipends"
	" in the county they are assigned to."
)
# The roles County Coordinator takes over at county level.
REPLACED = ("Branch Coordinator", "Volunteer Approver", "Membership Approver", "VMMS Asset Manager")
# Every setting naming who does a county's work.
COUNTY_FIELDS = (
	"vmms_membership_scope_role",
	"vmms_volunteer_scope_role",
	"vmms_asset_scope_role",
	"vmms_certificate_print_role",
	"vmms_service_certificate_scope_role",
	"vmms_deployment_scope_role",
	"vmms_deployment_request_scope_role",
	"vmms_branch_transfer_scope_role",
	"vmms_task_scope_role",
	"vmms_branch_location_scope_role",
	"vmms_announcement_scope_role",
	"vmms_stipend_report_scope_role",
	"vmms_stipend_payment_scope_role",
)
NEVER_TOUCHED = {"Administrator", "Guest"}


def _county_fields(frappe) -> list[str]:
	meta = frappe.get_meta(SETTINGS)
	return [field for field in COUNTY_FIELDS if meta.has_field(field)]


def _assignments(frappe, level: str) -> tuple[list[dict], list[dict]]:
	"""Live assignments of the replaced roles: (at the county level, elsewhere)."""
	assignment = frappe.qb.DocType("Geo Assignment")
	node = frappe.qb.DocType("Geo Node")
	rows = (
		frappe.qb.from_(assignment)
		.inner_join(node)
		.on(node.name == assignment.geo_node)
		.select(
			assignment.name,
			assignment.user,
			assignment.role,
			assignment.geo_node,
			node.geo_node_name,
			node.geo_level,
			assignment.valid_from,
		)
		.where((assignment.is_active == 1) & assignment.role.isin(list(REPLACED)))
		.orderby(node.geo_node_name)
		.orderby(assignment.user)
		.orderby(assignment.role)
		.run(as_dict=True)
	)
	county = [row for row in rows if row.geo_level == level and row.user not in NEVER_TOUCHED]
	other = [row for row in rows if row not in county]
	return county, other


def _has_cc(frappe, user: str, node: str) -> bool:
	return bool(
		frappe.db.exists(
			"Geo Assignment", {"user": user, "role": COUNTY_COORDINATOR, "geo_node": node, "is_active": 1}
		)
	)


def _stages(frappe) -> list[dict]:
	stage = frappe.qb.DocType("VMMS Approval Stage")
	workflow = frappe.qb.DocType("VMMS Approval Workflow")
	return (
		frappe.qb.from_(stage)
		.inner_join(workflow)
		.on(workflow.name == stage.parent)
		.select(
			workflow.name.as_("workflow"),
			workflow.workflow_for,
			stage.name.as_("stage"),
			stage.stage_label,
			stage.required_role,
		)
		.where((stage.parenttype == "VMMS Approval Workflow") & stage.required_role.isin(list(REPLACED)))
		.orderby(workflow.name)
		.orderby(stage.sequence)
		.run(as_dict=True)
	)


def _oversight(frappe) -> dict:
	from vmmsx.setup import national_oversight, regional_oversight

	head = regional_oversight.role()
	regions = frappe.get_all(
		"Geo Node",
		filters={"geo_level": "region"},
		fields=["name", "geo_node_name"],
		order_by="geo_node_name",
	)
	held = (
		{
			row.geo_node: row.users
			for row in frappe.db.sql(
				"""
			SELECT geo_node, GROUP_CONCAT(user ORDER BY user SEPARATOR ', ') AS users
			FROM `tabGeo Assignment` WHERE is_active = 1 AND role = %(role)s GROUP BY geo_node
			""",
				{"role": head},
				as_dict=True,
			)
		}
		if head
		else {}
	)
	return {
		"head_of_region": {
			"role": head,
			"regions": {region.geo_node_name: held.get(region.name) or "nobody" for region in regions},
		},
		"nsd_coordinator": {
			"role": national_oversight.role(),
			"holders": national_oversight.holders(),
			"core_reads_nationally": national_oversight.core_reads_nationally(),
		},
	}


def plan(frappe, level: str = "county") -> dict:
	settings = frappe.get_single(SETTINGS)
	county, other = _assignments(frappe, level)
	users = sorted({row.user for row in county})

	return {
		"county_coordinator": {
			"role_exists": bool(frappe.db.exists("Role", COUNTY_COORDINATOR)),
			"settings_to_change": {
				field: settings.get(field)
				for field in _county_fields(frappe)
				if settings.get(field) != COUNTY_COORDINATOR
			},
			"stages_to_change": [
				f"{row.workflow} {row.workflow_for}: {row.stage_label} ({row.required_role})"
				for row in _stages(frappe)
			],
			"people": len(users),
			"assignments_to_add": len(
				{(row.user, row.geo_node) for row in county if not _has_cc(frappe, row.user, row.geo_node)}
			),
			"old_assignments_to_switch_off": len(county),
			"left_alone_above_county": [
				f"{row.user}: {row.role} at {row.geo_node_name} ({row.geo_level})" for row in other
			],
		},
		**_oversight(frappe),
	}


def configure(frappe, level: str = "county", nsd: list[str] | None = None) -> dict:
	from frappe.utils import getdate, today

	if not frappe.db.exists("Geo Level", level):
		raise ValueError(f"There is no Geo Level {level!r}.")

	from vmmsx.setup import national_oversight

	if not frappe.get_meta(SETTINGS).has_field(national_oversight.ROLE_FIELD):
		raise ValueError(
			"The National Oversight Role setting is missing: the site needs migrating with the current vmmsx."
		)

	done = {
		"role": "exists",
		"settings": [],
		"stages": [],
		"assigned": 0,
		"switched_off": 0,
		"roles_removed": [],
		"nsd": [],
	}

	# 1. The role.
	if not frappe.db.exists("Role", COUNTY_COORDINATOR):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": COUNTY_COORDINATOR,
				"desk_access": 1,
				"description": COUNTY_DESCRIPTION,
			}
		).insert(ignore_permissions=True)
		done["role"] = "created"

	# 2. Who does the county's work.
	settings = frappe.get_single(SETTINGS)
	for field in _county_fields(frappe):
		if settings.get(field) != COUNTY_COORDINATOR:
			settings.set(field, COUNTY_COORDINATOR)
			done["settings"].append(field)
	if done["settings"]:
		settings.save(ignore_permissions=True)

	# 3. Who decides at each stage.
	for workflow in sorted({row.workflow for row in _stages(frappe)}):
		doc = frappe.get_doc("VMMS Approval Workflow", workflow)
		for stage in doc.stages:
			if stage.required_role in REPLACED:
				done["stages"].append(f"{workflow}: {stage.stage_label} ({stage.required_role})")
				stage.required_role = COUNTY_COORDINATOR
		doc.save(ignore_permissions=True)

	# 4. The people.
	county, _other = _assignments(frappe, level)
	for user in sorted({row.user for row in county}):
		account = frappe.get_doc("User", user)
		if COUNTY_COORDINATOR not in {row.role for row in account.roles}:
			account.add_roles(COUNTY_COORDINATOR)

	for user, node in sorted({(row.user, row.geo_node) for row in county}):
		if _has_cc(frappe, user, node):
			continue
		frappe.get_doc(
			{
				"doctype": "Geo Assignment",
				"user": user,
				"role": COUNTY_COORDINATOR,
				"geo_node": node,
				"is_active": 1,
				"valid_from": today(),
			}
		).insert(ignore_permissions=True)
		done["assigned"] += 1

	for row in county:
		values = {"is_active": 0}
		if not row.valid_from or getdate(row.valid_from) <= getdate(today()):
			values["valid_to"] = today()
		frappe.db.set_value("Geo Assignment", row.name, values)
		done["switched_off"] += 1

	for user in sorted({row.user for row in county}):
		still_used = set(
			frappe.get_all(
				"Geo Assignment",
				filters={"user": user, "is_active": 1, "role": ("in", REPLACED)},
				pluck="role",
			)
		)
		unused = [role for role in REPLACED if role not in still_used]
		account = frappe.get_doc("User", user)
		held = [role for role in unused if role in {row.role for row in account.roles}]
		if held:
			account.remove_roles(*held)
			done["roles_removed"].append(f"{user}: {', '.join(held)}")

	# 5. NSD Coordinators named on the command line.
	for user in nsd or []:
		if not frappe.db.exists("User", user):
			raise ValueError(f"There is no user {user!r}. Create the account first.")
		account = frappe.get_doc("User", user)
		if national_oversight.role() not in {row.role for row in account.roles}:
			account.add_roles(national_oversight.role())
			done["nsd"].append(user)

	# 6. Permissions and workspaces follow the settings; waiting approvals follow the stages.
	_reinstall(frappe)
	from vmmsx.approvals.services import repair

	done["approvals_moved"] = repair.resync_pending()
	return done


def _reinstall(frappe) -> None:
	from vmmsx.content.services import permissions as content_permissions
	from vmmsx.registration.services import desk
	from vmmsx.registration.services import permissions as registration_permissions
	from vmmsx.registration.services import workspaces as registration_workspaces
	from vmmsx.service_certificate import settings as service_certificate
	from vmmsx.setup import national_oversight, regional_oversight
	from vmmsx.staff.services import module_profile
	from vmmsx.staff.services import permissions as staff_permissions
	from vmmsx.staff.services import workspaces as staff_workspaces

	for install in (
		regional_oversight.install,
		national_oversight.install,
		service_certificate.install,
		registration_workspaces.install,
		registration_permissions.install,
		desk.install,
		staff_workspaces.install,
		staff_permissions.install,
		module_profile.install,
		content_permissions.install,
	):
		install()
	frappe.clear_cache()


def run(frappe, settings: dict, apply: bool) -> dict:
	nsd = emails(settings.get("nsd_emails"))
	result = {"before": plan(frappe)}
	if not apply:
		if nsd:
			result["nsd_would_be_given_the_role"] = nsd
		return result
	result["done"] = configure(frappe, nsd=nsd)
	result["after"] = plan(frappe)
	return result


def emails(value) -> list[str]:
	"""Addresses typed one per line, or separated by commas or spaces."""
	return [part for part in re.split(r"[\s,;]+", value or "") if part]
