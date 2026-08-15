# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Place the approver the routing design always needed, and re-open the queue.

**What was broken.** A society seed placed its demo approver at one region and
nowhere else, while the workflows it created resolve `at_level` at the Link and
the district. Most Links and districts have no named manager, so the stage
resolved nobody and the engine escalated to the nearest holder *above* the
anchor — the national node, where nobody held the role either. Every application
outside that one region was admitted to nobody at all: not the applicant, not an
approver, not an administrator, because the gate admits the people a document
routed to rather than whoever holds a role. Real applications could not be
decided.

`gambia.py::_workflows` had written down the requirement — "which is why the
society needs a holder of each role at the national node" — and the seed never
created that holder. The fix is in `place_approver()`; this patch is how it
reaches a site that was seeded before the fix existed.

**Why a patch and not an edit to the seed alone.** A Frappe patch runs once per
site by name, and `seed_society` and `reseed_society_with_operations` are both
already in the Patch Log of every deployed site. Neither will run again, so a
correction inside the seed reaches a fresh install and nothing else.

**It names no society**, the same way the two patches before it do not: the seed
to call is `vmmsx_seed_society` in the site's own config, read through
`seed_society.configured()`. A seed with no `place_approver` is skipped rather
than treated as an error — placing a demo approver is one society's decision
about its own data, not a contract every seed owes this app.

**It re-places, it does not overwrite.** `place_approver()` checks before every
write and reports `exists`, so a society that has since moved its own approvers
keeps them; the only thing added is a national row that was missing. The landing
page is untouched, which is the reason this calls one step rather than the whole
seed.
"""

import frappe

from vmmsx.approvals.services import repair
from vmmsx.patches.seed_society import SEED_PACKAGE, SITE_CONFIG_KEY, configured


def execute():
	_place_the_missing_approver()

	# The other half, and it is needed whether or not anything was placed above.
	# Authority is recomputed on every call, but the review queue is built from
	# ToDos written when a stage was entered — so an application that resolved
	# nobody at submission stays invisible to the person who can now decide it,
	# until something re-asks. This is that re-ask.
	changed = repair.resync_pending()

	if changed:
		print(f"vmmsx: re-opened {sum(changed.values())} approval(s) in the queue: {changed}")
	else:
		print("vmmsx: no pending approval needed reassigning")


def _place_the_missing_approver() -> None:
	society = configured()

	if not society:
		print(
			f"vmmsx: no {SITE_CONFIG_KEY} in this site's config, so no approver was placed.\n"
			f"       bench --site {frappe.local.site} set-config {SITE_CONFIG_KEY} <name>"
		)
		return

	import importlib

	try:
		module = importlib.import_module(f"{SEED_PACKAGE}.{society}")
	except ModuleNotFoundError:
		print(f"vmmsx: {SITE_CONFIG_KEY} names {society!r}, which is not a seed. Nothing placed.")
		return

	place = getattr(module, "place_approver", None)

	if not callable(place):
		print(f"vmmsx: {SEED_PACKAGE}.{society} places no approver of its own. Nothing to do.")
		return

	for row in place() or []:
		print(f"  [{row.get('status'):<12}] {row.get('key')}")
