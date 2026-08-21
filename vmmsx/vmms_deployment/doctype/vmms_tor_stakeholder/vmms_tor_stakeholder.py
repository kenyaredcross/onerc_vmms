# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One person or office a mission has to deal with, named on its terms of reference.

A child row with no rules of its own, and deliberately not a Link to anybody in
this app's registers. A stakeholder is usually somebody outside the society —
a county administrator, a partner agency's focal point, a community elder — and
making them a Link would mean either refusing to record them or creating a
volunteer record for somebody who is not one.
"""

from frappe.model.document import Document


class VMMSTORStakeholder(Document):
	pass
