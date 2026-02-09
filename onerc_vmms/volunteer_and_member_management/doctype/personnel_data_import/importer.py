import json
import os
import time
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.csvutils import get_csv_content_from_google_sheets, read_csv_content
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file, read_xls_file_from_attached_file

INVALID_VALUES = ("", None)
MAX_ROWS_IN_PREVIEW = 10

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
        self.import_logs = []

    def load_file_data(self):
        file_url = self.data_import.import_file
        if "docs.google.com/spreadsheets" in file_url:
            content = get_csv_content_from_google_sheets(file_url)
            return read_csv_content(content)
        else:
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
            employee_map = self.employee_options.get("column_to_field_map", {})
            if header_title in employee_map:
                mapping = employee_map[header_title]
                if mapping != "Don't Import":
                    column["df"] = self.get_field_definition(self.employee_doctype, mapping)
            if not column["df"]:
                user_map = self.user_options.get("column_to_field_map", {})
                if header_title in user_map:
                    mapping = user_map[header_title]
                    if mapping != "Don't Import":
                        column["df"] = self.get_field_definition(self.user_doctype, mapping)
            if not column["df"]:
                column["df"] = self.auto_match_field(header_title)
                if not column["df"]:
                    column["skip_import"] = True
            self.columns.append(column)

    def get_field_definition(self, doctype, fieldname):
        meta = frappe.get_meta(doctype)
        for df in meta.fields:
            if df.fieldname == fieldname:
                return {"fieldtype": df.fieldtype, "fieldname": df.fieldname, "label": df.label, "options": df.options, "parent": doctype}
        return None

    def auto_match_field(self, header_title):
        if not header_title:
            return None
        for dt in [self.employee_doctype, self.user_doctype]:
            meta = frappe.get_meta(dt)
            for df in meta.fields:
                if df.label and header_title.lower() == df.label.lower():
                    return {"fieldtype": df.fieldtype, "fieldname": df.fieldname, "label": df.label, "options": df.options, "parent": dt}
        return None

    def get_data_for_import_preview(self):
        valid_col_indices = []
        preview_columns = [{"header_title": _("Sr. No"), "skip_import": True}]
        for col in self.columns:
            if not col["header_title"] and col["skip_import"]:
                continue
            col_dict = {"index": col["index"], "header_title": col["header_title"] or _("Unnamed Column"), "skip_import": col["skip_import"]}
            if col.get("df"):
                col_dict["df"] = col["df"]
            preview_columns.append(col_dict)
            valid_col_indices.append(col["index"])
        preview_data = []
        for row in self.rows[:MAX_ROWS_IN_PREVIEW]:
            filtered_row = [row["row_number"]]
            for idx in valid_col_indices:
                val = row["data"][idx] if idx < len(row["data"]) else None
                filtered_row.append(val)
            preview_data.append(filtered_row)
        result = {"columns": preview_columns, "data": preview_data, "total_number_of_rows": len(self.rows)}
        if len(self.rows) > MAX_ROWS_IN_PREVIEW:
            result["max_rows_exceeded"] = True
            result["max_rows_in_preview"] = MAX_ROWS_IN_PREVIEW
        return result

    def split_string_values(self, value):
        if not value: return []
        content = str(value).replace('\n', ',')
        return [v.strip() for v in content.split(',') if v.strip()]

    def get_or_create_link(self, doctype, value):
        if not value: return None
        existing = frappe.db.get_value(doctype, {"name": value}, "name")
        if not existing:
            existing = frappe.db.get_value(doctype, {"name": ["like", f"%{value}%"]}, "name")
        if existing: return existing
        meta = frappe.get_meta(doctype)
        search_fields = [f.fieldname for f in meta.fields if f.fieldtype in ["Data", "Small Text"]]
        for field in search_fields:
            match = frappe.db.get_value(doctype, {field: ["like", f"%{value}%"]}, "name")
            if match: return match
        try:
            new_doc = frappe.new_doc(doctype)
            title_field = meta.get_title_field() or "name"
            if title_field == "name":
                new_doc.name = value
            else:
                new_doc.set(title_field, value)
            
            new_doc.db_insert()
            return new_doc.name
        except Exception as e:
            frappe.log_error(title=f"Personnel Import Link creation failed: {doctype}", message=str(e))
            return value

    def process_field_by_type(self, df, value):
        ftype = df.get("fieldtype")
        options = df.get("options")
        if ftype == "Link":
            return self.get_or_create_link(options, value)
        elif ftype == "Table MultiSelect":
            values = self.split_string_values(value)
            meta = frappe.get_meta(options)
            link_field = next(f.fieldname for f in meta.fields if f.fieldtype == "Link")
            return [{link_field: self.get_or_create_link(meta.get_field(link_field).options, v)} for v in values]
        elif ftype == "Table":
            values = self.split_string_values(value)
            meta = frappe.get_meta(options)
            main_field = meta.fields[0].fieldname
            return [{main_field: v} for v in values]
        elif ftype == "Check":
            return 1 if str(value).lower() in ["1", "yes", "true", "y"] else 0
        return value

    def parse_row_for_doctype(self, row, doctype):
        doc = {}
        mapping_dict = (self.employee_options if doctype == self.employee_doctype else self.user_options).get("column_to_field_map", {})
        for col in self.columns:
            fieldname = mapping_dict.get(col.get("header_title"))
            if not fieldname or fieldname == "Don't Import":
                continue
            if col["index"] < len(row["data"]):
                val = row["data"][col["index"]]
                if val not in INVALID_VALUES:
                    df = self.get_field_definition(doctype, fieldname)
                    if df:
                        doc[fieldname] = self.process_field_by_type(df, val)
        return doc if doc else None

    def import_data(self):
        successes = 0
        failures = 0
        total_rows = len(self.rows)
        frappe.flags.mute_emails = True
        self.data_import.db_set("status", "In Progress")
        
        for idx, row in enumerate(self.rows):
            try:
                if (idx + 1) % 50 == 0:
                    frappe.publish_realtime("data_import_progress", {"current": idx + 1, "total": total_rows, "data_import": self.data_import.name})
                    time.sleep(0.01) 

                user_id = None
                
                try:
                    user_data = self.parse_row_for_doctype(row, self.user_doctype)
                    if user_data and user_data.get("email"):
                        user_id = self.upsert_user(user_data, row["row_number"])
                except Exception as ue:
                    frappe.log_error(title=f"User creation failed at row {row['row_number']}", message=frappe.get_traceback())
                    self.create_import_log(row["row_number"], False, f"User Error: {str(ue)}")

                try:
                    employee_data = self.parse_row_for_doctype(row, self.employee_doctype)
                    if employee_data:
                        if user_id:
                            employee_data["user_id"] = user_id
                        
                        email_field = "personal_email"
                        existing_employee = frappe.db.exists("Employee", {email_field: employee_data.get(email_field)})
                        
                        if not existing_employee:
                            emp_name = self.create_employee(employee_data, row["row_number"])
                            self.create_import_log(row["row_number"], True, f"Created Employee: {emp_name}", emp_name)
                        else:
                            self.create_import_log(row["row_number"], True, f"Employee exists: {existing_employee}", existing_employee)
                except Exception as ee:
                    frappe.log_error(title=f"Employee creation failed at row {row['row_number']}", message=frappe.get_traceback())
                    self.create_import_log(row["row_number"], False, f"Employee Error: {str(ee)}")

                successes += 1
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(title=f"Unexpected error at row {row['row_number']}", message=frappe.get_traceback())
                self.create_import_log(row["row_number"], False, f"Row Error: {str(e)}", None, frappe.get_traceback())
                failures += 1
        
        frappe.flags.mute_emails = False
        status = "Success" if failures == 0 else ("Partial Success" if successes > 0 else "Error")
        self.data_import.db_set({"status": status, "successes": successes, "failures": failures, "total": total_rows})
        frappe.publish_realtime("data_import_refresh", {"data_import": self.data_import.name})
        return {"successes": successes, "failures": failures, "total": total_rows, "status": status}

    def upsert_user(self, user_data, row_number):
        email = user_data.get("email")
        if not email: return None
        if frappe.db.exists("User", email):
            user = frappe.get_doc("User", email)
            user.update(user_data)
            user.save(ignore_permissions=True)
            return user.name
        
        user = frappe.new_doc("User")
        user.email = email
        user.first_name = user_data.get("first_name", email.split('@')[0])
        user.send_welcome_email = 0
        user.role_profile_name = "Volunteer"
        user.module_profile = "Volunteer"
        
        user.db_insert()
        
        remaining_data = {k: v for k, v in user_data.items() if k not in ["email", "first_name"]}
        if remaining_data:
            user.update(remaining_data)
            user.save(ignore_permissions=True)
        return user.name

    def create_employee(self, employee_data, row_number):
        new_doc = frappe.new_doc("Employee")
        mandatory_fields = ["company", "date_of_joining", "gender", "date_of_birth", "first_name"]
        for field in mandatory_fields:
            if field in employee_data:
                new_doc.set(field, employee_data[field])
        
        new_doc.db_insert()
        
        remaining_data = {k: v for k, v in employee_data.items() if k not in mandatory_fields}
        if remaining_data:
            new_doc.update(remaining_data)
            new_doc.save(ignore_permissions=True)
        return new_doc.name

    def create_import_log(self, row_number, success, message, docname=None, exception=None):
        log_entry = {
            "doctype": "Data Import Log", 
            "data_import": self.data_import.name, 
            "log_index": row_number, 
            "success": success, 
            "message": message, 
            "docname": docname,
            "exception": exception
        }
        try:
            l = frappe.get_doc(log_entry)
            l.db_insert()
        except Exception as e:
            frappe.log_error(title="Personnel Import log creation failed", message=str(e))
        self.import_logs.append(log_entry)

class PersonnelDataImport(Document):
    def validate(self):
        doc_before_save = self.get_doc_before_save()
        if not self.import_file or (doc_before_save and doc_before_save.import_file != self.import_file):
            self.employee_template_options = ""
            self.user_template_options = ""
        for dt in ["Employee", "User"]:
            if not frappe.has_permission(dt, "import"):
                frappe.throw(_("No import permission for {0}").format(dt), frappe.PermissionError)

    @frappe.whitelist()
    def get_preview_from_template(self):
        if not self.import_file: return
        return PersonnelDataImporter("Employee", "User", data_import=self).get_data_for_import_preview()

    def start_import(self):
        frappe.enqueue(
            self._execute_import,
            queue="long",
            job_name=f"personnel_data_import_{self.name}"
        )

    def _execute_import(self):
        try:
            importer = PersonnelDataImporter("Employee", "User", data_import=self)
            result = importer.import_data()
            return True
        except Exception as e:
            frappe.log_error(title="Personnel Data Import Fatal Error", message=frappe.get_traceback())
            self.db_set("status", "Error")
            return False
        finally:
            frappe.publish_realtime("data_import_refresh", {"data_import": self.name})

@frappe.whitelist()
def get_import_logs(data_import: str):
    doc = frappe.get_doc("Personnel Data Import", data_import)
    doc.check_permission("read")
    return frappe.get_all("Data Import Log", fields=["log_index", "success", "message", "docname", "exception"], filters={"data_import": data_import}, order_by="log_index")