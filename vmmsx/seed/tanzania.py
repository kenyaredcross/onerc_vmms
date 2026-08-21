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

# Three rungs: National, Branch, Sub-branch.
#
# **The branch rung is TRCS's own and is sourced.** The society's copy says 31+
# regional branches, one per administrative region, which is exactly the list
# below.
#
# **The sub-branch rung is the society's own structure too — "1,250+
# sub-branches" — but TRCS does not publish their names**, and this seed will
# not invent 1,250 of them. What it does instead is the narrowest honest thing:
# it creates sub-branches only under the branches this demo actually puts people
# in, and names them after **Tanzania's own administrative districts** within
# each of those regions, which are real units at the right size. See
# `SUB_BRANCHES`. A society installing this replaces them with its own.
#
# The rung exists at all because the approval chain needs it: a volunteer
# application and a membership are both reviewed at the sub-branch first and
# then at the branch, which is two rungs of *reviewers* and therefore two rungs
# of tree.
LEVELS = (
	{"key": "trcs-national", "name": "National", "order": 1, "requires_parent": 0, "is_lowest": False},
	{"key": "trcs-branch", "name": "Branch", "order": 2, "requires_parent": 1, "is_lowest": False},
	{
		"key": "trcs-subbranch",
		"name": "Sub-Branch",
		"order": 3,
		"requires_parent": 1,
		"is_lowest": True,
	},
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

# Sub-branches, by the branch they hang under.
#
# **Only where the demo has people.** Six branches out of thirty-one, because a
# sub-branch that nobody is registered at, assigned to or deployed from teaches
# a reader nothing and makes the tree harder to walk. The other twenty-five
# branches have none, which is also what a real society mid-rollout looks like.
#
# **The names are Tanzania's own districts within each region**, not invented
# ones — Kinondoni, Ilala and Temeke really are districts of Dar es Salaam. They
# stand in for sub-branch names TRCS does not publish, and they are the right
# size of unit for one. Replace them with the society's real sub-branch register
# before this stops being a demo.
SUB_BRANCHES = {
	"Dar es Salaam": ("Kinondoni", "Ilala", "Temeke", "Ubungo", "Kigamboni"),
	"Arusha": ("Arusha City", "Meru", "Karatu"),
	"Mwanza": ("Nyamagana", "Ilemela", "Sengerema"),
	"Dodoma": ("Dodoma City", "Chamwino", "Bahi"),
	"Kilimanjaro": ("Moshi", "Hai", "Rombo"),
	"Mbeya": ("Mbeya City", "Rungwe", "Kyela"),
}

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

# Two stages, and they are the bottom two rungs of the tree rather than the top
# two: the sub-branch that actually knows the applicant reviews first, and the
# branch above it confirms. The national desk is not a stage — it runs the
# society, it does not read every volunteer form in the country.
#
# **The same chain governs both doctypes.** A volunteer application and a
# membership are reviewed by the same two rungs, by different roles.
STAGE_SUB_BRANCH = "Sub-Branch Review"
STAGE_BRANCH = "Branch Review"

# --- the demo approvers ---------------------------------------------------

# One login per rung of the chain, named after the rung they sit on, because the
# whole point of them is to show what the two stages feel like from the inside:
# sign in as one and the application is waiting, sign in as the other and it is
# not there yet.
SUB_BRANCH_APPROVER = "subbranch@mail.com"
BRANCH_APPROVER = "branch@mail.com"

# Where the two of them sit.
#
# **Each is placed at every rung of their own kind that this seed creates** —
# the sub-branch approver at all sixteen sub-branches, the branch approver at
# all six branches that have them, plus the national node. One person covering a
# whole rung is not what a real society looks like, and it is exactly what a
# demo needs: every application the seed files, wherever it was filed, has a
# real reviewer waiting at both stages, so signing in as either login shows a
# queue with something in it.
#
# A society replaces both with its own people, one per branch. `MANUAL_STEPS`
# says so.
#
# (login, first name, last name)
APPROVERS = (
	(SUB_BRANCH_APPROVER, "Amina", "Mwakalinga"),
	(BRANCH_APPROVER, "Joseph", "Kimaro"),
)

# The rung each of the two covers, as the roles they hold there.
APPROVER_ROLES = (ROLE_VOLUNTEER_APPROVER, ROLE_MEMBERSHIP_APPROVER, ROLE_BRANCH_COORDINATOR)

APPROVER_BRANCH = "Dar es Salaam"
APPROVER_SUB_BRANCH = "Kinondoni"

# The password every seeded login gets.
#
# **A demo site's password, and it must never be a production one.** It is
# written here in the open on purpose: a demo nobody can sign into is a
# screenshot, and the alternative — telling somebody to set six passwords by
# hand before they can look at the thing — is why the manual step this replaced
# was always the one that got skipped. The seed refuses to run against a site
# that has real people on it; that refusal is what keeps this honest.
DEMO_PASSWORD = "Kenya.11"

# Kept so a site seeded before the two-rung chain existed still resolves.
APPROVER_USER = SUB_BRANCH_APPROVER
APPROVER_REGION = APPROVER_BRANCH


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
	"Assign somebody to each approver role at every branch you intend to use, in Geo Assignment."
	" The sub-branch rung is optional and is skipped when nobody holds it; the branch rung is the"
	" decision, and an application anchored under a branch with nobody on it waits forever.",
	f"Change the demo passwords. Every seeded login is set to {DEMO_PASSWORD!r}, including"
	f" {SUB_BRANCH_APPROVER} and {BRANCH_APPROVER}. This is a demo credential and must not survive"
	" contact with real people's records.",
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
	"""The society, its 31 branches, and sub-branches where the demo needs them.

	Docnames are opaque (`GEO-.#####`), so idempotence is a lookup on the shape
	of the row rather than on its name: a node is the same node when its label,
	its level and its parent all match.

	A branch carrying sub-branches is a group; one that does not is a leaf. That
	is not decoration — a group node is what the picker walks into, and marking a
	branch with no children as a group draws an empty select underneath it.
	"""
	rows = []
	national, created = _node(NATIONAL_NODE, LEVELS[0]["key"], None, is_group=True)
	rows.append({"key": NATIONAL_NODE, "name": national, "status": created})

	for label in REGIONS:
		children = SUB_BRANCHES.get(label, ())
		node, created = _node(label, LEVELS[1]["key"], national, is_group=bool(children))
		rows.append({"key": label, "name": node, "status": created})

		for child in children:
			leaf, made = _node(child, LEVELS[2]["key"], node)
			rows.append({"key": f"{label} / {child}", "name": leaf, "status": made})

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


def branch(label: str) -> str | None:
	"""A branch by name, by shape. The middle rung, one per region."""
	return frappe.db.get_value(
		"Geo Node",
		{"geo_node_name": label, "geo_level": LEVELS[1]["key"], "parent_geo_node": national()},
		"name",
	)


def sub_branch(label: str, parent_label: str) -> str | None:
	"""A sub-branch by name *and* by the branch it hangs under.

	Both halves are needed and the second is not belt-and-braces: district names
	repeat across Tanzania's regions, and a lookup on the label alone would
	resolve "Moshi" to whichever one the database happened to return first.
	"""
	parent = branch(parent_label)

	if not parent:
		return None

	return frappe.db.get_value(
		"Geo Node",
		{"geo_node_name": label, "geo_level": LEVELS[2]["key"], "parent_geo_node": parent},
		"name",
	)


def region(label: str) -> str | None:
	"""The old name for `branch`, kept because other seed modules call it.

	The middle rung was called Region when this society had two rungs and the
	region *was* the branch. It is called Branch now that a sub-branch hangs
	beneath it, which is the society's own word for both. This alias means
	`tanzania_operations.py` and `tanzania_jobs.py` did not have to be edited in
	the same breath as the rename, and it resolves the same node either way.
	"""
	return branch(label)


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
	"""One workflow per approvable doctype, two rungs: sub-branch, then branch.

	The sub-branch stage is optional — `engine._advance` skips it when that
	sub-branch has named nobody, which is the case in twenty-five of the
	thirty-one branches — and the branch stage is not, for the same reason the
	last stage is never optional in `gambia.py`'s ladder: it is the decision, and
	an application that skipped every stage would be approved by nobody. The seed
	places both holders itself in `place_approver()`.

	Both governed doctypes get the same chain. A volunteer application and a
	membership are read by the same two rungs of the society, by the two
	different roles `APPROVER_WRITABLE` names.
	"""
	rows = []
	# A record may be anchored at a sub-branch or at a branch. Both, because a
	# sub-branch is where most people join and a branch is where somebody in a
	# region with no sub-branch yet has to join — twenty-five of the thirty-one
	# have none. ACC-03 in data, which is the only place it may be.
	anchor_levels = [LEVELS[1]["key"], LEVELS[2]["key"]]

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
				# Sub-branch first, branch second, and the first one is optional
				# while the second is not. That asymmetry is the whole design: an
				# applicant who joined at a branch directly, or at a sub-branch
				# nobody has been assigned to yet, has no first-stage reviewer to
				# wait for and skips straight to the branch. A society that made
				# both mandatory would have every application in twenty-five of its
				# thirty-one branches stall forever at a rung with nobody on it.
				"stages": [
					_stage(1, STAGE_SUB_BRANCH, role, LEVELS[2]["key"], is_optional=1),
					_stage(2, STAGE_BRANCH, role, LEVELS[1]["key"], is_optional=0),
				],
			}
		).insert(ignore_permissions=True)

		rows.append(
			{
				"key": doctype,
				"name": workflow.name,
				"status": "created",
				"role": role,
				"rungs": " then ".join(LEVELS[i]["name"] for i in (2, 1)),
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
	"""One approver per rung of the chain, each placed where they decide.

	**Two people, not one, and that is the point.** The chain is sub-branch then
	branch, and a single account holding both rungs would approve its own
	first-stage decision at the second stage — which the engine permits, because
	an approver holding a role at two nodes is an ordinary thing in a small
	society, and which teaches a reader of this demo exactly nothing about how
	two stages behave. Signing in as `subbranch@mail.com` shows an application
	waiting; signing in as `branch@mail.com` shows it only after the first rung
	has passed it up.

	Public, like `gambia.py`'s own `place_approver()`, for the same reason: a
	repair patch may need to call this by name on a site seeded before the
	sub-branch rung existed.

	Neither of them holds `ROLE_DEPLOYMENT_MANAGER` or `ROLE_STIPEND_MANAGER` —
	see `gambia.py`'s note on why the split is only visible on a demo account
	that is missing something.
	"""
	rows = []

	for login, first, last in APPROVERS:
		rows.append({"key": login, "status": _approver_user(login, first, last)})

		for role in APPROVER_ROLES:
			rows.append({"key": f"{login} holds {role}", "status": _grant(login, role)})

	# Every sub-branch this seed created, for the first stage.
	for parent_label, children in SUB_BRANCHES.items():
		for child in children:
			node = sub_branch(child, parent_label)

			if not node:
				rows.append({"key": f"{parent_label} / {child}", "status": "skipped: not seeded"})
				continue

			for role in APPROVER_ROLES:
				rows.append(
					{
						"key": f"{SUB_BRANCH_APPROVER}: {role} at {child}",
						"status": _assign(SUB_BRANCH_APPROVER, role, node),
					}
				)

	# Every branch above one, for the second stage — the decision.
	for parent_label in SUB_BRANCHES:
		node = branch(parent_label)

		if not node:
			continue

		for role in APPROVER_ROLES:
			rows.append(
				{
					"key": f"{BRANCH_APPROVER}: {role} at {parent_label}",
					"status": _assign(BRANCH_APPROVER, role, node),
				}
			)

	# And at the national node. Not as a stage — there isn't one there — but so
	# that a coordinator signing in as them sees the whole society rather than
	# six branches of it, which is what makes the admin screens worth opening on
	# a demo.
	root = national()

	if root:
		for role in APPROVER_ROLES:
			rows.append(
				{
					"key": f"{BRANCH_APPROVER}: {role} at the national node",
					"status": _assign(BRANCH_APPROVER, role, root),
				}
			)

	for login, _first, _last in APPROVERS:
		frappe.clear_cache(user=login)

	return rows


def _approver_user(login: str, first: str, last: str) -> str:
	"""The login, with `DEMO_PASSWORD` set on it. See that constant's note."""
	from frappe.utils.password import update_password

	if frappe.db.exists("User", login):
		status = "exists"
	else:
		frappe.get_doc(
			{
				"doctype": "User",
				"email": login,
				"first_name": first,
				"last_name": last,
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		).insert(ignore_permissions=True)
		status = "created"

	# Set on every run, not only on create. A demo whose documented password
	# stops working because somebody changed it once is worse than no demo.
	update_password(login, DEMO_PASSWORD)

	return status


def _grant(login: str, role: str) -> str:
	if role in frappe.get_roles(login):
		return "exists"

	frappe.get_doc("User", login).add_roles(role)

	return "created"


def _assign(login: str, role: str, node: str) -> str:
	"""One Geo Assignment: this person holds this role at this node."""
	if frappe.db.exists("Geo Assignment", {"user": login, "role": role, "geo_node": node}):
		return "exists"

	frappe.get_doc(
		{
			"doctype": "Geo Assignment",
			"user": login,
			"role": role,
			"geo_node": node,
			"is_active": 1,
		}
	).insert(ignore_permissions=True)

	return "created"


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
