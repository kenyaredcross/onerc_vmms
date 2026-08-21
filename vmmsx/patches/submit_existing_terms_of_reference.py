# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Submit the terms of reference that were written before submitting existed.

`VMMS Terms of Reference` became submittable when it grew into a mission
document — background, stakeholders, objectives, outputs, approach, itinerary,
resources. The reason it submits is that there is no separate contract: a
volunteer accepting a deployment assignment is accepting *these terms*, and a
document somebody has agreed to must not be editable afterwards.

**Without this patch every existing terms of reference is a draft**, because
that is what `docstatus` defaults to, and `terms.assert_offered` refuses a draft
— so every society already running on this app would find that no deployment and
no request could be raised under any of its existing specifications. The records
would look fine and the whole deployment seam would be shut.

**Set directly, not through `submit()`.** The controller's `validate` now holds
rules that did not exist when these records were written — a mission that ends
before it begins, an itinerary dated outside its own period — and none of them
can be true of a record that has none of those fields. Running the full submit
would re-validate documents nobody edited and could refuse one for a reason its
author was never given the chance to answer. What is wanted here is the
docstatus, not a fresh opinion about wording that has been in use for months.

Cancelled terms are left alone: there are none today, but a cancelled document
is one a society withdrew, and a patch must not un-withdraw it.
"""

import frappe

TERMS_DOCTYPE = "VMMS Terms of Reference"


def execute():
	drafts = frappe.get_all(TERMS_DOCTYPE, filters={"docstatus": 0}, pluck="name")

	if not drafts:
		return

	table = frappe.qb.DocType(TERMS_DOCTYPE)

	frappe.qb.update(table).set(table.docstatus, 1).where(table.name.isin(drafts)).run()

	frappe.clear_cache(doctype=TERMS_DOCTYPE)
