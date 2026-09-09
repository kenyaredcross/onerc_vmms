# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Kenya Red Cross Society newsroom. Demo content, never behaviour.

    bench --site <site> execute vmmsx.seed.kenya_stories.main

Split out of `kenya_operations.py`, which had five articles inside it and was
becoming a file where the prose outweighed the seeding. Ten articles now, long
enough to read as written rather than as filler, because the stories tab is one
of the surfaces an acceptance test actually looks at: a reader scrolling a list
of four-line stubs learns nothing about whether the screen works.

**`Article` is onerc_core's doctype**, and the portal reads it through core's own
guest-readable endpoint rather than through anything in this app. Seeded here for
the same reason the Buzz events are: the records belong to whichever app owns
them, and an empty newsroom demonstrates nothing.

**Every one is submitted, not merely published.** `Article` is submittable and
core's list endpoint filters on `docstatus = 1` *as well as*
`status = "Published"`. A seed that set only the status would produce records
that look published on the desk and are invisible in the portal — the most
confusing possible half-state — so each one is submitted here, deliberately and
visibly.

**What is real and what is written for the demo.** The places, the counties and
the kinds of work are real: KRCS runs reception centres, blood drives with the
Kenya National Blood Transfusion Service, community health volunteering and
first aid training, and the counties named below are counties it works in. The
people are not real people and the numbers are not real numbers. Nobody is
quoted who did not consent to being quoted, because nobody is quoted at all —
where a story needs a voice it is attributed to an unnamed volunteer, which is
what an honest demo can do. A society replaces the lot with its own.

**No cover image is attached.** The portal draws a designed placeholder for an
absent one, and a seed inventing photography would put a stock photograph on a
society's own newsroom.

Idempotent, and it says what it did. The check is on the title, so an article
somebody has since edited is left exactly as they edited it.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.seed import kenya

ARTICLE_DOCTYPE = "Article"
TYPE_DOCTYPE = "Localisation Type"
CATEGORY_DOCTYPE = "Localisation Category"

# Core's two vocabularies, each autonaming from its own label. The naming series
# below is matched to the type, which is the one place these two tables meet:
# core ships `NEWS-.YYYY.-.#####` and `STR-.YYYY.-.#####` as the options, and an
# article filed as a Story under a NEWS- number is a record whose name argues
# with its own type field.
ARTICLE_TYPES = (
	("News", "Something that happened, reported by the society."),
	("Story", "A volunteer, a county or a community, in their own words."),
)

SERIES = {"News": "NEWS-.YYYY.-.#####", "Story": "STR-.YYYY.-.#####"}

ARTICLE_CATEGORIES = (
	("Emergency Response", "Floods, fires, road accidents and the work that follows."),
	("Volunteering", "The people who give their time, and what it is like."),
	("Health", "Blood, first aid, community health and public awareness."),
	("County Life", "What is happening across the society's 47 counties."),
	("Training", "Courses, certifications, and keeping a qualification current."),
)

# `published_in` is days from the day the seed runs, negative for the past, so
# the newsroom never reads as though nobody has touched it since installation.
# `sort_order` is core's own tie-breaker and is left ascending with age.
ARTICLES = (
	{
		"title": "Three days in Mathare: what a reception centre actually looks like",
		"subtitle": "Forty households arrived in one night. Here is how Nairobi met them.",
		"type": "Story",
		"category": "Emergency Response",
		"location": "Nairobi County",
		"read_time": 7,
		"featured": True,
		"published_in": -4,
		"summary": (
			"When fire went through part of Mathare, Nairobi had a reception centre standing"
			" within four hours. Three volunteers describe the first night, the registration"
			" queue, and the one thing they would do differently."
		),
		"body": (
			"<p>The call came in at ten past eight on a Tuesday. By midnight the hall had forty"
			" households in it, and by the following evening it had ninety.</p>"
			"<h2>The first four hours</h2>"
			"<p>Setting up is not the hard part. Sleeping mats, a washing point and a feeding"
			" area go in fast when there are enough hands, and there were — eleven volunteers"
			" inside the first hour, most of them from two sub-counties away.</p>"
			"<p>What takes the time is registration, because registration is what everything"
			" else depends on: how much food to cook, how many mats are still needed, which"
			" children arrived without an adult, and who has not been accounted for. Get it"
			" wrong at nine in the evening and you are still paying for it at four in the"
			" morning.</p>"
			"<h2>The queue nobody plans for</h2>"
			"<p>By half past ten there were sixty people in a line for one table. The line was"
			" not the problem; the problem was that the line was the only place anybody could"
			" ask a question, so every question in the building was being asked at the table"
			" doing the registering.</p>"
			"<p>Splitting the two — one volunteer registering, one standing in front of the"
			" queue answering whatever was asked — took the wait from fifty minutes to"
			" fifteen. It cost nothing. It was also nobody's idea in advance.</p>"
			"<h2>What we would do differently</h2>"
			"<p>Two things. Put two people on registration from the start rather than one, and"
			" agree who is talking to the county government before anybody does. Two"
			" volunteers gave two different bed counts to two different officials inside the"
			" same hour, and both numbers were right when they were given.</p>"
			"<blockquote>You are not there to fix somebody's week. You are there so that their"
			" night is survivable.</blockquote>"
			"<p>Everyone who worked the centre logged their hours against it, which is how the"
			" county knows the centre cost 340 volunteer hours across three days — and how it"
			" knows that four people did more than thirty of those hours each.</p>"
		),
	},
	{
		"title": "Why your first aid certificate has an expiry date",
		"subtitle": "It is not administration. It is the difference between remembering and knowing.",
		"type": "News",
		"category": "Training",
		"location": "National",
		"read_time": 5,
		"featured": False,
		"published_in": -9,
		"summary": (
			"A number of certificates expire this quarter. What lapses, what it stops you being"
			" sent to do, and how to book the next sitting before rather than after."
		),
		"body": (
			"<p>A first aid certificate is valid for two years, and the society treats a lapsed"
			" one as a lapsed one. That is deliberate, and it is worth explaining rather than"
			" just enforcing.</p>"
			"<h2>Skills decay, and they decay unevenly</h2>"
			"<p>Recognising a problem stays with you for years. The sequence you carry out once"
			" you have recognised it does not — compression depth, the order of checks, how"
			" long you keep going. Those are the parts that go first, and they are the parts"
			" that matter under pressure.</p>"
			"<h2>What a lapse actually stops</h2>"
			"<p>Some certifications are held as a record and some are held as a requirement."
			" A lapsed <em>requirement</em> is the reason somebody cannot be sent on work that"
			" names it. Your own training page in the portal says so, on the certification"
			" itself, rather than leaving you to find out when a coordinator calls at six in"
			" the morning.</p>"
			"<h2>Booking the next one</h2>"
			"<p>The two-day certificate runs monthly at South C and quarterly in most counties;"
			" both are listed under events. Book it before yours runs out rather than after —"
			" a renewal is one course, a lapse is the full sitting again.</p>"
		),
	},
	{
		"title": "Grace has given 200 hours this year. She is 24.",
		"subtitle": "A conversation about turning up, burning out, and turning up again.",
		"type": "Story",
		"category": "Volunteering",
		"location": "Kisumu County",
		"read_time": 6,
		"featured": True,
		"published_in": -16,
		"summary": (
			"She joined for a line on a form and stayed for something else entirely. On"
			" psychosocial support, school talks, and the thing nobody tells you about the"
			" first deployment."
		),
		"body": (
			"<p>She signed up because a friend was signing up. She is fairly clear that this is"
			" not an inspiring reason and fairly clear that it does not matter.</p>"
			"<h2>The first deployment</h2>"
			"<p>A road traffic collision on the Kisumu-Busia road, eight months in. She was"
			" there for four hours and describes about ninety seconds of it in detail and the"
			" rest not at all.</p>"
			"<p>&ldquo;Nobody tells you that the hardest part is not the work,&rdquo; she says."
			" &ldquo;It is the hour afterwards, when there is nothing left to do and you are"
			" still there.&rdquo;</p>"
			"<h2>What she does now</h2>"
			"<p>School talks, mostly — first aid basics to sixteen-year-olds, which she"
			" maintains is harder than any incident she has attended. Psychosocial support"
			" training last year, and she is now one of two people in her county who can run"
			" the first-hour conversation with somebody who has just come off a scene.</p>"
			"<h2>On not burning out</h2>"
			"<p>Her advice is administrative and she knows it: log your hours honestly,"
			" including the ones you would rather not count.</p>"
			"<blockquote>A county that can see somebody is at 200 hours can do something about"
			" it. A county that cannot see it will keep calling.</blockquote>"
			"<p>Her own coordinator saw the number in March and took her off the call list for"
			" six weeks. She was annoyed about it at the time and is not now.</p>"
		),
	},
	{
		"title": "The Mombasa blood drive moved 412 units in a weekend",
		"subtitle": "And the small change in the reception area that halved the queue.",
		"type": "News",
		"category": "Health",
		"location": "Mombasa County",
		"read_time": 4,
		"featured": False,
		"published_in": -23,
		"summary": (
			"A two-day mobile drive with the Kenya National Blood Transfusion Service against a"
			" target of 300, and what the county learned about donor reception."
		),
		"body": (
			"<p>412 units over two days at two sites in Mombasa, against a target of 300. The"
			" number is good. The reason it is good is duller than the number.</p>"
			"<h2>The change that mattered</h2>"
			"<p>Screening and registration were run as one queue on the Saturday and it did not"
			" work. A donor who turned out to be ineligible had already waited thirty-five"
			" minutes to find out, and the people behind them had waited it too.</p>"
			"<p>Splitting them on the Sunday — two volunteers registering, two screening, and"
			" the screening desk first — halved the average wait and dropped the number of"
			" people who left before donating from twenty-nine to four.</p>"
			"<h2>What went in the report</h2>"
			"<p>Screening goes first. It is one line and it is the whole finding, and it is now"
			" in the standing brief every mobile drive in the county is set up from.</p>"
		),
	},
	{
		"title": "Every county is now on the same register",
		"subtitle": "What that changes for a volunteer, and what it does not.",
		"type": "News",
		"category": "County Life",
		"location": "National",
		"read_time": 5,
		"featured": False,
		"published_in": -34,
		"summary": (
			"One profile, whichever county you serve through. What moves with you, what stays"
			" with the county, and why your certifications are now visible to whoever is"
			" staffing a deployment."
		),
		"body": (
			"<p>You have one profile with the society and you will only ever have one. That is"
			" the whole of the change, and most of what follows from it is a consequence rather"
			" than a decision.</p>"
			"<h2>What moves with you</h2>"
			"<p>Your name, your contact details, your emergency contacts, your certifications"
			" and every hour you have ever logged. Moving between counties does not restart any"
			" of it, and it does not ask anybody to re-enter it.</p>"
			"<h2>What stays with the county</h2>"
			"<p>Your placement, and the decisions a county made about it. A transfer is a"
			" decision somebody with standing makes, not a field you edit — which is the same"
			" rule that has always applied, now written down somewhere it can be enforced.</p>"
			"<h2>Who can see what</h2>"
			"<p>A coordinator sees what is filed in their own county and at the sub-counties"
			" under it, and nothing filed in anybody else's. That is not a setting somebody"
			" remembered to switch on; it is how the register answers every question it is"
			" asked.</p>"
		),
	},
	{
		"title": "Turkana: eleven months of a drought response, in one register",
		"subtitle": "What 6,400 logged hours look like when you put them in order.",
		"type": "Story",
		"category": "Emergency Response",
		"location": "Turkana County",
		"read_time": 8,
		"featured": False,
		"published_in": -47,
		"summary": (
			"A long response is not a big response repeated. Turkana's volunteer coordinators"
			" go through what changed between month two and month nine, and what the hour logs"
			" showed that the situation reports did not."
		),
		"body": (
			"<p>A sudden-onset response is a sprint that somebody eventually calls time on. A"
			" drought response is not, and almost nothing that works in the first is still"
			" working in the eleventh month of the second.</p>"
			"<h2>Month two: everybody, all the time</h2>"
			"<p>Ninety-one volunteers active across four sub-counties, most of them doing"
			" whatever was in front of them. It worked, in the sense that the work got done.</p>"
			"<p>It also produced the pattern the hour logs made obvious later: fourteen people"
			" were carrying about a third of the total. Nobody had decided that. It was simply"
			" who answered the phone.</p>"
			"<h2>Month five: the rota nobody liked</h2>"
			"<p>Fixed two-week blocks, published a month ahead, with a named person per site and"
			" a named reserve. It was less flexible and it was resented for about three weeks.</p>"
			"<blockquote>The rota did not make us faster. It made us able to keep going, which"
			" turned out to be the thing we actually needed.</blockquote>"
			"<h2>Month nine: what the logs showed</h2>"
			"<p>6,400 hours across eleven months, and two findings nobody expected. Attendance"
			" at the nutrition screening sites was steady all year, and attendance at the water"
			" distribution points fell every single month after month four — not because the"
			" need fell, but because the same nine people were doing it and four of them"
			" stopped.</p>"
			"<p>Turnover is invisible in a situation report and obvious in an hour log. It is"
			" the strongest argument anybody in the county has yet made for logging hours"
			" against the work rather than against the month.</p>"
			"<h2>What is different now</h2>"
			"<p>Every long response in the county now gets a named deputy from the start, and no"
			" volunteer is rostered more than two blocks in a row without being asked.</p>"
		),
	},
	{
		"title": "The Nakuru first aid post that took 1,100 people in a day",
		"subtitle": "Twelve volunteers, one gazebo, and a county show.",
		"type": "News",
		"category": "Health",
		"location": "Nakuru County",
		"read_time": 4,
		"featured": False,
		"published_in": -58,
		"summary": (
			"Public event duty is the least dramatic thing the society does and one of the most"
			" common. What actually walks up to the post, and why the answer is mostly water."
		),
		"body": (
			"<p>1,100 people through a first aid post over nine hours at the Nakuru county"
			" agricultural show, staffed by twelve volunteers on two shifts.</p>"
			"<h2>What people came for</h2>"
			"<p>Heat, overwhelmingly. Around 700 of the 1,100 were dehydration, faintness or"
			" somewhere shaded to sit down for ten minutes. Then cuts and grazes, then blisters,"
			" then eleven cases that needed anything more than reassurance and water, then two"
			" that went to hospital.</p>"
			"<h2>Why that matters for the next one</h2>"
			"<p>A post stocked for trauma and staffed for trauma will spend its day handing out"
			" water it did not bring enough of. The county's standing kit list for public event"
			" duty has been rewritten around the 700 rather than the two.</p>"
			"<h2>The other finding</h2>"
			"<p>Nine of the twelve volunteers were on their first public duty. Every one of them"
			" was paired with somebody who was not, which is the only reason a post that busy"
			" ran calmly.</p>"
		),
	},
	{
		"title": "&ldquo;I thought volunteering meant emergencies.&rdquo;",
		"subtitle": "Six weeks with a community health volunteer in Kilifi.",
		"type": "Story",
		"category": "Volunteering",
		"location": "Kilifi County",
		"read_time": 7,
		"featured": False,
		"published_in": -71,
		"summary": (
			"No floods, no fires and no sirens. A household register, a set of scales, and 240"
			" homes visited twice a month — which is most of what the society actually does."
		),
		"body": (
			"<p>He applied after a flood he saw on television. He has never been to a flood.</p>"
			"<h2>What the work is</h2>"
			"<p>240 households, visited twice a month. Weighing children under five, checking"
			" who has missed an immunisation, asking about the mosquito net that was there last"
			" time, and referring anybody who needs referring to the dispensary four kilometres"
			" up the road.</p>"
			"<p>He can tell you which houses have a net and which ones say they have a net. This"
			" is, he says, the entire skill.</p>"
			"<h2>The part that took getting used to</h2>"
			"<p>Nothing is resolved. A household is not a case you close; it is a household you"
			" will see again in a fortnight, and the honest measure of six weeks' work is that"
			" three children are on the growth chart they should be on and one is not, yet.</p>"
			"<blockquote>The emergency is the part people can see. This is the part that means"
			" there are fewer of them.</blockquote>"
			"<h2>What he would tell somebody applying</h2>"
			"<p>Choose the availability you can actually keep, not the one that sounds"
			" committed. Two mornings a fortnight for two years is worth more to a household"
			" register than every weekend for two months.</p>"
		),
	},
	{
		"title": "Garissa's flood response was faster because of a form",
		"subtitle": "The pre-positioned volunteer register, and the 40 minutes it saved.",
		"type": "News",
		"category": "Emergency Response",
		"location": "Garissa County",
		"read_time": 5,
		"featured": False,
		"published_in": -86,
		"summary": (
			"When the Tana burst its banks, Garissa did not have to ask who was available and"
			" trained. It already knew, because 180 people had answered that question in"
			" advance."
		),
		"body": (
			"<p>The unglamorous claim first: the response was about forty minutes faster than"
			" the last comparable one, and the reason is a register that was up to date before"
			" anybody needed it.</p>"
			"<h2>What forty minutes is made of</h2>"
			"<p>In the previous response, the first hour was three coordinators phoning people"
			" to ask two questions: are you free, and do you still hold water and sanitation"
			" training. Most of the calls were to people who were not free, and a good number"
			" were to people whose training had lapsed eighteen months earlier.</p>"
			"<p>This time both answers were already recorded, by the volunteers themselves. The"
			" first hour was spent phoning 22 people who were free and current, rather than 60"
			" people in the hope of finding them.</p>"
			"<h2>Why the register was current</h2>"
			"<p>Because keeping it current is somebody's actual job, and because a volunteer can"
			" change their own availability from their own phone without asking anybody. A"
			" register only an administrator can edit is a register that is accurate on the day"
			" it is built.</p>"
			"<h2>The caveat</h2>"
			"<p>180 people is not the whole county and the register knows it. Four sub-counties"
			" are well covered and two are barely covered at all, which is now a recruitment"
			" question with a number attached to it rather than a feeling.</p>"
		),
	},
	{
		"title": "What a County Coordinator actually does all day",
		"subtitle": "A queue, forty-one decisions, and the two that took an afternoon.",
		"type": "Story",
		"category": "County Life",
		"location": "Nairobi County",
		"read_time": 6,
		"featured": False,
		"published_in": -104,
		"summary": (
			"Reviewing volunteer applications is most of the job and almost none of the"
			" conversation about the job. What a coordinator is looking for, and what makes"
			" them send one back rather than refuse it."
		),
		"body": (
			"<p>Forty-one applications in a week, which is a normal week. Thirty-six were"
			" straightforward, three needed a phone call, and two took most of an afternoon.</p>"
			"<h2>What the straightforward ones look like</h2>"
			"<p>A complete form, an availability that is plausible, an emergency contact who is"
			" not the applicant themselves, and a county that matches where the person says"
			" they live. That is the bulk of it, and it takes about four minutes.</p>"
			"<h2>Sending one back is not refusing it</h2>"
			"<p>The distinction matters more than anything else in the queue. A refusal is a"
			" decision about a person. A request for more information is a decision about a"
			" form, and it comes back to the applicant with the reason written on it so they"
			" can fix the thing that is wrong and resubmit.</p>"
			"<blockquote>If I can tell you what is missing, I have no business rejecting you"
			" for it.</blockquote>"
			"<p>Of the five that were not approved that week, four were sent back and three of"
			" those came back complete within a fortnight.</p>"
			"<h2>The two that took an afternoon</h2>"
			"<p>One was a sixteen-year-old, which is a conversation about guardian consent and"
			" what work is appropriate rather than a yes or a no. The other was somebody"
			" applying to a county they had left, which is a transfer wearing an application's"
			" clothes.</p>"
			"<h2>The part that is not the queue</h2>"
			"<p>Everything else: rostering, chasing lapsed certifications, and the standing"
			" argument with every county coordinator in the country about whether their own"
			" county is under-resourced. It is.</p>"
		),
	},
)


def main(commit: bool = True) -> dict:
	"""Seed the newsroom and report what changed. Safe to re-run.

	`commit` matches `kenya.main`'s argument and exists for the same reason: the
	bench path needs the writes to persist, and a test running this for real must
	not escape the transaction the runner rolls back.
	"""
	report = {"article_taxonomy": _taxonomy(), "articles": _articles()}

	if commit:
		frappe.db.commit()

	_print(report)

	return report


def _taxonomy() -> list[dict]:
	"""Core's article types and categories. Both autoname from their own label."""
	rows = []

	for doctype, entries, field in (
		(TYPE_DOCTYPE, ARTICLE_TYPES, "type_name"),
		(CATEGORY_DOCTYPE, ARTICLE_CATEGORIES, "category_name"),
	):
		if not frappe.db.exists("DocType", doctype):
			rows.append({"key": doctype, "status": "skipped: doctype not installed"})
			continue

		for label, description in entries:
			if frappe.db.exists(doctype, label):
				rows.append({"key": label, "status": "exists"})
				continue

			frappe.get_doc(
				{"doctype": doctype, field: label, "description": description, "is_active": 1}
			).insert(ignore_permissions=True)

			rows.append({"key": label, "status": "created"})

	return rows


def _articles() -> list[dict]:
	"""Published, submitted stories. See the note at the top about why submitted.

	The author is the seeded approver where that account exists and Administrator
	otherwise: `author` is mandatory on `Article` and a story with no byline is
	not a record core will accept. Either way it is a real user on this site,
	which is the only thing the field is actually asserting.
	"""
	if not frappe.db.exists("DocType", ARTICLE_DOCTYPE):
		return [{"key": ARTICLE_DOCTYPE, "status": "skipped: doctype not installed"}]

	author = kenya.APPROVER_USER if frappe.db.exists("User", kenya.APPROVER_USER) else "Administrator"
	rows = []

	for order, spec in enumerate(ARTICLES, start=1):
		if frappe.db.exists(ARTICLE_DOCTYPE, {"title": spec["title"]}):
			rows.append({"key": spec["title"][:52], "status": "exists"})
			continue

		article = frappe.get_doc(
			{
				"doctype": ARTICLE_DOCTYPE,
				"naming_series": SERIES[spec["type"]],
				"title": spec["title"],
				"subtitle": spec["subtitle"],
				"article_type": spec["type"],
				"category": spec["category"],
				"location": spec["location"],
				"summary": spec["summary"],
				"body": spec["body"],
				"read_time": spec["read_time"],
				"is_featured": int(spec["featured"]),
				"sort_order": order,
				"allow_comments": 1,
				# Core's own SEO fields. Filled from the article rather than left
				# empty because a newsroom being acceptance-tested is one somebody
				# will share a link to, and an unset meta description is how a
				# perfectly good story arrives in a chat window as a bare URL.
				"meta_title": spec["title"][:60],
				"meta_description": spec["summary"][:155],
				"author": author,
				"status": "Published",
				"published_on": add_days(today(), spec["published_in"]),
			}
		)
		article.insert(ignore_permissions=True)
		article.submit()

		rows.append({"key": spec["title"][:52], "status": "created", "slug": article.slug})

	return rows


def _print(report: dict) -> None:
	print(f"\nKenya Red Cross Society newsroom seed on {frappe.local.site}\n" + "=" * 62)

	for section, rows in report.items():
		print(f"\n{section.replace('_', ' ').title()}")

		for row in rows:
			extra = " ".join(f"{k}={v}" for k, v in row.items() if k not in ("key", "status"))
			print(f"  [{row['status']:<8}] {row['key']}{'  ' + extra if extra else ''}")

	print()
