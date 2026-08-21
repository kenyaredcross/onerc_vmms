# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One methodology a mission will use, and what it means for this mission.

A child row with no rules of its own. The Link carries the society's own name
for the method; the notes carry how this particular mission applies it. Neither
is read by code — the split exists so a society can report across missions on
*how* it works, which a typed-in phrase would never allow.
"""

from frappe.model.document import Document


class VMMSTORApproach(Document):
	pass
