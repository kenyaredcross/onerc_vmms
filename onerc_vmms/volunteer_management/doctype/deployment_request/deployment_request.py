import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class DeploymentRequest(Document):

	def before_save(self):
		self.update_status_summary()

	def on_submit(self):
		self.send_deployment_notifications()

	def update_status_summary(self):
		self.total_notified = len(self.volunteers)
		self.total_accepted  = sum(1 for v in self.volunteers if v.response == "Accepted")
		self.total_declined  = sum(1 for v in self.volunteers if v.response == "Declined")
		self.total_pending   = sum(1 for v in self.volunteers if v.response == "Pending")
		self.total_withdrawn = sum(1 for v in self.volunteers if v.response == "Withdrawn")

		if (self.total_pending == 0
				and self.total_accepted < (self.volunteers_required or 1)
				and not self.manager_notified_threshold):
			self.manager_notified_threshold = 1
			self.notify_manager_threshold()

	def notify_manager_threshold(self):
		try:
			frappe.sendmail(
				recipients=[frappe.session.user],
				subject=f"Deployment {self.name} — Insufficient acceptances",
				message=(
					f"<p>Deployment <b>{self.name}</b> ({self.tor_title}) "
					f"has {self.total_accepted} acceptance(s) but requires "
					f"{self.volunteers_required}. All volunteers have responded.</p>"
					f"<p>Accepted: {self.total_accepted} | "
					f"Declined: {self.total_declined} | "
					f"Withdrawn: {self.total_withdrawn}</p>"
				)
			)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Deployment threshold notification failed")

	def send_deployment_notifications(self):
		if not self.volunteers:
			return
		tor = frappe.get_doc("Terms of Reference", self.tor)
		for row in self.volunteers:
			try:
				vol = frappe.get_doc("Volunteer", row.volunteer)
				if self.notify_via_email and vol.email_address:
					self.send_email(vol, tor)
				if self.notify_via_sms and vol.primary_phone:
					self.send_sms(vol)
				frappe.db.set_value(
					"Deployment Request Volunteer", row.name,
					"notified_at", now_datetime()
				)
			except Exception:
				frappe.log_error(
					frappe.get_traceback(),
					f"Notification failed for volunteer {row.volunteer}"
				)
		frappe.db.commit()

	def send_email(self, vol, tor):
		link = frappe.utils.get_url(f"/vmms/deployments/{self.name}")
		msg = self.message_to_volunteers or ""
		frappe.sendmail(
			recipients=[vol.email_address],
			subject=f"Deployment Request — {tor.title_of_mission}",
			message=(
				f"<p>Dear {vol.first_name},</p>"
				f"<p>You have been selected for: <b>{tor.title_of_mission}</b></p>"
				f"<p>Dates: {tor.start_date} to {tor.end_date}<br>"
				f"Location: {tor.location_description or ''}<br>"
				f"Respond by: {self.response_deadline}</p>"
				f"{'<p>' + msg + '</p>' if msg else ''}"
				f"<p><a href='{link}' style='background:#EE2435;color:#fff;"
				f"padding:10px 20px;border-radius:6px;text-decoration:none;"
				f"font-weight:bold;'>Review and Respond</a></p>"
			)
		)

	def send_sms(self, vol):
		try:
			frappe.call(
				"onerc_sms.api.send_sms",
				phone=vol.primary_phone,
				message=(
					f"Deployment: {self.tor_title}. "
					f"Respond by {self.response_deadline}. "
					f"Login: {frappe.utils.get_url('/vmms')}"
				)
			)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"SMS failed for {vol.primary_phone}"
			)
