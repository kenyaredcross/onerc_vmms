# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Fixtures for the Stipend module. Nothing here is mocked.

Geo comes from **core's** geo fixtures, identity from core's Red Profile,
authority from real `Geo Assignment` rows, and volunteers from the Volunteer
module's own service. If a test passes here, the thing it tested actually works
end to end.

**Two hierarchies again**, deliberately shaped and named differently, because the
level a society files stipend paperwork at is its own choice (ACC-03) and the code
must not hold an opinion:

    Uplands (region)                       Coastal (province)
    ├── Njoro (branch)   ← supervisor      └── Malindi (district)
    │   └── Mau (ward)                         └── Watamu (ward)
    └── Molo (branch)    ← out of scope

Neither "branch" nor "district" appears in any assertion about *behaviour*; they
are labels the fixtures chose, and the same code works in both.

**Three scope roles, and they are three separate roles.** Being able to see a
volunteer, a progress report and a payment form are different questions with
different answers, and a fixture that answered all three with one role would let
a test pass because the wrong door happened to be open. The picker tests in
particular depend on this: a supervisor who could see reports but not volunteers
must get an empty picker, not a full one.

**No role name, level name, department name or currency code appears in a source
file, so the fixtures supply all of them.** They are deliberately concrete,
precisely to demonstrate that the app never reads one — see
`test_delegation.py`, which greps the module for every name defined here.
"""

from contextlib import contextmanager

import frappe
from frappe.utils import add_days, today
from onerc_core.geo.tests import fixtures as geo_fixtures

TEST_PREFIX = "STIPTEST"
USER_DOMAIN = "@stipend.test"

# Level key prefixes for the two societies these tests build. Kept distinct from
# the approval engine's fixtures (VK/VG), the Member module's (MA/MB), the
# Volunteer module's (VLA/VLB) and the Deployment module's (DPA/DPB) so the
# suites never delete each other's geo.
SOCIETY_A_PREFIX = "STA"
SOCIETY_B_PREFIX = "STB"
LEVEL_PREFIXES = (SOCIETY_A_PREFIX, SOCIETY_B_PREFIX)

# Who may *see* each kind of record. Deliberately three different roles.
VOLUNTEER_SCOPE_ROLE = f"{TEST_PREFIX} Volunteer Viewer"
REPORT_SCOPE_ROLE = f"{TEST_PREFIX} Report Viewer"
PAYMENT_SCOPE_ROLE = f"{TEST_PREFIX} Payment Viewer"

TEST_ROLES = (VOLUNTEER_SCOPE_ROLE, REPORT_SCOPE_ROLE, PAYMENT_SCOPE_ROLE)

SETTINGS_DOCTYPE = "National Society Settings"

# The Custom Fields vmmsx installs and reads through stipend/services/society.py,
# plus the Volunteer module's scope role, which is what the picker resolves.
VOLUNTEER_SCOPE_SETTING = "vmms_volunteer_scope_role"
VOLUNTEER_ANCHOR_SETTING = "vmms_volunteer_anchor_level"
REPORT_SCOPE_SETTING = "vmms_stipend_report_scope_role"
PAYMENT_SCOPE_SETTING = "vmms_stipend_payment_scope_role"
STIPEND_ANCHOR_SETTING = "vmms_stipend_anchor_level"
CURRENCY_SETTING = "currency"

REPORT_DOCTYPE = "VMMS Stipend Progress Report"
PAYMENT_DOCTYPE = "VMMS Stipend Payment Form"
LINE_DOCTYPE = "VMMS Stipend Attendance Line"
REPORT_VOLUNTEER_DOCTYPE = "VMMS Stipend Report Volunteer"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"


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
	"""Region → Branch → Ward, with two branches so scope has an outside."""
	region, branch, ward = _ladder(SOCIETY_A_PREFIX, ["Region", "Branch", "Ward"])

	tree = {"levels": {"region": region, "branch": branch, "ward": ward}}
	tree["region"] = geo_fixtures.make_node("Uplands", region, None, is_group=True)
	tree["branch"] = geo_fixtures.make_node("Njoro", branch, tree["region"], is_group=True)
	tree["ward"] = geo_fixtures.make_node("Mau", ward, tree["branch"])
	tree["other_branch"] = geo_fixtures.make_node("Molo", branch, tree["region"], is_group=True)
	tree["other_ward"] = geo_fixtures.make_node("Elburgon", ward, tree["other_branch"])

	return tree


def build_society_b() -> dict:
	"""Province → District → Ward. A different shape and different words."""
	province, district, ward = _ladder(SOCIETY_B_PREFIX, ["Province", "District", "Ward"])

	tree = {"levels": {"province": province, "district": district, "ward": ward}}
	tree["region"] = geo_fixtures.make_node("Coastal", province, None, is_group=True)
	tree["district"] = geo_fixtures.make_node("Malindi", district, tree["region"], is_group=True)
	tree["ward"] = geo_fixtures.make_node("Watamu", ward, tree["district"])

	return tree


# --- people ---------------------------------------------------------------


def make_role(name: str) -> str:
	if not frappe.db.exists("Role", name):
		frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": 1}).insert()

	return name


def make_user(handle: str, roles: list[str] | None = None) -> str:
	"""A System User with the given roles and nothing else.

	Never a System Manager unless a test is specifically about one: that role is
	core's documented scope bypass, so a user holding it would pass checks for the
	wrong reason. The picker tests depend on that absolutely.
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


def make_profile(first_name: str = "Wanjiru", last_name: str = "Kimani", **kwargs) -> str:
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

	The shipped doctypes grant only System Manager, because which society role gets
	this is configuration, so the tests grant it with a Custom DocPerm.
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


def set_report_scope_role(role: str | None) -> None:
	_set_setting(REPORT_SCOPE_SETTING, role)


def set_payment_scope_role(role: str | None) -> None:
	_set_setting(PAYMENT_SCOPE_SETTING, role)


def set_stipend_anchor_level(geo_level: str | None) -> None:
	_set_setting(STIPEND_ANCHOR_SETTING, geo_level)


def set_volunteer_anchor_level(geo_level: str | None) -> None:
	_set_setting(VOLUNTEER_ANCHOR_SETTING, geo_level)


def set_currency(currency: str | None) -> None:
	"""The society's currency, on core's own settings field.

	Named here rather than typed into a test, so no currency code appears twice
	and `test_delegation.py` can assert the app's source never names one.
	"""
	_set_setting(CURRENCY_SETTING, currency)


def a_currency(other_than: str | None = None) -> str | None:
	"""Some currency this site actually holds, whichever it happens to be.

	Deliberately not a named one: the point of the currency tests is that the app
	takes the society's answer, so the fixture must not care what the answer is.
	`other_than` asks for a *different* one, which is what makes a test that
	changes the setting actually prove the change was read rather than pass
	because the two happened to match.
	"""
	filters = {"name": ("!=", other_than)} if other_than else {}

	return frappe.db.get_value("Currency", filters, "name")


# --- records --------------------------------------------------------------


def make_volunteer(profile: str, home_geo_node: str, active: bool = True):
	"""A volunteer, Active by default because most tests are about working ones."""
	from vmmsx.volunteer.services import volunteer as volunteer_service

	volunteer = volunteer_service.ensure(profile, home_geo_node=home_geo_node)

	if active and volunteer.status != volunteer_service.STATUS_ACTIVE:
		volunteer.status = volunteer_service.STATUS_ACTIVE
		volunteer.save(ignore_permissions=True)

	return volunteer


def make_report(geo_node: str, volunteers: list[str] | None = None, **overrides):
	"""A progress report covering a week, and whoever the test names."""
	values = {
		"doctype": REPORT_DOCTYPE,
		"geo_node": geo_node,
		"period_from": today(),
		"period_to": add_days(today(), 6),
		"narrative": "Whatever this society recorded about the period.",
		"volunteers": [{"volunteer": name} for name in volunteers or []],
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def make_payment_form(report: str, geo_node: str, lines: list[dict] | None = None, **overrides):
	"""A payment form paired with a report, and whatever grid the test builds."""
	values = {
		"doctype": PAYMENT_DOCTYPE,
		"progress_report": report,
		"geo_node": geo_node,
		"attendance": list(lines or []),
	}
	values.update(overrides)

	return frappe.get_doc(values).insert()


def line(volunteer: str, attendance_date, amount=0, attended: bool = True, hours=None) -> dict:
	"""One row of the grid, as a dict, for building a form in one call."""
	return {
		"volunteer": volunteer,
		"attendance_date": attendance_date,
		"attended": 1 if attended else 0,
		"hours": hours,
		"stipend_amount": amount,
	}


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
	set_stipend_anchor_level(None)
	set_volunteer_anchor_level(None)

	for doctype in (PAYMENT_DOCTYPE, REPORT_DOCTYPE):
		for name in frappe.get_all(doctype, pluck="name"):
			frappe.delete_doc(doctype, name, force=True)

	for name in frappe.get_all(VOLUNTEER_DOCTYPE, pluck="name"):
		frappe.delete_doc(VOLUNTEER_DOCTYPE, name, force=True)

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
	set_report_scope_role(None)
	set_payment_scope_role(None)

	for role in TEST_ROLES:
		if frappe.db.exists("Role", role):
			frappe.delete_doc("Role", role, force=True)
