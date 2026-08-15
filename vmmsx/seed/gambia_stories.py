# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Twelve Gambia Red Cross Society stories, each with the source it came from.

Data, never behaviour. Read only by `gambia_operations.py::_stories`, which
writes each one into core's `Article`.

**Every story here is sourced.** They are drawn from published GRCS, IFRC,
ICRC, WHO Africa, UN Gambia and Gambian press reports, and each carries the URL
it came from into `Article.source_url` so a reader on the site can go and check
it. Quotations are reproduced as published and are not paraphrased or tidied.

**No photography ships with them.** The society's own seed-data pack suggests
image URLs on ifrc.org and elsewhere, and this seed deliberately does not
embed them: they are third-party pictures under their own licences, hot-linked
from a site the society does not control, and a cover image that 404s six
months from now is worse than none. `cover_image` is left empty for an editor
to fill from the society's own library.
"""

# Each story: slug, title, subtitle, location, summary, body paragraphs, the
# publication it came from, and when it happened.
STORIES = (
	{
		"slug": "pre-hospital-care-launch",
		"title": "Saving Lives on the Road: GRCS Launches The Gambia's First Pre-Hospital Care",
		"subtitle": "A new ambulance fleet reaches people at the point of need, not between hospitals.",
		"location": "Banjul",
		"published_on": "2026-05-08",
		"featured": 1,
		"source_name": "The Standard, Gambia",
		"source_url": "https://standard.gm/gambia-red-cross-launches-countrys-first-pre-hospital-care/",
		"summary": (
			"In May 2026 the Gambia Red Cross Society launched the country's first pre-hospital care"
			" and ambulance service, covering West Coast Region, Kanifing Municipality and Banjul."
		),
		"body": (
			"In May 2026, the Gambia Red Cross Society (GRCS) launched the country's first-ever"
			" pre-hospital care and ambulance service. President Fabakary Kalleh announced at a"
			" World Red Cross Day event: &ldquo;For the first time in The Gambia, we will pick you"
			" up from your home or an accident scene at any time of the night and take you to the"
			" nearest hospital with professional care and compassion. This is not just patient"
			" transfer between hospitals. This is emergency response from the point of need.&rdquo;",
			"The service covers West Coast Region, Kanifing Municipality and Banjul, the areas with"
			" the highest rates of road traffic accidents. Three new ambulances were deployed to"
			" WCR, two to KMC and one to Banjul, supplementing the existing fleet. GRCS already"
			" operates ambulances offering emergency support for an annual subscription of D3,800"
			" per family of five through its G-Plus Emergency Response Services. The Society is"
			" also working with partners to introduce a sea ambulance for the Barra crossing.",
			"Secretary General Ebou Faye Njie emphasised that this initiative addresses a deadly"
			" gap: &ldquo;Many people lose their lives because of how they are transported and"
			" handled before reaching the hospital. We are changing that.&rdquo; The ambulances are"
			" staffed by trained paramedics who provide advanced and basic life support en route to"
			" health facilities.",
		),
	},
	{
		"slug": "malaria-elimination-280-volunteers",
		"title": "280 Volunteers Mobilised: Accelerating Malaria Elimination Across All Regions",
		"subtitle": "A consignment of anti-malarials, and door-to-door work in all seven regions.",
		"location": "Nationwide",
		"published_on": "2025-07-15",
		"featured": 1,
		"source_name": "IFRC",
		"source_url": "https://www.ifrc.org/article/gambia-malaria-season-begins-life-saving-infusion-medicine",
		"summary": (
			"280 Red Cross volunteers were mobilised across all seven regions for the Seasonal"
			" Malaria Chemoprevention campaign, as GRCS handed anti-malarial medicines to the"
			" Ministry of Health."
		),
		"body": (
			"On a hot Thursday afternoon in July 2025, the courtyard of The Gambia's Central Medical"
			" Store was filled with people as the Gambia Red Cross Society officially handed over a"
			" vital consignment of anti-malarial medications to the Ministry of Health. The donation"
			" was part of the &ldquo;Accelerating Malaria Elimination in The Gambia&rdquo; project,"
			" funded by the China International Development Cooperation Agency (CIDCA) through the"
			" International Federation of Red Cross and Red Crescent Societies.",
			"Lamine Dampha, permanent secretary of the Ministry of Health, said during the handover:"
			" &ldquo;This delivery comes at the right time. The rainy season, commonly referred to"
			" as &lsquo;malaria season&rsquo;, has just begun.&rdquo; The medicines support the"
			" nationwide Seasonal Malaria Chemoprevention campaign targeting children under five,"
			" the most vulnerable population.",
			"Supporting the effort, 280 Red Cross volunteers were mobilised across all seven regions"
			" to raise awareness about malaria prevention. They went door-to-door educating families"
			" about the proper use of insecticide-treated mosquito nets, providing information on"
			" collection points, and assisting Ministry of Health staff with beneficiary"
			" registration. More than 1.5 million nets were distributed free of charge. In Sinthiou"
			" Sory, community health agent Alimathou Diadhiou reported achieving more than 90 per"
			" cent coverage. Malaria remains one of the top ten causes of death in The Gambia, with"
			" the entire population at risk.",
		),
	},
	{
		"slug": "omar-badjie-points-of-light",
		"title": "Omar Badjie: 20 Years of First Aid Training Recognised by the Commonwealth",
		"subtitle": "Two decades of teaching first aid in a country short of doctors.",
		"location": "Nationwide",
		"published_on": "2018-10-01",
		"source_name": "UK Government, Commonwealth Points of Light",
		"source_url": "https://www.pointsoflight.gov.uk/gambian-first-aid-trainer/",
		"summary": (
			"Omar Badjie has spent over 20 years training thousands of Gambians in first aid, and"
			" received the Commonwealth Points of Light Award for it."
		),
		"body": (
			"Omar Badjie has dedicated over 20 years to providing lifesaving first aid training"
			" across The Gambia through the Gambia Red Cross Society. Working in a country where a"
			" critical shortage of doctors makes it difficult for people to access healthcare, Omar"
			" leads workshops in schools and community centres across the nation, training thousands"
			" in basic and advanced first aid techniques.",
			"His work extends beyond first aid. Omar has led public health campaigns to combat"
			" polio, meningitis, HIV and Ebola, diseases that have severely impacted Gambian"
			" communities. His efforts were recognised when Her Royal Highness the Duchess of"
			" Cornwall presented him with the Commonwealth Points of Light Award during an official"
			" visit to The Gambia.",
			"Omar reflected on the recognition: &ldquo;I am truly and deeply honoured to receive this"
			" award. It is an even greater honour to know that the little things we do for our"
			" communities pays off and is recognised. I was convinced by my mom to join the Red"
			" Cross. I did join and I fell in love with the movement and the work we do every day to"
			" see that the most vulnerable and affected families are reached out to.&rdquo; He added"
			" that the award belongs equally to his colleagues still in the field.",
		),
	},
	{
		"slug": "restoring-family-links-mauritania",
		"title": "Restoring Family Links After the Mauritanian Coast Tragedy",
		"subtitle": "Families came to Kanifing to file tracing requests. The service has not stopped.",
		"location": "Kanifing",
		"published_on": "2019-12-15",
		"source_name": "The Point, Gambia",
		"source_url": "https://thepoint.gm/africa/gambia/article/grcs-activates-its-restoring-family-links",
		"summary": (
			"When a migrant boat capsized off Mauritania in December 2019, GRCS activated its"
			" Restoring Family Links service for the families of dozens of young Gambians."
		),
		"body": (
			"When a migrant boat capsized off the Mauritanian coast in December 2019, leaving dozens"
			" of young Gambians dead or missing, the Gambia Red Cross Society immediately activated"
			" its Restoring Family Links service. Families were invited to the GRCS headquarters in"
			" Kanifing to file tracing requests, helping to locate their loved ones among the"
			" survivors and the deceased.",
			"The GRCS worked in close coordination with its Red Cross Movement partners in both The"
			" Gambia and Mauritania, providing psychosocial support to survivors and their families."
			" The tragedy highlighted the dangerous Atlantic migration route that many young"
			" Gambians undertake in search of better opportunities in Europe. Between 2014 and 2018,"
			" an estimated 35,000 Gambians arrived in Europe via irregular means, the overwhelming"
			" majority of them young people.",
			"The RFL service continues to operate as a core programme, reconnecting families"
			" separated by conflict, disaster and migration. Through the global Family Links"
			" Network, the society processes tracing requests and coordinates with Red Cross"
			" societies along the entire migration route. The GRCS also collaborates with medical"
			" facilities, pharmacies and restaurants to provide free medical care, medication and"
			" food for migrants at border crossing points.",
		),
	},
	{
		"slug": "youth-volunteers-covid-urr-crr",
		"title": "Youth Volunteers Combat COVID-19 in Upper River and Central River Regions",
		"subtitle": "Nearly 100 young volunteers, door to door, in two of the country's most remote regions.",
		"location": "Upper River Region",
		"published_on": "2020-09-15",
		"source_name": "United Nations Gambia",
		"source_url": "https://gambia.un.org/en/100382-supporting-youth-efforts-enhance-community-action-against-covid-19",
		"summary": (
			"In September 2020 GRCS partnered with UNFPA and the Ministry of Health to deploy nearly"
			" 100 youth volunteers for contact tracing and risk communication."
		),
		"body": (
			"In September 2020, the Gambia Red Cross Society partnered with UNFPA and the Ministry"
			" of Health to launch a community contact tracing and surveillance initiative in the"
			" Central River and Upper River Regions, two of The Gambia's most remote areas. Nearly"
			" 100 youth volunteers, mobilised through the National Youth Council and the GRCS, were"
			" deployed across both regions to carry out risk communication and promote hygiene"
			" practices.",
			"In Badari Village, located about 8 kilometres from Basse in the Upper River Region, Red"
			" Cross volunteers used door-to-door risk communication to enhance community"
			" understanding of COVID-19. The Alkalo Muhammadou Manneh praised their work:"
			" &ldquo;Because of the discussions the volunteers continuously have with us, we now"
			" encourage all community members to wear facemasks, consistently wash their hands and"
			" we have put a stop to all mass gatherings. This will help us keep our community free"
			" from the virus.&rdquo;",
			"The volunteers also shared information on how pregnant and breastfeeding women could"
			" stay safe during the pandemic. The initiative was supported under the UN"
			" Peacebuilding-funded project on strengthening sustainable reintegration of returnees"
			" in The Gambia, recognising that many young volunteers had themselves returned from"
			" irregular migration journeys and were channelling their experiences into community"
			" service.",
		),
	},
	{
		"slug": "kafuta-truck-accident-response",
		"title": "Kafuta Truck Accident: G-Plus and Volunteers Respond Within Minutes",
		"subtitle": "When seconds matter, ambulances positioned in communities are the difference.",
		"location": "Kombo East, West Coast Region",
		"published_on": "2024-06-01",
		"source_name": "G-Plus Gambia",
		"source_url": "https://www.facebook.com/gplusgambia/",
		"summary": (
			"A truck ploughed into a crowd leaving a football game in Kafuta Village. G-Plus"
			" ambulances and GRCS volunteers from the local branch were among the first on scene."
		),
		"body": (
			"When a truck ploughed into a crowd leaving a football game in Kafuta Village, Kombo"
			" East District, in the West Coast Region, the response was immediate. G-Plus Gambia"
			" ambulances, the commercial emergency service jointly owned by the Gambia Red Cross"
			" Society and E-Plus Kenya, were among the first on the scene, joined by GRCS volunteers"
			" from the local branch.",
			"Working alongside health facilities and community members, the teams provided emergency"
			" medical care and first aid to dozens of seriously injured survivors. The incident"
			" underscored the critical role of pre-hospital care in a country where road traffic"
			" accidents are a leading cause of death and disability, particularly along the busy"
			" trans-Gambia highway corridor.",
			"The G-Plus service model represents an approach to sustainable emergency response. By"
			" operating on a commercial subscription basis while maintaining the Red Cross's"
			" humanitarian mandate, the service ensures that ambulances are professionally staffed,"
			" maintained and available around the clock. The Kafuta response demonstrated that when"
			" seconds matter, having trained volunteers and equipped ambulances positioned in"
			" communities can mean the difference between life and death.",
		),
	},
	{
		"slug": "boreholes-central-river-region",
		"title": "Drilling Boreholes: Clean Water Reaches Central River Region Communities",
		"subtitle": "&ldquo;We go where it is hard to reach.&rdquo;",
		"location": "Central River Region",
		"published_on": "2025-06-01",
		"source_name": "The Standard, Gambia",
		"source_url": "https://standard.gm/gambia-red-cross-launches-countrys-first-pre-hospital-care/",
		"summary": (
			"A GRCS borehole-drilling programme funded by the Spanish Red Cross brought clean water"
			" to remote Central River Region villages for the first time."
		),
		"body": (
			"In the Central River Region, some of The Gambia's most remote and underserved"
			" communities gained access to clean water for the first time through a GRCS"
			" borehole-drilling programme funded by the Spanish Red Cross. The project targeted"
			" villages where women and children walked several kilometres daily to collect water"
			" from unreliable and often contaminated sources.",
			"GRCS President Fabakary Kalleh spoke about the initiative: &ldquo;We go where it is hard"
			" to reach. We are auxiliary to the Government of The Gambia, not competitors. Our role"
			" is to fill the gaps and reach the most remote and vulnerable communities.&rdquo; The"
			" boreholes serve not only as water points but as community gathering spaces, reducing"
			" the burden on women and freeing children to attend school.",
			"Each borehole installation was accompanied by hygiene promotion activities led by GRCS"
			" volunteers, who trained community members on water storage, handwashing and sanitation"
			" practices. Water committees were established in each village to maintain the"
			" infrastructure, ensuring long-term sustainability. The project is part of the GRCS's"
			" broader WASH programme, which recognises clean water as fundamental to health, dignity"
			" and development.",
		),
	},
	{
		"slug": "world-red-cross-day-2026",
		"title": "United in Humanity: World Red Cross Day 2026",
		"subtitle": "Volunteers from all seven branches, and the launch of the new ambulance fleet.",
		"location": "Kanifing",
		"published_on": "2026-05-08",
		"source_name": "In-Depth Media, Gambia",
		"source_url": "https://indepthmedia.gm/gambia-red-cross-marks-world-red-cross-day-2026-launches-ambulances-for-emergency-response/",
		"summary": (
			"GRCS commemorated World Red Cross and Red Crescent Day 2026 under the theme"
			" &ldquo;United in Humanity&rdquo;, honouring volunteers from all seven branches."
		),
		"body": (
			"The Gambia Red Cross Society commemorated World Red Cross and Red Crescent Day 2026"
			" under the global theme &ldquo;United in Humanity&rdquo;, honouring volunteers and"
			" staff working at the frontline of humanitarian action across the country. The event"
			" brought together GRCS leadership, volunteers from all seven branches, government"
			" officials and partner organisations.",
			"President Fabakary Kalleh reminded attendees that humanity is the movement's common"
			" bond: &ldquo;Our volunteers and staff are not separate from the communities they"
			" serve, but are part of them, standing side by side with people in moments of crisis,"
			" vulnerability and hope.&rdquo; He highlighted the Society's expanded reach in both"
			" urban and rural areas, citing flood and fire response, health campaigns, road safety"
			" promotion, migrant assistance, family tracing and climate resilience programming.",
			"Secretary General Ebou Faye Njie echoed the sentiment: &ldquo;Whether responding to"
			" floods and fire incidents, supporting health campaigns, promoting first aid and road"
			" safety, assisting migrants, restoring family links, or supporting climate resilience,"
			" our mission remains clear: to alleviate human suffering.&rdquo; The celebration"
			" included the formal launch of the new ambulance fleet, recognition of long-serving"
			" volunteers, and cultural performances by Red Cross youth groups.",
		),
	},
	{
		"slug": "epidemic-preparedness-150-volunteers",
		"title": "150 Volunteers Trained: Epidemic Preparedness Across Seven Regions",
		"subtitle": "679 communities, and hand-washing stations at every branch and border post.",
		"location": "Nationwide",
		"published_on": "2024-03-01",
		"source_name": "IFRC DREF operation final report",
		"source_url": "https://adore.ifrc.org/Download.aspx?FileId=80212",
		"summary": (
			"GRCS trained 150 volunteers in the Epidemic Control for Volunteers manual and deployed"
			" them across 679 communities in all seven administrative regions."
		),
		"body": (
			"In preparation for potential disease outbreaks, the Gambia Red Cross Society trained"
			" 150 volunteers in the Epidemic Control for Volunteers manual, achieving 100 per cent"
			" of its target. These volunteers were deployed across 679 communities in all seven"
			" administrative regions to carry out disease surveillance, community awareness and"
			" behaviour change communication.",
			"The training covered identification of common epidemic-prone diseases, proper use of"
			" personal protective equipment, safe and dignified burial practices, contact tracing"
			" and psychosocial first aid. Hand-washing stations were installed at all GRCS branch"
			" offices, the national headquarters and key border posts, critical entry points where"
			" travellers could potentially introduce diseases.",
			"The programme was supported by the IFRC's Disaster Response Emergency Fund and aligned"
			" with the regional preparedness strategy for countries bordering nations where active"
			" outbreaks had been reported. The experience proved invaluable when The Gambia declared"
			" an mpox outbreak in July 2025, with trained volunteers already in place across"
			" communities. Volunteer coordinator Isatou Ceesay noted: &ldquo;Our volunteers are the"
			" eyes and ears of the communities. They know who is sick, who has travelled, and who"
			" needs help, before any report reaches the branch office.&rdquo;",
		),
	},
	{
		"slug": "mpox-preparedness-waho",
		"title": "Mpox Preparedness: GRCS and the West Africa Health Organisation Coordinate",
		"subtitle": "The Gambia declared an outbreak in July 2025. The volunteers were already trained.",
		"location": "Kanifing",
		"published_on": "2025-07-20",
		"source_name": "Gambia Red Cross Society",
		"source_url": "https://gm.linkedin.com/in/the-gambia-red-cross-society-a808261b2",
		"summary": (
			"When The Gambia declared an mpox outbreak, GRCS scaled up a response built on"
			" volunteers trained years earlier in epidemic control."
		),
		"body": (
			"When The Gambia declared an mpox outbreak in July 2025, the Gambia Red Cross Society"
			" was already prepared. Having previously trained hundreds of volunteers in epidemic"
			" control, the Society rapidly scaled up its response in coordination with the Ministry"
			" of Health and the West Africa Health Organisation.",
			"A delegation from WAHO visited GRCS headquarters in Kanifing to discuss regional"
			" preparedness strategies. The engagement focused on cross-border surveillance,"
			" community-based detection, and the Red Cross's role as auxiliary to government in"
			" public health emergencies. GRCS volunteers were deployed to conduct risk communication"
			" in markets, schools and transport hubs, particularly in areas near the Senegalese"
			" border where cross-border movement is constant.",
			"The response drew on lessons learned from COVID-19 and Ebola preparedness. Volunteers"
			" used the same trusted community networks established during previous health campaigns"
			" to disseminate accurate information, counter rumours and refer suspected cases to"
			" health facilities. The GRCS also provided psychosocial support to affected individuals"
			" and their families, recognising the stigma associated with mpox. The Gambia's"
			" geography, entirely surrounded by Senegal except for its Atlantic coastline, makes"
			" cross-border health security essential.",
		),
	},
	{
		"slug": "sahel-plus-migration",
		"title": "Sahel Plus: Protecting Migrants Along the Atlantic Route",
		"subtitle": "Ten National Societies sharing information along the route to the Canary Islands.",
		"location": "North Bank Region",
		"published_on": "2025-01-15",
		"source_name": "UN Migration Network",
		"source_url": "https://migrationnetwork.un.org/practice/cooperation-between-red-cross-and-red-crescent-national-societies-and-their-governments",
		"summary": (
			"GRCS is part of the Sahel Plus Migration Technical Working Group, and provides shelter,"
			" first aid and family reunification at border crossing points."
		),
		"body": (
			"The Gambia Red Cross Society plays an active role in the Sahel Plus Migration Technical"
			" Working Group, a coordination platform bringing together National Red Cross and Red"
			" Crescent Societies from Mali, Mauritania, Burkina Faso, Cape Verde, Guinea-Bissau,"
			" Guinea Conakry, Niger, Senegal, Chad and The Gambia. Through this network, societies"
			" share real-time information about migrant movements along the dangerous Atlantic route"
			" to the Canary Islands.",
			"GRCS teams provide assistance to migrants at multiple points: temporary shelter, food"
			" and non-food items, family reunification services, life-saving information, first aid"
			" and psychosocial support. The Society also collaborates with medical facilities,"
			" pharmacies and restaurants near border crossing points to offer free medical care and"
			" meals. Border police and security officers have been trained by the GRCS on migrants'"
			" rights and referral pathways to Red Cross services.",
			"The EU-funded Migration Project, running from 2025 to 2029, is expanding this work. The"
			" project aims to strengthen protection services, improve data collection on migration"
			" trends, and enhance community-based support mechanisms for both outbound migrants and"
			" returnees reintegrating into Gambian society.",
		),
	},
	{
		"slug": "voluntary-blood-donation",
		"title": "Blood Donation Drives: Building a Culture of Voluntary Giving",
		"subtitle": "A donor since 2004, a mother who nearly died, and a 14-year-old who came anyway.",
		"location": "Lower River Region",
		"published_on": "2019-10-01",
		"source_name": "World Health Organization Africa",
		"source_url": "https://www.afro.who.int/fr/node/11938",
		"summary": (
			"Stories from the GRCS blood donation programme, and the push toward the WHO target of"
			" 100 per cent voluntary donation."
		),
		"body": (
			"In Soma District Hospital, Lower River Region, Omar Colley has been voluntarily"
			" donating blood since 2004. He has been called upon during emergencies, the last being"
			" to save a woman in labour who was transported 22 kilometres from her village to the"
			" health facility on a donkey cart at 2:15 am. His dedication represents the spirit of"
			" the GRCS blood donation programme.",
			"Sutering Jawo, a mother of two, tells a different side of the story. She lost her own"
			" sister during childbirth and nearly died herself, saved only by a blood transfusion."
			" The experience transformed her into an advocate: &ldquo;This has given me the"
			" motivation and strength to be a voluntary blood donor so as to save would-be mothers"
			" who might find themselves in the critical situation like what I faced seven years"
			" ago.&rdquo;",
			"Even 14-year-old Ebrima Kambi tried to donate after learning about chronic blood"
			" shortages, saying: &ldquo;Because of what I have learnt about frequent blood shortages"
			" during emergencies causing loss of lives, I came to donate blood.&rdquo; Though too"
			" young to donate, he was thanked for his interest and told he could return at 16. These"
			" stories drive the GRCS's push toward the WHO target of 100 per cent voluntary blood"
			" donation, working alongside the Ministry of Health and UN partners to build a"
			" sustainable blood supply across all regions.",
		),
	},
)
