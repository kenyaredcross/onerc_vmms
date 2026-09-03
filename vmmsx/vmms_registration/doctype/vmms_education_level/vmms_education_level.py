# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""How far somebody got in school, as a register a society edits.

A vocabulary and not a ladder. `sequence` orders the picker and nothing else
reads it: no code in this app decides that one level outranks another, because
the mapping between a national qualification and a rung is a thing societies
disagree about and this product has no business settling.

Seeded with the ISCED-shaped list `patches/install_background_fields.py` carries,
which a society renames, reorders or deletes outright."""

from frappe.model.document import Document


class VMMSEducationLevel(Document):
	pass
