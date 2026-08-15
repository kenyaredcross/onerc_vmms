# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The row shape `Table MultiSelect` needs: one Link, nothing else.

Exists only so `VMMS Volunteer Application.languages` can be a multi-select of
Frappe's own `Language` doctype. Languages spoken are not a society's
vocabulary to invent — Frappe already ships one, core already links to it
(`Red Profile.preferred_language`, `National Society Settings.primary_language`)
— so this reuses it rather than building a second list of the world's
languages. Holds no logic of its own.
"""

from frappe.model.document import Document


class VMMSLanguageSelector(Document):
	pass
