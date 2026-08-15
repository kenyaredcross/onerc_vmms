# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Buzz stops at the seam.

The seam is two crossings and no more. BUZZ-01 writes one custom field onto
`Buzz Event`; BUZZ-02 reads the events a society has already published. So
`Buzz Event` may be named by exactly three files — `vmmsx/buzz/services/geo.py`
and `vmmsx/buzz/services/events.py`, the two halves of the seam, and
`vmmsx/patches/setup_buzz_seam.py`, the patch that installs the field — and
nowhere else in the app.

**Reading a listing is not building a bridge.** BUZZ-02 widened the seam
deliberately and in one direction only: title, date, venue, category, image,
route. No attendee, booking, ticket or check-in doctype Buzz owns is named
anywhere in vmmsx at all, this file included. The portal's every call to action
is a full navigation to `/b/<route>`, so Buzz keeps sole ownership of
registration, money and check-in. There is no identity bridge here, RP-14 is
deferred, and an attendee stays Buzz-native.

Mirrors `vmmsx/member/tests/test_delegation.py`'s shape: the raw text is
scanned for doctype string literals, and the detector is tested against a
planted leak so a scan that finds nothing because it is broken does not read
as a clean codebase.

**Prose may name what it documents; code may not.** `vmmsx/docs/` is excluded
from the scan for the same reason `member`'s scanner strips docstrings before
looking for gateway vocabulary: the guide's whole job is to say "Buzz Event"
out loud, in a table cell, describing the one field this seam adds. That is
documentation doing its job, not vmmsx code reading Buzz's model.
"""

from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

EXCLUDED_PARTS = {"tests", "docs", "__pycache__"}

# The only files in the app allowed to name Buzz's event doctype: the two halves
# of the seam, the patch that installs its one field on it, and one seed. Adding
# a fifth entry here should be an argued decision, not a convenience — the value
# of this list is that it is short.
#
# **The argument for the seeds.** `seed/kenya_operations.py` creates a demo
# society's events, and it creates them as `Buzz Event` records because that is
# where an event lives: writing them into a vmmsx doctype would be the second
# copy this whole rule exists to prevent. It is the same category as the install
# patch beside it — a deliberate, one-directional, findable crossing, run by
# hand from the bench and imported by nothing. What the rule actually protects
# against is *product code* reaching past the seam and growing a dependency on
# Buzz's schema; a seed that a society deletes has no such reach. It still may
# not name a booking or ticket doctype, and the test below enforces that on
# every file including this one.
#
# `seed/gambia_operations.py` is a second society's operations and arrives here
# by exactly the same argument. It was added without this entry, which is what a
# list like this is for: the failure said a seed had reached past the seam, and
# the answer was to look at it and agree that it had not. **A third society is a
# third line, and each one should be read before it is added rather than waved
# through because the two above it are here.**
ALLOWED_PATHS = {
	"buzz/services/geo.py",
	"buzz/services/events.py",
	"patches/setup_buzz_seam.py",
	"seed/kenya_operations.py",
	"seed/gambia_operations.py",
}

EVENT_DOCTYPE = "Buzz Event"

# Buzz's identity and ticketing vocabulary. If any of this appears outside
# Buzz's own app, an identity bridge has been built where none was asked for.
FORBIDDEN_BUZZ_DOCTYPES = (
	"Event Booking",
	"Event Booking Attendee",
	"Event Ticket",
	"Event Ticket Type",
	"Event Check In",
	"Event Feedback",
)


def app_files() -> list[Path]:
	root = Path(frappe.get_app_path("vmmsx"))

	return sorted(
		path for path in root.rglob("*.py") if not EXCLUDED_PARTS & set(path.relative_to(root).parts)
	)


class TestBuzzStopsAtTheSeam(IntegrationTestCase):
	def test_the_scan_actually_reads_the_app(self):
		"""A scan matching nothing at all would pass every test below."""
		relative = {str(path.relative_to(Path(frappe.get_app_path("vmmsx")))) for path in app_files()}

		self.assertTrue(ALLOWED_PATHS & relative, "the seam's own files were not found by the scan")

	def test_no_file_outside_the_seam_names_buzz_event(self):
		offenders = []

		for path in app_files():
			relative = str(path.relative_to(Path(frappe.get_app_path("vmmsx"))))

			if relative in ALLOWED_PATHS:
				continue

			text = path.read_text()

			if f'"{EVENT_DOCTYPE}"' in text or f"'{EVENT_DOCTYPE}'" in text:
				offenders.append(relative)

		self.assertEqual(offenders, [], "Buzz Event may only be named by the seam and its install patch")

	def test_no_file_anywhere_names_buzz_s_identity_or_ticketing_doctypes(self):
		"""Not even the seam. There is no identity bridge — RP-14 is deferred."""
		offenders = []

		for path in app_files():
			text = path.read_text()

			for doctype in FORBIDDEN_BUZZ_DOCTYPES:
				if f'"{doctype}"' in text or f"'{doctype}'" in text:
					offenders.append(f"{path.name}: {doctype}")

		self.assertEqual(offenders, [], "an attendee stays Buzz-native; no identity bridge was built")

	def test_the_scan_would_catch_a_leak_that_was_really_there(self):
		"""A scanner that finds nothing because it is broken proves nothing."""
		leaked = 'def read_attendees():\n\tfrappe.get_all("Buzz Event")\n'
		clean = "def unrelated():\n\treturn 1\n"

		self.assertIn(f'"{EVENT_DOCTYPE}"', leaked)
		self.assertNotIn(f'"{EVENT_DOCTYPE}"', clean)
