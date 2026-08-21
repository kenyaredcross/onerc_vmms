# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Empty this site of seeded and demo data, so one society's seed can own it.

    bench --site <site> execute vmmsx.seed.purge.main

**Why this exists.** A bench that has had more than one society's seed run
against it holds both, and they do not simply sit side by side: two active geo
ladders mean core's `resolve_upward` has two roots to choose from, a workflow
written for one society's levels refuses the other's records under ACC-03, and
the analytics panels count both. `seed/repair_workflows.py` widens a workflow
that is merely too narrow; this is the other half, for a site that should hold
one society and currently holds two.

**It deletes operational records, not the product.** Doctypes, workspaces,
templates, custom fields, roles and the content *surfaces* survive; the rows a
seed created inside them do not. Content blocks are left alone because a
society's seed overwrites them by key and a blank page between the two steps
would be worse than the old society's words.

**This is destructive and it is not clever about it.** It does not try to tell a
demo volunteer from a real one, because on the operational doctypes there is no
field that would answer the question, and a rule that guessed would be the kind
that deletes the one record somebody actually entered. It empties them. Run it
on a bench or on a site being set up, and take a backup first:

    bench --site <site> backup

`dry_run=True` reports exactly what it would delete and deletes nothing. That is
the intended first run.
"""

import frappe

# Deletion order, dependants before the records they point at. Frappe refuses a
# delete that would orphan a Link, so this is not a preference: `VMMS Time Log`
# points at a volunteer and a deployment, so both outlive it by two lines.
#
# Child tables are absent on purpose. A child row is deleted with its parent,
# and naming one here would delete the row out from under a parent that still
# expects it.
OPERATIONAL_DOCTYPES = (
	# what somebody did
	"VMMS Task",
	"VMMS Time Log",
	"VMMS Certification",
	"VMMS Stipend Payment Form",
	"VMMS Stipend Progress Report",
	# where they were sent
	"VMMS Deployment Request",
	# One person's place on a deployment, and it outlives neither: it points at
	# the deployment and at the volunteer, so it goes before both.
	"VMMS Deployment Assignment",
	"VMMS Deployment",
	# what they were told
	"VMMS Notification",
	"VMMS Announcement",
	# who they are to the society
	"VMMS Membership",
	"VMMS Member",
	"VMMS Volunteer Application",
	"VMMS Branch Transfer",
	"VMMS Volunteer",
	# where the society is
	"VMMS Branch Location",
)

# Configuration a society's seed writes and the next society's seed would
# otherwise inherit. The vocabularies go because they are the society's own
# words (a Kenyan time-log category is not a Gambian one); the workflows go
# because a workflow names one doctype, so the second society never gets its
# own and silently inherits the first's roles and anchor levels.
CONFIGURATION_DOCTYPES = (
	"VMMS Approval Workflow",
	"VMMS Membership Type",
	"VMMS Terms of Reference",
	# A programme of work is operational rather than configuration, and it is
	# listed here anyway: a terms of reference points at its project, and the
	# rule this file is ordered by is dependants first. Leaving it out is what
	# stranded a departing society's projects on an anchor `_empty_geo_nodes`
	# had already force-deleted underneath them — a register that then threw
	# "Geo Node GEO-00004 does not exist" at everybody who opened it.
	"VMMS Project",
	"VMMS Certification Type",
	"VMMS Time Log Category",
	"VMMS Announcement Type",
	"VMMS Skill",
	"VMMS Motivation",
	"VMMS Availability Slot",
)

# Core's records. Deleted last: everything above points at them.
CORE_DOCTYPES = ("Geo Assignment", "Red Profile", "Article")

GEO_NODE = "Geo Node"
GEO_LEVEL = "Geo Level"

SETTINGS_DOCTYPE = "National Society Settings"

# The previous society's answers on the settings single. They are cleared rather
# than left, because every society seed sets these *only when empty* — which is
# the right rule for a re-run and the wrong one for a site changing hands: a
# Gambian seed run over a Kenyan one otherwise reports `exists` against a Kenyan
# time zone and leaves it in place. Clearing here is what makes the next seed's
# answer the one that lands.
#
# The logo is not in the list. It is an uploaded file rather than a value, and a
# society that has uploaded its own mark before running a seed should keep it.
SOCIETY_FIELDS = (
	"organization_name",
	"organization_short_name",
	"country",
	"currency",
	"time_zone",
	"primary_language",
	"official_website",
	"telephone",
	"physical_address",
	"phone_number_pattern",
	"phone_number_example",
	# The role settings vmmsx owns. Each names a role, and a role that belonged
	# to the departing society's ladder gates the arriving society's writes.
	"vmms_volunteer_scope_role",
	"vmms_membership_scope_role",
	"vmms_announcement_scope_role",
	"vmms_task_scope_role",
	"vmms_content_editor_role",
	"vmms_certificate_print_role",
	"vmms_volunteer_member_role",
	"vmms_membership_member_role",
	"vmms_self_service_role",
	"vmms_membership_anchor_level",
)


def main(dry_run: bool = False, keep_articles: bool = False) -> dict:
	"""Empty the site. Reports counts per doctype.

	`dry_run` counts and prints without deleting, and is the sensible first run.
	`keep_articles` spares core's `Article`, which is the one doctype here a
	society may have written into by hand rather than by seed.
	"""
	dry_run = frappe.parse_json(dry_run) if isinstance(dry_run, str) else dry_run
	keep_articles = frappe.parse_json(keep_articles) if isinstance(keep_articles, str) else keep_articles

	report: dict[str, dict] = {}
	core = tuple(d for d in CORE_DOCTYPES if not (keep_articles and d == "Article"))

	for doctype in OPERATIONAL_DOCTYPES + CONFIGURATION_DOCTYPES + core:
		report[doctype] = _empty(doctype, dry_run)

	report[GEO_NODE] = _empty_geo_nodes(dry_run)
	report[GEO_LEVEL] = _empty(GEO_LEVEL, dry_run)
	report[SETTINGS_DOCTYPE] = _clear_settings(dry_run)

	if not dry_run:
		frappe.db.commit()

	_print(report, dry_run)

	return report


# --- the delete -----------------------------------------------------------


def _empty(doctype: str, dry_run: bool) -> dict:
	if not frappe.db.exists("DocType", doctype):
		return {"status": "absent", "deleted": 0}

	names = frappe.get_all(doctype, pluck="name", limit_page_length=0)

	if dry_run:
		return {"status": "would delete", "deleted": len(names), "names": names[:5]}

	deleted, failed = 0, []

	for name in names:
		try:
			_cancel_if_submitted(doctype, name)
			# `force` skips the link check, which is what makes the order above a
			# courtesy rather than a requirement; `delete_permanently` keeps the
			# Deleted Document trail from being the thing that fills the site up.
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True, delete_permanently=True)
			deleted += 1
		except Exception as error:
			failed.append(f"{name}: {error}")

	return {"status": "deleted", "deleted": deleted, "failed": failed}


def _cancel_if_submitted(doctype: str, name: str) -> None:
	"""A submitted document refuses to be deleted, so cancel it first.

	None of vmmsx's own approvable doctypes reach `docstatus = 1` — the approval
	state is their lifecycle and they stay at 0 — but core's `Article` is a
	submittable doctype and a published one is submitted. Without this the
	articles survive the purge and the next society's stories land beside the
	last society's.
	"""
	if frappe.db.get_value(doctype, name, "docstatus") != 1:
		return

	doc = frappe.get_doc(doctype, name)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.cancel()


def _empty_geo_nodes(dry_run: bool) -> dict:
	"""Leaves first. A Geo Node is a nested set and a parent still holding
	children refuses to go, so the tree comes down from the bottom.

	Ordering on `lft` descending is that order: in a nested set the deepest,
	rightmost node has the highest `lft`, so walking down it never reaches a
	parent before its children.
	"""
	if not frappe.db.exists("DocType", GEO_NODE):
		return {"status": "absent", "deleted": 0}

	names = frappe.get_all(GEO_NODE, pluck="name", order_by="lft desc", limit_page_length=0)

	if dry_run:
		return {"status": "would delete", "deleted": len(names), "names": names[:5]}

	deleted, failed = 0, []

	for name in names:
		try:
			doc = frappe.get_doc(GEO_NODE, name)
			# The nested-set controller refuses to delete a node it still counts
			# as a group. Every node here is going, so the flag is noise.
			doc.flags.ignore_permissions = True
			doc.is_group = 0
			doc.save(ignore_permissions=True)
			frappe.delete_doc(GEO_NODE, name, force=True, ignore_permissions=True, delete_permanently=True)
			deleted += 1
		except Exception as error:
			failed.append(f"{name}: {error}")

	return {"status": "deleted", "deleted": deleted, "failed": failed}


def _clear_settings(dry_run: bool) -> dict:
	"""Empty the departing society's answers off the settings single.

	**A mandatory field is left alone and reported.** Core makes the society's
	name, short name, country and primary language required, so a single with
	them blanked does not save at all. They are also the four an operator
	notices immediately on the settings form, unlike a time zone quietly reading
	`Africa/Nairobi` on a Gambian site, which is the case this function exists
	for. Blanking what can be blanked and naming what cannot is the honest split.
	"""
	settings = frappe.get_single(SETTINGS_DOCTYPE)
	clearable, kept = [], []

	for field in SOCIETY_FIELDS:
		if not (settings.meta.has_field(field) and settings.get(field)):
			continue

		if settings.meta.get_field(field).reqd:
			kept.append(f"{field}={settings.get(field)}")
		else:
			clearable.append(field)

	if dry_run:
		return {"status": "would clear", "deleted": len(clearable), "names": clearable[:5], "kept": kept}

	for field in clearable:
		settings.set(field, None)

	if clearable:
		settings.save(ignore_permissions=True)
		frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)

	return {"status": "cleared", "deleted": len(clearable), "failed": [], "kept": kept}


def _print(report: dict, dry_run: bool) -> None:
	head = "Would purge" if dry_run else "Purged"
	print(f"\n{head} {frappe.local.site}\n" + "=" * 60)

	total = 0

	for doctype, row in report.items():
		if not row["deleted"] and row["status"] == "absent":
			continue

		total += row["deleted"]
		note = ""

		if row.get("failed"):
			note = f"  ({len(row['failed'])} failed)"
		elif row.get("names"):
			note = "  e.g. " + ", ".join(row["names"])

		print(f"  [{row['status']:<12}] {doctype}: {row['deleted']}{note}")

	print(f"\n{total} record(s) {'to delete' if dry_run else 'deleted'}.")

	for doctype, row in report.items():
		for failure in row.get("failed", []):
			print(f"  FAILED {doctype} {failure}")

	kept = report.get(SETTINGS_DOCTYPE, {}).get("kept") or []

	if kept:
		print(
			"\nLeft on National Society Settings because core makes them mandatory."
			"\nThe next society's seed will not overwrite them; edit them on the form if they"
			"\nstill name the society that is leaving:"
		)

		for field in kept:
			print(f"  - {field}")

	if dry_run:
		print("\nNothing was deleted. Re-run without dry_run to do it.")
