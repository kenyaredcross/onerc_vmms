# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Put the FAQ in the top navigation, on a site that shipped before it existed.

The public answers now have a page — `/portal/faq`, drawn from core's `FAQ` —
and the shipped navigation defaults point the fifth slot at it. That default
only reaches a site that has never been seeded: `content/services/blocks.py::
seed` never overwrites, deliberately, because it runs on every migrate and a
seed that refreshed defaults would revert a society's own wording on every
deploy.

So this fills the slot once, and only where filling it destroys nothing:

* the block must exist (a site that has never been seeded gets the default from
  `seed()` instead, and this does nothing);
* its **text and its link must both be empty**. That is the shipped state of the
  fifth slot and the state of a slot a society has deliberately cleared — and
  the two are indistinguishable, which is why this runs once by name rather than
  on every migrate. A society that empties it again after this keeps it empty.

Nothing is edited. A slot carrying a society's own word for anything is left
exactly as it is, whatever it points at.
"""

import frappe

BLOCK_DOCTYPE = "VMMS Content Block"

SLOT = "landing.nav.item5"
TEXT = "Help"
HREF = "/portal/faq"


def execute():
	block = frappe.db.get_value(
		BLOCK_DOCTYPE, SLOT, ["name", "text_value", "link_href"], as_dict=True
	)

	if not block:
		return

	if (block.text_value or "").strip() or (block.link_href or "").strip():
		return

	frappe.db.set_value(BLOCK_DOCTYPE, block.name, {"text_value": TEXT, "link_href": HREF})
