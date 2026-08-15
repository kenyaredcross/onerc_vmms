# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Fixtures for the approval engine.

**The approvable doctype is a stand-in, and it is created for real.** The engine
governs Volunteer Application, Membership, Deployment Request — none of which
exist yet, and none of which the engine may name. So the tests register one of
their own: a genuine DocType, with a genuine table, a genuine mandatory Link to
Geo Node and a genuine `VMMS Approval Decision` table. Everything then runs
unmocked — routing goes through core against real Geo Assignments, the gate
reads real resolutions, assignment writes real ToDos.

That the engine is proven against a doctype it has never heard of is the point:
if it works here it works for the real modules, because there is nothing about
this one it could have been written around.

**Two hierarchies, deliberately shaped differently.** The same workflow
configuration has to route correctly in both, and neither shape may be
assumed anywhere in the engine:

    Central (region)                    North Bank (region)   ← a region head
    └── Kiambu (county)  ← a county     ├── Kerewan (district)  ← a district officer
    │   ├── Kihara (ward)   coordinator │   └── Illiassa (village)
    │   └── Ndenderu (ward)             └── Jokadu (district)   ← nobody here
    └── Nakuru (county)  ← nobody           └── Kuntaur (village)
        └── Bahati (ward)

Geo data is built through **core's** geo fixtures. Nothing in vmmsx creates a
Geo Node of its own, in tests any more than in the app.
"""

from contextlib import contextmanager

import frappe
from onerc_core.geo.tests import fixtures as geo_fixtures

from vmmsx.approvals import states

TEST_PREFIX = "VMMS-TEST"
USER_DOMAIN = "@vmmsx.test"

# The stand-in. Custom, so it lives in the database and is torn down with the
# test class rather than shipping in the app.
APPROVABLE_DOCTYPE = "VMMS Test Application"
GEO_FIELD = "geo_node"
OPTIONAL_GEO_FIELD = "optional_geo_node"
APPLICANT_FIELD = "applicant_ref"

# Society-named roles. Nothing in the engine names them; they arrive as
# configuration on a stage.
APPROVER_ROLE = f"{TEST_PREFIX} Volunteer Approver"
SECOND_ROLE = f"{TEST_PREFIX} Branch Officer"
APPLICANT_ROLE = f"{TEST_PREFIX} Applicant"
TEST_ROLES = (APPROVER_ROLE, SECOND_ROLE, APPLICANT_ROLE)

KENYA_PREFIX = "VK"
GAMBIA_PREFIX = "VG"
LEVEL_PREFIXES = (KENYA_PREFIX, GAMBIA_PREFIX)

# Stage labels, as a society would name them. They live here rather than being
# typed into each test so that `test_no_stage_branching` can assert that not one
# of them appears in the engine's code: what a society calls a stage is data,
# and the engine that routes it has never heard the words.
LABEL_BRANCH = "Branch Endorsement"
LABEL_COUNTY = "County Approval"
LABEL_REGION = "Regional Sign-off"
LABEL_NATIONAL = "National Desk"
STAGE_LABELS = (LABEL_BRANCH, LABEL_COUNTY, LABEL_REGION, LABEL_NATIONAL)

WORKFLOW_DOCTYPE = "VMMS Approval Workflow"


# --- the stand-in doctype -------------------------------------------------


def ensure_approvable_doctype() -> str:
	"""Create the stand-in, once.

	Creating a DocType is DDL and commits implicitly, so this runs before
	anything that must roll back with the test transaction.
	"""
	for role in TEST_ROLES:
		make_role(role)

	if frappe.db.exists("DocType", APPROVABLE_DOCTYPE):
		return APPROVABLE_DOCTYPE

	frappe.get_doc(
		{
			"doctype": "DocType",
			"name": APPROVABLE_DOCTYPE,
			"module": "VMMS Approvals",
			"custom": 1,
			"autoname": "hash",
			"fields": [
				{"fieldname": "title", "fieldtype": "Data", "label": "Title", "reqd": 1},
				{
					# ACC-02: a Link, and mandatory at creation. The workflow
					# refuses to govern a doctype whose anchor is either free
					# text or optional, so this shape is not incidental.
					"fieldname": GEO_FIELD,
					"fieldtype": "Link",
					"options": "Geo Node",
					"label": "Geo Node",
					"reqd": 1,
				},
				{
					# Deliberately optional, and never used as an anchor. It
					# exists so the ACC-02 guardrail can be proved: a workflow
					# must refuse to anchor on a field a user may leave empty.
					"fieldname": OPTIONAL_GEO_FIELD,
					"fieldtype": "Link",
					"options": "Geo Node",
					"label": "Optional Geo Node",
				},
				{"fieldname": APPLICANT_FIELD, "fieldtype": "Data", "label": "Applicant Reference"},
				{
					"fieldname": "approval_state",
					"fieldtype": "Select",
					"label": "Approval State",
					"options": "\n".join(states.STATES),
					"default": states.DRAFT,
					"read_only": 1,
				},
				{
					"fieldname": "approval_stage",
					"fieldtype": "Data",
					"label": "Approval Stage",
					"read_only": 1,
				},
				{
					"fieldname": "approval_stage_entered_on",
					"fieldtype": "Datetime",
					"label": "Stage Entered On",
					"read_only": 1,
				},
				{
					"fieldname": "approval_decisions",
					"fieldtype": "Table",
					"label": "Approval Decisions",
					"options": "VMMS Approval Decision",
				},
			],
			"permissions": [
				{"role": role, "read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "share": 1}
				for role in ("System Manager", *TEST_ROLES)
			],
		}
	).insert()

	return APPROVABLE_DOCTYPE


# --- geo, through core ----------------------------------------------------


def build_kenya() -> dict:
	"""Region → County → Ward. Returns {label: geo node docname}."""
	levels = [
		geo_fixtures.make_level(f"{KENYA_PREFIX}-1", "Region", 1),
		geo_fixtures.make_level(f"{KENYA_PREFIX}-2", "County", 2),
		geo_fixtures.make_level(f"{KENYA_PREFIX}-3", "Ward", 3),
	]
	region_level, county_level, ward_level = levels

	tree = {"levels": {"region": region_level, "county": county_level, "ward": ward_level}}
	tree["region"] = geo_fixtures.make_node("Central", region_level, None, is_group=True)
	tree["kiambu"] = geo_fixtures.make_node("Kiambu", county_level, tree["region"], is_group=True)
	tree["nakuru"] = geo_fixtures.make_node("Nakuru", county_level, tree["region"], is_group=True)
	tree["kihara"] = geo_fixtures.make_node("Kihara", ward_level, tree["kiambu"])
	tree["ndenderu"] = geo_fixtures.make_node("Ndenderu", ward_level, tree["kiambu"])
	tree["bahati"] = geo_fixtures.make_node("Bahati", ward_level, tree["nakuru"])

	return tree


def build_gambia() -> dict:
	"""Region → District → Village. A different shape, and different words."""
	levels = [
		geo_fixtures.make_level(f"{GAMBIA_PREFIX}-1", "Region", 1),
		geo_fixtures.make_level(f"{GAMBIA_PREFIX}-2", "District", 2),
		geo_fixtures.make_level(f"{GAMBIA_PREFIX}-3", "Village", 3),
	]
	region_level, district_level, village_level = levels

	tree = {"levels": {"region": region_level, "district": district_level, "village": village_level}}
	tree["region"] = geo_fixtures.make_node("North Bank", region_level, None, is_group=True)
	tree["kerewan"] = geo_fixtures.make_node("Kerewan", district_level, tree["region"], is_group=True)
	tree["jokadu"] = geo_fixtures.make_node("Jokadu", district_level, tree["region"], is_group=True)
	tree["illiassa"] = geo_fixtures.make_node("Illiassa", village_level, tree["kerewan"])
	tree["kuntaur"] = geo_fixtures.make_node("Kuntaur", village_level, tree["jokadu"])

	return tree


# --- users, roles, authority ----------------------------------------------


def make_role(name: str) -> str:
	if not frappe.db.exists("Role", name):
		frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": 1}).insert()

	return name


def make_user(handle: str, roles: list[str] | None = None) -> str:
	"""A System User with the given roles and nothing else.

	Never a System Manager: that role is core's documented scope bypass, so a
	test user holding it would pass checks for the wrong reason.
	"""
	email = f"{handle}{USER_DOMAIN}"

	if frappe.db.exists("User", email):
		frappe.delete_doc("User", email, force=True)

	for role in roles or []:
		make_role(role)

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": handle.replace("_", " ").title(),
			"send_welcome_email": 0,
			"user_type": "System User",
			"roles": [{"role": role} for role in roles or []],
		}
	)
	user.insert()
	frappe.clear_cache(user=email)

	return email


def make_assignment(
	user: str,
	role: str,
	geo_node: str,
	*,
	is_active: bool = True,
	valid_from: str | None = None,
	valid_to: str | None = None,
) -> str:
	"""Authority: a role held at a place. Core's doctype, used as core intends."""
	make_role(role)

	doc = frappe.get_doc(
		{
			"doctype": "Geo Assignment",
			"user": user,
			"role": role,
			"geo_node": geo_node,
			"is_active": int(is_active),
			"valid_from": valid_from,
			"valid_to": valid_to,
		}
	)
	doc.insert()

	return doc.name


# --- configuration --------------------------------------------------------


def stage(sequence: int, label: str, role: str, **overrides) -> dict:
	"""One stage row, with the defaults an administrator would see on the form."""
	row = {
		"sequence": sequence,
		"stage_label": label,
		"required_role": role,
		"resolution_rule": "nearest_ancestor",
		"completion_rule": "single",
		"can_reject": 1,
		"is_optional": 0,
		"sla_days": 5,
		"on_sla_breach": "escalate_up",
	}
	row.update(overrides)

	return row


def make_workflow(stages: list[dict], doctype: str = APPROVABLE_DOCTYPE, **policy):
	"""The one workflow governing the stand-in. Replaces any earlier one."""
	existing = frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": doctype}, "name")

	if existing:
		frappe.delete_doc(WORKFLOW_DOCTYPE, existing, force=True)

	doc = frappe.get_doc(
		{
			"doctype": WORKFLOW_DOCTYPE,
			"workflow_for": doctype,
			"geo_node_field": GEO_FIELD,
			"stages": stages,
			**policy,
		}
	)
	doc.insert()

	return doc


def make_application(
	title: str, geo_node: str, applicant: str | None = None, owner: str | None = None
) -> str:
	doc = frappe.get_doc(
		{
			"doctype": APPROVABLE_DOCTYPE,
			"title": f"{TEST_PREFIX} {title}",
			GEO_FIELD: geo_node,
			APPLICANT_FIELD: applicant,
		}
	)
	doc.insert()

	if owner:
		frappe.db.set_value(APPROVABLE_DOCTYPE, doc.name, "owner", owner, update_modified=False)
		doc.reload()

	return doc.name


def load(name: str):
	return frappe.get_doc(APPROVABLE_DOCTYPE, name)


@contextmanager
def acting_as(user: str):
	"""Run a block as somebody else, and always put the session back."""
	previous = frappe.session.user
	frappe.set_user(user)

	try:
		yield
	finally:
		frappe.set_user(previous)


# --- teardown -------------------------------------------------------------


def reset() -> None:
	"""Drop fixture rows left behind by a run that committed.

	Order matters: applications and assignments hold Links to Geo Nodes, and
	NestedSet refuses to delete a node that still has children, so nodes go
	deepest first.
	"""
	if frappe.db.exists("DocType", APPROVABLE_DOCTYPE):
		for application in frappe.get_all(APPROVABLE_DOCTYPE, pluck="name"):
			frappe.db.delete("ToDo", {"reference_type": APPROVABLE_DOCTYPE, "reference_name": application})
			frappe.delete_doc(APPROVABLE_DOCTYPE, application, force=True)

		workflow = frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": APPROVABLE_DOCTYPE}, "name")

		if workflow:
			frappe.delete_doc(WORKFLOW_DOCTYPE, workflow, force=True)

	for user in frappe.get_all("User", filters={"email": ("like", f"%{USER_DOMAIN}")}, pluck="name"):
		frappe.delete_doc("User", user, force=True)

	levels = [
		level
		for level in frappe.get_all("Geo Level", filters={"name": ("like", "V_-%")}, pluck="name")
		if level.split("-")[0] in LEVEL_PREFIXES
	]

	if not levels:
		return

	for node in frappe.get_all(
		"Geo Node", filters={"geo_level": ("in", levels)}, order_by="lft desc", pluck="name"
	):
		for assignment in frappe.get_all("Geo Assignment", filters={"geo_node": node}, pluck="name"):
			frappe.delete_doc("Geo Assignment", assignment, force=True)

		frappe.delete_doc("Geo Node", node, force=True)

	for level in levels:
		frappe.delete_doc("Geo Level", level, force=True)


def teardown() -> None:
	"""Remove the stand-in doctype and its roles. Mirrors ensure_approvable_doctype()."""
	reset()

	if frappe.db.exists("DocType", APPROVABLE_DOCTYPE):
		frappe.delete_doc("DocType", APPROVABLE_DOCTYPE, force=True)

	for role in TEST_ROLES:
		if frappe.db.exists("Role", role):
			frappe.delete_doc("Role", role, force=True)
