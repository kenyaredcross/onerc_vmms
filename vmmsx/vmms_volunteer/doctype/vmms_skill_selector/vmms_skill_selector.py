# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The row shape `Table MultiSelect` needs: one Link, nothing else.

Exists only so `VMMS Volunteer Application.skills` can be a multi-select of
`VMMS Skill`. Holds no logic of its own.
"""

from frappe.model.document import Document


class VMMSSkillSelector(Document):
	pass
