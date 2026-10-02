from frappe.model.document import Document

from vmmsx.service_certificate import settings


class VMMSServiceCertificateSettings(Document):
	def validate(self):
		settings.validate(self)
