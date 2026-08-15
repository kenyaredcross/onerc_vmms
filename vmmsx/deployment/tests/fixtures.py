# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Fixtures for the Deployment module. Nothing here is mocked.

Geo comes from **core's** geo fixtures, identity from core's Red Profile,
authority from real `Geo Assignment` rows, approval from a real
`VMMS Approval Workflow` driving the real engine, and volunteers from the
Volunteer module's own service. If a test passes here, the thing it tested
actually works end to end.

**Two hierarchies again**, deliberately shaped and named differently, because
the level a deployment is anchored at is a society's choice (ACC-03) and the code
must not hold an opinion:

    Highland (region)                      Delta (province)
    ├── Karura (branch)   ← searcher       └── Estuary (district)
    │   └── Ruaka (post)                       └── Shoreline (ward)
    └── Limuru (branch)   ← out of scope

Neither "branch" nor "district" appears in any assertion about *behaviour*; they
are labels the fixtures chose, and the same code works in both.

**No certification name, no terms-of-reference name and no role name appears in
a source file, so the fixtures supply all three.** They are deliberately
concrete, precisely to demonstrate that the app never reads one.

**Three scope roles, and they are three separate roles.** Being able to see a
volunteer, a deployment and a transfer are different questions with different
answers, and a fixture that answered all three with one role would let a test
pass because the wrong door happened to be open.
"""

from contextlib import contextmanager

import frappe
from frappe.utils import add_days, today
from onerc_core.geo.tests import fixtures as geo_fixtures

TEST_PREFIX = "DEPTEST"
USER_DOMAIN = "@deployment.test"

# Level key prefixes for the two societies these tests build. Kept distinct from
# the approval engine's fixtures (VK/VG), the Member module's (MA/MB) and the
# Volunteer module's (VLA/VLB) so the four suites never delete each other's geo.
SOCIETY_A_PREFIX = "DPA"
SOCIETY_B_PREFIX = "DPB"
LEVEL_PREFIXES = (SOCIETY_A_PREFIX, SOCIETY_B_PREFIX)

# Society-named roles. Nothing in the Deployment module names one; they arrive
# as configuration on an approval stage or in a settings field.
REQUEST_APPROVER_ROLE = f"{TEST_PREFIX} Deployment Approver"
TRANSFER_APPROVER_ROLE = f"{TEST_PREFIX} Transfer Approver"

# Who may *see* each kind of record, as distinct from who may decide anything.
# Deliberately four different roles: a test asserting that the person-gate
# refused somebody must not pass because geo scoping stopped them at the door.
VOLUNTEER_SCOPE_ROLE = f"{TEST_PREFIX} Volunteer Viewer"
DEPLOYMENT_SCOPE_ROLE = f"{TEST_PREFIX} Deployment Viewer"
REQUEST_SCOPE_ROLE = f"{TEST_PREFIX} Request Viewer"
TRANSFER_SCOPE_ROLE = f"{TEST_PREFIX} Transfer Viewer"

TEST_ROLES = (
	REQUEST_APPROVER_ROLE,
	TRANSFER_APPROVER_ROLE,
	VOLUNTEER_SCOPE_ROLE,
	DEPLOYMENT_SCOPE_ROLE,
	REQUEST_SCOPE_ROLE,
	TRANSFER_SCOPE_ROLE,
)

SETTINGS_DOCTYPE = "National Society Settings"

# The Custom Fields vmmsx installs and registers through onerc_scopeable_doctypes
# and reads through deployment/services/society.py.
VOLUNTEER_SCOPE_SETTING = "vmms_volunteer_scope_role"
VOLUNTEER_ANCHOR_SETTING = "vmms_volunteer_anchor_level"
DEPLOYMENT_SCOPE_SETTING = "vmms_deployment_scope_role"
REQUEST_SCOPE_SETTING = "vmms_deployment_request_scope_role"
TRANSFER_SCOPE_SETTING = "vmms_branch_transfer_scope_role"
DEPLOYMENT_ANCHOR_SETTING = "vmms_deployment_anchor_level"
TRANSFER_MODE_SETTING = "vmms_transfer_approval_mode"

TERMS_DOCTYPE = "VMMS Terms of Reference"
DEPLOYMENT_DOCTYPE = "VMMS Deployment"
REQUEST_DOCTYPE = "VMMS Deployment Request"
TRANSFER_DOCTYPE = "VMMS Branch Transfer"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"
TIME_LOG_DOCTYPE = "VMMS Time Log"
CERTIFICATION_DOCTYPE = "VMMS Certification"
CERTIFICATION_TYPE_DOCTYPE = "VMMS Certification Type"
WORKFLOW_DOCTYPE = "VMMS Approval Workflow"

# Certification type keys the tests configure. Concrete, memorable names, chosen
# so that a grep of the app's source for any of them finds nothing.
CERT_SWIFT_WATER = f"{TEST_PREFIX}-swift-water"
CERT_RADIO = f"{TEST_PREFIX}-radio-operator"
CERT_LOGISTICS = f"{TEST_PREFIX}-logistics"

# Terms of reference keys, likewise.
TOR_FLOOD = f"{TEST_PREFIX}-flood-response"
TOR_OPEN = f"{TEST_PREFIX}-open-day"


# --- geo, through core ----------------------------------------------------


def _ladder(prefix: str, labels: list[str]) -> list[str]:
	"""A level ladder that does not claim to be the society's lowest.

	`geo_fixtures.make_levels` flags its deepest level `is_lowest`, and core
	permits exactly one active lowest level per site, so building two societies
	that way makes the second refuse to save. These tests need two ladders
	coexisting and never assert on `is_lowest`.
	"""
	return [
		geo_fixtures.make_level(f"{prefix}-{order}", label, order)
		for order, label in enumerate(labels, start=1)
	]


def build_society_a() -> dict:
	"""Region → Branch → Post, with two branches so scope has an outside."""
	region, branch, post = _ladder(SOCIETY_A_PREFIX, ["Region", "Branch", "Post"])

	tree = {"levels": {"region": region, "branch": branch, "post": post}}
	tree["region"] = geo_fixtures.make_node("Highland", region, None, is_group=True)
	tree["branch"] = geo_fixtures.make_node("Karura", branch, tree["region"], is_group=True)
	tree["post"] = geo_fixtures.make_node("Ruaka", post, tree["branch"])
	tree["other_branch"] = geo_fixtures.make_node("Limuru", branch, tree["region"], is_group=True)
	tree["other_post"] = geo_fixtures.make_node("Tigoni", post, tree["other_branch"])

	return tree


def build_society_b() -> dict:
	"""Province → District → Ward. A different shape and different words."""
	province, district, ward = _ladder(SOCIETY_B_PREFIX, ["Province", "District", "Ward"])

	tree = {"levels": {"province": province, "district": district, "ward": ward}}
	tree["region"] = geo_fixtures.make_node("Delta", province, None, is_group=True)
	tree["district"] = geo_fixtures.make_node("Estuary", district, tree["region"], is_group=True)
	tree["ward"] = geo_fixtures.make_node("Shoreline", ward, tree["district"])

	return tree


# --- people ---------------------------------------------------------------


def make_role(name: str) -> str:
	if not frappe.db.exists("Role", name):
		frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": 1}).insert()

	return name


def make_user(handle: str, roles: list[str] | None = None) -> str:
	"""A System User with the given roles and nothing else.

	Never a System Manager unless a test is specifically about one: that role is
	core's documented scope bypass, so a user holding it would pass checks for
	the wrong reason.
	"""
	email = f"{handle}{USER_DOMAIN}"

	if frappe.db.exists("User", email):
		frappe.delete_doc("User", email, force=True)

	for role in roles or []:
		make_role(role)

	frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": handle.replace("_", " ").title(),
			"send_welcome_email": 0,
			"user_type": "System User",
			"roles": [{"role": role} for role in roles or []],
		}
	).insert()
	frappe.clear_cache(user=email)

	return email


def make_profile(first_name: str = "Amina", last_name: str = "Otieno", **kwargs) -> str:
	"""A Red Profile — core's identity spine. The volunteer links to this."""
	slug = f"{first_name}.{last_name}".lower()

	return (
		frappe.get_doc(
			{
				"doctype": "Red Profile",
				"first_name": first_name,
				"last_name": last_name,
				"email": kwargs.pop("email", f"{slug}.{frappe.generate_hash(length=6)}{USER_DOMAIN}"),
				**kwargs,
			}
		)
		.insert()
		.name
	)


def make_assignment(user: str, role: str, geo_node: str) -> str:
	"""Authority: a role held at a place. Core's doctype, used as core intends."""
	make_role(role)

	return (
		frappe.get_doc(
			{
				"doctype": "Geo Assignment",
				"user": user,
				"role": role,
				"geo_node": geo_node,
				"is_active": 1,
			}
		)
		.insert()
		.name
	)


def grant_scope(user: str, role: str, *nodes: str) -> None:
	"""Let this user see, under `role`, these nodes and everything beneath them."""
	make_role(role)
	frappe.get_doc("User", user).add_roles(role)

	for node in nodes:
		make_assignment(user, role, node)


def grant_doctype_access(doctype: str, role: str) -> None:
	"""Let a society role read and write a doctype, the way an administrator would.

	The shipped doctypes grant only System Manager, because which society role
	gets this is configuration, so the tests grant it with a Custom DocPerm.
	"""
	from frappe.permissions import add_permission, update_permission_property

	make_role(role)
	add_permission(doctype, role, 0)

	for permission in ("read", "write", "create", "share", "delete"):
		update_permission_property(doctype, role, 0, permission, 1)

	frappe.clear_cache(doctype=doctype)


# --- society settings -----------------------------------------------------


def _set_setting(fieldname: str, value) -> None:
	"""Write one settings value the way an administrator saving the form would."""
	frappe.db.set_single_value(SETTINGS_DOCTYPE, fieldname, value)
	frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)


def set_volunteer_scope_role(role: str | None) -> None:
	_set_setting(VOLUNTEER_SCOPE_SETTING, role)


def set_deployment_scope_role(role: str | None) -> None:
	_set_setting(DEPLOYMENT_SCOPE_SETTING, role)


def set_request_scope_role(role: str | None) -> None:
	_set_setting(REQUEST_SCOPE_SETTING, role)


def set_transfer_scope_role(role: str | None) -> None:
	_set_setting(TRANSFER_SCOPE_SETTING, role)


def set_deployment_anchor_level(geo_level: str | None) -> None:
	_set_setting(DEPLOYMENT_ANCHOR_SETTING, geo_level)


def set_volunteer_anchor_level(geo_level: str | None) -> None:
	_set_setting(VOLUNTEER_ANCHOR_SETTING, geo_level)


def set_transfer_mode(mode: str | None) -> None:
	_set_setting(TRANSFER_MODE_SETTING, mode)


# --- configuration --------------------------------------------------------


def make_certification_type(key: str, validity_days: int = 365, **overrides):
	"""A certification the society recognises, and how long it lasts."""
	if frappe.db.exists(CERTIFICATION_TYPE_DOCTYPE, key):
		frappe.delete_doc(CERTIFICATION_TYPE_DOCTYPE, key, force=True)

	values = {
		"doctype": CERTIFICATION_TYPE_DOCTYPE,
		"certification_type_key": key,
		"certification_type_name": key.replace(f"{TEST_PREFIX}-", "").replace("-", " ").title(),
		"validity_days": validity_days,
		"blocks_deployment_when_lapsed": 1,
		"is_active": 1,
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def make_certification(volunteer: str, certification_type: str, completion_date=None):
	"""A held certification. Its expiry is computed by the controller, never typed."""
	return frappe.get_doc(
		{
			"doctype": CERTIFICATION_DOCTYPE,
			"volunteer": volunteer,
			"certification_type": certification_type,
			"completion_date": completion_date or today(),
		}
	).insert()


def make_terms(key: str = TOR_FLOOD, **overrides):
	"""One terms of reference. Direct approval unless a test asks otherwise."""
	if frappe.db.exists(TERMS_DOCTYPE, key):
		frappe.delete_doc(TERMS_DOCTYPE, key, force=True)

	values = {
		"doctype": TERMS_DOCTYPE,
		"tor_key": key,
		"tor_name": key.replace(f"{TEST_PREFIX}-", "").replace("-", " ").title(),
		"purpose": "Whatever this society uses these terms for.",
		"approval_mode": "direct",
		"is_active": 1,
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def make_terms_requiring(mandatory: tuple = (), desirable: tuple = (), **overrides):
	"""A terms of reference of its own, with its own requirements.

	Its key is generated, so each test gets a record nothing else has edited.
	Frappe rolls the test transaction back once per *class*, not per method, so a
	shared terms of reference that one method added a requirement to would still
	carry it for the next method, and the test that then passed would be lying.
	"""
	terms = make_terms(f"{TEST_PREFIX}-tor-{frappe.generate_hash(length=8)}", **overrides)

	for key in mandatory:
		terms.append("required_certifications", {"certification_type": key, "is_mandatory": 1})

	for key in desirable:
		terms.append("required_certifications", {"certification_type": key, "is_mandatory": 0})

	if mandatory or desirable:
		terms.save()

	return terms


def make_workflow(doctype: str, role: str, geo_node_field: str = "geo_node", **overrides):
	"""One approval workflow governing `doctype`.

	Deliberately built through the real config doctype: a record must go through
	the engine as configured, not through anything these tests wrote.
	"""
	existing = frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": doctype}, "name")

	if existing:
		frappe.delete_doc(WORKFLOW_DOCTYPE, existing, force=True)

	# The stage names a role, and a Link refuses one that does not exist yet. The
	# role is the society's, which is exactly why the workflow has to be handed
	# one rather than assume it.
	make_role(role)

	values = {
		"doctype": WORKFLOW_DOCTYPE,
		"workflow_for": doctype,
		"geo_node_field": geo_node_field,
		"stages": [
			{
				"sequence": 1,
				"stage_label": "Deployment Review",
				"required_role": role,
				"resolution_rule": "nearest_ancestor",
				"completion_rule": "single",
				"can_reject": 1,
				"is_optional": 0,
				"sla_days": 5,
				"on_sla_breach": "escalate_up",
			}
		],
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


# --- records --------------------------------------------------------------


def make_volunteer(profile: str, home_geo_node: str, active: bool = True):
	"""A volunteer, Active by default because most tests are about deployable ones.

	Activated through the satellite's own status field rather than by driving a
	whole application through the engine: what these tests are about is what
	happens to a volunteer who exists, and the acceptance path has its own suite.
	"""
	from vmmsx.volunteer.services import volunteer as volunteer_service

	volunteer = volunteer_service.ensure(profile, home_geo_node=home_geo_node)

	if active and volunteer.status != volunteer_service.STATUS_ACTIVE:
		volunteer.status = volunteer_service.STATUS_ACTIVE
		volunteer.save(ignore_permissions=True)

	return volunteer


def make_deployment(terms: str, geo_node: str, participants: list[str] | None = None, **overrides):
	"""A deployment, running today unless a test says otherwise."""
	values = {
		"doctype": DEPLOYMENT_DOCTYPE,
		"terms_of_reference": terms,
		"geo_node": geo_node,
		"start_date": today(),
		"end_date": add_days(today(), 7),
		"status": "Planned",
		"participants": [{"volunteer": name} for name in participants or []],
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def make_request(terms: str, geo_node: str, **overrides):
	"""A deployment request, created the way the API creates one."""
	values = {
		"doctype": REQUEST_DOCTYPE,
		"terms_of_reference": terms,
		"geo_node": geo_node,
		"needed_from": today(),
		"needed_until": add_days(today(), 7),
		"volunteers_requested": 2,
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def make_transfer(volunteer: str, to_geo_node: str, **overrides):
	"""A branch transfer, effective today unless a test says otherwise."""
	values = {
		"doctype": TRANSFER_DOCTYPE,
		"volunteer": volunteer,
		"to_geo_node": to_geo_node,
		"effective_date": today(),
		"reason": "Whatever reason this society recorded.",
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def make_time_log(volunteer: str, geo_node: str, **overrides):
	"""A time log, with the general kind and plausible values by default."""
	values = {
		"doctype": TIME_LOG_DOCTYPE,
		"volunteer": volunteer,
		"geo_node": geo_node,
		"log_type": "general",
		"activity_date": today(),
		"hours": 4,
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


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
	"""Drop fixture rows left behind by a run that committed."""
	set_deployment_anchor_level(None)
	set_volunteer_anchor_level(None)
	set_transfer_mode(None)

	for doctype in (
		TIME_LOG_DOCTYPE,
		TRANSFER_DOCTYPE,
		REQUEST_DOCTYPE,
		DEPLOYMENT_DOCTYPE,
		CERTIFICATION_DOCTYPE,
	):
		for name in frappe.get_all(doctype, pluck="name"):
			frappe.delete_doc(doctype, name, force=True)

	for name in frappe.get_all(VOLUNTEER_DOCTYPE, pluck="name"):
		frappe.delete_doc(VOLUNTEER_DOCTYPE, name, force=True)

	# Every terms of reference this suite made, including the generated ones.
	for name in frappe.get_all(TERMS_DOCTYPE, filters={"name": ("like", f"{TEST_PREFIX}-%")}, pluck="name"):
		frappe.delete_doc(TERMS_DOCTYPE, name, force=True)

	for key in (CERT_SWIFT_WATER, CERT_RADIO, CERT_LOGISTICS):
		if frappe.db.exists(CERTIFICATION_TYPE_DOCTYPE, key):
			frappe.delete_doc(CERTIFICATION_TYPE_DOCTYPE, key, force=True)

	for doctype in (REQUEST_DOCTYPE, TRANSFER_DOCTYPE):
		workflow = frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": doctype}, "name")

		if workflow:
			frappe.delete_doc(WORKFLOW_DOCTYPE, workflow, force=True)

	for profile in frappe.get_all(
		"Red Profile", filters={"email": ("like", f"%{USER_DOMAIN}")}, pluck="name"
	):
		frappe.delete_doc("Red Profile", profile, force=True)

	for user in frappe.get_all("User", filters={"email": ("like", f"%{USER_DOMAIN}")}, pluck="name"):
		frappe.delete_doc("User", user, force=True)

	_reset_geo()


def _reset_geo() -> None:
	"""Geo goes deepest-first: NestedSet refuses to delete a node with children."""
	levels = [
		level for level in frappe.get_all("Geo Level", pluck="name") if level.split("-")[0] in LEVEL_PREFIXES
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
	reset()
	set_volunteer_scope_role(None)
	set_deployment_scope_role(None)
	set_request_scope_role(None)
	set_transfer_scope_role(None)

	for role in TEST_ROLES:
		if frappe.db.exists("Role", role):
			frappe.delete_doc("Role", role, force=True)
