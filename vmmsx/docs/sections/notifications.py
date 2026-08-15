# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Notifications section of the guide.

What a branch or the national society tells its people, and how one message
becomes one copy per person exactly once. Field tables are generated from the
doctype JSON, as everywhere else in this guide, and every claim names the file
or function it describes.
"""

from vmmsx.docs import doctypes

TITLE = "Notifications"
SUMMARY = "Alerts, advisories and news from a branch, fanned out once to everybody beneath it."

MODULE_DOCTYPES = ("VMMS Announcement", "VMMS Notification", "VMMS Announcement Type")


def render(w) -> None:
	w.h1(TITLE)

	_what_it_is(w)
	_the_doctypes(w)
	_who_hears_it(w)
	_idempotence(w)
	_the_two_channels(w)
	_the_feed(w)
	_who_may_send(w)
	_safety(w)
	_what_is_tested(w)


def _what_it_is(w) -> None:
	w.h2("What this module is")

	w.lead(
		"A society needs to tell its people things: a weather advisory, a change to a training"
		" date, news from the national office. Before this module the only channel was email, which"
		" reaches somebody's inbox and then competes with everything else in it, and leaves no"
		" record in the product of who was told what."
	)
	w.p(
		"So an announcement is a record. Somebody with the right role at the right place in the"
		" hierarchy writes one, publishes it, and it arrives in the notification list of every"
		" volunteer and member at or beneath that point — optionally as an email as well. The"
		" Notifications tab in the portal is where a person reads them."
	)
	w.p(
		"The module is deliberately not approvable. Routing a broadcast through the approval engine"
		" would mean a weather advisory waiting in somebody's queue, and the thing that makes an"
		" advisory worth sending is that it goes now. The control is who holds the role and where,"
		" decided before anybody writes anything, rather than a review after they have."
	)


def _the_doctypes(w) -> None:
	w.h2("The doctypes")

	w.p(
		"Three. The announcement is what somebody wrote; the notification is one person's copy of"
		" it; the type is the society's own vocabulary for what it sends."
	)

	for doctype in MODULE_DOCTYPES:
		w.h3(doctype)
		w.table(
			doctypes.FIELD_TABLE_HEADERS,
			doctypes.fields(doctype),
			doctypes.FIELD_TABLE_WIDTHS,
		)
		w.caption(f"Naming — {doctypes.naming_of(doctype)}")

	w.h3("Why the wording is not copied onto the copies")

	w.p(
		"VMMS Notification holds a recipient, a link to the announcement, and whether it has been"
		" read. It holds no title and no body. An announcement corrected after it went out is"
		" therefore corrected in every copy of it at once, whereas a thousand copies of a paragraph"
		" would be a thousand chances for the correction to miss one. Tested:"
		" test_the_wording_is_read_through_the_link_not_copied."
	)

	w.h3("Configuration and code, side by side on one form")

	w.p(
		"announcement_type is a Link to a doctype a society fills with its own words, and no code"
		" anywhere branches on a value of it — the same rule VMMS Template Category and VMMS Time"
		" Log Category already follow. urgency next to it is a closed Select the server owns, and"
		" it is the only field on the record that changes what happens. A society that adds a type"
		" called Emergency gets a new label; it does not get new behaviour, and nothing silently"
		" starts emailing because of the word."
	)


def _who_hears_it(w) -> None:
	w.h2("Who hears an announcement")

	w.p(
		"Two independent narrowings, resolved separately in vmmsx/notifications/services/audience.py"
		" and then intersected, because they answer different questions and conflating them is how"
		" a broadcast reaches the wrong county."
	)
	w.bullets(
		[
			"Where comes from core. The announcement's geo_node and everything beneath it, resolved"
			" through onerc_core.geo.services.adapter.get_descendants. This module never queries"
			" tabGeo Node and never assumes a depth, so a national office anchored at the root"
			" reaches the whole society and a ward reaches a ward, with neither a special case.",
			"Who comes from a dispatch table keyed by audience — everyone, volunteers, members —"
			" the same shape as the Member module's approval_mode. Adding a fourth audience is"
			" adding an entry to _RESOLVERS, never adding a branch.",
		]
	)

	w.h3("Three consequences worth stating")

	w.bullets(
		[
			"A person is resolved once. Somebody who is both a volunteer and a member appears in"
			" both resolvers and receives one copy, because the resolvers answer sets of Red"
			" Profiles and the union is taken before anything is written. Two copies of one"
			" advisory is the kind of bug that only shows up for exactly the people most involved"
			" in the society.",
			"Standing is read at the moment of sending. A suspended volunteer or a lapsed member is"
			" not written to: an announcement is addressed to the people a branch is responsible"
			" for right now, and somebody whose standing has ended stops hearing from it without"
			" anybody having to remember to remove them from a list.",
			"An unknown audience reaches nobody rather than everybody. The Select makes an unknown"
			" value hard to produce, but the failure modes are not symmetrical: delivering to no"
			" one is a message somebody notices is missing, and delivering to everyone is a message"
			" that cannot be recalled.",
		]
	)


def _idempotence(w) -> None:
	w.h2("Publishing twice delivers nothing twice")

	w.lead(
		"announce.publish() may be called any number of times and the second call observes that the"
		" work is done and returns the same answer. That is not a nicety here: a fan-out to a"
		" national society is a long write, and the realistic ways it gets called twice are a"
		" retried background job and somebody pressing a button again because the first press"
		" appeared to do nothing."
	)
	w.p(
		"The structure providing it is delivery.ensure(), which checks for a copy before writing"
		" one, and the uniqueness rule enforced on VMMS Notification itself. The two protect"
		" against different things: ensure() handles the ordinary retry cheaply, and the controller"
		" stops a second copy arriving by any other route at all, including a desk insert or a data"
		" import."
	)
	w.p(
		"The property that matters more than the double press is that a partial fan-out is safe to"
		" resume. If a publish dies halfway through, running it again finishes it rather than"
		" starting a second copy alongside the first. The fan-out is wired to on_update rather than"
		" to a single lifecycle moment precisely so that every realistic sequence — a draft"
		" published, a published announcement corrected, a publish that died and is saved again —"
		" runs the same idempotent service."
	)
	w.note(
		"Publishing is one-way, and the controller refuses to move a published announcement back to"
		" Draft. Copies are already in people's lists and have been read; a field that pretended to"
		" recall them would leave rows nothing owned, and a reader who saw an advisory would have"
		" no way to know it had been withdrawn. Correcting the wording is the supported path, and"
		" an expiry date is how a stale advisory leaves people's lists without the record of having"
		" sent it being destroyed."
	)


def _the_two_channels(w) -> None:
	w.h2("The in-app copy and the email reach different people")

	w.p(
		"The in-app copy needs a login. The email needs an address. Those are different sets of"
		" people and the difference is the point: a member enrolled at a desk by a clerk has a Red"
		" Profile and no user, so there is nowhere to put an in-app notification, and email is the"
		" only thing that reaches them. A volunteer who signed up online may have a login and a"
		" bad address."
	)
	w.p(
		"So audience.logins() and audience.emails() are resolved independently from the same set of"
		" Red Profiles, and neither is derived from the other. Somebody with no login is dropped"
		" from the in-app fan-out rather than counted as delivered, which is why delivered_count on"
		" the announcement can be lower than the number of people it was addressed to. That is"
		" honest rather than a bug: the count says how many people hold a copy."
	)
	w.p(
		"The email is queued rather than sent inline, because a national announcement is thousands"
		" of messages and a publish that blocks on an SMTP conversation per recipient is a publish"
		" that times out. It goes out bcc, so a society's whole membership list is not printed at"
		" the top of everybody's copy."
	)


def _the_feed(w) -> None:
	w.h2("One person's list, from both places it comes from")

	w.p(
		"A volunteer opening the Notifications tab expects to find two different kinds of thing"
		" there, and does not care that the two are stored differently: what their branch sent"
		" them, and what the system told them. The second is already written by Frappe to"
		" Notification Log, the approval engine's own assignments among it, and building a second"
		" copy of that would mean the same event arriving twice or arriving in the tab nobody"
		" thought to look at."
	)
	w.p(
		"So vmmsx/notifications/services/delivery.py merges the two, and the merge is dispatched"
		" rather than branched: _SOURCES holds one entry per source, each knowing how to read a"
		" page of its own rows, turn one into the shared DTO, and mark one read. A third source"
		" later is a third entry, and no reader, counter or endpoint gains a comparison."
	)
	w.bullets(
		[
			"The feed is sorted on urgency and then on time, unread before read, so an urgent"
			" advisory sent on Monday stays above Thursday's routine news until it has been dealt"
			" with. That ordering is the whole behavioural difference the urgency field buys, and"
			" it is computed on the server: the frontend renders the order it is given.",
			"Reading somebody else's notifications is not possible rather than not allowed. Every"
			" query is filtered on frappe.session.user and no function in the module takes a user"
			" argument — the same shape as my_memberships, my_volunteer and approvals.my_queue.",
			"A notification's id is meaningless without the source beside it, and the pair travels"
			" together so mark_read can dispatch on it. The frontend passes back what it was given"
			" and constructs neither. A pair naming somebody else's notification reports that"
			" nothing changed rather than raising, so the endpoint cannot be used to find out"
			" whether a given notification exists.",
		]
	)


def _who_may_send(w) -> None:
	w.h2("Who may speak for a branch")

	w.p(
		"VMMS Announcement is registered as geo-scopeable through core's onerc_scopeable_doctypes"
		" hook, on its geo_node, naming vmms_announcement_scope_role — a Custom Field vmmsx owns on"
		" National Society Settings, installed by vmmsx/patches/setup_notification_module.py. Core's"
		" doctype is not edited, exactly as with every other scope role in this guide."
	)
	w.p(
		"Scoping is doing more work here than it does elsewhere. For a membership it decides who"
		" may read a record. For an announcement it also decides who may write one and from where,"
		" and writing one sends a message to every volunteer and member beneath that node. Core's"
		" Geo Assignment is what stops a branch coordinator anchoring an announcement at the"
		" country and addressing the whole society: the anchor has to sit inside the scope they"
		" hold, which is the same check that governs everything else they touch."
	)
	w.p(
		"The field ships empty and empty fails closed, so no non-administrator can broadcast"
		" anything until a society names the role. That is the right default for the one action in"
		" this app whose blast radius is every volunteer in the country. There is deliberately no"
		" whitelisted send endpoint: an announcement is written and published on the desk, and"
		" whitelisting a broadcast would put a second answer in front of that check."
	)
	w.note(
		"The announcement types are not seeded. News, Alert and Advisory read like obvious defaults"
		" and are not: they are a society's own vocabulary, and shipping three English nouns would"
		" be this app deciding what a national society calls the things it sends."
	)


def _safety(w) -> None:
	w.h2("Text is text, and a link goes somewhere sane")

	w.p(
		"The body is a plain Text field, rendered as a string wherever it is shown. A rich text"
		" field here would mean a person able to write announcements could put scripts into a page"
		" served to every volunteer in the society, and the ability to broadcast is not the same"
		" permission as the ability to run code in somebody's browser. The email body is escaped"
		" for the same reason."
	)
	w.p(
		"link_href is refused on save unless it is site-relative or an http, https, mailto or tel"
		" address. The rule lives in vmmsx/links.py and is shared with VMMS Content Block, which"
		" needs the identical answer for the identical reason — an authorised person types a"
		" destination and every reader clicks it. Anything outside the allow-list is refused rather"
		" than the dangerous schemes being named, so a scheme nobody thought of is refused too."
	)
	w.p(
		"Notification Log's subject is written by whichever app raised it, so delivery.py strips"
		" markup from it before it reaches a page. The guarantee is kept on the server rather than"
		" trusted to the frontend, which is where the content module already puts it."
	)


def _what_is_tested(w) -> None:
	w.h2("What is tested")

	w.p("23 integration tests in vmmsx/notifications/tests/test_announce.py.")
	w.table(
		("Area", "What it proves"),
		[
			[
				"The geo boundary",
				"A region's announcement reaches its branches; a branch's does not leak up to the"
				" region above it, and a sibling branch hears nothing at all.",
			],
			[
				"Idempotence",
				"Publishing twice creates no second copy and reports created: 0. A fan-out"
				" resumed after somebody new has joined writes only the new person. One person"
				" cannot hold two copies by any route, including a direct insert.",
			],
			[
				"Audience",
				"volunteers narrows to volunteers; somebody who is both a volunteer and a member"
				" receives exactly one copy; a suspended volunteer stops hearing from the branch;"
				" an unknown audience resolves to nobody.",
			],
			[
				"The two channels",
				"A person with no login is addressed but not delivered to in-app, and their"
				" address is still resolved for the email channel.",
			],
			[
				"The lifecycle",
				"A draft is delivered to nobody; a published announcement cannot be moved back to"
				" Draft; delivered_count and published_on record the reach; an expired"
				" announcement leaves the feed while its copies survive.",
			],
			[
				"One person's feed",
				"The feed is only ever your own; unread counts and clears; marking somebody"
				" else's notification read does nothing and leaves it unread; an unknown source"
				" is false rather than an exception; urgent sorts above routine; mark-all clears"
				" the list; a corrected announcement is corrected in every copy.",
			],
			[
				"Safety and dispatch",
				"A javascript link is refused and a site-relative one is accepted; the urgency"
				" table ranks and mails by dispatch, and an invented value ranks lowest and mails"
				" not.",
			],
		],
		(1.35, 4.65),
	)
	w.p(
		"Real geo levels and nodes through core's own fixtures, real volunteers and real"
		" memberships, and nothing about the resolution or the delivery mocked. Each test builds"
		" its own subtree of geo nodes, because Frappe rolls the test transaction back once per"
		" class rather than once per method and every count in the file is a count of who heard"
		" something."
	)
