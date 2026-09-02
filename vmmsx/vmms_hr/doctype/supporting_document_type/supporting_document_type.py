# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Supporting Document Type — The kinds of document an application can be asked to carry.

`is_required` is the society's default for the type; an opening still lists the
documents it wants in its own `required_attachments` table, so a type marked
required here is a default and not a global rule.
"""

from frappe.model.document import Document


class SupportingDocumentType(Document):
	pass
