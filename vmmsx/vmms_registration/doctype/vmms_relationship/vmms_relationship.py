# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""How an emergency contact knows the applicant, as a list a society edits.

Named by the relationship itself, so the value a contact stores is the word
people read ("Sibling"), and adding a relationship on the desk needs no code.
Clearing `is_active` stops the form offering one; contacts that already hold it
keep it. Seeded by `patches/install_relationships.py`.
"""

from frappe.model.document import Document


class VMMSRelationship(Document):
	pass
