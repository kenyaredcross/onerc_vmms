# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One thing a programme's plan takes for granted.

A child row on ERPNext's `Project`, added by vmmsx. `still_holds` is why this is
a row and not a bullet in a notes field: an assumption that stopped being true
is the most useful thing on a plan that has stopped working, and deleting the
row would take that away exactly when somebody needs it.
"""

from frappe.model.document import Document


class VMMSProjectAssumption(Document):
	pass
