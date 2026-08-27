# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Elevating to Administrator must not sign the caller out.

This suite exists because of a bug that read as anything but a session bug.
Somebody registering as a volunteer pressed "Save draft"; the draft saved, and
every control on the page then failed with

    You are not permitted to access this resource. Login to access
    Function vmmsx.api.geo.browse is not whitelisted.

They had been signed out by saving. The cause is that `frappe.set_user` is not
only a user switch — it also overwrites `frappe.local.session.sid` with the
username it was handed and replaces `frappe.local.session.data` with an empty
dict. `frappe.local.session` **is** the live `Session.data`, so the naive
"become Administrator, then set_user back" pair leaves the request holding a
session whose id is an email address and whose data is gone. On the way out,
`Session.update()` writes that emptied data into the cache under the real sid,
and the next request resumes a session with no user in it.

Nothing about it was catchable through the endpoint's own return value, which
was correct: the draft really was saved. So the assertions are about the
session the request is left holding, not about the write that happened inside.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx import elevation


class TestElevationLeavesTheSessionAlone(IntegrationTestCase):
	"""What `as_system()` must hand back, whatever it did in between."""

	def setUp(self):
		# A session shaped like a live one: a generated id, and data behind it.
		# The real one on a test run is the runner's, and restoring a copy of it
		# afterwards is what keeps this suite from disturbing anything else.
		self.original = frappe.local.session

		frappe.local.session = frappe._dict(
			{
				"user": "Administrator",
				"sid": "a-real-looking-session-id",
				"data": frappe._dict({"csrf_token": "a-real-looking-csrf-token"}),
			}
		)

	def tearDown(self):
		frappe.local.session = self.original
		frappe.set_user("Administrator")

	def test_the_session_id_survives_the_round_trip(self):
		"""The sid is the session. Losing it is being logged out one request later."""
		before = frappe.local.session.sid

		with elevation.as_system():
			pass

		self.assertEqual(frappe.local.session.sid, before)

	def test_the_session_data_survives_the_round_trip(self):
		"""The csrf token lives in here, and a lost one refuses the next POST."""
		with elevation.as_system():
			pass

		self.assertEqual(frappe.local.session.data.csrf_token, "a-real-looking-csrf-token")

	def test_the_user_is_the_caller_again_afterwards(self):
		"""The elevation itself still has to work, and still has to end."""
		frappe.local.session.user = "Administrator"

		with elevation.as_system():
			self.assertEqual(frappe.session.user, "Administrator")

		self.assertEqual(frappe.session.user, "Administrator")

	def test_a_raising_block_restores_the_session_too(self):
		"""`finally`, not a trailing line: a throw inside is the common case."""
		before = frappe.local.session.sid

		with self.assertRaises(ValueError):
			with elevation.as_system():
				raise ValueError("something the wrapped write refused")

		self.assertEqual(frappe.local.session.sid, before)
		self.assertEqual(frappe.local.session.data.csrf_token, "a-real-looking-csrf-token")
