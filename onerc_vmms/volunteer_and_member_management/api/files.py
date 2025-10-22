import frappe
from frappe.core.doctype.file.file import save_file
from frappe.utils import _, cint


@frappe.whitelist(allow_guest=True)
def upload_file():
    try:
        if "file" not in frappe.request.files:
            frappe.throw(_("No file attached"))

        upload = frappe.request.files["file"]
        filename = frappe.request.form.get("filename") or upload.filename
        doctype = frappe.request.form.get("doctype")
        docname = frappe.request.form.get("docname")
        folder = frappe.request.form.get("folder")
        is_private = cint(frappe.request.form.get("is_private", 0))

        file_doc = save_file(
            fname=filename,
            content=upload.stream.read(),
            dt=doctype,
            dn=docname,
            folder=folder,
            is_private=is_private,
        )

        frappe.db.commit()
        return {
            "file_url": file_doc.file_url,
            "name": file_doc.name,
            "file_name": file_doc.file_name,
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Upload File Failed"))
        frappe.throw(_("Upload failed: {0}").format(str(e)))


def _attach_file(doc, file_info, field_name=None):
    file_url = file_info.get("file_url") if isinstance(file_info, dict) else file_info
    file_name = file_info.get("file_name") if isinstance(file_info, dict) else None

    if not file_url:
        return

    already_attached = frappe.db.exists(
        "File",
        {
            "attached_to_doctype": doc.doctype,
            "attached_to_name": doc.name,
            "file_url": file_url,
        },
    )
    if already_attached:
        return

    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": file_name or file_url.split("/")[-1],
            "file_url": file_url,
            "attached_to_doctype": doc.doctype,
            "attached_to_name": doc.name,
            "is_private": 0,
            "file_size": 0,
            "content": None,
        }
    )

    file_doc.insert(ignore_permissions=True)

    if field_name:
        frappe.db.set_value(
            doc.doctype,
            doc.name,
            {field_name: file_doc.file_url},
        )
        frappe.db.commit()


def handle_attachment_files(application, files_data):
    profile_photo = files_data.get("profile_photo")
    documents = files_data.get("documents")
    resume = files_data.get("resume")
    for doc in documents or []:
        _attach_file(application, doc)
    if resume:
        _attach_file(application, resume, field_name="resume_attachment")

    if profile_photo:
        _attach_file(application, profile_photo, field_name="profile_photo")

    return application
