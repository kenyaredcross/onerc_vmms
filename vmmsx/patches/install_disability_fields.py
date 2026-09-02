# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Whether somebody has a disability, asked once and held on the spine.

Two Custom Fields on core's `Red Profile`, both owned by vmmsx and neither an
edit to another app's source — the same shape as
`install_identity_document_rules.py`, and for the same reason: core's Red
Profile is shared with sibling products, and a field one product needs is added
beside the spine rather than into it.

**Why it is on Red Profile and not on the volunteer record.** It is a fact about
a person rather than about their volunteering: it does not change when somebody
transfers branch, it should not be asked again when the same person joins as a
member, and a copy on each satellite would be two answers to one question that
diverge the first time either is corrected. Every other identity fact this
product asks for — name, date of birth, citizenship, identity documents — is
already held there and read through `volunteer/services/identity.py`, and this
follows them.

**Three answers, not two.** "Prefer not to say" is a first-class option and is
not the same as leaving the field blank: one is a person declining to answer and
the other is a form nobody has filled in. A society counting who it serves needs
to be able to tell those apart, and an applicant who does not want to disclose
should not have to leave a required field empty to do it.

**Nothing is inferred from the answer.** The field is collected because a
society running an inclusive volunteering programme has to know what adjustments
to make, and it is shown to the branch reviewing the application. It is not a
routing input, it is not on the printed card, and it does not reach Frappe HR —
see `hr._OUTBOUND`, which did not widen with this.

**`vmms_needs` is optional whatever the answer.** A person may say they have a
disability and choose not to describe it; a form that then demanded a
description would be one that punishes disclosure. The branch asks in person if
it needs to.
"""

import frappe

PROFILE_DOCTYPE = "Red Profile"

DISABILITY_FIELD = "vmms_disability_status"
NEEDS_FIELD = "vmms_disability_needs"

# The vocabulary, spelled here once. The leading blank is Frappe's own "nothing
# chosen", and it is what a profile created before this field existed holds.
DISABILITY_OPTIONS = "\nNo\nYes\nPrefer not to say"

FIELDS = (
	{
		"fieldname": DISABILITY_FIELD,
		"label": "Disability",
		"fieldtype": "Select",
		"options": DISABILITY_OPTIONS,
		"insert_after": "preferred_language",
		"description": (
			"Whether this person has a disability. Asked of volunteer applicants so their branch"
			" knows what adjustments to make. Blank means nobody has been asked; 'Prefer not to"
			" say' means they were asked and declined, and the two are not the same. Owned by"
			" vmmsx."
		),
	},
	{
		"fieldname": NEEDS_FIELD,
		"label": "Support Needed",
		"fieldtype": "Small Text",
		"insert_after": DISABILITY_FIELD,
		"depends_on": f"eval:doc.{DISABILITY_FIELD} == 'Yes'",
		"description": (
			"Anything the society should know in order to make volunteering work — access,"
			" equipment, the kind of task. Always optional: a person may disclose a disability"
			" and choose not to describe it. Owned by vmmsx."
		),
	},
)


def execute():
	"""Create what is absent and touch nothing that is there.

	Guarded per field rather than per patch, so a run interrupted half way
	finishes on the next migrate rather than skipping the rest for ever.
	"""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	for field in FIELDS:
		if frappe.db.exists("Custom Field", {"dt": PROFILE_DOCTYPE, "fieldname": field["fieldname"]}):
			continue

		create_custom_field(PROFILE_DOCTYPE, dict(field), ignore_validate=True)
