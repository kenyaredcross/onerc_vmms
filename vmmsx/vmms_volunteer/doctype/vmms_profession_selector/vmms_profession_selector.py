# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The row shape `Table MultiSelect` needs: one Link, nothing else.

Exists so `VMMS Deployment.professions_needed` can be a multi-select of
`Profession`. Holds no logic of its own.
"""

from frappe.model.document import Document


class VMMSProfessionSelector(Document):
	pass
