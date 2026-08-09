import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

CREATABLE_LINK_DOCTYPES = frozenset(
	{
		"Administrative Location",
		"Location",
		"Sub Location",
		"County",
		"Sub County",
		"Ward",
	}
)


@frappe.whitelist()
@rate_limit(limit=30, seconds=60 * 5)
def create_link_doc(data: dict):
	try:
		doctype = data.get("doctype")
		if not doctype:
			return {"status": "error", "message": "Missing 'doctype' in data"}

		if doctype not in CREATABLE_LINK_DOCTYPES:
			frappe.throw(f"Cannot create records of type {doctype}", frappe.PermissionError)

		doc = frappe.get_doc(data).insert(ignore_permissions=True)
		frappe.db.commit()
		return {"status": "success", "name": doc.name}
	except frappe.DuplicateEntryError:
		frappe.db.rollback()
		return {
			"status": "error",
			"message": "A record with the same name already exists",
		}

	except Exception:
		frappe.log_error(message=frappe.get_traceback(), title="Create Link Doc Error")
		frappe.db.rollback()
		return {"status": "error", "message": _("Could not create the record.")}


@frappe.whitelist()
def get_doc_info(doctype: str):
	"""
	Get doctype metadata: fields, labels, and other configurations
	"""
	try:
		if doctype not in CREATABLE_LINK_DOCTYPES:
			frappe.throw(
				_("Cannot fetch metadata for {0}").format(doctype),
				frappe.PermissionError,
			)

		if not frappe.db.exists("DocType", doctype):
			frappe.throw(_("Invalid Doctype: {0}").format(doctype))

		meta = frappe.get_meta(doctype)
		fields = [
			{
				"fieldname": f.fieldname,
				"fieldtype": f.fieldtype,
				"label": f.label,
				"options": f.options,
				"reqd": f.reqd,
				"hidden": f.hidden,
				"read_only": f.read_only,
			}
			for f in meta.fields
			if not f.hidden
		]

		return {
			"doctype": doctype,
			"fields": fields,
			"title_field": meta.title_field,
			"module": meta.module,
			"issingle": meta.issingle,
		}

	except Exception:
		frappe.log_error(frappe.get_traceback(), "get_doc_info API Error")
		frappe.throw(_("Error fetching doctype info."))


def _convert_table_multiselect(doc):
	if not doc:
		return {}

	meta = frappe.get_meta(doc.doctype)
	doc_dict = doc.as_dict()

	for df in meta.fields:
		if df.fieldtype == "Table MultiSelect":
			child_doctype = df.options
			child_meta = frappe.get_meta(child_doctype)

			link_field = next(
				(f.fieldname for f in child_meta.fields if f.fieldtype == "Link"),
				None,
			)
			if not link_field:
				continue

			linked_doctype = next(
				(f.options for f in child_meta.fields if f.fieldname == link_field),
				None,
			)
			title_field = frappe.get_meta(linked_doctype).title_field or "name"

			values = []
			for row in doc_dict.get(df.fieldname, []):
				link_value = row.get(link_field)
				if link_value:
					label = frappe.db.get_value(linked_doctype, link_value, title_field) or link_value
					values.append({"value": link_value, "label": label})

			doc_dict[df.fieldname] = values

	return doc_dict
