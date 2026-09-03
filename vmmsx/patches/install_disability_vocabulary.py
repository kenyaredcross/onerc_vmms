# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""*Which* disability, on top of whether — core's own register, wired up.

`install_disability_fields.py` asked the question and kept the answer: a Select
holding No / Yes / Prefer not to say, and a free-text box beside it. That is
enough to know somebody should be asked about adjustments and not enough for
anything else. A society cannot count how many of its volunteers are Deaf, a
deployment cannot be matched against what it would have to arrange, and the one
description that exists is a sentence somebody typed, which no two people write
the same way.

**The register already existed and nothing used it.** `onerc_core` ships
`Disability Type` and `Disability` — a two-level vocabulary, the same shape the
older onerc_vmms product selected through its `Employee Disability` table.
Neither doctype had a single reader in this app. So this adds no new vocabulary
doctype: it points a table field at the one core already maintains, which is
also what keeps a person's disabilities on the spine with the rest of who they
are rather than in a product-shaped copy of it.

**The Select stays, and stays the gate.** It is not made redundant by a list,
because a list cannot hold the two answers that matter most:

    "Prefer not to say"   a person asked, who declined. An empty table would be
                          indistinguishable from a form nobody filled in.
    "No"                  an answer, and an empty table is the correct storage
                          for it.

So `vmms_disability_status` remains the required question and the thing every
reader branches on, and `vmms_disabilities` is what somebody who answered "Yes"
may optionally say more precisely. It depends on the Select for that reason.

**Optional, whatever the answer.** Same rule `vmms_disability_needs` follows and
for the same reason: a person may disclose a disability and decline to name it,
and a form that then demanded one would punish the disclosure it asked for.

**Read for `All` on both core doctypes.** A vocabulary is what a form may offer
and says nothing about any person — the footing `VMMS Skill` and
`VMMS Motivation` are already on, both of which grant `All` read in their own
source. Core ships these two as System Manager only, which would leave an
applicant unable to draw the control that asks them the question. Granted here
rather than edited into core, the same way the Custom Fields beside them are
added rather than merged into core's spine.

**The seed is a starting point, not policy.** The types are the functional
domains of the Washington Group short set, which is what a national society
reports against; the rows under them are ordinary language, not diagnoses. Every
one of them is an editable record and no source file in this app branches on any
of their names. A society renames, retires, or replaces the lot.
"""

import frappe

PROFILE_DOCTYPE = "Red Profile"
TYPE_DOCTYPE = "Disability Type"
DISABILITY_DOCTYPE = "Disability"

STATUS_FIELD = "vmms_disability_status"
DISABILITIES_FIELD = "vmms_disabilities"
SELECTOR_DOCTYPE = "VMMS Disability Selector"

FIELD = {
	"fieldname": DISABILITIES_FIELD,
	"label": "Disabilities",
	"fieldtype": "Table MultiSelect",
	"options": SELECTOR_DOCTYPE,
	"insert_after": STATUS_FIELD,
	"depends_on": f"eval:doc.{STATUS_FIELD} == 'Yes'",
	"description": (
		"Which disabilities this person has said they have, from the society's own register."
		" Always optional: somebody may answer 'Yes' above and choose not to say more. Empty"
		" means nothing further was said, never that the answer above is 'No'. Owned by vmmsx."
	),
}

# Washington Group short-set domains. A society reports against these, which is
# the only reason this particular six and not some other grouping.
TYPES = (
	"Vision",
	"Hearing",
	"Mobility",
	"Cognition",
	"Self-care",
	"Communication",
)

# type, disability. Ordinary words for what somebody would say about themselves,
# rather than clinical names for what a doctor would write about them.
DISABILITIES = (
	("Vision", "Blindness"),
	("Vision", "Low vision"),
	("Hearing", "Deafness"),
	("Hearing", "Hard of hearing"),
	("Mobility", "Wheelchair user"),
	("Mobility", "Difficulty walking or climbing steps"),
	("Mobility", "Limb difference"),
	("Cognition", "Learning disability"),
	("Cognition", "Difficulty remembering or concentrating"),
	("Self-care", "Difficulty with washing or dressing"),
	("Communication", "Speech impairment"),
	("Communication", "Difficulty being understood"),
)


def execute():
	"""Grant, seed, then add the field. Each step guarded on its own.

	Ordered so that the field arrives last: a control that can be drawn before
	there is anything to draw in it is an empty picker on somebody's
	registration, and a step interrupted half way leaves the register usable on
	the desk either way.
	"""
	if not (frappe.db.table_exists(TYPE_DOCTYPE) and frappe.db.table_exists(DISABILITY_DOCTYPE)):
		# A site without onerc_core's register has nothing to point at. Not an
		# error: the Select installed by `install_disability_fields` still asks
		# the question, and this patch reruns clean when core catches up.
		return

	grant_read()
	seed()
	install_field()


def grant_read() -> None:
	"""`All` may read both registers. Nothing may write them but System Manager."""
	from frappe.permissions import add_permission, update_permission_property

	for doctype in (TYPE_DOCTYPE, DISABILITY_DOCTYPE):
		if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": "All"}):
			continue

		add_permission(doctype, "All", 0)
		update_permission_property(doctype, "All", 0, "read", 1)


def seed() -> None:
	"""What is absent, and nothing that is there.

	Checked per row rather than per register, so a society that has already
	retired one of these keeps it retired while the rest still arrive.
	"""
	for label in TYPES:
		if frappe.db.exists(TYPE_DOCTYPE, label):
			continue

		frappe.get_doc({"doctype": TYPE_DOCTYPE, "disability_type": label}).insert(ignore_permissions=True)

	for disability_type, label in DISABILITIES:
		if frappe.db.exists(DISABILITY_DOCTYPE, label):
			continue

		frappe.get_doc(
			{
				"doctype": DISABILITY_DOCTYPE,
				"disability_type": disability_type,
				"disability_name": label,
			}
		).insert(ignore_permissions=True)


def install_field() -> None:
	"""The table beside the Select, if it is not already there."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": PROFILE_DOCTYPE, "fieldname": DISABILITIES_FIELD}):
		return

	if not frappe.get_meta(PROFILE_DOCTYPE).has_field(STATUS_FIELD):
		# `insert_after` names a field that is not there yet, which would put the
		# table somewhere arbitrary. `install_disability_fields` runs before this
		# in patches.txt; the guard is for a site that ran neither.
		return

	create_custom_field(PROFILE_DOCTYPE, dict(FIELD), ignore_validate=True)
