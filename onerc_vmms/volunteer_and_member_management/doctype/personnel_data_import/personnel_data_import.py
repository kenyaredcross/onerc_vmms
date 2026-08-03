import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from .importer import PersonnelDataImporter

CHUNK_SIZE = 100


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
		if not self.import_file:
			return
		importer = PersonnelDataImporter("Employee", "User", data_import=self)
		valid_indices = [
			c["index"] for c in importer.columns if not (not c["header_title"] and c["skip_import"])
		]

		preview_data = []
		for r in importer.rows[:10]:
			preview_data.append([r["row_number"]] + [r["data"][i] for i in valid_indices])

		return {
			"columns": [{"header_title": _("Sr. No")}]
			+ [c for c in importer.columns if c["index"] in valid_indices],
			"data": preview_data,
			"total_number_of_rows": len(importer.rows),
		}

	def start_import(self):
		importer = PersonnelDataImporter("Employee", "User", data_import=self)
		total_rows = len(importer.rows)

		if total_rows == 0:
			frappe.throw(_("No data found to import"))

		self.db_set(
			{
				"status": "In Progress",
				"total": total_rows,
				"successes": 0,
				"failures": 0,
			}
		)

		path = "onerc_vmms.volunteer_and_member_management.doctype.personnel_data_import.personnel_data_import.execute_import_chunk"

		for i in range(0, total_rows, CHUNK_SIZE):
			frappe.enqueue(
				path,
				data_import_name=self.name,
				start_index=i,
				end_index=i + CHUNK_SIZE,
				queue="long",
				timeout=10000,
			)


@frappe.whitelist()
def export_errored_rows(name: str):
	from frappe.utils.csvutils import build_csv_response

	frappe.get_doc("Personnel Data Import", name).check_permission("read")

	logs = frappe.get_list(
		"Data Import Log",
		fields=["log_index", "row_indexes", "messages", "docname", "exception"],
		filters={"data_import": name, "success": 0},
		order_by="log_index asc",
	)

	if not logs:
		frappe.throw(_("No error logs found for this import."))

	headers = [_("Excel Row Numbers"), _("Error Message"), _("Technical Traceback")]

	csv_rows = [headers]

	for log in logs:
		try:
			msg_list = json.loads(log.messages or "[]")
			readable_msg = "; ".join([m.get("message", "") for m in msg_list if m.get("message")])
		except Exception:
			readable_msg = log.messages

		try:
			rows = ", ".join(map(str, json.loads(log.row_indexes or "[]")))
		except Exception:
			rows = log.row_indexes

		csv_rows.append([rows, readable_msg, log.exception])

	build_csv_response(csv_rows, f"Error_Log_{name}")


def execute_import_chunk(data_import_name, start_index, end_index):
	doc = frappe.get_doc("Personnel Data Import", data_import_name)
	importer = PersonnelDataImporter("Employee", "User", data_import=doc)

	batch = importer.rows[start_index:end_index]
	local_success = 0
	local_failures = 0
	success_rows = []

	for row in batch:
		if importer.import_single_row(row):
			local_success += 1
			success_rows.append(row["row_number"])
		else:
			local_failures += 1

	if local_success > 0:
		importer.log(
			idx=success_rows[0],
			success=True,
			msg=f"Successfully processed {local_success} records in this batch.",
			docname=f"Batch {start_index}-{end_index}",
			row_indexes=success_rows,
		)

	counts = frappe.db.get_value(
		"Personnel Data Import", data_import_name, ["successes", "failures"], as_dict=1
	)
	frappe.db.set_value(
		"Personnel Data Import",
		data_import_name,
		{
			"successes": cint(counts.successes or 0) + local_success,
			"failures": cint(counts.failures or 0) + local_failures,
		},
		update_modified=False,
	)

	frappe.db.commit()

	updated_doc = frappe.get_doc("Personnel Data Import", data_import_name)
	if (cint(updated_doc.successes) + cint(updated_doc.failures)) >= cint(updated_doc.total):
		status = "Success" if cint(updated_doc.failures) == 0 else "Partial Success"
		updated_doc.db_set("status", status)
		frappe.publish_realtime("data_import_refresh", {"data_import": data_import_name})


@frappe.whitelist()
def form_start_import(data_import):
	doc = frappe.get_doc("Personnel Data Import", data_import)
	doc.check_permission("write")
	doc.start_import()
	return True


@frappe.whitelist()
def get_import_logs(data_import: str):
	frappe.get_doc("Personnel Data Import", data_import).check_permission("read")

	return frappe.get_list(
		"Data Import Log",
		fields=[
			"docname",
			"log_index",
			"success",
			"messages",
			"row_indexes",
			"exception",
		],
		filters={"data_import": data_import},
		order_by="log_index desc",
		limit_page_length=100,
	)
