# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One resource a mission needs, what it costs, and who is expected to fund it.

A child row with no rules of its own. `total_cost` is derived from quantity and
unit cost, but it is computed on the **parent** — `VMMS Terms of Reference` runs
`price_resources()` in its own validate — rather than here. Frappe does not call
a child controller's `validate`, so a rule written in this file would look like
it worked and quietly never run.
"""

from frappe.model.document import Document


class VMMSTORResource(Document):
	pass
