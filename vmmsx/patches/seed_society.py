# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Run the seed a site has declared itself to be, once, on migrate.

**Why this is a patch.** A society's configuration — its ladder, its roles, its
membership plans, its approval workflows — is data an administrator creates,
and on a bench somebody runs `vmmsx.seed.<society>.main` by hand. A hosted site
has no bench to run it from: the only thing that executes server-side code on a
deploy is migrate, and the only thing migrate runs exactly once per site is a
patch. The browser cannot stand in — `frappe.client` reaches whitelisted
methods only, and the System Console's sandbox refuses the import.

**It names no society.** Which seed to run is `vmmsx_seed_society` in the site's
own config, and this imports `vmmsx.seed.<that>`. Kenya, Gambia and a society
added next year are one line of configuration and no change here, which is the
rule the rest of the app follows: a second society is a second seed, never a
branch in shared code.

    bench --site <site> set-config vmmsx_seed_society gambia

On Frappe Cloud the same key goes in the site's Config editor in the dashboard.

**A site that has not declared one is left alone, and says so.** That is the
state every existing bench is in, and a patch that guessed would seed one
society's ladder onto another society's site — the failure this whole app is
structured to prevent.

Idempotent twice over: a patch runs once per site by name, and every seed is
itself safe to re-run, checking before it writes and never overwriting a value
an administrator has since edited. After this has been logged, re-running is
`bench --site <site> execute vmmsx.seed.<society>.main`.
"""

import importlib

import frappe

SITE_CONFIG_KEY = "vmmsx_seed_society"
SEED_PACKAGE = "vmmsx.seed"


def configured() -> str | None:
	"""The society this site has declared itself to be, validated, or None.

	Shared with `reseed_society_with_operations`, which asks the same config key
	the same question — one answer to what `vmmsx_seed_society` means, rather
	than two that can disagree about which values are acceptable.
	"""
	society = frappe.conf.get(SITE_CONFIG_KEY)

	if not society:
		return None

	society = str(society)

	# A config value becomes a module path below, so it may only be a bare
	# name. Anything dotted or relative would reach outside the seed package.
	if not society.isidentifier():
		frappe.throw(
			f"{SITE_CONFIG_KEY} is {society!r}, which is not a module name. "
			f"It names one module in {SEED_PACKAGE}, such as the country a site belongs to.",
			title="Bad Society Seed Name",
		)

	return society


def entry_point(module_name: str, required: bool = True):
	"""`vmmsx.seed.<module_name>.main`, or None when it is optional and absent.

	`required=False` is for the operations companion: a society may have one and
	may not, and not having one is an ordinary state rather than a broken site.
	"""
	try:
		module = importlib.import_module(f"{SEED_PACKAGE}.{module_name}")
	except ModuleNotFoundError:
		if not required:
			return None

		frappe.throw(
			f"{SITE_CONFIG_KEY} names {module_name!r}, and there is no {SEED_PACKAGE}.{module_name} "
			f"to run. Available: {', '.join(_available()) or 'none'}.",
			title="No Such Society Seed",
		)

	main = getattr(module, "main", None)

	if not callable(main):
		if not required:
			return None

		frappe.throw(
			f"{SEED_PACKAGE}.{module_name} has no main() to run.",
			title="Seed Has No Entry Point",
		)

	return main


def execute():
	society = configured()

	if not society:
		print(
			f"vmmsx: no {SITE_CONFIG_KEY} in this site's config, so no society seed was run.\n"
			f"       bench --site {frappe.local.site} set-config {SITE_CONFIG_KEY} <name>"
		)
		return

	main = entry_point(society)

	print(f"vmmsx: seeding {society} from {SEED_PACKAGE}.{society}.main")

	# migrate owns the transaction. Every seed takes this argument for exactly
	# this case, and committing inside a patch would leave a half-migrated site
	# looking finished if a later patch failed.
	main(commit=False)


def _available() -> list[str]:
	"""Seed modules that could be named, for the error message.

	A seed is a module with a `main`; the operations companions have one too and
	are listed, because naming one is a fair thing to want and it will work.
	"""
	from pathlib import Path

	directory = Path(__file__).resolve().parents[1] / "seed"

	return sorted(
		path.stem
		for path in directory.glob("*.py")
		if not path.stem.startswith("_") and "def main(" in path.read_text()
	)
