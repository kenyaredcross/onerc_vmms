# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One thing that could stop a programme of work.

A child row on ERPNext's `Project`, added by vmmsx because ERPNext has nowhere
to record a risk. Rows rather than a paragraph so a society reviewing its
portfolio can sort by impact and see which risks nobody is watching.

No rules of its own. `likelihood` and `impact` are both allowed to be blank,
because "we have written down the risk and not yet judged it" is a real and
common state, and a scale that forced a guess would fill the register with
guesses.
"""

from frappe.model.document import Document


class VMMSProjectRisk(Document):
	pass
