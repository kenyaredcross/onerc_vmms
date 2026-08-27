# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The three-page status brief — where the build is, and where it is going.

    bench --site vmms.localhost execute vmmsx.docs.status_brief.main

A third artefact alongside the system guide and the walkthrough, and a
deliberately different kind of writing again. The guide describes what the
software *is*, section by section, and runs to a hundred pages. The walkthrough
describes what to *do* on a real site. This one answers the only two questions
somebody who is not building it actually has — **what works, and what is left**
— and it answers them in three pages, walking the journey once from a stranger
on the landing page to a volunteer coming home from a deployment.

**Three pages is the specification, not a target.** The page breaks below are
explicit for that reason: one page for the standing and the first half of the
journey, one for the second half, one for the work in flight and the work
remaining. Anything that does not earn its place on those three pages belongs in
the guide, which is where the detail already lives.

**Nothing here is aspirational.** Every count is read off the tree at build
time rather than typed in, so the figures cannot drift; every gap named in
section four is one the source says out loud about itself — the stipend dead end
is `stipend/services/approval.py`'s own docstring, the seams are the seam
modules' own. A status document that reported the gaps optimistically would be
the one document in this repository nobody could trust.
"""

from datetime import datetime
from pathlib import Path

from docx.shared import Pt, RGBColor

from vmmsx.docs.writer import ACCENT, MUTED, Writer, plain

APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = APP_ROOT / "docs" / "vmmsx-status-brief.docx"

TITLE = "vmmsx"
SUBTITLE = "Build status, the user journey end to end, and what remains"

LEAD = (
	"vmmsx is the Volunteer and Member Management System: the software a National Society uses to"
	" take somebody from a stranger on its website to a volunteer it has trained, placed and sent"
	" into the field, and to keep the record of it. This brief walks that journey once, then says"
	" what is finished, what is in my hands, and what is left."
)


def main(path: str | None = None) -> str:
	"""Build the brief and return where it was written."""
	target = Path(path) if path else OUTPUT

	writer = _render(datetime.now().strftime("%d %B %Y"))

	target.parent.mkdir(parents=True, exist_ok=True)
	writer.doc.save(str(target))

	return str(target)


def _render(generated_on: str) -> Writer:
	w = Writer()

	_masthead(w, generated_on)

	_standing(w)
	_journey_first_half(w)

	w.page_break()
	_journey_second_half(w)
	_in_flight(w)

	w.page_break()
	_remaining(w)

	return w


# --- presentation helpers ---------------------------------------------------
#
# `Writer.cover` and `Writer.contents` each spend a whole page, which is a third
# of this document, so neither is used. `Writer.bullets` renders its text
# verbatim, and the guide's own `**lead-in**` convention therefore reaches the
# page as literal asterisks — tolerable in a hundred-page reference somebody
# skims, wrong in a three-page brief somebody reads. So the two helpers below,
# and nothing else: a compact masthead, and a bullet whose lead-in is genuinely
# bold. Both are presentation for this document alone and stay out of `Writer`.


def _masthead(w: Writer, generated_on: str) -> None:
	"""Title, one line of provenance, and the paragraph that frames the rest."""
	heading = w.doc.add_paragraph()
	heading.paragraph_format.space_after = Pt(1)
	run = heading.add_run(TITLE)
	run.font.size = Pt(26)
	run.font.bold = True
	run.font.color.rgb = ACCENT

	sub = w.doc.add_paragraph()
	sub.paragraph_format.space_after = Pt(6)
	sub_run = sub.add_run(SUBTITLE)
	sub_run.font.size = Pt(11.5)
	sub_run.font.color.rgb = MUTED

	meta = w.doc.add_paragraph()
	meta.paragraph_format.space_after = Pt(12)
	meta_run = meta.add_run(f"Prepared by Nigel   ·   {generated_on}   ·   branch vmmsx")
	meta_run.font.size = Pt(8.5)
	meta_run.font.color.rgb = MUTED

	body = w.doc.add_paragraph()
	body.paragraph_format.space_after = Pt(10)
	body_run = body.add_run(plain(LEAD))
	body_run.font.size = Pt(10.5)


def _point(w: Writer, label: str, text: str, *, numbered: bool = False) -> None:
	"""One bullet whose opening phrase is bold, because it is the thing being said."""
	para = w.doc.add_paragraph(style="List Number" if numbered else "List Bullet")
	para.paragraph_format.space_after = Pt(3)

	lead = para.add_run(f"{plain(label)}  ")
	lead.font.bold = True

	para.add_run(plain(text))


# --- the numbers ------------------------------------------------------------
#
# Counted off the tree at build time, never typed in. A status document whose
# figures were transcribed once would be wrong within a week and there would be
# no way to notice; these are wrong only if the tree is.

APP_PACKAGE = APP_ROOT / "vmmsx"
PORTAL_SRC = APP_ROOT / "portal" / "src"

WHITELIST = "@frappe.whitelist"
TEST_DEF = "def test_"
ROUTE = "<Route path="


def _lines_starting(source: Path, token: str) -> int:
	"""How many lines of `source` begin with `token`, ignoring indentation."""
	return sum(1 for line in source.read_text().splitlines() if line.lstrip().startswith(token))


def _counts() -> dict[str, int]:
	modules = [line for line in (APP_PACKAGE / "modules.txt").read_text().splitlines() if line.strip()]

	# A doctype is a directory under some `doctype/` holding the JSON it is
	# defined by. Counting the JSON files directly would also count every child
	# table's parent listing and every test fixture that happens to live there.
	doctypes = [
		folder
		for folder in APP_PACKAGE.glob("*/doctype/*")
		if folder.is_dir() and (folder / f"{folder.name}.json").exists()
	]

	# Both of these are counted as *lines that begin with the token*, not as
	# occurrences of it. Every one of these files documents itself at length and
	# several name the decorator or a test in prose, so a substring count reads
	# the commentary as if it were code and reports a handful too many.
	endpoints = sum(_lines_starting(source, WHITELIST) for source in (APP_PACKAGE / "api").glob("*.py"))

	tests = sum(_lines_starting(source, TEST_DEF) for source in APP_PACKAGE.rglob("test_*.py"))

	screens = (PORTAL_SRC / "App.tsx").read_text().count(ROUTE)

	return {
		"modules": len(modules),
		"doctypes": len(doctypes),
		"endpoints": endpoints,
		"tests": tests,
		"screens": screens,
	}


# --- 1. where the build stands ----------------------------------------------


def _standing(w: Writer) -> None:
	w.h1("Where the build stands")

	n = _counts()

	w.table(
		[
			f"{n['modules']} modules",
			f"{n['doctypes']} doctypes",
			f"{n['endpoints']} server endpoints",
			f"{n['screens']} routed screens",
		],
		[
			[
				f"{n['tests']} automated tests",
				"3 societies seeded",
				"1 approval engine",
				"1 identity per person",
			]
		],
		[1.6, 1.6, 1.7, 1.6],
	)

	w.p(
		"The spine runs end to end: a person registers themselves, the right coordinator reviews and"
		" approves them, they become a volunteer, they are matched to work, they accept it, they"
		" serve, and the hours are recorded against it. Kenya, Tanzania and The Gambia are each"
		" seeded from source, so any of them can be demonstrated on a clean site. One decision"
		" carries most of the weight: approval is a single engine rather than a feature repeated per"
		" module, and a society changes its ladder, branches, types and wording by editing records,"
		" not by writing code."
	)


# --- 2. the journey ---------------------------------------------------------


def _journey_first_half(w: Writer) -> None:
	w.h1("The journey, end to end")

	_point(
		w,
		"They arrive.",
		"The public landing page introduces the society, and every sentence on it is content a"
		" coordinator edits — the software ships no wording of its own. A locator helps them find"
		" the branch nearest them before they commit to anything.",
		numbered=True,
	)

	_point(
		w,
		"They sign in.",
		"Registration is refused to a guest, deliberately and first. The login is the identity: the"
		" email address is never a field on any form, because a form value would let anybody claim"
		" to be anybody. One login means exactly one person record, forever.",
		numbered=True,
	)

	_point(
		w,
		"They register.",
		"A wizard asking one thing per screen — seven for a volunteer, five for a member: who they"
		" are, the branch they are joining, citizenship, residence, identification, the declaration,"
		" and whatever else this society asks. Every list on it is configuration.",
		numbered=True,
	)

	_point(
		w,
		"The right person is asked.",
		"On submission the application enters the approval engine, which works out from the branch"
		" it was filed at who may answer it and puts it in their queue. No coordinator ever sees an"
		" application from a branch they have no standing over.",
		numbered=True,
	)

	_point(
		w,
		"The coordinator answers.",
		"They approve it, decline it, or send it back for correction, and the applicant is emailed"
		" on each change. A society that configures no approvals at all gets applications that"
		" approve on submission — the same engine, with nobody to resolve.",
		numbered=True,
	)


def _journey_second_half(w: Writer) -> None:
	_point(
		w,
		"They become a volunteer.",
		"Approval creates the volunteer record, grants the access that opens their own portal, and"
		" issues the identity card the society prints. That follows from the state being Approved"
		" rather than from the next line of a script, so there is no half-finished volunteer if"
		" anything is retried.",
		numbered=True,
	)

	_point(
		w,
		"They have somewhere to be one.",
		"The portal is theirs: their profile and the photograph on their card, the availability they"
		" offer, the certifications they hold and when each expires, the hours they have logged,"
		" their tasks, and the society's announcements and events.",
		numbered=True,
	)

	_point(
		w,
		"The society plans real work.",
		"A Project is the programme. A Terms of Reference is the mission written under it —"
		" objectives, outputs, methodology, itinerary, stakeholders, resources — and it prints on"
		" the society's own letterhead. A Deployment Request says that mission needs people, here,"
		" on these dates; it clears its approval and becomes a Deployment.",
		numbered=True,
	)

	_point(
		w,
		"People are matched to it.",
		"Candidate search runs over the register for that mission and place, within the part of the"
		" society the searcher may see, and excludes anyone whose required certification will have"
		" lapsed by the day work starts. A deployment opens with nobody on it: who goes is a"
		" coordinator's judgement, made with facts this software does not hold.",
		numbered=True,
	)

	_point(
		w,
		"The volunteer answers.",
		"An invitation is that volunteer's own record with its own address, not a row on a list"
		" only a coordinator can open — which is what lets it be emailed to them and answered by"
		" them. Accepting records which version of the terms they agreed to, so amending the"
		" mission afterwards cannot change what somebody signed up for.",
		numbered=True,
	)

	_point(
		w,
		"They serve, and it is recorded.",
		"The deployment moves Planned to Active to Completed, with a feed of updates against it."
		" Volunteers log hours to it only if they were genuinely on its roster — refused on the"
		" server, not merely hidden on the screen. A completed deployment still accepts them,"
		" because filing afterwards is the ordinary case.",
		numbered=True,
	)

	w.note(
		"The membership road runs alongside this one from step three, through the same engine and"
		" the same queues, ending in an activated membership, a printable certificate, and a"
		" renewal the member starts."
	)


# --- 3. the work in flight --------------------------------------------------


def _in_flight(w: Writer) -> None:
	w.h1("What I am working on now")

	w.p(
		"The features are built; this stage is about making the data underneath them correct. A"
		" person's own facts — citizenship, residence, and the documents proving who they are —"
		" were written down three times: on the central person record, on their application, and"
		" again on the volunteer record approval created. Three copies is three answers, and they"
		" drift the moment anybody corrects one. The central record is now the only owner, and"
		" everything else reads from it."
	)

	_point(
		w,
		"The duplicate columns are gone.",
		"They are removed from the volunteer and the application, along with the form fields that"
		" wrote them.",
	)

	_point(
		w,
		"Identification became a list.",
		"A person can hold a national ID and a passport, each with its own scan and one marked"
		" primary. The old shape held one and lost the other.",
	)

	_point(
		w,
		"A migration carries existing data forward.",
		"It fills a person record that is empty and never overwrites one already answered — the safe"
		" direction when two copies disagree.",
	)

	_point(
		w,
		"There is one public door again.",
		"The older built-in web form is withdrawn: it could not write a person's facts and file"
		" their application in one transaction.",
	)


# --- 4. what remains --------------------------------------------------------


def _remaining(w: Writer) -> None:
	w.h1("What remains")

	w.p(
		"Three kinds of thing, and the distinction is the point: work that is genuinely missing,"
		" work that belongs to a neighbouring system by design, and one place where the honest"
		" answer is that it does not work yet."
	)

	w.table(
		["Kind", "What", "Where it stands"],
		[
			[
				"Missing",
				"Documents on the application",
				"A registrant cannot attach an ID or a supporting letter, and no reviewer screen"
				" shows one. The person record now has somewhere to put it, which is half the"
				" work; the wizard step and the reviewer's view are the rest.",
			],
			[
				"Missing",
				"Renewal from the coordinator's side",
				"A member can renew from their own portal when the server says they are eligible."
				" A coordinator doing it for them has no screen, and would create a second"
				" membership instead.",
			],
			[
				"Missing",
				"Off-boarding",
				"Suspension, exit and lapse leave the person still holding the access they were"
				" granted. Withdrawing it should stay a society's decision rather than an"
				" automatic one, but there is no screen for making it.",
			],
			[
				"Missing",
				"Analytics beyond counting",
				"The coordinator's overview reports live figures, correctly scoped to what they"
				" may see. Growth, retention and comparison between branches are not built.",
			],
			[
				"By design",
				"Payment, events, recruitment, training",
				"A fee-bearing membership raises a transaction the payments app settles; events"
				" are browsed here and ticketed elsewhere; job openings are browsed here and"
				" applied for in the HR system; a course completed in the learning system can"
				" grant a certification here. Four small named seams, each of which works on a"
				" site where the other app is not installed. A demonstration crosses an"
				" application boundary at those four points and should be presented that way"
				" rather than as a gap.",
			],
			[
				"Not working",
				"Stipend approval",
				"A progress report or payment form can be filled in and submitted, and then waits"
				" for a departmental approval nobody can give. The reason is deliberate: this one"
				" runs supervisor to head of department, and the engine routing everything else"
				" resolves approvers by geography. Wiring it up would route every report promptly"
				" and confidently to the wrong person, and paperwork that comes back wrongly"
				" signed is worse than paperwork that comes back unsigned. It needs a resolver"
				" that understands departments.",
			],
		],
		[0.85, 1.55, 4.1],
	)

	w.p(
		"In that order, roughly: finish the person-record consolidation and get the suite green"
		" behind it, since everything downstream reads those facts; then documents on the"
		" application, which is the gap a real registrant notices first; then departmental routing,"
		" which turns stipends from a dead end into a working chain. Renewal and off-boarding after"
		" that — both are small, and both are felt by coordinators rather than by the public."
	)


if __name__ == "__main__":
	print(main())
