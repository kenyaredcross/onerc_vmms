# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Putting the shipped card designs on the site, once, and never again.

**`after_migrate` rather than a patch, and the reason is the one the welcome
email states.** A patch runs once per site by name, so a card design shipped
after a site had already migrated would never reach it, and a society that
installed vmmsx before cards existed would have the endpoints and no template
to render. Running on every migrate and creating only what is absent reaches
every site exactly once, whenever it happens to catch up.

**Both writes are additive, and that is the whole safety story.** A record is
created when the site has none by that key and is *never* edited again, so a
society that has rewritten its card — different wording, its own colours, a
line about where to return a lost one — survives every deploy afterwards. Same
rule, same reason, as `content/services/blocks.py::seed` and
`notifications/services/welcome.py::install`.

**One body, two records.** A volunteer card and a member card differ in what is
written on them rather than in what they are, so both point at the same shipped
markup and the template guards the rows only one of them has. They are two
records rather than one because a society editing its member card must not
silently redesign its volunteer card, which is exactly what sharing a record
would mean.
"""

from pathlib import Path

import frappe

from vmmsx.member.services import card as member_card
from vmmsx.volunteer.services import card as volunteer_card

TEMPLATE_DOCTYPE = "VMMS Template"
CATEGORY_DOCTYPE = "VMMS Template Category"

CATEGORY_KEY = "card"
SEED_DIR = Path(frappe.get_app_path("vmmsx")) / "templating" / "seeds"
SEED_FILE = "identity_card.html"

# What each shipped card is called and what it renders for. The wording inside
# them is not here: it is in the file above, and after the first migrate it is
# in a record on the site.
CARDS = (
	(volunteer_card.TEMPLATE_KEY, "Volunteer Card", "Volunteer Card"),
	(member_card.TEMPLATE_KEY, "Member Card", "Member Card"),
)

CONTEXT_KEYS = (
	"society_name, society_logo, card_kind, holder_name, holder_photo, record_id, status,"
	" geo_path, joined_on, valid_from, valid_to, membership_type, issued_on, verify_url,"
	" verify_qr, card_token"
)


def install() -> dict:
	"""Create the card category and the two shipped cards, if they are missing."""
	created = []

	if not frappe.db.exists(CATEGORY_DOCTYPE, CATEGORY_KEY):
		frappe.get_doc(
			{
				"doctype": CATEGORY_DOCTYPE,
				"category_key": CATEGORY_KEY,
				"category_name": "Card",
				"description": (
					"The pocket-sized proof of standing a volunteer or member carries."
					" Nothing in the code branches on this category."
				),
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
		created.append(CATEGORY_KEY)

	body = (SEED_DIR / SEED_FILE).read_text()

	for key, name, subject in CARDS:
		if frappe.db.exists(TEMPLATE_DOCTYPE, key):
			continue

		frappe.get_doc(
			{
				"doctype": TEMPLATE_DOCTYPE,
				"template_key": key,
				"template_name": name,
				"template_category": CATEGORY_KEY,
				"subject": subject,
				"body": body,
				"output_format": "html",
				"is_active": 1,
				"description": (
					f"The default {name.lower()}. Context keys: {CONTEXT_KEYS}."
					" Edit freely: nothing in the code depends on this wording or these"
					" colours, and a row whose value is empty renders itself away."
				),
			}
		).insert(ignore_permissions=True)
		created.append(key)

	return {"created": created}


def reinstall() -> dict:
	"""Replace the shipped card bodies with the current default. **Destructive.**

	`install()` runs on every migrate and never touches a template that already
	exists, which is what stops a deploy silently reverting a society's redesigned
	card — the same rule `content/services/blocks.py::seed` keeps for a rewritten
	home page. That rule is right, and it has one consequence: a genuine
	improvement to the shipped card never reaches a site that has already been
	migrated once.

	This is the deliberate way through, and it is a bench command rather than
	anything that runs on its own:

	    bench --site <site> execute vmmsx.cards.services.templates.reinstall

	**It discards whatever the card body currently says.** A society that has
	edited its card will lose those edits, which is why nothing calls this
	automatically and why it reports exactly which templates it replaced. Only
	the body is replaced; the category, the name and `is_active` are left as they
	are, so a society that retired one of the two cards stays retired.

	`install()` is still called first, so a site missing a card gets one rather
	than being silently skipped by a function whose name suggests it would.
	"""
	summary = install()
	body = (SEED_DIR / SEED_FILE).read_text()
	replaced = []

	for key, _name, _subject in CARDS:
		if not frappe.db.exists(TEMPLATE_DOCTYPE, key):
			continue

		template = frappe.get_doc(TEMPLATE_DOCTYPE, key)

		if template.body == body:
			# Already the shipped default. Reported as untouched rather than
			# rewritten, so running this twice says something honest the second
			# time.
			continue

		template.body = body
		template.save(ignore_permissions=True)
		replaced.append(key)

	return {**summary, "replaced": replaced}
