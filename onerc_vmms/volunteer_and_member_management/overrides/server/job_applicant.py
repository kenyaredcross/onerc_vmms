import frappe
from frappe.model.document import Document

FIELD_GROUPS = {
    0: [
        "ward",
        "date_of_birth",
        "id_number",
        "passport_number",
        "mpesa_mobile_phone",
        "number_of_dependants",
        "marital_status",
        "blood_group",
        "citizenship",
        "country_of_citizenship",
        "administrative_location",
        "sub_county",
        "county",
        "access_to_internet",
        "profession",
        "reason_to_join_krcs",
    ],
    1: [
        "languages",
        "education",
        "disabilities",
        "driving_licence",
        "certification",
        "licences",
        "additional_skills",
        "courses",
    ],
}

SKIP_CHILD_FIELDS = [
    "name",
    "parent",
    "parentfield",
    "parenttype",
    "doctype",
    "idx",
    "docstatus",
]


def on_update(doc: Document, method: str) -> None:
    try:
        if doc.status != "Open":
            return

        email = doc.email_id
        if not email:
            return

        user = frappe.get_all("User", filters={"email": email}, limit=1)
        if not user:
            return

        user_doc = frappe.get_doc("User", user[0].name)

        for group in FIELD_GROUPS.values():
            for field in group:
                if not hasattr(doc, field):
                    continue

                field_meta = doc.meta.get_field(field)
                if not field_meta:
                    continue

                if field_meta.fieldtype in ("Table", "Table MultiSelect"):
                    if hasattr(user_doc, field):
                        user_doc.set(field, [])

                    for row in getattr(doc, field) or []:
                        child_doc = user_doc.append(field, {})
                        for child_field in row.meta.get_valid_columns():
                            if child_field in SKIP_CHILD_FIELDS:
                                continue
                            child_doc.set(child_field, row.get(child_field))
                else:
                    user_doc.set(field, getattr(doc, field))

        user_doc.save(ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Job Applicant -> User Sync Error")
