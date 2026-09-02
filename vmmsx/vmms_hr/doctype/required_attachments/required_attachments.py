# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Required Attachments — One document an opening asks an applicant to attach.

A child table. The type is a link into `Supporting Document Type`; the name is
free text for the case where a society wants a particular document of that type
("Certificate of Good Conduct issued within 6 months").
"""

from frappe.model.document import Document


class RequiredAttachments(Document):
	pass
