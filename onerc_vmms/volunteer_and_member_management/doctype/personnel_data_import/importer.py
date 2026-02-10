import json
import frappe
from frappe import _
from frappe.utils.csvutils import get_csv_content_from_google_sheets, read_csv_content
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file, read_xls_file_from_attached_file

INVALID_VALUES = ("", None)

class PersonnelDataImporter:
    def __init__(self, employee_doctype, user_doctype, data_import=None):
        self.employee_doctype = employee_doctype
        self.user_doctype = user_doctype
        self.data_import = data_import
        self.header = []
        self.rows = []
        self.columns = []
        self.employee_options = frappe.parse_json(self.data_import.employee_template_options or "{}")
        self.user_options = frappe.parse_json(self.data_import.user_template_options or "{}")
        self.raw_data = self.load_file_data()
        self.prepare_data()

    def load_file_data(self):
        file_url = self.data_import.import_file
        if not file_url: return []
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
        if not self.raw_data: return
        for i, row in enumerate(self.raw_data):
            if all(v in INVALID_VALUES for v in row): continue
            if i == 0:
                self.header = [str(cell).strip() if cell is not None else "" for cell in row]
                self.create_columns()
            else:
                self.rows.append({"index": i, "row_number": i + 1, "data": row})

    def create_columns(self):
        self.columns = []
        for i, header_title in enumerate(self.header):
            column = {"index": i, "header_title": header_title, "skip_import": False, "df": None}
            emp_map = self.employee_options.get("column_to_field_map", {})
            if header_title in emp_map and emp_map[header_title] != "Don't Import":
                column["df"] = self.get_field_def(self.employee_doctype, emp_map[header_title])
            if not column["df"]:
                usr_map = self.user_options.get("column_to_field_map", {})
                if header_title in usr_map and usr_map[header_title] != "Don't Import":
                    column["df"] = self.get_field_def(self.user_doctype, usr_map[header_title])
            if not column["df"]:
                column["df"] = self.auto_match(header_title)
                if not column["df"]: column["skip_import"] = True
            self.columns.append(column)

    def get_field_def(self, doctype, fieldname):
        meta = frappe.get_meta(doctype)
        df = meta.get_field(fieldname)
        if df:
            return {"fieldtype": df.fieldtype, "fieldname": df.fieldname, "label": df.label, "options": df.options, "parent": doctype}
        return None

    def auto_match(self, header_title):
        for dt in [self.employee_doctype, self.user_doctype]:
            meta = frappe.get_meta(dt)
            for df in meta.fields:
                if df.label and header_title.lower() == df.label.lower():
                    return {"fieldtype": df.fieldtype, "fieldname": df.fieldname, "label": df.label, "options": df.options, "parent": dt}
        return None

    def import_single_row(self, row):
        try:
            user_id = None
            user_data = self.parse_row(row, self.user_doctype)
            if user_data and user_data.get("email"):
                user_id = self.upsert_user(user_data)
            
            emp_data = self.parse_row(row, self.employee_doctype)
            if emp_data:
                if user_id: emp_data["user_id"] = user_id
                email = emp_data.get("personal_email")
                exists = frappe.db.exists("Employee", {"personal_email": email}) if email else None
                
                if not exists:
                    self.create_doc("Employee", emp_data)
                else:
                    pass
            return True
        except Exception as e:
            self.log(row["row_number"], False, str(e), exception=frappe.get_traceback())
            return False

    def parse_row(self, row, doctype):
        data = {}
        mapping = (self.employee_options if doctype == self.employee_doctype else self.user_options).get("column_to_field_map", {})
        for col in self.columns:
            fld = mapping.get(col["header_title"])
            if fld and fld != "Don't Import" and col["index"] < len(row["data"]):
                val = row["data"][col["index"]]
                if val not in INVALID_VALUES: data[fld] = val
        return data

    def upsert_user(self, data):
        email = data.get("email")
        if frappe.db.exists("User", email):
            u = frappe.get_doc("User", email)
            u.update(data)
            u.save(ignore_permissions=True)
            return u.name
        
        u = frappe.new_doc("User")
        u.update(data)
        if not u.first_name: u.first_name = email.split('@')[0]
        u.enabled = 1
        u.send_welcome_email = 0
        u.db_insert()
        return u.name

    def create_doc(self, doctype, data):
        d = frappe.new_doc(doctype)
        d.update(data)
        d.insert(ignore_permissions=True)
        return d.name

    def log(self, idx, success, msg, docname=None, exception=None, row_indexes=None):
        indexes = row_indexes if row_indexes else [idx]
        
        frappe.get_doc({
            "doctype": "Data Import Log",
            "data_import": self.data_import.name,
            "log_index": idx,
            "success": 1 if success else 0,
            "messages": json.dumps([msg]) if msg else None,
            "row_indexes": json.dumps(indexes),
            "docname": docname,
            "exception": exception
        }).db_insert()