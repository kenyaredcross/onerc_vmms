# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Which identity documents a volunteer must produce, and who counts as a minor.

Four Custom Fields, all owned by vmmsx, none of them an edit to another app's
source. Three sit on core's `Identification Type` and one on core's
`National Society Settings`.

**Why the document rules live on `Identification Type` rather than in a list
here.** A society's answer to "what do we need to see before we let somebody
volunteer" is a property of each document it recognises, not a separate register
that would have to be kept in step with the first one. A branch that stops
accepting a school card edits the row it already has; nothing in this app names
a document type, and `volunteer/services/application.py` reads the flags rather
than a constant.

Core's own doctype carries name, key, `is_active` and description and knows
nothing about volunteering — correctly, because a Vendor Application in a
sibling app uses the same list for its own purposes and must not inherit
volunteering's requirements. Hence the `vmms_` prefix on all three: they say
whose rule this is, and a second product may add its own beside them.

**Everything ships empty, and empty means "not required".** A society that has
never opened this screen is not thereby refusing every application; it is a
society that has not narrowed anything, which is the same direction
`volunteer/services/society.py` documents for the anchor level and the employee
provisioning flag. The one place empty means *closed* in this app is a scope
role, and none of these is one.

`vmms_minor_age` is the fourth, and it governs whether the guardian rules apply
at all. Left empty — the shipped state — `application.is_minor()` answers False
for everybody and the guardian gate never fires. A society that puts 18 in it
starts getting the guardian section and the approval gate that goes with it,
with no deploy. Nothing in this app assumes a number: eighteen is not a fact
about the world, it is a fact about a jurisdiction.
"""

import frappe

SETTINGS_DOCTYPE = "National Society Settings"
IDENTIFICATION_TYPE_DOCTYPE = "Identification Type"

REQUIRED_FIELD = "vmms_is_required_for_volunteers"
ATTACHMENT_FIELD = "vmms_requires_attachment"
MINIMUM_AGE_FIELD = "vmms_minimum_age"
MINOR_AGE_FIELD = "vmms_minor_age"

DOCUMENT_RULES = (
	{
		"fieldname": REQUIRED_FIELD,
		"label": "Required for Volunteers",
		"fieldtype": "Check",
		"insert_after": "description",
		"description": (
			"Ticked, a volunteer application cannot be submitted until the applicant has"
			" produced this document. Left unticked — the shipped state — the document is"
			" accepted but never insisted on. Owned by vmmsx."
		),
	},
	{
		"fieldname": ATTACHMENT_FIELD,
		"label": "Requires an Attachment",
		"fieldtype": "Check",
		"insert_after": REQUIRED_FIELD,
		"description": (
			"Ticked, a number on its own is not enough: the applicant must also upload a copy."
			" The upload is private, readable only by the applicant and by whoever may read the"
			" application. Owned by vmmsx."
		),
	},
	{
		"fieldname": MINIMUM_AGE_FIELD,
		"label": "Minimum Age",
		"fieldtype": "Int",
		"insert_after": ATTACHMENT_FIELD,
		"description": (
			"The age below which this document cannot be expected, because it does not exist for"
			" a child. A required document is not insisted on for an applicant younger than this."
			" Leave at zero where the document exists for everybody. Owned by vmmsx."
		),
	},
)

SOCIETY_RULES = (
	{
		"fieldname": MINOR_AGE_FIELD,
		"label": "Age of Majority",
		"fieldtype": "Int",
		"insert_after": "vmms_branch_location_scope_role",
		"description": (
			"The age at which this society treats a volunteer as an adult. An applicant younger"
			" than this is a minor: their application shows the guardian consent section, and it"
			" cannot be approved until a guardian's consent has been recorded and verified. Left"
			" empty, nobody is treated as a minor and the guardian rules never apply. Owned by"
			" vmmsx."
		),
	},
)


def execute():
	_install(IDENTIFICATION_TYPE_DOCTYPE, DOCUMENT_RULES)
	_install(SETTINGS_DOCTYPE, SOCIETY_RULES)


def _install(doctype: str, fields: tuple) -> None:
	"""Create what is absent and touch nothing that is there.

	Guarded per field rather than per patch, so a run interrupted half way
	finishes on the next migrate rather than skipping the rest for ever.
	"""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	for field in fields:
		if frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]}):
			continue

		create_custom_field(doctype, dict(field), ignore_validate=True)
