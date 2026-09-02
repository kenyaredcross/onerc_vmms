# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A worked Kenya Red Cross Society configuration. Data, never behaviour.

    bench --site <site> execute vmmsx.seed.kenya.main

**Everything here is data.** Roles, geo levels, geo nodes, membership types,
approval workflows and settings values are all records a society creates in the
desk, and this module creates the ones a Kenyan society would so that a demo,
a training environment or a fresh developer bench has something real to work
against. Not one line of it is imported by the app: no source file outside this
package names "Kenya", "County", "Branch", "Ordinary", "Volunteer Approver" or
any other value below, and deleting this package would leave vmmsx working
exactly as it does now, configured by whoever installs it.

That is the whole point of the split the app has held from the start. The
universal rules are code; the answers are configuration; a second society is a
second seed and no diff at all.

**Idempotent, and it says what it did.** Every step checks before it writes and
reports `created` or `exists`, so running it twice changes nothing and running it
on a site somebody has since edited overwrites none of their edits. The one
thing it will not do is guess: a setting an administrator has already filled in
is left as they left it.

**What it deliberately does not do.**

* **The logo is not seeded.** Core stores it as an uploaded file, and inventing
  one would put a placeholder on every certificate the society issues. The
  report says so, out loud, every run.
* **No certification type and no course mapping.** Those name real
  qualifications and real courses, and neither this app nor this seed has any
  business inventing them.
* **No ACC-03 anchor level is narrowed.** The society settings that constrain
  where a volunteer or a membership may sit are left empty, which means
  unconstrained. What *is* constrained is the approval workflows'
  `allowed_anchor_levels`, because that is where the demo shows the rule.
"""

import frappe

from vmmsx.registration.services.desk import PORTAL_HOME

SETTINGS_DOCTYPE = "National Society Settings"

# --- the society ----------------------------------------------------------

ORGANIZATION_NAME = "Kenya Red Cross Society"
ORGANIZATION_SHORT_NAME = "KRCS"
COUNTRY = "Kenya"
CURRENCY = "KES"
LANGUAGE = "en"
TIME_ZONE = "Africa/Nairobi"

# What people here speak, as against what the desk is translated into. Frappe's
# shipped Language list is the latter and holds none of these but Kiswahili,
# which is why a volunteer form reading it alone had nothing to offer somebody
# whose first language is Dholuo. Codes are ISO 639; the labels are how each
# language names itself, the way Frappe's own rows do.
SPOKEN_LANGUAGES = (
	("ki", "Gĩkũyũ"),
	("luo", "Dholuo"),
	("kam", "Kikamba"),
	("kln", "Kalenjin"),
	("luy", "Luluhya"),
	("guz", "Ekegusii"),
	("mer", "Kĩmĩrũ"),
	("so", "Soomaali"),
	("mas", "Maa"),
	("tuv", "Ng'aturkana"),
)

# --- the hierarchy --------------------------------------------------------
#
# Three levels, named as this society names them. Another society's seed names
# three different ones, or five, and no code changes.

LEVELS = (
	{"key": "krcs-national", "name": "National", "order": 1, "requires_parent": 0, "is_lowest": 0},
	{"key": "krcs-county", "name": "County", "order": 2, "requires_parent": 1, "is_lowest": 0},
	{"key": "krcs-branch", "name": "Branch", "order": 3, "requires_parent": 1, "is_lowest": 1},
)

NATIONAL_NODE = "Kenya Red Cross Society"
COUNTY_NODES = ("Nairobi", "Mombasa")
# Both branches sit under the first county, so that nearest-ancestor routing has
# something to walk: the approver is placed at the county, and an application
# made at a branch has to find them one level up.
BRANCH_NODES = ("Nairobi Central", "Nairobi West")

# --- roles ----------------------------------------------------------------
#
# Names a society chose, and for each of them the one thing that is not a name:
# whether holding it makes an account a desk user. Frappe derives `user_type`
# from `desk_access`, so this is the difference between somebody who works on
# the society's records and somebody the society keeps a record of.
#
# The approvers work on the desk. The volunteer, the member and the applicant do
# not: their surface is the portal, and `registration/services/desk.py` keeps
# these three closed on every migrate for whichever roles a society has named in
# its settings, whatever they are called.

ROLE_VOLUNTEER_APPROVER = "Volunteer Approver"
ROLE_MEMBERSHIP_APPROVER = "Membership Approver"
# Deployments, terms of reference and projects postdate the rest of this
# file's role table, the same reason `VMMS Project` postdates
# `kenya_operations.py`'s terms of reference. Named separately from the two
# approver roles above rather than folded into one of them, the same reasoning
# `gambia.py`'s `ROLE_DEPLOYMENT_MANAGER` states: "who may see the register" and
# "who sends people out" are different questions even where one demo account
# answers both.
ROLE_DEPLOYMENT_MANAGER = "Deployment Manager"
ROLE_VOLUNTEER = "Volunteer"
ROLE_MEMBER = "Member"
ROLE_APPLICANT = "Society Applicant"

# (name, description, desk_access)
ROLES = (
	(ROLE_VOLUNTEER_APPROVER, "Reviews volunteer applications for the area they are assigned to.", True),
	(ROLE_MEMBERSHIP_APPROVER, "Reviews memberships that a membership type routes for approval.", True),
	(
		ROLE_DEPLOYMENT_MANAGER,
		"Sends people out: projects, terms of reference, deployments and deployment requests.",
		True,
	),
	(ROLE_VOLUNTEER, "An accepted volunteer, seeing their own record and nobody else's.", False),
	(
		ROLE_MEMBER,
		"An active member, seeing their own memberships and printing their own certificate.",
		False,
	),
	(ROLE_APPLICANT, "Somebody with an account who has not registered as anything yet.", False),
)

# --- membership types -----------------------------------------------------

TYPE_ORDINARY = "ordinary"
TYPE_LIFE = "life"

MEMBERSHIP_TYPES = (
	{
		"key": TYPE_ORDINARY,
		"name": "Ordinary",
		"approval_mode": "auto_on_payment",
		"fee_amount": 1000,
		"is_lifetime": False,
		"duration_days": 365,
		"description": "Annual membership, open to anybody. Active as soon as the fee is confirmed.",
		"approval_note": (
			"Nobody approves an ordinary membership. Paying the fee is the act of joining, and the"
			" membership activates on confirmation."
		),
		"benefits": (
			("newsletter", "Society newsletter"),
			("events", "Member rate at society events"),
			("agm", "Vote at the annual general meeting"),
		),
	},
	{
		"key": TYPE_LIFE,
		"name": "Life Member",
		"approval_mode": "routed",
		"fee_amount": 0,
		# A life membership does not expire, so it carries no duration at all.
		# It was previously seeded as 3650 days, which is a life membership that
		# quietly lapses after ten years — the sort of stand-in that works right
		# up until the society it was demonstrated to has been running for a
		# decade.
		"is_lifetime": True,
		"duration_days": 0,
		"description": "Conferred by a branch in recognition of service. Reviewed, not bought, and never expires.",
		"approval_note": (
			"Routed to a membership approver, and carries no fee, so the approval alone activates"
			" it. That is the point of the two modes: which one applies is this field, not a name"
			" anywhere in the code. Marked as a lifetime type, so it activates with a start date"
			" and no end date and the daily expiry sweep never selects it."
		),
		"benefits": (
			("newsletter", "Society newsletter"),
			("events", "Guest rate at society events"),
			("agm", "Vote at the annual general meeting"),
			("recognition", "Named in the society's roll of life members"),
		),
	},
)

CERTIFICATE_TEMPLATE_KEY = "membership_certificate"

# --- approval workflows ---------------------------------------------------

APPLICATION_DOCTYPE = "VMMS Volunteer Application"
MEMBERSHIP_DOCTYPE = "VMMS Membership"
WORKFLOW_DOCTYPE = "VMMS Approval Workflow"
# ERPNext's own, adopted as the programme of work; `VMMS Project` was retired.
# Still in this table for the same reason the other three are: a role holding a
# Geo Assignment and nothing else fails `frappe.get_list`'s own permission check
# before geo scoping ever gets a say, and Project's shipped rows are ERPNext's
# accounting audience rather than a volunteering one.
PROJECT_DOCTYPE = "Project"
TERMS_DOCTYPE = "VMMS Terms of Reference"
DEPLOYMENT_DOCTYPE = "VMMS Deployment"
REQUEST_DOCTYPE = "VMMS Deployment Request"

# The doctypes a society role has to be able to write for the engine to record a
# decision on its behalf: acting on an approval saves the governed document. The
# shipped JSONs grant only System Manager, deliberately, because which society
# role gets this is configuration. This is that configuration.
#
# The four deployment doctypes below are not approval-governed and are here for
# a related but distinct reason: `vmms_deployment_scope_role` and its two
# siblings only narrow a read `frappe.get_list` was already going to run — they
# are not, by themselves, read permission. A role holding only a Geo Assignment
# and none of this fails `frappe.get_list`'s own permission check before the
# geo scope condition ever gets a say, which is what an empty console (or a
# raw Permission Error) on a site seeded before this line existed would mean.
APPROVER_WRITABLE = {
	APPLICATION_DOCTYPE: ROLE_VOLUNTEER_APPROVER,
	MEMBERSHIP_DOCTYPE: ROLE_MEMBERSHIP_APPROVER,
	PROJECT_DOCTYPE: ROLE_DEPLOYMENT_MANAGER,
	TERMS_DOCTYPE: ROLE_DEPLOYMENT_MANAGER,
	DEPLOYMENT_DOCTYPE: ROLE_DEPLOYMENT_MANAGER,
	REQUEST_DOCTYPE: ROLE_DEPLOYMENT_MANAGER,
}

# --- the demo approver ----------------------------------------------------

APPROVER_USER = "approver@krcs.demo"
APPROVER_FIRST_NAME = "Wanjiru"
APPROVER_LAST_NAME = "Kamau"


def main(commit: bool = True) -> dict:
	"""Seed the whole society and report what changed. Safe to re-run.

	`commit` is on for the ordinary `bench execute` path, where a seed that did
	not persist would be a seed that did nothing. It is turned off by the test
	that runs this seed for real, because committing inside a test would escape
	the transaction the runner rolls back and leave the demo society sitting on
	whatever site the suite happened to run against.
	"""
	report = {
		"roles": _roles(),
		"geo_levels": _geo_levels(),
		"geo_nodes": _geo_nodes(),
		"society": _society(),
		"spoken_languages": _spoken_languages(),
		"membership_types": _membership_types(),
		"workflows": _workflows(),
		"approver_permissions": _approver_permissions(),
		"approver": _approver(),
		"settings": _settings(),
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
	"Upload the society logo on National Society Settings. It is an Attach Image and a seed"
	" cannot invent a file; until it is uploaded, certificates render without a mark.",
	f"Set a password for {APPROVER_USER} (bench set-password, or the desk) before signing in as them.",
	"Activate a gateway in OneRC Payment Settings if you want the fee-bearing membership type to"
	" work. The Manual driver is enough for a demo. That is another app's configuration and this"
	" seed deliberately does not write it.",
)


# --- roles ----------------------------------------------------------------


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
				# The whole of what separates a coordinator's account from a
				# volunteer's. Frappe promotes an account to System User the moment
				# it holds a role with this on, so it is switched on only for the
				# people who work on the desk. See the note above the table.
				"desk_access": int(desk),
				# Where a portal role lands after signing in. Without it the
				# framework falls through to Portal Settings, which on a site set
				# up for the desk says `/desk` — a Website User sent to a
				# permission error. Kept in step with `desk.py`, which repairs it
				# on every migrate for whichever roles the settings name.
				"home_page": None if desk else PORTAL_HOME,
				"description": description,
			}
		).insert(ignore_permissions=True)

		rows.append({"key": name, "status": "created"})

	return rows


# --- geo ------------------------------------------------------------------


def _geo_levels() -> list[dict]:
	rows = []

	for level in LEVELS:
		if frappe.db.exists("Geo Level", level["key"]):
			rows.append({"key": level["key"], "status": "exists"})
			continue

		# Core permits at most one *active* lowest level per site. A bench that
		# already has one from another society's data is not this seed's to
		# overrule, so the flag is dropped and the fact reported rather than the
		# insert being allowed to throw.
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
	"""One national root, two counties, two branches under the first county.

	Docnames are opaque (`GEO-.#####`), so idempotence is a lookup on the shape
	of the row rather than on its name: a node is the same node when its label,
	its level and its parent all match.
	"""
	rows = []
	national, created = _node(NATIONAL_NODE, LEVELS[0]["key"], None, is_group=True)
	rows.append({"key": NATIONAL_NODE, "name": national, "status": created})

	counties = []

	for label in COUNTY_NODES:
		name, created = _node(label, LEVELS[1]["key"], national, is_group=True)
		counties.append(name)
		rows.append({"key": label, "name": name, "status": created})

	for label in BRANCH_NODES:
		name, created = _node(label, LEVELS[2]["key"], counties[0])
		rows.append({"key": label, "name": name, "status": created})

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


def county(index: int = 0) -> str | None:
	"""The seeded county at `index`, by shape. Used by the approver's placement."""
	national = frappe.db.get_value(
		"Geo Node", {"geo_node_name": NATIONAL_NODE, "geo_level": LEVELS[0]["key"]}, "name"
	)

	return frappe.db.get_value(
		"Geo Node",
		{"geo_node_name": COUNTY_NODES[index], "geo_level": LEVELS[1]["key"], "parent_geo_node": national},
		"name",
	)


def branch(index: int = 0) -> str | None:
	"""The seeded branch at `index`, by shape. Used by the walkthrough and tests."""
	return frappe.db.get_value(
		"Geo Node", {"geo_node_name": BRANCH_NODES[index], "geo_level": LEVELS[2]["key"]}, "name"
	)


# --- the society single ---------------------------------------------------


def _society() -> list[dict]:
	"""Fill in the society's own identity, without overwriting an edit.

	Every field is set only when it is empty, because a seed re-run on a live
	site must not rename somebody's society back to the demo's answer.
	"""
	settings = frappe.get_single(SETTINGS_DOCTYPE)
	rows = []

	values = {
		"organization_name": ORGANIZATION_NAME,
		"organization_short_name": ORGANIZATION_SHORT_NAME,
		"country": COUNTRY if frappe.db.exists("Country", COUNTRY) else None,
		"currency": CURRENCY if frappe.db.exists("Currency", CURRENCY) else None,
		"primary_language": LANGUAGE if frappe.db.exists("Language", LANGUAGE) else None,
		"time_zone": TIME_ZONE,
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

	rows.append({"key": "logo", "status": "manual: upload it yourself"})

	return rows


# --- the languages people here actually speak -----------------------------


def _spoken_languages() -> list[dict]:
	"""Add the languages a Kenyan volunteer would name, if the site lacks them.

	Frappe ships a Language list built for translating an interface, so it holds
	Kiswahili but nothing else spoken here. A volunteer declaring what they speak
	is answering a different question, and a form that could not accept "Dholuo"
	was one a coordinator could not staff a Kisumu deployment from.

	`enabled` stays off on purpose: that flag means "this site's interface is
	offered in this language", which none of these is, and the volunteer form no
	longer reads it (`api/volunteer.py::_languages`).
	"""
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


# --- membership types -----------------------------------------------------


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
				"mode": definition["approval_mode"],
				"fee": definition["fee_amount"],
				# The seed's report is read in a terminal as key=value pairs, so
				# this stays one token.
				"validity": "lifetime" if definition["is_lifetime"] else f"{definition['duration_days']}d",
			}
		)

	return rows


# --- approval workflows ---------------------------------------------------


def _workflows() -> list[dict]:
	"""One workflow per approvable doctype, each with one stage that can reject.

	Both resolve `nearest_ancestor`: an application made at a branch walks up
	until it finds somebody holding the stage's role, which is the county here.
	Neither names a level in code; `allowed_anchor_levels` is where this society
	says where a record may sit, and it is ACC-03 in data.
	"""
	rows = []
	anchor_levels = [LEVELS[1]["key"], LEVELS[2]["key"]]

	for doctype, role, applicant_field, label in (
		(APPLICATION_DOCTYPE, ROLE_VOLUNTEER_APPROVER, "red_profile", "Branch Review"),
		(MEMBERSHIP_DOCTYPE, ROLE_MEMBERSHIP_APPROVER, "member", "Membership Review"),
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
					{
						"sequence": 1,
						"stage_label": label,
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
		).insert(ignore_permissions=True)

		rows.append({"key": doctype, "name": workflow.name, "status": "created", "role": role})

	return rows


def _approver_permissions() -> list[dict]:
	"""Grant each role in `APPROVER_WRITABLE` ordinary access to its doctype.

	Two reasons live in the one dict: recording a decision saves the governed
	document, so an approval stage's role needs write on it; a deployment scope
	role needs read for a different reason, stated where `APPROVER_WRITABLE` is
	built. Added as Custom DocPerms, which is what an administrator does in the
	Role Permissions Manager.
	"""
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


def _approver() -> list[dict]:
	"""One person holding all three staff roles, placed at the first county.

	Placed with `Geo Assignment`, which is core's answer to *where*: holding
	the role is not authority anywhere, and holding it at Nairobi is authority
	over Nairobi and everything beneath it. The two questions stay separate,
	which is the access model this app is built on.
	"""
	rows = []
	node = county(0)

	if not node:
		return [{"key": APPROVER_USER, "status": "skipped: no county seeded"}]

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

	for role in (ROLE_VOLUNTEER_APPROVER, ROLE_MEMBERSHIP_APPROVER, ROLE_DEPLOYMENT_MANAGER):
		if role not in frappe.get_roles(APPROVER_USER):
			user.add_roles(role)
			rows.append({"key": f"{APPROVER_USER} holds {role}", "status": "created"})
		else:
			rows.append({"key": f"{APPROVER_USER} holds {role}", "status": "exists"})

		assignment = frappe.db.exists(
			"Geo Assignment", {"user": APPROVER_USER, "role": role, "geo_node": node}
		)

		if assignment:
			rows.append({"key": f"{role} at {node}", "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": "Geo Assignment",
				"user": APPROVER_USER,
				"role": role,
				"geo_node": node,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		rows.append({"key": f"{role} at {node} ({COUNTY_NODES[0]})", "status": "created"})

	frappe.clear_cache(user=APPROVER_USER)

	return rows


# --- settings vmmsx owns --------------------------------------------------


def _settings() -> list[dict]:
	"""Point every role setting this app owns at a role that really exists.

	All ship empty and empty fails closed, which is right for an app nobody
	has configured and useless for a demo: an unconfigured scope role means no
	approver can open the application routed to them. This is a society making
	its choices, and every one of them is a value in this file rather than a
	default anywhere in the source.

	The volunteer and membership scope roles are pointed at the approver roles
	here, which keeps the demo to one role per job. A larger society would
	separate them, because "who may see the register" and "who decides an
	application" are genuinely different questions and the app keeps them in
	different settings for exactly that reason. The three deployment-related
	settings are pointed at `ROLE_DEPLOYMENT_MANAGER` instead — see the note on
	that role — even though the demo hands both to the same person.
	"""
	from vmmsx.member.services.society import MEMBER_ROLE_FIELD as MEMBERSHIP_MEMBER_ROLE
	from vmmsx.member.services.society import PRINT_ROLE_FIELD
	from vmmsx.registration.services.society import SELF_SERVICE_ROLE_FIELD
	from vmmsx.volunteer.services.society import MEMBER_ROLE_FIELD as VOLUNTEER_MEMBER_ROLE

	values = {
		"vmms_volunteer_scope_role": ROLE_VOLUNTEER_APPROVER,
		"vmms_membership_scope_role": ROLE_MEMBERSHIP_APPROVER,
		# Ship empty otherwise, per `deployment/services/society.py`'s own
		# docstring — which means nobody but an administrator could open the
		# console's Deployments tab on a site seeded before this line existed.
		"vmms_deployment_scope_role": ROLE_DEPLOYMENT_MANAGER,
		"vmms_deployment_request_scope_role": ROLE_DEPLOYMENT_MANAGER,
		"vmms_branch_transfer_scope_role": ROLE_DEPLOYMENT_MANAGER,
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
	"""Let people make their own accounts, and say what a new one is.

	Two native records and nothing else: Website Settings decides whether signup
	is offered at all, and Portal Settings decides which role a self-registered
	account is given. Pointing the second at the same role the landing workspace
	names is what closes the loop between "I made an account" and "here are the
	two things I may do".
	"""
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


def _surfaces() -> dict:
	"""Build the workspaces and permissions now that the roles exist.

	The same call `after_migrate` makes. It is here as well because the roles
	were only chosen a few lines ago, and a surface naming a role has to be
	built after somebody has said which role.
	"""
	from vmmsx.registration.services import permissions, workspaces
	from vmmsx.staff.services import permissions as staff_permissions
	from vmmsx.staff.services import workspaces as staff_workspaces

	# The staff half too, and for the reason `gambia.py::_surfaces` sets out: the
	# installers also run from `after_migrate`, where a fresh site's scope-role
	# settings are still empty, so the grants have to be re-run once this seed
	# has named the roles. Otherwise a coordinator holds a role that permits
	# nothing.
	return {
		"workspaces": workspaces.install(),
		"permissions": permissions.install(),
		"staff_workspaces": staff_workspaces.install(),
		"staff_permissions": staff_permissions.install(),
	}


def _landing_content() -> dict:
	"""Put the Kenya wording and photography on the public landing page.

	The one step of this seed that deliberately **overwrites**. Everything else
	here leaves an administrator's edits alone, but somebody running the Kenya
	seed is asking to see the Kenya page, and a page half in the product's
	neutral voice would be nobody's idea of a worked example. The copy itself is
	`kenya_content.py`, beside this file, because a wall of marketing prose in
	the middle of the geo and role configuration helps no one read either.
	"""
	from vmmsx.seed import kenya_content

	return kenya_content.install()


# --- the report -----------------------------------------------------------


def _print(report: dict) -> None:
	"""Say what happened, in a shape somebody can read in a terminal."""
	print(f"\nKenya Red Cross Society seed on {frappe.local.site}\n" + "=" * 60)

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
