# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Gambia Red Cross Society's own configuration. Data, never behaviour.

    bench --site <site> execute vmmsx.seed.gambia.main

The second society, and therefore the proof of the split this app is built on:
`kenya.py` beside it configures a different country with a different ladder and
different money, and not one line of source outside `vmmsx/seed/` changed to
allow it. Roles, geo levels, geo nodes, membership types, approval workflows and
settings are all records an administrator creates in the desk; this module
creates the ones GRCS would.

**Where the data comes from.** Unlike `kenya.py`, which is a worked example
somebody invented, everything here is the society's own:

* the ladder and its 369 links are the society's registration spreadsheets,
  carried in `gambia_structure.py` beside this file;
* the membership plans are the society's own "Membership Plans Template" —
  amounts, billing cycle, age requirement and benefits as written;
* the branches are the seven administrative regions the society is organised on.

**Idempotent, and it says what it did.** Every step checks before it writes and
reports `created` or `exists`. It never overwrites a value an administrator has
since edited. It expects a site with no other society on it — run
`vmmsx.seed.purge.main` first on a bench that has had one.
"""

import frappe

from vmmsx.registration.services.desk import PORTAL_HOME
from vmmsx.seed.gambia_structure import STRUCTURE

SETTINGS_DOCTYPE = "National Society Settings"

# --- the society ----------------------------------------------------------

ORGANIZATION_NAME = "The Gambia Red Cross Society"
ORGANIZATION_SHORT_NAME = "GRCS"
COUNTRY = "Gambia"
CURRENCY = "GMD"
LANGUAGE = "en"
TIME_ZONE = "Africa/Banjul"

WEBSITE = "https://www.thegambiaredcrosss.com"
TELEPHONE = "+220 439 2405"
ADDRESS = "56 Mamadi Manyang Highway, Kanifing Industrial Area, P.O. Box 472, Banjul, The Gambia"

# Served by Frappe from `sites/assets/vmmsx` -> `vmmsx/public`, so it exists on
# every site the app is installed on without anybody uploading anything.
LOGO = "/assets/vmmsx/images/seed_gambia/grcs-logo.jpg"

# What people here actually speak, as against what the desk is translated into.
# Frappe's shipped Language list is the latter and holds none of these, so a
# volunteer form reading it alone had nothing to offer somebody whose first
# language is Mandinka — which is most of the country. Codes are ISO 639; the
# labels are how each language names itself, the way Frappe's own rows do.
SPOKEN_LANGUAGES = (
	("mnk", "Mandinka"),
	("wo", "Wollof"),
	("ff", "Pulaar"),
	("dyo", "Jola"),
	("srr", "Serer"),
	("snk", "Soninke"),
	("mfv", "Manjago"),
	("bsc", "Bainouk"),
)

# --- the hierarchy --------------------------------------------------------

# Four rungs, which is what the society's own spreadsheets are organised on:
# a region has districts, a district has Red Cross Links, and a Link is where a
# volunteer actually is. ACC-03 says which of these a record may anchor at, and
# that is configuration below, never a constant in a source file.
LEVELS = (
	{"key": "grcs-national", "name": "National", "order": 1, "requires_parent": 0, "is_lowest": False},
	{"key": "grcs-region", "name": "Region", "order": 2, "requires_parent": 1, "is_lowest": False},
	{"key": "grcs-district", "name": "District", "order": 3, "requires_parent": 1, "is_lowest": False},
	{"key": "grcs-link", "name": "Link", "order": 4, "requires_parent": 1, "is_lowest": True},
)

NATIONAL_NODE = ORGANIZATION_NAME

# The seven branches, one per administrative region, in the order the society
# lists them. Banjul is the national headquarters and has no districts beneath
# it in the society's returns; it is here because it is a branch, and a branch
# with nothing under it yet is a true statement about the register.
REGIONS = (
	("Banjul", "Banjul"),
	("Kanifing Municipal", "Kanifing / Serekunda"),
	("West Coast Region", "Brikama"),
	("North Bank Region", "Kerewan"),
	("Lower River Region", "Mansakonko"),
	("Central River Region", "Janjanbureh"),
	("Upper River Region", "Basse"),
)

# --- roles ----------------------------------------------------------------

ROLE_VOLUNTEER_APPROVER = "Volunteer Approver"
ROLE_MEMBERSHIP_APPROVER = "Membership Approver"
ROLE_BRANCH_COORDINATOR = "Branch Coordinator"
# Two roles that exist because "coordinator" is not one job. Sending people
# somewhere and paying them a stipend are the two acts in this product with the
# most consequence attached, and a society that wants an assistant to run tasks
# and the register without either of those has to be able to say so. The
# settings below are what makes that real: each names one of these rather than
# the Branch Coordinator, so holding the coordinating role no longer carries
# deployments and money along with it.
ROLE_DEPLOYMENT_MANAGER = "Deployment Manager"
ROLE_STIPEND_MANAGER = "Stipend Manager"
ROLE_VOLUNTEER = "Volunteer"
ROLE_MEMBER = "Member"
ROLE_APPLICANT = "Society Applicant"

# (name, description, desk_access)
#
# The third column is the difference between somebody who works on the society's
# records and somebody the society keeps a record of. Frappe derives `user_type`
# from `desk_access`, so it decides whether an account can reach the desk at all.
# The three approving and coordinating roles work there; the volunteer, the
# member and the applicant have the portal, and `registration/services/desk.py`
# holds them to it on every migrate whatever a society calls them.
ROLES = (
	(ROLE_VOLUNTEER_APPROVER, "Reviews volunteer applications for a branch and its districts.", True),
	(ROLE_MEMBERSHIP_APPROVER, "Reviews membership applications for a branch and its districts.", True),
	(
		ROLE_BRANCH_COORDINATOR,
		"Runs a branch: tasks, announcements, offices and the page content.",
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

# The society's own "Membership Plans Template", as written: three plans, each
# billed every three years, each with an age requirement and its own benefits.
#
# Two things in it are worth saying out loud rather than quietly tidying away.
# The Volunteering Aid Detachment plan is written "D500-750", a range rather
# than a price; the floor is seeded because a member has to be charged one
# number, and the range is kept in the description where a branch can see it.
# And the template has no free tier, so none is invented here: the mockups show
# an "Ordinary (free)" plan and the society's own document does not, and this
# file follows the document.
TYPE_YOUTH = "youth-in-school"
TYPE_SENIOR = "senior-member"
TYPE_VAD = "volunteering-aid-detachment"

THREE_YEARS = 1095

MEMBERSHIP_TYPES = (
	{
		"key": TYPE_YOUTH,
		"name": "Youth in School",
		"fee_amount": 225,
		"duration_days": THREE_YEARS,
		"is_lifetime": False,
		"approval_mode": "routed",
		"description": (
			"For school-age members, 10 to 17 years. Billed every three years. Joined through a"
			" school Red Cross Link and reviewed by the branch."
		),
		"approval_note": "Reviewed by the branch the applicant's Link belongs to.",
		"benefits": (
			("membership-certificate", "Membership certificate"),
			("training", "Benefits from training"),
			("youth-leadership", "Youth leadership programmes"),
			("link-activities", "Attend Link activities"),
			("branch-register", "Listed in the Branch Register"),
		),
	},
	{
		"key": TYPE_SENIOR,
		"name": "Senior Member",
		"fee_amount": 350,
		"duration_days": THREE_YEARS,
		"is_lifetime": False,
		"approval_mode": "routed",
		"description": "For members 18 to 35 years. Billed every three years.",
		"approval_note": "Reviewed by the branch the applicant's Link belongs to.",
		"benefits": (
			("membership-certificate", "Membership certificate"),
			("training", "Benefits from training"),
			("leadership", "Leadership programmes"),
			("branch-programmes", "Attend Branch programmes"),
			("branch-register", "Registered in the Branch Register"),
		),
	},
	{
		"key": TYPE_VAD,
		"name": "Volunteering Aid Detachment",
		"fee_amount": 500,
		"duration_days": THREE_YEARS,
		"is_lifetime": False,
		"approval_mode": "routed",
		"description": (
			"For members 35 years and above. Billed every three years. The society's plan sets this"
			" at D500 to D750; the lower figure is charged and a branch may vary it."
		),
		"approval_note": "Reviewed by the branch the applicant's Link belongs to.",
		"benefits": (
			("membership-certificate", "Membership certificate"),
			("training", "Benefits from training"),
			("leadership", "Leadership programmes"),
			("national-programmes", "Attend National programmes"),
			("community-outreach", "Support and organise community outreach programmes"),
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

# The two rungs an application is reviewed at, in order. Labels are display
# only — the engine identifies a stage by its opaque row name and orders by
# sequence — so these are the society's own words and nothing branches on them.
STAGE_LINK = "Link Manager"
STAGE_DISTRICT = "District Manager"
STAGE_REGION = "Regional Coordinator"
STAGE_NATIONAL = "National Desk"

# --- the demo approver ----------------------------------------------------

APPROVER_USER = "approver@grcs.demo"
APPROVER_FIRST_NAME = "Fatou"
APPROVER_LAST_NAME = "Ceesay"
APPROVER_REGION = "West Coast Region"


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
		# Before the surfaces, because a member who cannot apply is a workflow
		# nobody can test. See the function's own note on why the fee stays.
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
	"Assign somebody to each approver role at the national node, in Geo Assignment. Every other"
	" rung of the ladder is optional and skipped when empty; the national one is the final"
	" decision and nothing above it exists to escalate to.",
	f"Set a password for {APPROVER_USER} on their User form before signing in as them.",
	"Replace the Manual payment gateway with a real one in OneRC Payment Settings when the society"
	" is ready to take money online. Until then a member applies and pays at the branch, and a"
	" clerk confirms it — see _payment_gateway() in this file.",
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
				# On for the people who work on the desk, off for the people the
				# society keeps records about. See the note above the table.
				"desk_access": int(desk),
				# Where a portal role lands after signing in. Left unset for a desk
				# role, which lands on the desk the framework's own way. Kept in
				# step with `desk.py`, which repairs it on every migrate.
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
	"""The society, its seven branches, their districts and every Red Cross Link.

	Docnames are opaque (`GEO-.#####`), so idempotence is a lookup on the shape
	of the row rather than on its name: a node is the same node when its label,
	its level and its parent all match. That is what lets this run twice, and
	what lets a branch be re-run after the society sends a corrected return.
	"""
	rows = []
	national, created = _node(NATIONAL_NODE, LEVELS[0]["key"], None, is_group=True)
	rows.append({"key": NATIONAL_NODE, "name": national, "status": created})

	for label, _capital in REGIONS:
		region, created = _node(label, LEVELS[1]["key"], national, is_group=True)
		districts = STRUCTURE.get(label, {})
		links = 0

		for district, entries in districts.items():
			node, _ = _node(district, LEVELS[2]["key"], region, is_group=True)

			for link, _kind, _male, _female in entries:
				_node(link, LEVELS[3]["key"], node)
				links += 1

		rows.append(
			{
				"key": label,
				"name": region,
				"status": created,
				"districts": len(districts),
				"links": links,
			}
		)

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
	"""A branch by its region name, by shape. Used by the operations seed."""
	return frappe.db.get_value(
		"Geo Node",
		{"geo_node_name": label, "geo_level": LEVELS[1]["key"], "parent_geo_node": national()},
		"name",
	)


def district(label: str, within: str | None = None) -> str | None:
	"""A district by name, optionally inside a named region."""
	filters = {"geo_node_name": label, "geo_level": LEVELS[2]["key"]}

	if within:
		filters["parent_geo_node"] = region(within)

	return frappe.db.get_value("Geo Node", filters, "name")


# --- the society single ---------------------------------------------------


def _society() -> list[dict]:
	"""Fill in the society's own identity, without overwriting an edit.

	Every field is set only when it is empty, because a seed re-run on a live
	site must not rename somebody's society back to the seed's answer.
	"""
	settings = frappe.get_single(SETTINGS_DOCTYPE)
	rows = []

	values = {
		"organization_name": ORGANIZATION_NAME,
		"organization_short_name": ORGANIZATION_SHORT_NAME,
		# The society's mark, shipped with the app rather than uploaded.
		#
		# It used to be a manual step, and a manual step is a step a fresh site
		# does not have: the logo lived at `/files/`, which is a site upload and
		# is in nobody's repository, so every new site rendered the portal, the
		# emails and the membership cards with no mark on them at all. An
		# `Attach Image` holds any URL, and `/assets/vmmsx/...` is served from
		# `public/` on every site the app is installed on — so the file travels
		# with the code and the setting can simply point at it.
		#
		# It is in `seed_gambia/` beside the licensed landing photography for the
		# reason that folder exists: the shipped defaults in `content/seeds/` stay
		# society-neutral, and anything that knows what country this is lives in
		# `vmmsx/seed/`.
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
	"""Add the languages a Gambian volunteer would name, if the site lacks them.

	`enabled` stays off on purpose: that flag means "this site's interface is
	offered in this language", which none of these is, and the volunteer form
	does not read it (`api/volunteer.py::_languages`).
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
				# The seed's report is read in a terminal as key=value pairs, so
				# this stays one token.
				"validity": "lifetime" if definition["is_lifetime"] else f"{definition['duration_days']}d",
			}
		)

	return rows


# --- approval workflows ---------------------------------------------------


def _workflows() -> list[dict]:
	"""One workflow per approvable doctype: the society's whole ladder, in order.

	Link, then district, then region, then the national desk — and **every stage
	names the same role**. `at_level` is what makes them different people: a
	Link manager is that role held at a Link, a regional coordinator is the same
	role held at a region. That is this app's access model rather than a
	shortcut — a Frappe role answers *what* and core's Geo Assignment answers
	*where*, so a second role would have said "where" twice. It would also have
	split `vmms_membership_scope_role`, which names one role and is the whole of
	who may read a membership: the rung that setting did not name would be
	routed decisions it cannot open.

	**The first three rungs are optional and the last is not**, which is the
	whole of how a society staffs this. `engine._advance` skips an optional
	stage that resolves nobody, so a branch that has named no Link manager and
	no district manager simply does not have those steps; the moment it names
	one, that person is in the chain, with nothing reconfigured. Adding an
	approver is one Geo Assignment and nothing else.

	**The national stage is required, and that is the one rule this shape
	imposes.** A society must have somebody holding each role at the national
	node. Nothing above it exists to escalate to, so an application whose every
	rung is empty would otherwise reach the end of the ladder with nobody able
	to act — which is exactly the failure this seed produced on a live site.
	The seed places that holder itself in `place_approver()`; a society that
	replaces the demo account must put its own there first.

	It is deliberately *not* the case that every stage is optional. Look at
	`engine._advance`: when the last stage is skipped the document is set to
	Approved. A ladder that could skip every rung would approve applications
	nobody had read.

	`allowed_anchor_levels` keeps the region alongside the district and the
	Link. Banjul is a branch with no districts in the society's returns, so an
	applicant there has nowhere further down to sit, and a record anchored at a
	region skips the two rungs beneath it and is decided above.
	"""
	rows = []
	anchor_levels = [LEVELS[1]["key"], LEVELS[2]["key"], LEVELS[3]["key"]]

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
					_stage(1, STAGE_LINK, role, LEVELS[3]["key"], is_optional=1),
					_stage(2, STAGE_DISTRICT, role, LEVELS[2]["key"], is_optional=1),
					_stage(3, STAGE_REGION, role, LEVELS[1]["key"], is_optional=1),
					_stage(4, STAGE_NATIONAL, role, LEVELS[0]["key"], is_optional=0),
				],
			}
		).insert(ignore_permissions=True)

		rows.append(
			{
				"key": doctype,
				"name": workflow.name,
				"status": "created",
				"role": role,
				# One token each, because the report is read as key=value pairs.
				"rungs": "+".join(LEVELS[i]["name"] for i in (3, 2, 1, 0)),
			}
		)

	return rows


def _stage(sequence: int, label: str, role: str, level: str, is_optional: int) -> dict:
	"""One row of the Stages table.

	Every stage carries a clock and says what a breach does, because a stage
	with neither is a queue nobody is watching.
	"""
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
	"""Let each approver role act on the doctype it approves.

	Recording a decision saves the governed document, so the role a stage names
	needs write on it. Added as Custom DocPerms, which is what an administrator
	does in the Role Permissions Manager.
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


def place_approver() -> list[dict]:
	"""One person holding the approver roles, placed at one branch and at the top.

	Placed with `Geo Assignment`, which is core's answer to *where*: holding the
	role is not authority anywhere, and holding it at West Coast Region is
	authority over that region, its districts and every Link beneath them. The
	two questions stay separate, which is the access model this app is built on.

	**The national placement is not decoration, and leaving it out made the
	product unusable.** `_workflows()` above already says why: both stages
	resolve `at_level` at the Link and the district, most Links and districts
	have no named manager, and a record that resolves nobody escalates to the
	nearest holder *above* it — "which is why the society needs a holder of each
	role at the national node". That holder was never created. So on a site
	seeded from this file, an application anywhere outside West Coast Region
	resolved nobody, escalated to a national holder that did not exist, and was
	admitted to nobody at all. Not the applicant, not the approver, not an
	administrator: the gate admits the people a document routed to, and the
	list was empty. Applications submitted by real people could not be decided.

	Two rows per role rather than one, then. The regional placement is what a
	branch approver's authority actually looks like; the national one is the
	backstop the routing design depends on, and without it every branch that has
	not named its own approver is a dead end.

	Public, unlike the rest of this file's steps, because
	`patches/repair_approval_routing.py` calls it by name on sites that were
	seeded before this was fixed. A society seed is data, and this is the one
	piece of it a later release had to be able to re-place on its own.

	**This person deliberately does not hold `ROLE_DEPLOYMENT_MANAGER` or
	`ROLE_STIPEND_MANAGER`**, and adding them would undo the thing the two roles
	were created for. A demo account holding every role is how "coordinator"
	quietly comes to mean "everything" again, and the split is only visible on a
	site where somebody actually lacks something: signed in as this person, the
	console draws Overview, the review queue, the register, tasks, events and
	analytics — and no Deployments or Stipends tab, because those are somebody
	else's job. A society hands the two manager roles to the people who do them,
	the same way it hands out every other role here.
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

		# The branch placement, and the national backstop the routing design
		# depends on. `Branch Coordinator` gets both too: its scope decides what
		# a coordinator may read and where they may send an announcement, and a
		# demo account that can only see one region of seven shows a fraction of
		# the site to whoever is being shown it.
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
	"""Point every role setting this app owns at a role that really exists.

	They all ship empty and empty fails closed, which is right for an app nobody
	has configured and useless for a working site: an unconfigured scope role
	means no approver can open the application routed to them. This is a society
	making its choices, and every one of them is a value in this file rather than
	a default anywhere in the source.
	"""
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
		# The six that used to be left empty. Empty fails closed, which is the
		# right shipped default and the wrong state for a working site: it meant
		# nobody but an administrator could open a deployment, a transfer, a
		# stipend report or the branch office list, while the console drew tabs
		# onto all four regardless. Naming a role here is what turns them on, and
		# naming a *different* role from the coordinating one is what keeps "runs
		# a branch" from also meaning "sends people out and signs the payments".
		"vmms_deployment_scope_role": ROLE_DEPLOYMENT_MANAGER,
		"vmms_deployment_request_scope_role": ROLE_DEPLOYMENT_MANAGER,
		"vmms_branch_transfer_scope_role": ROLE_DEPLOYMENT_MANAGER,
		"vmms_stipend_report_scope_role": ROLE_STIPEND_MANAGER,
		"vmms_stipend_payment_scope_role": ROLE_STIPEND_MANAGER,
		# Where the branch actually is, which is the coordinator's own list to keep
		# rather than a third manager's.
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
	"""Let people make their own accounts, and say what a new one is."""
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
	"""Collect the membership fee at the branch, not through a gateway.

	Every GRCS plan carries a fee, and a fee-bearing membership opens an
	`OneRC Payment Transaction` the moment somebody applies. With no gateway
	chosen that insert fails on its own mandatory `gateway` field, so a person
	registering as a member got an error and no membership — the application
	never reached the approver at all.

	The answer is not to make the plans free. A fee a society charges is a fact
	about the society, and zeroing it to get past an error would put a wrong
	number in front of every applicant and leave the branch with no record of
	what is owed. It is to say **how** the fee is collected, which is what the
	Manual driver is for: the transaction is created and stays Pending, the
	applicant is told to pay at the branch, and a clerk confirms it with
	`onerc_payments.gateways.manual.confirm_payment`. That confirmation is the
	ordinary `on_payment_confirmed` hook MEM-01 already defines — nothing about
	the money path is special-cased, and no vmmsx code changes.

	Approval and payment stay independent, which is the point of
	`membership.try_activate()` being a predicate: the approver can decide
	before the money arrives or after it, and the membership activates when both
	are settled. Testing the approval workflow no longer waits on a gateway.

	**Additive, like every other step here.** A society that has already chosen
	a gateway keeps it — this only fills an empty `active_gateway`.
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

	# What the applicant is actually told. Left alone if the society has written
	# its own, the same rule the settings step above follows.
	if not settings.manual_instructions:
		settings.manual_instructions = (
			"Pay your membership fee at your nearest Red Cross branch office. "
			"Quote your reference number, and the branch will confirm the payment "
			"on your record."
		)

	settings.save(ignore_permissions=True)
	frappe.clear_document_cache(settings_doctype, settings_doctype)

	rows.append({"key": "active_gateway", "status": "created", "value": gateway})

	return rows


def _surfaces() -> dict:
	"""Build the workspaces and permissions now that the roles exist.

	**Both halves, and the staff half is the one that has to be here.** Each
	installer reads the scope-role settings and grants what they name, and every
	one of them also runs from `after_migrate` — where, on a fresh site, the
	settings are still empty and there is nothing to grant. `_settings()` fills
	them a few steps above this one, so without re-running the installers here
	the site ends up with a Deployment Manager who holds the role, appears on the
	workspace, and has no permission on a single deployment. The console would
	then draw them no tab, correctly and uselessly: `staff/services/console.py`
	gates on `frappe.has_permission`, which is exactly what never got granted.

	Idempotent, like everything else in this file — a second run finds the rows
	already there.
	"""
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
	"""Put the society's own wording on the public landing page.

	The one step of this seed that deliberately **overwrites**. Everything else
	leaves an administrator's edits alone, but somebody running the Gambia seed
	is asking to see the Gambia page, and a page half in the product's neutral
	voice would be nobody's idea of a configured site.
	"""
	from vmmsx.seed import gambia_content

	return gambia_content.install()


# --- the report -----------------------------------------------------------


def _print(report: dict) -> None:
	"""Say what happened, in a shape somebody can read in a terminal."""
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
