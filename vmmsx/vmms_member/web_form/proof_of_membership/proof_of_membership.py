# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""No page context of its own — same shape as register_as_a_member.py.

The form is the whole of it. Everything the submission needs happens server
side, on the document: `VMMSMembership.before_insert` for the two-doctype
write, `validate_source` for the routed-only and attachment guardrails, and
`membership_service.submit` for putting it into motion.
"""


def get_context(context):
	pass
