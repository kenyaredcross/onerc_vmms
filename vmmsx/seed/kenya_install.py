# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One command that stands a Kenya Red Cross Society site up for acceptance testing.

    bench --site <site> execute vmmsx.seed.kenya_install.main

This is the production runner, on the same shape as `tanzania_install.py` and
`gambia_install.py`: it does in order what a person would otherwise do in six
commands, refuses rather than guesses when the site is not in the state it
expects, and **finishes by checking its own work**.

    1. purge      empty an existing society's records off the site (opt-in)
    2. kenya      roles, the three-rung ladder, all 47 counties and their 290
                  sub-counties, membership plans, and the county-only workflows
    3. content    the society's wording on the public landing page
    4. operations vocabularies, programmes, terms of reference, open needs,
                  15 events in Buzz and the county announcements
    5. stories    ten articles in the newsroom
    6. jobs       eleven openings on the opportunities board, in HRMS
    7. readiness  every check that has to pass before somebody can be asked to
                  test this site, run against the database rather than assumed

**Nobody is seeded, and that is the design.** No county coordinators, no
volunteers, no members. A site stood up for a UAT by County Coordinators and
volunteers is a site where registering and deciding are the things being tested,
and seeding them would mean both had already happened offstage. What the seed
provides is everything those people need to exist *against*: the counties they
choose from, the workflow that routes their application, the roles that will be
granted to them, and enough real content that every screen they open has
something on it.

**The one account is `approver@krcs.demo`, and it has no password.** It exists so
that the site has an approval path from the first minute and so that
`registration/tests/test_seed.py` has somebody to drive its journey through. Give
it a password with `bench set-password` if you want to sign in as it. To give a
County Coordinator who has signed up for their own account standing over their
own county:

    bench --site <site> execute vmmsx.seed.kenya.promote_coordinator \\
        --kwargs "{'email': 'their@email', 'county_name': 'Kisumu'}"

**One thing the purge does not reach.** `purge.py` empties this app's records,
core's Geo Nodes, Red Profiles and Articles — and nothing belonging to Buzz or
HRMS. So a bench that carried another society keeps that society's `Buzz Event`
and `Job Opening` rows, and they will sit on the KRCS diary and opportunities
board beside the ones seeded here. Deliberately not widened: deleting another
app's records wholesale is a bigger decision than a purge for one society, and
`purge.py` is shared by three of them. Clear them by hand, or install onto a
fresh site, if a mixed board would confuse a tester:

    bench --site <site> console
    >>> frappe.db.delete("Buzz Event")     # every event, from every society
    >>> frappe.db.delete("Job Opening")    # every opening, from every society

**The purge is opt-in and it is destructive.** `purge=False` is the default, so
the plain command is safe on a fresh site and does nothing irreversible. Pass
`purge=True` only on a bench that already carries another society's seed, and
take a backup first:

    bench --site <site> backup
    bench --site <site> execute vmmsx.seed.kenya_install.main --kwargs "{'purge': True}"

**Check it before you run it.** `dry_run=True` reports what each step would do,
including exactly what the purge would delete, and writes nothing:

    bench --site <site> execute vmmsx.seed.kenya_install.main --kwargs "{'dry_run': True, 'purge': True}"

**It is safe to run twice.** Every step underneath is idempotent: the second run
reports `exists` against everything and changes nothing. The one exception is the
landing page copy, which is deliberately overwritten each time, because somebody
running the Kenya seed is asking for the Kenya page.
"""

import frappe

from vmmsx.seed import kenya, kenya_geography, kenya_jobs, kenya_operations, kenya_stories
from vmmsx.seed import purge as purge_service

STEPS = 7


def main(purge_first: bool = False, dry_run: bool = False, purge: bool = False) -> dict:
	"""Install the society. `purge_first` and `purge` are the same switch."""
	purge_first = _flag(purge_first) or _flag(purge)
	dry_run = _flag(dry_run)

	_require_migrated()

	report: dict = {}

	if purge_first:
		print(f"\n>>> Step 1 of {STEPS}: emptying the site of any existing society\n")
		report["purge"] = purge_service.main(dry_run=dry_run)
	else:
		print(f"\n>>> Step 1 of {STEPS}: skipped (pass purge=True to empty an existing society)\n")

	if dry_run:
		print(
			"\nDry run. Nothing was written.\n"
			"The configuration and content steps are not simulated: they are idempotent,\n"
			"so the honest way to see what they would do is to run them.\n"
		)
		return report

	print(f"\n>>> Step 2 of {STEPS}: the society, 47 counties, 290 sub-counties and the workflows\n")
	report["kenya"] = kenya.main(commit=True)

	print(f"\n>>> Step 3 of {STEPS}: the public landing page\n")
	report["content"] = report["kenya"].get("landing_content")

	print(f"\n>>> Step 4 of {STEPS}: vocabularies, programmes, open needs, events and announcements\n")
	report["operations"] = kenya_operations.main(commit=True)

	print(f"\n>>> Step 5 of {STEPS}: the newsroom\n")
	report["stories"] = kenya_stories.main(commit=True)

	print(f"\n>>> Step 6 of {STEPS}: the opportunities board\n")
	report["jobs"] = kenya_jobs.main(commit=True)

	print(f"\n>>> Step 7 of {STEPS}: is this site actually testable?\n")
	report["readiness"] = readiness()

	_summary(report)

	return report


def _flag(value) -> bool:
	"""`bench execute --kwargs` hands strings through, so "True" has to work."""
	return bool(frappe.parse_json(value) if isinstance(value, str) else value)


def _require_migrated() -> None:
	settings = frappe.get_single(kenya.SETTINGS_DOCTYPE)
	missing = [
		field
		for field in ("vmms_volunteer_scope_role", "vmms_content_editor_role", "vmms_task_scope_role")
		if not settings.meta.has_field(field)
	]

	if missing:
		frappe.throw(
			f"This site is not migrated for vmmsx: {', '.join(missing)} missing from "
			f"{kenya.SETTINGS_DOCTYPE}. Run `bench --site {frappe.local.site} migrate` first."
		)


# --- is this site actually testable? --------------------------------------


def readiness() -> list[dict]:
	"""Every check that has to pass before somebody can be asked to test this site.

	    bench --site <site> execute vmmsx.seed.kenya_install.readiness

	Runnable on its own, because "is the site up" is a question worth asking on a
	site somebody has since been editing, not only at the end of an install.

	**Each check reads the database rather than trusting the step that wrote it.**
	A seed reporting `created` proves a row was written; it does not prove the
	rows agree with each other. Every failure below was a real dead end at some
	point during this seed's development — an application accepted into nobody's
	queue, a picker asking for a rung the server would refuse, a portal role sent
	to `/app` — and each is cheaper to catch here than in front of a tester.
	"""
	checks = [
		_check_ladder(),
		_check_tree(),
		_check_anchor_levels(),
		_check_no_dead_end_counties(),
		_check_roles_land_somewhere(),
		_check_signup_is_open(),
		_check_there_is_something_to_look_at(),
	]

	rows = [row for group in checks for row in group]
	_print_readiness(rows)

	return rows


def _ok(key: str, detail: str) -> dict:
	return {"key": key, "status": "ok", "detail": detail}


def _fail(key: str, detail: str) -> dict:
	return {"key": key, "status": "FAILED", "detail": detail}


def _check_ladder() -> list[dict]:
	"""Three active levels, and the county carrying the lowest marker."""
	rows = []

	for level in kenya.LEVELS:
		if not frappe.db.get_value("Geo Level", level["key"], "is_active"):
			rows.append(_fail(f"level {level['key']}", "missing or inactive"))

	county_level = kenya.LEVELS[1]["key"]
	lowest = frappe.get_all("Geo Level", filters={"is_active": 1, "is_lowest_level": 1}, pluck="name")

	if lowest == [county_level]:
		rows.append(_ok("lowest level", f"{county_level}, which is where this society records"))
	elif county_level in lowest:
		rows.append(_ok("lowest level", f"{county_level}, alongside {lowest}"))
	else:
		# Not fatal: `allowed_anchor_levels` is what the server enforces, and the
		# marker is a hint a picker reads. Worth saying out loud all the same,
		# because the usual cause is another society's seed holding it.
		rows.append(
			_ok(
				"lowest level",
				f"held by {lowest or 'nobody'} rather than {county_level} — cosmetic only,"
				" anchoring is enforced by the workflows",
			)
		)

	for key in kenya.RETIRED_LEVELS:
		if frappe.db.exists("Geo Level", key) and frappe.db.get_value("Geo Level", key, "is_active"):
			rows.append(_fail(f"retired level {key}", "still active; it will show as a rung in every picker"))

	return rows


def _check_tree() -> list[dict]:
	"""One root, 47 counties under it, 290 sub-counties under those."""
	root = kenya.national()

	if not root:
		return [_fail("geo tree", f"no {kenya.NATIONAL_NODE} root node")]

	counties = frappe.get_all(
		"Geo Node",
		filters={"geo_level": kenya.LEVELS[1]["key"], "parent_geo_node": root},
		pluck="name",
	)
	subs = frappe.db.count("Geo Node", {"geo_level": kenya.LEVELS[2]["key"]})
	expected_subs = kenya_geography.total_sub_counties()

	rows = []

	if len(counties) == len(kenya.COUNTY_NODES):
		rows.append(_ok("counties", f"{len(counties)} under {kenya.NATIONAL_NODE}"))
	else:
		rows.append(_fail("counties", f"{len(counties)} found, expected {len(kenya.COUNTY_NODES)}"))

	if subs == expected_subs:
		rows.append(_ok("sub-counties", f"{subs}, which is all of them"))
	else:
		rows.append(_fail("sub-counties", f"{subs} found, expected {expected_subs}"))

	# One county spot-checked all the way down, because a count can be right while
	# the parentage is wrong.
	sample = kenya.sub_county(kenya.PRIMARY_COUNTY, 0)

	if sample and frappe.db.get_value("Geo Node", sample, "parent_geo_node") == kenya.primary_county():
		rows.append(_ok("parentage", f"{kenya.SUB_COUNTY_NODES[0]} sits under {kenya.PRIMARY_COUNTY}"))
	else:
		rows.append(_fail("parentage", f"{kenya.PRIMARY_COUNTY}'s first sub-county is not under it"))

	return rows


def _check_anchor_levels() -> list[dict]:
	"""Both workflows accept the county, and nothing below it.

	This is the check that would have caught `kenya_operations._reconcile_workflows`
	silently re-adding the sub-county level after `kenya.py` had just written the
	county on its own.
	"""
	from vmmsx.approvals.services import config

	county_level = kenya.LEVELS[1]["key"]
	sub_level = kenya.LEVELS[2]["key"]
	rows = []

	for doctype in (kenya.APPLICATION_DOCTYPE, kenya.MEMBERSHIP_DOCTYPE):
		if not frappe.db.exists(kenya.WORKFLOW_DOCTYPE, {"workflow_for": doctype}):
			rows.append(_fail(f"workflow for {doctype}", "none configured; nothing can be submitted"))
			continue

		levels = config.allowed_anchor_levels_for(doctype)

		if sub_level in levels:
			rows.append(
				_fail(
					f"anchor levels for {doctype}",
					f"{sub_level} is anchorable; approval was asked to be through the county only",
				)
			)
		elif levels == [county_level]:
			rows.append(_ok(f"anchor levels for {doctype}", "the county, and only the county"))
		elif not levels:
			rows.append(
				_fail(
					f"anchor levels for {doctype}",
					"empty, which means any active level — including the 290 sub-counties",
				)
			)
		elif county_level not in levels:
			# The case a shared bench actually produces, and the one this branch
			# used to report as `ok` while saying the opposite. `_workflows()`
			# skips a doctype another society already governs, so on such a bench
			# the governing workflow is theirs and a Kenyan county is refused at
			# submit — "Nairobi is at County level. VMMS Volunteer Application may
			# only be anchored at: Branch, Sub-Branch." Nobody can register.
			rows.append(
				_fail(
					f"anchor levels for {doctype}",
					f"{levels} — the county is not among them, so no county application can be"
					" submitted at all. Another society's workflow governs this doctype; run"
					" vmmsx.seed.kenya_operations.main to widen it by the county",
				)
			)
		else:
			rows.append(_ok(f"anchor levels for {doctype}", f"{levels}, which includes the county"))

	return rows


def _check_no_dead_end_counties() -> list[dict]:
	"""Every county has somebody its applications can route to.

	The failure this exists for: routing is nearest-ancestor, so an application
	filed in a county whose own coordinator does not exist walks up to the
	national root and stops. If nobody holds the stage's role at the root either,
	the application is accepted and lands in no queue — no error, no ToDo, and
	nobody to notice. Measured by walking the tree the way the engine does rather
	than by counting Geo Assignments.
	"""
	from onerc_core.geo.services import adapter

	root = kenya.national()

	if not root:
		return [_fail("routing", "no root node to route to")]

	rows = []

	for doctype in (kenya.APPLICATION_DOCTYPE, kenya.MEMBERSHIP_DOCTYPE):
		workflow_name = frappe.db.get_value(kenya.WORKFLOW_DOCTYPE, {"workflow_for": doctype}, "name")

		if not workflow_name:
			continue

		workflow = frappe.get_cached_doc(kenya.WORKFLOW_DOCTYPE, workflow_name)
		roles = [stage.required_role for stage in workflow.stages if stage.required_role]

		for role in roles:
			holders = set(
				frappe.get_all("Geo Assignment", filters={"role": role, "is_active": 1}, pluck="geo_node")
			)

			if not holders:
				rows.append(_fail(f"{role}", "nobody holds it anywhere; every county is a dead end"))
				continue

			dead = [
				label
				for label in kenya.COUNTY_NODES
				if (node := kenya.county_named(label))
				and not adapter.resolve_upward(node, lambda candidate: candidate in holders)
			]

			if dead:
				rows.append(
					_fail(
						f"{role}",
						f"{len(dead)} counties route to nobody, starting with {', '.join(dead[:5])}",
					)
				)
			else:
				rows.append(
					_ok(f"{role}", f"every one of the {len(kenya.COUNTY_NODES)} counties routes to somebody")
				)

	return rows


def _check_roles_land_somewhere() -> list[dict]:
	"""A portal role with no home page signs somebody in and hands them `/app`."""
	from vmmsx.registration.services.desk import PORTAL_HOME

	rows = []

	for name, _description, desk_access in kenya.ROLES:
		if not frappe.db.exists("Role", name):
			rows.append(_fail(f"role {name}", "missing"))
			continue

		if desk_access:
			continue

		if frappe.db.get_value("Role", name, "home_page") == PORTAL_HOME:
			continue

		rows.append(_fail(f"role {name}", f"lands nowhere in the portal; expected {PORTAL_HOME}"))

	if not rows:
		rows.append(_ok("roles", "all present, and every portal role lands in the portal"))

	return rows


def _check_signup_is_open() -> list[dict]:
	"""Nobody can register on a site that will not let them make an account."""
	rows = []
	signup = frappe.db.get_single_value("Website Settings", "disable_signup")
	default_role = frappe.db.get_single_value("Portal Settings", "default_role")

	if signup:
		rows.append(_fail("signup", "disabled in Website Settings; nobody can create an account"))
	else:
		rows.append(_ok("signup", "open, so a coordinator or a volunteer can create their own account"))

	if default_role == kenya.ROLE_APPLICANT:
		rows.append(_ok("default role", kenya.ROLE_APPLICANT))
	else:
		rows.append(_fail("default role", f"{default_role!r} rather than {kenya.ROLE_APPLICANT!r}"))

	return rows


def _check_there_is_something_to_look_at() -> list[dict]:
	"""Content, per surface. A screen that works and is empty tests nothing.

	Not fatal — a site with an empty newsroom is a usable site — so these report
	as `ok` with a count, and a zero says so plainly rather than passing quietly.
	"""
	surfaces = {
		"stories": ("Article", {"status": "Published", "docstatus": 1}),
		"events": ("Buzz Event", {"is_published": 1}),
		"opportunities": ("Job Opening", {"publish": 1, "status": "Open"}),
		"announcements": ("VMMS Announcement", {"status": "Published"}),
		"open needs": ("VMMS Deployment Request", {"is_published": 1}),
		"membership plans": ("VMMS Membership Type", {"is_active": 1}),
	}

	rows = []

	for label, (doctype, filters) in surfaces.items():
		if not frappe.db.exists("DocType", doctype):
			rows.append(_ok(label, f"{doctype} is not installed on this site"))
			continue

		count = frappe.db.count(doctype, filters)
		rows.append(_ok(label, f"{count} to look at") if count else _fail(label, "nothing to look at"))

	return rows


def _print_readiness(rows: list[dict]) -> None:
	failures = [row for row in rows if row["status"] != "ok"]

	print("Readiness")

	for row in rows:
		mark = "  ok  " if row["status"] == "ok" else "FAILED"
		print(f"  [{mark}] {row['key']}: {row['detail']}")

	if failures:
		print(f"\n  {len(failures)} check(s) failed. This site is not ready to be tested.")
	else:
		print(f"\n  All {len(rows)} checks passed.")

	print()


# --- the report -----------------------------------------------------------


def _summary(report: dict) -> None:
	counts = {
		"Counties": frappe.db.count("Geo Node", {"geo_level": kenya.LEVELS[1]["key"]}),
		"Sub-counties": frappe.db.count("Geo Node", {"geo_level": kenya.LEVELS[2]["key"]}),
		"Membership plans": frappe.db.count("VMMS Membership Type"),
		"Published events": frappe.db.count("Buzz Event", {"is_published": 1})
		if frappe.db.exists("DocType", "Buzz Event")
		else "Buzz not installed",
		"Opportunities on the board": frappe.db.count("Job Opening", {"publish": 1, "status": "Open"})
		if frappe.db.exists("DocType", "Job Opening")
		else "HRMS not installed",
		"Stories": frappe.db.count("Article", {"status": "Published", "docstatus": 1})
		if frappe.db.exists("DocType", "Article")
		else "onerc_core Article not installed",
		"Announcements": frappe.db.count("VMMS Announcement", {"status": "Published"}),
		"Programmes": frappe.db.count("Project", {"vmms_geo_node": ("is", "set")}),
		"Terms of reference": frappe.db.count("VMMS Terms of Reference"),
		"Open needs": frappe.db.count("VMMS Deployment Request", {"is_published": 1}),
		"Volunteer applications": frappe.db.count(kenya.APPLICATION_DOCTYPE),
		"Volunteers": frappe.db.count("VMMS Volunteer"),
		"Memberships": frappe.db.count("VMMS Membership"),
	}

	failures = [row for row in report.get("readiness", []) if row["status"] != "ok"]

	print("\n" + "=" * 62)
	print(f"{kenya.ORGANIZATION_NAME} is installed on {frappe.local.site}")
	print("=" * 62)

	for label, count in counts.items():
		print(f"  {label}: {count}")

	print("\nThe last three are zero on purpose. See the note at the top of this file.")

	print("\nStill to do by hand")

	for step in kenya.MANUAL_STEPS:
		print(f"  - {step}")

	print("\nRunning the UAT")
	print("  1. Coordinators and volunteers each sign up for their own account at /login.")
	print("  2. For each coordinator, give them their county:")
	print("       bench --site <site> execute vmmsx.seed.kenya.promote_coordinator \\")
	print("         --kwargs \"{'email': 'their@email', 'county_name': 'Kisumu'}\"")
	print("  3. Volunteers register through the portal and choose their county. Until a")
	print(f"     county has its own coordinator, its applications route to {kenya.APPROVER_USER}")
	print(f"     at the {kenya.NATIONAL_NODE} root, so nothing is ever accepted into an empty queue.")
	print("  4. Re-run the readiness check any time:")
	print("       bench --site <site> execute vmmsx.seed.kenya_install.readiness")

	if failures:
		print(f"\n  {len(failures)} readiness check(s) FAILED — see step 7 above.")

	print()
