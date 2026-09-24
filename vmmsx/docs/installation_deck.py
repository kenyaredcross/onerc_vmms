# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""bench --site vmms.localhost execute vmmsx.docs.installation_deck.main

The installation deck explains how to set up a new site, slide by slide.

Writes `docs/vmmsx-installation-guide.pptx`. Like the guide and the status
brief it is a build artefact and `/docs/` is git-ignored: regenerate it, do not
edit the .pptx and commit the result.

**A deck rather than a document because of who reads it.** The guide describes
what the software is and the walkthrough what to do on a running site. This is
for the administrator preparing the site. They can keep the deck open beside
Frappe Cloud and follow one screen at a time.

**Every step slide carries an empty screenshot frame.** They are placeholders on
purpose. The captures have to come from a real install on the society's own
hosting. A screenshot from another society would show names and a hierarchy the
reader will not find on their own screen. The
caption inside each frame says what to capture, so the person doing the install
can fill them in as they go.

**What the deck claims about the software is read from the software.** The app
table is `hooks.required_apps` plus the two optional seams; the geography slides
follow `vmmsx/setup/wizard.py`, which is what actually writes the Geo Levels;
the Geo Node rules are the ones `onerc_core`'s `GeoNode.validate` enforces. When
one of those changes, this file is wrong and should be changed with it.

No site is needed. Use `bench execute` above, or run the module with the bench python.
"""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = APP_ROOT / "docs" / "vmmsx-installation-guide.pptx"

# --- palette --------------------------------------------------------------
#
# The movement's red for accents only, the way `writer.py` uses it in the
# .docx: a deck that painted whole panels red would be a brand exercise, and
# this one is a set of instructions.

INK = RGBColor(0x11, 0x18, 0x1F)
BODY = RGBColor(0x40, 0x4C, 0x59)
MUTED = RGBColor(0x7C, 0x8A, 0x97)
FAINT = RGBColor(0xB6, 0xC0, 0xC9)
ACCENT = RGBColor(0xC8, 0x10, 0x2E)
PANEL = RGBColor(0xF4, 0xF6, 0xF8)
SHOT_BG = RGBColor(0xF8, 0xFA, 0xFB)
BORDER = RGBColor(0xDD, 0xE3, 0xE8)
DASH = RGBColor(0xBF, 0xCA, 0xD3)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CODE_BG = RGBColor(0x14, 0x1B, 0x22)
CODE_TX = RGBColor(0xDA, 0xE3, 0xEA)
CODE_CM = RGBColor(0x7F, 0x92, 0xA3)
DIVIDER_TX = RGBColor(0x9F, 0xAE, 0xBB)
DIVIDER_RULE = RGBColor(0x26, 0x30, 0x39)

# Named for what the reader has installed, not for what looks best here. A font
# nobody has is substituted silently by PowerPoint, and the layout below is
# measured against these two.
SANS = "Segoe UI"
MONO = "Consolas"

# --- geometry -------------------------------------------------------------

W, H = 13.333, 7.5
MARGIN = 0.85
CONTENT_W = W - 2 * MARGIN
BODY_TOP = 2.12
FOOTER_Y = 6.94

REPO_VMMSX = "https://github.com/kenyaredcross/onerc_vmms"
REPO_CORE = "https://github.com/kenyaredcross/onerc_core"
REPO_SMS = "https://github.com/kenyaredcross/onerc_sms"
REPO_PAY = "https://github.com/kenyaredcross/onerc_payments"


# --------------------------------------------------------------------------
# The writer half. One file rather than two because there is one deck; if a
# second one is ever written, everything above `SLIDES` is the writer.
# --------------------------------------------------------------------------


def _slide(prs):
	"""A blank canvas. Every slide here is drawn, so no layout placeholders."""
	return prs.slides.add_slide(prs.slide_layouts[6])


def _rect(s, x, y, w, h, fill=None, line=None, lw=1.0, dashed=False):
	shape = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))

	if fill is None:
		shape.fill.background()
	else:
		shape.fill.solid()
		shape.fill.fore_color.rgb = fill

	if line is None:
		shape.line.fill.background()
	else:
		shape.line.color.rgb = line
		shape.line.width = Pt(lw)
		if dashed:
			shape.line.dash_style = MSO_LINE_DASH_STYLE.DASH

	shape.shadow.inherit = False
	shape.text_frame.word_wrap = True
	return shape


def _tbox(s, x, y, w, h, anchor=MSO_ANCHOR.TOP):
	frame = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
	frame.word_wrap = True
	frame.vertical_anchor = anchor
	frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
	return frame


def _para(tf, first=False, space_before=0, space_after=0, line=None, align=PP_ALIGN.LEFT):
	"""A text frame arrives with one empty paragraph; `first` claims it."""
	p = tf.paragraphs[0] if first else tf.add_paragraph()
	p.space_before = Pt(space_before)
	p.space_after = Pt(space_after)
	if line:
		p.line_spacing = line
	p.alignment = align
	return p


def _run(p, text, size=12, color=BODY, bold=False, font=SANS, italic=False, spacing=None, link=None):
	r = p.add_run()
	r.text = text
	r.font.size = Pt(size)
	r.font.color.rgb = color
	r.font.bold = bold
	r.font.italic = italic
	r.font.name = font

	if spacing is not None:
		# Letter-spacing has no python-pptx accessor. `spc` is hundredths of a
		# point on the run properties, and is what the eyebrow labels ride on.
		r.font._rPr.set("spc", str(int(spacing * 100)))

	if link:
		r.hyperlink.address = link
		# Setting the address restyles the run as a theme hyperlink; the colour
		# has to be reasserted afterwards or the deck grows a blue underline.
		r.font.color.rgb = color

	return r


def _footer(s, n, label="VMMS · Installation guide"):
	tf = _tbox(s, MARGIN, FOOTER_Y, CONTENT_W, 0.3)
	_run(_para(tf, first=True), label, size=9, color=FAINT, spacing=0.4)

	tf = _tbox(s, MARGIN, FOOTER_Y, CONTENT_W, 0.3)
	_run(_para(tf, first=True, align=PP_ALIGN.RIGHT), f"{n:02d}", size=9, color=FAINT, bold=True)


def _header(s, eyebrow, title, sub=None):
	tf = _tbox(s, MARGIN, 0.66, CONTENT_W, 0.3)
	_run(_para(tf, first=True), eyebrow.upper(), size=10, color=ACCENT, bold=True, spacing=1.6)

	tf = _tbox(s, MARGIN, 0.98, CONTENT_W, 0.62)
	_run(_para(tf, first=True, line=0.95), title, size=29, color=INK, bold=True)

	rule_y = 1.72
	if sub:
		tf = _tbox(s, MARGIN, 1.62, CONTENT_W - 0.4, 0.4)
		_run(_para(tf, first=True, line=1.15), sub, size=13, color=MUTED)
		rule_y = 2.06

	_rect(s, MARGIN, rule_y, CONTENT_W, 0.012, fill=BORDER)


def _shot(s, x, y, w, h, title, caption):
	"""An empty frame the installer drops their own capture into."""
	_rect(s, x, y, w, h, fill=WHITE, line=DASH, dashed=True)

	tf = _tbox(s, x + 0.32, y + 0.27, w - 0.64, min(1.35, h - 0.35))
	_run(
		_para(tf, first=True, space_after=5),
		"CAPTURE FROM YOUR SITE",
		size=8.5,
		color=ACCENT,
		bold=True,
		spacing=1.4,
	)
	_run(_para(tf, space_after=4, line=1.15), title, size=12.5, color=INK, bold=True)
	_run(_para(tf, line=1.2), caption, size=9.5, color=MUTED)


def _lines(s, x, y, w, items, marker, size=12.5, gap=10, height=4.4):
	"""A list. `marker` is given the one-based index and returns its prefix.

	Items are either a string or a (lead, rest) pair, where the lead is the part
	set in bold: the instruction's verb, or the name of the field being
	described. Splitting it in the content rather than parsing a delimiter out
	of the string keeps the copy readable where it is written.
	"""
	tf = _tbox(s, x, y, w, height)

	for index, item in enumerate(items, 1):
		p = _para(tf, first=(index == 1), space_after=gap, line=1.28)
		prefix, prefix_color = marker(index)
		_run(p, prefix, size=size, color=prefix_color, bold=True)

		if isinstance(item, tuple):
			_run(p, item[0], size=size, color=INK, bold=True)
			_run(p, item[1], size=size, color=BODY)
		else:
			_run(p, item, size=size, color=BODY)


def _steps(s, x, y, w, items, size=12.5, gap=11, height=4.4):
	_lines(s, x, y, w, items, lambda i: (f"{i}  ", ACCENT), size=size, gap=gap, height=height)


def _bullets(s, x, y, w, items, size=12.5, gap=10):
	_lines(s, x, y, w, items, lambda i: ("•   ", FAINT), size=size, gap=gap)


def _note(s, x, y, w, h, title, lines, tone=MUTED, size=11):
	"""An aside in a tinted panel with a coloured edge."""
	_rect(s, x, y, w, h, fill=PANEL)
	_rect(s, x, y, 0.045, h, fill=tone)

	tf = _tbox(s, x + 0.34, y + 0.22, w - 0.62, h - 0.4)
	_run(_para(tf, first=True, space_after=6), title.upper(), size=9.5, color=tone, bold=True, spacing=1.2)

	for line in lines:
		p = _para(tf, space_after=4, line=1.25)
		if isinstance(line, tuple):
			_run(p, line[0], size=size, color=INK, bold=True)
			_run(p, line[1], size=size, color=BODY)
		else:
			_run(p, line, size=size, color=BODY)


def _code(s, x, y, w, h, lines):
	"""A terminal block. A line starting with `#` is set as a comment."""
	_rect(s, x, y, w, h, fill=CODE_BG)
	tf = _tbox(s, x + 0.34, y + 0.26, w - 0.6, h - 0.5)

	for index, line in enumerate(lines):
		p = _para(tf, first=(index == 0), space_after=3, line=1.22)
		if not line:
			_run(p, " ", size=6, color=CODE_CM, font=MONO)
		elif line.startswith("#"):
			_run(p, line, size=10.5, color=CODE_CM, font=MONO)
		else:
			_run(p, line, size=11, color=CODE_TX, font=MONO)


def _table(s, x, y, w, rows, widths, row_h=0.42, head_h=0.4, size=10.5):
	"""A table. A cell is a string, or a (text, kind) pair: b bold, m mono."""
	shape = s.shapes.add_table(
		len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(head_h + row_h * (len(rows) - 1))
	)
	table = shape.table
	table.first_row = False
	table.horz_banding = False

	for index, width in enumerate(widths):
		table.columns[index].width = Inches(width)

	table.rows[0].height = Inches(head_h)
	for index in range(1, len(rows)):
		table.rows[index].height = Inches(row_h)

	for r, row in enumerate(rows):
		for c, value in enumerate(row):
			cell = table.cell(r, c)
			cell.margin_left = Inches(0.14)
			cell.margin_right = Inches(0.1)
			cell.margin_top = Inches(0.05)
			cell.margin_bottom = Inches(0.05)
			cell.vertical_anchor = MSO_ANCHOR.MIDDLE
			cell.fill.solid()
			cell.fill.fore_color.rgb = WHITE if r else INK

			cell.text_frame.word_wrap = True
			p = _para(cell.text_frame, first=True, line=1.1)
			text, kind = value if isinstance(value, tuple) else (value, "n")

			if r == 0:
				_run(p, text.upper(), size=9, color=WHITE, bold=True, spacing=1.0)
			elif kind == "b":
				_run(p, text, size=size, color=INK, bold=True)
			elif kind == "m":
				_run(p, text, size=size - 0.5, color=BODY, font=MONO)
			elif kind == "l":
				_run(p, text, size=size - 0.7, color=BODY, font=MONO, link=text)
			else:
				_run(p, text, size=size, color=BODY)


def _divider(s, part, title, blurb):
	_rect(s, 0, 0, W, H, fill=INK)
	_rect(s, 0, 0, 0.22, H, fill=ACCENT)

	tf = _tbox(s, 1.5, 2.55, 10, 0.4)
	_run(_para(tf, first=True), part.upper(), size=11, color=ACCENT, bold=True, spacing=2.0)

	tf = _tbox(s, 1.5, 2.98, 10.4, 1.0)
	_run(_para(tf, first=True, line=0.98), title, size=40, color=WHITE, bold=True)

	tf = _tbox(s, 1.5, 4.22, 8.6, 0.8)
	_run(_para(tf, first=True, line=1.3), blurb, size=14, color=DIVIDER_TX)


# --------------------------------------------------------------------------
# The slides, in the order they are presented.
# --------------------------------------------------------------------------


def _title(prs, n):
	s = _slide(prs)
	_rect(s, 0, 0, W, H, fill=INK)
	_rect(s, 0, 0, 0.22, H, fill=ACCENT)
	_rect(s, 1.5, 4.62, 1.5, 0.035, fill=ACCENT)

	tf = _tbox(s, 1.5, 1.95, 10, 0.4)
	_run(_para(tf, first=True), "INSTALLATION GUIDE", size=11.5, color=ACCENT, bold=True, spacing=2.2)

	tf = _tbox(s, 1.5, 2.42, 10.6, 1.8)
	_run(_para(tf, first=True, line=0.95), "Install VMMS on Frappe Cloud", size=42, color=WHITE, bold=True)
	_run(
		_para(tf, line=1.2, space_before=10),
		"Administrator guide: from an empty account to the first volunteer registration.",
		size=16,
		color=DIVIDER_TX,
	)

	tf = _tbox(s, 1.5, 4.95, 10.6, 1.2)
	p = _para(tf, first=True, space_after=7)
	_run(p, "Volunteer & Member Management System", size=12, color=RGBColor(0xC6, 0xD1, 0xDA), bold=True)

	p = _para(tf, space_after=4)
	_run(p, "Repository   ", size=11, color=MUTED)
	_run(p, "github.com/kenyaredcross/onerc_vmms", size=11, color=DIVIDER_TX, font=MONO, link=REPO_VMMSX)
	_run(p, "   ·   branch ", size=11, color=MUTED)
	_run(p, "vmmsx", size=11, color=DIVIDER_TX, font=MONO)

	_run(_para(tf), "Typical setup time: 45 to 60 minutes", size=11, color=MUTED)


def _overview(prs, n):
	s = _slide(prs)
	_header(
		s,
		"Overview",
		"Installation checklist",
		"Complete these six stages in order. You need administrator access to the site.",
	)

	stages = (
		("01", "Prepare", "Confirm access, site name, email account, logo and geographic levels."),
		("02", "Add apps", "Create the Frappe Cloud bench group and add each repository."),
		("03", "Create site", "Select the required apps and wait for installation to finish."),
		("04", "Run wizard", "Enter the society identity and geographic level structure."),
		("05", "Configure geography", "Add places and assign coordinators to the correct scope."),
		("06", "Test registration", "Configure outgoing email and submit a volunteer registration."),
	)

	for index, (number, title, detail) in enumerate(stages):
		y = 2.36 + index * 0.67
		_run(_para(_tbox(s, 1.0, y, 0.5, 0.3), first=True), number, size=11, color=ACCENT, bold=True)
		_run(_para(_tbox(s, 1.65, y - 0.02, 2.45, 0.35), first=True), title, size=14, color=INK, bold=True)
		_run(_para(_tbox(s, 4.25, y, 7.8, 0.36), first=True), detail, size=11.5, color=BODY)
		_rect(s, 1.0, y + 0.43, 11.1, 0.008, fill=BORDER)

	_footer(s, n)


def _prepare(prs, n):
	s = _slide(prs)
	_header(
		s,
		"Stage 1 · Prepare",
		"Before you start",
		"Have these details ready before creating the bench group.",
	)

	_bullets(
		s,
		MARGIN,
		2.42,
		6.4,
		[
			(
				"A place to run it.  ",
				"A Frappe Cloud account with billing set up, or your own bench on Frappe v16"
				" (Python 3.14+, MariaDB, Redis, Node 20+).",
			),
			(
				"Repository access.  ",
				"The four repos below are private. On Frappe Cloud, install the Frappe Cloud GitHub app"
				" on the organisation so it can read them.",
			),
			(
				"A site address.  ",
				"e.g. vmms.yoursociety.org, or a free *.frappe.cloud subdomain to start with.",
			),
			(
				"An outgoing email account.  ",
				"SMTP host, port, username and password. Nobody can register until this works.",
			),
			(
				"Your society's logo.  ",
				"PNG or SVG. It is asked for in the setup wizard and appears in the portal, emails"
				" and certificates.",
			),
			(
				"Your list of geographic levels.  ",
				"National, Region, County, Branch, or the levels your society uses, listed top down.",
			),
		],
		size=12,
	)

	_note(
		s,
		7.75,
		2.42,
		4.73,
		2.35,
		"You will be asked for",
		[
			("Organisation name", ": the full legal name"),
			("Short name", ": the initials used on cards and messages"),
			("Country and primary language", ""),
			("The level applications belong to", ": usually the lowest one"),
		],
	)
	_note(
		s,
		7.75,
		4.98,
		4.73,
		1.5,
		"Administrator details",
		[
			"The admin password you set during site creation, and the email address you want the first"
			" administrator account under.",
		],
		tone=MUTED,
	)
	_footer(s, n)


def _apps(prs, n):
	s = _slide(prs)
	_header(
		s,
		"Stage 1 · Prepare",
		"Apps and installation order",
		'VMMS declares required_apps = ["onerc_core"]. ERPNext is also required by the migration code.',
	)

	rows = [
		("App", "Repository · branch", "Purpose"),
		(("frappe", "b"), ("frappe/frappe · develop (v16)", "m"), "The framework. Frappe Cloud provides it."),
		(
			("erpnext", "b"),
			("frappe/erpnext · develop (v16)", "m"),
			"Required. project_fields.py adds Custom Fields to Project on every after_migrate.",
		),
		(
			("onerc_core", "b"),
			("kenyaredcross/onerc_core · vmmsx-edition", "m"),
			"Required. Provides Geo Level, Geo Node, Geo Assignment and National Society Settings.",
		),
		(
			("vmmsx", "b"),
			("kenyaredcross/onerc_vmms · vmmsx", "m"),
			"The application itself. Install it after core.",
		),
		(
			("hrms", "b"),
			("frappe/hrms · develop (v16)", "m"),
			"Optional. Provides recruitment and remains dormant when absent.",
		),
		(
			("onerc_sms", "b"),
			("kenyaredcross/onerc_sms · vmmsx-edition", "m"),
			"Optional. Provides SMS and WhatsApp messaging.",
		),
		(
			("onerc_payments", "b"),
			("kenyaredcross/onerc_payments · vmmsx-edition", "m"),
			"Optional. Provides stipends and volunteer payments.",
		),
	]
	_table(s, MARGIN, 2.46, CONTENT_W, rows, [1.9, 4.5, 5.23], row_h=0.44, head_h=0.38)

	_note(
		s,
		MARGIN,
		6.05,
		CONTENT_W,
		0.75,
		"Repository and folder names differ",
		[
			"The vmmsx app lives on the vmmsx branch of the onerc_vmms repository. Bench renames the"
			" checkout folder to vmmsx.",
		],
	)
	_footer(s, n)


def _part_one(prs, n):
	_divider(
		_slide(prs),
		"Part one",
		"Add the apps to a bench",
		"Frappe Cloud is the supported path. The CLI steps for a self-hosted bench are on slide 10.",
	)


def _bench_group(prs, n):
	s = _slide(prs)
	_header(s, "Stage 2 · Add the apps", "Create a bench group on Frappe Cloud")

	_steps(
		s,
		MARGIN,
		BODY_TOP + 0.24,
		4.85,
		[
			("Sign in at ", "frappecloud.com and open your team's dashboard."),
			("Go to ", "Benches, then New Bench Group."),
			("Name it ", "something recognisable, such as vmms-production."),
			("Choose the Frappe version ", "that matches the apps: v16."),
			("Choose a server ", "and region close to your users."),
		],
	)
	_note(
		s,
		MARGIN,
		5.72,
		4.85,
		1.05,
		"Bench group",
		[
			"A bench group is the set of apps your sites run. Sites are created inside it, and every site"
			" in it shares the same app versions.",
		],
	)
	_shot(
		s,
		6.15,
		BODY_TOP + 0.2,
		6.33,
		4.5,
		"Frappe Cloud → New Bench Group",
		"The creation form with the version and region filled in.\nCapture the full browser window.",
	)
	_footer(s, n)


def _add_apps(prs, n):
	s = _slide(prs)
	_header(
		s,
		"Stage 2 · Add the apps",
		"Add the private apps from GitHub",
		"Frappe Cloud must have access to the private kenyaredcross repositories.",
	)

	_steps(
		s,
		MARGIN,
		BODY_TOP + 0.28,
		5.65,
		[
			("Add ERPNext from the marketplace. ", "Add HRMS there too if recruitment is required."),
			("Open the Apps tab, ", "select Add App, then select Add from GitHub."),
			("Choose Private Repository, ", "paste the GitHub URL and select Fetch Branches."),
			("Select the branch ", "shown in the table below, then select Add App."),
			("Repeat for each app. ", "Add onerc_core before vmmsx. SMS and payments are optional."),
		],
		size=11.2,
		gap=7,
		height=2.25,
	)
	_shot(
		s,
		6.82,
		BODY_TOP + 0.25,
		5.66,
		2.12,
		"Apps → Add App → Add from GitHub",
		"The Private Repository tab with a URL pasted and the required branch selected.",
	)

	rows = [
		("App", "Paste this GitHub URL", "Branch"),
		(("onerc_core", "b"), (REPO_CORE, "l"), ("vmmsx-edition", "m")),
		(("vmmsx", "b"), (REPO_VMMSX, "l"), ("vmmsx", "m")),
		(("onerc_sms (optional)", "b"), (REPO_SMS, "l"), ("vmmsx-edition", "m")),
		(("onerc_payments (optional)", "b"), (REPO_PAY, "l"), ("vmmsx-edition", "m")),
	]
	_table(
		s,
		MARGIN,
		4.72,
		CONTENT_W,
		rows,
		[2.45, 6.7, 2.48],
		row_h=0.39,
		head_h=0.34,
		size=9.7,
	)
	_footer(s, n)


def _deploy(prs, n):
	s = _slide(prs)
	_header(s, "Stage 2 · Add the apps", "Deploy the bench")

	_steps(
		s,
		MARGIN,
		BODY_TOP + 0.24,
		4.85,
		[
			("Click ", "Deploy once every app is on the list."),
			("Review the app versions ", "in the confirmation dialog and confirm."),
			("Wait for the build ", "to finish. It usually takes 5 to 15 minutes, and the log updates live."),
			(
				"Check the log ",
				"if it fails. Start with the dependency list and access to the private repositories.",
			),
		],
	)
	_note(
		s,
		MARGIN,
		5.5,
		4.85,
		1.28,
		"The build compiles the portal",
		[
			"The volunteer portal is a React app built during deployment. A green deployment has already"
			" built it. No separate build is required.",
		],
	)
	_shot(
		s,
		6.15,
		BODY_TOP + 0.2,
		6.33,
		4.5,
		"Frappe Cloud → Deploys → build log",
		"A successful deployment, showing all apps and a green status.\nScroll to the end of the log before capturing.",
	)
	_footer(s, n)


def _create_site(prs, n):
	s = _slide(prs)
	_header(s, "Stage 3 · Create the site", "Create the site and choose its apps")

	_steps(
		s,
		MARGIN,
		BODY_TOP + 0.24,
		4.85,
		[
			("From the bench group choose ", "New Site."),
			("Enter the subdomain ", "or attach your own domain later."),
			("Select the apps ", "to install: erpnext, onerc_core, vmmsx, plus any optional ones."),
			("Create the site ", "and wait for it to come up."),
			("Open the site. ", "The first sign-in opens the setup wizard."),
		],
		gap=9,
	)
	_note(
		s,
		MARGIN,
		5.85,
		4.85,
		0.99,
		"Order matters here too",
		[
			"Tick onerc_core above vmmsx. Frappe installs the apps in the order shown, and vmmsx needs core's doctypes.",
		],
	)
	_shot(
		s,
		6.15,
		BODY_TOP + 0.2,
		6.33,
		4.5,
		"Frappe Cloud → New Site → app selection",
		"The app checklist with erpnext, onerc_core and vmmsx ticked.\nThe site name should be visible at the top.",
	)
	_footer(s, n)


def _self_hosted(prs, n):
	s = _slide(prs)
	_header(
		s,
		"Alternative",
		"On your own bench",
		"Same result, from the command line. Skip this slide if you are on Frappe Cloud.",
	)

	_code(
		s,
		MARGIN,
		2.42,
		7.1,
		3.62,
		[
			"# from the root of a bench running Frappe v16",
			"cd $PATH_TO_YOUR_BENCH",
			"",
			"bench get-app erpnext",
			"bench get-app https://github.com/kenyaredcross/onerc_core \\",
			"      --branch vmmsx-edition",
			"bench get-app https://github.com/kenyaredcross/onerc_vmms \\",
			"      --branch vmmsx",
			"",
			"bench new-site vmms.yoursociety.org",
			"bench --site vmms.yoursociety.org \\",
			"      install-app erpnext onerc_core vmmsx",
			"",
			"bench --site vmms.yoursociety.org migrate",
			"bench build --app vmmsx",
		],
	)

	_bullets(
		s,
		8.25,
		2.42,
		4.23,
		[
			("Install core first. ", "vmmsx refuses to install without it."),
			("The folder is renamed. ", "The onerc_vmms repo checks out as apps/vmmsx."),
			(
				"Set host_name ",
				"in the site config. Include the port when the site uses one, or password links may omit it.",
			),
		],
		size=11.5,
		gap=9,
	)
	_code(
		s,
		8.25,
		5.05,
		4.23,
		0.99,
		[
			"# sites/<site>/site_config.json",
			'"host_name": "http://vmms.yoursociety.org:8000"',
		],
	)
	_note(
		s,
		8.25,
		6.14,
		4.23,
		0.7,
		"Open the site",
		["bench --site <site> browse --user Administrator"],
		tone=MUTED,
		size=10,
	)
	_footer(s, n)


def _wizard_opens(prs, n):
	s = _slide(prs)
	_header(s, "Stage 4 · The wizard", "First run: the setup wizard")

	_steps(
		s,
		MARGIN,
		BODY_TOP + 0.24,
		4.85,
		[
			("Open the site ", "and sign in as Administrator with the password from site creation."),
			(
				"Work through Frappe's own slides ",
				"first: language, country and time zone, then the currency and company slides ERPNext adds.",
			),
			("Complete the two VMMS slides. ", "The society details come first, followed by geography."),
			(
				"Do not skip them. ",
				"The wizard is where the society's identity and its geographic ladder are written.",
			),
		],
		gap=9,
	)
	_note(
		s,
		MARGIN,
		5.85,
		4.85,
		0.94,
		"This runs once",
		[
			"When the wizard finishes, the site opens the VMMS Setup workspace. The wizard does not run again.",
		],
	)
	_shot(
		s,
		6.15,
		BODY_TOP + 0.2,
		6.33,
		4.5,
		"The setup wizard, first slide",
		"Frappe's welcome slide on a fresh site.\nCapture before entering anything.",
	)
	_footer(s, n)


def _wizard_society(prs, n):
	s = _slide(prs)
	_header(
		s,
		"Stage 4 · The wizard",
		"Tell us about your National Society",
		"Organization Name, Short Name and Logo are all required.",
	)

	_bullets(
		s,
		MARGIN,
		BODY_TOP + 0.24,
		4.85,
		[
			("Organization Name: ", "the full name, for example Tanzania Red Cross Society."),
			(
				"Short Name: ",
				"the initials. The wizard proposes them from the name. Edit them if needed.",
			),
			(
				"Logo: ",
				"required and stored publicly because it is shown before sign-in, on the portal"
				" landing page, in every email and on membership certificates.",
			),
		],
		gap=11,
	)
	_note(
		s,
		MARGIN,
		5.42,
		4.85,
		1.36,
		"Saved in",
		[
			"National Society Settings, a single record owned by onerc_core. Every one of these values can"
			" be changed later, and the theme, address and social links live on the same record.",
		],
	)
	_shot(
		s,
		6.15,
		BODY_TOP + 0.2,
		6.33,
		4.5,
		"Wizard → Tell us about your National Society",
		"All three fields filled in, with the logo preview showing.",
	)
	_footer(s, n)


def _wizard_geography(prs, n):
	s = _slide(prs)
	_header(
		s,
		"Stage 4 · The wizard",
		"Where does your Society operate?",
		"This is the geographic hierarchy. Build it from the national level down.",
	)

	_steps(
		s,
		MARGIN,
		BODY_TOP + 0.34,
		4.85,
		[
			(
				"Name the top level. ",
				"Use National, or the term your society uses for the whole country.",
			),
			("Add a level for each tier ", "below it: Region, County, Branch, Unit. As many as you use."),
			("Name the levels, not the places. ", "Nairobi is a place; County is a level."),
			(
				"Choose the application level ",
				"at the bottom of the slide. This is the tier an applicant selects when registering."
				" Usually the lowest.",
			),
		],
		gap=10,
	)
	_shot(
		s,
		6.15,
		BODY_TOP + 0.3,
		6.33,
		3.1,
		"Wizard → Where does your Society operate?",
		"Four levels entered, with the application-level dropdown open.",
	)
	_note(
		s,
		6.15,
		5.62,
		6.33,
		1.22,
		"Saved by the wizard",
		[
			"One Geo Level per row, numbered from the top. Every level below the first is marked as requiring"
			" a parent, and the last is marked the lowest. You can edit all of it afterwards.",
		],
	)
	_footer(s, n)


def _part_two(prs, n):
	_divider(
		_slide(prs),
		"Part two",
		"Build the geography",
		"The wizard created the levels. Next, add the actual places and assign staff access.",
	)


def _setup_workspace(prs, n):
	s = _slide(prs)
	_header(s, "Stage 5 · Geography", "The VMMS Setup workspace")

	_bullets(
		s,
		MARGIN,
		BODY_TOP + 0.24,
		4.85,
		[
			(
				"The wizard lands here. ",
				"It is a checklist of everything a fresh site needs before day one, in dependency order.",
			),
			(
				"Work down it. ",
				"Geography first, then settings, then the types and categories, then approval workflows"
				" and templates.",
			),
			("Steps tick themselves off ", "as you save each form, so you can leave and come back."),
			("Find it again ", "from the Desk sidebar: VMMS Setup."),
		],
		gap=10,
	)
	_note(
		s,
		MARGIN,
		5.72,
		4.85,
		1.1,
		"Only the geography is covered here",
		[
			"Membership types, certifications, time-log categories and approval workflows are"
			" society-specific. Set them after the site is up.",
		],
	)
	_shot(
		s,
		6.15,
		BODY_TOP + 0.2,
		6.33,
		4.5,
		"Desk → VMMS Setup workspace",
		"The onboarding checklist with the first steps complete.\nCapture the whole workspace, sidebar included.",
	)
	_footer(s, n)


def _geo_levels(prs, n):
	s = _slide(prs)
	_header(
		s,
		"Stage 5 · Geography",
		"Check the levels",
		"Geo Level is the ladder the wizard just created. Open the list and confirm each rung.",
	)

	rows = [
		("Field", "What it means"),
		(("Geo Level Name", "b"), "What your society calls this tier, such as County, Branch or Unit."),
		(
			("Geo Level Key", "b"),
			"The stable internal key. Generated from the name; leave it alone once places exist.",
		),
		(
			("Geo Level Order", "b"),
			"1 is the top. Every level below must be a higher number than its parent's.",
		),
		(("Requires Parent", "b"), "On for every level except the top one."),
		(("Is Lowest Level", "b"), "On for the bottom rung only."),
		(("Is Active", "b"), "Turn off a tier you have stopped using rather than deleting it."),
	]
	_table(s, MARGIN, 2.5, 5.95, rows, [1.85, 4.10], row_h=0.5, head_h=0.38)

	_shot(s, 7.1, 2.5, 5.38, 3.28, "Desk → Geo Level list", "The full ladder, ordered top to bottom.")
	_note(
		s,
		7.1,
		5.9,
		5.38,
		0.94,
		"Adding a tier later",
		[
			"Add the tier first, then re-parent the places under it. Renaming a level is safe; changing its"
			" key is not.",
		],
	)
	_footer(s, n)


def _geo_nodes(prs, n):
	s = _slide(prs)
	_header(
		s,
		"Stage 5 · Geography",
		"Add the places: Geo Nodes",
		"A Geo Node is an actual location assigned to one Geo Level.",
	)

	_steps(
		s,
		MARGIN,
		BODY_TOP + 0.34,
		4.85,
		[
			("Open Geo Node ", "and switch to the tree view."),
			("Create the national node first. ", "Use the top level and leave the parent empty."),
			("Add each place under its parent, ", "setting its Geo Level as you go."),
			("Add a code ", "if your society uses one, and coordinates if you want the node on a map."),
			(
				"Use the import tool ",
				"for a long list: prepare a spreadsheet, and import parents before children.",
			),
		],
		gap=9,
		size=12.3,
	)
	_shot(
		s,
		6.15,
		BODY_TOP + 0.3,
		6.33,
		2.72,
		"Desk → Geo Node → tree view",
		"The tree expanded two levels deep.",
	)
	_note(
		s,
		6.15,
		5.26,
		6.33,
		1.58,
		"The rules it enforces",
		[
			"Geo Node is a NestedSet with a tree view; records are named GEO-#####.",
			"A level is required. Below the top, a parent is required and must be on a shallower level.",
			"Sibling names must be unique under one parent. Coordinates are optional and range-checked.",
		],
		size=10.2,
	)
	_footer(s, n)


def _geo_assignments(prs, n):
	s = _slide(prs)
	_header(
		s,
		"Stage 5 · Geography",
		"Who sees which part of the tree",
		"Geo Assignment ties a person to a place. Without one, a coordinator sees nothing.",
	)

	_bullets(
		s,
		MARGIN,
		BODY_TOP + 0.24,
		5.5,
		[
			("User: ", "the staff account."),
			("Role: ", "the work they are allowed to do at this location."),
			("Geo Node: ", "the location they can access, including all nodes below it."),
			("Valid From / Valid To: ", "optional dates for a temporary assignment."),
			("Is Active: ", "clear this instead of deleting the assignment so the history remains."),
		],
		gap=10,
	)
	_note(
		s,
		MARGIN,
		5.78,
		5.5,
		1.06,
		"Applies across the site",
		[
			"Geo Assignment scopes every list on the site. An administrator sees everything; a coordinator"
			" without a live assignment sees nothing.",
		],
	)
	_shot(
		s,
		6.8,
		BODY_TOP + 0.2,
		5.68,
		4.5,
		"Desk → Geo Assignment → new",
		"One assignment with User, Role and Geo Node filled in.\nA populated list view also works.",
	)
	_footer(s, n)


def _part_three(prs, n):
	_divider(
		_slide(prs),
		"Part three",
		"Email, then go live",
		"Registration uses email for the welcome message and password link. Test it before launch.",
	)


def _email(prs, n):
	s = _slide(prs)
	_header(
		s,
		"Stage 6 · Email",
		"Set up outgoing email",
		"Create one Email Account and mark it as the site's default outgoing account.",
	)

	_steps(
		s,
		MARGIN,
		BODY_TOP + 0.34,
		5.15,
		[
			("Open ", "Email Account in the Desk and create a new one."),
			("Enter the sending address, ", "such as noreply@yoursociety.org."),
			("Tick Enable Outgoing ", "and Default Outgoing."),
			("Fill in the SMTP details: ", "host, port, and the password or app password."),
			("Save, then send a test ", "with the Send Test Mail button."),
		],
		gap=9,
		size=12.3,
	)
	_shot(
		s,
		6.45,
		BODY_TOP + 0.3,
		6.03,
		2.85,
		"Desk → Email Account → new",
		"The outgoing account with Default Outgoing ticked.\nBlank out the password before capturing.",
	)
	_note(
		s,
		6.45,
		5.4,
		6.03,
		1.44,
		"Messages sent through this account",
		[
			"The app already installs the welcome email template; this account lets it send the password link.",
			"Every approval, rejection and lifecycle message about an application, with a guardian copied"
			" in where the applicant is a minor.",
			"Announcements and direct messages from the console.",
		],
	)
	_footer(s, n)


def _verify(prs, n):
	s = _slide(prs)
	_header(
		s,
		"Stage 6 · Go live",
		"Verify with a real registration",
		"Do this yourself, once, before anyone else touches the site.",
	)

	_steps(
		s,
		MARGIN,
		BODY_TOP + 0.34,
		5.15,
		[
			("Open the portal ", "at https://your-site/home while signed out, preferably in a private window."),
			(
				"Choose Join ",
				"and complete the form as a volunteer would, using an address you can read.",
			),
			("Check the inbox. ", "The welcome email should arrive within a minute."),
			(
				"Follow the link, ",
				"set a password, and confirm it lands in the portal rather than on a desk.",
			),
			("Check the console: ", "the application should be sitting in the review queue."),
			("Keep /verify public. ", "It is the card-check page used when somebody scans a VMMS card."),
		],
		gap=7,
		size=11.5,
	)
	_shot(
		s,
		6.45,
		BODY_TOP + 0.3,
		6.03,
		3.05,
		"The portal landing page and the Join form",
		"Two screenshots side by side if you have room:\nthe public landing page, and the welcome email.",
	)
	_note(
		s,
		6.45,
		5.6,
		6.03,
		1.24,
		"If the email never arrives",
		[
			"Check Email Queue in the Desk. A row stuck at Not Sent is an SMTP problem; no row at all means"
			" no default outgoing account.",
		],
	)
	_footer(s, n)


def _troubleshooting(prs, n):
	s = _slide(prs)
	_header(s, "Reference", "If something goes wrong")

	rows = [
		("What you see", "What it means", "What to do"),
		(
			("The repository is not listed on Frappe Cloud", "b"),
			"The GitHub app cannot read a private repo.",
			"Grant it access in GitHub → Settings → Applications.",
		),
		(
			("Installation fails on vmmsx", "b"),
			"onerc_core is not installed yet.",
			"Install core first, then vmmsx, then run migrate.",
		),
		(
			('"Add at least one geographic level"', "b"),
			"The wizard's geography slide was submitted empty.",
			"Go back a slide and name at least the top level.",
		),
		(
			("Password links open a page that will not load", "b"),
			"The site does not know its own address.",
			"Set host_name in the site config. On Frappe Cloud this is set for you.",
		),
		(
			('"Geo Node GEO-00000 does not exist"', "b"),
			"A node was deleted while records still pointed at it.",
			"Recreate it, or re-point the records, then delete properly.",
		),
		(
			("A coordinator sees an empty list", "b"),
			"No Geo Assignment, or an inactive one.",
			"Give them an assignment on the right node.",
		),
		(
			("No email arrives", "b"),
			"No default outgoing account, or SMTP is refusing.",
			"Check Email Account and Email Queue.",
		),
	]
	_table(s, MARGIN, 2.34, CONTENT_W, rows, [4.0, 3.9, 3.73], row_h=0.58, head_h=0.38, size=10)
	_footer(s, n)


def _links(prs, n):
	s = _slide(prs)
	_rect(s, 0, 0, W, H, fill=INK)
	_rect(s, 0, 0, 0.22, H, fill=ACCENT)

	tf = _tbox(s, 1.5, 0.95, 10, 0.34)
	_run(_para(tf, first=True), "REFERENCE", size=10.5, color=ACCENT, bold=True, spacing=2.0)

	tf = _tbox(s, 1.5, 1.32, 10, 0.7)
	_run(_para(tf, first=True), "Repositories and documentation", size=32, color=WHITE, bold=True)

	links = (
		("vmmsx", "The application. Branch: vmmsx", "github.com/kenyaredcross/onerc_vmms", REPO_VMMSX),
		(
			"onerc_core",
			"Geography and society settings. Branch: vmmsx-edition",
			"github.com/kenyaredcross/onerc_core",
			REPO_CORE,
		),
		(
			"onerc_sms",
			"Optional. SMS and WhatsApp. Branch: vmmsx-edition",
			"github.com/kenyaredcross/onerc_sms",
			REPO_SMS,
		),
		(
			"onerc_payments",
			"Optional. Stipends. Branch: vmmsx-edition",
			"github.com/kenyaredcross/onerc_payments",
			REPO_PAY,
		),
		(
			"Frappe Cloud",
			"Hosting, bench groups and deployments",
			"frappecloud.com",
			"https://frappecloud.com",
		),
		(
			"Frappe Cloud docs",
			"Bench groups, sites, domains and email",
			"docs.frappe.io/cloud",
			"https://docs.frappe.io/cloud",
		),
		("bench CLI", "Self-hosted installs", "github.com/frappe/bench", "https://github.com/frappe/bench"),
	)

	y = 2.4
	for name, blurb, label, url in links:
		_run(_para(_tbox(s, 1.5, y, 3.1, 0.3), first=True), name, size=12.5, color=WHITE, bold=True)
		_run(
			_para(_tbox(s, 4.35, y + 0.01, 3.7, 0.3), first=True),
			blurb,
			size=11,
			color=RGBColor(0x8E, 0x9D, 0xAB),
		)
		_run(
			_para(_tbox(s, 8.2, y + 0.01, 4.3, 0.3), first=True),
			label,
			size=11,
			color=WHITE,
			font=MONO,
			link=url,
		)
		_rect(s, 1.5, y + 0.4, 11.0, 0.008, fill=DIVIDER_RULE)
		y += 0.58

	_run(
		_para(_tbox(s, 1.5, 6.72, 11, 0.3), first=True),
		"Replace every screenshot placeholder with a capture from your own site before handing this on.",
		size=10.5,
		color=MUTED,
		italic=True,
	)


# The deck, in order. A slide is a function of (presentation, slide number);
# the number is what the footer prints, and the dividers and the two dark
# slides ignore it because they carry no footer.
SLIDES = (
	_title,
	_overview,
	_prepare,
	_apps,
	_part_one,
	_bench_group,
	_add_apps,
	_deploy,
	_create_site,
	_self_hosted,
	_wizard_opens,
	_wizard_society,
	_wizard_geography,
	_part_two,
	_setup_workspace,
	_geo_levels,
	_geo_nodes,
	_geo_assignments,
	_part_three,
	_email,
	_verify,
	_troubleshooting,
	_links,
)


def main(path: str | None = None) -> str:
	"""Build the deck and return where it was written."""
	target = Path(path) if path else OUTPUT

	prs = Presentation()
	prs.slide_width = Inches(W)
	prs.slide_height = Inches(H)

	for number, build_slide in enumerate(SLIDES, 1):
		build_slide(prs, number)

	target.parent.mkdir(parents=True, exist_ok=True)
	prs.save(str(target))

	return str(target)


if __name__ == "__main__":
	print(main())
