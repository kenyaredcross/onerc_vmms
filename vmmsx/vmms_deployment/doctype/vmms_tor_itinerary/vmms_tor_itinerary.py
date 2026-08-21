# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One line of a mission's itinerary: a day, a time, a thing that happens.

A child row with no rules of its own. In particular it does **not** check that
its date falls between the mission's own start and end dates — that rule lives
on the parent, in `VMMS Terms of Reference.validate_itinerary`, because a child
row cannot see the parent's dates while it is being edited and a rule that
half-works is worse than one written down in one place.
"""

from frappe.model.document import Document


class VMMSTORItinerary(Document):
	pass
