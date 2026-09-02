# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Payment Method — one way this society will take a membership fee.

A child row on core's `National Society Settings`, and nothing more. What the
row *means* — which gateways exist, whether one of them is still active, what
happens when an applicant picks it — is `member/services/methods.py`'s and
`onerc_payments`'s; this is the record of a decision a society made.

**`gateway` is a Data field and not a Link, deliberately.** It names a record in
`onerc_payments`, an app vmmsx does not require: a society running fee-free
membership should not have to install a payment gateway, and a Link whose target
doctype is not on the site is a doctype that will not sync. So the value is a
name, the rows are written by `methods.sync()` from what the payments app
actually offers, and the field is read-only on the form — a society chooses
whether to offer a method, never what the methods are.
"""

from frappe.model.document import Document


class VMMSPaymentMethod(Document):
	pass
