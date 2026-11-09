# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Legacy registration facts kept on the shared person, with explicit policy gates.

The wire dictionary is closed. Omitted keys leave existing facts alone; explicit
blank scalars and empty tables clear them. Supporting files use the same private
upload handling as identity evidence. Kenya's agreed age range also applies
when its age settings have not been configured.
"""

import json
import re
from datetime import date
from urllib.parse import urlsplit

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from vmmsx.registration.services import evidence

PROFILE_DOCTYPE = "Red Profile"
DOCUMENT_TYPE_DOCTYPE = "Supporting Document Type"
REQUIRED_DOCUMENT_FIELD = "vmms_required_for_volunteers"
DOCUMENT_NAME_FIELD = "vmms_requires_document_name"
ID_PATTERN_FIELD = "vmms_validation_pattern"
SCALAR_FIELDS = {
	"middle_name": "middle_name",
	"marital_status": "marital_status",
	"number_of_dependants": "vmms_number_of_dependants",
	"blood_group": "vmms_blood_group",
	"has_insurance": "vmms_has_insurance",
	"access_to_internet": "vmms_access_to_internet",
	"mpesa_mobile_phone": "vmms_mpesa_mobile_phone",
	"place_of_work": "vmms_place_of_work",
	"linkedin": "vmms_linkedin",
	"github": "vmms_github",
	"county": "vmms_residence_county",
	"sub_county": "vmms_residence_sub_county",
	"ward": "vmms_residence_ward",
	"administrative_location": "vmms_residence_location",
	"sub_location": "vmms_residence_sub_location",
}
TABLES = {
	"additional_skills": ("vmms_additional_skills", ("additional_skill",), ()),
	"allergies": ("vmms_allergies", ("allergy",), ()),
	"supporting_documents": (
		"vmms_supporting_documents",
		("type", "document_name", "attachment"),
		("attachment",),
	),
}
ENUMS = {
	"marital_status": ("Single", "Married", "Divorced", "Widowed", "Other"),
	"has_insurance": ("Yes", "No"),
	"access_to_internet": ("Yes", "No", "Sometimes"),
}
POLICY_FIELDS = {
	"member_min_age": "vmms_member_min_age",
	"member_max_age": "vmms_member_max_age",
	"volunteer_min_age": "vmms_volunteer_min_age",
	"volunteer_max_age": "vmms_volunteer_max_age",
	"member_requires_identity": "vmms_member_requires_identity",
	"collect_legacy_details": "vmms_registration_collect_legacy_details",
}


def normalise_personal_details(supplied) -> dict:
	"""Return only applicant-owned fields; raise ValueError for malformed input."""
	if supplied is None:
		return {}
	if isinstance(supplied, str):
		supplied = json.loads(supplied)
	if not isinstance(supplied, dict):
		raise ValueError("Personal details must be an object.")
	result = {}
	for key in SCALAR_FIELDS:
		if key not in supplied:
			continue
		value = supplied[key]
		if value is None or value == "":
			result[key] = None
			continue
		if key == "number_of_dependants":
			if isinstance(value, bool) or not re.fullmatch(r"\d+", str(value)):
				raise ValueError("Number of dependants must be a non-negative whole number.")
			result[key] = int(value)
			continue
		if not isinstance(value, str):
			raise ValueError(f"{key.replace('_', ' ').capitalize()} must be text.")
		value = value.strip()
		if key in ENUMS and value and value not in ENUMS[key]:
			raise ValueError(f"Choose a valid {key.replace('_', ' ')}.")
		if key in ("linkedin", "github") and value:
			parts = urlsplit(value)
			if (
				parts.scheme not in ("http", "https")
				or not parts.hostname
				or parts.username
				or parts.password
			):
				raise ValueError("Profile links must be an http or https address.")
		result[key] = value or None
	for key, (_field, allowed, files) in TABLES.items():
		if key not in supplied or supplied[key] is None:
			continue
		rows = supplied[key]
		if not isinstance(rows, list):
			raise ValueError(f"{key.replace('_', ' ').capitalize()} must be a list.")
		clean = []
		for row in rows:
			if not isinstance(row, dict):
				raise ValueError("Each registration detail row must be an object.")
			value = {}
			for field in allowed:
				if field not in row:
					continue
				if row[field] is not None and not isinstance(row[field], str):
					raise ValueError(f"{field.replace('_', ' ').capitalize()} must be text.")
				value[field] = (row[field] or "").strip()
				if field in files and value[field] and not evidence.is_upload(value[field]):
					raise ValueError("Supporting documents must be uploaded to this site.")
			if any(value.values()):
				clean.append(value)
		result[key] = clean
	return result


def write_profile(document, personal_details, *, actor=None) -> None:
	"""Mutate one already-authorised Red Profile. The caller saves the document."""
	try:
		values = normalise_personal_details(personal_details)
	except (ValueError, TypeError) as exc:
		frappe.throw(_(str(exc)), frappe.ValidationError)
	for key, value in values.items():
		field = SCALAR_FIELDS.get(key) or TABLES[key][0]
		if not document.meta.has_field(field):
			frappe.throw(_("Registration fields have not been installed. Run the site migration."))
		if key in SCALAR_FIELDS:
			document.set(field, value)
			if key == "number_of_dependants" and document.meta.has_field("vmms_dependants_answered"):
				document.set("vmms_dependants_answered", int(value is not None))
			continue
		rows = []
		for supplied in value:
			row = dict(supplied)
			if key == "supporting_documents" and row.get("type"):
				if not frappe.db.exists(DOCUMENT_TYPE_DOCTYPE, row["type"]):
					frappe.throw(_("Choose a configured supporting document type."), frappe.ValidationError)
				meta = frappe.get_meta(DOCUMENT_TYPE_DOCTYPE)
				if row.get("attachment") and meta.has_field(DOCUMENT_NAME_FIELD):
					if frappe.db.get_value(
						DOCUMENT_TYPE_DOCTYPE, row["type"], DOCUMENT_NAME_FIELD
					) and not row.get("document_name"):
						frappe.throw(_("Give this supporting document a name."), frappe.MandatoryError)
			for file_field in TABLES[key][2]:
				if row.get(file_field):
					row[file_field] = _secure_file(document, row[file_field], actor or frappe.session.user)
			rows.append(row)
		document.set(field, rows)


def _secure_file(document, url: str, actor: str) -> str:
	file = frappe.db.get_value(
		"File", {"file_url": url}, ["name", "owner", "attached_to_doctype", "attached_to_name"], as_dict=True
	)
	if not file:
		frappe.throw(_("Upload the supporting document before saving it."), frappe.ValidationError)
	anchored_here = file.attached_to_doctype == document.doctype and file.attached_to_name == document.name
	if not anchored_here and actor != "Administrator" and file.owner != actor:
		frappe.throw(_("You may only attach documents you uploaded yourself."), frappe.PermissionError)
	if file.attached_to_name and not anchored_here:
		frappe.throw(
			_("This file is attached to another record. Upload a separate copy."), frappe.ValidationError
		)
	return evidence.secure(document, url)


def profile_dto(profile) -> dict:
	"""Read the restored details without exposing framework or reviewer columns."""
	document = frappe.get_doc(PROFILE_DOCTYPE, profile) if isinstance(profile, str) else profile
	result = {
		key: document.get(field) if document.meta.has_field(field) else None
		for key, field in SCALAR_FIELDS.items()
	}
	if (
		document.meta.has_field("vmms_dependants_answered")
		and not document.get("vmms_dependants_answered")
		and not result["number_of_dependants"]
	):
		result["number_of_dependants"] = None
	for key, (field, allowed, _files) in TABLES.items():
		result[key] = (
			[{column: row.get(column) for column in allowed} for row in document.get(field) or []]
			if document.meta.has_field(field)
			else []
		)
	return result


def supporting_document_types() -> list[dict]:
	if not frappe.db.exists("DocType", DOCUMENT_TYPE_DOCTYPE):
		return []
	meta = frappe.get_meta(DOCUMENT_TYPE_DOCTYPE)
	fields = ["name"] + [
		field for field in (REQUIRED_DOCUMENT_FIELD, DOCUMENT_NAME_FIELD) if meta.has_field(field)
	]
	return [
		{
			"key": row.name,
			"label": row.name,
			"is_required": bool(row.get(REQUIRED_DOCUMENT_FIELD)),
			"requires_name": bool(row.get(DOCUMENT_NAME_FIELD)),
		}
		for row in frappe.get_all(DOCUMENT_TYPE_DOCTYPE, fields=fields, order_by="name asc")
	]


def options() -> dict:
	from onerc_core.society.services import config

	settings = config.settings()
	policy = {key: cint(settings.get(field)) for key, field in POLICY_FIELDS.items()}
	# Kenya's agreed limits must also apply to existing sites whose new fields
	# have not been configured yet. Other societies retain their own policy.
	if (settings.get("country") or "").strip().casefold() == "kenya":
		for path in ("member", "volunteer"):
			policy[f"{path}_min_age"] = policy[f"{path}_min_age"] or 7
			policy[f"{path}_max_age"] = policy[f"{path}_max_age"] or 150
	return {
		**policy,
		"supporting_document_types": supporting_document_types(),
		"identification_patterns": identification_patterns(),
	}


def identification_patterns() -> dict[str, str]:
	meta = frappe.get_meta("Identification Type")
	if not meta.has_field(ID_PATTERN_FIELD):
		return {}
	return {
		row.name: row.get(ID_PATTERN_FIELD)
		for row in frappe.get_all(
			"Identification Type",
			filters={"is_active": 1},
			fields=["name", ID_PATTERN_FIELD],
		)
		if row.get(ID_PATTERN_FIELD)
	}


def missing_required_documents(rows, types: list[dict]) -> list[str]:
	held = {row.get("type") for row in rows or [] if row.get("type") and row.get("attachment")}
	return [row["key"] for row in types if row.get("is_required") and row["key"] not in held]


def _age_exception(profile):
	"""A missing date of birth is a missing required fact; a wrong age is not."""
	return frappe.ValidationError if profile.get("date_of_birth") else frappe.MandatoryError


def age_error(birth_date, minimum=0, maximum=0, as_of=None) -> str | None:
	if not minimum and not maximum:
		return None
	if not birth_date:
		return "Enter your date of birth before submitting."
	born = date.fromisoformat(str(birth_date)) if not isinstance(birth_date, date) else birth_date
	reference = date.fromisoformat(str(as_of)) if as_of else date.today()
	age = reference.year - born.year - ((reference.month, reference.day) < (born.month, born.day))
	if minimum and age < minimum:
		return f"Applicants must be at least {minimum} years old."
	if maximum and age > maximum:
		return f"Applicants must be no older than {maximum} years."
	return None


def identification_error(number: str, pattern: str | None) -> str | None:
	if not pattern:
		return None
	try:
		if re.fullmatch(pattern, number or ""):
			return None
	except re.error:
		return "The configured identification format is invalid. Contact the society."
	return "The identification number does not match the format for this document type."


def assert_ready(application) -> None:
	"""The society's optional legacy policy, evaluated at submission, never draft save."""
	profile = application.get("red_profile")
	if not profile:
		return
	document = frappe.get_doc(PROFILE_DOCTYPE, profile)
	policy = options()
	message = age_error(
		document.get("date_of_birth"), policy["volunteer_min_age"], policy["volunteer_max_age"], today()
	)
	if message:
		frappe.throw(_(message), _age_exception(document))
	if policy["collect_legacy_details"]:
		fields = ["phone", "gender", "vmms_access_to_internet", "vmms_profession"]
		if document.get("residency_type") == "Local":
			fields.extend(("vmms_residence_county", "vmms_residence_sub_county", "vmms_residence_ward"))
		_required_profile(document, fields)
	missing = missing_required_documents(
		document.get("vmms_supporting_documents") or [], policy["supporting_document_types"]
	)
	if missing:
		frappe.throw(
			_("Upload the required supporting documents: {0}.").format(", ".join(missing)),
			frappe.MandatoryError,
		)
	meta = frappe.get_meta("Identification Type")
	if meta.has_field(ID_PATTERN_FIELD):
		for row in document.get("identifications") or []:
			pattern = frappe.db.get_value("Identification Type", row.id_type, ID_PATTERN_FIELD)
			message = identification_error(row.id_number, pattern)
			if message:
				frappe.throw(_(message), frappe.ValidationError)


def assert_member_ready(membership) -> None:
	policy = options()
	if not (policy["member_requires_identity"] or policy["member_min_age"] or policy["member_max_age"]):
		return
	profile = frappe.db.get_value("VMMS Member", membership.get("member"), "red_profile")
	if not profile:
		frappe.throw(_("Complete your member identity before submitting."), frappe.MandatoryError)
	_assert_member_profile(frappe.get_doc(PROFILE_DOCTYPE, profile), policy)


def member_profile_ready(profile: str) -> bool:
	"""Would this profile pass `assert_member_ready` as it stands? Changes nothing.

	The one-page membership (`registration.my_quick_membership`) is offered only
	to somebody for whom this is true, so it never ends in a refusal about a
	detail it did not ask for. A date of birth is required here whatever the
	policy, because the page uses it to rule out types by age.
	"""
	document = frappe.get_doc(PROFILE_DOCTYPE, profile)
	if not document.get("date_of_birth"):
		return False
	try:
		_assert_member_profile(document, options())
	except frappe.ValidationError:
		return False
	return True


def _assert_member_profile(document, policy) -> None:
	message = age_error(
		document.get("date_of_birth"), policy["member_min_age"], policy["member_max_age"], today()
	)
	if message:
		frappe.throw(_(message), _age_exception(document))
	if not policy["member_requires_identity"]:
		return
	_required_profile(
		document,
		(
			"first_name",
			"last_name",
			"phone",
			"gender",
			"date_of_birth",
			"country_of_citizenship",
			"citizenship_status",
		),
	)
	if document.get("residency_type") == "Local":
		_required_profile(document, ("home_geo_node", "vmms_residence_county", "vmms_residence_sub_county"))
	elif document.get("residency_type") == "Abroad":
		_required_profile(document, ("country_of_residence", "residence_address"))
	else:
		frappe.throw(_("Choose whether you live locally or abroad."), frappe.MandatoryError)
	if not any(row.get("id_type") and row.get("id_number") for row in document.get("identifications") or []):
		frappe.throw(_("Add an identification type and number before submitting."), frappe.MandatoryError)


def _required_profile(document, fields) -> None:
	missing = [document.meta.get_label(field) for field in fields if not document.get(field)]
	if missing:
		frappe.throw(
			_("Complete the following profile details before submitting: {0}.").format(", ".join(missing)),
			frappe.MandatoryError,
		)
