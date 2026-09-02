# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What vmmsx adds to ERPNext's `Project`, and everything it deliberately does not.

A society's programme of work is a `Project`. Not `VMMS Project` — that doctype
was this app's own thin container and it has been retired, because ERPNext
already ships identity, type, dates, priority, progress, Company, cost centre,
timesheet and invoice roll-ups, and a project dashboard that links the lot.
Rebuilding a quarter of that under a `VMMS ` prefix bought a name and lost every
connection.

**Every field here is a Custom Field owned by vmmsx.** ERPNext's source is not
edited; a product pushing its columns into the shared foundation's source is how
the foundation stops being shared. The `vmms_` prefix says whose rule each is,
and leaves room for a second product on the same site to add its own beside them.

Three additions, and each exists because ERPNext has no field for it:

1. **`vmms_geo_node` — the owning Geo Node.** ACC-02 for a project: where in the
   organisation this programme belongs. It is *not* Company and does not replace
   it — Company is the legal entity the money runs through, and a national
   society is one Company with a hundred branches. Both are mandatory and they
   answer different questions. It is what core's geo scoping filters the
   register on, so a project without one would be a project nobody but an
   administrator could see.

2. **Funding.** ERPNext costs a project (estimated, actual, billed) and has
   nowhere to record *whose money it is*. A donor, the agreement reference the
   society files it under, and whether the money is promised or in the bank.
   Three fields, deliberately flat: this is planning information a coordinator
   reads, not an accounting record, and ERPNext already owns the accounting.

3. **Planning — risks, assumptions and notes.** Structured because a society
   reviewing a programme wants to sort by impact and tick off assumptions, which
   a paragraph of prose cannot do. `notes` (ERPNext's own) stays what it is: the
   free-text story of the project. `vmms_planning_notes` is the planning
   caveat that belongs beside the two tables.

**Nothing here duplicates a native field.** No VMMS status, no VMMS priority, no
VMMS progress, no VMMS company, no second set of dates. Where ERPNext has the
concept, this app uses ERPNext's field and reads it by ERPNext's name.

**Installed on every migrate, not once by a patch.** The usual convention in this
app is a patch, and this one breaks it on purpose: `vmms_geo_node` is the field
core's scope registration in `hooks.py` names, and a registration pointing at a
field that is not there makes `registry.geo_node_field` throw on every Project
list view on the site. A patch runs once per site by name and cannot heal that;
an idempotent installer on `after_migrate` can, and does. The migration patch
calls it directly for the same reason — it needs the column before it can write
to it.
"""

import frappe

PROJECT_DOCTYPE = "Project"

# The field core's `onerc_scopeable_doctypes` registration names. Written here
# once and imported by everything that needs it, so the registration, the
# services and the tests cannot spell it three ways.
GEO_NODE_FIELD = "vmms_geo_node"

DONOR_FIELD = "vmms_donor"
FUNDING_REFERENCE_FIELD = "vmms_funding_reference"
FUNDING_STATUS_FIELD = "vmms_funding_status"
RISKS_FIELD = "vmms_risks"
ASSUMPTIONS_FIELD = "vmms_assumptions"
PLANNING_NOTES_FIELD = "vmms_planning_notes"

# What a society may say about where a project's money stands. A closed set
# because a screen groups on it; the blank first option is the shipped answer
# and means "not recorded", never "unfunded" — those are different facts and a
# register that conflated them would report a society as unfunded on the day it
# started planning.
FUNDING_STATUSES = ("Planned", "Committed", "Received", "Unfunded")

FIELDS = (
	{
		"fieldname": GEO_NODE_FIELD,
		"label": "Owning Geo Node",
		"fieldtype": "Link",
		"options": "Geo Node",
		"insert_after": "department",
		"reqd": 1,
		"in_standard_filter": 1,
		"description": (
			"The branch, region or office that owns this programme of work. Decides who can"
			" see it. This is not Company: Company is the legal entity, and one society is one"
			" Company with many branches. Owned by vmmsx."
		),
	},
	{
		"fieldname": "vmms_funding_section",
		"label": "Funding",
		"fieldtype": "Section Break",
		"insert_after": "notes",
		"collapsible": 1,
	},
	{
		"fieldname": DONOR_FIELD,
		"label": "Donor or Funding Source",
		"fieldtype": "Data",
		"insert_after": "vmms_funding_section",
		"description": (
			"Whose money this programme runs on, in the society's own words. Planning"
			" information, not an accounting record. Owned by vmmsx."
		),
	},
	{
		"fieldname": FUNDING_REFERENCE_FIELD,
		"label": "Funding Reference",
		"fieldtype": "Data",
		"insert_after": DONOR_FIELD,
		"description": (
			"The grant, appeal or agreement number this society files the programme under."
			" Owned by vmmsx."
		),
	},
	{
		"fieldname": "vmms_funding_column",
		"fieldtype": "Column Break",
		"insert_after": FUNDING_REFERENCE_FIELD,
	},
	{
		"fieldname": FUNDING_STATUS_FIELD,
		"label": "Funding Status",
		"fieldtype": "Select",
		"options": "\n" + "\n".join(FUNDING_STATUSES),
		"insert_after": "vmms_funding_column",
		"description": (
			"Where the money has got to. Left blank — the shipped state — means nobody has"
			" recorded it, which is not the same as unfunded. Owned by vmmsx."
		),
	},
	{
		"fieldname": "vmms_planning_section",
		"label": "Planning",
		"fieldtype": "Section Break",
		"insert_after": FUNDING_STATUS_FIELD,
		"collapsible": 1,
	},
	{
		"fieldname": RISKS_FIELD,
		"label": "Risks",
		"fieldtype": "Table",
		"options": "VMMS Project Risk",
		"insert_after": "vmms_planning_section",
		"description": (
			"What could stop this programme, how likely it is, what it would cost, and what"
			" the society intends to do about it. Owned by vmmsx."
		),
	},
	{
		"fieldname": ASSUMPTIONS_FIELD,
		"label": "Assumptions",
		"fieldtype": "Table",
		"options": "VMMS Project Assumption",
		"insert_after": RISKS_FIELD,
		"description": (
			"What this plan takes for granted. Written down so that a plan which stops"
			" working can be read back against the thing that changed. Owned by vmmsx."
		),
	},
	{
		"fieldname": PLANNING_NOTES_FIELD,
		"label": "Planning Notes",
		"fieldtype": "Small Text",
		"insert_after": ASSUMPTIONS_FIELD,
		"description": (
			"Anything about the plan that is not a risk, an assumption or a field. ERPNext's"
			" own Notes stays the story of the project itself. Owned by vmmsx."
		),
	},
)


def install() -> None:
	"""Create what is absent and touch nothing that is there.

	Guarded per field rather than per run, so a migrate interrupted half way
	finishes on the next one rather than skipping the rest for ever — and so an
	administrator who has edited a description or a label keeps their edit.
	"""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	for field in FIELDS:
		if frappe.db.exists("Custom Field", {"dt": PROJECT_DOCTYPE, "fieldname": field["fieldname"]}):
			continue

		create_custom_field(PROJECT_DOCTYPE, dict(field), ignore_validate=True)
