# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Printing a certificate: whose it is, and what the renderer can actually see.

Two things are proved here, and the first is the one that would be easy to get
wrong in a way nobody noticed for a year.

**The owner is the member, not the record's owner.** A membership registered at
a branch desk is *created by* a clerk: `membership.owner` is the clerk's login,
and the member may never have touched a keyboard. Gating a certificate on
`owner` would therefore hand every member's certificate to whoever typed them in
and withhold it from the member themselves — and on a site where members
register for themselves, the two happen to coincide and the bug is invisible.
`TestTheOwnerIsTheMemberNotTheClerk` builds the case where they differ and
asserts the gate follows the person, through core's `Red Profile.user`.

**An unresolved print role refuses.** Empty setting, or a setting naming a role
somebody deleted: both mean the society has not said anybody else may print, and
both must therefore grant nothing. The failure being designed against is a blank
config reading as "everyone", which fails open while looking entirely normal.

**And the logo has to carry its own location.** A PDF renderer is handed a string
of HTML with no page behind it, so `/files/logo.png` resolves against nothing and
silently renders as a gap. `TestTheLogoIsPrintable` asserts the conversion
happens, using a real File with real bytes so the embedding path is exercised
rather than the fallback.

Nothing is mocked: real memberships, activated through the real payment path,
rendered through the real template and the real PDF binary.
"""

import frappe

from vmmsx.member.services import approval, certificate, identity, society
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

PRINT_ROLE = f"{fixtures.TEST_PREFIX} Certificate Printer"

# The whole readable surface of the member's identity reader, written out. An
# assertEqual against this is what makes widening it a decision somebody takes
# rather than something that drifts.
#
# **The last six were added for the coordinator's view**, and this list moving is
# the guard working rather than the guard being in the way: widening the reader
# had to break a test somebody then had to justify. The justification is in
# `identity._READABLE`'s own comment — a coordinator opening a member record was
# shown a docname and had to visit the Red Profile to find out who it was.
#
# Widening what is *read* is not widening what is *stored*, and the two are
# independent: `member/tests/test_dossier.py` asserts that none of these ever
# becomes a column on `VMMS Member`.
EXPECTED_READABLE = (
	"full_name",
	"first_name",
	"last_name",
	"email",
	"phone",
	"home_geo_node",
	"user",
	"gender",
	"date_of_birth",
	"profile_photo",
	"preferred_language",
	"country_of_citizenship",
	"citizenship_status",
	"residency_type",
	"country_of_residence",
	"residence_address",
)

# Core holds these back for a gated extension. They are not this app's to show,
# and the volunteer module names the same four.
GATED_SENSITIVE = ("blood_group", "medical_conditions", "next_of_kin", "disability")


class PrintTestCase(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=600)
		fixtures.make_role(PRINT_ROLE)

		# `api/member.py::_readable` checks Frappe's own read permission before
		# the print gate ever runs, so a caller reaching the endpoint needs
		# doctype access as well as being the right person. Granted here to the
		# scope role every test user holds, so that a refusal in this suite is
		# always the print gate and never a DocPerm stopping somebody at the
		# door — the same arrangement the engine's person-gate tests make.
		fixtures.grant_membership_access(fixtures.SCOPE_ROLE)
		# And a clerk registering somebody creates the member satellite, which
		# `member.ensure()` inserts without elevation.
		fixtures.grant_member_access(fixtures.SCOPE_ROLE)

	def setUp(self):
		super().setUp()
		# Every test states the branding and the print rule it wants; put the
		# shipped state back so nothing leaks between them.
		self.addCleanup(fixtures.reset_branding)

	@classmethod
	def active_membership_for(cls, handle: str, user: str | None = None, created_by: str | None = None):
		"""An active membership, optionally created by somebody other than its member.

		`created_by` is the whole point of this helper: it makes `owner` and the
		member two different people, which is the case the gate has to get right.

		A classmethod, and called from `setUpClass` rather than `setUp`, because
		`Red Profile.user` is unique in core and this suite's transaction rolls
		back once per class. Building a profile for the same login in every
		method would collide on the second one.
		"""
		profile = fixtures.make_profile("Print", handle.title(), user=user)

		if created_by:
			with fixtures.acting_as(created_by):
				membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, cls.society_a["ward"])
		else:
			membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, cls.society_a["ward"])

		membership_service.submit(membership)

		row = frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)
		row.on_payment_confirmed(amount=600, transaction_id=row.payment_transaction)

		return {
			"profile": profile,
			"membership": frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name),
		}


# --- the owner gate --------------------------------------------------------


class TestTheOwnerIsTheMemberNotTheClerk(PrintTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# The clerk registers people. They hold membership access so that any
		# refusal below is the print gate and not a permission stopping them at
		# the door — the same reasoning the engine's person-gate tests use.
		cls.clerk = cls.scoped_user("print_clerk")
		fixtures.grant_membership_access(fixtures.SCOPE_ROLE)

		# The member. A login of their own, and no role at all.
		cls.member_user = cls.scoped_user("print_member")

		cls.case = cls.active_membership_for("owned", user=cls.member_user, created_by=cls.clerk)
		# A member registered from a paper form: no login at all.
		cls.paperless = cls.active_membership_for("no_login", user=None, created_by=cls.clerk)
		# Somebody else's, held by the clerk, so "the clerk can print their own"
		# is provable without weakening the assertion above.
		cls.clerks_own = cls.active_membership_for("stranger", user=cls.clerk)

	def test_the_fixture_really_made_them_different_people(self):
		"""Without this, every assertion below could pass for the wrong reason."""
		self.assertEqual(self.case["membership"].owner, self.clerk)
		self.assertNotEqual(self.case["membership"].owner, self.member_user)

	def test_the_member_may_print_their_own(self):
		self.assertTrue(certificate.may_print(self.case["membership"], self.member_user))

	def test_the_clerk_who_created_it_may_not(self):
		"""The assertion this suite exists for.

		The clerk is `membership.owner`. If the gate consulted `owner` — the
		obvious, wrong implementation — this would pass them.
		"""
		self.assertFalse(certificate.may_print(self.case["membership"], self.clerk))

	def test_the_clerk_is_refused_at_the_endpoint_too(self):
		from vmmsx.api import member as member_api

		with fixtures.acting_as(self.clerk), self.assertRaises(frappe.PermissionError):
			member_api.download_certificate(self.case["membership"].name)

	def test_the_refusal_is_the_gate_and_not_a_read_permission(self):
		"""The clerk can open the record perfectly well. Only printing is refused."""
		with fixtures.acting_as(self.clerk):
			readable = frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, self.case["membership"].name)

			self.assertEqual(readable.name, self.case["membership"].name)
			self.assertTrue(frappe.has_permission(fixtures.MEMBERSHIP_DOCTYPE, doc=readable, ptype="read"))

	def test_the_owner_resolves_through_red_profile_and_not_the_document(self):
		"""Named directly, so the mechanism is asserted and not just its effect."""
		self.assertEqual(certificate.owner_user(self.case["membership"]), self.member_user)
		self.assertNotEqual(certificate.owner_user(self.case["membership"]), self.case["membership"].owner)

	def test_a_member_with_no_login_is_nobody(self):
		"""Ordinary: a paper registration has no account. It must not match anyone."""
		self.assertIsNone(certificate.owner_user(self.paperless["membership"]))
		self.assertFalse(certificate.may_print(self.paperless["membership"], self.clerk))

	def test_another_member_cannot_print_someone_elses(self):
		"""The clerk holds one of their own, and still cannot have the member's."""
		self.assertFalse(certificate.may_print(self.case["membership"], self.clerk))
		self.assertTrue(certificate.may_print(self.clerks_own["membership"], self.clerk))


# --- the role gate ---------------------------------------------------------


class TestTheConfiguredPrintRole(PrintTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.officer = cls.scoped_user("print_officer", [PRINT_ROLE])
		cls.bystander = cls.scoped_user("print_bystander")
		cls.member_user = cls.scoped_user("print_role_member")

		cls.case = cls.active_membership_for("role_gated", user=cls.member_user)

	def test_a_holder_of_the_configured_role_may_print_anyones(self):
		fixtures.set_print_role(PRINT_ROLE)

		self.assertTrue(certificate.may_print(self.case["membership"], self.officer))

	def test_somebody_without_it_still_may_not(self):
		fixtures.set_print_role(PRINT_ROLE)

		self.assertFalse(certificate.may_print(self.case["membership"], self.bystander))

	def test_pointing_the_setting_elsewhere_changes_who_prints(self):
		"""Configuration decides, with no code diff. The MEM-02 property restated."""
		other_role = f"{fixtures.TEST_PREFIX} Other Printer"
		fixtures.make_role(other_role)

		fixtures.set_print_role(PRINT_ROLE)
		self.assertTrue(certificate.may_print(self.case["membership"], self.officer))

		fixtures.set_print_role(other_role)
		self.assertFalse(certificate.may_print(self.case["membership"], self.officer))

	def test_an_empty_setting_grants_nobody(self):
		"""The shipped state. Blank is a closed door, not an open one."""
		fixtures.set_print_role(None)

		self.assertFalse(certificate.may_print(self.case["membership"], self.officer))
		self.assertFalse(certificate.may_print(self.case["membership"], self.bystander))

	def test_an_empty_setting_still_lets_the_member_print(self):
		"""Fail-closed must not close the door on the person it belongs to."""
		fixtures.set_print_role(None)

		self.assertTrue(certificate.may_print(self.case["membership"], self.member_user))

	def test_a_setting_naming_a_deleted_role_grants_nobody(self):
		"""A Link can be left holding a role that was removed afterwards."""
		ghost = f"{fixtures.TEST_PREFIX} Ghost Printer"
		fixtures.make_role(ghost)
		fixtures.set_print_role(ghost)
		frappe.delete_doc("Role", ghost, force=True)

		self.assertFalse(certificate.may_print(self.case["membership"], self.officer))
		self.assertTrue(certificate.may_print(self.case["membership"], self.member_user))

	def test_an_unresolvable_role_is_logged_rather_than_silent(self):
		"""A membership office whose printing stopped must be able to find out why."""
		ghost = f"{fixtures.TEST_PREFIX} Logged Ghost"
		fixtures.make_role(ghost)
		fixtures.set_print_role(ghost)
		frappe.delete_doc("Role", ghost, force=True)

		before = frappe.db.count("Error Log", {"method": certificate.PRINT_REFUSED_LOG_TITLE})
		certificate.may_print(self.case["membership"], self.officer)

		self.assertGreater(
			frappe.db.count("Error Log", {"method": certificate.PRINT_REFUSED_LOG_TITLE}), before
		)

	def test_the_setting_is_a_real_custom_field_vmmsx_owns(self):
		field = frappe.db.get_value(
			"Custom Field",
			{"dt": "National Society Settings", "fieldname": society.PRINT_ROLE_FIELD},
			["fieldtype", "options"],
			as_dict=True,
		)

		self.assertIsNotNone(field, "the print role setting was never installed")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Role")

	def test_an_administrator_is_exempt_as_a_framework_primitive(self):
		fixtures.set_print_role(None)

		self.assertTrue(certificate.may_print(self.case["membership"], "Administrator"))


# --- state -----------------------------------------------------------------


class TestOnlyAnActiveMembershipHasACertificate(PrintTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.member_user = cls.scoped_user("print_pending_member")
		cls.stranger = cls.scoped_user("print_stranger")

		profile = fixtures.make_profile("Pending", "Holder", user=cls.member_user)
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, cls.society_a["ward"])
		membership_service.submit(membership)

		cls.pending = frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

	def test_the_fixture_really_is_not_active(self):
		self.assertNotEqual(self.pending.membership_status, membership_service.STATUS_ACTIVE)

	def test_a_membership_awaiting_payment_has_none(self):
		with self.assertRaises(frappe.ValidationError):
			certificate.pdf_for(self.pending, self.member_user)

	def test_the_gate_runs_before_the_state_check(self):
		"""A caller who may not have it is refused without the server rendering.

		Asserted by the exception type: a stranger gets PermissionError on the
		very same document that gives its own member a ValidationError. If the
		state check ran first, both would raise ValidationError and the ordering
		would be unobservable.
		"""
		with self.assertRaises(frappe.PermissionError):
			certificate.pdf_for(self.pending, self.stranger)


# --- the PDF ---------------------------------------------------------------


class TestThePdf(PrintTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.member_user = cls.scoped_user("print_pdf_member")
		cls.case = cls.active_membership_for("pdf", user=cls.member_user)

	def test_it_produces_a_pdf(self):
		pdf = certificate.pdf_for(self.case["membership"], self.member_user)

		self.assertIsInstance(pdf, bytes)
		self.assertTrue(pdf.startswith(b"%PDF"), "what came back is not a PDF")
		self.assertGreater(len(pdf), 1000, "the PDF is too small to contain a certificate")

	def test_the_endpoint_streams_it_with_a_filename(self):
		from vmmsx.api import member as member_api

		with fixtures.acting_as(self.member_user):
			member_api.download_certificate(self.case["membership"].name)

		self.assertEqual(frappe.local.response.type, "pdf")
		self.assertTrue(frappe.local.response.filecontent.startswith(b"%PDF"))
		self.assertEqual(
			frappe.local.response.filename,
			f"membership-certificate-{self.case['membership'].name}.pdf",
		)

	def test_the_filename_names_the_membership_and_not_the_person(self):
		"""A filename travels without its contents being opened."""
		name = certificate.pdf_filename(self.case["membership"])

		self.assertIn(self.case["membership"].name, name)
		self.assertNotIn("Print", name)
		self.assertNotIn(self.member_user.split("@")[0], name)

	def test_nothing_is_stored_by_printing(self):
		"""No File row, and no change to the membership."""
		before_files = frappe.db.count("File")
		before = frappe.db.get_value(
			fixtures.MEMBERSHIP_DOCTYPE, self.case["membership"].name, "*", as_dict=True
		)

		certificate.pdf_for(self.case["membership"], self.member_user)

		after = frappe.db.get_value(
			fixtures.MEMBERSHIP_DOCTYPE, self.case["membership"].name, "*", as_dict=True
		)

		self.assertEqual(frappe.db.count("File"), before_files, "printing created a File row")
		self.assertEqual(dict(before), dict(after), "printing wrote to the membership")


# --- the logo --------------------------------------------------------------


class TestTheLogoIsPrintable(PrintTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.member_user = cls.scoped_user("print_logo_member")
		cls.case = cls.active_membership_for("logo", user=cls.member_user)

	def test_the_stored_logo_is_site_relative_which_is_the_trap(self):
		"""The premise. Without it the assertion below could pass trivially."""
		url = fixtures.make_logo_file()
		fixtures.set_logo(url)

		self.assertTrue(url.startswith("/"), "the fixture did not produce a relative path")
		self.assertEqual(society.logo(), url)
		self.assertEqual(certificate.context_for(self.case["membership"])["society_logo"], url)

	def test_the_print_context_makes_it_carry_its_own_location(self):
		"""The wkhtmltopdf trap, closed. A bare path resolves against nothing."""
		fixtures.set_logo(fixtures.make_logo_file())

		printable = certificate.context_for(self.case["membership"], absolute_assets=True)["society_logo"]

		self.assertFalse(printable.startswith("/"), "the logo is still a bare path")
		self.assertTrue(printable.startswith(("data:", "http://", "https://")))

	def test_a_real_file_is_embedded_rather_than_linked(self):
		"""The bytes travel in the document, so rendering needs no network."""
		content = b"\x89PNG\r\n\x1a\nembedded-bytes"
		fixtures.set_logo(fixtures.make_logo_file(content))

		printable = certificate.context_for(self.case["membership"], absolute_assets=True)["society_logo"]

		self.assertTrue(printable.startswith("data:"), "the logo was not embedded")

		from base64 import b64decode

		self.assertEqual(b64decode(printable.split(",", 1)[1]), content)

	def test_a_logo_that_cannot_be_read_falls_back_to_an_absolute_url(self):
		"""Better a link that might resolve than a path that certainly will not."""
		fixtures.set_logo("/files/vmmsx-no-such-logo.png")

		printable = certificate.context_for(self.case["membership"], absolute_assets=True)["society_logo"]

		self.assertTrue(printable.startswith(("http://", "https://")))
		self.assertTrue(printable.endswith("/files/vmmsx-no-such-logo.png"))

	def test_an_already_absolute_logo_is_left_alone(self):
		fixtures.set_logo("https://example.test/logo.png")

		self.assertEqual(
			certificate.printable_asset("https://example.test/logo.png"), "https://example.test/logo.png"
		)

	def test_no_logo_is_ordinary(self):
		"""A society that has not uploaded one still gets a certificate."""
		fixtures.set_logo(None)

		self.assertEqual(
			certificate.context_for(self.case["membership"], absolute_assets=True)["society_logo"], ""
		)

		pdf = certificate.pdf_for(self.case["membership"], self.member_user)

		self.assertTrue(pdf.startswith(b"%PDF"))

	def test_the_shipped_template_renders_the_logo_when_there_is_one(self):
		"""End to end through the real seeded template, not the test one."""
		from vmmsx.templating.services import render

		fixtures.set_logo(fixtures.make_logo_file())
		context = certificate.context_for(self.case["membership"], absolute_assets=True)
		body = render.render_template("membership_certificate", context)["body"]

		self.assertIn(context["society_logo"], body)

	def test_the_shipped_template_omits_it_when_there_is_none(self):
		from vmmsx.templating.services import render

		fixtures.set_logo(None)
		context = certificate.context_for(self.case["membership"], absolute_assets=True)
		body = render.render_template("membership_certificate", context)["body"]

		self.assertNotIn("<img", body)


# --- the identity widening -------------------------------------------------


class TestTheMemberReadableSurface(PrintTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.user_of_login = cls.scoped_user("print_user_of")

	def test_the_allow_list_is_the_agreed_set_and_no_more(self):
		"""Whole-tuple equality. A superset is a failure too."""
		self.assertEqual(identity._READABLE, EXPECTED_READABLE)

	def test_user_is_in_it_because_the_print_gate_needs_it(self):
		self.assertIn("user", identity._READABLE)

	def test_the_gated_sensitive_set_is_not(self):
		for fieldname in GATED_SENSITIVE:
			self.assertNotIn(
				fieldname,
				identity._READABLE,
				f"{fieldname} belongs to core's gated extension and is not vmmsx's to surface",
			)

	def test_the_reader_will_not_return_a_field_outside_the_list(self):
		"""Asked for nothing but withheld names, it surfaces none of them.

		The reader filters to the allow-list, so what comes back for a request
		made entirely of names that are not on it carries no person-fact at all.
		"""
		from vmmsx.member.services import member as member_service

		profile = fixtures.make_profile("Surface", "Person")
		member = member_service.ensure(profile)
		read = identity.read(member, GATED_SENSITIVE)

		for fieldname in GATED_SENSITIVE:
			self.assertNotIn(fieldname, read, f"{fieldname} reached a caller")

	def test_user_of_resolves_the_login(self):
		from vmmsx.member.services import member as member_service

		profile = fixtures.make_profile("Login", "Person", user=self.user_of_login)
		member = member_service.ensure(profile)

		self.assertEqual(identity.user_of(member), self.user_of_login)

	def test_user_of_is_none_for_somebody_with_no_account(self):
		from vmmsx.member.services import member as member_service

		profile = fixtures.make_profile("Paper", "Person")
		member = member_service.ensure(profile)

		self.assertIsNone(identity.user_of(member))

	def test_the_member_still_stores_no_identity_of_its_own(self):
		"""Widening what is read is not widening what is held."""
		meta = frappe.get_meta(fixtures.MEMBER_DOCTYPE)
		columns = set(frappe.db.get_table_columns(fixtures.MEMBER_DOCTYPE))

		for fieldname in ("full_name", "email", "phone", "user"):
			self.assertIsNone(meta.get_field(fieldname), f"the member grew {fieldname}")
			self.assertNotIn(fieldname, columns, f"the member stores {fieldname}")
