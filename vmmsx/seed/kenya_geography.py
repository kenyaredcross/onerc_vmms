# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Kenya's administrative geography, as data. No behaviour, no Frappe import.

The 47 counties and the 290 sub-counties under them, which is the whole of what
`kenya.py` needs to build a Geo Node tree the Kenya Red Cross Society would
recognise. Kept in its own module for one reason: it is 340 place names, and
`kenya.py` is a *configuration* seed somebody has to be able to read.

**Where these names come from.**

* **The counties** are copied from `data_capture_forms`' own county master
  (`cva_county.py::COUNTIES`) — code, name and the pre-devolution province the
  county sits in — so that two apps on this bench spell Kenya the same way and
  can be reconciled later without a remap. The one departure is county 047,
  which that master calls "Nairobi City" and this calls **Nairobi**: an existing
  Kenya-seeded site already carries a `krcs-county` node named "Nairobi", and
  renaming it would make this seed create a duplicate rather than recognise the
  node it made last time.
* **The sub-counties** are Kenya's 290 electoral constituencies, which is the
  set almost every Kenyan register — KRCS's own forms included — means by
  "sub-county". It is worth saying plainly that this is *not* the same as the
  Interior Ministry's administrative sub-county list, which has drifted above
  290 (roughly 314 as of 2023) as districts were split. The constituency set was
  chosen because it is stable, published, and the one a volunteer filling in a
  form will recognise; a society that needs the administrative set replaces this
  table and nothing else.

**`region` is carried but not built into the tree.** KRCS's own operational
structure is eight regions, and the ladder this seed builds is
National -> County -> Sub-County, with no regional rung. The column is here
because it is free to carry, it is what the county master already holds, and a
society that later wants a regional tier has the grouping to hand rather than
having to source it again. See `kenya.LEVELS` for the ladder that is actually
created.

Nothing in this module is imported by the app. See the note at the top of
`kenya.py`: the universal rules are code, the answers are configuration.
"""

#: (code, county, region) for Kenya's 47 counties, in official county-code order.
COUNTIES = (
	("001", "Mombasa", "Coast"),
	("002", "Kwale", "Coast"),
	("003", "Kilifi", "Coast"),
	("004", "Tana River", "Coast"),
	("005", "Lamu", "Coast"),
	("006", "Taita Taveta", "Coast"),
	("007", "Garissa", "North Eastern"),
	("008", "Wajir", "North Eastern"),
	("009", "Mandera", "North Eastern"),
	("010", "Marsabit", "Eastern"),
	("011", "Isiolo", "Eastern"),
	("012", "Meru", "Eastern"),
	("013", "Tharaka Nithi", "Eastern"),
	("014", "Embu", "Eastern"),
	("015", "Kitui", "Eastern"),
	("016", "Machakos", "Eastern"),
	("017", "Makueni", "Eastern"),
	("018", "Nyandarua", "Central"),
	("019", "Nyeri", "Central"),
	("020", "Kirinyaga", "Central"),
	("021", "Murang'a", "Central"),
	("022", "Kiambu", "Central"),
	("023", "Turkana", "Rift Valley"),
	("024", "West Pokot", "Rift Valley"),
	("025", "Samburu", "Rift Valley"),
	("026", "Trans Nzoia", "Rift Valley"),
	("027", "Uasin Gishu", "Rift Valley"),
	("028", "Elgeyo Marakwet", "Rift Valley"),
	("029", "Nandi", "Rift Valley"),
	("030", "Baringo", "Rift Valley"),
	("031", "Laikipia", "Rift Valley"),
	("032", "Nakuru", "Rift Valley"),
	("033", "Narok", "Rift Valley"),
	("034", "Kajiado", "Rift Valley"),
	("035", "Kericho", "Rift Valley"),
	("036", "Bomet", "Rift Valley"),
	("037", "Kakamega", "Western"),
	("038", "Vihiga", "Western"),
	("039", "Bungoma", "Western"),
	("040", "Busia", "Western"),
	("041", "Siaya", "Nyanza"),
	("042", "Kisumu", "Nyanza"),
	("043", "Homa Bay", "Nyanza"),
	("044", "Migori", "Nyanza"),
	("045", "Kisii", "Nyanza"),
	("046", "Nyamira", "Nyanza"),
	("047", "Nairobi", "Nairobi"),
)

#: {county: (sub-county, ...)} — Kenya's 290 constituencies, by the county they
#: sit in. Keys match `COUNTIES` exactly; `kenya.py` asserts that on every run
#: rather than trusting it, because a typo here would silently orphan a county's
#: whole sub-county list.
SUB_COUNTIES = {
	"Mombasa": (
		"Changamwe",
		"Jomvu",
		"Kisauni",
		"Nyali",
		"Likoni",
		"Mvita",
	),
	"Kwale": (
		"Msambweni",
		"Lunga Lunga",
		"Matuga",
		"Kinango",
	),
	"Kilifi": (
		"Kilifi North",
		"Kilifi South",
		"Kaloleni",
		"Rabai",
		"Ganze",
		"Malindi",
		"Magarini",
	),
	"Tana River": (
		"Garsen",
		"Galole",
		"Bura",
	),
	"Lamu": (
		"Lamu East",
		"Lamu West",
	),
	"Taita Taveta": (
		"Taveta",
		"Wundanyi",
		"Mwatate",
		"Voi",
	),
	"Garissa": (
		"Garissa Township",
		"Balambala",
		"Lagdera",
		"Dadaab",
		"Fafi",
		"Ijara",
	),
	"Wajir": (
		"Wajir North",
		"Wajir East",
		"Tarbaj",
		"Wajir West",
		"Eldas",
		"Wajir South",
	),
	"Mandera": (
		"Mandera West",
		"Banissa",
		"Mandera North",
		"Mandera South",
		"Mandera East",
		"Lafey",
	),
	"Marsabit": (
		"Moyale",
		"North Horr",
		"Saku",
		"Laisamis",
	),
	"Isiolo": (
		"Isiolo North",
		"Isiolo South",
	),
	"Meru": (
		"Igembe South",
		"Igembe Central",
		"Igembe North",
		"Tigania West",
		"Tigania East",
		"North Imenti",
		"Buuri",
		"Central Imenti",
		"South Imenti",
	),
	"Tharaka Nithi": (
		"Maara",
		"Chuka/Igambang'ombe",
		"Tharaka",
	),
	"Embu": (
		"Manyatta",
		"Runyenjes",
		"Mbeere South",
		"Mbeere North",
	),
	"Kitui": (
		"Mwingi North",
		"Mwingi West",
		"Mwingi Central",
		"Kitui West",
		"Kitui Rural",
		"Kitui Central",
		"Kitui East",
		"Kitui South",
	),
	"Machakos": (
		"Masinga",
		"Yatta",
		"Kangundo",
		"Matungulu",
		"Kathiani",
		"Mavoko",
		"Machakos Town",
		"Mwala",
	),
	"Makueni": (
		"Mbooni",
		"Kilome",
		"Kaiti",
		"Makueni",
		"Kibwezi West",
		"Kibwezi East",
	),
	"Nyandarua": (
		"Kinangop",
		"Kipipiri",
		"Ol Kalou",
		"Ol Jorok",
		"Ndaragwa",
	),
	"Nyeri": (
		"Tetu",
		"Kieni",
		"Mathira",
		"Othaya",
		"Mukurweini",
		"Nyeri Town",
	),
	"Kirinyaga": (
		"Mwea",
		"Gichugu",
		"Ndia",
		"Kirinyaga Central",
	),
	"Murang'a": (
		"Kangema",
		"Mathioya",
		"Kiharu",
		"Kigumo",
		"Maragwa",
		"Kandara",
		"Gatanga",
	),
	"Kiambu": (
		"Gatundu South",
		"Gatundu North",
		"Juja",
		"Thika Town",
		"Ruiru",
		"Githunguri",
		"Kiambu",
		"Kiambaa",
		"Kabete",
		"Kikuyu",
		"Limuru",
		"Lari",
	),
	"Turkana": (
		"Turkana North",
		"Turkana West",
		"Turkana Central",
		"Loima",
		"Turkana South",
		"Turkana East",
	),
	"West Pokot": (
		"Kapenguria",
		"Sigor",
		"Kacheliba",
		"Pokot South",
	),
	"Samburu": (
		"Samburu West",
		"Samburu North",
		"Samburu East",
	),
	"Trans Nzoia": (
		"Kwanza",
		"Endebess",
		"Saboti",
		"Kiminini",
		"Cherangany",
	),
	"Uasin Gishu": (
		"Soy",
		"Turbo",
		"Moiben",
		"Ainabkoi",
		"Kapseret",
		"Kesses",
	),
	"Elgeyo Marakwet": (
		"Marakwet East",
		"Marakwet West",
		"Keiyo North",
		"Keiyo South",
	),
	"Nandi": (
		"Tinderet",
		"Aldai",
		"Nandi Hills",
		"Chesumei",
		"Emgwen",
		"Mosop",
	),
	"Baringo": (
		"Tiaty",
		"Baringo North",
		"Baringo Central",
		"Baringo South",
		"Mogotio",
		"Eldama Ravine",
	),
	"Laikipia": (
		"Laikipia West",
		"Laikipia East",
		"Laikipia North",
	),
	"Nakuru": (
		"Molo",
		"Njoro",
		"Naivasha",
		"Gilgil",
		"Kuresoi South",
		"Kuresoi North",
		"Subukia",
		"Rongai",
		"Bahati",
		"Nakuru Town West",
		"Nakuru Town East",
	),
	"Narok": (
		"Kilgoris",
		"Emurua Dikirr",
		"Narok North",
		"Narok East",
		"Narok South",
		"Narok West",
	),
	"Kajiado": (
		"Kajiado North",
		"Kajiado Central",
		"Kajiado East",
		"Kajiado West",
		"Kajiado South",
	),
	"Kericho": (
		"Kipkelion East",
		"Kipkelion West",
		"Ainamoi",
		"Bureti",
		"Belgut",
		"Sigowet-Soin",
	),
	"Bomet": (
		"Sotik",
		"Chepalungu",
		"Bomet East",
		"Bomet Central",
		"Konoin",
	),
	"Kakamega": (
		"Lugari",
		"Likuyani",
		"Malava",
		"Lurambi",
		"Navakholo",
		"Mumias West",
		"Mumias East",
		"Matungu",
		"Butere",
		"Khwisero",
		"Shinyalu",
		"Ikolomani",
	),
	"Vihiga": (
		"Vihiga",
		"Sabatia",
		"Hamisi",
		"Luanda",
		"Emuhaya",
	),
	"Bungoma": (
		"Mount Elgon",
		"Sirisia",
		"Kabuchai",
		"Bumula",
		"Kanduyi",
		"Webuye East",
		"Webuye West",
		"Kimilili",
		"Tongaren",
	),
	"Busia": (
		"Teso North",
		"Teso South",
		"Nambale",
		"Matayos",
		"Butula",
		"Funyula",
		"Budalangi",
	),
	"Siaya": (
		"Ugenya",
		"Ugunja",
		"Alego Usonga",
		"Gem",
		"Bondo",
		"Rarieda",
	),
	"Kisumu": (
		"Kisumu East",
		"Kisumu West",
		"Kisumu Central",
		"Seme",
		"Nyando",
		"Muhoroni",
		"Nyakach",
	),
	"Homa Bay": (
		"Kasipul",
		"Kabondo Kasipul",
		"Karachuonyo",
		"Rangwe",
		"Homa Bay Town",
		"Ndhiwa",
		"Suba North",
		"Suba South",
	),
	"Migori": (
		"Rongo",
		"Awendo",
		"Suna East",
		"Suna West",
		"Uriri",
		"Nyatike",
		"Kuria West",
		"Kuria East",
	),
	"Kisii": (
		"Bonchari",
		"South Mugirango",
		"Bomachoge Borabu",
		"Bobasi",
		"Bomachoge Chache",
		"Nyaribari Masaba",
		"Nyaribari Chache",
		"Kitutu Chache North",
		"Kitutu Chache South",
	),
	"Nyamira": (
		"Kitutu Masaba",
		"West Mugirango",
		"North Mugirango",
		"Borabu",
	),
	"Nairobi": (
		"Westlands",
		"Dagoretti North",
		"Dagoretti South",
		"Lang'ata",
		"Kibra",
		"Roysambu",
		"Kasarani",
		"Ruaraka",
		"Embakasi South",
		"Embakasi North",
		"Embakasi Central",
		"Embakasi East",
		"Embakasi West",
		"Makadara",
		"Kamukunji",
		"Starehe",
		"Mathare",
	),
}


def county_names() -> tuple[str, ...]:
	"""The 47 county names, in county-code order."""
	return tuple(county for _code, county, _region in COUNTIES)


def sub_counties_of(county: str) -> tuple[str, ...]:
	"""The sub-counties under one county, or an empty tuple for an unknown one."""
	return SUB_COUNTIES.get(county, ())


def region_of(county: str) -> str | None:
	"""The province a county sits in. Carried, not built into the tree."""
	for _code, name, region in COUNTIES:
		if name == county:
			return region

	return None


def total_sub_counties() -> int:
	"""290, and a cheap way for a report to say so without importing the table."""
	return sum(len(names) for names in SUB_COUNTIES.values())
