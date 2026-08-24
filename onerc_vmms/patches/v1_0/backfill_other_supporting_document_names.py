import os

import frappe


def execute():
	"""Give existing "Other" supporting documents a Document Name.

	`document_name` is mandatory_depends_on type == "Other", but frappe only enforces
	that in the desk client, so portal and API writes left rows with a file and no name.
	Those records cannot be saved or submitted from the desk at all. Fall back to the
	attached file's name, which is what the field was meant to hold anyway.
	"""
	rows = frappe.get_all(
		"Supporting Document",
		filters={"type": "Other", "document_name": ("in", ("", None))},
		fields=["name", "attachment"],
	)

	for row in rows:
		label = _label_from_attachment(row.attachment)
		frappe.db.set_value("Supporting Document", row.name, "document_name", label, update_modified=False)

	if rows:
		frappe.db.commit()


def _label_from_attachment(attachment: str | None) -> str:
	if not attachment:
		return "Other Document"

	# no rstrip("/"): a path ending in "/" has no filename and should fall back
	filename = os.path.basename(attachment.split("?")[0])
	stem = (os.path.splitext(filename)[0] or filename).strip()

	return stem or "Other Document"
