# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Motivation — a society's own vocabulary of why people volunteer.

An open set, extended freely, and **no code anywhere branches on a motivation
value**. Seeded with a starting set by
`vmmsx.patches.setup_volunteer_application_module`; owned by the society from
the moment it lands.

The controller is empty on purpose. There is nothing to validate: a society's
vocabulary is not this app's to have an opinion about.
"""

from frappe.model.document import Document


class VMMSMotivation(Document):
	pass
