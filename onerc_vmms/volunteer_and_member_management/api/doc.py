import json
import re

import frappe
from frappe import _, cint, cstr
from frappe.desk.search import (
    LinkSearchResults,
    build_for_autosuggest,
    get_std_fields_list,
    relevance_sorter,
    sanitize_searchfield,
)
from frappe.model.db_query import get_order_by
from frappe.utils.data import make_filter_tuple


@frappe.whitelist(allow_guest=True)
def get_list(
    doctype,
    fields=None,
    filters=None,
    order_by=None,
    limit_start=0,
    limit_page_length=20,
):
    """
    Override standard get_list to allow fetching lists with ignore_permissions=True
    """
    if not doctype:
        frappe.throw(_("Doctype is required"))

    if isinstance(fields, str):
        fields = json.loads(fields)

    if isinstance(filters, str):
        filters = json.loads(filters)

    if isinstance(order_by, str) and order_by == "null":
        order_by = None

    results = frappe.get_list(
        doctype=doctype,
        fields=fields,
        filters=filters,
        order_by=order_by,
        start=limit_start,
        page_length=limit_page_length,
        ignore_permissions=True,
    )

    return results


@frappe.whitelist(allow_guest=True)
def search_doctype(
    doctype: str,
    name: str | None = None,
    filters: str | None | dict | list = None,
    first: bool = False,
):
    """
    Search for a doctype by name or filters.
    If name is provided, it will return the document with that name.
    If filters are provided, it will return documents matching those filters.
    """
    if not doctype:
        frappe.throw(_("Doctype is required"))

    if not frappe.db.exists("DocType", doctype):
        frappe.throw(_("Invalid Doctype: {0}").format(doctype))

    if name:
        return frappe.get_doc(doctype, name)

    if isinstance(filters, str):
        filters = json.loads(filters)

    results = frappe.get_all(doctype, filters=filters, as_list=False)

    if first:
        data = frappe.get_doc(doctype, results[0].name) if results else None
        if data:
            return _convert_table_multiselect(data)

    return results


@frappe.whitelist(allow_guest=True)
def search_widget(
    doctype: str,
    txt: str,
    query: str | None = None,
    searchfield: str | None = None,
    start: int = 0,
    page_length: int = 10,
    filters: str | None | dict | list = None,
    filter_fields=None,
    as_dict: bool = False,
    reference_doctype: str | None = None,
    ignore_permissions: bool = True,
):

    start = cint(start)

    if isinstance(filters, str):
        filters = json.loads(filters)

    if searchfield:
        sanitize_searchfield(searchfield)

    if not searchfield:
        searchfield = "name"

    standard_queries = frappe.get_hooks().standard_queries or {}

    if not query and doctype in standard_queries:
        query = standard_queries[doctype][-1]

    if query:
        try:
            return frappe.call(
                query,
                doctype,
                txt,
                searchfield,
                start,
                page_length,
                filters,
                as_dict=as_dict,
                reference_doctype=reference_doctype,
                ignore_user_permissions=True,
            )
        except Exception:
            return []

    meta = frappe.get_meta(doctype)

    if isinstance(filters, dict):
        filters_items = filters.items()
        filters = []
        for key, value in filters_items:
            filters.append(make_filter_tuple(doctype, key, value))

    if filters is None:
        filters = []
    or_filters = []

    if txt:
        field_types = {
            "Data",
            "Text",
            "Small Text",
            "Long Text",
            "Link",
            "Select",
            "Read Only",
            "Text Editor",
        }
        search_fields = ["name"]
        if meta.title_field:
            search_fields.append(meta.title_field)

        if meta.search_fields:
            search_fields.extend(meta.get_search_fields())

        for f in search_fields:
            fmeta = meta.get_field(f.strip())
            if not meta.translated_doctype and (
                f == "name" or (fmeta and fmeta.fieldtype in field_types)
            ):
                or_filters.append([doctype, f.strip(), "like", f"%{txt}%"])

    if meta.get("fields", {"fieldname": "enabled", "fieldtype": "Check"}):
        filters.append([doctype, "enabled", "=", 1])
    if meta.get("fields", {"fieldname": "disabled", "fieldtype": "Check"}):
        filters.append([doctype, "disabled", "!=", 1])

    fields = get_std_fields_list(meta, searchfield or "name")
    if filter_fields:
        fields = list(set(fields + json.loads(filter_fields)))
    formatted_fields = [f"`tab{meta.name}`.`{f.strip()}`" for f in fields]

    if meta.show_title_field_in_link and meta.title_field:
        formatted_fields.insert(1, f"`tab{meta.name}`.{meta.title_field} as `label`")

    order_by_based_on_meta = get_order_by(doctype, meta)
    order_by = f"`tab{doctype}`.idx desc, {order_by_based_on_meta}"

    if not meta.translated_doctype:
        _txt = frappe.db.escape((txt or "").replace("%", "").replace("@", ""))
        _relevance = f"(1 / nullif(locate({_txt}, `tab{doctype}`.`name`), 0))"
        formatted_fields.append(f"""{_relevance} as `_relevance`""")
        if frappe.db.db_type == "mariadb":
            order_by = f"ifnull(_relevance, -9999) desc, {order_by}"
        elif frappe.db.db_type == "postgres":
            order_by = f"{len(formatted_fields)} desc nulls last, {order_by}"

    ignore_permissions = True

    values = frappe.get_list(
        doctype,
        filters=filters,
        fields=formatted_fields,
        or_filters=or_filters,
        limit_start=start,
        limit_page_length=None if meta.translated_doctype else page_length,
        order_by=order_by,
        ignore_permissions=ignore_permissions,
        reference_doctype=reference_doctype,
        as_list=not as_dict,
        strict=False,
    )

    if meta.translated_doctype:
        values = (
            result
            for result in values
            if any(
                re.search(f"{re.escape(txt)}.*", _(cstr(value)) or "", re.IGNORECASE)
                for value in (result.values() if as_dict else result)
            )
        )

    values = sorted(values, key=lambda x: relevance_sorter(x, txt, as_dict))

    if not meta.translated_doctype:
        if as_dict:
            for r in values:
                r.pop("_relevance", None)
        else:
            values = [r[:-1] for r in values]

    return values


@frappe.whitelist(allow_guest=True)
def custom_search_link(
    doctype: str,
    txt: str,
    query: str | None = None,
    filters: str | dict | list | None = None,
    page_length: int = 10,
    searchfield: str | None = None,
    reference_doctype: str | None = None,
    ignore_permissions: bool = False,
) -> list[LinkSearchResults]:
    results = search_widget(
        doctype,
        txt.strip(),
        query,
        searchfield=searchfield,
        page_length=page_length,
        filters=filters,
        reference_doctype=reference_doctype,
        ignore_permissions=ignore_permissions,
    )

    return build_for_autosuggest(results, doctype=doctype)


@frappe.whitelist(allow_guest=True)
def create_link_doc(data: dict):
    try:
        doctype = data.get("doctype")
        if not doctype:
            return {"status": "error", "message": "Missing 'doctype' in data"}

        if not frappe.db.exists("DocType", doctype):
            return {"status": "error", "message": f"Invalid doctype: {doctype}"}

        doc = frappe.get_doc(data).insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "name": doc.name}
    except frappe.DuplicateEntryError:
        frappe.db.rollback()
        return {
            "status": "error",
            "message": "A record with the same name already exists",
        }

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Create Link Doc Error")
        frappe.db.rollback()
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def get_doc_info(doctype: str):
    """
    Get doctype metadata: fields, labels, and other configurations
    """
    try:
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

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_doc_info API Error")
        frappe.throw(_("Error fetching doctype info: {0}").format(str(e)))


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
                    label = (
                        frappe.db.get_value(linked_doctype, link_value, title_field)
                        or link_value
                    )
                    values.append({"value": link_value, "label": label})

            doc_dict[df.fieldname] = values

    return doc_dict
