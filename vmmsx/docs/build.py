# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Assemble the guide.

    bench --site vmms.localhost execute vmmsx.docs.build.main

Writes `docs/vmmsx-guide.docx` — cover, contents, then one top-level section per
module in `sections.SECTIONS` order. The output is git-ignored on purpose: it is
a build artefact, and a committed binary would be a file nobody can diff that
goes stale the moment a field changes.

Rendered twice. The contents page is generated from the outline the body
produces, and that outline does not exist until the body has been written, so
the first pass exists only to collect it. Rendering is deterministic apart from
the timestamp, which is passed in rather than read twice.
"""

from datetime import datetime
from pathlib import Path

from vmmsx.docs.sections import SECTIONS
from vmmsx.docs.writer import Writer

APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = APP_ROOT / "docs" / "vmmsx-guide.docx"

TITLE = "vmmsx"
SUBTITLE = "Volunteer & Member Management System — System Guide"

BLURB = (
	"A living document. Each stage of the build appends one top-level section and leaves the"
	" others as they were. It is generated from the source — field tables are read from the"
	" doctype JSON the site installs from, so they cannot drift out of step with the schema."
)


def main(path: str | None = None) -> str:
	"""Build the guide and return where it was written."""
	target = Path(path) if path else OUTPUT
	generated_on = datetime.now().strftime("%d %B %Y")

	collected = _render(generated_on, outline=None).outline
	writer = _render(generated_on, outline=collected)

	target.parent.mkdir(parents=True, exist_ok=True)
	writer.doc.save(str(target))

	return str(target)


def _render(generated_on: str, outline: list[tuple[int, str, str]] | None) -> Writer:
	writer = Writer()

	writer.cover(
		TITLE,
		SUBTITLE,
		[
			("Generated", generated_on),
			("Sections", ", ".join(section.TITLE for section in SECTIONS)),
			("Built from", "vmmsx/docs — regenerate, do not edit the .docx"),
			("Depends on", "onerc_core (identity, geo, access)"),
		],
		blurb=BLURB,
	)

	if outline is not None:
		writer.contents(outline)

	for index, section in enumerate(SECTIONS):
		if index:
			writer.page_break()

		section.render(writer)

	return writer


if __name__ == "__main__":
	print(main())
