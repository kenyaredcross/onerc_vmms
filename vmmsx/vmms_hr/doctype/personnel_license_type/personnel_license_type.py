# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Personnel License Type — The kinds of licence this society recognises: a driving licence, a nursing
registration, a radio operator's certificate.

Named by whoever creates the row, for the same reason `Profession` is: the list
is jurisdictional. Referenced by `Personnel Licence`, the child table an opening
lists its required licences in.
"""

from frappe.model.document import Document


class PersonnelLicenseType(Document):
	pass
