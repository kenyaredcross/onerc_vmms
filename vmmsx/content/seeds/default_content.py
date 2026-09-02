# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The slots every screen has, and society-neutral wording to start them with.

**This is data, not behaviour.** It declares which editable slots exist and what
they say before anybody has edited them. Nothing here is read at render time by
name; the frontend asks for a surface and draws whatever blocks it gets back.

Two rules shape the wording below, and both matter more than it reading well:

- **No country, currency, count or society name appears in it.** A national
  society is not this app's to assume, so the defaults describe the *slot* in
  ordinary words a society will replace. The worked Kenya example, with its own
  copy and its own photography, is `vmmsx/seed/kenya.py`, and it is the only
  place in this app that knows what a county is.
- **No image is shipped as a default.** An empty image slot draws a branded
  placeholder with an upload control on it, which is a better first run than a
  photograph of somewhere the society does not work.

Adding a slot is adding a row here. Deleting one is deleting the row and the
component that asked for it; a key nobody asks for is harmless, and a component
asking for a key nobody seeded renders its own fallback rather than breaking.
"""

#: Slots the product no longer draws, deleted on every migrate by
#: `blocks.retire()`. A key belongs here only once the screen reading it is
#: gone, so what is removed is a row that could still be edited and would change
#: nothing on any page.
#:
#: The first two held the product's name and a short society name typed onto the
#: page. The lockup now reads the society's real logo and name from National
#: Society Settings through `api/society.py::branding`, so a block beside it was
#: a second copy of an identity core already owns — stale the moment somebody
#: uploaded a logo, and a vendor's name on a society's screens besides.
#:
#: The third is the same mistake about a number instead of a name. The first
#: statistic is how many volunteers are on the register, and the register is
#: what knows: `api/society.py::figures` counts it and rounds it, and the strip
#: draws that. A typed figure beside it was correct on the day somebody typed it
#: and wrong the day after. The *caption* is still a block, because what a
#: society calls its volunteers is a society's own word.
#: The rest are lines of explanation under a heading, and every one of them
#: described the screen it sat on: "What your society has on, and which of it
#: you have said you are coming to" over a calendar, "Where your application
#: stands, the hours you have logged, and what is coming up" over a dashboard
#: showing exactly those three things. A heading and the page under it say it
#: already, so the slots are gone rather than reworded — there is nothing for a
#: society to write in them that the page is not already showing.
RETIRED = (
	"chrome.brand.name",
	"chrome.brand.society",
	"landing.stat1.value",
	"portal.home.intro",
	"portal.hours.intro",
	"portal.calendar.intro",
	"portal.calendar.note",
	"portal.membership.plans.blurb",
	"portal.events.attending.calendar_note",
)

# Links this app shipped pointing at nothing, and where they should go instead.
# `None` means the item leaves the navigation altogether. Read by
# `blocks.relink()` on every migrate, and matched on the exact broken value, so
# a society that has already pointed one of these somewhere of its own keeps it.
#
# `#volunteer`, `#membership` and `#events` are deliberately absent: those
# anchors were dead too, and the fix was to give the sections they name their
# `id` in `Landing.tsx` rather than to move the links off them.
# The events button changed from "Get tickets" to "Attend" when the card stopped
# handing people off and started opening the society's own details panel. Only
# where the old wording is still there — a society that has renamed it keeps it.
#
# The two join buttons said "free", which is a claim this app is in no position
# to make: a society's membership types carry a fee, `PlanCards` prices them,
# and the closing panel of the same page invites somebody onto that road. The
# word had to go from both, and "us" says the thing that is actually true.
#
# The attendance wording below is one change, not nine. Saying yes to an event
# was "I'm going" in the calendar, "Attend" on a card and "You're going" on the
# panel, and taking it back was "I can't make it", "Can't make it" and "I can no
# longer come" — six phrasings of two actions, none of them the words anybody
# would use, and all of them first person as though the button were speaking.
# It is Attend and Cancel now, and the state either of them leaves behind is
# Attending, wherever it is drawn.
RELABELLED = {
	"portal.events.card.action": ("Get tickets", "Attend"),
	"chrome.action.join": ("Join free", "Join us"),
	"landing.cta.button": ("Join free today", "Join us today"),
	"portal.calendar.day.attend": ("I'm going", "Attend"),
	"portal.calendar.day.withdraw": ("I can't make it", "Cancel"),
	"portal.calendar.day.badge": ("Going", "Attending"),
	"portal.calendar.legend.mine": ("You are going", "Attending"),
	"portal.calendar.legend.other": ("Something on", "Scheduled"),
	"portal.events.attend.confirmed": ("You're going", "Attending"),
	"portal.events.attend.withdraw": ("I can no longer come", "Cancel"),
	"portal.events.attend.calendar": ("Add to my calendar", "Add to calendar"),
	"portal.events.attending.going": ("Going", "Attending"),
	"portal.events.attending.withdraw": ("Can't make it", "Cancel"),
	"portal.events.attending.label": ("Events you are going to", "Your events"),
	"portal.events.hero.eyebrow": ("Find your next experience", "What's on"),
	"portal.events.attend.claim": (
		"Your branch has been told to expect you. This does not book a ticket or hold a place.",
		"Your branch has been told to expect you. This does not hold a place.",
	),
	"admin.communication.lead": (
		"Say something to the volunteers and members your branches cover. Choose who hears"
		" it before you write it — this is the one thing here that cannot be taken back.",
		"Sent to the volunteers and members your branches cover.",
	),
}

DEAD_LINKS = {
	"#training": None,
	"#branches": "/portal/locations",
	# The hero's secondary link. There is no "how it works" section either.
	"#how-it-works": None,
}

# (surface_key, surface_name, description, readable_by_guests)
SURFACES = (
	(
		"chrome",
		"Shared Chrome",
		"The wording that appears on every screen: the product name, the society's short name,"
		" the sign-in and join buttons. Edited once, changed everywhere.",
		True,
	),
	(
		"landing",
		"Guest Landing Page",
		"The public home page a visitor sees before signing in. Every heading, paragraph, button"
		" and photograph on it is a block in this surface.",
		True,
	),
	(
		"login",
		"Sign In and Set Password",
		"The wording either side of the sign-in page: the panel a visitor reads while they type,"
		" and the heading over each of its panels. Also the set-password page the welcome email"
		" opens. The field labels and buttons on those pages are the framework's own and are"
		" translated rather than edited here.",
		True,
	),
	(
		"portal",
		"Volunteer Portal",
		"Headings, section labels and empty-state wording across the signed-in volunteer and member screens.",
		False,
	),
	(
		"admin",
		"Manager Console",
		"Headings and section labels across the manager side: the review queue, the registry"
		" and the reports.",
		False,
	),
)


def _block(key, label, surface, sequence, text="", href="", notes=""):
	row = {
		"content_key": key,
		"label": label,
		"surface": surface,
		"sequence": sequence,
	}
	if text:
		row["text_value"] = text
	if href:
		row["link_href"] = href
	if notes:
		row["description"] = notes
	return row


def _chrome():
	# The lockup is deliberately absent from this surface. It is the society's
	# own logo and name, read live from National Society Settings through
	# `api/society.py::branding` — identity has one home, and a content block
	# beside it was a second copy that went stale the moment somebody uploaded a
	# logo. `chrome.brand.name` and `chrome.brand.society` were those blocks;
	# they are gone, and `patches/setup_content_module.py` retires any left on a
	# site that has them.
	s = "chrome"
	return [
		_block("chrome.action.signin", "Sign in button", s, 30, "Sign in", "/login"),
		_block("chrome.action.join", "Join button", s, 40, "Join us", "/portal/join"),
		_block("chrome.action.signout", "Sign out link", s, 50, "Sign out"),
	]


def _landing_nav():
	s = "landing"
	# Every one of these has to lead somewhere, and for a long time none of them
	# did: the three anchors named sections that carried no `id`, and `#training`
	# and `#branches` named sections that do not exist on this page at all. Five
	# links, five of them dead.
	#
	# The first three are anchors now that `Landing.tsx` gives those sections
	# their ids. `#training` is gone, because there is no training section to
	# scroll to and inventing one to justify a link is the wrong way round.
	# Branches goes to the map, which is a real, public, working page — and the
	# one a visitor most often wants, because "where are you" is the question
	# somebody asks before any of the others.
	#
	# The fifth slot ships empty, and the note on each block explains that an
	# empty one is dropped. That is how a society adds its own.
	items = (
		("Volunteering", "#volunteer"),
		("Membership", "#membership"),
		("Events", "#events"),
		("Branches", "/portal/locations"),
		("", ""),
	)
	rows = []
	for i, (text, href) in enumerate(items, start=1):
		rows.append(
			_block(
				f"landing.nav.item{i}",
				f"Top navigation, item {i}",
				s,
				100 + i,
				text,
				href,
				notes="Leave the text empty to drop this item from the navigation bar.",
			)
		)
	return rows


def _landing_hero():
	s = "landing"
	return [
		_block(
			"landing.hero.image",
			"Hero photograph",
			s,
			200,
			notes="A wide photograph, at least 1600px across. The overlay card sits on the left, so keep the left third uncluttered.",
		),
		_block("landing.hero.eyebrow", "Hero eyebrow", s, 210, "THE NATIONAL SOCIETY"),
		_block("landing.hero.headline", "Hero headline", s, 220, "Show up for your community."),
		_block(
			"landing.hero.body",
			"Hero paragraph",
			s,
			230,
			"One profile for volunteering, training, deployments and membership, across every branch.",
		),
		_block(
			"landing.hero.cta_primary",
			"Hero primary button",
			s,
			240,
			"Become a volunteer",
			"/portal/join?path=volunteer",
		),
		_block("landing.hero.cta_secondary", "Hero secondary link", s, 250),
	]


def _landing_cards():
	s = "landing"
	cards = (
		(
			"Volunteer",
			"Give time and skills. Apply once, get verified by your branch, deploy when it matters.",
			"Apply now",
			"/portal/join?path=volunteer",
		),
		(
			"Become a member",
			"Join the Society formally. Voting rights, a verifiable certificate, and a Society that counts you.",
			"Compare plans",
			"/portal/join?path=member",
		),
		(
			"Train and certify",
			"Courses with certificates issued straight to your profile, and kept current for you.",
			# No button, because there is nowhere honest to send a visitor: course
			# browsing is one of the screens this app draws as `<NotBuilt>`, and a
			# card is not the place to make a promise the product does not keep.
			# The card still says what the society does; a society that has an LMS
			# to point at fills the link in with the pencil.
			"",
			"",
		),
		(
			"Join an event",
			"Public events run by your branch, open to anyone who wants to take part.",
			"See events",
			"#events",
		),
	)
	rows = []
	for i, (title, body, link, href) in enumerate(cards, start=1):
		base = 300 + i * 10
		rows += [
			_block(
				f"landing.card{i}.image",
				f"Card {i} photograph",
				s,
				base,
				notes="Roughly 2:1. Shown about 300px wide.",
			),
			_block(f"landing.card{i}.title", f"Card {i} title", s, base + 1, title),
			_block(f"landing.card{i}.body", f"Card {i} paragraph", s, base + 2, body),
			_block(f"landing.card{i}.link", f"Card {i} link", s, base + 3, link, href),
		]
	return rows


def _landing_bands():
	s = "landing"
	return [
		_block(
			"landing.band1.image",
			"First photo band, photograph",
			s,
			400,
			notes="Wide. The text block sits on the right, so keep the right third uncluttered.",
		),
		_block("landing.band1.eyebrow", "First photo band, eyebrow", s, 410, "OPPORTUNITIES THAT FIND YOU"),
		_block(
			"landing.band1.heading",
			"First photo band, heading",
			s,
			420,
			"Matched to your skills, not blasted to everyone.",
		),
		_block(
			"landing.band1.body",
			"First photo band, paragraph",
			s,
			430,
			"Deployments are scored against your certifications, languages and availability. You see"
			" the match, and the exact training that closes the gap.",
		),
		_block(
			"landing.band1.cta",
			"First photo band, link",
			s,
			440,
			"Browse opportunities",
			"/portal/opportunities",
		),
		_block(
			"landing.band2.image",
			"Second photo band, photograph",
			s,
			500,
			notes="Wide. The text block sits on the left.",
		),
		_block("landing.band2.eyebrow", "Second photo band, eyebrow", s, 510, "MEMBERSHIP"),
		_block(
			"landing.band2.heading", "Second photo band, heading", s, 520, "Be counted. Renew in two taps."
		),
		_block(
			"landing.band2.body",
			"Second photo band, paragraph",
			s,
			530,
			"Pay however your society collects, download a certificate you can verify, and carry your"
			" membership with you when you move branch.",
		),
		_block(
			"landing.band2.cta_primary",
			"Second photo band, button",
			s,
			540,
			"Join as a member",
			"/portal/join?path=member",
		),
		_block(
			"landing.band2.cta_secondary", "Second photo band, link", s, 550, "Compare plans", "#membership"
		),
	]


def _landing_stats():
	"""Four figures, and the first of them is not a slot anybody fills in.

	Statistic one is how many volunteers the society has, counted off the
	register by `api/society.py::figures` and rounded there. There is no
	`landing.stat1.value` block, and `RETIRED` deletes it from sites that still
	carry one: a number a person types is a number that stops being true, and
	this one stops being true every time a branch verifies an application.

	Its caption stays editable and ships with a word, because "volunteers" is
	what this app counted and a society is entitled to call them something else.
	The other three are the society's own to fill in or leave empty.
	"""
	s = "landing"
	rows = [_block("landing.stat1.label", "Statistic 1, caption", s, 611, "VOLUNTEERS")]

	for i in range(2, 5):
		base = 600 + i * 10
		rows += [
			_block(
				f"landing.stat{i}.value",
				f"Statistic {i}, number",
				s,
				base,
				notes="Leave empty to hide this statistic. The row draws only the ones that have a number.",
			),
			_block(f"landing.stat{i}.label", f"Statistic {i}, caption", s, base + 1),
		]
	return rows


def _landing_events():
	"""The public events teaser, which is live now and typed only as a fallback.

	The band draws the next three published events from Buzz through
	`api/events.py::teaser`. Nobody types those; a society that has scheduled
	something has it on its front page the moment it publishes it.

	**The typed rows below stayed.** They are what the band falls back to when
	there is nothing live to show — a site without Buzz, or a season with nothing
	in it — so a society that has always kept a hand-written teaser keeps it, and
	one that has not gets a band that hides itself rather than an empty heading.
	Live records win whenever there are any.

	`landing.events.action`, `.more` and `.join` belong to the live half: the
	words on a card's link, and the sentence and the link under the row that
	tells a signed-out visitor the rest of the calendar is for people who have
	joined. The per-event `cta` blocks belong to the typed half and are drawn
	only there.
	"""
	s = "landing"
	rows = [
		_block("landing.events.heading", "Events section, heading", s, 700, "Upcoming public events"),
		_block("landing.events.link", "Events section, link", s, 710, "All events", "#events"),
		_block("landing.events.action", "Events section, card link", s, 712, "Details"),
		_block(
			"landing.events.more",
			"Events section, invitation",
			s,
			714,
			"These are the ones open to everybody. Volunteers see the whole calendar, and can say"
			" they are coming.",
			notes="Shown under the row to visitors who are not signed in.",
		),
		_block("landing.events.join", "Events section, invitation link", s, 716, "Become a volunteer"),
	]
	for i in range(1, 4):
		base = 720 + i * 10
		rows += [
			_block(
				f"landing.event{i}.date",
				f"Event {i}, date",
				s,
				base,
				notes="Shown in the date tile. Leave empty to hide this event entirely.",
			),
			_block(f"landing.event{i}.title", f"Event {i}, title", s, base + 1),
			_block(f"landing.event{i}.meta", f"Event {i}, time and place", s, base + 2),
			_block(f"landing.event{i}.cta", f"Event {i}, link", s, base + 3, "RSVP"),
		]
	return rows


def _landing_close():
	s = "landing"
	# The seven Fundamental Principles of the Movement. Universal to every
	# national society rather than particular to one, which is why they are here
	# and not in a society seed. Still editable: they are text on a page.
	principles = (
		"HUMANITY",
		"IMPARTIALITY",
		"NEUTRALITY",
		"INDEPENDENCE",
		"VOLUNTARY SERVICE",
		"UNITY",
		"UNIVERSALITY",
	)
	rows = [
		_block("landing.cta.heading", "Closing panel, heading", s, 800, "Ready when you are."),
		_block(
			"landing.cta.body",
			"Closing panel, paragraph",
			s,
			810,
			"Register in five minutes. Your branch confirms your record, and the Society gains one"
			" more person who shows up.",
		),
		_block("landing.cta.button", "Closing panel, button", s, 820, "Join us today", "/portal/join"),
	]
	for i, word in enumerate(principles, start=1):
		rows.append(_block(f"landing.principle{i}", f"Fundamental principle {i}", s, 830 + i, word))
	return rows


def _landing_footer():
	s = "landing"
	rows = [
		_block(
			"landing.footer.emergency",
			"Footer emergency line",
			s,
			900,
			notes="The society's emergency number and hours. Leave empty to hide the line.",
		),
		_block("landing.footer.copyright", "Footer copyright", s, 910),
	]
	links = ("Volunteering", "Membership", "Events", "Branch directory", "Privacy", "Terms")
	for i, text in enumerate(links, start=1):
		rows.append(
			_block(
				f"landing.footer.link{i}",
				f"Footer link {i}",
				s,
				920 + i,
				text,
				notes="Leave the text empty to drop this link from the footer.",
			)
		)
	return rows


def _login():
	# The sign-in page is a Jinja page rather than a React screen, so these are
	# read server-side by `vmmsx/auth_page.py` and there is no pencil on the page
	# itself: they are edited from the desk like any other block. That is the only
	# difference, and it is a property of the page being served before anybody has
	# signed in — an edit control on it would be a control drawn for a stranger.
	#
	# What is deliberately *not* here: "Email", "Password", "Forgot password?",
	# "Create Account". Those are the framework's own login strings, shared with
	# the flows this page inherits whole, and moving them into blocks would take
	# them out of Frappe's translations to gain a society nothing.
	s = "login"
	return [
		_block(
			"login.panel.image",
			"Sign-in page photograph",
			s,
			10,
			notes="A tall photograph for the panel beside the form, at least 1200px across. It is"
			" laid under a dark wash with the wording over it, so a busy or bright image reads"
			" poorly. Leave it empty for a plain panel.",
		),
		_block(
			"login.panel.headline",
			"Sign-in panel headline",
			s,
			20,
			"One account for membership, volunteering and training.",
		),
		_block(
			"login.panel.body",
			"Sign-in panel paragraph",
			s,
			30,
			"Your record follows you between branches. Certificates, hours and deployments stay"
			" in one place.",
		),
		_block("login.signin.eyebrow", "Sign in, eyebrow", s, 100, "Sign in"),
		_block("login.signin.title", "Sign in, heading", s, 110, "Welcome back"),
		_block("login.signin.prompt", "Sign in, footer question", s, 120, "New to the society?"),
		_block(
			"login.signin.action",
			"Sign in, footer link",
			s,
			130,
			"Create an account",
			notes="Opens the account panel on this same page. It is not the registration form:"
			" a person makes an account first and registers afterwards.",
		),
		_block("login.signup.eyebrow", "Create account, eyebrow", s, 200, "Get started"),
		_block("login.signup.title", "Create account, heading", s, 210, "Create your account"),
		_block(
			"login.signup.body",
			"Create account, paragraph",
			s,
			220,
			"We will email you a link to set a password. Registering as a volunteer or a member"
			" comes afterwards.",
		),
		_block("login.signup.prompt", "Create account, footer question", s, 230, "Already have one?"),
		_block("login.signup.action", "Create account, footer link", s, 240, "Sign in"),
		# The panel that replaces the form once the account exists. The form used
		# to stay on screen with a green line above it and the word "Success" on
		# the button, which reads as though there is still something to fill in.
		# The address is drawn by the page, not by these words, so none of them
		# needs to interpolate anything.
		_block("login.signup.sent_eyebrow", "Account created, eyebrow", s, 250, "Almost there"),
		_block("login.signup.sent_title", "Account created, heading", s, 260, "Check your email"),
		_block(
			"login.signup.sent_body",
			"Account created, paragraph",
			s,
			270,
			"We have sent a link to set your password. Open it and you can finish signing up."
			" It may take a minute to arrive, and it is worth a look in your spam folder.",
		),
		_block(
			"login.signup.pending_body",
			"Account created but not emailed, paragraph",
			s,
			280,
			"Your account has been created, but this site cannot send email yet, so nobody could"
			" send you a link. Ask your branch to activate the account for you.",
			notes="Shown instead of the paragraph above when the site has no outgoing email"
			" configured. There is nothing to resend, so no button is offered with it.",
		),
		_block("login.forgot.eyebrow", "Forgotten password, eyebrow", s, 300, "Password"),
		_block("login.forgot.title", "Forgotten password, heading", s, 310, "Reset your password"),
		_block(
			"login.forgot.body",
			"Forgotten password, paragraph",
			s,
			320,
			"Give us the address you sign in with and we will send you a link to set a new one.",
		),
		_block("login.link.eyebrow", "Sign in by email link, eyebrow", s, 400, "Sign in"),
		_block("login.link.title", "Sign in by email link, heading", s, 410, "Send me a link"),
		_block(
			"login.link.body",
			"Sign in by email link, paragraph",
			s,
			420,
			"We will email you a link that signs you in without a password.",
			notes="This panel is only reachable when the site has login by email link switched"
			" on in System Settings. It is not drawn otherwise.",
		),
		_block("login.password.eyebrow", "Set password, eyebrow", s, 500, "Your account"),
		_block("login.password.title", "Set password, heading", s, 510, "Set your password"),
		_block(
			"login.password.body",
			"Set password, paragraph",
			s,
			520,
			"Choose something you do not use anywhere else. You will sign in with it from now on.",
		),
	]


def _portal():
	s = "portal"
	# The sidebar, in the order it is drawn. The last three name the neighbouring
	# apps a site may have installed — `api/companions.py` decides whether each
	# tab appears at all, and this decides what it is called when it does. A
	# society whose LMS is "Training Centre" renames it with the pencil.
	nav = (
		("home", "Home"),
		("calendar", "Calendar"),
		("tasks", "Tasks"),
		("events", "Events"),
		("opportunities", "Opportunities"),
		("stories", "Stories"),
		("notifications", "Notifications"),
		("deployments", "Deployments"),
		("membership", "Membership"),
		("hours", "My hours"),
		("profile", "Profile"),
		("companions", "Also available"),
		("learning", "Learning"),
		("raven", "Raven"),
		("helpdesk", "Helpdesk"),
		# The switch across to the manager console, drawn only for somebody
		# `api/console.py::sections` says has one. A society that calls that
		# surface something else renames it here rather than in the frontend.
		("console", "Manager console"),
	)
	# The two headings the rail draws between bands of the nav. Content, like the
	# items under them: a society that calls its register something else renames
	# the heading rather than the nine links beneath it.
	groups = (
		("record", "My record"),
		("society", "From the society"),
	)
	rows = []
	for i, (slug, text) in enumerate(nav, start=1):
		rows.append(_block(f"portal.nav.{slug}", f"Sidebar item: {text}", s, 100 + i, text))
	for i, (slug, text) in enumerate(groups, start=1):
		rows.append(_block(f"portal.nav.group.{slug}", f"Sidebar heading: {text}", s, 150 + i, text))
	rows += [
		_block("portal.home.heading", "Dashboard heading", s, 200, "Your dashboard"),
		# The home hero. The photograph is a slot rather than a shipped asset, for
		# the reason at the top of this file: an empty one draws the branded
		# gradient, which is a better first run than a picture of somewhere the
		# society does not work.
		_block(
			"portal.home.hero.image",
			"Home hero photograph",
			s,
			205,
			notes="A wide photograph, at least 1200px across. The wording sits on the left, so keep the left half uncluttered.",
		),
		_block(
			"portal.home.choice.heading",
			"Home: heading over the two ways to join",
			s,
			210,
			"How would you like to get involved?",
		),
		_block(
			"portal.home.discover.opportunities",
			"Home: link to the opportunities board",
			s,
			215,
			"Browse opportunities",
		),
		_block("portal.home.discover.stories", "Home: link to stories", s, 216, "Volunteer stories"),
		_block("portal.membership.eyebrow", "Membership page eyebrow", s, 295, "Member account"),
		_block("portal.membership.heading", "Membership page heading", s, 300, "Membership"),
		_block(
			"portal.membership.lead",
			"Membership page, the line under the heading",
			s,
			305,
			"Choose the membership that fits you, then manage every branch membership from one account.",
		),
		_block(
			"portal.membership.empty",
			"Membership page, when there is none",
			s,
			310,
			"You do not hold a membership yet.",
		),
		# The plan grid on the membership tab. The *plans themselves* are not
		# content: every name, fee, benefit and eligibility note is read from
		# VMMS Membership Type, because those are the records the registration
		# charges against. Only the three sentences framing them are here.
		_block("portal.membership.plans.eyebrow", "Membership plans eyebrow", s, 320, "Membership types"),
		_block(
			"portal.membership.plans.heading",
			"Membership plans heading",
			s,
			325,
			"Choose a plan to become a member",
		),
		# The same heading for somebody whose application is already with a branch:
		# there is nothing for them to choose, so the grid reads rather than invites.
		_block(
			"portal.membership.plans.heading.pending",
			"Membership plans heading, while an application is undecided",
			s,
			326,
			"What your society offers",
		),
		_block("portal.tasks.heading", "Tasks page heading", s, 340, "Tasks"),
		_block("portal.hours.heading", "Hours page heading", s, 400, "My hours"),
		_block("portal.profile.heading", "Profile page heading", s, 500, "Profile"),
		_block("portal.opportunities.heading", "Opportunities page heading", s, 600, "Opportunities"),
		_block("portal.deployments.heading", "Deployments page heading", s, 650, "Deployments"),
		# The events screen. Its wording is a society's, like every other sentence
		# in this product: the hero says nothing about a country, a season or a
		# kind of event, so a society that runs nothing but training days rewrites
		# three slots rather than living with a heading about festivals.
		# Stories reads core's `Article` records. The wording around them is this
		# app's, and editable like everything else; the articles themselves are
		# written on the desk and are not content blocks.
		_block("portal.stories.eyebrow", "Stories page eyebrow", s, 690, "From the society"),
		_block("portal.stories.heading", "Stories page heading", s, 692, "Stories"),
		_block(
			"portal.stories.intro",
			"Stories page introduction",
			s,
			694,
			"What the society has been doing, and the people doing it.",
		),
		_block("portal.events.eyebrow", "Events page eyebrow", s, 700, "Upcoming events"),
		_block("portal.events.heading", "Events page heading", s, 705, "Featured events"),
		_block(
			"portal.events.hero.eyebrow",
			"Events hero eyebrow",
			s,
			710,
			"What's on",
		),
		_block(
			"portal.events.hero.headline",
			"Events hero headline",
			s,
			715,
			"Discover and join upcoming events",
		),
		_block(
			"portal.events.hero.blurb",
			"Events hero supporting line",
			s,
			720,
			"Training days, community drives and everything else your society has planned.",
		),
		# "Attend" rather than "Get tickets": the button opens the society's own
		# details panel — where, when, and a way to keep them — rather than
		# handing somebody off to buy something.
		_block("portal.events.card.action", "Events card button", s, 725, "Attend"),
		_block(
			"portal.events.attend.heading",
			"Attend panel heading",
			s,
			726,
			"What you need on the day",
		),
		_block("portal.events.attend.confirmed", "Attend confirmation chip", s, 727, "Attending"),
		_block("portal.events.attend.calendar", "Add to calendar button", s, 727, "Add to calendar"),
		_block("portal.events.attend.directions", "Find the venue button", s, 728, "Find the venue"),
		_block(
			"portal.events.attend.withdraw",
			"Withdraw link on the attend panel",
			s,
			729,
			"Cancel",
		),
		# The one sentence on the panel that says what the answer is and is not.
		# Every other word here can be reworded freely; if a society rewrites this
		# one, it must keep saying that no place has been held, because the
		# society's own record is an intention and the ticket is another app's.
		_block(
			"portal.events.attend.claim",
			"What saying yes actually does",
			s,
			730,
			"Your branch has been told to expect you. This does not hold a place.",
		),
		# The reader's own diary, above the listing.
		_block(
			"portal.events.attending.label",
			"Heading over the events this person is attending",
			s,
			735,
			"Your events",
		),
		_block("portal.events.attending.next", "Featured event flag", s, 736, "Next up"),
		_block("portal.events.attending.details", "Featured event details button", s, 737, "Details"),
		_block("portal.events.attending.going", "Attending confirmation on a row", s, 738, "Attending"),
		_block(
			"portal.events.attending.withdraw",
			"What the confirmation becomes on hover",
			s,
			739,
			"Cancel",
		),
		_block("portal.events.attending.saving", "While an answer is being saved", s, 740, "Saving…"),
		_block("portal.events.attending.show_calendar", "Show the small calendar", s, 741, "Show calendar"),
		_block("portal.events.attending.hide_calendar", "Hide the small calendar", s, 742, "Hide calendar"),
		_block("portal.events.attending.full", "Link to the calendar tab", s, 743, "Full calendar"),
		# The calendar tab.
		_block("portal.calendar.heading", "Calendar page heading", s, 760, "Your calendar"),
		_block("portal.calendar.today", "Jump to today", s, 762, "Today"),
		_block("portal.calendar.filter.all", "Show every event", s, 763, "Everything on"),
		_block("portal.calendar.filter.mine", "Show only your own events", s, 764, "Only mine"),
		_block("portal.calendar.legend.mine", "Legend: your own events", s, 765, "Attending"),
		_block("portal.calendar.legend.other", "Legend: everything else", s, 766, "Scheduled"),
		_block("portal.calendar.day.none", "Heading when no day is chosen", s, 767, "Pick a day"),
		_block("portal.calendar.day.badge", "Attending badge in the day panel", s, 768, "Attending"),
		_block("portal.calendar.day.attend", "Attend, in the day panel", s, 769, "Attend"),
		_block("portal.calendar.day.withdraw", "Take it back, in the day panel", s, 770, "Cancel"),
		_block("portal.notifications.heading", "Notifications page heading", s, 750, "Notifications"),
		_block("portal.training.heading", "Training page heading", s, 800, "Training"),
	]
	return rows


def _admin():
	s = "admin"
	nav = (
		("overview", "Overview"),
		("queue", "Review queue"),
		# The two lists under it. The queue became a parent with two children when
		# volunteer and membership approvals were split apart — one job each,
		# done in batches — so each list is a sidebar row a society can rename.
		("queue.volunteers", "Volunteer applications"),
		("queue.members", "Membership applications"),
		("registry.members", "Members"),
		("registry.volunteers", "Volunteers"),
		# `admin.nav.tasks` was drawn by the console from the day the Tasks screen
		# was built and never had a block, so it was the one sidebar item a society
		# could not rename. The pencil reaches it now like every other word.
		("tasks", "Tasks"),
		("projects", "Projects"),
		("deployments", "Deployments"),
		("stipends", "Stipends"),
		("events", "Events"),
		("analytics", "Analytics"),
		("communication", "Communication"),
		("content", "Page content"),
		# The two accordion headings the sidebar draws its tabs under —
		# `AdminLayout.tsx`'s `INSIGHT` and `OPERATIONS` — named the same way the
		# portal's own two group headings are, so a society renaming one renames
		# both surfaces through the one mechanism.
		("group.insight", "People & Insight"),
		("group.operations", "Operations"),
		# The way back to the person's own portal. Unconditional in the console,
		# because being staff is a role somebody holds rather than a thing they
		# are instead of a volunteer.
		("portal", "My portal"),
		# The way through to the Frappe desk, drawn only for somebody who may
		# open it. Named here so a society can call it whatever it calls that.
		("desk", "Desk"),
	)
	rows = []
	for i, (slug, text) in enumerate(nav, start=1):
		rows.append(_block(f"admin.nav.{slug}", f"Sidebar item: {text}", s, 100 + i, text))
	rows += [
		_block("admin.queue.heading", "Review queue heading", s, 200, "Review queue"),
		_block(
			"admin.queue.empty",
			"Review queue, when it is clear",
			s,
			210,
			"Nothing is waiting on you.",
		),
		_block(
			"admin.queue.volunteers.heading",
			"Volunteer applications heading",
			s,
			220,
			"Volunteer applications",
		),
		_block(
			"admin.queue.members.heading",
			"Membership applications heading",
			s,
			230,
			"Membership applications",
		),
		_block("admin.registry.members.heading", "Members heading", s, 300, "Members"),
		_block("admin.registry.volunteers.heading", "Volunteers heading", s, 310, "Volunteers"),
		_block("admin.deployments.heading", "Deployments heading", s, 400, "Deployments"),
		_block("admin.stipends.heading", "Stipends heading", s, 500, "Stipends"),
		_block("admin.communication.heading", "Communication heading", s, 550, "Communication"),
		_block(
			"admin.communication.lead",
			"Communication, the line under the heading",
			s,
			560,
			"Sent to the volunteers and members your branches cover.",
		),
		_block("admin.content.heading", "Page content heading", s, 600, "Page content"),
		_block(
			"admin.content.intro",
			"Page content introduction",
			s,
			610,
			"Every heading, paragraph, button and photograph in this product is edited here, or"
			" in place with the pencil that appears on the page itself.",
		),
	]
	return rows


def blocks() -> list[dict]:
	"""Every default block, in the order the desk list should show them."""
	return (
		_chrome()
		+ _landing_nav()
		+ _landing_hero()
		+ _landing_cards()
		+ _landing_bands()
		+ _landing_stats()
		+ _landing_events()
		+ _landing_close()
		+ _landing_footer()
		+ _login()
		+ _portal()
		+ _admin()
	)
