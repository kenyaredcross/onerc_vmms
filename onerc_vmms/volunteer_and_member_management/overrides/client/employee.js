// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee", {
	refresh(frm) {
		if (frm.doc.job_applicant) {
			fetchJobApplicantDetails(frm);
		}

		if (!frm.doc.date_of_joining) {
			frm.set_value("date_of_joining", frappe.datetime.get_today());
		}

		frappe.db
			.get_value("VM Member", { email_id: frm.doc.personal_email }, "name")
			.then((r) => {
				if (!(r && r.message && r.message.name)) {
					frm.add_custom_button(__("Create Member"), () => {
						frm.call({
							method: "onerc_vmms.volunteer_and_member_management.api.membership.create_member",
							args: { name: frm.doc.name },
						}).then(() => {
							frappe.show_alert({
								message: __("Member created successfully"),
								indicator: "green",
							});
							frm.reload_doc();
						});
					});
				}
			});
	},

	job_applicant(frm) {
		if (!frm.doc.job_applicant) return;
		fetchJobApplicantDetails(frm);
	},
});

function fetchJobApplicantDetails(frm) {
	frappe.model.with_doc("Job Applicant", frm.doc.job_applicant, function () {
		const job_applicant = frappe.get_doc("Job Applicant", frm.doc.job_applicant);
		const update_fields = {};

		const same_fields = [
			"company",
			"gender",
			"blood_group",
			"marital_status",
			"date_of_birth",
		];

		const field_mapping = {
			surname: "last_name",
			other_names: "first_name",
			email_id: "personal_email",
			phone_number: "cell_number",
			cover_letter: "bio",
			// profile_photo: "image",
		};

		same_fields.forEach((field) => {
			if (job_applicant[field] && !frm.doc[field]) {
				update_fields[field] = job_applicant[field];
			}
		});

		Object.entries(field_mapping).forEach(([applicant_field, employee_field]) => {
			if (job_applicant[applicant_field] && !frm.doc[employee_field]) {
				update_fields[employee_field] = job_applicant[applicant_field];
			}
		});

		if (job_applicant.applicant_name && !frm.doc.first_name && !frm.doc.last_name) {
			const parts = job_applicant.applicant_name.trim().split(" ");
			if (parts.length > 1) {
				update_fields.first_name = parts.slice(0, -1).join(" ");
				update_fields.last_name = parts.slice(-1).join(" ");
			} else {
				update_fields.first_name = parts[0];
			}
		}

		if (Object.keys(update_fields).length > 0) {
			frm.set_value(update_fields);
		}
	});
}
