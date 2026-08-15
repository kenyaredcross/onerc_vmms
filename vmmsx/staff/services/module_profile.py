# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The clean desk: one Module Profile, blocking everything that is not VMMS.

A fresh site installs `erpnext`, `hrms`, `lms`, `buzz`, `raven` and friends
alongside vmmsx, and every one of them ships public Workspaces that carry no
`roles` at all — Frappe's own convention for "visible to any desk user"
(`Workspace.is_permitted()`; see `staff/services/workspaces.py`, which is why
*this* app's own cluster is role-gated instead). A volunteer coordinator who
only ever needed VMMS ends up with Accounting, Buying, HR, Raven and Buzz on
their desk too — none of it wrong, all of it noise.

Frappe's own answer to "hide modules this person has no business in" is a
Module Profile: `User.module_profile` fills `User.block_modules`, and a
role-less Workspace whose `module` is blocked stops falling back to visible
(`Workspace.is_permitted`, `frappe/desk/desktop.py`). That is the whole
mechanism — no client script, no page, no override.

**Computed, not enumerated.** `_blocked_modules()` asks the exact question
`is_permitted()` asks: which modules currently back a public workspace with
no role. That is what makes a module "clutter" here, and asking it directly
means a future app that ships another unrestricted workspace is caught on the
next migrate rather than needing this file edited to name it. Nothing here
is a society's decision — which modules exist is an installer's question, not
national society configuration — so a computed, framework-wide answer is not
the "no hardcoded society policy" rule being bent, only the ordinary "derive
it, don't duplicate it" one this app already holds everywhere else.

**vmmsx's own modules are never blocked**, whatever they carry: the exclusion
is by app (`Module Def.app_name == "vmmsx"`), not by re-deriving which of its
workspaces happen to hold roles today. A vmmsx workspace with a role clears
this list by construction (`is_permitted` prefers roles over blocked modules
in the first place), but excluding by app is what keeps a future vmmsx
workspace shipped without roles by mistake from silently blocking itself.

**Created once, and then it is a society's to tune.** A society that decides
its coordinators should also see, say, the LMS module edits the row this
installs and that edit survives every later migrate — `install()` only ever
creates the missing record, the same "create-if-missing" shape
`registration/services/permissions.py` and the self-service surfaces use for
anything a society might reasonably want to hand-tune afterwards, as opposed
to `staff/services/workspaces.py`'s own cluster, which this app fully owns
the shape of and re-syncs every time.

**Assignment is two different doors, both of them stock Frappe.** A society
assigns it to a member of staff by hand, on the ordinary User form —
`User.module_profile`, no vmmsx code involved at all. A self-service login
gets it automatically, the moment `registration/services/roles.py::grant()`
grants them their volunteer or member role, so a newly approved volunteer's
very first look at the desk is already the clean one. Administrator and
System Manager are never assigned this profile by anything in this app, so
an administrator's own desk is never narrowed by it.
"""

import frappe

MODULE_PROFILE_DOCTYPE = "Module Profile"
WORKSPACE_DOCTYPE = "Workspace"

# The name a society finds on the standard User form, and the name
# `registration/services/roles.py` looks for before assigning it.
PROFILE_NAME = "VMMS Only"

# The one app this installer never blocks a module from, regardless of what
# any of its workspaces carry. See the module docstring.
OWN_APP = "vmmsx"


def install() -> dict:
	"""Create the "VMMS Only" Module Profile if it does not exist yet.

	Called from `after_migrate`, after the workspace installs, so the modules
	it blocks reflect the workspace state this migrate just produced. Safe to
	re-run directly once a fresh app has landed on the bench and a society
	wants the block list picked up again:

	    bench --site <site> execute vmmsx.staff.services.module_profile.install

	**Never touches an existing record.** The block list is a starting point a
	society may hand-tune afterwards — see the module docstring — so an
	existing "VMMS Only" profile, edited or not, is left exactly as it is.
	"""
	if frappe.db.exists(MODULE_PROFILE_DOCTYPE, PROFILE_NAME):
		return {"status": "exists", "blocked": _current_blocked()}

	blocked = _blocked_modules()

	# Runs from after_migrate, building this app's own installer default rather
	# than anybody's document — there is no acting user whose permissions
	# could apply here, the same reasoning `staff/services/workspaces.py`
	# states for its own `ignore_permissions=True`.
	frappe.get_doc(
		{
			"doctype": MODULE_PROFILE_DOCTYPE,
			"module_profile_name": PROFILE_NAME,
			"block_modules": [{"module": module} for module in blocked],
		}
	).insert(ignore_permissions=True)

	return {"status": "created", "blocked": blocked}


def _blocked_modules() -> list[str]:
	"""Every module backing a public, role-less workspace today, except vmmsx's own.

	This is `Workspace.is_permitted()`'s own fallback question, asked once at
	install time instead of trusted to have been asked correctly by whoever
	shipped the workspace: a role-less public workspace is visible to anybody
	unless its module is blocked, so blocking every such module *except*
	vmmsx's own is what "VMMS and nothing else" means in Frappe's own terms.
	"""
	roled = frappe.get_all("Has Role", filters={"parenttype": WORKSPACE_DOCTYPE}, pluck="parent")

	unrestricted_modules = frappe.get_all(
		WORKSPACE_DOCTYPE,
		filters={"public": 1, "name": ("not in", roled or [""])},
		pluck="module",
		distinct=True,
	)

	own_modules = frappe.get_all("Module Def", filters={"app_name": OWN_APP}, pluck="name")

	return sorted({module for module in unrestricted_modules if module and module not in own_modules})


def _current_blocked() -> list[str]:
	"""What the existing profile blocks today, for the caller's report."""
	return frappe.get_all(
		"Block Module", filters={"parent": PROFILE_NAME, "parenttype": MODULE_PROFILE_DOCTYPE}, pluck="module"
	)
