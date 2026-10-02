from frappe.model.document import Document

from vmmsx.service_certificate import service


class VMMSServiceCertificateRequest(Document):
	def validate(self):
		service.validate(self)

	def on_update(self):
		service.on_update(self)

	def on_trash(self):
		service.prevent_delete(self)
