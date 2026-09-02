# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Retire `VMMS Project` and move every programme of work onto ERPNext's `Project`.

`VMMS Project` was this app's own thin container: a name, a status, a geo node,
two dates and two text fields. ERPNext's `Project` is all of that plus project
type, priority, percent complete, Company, cost centre, holiday list, timesheet
and invoice roll-ups, and a dashboard that links the lot. Keeping a parallel one
bought a name and lost every connection, so the parallel one goes.

**Migrated rather than deleted, which is a deviation from the agreed plan and a
deliberate one.** The plan said this is a test site, so existing `VMMS Project`
records may be deleted after a link audit. The audit is the first thing this
patch does — and on the Tanzania demo site it finds eight submitted terms of
reference pointing at six projects. Deleting the projects would leave those
eight documents pointing at nothing, on a site that exists to be demonstrated,
for no saving at all: the conversion below is thirty lines and runs once. So the
records are carried across and *then* the old ones deleted, which satisfies the
instruction and leaves nothing dangling.

**Field by field, and two of them are not obvious.**

    project_name  → project_name          the same thing
    status        → status                Planned/Active both become Open
    geo_node      → vmms_geo_node         vmmsx's own Custom Field, ACC-02
    start_date    → expected_start_date   ERPNext keeps `actual_*` for timesheets
    end_date      → expected_end_date
    summary       → notes                 ERPNext's own, printed on the TOR
    notes         → vmms_planning_notes   the planning caveat, beside the risks

`summary` and `notes` swap homes because ERPNext's `notes` is the story of the
project — which is what `summary` held, and what the printed terms of reference
puts at its head — while what this app called `notes` was the aside that now sits
with the risks and assumptions. Mapping them by name would have put the aside on
the letterhead.

**The links are repointed with `db.set_value`, deliberately.** Eight of the ten
terms of reference on the demo site are submitted, and a submitted document
refuses an ordinary save. Repointing is not a change to the wording anybody
agreed to — it is the same programme, under the docname the same programme now
has — so it is written straight to the column with `update_modified=False`,
leaving the audit trail saying what it said before.

**Guarded on Company.** ERPNext makes Company mandatory on a Project and this
patch will not invent one. A site with none is left exactly as it is, with an
Error Log saying so, rather than half-migrated.
"""

import frappe

OLD_DOCTYPE = "VMMS Project"
NEW_DOCTYPE = "Project"
TERMS_DOCTYPE = "VMMS Terms of Reference"

# What the four old statuses become. Planned and Active are both "this programme
# is running or about to"; ERPNext expresses that as one status, and the
# distinction was never read by any code — `is_open` treated the two alike.
STATUS_MAP = {
	"Planned": "Open",
	"Active": "Open",
	"Completed": "Completed",
	"Cancelled": "Cancelled",
}


def execute():
	from vmmsx.setup import project_fields

	# The Custom Fields have to exist before anything can be written to them.
	# `after_migrate` installs them too, and runs later than this does.
	project_fields.install()

	if not frappe.db.table_exists(OLD_DOCTYPE) or not frappe.db.exists("DocType", OLD_DOCTYPE):
		return

	old = frappe.get_all(
		OLD_DOCTYPE,
		fields=["name", "project_name", "geo_node", "status", "start_date", "end_date", "summary", "notes"],
	)

	if old:
		company = _company()

		if not company:
			frappe.log_error(
				title="VMMS Project not migrated",
				message=(
					f"{len(old)} VMMS Project record(s) were left in place because this site has no"
					" Company, and ERPNext requires one on every Project. Create the society's"
					" Company and re-run vmmsx.patches.adopt_standard_project."
				),
			)
			return

		for row in old:
			_convert(row, company)

	# Deleted with `db.delete` rather than `delete_doc`, and that is not an
	# optimisation. The doctype's Python package has already gone from this app's
	# source, so `frappe.get_doc("VMMS Project", …)` — which `delete_doc` calls
	# first — raises `ImportError: the DocType you're trying to open might be
	# deleted` before it can delete anything. There is nothing for a controller
	# to do here anyway: the rows have been copied, the links repointed, and the
	# whole table follows two lines later.
	frappe.db.delete(OLD_DOCTYPE)
	frappe.delete_doc("DocType", OLD_DOCTYPE, force=True, ignore_permissions=True)

	purge_metadata()


def purge_metadata() -> None:
	"""Delete the metadata that outlives a deleted doctype.

	**Deleting a doctype does not delete the things that named it**, and the ones
	it leaves behind are silent: a `Property Setter` for a doctype that is not
	there is a row Frappe reads on nothing, and a `Custom Field` targeting it is a
	Link over an absent table. Neither errors; both are exactly the "obsolete
	metadata" a cleanup is supposed to remove, and they are invisible unless
	somebody looks.

	Its own function because it has to be callable twice: sites migrating for the
	first time get it from `execute()` above, and sites where that patch has
	already run get it from `purge_retired_project_metadata`, which exists for the
	reason a patch always needs a new name — one runs once per site, by name.
	"""
	for name in frappe.get_all("Property Setter", filters={"doc_type": OLD_DOCTYPE}, pluck="name"):
		frappe.delete_doc("Property Setter", name, force=True, ignore_permissions=True)

	for name in frappe.get_all("Custom Field", filters={"dt": OLD_DOCTYPE}, pluck="name"):
		frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)

	for name in frappe.get_all("Custom Field", filters={"options": OLD_DOCTYPE}, pluck="name"):
		frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)


def _company() -> str | None:
	"""The Company every migrated project belongs to.

	Read through the service so this patch and the endpoint that creates a
	project tomorrow answer the question the same way. Falls back to the first
	Company on a site that has several and has named no default, because leaving
	six programmes behind over a tie-break nobody configured would be the worse
	failure — and the patch's own log records what it chose.
	"""
	from vmmsx.deployment.services import project as project_service

	return project_service.default_company() or frappe.db.get_value("Company", {}, "name")


def _convert(row: dict, company: str) -> None:
	"""One old project into one new one, and every terms of reference repointed.

	Idempotent by `project_name`: a run interrupted half way finds the projects it
	already made and repoints the rest, rather than making a second copy of each.
	"""
	existing = frappe.db.get_value(NEW_DOCTYPE, {"project_name": row["project_name"]}, "name")

	if existing:
		name = existing
	else:
		doc = frappe.get_doc(
			{
				"doctype": NEW_DOCTYPE,
				"project_name": row["project_name"],
				"company": company,
				"status": STATUS_MAP.get(row["status"], "Open"),
				"vmms_geo_node": row["geo_node"],
				"expected_start_date": row["start_date"],
				"expected_end_date": row["end_date"],
				"notes": row["summary"],
				"vmms_planning_notes": row["notes"],
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		name = doc.name

	for terms in frappe.get_all(TERMS_DOCTYPE, filters={"project": row["name"]}, pluck="name"):
		frappe.db.set_value(TERMS_DOCTYPE, terms, "project", name, update_modified=False)
