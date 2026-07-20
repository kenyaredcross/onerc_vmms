import json

import frappe
from frappe import _
from frappe.utils.csvutils import get_csv_content_from_google_sheets, read_csv_content
from frappe.utils.xlsxutils import read_xls_file_from_attached_file, read_xlsx_file_from_attached_file

from onerc_vmms.volunteer_and_member_management.services.user import (
	ensure_user_self_permission,
)

INVALID_VALUES = ("", None)


class PersonnelDataImporter:
	def __init__(self, employee_doctype, user_doctype, data_import=None):
		self.employee_doctype = employee_doctype
		self.user_doctype = user_doctype
		self.data_import = data_import
		self.header = []
		self.rows = []
		self.columns = []
		self.import_mode = self.data_import.import_mode or "Both"
		self.employee_options = frappe.parse_json(self.data_import.employee_template_options or "{}")
		self.user_options = frappe.parse_json(self.data_import.user_template_options or "{}")
		self.raw_data = self.load_file_data()
		self.prepare_data()

	def load_file_data(self):
		file_url = self.data_import.import_file
		if not file_url:
			return []
		if "docs.google.com/spreadsheets" in file_url:
			content = get_csv_content_from_google_sheets(file_url)
			return read_csv_content(content)
		file_doc = frappe.get_doc("File", {"file_url": file_url})
		content = file_doc.get_content()
		ext = file_doc.get_extension()[1].lstrip(".")
		if ext == "csv":
			return read_csv_content(content)
		elif ext == "xlsx":
			return read_xlsx_file_from_attached_file(fcontent=content)
		elif ext == "xls":
			return read_xls_file_from_attached_file(content)
		else:
			frappe.throw(_("Unsupported file format"))

	def prepare_data(self):
		if not self.raw_data:
			return
		for i, row in enumerate(self.raw_data):
			if all(v in INVALID_VALUES for v in row):
				continue
			if i == 0:
				self.header = [str(cell).strip() if cell is not None else "" for cell in row]
				self.create_columns()
			else:
				self.rows.append({"index": i, "row_number": i + 1, "data": row})

	def create_columns(self):
		self.columns = []
		for i, header_title in enumerate(self.header):
			column = {"index": i, "header_title": header_title, "skip_import": False, "df": None}
			if self.import_mode in ["Employee", "Both"]:
				emp_map = self.employee_options.get("column_to_field_map", {})
				if header_title in emp_map and emp_map[header_title] != "Don't Import":
					column["df"] = self.get_field_def(self.employee_doctype, emp_map[header_title])
			if not column["df"] and self.import_mode in ["User", "Both"]:
				usr_map = self.user_options.get("column_to_field_map", {})
				if header_title in usr_map and usr_map[header_title] != "Don't Import":
					column["df"] = self.get_field_def(self.user_doctype, usr_map[header_title])
			if not column["df"]:
				column["df"] = self.auto_match(header_title)
				if not column["df"]:
					column["skip_import"] = True
			self.columns.append(column)

	def get_field_def(self, doctype, fieldname):
		if "." in fieldname:
			parent_field, child_field = fieldname.split(".", 1)
			parent_meta = frappe.get_meta(doctype)
			df = parent_meta.get_field(parent_field)
			if df:
				return {
					"fieldtype": df.fieldtype,
					"fieldname": fieldname,
					"label": df.label,
					"options": df.options,
					"parent": doctype,
				}
		meta = frappe.get_meta(doctype)
		df = meta.get_field(fieldname)
		if df:
			return {
				"fieldtype": df.fieldtype,
				"fieldname": df.fieldname,
				"label": df.label,
				"options": df.options,
				"parent": doctype,
			}
		return None

	def auto_match(self, header_title):
		search_doctypes = []
		if self.import_mode in ["Employee", "Both"]:
			search_doctypes.append(self.employee_doctype)
		if self.import_mode in ["User", "Both"]:
			search_doctypes.append(self.user_doctype)
		for dt in search_doctypes:
			meta = frappe.get_meta(dt)
			for df in meta.fields:
				if df.label and header_title.lower() == df.label.lower():
					return {
						"fieldtype": df.fieldtype,
						"fieldname": df.fieldname,
						"label": df.label,
						"options": df.options,
						"parent": dt,
					}
		return None

	def validate_and_transform(self, doctype, fieldname, value, is_child=False):
		if value in INVALID_VALUES:
			return None
		meta = frappe.get_meta(doctype)
		df = meta.get_field(fieldname)
		if not df:
			return value

		if df.fieldtype == "Link":
			target_doctype = df.options
			existing_name = frappe.db.get_value(target_doctype, value, "name")
			if existing_name:
				return existing_name
			target_meta = frappe.get_meta(target_doctype)
			title_field = target_meta.get_title_field()
			if title_field:
				existing_by_title = frappe.db.get_value(
					target_doctype, {title_field: ["like", value]}, "name"
				)
				if existing_by_title:
					return existing_by_title
			new_doc = frappe.new_doc(target_doctype)
			new_doc.set(title_field or "name", value)
			new_doc.insert(ignore_permissions=True, ignore_mandatory=True)
			return new_doc.name
		return value

	def parse_row_separated(self, row, doctype):
		base_data = {}
		child_data_map = {}
		mapping = (self.employee_options if doctype == self.employee_doctype else self.user_options).get(
			"column_to_field_map", {}
		)

		for col in self.columns:
			fld = mapping.get(col["header_title"])
			if not fld or fld == "Don't Import" or col["index"] >= len(row["data"]):
				continue
			raw_val = row["data"][col["index"]]
			if raw_val in INVALID_VALUES:
				continue

			if "." in fld:
				parent_fld, child_fld = fld.split(".", 1)
				parent_df = frappe.get_meta(doctype).get_field(parent_fld)
				if parent_df and parent_df.fieldtype in ["Table", "Table MultiSelect"]:
					child_doctype = parent_df.options
					vals = [v.strip() for v in str(raw_val).split(",") if v.strip()]
					if parent_fld not in child_data_map:
						child_data_map[parent_fld] = {"doctype": child_doctype, "rows": []}
					for idx, val in enumerate(vals):
						transformed = self.validate_and_transform(child_doctype, child_fld, val, True)
						if len(child_data_map[parent_fld]["rows"]) <= idx:
							child_data_map[parent_fld]["rows"].append({})
						child_data_map[parent_fld]["rows"][idx][child_fld] = transformed
			else:
				base_data[fld] = self.validate_and_transform(doctype, fld, raw_val)
		return base_data, child_data_map

	def has_changes(self, doc, base_data, child_data_map):
		changed = False
		for key, value in base_data.items():
			if str(doc.get(key)) != str(value):
				doc.set(key, value)
				changed = True

		for parent_fld, config in child_data_map.items():
			current_rows = doc.get(parent_fld) or []
			new_rows = config["rows"]

			if len(current_rows) != len(new_rows):
				changed = True
				continue

			for i in range(len(new_rows)):
				for field, val in new_rows[i].items():
					if str(current_rows[i].get(field)) != str(val):
						changed = True
						break
				if changed:
					break
		return changed

	def insert_child_rows(self, parent_doc, child_data_map):
		for parent_fld, config in child_data_map.items():
			frappe.db.delete(config["doctype"], {"parent": parent_doc.name, "parentfield": parent_fld})
			for row_data in config["rows"]:
				row_data.update(
					{
						"parent": parent_doc.name,
						"parentfield": parent_fld,
						"parenttype": parent_doc.doctype,
						"doctype": config["doctype"],
						"name": frappe.generate_hash(length=10),
					}
				)
				frappe.flags.in_import = True
				frappe.get_doc(row_data).insert(
					ignore_permissions=True,
					ignore_links=True,
					ignore_if_duplicate=True,
					ignore_mandatory=True,
				)

	def import_single_row(self, row):
		try:
			user_id = None
			docname = None

			if self.import_mode in ["User", "Both"]:
				u_base, u_child = self.parse_row_separated(row, self.user_doctype)
				if u_base.get("email"):
					exists = frappe.db.exists("User", u_base["email"])
					if exists:
						u_doc = frappe.get_doc("User", exists)
						if self.has_changes(u_doc, u_base, u_child):
							u_doc.save(ignore_permissions=True)
							self.insert_child_rows(u_doc, u_child)
						user_id = u_doc.name
					else:
						user_id = self.upsert_user_base(u_base)
						self.insert_child_rows(frappe.get_doc("User", user_id), u_child)

					ensure_user_self_permission(user_id)
					docname = user_id

			if self.import_mode in ["Employee", "Both"]:
				e_base, e_child = self.parse_row_separated(row, self.employee_doctype)
				if e_base:
					if user_id:
						e_base["user_id"] = user_id
					email = e_base.get("personal_email")
					exists = frappe.db.exists("Employee", {"personal_email": email}) if email else None
					if exists:
						emp = frappe.get_doc("Employee", exists)
						if self.has_changes(emp, e_base, e_child):
							emp.save(ignore_permissions=True)
							self.insert_child_rows(emp, e_child)
						docname = emp.name
					else:
						docname = self.create_doc_base("Employee", e_base)
						self.insert_child_rows(frappe.get_doc("Employee", docname), e_child)

			self.log(row["row_number"], True, _("Import Successful"), docname=docname)
			return True
		except Exception as e:
			self.log(row["row_number"], False, str(e), exception=frappe.get_traceback())
			return False

	def upsert_user_base(self, data):
		frappe.flags.in_import = True
		u = frappe.new_doc("User")
		u.update(data)
		if not u.first_name:
			u.first_name = data.get("email").split("@")[0]
		u.enabled = 1
		u.send_welcome_email = 0
		u.insert(ignore_permissions=True)
		return u.name

	def create_doc_base(self, doctype, data):
		frappe.flags.in_import = True
		d = frappe.new_doc(doctype)
		d.update(data)
		d.insert(ignore_permissions=True)
		return d.name

	def log(self, idx, success, msg, docname=None, exception=None, row_indexes=None):
		indexes = row_indexes if row_indexes else [idx]
		frappe.get_doc(
			{
				"doctype": "Data Import Log",
				"data_import": self.data_import.name,
				"log_index": idx,
				"success": 1 if success else 0,
				"messages": json.dumps([{"message": msg}]) if msg else None,
				"row_indexes": json.dumps(indexes),
				"docname": docname,
				"exception": exception,
			}
		).db_insert()
