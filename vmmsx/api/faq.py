# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The society's answers to the questions it keeps being asked.

**Not this app's content, and deliberately not stored here.** `FAQ` and `FAQ
Category` are core's doctypes and core already serves them —
`onerc_core.api.faq` has the readers, the published filter and the vote counter.
A society writes its answers once and every product on the site shows the same
ones. So this module holds no questions, no categories and no wording, and every
row below comes out of a call into core.

**Then why does it exist at all.** Three things the page needs that core's flat
list does not give it, and none of them is content:

1. **Grouping.** Core returns categories and questions as two lists. A page that
   fetched both and joined them in the browser would be doing on every visit,
   in every client, what one pass here does once.
2. **A closed shape.** Core's reader hands back whatever fields it selects, and
   a field added to `FAQ` next year would start appearing in a vmmsx payload
   without anybody deciding it should. The DTO below is built field by field,
   the same discipline `member/services/payment.py::_TRANSACTION_FIELDS` keeps
   for the payments app's records.
3. **Absence.** A core older than the FAQ module, or a society that has written
   nothing, has to produce an empty page rather than a traceback — this is a
   public address, reachable by somebody who has never signed in.

**Guest-readable, like the locations directory and the society's branding.**
Somebody reading the answers has not signed in and very often is reading in
order to decide whether to. The boundary is core's own `status == "Published"`,
which a society sets on each record; nothing here decides what is shown.
"""

import frappe

FAQ_DOCTYPE = "FAQ"
CATEGORY_DOCTYPE = "FAQ Category"

# Everything with no category of its own goes here. A society that has never
# made a category still has a page that reads as a page rather than as a list
# with an empty heading over it.
UNCATEGORISED = ""


def _available() -> bool:
	"""Does this site's core carry the FAQ module?

	Asked of the doctype rather than by catching an import error, and for the
	reason the payments seam gives: an answer that can only be had by raising
	cannot be asked at render time on a public page.
	"""
	return frappe.db.table_exists(f"tab{FAQ_DOCTYPE}")


@frappe.whitelist(allow_guest=True)
def published(search: str | None = None) -> dict:
	"""Every published answer, in the society's own categories and order.

	`search` is passed straight through to core's reader, which matches on the
	question and the answer. Empty means everything.
	"""
	if not _available():
		return {"categories": [], "count": 0}

	from onerc_core.api.faq import get_faq_categories, get_faq_list

	entries = get_faq_list(search=search) or []
	# Read whether or not there are entries: a society that has written
	# categories and no answers yet gets a page saying so rather than nothing.
	named = {row["name"]: row for row in (get_faq_categories() or [])}

	# The society's own order — `sort_order`, then the category's name — with
	# anything uncategorised last, because a heading nobody wrote should not sit
	# above the ones they did.
	buckets: dict[str, list] = {}

	for entry in entries:
		buckets.setdefault(entry.get("category") or UNCATEGORISED, []).append(_answer(entry))

	categories = [
		{
			"name": key,
			"label": named[key].get("category_name") or key,
			"description": named[key].get("description") or "",
			"questions": buckets.get(key, []),
		}
		for key in named
		if buckets.get(key)
	]

	loose = buckets.get(UNCATEGORISED) or []

	if loose:
		categories.append(
			{"name": UNCATEGORISED, "label": "", "description": "", "questions": loose}
		)

	return {"categories": categories, "count": len(entries)}


def _answer(entry: dict) -> dict:
	"""One published answer, built field by field.

	`answer` is a Text Editor field written by whoever wrote the FAQ and is
	rendered as markup on the page, so it is sanitised here rather than trusted
	in the browser — the same rule `content/services/blocks.py` applies to a
	content block, and for the same reason: the guarantee belongs on the server.
	"""
	return {
		"name": entry.get("name"),
		"question": entry.get("question") or "",
		"answer": frappe.utils.sanitize_html(entry.get("answer") or ""),
	}
