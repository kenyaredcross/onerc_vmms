# Copyright (c) 2026, Kenya Red Cross Society and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class VMNotificationParty(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		link_doctype: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party: DF.DynamicLink | None
		party_name: DF.Data | None
		phone: DF.Data | None
		user: DF.Link | None
	# end: auto-generated types
	pass
