# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One entry in a deployment's feed.

A child row with no rules of its own, and the sibling of `VMMS Task Update`
next door. What the row means is decided where it is written:
`deployment/services/feed.py` stamps the author and the time from the session
rather than from the form, so a feed cannot be made to say somebody said
something they did not.

`entry_type` is display only. The deployment's own status is the state machine,
and nothing branches on this value; it exists so that an account of a deployment
reads as one.
"""

from frappe.model.document import Document


class VMMSDeploymentUpdate(Document):
	pass
