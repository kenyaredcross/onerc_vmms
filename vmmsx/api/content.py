# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The editable-wording endpoints.

Three of them, and the shape of each is the security argument for it:

- `surface(surface)` reads one screen's wording. It is the only `allow_guest`
  endpoint in this app, because the guest landing page has to render before
  anybody has signed in. What it will serve a guest is decided by the
  `is_public` flag on the surface record, not by anything written here, so
  opening a screen to the public is an administrator's decision that leaves an
  audit trail on a document.

- `update_block(...)` writes one slot. It names no role and performs no check of
  its own: `write_block` saves through the ordinary permission layer, so who may
  reword a page is a Role question the framework answers. A caller without write
  permission on VMMS Content Block gets the framework's own refusal.

- `attach_image(...)` is not here. Uploading goes through Frappe's own
  `upload_file`, and the resulting file URL comes back to `update_block` like any
  other value. Writing a second upload endpoint would be writing a second file
  validator, and the framework's is the one that gets patched.

`can_edit` travels with the read rather than being a fourth endpoint, because
the frontend needs it at exactly the moment it renders the page and asking twice
would mean a page that flickers a pencil on or off after it has drawn.
"""

import frappe
from frappe import _

from vmmsx.content.services import blocks as block_service


@frappe.whitelist(allow_guest=True)
def surface(surface: str) -> dict:
	"""One or more screens' wording, plus whether this caller may change it.

	`surface` is one key, or several separated by commas. Several because nearly
	every page needs its own slots *and* the shared chrome, and two round trips
	before the hero paints is two round trips too many. The blocks come back
	merged into one dictionary, which is safe because a content key is unique
	across the whole site rather than within a surface.

	A surface that is not marked public is refused to a signed-out visitor with
	the same message it gives for one that does not exist. That is deliberate:
	the alternative tells somebody probing for surface keys which ones they
	guessed right. **Every** named surface must pass, so a public key cannot be
	used to smuggle a private one alongside it.
	"""
	keys = [key.strip() for key in (surface or "").split(",") if key.strip()]

	if not keys:
		frappe.throw(_("No surface was named."), frappe.ValidationError, title=_("Not Published"))

	is_guest = frappe.session.user == "Guest"
	blocks = {}

	for key in keys:
		if is_guest and not block_service.is_public(key):
			frappe.throw(
				_("No page content is published under {0}.").format(key),
				frappe.PermissionError,
				title=_("Not Published"),
			)

		if not is_guest and not frappe.db.exists(block_service.SURFACE_DOCTYPE, key):
			frappe.throw(
				_("No page content is published under {0}.").format(key),
				frappe.DoesNotExistError,
				title=_("Not Published"),
			)

		blocks.update(block_service.surface_dto(key))

	return {
		"surface": ",".join(keys),
		"blocks": blocks,
		# The pencil is drawn from this and nothing else. It is a convenience for
		# the interface, not the check: the write endpoint re-asks the permission
		# layer on every save, so a caller who forges it gains nothing.
		"can_edit": bool(
			frappe.has_permission(block_service.BLOCK_DOCTYPE, ptype="write", user=frappe.session.user)
		),
	}


@frappe.whitelist()
def catalogue() -> dict:
	"""Every editable slot on the site, grouped by surface. Never for guests.

	The bulk editor's list. Deliberately a separate endpoint from `surface`
	rather than a flag on it: `surface` is the guest-readable one and is called
	on every page load, and an argument that could turn it into "give me
	everything" is an argument somebody will eventually pass from a signed-out
	browser.

	Read permission on the block doctype is the gate, asked of the framework.
	Somebody who may read but not write gets the list and a refusal on save,
	which is the right shape for a coordinator looking up what a page says.
	"""
	frappe.has_permission(block_service.BLOCK_DOCTYPE, ptype="read", throw=True)

	surfaces = frappe.get_all(
		block_service.SURFACE_DOCTYPE,
		fields=["name", "surface_name", "is_public"],
		order_by="surface_name asc",
	)

	return {
		"can_edit": bool(
			frappe.has_permission(block_service.BLOCK_DOCTYPE, ptype="write", user=frappe.session.user)
		),
		"surfaces": [
			{
				"key": row["name"],
				"label": row["surface_name"],
				"is_public": bool(row["is_public"]),
				"blocks": list(block_service.surface_dto(row["name"]).values()),
			}
			for row in surfaces
		],
	}


@frappe.whitelist()
def update_block(
	content_key: str,
	text_value: str | None = None,
	link_href: str | None = None,
	image: str | None = None,
	image_alt: str | None = None,
	image_credit: str | None = None,
) -> dict:
	"""Change one slot, and return it as the page will now render it.

	Every argument but the key is optional and **omitted means untouched**, which
	is what lets the pencil beside a caption send only a caption. Clearing a slot
	is passing the empty string, which is a different thing from not passing it
	at all and is treated as one.
	"""
	values = {
		"text_value": text_value,
		"link_href": link_href,
		"image": image,
		"image_alt": image_alt,
		"image_credit": image_credit,
	}

	return block_service.write_block(
		content_key, **{field: value for field, value in values.items() if value is not None}
	)
