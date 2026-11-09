import os

import frappe
from frappe import _, cint
from frappe.core.api.file import get_max_file_size
from frappe.rate_limiter import rate_limit

ALLOWED_UPLOAD_TYPES = {
	".pdf": frozenset({"application/pdf"}),
	".png": frozenset({"image/png"}),
	".jpg": frozenset({"image/jpeg", "image/pjpeg"}),
	".jpeg": frozenset({"image/jpeg", "image/pjpeg"}),
	".docx": frozenset({"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}),
}


MAX_UPLOAD_SIZE = 10 * 1024 * 1024


ALLOWED_MAGIC_BYTES = {
	".pdf": (b"%PDF",),
	".png": (b"\x89PNG\r\n\x1a\n",),
	".jpg": (b"\xff\xd8\xff",),
	".jpeg": (b"\xff\xd8\xff",),
	".docx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
}


@frappe.whitelist()
@rate_limit(limit=20, seconds=60 * 5)
def upload_file():
	extension = None
	try:
		if "file" not in frappe.request.files:
			frappe.throw(_("No file attached"))

		upload = frappe.request.files["file"]
		filename = frappe.request.form.get("filename") or upload.filename

		if not filename:
			frappe.throw(_("Invalid file name"))

		extension = os.path.splitext(filename)[1].lower()
		allowed_content_types = ALLOWED_UPLOAD_TYPES.get(extension)
		if allowed_content_types is None:
			frappe.throw(_(f"File type {extension or filename} is not allowed"))

		content_type = (upload.content_type or "").split(";")[0].strip().lower()
		if content_type not in allowed_content_types:
			frappe.throw(_("File type is not allowed"))

		# Frappe's File doctype also enforces System Settings > Max File Size, so the
		# effective limit is the smaller of the two. Check it here so the user gets a
		# clear message instead of a generic failure from deep inside save_file.
		max_size = min(MAX_UPLOAD_SIZE, get_max_file_size())

		# Read at most max_size + 1 bytes so an oversized upload can't be
		# pulled fully into memory, then enforce the real size limit on actual bytes.
		content = upload.stream.read(max_size + 1)
		if not content:
			frappe.throw(_("The file is empty"))
		if len(content) > max_size:
			frappe.throw(
				_("File is too large. Maximum size is {0} MB.").format(f"{max_size / (1024 * 1024):g}"),
				title=_("File Too Large"),
			)

		# Verify the real content signature — the extension and declared MIME are
		# both client-supplied and cannot be trusted on their own.
		if not any(content.startswith(sig) for sig in ALLOWED_MAGIC_BYTES.get(extension, ())):
			frappe.throw(_("File content does not match its type"))

		is_private = cint(frappe.request.form.get("is_private", 1))

		# Save through the File doctype, the same way Frappe's own
		# /api/method/upload_file does, rather than the legacy
		# frappe.utils.file_manager.save_file. The legacy helper points the new File at
		# the URL of *any* existing File with the same content hash, so uploading bytes
		# that another user already uploaded privately fails with "You do not have
		# permission to access this file", and bytes whose earlier copy is missing from
		# disk fail with FileNotFoundError. File.save_file only reuses a copy that
		# actually exists on disk and otherwise writes a new one.
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": filename,
				"folder": frappe.request.form.get("folder") or "Home",
				"is_private": is_private,
				"content": content,
			}
		)
		file_doc.insert(ignore_permissions=True)

		frappe.db.commit()
		return {
			"file_url": file_doc.file_url,
			"name": file_doc.name,
			"file_name": file_doc.file_name,
		}

	except frappe.ValidationError:
		# Our own checks and Frappe's File validation raise these with a message the
		# user can act on (too large, wrong type, ...): log as before, but pass the
		# real message through instead of masking it as "Upload failed".
		frappe.log_error(_("Upload File Failed"), frappe.get_traceback())
		raise

	except Exception:
		frappe.log_error(_("Upload File Failed"), frappe.get_traceback())
		if extension == ".pdf":
			frappe.throw(
				_("This file could not be read as a PDF. It may be damaged; please re-save or re-scan it.")
			)
		frappe.throw(_("Upload failed"))


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


def _iter_file_urls(value):
	"""Yield every /files/ or /private/files/ URL reachable from a field value."""
	if isinstance(value, str):
		if value.startswith(("/files/", "/private/files/")):
			yield value
	elif isinstance(value, dict):
		for item in value.values():
			yield from _iter_file_urls(item)
	elif isinstance(value, (list, tuple)):
		for item in value:
			yield from _iter_file_urls(item)


def link_files_to_document(doc):
	urls = set()
	for field, value in doc.as_dict().items():
		if field in ("doctype", "name", "owner", "modified_by"):
			continue
		urls.update(_iter_file_urls(value))

	if not urls:
		return

	rows = frappe.get_all(
		"File",
		filters={"file_url": ("in", list(urls))},
		fields=["name", "attached_to_doctype", "attached_to_name"],
	)
	for row in rows:
		if row.attached_to_doctype and row.attached_to_name:
			continue
		frappe.db.set_value(
			"File",
			row.name,
			{"attached_to_doctype": doc.doctype, "attached_to_name": doc.name},
			update_modified=False,
		)
