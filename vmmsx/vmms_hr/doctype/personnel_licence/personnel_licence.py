# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Personnel Licence — One licence an opening requires, or one a person holds.

A child table. `license_name` is asked for only when the type is "Other", and a
`valid_to` date is insisted on only when the licence is not marked as
non-expiring — both rules live in the field definitions rather than in code.
"""

from frappe.model.document import Document


class PersonnelLicence(Document):
	pass
