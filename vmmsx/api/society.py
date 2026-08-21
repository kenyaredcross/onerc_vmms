# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Who this society is, for the mark in the corner of every screen.

The portal's lockup is the society's own logo and its own name, and both live on
core's `National Society Settings`. They were previously two content blocks —
words an administrator typed into the page a second time — which meant a society
that had uploaded its logo and named itself in settings still saw the product's
placeholder mark until somebody retyped it. Identity has one home, the same rule
`VMMS Volunteer` follows about Red Profile.

**This is the app's second `allow_guest` endpoint, and the first was
`content.surface`.** That is worth stating rather than slipping in, because
"only one endpoint in this app serves a signed-out visitor" was a property worth
having. The justification here is the same shape as the content one and rests on
*what* is returned rather than on who is asking:

* the three fields below are a society's public identity — the name it trades
  under, the short form of it, and the logo it puts on its own website. There is
  no version of them that is private, and the landing page they are drawn on is
  already public;
* the whole of `get_ui_config()` is **not** returned, and must not be. That call
  is authenticated on purpose — it carries feature toggles, validation policy and
  theme tokens, which describe how a product behaves internally. This builds its
  answer field by field from the three that are branding, so widening it is a
  visible edit to this function rather than something that follows from a change
  in core.

**Read through core's service, never off the doctype.** `get_ui_config()` is the
supported reader and its *fallbacks* are the contract — `logo_dark` falling back
to `logo` is the one that matters here, because the sidebar is navy and the
landing page is white and a society that uploaded one mark should not have a
hole on one of them.

`figures()` is the second thing here, and it is public for the same kind of
reason: how many volunteers a national society has is a number that society
publishes about itself, and the landing page used to carry it as a sentence
somebody typed. See its own docstring for what it does and does not say.
"""

import frappe

#: The register this app keeps, and the one status on it that means somebody is
#: currently a volunteer of the society. `Prospective` has not been verified yet,
#: `Suspended` is not serving and `Exited` has left, and a public figure that
#: counted any of them would be claiming a strength the society does not have.
VOLUNTEER_DOCTYPE = "VMMS Volunteer"
ACTIVE = "Active"


@frappe.whitelist(allow_guest=True)
def branding() -> dict:
	"""The society's name and marks. Three fields, and nothing else.

	Every value may be empty, and empty is ordinary: a fresh site has never had
	the settings form opened, and core's `settings()` loads a Single that was
	never saved with every field blank. The frontend draws its own placeholder
	mark in that case rather than a broken image, so nothing here invents a
	fallback that would put one society's name on another's screen.
	"""
	from onerc_core.society.services.config import get_ui_config

	society = get_ui_config()["society"]

	return {
		"name": society.get("name") or "",
		"short_name": society.get("short_name") or "",
		"logo": society.get("logo") or "",
		# Already falls back to `logo` in core. Named separately here because the
		# sidebar is dark and the landing page is not, and the caller is the only
		# one that knows which surface it is drawing on.
		"logo_dark": society.get("logo_dark") or "",
	}


@frappe.whitelist(allow_guest=True)
def figures() -> dict:
	"""Numbers about the society that the society itself would publish.

	One figure so far: how many volunteers are on the register. It replaced a
	content block — a number an administrator typed onto the landing page — and
	the reason that had to change is the reason every identity field moved to
	National Society Settings: a figure kept in a second place is a figure that
	goes stale, and this one went stale the day the society registered its next
	volunteer. Nobody edits it now, because there is nothing to edit.

	**Rounded here rather than on the page, and rounded down.** Two reasons, and
	both are about what leaves this function. A public endpoint returning an
	exact headcount publishes a fact the society did not choose to publish, and
	rounding in the browser would put that exact number in the response anyway.
	And a landing page statistic is a claim, so it has to be one the society can
	stand behind on any day: floored and suffixed, "1,200+" is true until the
	1,201st volunteer, and then it is still true.

	The step widens with the figure, so the claim keeps two or three significant
	figures at every size rather than becoming useless at one end or spuriously
	precise at the other. Below fifty there is no rounding and no "+": a society
	with eleven volunteers is better served by the truth than by "10+", and a
	statistics strip is not the place to round eleven people to ten.

	An empty string for a society with nobody on the register yet, and the strip
	drops the slot rather than announcing a zero on its own front page. That is
	the same rule an unfilled statistic already follows.
	"""
	return {"volunteers": approximate(frappe.db.count(VOLUNTEER_DOCTYPE, {"status": ACTIVE}))}


def approximate(count: int) -> str:
	"""A count as a society would print it. See `figures()` for why.

	Separated from the endpoint so the rule can be read and tested as the one
	thing it is, rather than through a whitelisted call and a dict.
	"""
	if count <= 0:
		return ""

	if count < 50:
		return f"{count:,}"

	step = 10 if count < 1_000 else 100 if count < 10_000 else 1_000

	return f"{count - count % step:,}+"
