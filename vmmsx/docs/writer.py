# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A thin layer over python-docx, so section modules write prose, not XML.

Two things here are worth knowing:

**Headings number themselves and record an outline.** `h1` opens a module's
section and resets the sub-counters; `h2`/`h3` number beneath it. Every heading
is appended to `outline`, which is what the contents page is built from — so
the contents cannot list a heading the document does not have, or miss one it
does.

**The contents page needs the outline before the body is written**, and the
outline does not exist until the body has been written. `build` resolves that
by rendering twice: once to collect, once for real. Rendering is deterministic
apart from the timestamp, which is passed in.
"""

import html
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

BODY_FONT = "Calibri"
MONO_FONT = "Consolas"

INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x60, 0x60, 0x60)
ACCENT = RGBColor(0xA8, 0x1C, 0x22)  # the movement's red, for headings only
HEADER_FILL = "F2F2F2"

TAG = re.compile(r"<[^>]+>")


def plain(text: str) -> str:
	"""Field descriptions carry desk HTML (`<b>`, `<i>`). Word wants the words."""
	return html.unescape(TAG.sub("", text or "")).strip()


class Writer:
	"""One document under construction, plus the outline it has accumulated."""

	def __init__(self):
		self.doc = Document()
		self.outline: list[tuple[int, str, str]] = []
		self._counters = [0, 0, 0]

		self._style_document()

	# --- page furniture ---------------------------------------------------

	def _style_document(self) -> None:
		for section in self.doc.sections:
			section.left_margin = Inches(1.0)
			section.right_margin = Inches(1.0)
			section.top_margin = Inches(0.9)
			section.bottom_margin = Inches(0.9)

		normal = self.doc.styles["Normal"]
		normal.font.name = BODY_FONT
		normal.font.size = Pt(10.5)
		normal.font.color.rgb = INK
		normal.paragraph_format.space_after = Pt(7)
		normal.paragraph_format.line_spacing = 1.12

		# The east-asian font name has to be set through XML or Word ignores the
		# choice for anything outside latin-1.
		normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)

		for level, size in ((1, 17), (2, 13), (3, 11.5)):
			style = self.doc.styles[f"Heading {level}"]
			style.font.name = BODY_FONT
			style.font.size = Pt(size)
			style.font.bold = True
			style.font.color.rgb = ACCENT if level < 3 else INK
			style.paragraph_format.space_before = Pt(16 if level == 1 else 12)
			style.paragraph_format.space_after = Pt(5)

	def page_break(self) -> None:
		self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

	def cover(self, title: str, subtitle: str, meta: list[tuple[str, str]], blurb: str = "") -> None:
		"""Title page. Deliberately quiet: a guide, not a brochure."""
		spacer = self.doc.add_paragraph()
		spacer.paragraph_format.space_after = Pt(120)

		heading = self.doc.add_paragraph()
		run = heading.add_run(title)
		run.font.size = Pt(34)
		run.font.bold = True
		run.font.color.rgb = ACCENT
		heading.paragraph_format.space_after = Pt(2)

		sub = self.doc.add_paragraph()
		sub_run = sub.add_run(subtitle)
		sub_run.font.size = Pt(13)
		sub_run.font.color.rgb = MUTED
		sub.paragraph_format.space_after = Pt(28)

		for label, value in meta:
			line = self.doc.add_paragraph()
			line.paragraph_format.space_after = Pt(2)

			key = line.add_run(f"{label}   ")
			key.font.size = Pt(9)
			key.font.color.rgb = MUTED

			val = line.add_run(value)
			val.font.size = Pt(9)
			val.font.bold = True

		if blurb:
			para = self.doc.add_paragraph()
			para.paragraph_format.space_before = Pt(28)
			run = para.add_run(plain(blurb))
			run.font.size = Pt(9.5)
			run.font.color.rgb = MUTED
			run.italic = True

		self.page_break()

	def contents(self, outline: list[tuple[int, str, str]]) -> None:
		"""A generated contents page — not a Word field nobody remembers to refresh."""
		heading = self.doc.add_paragraph()
		run = heading.add_run("Contents")
		run.font.size = Pt(17)
		run.font.bold = True
		run.font.color.rgb = ACCENT
		heading.paragraph_format.space_after = Pt(10)

		for level, number, title in outline:
			if level > 2:
				continue

			entry = self.doc.add_paragraph()
			entry.paragraph_format.space_after = Pt(3 if level == 1 else 1)
			entry.paragraph_format.left_indent = Inches(0 if level == 1 else 0.3)

			text = entry.add_run(f"{number}   {title}")
			text.font.bold = level == 1
			text.font.size = Pt(11 if level == 1 else 10)

			if level == 1:
				entry.paragraph_format.space_before = Pt(8)

		self.page_break()

	# --- headings ---------------------------------------------------------

	def _number(self, level: int) -> str:
		self._counters[level - 1] += 1

		for deeper in range(level, len(self._counters)):
			self._counters[deeper] = 0

		return ".".join(str(part) for part in self._counters[:level])

	def heading(self, level: int, title: str) -> str:
		number = self._number(level)
		self.outline.append((level, number, title))
		self.doc.add_heading(f"{number}  {title}", level=level)

		return number

	def h1(self, title: str) -> str:
		return self.heading(1, title)

	def h2(self, title: str) -> str:
		return self.heading(2, title)

	def h3(self, title: str) -> str:
		return self.heading(3, title)

	# --- body -------------------------------------------------------------

	def p(self, text: str) -> None:
		self.doc.add_paragraph(plain(text))

	def lead(self, text: str) -> None:
		"""The one-paragraph answer to "what is this", set slightly larger."""
		para = self.doc.add_paragraph()
		run = para.add_run(plain(text))
		run.font.size = Pt(11.5)
		run.font.color.rgb = MUTED
		para.paragraph_format.space_after = Pt(10)

	def bullets(self, items: list[str]) -> None:
		for item in items:
			para = self.doc.add_paragraph(plain(item), style="List Bullet")
			para.paragraph_format.space_after = Pt(3)

	def steps(self, items: list[str]) -> None:
		for item in items:
			para = self.doc.add_paragraph(plain(item), style="List Number")
			para.paragraph_format.space_after = Pt(3)

	def code(self, text: str) -> None:
		para = self.doc.add_paragraph()
		para.paragraph_format.left_indent = Inches(0.25)
		para.paragraph_format.space_before = Pt(4)
		para.paragraph_format.space_after = Pt(8)

		run = para.add_run(text)
		run.font.name = MONO_FONT
		run.font.size = Pt(9)
		run.element.rPr.rFonts.set(qn("w:eastAsia"), MONO_FONT)

	def note(self, text: str) -> None:
		para = self.doc.add_paragraph()
		para.paragraph_format.left_indent = Inches(0.25)
		para.paragraph_format.space_after = Pt(10)

		run = para.add_run(plain(text))
		run.italic = True
		run.font.size = Pt(9.5)
		run.font.color.rgb = MUTED

	def table(self, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
		table = self.doc.add_table(rows=1, cols=len(headers))
		table.style = "Table Grid"
		table.alignment = WD_TABLE_ALIGNMENT.LEFT
		table.autofit = False

		for cell, text, width in zip(table.rows[0].cells, headers, widths, strict=True):
			cell.width = Inches(width)
			self._fill(cell)
			paragraph = cell.paragraphs[0]
			paragraph.paragraph_format.space_after = Pt(2)
			run = paragraph.add_run(text)
			run.font.bold = True
			run.font.size = Pt(9.5)

		for values in rows:
			cells = table.add_row().cells

			for cell, text, width in zip(cells, values, widths, strict=True):
				cell.width = Inches(width)
				paragraph = cell.paragraphs[0]
				paragraph.paragraph_format.space_after = Pt(2)
				run = paragraph.add_run(plain(text))
				run.font.size = Pt(9)

		self.doc.add_paragraph().paragraph_format.space_after = Pt(4)

	def _fill(self, cell) -> None:
		"""Header shading. python-docx has no API for it, so it is XML."""
		shading = cell._tc.get_or_add_tcPr().makeelement(qn("w:shd"), {})
		shading.set(qn("w:val"), "clear")
		shading.set(qn("w:fill"), HEADER_FILL)
		cell._tc.get_or_add_tcPr().append(shading)

	def caption(self, text: str) -> None:
		para = self.doc.add_paragraph()
		para.alignment = WD_ALIGN_PARAGRAPH.LEFT
		para.paragraph_format.space_after = Pt(10)

		run = para.add_run(plain(text))
		run.font.size = Pt(9)
		run.font.color.rgb = MUTED
