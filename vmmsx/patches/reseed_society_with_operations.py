# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Re-run the society's seed, and run its operations companion after it.

**Why a second patch rather than an edit to the first.** `seed_society` is
already in every existing site's Patch Log, and a Frappe patch runs once per
site *by name*. So everything added to a seed after that patch first ran — the
six scope-role settings the console's tab gating depends on, the staff
permission grants that make them mean anything — reaches a hosted site never.
Editing `seed_society` would change code that will not execute again. This is
the same rule `register_member_modules` follows beside `register_modules`, and
CLAUDE.md states it: a module added later needs its own patch.

**And the operations half was never run by a patch at all.** `seed_society`
runs `vmmsx.seed.<society>.main`, which is a society's *configuration* — its
ladder, roles, plans and workflows. What it did last month lives in
`<society>_operations.main`: the branch offices on the public map, the
opportunities, the stories, the vocabularies. On a bench somebody runs that by
hand; a hosted site has no bench to run it from, which is the whole reason
`seed_society` exists, and the operations companion was left out of it.

**Both halves are idempotent**, so this is a re-run rather than a repair: every
step checks before it writes and reports `created` or `exists`. The one
exception is the landing page copy, which `<society>.main` deliberately
overwrites — somebody running the society seed is asking for that society's
page. That is a real cost on a site whose wording has been rewritten in place,
and it is the reason this patch is written down as a decision rather than
quietly added.

**It names no society.** Which seed to run is `vmmsx_seed_society` in the site's
own config, read through `seed_society.configured()` so there is one answer to
what that key means. A society with no operations companion gets the
configuration half and nothing else, which is ordinary rather than an error.

    bench --site <site> set-config vmmsx_seed_society gambia

After this has been logged, re-running is by hand again:

    bench --site <site> execute vmmsx.seed.<society>_operations.main
"""

import frappe

from vmmsx.patches.seed_society import SEED_PACKAGE, SITE_CONFIG_KEY, configured, entry_point

# What a society's operations companion is called, given the society's own name.
# `gambia` -> `gambia_operations`, the convention both seeded societies follow.
OPERATIONS_SUFFIX = "_operations"


def execute():
	society = configured()

	if not society:
		print(
			f"vmmsx: no {SITE_CONFIG_KEY} in this site's config, so nothing was re-seeded.\n"
			f"       bench --site {frappe.local.site} set-config {SITE_CONFIG_KEY} <name>"
		)
		return

	print(f"vmmsx: re-running {SEED_PACKAGE}.{society}.main")

	# migrate owns the transaction, the same reason `seed_society` gives.
	entry_point(society)(commit=False)

	operations = f"{society}{OPERATIONS_SUFFIX}"
	main = entry_point(operations, required=False)

	if not main:
		print(
			f"vmmsx: {society} has no {SEED_PACKAGE}.{operations}, so no operations were seeded.\n"
			f"       That is ordinary: a society's configuration and what it did last month\n"
			f"       are separate seeds, and not every society has the second."
		)
		return

	print(f"vmmsx: seeding operations from {SEED_PACKAGE}.{operations}.main")

	main(commit=False)
