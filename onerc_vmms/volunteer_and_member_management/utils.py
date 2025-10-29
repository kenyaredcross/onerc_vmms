import json
from datetime import timedelta

import frappe
from frappe import _
from frappe.translate import get_all_translations
from frappe.utils.nestedset import get_descendants_of


def get_company():
    company = frappe.defaults.get_defaults().company
    if company:
        return company
    else:
        company = frappe.get_list("Company", limit=1)
        if company:
            return company[0].name
    return None


def get_current_fiscal_year():

    today = frappe.utils.today()
    fiscal_year = frappe.db.get_value(
        "Fiscal Year",
        {"year_start_date": ("<=", today), "year_end_date": (">=", today)},
    )
    return fiscal_year


def get_shift_types():
    """Get all shift types with their times"""
    return frappe.get_all("Shift Type", fields=["name", "start_time", "end_time"])


def get_dates_for_day_of_week(start_date, end_date, day_name):
    """Get all dates for a specific day of week within date range"""

    day_mapping = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    target_weekday = day_mapping.get(day_name.lower())
    if target_weekday is None:
        return []

    dates = []
    current_date = start_date

    while current_date.weekday() != target_weekday:
        current_date += timedelta(days=1)

    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=7)

    return dates


@frappe.whitelist()
def get_interviewers():
    settings = frappe.get_single("Non Profit Settings")
    allowed_roles = [r.role for r in settings.interview_roles]

    if not allowed_roles:
        return frappe.get_all("User", filters={"enabled": 1}, pluck="name")

    users_with_roles = frappe.get_all(
        "User",
        filters={
            "name": [
                "in",
                frappe.get_all(
                    "Has Role", filters={"role": ["in", allowed_roles]}, pluck="parent"
                ),
            ],
            "enabled": 1,
        },
        pluck="name",
    )

    return users_with_roles


@frappe.whitelist()
def get_expense_and_advance_approvers():

    allowed_roles = ["Expense Approver", "HR Manager"]

    users_with_roles = frappe.get_all(
        "User",
        filters={
            "name": [
                "in",
                frappe.get_all(
                    "Has Role",
                    filters={"role": ["in", allowed_roles]},
                    pluck="parent",
                ),
            ],
            "enabled": 1,
        },
        pluck="name",
    )

    return users_with_roles


def check_and_renew_membership(invoice_id: str) -> None:
    if not invoice_id or not frappe.db.exists("Sales Invoice", invoice_id):
        return

    invoice = frappe.get_doc("Sales Invoice", invoice_id)
    if not invoice.membership:
        return
    membership = frappe.get_doc("VM Membership", invoice.membership)
    membership.validate_membership_period()


@frappe.whitelist()
def get_company_descendants(company=None, company_list=None, include_parent=True):
    """
    Retrieves the name of all descendants (children, grandchildren, etc.)
    of one or more given Company names.

    :param company: The name (string) of a parent Company or a list of company names.
    :param company_list: Optional list of company names (alternative to `company`).
    :param include_parent: If True, each parent company's name is included in the list.
    :returns: A list of strings, where each string is the name of a descendant Company.
    """
    companies = company_list if company_list is not None else company
    if not companies:
        return []

    if not isinstance(companies, (list, tuple)):
        companies = [companies]

    descendants_set = set()
    for comp in companies:
        if not comp:
            continue
        desc = get_descendants_of("Company", comp) or []
        for d in desc:
            descendants_set.add(d)
        if include_parent:
            descendants_set.add(comp)

    return sorted(descendants_set)


@frappe.whitelist()
def get_companies():
    return frappe.get_all("Company", filters={"is_group": 0}, fields=["name"])


@frappe.whitelist()
def get_meta_info(type, route):
    if frappe.db.exists("Website Meta Tag", {"parent": f"{type}/{route}"}):
        meta_tags = frappe.get_all(
            "Website Meta Tag",
            {
                "parent": f"{type}/{route}",
            },
            ["name", "key", "value"],
        )

        return meta_tags

    return []


@frappe.whitelist()
def update_meta_info(type, route, meta_tags):
    parent_name = f"{type}/{route}"
    if not isinstance(meta_tags, list):
        frappe.throw(_("Meta tags should be a list."))

    for tag in meta_tags:
        existing_tag = frappe.db.exists(
            "Website Meta Tag",
            {
                "parent": parent_name,
                "parenttype": "Website Route Meta",
                "parentfield": "meta_tags",
                "key": tag["key"],
            },
        )
        if existing_tag:
            if not tag.get("value"):
                frappe.db.delete("Website Meta Tag", existing_tag)
                continue
            frappe.db.set_value("Website Meta Tag", existing_tag, "value", tag["value"])
        elif tag.get("value"):
            tag_properties = {
                "parent": parent_name,
                "parenttype": "Website Route Meta",
                "parentfield": "meta_tags",
                "key": tag["key"],
                "value": tag["value"],
            }

            parent_exists = frappe.db.exists("Website Route Meta", parent_name)
            if not parent_exists:
                route_meta = frappe.new_doc("Website Route Meta")
                route_meta.update(
                    {
                        "__newname": parent_name,
                    }
                )
                route_meta.append("meta_tags", tag_properties)
                route_meta.insert()
            else:
                new_tag = frappe.new_doc("Website Meta Tag")
                new_tag.update(tag_properties)
                new_tag.insert()


@frappe.whitelist(allow_guest=True)
def get_translations():
    if frappe.session.user != "Guest":
        language = frappe.db.get_value("User", frappe.session.user, "language")
    else:
        language = frappe.db.get_single_value("System Settings", "language")
    return get_all_translations(language)


@frappe.whitelist(allow_guest=True)
def get_branding():
    """Get branding details."""
    website_settings = frappe.get_single("Website Settings")
    image_fields = ["banner_image", "footer_logo", "favicon"]

    for field in image_fields:
        if website_settings.get(field):
            file_info = get_file_info(website_settings.get(field))
            website_settings.update({field: json.loads(json.dumps(file_info))})
        else:
            website_settings.update({field: None})

    return website_settings


@frappe.whitelist()
def get_file_info(file_url):
    """Get file info for the given file URL."""
    file_info = frappe.db.get_value(
        "File",
        {"file_url": file_url},
        ["file_name", "file_size", "file_url"],
        as_dict=1,
    )
    return file_info


def set_field_value(doc, fieldname, value, fieldtype=None):
    if not fieldtype:
        fieldmeta = frappe.get_meta(doc.doctype).get_field(fieldname)
        fieldtype = fieldmeta.fieldtype

    if fieldtype == "Table MultiSelect":
        child_table = frappe.get_meta(doc.doctype).get_field(fieldname).options
        child_meta = frappe.get_meta(child_table)
        link_field = next(
            (df.fieldname for df in child_meta.fields if df.fieldtype == "Link"),
            None,
        )
        if not link_field:
            frappe.throw(f"No Link field found in child table {child_table}")

        if not isinstance(value, list):
            frappe.throw(
                f"Expected list of values for Table MultiSelect field {fieldname}"
            )

        existing = {row.name: row for row in doc.get(fieldname)}

        doc.set(fieldname, [])

        for item in value:
            if isinstance(item, str):
                if item.strip():
                    doc.append(fieldname, {link_field: item})

            elif isinstance(item, dict):
                row_data = item.copy()

                if row_data.get("name") and row_data["name"] in existing:
                    row = existing[row_data["name"]]
                    for k, v in row_data.items():
                        if k != "name":
                            row.set(k, v)
                    doc.append(fieldname, row.as_dict())

                else:
                    if link_field not in row_data and row_data.get("value"):
                        row_data[link_field] = row_data.pop("value")
                    if link_field not in row_data:
                        frappe.throw(
                            f"Missing link field {link_field} for new child row in {fieldname}"
                        )
                    doc.append(fieldname, row_data)

            else:
                frappe.throw(
                    f"Unsupported item type {type(item)} for Table MultiSelect field {fieldname}"
                )

    elif fieldtype == "Table":
        if isinstance(value, list):
            doc.set(fieldname, [])
            child_meta = frappe.get_meta(
                frappe.get_meta(doc.doctype).get_field(fieldname).options
            )
            for row in value:
                if isinstance(row, dict):
                    processed_row = {}
                    for k, v in row.items():
                        if k.startswith("__"):
                            continue
                        df = child_meta.get_field(k)
                        if not df:
                            continue
                        if df.fieldtype in ("Attach", "Attach Image"):
                            if isinstance(v, dict) and v.get("file_url"):
                                processed_row[k] = v["file_url"]
                            elif isinstance(v, str) and v.strip():
                                processed_row[k] = v
                            else:
                                processed_row[k] = None
                        else:
                            processed_row[k] = v
                    has_values = any(
                        val not in (None, "", []) for val in processed_row.values()
                    )
                    if has_values:
                        doc.append(fieldname, processed_row)
        else:
            frappe.throw(f"Expected list of dicts for Table field {fieldname}")

    elif fieldtype in ("Attach", "Attach Image"):
        if isinstance(value, dict) and value.get("file_url"):
            doc.set(fieldname, value["file_url"])
        elif isinstance(value, str):
            doc.set(fieldname, value)
        elif value in (None, "", []):
            doc.set(fieldname, None)
        else:
            frappe.throw(
                f"Expected file url (string) or object with file_url for field {fieldname}"
            )

    else:
        doc.set(fieldname, value)
