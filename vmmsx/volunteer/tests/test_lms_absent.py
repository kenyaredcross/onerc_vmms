# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A society running volunteering with no learning system is an ordinary society.

vmmsx declares `required_apps = ["onerc_core"]` and not the LMS, deliberately.
Training is one way a certification arrives; a coordinator typing one in from a
paper register is another, and it is not the lesser of the two. So "there is no
LMS on this site" is a supported state rather than a degraded one, and what has
to be true of it is narrow and checkable:

1. **Nothing throws.** Not on save, not on read, not on a deployability
   question, not on a sweep that has no learning system to sweep.
2. **The manual path is untouched.** Recording, renewing, expiring and the
   derived lapse all work exactly as they do here, because none of them was ever
   the LMS's business.
3. **The automation is dormant, not broken.** `sync_volunteer()` reports that it
   read nothing rather than raising, and the `doc_events` hook simply never
   fires because the doctype it names does not exist.
4. **Configuration is still ours.** A `VMMS Course Mapping` is a vmmsx record
   about an identifier in another system, so it can be written and read with no
   learning system present at all — which is what makes the mapping *config*
   rather than a foreign key.

**Absence is mocked, because the LMS really is installed on this site.** The
mock patches `frappe.get_installed_apps` to the real list minus `lms`, which is
exactly the surface `learning.is_available()` reads — the same shape
`member/tests/test_payments_absent.py` uses against the payments app, and for
the same reason: the guard asks installed-apps rather than trying an import, so
absence is a question that can be asked at configuration time instead of an
exception that can only happen at call time.

It patches the app's *hooks* out alongside it, because an absent app contributes
none, and hiding only the installed list produces a site that has never existed.
See `without_learning()` for what goes wrong if you hide one and not the other;
it is worth reading before adding a test here.
"""

from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.volunteer.services import certification, learning
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

TYPE_MANUAL = f"{fixtures.TEST_PREFIX}-absent-manual"
COURSE_ABSENT = f"{fixtures.TEST_PREFIX}-course-absent"


@contextmanager
def without_learning():
	"""Make this site look like one where the learning app was never installed.

	**Two things are patched, because an absent app is two things.** It is not in
	`frappe.get_installed_apps()`, which is the surface vmmsx's own guard reads —
	and it contributes no hooks, which is the surface the *framework* reads.

	Hiding only the first produces a site that has never existed and fails for a
	reason that has nothing to do with vmmsx: Frappe's search indexer runs on
	every insert, resolves its `sqlite_search` hook through `frappe.get_attr`,
	and `get_attr` refuses a path whose app is not installed. The learning app
	registers such a hook here, so every document save inside the patch would
	die with `AppNotInstalledError` — a mock catching itself lying, not a defect
	in anything being tested.

	`frappe.get_hooks` builds its map from the installed apps and then caches it,
	so the cached map still carries the learning app's entries. Filtering them
	out reproduces exactly what an uncached rebuild under the same patch would
	have produced. Only values *naming that app* are dropped; the `doc_events`
	registration for `LMS Enrollment` is vmmsx's own line in vmmsx's own hooks
	and stays, which is faithful too — on a site with no LMS that registration is
	still there and simply never fires, because the doctype it names does not
	exist.

	The installed list is the real one minus a single entry rather than something
	hand-written: patching in `["frappe"]` would also hide vmmsx and onerc_core
	from any framework code that asked during the same call.
	"""
	remaining = [app for app in frappe.get_installed_apps() if app != learning.LEARNING_APP]
	real_get_hooks = frappe.get_hooks
	prefix = f"{learning.LEARNING_APP}."

	def strip(value):
		"""Drop every method path belonging to the learning app, at any depth.

		Recursive because hooks nest: `sqlite_search` is a flat list of paths,
		while `doc_events` is a dict of doctypes to a dict of events to a list of
		paths, and the learning app registers under both. Dict subclasses are
		rebuilt as themselves so that `frappe._dict`'s attribute access survives.
		"""
		if isinstance(value, dict):
			return value.__class__({key: strip(inner) for key, inner in value.items()})

		if isinstance(value, list):
			return [strip(entry) for entry in value if not str(entry).startswith(prefix)]

		return value

	def hooks_without_learning(*args, **kwargs):
		return strip(real_get_hooks(*args, **kwargs))

	# `frappe.get_doc_hooks()` flattens `doc_events` once and keeps the result on
	# `frappe.local`, so by the time a test runs it is already holding the
	# unfiltered map and would never consult the patch. Dropping it makes the
	# next save rebuild it through `hooks_without_learning`; the original is put
	# back afterwards so no other suite inherits a site missing an app.
	previous_doc_hooks = getattr(frappe.local, "doc_events_hooks", None)
	frappe.local.doc_events_hooks = None

	try:
		with (
			patch.object(frappe, "get_installed_apps", return_value=remaining),
			patch.object(frappe, "get_hooks", side_effect=hooks_without_learning),
		):
			yield
	finally:
		frappe.local.doc_events_hooks = previous_doc_hooks


class LMSAbsentTestCase(VolunteerTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_certification_type(TYPE_MANUAL, validity_days=90)

	def volunteer(self, handle: str = "Absent"):
		"""An Active volunteer, so a deployability answer is about certifications."""
		from vmmsx.volunteer.services import volunteer as volunteer_service

		profile = fixtures.make_profile(handle, "Nolms")
		volunteer = fixtures.make_volunteer(profile, self.society_a["ward"])

		frappe.db.set_value(fixtures.VOLUNTEER_DOCTYPE, volunteer.name, "status", "Active")
		volunteer.reload()
		volunteer_service.report(volunteer)

		return volunteer


class TestTheMockReallyHidesTheLearningApp(LMSAbsentTestCase):
	def test_it_flips_the_availability_answer(self):
		"""A mock that did not work would make every test below vacuous."""
		self.assertIn(learning.LEARNING_APP, frappe.get_installed_apps())
		self.assertTrue(learning.is_available())

		with without_learning():
			self.assertNotIn(learning.LEARNING_APP, frappe.get_installed_apps())
			self.assertFalse(learning.is_available())

		# ...and it is put back afterwards.
		self.assertTrue(learning.is_available())

	def test_detection_does_not_depend_on_an_import_failing(self):
		"""Absence is a *setting*, asked of the site, not an ImportError caught.

		If the guard detected absence by trying the import, this is the test that
		would expose it: the LMS is still perfectly importable under the mock,
		and the guard must still say it is unavailable. An app can also sit in
		the bench without being installed on *this* site, which is the case that
		actually bites and which an import check cannot see at all.
		"""
		with without_learning():
			self.assertFalse(learning.is_available())

			self.assertTrue(frappe.db.exists("DocType", learning.ENROLLMENT_DOCTYPE))


class TestTheManualPathIsUntouched(LMSAbsentTestCase):
	"""A coordinator recording a certification by hand needs no learning system."""

	def test_a_certification_can_still_be_recorded(self):
		volunteer = self.volunteer()

		with without_learning():
			held = certification.record(volunteer.name, TYPE_MANUAL, today())

		self.assertTrue(frappe.db.exists(fixtures.CERTIFICATION_DOCTYPE, held.name))

	def test_the_expiry_is_still_computed_from_the_types_validity(self):
		"""Expiry comes from our configuration; the LMS never had a say in it."""
		volunteer = self.volunteer()

		with without_learning():
			held = certification.record(volunteer.name, TYPE_MANUAL, today())

		self.assertEqual(getdate(held.expiry_date), getdate(add_days(today(), 90)))

	def test_the_lapse_is_still_derived(self):
		volunteer = self.volunteer()

		with without_learning():
			held = certification.record(volunteer.name, TYPE_MANUAL, add_days(today(), -200))
			expiry = getdate(held.expiry_date)

			self.assertTrue(certification.is_lapsed(held))
			self.assertFalse(certification.is_lapsed(held, as_of=add_days(expiry, -1)))

	def test_deployability_still_answers(self):
		"""The rule the module exists for does not need a learning system."""
		volunteer = self.volunteer()

		with without_learning():
			certification.record(volunteer.name, TYPE_MANUAL, add_days(today(), -200))
			answer = certification.deployability(volunteer)

			self.assertFalse(answer["deployable"])
			self.assertTrue(answer["reasons"])
			self.assertEqual(volunteer.status, "Active")

	def test_a_renewal_still_un_lapses_it(self):
		volunteer = self.volunteer()

		with without_learning():
			held = certification.record(volunteer.name, TYPE_MANUAL, add_days(today(), -200))
			self.assertFalse(certification.is_deployable(volunteer))

			renewed = certification.record(volunteer.name, TYPE_MANUAL, today())

			self.assertEqual(renewed.name, held.name)
			self.assertTrue(certification.is_deployable(volunteer))


class TestTheAutomationIsDormantRatherThanBroken(LMSAbsentTestCase):
	def test_syncing_a_volunteer_reads_nothing_and_does_not_raise(self):
		"""The catch-up path is the one thing that would go looking for the LMS.

		It asks `is_available()` first and returns its empty summary, so a site
		with no learning system gets an honest answer rather than a query against
		a table that is not there.
		"""
		volunteer = self.volunteer()

		with without_learning():
			summary = learning.sync_volunteer(volunteer)

		self.assertEqual(summary["read"], 0)
		self.assertEqual(summary["awarded"], [])
		self.assertEqual(summary["volunteer"], volunteer.name)

	def test_it_awards_nothing_even_where_a_mapping_and_a_completion_exist(self):
		"""Dormant means dormant: the mapping is real and still nothing happens."""
		volunteer = self.volunteer()
		fixtures.make_mapping(COURSE_ABSENT, TYPE_MANUAL)

		with without_learning():
			summary = learning.sync_volunteer(volunteer)

		self.assertEqual(summary["awarded"], [])
		self.assertEqual(certification.held(volunteer.name), [])

	def test_the_app_does_not_require_the_learning_app(self):
		"""The whole claim, in one assertion against hooks.py.

		If the LMS were ever added to `required_apps`, every society without one
		would be unable to install vmmsx at all — and the graceful degradation
		these tests describe would be unreachable rather than merely untested.
		"""
		required = frappe.get_hooks("required_apps", app_name="vmmsx")

		self.assertNotIn(learning.LEARNING_APP, required)
		self.assertIn("onerc_core", required)


class TestConfigurationIsOursNotTheLearningSystems(LMSAbsentTestCase):
	def test_a_course_mapping_can_be_written_with_no_learning_system(self):
		"""The mapping is a vmmsx record about somebody else's identifier.

		This is exactly why `external_course` is Data rather than a Link. A Link
		would make the mapping unsaveable — and the doctype uninstallable — on a
		site with no LMS, which is the site this whole file is about.
		"""
		with without_learning():
			mapping = fixtures.make_mapping(COURSE_ABSENT, TYPE_MANUAL)

		self.assertTrue(frappe.db.exists(fixtures.MAPPING_DOCTYPE, mapping.name))
		self.assertEqual(mapping.certification_type, TYPE_MANUAL)

	def test_the_mapping_can_be_read_back_with_no_learning_system(self):
		"""A society may configure its course mappings before it buys an LMS."""
		fixtures.make_mapping(COURSE_ABSENT, TYPE_MANUAL)

		with without_learning():
			found = learning.mapping_for(COURSE_ABSENT)

			self.assertIsNotNone(found)
			self.assertEqual(found.certification_type, TYPE_MANUAL)
			self.assertEqual(learning.mapped_courses(), [COURSE_ABSENT])

	def test_the_write_half_of_the_seam_speaks_only_our_vocabulary(self):
		"""`record_completion` reads our mapping and writes our certification.

		Nothing in it touches the learning system — the completion arrives as two
		plain arguments — so it works under the mock. That is the containment
		being demonstrated rather than a feature anybody uses: on a site with no
		LMS nothing ever calls it, because the doctype whose save would trigger
		the hook does not exist.
		"""
		volunteer = self.volunteer()
		user = fixtures.make_user("absent_learner")
		frappe.db.set_value("Red Profile", volunteer.red_profile, "user", user)
		fixtures.make_mapping(COURSE_ABSENT, TYPE_MANUAL)

		with without_learning():
			awarded = learning.record_completion(user, COURSE_ABSENT, today())

		self.assertIsNotNone(awarded)
		self.assertEqual(awarded["certification_type"], TYPE_MANUAL)
		self.assertEqual(getdate(awarded["expiry_date"]), getdate(add_days(today(), 90)))
