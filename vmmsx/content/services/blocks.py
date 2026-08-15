# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Reading and writing the editable wording of a screen.

The whole public surface is three functions, and all three are idempotent:

- `surface_dto(surface)` — every block of one screen, as an explicit dict keyed
  by `content_key`. This is what a page renders from.
- `write_block(content_key, **values)` — change one slot. Only the fields named
  in the call are touched, so an editor changing a caption cannot blank the
  photograph beside it by omitting it.
- `seed(rows)` — create the blocks a screen needs, and *never overwrite* one
  that already exists. That is what lets the default wording ship in code, the
  Kenya seed layer its own on top, and both be re-run on every migrate without
  reverting a sentence somebody in the society has since rewritten.

The DTO is built field by field, on purpose. Returning the documents would put
`owner`, `modified_by` and every future field of the doctype into a public,
guest-readable response, and turn a schema change into an API change.
"""

import frappe

BLOCK_DOCTYPE = "VMMS Content Block"
SURFACE_DOCTYPE = "VMMS Content Surface"

# The fields an editor may write, and the only ones `write_block` will touch.
# A field absent from this set is not editable from the frontend however the
# request is shaped, which is why the write endpoint can take loose keyword
# arguments without that being a way into the rest of the document.
EDITABLE_FIELDS = frozenset({"text_value", "link_href", "image", "image_alt", "image_credit"})


def block_dto(row: dict) -> dict:
	"""One block, as the frontend sees it.

	`None` is normalised to the empty string for the text fields so a component
	can render what it is given without every one of them testing for null, and
	`image` is left as `None` when unset because "no picture" and "a picture
	whose path is empty" are the same thing to a renderer but different to a
	human reading the payload.
	"""
	return {
		"key": row["name"],
		"label": row.get("label") or "",
		"text": row.get("text_value") or "",
		"href": row.get("link_href") or "",
		"image": row.get("image") or None,
		"image_alt": row.get("image_alt") or "",
		"image_credit": row.get("image_credit") or "",
	}


def surface_dto(surface: str) -> dict:
	"""Every block of one screen, keyed by content key.

	A dict rather than a list because the caller always wants one named slot at
	a time: a component asks for `landing.hero.headline` and renders it. Order
	is the page's business, and the page is code.
	"""
	rows = frappe.get_all(
		BLOCK_DOCTYPE,
		filters={"surface": surface},
		fields=[
			"name",
			"label",
			"text_value",
			"link_href",
			"image",
			"image_alt",
			"image_credit",
		],
		order_by="sequence asc, name asc",
		limit_page_length=0,
	)

	return {row["name"]: block_dto(row) for row in rows}


def is_public(surface: str) -> bool:
	"""Whether a signed-out visitor may read this surface.

	A surface that does not exist is not public. Returning False rather than
	raising keeps the guest endpoint from confirming which surface keys exist to
	somebody guessing at them.
	"""
	return bool(frappe.db.get_value(SURFACE_DOCTYPE, surface, "is_public"))


def write_block(content_key: str, **values) -> dict:
	"""Change one slot, and return it as the frontend will now see it.

	Ordinary permissions: `frappe.get_doc(...).save()` runs the write through the
	same check a desk user gets, so who may edit the wording is a Role question
	answered by the permission layer, not by anything invented here.

	Only the fields in `EDITABLE_FIELDS` are considered, and only those actually
	passed are assigned. Partial updates are the normal case: the pencil beside a
	caption sends a caption.
	"""
	block = frappe.get_doc(BLOCK_DOCTYPE, content_key)

	for field, value in values.items():
		if field not in EDITABLE_FIELDS:
			continue
		block.set(field, value)

	block.save()

	return block_dto(
		{
			"name": block.name,
			"label": block.label,
			"text_value": block.text_value,
			"link_href": block.link_href,
			"image": block.image,
			"image_alt": block.image_alt,
			"image_credit": block.image_credit,
		}
	)


def ensure_surface(surface_key: str, surface_name: str, description: str, public: bool) -> None:
	"""Create a surface if the site has none by that key. Never edits one."""
	if frappe.db.exists(SURFACE_DOCTYPE, surface_key):
		return

	frappe.get_doc(
		{
			"doctype": SURFACE_DOCTYPE,
			"surface_key": surface_key,
			"surface_name": surface_name,
			"description": description,
			"is_public": 1 if public else 0,
		}
	).insert(ignore_permissions=True)  # A patch installing configuration, running as Administrator.


def install_defaults() -> dict:
	"""Ensure every shipped surface and slot exists. Idempotent, and additive only.

	**Wired into `after_migrate`, not into a patch, and the difference is the
	whole point.** A Frappe patch runs once per site by name, so
	`setup_content_module` seeded the slots that existed on the day a site first
	migrated and could never seed another. Every slot added by a later release
	was therefore missing on every existing site, and the screen using it fell
	back to its hardcoded default with no pencil on it: uneditable wording, which
	is exactly the state this module exists to prevent. The bug was invisible
	because a fallback renders perfectly.

	It is safe to run on every migrate because `seed()` never overwrites and
	`ensure_surface()` never edits. A society that has rewritten its home page
	keeps every word of it; only slots with no record at all are created. That
	property is what makes "run it always" the correct wiring rather than a risk,
	and it is why this is a service call rather than a second patch nobody would
	remember to add next time.
	"""
	from vmmsx.content.seeds import default_content

	for key, name, description, public in default_content.SURFACES:
		ensure_surface(key, name, description, public)

	return {
		**seed(default_content.blocks()),
		"retired": retire(default_content.RETIRED),
		"relinked": relink(default_content.DEAD_LINKS),
		"relabelled": relabel(default_content.RELABELLED),
	}


def relabel(replacements: dict[str, tuple[str, str]]) -> list[str]:
	"""Update wording this app shipped, where the society has not changed it.

	The same narrow exception `relink` is, and narrower: it rewrites a block's
	text only when it still holds the exact words this app seeded, so a society
	that has renamed a button keeps its own name for it. What it is for is a
	label that stopped being true — a button reading "Get tickets" that no longer
	takes anybody anywhere near a ticket.
	"""
	changed = []

	for key, (was, now) in replacements.items():
		name = frappe.db.get_value(BLOCK_DOCTYPE, {"content_key": key}, "name")

		if not name:
			continue

		block = frappe.get_doc(BLOCK_DOCTYPE, name)

		if (block.text_value or "").strip() != was:
			continue

		block.text_value = now
		block.save(ignore_permissions=True)
		changed.append(key)

	return changed


def relink(replacements: dict[str, str | None]) -> list[str]:
	"""Repoint links this app shipped pointing at nothing.

	The one place `install_defaults` is not purely additive, and it is narrow
	enough to say exactly why. `seed()` never overwrites because a society's
	wording is its own — but a *destination* that goes nowhere was never a
	society's choice, it was this app's mistake, and leaving it alone means
	leaving a visitor clicking a link that does nothing.

	So this rewrites an `href` only where it still holds the exact broken value
	this app shipped. A society that has pointed the link somewhere of its own
	has a different value and is not touched, and the visible text is never
	changed — only where the link goes.

	A replacement of `None` clears the block's text as well, which is how a link
	with no destination at all leaves the navigation: the seed's own note says an
	empty item is dropped.
	"""
	relinked = []

	for href, replacement in replacements.items():
		for name in frappe.get_all(BLOCK_DOCTYPE, filters={"link_href": href}, pluck="name"):
			doc = frappe.get_doc(BLOCK_DOCTYPE, name)
			doc.link_href = replacement or ""

			if replacement is None:
				doc.text_value = ""

			doc.save(ignore_permissions=True)
			relinked.append(doc.content_key)

	return relinked


def retire(keys) -> int:
	"""Delete slots the product no longer draws. Returns how many went.

	**The one thing in this module that removes rather than adds**, and it is
	narrow on purpose: a key only appears in `RETIRED` when the screen that read
	it is gone, so the block is a row an administrator can still edit that
	changes nothing on any page. Leaving those behind turns the content
	catalogue into a list of slots that may or may not do something, which is
	worse than either having them or not.

	It is not a general "sync to the shipped list": a key an administrator added
	themselves, or one from a release this code has not heard of, is left
	strictly alone. Only what is named goes.
	"""
	gone = 0

	# The block's docname *is* its content key, which is what makes this a
	# lookup rather than a query.
	for key in keys:
		if not frappe.db.exists(BLOCK_DOCTYPE, key):
			continue

		frappe.delete_doc(BLOCK_DOCTYPE, key, force=True, ignore_permissions=True)
		gone += 1

	return gone


def seed(rows) -> dict:
	"""Create missing blocks. Returns counts, and overwrites nothing.

	`rows` is an iterable of dicts carrying at least `content_key`, `label` and
	`surface`. Anything else in the dict is passed through to the document, so a
	seed may set text, an image, a credit, or nothing at all and leave the slot
	for the society to fill.

	**Existing blocks are left exactly as they are.** This runs on every migrate,
	and a seed that refreshed the defaults would silently revert an
	administrator's rewording every time somebody deployed.
	"""
	created = 0
	existed = 0

	for row in rows:
		key = row["content_key"]

		if frappe.db.exists(BLOCK_DOCTYPE, key):
			existed += 1
			continue

		frappe.get_doc({"doctype": BLOCK_DOCTYPE, **row}).insert(
			ignore_permissions=True
		)  # A patch installing configuration, running as Administrator.
		created += 1

	return {"created": created, "existed": existed}


def overwrite(rows) -> dict:
	"""Write blocks whether or not they exist. For a demo seed, not for migrate.

	The difference from `seed` is the whole reason both exist. `seed` ships the
	product's neutral defaults and must never clobber a society's words;
	`overwrite` is what a worked example like the Kenya seed uses when somebody
	runs it deliberately to *get* that example, and expects the page to look like
	the example afterwards.
	"""
	written = 0

	for row in rows:
		key = row["content_key"]

		if frappe.db.exists(BLOCK_DOCTYPE, key):
			block = frappe.get_doc(BLOCK_DOCTYPE, key)
			for field, value in row.items():
				if field == "content_key":
					continue
				block.set(field, value)
			block.save(ignore_permissions=True)  # Deliberate seed run, as Administrator.
		else:
			frappe.get_doc({"doctype": BLOCK_DOCTYPE, **row}).insert(ignore_permissions=True)

		written += 1

	return {"written": written}
