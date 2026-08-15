# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Seed the society this site says it is, once, whenever the site is ready.

The society seed has been reachable three ways and each has failed a real site
for a different reason. A bench command needs a bench, which a hosted site does
not have. A patch runs once per site by name — and on a *fresh install* Frappe
marks every patch complete without running it, so a new site got nothing at all.
And both of those had to be aimed at the right moment: set the config key after
the install and the one thing that would have seeded is already spent.

So this asks the question on every install and every migrate, and answers it
from the state of the site rather than from a log of what has been attempted:

    is a society named in the site's config, and is it not on the site yet?

If both, seed it. If the society is already here, do nothing — which is what
makes this safe to run on every deploy forever, and what stops a redeploy from
overwriting a landing page somebody has since rewritten.

**It names no society.** Which one to seed is `vmmsx_seed_society` in the site's
own config, the same key `patches/seed_society.py` reads, resolved through the
same function so the two cannot disagree about what a valid value is.

**"Already here" is a Geo Node, not a flag.** Every seed declares
`NATIONAL_NODE`, and the presence of that node is the honest test of whether the
society has been created: it is the root everything else hangs from, it cannot
be there by accident, and unlike a marker in a settings field it stays true if
somebody restores a backup or copies a site. A society half-seeded by an
interrupted run is re-run and completes, because every seed is idempotent.
"""

import frappe

from vmmsx.patches.seed_society import SEED_PACKAGE, SITE_CONFIG_KEY, configured, entry_point


def ensure_society(force: bool = False) -> dict | None:
	"""Seed the configured society if it is not on this site yet.

	`force=True` re-runs it even when the society is present, which is what a
	person asking for it by hand means. Note that a re-run overwrites the
	landing page copy — the one deliberately non-additive step in a seed — so it
	is not the default and never happens on a deploy.

	Returns the seed's own report, or None when there was nothing to do.
	"""
	society = configured()

	if not society:
		return None

	if not force and is_seeded(society):
		return None

	main = entry_point(society)

	print(f"vmmsx: seeding {society} from {SEED_PACKAGE}.{society}.main")

	# The caller owns the transaction: `after_install` and `after_migrate` are
	# both inside one, and committing here would leave a partly-set-up site
	# looking finished if a later step failed.
	report = main(commit=False)

	_seed_operations(society)

	return report


def is_seeded(society: str) -> bool:
	"""Is this society's root node on the site?

	A seed that declares no `NATIONAL_NODE` is treated as never seeded, so it
	runs and its own idempotence decides what happens. That is the safe way
	round: running an idempotent seed again costs seconds, and skipping one that
	was never run costs a site nobody can use.
	"""
	module = _module(society)
	root = getattr(module, "NATIONAL_NODE", None) if module else None

	if not root:
		return False

	return bool(frappe.db.exists("Geo Node", {"geo_node_name": root}))


def _seed_operations(society: str) -> None:
	"""The society's operations companion, where it has one.

	Configuration is what a society holds and an operation is what it did last
	month, which is why they are two modules — but a site being set up for a
	demonstration wants both, and the operations half is where the branch
	offices, the published opportunities, the stories and the events live. A
	society with no companion is ordinary, not an error.
	"""
	main = entry_point(f"{society}_operations", required=False)

	if not main:
		return

	print(f"vmmsx: seeding operations from {SEED_PACKAGE}.{society}_operations.main")

	main(commit=False)


def _module(society: str):
	import importlib

	try:
		return importlib.import_module(f"{SEED_PACKAGE}.{society}")
	except ModuleNotFoundError:
		return None
