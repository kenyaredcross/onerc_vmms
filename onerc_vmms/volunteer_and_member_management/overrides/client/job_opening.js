frappe.ui.form.on("Job Opening", {
	refresh: function (frm) {
		frappe.db.get_doc("VM Settings").then((settings) => {
			if (!settings) return;

			const mapping = {
				enable_automatic_rejection_notifications:
					"enable_automatic_rejection_notifications",
				notify_unshortlisted_applicants_after: "notify_unshortlisted_applicants_after",
				rejection_email_template: "rejection_email_template",
			};

			Object.entries(mapping).forEach(([target_field, source_field]) => {
				const value = settings[source_field];
				if (value && !frm.doc[target_field]) {
					frm.set_value(target_field, value);
				}
			});
		});

		frappe.call({
			method: "onerc_vmms.volunteer_and_member_management.overrides.server.job_opening.get_rejected_applicants",
			args: { job_opening: frm.doc.name },
			callback: function (r) {
				if (r.message && r.message.length > 0) {
					frm.add_custom_button(
						__("Send Rejection Emails"),
						() => show_rejection_dialog(frm, r.message),
						__("Actions")
					);
				}
			},
		});

		update_screening_questions_scoring_property(frm);
	},

	validate: function (frm) {
		if (frm.doc.opportunity_type === "Internal") {
			if (!frm.doc.required_skills || frm.doc.required_skills.length === 0) {
				frappe.msgprint({
					title: __("Missing Skills"),
					message: __(
						"At least one Required Skill must be added for Internal opportunities."
					),
					indicator: "red",
				});
				frappe.validated = false;
				return;
			}
		}
		if (
			frm.doc.shortlisted_rejection_notification_date &&
			frm.doc.closes_on > frm.doc.shortlisted_rejection_notification_date
		) {
			frappe.msgprint({
				title: __("Invalid Date"),
				message: __(
					"The Closing Date must be before the Shortlisted Rejection Notification Date."
				),
				indicator: "red",
			});
			frappe.validated = false;
			return;
		}
	},

	designation: function (frm) {
		if (frm.doc.designation) {
			frappe.call({
				method: "frappe.client.get",
				args: { doctype: "Designation", name: frm.doc.designation },
				callback: function (r) {
					if (r.message && r.message.skills && r.message.skills.length > 0) {
						frm.clear_table("required_skills");

						r.message.skills.forEach(function (skill) {
							let row = frm.add_child("required_skills");
							row.skill = skill.skill;
						});

						frm.refresh_field("required_skills");
						frappe.show_alert(__("Skills updated from Designation"));
					}
				},
			});
		}
	},

	job_opening_template: function (frm) {
		if (!frm.doc.job_opening_template) return;

		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Job Opening Template",
				name: frm.doc.job_opening_template,
			},
			callback: function (r) {
				if (!r.message) return;

				let template = r.message;

				const skip_fields = [
					"name",
					"job_opening_template",
					"creation",
					"modified",
					"modified_by",
					"owner",
					"idx",
				];

				const skip_fieldtypes = [
					"Section Break",
					"Column Break",
					"Tab Break",
					"HTML",
					"Button",
					"Read Only",
					"Image",
					"Fold",
				];

				frappe.meta.get_docfields("Job Opening").forEach((df) => {
					let fieldname = df.fieldname;

					if (
						!fieldname ||
						skip_fields.includes(fieldname) ||
						skip_fieldtypes.includes(df.fieldtype)
					) {
						return;
					}

					if (df.fieldtype === "Table") {
						frm.clear_table(fieldname);

						if (template[fieldname] && template[fieldname].length > 0) {
							template[fieldname].forEach((row) => {
								let new_row = frm.add_child(fieldname);
								Object.keys(row).forEach((key) => {
									if (
										!skip_fields.includes(key) &&
										![
											"doctype",
											"parent",
											"parentfield",
											"parenttype",
											"name",
											"idx",
										].includes(key)
									) {
										new_row[key] = row[key];
									}
								});
							});
							frm.refresh_field(fieldname);
						}
					} else {
						frm.set_value(fieldname, template[fieldname]);
					}
				});

				update_question_identifiers(frm);
				update_screening_questions_scoring_property(frm);
				frappe.show_alert(__("Fields copied from Job Opening Template"));
			},
		});
	},

	status: function (frm) {
		if (frm.doc.status === "Closed") {
			frm.set_value("closed_on", frappe.datetime.get_today());
		} else {
			frm.set_value("closed_on", null);
		}
	},
});

frappe.ui.form.on("Job Application Screening Questions", {
	screening_questions_add: function (frm, cdt, cdn) {
		update_question_identifiers(frm);
	},

	screening_questions_remove: function (frm, cdt, cdn) {
		update_question_identifiers(frm);
	},

	question_type: function (frm, cdt, cdn) {
		validate_expected_answers(frm, cdt, cdn);
	},

	options: function (frm, cdt, cdn) {
		validate_expected_answers(frm, cdt, cdn);
	},

	is_knock_off: function (frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);

		if (row.is_knock_off) {
			frappe.model.set_value(cdt, cdn, "is_required", 1);
		}

		let should_enable = row.is_knock_off || row.expected_answer;
		frappe.model.set_value(cdt, cdn, "enable_scoring", should_enable ? 1 : 0);
	},

	expected_answer: function (frm, cdt, cdn) {
		validate_expected_answers(frm, cdt, cdn);
	},
});

function validate_expected_answers(frm, cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);
	if (!row.expected_answer) {
		let should_enable = row.is_knock_off || row.expected_answer;
		frappe.model.set_value(cdt, cdn, "enable_scoring", should_enable ? 1 : 0);
		return;
	}

	let raw_answers = row.expected_answer
		.split("\n")
		.map((ans) => ans.trim())
		.filter(Boolean);
	let raw_options = row.options
		? row.options
				.split("\n")
				.map((opt) => opt.trim())
				.filter(Boolean)
		: [];

	if (row.question_type === "Yes/No") {
		let invalid = raw_answers.filter((ans) => !["Yes", "No"].includes(ans));
		if (invalid.length > 0 || raw_answers.length > 1) {
			frappe.msgprint({
				title: __("Validation Error"),
				message: __(
					"For Yes/No questions, the Expected Answer can only be a single line containing either 'Yes' or 'No'."
				),
				indicator: "red",
			});
			frappe.model.set_value(cdt, cdn, "expected_answer", "");
			return;
		}
	}

	if (row.question_type === "Select") {
		if (raw_answers.length > 1) {
			frappe.msgprint({
				title: __("Validation Error"),
				message: __(
					"For Select questions, only one single answer line from the Options config is allowed."
				),
				indicator: "red",
			});
			frappe.model.set_value(cdt, cdn, "expected_answer", "");
			return;
		}
		if (raw_options.length > 0 && !raw_options.includes(raw_answers[0])) {
			frappe.msgprint({
				title: __("Validation Error"),
				message: __(
					"The Expected Answer '{0}' does not match any row configured in the Options text field.",
					[raw_answers[0]]
				),
				indicator: "red",
			});
			frappe.model.set_value(cdt, cdn, "expected_answer", "");
			return;
		}
	}

	if (row.question_type === "MultiSelect") {
		if (raw_options.length > 0) {
			let invalid_opts = raw_answers.filter((ans) => !raw_options.includes(ans));
			if (invalid_opts.length > 0) {
				frappe.msgprint({
					title: __("Validation Error"),
					message: __(
						"The following items in your Expected Answer are missing from the Options rows field: <br><br><b>{0}</b>",
						[invalid_opts.join(", ")]
					),
					indicator: "red",
				});
				frappe.model.set_value(cdt, cdn, "expected_answer", "");
				return;
			}
		}
	}

	let should_enable = row.is_knock_off || row.expected_answer;
	frappe.model.set_value(cdt, cdn, "enable_scoring", should_enable ? 1 : 0);
}

function update_question_identifiers(frm) {
	if (!frm.doc.screening_questions) return;

	frm.doc.screening_questions.forEach((row, index) => {
		const expected_id = `Q${index + 1}`;
		if (row.question_id !== expected_id) {
			frappe.model.set_value(row.doctype, row.name, "question_id", expected_id);
		}
	});
}

function update_screening_questions_scoring_property(frm) {
	if (!frm.doc.screening_questions) return;

	frm.doc.screening_questions.forEach((row) => {
		const should_enable = row.is_knock_off || row.expected_answer;
		if (should_enable && !row.enable_scoring) {
			frappe.model.set_value(row.doctype, row.name, "enable_scoring", 1);
		}
	});
}

function show_rejection_dialog(frm, applicants) {
	const d = new frappe.ui.Dialog({
		title: __("Send Rejection Emails"),
		fields: [
			{
				fieldtype: "HTML",
				options:
					"<p class='text-muted mb-3'>" +
					__(
						"Only the applicants listed in the table below will receive rejection emails. You may remove applicants you do not wish to notify."
					) +
					"</p>",
			},
			{
				fieldname: "applicants_table",
				fieldtype: "Table",
				label: __("Applicants to Notify"),
				cannot_add_rows: true,
				in_place_edit: false,
				data: applicants.map((a) => ({
					name: a.name,
					applicant_name: a.applicant_name,
					email_id: a.email_id,
				})),
				fields: [
					{
						fieldname: "name",
						label: __("ID"),
						fieldtype: "Link",
						read_only: 1,
						options: "Job Applicant",
						in_list_view: 1,
					},
					{
						fieldname: "applicant_name",
						label: __("Applicant Name"),
						fieldtype: "Data",
						read_only: 1,
						in_list_view: 1,
					},
					{
						fieldname: "email_id",
						label: __("Email"),
						fieldtype: "Data",
						read_only: 1,
						in_list_view: 1,
					},
				],
			},
		],
		primary_action_label: __("Send Emails"),
		primary_action(values) {
			const selected_applicants = values.applicants_table || [];
			if (selected_applicants.length === 0) {
				frappe.msgprint({
					title: __("No Applicants Selected"),
					message: __("Please keep at least one applicant in the table."),
					indicator: "red",
				});
				return;
			}

			frappe.call({
				method: "onerc_vmms.volunteer_and_member_management.overrides.server.job_opening.send_rejection_emails",
				args: { applicants: JSON.stringify(selected_applicants) },
				callback: function (r) {
					if (!r.exc) {
						frappe.msgprint({
							title: __("Success"),
							message: __("Rejection emails queued successfully."),
							indicator: "green",
						});
						d.hide();
					}
				},
			});
		},
	});

	d.show();
}
