# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Somebody a coordinator has chosen to ask, waiting for the deployment's send time.

Not an assignment yet, on purpose: the volunteer is told nothing and the
roster does not count them until `scheduling.send_due` raises the ask at
`VMMS Deployment.send_on`. Removing a row before then is simply not asking.
"""

from frappe.model.document import Document


class VMMSScheduledAsk(Document):
	pass
