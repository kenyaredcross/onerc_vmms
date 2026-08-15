# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Availability Slot — a society's own vocabulary of when a volunteer can serve.

Days, hours and shift patterns are society variable, so this is a doctype rather
than a `Select` a form built once and never revisited — a national society may
add a slot (school holidays, night shifts) or rename one without a code change.
It follows the exact shape of `VMMS Skill` and `VMMS Motivation` on purpose:
this module already has a proven pattern for "a society-editable multi-select
vocabulary", and giving availability its own bespoke shape would be a second
answer to a question this app has already answered twice.

An open set, extended freely, and **no code anywhere branches on a slot
value**. Seeded with a starting set by
`vmmsx.patches.setup_volunteer_application_module`; owned by the society from
the moment it lands.

The controller is empty on purpose. There is nothing to validate: a society's
vocabulary is not this app's to have an opinion about.
"""

from frappe.model.document import Document


class VMMSAvailabilitySlot(Document):
	pass
