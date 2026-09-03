# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The row shape `Table MultiSelect` needs: one Link, nothing else.

Exists only so the `vmms_disabilities` Custom Field on core's `Red Profile` can
be a multi-select of core's own `Disability` register. Holds no logic.

**Why there is no note on the row.** The obvious extra field would be "anything
about this one" — and the profile already has `vmms_disability_needs` beside it,
which is one box for the whole answer. Two places to write the same sentence is
a form asking twice, and the second one would be the one nobody reads.

Lives in VMMS Registration rather than in VMMS Volunteer, with the emergency
contacts and the guardian consent, because the field it fills is a fact about a
*person*: a member has one as much as a volunteer does, and only the volunteer
path happens to ask for it today.
"""

from frappe.model.document import Document


class VMMSDisabilitySelector(Document):
	pass
