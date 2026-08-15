# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One command that puts The Gambia Red Cross Society on a site. Run once.

    bench --site <site> execute vmmsx.seed.gambia_install.main

This is the production runner: it does in order what a person would otherwise
do in four commands, and it refuses rather than guesses when the site is not in
the state it expects.

    1. purge     empty an existing society's records off the site
    2. gambia    roles, the four-rung ladder, 369 Links, plans, workflows
    3. content   the society's wording on the public landing page
    4. operations vocabularies, twelve opportunities, twelve stories, locations

**The purge is opt-in and it is destructive.** `purge=False` is the default, so
the plain command is safe on a fresh site and does nothing irreversible. Pass
`purge=True` only on a bench that already carries another society's seed, and
take a backup first:

    bench --site <site> backup
    bench --site <site> execute vmmsx.seed.gambia_install.main --kwargs "{'purge': True}"

**Check it before you run it.** `dry_run=True` reports what each step would do,
including exactly what the purge would delete, and writes nothing:

    bench --site <site> execute vmmsx.seed.gambia_install.main --kwargs "{'dry_run': True, 'purge': True}"

**It is safe to run twice.** Every step underneath is idempotent: the second run
reports `exists` against everything and changes nothing. The one exception is
the landing page copy, which is deliberately overwritten each time, because
somebody running the Gambia seed is asking for the Gambia page.
"""

import frappe

from vmmsx.seed import gambia, gambia_operations
from vmmsx.seed import purge as purge_service


def main(purge_first: bool = False, dry_run: bool = False, purge: bool = False) -> dict:
	"""Install the society. `purge_first` and `purge` are the same switch.

	Both spellings are accepted because the destructive flag is the one somebody
	types from memory at a production prompt, and a typo that silently skipped
	the purge would leave two societies on the site with no error to notice.
	"""
	purge_first = _flag(purge_first) or _flag(purge)
	dry_run = _flag(dry_run)

	_require_migrated()

	report: dict = {}

	if purge_first:
		print("\n>>> Step 1 of 4: emptying the site of any existing society\n")
		report["purge"] = purge_service.main(dry_run=dry_run)
	else:
		print("\n>>> Step 1 of 4: skipped (pass purge=True to empty an existing society)\n")

	if dry_run:
		print(
			"\nDry run. Nothing was written.\n"
			"The configuration and operations steps are not simulated: they are idempotent,\n"
			"so the honest way to see what they would do is to run them.\n"
		)
		return report

	print("\n>>> Step 2 of 4: the society, its ladder and its plans\n")
	report["gambia"] = gambia.main(commit=True)

	print("\n>>> Step 3 of 4: the public landing page\n")
	# `gambia.main` already installed the content as its last step. Reported here
	# so the four steps this module promises are the four it prints.
	report["content"] = report["gambia"].get("landing_content")

	print("\n>>> Step 4 of 4: opportunities, stories, vocabularies and locations\n")
	report["operations"] = gambia_operations.main(commit=True)

	_summary()

	return report


def _flag(value) -> bool:
	"""`bench execute --kwargs` hands strings through, so "True" has to work."""
	return bool(frappe.parse_json(value) if isinstance(value, str) else value)


def _require_migrated() -> None:
	"""Stop before touching anything if the app is not migrated on this site.

	The custom fields vmmsx owns on National Society Settings are installed by
	patches, and a seed that ran without them would report a page of
	`skipped: field not installed` and leave the society half-configured, which
	is a worse outcome than refusing.
	"""
	settings = frappe.get_single(gambia.SETTINGS_DOCTYPE)
	missing = [
		field
		for field in ("vmms_volunteer_scope_role", "vmms_content_editor_role", "vmms_task_scope_role")
		if not settings.meta.has_field(field)
	]

	if missing:
		frappe.throw(
			f"This site is not migrated for vmmsx: {', '.join(missing)} missing from "
			f"{gambia.SETTINGS_DOCTYPE}. Run `bench --site {frappe.local.site} migrate` first."
		)


def _summary() -> None:
	counts = {
		"Geo Nodes": frappe.db.count("Geo Node"),
		"Membership plans": frappe.db.count("VMMS Membership Type"),
		"Published opportunities": frappe.db.count("VMMS Deployment Request", {"is_published": 1}),
		"Stories": frappe.db.count("Article", {"status": "Published"}),
		"Published locations": frappe.db.count("VMMS Branch Location", {"is_published": 1}),
	}

	print("\n" + "=" * 60)
	print(f"{gambia.ORGANIZATION_NAME} is installed on {frappe.local.site}")
	print("=" * 60)

	for label, count in counts.items():
		print(f"  {label}: {count}")

	print("\nStill to do by hand")

	for step in gambia.MANUAL_STEPS[:-1]:
		print(f"  - {step}")

	print()
