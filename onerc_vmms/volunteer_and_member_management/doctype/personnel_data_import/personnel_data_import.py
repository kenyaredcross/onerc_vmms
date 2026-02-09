import frappe
from frappe import _
from frappe.model.document import Document
from .importer import PersonnelDataImporter

class PersonnelDataImport(Document):
    def validate(self):
        doc_before_save = self.get_doc_before_save()
        if (
            not self.import_file 
            or (doc_before_save and doc_before_save.import_file != self.import_file)
        ):
            self.employee_template_options = ""
            self.user_template_options = ""

        self.validate_doctype_permissions()

    def validate_doctype_permissions(self):
        for dt in ["Employee", "User"]:
            if not frappe.has_permission(dt, "import"):
                frappe.throw(_("No import permission for {0}").format(dt), frappe.PermissionError)

    @frappe.whitelist()
    def get_preview_from_template(self):
        if not self.import_file: return
        return PersonnelDataImporter("Employee", "User", data_import=self).get_data_for_import_preview()

    def start_import(self):
        importer = PersonnelDataImporter("Employee", "User", data_import=self)
        try:
            self.db_set("status", "In Progress")
            importer.import_data()
            return True
        except Exception as e:
            self.db_set("status", "Error")
            frappe.log_error(message=f"Import failed: {str(e)}", title="Personnel Import Error")
            return False
        finally:
            frappe.publish_realtime("data_import_refresh", {"data_import": self.name})

@frappe.whitelist()
def form_start_import(data_import):
    doc = frappe.get_doc("Personnel Data Import", data_import)
    doc.check_permission("write")
    return doc.start_import()

def run_import(data_import):
    doc = frappe.get_doc("Personnel Data Import", data_import)
    try:
        doc.db_set("status", "In Progress")
        importer = PersonnelDataImporter("Employee", "User", data_import=doc)
        importer.import_data()
    except Exception as e:
        frappe.log_error(message=f"Import failed: {str(e)}", title="Personnel Import Error")
        doc.db_set("status", "Error")
    finally:
        frappe.publish_realtime("data_import_refresh", {"data_import": doc.name})

@frappe.whitelist()
def get_import_logs(data_import: str):
    doc = frappe.get_doc("Personnel Data Import", data_import)
    doc.check_permission("read")

    return frappe.get_all(
        "Data Import Log",
        fields=["success", "docname", "messages", "exception", "row_indexes"],
        filters={"data_import": data_import},
        limit_page_length=5000,
        order_by="log_index",
    )
