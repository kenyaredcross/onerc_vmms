# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One person a batch is for, and what happened when it was generated.

`result` is the whole point of this row existing rather than the batch holding a
plain list of names. Generating forty tasks will not produce forty tasks: some
of those volunteers already hold one for this batch, one has been suspended
since the list was drawn up, and one will fail for a reason nobody predicted.
Recording the outcome per person is what lets the batch report honestly and what
lets a retry pick up only the rows that are still unresolved.

Blank means "not tried yet", which is exactly what a retry looks for.
"""

from frappe.model.document import Document


class VMMSTaskBatchVolunteer(Document):
	pass
