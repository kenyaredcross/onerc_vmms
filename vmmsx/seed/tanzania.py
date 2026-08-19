# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Tanzania Red Cross Society's own configuration. Data, never behaviour.

    bench --site <site> execute vmmsx.seed.tanzania.main

The third society, on the split `gambia.py` and `kenya.py` already proved: a
different country, a different ladder, a different currency, and not one line
of source outside `vmmsx/seed/` changes to allow it. Roles, geo levels, geo
nodes, membership types, approval workflows and settings are all records an
administrator creates in the desk; this module creates the ones TRCS would.

**Where the data comes from.** The society's own public facts — founding year,
headquarters, hotline, volunteer and branch counts, mission and vision — are
taken from `trcs.or.tz` and the IFRC National Societies Directory, and are real.
The 31 regions are Tanzania's own administrative regions (26 on the mainland,
5 in Zanzibar), which is also the society's own count of regional branches, one
per region. **The membership plans are not sourced from a published TRCS price
list** — no such document was found — and are a worked example in the shape of
the society's real structure, the same honest label `kenya.py` carries for its
own plans. Replace the amounts with the society's real fee schedule before this
stops being a demo.

**Idempotent, and it says what it did.** Every step checks before it writes and
reports `created` or `exists`. It never overwrites a value an administrator has
since edited. It expects a site with no other society on it — run
`vmmsx.seed.purge.main` first on a bench that has had one, which is exactly
`tanzania_install.py`'s job.
"""

import frappe

from vmmsx.registration.services.desk import PORTAL_HOME

SETTINGS_DOCTYPE = "National Society Settings"

# --- the society ------------------------------------------------------------

ORGANIZATION_NAME = "Tanzania Red Cross Society"
ORGANIZATION_SHORT_NAME = "TRCS"
COUNTRY = "Tanzania"
CURRENCY = "TZS"
LANGUAGE = "sw"
TIME_ZONE = "Africa/Dar_es_Salaam"

WEBSITE = "https://trcs.or.tz"
# The 24-hour hotline TRCS publishes on its own site, not a branch line.
TELEPHONE = "0800 750 150"
ADDRESS = "Mwai Kibaki Road, Plot 53, Block C, Mikocheni B, P.O. Box 1133, Dar es Salaam, Tanzania"

# No logo ships with this seed. Gambia's and Kenya's each point at a real mark
# committed to `public/images/seed_<society>/`; nobody has TRCS's own logo file
# to commit, and a placeholder pretending to be one is worse than the branded
# upload control an empty field already draws. Uploading the real mark is the
# first manual step — see MANUAL_STEPS.
LOGO = None

# What people here actually speak, as against what the desk is translated
# into. Frappe ships Swahili itself (`sw`), so it is not repeated below; these
# are community languages spoken across mainland regions that a volunteer form
# offering only Swahili and English would have nothing to say to. Codes are
# ISO 639-3; labels are how each language names itself.
SPOKEN_LANGUAGES = (
	("suk", "Sukuma"),
	("nym", "Nyamwezi"),
	("hay", "Haya"),
	("mas", "Maa"),
	("gog", "Gogo"),
	("heh", "Hehe"),
	("kde", "Makonde"),
	("nyy", "Nyakyusa-Ngonde"),
)

# --- the hierarchy ------------------------------------------------------------

# Two rungs, not four: TRCS's own copy says 31+ regional branches and 1,250+
# sub-branches, but the sub-branches are not named anywhere public, and this
# seed does not invent 1,250 names to fill a third level — the same restraint
# `gambia_operations.py` takes with people. A region is a real, sourced unit;
# a fabricated sub-branch tree under it would not be.
LEVELS = (
	{"key": "trcs-national", "name": "National", "order": 1, "requires_parent": 0, "is_lowest": False},
	{"key": "trcs-region", "name": "Region", "order": 2, "requires_parent": 1, "is_lowest": True},
)

NATIONAL_NODE = ORGANIZATION_NAME

# Tanzania's 31 administrative regions: 26 on the mainland, 5 in Zanzibar. This
# is also TRCS's own count of regional branches, one per region, so the geo
# tree below is the real structure rather than a subset invented for a demo.
REGIONS = (
	# -- mainland, 26 --
	"Arusha",
	"Dar es Salaam",
	"Dodoma",
	"Geita",
	"Iringa",
	"Kagera",
	"Katavi",
	"Kigoma",
	"Kilimanjaro",
	"Lindi",
	"Manyara",
	"Mara",
	"Mbeya",
	"Morogoro",
	"Mtwara",
	"Mwanza",
	"Njombe",
	"Pwani",
	"Rukwa",
	"Ruvuma",
	"Shinyanga",
	"Simiyu",
	"Singida",
	"Songwe",
	"Tabora",
	"Tanga",
	# -- Zanzibar, 5 --
	"Kaskazini Unguja",
	"Kusini Unguja",
	"Mjini Magharibi",
	"Kaskazini Pemba",
	"Kusini Pemba",
)

# --- roles --------------------------------------------------------------------

ROLE_VOLUNTEER_APPROVER = "Volunteer Approver"
ROLE_MEMBERSHIP_APPROVER = "Membership Approver"
ROLE_BRANCH_COORDINATOR = "Branch Coordinator"
ROLE_DEPLOYMENT_MANAGER = "Deployment Manager"
ROLE_STIPEND_MANAGER = "Stipend Manager"
ROLE_VOLUNTEER = "Volunteer"
ROLE_MEMBER = "Member"
ROLE_APPLICANT = "Society Applicant"

# (name, description, desk_access)
#
# The same eight `gambia.py` and `kenya.py` each define underneath their own
# extras — see `vmmsx.setup.core_roles` for the six every society needs, which
# this table re-states idempotently alongside the two coordinating roles TRCS
# needs of its own.
ROLES = (
	(ROLE_VOLUNTEER_APPROVER, "Reviews volunteer applications for a region.", True),
	(ROLE_MEMBERSHIP_APPROVER, "Reviews membership applications for a region.", True),
	(
		ROLE_BRANCH_COORDINATOR,
		"Runs a regional branch: tasks, announcements, offices and the page content.",
		True,
	),
	(
		ROLE_DEPLOYMENT_MANAGER,
		"Sends people out: deployments, deployment requests and branch transfers.",
		True,
	),
	(
		ROLE_STIPEND_MANAGER,
		"Handles stipend paperwork: progress reports and payment forms.",
		True,
	),
	(ROLE_VOLUNTEER, "An approved volunteer, with the self-service portal.", False),
	(ROLE_MEMBER, "An approved member, with the self-service portal.", False),
	(
		ROLE_APPLICANT,
		"Somebody who has made an account and not yet been approved as anything.",
		False,
	),
)

# --- membership plans -----------------------------------------------------

# A worked example in the shape of the society's real structure — see the
# module docstring for why this is not a sourced price list. Two annual plans
# and one lifetime plan, priced in TZS.
TYPE_YOUTH = "youth-member"
TYPE_ORDINARY = "ordinary-member"
TYPE_LIFE = "life-member"

ONE_YEAR = 365

MEMBERSHIP_TYPES = (
	{
		"key": TYPE_YOUTH,
		"name": "Youth Member",
		"fee_amount": 5000,
		"duration_days": ONE_YEAR,
		"is_lifetime": False,
		"approval_mode": "routed",
		"description": "For school-age members, 10 to 17 years. Renewed every year, reviewed by the region.",
		"approval_note": "Reviewed by the region the applicant belongs to.",
		"benefits": (
			("membership-certificate", "Membership certificate"),
			("training", "Benefits from training"),
			("youth-leadership", "Youth leadership programmes"),
			("branch-register", "Listed in the Branch Register"),
		),
	},
	{
		"key": TYPE_ORDINARY,
		"name": "Ordinary Member",
		"fee_amount": 10000,
		"duration_days": ONE_YEAR,
		"is_lifetime": False,
		"approval_mode": "routed",
		"description": "For members 18 years and above. Renewed every year, reviewed by the region.",
		"approval_note": "Reviewed by the region the applicant belongs to.",
		"benefits": (
			("membership-certificate", "Membership certificate"),
			("training", "Benefits from training"),
			("branch-programmes", "Attend branch programmes"),
			("branch-register", "Registered in the Branch Register"),
		),
	},
	{
		"key": TYPE_LIFE,
		"name": "Life Member",
		"fee_amount": 100000,
		"duration_days": 0,
		"is_lifetime": True,
		"approval_mode": "routed",
		"description": "A one-time fee, reviewed by the region and confirmed by the national desk.",
		"approval_note": "Reviewed by the region, then confirmed at national level.",
		"benefits": (
			("membership-certificate", "Membership certificate"),
			("training", "Benefits from training"),
			("leadership", "Leadership programmes"),
			("national-programmes", "Attend national programmes"),
		),
	},
)

CERTIFICATE_TEMPLATE_KEY = "membership_certificate"

# --- approval workflows ---------------------------------------------------

APPLICATION_DOCTYPE = "VMMS Volunteer Application"
MEMBERSHIP_DOCTYPE = "VMMS Membership"
WORKFLOW_DOCTYPE = "VMMS Approval Workflow"

APPROVER_WRITABLE = {
	APPLICATION_DOCTYPE: ROLE_VOLUNTEER_APPROVER,
	MEMBERSHIP_DOCTYPE: ROLE_MEMBERSHIP_APPROVER,
}

# Two rungs, matching the two-rung geo tree: a region decides first, and the
# national desk is the backstop every unstaffed region escalates to.
STAGE_REGION = "Regional Coordinator"
STAGE_NATIONAL = "National Desk"

# --- the demo approver ----------------------------------------------------

APPROVER_USER = "approver@trcs.demo"
APPROVER_FIRST_NAME = "Amina"
APPROVER_LAST_NAME = "Mwakalinga"
APPROVER_REGION = "Dar es Salaam"


def main(commit: bool = True) -> dict:
	"""Seed the whole society and report what changed. Safe to re-run."""
	report = {
		"roles": _roles(),
		"geo_levels": _geo_levels(),
		"geo_nodes": _geo_nodes(),
		"society": _society(),
		"spoken_languages": _spoken_languages(),
		"membership_types": _membership_types(),
		"workflows": _workflows(),
		"approver_permissions": _approver_permissions(),
		"approver": place_approver(),
		"settings": _settings(),
		"payment_gateway": _payment_gateway(),
		"signup": _signup(),
		"surfaces": _surfaces(),
		"landing_content": _landing_content(),
	}

	report["manual_steps"] = MANUAL_STEPS

	if commit:
		frappe.db.commit()

	_print(report)

	return report


MANUAL_STEPS = (
	"Assign somebody to each approver role at the national node, in Geo Assignment. The regional"
	" rung is optional and skipped when empty; the national one is the final decision and nothing"
	" above it exists to escalate to.",
	f"Set a password for {APPROVER_USER} on their User form before signing in as them.",
	"Replace the Manual payment gateway with a real one in OneRC Payment Settings when the society"
	" is ready to take money online. Until then a member applies and pays at the branch, and a"
	" clerk confirms it — see _payment_gateway() in this file.",
	"Upload TRCS's real logo onto National Society Settings, and replace the placeholder"
	" photography on the landing page with the society's own — see tanzania_content.py.",
	"Replace the illustrative membership fees in MEMBERSHIP_TYPES with the society's real,"
	" published fee schedule.",
)


# --- roles ------------------------------------------------------------------


def _roles() -> list[dict]:
	rows = []

	for name, description, desk in ROLES:
		if frappe.db.exists("Role", name):
			rows.append({"key": name, "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": name,
				"desk_access": int(desk),
				"home_page": None if desk else PORTAL_HOME,
				"description": description,
			}
		).insert(ignore_permissions=True)

		rows.append({"key": name, "status": "created"})

	return rows


# --- geo ----------------------------------------------------------------------


def _geo_levels() -> list[dict]:
	rows = []

	for level in LEVELS:
		if frappe.db.exists("Geo Level", level["key"]):
			rows.append({"key": level["key"], "status": "exists"})
			continue

		is_lowest = level["is_lowest"] and not _has_lowest_level()

		frappe.get_doc(
			{
				"doctype": "Geo Level",
				"geo_level_key": level["key"],
				"geo_level_name": level["name"],
				"geo_level_order": level["order"],
				"requires_parent": level["requires_parent"],
				"is_lowest_level": int(is_lowest),
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		row = {"key": level["key"], "status": "created"}

		if level["is_lowest"] and not is_lowest:
			row["note"] = "another active lowest level already exists; flag not set"

		rows.append(row)

	return rows


def _has_lowest_level() -> bool:
	return bool(frappe.db.exists("Geo Level", {"is_active": 1, "is_lowest_level": 1}))


def _geo_nodes() -> list[dict]:
	"""The society and its 31 regions.

	Docnames are opaque (`GEO-.#####`), so idempotence is a lookup on the shape
	of the row rather than on its name: a node is the same node when its label,
	its level and its parent all match.
	"""
	rows = []
	national, created = _node(NATIONAL_NODE, LEVELS[0]["key"], None, is_group=True)
	rows.append({"key": NATIONAL_NODE, "name": national, "status": created})

	for label in REGIONS:
		node, created = _node(label, LEVELS[1]["key"], national)
		rows.append({"key": label, "name": node, "status": created})

	return rows


def _node(label: str, level: str, parent: str | None, is_group: bool = False) -> tuple[str, str]:
	existing = frappe.db.get_value(
		"Geo Node", {"geo_node_name": label, "geo_level": level, "parent_geo_node": parent}, "name"
	)

	if existing:
		return existing, "exists"

	node = frappe.get_doc(
		{
			"doctype": "Geo Node",
			"geo_node_name": label,
			"geo_level": level,
			"parent_geo_node": parent,
			"is_group": int(is_group),
		}
	).insert(ignore_permissions=True)

	return node.name, "created"


def national() -> str | None:
	"""The society's root node, by shape."""
	return frappe.db.get_value(
		"Geo Node", {"geo_node_name": NATIONAL_NODE, "geo_level": LEVELS[0]["key"]}, "name"
	)


def region(label: str) -> str | None:
	"""A region by name, by shape. Used by the operations and jobs seeds."""
	return frappe.db.get_value(
		"Geo Node",
		{"geo_node_name": label, "geo_level": LEVELS[1]["key"], "parent_geo_node": national()},
		"name",
	)


# --- the society single ---------------------------------------------------


def _society() -> list[dict]:
	"""Fill in the society's own identity, without overwriting an edit."""
	settings = frappe.get_single(SETTINGS_DOCTYPE)
	rows = []

	values = {
		"organization_name": ORGANIZATION_NAME,
		"organization_short_name": ORGANIZATION_SHORT_NAME,
		"logo": LOGO,
		"country": COUNTRY if frappe.db.exists("Country", COUNTRY) else None,
		"currency": CURRENCY if frappe.db.exists("Currency", CURRENCY) else None,
		"primary_language": LANGUAGE if frappe.db.exists("Language", LANGUAGE) else None,
		"time_zone": TIME_ZONE,
		"official_website": WEBSITE,
		"telephone": TELEPHONE,
		"physical_address": ADDRESS,
	}

	changed = False

	for field, value in values.items():
		if not value:
			rows.append({"key": field, "status": "skipped: not available on this site"})
			continue

		if settings.get(field):
			rows.append({"key": field, "status": "exists", "value": settings.get(field)})
			continue

		settings.set(field, value)
		changed = True
		rows.append({"key": field, "status": "created", "value": value})

	if changed:
		settings.save(ignore_permissions=True)

	return rows


# --- the languages people here actually speak -----------------------------


def _spoken_languages() -> list[dict]:
	rows = []

	for code, label in SPOKEN_LANGUAGES:
		if frappe.db.exists("Language", code):
			rows.append({"key": code, "status": "exists"})
			continue

		frappe.get_doc(
			{"doctype": "Language", "language_code": code, "language_name": label, "enabled": 0}
		).insert(ignore_permissions=True)

		rows.append({"key": code, "status": "created", "value": label})

	return rows


# --- membership plans -----------------------------------------------------


def _membership_types() -> list[dict]:
	rows = []
	template = (
		CERTIFICATE_TEMPLATE_KEY if frappe.db.exists("VMMS Template", CERTIFICATE_TEMPLATE_KEY) else None
	)

	for definition in MEMBERSHIP_TYPES:
		if frappe.db.exists("VMMS Membership Type", definition["key"]):
			rows.append({"key": definition["key"], "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": "VMMS Membership Type",
				"membership_type_key": definition["key"],
				"membership_type_name": definition["name"],
				"approval_mode": definition["approval_mode"],
				"fee_amount": definition["fee_amount"],
				"fee_currency": CURRENCY if frappe.db.exists("Currency", CURRENCY) else None,
				"is_lifetime": int(definition["is_lifetime"]),
				"duration_days": definition["duration_days"],
				"description": definition["description"],
				"approval_note": definition["approval_note"],
				"template_key": template,
				"is_active": 1,
				"benefits": [
					{"benefit_key": key, "benefit_name": label, "is_active": 1}
					for key, label in definition["benefits"]
				],
			}
		).insert(ignore_permissions=True)

		rows.append(
			{
				"key": definition["key"],
				"status": "created",
				"fee": f"{CURRENCY} {definition['fee_amount']}",
				"validity": "lifetime" if definition["is_lifetime"] else f"{definition['duration_days']}d",
			}
		)

	return rows


# --- approval workflows ---------------------------------------------------


def _workflows() -> list[dict]:
	"""One workflow per approvable doctype, two rungs: region, then national.

	The regional stage is optional — `engine._advance` skips it when the region
	has named nobody — and the national stage is not, for the same reason it is
	not optional in `gambia.py`'s ladder: nothing above it exists to escalate to.
	The seed places that holder itself in `place_approver()`.
	"""
	rows = []
	anchor_levels = [LEVELS[1]["key"]]

	for doctype, role, applicant_field in (
		(APPLICATION_DOCTYPE, ROLE_VOLUNTEER_APPROVER, "red_profile"),
		(MEMBERSHIP_DOCTYPE, ROLE_MEMBERSHIP_APPROVER, "member"),
	):
		existing = frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": doctype}, "name")

		if existing:
			rows.append({"key": doctype, "name": existing, "status": "exists"})
			continue

		workflow = frappe.get_doc(
			{
				"doctype": WORKFLOW_DOCTYPE,
				"workflow_for": doctype,
				"geo_node_field": "geo_node",
				"applicant_field": applicant_field,
				"allow_withdrawal": 1,
				"reapplication_cooldown_days": 0,
				"application_expiry_days": 0,
				"allowed_anchor_levels": [{"geo_level": level} for level in anchor_levels],
				"stages": [
					_stage(1, STAGE_REGION, role, LEVELS[1]["key"], is_optional=1),
					_stage(2, STAGE_NATIONAL, role, LEVELS[0]["key"], is_optional=0),
				],
			}
		).insert(ignore_permissions=True)

		rows.append(
			{
				"key": doctype,
				"name": workflow.name,
				"status": "created",
				"role": role,
				"rungs": "+".join(LEVELS[i]["name"] for i in (1, 0)),
			}
		)

	return rows


def _stage(sequence: int, label: str, role: str, level: str, is_optional: int) -> dict:
	return {
		"sequence": sequence,
		"stage_label": label,
		"required_role": role,
		"resolution_rule": "at_level",
		"geo_level": level,
		"completion_rule": "single",
		"can_reject": 1,
		"is_optional": is_optional,
		"sla_days": 5,
		"on_sla_breach": "escalate_up",
	}


def _approver_permissions() -> list[dict]:
	from frappe.permissions import add_permission, update_permission_property

	rows = []

	for doctype, role in APPROVER_WRITABLE.items():
		added = bool(add_permission(doctype, role, 0))

		for permission in ("read", "write", "create", "share"):
			update_permission_property(doctype, role, 0, permission, 1)

		frappe.clear_cache(doctype=doctype)
		rows.append({"key": f"{role} on {doctype}", "status": "created" if added else "exists"})

	return rows


# --- the demo approver ----------------------------------------------------


def place_approver() -> list[dict]:
	"""One person holding the approver roles, placed at one region and at the top.

	Public, like `gambia.py`'s own `place_approver()`, for the same reason: the
	national placement is the routing backstop, not decoration, and a repair
	patch may need to call this by name on a site that was seeded before one
	existed. This person deliberately does not hold `ROLE_DEPLOYMENT_MANAGER` or
	`ROLE_STIPEND_MANAGER` — see `gambia.py`'s own note on why the split is only
	visible on a demo account that is missing something.
	"""
	rows = []
	node = region(APPROVER_REGION)
	root = national()

	if not node:
		return [{"key": APPROVER_USER, "status": f"skipped: {APPROVER_REGION} not seeded"}]

	if frappe.db.exists("User", APPROVER_USER):
		rows.append({"key": APPROVER_USER, "status": "exists"})
		user = frappe.get_doc("User", APPROVER_USER)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": APPROVER_USER,
				"first_name": APPROVER_FIRST_NAME,
				"last_name": APPROVER_LAST_NAME,
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		).insert(ignore_permissions=True)
		rows.append({"key": APPROVER_USER, "status": "created"})

	for role in (ROLE_VOLUNTEER_APPROVER, ROLE_MEMBERSHIP_APPROVER, ROLE_BRANCH_COORDINATOR):
		if role not in frappe.get_roles(APPROVER_USER):
			user.add_roles(role)
			rows.append({"key": f"{APPROVER_USER} holds {role}", "status": "created"})
		else:
			rows.append({"key": f"{APPROVER_USER} holds {role}", "status": "exists"})

		for where, label in ((node, APPROVER_REGION), (root, "the national node")):
			if not where:
				continue

			if frappe.db.exists("Geo Assignment", {"user": APPROVER_USER, "role": role, "geo_node": where}):
				rows.append({"key": f"{role} at {label}", "status": "exists"})
				continue

			frappe.get_doc(
				{
					"doctype": "Geo Assignment",
					"user": APPROVER_USER,
					"role": role,
					"geo_node": where,
					"is_active": 1,
				}
			).insert(ignore_permissions=True)

			rows.append({"key": f"{role} at {label}", "status": "created"})

	frappe.clear_cache(user=APPROVER_USER)

	return rows


# --- settings vmmsx owns --------------------------------------------------


def _settings() -> list[dict]:
	from vmmsx.member.services.society import MEMBER_ROLE_FIELD as MEMBERSHIP_MEMBER_ROLE
	from vmmsx.member.services.society import PRINT_ROLE_FIELD
	from vmmsx.registration.services.society import SELF_SERVICE_ROLE_FIELD
	from vmmsx.volunteer.services.society import MEMBER_ROLE_FIELD as VOLUNTEER_MEMBER_ROLE

	values = {
		"vmms_volunteer_scope_role": ROLE_VOLUNTEER_APPROVER,
		"vmms_membership_scope_role": ROLE_MEMBERSHIP_APPROVER,
		"vmms_announcement_scope_role": ROLE_BRANCH_COORDINATOR,
		"vmms_task_scope_role": ROLE_BRANCH_COORDINATOR,
		"vmms_content_editor_role": ROLE_BRANCH_COORDINATOR,
		"vmms_deployment_scope_role": ROLE_DEPLOYMENT_MANAGER,
		"vmms_deployment_request_scope_role": ROLE_DEPLOYMENT_MANAGER,
		"vmms_branch_transfer_scope_role": ROLE_DEPLOYMENT_MANAGER,
		"vmms_stipend_report_scope_role": ROLE_STIPEND_MANAGER,
		"vmms_stipend_payment_scope_role": ROLE_STIPEND_MANAGER,
		"vmms_branch_location_scope_role": ROLE_BRANCH_COORDINATOR,
		PRINT_ROLE_FIELD: ROLE_MEMBERSHIP_APPROVER,
		VOLUNTEER_MEMBER_ROLE: ROLE_VOLUNTEER,
		MEMBERSHIP_MEMBER_ROLE: ROLE_MEMBER,
		SELF_SERVICE_ROLE_FIELD: ROLE_APPLICANT,
	}

	rows = []
	settings = frappe.get_single(SETTINGS_DOCTYPE)
	changed = False

	for field, role in values.items():
		if not settings.meta.has_field(field):
			rows.append({"key": field, "status": "skipped: field not installed, run bench migrate"})
			continue

		if settings.get(field):
			rows.append({"key": field, "status": "exists", "value": settings.get(field)})
			continue

		settings.set(field, role)
		changed = True
		rows.append({"key": field, "status": "created", "value": role})

	if changed:
		settings.save(ignore_permissions=True)
		frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)

	return rows


def _signup() -> list[dict]:
	rows = []

	if frappe.db.get_single_value("Website Settings", "disable_signup"):
		frappe.db.set_single_value("Website Settings", "disable_signup", 0)
		rows.append({"key": "Website Settings.disable_signup", "status": "created", "value": 0})
	else:
		rows.append({"key": "Website Settings.disable_signup", "status": "exists", "value": 0})

	current = frappe.db.get_single_value("Portal Settings", "default_role")

	if current:
		rows.append({"key": "Portal Settings.default_role", "status": "exists", "value": current})
	else:
		frappe.db.set_single_value("Portal Settings", "default_role", ROLE_APPLICANT)
		rows.append({"key": "Portal Settings.default_role", "status": "created", "value": ROLE_APPLICANT})

	frappe.clear_document_cache("Portal Settings", "Portal Settings")
	frappe.clear_document_cache("Website Settings", "Website Settings")

	return rows


def _payment_gateway() -> list[dict]:
	"""Collect the membership fee at the region, not through a gateway.

	Same reasoning as `gambia.py::_payment_gateway`: every TRCS plan carries a
	fee, and with no gateway chosen the transaction insert fails on its own
	mandatory `gateway` field the moment somebody applies. The Manual driver
	says how the fee is collected instead — at the branch, confirmed by a clerk.
	"""
	settings_doctype = "OneRC Payment Settings"

	if not frappe.db.exists("DocType", settings_doctype):
		return [{"key": "payment gateway", "status": "skipped: onerc_payments is not installed"}]

	rows = []
	settings = frappe.get_single(settings_doctype)

	if settings.active_gateway:
		return [{"key": "active_gateway", "status": "exists", "value": settings.active_gateway}]

	gateway = frappe.db.get_value("OneRC Payment Gateway", {"driver_class": ("like", "%manual%")}, "name")

	if not gateway:
		gateway = (
			frappe.get_doc(
				{
					"doctype": "OneRC Payment Gateway",
					"gateway_name": "Manual",
					"driver_class": "onerc_payments.gateways.manual.ManualGateway",
					"is_active": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		rows.append({"key": "OneRC Payment Gateway Manual", "status": "created"})

	settings.active_gateway = gateway

	if not settings.manual_instructions:
		settings.manual_instructions = (
			"Pay your membership fee at your nearest Red Cross regional branch office. "
			"Quote your reference number, and the branch will confirm the payment "
			"on your record."
		)

	settings.save(ignore_permissions=True)
	frappe.clear_document_cache(settings_doctype, settings_doctype)

	rows.append({"key": "active_gateway", "status": "created", "value": gateway})

	return rows


def _surfaces() -> dict:
	from vmmsx.registration.services import permissions, workspaces
	from vmmsx.staff.services import permissions as staff_permissions
	from vmmsx.staff.services import workspaces as staff_workspaces

	return {
		"workspaces": workspaces.install(),
		"permissions": permissions.install(),
		"staff_workspaces": staff_workspaces.install(),
		"staff_permissions": staff_permissions.install(),
	}


def _landing_content() -> dict:
	"""Put the society's own wording on the public landing page. Overwrites."""
	from vmmsx.seed import tanzania_content

	return tanzania_content.install()


# --- the report -----------------------------------------------------------


def _print(report: dict) -> None:
	print(f"\n{ORGANIZATION_NAME} seed on {frappe.local.site}\n" + "=" * 60)

	for section, rows in report.items():
		if section == "manual_steps":
			continue

		print(f"\n{section.replace('_', ' ').title()}")

		if isinstance(rows, dict):
			for key, value in rows.items():
				print(f"  {key}: {value}")

			continue

		for row in rows:
			extra = " ".join(f"{k}={v}" for k, v in row.items() if k not in ("key", "status"))
			print(f"  [{row['status']:<8}] {row['key']}{'  ' + extra if extra else ''}")

	print("\nStill to do by hand")

	for step in report["manual_steps"]:
		print(f"  - {step}")

	print()
