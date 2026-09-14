# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Put the shipped photographs onto sites that already exist.

A fresh install needs none of this: `default_content.DEFAULT_IMAGES` is read by
`_block()`, so `seed()` inserts each slot with its picture already on it and the
first page anybody opens is a finished one. This is for the sites that were
installed before that was true, where the nine photograph slots were created
empty and `seed()` — which only ever creates what is missing — will never go
back and fill them.

**Two jobs, and the order between them is the point.**

1. *Repoint what the old society seeds wrote.* Until `85fcd86` the pictures were
   set by `vmmsx/seed/kenya_content.py` from `public/images/seed_kenya/`. That
   folder is now `public/images/defaults/` and five of the eight files lost the
   county in their name, so a site seeded back then holds eight paths that now
   404 — a broken page that raises nothing, which is the worst kind. The map
   below is the rename, and nothing but the path is touched: a society that
   wrote its own alt text or credit against that picture keeps both.

2. *Fill what is still empty.* Only where `image` is blank, and only for the
   nine keys the product ships a picture for. A slot holding anything at all is
   somebody's decision and is left alone.

**A one-time patch rather than a step in `install_defaults()`**, which is the
one design choice here worth defending. `install_defaults()` runs on every
migrate, and an image backfill wired into it would re-fill a slot a society had
deliberately cleared — every deploy, for ever, with no way to say no. `relabel`
gets to run every time because it matches the exact string it shipped and can
tell "untouched" from "changed"; an empty image field cannot tell "never filled"
from "emptied on purpose". So this runs once, on the sites that predate the
change, and never again. Sites created afterwards get the pictures from `seed()`
and are not in scope.
"""

import frappe

from vmmsx.content.seeds import default_content

BLOCK_DOCTYPE = "VMMS Content Block"

OLD_BASE = "/assets/vmmsx/images/seed_kenya"

#: `{old filename: new filename}` for the eight pictures the Kenya seed used to
#: write. Three kept their names because they never named a place.
RENAMED = {
	"outreach-lamu.jpg": "community-outreach.jpg",
	"field-turkana.jpg": "community-gathering.jpg",
	"ambulance-coast.jpg": "ambulance.jpg",
	"clinic-turkana.jpg": "health-clinic.jpg",
	"firstaid-sagana.jpg": "first-aid-training.jpg",
	"community-session.jpg": "community-session.jpg",
	"training-manual.jpg": "training-manual.jpg",
	"lake-shore.jpg": "lake-shore.jpg",
}


def execute():
	repoint_the_old_seed_paths()
	fill_the_empty_slots()


def repoint_the_old_seed_paths() -> list[str]:
	"""Move a picture that still points into `seed_kenya/` to where it now lives."""
	moved = []

	for name, key, image in frappe.get_all(
		BLOCK_DOCTYPE,
		filters={"image": ["like", f"{OLD_BASE}/%"]},
		fields=["name", "content_key", "image"],
		as_list=True,
	):
		filename = image.rsplit("/", 1)[-1]
		replacement = RENAMED.get(filename)

		if not replacement:
			# A file the Kenya seed never shipped. Nothing here knows where it
			# went, and guessing would swap one broken path for another.
			continue

		frappe.db.set_value(
			BLOCK_DOCTYPE, name, "image", f"{default_content.IMAGE_BASE}/{replacement}"
		)
		moved.append(key)

	return moved


def fill_the_empty_slots() -> list[str]:
	"""Give a blank photograph slot the picture the product now ships for it."""
	filled = []

	for key, (filename, alt, credit) in default_content.DEFAULT_IMAGES.items():
		name = frappe.db.get_value(BLOCK_DOCTYPE, {"content_key": key}, "name")

		if not name:
			# Not on this site yet. `install_defaults()` runs after this on the
			# same migrate and creates it with the picture already on it.
			continue

		if (frappe.db.get_value(BLOCK_DOCTYPE, name, "image") or "").strip():
			continue

		frappe.db.set_value(
			BLOCK_DOCTYPE,
			name,
			{
				"image": f"{default_content.IMAGE_BASE}/{filename}",
				"image_alt": alt,
				"image_credit": credit,
			},
		)
		filled.append(key)

	return filled
