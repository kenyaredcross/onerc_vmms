import frappe
from frappe import _
from frappe.model.document import Document

OTHER_DOCUMENT_TYPE = "Other"


def validate_supporting_document_names(doc: Document, method: str | None = None) -> None:
	"""Require a Document Name on Supporting Document rows typed "Other"."""
	rows = doc.get("supporting_documents") or []

	missing = [
		row.idx for row in rows if row.type == OTHER_DOCUMENT_TYPE and not (row.document_name or "").strip()
	]
	if not missing:
		return

	frappe.throw(
		_("Please provide a Document Name for Supporting Documents row {0}, because the type is {1}.").format(
			", ".join(str(idx) for idx in missing),
			frappe.bold(_(OTHER_DOCUMENT_TYPE)),
		),
		title=_("Missing Document Name"),
	)
