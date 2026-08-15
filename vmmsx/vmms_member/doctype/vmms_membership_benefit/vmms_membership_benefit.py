# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Membership Benefit — one entitlement under a membership type.

A child row and nothing more. Validation that spans the table (a benefit key
appearing twice) belongs to the parent type, which is the only thing that can
see the whole list.
"""

from frappe.model.document import Document


class VMMSMembershipBenefit(Document):
	pass
