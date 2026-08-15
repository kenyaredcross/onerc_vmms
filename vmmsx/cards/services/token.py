# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The opaque handle a card is verified by.

A card is checked by somebody who is holding it and has no account: a steward
on a gate, a branch officer at a distribution. The thing they scan therefore
has to be readable without signing in, which makes the token the entire
boundary around what a stranger can see.

**Why not the docname.** `VOL-00042` is printed on the card and follows a
sequence, so a public lookup keyed on it would let anybody walk the whole
register by counting. The token is `frappe.generate_hash` — unguessable, and
carrying no information about how many there are or what order they came in.

**Minted on first use, never rotated.** A card already in somebody's wallet has
its token printed on it, so changing the value would silently invalidate paper
that is still perfectly good. Withdrawing a card is a status change on the
record the token points at, which is what the verify page reads and reports;
the token itself stays put.

Domain-free on purpose, like everything in this package: it takes a document
and gives back a string, and it has never heard of a volunteer.
"""

import frappe

# Long enough that guessing is not a strategy, short enough to survive being
# encoded into a QR that still scans from a phone at arm's length.
TOKEN_LENGTH = 22

FIELD = "card_token"


def ensure(doc) -> str:
	"""This document's card token, minting one the first time it is asked for.

	Written with `db.set_value` rather than `doc.save()`, deliberately: minting a
	token is not a change to the record anybody made, and putting it through the
	document's own save would fire `on_update`, re-run whatever the domain hangs
	off it, and bump `modified` on a volunteer nobody touched. It would also need
	whatever permission the caller happens to lack.

	Idempotent by construction: a document that has one gets it back.
	"""
	existing = doc.get(FIELD)

	if existing:
		return existing

	token = frappe.generate_hash(length=TOKEN_LENGTH)

	# Elevated, and the justification is that this writes nothing a user chose.
	# It is a derived identifier on a record the caller has already been allowed
	# to reach, and the alternative is refusing a card to the person it belongs
	# to because they hold no write permission on their own volunteer record.
	frappe.db.set_value(doc.doctype, doc.name, FIELD, token, update_modified=False)
	doc.set(FIELD, token)

	return token


def holder(token: str, doctypes: tuple[str, ...]) -> tuple[str, str] | None:
	"""Which record this token belongs to, as `(doctype, name)`, or None.

	The caller names the doctypes it is willing to resolve, so this is never a
	way to reach an arbitrary record that happens to have grown the same field.

	A blank token resolves to nothing rather than to the first row with an empty
	column, which is the failure that would turn "no card" into "somebody's
	card".
	"""
	token = (token or "").strip()

	if not token:
		return None

	for doctype in doctypes:
		if not frappe.db.exists("DocType", doctype):
			continue

		name = frappe.db.get_value(doctype, {FIELD: token}, "name")

		if name:
			return doctype, name

	return None
