# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One expected output of a mission — what will exist that did not before.

A child row with no rules of its own. Kept as its own list rather than folded
into the objectives, because they answer different questions: an objective is
what the mission sets out to do, an output is what it leaves behind, and a
society reporting on a deployment afterwards reports against the second.
"""

from frappe.model.document import Document


class VMMSTOROutput(Document):
	pass
