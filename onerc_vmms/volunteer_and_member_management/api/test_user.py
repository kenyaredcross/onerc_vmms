import frappe
from frappe.tests.utils import FrappeTestCase

from onerc_vmms.volunteer_and_member_management.api.user import update_user_details

TEST_EMAIL = "profile-save-test@example.com"


class TestUpdateUserDetails(FrappeTestCase):
	"""update_user_details commits, so each test creates and removes its own user."""

	def setUp(self):
		frappe.set_user("Administrator")
		_delete_test_user()
		# addCleanup, not tearDown: it also runs if the rest of setUp fails.
		self.addCleanup(_delete_test_user)
		frappe.get_doc(
			{
				"doctype": "User",
				"email": TEST_EMAIL,
				"first_name": "Profile",
				"user_type": "Website User",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()

		frappe.set_user(TEST_EMAIL)
		# An upload as the portal's Uploader makes it: private and not yet attached.
		self.file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "certificate.txt",
				"is_private": 1,
				"content": b"test certificate",
			}
		).insert(ignore_permissions=True)

	def test_profile_tables_and_their_attachments_are_saved(self):
		# The shape the Qualifications & Skills tab sends: an Attach value is the
		# Uploader's response object, not a URL.
		attachment = {
			"file_url": self.file.file_url,
			"name": self.file.name,
			"file_name": self.file.file_name,
		}
		update_user_details(
			linkedin="https://www.linkedin.com/in/profile-save-test",
			courses=[
				{
					"course_name": "First Aid",
					"institution": "Kenya Red Cross",
					"start_date": "2025-01-06",
					"date_completed": "2025-01-10",
					"attachment": attachment,
				}
			],
			education=[
				{
					"school_univ": "University of Nairobi",
					"level": "Undergraduate",
					"year_of_passing": 2020,
					"attachment": attachment,
				}
			],
			work_experience=[
				{
					"title": "Field Officer",
					"company": "KRCS",
					"location": "Nairobi",
					"from_date": "2021-01-01",
					"current": 1,
				}
			],
			additional_skills=[{"additional_skill": "Logistics"}],
			allergies=[{"allergy": "Penicillin"}],
		)

		user = frappe.get_doc("User", TEST_EMAIL)
		self.assertEqual(user.linkedin, "https://www.linkedin.com/in/profile-save-test")
		self.assertEqual([r.course_name for r in user.courses], ["First Aid"])
		self.assertEqual(user.courses[0].attachment, self.file.file_url)
		self.assertEqual(user.education[0].attachment, self.file.file_url)
		self.assertEqual([r.title for r in user.work_experience], ["Field Officer"])
		self.assertEqual([r.additional_skill for r in user.additional_skills], ["Logistics"])
		self.assertEqual([r.allergy for r in user.allergies], ["Penicillin"])

	def test_fields_outside_the_allowlist_are_still_ignored(self):
		update_user_details(
			first_name="Renamed",
			roles=[{"role": "System Manager"}],
			user_type="System User",
			email="someone-else@example.com",
		)

		user = frappe.get_doc("User", TEST_EMAIL)
		self.assertEqual(user.first_name, "Renamed")
		self.assertEqual(user.user_type, "Website User")
		self.assertEqual(user.email, TEST_EMAIL)
		self.assertNotIn("System Manager", [r.role for r in user.roles])


def _delete_test_user():
	frappe.set_user("Administrator")
	for name in frappe.get_all("File", filters={"owner": TEST_EMAIL}, pluck="name"):
		frappe.delete_doc("File", name, force=True, ignore_permissions=True)
	for name in frappe.get_all("Contact", filters={"email_id": TEST_EMAIL}, pluck="name"):
		frappe.delete_doc("Contact", name, force=True, ignore_permissions=True)
	if frappe.db.exists("User", TEST_EMAIL):
		frappe.delete_doc("User", TEST_EMAIL, force=True, ignore_permissions=True)
	frappe.db.commit()
