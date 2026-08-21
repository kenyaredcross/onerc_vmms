# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Kenya Red Cross wording and photography for the public landing page.

Part of the Kenya seed, and here for the same reason the rest of it is: the
product ships society-neutral defaults in `content/seeds/default_content.py`,
and every sentence below that says "Kenya", "county" or "KES" would break the
rule that no source file outside `vmmsx/seed/` names them. A second society is a
second seed and no diff at all.

**This one overwrites.** `blocks.seed()` is the migrate-safe call that never
touches an existing slot; this uses `blocks.overwrite()` because somebody who
runs the Kenya seed deliberately is asking for the Kenya page and would not
thank us for a half-Kenyan one. That is the difference between the two functions
and the reason both exist.

**About the photographs.** They ship in `public/images/seed_kenya/` and are
third-party pictures under their own licences, which is why every one of them
carries its credit into an editable field rather than having it burned into a
template. They are here so a demo looks like something on the first run. A
society putting this into real use replaces them with its own, and the credit
field empties with them.
"""

from vmmsx.content.services import blocks as block_service

# Served by Frappe from `sites/assets/vmmsx` -> `vmmsx/public`.
IMAGE_BASE = "/assets/vmmsx/images/seed_kenya"


def _image(filename: str) -> str:
	return f"{IMAGE_BASE}/{filename}"


# (content_key, text, image, alt, credit)
#
# A None image leaves whatever is there; the empty string clears it. Most rows
# set one or the other rather than both, because most slots are either words or
# a picture.
COPY = (
	# No brand row. The lockup is the society's own logo and name, read live from
	# National Society Settings; a seed writing them onto the page as words would
	# be a second copy of what core already holds.
	# --- hero -------------------------------------------------------------
	("landing.hero.eyebrow", "KENYA RED CROSS SOCIETY", None, None, None),
	("landing.hero.headline", "Show up for Kenya.", None, None, None),
	(
		"landing.hero.body",
		"One profile for volunteering, training, deployments and membership, across all 47 county branches.",
		None,
		None,
		None,
	),
	(
		"landing.hero.image",
		None,
		_image("outreach-lamu.jpg"),
		"A community health volunteer shares a moment with children in Lamu County",
		"Lamu County · Neil Thomas / Safari Doctors · CC BY-SA 4.0",
	),
	# --- the four cards ---------------------------------------------------
	("landing.card1.image", None, _image("firstaid-sagana.jpg"), "A first aid training session", ""),
	("landing.card2.image", None, _image("clinic-turkana.jpg"), "A clinic in Turkana County", ""),
	(
		"landing.card3.image",
		None,
		_image("training-manual.jpg"),
		"An adviser talking through a training manual",
		"",
	),
	("landing.card4.image", None, _image("community-session.jpg"), "A community session in progress", ""),
	(
		"landing.card2.body",
		"From KES 100 a year. Voting rights, a verifiable certificate, and a Society that counts you.",
		None,
		None,
		None,
	),
	(
		"landing.card3.body",
		"First aid, WASH and leadership courses with certificates issued straight to your profile.",
		None,
		None,
		None,
	),
	(
		"landing.card4.body",
		"Blood drives, youth camps and fundraisers open to the public. RSVP in one tap.",
		None,
		None,
		None,
	),
	# --- photo bands ------------------------------------------------------
	(
		"landing.band1.image",
		None,
		_image("field-turkana.jpg"),
		"Community members gather at a field site in Turkana County",
		"Turkana County · DFID · CC BY 2.0",
	),
	(
		"landing.band2.image",
		None,
		_image("ambulance-coast.jpg"),
		"A Kenya Red Cross mobile clinic on the coast",
		"Coast Province · U.S. Marine Corps · public domain",
	),
	("landing.band2.eyebrow", "MEMBERSHIP FROM KES 100/YEAR", None, None, None),
	(
		"landing.band2.body",
		"Pay by M-Pesa, download a certificate with QR verification, and carry your membership"
		" across branches when you move.",
		None,
		None,
		None,
	),
	# --- statistics -------------------------------------------------------
	#
	# The first figure is not seeded: it is counted off the register by
	# `api/society.py::figures`, so the page shows how many volunteers this site
	# holds rather than KRCS's published national total. The caption follows the
	# figure — it counts volunteers, so it may not say "& members".
	("landing.stat1.label", "VOLUNTEERS", None, None, None),
	("landing.stat2.value", "47", None, None, None),
	("landing.stat2.label", "COUNTY BRANCHES", None, None, None),
	("landing.stat3.value", "191", None, None, None),
	("landing.stat3.label", "NATIONAL SOCIETIES", None, None, None),
	("landing.stat4.value", "1965", None, None, None),
	("landing.stat4.label", "EST. BY ACT, CAP 256", None, None, None),
	# --- the public events teaser ----------------------------------------
	#
	# The fallback half of the band, not what it normally draws. `Landing.tsx`
	# reads the next three published Buzz events through
	# `api/events.py::teaser`, and these rows are what it shows only when there
	# are none — a site without Buzz, or a season with nothing in it. Seeded so
	# the demo page is never a heading over an empty row.
	("landing.event1.date", "AUG 14", None, None, None),
	("landing.event1.title", "Blood donor drive", None, None, None),
	("landing.event1.meta", "08:00 · Uhuru Park, Nairobi", None, None, None),
	("landing.event2.date", "AUG 15", None, None, None),
	("landing.event2.title", "Youth fun & skills fest", None, None, None),
	("landing.event2.meta", "10:00 · KRCS Nyeri grounds", None, None, None),
	("landing.event3.date", "AUG 22", None, None, None),
	("landing.event3.title", "Charity golf tournament", None, None, None),
	("landing.event3.meta", "09:00 · Machakos Golf Club", None, None, None),
	("landing.event3.cta", "Tickets", None, None, None),
	# --- closing ----------------------------------------------------------
	(
		"landing.cta.body",
		"Register in five minutes. Your branch confirms your record, and Kenya gains one more"
		" person who shows up.",
		None,
		None,
		None,
	),
	("landing.footer.emergency", "Emergency? Call 1199, toll-free, 24/7", None, None, None),
	("landing.footer.copyright", "© Kenya Red Cross Society", None, None, None),
)


def install() -> dict:
	"""Write the Kenya wording over the neutral defaults. Reports what it wrote.

	Only the slots named above are touched. Everything the product seeded and
	Kenya has nothing different to say about, such as the seven Fundamental
	Principles, stays exactly as it shipped.
	"""
	rows = []

	for key, text, image, alt, credit in COPY:
		row = {"content_key": key}

		# A None means "this seed has nothing to say about that field", which is
		# not the same as the empty string, which clears it.
		if text is not None:
			row["text_value"] = text
		if image is not None:
			row["image"] = image
		if alt is not None:
			row["image_alt"] = alt
		if credit is not None:
			row["image_credit"] = credit

		rows.append(row)

	return block_service.overwrite(rows)
