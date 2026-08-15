# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One volunteer on one deployment. The roster row, and the ownership rule's evidence.

A child row with no rules of its own; the deployment's controller checks the
roster as a whole, because "the same volunteer twice" is a property of the list
rather than of any row in it.

Why a child table rather than a doctype of its own is argued in
`deployment/services/participation.py`, which is also the only place the roster
is read. Nothing else queries this table directly.
"""

from frappe.model.document import Document


class VMMSDeploymentParticipant(Document):
	pass
