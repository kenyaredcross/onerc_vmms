# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The staff desk: one VMMS cluster, seven operational children, native Workspaces.

Frappe's own shape for this is Accounting in ERPNext — a parent workspace whose
job is to be a landing page, and a set of children nested under it through
`parent_page`. This module builds the same shape for VMMS: one parent, seven
children, no doctype, no page, no bundle. What is code is the shape — which
children exist, what each one offers, in what order. What is configuration is
the *extra* roles a society may layer on, read from National Society Settings
exactly the way `registration/services/workspaces.py` reads its own roles.

    VMMS              the landing page. A grid of shortcuts, one per child,
                      and nothing else.
    Membership        VMMS Member, VMMS Membership, VMMS Membership Type,
                      VMMS Membership Benefit.
    Volunteers        VMMS Volunteer, VMMS Volunteer Application,
                      VMMS Certification, VMMS Certification Type,
                      VMMS Course Mapping, VMMS Time Log.
    Tasks             VMMS Task.
    Deployments       VMMS Deployment, VMMS Deployment Request,
                      VMMS Terms of Reference, VMMS Branch Transfer.
    Stipend           VMMS Stipend Progress Report, VMMS Stipend Payment Form.
    Places            VMMS Branch Location.
    VMMS Setup        Geo Level, Geo Node, Geo Assignment, National Society
                      Settings (all core's), Affiliation Type, VMMS Membership
                      Type, VMMS Certification Type, VMMS Course Mapping, VMMS
                      Time Log Category, VMMS Skill, VMMS Announcement Type,
                      VMMS Approval Workflow, VMMS Template Category, VMMS
                      Template, VMMS Application Question.

VMMS Setup also carries a native Frappe onboarding checklist (`Module
Onboarding` plus one `Onboarding Step` per doctype above, `_install_setup_onboarding()`
below) — the same "Let's get started" mechanism ERPNext uses for Accounting.
Ordered so a step's own prerequisites come first (the geo tree before anything
scoped to it, membership/certification/template *types* before the records
that pick from them), and each step auto-completes the way Frappe's own
onboarding widget already does: opening the step's "Create Entry" form and
saving marks it done, no bespoke completion logic here.

Two of those carry a single doctype today, and each is a child of its own rather
than a card on a neighbour for the same reason: it has a scope role of its own,
so a society can put supervising work, or maintaining an office address, in
different hands from administering the volunteer register. A shared workspace
could not express that; `_tasks()` and `_places()` say so at their definitions.

**Why this is not shaped like the self-service surfaces.** Those three
(`registration/services/workspaces.py`) exist only once a society has named a
role for them, and are *removed* when that role is cleared, because an
unconfigured self-service surface with no roles would be a public page in front
of the whole society. This cluster is the opposite kind of thing: it is the
staff desk itself, and a fresh site must show it the way a fresh ERPNext site
shows Accounting, without an administrator configuring anything first.

So the floor here is **System Manager**, always present, never conditional.
`System Manager` is a Frappe framework primitive, not a society role, so naming
it directly does not reintroduce the "no hardcoded role" rule the rest of this
app follows — see core's `access/services/scope.py`, which states the same
exemption for the same reason.

A society may layer a **narrower coordinator role on top of a child**, by
naming the same geo scope role settings that already gate *record* access for
that child's doctypes (`vmms_volunteer_scope_role` and friends, registered in
`hooks.py` under `onerc_scopeable_doctypes`). That role is additive, not a
replacement for System Manager: `_roles()` always returns System Manager first
and appends whatever scope role a society has configured and not since deleted.
Doing this makes a scoped coordinator's own child reachable without touching
what an administrator already sees. The parent workspace carries the union of
every child's roles, so the desk path from Home through VMMS to a coordinator's
own child stays unbroken. Note this is desk-surface visibility, not record
visibility — core's geo-scoped list queries are what narrows the rows inside;
this module never touches that.

**The grid is shortcuts, not a workspace-typed link.** `Workspace Shortcut` has
no "Workspace" option in its `type` field — DocType, Report, Page, Dashboard and
URL are the whole list — so the parent's five tiles are URL shortcuts to each
child's own desk route, `/desk/<slug>`, built with the same `slug()` Frappe's
router uses to resolve it (`frappe.desk.utils.slug`), so the link and the route
it opens can never drift apart. `/desk` rather than the older `/app` — the
latter is now a redirect shim (`website_redirects` in core Frappe's own
`hooks.py`), and a shortcut built on the shim would cost every click an extra
hop for no reason.

**Mounted onto the app it belongs to.** A Workspace's `app` field decides which
app's dock (workspace rail) lists it, and which apps-screen icon owns it; a
standard, module-shipped workspace inherits this from its module, but a custom
one — every workspace this file builds — has to say so explicitly or it hangs
off no dock at all. `_sync()` sets it to `"vmmsx"` on every one of the six.

**Nesting is `parent_page`, and nothing else.** A child's `parent_page` is set
to the parent's `title` — Frappe's own convention, read directly out of
`workspace.py`'s `update_page` — which is what makes the desk show these five
under VMMS in its own sidebar tree, no different from the way it shows
Invoicing and Payments under Accounting.
"""

import frappe
from frappe.desk.utils import slug
from frappe.utils.user import is_website_user

WORKSPACE_DOCTYPE = "Workspace"

# A Frappe framework primitive, not a society role — see this module's
# docstring and core's `access/services/scope.py`, which draws the same line.
SYSTEM_MANAGER = "System Manager"

PARENT = "VMMS"
MEMBERSHIP = "Membership"
VOLUNTEERS = "Volunteers"
TASKS = "Tasks"
DEPLOYMENTS = "Deployments"
STIPEND = "Stipend"
PLACES = "Places"
SOCIETY_SETUP = "VMMS Setup"

CHILDREN = (MEMBERSHIP, VOLUNTEERS, TASKS, DEPLOYMENTS, STIPEND, PLACES, SOCIETY_SETUP)

# The settings field naming `VMMS Membership`'s geo scope role. Registered as a
# literal in `hooks.py` under `onerc_scopeable_doctypes`, the same place every
# other scope-role field is a literal too; `member/services/society.py` does not
# export it as a constant, so this names the one other spot it is written down
# rather than inventing a second copy silently.
MEMBERSHIP_SCOPE_ROLE_FIELD = "vmms_membership_scope_role"

# The same for the two modules whose services do not export the constant either.
# Both are literals in `hooks.py` under `onerc_scopeable_doctypes` and installed
# by their own patch; this names the one other spot each is written down.
TASK_SCOPE_ROLE_FIELD = "vmms_task_scope_role"
BRANCH_LOCATION_SCOPE_ROLE_FIELD = "vmms_branch_location_scope_role"


def _migrate_legacy_setup_workspace() -> None:
	"""One-time cleanup for a site that already ran `install()` under this
	child's old name, "Society & Setup", before it became `SOCIETY_SETUP =
	"VMMS Setup"`. Renaming the Python string alone leaves the old workspace
	orphaned — `_sync()` keys off `label`, so on its own it would create a
	fresh "VMMS Setup" doc rather than renaming the site's existing one, and
	the old doc would never be touched by `install()` again. Runs before
	`_sync()` so there is at most one workspace under either name by the time
	it does; a no-op on a fresh site that never had the old name.
	"""
	LEGACY = "Society & Setup"

	if not frappe.db.exists(WORKSPACE_DOCTYPE, LEGACY):
		return

	if frappe.db.exists(WORKSPACE_DOCTYPE, SOCIETY_SETUP):
		# `install()` already ran once since the rename, before this guard
		# existed, and created a fresh "VMMS Setup" — the legacy doc is now
		# redundant, not a rename target.
		frappe.delete_doc(WORKSPACE_DOCTYPE, LEGACY, force=True, ignore_permissions=True)
		return

	frappe.rename_doc(WORKSPACE_DOCTYPE, LEGACY, SOCIETY_SETUP, ignore_permissions=True, force=True)


def install() -> dict:
	"""Build or refresh the parent and its seven children. Idempotent.

	Called from `after_migrate`, alongside the self-service surfaces, and safe
	to call directly when a society changes one of the scope-role settings this
	reads:

	    bench --site <site> execute vmmsx.staff.services.workspaces.install

	The parent is written first: a child's `parent_page` is a Link to
	`Workspace`, and Frappe validates that link on save, so VMMS has to exist
	before Membership, Volunteers, Deployments, Stipend or VMMS Setup can
	name it.
	"""
	_migrate_legacy_setup_workspace()

	from onerc_core.society.services import config

	settings = config.settings()

	child_roles = {
		MEMBERSHIP: _roles(settings, MEMBERSHIP_SCOPE_ROLE_FIELD),
		VOLUNTEERS: _roles(settings, _volunteer_scope_role_field()),
		TASKS: _roles(settings, TASK_SCOPE_ROLE_FIELD),
		DEPLOYMENTS: _roles(settings, *_deployment_scope_role_fields()),
		STIPEND: _roles(settings, *_stipend_scope_role_fields()),
		PLACES: _roles(settings, BRANCH_LOCATION_SCOPE_ROLE_FIELD),
		SOCIETY_SETUP: [SYSTEM_MANAGER],
	}

	result = {
		# Negative, but above the self-service surfaces' -3.0 to -1.0: the desk
		# opens on the first workspace a user is permitted to see, in ascending
		# `sequence_id` order, across every public workspace on the site — not
		# only this app's own. Every third-party app here ships its workspaces
		# with a zero or positive sequence_id (Buzz's own lands at 0.0), so a
		# staff member or administrator who holds no self-service role skips
		# past those three and would otherwise land on whichever unrestricted
		# workspace happens to sort first — Buzz, on this bench. Sitting below
		# every one of them is what makes VMMS the landing page instead, for
		# anybody who does not hold a self-service role, without reordering
		# anything this app does not own.
		PARENT: _sync(_parent(), _union(child_roles), sequence=-0.5, module="Vmmsx", parent_page=None),
		MEMBERSHIP: _sync(
			_membership(), child_roles[MEMBERSHIP], sequence=1.1, module="VMMS Member", parent_page=PARENT
		),
		VOLUNTEERS: _sync(
			_volunteers(), child_roles[VOLUNTEERS], sequence=1.2, module="VMMS Volunteer", parent_page=PARENT
		),
		TASKS: _sync(_tasks(), child_roles[TASKS], sequence=1.25, module="VMMS Task", parent_page=PARENT),
		DEPLOYMENTS: _sync(
			_deployments(),
			child_roles[DEPLOYMENTS],
			sequence=1.3,
			module="VMMS Deployment",
			parent_page=PARENT,
		),
		STIPEND: _sync(
			_stipend(), child_roles[STIPEND], sequence=1.4, module="VMMS Stipend", parent_page=PARENT
		),
		PLACES: _sync(
			_places(), child_roles[PLACES], sequence=1.45, module="VMMS Branch", parent_page=PARENT
		),
		SOCIETY_SETUP: _sync(
			_society_setup(), child_roles[SOCIETY_SETUP], sequence=1.5, module="Vmmsx", parent_page=PARENT
		),
	}

	_install_setup_onboarding()

	return result


def has_desk_access() -> bool:
	"""Whether the current user may open the staff desk cluster at all.

	The `has_permission` gate named on vmmsx's `add_to_apps_screen` entry for
	the VMMS tile — see `hooks.py`. Reads the parent workspace's own Roles table
	rather than re-deriving System Manager plus whatever scope roles a society
	has configured today: `install()` already computed that exact union onto
	`VMMS` (`_union()`), and resolving it a second way here would let the two
	answers drift apart. Falls back to a literal System Manager check so the
	tile still shows for an administrator on a fresh site that has not migrated
	yet, before any `Has Role` row exists to read.
	"""
	# Asked first, and ahead of the System Manager floor, because it is the one
	# answer that cannot be overridden by a role: a Website User cannot open a
	# workspace whatever they hold, so a tile routing to one is a permission
	# error with a title. It matters beyond the tile — `get_default_path()` reads
	# the apps screen to decide where somebody lands after signing in, and a
	# self-service login is a Website User by `desk.py`'s design.
	if is_website_user():
		return False

	if SYSTEM_MANAGER in frappe.get_roles():
		return True

	roles = frappe.get_all(
		"Has Role", filters={"parent": PARENT, "parenttype": WORKSPACE_DOCTYPE}, pluck="role"
	)

	return bool(set(roles) & set(frappe.get_roles()))


def _volunteer_scope_role_field() -> str:
	from vmmsx.volunteer.services.society import SCOPE_ROLE_FIELD

	return SCOPE_ROLE_FIELD


def _deployment_scope_role_fields() -> tuple:
	from vmmsx.deployment.services.society import (
		DEPLOYMENT_SCOPE_ROLE_FIELD,
		REQUEST_SCOPE_ROLE_FIELD,
		TRANSFER_SCOPE_ROLE_FIELD,
	)

	return (DEPLOYMENT_SCOPE_ROLE_FIELD, REQUEST_SCOPE_ROLE_FIELD, TRANSFER_SCOPE_ROLE_FIELD)


def _stipend_scope_role_fields() -> tuple:
	from vmmsx.stipend.services.society import PAYMENT_SCOPE_ROLE_FIELD, REPORT_SCOPE_ROLE_FIELD

	return (REPORT_SCOPE_ROLE_FIELD, PAYMENT_SCOPE_ROLE_FIELD)


def _roles(settings, *fields: str) -> list:
	"""System Manager, plus whichever of `fields` names a role that still exists.

	Resolved through the same `resolved_role()` the self-service surfaces use: a
	setting naming a role somebody has since deleted is logged and treated as
	unconfigured, rather than being written onto a workspace that would then
	grant nobody anything and say nothing about why.
	"""
	from vmmsx.registration.services import society as self_service

	roles = [SYSTEM_MANAGER]

	for field in fields:
		role = self_service.resolved_role(settings.get(field), field)
		if role and role not in roles:
			roles.append(role)

	return roles


def _union(child_roles: dict) -> list:
	"""Every role any child carries, System Manager first. For the parent."""
	roles = [SYSTEM_MANAGER]

	for roles_for_child in child_roles.values():
		for role in roles_for_child:
			if role not in roles:
				roles.append(role)

	return roles


def _sync(spec: dict, roles: list, sequence: float, module: str, parent_page: str | None) -> str:
	"""Create or update one workspace. Returns what happened, for the report.

	Unlike the self-service surfaces, `roles` here is never empty — `_roles()`
	and `_union()` both start from System Manager — so there is no "no role,
	remove it" branch: this cluster is never uninstalled by configuration, only
	ever narrowed or widened.
	"""
	label = spec["label"]
	exists = frappe.db.exists(WORKSPACE_DOCTYPE, label)

	doc = frappe.get_doc(WORKSPACE_DOCTYPE, label) if exists else frappe.new_doc(WORKSPACE_DOCTYPE)

	doc.update(
		{
			"label": label,
			"title": label,
			"module": module,
			"icon": spec["icon"],
			"public": 1,
			# Not a standard workspace: built from configuration at install time,
			# not shipped as a file. See registration/services/workspaces.py for
			# why `standard` stays 0.
			"standard": 0,
			# Mounts this workspace onto the VMMS apps-screen icon and its dock —
			# see the module docstring. A custom workspace that left this blank
			# would fall back to whatever `Module Def.app_name` resolves to at
			# read time, which happens to also be "vmmsx" today but is an
			# implementation detail of `get_workspaces()`, not a contract this
			# file should depend on silently holding.
			"app": "vmmsx",
			"parent_page": parent_page or "",
			"sequence_id": sequence,
			"content": frappe.as_json(spec["content"]),
		}
	)

	doc.set("roles", [{"role": role} for role in roles])
	doc.set("shortcuts", spec["shortcuts"])
	doc.set("links", spec.get("links") or [])

	# Runs from after_migrate, with no session, building this app's own admin
	# desk configuration rather than anybody's document — there is no acting
	# user whose permissions could apply here.
	doc.save(ignore_permissions=True)

	return "updated" if exists else "created"


# --- the six surfaces -------------------------------------------------------


def _parent() -> dict:
	"""The grid: one URL shortcut per child, and nothing else."""
	shortcuts = [
		_url_shortcut(MEMBERSHIP, _child_route(MEMBERSHIP), "id-card"),
		_url_shortcut(VOLUNTEERS, _child_route(VOLUNTEERS), "heart-handshake"),
		_url_shortcut(TASKS, _child_route(TASKS), "list-checks"),
		_url_shortcut(DEPLOYMENTS, _child_route(DEPLOYMENTS), "route"),
		_url_shortcut(STIPEND, _child_route(STIPEND), "banknote"),
		_url_shortcut(PLACES, _child_route(PLACES), "map-pin"),
		_url_shortcut(SOCIETY_SETUP, _child_route(SOCIETY_SETUP), "settings"),
	]

	return {
		"label": PARENT,
		"icon": "layout-grid",
		"shortcuts": shortcuts,
		"content": [
			_header("VMMS"),
			_paragraph(
				"The operational layer, in one place. Open a card below for a national"
				" society's members, volunteers, the work assigned to them, deployments,"
				" stipend paperwork and the places it can be found, or for the geo tree and"
				" approval configuration behind all of them."
			),
			*_shortcut_blocks(shortcuts, col=3),
		],
	}


def _membership() -> dict:
	return _child_spec(
		MEMBERSHIP,
		"id-card",
		(
			("VMMS Member", "user"),
			("VMMS Membership", "id-card"),
			("VMMS Membership Type", "tag"),
			("VMMS Membership Benefit", "gift"),
		),
		"Members, the memberships that make them one, and the types and benefits a"
		" society configures for them.",
	)


def _volunteers() -> dict:
	return _child_spec(
		VOLUNTEERS,
		"heart-handshake",
		(
			("VMMS Volunteer", "user"),
			("VMMS Volunteer Application", "file-text"),
			("VMMS Certification", "award"),
			("VMMS Certification Type", "shield-check"),
			("VMMS Course Mapping", "book-open"),
			("VMMS Time Log", "clock"),
		),
		"Volunteers, their applications, the certifications and time they log, and how"
		" a learning system's courses map onto a certification.",
	)


def _tasks() -> dict:
	"""Its own child rather than a card on Volunteers, because it is its own role.

	A society may put supervising work in different hands from maintaining the
	register: the person who assigns and signs off a task is often a branch
	coordinator, and the person who administers volunteer records is often not.
	Two settings can express that; one shared workspace could not.
	"""
	return _child_spec(
		TASKS,
		"list-checks",
		(("VMMS Task", "list-checks"),),
		"Work assigned to volunteers: what was asked for, who accepted it, what they"
		" reported, and what a coordinator signed off.",
	)


def _deployments() -> dict:
	return _child_spec(
		DEPLOYMENTS,
		"route",
		(
			("VMMS Project", "folder-normal"),
			("VMMS Deployment", "map-pin"),
			# One person's deployment, with its own status and its own record of the
			# terms they agreed to. Here rather than only inside a deployment,
			# because "what has this volunteer been asked and what did they say" is a
			# question a coordinator asks across deployments, and a list view answers
			# it in a way a roster on one record cannot.
			("VMMS Deployment Assignment", "user-check"),
			("VMMS Deployment Request", "clipboard-list"),
			("VMMS Terms of Reference", "file-text"),
			("VMMS Branch Transfer", "arrow-left-right"),
		),
		"Programmes of work, requests for deployment, the deployments they become,"
		" who is on each of them, the terms they are governed by, and volunteers"
		" moving between branches.",
	)


def _stipend() -> dict:
	return _child_spec(
		STIPEND,
		"banknote",
		(
			("VMMS Stipend Progress Report", "file-text"),
			("VMMS Stipend Payment Form", "banknote"),
		),
		"What a branch reports doing over a period, and what it was paid for it.",
	)


def _places() -> dict:
	"""The society's own addresses, kept out of VMMS Setup deliberately.

	VMMS Setup carries the geo tree, the settings document and Geo
	Assignment, and its role list is System Manager and nothing else for that
	reason. A branch that maintains its own office address should not need
	sight of any of those, so its doctype lives here with a role of its own.
	"""
	return _child_spec(
		PLACES,
		"map-pin",
		(("VMMS Branch Location", "map-pin"),),
		"Offices, warehouses and training centres, with the coordinates that put them"
		" on the public map and the contact details beside it.",
	)


def _society_setup() -> dict:
	"""Every doctype a society configures once, before the rest of the app is
	usable — the same set `SETUP_STEPS` below walks as a checklist. Doctypes
	that also have an operational home elsewhere (Membership Type on
	Membership, Certification Type and Course Mapping on Volunteers) are
	listed here too, deliberately: this child is not "where these doctypes
	live," it is "everything a fresh site needs before day one," and the two
	questions have different answers.
	"""
	return _child_spec(
		SOCIETY_SETUP,
		"settings",
		(
			("Geo Level", "layers"),
			("Geo Node", "map"),
			("Geo Assignment", "map-pinned"),
			("National Society Settings", "settings"),
			("Affiliation Type", "tags"),
			("VMMS Membership Type", "tag"),
			("VMMS Certification Type", "shield-check"),
			("VMMS Course Mapping", "book-open"),
			("VMMS Time Log Category", "clock"),
			("VMMS Skill", "star"),
			("VMMS Availability Slot", "clock-4"),
			("VMMS TOR Methodology", "compass"),
			("VMMS Announcement Type", "megaphone"),
			("VMMS Approval Workflow", "workflow"),
			("VMMS Template Category", "layout-list"),
			("VMMS Template", "layout-template"),
			("VMMS Application Question", "help-circle"),
		),
		"Everything a society configures once, before the rest of the app is usable:"
		" the geo tree and the society's own settings — both onerc_core's — the types"
		" and categories that membership, volunteering, notifications and templates"
		" pick from, the approval workflows that govern them, and the volunteer"
		" application form's own questions. Work through the checklist above top to"
		" bottom on a fresh site.",
	)


# --- the setup checklist -----------------------------------------------------

# One row per `Onboarding Step`, in the exact order `_society_setup()`'s own
# shortcut grid lists them — the geo tree first (everything else scopes to
# it), the society's own settings right after, then every *type*/*category*
# doctype the operational records go on to pick from. `action` is "Create
# Entry" throughout except National Society Settings, which is a Single: there
# is nothing to create, only a form to fill in, which is "Update Settings" in
# Frappe's own onboarding vocabulary and carries `is_single` alongside it.
SETUP_STEPS = (
	(
		"Geo Level",
		"Create Entry",
		"Define the levels of your location tree, in order (for example Country, County, Branch).",
	),
	("Geo Node", "Create Entry", "Build the tree itself: one node per level, each linked to its parent."),
	(
		"Geo Assignment",
		"Create Entry",
		"Give a record the geo node it belongs to, wherever this app or onerc_core asks for one.",
	),
	(
		"National Society Settings",
		"Update Settings",
		"Name the roles this society uses to scope membership, volunteers, tasks, deployments and stipends.",
	),
	(
		"Affiliation Type",
		"Create Entry",
		"The ways a person can be affiliated with the society, beyond membership.",
	),
	(
		"VMMS Membership Type",
		"Create Entry",
		"The kinds of membership the society offers, and what each one includes.",
	),
	("VMMS Certification Type", "Create Entry", "The certifications a volunteer can hold."),
	(
		"VMMS Course Mapping",
		"Create Entry",
		"How an external learning system's course IDs map onto a certification.",
	),
	("VMMS Time Log Category", "Create Entry", "The categories a volunteer logs their time against."),
	("VMMS Skill", "Create Entry", "The skills a volunteer can list on their profile."),
	(
		"VMMS Availability Slot",
		"Create Entry",
		"The windows of the day a volunteer can say they"
		" are free in. Give one an opening and a closing time and it becomes a column in the"
		" weekly availability grid; leave the times empty and it stays a label picked at intake.",
	),
	(
		"VMMS TOR Methodology",
		"Create Entry",
		"The ways this society goes about its work, which a terms of reference picks its approach from.",
	),
	("VMMS Announcement Type", "Create Entry", "The categories an announcement can be posted under."),
	(
		"VMMS Approval Workflow",
		"Create Entry",
		"The stages a request moves through before it counts as approved.",
	),
	("VMMS Template Category", "Create Entry", "How message templates are grouped."),
	("VMMS Template", "Create Entry", "The wording sent for each notification this app fires."),
	("VMMS Application Question", "Create Entry", "The questions asked on the volunteer application form."),
)

MODULE_ONBOARDING_DOCTYPE = "Module Onboarding"
ONBOARDING_STEP_DOCTYPE = "Onboarding Step"


def _install_setup_onboarding() -> None:
	"""Build or refresh the VMMS Setup checklist. Idempotent, like `_sync()`.

	One `Onboarding Step` per row in `SETUP_STEPS`, a `Module Onboarding`
	naming them in order, and the VMMS Setup workspace's own `module_onboarding`
	field plus an `onboarding` content block pointing at it — the exact shape
	core's `update_workspace2` patch builds for every standard onboarding, read
	from `frappe/public/js/frappe/views/workspace/blocks/onboarding.js` and
	`onboarding_step.json`'s own `action` options.

	Completion is entirely Frappe's own: `onboarding_widget.js` opens each
	step's "Create Entry" (or "Update Settings") form and marks the step done
	on save, the same as every onboarding checklist ERPNext ships. Nothing
	here tracks progress a second way.

	Called from `install()`, after the VMMS Setup workspace itself has been
	synced — a step's `reference_document` not existing yet is skipped, the
	same guard `_child_spec` opens with and for the same self-healing reason.
	"""
	step_names = [
		_sync_onboarding_step(doctype, action, description)
		for doctype, action, description in SETUP_STEPS
		if _installed(doctype)
	]

	exists = frappe.db.exists(MODULE_ONBOARDING_DOCTYPE, SOCIETY_SETUP)
	doc = (
		frappe.get_doc(MODULE_ONBOARDING_DOCTYPE, SOCIETY_SETUP)
		if exists
		else frappe.new_doc(MODULE_ONBOARDING_DOCTYPE)
	)

	if not exists:
		doc.name = SOCIETY_SETUP

	doc.update({"title": SOCIETY_SETUP, "module": "Vmmsx"})
	doc.set("steps", [{"step": name} for name in step_names])
	doc.set("allow_roles", [{"role": SYSTEM_MANAGER}])
	doc.save(ignore_permissions=True)

	workspace = frappe.get_doc(WORKSPACE_DOCTYPE, SOCIETY_SETUP)
	workspace.module_onboarding = doc.name
	content = [
		block for block in frappe.parse_json(workspace.content or "[]") if block.get("type") != "onboarding"
	]
	content.insert(1, _block("onboarding", {"onboarding_name": doc.name, "col": 12}))
	workspace.content = frappe.as_json(content)
	workspace.save(ignore_permissions=True)


def _sync_onboarding_step(doctype: str, action: str, description: str) -> str:
	"""Create or update one `Onboarding Step`, named after its doctype so a
	second `install()` finds and updates the same row rather than duplicating
	it. Returns the step's `name`, for `_install_setup_onboarding()`'s table.
	"""
	title = f"Set up {doctype}"
	exists = frappe.db.exists(ONBOARDING_STEP_DOCTYPE, title)
	doc = (
		frappe.get_doc(ONBOARDING_STEP_DOCTYPE, title) if exists else frappe.new_doc(ONBOARDING_STEP_DOCTYPE)
	)

	if not exists:
		doc.name = title

	doc.update(
		{
			"title": title,
			"description": description,
			"action": action,
			"reference_document": doctype,
			"is_single": 1 if action == "Update Settings" else 0,
			"show_full_form": 1,
		}
	)
	doc.save(ignore_permissions=True)

	return doc.name


def _child_spec(label: str, icon: str, doctypes: tuple, intro: str) -> dict:
	"""Shared shape for a child: shortcuts to every doctype named, then a card
	grouping the same set again for the fuller list.

	**A doctype that does not exist yet is skipped**, the same guard
	`permissions.py::_grant` opens with and for the same reason. On the migrate
	that first introduces a module, the pre-model-sync patch creates its Module
	Def but the module-to-app map was cached before that patch ran, so the new
	module's doctypes are not synced until the *next* migrate. A `Workspace Link`
	is a real Link field and Frappe validates it on save, so without this filter
	that first migrate dies in `after_migrate` naming a doctype nobody can see is
	missing, and the module it belongs to never gets installed at all.

	Self-healing rather than permanent: the next migrate finds the doctype and
	writes the shortcut. A fresh install is unaffected, because `modules.txt` is
	read at install time and everything is synced before any hook runs.
	"""
	doctypes = tuple((name, doctype_icon) for name, doctype_icon in doctypes if _installed(name))

	shortcuts = [_doctype_shortcut(name, name, doctype_icon) for name, doctype_icon in doctypes]

	return {
		"label": label,
		"icon": icon,
		"shortcuts": shortcuts,
		"links": [
			_card(label, len(doctypes)),
			*(_link(name) for name, _icon in doctypes),
		],
		"content": [
			_header(label),
			_paragraph(intro),
			*_shortcut_blocks(shortcuts, col=3),
			_card_block(label),
		],
	}


def _child_route(label: str) -> str:
	return f"/desk/{slug(label)}"


def _installed(doctype: str) -> bool:
	"""Is this doctype on the site yet? See `_child_spec` for why this is asked."""
	return bool(frappe.db.exists("DocType", doctype))


# --- block and row builders --------------------------------------------------


def _url_shortcut(label: str, url: str, icon: str) -> dict:
	return {"type": "URL", "label": label, "url": url, "icon": icon, "color": "Blue"}


def _doctype_shortcut(label: str, doctype: str, icon: str) -> dict:
	return {"type": "DocType", "label": label, "link_to": doctype, "icon": icon, "color": "Grey"}


def _card(label: str, link_count: int) -> dict:
	return {"type": "Card Break", "label": label, "link_count": link_count, "hidden": 0}


def _link(doctype: str) -> dict:
	return {"type": "Link", "label": doctype, "link_type": "DocType", "link_to": doctype, "hidden": 0}


def _header(text: str) -> dict:
	return _block("header", {"text": f"<span class='h4'><b>{text}</b></span>", "col": 12})


def _paragraph(text: str) -> dict:
	return _block("paragraph", {"text": text, "col": 12})


def _shortcut_blocks(shortcuts: list, col: int) -> list:
	return [_block("shortcut", {"shortcut_name": row["label"], "col": col}) for row in shortcuts]


def _card_block(label: str) -> dict:
	return _block("card", {"card_name": label, "col": 4})


def _block(kind: str, data: dict) -> dict:
	"""One content block, with a stable id derived from the block itself, so
	re-running the installer produces byte-identical content."""
	import hashlib

	seed = f"{kind}:{sorted(data.items())}"

	return {"id": hashlib.sha1(seed.encode()).hexdigest()[:10], "type": kind, "data": data}
