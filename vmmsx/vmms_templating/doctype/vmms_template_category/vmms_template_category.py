# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Template Category — the configurable set of kinds of template.

Certificate, agreement, notification: a society may add to this list, and that
is the whole point of it being a doctype rather than a Select. **No source file
in vmmsx branches on a category value.** The render service returns the category
as data and treats every template identically, so adding one needs no code.
"""

from frappe.model.document import Document


class VMMSTemplateCategory(Document):
	pass
