# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What has to happen when the app is *installed*, as against migrated.

**Frappe does not run an app's patches on a fresh install.** `install_app()`
calls `set_all_patches_as_completed(name)`, which writes every line of
`patches.txt` into the Patch Log without executing any of it. The reasoning is
sound for schema — the doctypes are synced fresh from their JSON, so a patch
that adds a field has nothing to do. It is wrong for everything else this app
keeps in patches, and this app keeps a great deal there:

* the Custom Fields vmmsx owns on core's `National Society Settings` — every
  scope-role setting the access model reads;
* the geo anchor field on Buzz's `Buzz Event`;
* the content surfaces, the notification types, the task and branch modules;
* the society seed itself.

So a brand new site installed the app, marked nineteen patches "done", and had
none of it. That is not a subtle failure: with no scope-role fields there is no
access model, with no geo nodes nobody can register, and with the seed skipped
the sign-up page reports that the society is not taking new accounts. Every one
of those was seen on a real site before this file existed.

**`after_install` therefore runs what a migrate would have run**, and it reads
the list from `patches.txt` rather than restating it, so a patch added next year
is picked up here with nothing to remember. Every post-model-sync patch in this
app is documented idempotent and most are re-run on `after_migrate` anyway, so
running them once more costs a few seconds and guarantees the two paths agree.

**Install order is not ours to control**, which is the other half. A site that
installs vmmsx before Buzz gets a Buzz seam that correctly does nothing, and
nothing would ever come back to it — the patch is spent. `hooks.py` therefore
also puts the seam's installer on `after_migrate`, where it is asked again on
every deploy and installs the field the first time Buzz is actually present.
"""

import frappe
from frappe.modules.patch_handler import PatchType, get_patches_from_app

APP = "vmmsx"


def after_install() -> None:
	"""Run everything a migrate would have, in the order a migrate runs it.

	Two lists, and both are needed. The patches are what Frappe marked complete
	without executing. The `after_migrate` hooks are the other half and are just
	as absent: Frappe runs them on `bench migrate` and nowhere else, so a fresh
	install had no `Email Template` for the welcome or the four application
	messages, no card designs, no staff workspaces and no doctype permissions
	for the roles the seed had just created. Everything in that list is written
	to be idempotent and re-runnable — most of it exists there precisely because
	a patch runs once and a later release needs another go — so running it here
	is the same call a deploy makes.
	"""
	_run_setup_patches()
	_run_after_migrate_hooks()


def _run_setup_patches() -> None:
	"""Every post-model-sync patch, in the order `patches.txt` lists them.

	Read rather than restated: a list here would be a second copy that drifts,
	and the failure of drift is silent — a setting nobody installed, found
	months later by somebody wondering why a role does nothing.

	Pre-model-sync patches are deliberately not run. Those create Module Defs,
	which `install_app` has already done for us through `add_module_defs`.

	One patch failing must not abort the install: the app is already on the site
	by this point, and a half-installed app that reports success is worse than
	one that says which step needs re-running. Each is logged and named.
	"""
	for patch in get_patches_from_app(APP, PatchType.post_model_sync):
		module = patch.split(maxsplit=1)[0]

		_run(f"{module}.execute", module)


def _run_after_migrate_hooks() -> None:
	"""This app's own `after_migrate` entries, in the order it declares them.

	Read from `vmmsx.hooks` directly rather than `frappe.get_hooks`, which
	aggregates every installed app: running another app's migrate hooks from our
	install would be reaching into somebody else's setup, and the order they
	expect is not ours to assume.

	The order within our own list is load-bearing and is preserved: permissions
	follow the workspaces they open, the module profile is computed from the
	workspace state those installs produce, and the society seed is last because
	everything above it is what the seed writes into.
	"""
	from vmmsx import hooks

	for method in getattr(hooks, "after_migrate", []) or []:
		_run(method, method)


def _run(dotted_path: str, label: str) -> None:
	"""Call one setup step, and let the rest of the install continue if it fails.

	The app is already on the site by the time any of this runs, so aborting
	would leave it installed and unconfigured with no record of how far it got.
	Each failure is logged against its own name and printed, so the thing to
	re-run is on screen rather than inferred later from what is missing.
	"""
	try:
		frappe.get_attr(dotted_path)()
	except Exception:
		frappe.log_error(title=f"vmmsx install step failed: {label}")
		print(f"vmmsx: {label} failed on install; re-run it with `bench migrate`")
