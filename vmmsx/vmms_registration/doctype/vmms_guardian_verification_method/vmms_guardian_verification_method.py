# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Guardian Verification Method — how a society checks a parent's consent.

A vocabulary, the same shape as `VMMS Skill` and `VMMS Motivation`: a seeded
starting set a society then edits, autonamed from a stable key so that
relabelling one never rewrites the consents already recorded under it.

**Nothing in this app branches on a method.** A branch that verifies consent by
sending somebody to the house, and one that accepts a stamped form from a
school, are the same shape to every line of code here: a reviewer ticks
`is_verified` on `VMMS Guardian Consent` and this row records what they did to
earn the tick. That is the same rule every other vocabulary in this product
follows, and `approvals/tests/test_no_stage_branching.py` exists because it is
the rule most easily broken by accident.
"""

from frappe.model.document import Document


class VMMSGuardianVerificationMethod(Document):
	pass
