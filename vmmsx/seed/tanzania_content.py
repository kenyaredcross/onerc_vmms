# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Tanzania Red Cross Society wording for the public landing page.

Part of the Tanzania seed, and here for the same reason `gambia_content.py`
and `kenya_content.py` are: the product ships society-neutral defaults in
`content/seeds/default_content.py`, and every sentence below that names
Tanzania, a region or TZS would break the rule that no source file outside
`vmmsx/seed/` names them.

**This one overwrites.** `blocks.seed()` is the migrate-safe call that never
touches an existing slot; this uses `blocks.overwrite()` because somebody who
runs the Tanzania seed deliberately is asking for the Tanzania page.

**The figures below are the society's own**, published on `trcs.or.tz` and the
IFRC National Societies Directory: 41,300+ volunteers, 31 regional branches
(Tanzania's own administrative regions), 1,250+ sub-branches, founded 1962.

**The photographs are placeholders, and they are not of Tanzania.** No TRCS
photography is committed to this repository, so this seed reuses the same
licensed images `gambia_content.py` already reuses from
`public/images/seed_kenya/`, each carrying its real provenance into
`image_credit` — the hero and both bands draw it in the corner, so a visitor is
told where the picture was actually taken. **Replacing them with TRCS's own
photography is the first thing to do with the pencil.**
"""

from vmmsx.content.services import blocks as block_service

IMAGE_BASE = "/assets/vmmsx/images/seed_kenya"


def _image(filename: str) -> str:
	return f"{IMAGE_BASE}/{filename}"


# (content_key, text, image, alt, credit)
#
# A None image leaves whatever is there; the empty string clears it. Every row
# here sets words only, for the reason in the module docstring.
COPY = (
	# No brand row — the lockup is the society's own logo and name, read live
	# from National Society Settings.
	# --- hero ---------------------------------------------------------------
	("landing.hero.eyebrow", "TANZANIA RED CROSS SOCIETY", None, None, None),
	("landing.hero.headline", "Show up for your community.", None, None, None),
	(
		"landing.hero.body",
		"One profile for volunteering, training, deployments and membership, across all 31"
		" regional branches, from Kigoma to Zanzibar.",
		None,
		None,
		None,
	),
	(
		"landing.hero.image",
		None,
		_image("outreach-lamu.jpg"),
		"A community health volunteer shares a moment with children in Lamu County, Kenya",
		"Lamu County, Kenya · Neil Thomas / Safari Doctors · CC BY-SA 4.0",
	),
	# --- the four cards -------------------------------------------------------
	("landing.card1.image", None, _image("firstaid-sagana.jpg"), "A first aid training session", ""),
	("landing.card2.image", None, _image("clinic-turkana.jpg"), "A community clinic", ""),
	(
		"landing.card3.image",
		None,
		_image("training-manual.jpg"),
		"An adviser talking through a training manual",
		"",
	),
	("landing.card4.image", None, _image("community-session.jpg"), "A community session in progress", ""),
	(
		"landing.card1.body",
		"Join TRCS in your own region. Your branch confirms your record and your name enters the"
		" Branch Register.",
		None,
		None,
		None,
	),
	(
		"landing.card2.body",
		"Membership from TZS 5,000 a year. A certificate, a place at branch programmes, and a"
		" Society that counts you.",
		None,
		None,
		None,
	),
	(
		"landing.card3.body",
		"First aid, disaster response and community health training, with certificates issued"
		" straight to your profile.",
		None,
		None,
		None,
	),
	(
		"landing.card4.body",
		"Blood drives, health campaigns and youth programmes open to the public across every region.",
		None,
		None,
		None,
	),
	# --- photo bands ------------------------------------------------------
	(
		"landing.band1.image",
		None,
		_image("field-turkana.jpg"),
		"Community members gather at a field site in Turkana County, Kenya",
		"Turkana County, Kenya · DFID · CC BY 2.0",
	),
	(
		"landing.band2.image",
		None,
		_image("ambulance-coast.jpg"),
		"A Red Cross mobile clinic",
		"Coast Province, Kenya · U.S. Marine Corps · public domain",
	),
	("landing.band2.eyebrow", "MEMBERSHIP FROM TZS 5,000", None, None, None),
	(
		"landing.band2.body",
		"Three plans: Youth Member, Ordinary Member and Life Member. Your region reviews the"
		" application and your certificate follows.",
		None,
		None,
		None,
	),
	# --- statistics -------------------------------------------------------
	#
	# TRCS's own published figures (trcs.or.tz, IFRC National Societies
	# Directory): 41,300+ volunteers, 31 regional branches, 1,250+
	# sub-branches, founded 1962 under Parliamentary Act No. 71.
	("landing.stat1.value", "41,300+", None, None, None),
	("landing.stat1.label", "VOLUNTEERS", None, None, None),
	("landing.stat2.value", "31", None, None, None),
	("landing.stat2.label", "REGIONAL BRANCHES", None, None, None),
	("landing.stat3.value", "1,250+", None, None, None),
	("landing.stat3.label", "SUB-BRANCHES", None, None, None),
	("landing.stat4.value", "1962", None, None, None),
	("landing.stat4.label", "FOUNDED", None, None, None),
	# --- the public events teaser ----------------------------------------
	#
	# Typed in, not queried: this app has no event doctype at the content-block
	# layer, and the honest way to show upcoming events on a page is for
	# somebody to have written them. Dates are illustrative rather than tied to
	# the real Buzz events `tanzania_operations.py` seeds, the same as Gambia's
	# own teaser — see the note in `content/seeds/default_content.py`.
	("landing.event1.date", "SEP 12", None, None, None),
	("landing.event1.title", "World First Aid Day", None, None, None),
	("landing.event1.meta", "09:00 · Dar es Salaam", None, None, None),
	("landing.event2.date", "SEP 20", None, None, None),
	("landing.event2.title", "Regional blood donor drive", None, None, None),
	("landing.event2.meta", "08:00 · Mwanza", None, None, None),
	("landing.event3.date", "OCT 04", None, None, None),
	("landing.event3.title", "Volunteer induction, new intake", None, None, None),
	("landing.event3.meta", "09:00 · TRCS National Headquarters", None, None, None),
	("landing.event3.cta", "Details", None, None, None),
	# --- closing ------------------------------------------------------------
	(
		"landing.cta.body",
		"Register in five minutes. Your region confirms your record, and Tanzania gains one more"
		" person who shows up.",
		None,
		None,
		None,
	),
	(
		"landing.footer.emergency",
		"24-hour hotline: 0800 750 150 · Counselling: 0800 750 151",
		None,
		None,
		None,
	),
	("landing.footer.copyright", "© Tanzania Red Cross Society", None, None, None),
)


def install() -> dict:
	"""Write the Tanzania wording over the neutral defaults. Reports what it wrote."""
	rows = []

	for key, text, image, alt, credit in COPY:
		row = {"content_key": key}

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
