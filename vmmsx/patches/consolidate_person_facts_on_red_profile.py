# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

import frappe


PERSON_FIELDS = (
	"country_of_citizenship",
	"residency_type",
	"home_geo_node",
	"country_of_residence",
	"residence_address",
)


def execute():
	"""Best-effort carry-forward for the small pre-production data set.

	Red Profile is now the only owner of citizenship, residence and identity
	documents. Old columns may still exist in MariaDB after their DocType fields
	are removed, so copy any useful values into an empty profile and leave an
	already-populated person alone.
	"""
	if not frappe.db.table_exists("Red Profile"):
		return

	_copy_from("VMMS Volunteer Application", include_identification=True)
	_copy_from("VMMS Volunteer", include_identification=False)
	_mark_existing_local_residences()


def _copy_from(doctype: str, *, include_identification: bool) -> None:
	if not frappe.db.table_exists(doctype):
		return

	columns = set(frappe.db.get_table_columns(doctype))
	required = {"name", "red_profile"}

	if not required.issubset(columns):
		return

	fields = [field for field in PERSON_FIELDS if field in columns]

	if include_identification:
		fields.extend(field for field in ("id_type", "id_number") if field in columns)

	if not fields:
		return

	quoted = ", ".join(f"`{field}`" for field in ("red_profile", *fields))
	rows = frappe.db.sql(
		f"select {quoted} from `tab{doctype}` where `red_profile` is not null order by `creation` desc",
		as_dict=True,
	)

	for row in rows:
		profile_name = row.red_profile

		if not frappe.db.exists("Red Profile", profile_name):
			continue

		profile = frappe.get_doc("Red Profile", profile_name)
		changed = False

		for fieldname in PERSON_FIELDS:
			value = row.get(fieldname)

			if value and not profile.get(fieldname):
				profile.set(fieldname, value)
				changed = True

		if include_identification and row.get("id_type") and row.get("id_number"):
			exists = any(
				item.id_type == row.id_type and item.id_number == row.id_number
				for item in profile.identifications
			)

			if not exists:
				profile.append(
					"identifications",
					{
						"id_type": row.id_type,
						"id_number": row.id_number,
						"is_primary": 0 if profile.identifications else 1,
					},
				)
				changed = True

		if changed:
			profile.save(ignore_permissions=True)


def _mark_existing_local_residences() -> None:
	profiles = frappe.get_all(
		"Red Profile",
		filters={"home_geo_node": ("is", "set"), "residency_type": ("is", "not set")},
		pluck="name",
	)

	for name in profiles:
		frappe.db.set_value("Red Profile", name, "residency_type", "Local", update_modified=False)
