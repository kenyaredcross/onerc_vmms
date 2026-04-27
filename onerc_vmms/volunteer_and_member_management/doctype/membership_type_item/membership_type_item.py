# Copyright (c) 2025, Kenya Red Cross Society and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MembershipTypeItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		membership_type: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types
	pass
