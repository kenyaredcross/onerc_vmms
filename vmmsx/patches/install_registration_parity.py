# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install structured registration facts without changing a society's policy.

Fields are added, never rewritten or erased. Kenya's required-document and age
choices belong in the society setup, not in this generic schema installation.
The accompanying integer answer marker distinguishes an unanswered household
question from a person explicitly answering zero, which Frappe Int cannot do alone.
"""

import frappe

PROFILE_DOCTYPE = "Red Profile"
SETTINGS_DOCTYPE = "National Society Settings"

PROFILE_FIELDS = (
	{
		"fieldname": "vmms_additional_skills",
		"label": "Additional Skills",
		"fieldtype": "Table",
		"options": "VMMS Declared Skill",
	},
	{
		"fieldname": "vmms_registration_details_section",
		"label": "Registration Details",
		"fieldtype": "Section Break",
		"insert_after": "vmms_references",
	},
	{
		"fieldname": "vmms_number_of_dependants",
		"label": "Number of Dependants",
		"fieldtype": "Int",
		"non_negative": 1,
	},
	{
		"fieldname": "vmms_dependants_answered",
		"label": "Dependants Question Answered",
		"fieldtype": "Check",
		"default": "0",
		"hidden": 1,
	},
	{
		"fieldname": "vmms_blood_group",
		"label": "Blood Group",
		"fieldtype": "Link",
		"options": "VMMS Blood Group",
	},
	{
		"fieldname": "vmms_has_insurance",
		"label": "Society Insurance",
		"fieldtype": "Select",
		"options": "\nYes\nNo",
		"description": "Whether this person reports having the society's insurance. Distinct from personal health cover.",
	},
	{
		"fieldname": "vmms_access_to_internet",
		"label": "Access to Internet",
		"fieldtype": "Select",
		"options": "\nYes\nNo\nSometimes",
	},
	{
		"fieldname": "vmms_mpesa_mobile_phone",
		"label": "Mobile Money Phone",
		"fieldtype": "Data",
		"options": "Phone",
	},
	{"fieldname": "vmms_place_of_work", "label": "Place of Work", "fieldtype": "Data"},
	{
		"fieldname": "vmms_linkedin",
		"label": "LinkedIn Profile",
		"fieldtype": "Data",
		"options": "URL",
		"length": 500,
	},
	{
		"fieldname": "vmms_github",
		"label": "GitHub Profile",
		"fieldtype": "Data",
		"options": "URL",
		"length": 500,
	},
	{"fieldname": "vmms_residence_county", "label": "County of Residence", "fieldtype": "Data"},
	{"fieldname": "vmms_residence_sub_county", "label": "Sub-county of Residence", "fieldtype": "Data"},
	{"fieldname": "vmms_residence_ward", "label": "Ward of Residence", "fieldtype": "Data"},
	{"fieldname": "vmms_residence_location", "label": "Administrative Location", "fieldtype": "Data"},
	{"fieldname": "vmms_residence_sub_location", "label": "Sub-location", "fieldtype": "Data"},
	{
		"fieldname": "vmms_allergies",
		"label": "Allergies",
		"fieldtype": "Table",
		"options": "VMMS Declared Allergy",
	},
	{
		"fieldname": "vmms_supporting_documents",
		"label": "Supporting Documents",
		"fieldtype": "Table",
		"options": "VMMS Supporting Document",
	},
	{
		"fieldname": "vmms_certifications",
		"label": "Declared Certifications",
		"fieldtype": "Table",
		"options": "VMMS Declared Certification",
	},
)

POLICY_FIELDS = (
	{
		"fieldname": "vmms_registration_policy_section",
		"label": "Registration Policy",
		"fieldtype": "Section Break",
	},
	{
		"fieldname": "vmms_registration_collect_legacy_details",
		"label": "Require Full Registration Details",
		"fieldtype": "Check",
		"default": "0",
		"description": "Require volunteer phone, gender, internet answer, profession and local residence details. The additional structured fields remain available when this is off.",
	},
	{
		"fieldname": "vmms_member_requires_identity",
		"label": "Require Member Identity Details",
		"fieldtype": "Check",
		"default": "0",
		"description": "Member submission needs contact details, date of birth, nationality/citizenship, home area and identification.",
	},
	{
		"fieldname": "vmms_volunteer_min_age",
		"label": "Minimum Volunteer Age",
		"fieldtype": "Int",
		"non_negative": 1,
		"description": "Inclusive minimum age at submission. Zero uses 7 in Kenya; other societies have no lower bound.",
	},
	{
		"fieldname": "vmms_volunteer_max_age",
		"label": "Maximum Volunteer Age",
		"fieldtype": "Int",
		"non_negative": 1,
		"description": "Inclusive maximum age at submission. Zero uses 150 in Kenya; other societies have no upper bound.",
	},
	{
		"fieldname": "vmms_member_min_age",
		"label": "Minimum Member Age",
		"fieldtype": "Int",
		"non_negative": 1,
		"description": "Inclusive minimum age at submission. Zero uses 7 in Kenya; other societies have no lower bound.",
	},
	{
		"fieldname": "vmms_member_max_age",
		"label": "Maximum Member Age",
		"fieldtype": "Int",
		"non_negative": 1,
		"description": "Inclusive maximum age at submission. Zero uses 150 in Kenya; other societies have no upper bound.",
	},
)

DOCUMENT_TYPE_FIELDS = (
	{
		"fieldname": "vmms_required_for_volunteers",
		"label": "Required for Volunteer Registration",
		"fieldtype": "Check",
		"default": "0",
		"description": "A volunteer cannot submit without an attachment of this type. Independent of recruitment defaults.",
	},
	{
		"fieldname": "vmms_requires_document_name",
		"label": "Require Document Name",
		"fieldtype": "Check",
		"default": "0",
		"description": "Ask the applicant to describe this document, for example when the type is Other.",
	},
)

ID_FIELDS = (
	{
		"fieldname": "vmms_validation_pattern",
		"label": "Registration Number Pattern",
		"fieldtype": "Data",
		"length": 200,
		"description": "Optional regular expression, matched against the whole identification number at volunteer submission. Empty means no format constraint.",
	},
)


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	for doctype, definitions in (
		(PROFILE_DOCTYPE, PROFILE_FIELDS),
		(SETTINGS_DOCTYPE, POLICY_FIELDS),
		("Supporting Document Type", DOCUMENT_TYPE_FIELDS),
		("Identification Type", ID_FIELDS),
	):
		if not frappe.db.exists("DocType", doctype):
			continue
		previous = None
		for definition in definitions:
			fieldname = definition["fieldname"]
			if not frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fieldname}):
				field = dict(definition)
				if previous and "insert_after" not in field:
					field["insert_after"] = previous
				if field.get("insert_after") and not frappe.get_meta(doctype).has_field(
					field["insert_after"]
				):
					field.pop("insert_after")
				create_custom_field(doctype, field, ignore_validate=True)
			previous = fieldname
		frappe.clear_cache(doctype=doctype)
