# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One certification a Terms of Reference asks for, and how hard it asks.

A child row with no rules of its own. What the row means is decided where it is
read: `deployment/services/matching.py` treats a mandatory row as a hard filter
and a non-mandatory one as a preference that ranks. Keeping the meaning at the
point of use is what lets a society change a requirement from desirable to
required without anything being migrated.
"""

from frappe.model.document import Document


class VMMSDeploymentRequirement(Document):
	pass
