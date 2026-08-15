# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Content Surface — one screen's worth of editable wording.

A surface is a grouping and a read boundary, and nothing else. The frontend asks
for one by key and renders whatever blocks come back; no source file branches on
which surface it got, the same way no source file branches on a template
category. A society may add surfaces of its own.

`is_public` is the entire guest read rule. `vmmsx/api/content.py` serves a
signed-out visitor only a surface flagged here, so opening the door on a new
screen is a settings change an administrator can see and audit, rather than an
`allow_guest` somebody has to find in a source file.
"""

from frappe.model.document import Document


class VMMSContentSurface(Document):
	pass
