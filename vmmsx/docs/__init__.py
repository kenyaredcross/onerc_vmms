# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The source of the living guide.

`docs/vmmsx-guide.docx` is a build artefact, not a document anybody edits. This
package builds it: `build.main()` assembles a cover, a contents page and one
top-level section per module, in the order given by `sections.SECTIONS`.

A later stage — Member, Volunteer, Deployment — adds a module under `sections/`
and one line to that list. It does not touch the sections already there.

The guide is generated rather than transcribed: field tables come from the
doctype JSON on disk and the state table from `vmmsx.approvals.states`, so
neither can drift out of step with the code. Prose names the file or function it
describes, so a reader can go and check it.

No site is needed — build it with `bench execute vmmsx.docs.build.main` or with
the bench python directly.
"""
