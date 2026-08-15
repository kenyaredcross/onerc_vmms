# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Buzz section of the guide (BUZZ-01 and BUZZ-02).

Still the shortest section in the guide, because the seam it documents is still
deliberately thin: one optional field written onto an app vmmsx does not own,
and one read-only listing of what that app already publishes. There is no vmmsx
doctype behind either, so there is no generated field table here — the field
lives on Buzz's own `Buzz Event`, and its one description is quoted from the
patch that installs it, the same words an administrator sees on the field.
"""

TITLE = "Buzz"
SUMMARY = "Two crossings onto Buzz: one optional geo field, and a read-only event listing."


def render(w) -> None:
	w.h1(TITLE)

	_what_it_is(w)
	_the_field(w)
	_why_optional(w)
	_the_listing(w)
	_graceful_absence(w)
	_what_is_tested(w)


def _what_it_is(w) -> None:
	w.h2("What BUZZ-01 is")

	w.lead(
		"Buzz is an events and ticketing app this bench also runs. BUZZ-01 places a Buzz event in"
		" the society's geo hierarchy — nothing more. It is not an integration in the sense any"
		" other seam in this guide is: there is no data flowing in either direction, no hook, and"
		" no reading of Buzz's own model beyond the one field this seam adds."
	)
	w.p(
		"BUZZ-02 added the second crossing and it runs the other way: the portal's Events screen"
		" reads the events a society has already published in Buzz and lists them. It is covered"
		" under \u201cBrowse here, book there\u201d below."
	)
	w.p(
		"vmmsx/buzz/services/geo.py and vmmsx/buzz/services/events.py are the only files in the"
		" app that name Buzz's event doctype."
		" vmmsx/buzz/tests/test_delegation.py asserts that structurally, against the source, the"
		" same way test_delegation.py already does for the learning and payment seams in the"
		" Member section: Buzz Event may be named by the two halves of the seam and by the patch"
		" that installs its field, and by nothing else in the app."
	)
	w.p(
		"vmmsx does not declare buzz in required_apps. A society running vmmsx without Buzz"
		" installed at all is an ordinary, fully supported state, not a degraded one."
	)

	w.h3("What this deliberately does not do")

	w.p(
		"An attendee stays Buzz-native. There is no bridge here from a Buzz booking, ticket or"
		" check-in to a Red Profile, a VMMS Volunteer or a VMMS Member — that bridge (RP-14) was"
		" considered and explicitly deferred, as a separate decision for a separate build. Placing"
		" an event in the geo hierarchy says nothing about who is attending it, and no file in"
		" vmmsx names Event Booking, Event Booking Attendee, Event Ticket, Event Ticket Type,"
		" Event Check In or Event Feedback at all — not even the seam itself."
	)


def _the_field(w) -> None:
	w.h2("The one field")

	w.table(
		("Field", "On", "What it does"),
		[
			[
				"geo_node",
				"Buzz Event",
				"A Link to Geo Node. Where this event sits in the society's geo hierarchy, if"
				" anywhere. Optional: an event may be placed in the hierarchy, but nothing"
				" requires it. Owned by vmmsx.",
			]
		],
		(1.35, 1.65, 3.50),
	)
	w.p(
		"Installed as a Custom Field by vmmsx/patches/setup_buzz_seam.py, positioned after"
		" Buzz's own venue field — never by editing Buzz's schema directly, the same pattern the"
		" Member module already uses for the ACC-03 anchor-level field it owns on core's National"
		" Society Settings. The patch is idempotent: re-running it finds the field already there"
		" and changes nothing."
	)
	w.p(
		"geo.geo_node_of(event) is the one read this seam performs, and it reads only the field"
		" vmmsx itself installed — never an event's title, category, host, schedule or anything"
		" else Buzz's own model carries."
	)


def _why_optional(w) -> None:
	w.h2("Why the anchor is optional, not mandatory")

	w.p(
		"Every operational record vmmsx owns outright carries a mandatory Geo Node — ACC-02 says"
		" so, and says it precisely because an unplaced VMMS record is invisible to this app's own"
		" geo scoping and unroutable by its own approval engine. Buzz Event is not one of those"
		" records. It is Buzz's own doctype, created through Buzz's own native flows, which know"
		" nothing about vmmsx, a geo hierarchy, or ACC-02 at all."
	)
	w.p(
		"Making the anchor mandatory would reach into an app vmmsx does not own and force every"
		" event a society creates — including a purely virtual one with no geographic scope"
		" whatsoever — through a constraint this app invented. That is the leak running the other"
		" way: not vmmsx reading Buzz's model, but vmmsx imposing on it. Optional was the only"
		" choice consistent with BUZZ-01 being a seam rather than a takeover."
	)


def _the_listing(w) -> None:
	w.h2("BUZZ-02 — browse here, book there")

	w.lead(
		"The portal's Events screen shows real events, read out of Buzz. vmmsx keeps no event"
		" record of its own and invents no second notion of what is visible: the filter is Buzz's"
		" own is_published flag, so an event a society has published in Buzz is an event the portal"
		" shows, and one it has not is one the portal does not know exists."
	)
	w.p(
		"vmmsx/buzz/services/events.py reads title, summary, date, time, venue, medium, category,"
		" image and route, and builds an explicit DTO field by field. That matters more here than"
		" it does elsewhere in the app: the row comes from another app's schema, which this one"
		" neither controls nor reviews, so handing a caller the raw row would leak whatever Buzz"
		" gained since anybody last looked."
	)

	w.h3("Where the seam stops")

	w.p(
		"Every card's call to action is a full navigation to Buzz's own event page at /b/<route>."
		" Buzz owns ticket types, coupons, payment, guest verification and check-in, and each of"
		" those is a flow with money or identity in it. A vmmsx endpoint wrapping any of them would"
		" be a second implementation of a rule that has to stay in step with Buzz's forever, and"
		" the first time the two disagreed somebody would be charged the wrong amount. So there is"
		" no booking endpoint in vmmsx and no plan for one; an event with no route yet renders"
		" without its button rather than with a link to a 404."
	)

	w.h3("Two rules that are not what they look like")

	w.bullets(
		[
			"Upcoming is decided on the end date, not the start date, so a four-day training that"
			" began yesterday is still on the page for somebody deciding whether to turn up"
			" tomorrow. Buzz leaves end_date empty for a single-day event, so the two dates are"
			" compared with an OR rather than coalesced: a single-day event today matches on its"
			" start date, and one from last week matches neither.",
			"Geo is a filter, never a gate. Because BUZZ-01 made the anchor optional, most events a"
			" society runs carry none, and filtering the unplaced ones out would hide the majority"
			" of its calendar from the people it runs it for. So an unplaced event is shown to"
			" everybody, and narrowing by place only ever narrows among events that actually"
			" declared one. That is the deliberate reverse of ACC-02's rule for vmmsx's own"
			" records, because this is Buzz's record and not ours.",
		]
	)
	w.p(
		"vmmsx/api/events.py is the whitelisted door and adds no logic. Neither of its two methods"
		" is allow_guest: the public landing page's events are wording an administrator typed into"
		" content blocks, and api/content.py::surface remains the only guest-readable endpoint in"
		" the app."
	)


def _graceful_absence(w) -> None:
	w.h2("Graceful absence")

	w.p(
		"The same pattern the LMS and payments seams already use. geo.is_available() asks"
		" frappe.get_installed_apps() rather than importing buzz and catching failure — an app can"
		" sit in the bench without being installed on this site, which is the case that actually"
		" bites, and a question answered by an exception cannot be asked at configuration time."
	)
	w.p(
		"setup_buzz_seam.install_geo_anchor_field() checks is_available() before doing anything at"
		" all, so on a site with no Buzz the install is dormant: nothing is created, nothing"
		" throws, and the patch completes exactly as it would on a site where Buzz has never"
		" existed. geo.geo_node_of() answers None rather than raising for the same reason."
	)
	w.note(
		"Buzz really is installed on this bench, so the tests exercise the real Buzz Event doctype"
		" and the real Custom Field the patch installs. Absence is mocked — frappe.get_installed_apps()"
		" patched to the real list minus buzz — because a test cannot uninstall an app that is"
		" genuinely there, the same discipline test_payments_absent.py uses for the payments seam."
	)


def _what_is_tested(w) -> None:
	w.h2("What is tested")

	w.p("32 integration tests, across three files, all under vmmsx/buzz/tests/.")
	w.table(
		("Test file", "Tests", "What it proves"),
		[
			[
				"test_geo.py",
				"9",
				"The Custom Field exists on Buzz Event, is a Link to Geo Node, and is optional;"
				" a real event can be anchored to a real Geo Node and the anchor reads back"
				" correctly; an event may be created with no anchor at all. With Buzz mocked"
				" absent: is_available() answers false, the install patch runs to completion"
				" without touching anything or raising, and geo_node_of() answers None rather"
				" than raising. Re-running the patch with Buzz present changes nothing.",
			],
			[
				"test_events.py",
				"19",
				"A published upcoming event appears and an unpublished one does not; a finished"
				" one drops off but one under way stays, and a single-day event with no end date"
				" still shows on the day; soonest first; search narrows on the title. An unplaced"
				" event is shown to everybody, an event anchored elsewhere is not, and narrowing"
				" by a parent admits what is beneath it. The card carries a link to Buzz's own"
				" page, the DTO is exactly the fifteen fields the seam builds, and the listing is"
				" bounded. With Buzz mocked absent both readers answer empty and the endpoint"
				" reports available: false rather than an empty calendar.",
			],
			[
				"test_delegation.py",
				"4",
				"Buzz Event is named by exactly the two halves of the seam and its install patch,"
				" and nowhere else in the app; none of Buzz's identity or ticketing doctypes —"
				" bookings, attendees, tickets, check-ins, feedback — are named anywhere in vmmsx,"
				" not even by the seam itself; the detector is proved against a planted leak.",
			],
		],
		(1.55, 0.55, 4.40),
	)
