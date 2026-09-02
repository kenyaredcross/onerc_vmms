# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Emergency Contact — who to call about this volunteer, and whether we may.

A child table on the registration, held by vmmsx and never written to
`Red Profile`. That placement is a decision, not an accident, and it is worth
stating because the obvious alternative looks tidier and is wrong.

Core's identity spine deliberately holds `next_of_kin` off to one side, in the
sensitive set `vmmsx/volunteer/services/identity.py::_WITHHELD` refuses to
surface at all, awaiting a gated extension of core's own. An emergency contact
is *not* that field wearing a different name:

- A next of kin is a fact about a person, true wherever they are and whoever is
  asking. An emergency contact is a fact about **this volunteering** — who the
  society should call if something happens while this person is out on its
  behalf — and an applicant may reasonably give a different name to each.
- The two have different lifetimes. A next of kin is corrected when a family
  changes; an emergency contact is re-asked every time somebody applies, and the
  one on a 2024 application is the right answer about a 2024 deployment.
- `may_contact_in_emergency` has no meaning at all on an identity record. It is
  permission given to *this society*, for *this purpose*, and it travels with
  the application that asked for it.

So `_WITHHELD` stays exactly as it is, nothing here is read from or written to
core, and when core's gated extension lands the two coexist without either
having to be migrated into the other.

**"May contact" is a real answer, not a formality.** An unticked box means the
society holds a number it has been told not to call, which is a different state
from holding no number — and `application.assert_approvable` counts only the
contacts the applicant actually permitted, because a contact nobody may call is
not an emergency contact.
"""

from frappe.model.document import Document


class VMMSEmergencyContact(Document):
	pass
