# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Every file a person attached to their registration, as reviewers open them.

The files are private. Those uploaded to the profile (identification, supporting
documents, education, training and licences) are anchored to the Red Profile,
which most reviewers cannot read. So nothing here hands out a file's own URL:
each entry carries `url`, which goes through `api.registration.download_evidence`
and is checked against the record the reviewer is reading.

`download_evidence` asks `referenced` whether a URL belongs to that record, using
the same lists as this module, so a file appears on screen exactly when it can
be opened.
"""

from os.path import basename
from urllib.parse import unquote, urlencode

import frappe

PROFILE_DOCTYPE = "Red Profile"
EVIDENCE_ENDPOINT = "/api/method/vmmsx.api.registration.download_evidence"

# Profile tables carrying a file: key, Red Profile field, heading, label builder.
_PROFILE_TABLES = (
	(
		"education",
		"vmms_education",
		"Education",
		lambda row: " · ".join(filter(None, (row.get("qualification"), row.get("institution")))),
	),
	(
		"training",
		"vmms_training",
		"Training and courses",
		lambda row: " · ".join(filter(None, (row.get("course_name"), row.get("institution")))),
	),
	(
		"licences",
		"vmms_licences",
		"Licences",
		lambda row: " · ".join(
			filter(None, (row.get("license_name") or row.get("license_type"), row.get("registration_no")))
		),
	),
	(
		"driving_licences",
		"vmms_driving_licences",
		"Driving licence",
		lambda row: " · ".join(
			filter(None, (_class_label(row.get("licence_class")), row.get("licence_number")))
		),
	),
)


def file_name(url: str | None) -> str:
	"""The name a person gave the file, from its URL."""
	return unquote(basename((url or "").split("?")[0])) or "File"


def evidence_url(doctype: str, name: str, attachment: str) -> str:
	"""Where a reviewer reading `doctype`/`name` opens `attachment`."""
	return f"{EVIDENCE_ENDPOINT}?{urlencode({'doctype': doctype, 'name': name, 'attachment': attachment})}"


def of_profile(profile: str | None) -> list[dict]:
	"""Files on the person's own record, in the order the registration asks for them."""
	if not profile or not frappe.db.exists(PROFILE_DOCTYPE, profile):
		return []

	document = frappe.get_doc(PROFILE_DOCTYPE, profile)
	meta = document.meta
	found = []

	if meta.has_field("identifications"):
		labels = _id_type_labels(document.get("identifications") or [])
		for index, row in enumerate(document.get("identifications") or []):
			if row.get("attachment"):
				found.append(
					_entry(
						"identifications",
						index,
						"Identification",
						" ".join(filter(None, (labels.get(row.id_type, row.id_type), row.id_number))),
						row.attachment,
					)
				)

	if meta.has_field("vmms_supporting_documents"):
		from vmmsx.registration.services import parity

		# A required document has its own field on the form, so it has its own
		# heading here too.
		required = {row["key"] for row in parity.supporting_document_types() if row["is_required"]}
		for index, row in enumerate(document.get("vmms_supporting_documents") or []):
			if row.get("attachment"):
				label = " · ".join(filter(None, (row.get("type"), row.get("document_name"))))
				group = row.get("type") if row.get("type") in required else "Supporting documents"
				found.append(_entry("supporting_documents", index, group, label, row.attachment))

	for key, field, group, label in _PROFILE_TABLES:
		if not meta.has_field(field):
			continue
		for index, row in enumerate(document.get(field) or []):
			if row.get("attachment"):
				found.append(_entry(key, index, group, label(row), row.attachment))

	return found


def of_application(application) -> list[dict]:
	"""Files uploaded onto the application itself: consent evidence and answers."""
	found = []

	for index, row in enumerate(application.get("guardian_consents") or []):
		if row.get("consent_evidence"):
			found.append(
				_entry(
					"guardian_consents",
					index,
					"Parent or guardian consent",
					row.get("guardian_name") or "Consent document",
					row.consent_evidence,
				)
			)

	found.extend(_answer_files(application))
	return found


def of_membership(membership) -> list[dict]:
	"""Files uploaded onto a membership: the proof of payment and answers."""
	found = []

	if membership.get("proof_attachment"):
		found.append(_entry("proof", 0, "Payment", "Proof of payment", membership.proof_attachment))

	found.extend(_answer_files(membership))
	return found


def for_record(doctype: str, document, profile: str | None) -> list[dict]:
	"""Every file a reviewer of this record may open, each with its checked URL."""
	rows = of_profile(profile)

	if doctype == "VMMS Volunteer Application":
		rows += of_application(document)
	elif doctype == "VMMS Membership":
		rows += of_membership(document)

	for row in rows:
		row["url"] = evidence_url(doctype, document.name, row["attachment"])

	return rows


def referenced(doctype: str, document, profile: str | None) -> set[str]:
	"""The file URLs this record may hand out. `download_evidence` checks against it."""
	return {row["attachment"] for row in for_record(doctype, document, profile)}


def _answer_files(document) -> list[dict]:
	from vmmsx.registration.services import questions

	return [
		_entry("answers", index, "Questionnaire", answer.get("label") or "File", answer["file_url"])
		for index, answer in enumerate(questions.answers_of(document))
		if answer.get("is_file") and answer.get("file_url")
	]


def _entry(table: str, index: int, group: str, label: str, attachment: str) -> dict:
	return {
		"key": f"{table}:{index}",
		"table": table,
		"index": index,
		"group": group,
		"label": label or group,
		"attachment": attachment,
		"file_name": file_name(attachment),
	}


def _id_type_labels(rows) -> dict:
	keys = [row.id_type for row in rows if row.get("id_type")]
	if not keys:
		return {}
	return dict(
		frappe.get_all(
			"Identification Type",
			filters={"name": ("in", keys)},
			fields=["name", "identification_type_name"],
			as_list=True,
		)
	)


def _class_label(key: str | None) -> str | None:
	if not key:
		return None
	name = frappe.db.get_value("VMMS Driving Licence Class", key, "class_name")
	return f"Class {name or key}"


def answers_of_profile(profile: str | None) -> dict:
	"""What the applicant answered on the identity step that no other read carries.

	Shown on the application and membership review only. Disability needs are
	free text a person wrote about themselves; the branch deciding the
	application is the one that arranges adjustments, so it reads them here and
	they stay out of the general registers.
	"""
	empty = {
		"citizenship_status": None,
		"disability_status": None,
		"disability_needs": None,
		"disabilities": [],
		"profession": None,
	}
	if not profile or not frappe.db.exists(PROFILE_DOCTYPE, profile):
		return empty
	document = frappe.get_doc(PROFILE_DOCTYPE, profile)
	meta = document.meta

	def value(field):
		return document.get(field) if meta.has_field(field) else None

	keys = [row.disability for row in (value("vmms_disabilities") or []) if row.get("disability")]
	labels = (
		dict(
			frappe.get_all(
				"Disability",
				filters={"name": ("in", keys)},
				fields=["name", "disability_name"],
				as_list=True,
			)
		)
		if keys and frappe.get_meta("Disability").has_field("disability_name")
		else {}
	)
	profession = value("vmms_profession")
	return {
		"citizenship_status": value("citizenship_status"),
		"disability_status": value("vmms_disability_status"),
		"disability_needs": value("vmms_disability_needs"),
		"disabilities": [labels.get(key) or key for key in keys],
		"profession": value("vmms_other_profession") if profession == "Other" else profession,
	}
