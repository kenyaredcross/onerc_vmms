# Copyright (c) 2026, Kenya Red Cross Society and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ICTIncidentManagent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date_incident_occured: DF.Date | None
		describe_the_incident: DF.SmallText | None
		name_of_incident: DF.Data | None
	# end: auto-generated types
	pass
