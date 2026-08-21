# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS TOR Methodology — a society's own register of ways it does the work.

Configuration vocabulary, on the same footing as `VMMS Skill` and
`VMMS Certification Type`: keyed by a stable business key rather than an opaque
series, because a terms of reference points at one and relabelling the method
next year must not rewrite the documents that cited it this year.

**No methodology name appears anywhere in this app's source.** Which methods
exist is entirely a society's answer, which is what lets one national society
work in household surveys and another in mass mobilisation without either of
them needing a code change.
"""

from frappe.model.document import Document


class VMMSTORMethodology(Document):
	pass
