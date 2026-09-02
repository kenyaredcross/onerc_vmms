# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Give every declaration already on a site the version record it now needs.

Before `VMMS Declaration Version` existed, a declaration carried one `version`
label and one `body`, and rewording it overwrote both. That wording is now
published as a submitted version record — frozen, dated, and pointed at by every
acceptance made against it — and this is what carries an existing site across.

**What it does, in the order it has to happen:**

1. Every declaration with no version record gets one, holding the wording it is
   showing right now, wearing the version label it is already wearing. Submitted,
   because it *is* published — applicants have been reading it.
2. Every declaration with no `source` gets `Text`. Those all hold wording; the
   field is new and empty means "nobody has said", not "no wording".
3. Every acceptance already recorded is pointed at the version record that
   matches the label it was stamped with, and told that what it snapshotted was
   text. An acceptance whose label matches nothing keeps its snapshot and gains
   no link, which is the honest outcome: it recorded wording that has since been
   replaced by a rewording nobody preserved, and inventing a version record for
   it would manufacture a document that never existed.

**`published_on` is the declaration's `modified`, not now.** The date this patch
ran is the date somebody deployed, and stamping it would say the society
published its privacy notice on the morning of an upgrade. `modified` is the last
time the row changed, which for a wording that has been sitting there unedited is
the closest true answer available — and it is what makes `current_version`, which
orders by `published_on`, put a genuinely later version after this one.

**Written with `db.set_value` and one insert, not through `sync_mirror`.** The
mirror is already correct: this patch is reading its values *out* of the
declaration to build the version, so writing them back would be a no-op through
three more layers. The version is inserted and submitted through the document API
because `docstatus` is not a column to poke at, and because the controller's own
checks are exactly the ones a migration should not be skipping.
"""

import frappe

from vmmsx.registration.services import declarations

DECLARATION_DOCTYPE = "VMMS Declaration"
VERSION_DOCTYPE = "VMMS Declaration Version"
ACCEPTANCE_DOCTYPE = "VMMS Declaration Acceptance"


def execute() -> dict:
	if not frappe.db.exists("DocType", VERSION_DOCTYPE):
		return {"published": [], "acceptances": 0}

	published = _publish_current_wording()
	acceptances = _link_acceptances()

	return {"published": published, "acceptances": acceptances}


def _publish_current_wording() -> list[str]:
	"""One submitted version per declaration that has none yet."""
	published = []

	rows = frappe.get_all(
		DECLARATION_DOCTYPE,
		fields=["name", "version", "body", "source", "external_url", "modified"],
	)

	for row in rows:
		if not row.source:
			frappe.db.set_value(
				DECLARATION_DOCTYPE, row.name, "source", declarations.SOURCE_TEXT, update_modified=False
			)

		if frappe.db.exists(VERSION_DOCTYPE, {"declaration": row.name}):
			continue

		if not (row.version and (row.body or row.external_url)):
			# A declaration with no wording and no address has nothing to
			# publish. Skipped rather than refused: it is a half-finished
			# configuration row, and a migration is not the place to insist
			# somebody finishes it.
			continue

		version = declarations.publish(
			row.name,
			row.version,
			body=row.body,
			external_url=row.external_url,
		)

		version.db_set("published_on", row.modified, update_modified=False)

		published.append(version.name)

	return published


def _link_acceptances() -> int:
	"""Point every recorded acceptance at the version record it was made against."""
	versions = {
		(row.declaration, row.version): row.name
		for row in frappe.get_all(
			VERSION_DOCTYPE, filters={"docstatus": 1}, fields=["name", "declaration", "version"]
		)
	}

	rows = frappe.get_all(
		ACCEPTANCE_DOCTYPE,
		filters={"declaration_version": ["is", "not set"]},
		fields=["name", "declaration", "version"],
	)

	linked = 0

	for row in rows:
		values = {"source": declarations.SOURCE_TEXT}
		version = versions.get((row.declaration, row.version))

		if version:
			values["declaration_version"] = version

		frappe.db.set_value(ACCEPTANCE_DOCTYPE, row.name, values, update_modified=False)
		linked += 1

	return linked
