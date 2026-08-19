# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Four Tanzania Red Cross Society stories, each with the source it came from.

Data, never behaviour. Read only by `tanzania_operations.py::_stories`, which
writes each one into core's `Article`.

**Every story here is sourced**, from TRCS's own site, the EU delegation to
Tanzania, and the European Commission's international partnerships site, and
each carries the URL it came from into `Article.source_url`. Where a source
gave a precise figure — the EU's €100,000 DREF allocation, the death toll, the
number of people reached by the heatwave campaign — it is reproduced as
published. **Nothing here is a fabricated quotation**: none of the source
articles found while researching this seed carried an attributable quote from
a named official, so none is invented here either, unlike `gambia_stories.py`,
whose sources did carry direct quotes.

**No photography ships with them.** `cover_image` is left empty for an editor
to fill from the society's own library, for the same reason `gambia_stories.py`
leaves it empty rather than hot-linking a third party's picture.
"""

# Each story: slug, title, subtitle, location, summary, body paragraphs, the
# publication it came from, and when it happened.
STORIES = (
	{
		"slug": "rungwe-kyela-flood-response",
		"title": "Floods and Landslides in Rungwe: TRCS Reaches Over 2,600 People",
		"subtitle": "EU emergency funding backs a three-month relief operation across six wards in Mbeya Region.",
		"category": "Emergency Response",
		"location": "Rungwe and Kyela Districts, Mbeya Region",
		"published_on": "2026-04-27",
		"featured": 1,
		"source_name": "Tanzania Red Cross Society, and the EU Delegation to Tanzania",
		"source_url": (
			"https://www.eeas.europa.eu/delegations/tanzania/"
			"european-union-provides-%E2%82%AC100000-support-people-affected-devastating-floods_en"
		),
		"summary": (
			"Intense rainfall on 25 and 26 March 2026 triggered flash floods and landslides across"
			" Rungwe District, Mbeya Region, destroying homes and roads and displacing hundreds of"
			" families. The Tanzania Red Cross Society is delivering shelter, clean water, health"
			" services and hygiene support to over 2,600 people, backed by €100,000 in EU emergency"
			" funding."
		),
		"body": (
			"Continuous heavy rain and strong winds during the March to May rainy season triggered"
			" multiple landslides and flash floods in Mbeya Region on 25 and 26 March 2026. The"
			" worst-hit wards were Nkunga, Lupepo, Kawetele and Ikuti in Rungwe District, where homes"
			" were buried and roads and other infrastructure were badly damaged.",
			"By 27 March at least 20 people, including several children, had died, and a number of"
			" others were injured. Around 600 people were displaced and are sheltering in schools and"
			" other temporary facilities, where overcrowding, limited safe drinking water and"
			" inadequate sanitation are raising the risk of waterborne disease and malaria on top of"
			" the disaster itself.",
			"The European Union has released €100,000 through its Disaster Response Emergency Fund to"
			" support the response. The Tanzania Red Cross Society is using the funding to deliver"
			" shelter, clean water, health services, and hygiene and sanitation support, with"
			" attention to gender inclusion in how aid is distributed. The operation is planned to run"
			" for three months, through the end of July 2026, and aims to reach more than 2,600 people"
			" across six wards in Rungwe and Kyela Districts.",
		),
	},
	{
		"slug": "mbarali-flood-relief",
		"title": "Relief Support Delivered to Flood-Affected Families in Mbarali",
		"subtitle": "One of several regions hit during a rainy season that affected tens of thousands nationwide.",
		"category": "Emergency Response",
		"location": "Mbarali District, Mbeya Region",
		"published_on": "2026-04-27",
		"featured": 0,
		"source_name": "Tanzania Red Cross Society",
		"source_url": "https://trcs.or.tz/",
		"summary": (
			"Alongside its response in neighbouring Rungwe, the Tanzania Red Cross Society delivered"
			" relief support to families displaced by flooding in Mbarali District, part of a rainy"
			" season that affected tens of thousands of people across the country."
		),
		"body": (
			"The same rainy season that struck Rungwe and Kyela Districts also flooded communities in"
			" Mbarali District, further south in Mbeya Region. Tanzania Red Cross Society teams and"
			" volunteers delivered relief support directly to affected families, working alongside the"
			" district's own disaster management structures.",
			"Nationally, heavy rains between December 2025 and March 2026 caused flooding that the"
			" government and humanitarian partners linked to dozens of deaths and injuries and over"
			" 37,000 people affected across multiple regions. The Mbarali response is one of several"
			" TRCS branch-level operations run during that season, funded and staffed alongside the"
			" larger EU-backed operation in Rungwe and Kyela.",
			"As with every TRCS emergency response, the relief was delivered by trained regional"
			" volunteers under the branch's own coordination, the same structure a volunteer signing up"
			" through this portal joins.",
		),
	},
	{
		"slug": "heatwave-albinism-awareness-zanzibar",
		"title": "Heatwave Campaign Reaches Over 4,000 People to Protect Zanzibar's Albinism Community",
		"subtitle": "Schools, madrasas and markets host sessions on a risk most heat advice does not mention.",
		"category": "Health",
		"location": "Zanzibar Island",
		"published_on": "2026-03-04",
		"featured": 1,
		"source_name": "Tanzania Red Cross Society, and the European Commission's International Partnerships",
		"source_url": "https://international-partnerships.ec.europa.eu/news-and-events/stories/protecting-people-albinism-tanzania_en",
		"summary": (
			"A Tanzania Red Cross Society heatwave awareness campaign reached more than 4,000 people"
			" in schools, madrasas, markets and communities around Zanzibar Island, focused on the"
			" particular danger extreme heat poses to people with albinism."
		),
		"body": (
			"Tanzania has one of the highest rates of albinism in the world, close to 1 in 14,000"
			" people — more than 40,000 people nationally. Albinism causes a lack of melanin in the"
			" skin, hair and eyes, leaving people with the condition highly vulnerable to sun exposure,"
			" at sharply higher risk of skin cancer, and, in almost every case, visually impaired.",
			"In early 2026, as temperatures rose during a regional heatwave, Tanzania Red Cross Society"
			" volunteers ran an awareness campaign in schools, madrasas, markets and communities around"
			" Zanzibar Island, reaching more than 4,000 people directly with practical guidance on"
			" sun protection, hydration and recognising heat-related illness — information ordinary"
			" heat advice rarely tailors to this community at all.",
			"The campaign sits alongside a wider push by TRCS and partner organisations to support"
			" Tanzanians living with albinism, whose vulnerability to the sun is compounded, in some"
			" areas, by social stigma and threats to their safety. Volunteer-led, community-level"
			" awareness work of exactly this kind is what a branch runs when it needs people, not"
			" just funding.",
		),
	},
	{
		"slug": "sixty-years-of-trcs",
		"title": "Sixty Years of Humanity: From a 1962 Act of Parliament to 41,300 Volunteers",
		"subtitle": "How a society founded to respond to one emergency became a permanent presence in every region.",
		"category": "Branch Life",
		"location": "Dar es Salaam",
		"published_on": "2026-01-15",
		"featured": 0,
		"source_name": "Tanzania Red Cross Society, and the IFRC National Societies Directory",
		"source_url": "https://www.ifrc.org/national-societies-directory/tanzania-red-cross-national-society",
		"summary": (
			"The Tanzania Red Cross Society was established by Parliamentary Act No. 71 of 1962. Six"
			" decades on, it is present in all 31 regions of mainland Tanzania and Zanzibar, with over"
			" 41,300 volunteers and 1,250 sub-branches."
		),
		"body": (
			"The Tanzania Red Cross Society was established by an Act of Parliament, No. 71 of 1962,"
			" the same year mainland Tanganyika became a republic. What began as a small,"
			" headquarters-led organisation has grown into a nationwide volunteer movement: TRCS is"
			" now organised into 31 regional branches, one in every region of mainland Tanzania and"
			" Zanzibar, and more than 1,250 sub-branches beneath them.",
			"Today the Society counts more than 41,300 volunteers, coordinated from its national"
			" headquarters on Mwai Kibaki Road in Mikocheni B, Dar es Salaam, and run day to day"
			" through the regional branch structure. Its mission, published on its own site, is to"
			" improve the situation of the most vulnerable in Tanzania through the power of humanity;"
			" its stated vision is to be a strong, credible and dependable national institution.",
			"The scale is a fact about volunteers, not about headquarters staff. Disaster response,"
			" first aid, blood donor support, community health outreach and youth programmes across 31"
			" regions are carried out overwhelmingly by people who signed up at their own branch — the"
			" same register this portal keeps.",
		),
	},
)
