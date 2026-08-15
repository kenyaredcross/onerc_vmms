# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Fixtures for the Member module. Nothing here is mocked.

Geo comes from **core's** geo fixtures, identity from core's Red Profile,
authority from real `Geo Assignment` rows, approval from a real
`VMMS Approval Workflow` driving the real engine, and payment from the real
`onerc_payments` Manual driver. If a test passes here, the thing it tested
actually works end to end.

**Two hierarchies again**, deliberately shaped and named differently, because
ACC-03 says the level a membership anchors at is a society's choice and the code
must not hold an opinion:

    Highland (region)                    Coastal (province)
    └── Meru (county)      ← approver    └── Tana (district)   ← approver
        ├── Timau (ward)                     └── Kipini (ward)
        └── Buuri (ward)

Neither "county" nor "district" appears in any assertion about *behaviour* —
they are labels the fixtures chose, and the same code routes correctly in both.
"""

from contextlib import contextmanager

import frappe
from onerc_core.geo.tests import fixtures as geo_fixtures

TEST_PREFIX = "MEMTEST"
USER_DOMAIN = "@member.test"

# Level key prefixes for the two societies these tests build. Kept distinct from
# the approval engine's fixtures (VK/VG) so the two suites never delete each
# other's geo.
SOCIETY_A_PREFIX = "MA"
SOCIETY_B_PREFIX = "MB"
LEVEL_PREFIXES = (SOCIETY_A_PREFIX, SOCIETY_B_PREFIX)

# A society-named role. Nothing in the Member module names it; it arrives as
# configuration on an approval stage.
APPROVER_ROLE = f"{TEST_PREFIX} Membership Approver"
APPLICANT_ROLE = f"{TEST_PREFIX} Applicant"

# Who may *see* a membership, as distinct from who may decide one. Deliberately
# a different role from APPROVER_ROLE: core's scope service makes the point that
# "where may I approve" and "where may I view" are different questions, and
# keeping them apart here is what stops a person-gate test from passing because
# geo scoping happened to deny the user first.
SCOPE_ROLE = f"{TEST_PREFIX} Membership Viewer"

TEST_ROLES = (APPROVER_ROLE, APPLICANT_ROLE, SCOPE_ROLE)

SETTINGS_DOCTYPE = "National Society Settings"

# The Custom Field vmmsx installs and registers through onerc_scopeable_doctypes.
SCOPE_ROLE_SETTING = "vmms_membership_scope_role"

# Membership type keys the tests configure. They exist here, in data, precisely
# so that no source file has to know them.
TYPE_ROUTED = f"{TEST_PREFIX}-routed"
TYPE_AUTO = f"{TEST_PREFIX}-auto"
TYPE_FREE = f"{TEST_PREFIX}-free"
TYPE_PROOF = f"{TEST_PREFIX}-proof"
TYPE_LIFETIME = f"{TEST_PREFIX}-lifetime"

TEMPLATE_KEY = f"{TEST_PREFIX}-certificate"

MEMBERSHIP_DOCTYPE = "VMMS Membership"
MEMBER_DOCTYPE = "VMMS Member"
TYPE_DOCTYPE = "VMMS Membership Type"
TEMPLATE_DOCTYPE = "VMMS Template"
WORKFLOW_DOCTYPE = "VMMS Approval Workflow"


# --- geo, through core ----------------------------------------------------


def _ladder(prefix: str, labels: list[str]) -> list[str]:
	"""A level ladder that does not claim to be the society's lowest.

	`geo_fixtures.make_levels` flags its deepest level `is_lowest`, and core
	permits exactly one active lowest level per site — so building two societies
	that way makes the second one refuse to save. These tests need two ladders
	coexisting and never assert on `is_lowest`, so they are created without it.
	"""
	return [
		geo_fixtures.make_level(f"{prefix}-{order}", label, order)
		for order, label in enumerate(labels, start=1)
	]


def build_society_a() -> dict:
	"""Region → County → Ward."""
	region, county, ward = _ladder(SOCIETY_A_PREFIX, ["Region", "County", "Ward"])

	tree = {"levels": {"region": region, "county": county, "ward": ward}}
	tree["region"] = geo_fixtures.make_node("Highland", region, None, is_group=True)
	tree["county"] = geo_fixtures.make_node("Meru", county, tree["region"], is_group=True)
	tree["ward"] = geo_fixtures.make_node("Timau", ward, tree["county"])
	tree["other_ward"] = geo_fixtures.make_node("Buuri", ward, tree["county"])

	return tree


def build_society_b() -> dict:
	"""Province → District → Ward. A different shape and different words."""
	province, district, ward = _ladder(SOCIETY_B_PREFIX, ["Province", "District", "Ward"])

	tree = {"levels": {"province": province, "district": district, "ward": ward}}
	tree["region"] = geo_fixtures.make_node("Coastal", province, None, is_group=True)
	tree["district"] = geo_fixtures.make_node("Tana", district, tree["region"], is_group=True)
	tree["ward"] = geo_fixtures.make_node("Kipini", ward, tree["district"])

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
	"""A Red Profile — core's identity spine. The member links to this."""
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


# --- configuration --------------------------------------------------------


def make_template(key: str = TEMPLATE_KEY, body: str | None = None, **overrides):
	"""A society-authored template. Editable, which is the point of the tests."""
	if frappe.db.exists(TEMPLATE_DOCTYPE, key):
		frappe.delete_doc(TEMPLATE_DOCTYPE, key, force=True)

	values = {
		"doctype": TEMPLATE_DOCTYPE,
		"template_key": key,
		"template_name": "Test Certificate",
		"template_category": "certificate",
		"subject": "Certificate of Membership",
		"body": body or "Member: {{ member_name }} | Type: {{ membership_type }} | At: {{ geo_path }}",
		"output_format": "html",
		"is_active": 1,
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def make_type(key: str, approval_mode: str, fee: float = 0, **overrides):
	"""A membership type — the configuration MEM-02 turns on."""
	if frappe.db.exists(TYPE_DOCTYPE, key):
		frappe.delete_doc(TYPE_DOCTYPE, key, force=True)

	values = {
		"doctype": TYPE_DOCTYPE,
		"membership_type_key": key,
		"membership_type_name": key.replace("-", " ").title(),
		"approval_mode": approval_mode,
		"fee_amount": fee,
		"duration_days": 365,
		"is_active": 1,
		"template_key": TEMPLATE_KEY if frappe.db.exists(TEMPLATE_DOCTYPE, TEMPLATE_KEY) else None,
		"benefits": [
			{"benefit_key": "clinic", "benefit_name": "Clinic access", "is_active": 1},
		],
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def make_workflow(role: str = APPROVER_ROLE, **overrides):
	"""One approval workflow governing VMMS Membership. Replaces any earlier one.

	Deliberately built through the real config doctype: a routed membership must
	go through the engine as configured, not through anything these tests wrote.
	"""
	existing = frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": MEMBERSHIP_DOCTYPE}, "name")

	if existing:
		frappe.delete_doc(WORKFLOW_DOCTYPE, existing, force=True)

	values = {
		"doctype": WORKFLOW_DOCTYPE,
		"workflow_for": MEMBERSHIP_DOCTYPE,
		"geo_node_field": "geo_node",
		"stages": [
			{
				"sequence": 1,
				"stage_label": "Membership Review",
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


def grant_membership_access(role: str) -> None:
	"""Let a society role read and write memberships.

	An approver acting on a membership *saves* it, so the role a society names on
	an approval stage needs write access to the governed doctype. The shipped
	doctype grants only System Manager, because which society role gets this is
	configuration — so the tests grant it the way an administrator would, with a
	Custom DocPerm.
	"""
	from frappe.permissions import add_permission, update_permission_property

	make_role(role)
	add_permission(MEMBERSHIP_DOCTYPE, role, 0)

	for permission in ("read", "write", "create", "share"):
		update_permission_property(MEMBERSHIP_DOCTYPE, role, 0, permission, 1)

	frappe.clear_cache(doctype=MEMBERSHIP_DOCTYPE)


def grant_member_access(role: str) -> None:
	"""Let a society role create and read member records.

	A registration clerk enrolling somebody at a counter creates the member
	satellite, and `member.ensure()` inserts it *without* bypassing permissions —
	unlike the volunteer register, whose insert is elevated with a justification
	in its own docstring. So a clerk who is not an administrator needs this grant
	for the ordinary registration path to work at all, which is exactly what the
	print tests reproduce.
	"""
	from frappe.permissions import add_permission, update_permission_property

	make_role(role)
	add_permission(MEMBER_DOCTYPE, role, 0)

	for permission in ("read", "write", "create", "share"):
		update_permission_property(MEMBER_DOCTYPE, role, 0, permission, 1)

	frappe.clear_cache(doctype=MEMBER_DOCTYPE)


def set_scope_role(role: str | None) -> None:
	"""Point the society's membership scope role at a role — or clear it.

	Written straight to the settings single and the cache dropped, which is what
	an administrator saving the form amounts to as far as enforcement is
	concerned. Clearing it is the shipped default: no role, nobody but an
	administrator reads a membership.
	"""
	frappe.db.set_single_value(SETTINGS_DOCTYPE, SCOPE_ROLE_SETTING, role)
	frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)


def grant_membership_scope(user: str, *nodes: str) -> None:
	"""Let this user see memberships at these nodes and everything beneath them.

	Separate from `make_assignment(user, APPROVER_ROLE, ...)` on purpose. Being
	able to *see* a membership is what geo scoping governs; being the person it
	routed to is what the approval engine's person-gate governs. Tests that
	assert a refusal need the first so they can prove it was the second.
	"""
	make_role(SCOPE_ROLE)
	frappe.get_doc("User", user).add_roles(SCOPE_ROLE)

	for node in nodes:
		make_assignment(user, SCOPE_ROLE, node)


def set_print_role(role: str | None) -> None:
	"""Point the society's certificate print role at a role — or clear it.

	Clearing it is the shipped state, and it means nobody but the member. Written
	straight onto the settings single with the cache dropped, which is what an
	administrator saving the form amounts to.
	"""
	from vmmsx.member.services.society import PRINT_ROLE_FIELD

	frappe.db.set_single_value(SETTINGS_DOCTYPE, PRINT_ROLE_FIELD, role)
	frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)


def set_logo(url: str | None) -> None:
	"""Put a logo on core's settings, or clear it. Read by the certificate."""
	frappe.db.set_single_value(SETTINGS_DOCTYPE, "logo", url)
	frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)


def make_logo_file(content: bytes = b"\x89PNG\r\n\x1a\nvmmsx-test-logo") -> str:
	"""A real public File on this site, and its URL.

	A real row rather than a bare path, because the thing under test is whether
	the certificate can find the *bytes* behind a stored URL and embed them. A
	made-up path would exercise only the fallback.
	"""
	from frappe.utils import random_string

	uploaded = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{TEST_PREFIX}-logo-{random_string(6)}.png",
			"is_private": 0,
			"content": content,
		}
	).insert(ignore_permissions=True)

	return uploaded.file_url


def set_anchor_level(geo_level: str | None) -> None:
	"""Point the society's ACC-03 setting at a level — or clear it.

	Written straight onto the settings single, which is what an administrator
	editing the form does. The cache is cleared so the next read sees it.
	"""
	from vmmsx.member.services.society import ANCHOR_LEVEL_FIELD

	frappe.db.set_single_value("National Society Settings", ANCHOR_LEVEL_FIELD, geo_level)
	frappe.clear_document_cache("National Society Settings", "National Society Settings")


# --- records --------------------------------------------------------------


def make_membership(profile: str, type_key: str, geo_node: str, **overrides):
	"""A membership, created the way the API creates one.

	`overrides` is for Proof-of-Membership tests — `membership_source` and
	`proof_attachment` — and is otherwise unused, so every existing caller is
	unaffected.
	"""
	from vmmsx.member.services import member as member_service

	member = member_service.ensure(profile)

	values = {
		"doctype": MEMBERSHIP_DOCTYPE,
		"member": member.name,
		"membership_type": type_key,
		"geo_node": geo_node,
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def make_proof_file(content: bytes = b"\x89PNG\r\n\x1a\nvmmsx-test-proof") -> str:
	"""A real public File on this site, standing in for an uploaded proof document.

	A PNG signature rather than a `.pdf` name: Frappe scans PDF content for
	embedded JavaScript on upload, and a fake, truncated PDF trips the scanner's
	own parser rather than the check it runs. A plain image is exactly what a
	photographed receipt or record book usually is anyway.
	"""
	from frappe.utils import random_string

	uploaded = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{TEST_PREFIX}-proof-{random_string(6)}.png",
			"is_private": 0,
			"content": content,
		}
	).insert(ignore_permissions=True)

	return uploaded.file_url


def confirm_payment_through_manual_driver(membership) -> dict:
	"""Settle this membership's fee through the real Manual gateway.

	`confirm_payment()` is the payments app's own admin path: it marks the
	transaction Completed, writes a Manual Payment detail row, and calls
	`_notify_source_app`, which invokes `on_payment_confirmed` on this
	membership by name. Nothing here touches a gateway or fakes the hook.
	"""
	from onerc_payments.gateways.manual import confirm_payment

	membership.reload()

	return confirm_payment(membership.payment_transaction, f"MANUAL-{frappe.generate_hash(length=6)}")


def use_manual_gateway() -> None:
	"""Point the payments app at its Manual driver for the duration of a test."""
	settings = frappe.get_single("OneRC Payment Settings")
	settings.active_gateway = _manual_gateway_name()
	settings.save(ignore_permissions=True)
	frappe.clear_document_cache("OneRC Payment Settings", "OneRC Payment Settings")


def _manual_gateway_name() -> str:
	"""The gateway record whose driver is the manual one, by driver class."""
	name = frappe.db.get_value("OneRC Payment Gateway", {"driver_class": ("like", "%manual%")}, "name")

	if name:
		return name

	gateway = frappe.get_doc(
		{
			"doctype": "OneRC Payment Gateway",
			"gateway_name": "Manual",
			"driver_class": "onerc_payments.gateways.manual.ManualGateway",
			"is_active": 1,
		}
	).insert(ignore_permissions=True)

	return gateway.name


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


def reset_branding() -> None:
	"""Put the society's branding and print rule back to the shipped state."""
	set_print_role(None)
	set_logo(None)


def reset() -> None:
	"""Drop fixture rows left behind by a run that committed."""
	set_anchor_level(None)

	for membership in frappe.get_all(MEMBERSHIP_DOCTYPE, pluck="name"):
		frappe.delete_doc(MEMBERSHIP_DOCTYPE, membership, force=True)

	for member in frappe.get_all(MEMBER_DOCTYPE, pluck="name"):
		frappe.delete_doc(MEMBER_DOCTYPE, member, force=True)

	workflow = frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": MEMBERSHIP_DOCTYPE}, "name")

	if workflow:
		frappe.delete_doc(WORKFLOW_DOCTYPE, workflow, force=True)

	for key in (TYPE_ROUTED, TYPE_AUTO, TYPE_FREE, TYPE_PROOF, TYPE_LIFETIME):
		if frappe.db.exists(TYPE_DOCTYPE, key):
			frappe.delete_doc(TYPE_DOCTYPE, key, force=True)

	if frappe.db.exists(TEMPLATE_DOCTYPE, TEMPLATE_KEY):
		frappe.delete_doc(TEMPLATE_DOCTYPE, TEMPLATE_KEY, force=True)

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

	for role in TEST_ROLES:
		if frappe.db.exists("Role", role):
			frappe.delete_doc("Role", role, force=True)
