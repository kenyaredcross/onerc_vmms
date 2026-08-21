# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Gambia Red Cross Society wording for the public landing page.

Part of the Gambia seed, and here for the same reason the rest of it is: the
product ships society-neutral defaults in `content/seeds/default_content.py`,
and every sentence below that says "Gambia", "region" or "GMD" would break the
rule that no source file outside `vmmsx/seed/` names them.

**This one overwrites.** `blocks.seed()` is the migrate-safe call that never
touches an existing slot; this uses `blocks.overwrite()` because somebody who
runs the Gambia seed deliberately is asking for the Gambia page and would not
thank us for a half-Gambian one.

**Every figure below is the society's own.** The statistics are GRCS's 2026
IFRC Federation-wide Databank return (17,889 volunteers, 473 local units, 56
staff) and the seven branches are the seven administrative regions. Nothing is
rounded up and nothing is invented: a number on a public page is a claim the
society has to stand behind.

**The photographs are placeholders, and they are not of The Gambia.** This seed
used to ship none at all, on the reasoning that an empty slot with an upload
control on it is more honest than a picture of somewhere the society does not
work. That is true of a slot nobody has looked at and false of a landing page
somebody has to stand in front of: the design is built out of full-bleed
photography, and without any the page is three navy rectangles.

So it now points at the licensed images in `public/images/seed_kenya/`, and
every one of them carries its real provenance into `image_credit`, which the
hero and both bands draw in the corner. A visitor is told where the picture was
taken. **Replacing them with GRCS's own photography is the first thing to do
with the pencil**, and the credit field empties with them.
"""

from vmmsx.content.services import blocks as block_service

# Served by Frappe from `sites/assets/vmmsx` -> `vmmsx/public`. The folder is
# named for where the pictures were taken, not for which society is using them.
IMAGE_BASE = "/assets/vmmsx/images/seed_kenya"


def _image(filename: str) -> str:
	return f"{IMAGE_BASE}/{filename}"

# (content_key, text, image, alt, credit)
#
# A None image leaves whatever is there; the empty string clears it. Every row
# here sets words only, for the reason in the module docstring.
COPY = (
	# No brand row. The lockup is the society's own logo and name, read live from
	# National Society Settings; a seed writing them onto the page as words would
	# be a second copy of what core already holds.
	# --- hero -------------------------------------------------------------
	("landing.hero.eyebrow", "THE GAMBIA RED CROSS SOCIETY", None, None, None),
	("landing.hero.headline", "Stand with your community.", None, None, None),
	(
		"landing.hero.body",
		"One profile for volunteering, training, deployments and membership, across all seven"
		" regional branches and the Links that make them up.",
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
	#
	# No credit on these four: the design draws none on a card, and the licences
	# of the four are not recorded anywhere this seed can read them. The three
	# that are credited are the three the page actually captions.
	("landing.card1.image", None, _image("firstaid-sagana.jpg"), "A first aid training session", ""),
	("landing.card2.image", None, _image("clinic-turkana.jpg"), "A clinic in Turkana County", ""),
	(
		"landing.card3.image",
		None,
		_image("training-manual.jpg"),
		"An adviser talking through a training manual",
		"",
	),
	(
		"landing.card4.image",
		None,
		_image("community-session.jpg"),
		"A community session in progress",
		"",
	),
	(
		"landing.card1.body",
		"Join a Red Cross Link in your own community or school. Your branch confirms your record"
		" and your name enters the Branch Register.",
		None,
		None,
		None,
	),
	(
		"landing.card2.body",
		"Membership from GMD 225 every three years. A certificate, a place at branch programmes,"
		" and a Society that counts you.",
		None,
		None,
		None,
	),
	(
		"landing.card3.body",
		"First aid, epidemic control and community health training, with certificates issued"
		" straight to your profile.",
		None,
		None,
		None,
	),
	(
		"landing.card4.body",
		"Blood drives, health campaigns and youth programmes open to the public across the regions.",
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
		"A Red Cross mobile clinic on the coast",
		"Coast Province · U.S. Marine Corps · public domain",
	),
	("landing.band2.eyebrow", "MEMBERSHIP FROM GMD 225", None, None, None),
	(
		"landing.band2.body",
		"Three plans, each billed every three years: Youth in School, Senior Member and the"
		" Volunteering Aid Detachment. Your branch reviews the application and your certificate"
		" follows.",
		None,
		None,
		None,
	),
	# --- statistics -------------------------------------------------------
	#
	# GRCS's 2026 IFRC Federation-wide Databank return, except the branch count,
	# which is the society's own structure.
	#
	# The volunteer figure is not seeded at all now: `api/society.py::figures`
	# counts the register, so the page shows this site's volunteers rather than
	# the national 17,889. That also settles the old worry recorded here — that
	# the national return is not the sum of the branch registration sheets in
	# `gambia_structure.py`, which count a person once per Link they belong to.
	# The register counts a person once.
	("landing.stat1.label", "VOLUNTEERS", None, None, None),
	("landing.stat2.value", "7", None, None, None),
	("landing.stat2.label", "REGIONAL BRANCHES", None, None, None),
	("landing.stat3.value", "473", None, None, None),
	("landing.stat3.label", "RED CROSS LINKS", None, None, None),
	("landing.stat4.value", "1966", None, None, None),
	("landing.stat4.label", "FOUNDED", None, None, None),
	# --- the public events teaser ----------------------------------------
	#
	# The fallback half of the band, not what it normally draws. `Landing.tsx`
	# reads the next three published Buzz events through
	# `api/events.py::teaser`, and these rows are what it shows only when there
	# are none — a site without Buzz, or a season with nothing in it.
	("landing.event1.date", "AUG 20", None, None, None),
	("landing.event1.title", "Blood donor drive", None, None, None),
	("landing.event1.meta", "08:00 · Brikama, West Coast Region", None, None, None),
	("landing.event2.date", "SEP 01", None, None, None),
	("landing.event2.title", "Seasonal malaria campaign launch", None, None, None),
	("landing.event2.meta", "09:00 · Nationwide", None, None, None),
	("landing.event3.date", "SEP 10", None, None, None),
	("landing.event3.title", "Road safety week", None, None, None),
	("landing.event3.meta", "08:00 · Serekunda, Kanifing Municipal", None, None, None),
	("landing.event3.cta", "Details", None, None, None),
	# --- closing ----------------------------------------------------------
	(
		"landing.cta.body",
		"Register in five minutes. Your branch confirms your record, and The Gambia gains one"
		" more person who shows up.",
		None,
		None,
		None,
	),
	(
		"landing.footer.emergency",
		"Emergency ambulance: G-Plus 1122 · GRCS headquarters +220 439 2405",
		None,
		None,
		None,
	),
	("landing.footer.copyright", "© The Gambia Red Cross Society", None, None, None),
)


def install() -> dict:
	"""Write the Gambia wording over the neutral defaults. Reports what it wrote.

	Only the slots named above are touched. Everything the product seeded and
	this society has nothing different to say about, such as the seven
	Fundamental Principles, stays exactly as it shipped.
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
