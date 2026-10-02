"""Exercise ownership, real approval routing, frozen issues and the PDF download."""

from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from vmmsx.api import approvals, service_certificate as api
from vmmsx.approvals.tests import fixtures as approval_fixtures
from vmmsx.member.tests import fixtures as member_fixtures
from vmmsx.service_certificate import service, settings
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
ROLE = "VMMS-TEST Service Certificate Reviewer"


class TestServiceCertificate(VolunteerTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fixtures.make_role(ROLE)
		frappe.db.set_single_value("National Society Settings", settings.SCOPE_FIELD, ROLE)
		fixtures.grant_doctype_access(settings.REQUEST, ROLE)
		cls.reviewer = fixtures.make_user("certificate-reviewer", [ROLE])
		cls.outsider = fixtures.make_user("certificate-outsider", [ROLE])
		fixtures.make_assignment(cls.reviewer, ROLE, cls.society_a["region"])
		fixtures.make_assignment(cls.outsider, ROLE, cls.society_b["region"])
		approval_fixtures.make_workflow([{
			"sequence": 1, "stage_label": "Service review", "required_role": ROLE,
			"resolution_rule": "nearest_ancestor", "completion_rule": "any_of", "can_reject": 1,
			"is_optional": 0, "sla_days": 5, "on_sla_breach": "notify_only",
		}], doctype=settings.REQUEST, applicant_field="red_profile", allow_withdrawal=0)

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.addCleanup(patch.stopall)
		patch("vmmsx.service_certificate.service.direct.tell").start()
		patch("vmmsx.service_certificate.service.frappe.enqueue").start()
		config = frappe.get_single(settings.SETTINGS)
		config.certificate_title = "CERTIFICATE OF SERVICE"
		config.identity_source = "Registration number"
		config.certificate_logo = None
		config.set("certificate_fields", [])
		for source, label, placement in settings.DEFAULT_FIELDS:
			config.append("certificate_fields", {"source": source, "label": label, "placement": placement,
				"enabled": 1, "required": 1, "hide_if_empty": 1})
		config.save()
		self.user = fixtures.make_user("certificate-" + frappe.generate_hash(length=8))
		self.profile = fixtures.make_profile("Certificate", "Applicant", user=self.user)
		self.volunteer = fixtures.make_volunteer(self.profile, self.society_a["ward"])
		frappe.db.set_value("VMMS Volunteer", self.volunteer.name, {"status": "Active", "joined_on": "2020-01-01"})

	def request(self, **values):
		frappe.set_user(self.user)
		return api.submit_request(**{"kind": "Volunteer", "record": self.volunteer.name,
			"service_from": "2020-01-01", "service_to": nowdate(), "position": "Community support", **values})

	def approve(self, name):
		frappe.set_user(self.reviewer)
		return api.decide(name, "Approved", review_note="Checked the branch service register and supervisor confirmation.")

	def test_submission_routes_and_blocks_duplicate_and_cross_owner(self):
		request = self.request()
		self.assertEqual(request["status"], "Pending")
		self.assertFalse(request["can_review"])
		self.assertEqual(api.my_requests()["requests"][0]["name"], request["name"])
		with self.assertRaises(frappe.ValidationError):
			self.request()
		frappe.set_user(self.outsider)
		self.assertEqual(api.my_requests()["requests"], [])
		with self.assertRaises(frappe.PermissionError):
			api.get_request(request["name"])
		with self.assertRaises(frappe.PermissionError):
			api.submit_request("Volunteer", self.volunteer.name, "2020-01-01", nowdate(), "Support")
		frappe.set_user(self.reviewer)
		self.assertTrue(api.get_request(request["name"])["can_review"])

	def test_scope_filters_queue_and_refuses_other_branch_decisions(self):
		name = self.request()["name"]
		frappe.set_user(self.outsider)
		self.assertNotIn(name, [r["name"] for r in api.review_requests()["requests"]])
		with self.assertRaises(frappe.PermissionError):
			api.decide(name, "Approved", review_note="Checked")
		frappe.set_user(self.reviewer)
		self.assertIn(name, [r["name"] for r in api.review_requests()["requests"]])

	def test_rejection_requires_reason_and_allows_a_new_request(self):
		name = self.request()["name"]
		frappe.set_user(self.reviewer)
		with self.assertRaises(frappe.ValidationError):
			api.decide(name, "Rejected")
		result = api.decide(name, "Rejected", reason="The service dates need correction.")
		self.assertEqual(result["status"], "Rejected")
		self.assertFalse(result["can_download"])
		self.assertNotEqual(self.request()["name"], name)

	def test_direct_edits_cannot_approve_or_rewrite_a_request(self):
		name = self.request()["name"]
		frappe.set_user("Administrator")
		doc = frappe.get_doc(settings.REQUEST, name)
		doc.approval_state = "Approved"
		with self.assertRaises(frappe.PermissionError):
			doc.save()
		doc = frappe.get_doc(settings.REQUEST, name)
		doc.service_to = "2020-01-01"
		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_self_approval_is_refused_even_through_generic_api(self):
		name = self.request()["name"]
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.user).add_roles(ROLE)
		fixtures.make_assignment(self.user, ROLE, self.society_a["region"])
		frappe.set_user(self.user)
		with self.assertRaises(frappe.PermissionError):
			api.decide(name, "Approved", review_note="Checked")
		with self.assertRaises(frappe.PermissionError):
			approvals.decide(settings.REQUEST, name, "Rejected", "Self decision")

	def test_approval_requires_verification_and_keeps_frozen_values(self):
		log = fixtures.make_time_log(self.volunteer.name, self.society_a["ward"], hours=3)
		name = self.request()["name"]
		frappe.set_user(self.reviewer)
		with self.assertRaises(frappe.ValidationError):
			api.decide(name, "Approved")
		self.approve(name)
		before = api.get_request(name)
		self.assertEqual(before["service_hours"], 3)
		frappe.set_user("Administrator")
		frappe.db.set_value("VMMS Time Log", log.name, "hours", 8)
		frappe.db.set_value("Red Profile", self.profile, "full_name", "Changed Later")
		frappe.db.set_single_value(settings.SETTINGS, "certificate_title", "Changed Later")
		frappe.set_user(self.user)
		after = api.get_request(name)
		self.assertEqual(after["certificate_html"], before["certificate_html"])
		self.assertEqual(after["service_hours"], 3)
		self.assertNotIn("Changed Later", after["certificate_html"])

	def test_real_pdf_is_private_downloadable_and_generation_is_idempotent(self):
		name = self.request()["name"]
		self.approve(name)
		result = api.generate(name)
		self.assertEqual(result["generation_status"], "Ready")
		file_name = frappe.db.get_value(settings.REQUEST, name, "certificate_file")
		self.assertTrue(frappe.db.get_value("File", file_name, "is_private"))
		api.generate(name)
		self.assertEqual(file_name, frappe.db.get_value(settings.REQUEST, name, "certificate_file"))
		frappe.set_user(self.user)
		api.download(name)
		self.assertTrue(frappe.local.response.filecontent.startswith(b"%PDF"))
		frappe.set_user(self.outsider)
		with self.assertRaises(frappe.PermissionError):
			api.download(name)

	def test_failed_pdf_keeps_approval_and_can_retry(self):
		name = self.request()["name"]
		self.approve(name)
		with patch("frappe.utils.pdf.get_pdf", side_effect=RuntimeError("renderer unavailable")):
			result = api.generate(name)
		self.assertEqual(result["status"], "Approved")
		self.assertEqual(result["generation_status"], "Failed")
		self.assertTrue(result["can_generate"])

	def test_invalid_dates_and_unapproved_download_are_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.request(service_to=add_days(nowdate(), 1))
		with self.assertRaises(frappe.ValidationError):
			self.request(service_from=nowdate(), service_to="2019-01-01")
		name = self.request()["name"]
		with self.assertRaises(frappe.ValidationError):
			api.download(name)

	def test_member_without_volunteer_can_submit(self):
		person = fixtures.make_profile("Member", "Only", user=fixtures.make_user("certificate-member-only"))
		kind = member_fixtures.make_type("VMMS-TEST-service-certificate", "auto_on_payment", fee=100)
		membership = member_fixtures.make_membership(person, kind.name, self.society_a["ward"])
		frappe.db.set_value("VMMS Membership", membership.name, {"membership_status": "Active", "valid_from": "2020-01-01"})
		frappe.set_user(frappe.db.get_value("Red Profile", person, "user"))
		row = api.submit_request("Member", membership.name, "2020-01-01", nowdate(), "Branch support", "Paper service register")
		self.assertEqual(row["applicant_kind"], "Member")
		self.assertEqual(api.get_request(row["name"])["service_history"], [])
		self.approve(row["name"])

	def test_fields_can_be_hidden_renamed_reordered_and_customised(self):
		config = frappe.get_single(settings.SETTINGS)
		config.certificate_title = "CERTIFICATE OF SERVICE"
		for row in config.certificate_fields:
			if row.source == "position":
				row.enabled = 0
			if row.source == "applicant_name":
				row.label = "Awarded to"
		config.append("certificate_fields", {"source": "custom_value", "label": "Programme", "placement": "Body", "enabled": 1, "required": 1})
		config.save()
		custom = config.certificate_fields[-1].name
		name = self.request(position="", custom_values={custom: "<script>alert(1)</script>"})["name"]
		html = api.get_request(name)["certificate_html"]
		self.assertIn("Awarded to", html)
		self.assertNotIn("Position:", html)
		self.assertNotIn("<script>", html)
		self.assertIn("&lt;script&gt;", html)
		self.assertNotIn("DATE OF LEAVING", html)

	def test_settings_preview_is_admin_only_and_has_no_fixed_brand(self):
		html = api.preview()["html"]
		self.assertNotIn("Kenya", html)
		self.assertNotIn("Red Cross", html)
		self.assertIn("landscape", html)
		frappe.set_user(self.user)
		with self.assertRaises(frappe.PermissionError):
			api.preview()

	def test_certificate_logo_is_independent_and_frozen_with_the_request(self):
		from io import BytesIO

		from frappe.utils.file_manager import save_file
		from PIL import Image

		image = BytesIO()
		Image.new("RGB", (40, 20), "blue").save(image, format="PNG")
		file = save_file("certificate-test-logo.png", image.getvalue(), settings.SETTINGS, settings.SETTINGS, is_private=1)
		config = frappe.get_single(settings.SETTINGS)
		config.certificate_logo = file.file_url
		config.save()
		name = self.request()["name"]
		html = api.get_request(name)["certificate_html"]
		self.assertIn("data:image/png;base64,", html)
		frappe.set_user("Administrator")
		config.certificate_logo = None
		config.save()
		self.assertEqual(api.get_request(name)["certificate_html"], html)

	def test_migrating_preserves_custom_fields_and_printed_labels(self):
		config = frappe.get_single(settings.SETTINGS)
		config.certificate_fields[1].label = "Certificate holder"
		config.save()
		settings.install()
		self.assertEqual(frappe.get_single(settings.SETTINGS).certificate_fields[1].label, "Certificate holder")
