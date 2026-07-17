frappe.ui.form.on("Job Applicant", {
	setup: function (frm) {
		frm.update_primary_actions = function () {
			frm.meta.is_submittable = 1;

			if (frm.is_new()) return;

			frm.page.clear_primary_action();

			if (frm.doc.docstatus === 0) {
				if (frm.is_dirty()) {
					frm.page.set_primary_action(__("Save"), () => {
						frm.save();
					});
				} else {
					frm.page.set_primary_action(__("Submit"), () => {
						frappe.confirm(
							__("Are you sure you want to submit this document?"),
							() => {
								frm.save("Submit");
							}
						);
					});
				}
			} else if (frm.doc.docstatus === 1) {
				if (frm.is_dirty()) {
					frm.page.set_primary_action(__("Update"), () => {
						frm.save("Update");
					});
					// } else {
					// 	frm.page.set_primary_action(__("Cancel"), () => {
					// 		frappe.confirm(__("Are you sure you want to cancel this document?"), () =>
					// 			frm.save("Cancel")
					// 		);
					// 	});
				}
			} else if (frm.doc.docstatus === 2) {
				frm.page.set_primary_action(__("Amend"), () => {
					frm.amend_doc();
				});
			}
		};

		frm.events.bind_field_watchers = function () {
			(frm.fields || []).forEach((f) => {
				if (f.df && f.df.fieldname && !f.__change_bound) {
					f.df.onchange = () => {
						frm.update_primary_actions();
					};
					f.__change_bound = true;
				}
			});
		};
	},

	refresh: function (frm) {
		frm.update_primary_actions();
		frm.events.bind_field_watchers();

		if (frm.doc.status === "Accepted" && frm.doc.is_volunteer == 1) {
			frappe.db.get_value("Employee", { job_applicant: frm.doc.name }, "name").then((r) => {
				if (r && !r.message.name) {
					frm.add_custom_button(
						__("Volunteer"),
						() => {
							frappe.route_options = {
								job_applicant: frm.doc.name,
								company: frm.doc.company,
							};
							frappe.new_doc("Employee");
						},
						__("Create")
					);
				}
			});
		}

		if (frm.doc.status === "Accepted" && frm.doc.is_volunteer == 0) {
			frappe.db
				.get_value("Employee", { personal_email: frm.doc.email_id }, "name")
				.then((r) => {
					if (r && !r.message.name) {
						frm.add_custom_button(
							__("Personnel"),
							() => {
								frappe.route_options = {
									job_applicant: frm.doc.name,
									company: frm.doc.company,
								};
								frappe.new_doc("Employee");
							},
							__("Create")
						);
					} else if (r && r.message.name) {
						frm.add_custom_button(__("Update Personnel Skills"), async () => {
							const employee_name = r.message.name;

							if (!frm.doc.job_title) {
								frappe.msgprint({
									title: __("Missing Opportunity Opening"),
									message: __(
										"No Opportunity Opening linked to this application."
									),
									indicator: "red",
								});
								return;
							}

							const job_opening = await frappe.db.get_doc(
								"Job Opening",
								frm.doc.job_title
							);

							if (
								!job_opening.required_skills ||
								!job_opening.required_skills.length
							) {
								frappe.msgprint({
									title: __("No Skills Found"),
									message: __(
										"The linked Opportunity Opening has no skills defined."
									),
									indicator: "orange",
								});
								return;
							}

							const fields = job_opening.required_skills.map((s) => ({
								fieldname: s.skill,
								label: s.skill,
								fieldtype: "Rating",
								reqd: 1,
								default: s.proficiency || 0,
							}));

							const d = new frappe.ui.Dialog({
								title: __("Rate Skills for Personnel"),
								fields: [
									{
										fieldname: "section",
										fieldtype: "Section Break",
										label: __("Skill Ratings"),
									},
									...fields,
								],
								primary_action_label: __("Update Skills"),
								primary_action: async () => {
									const values = d.get_values();
									if (!values) return;

									d.hide();

									await frappe.call({
										method: "onerc_vmms.volunteer_and_member_management.utils.utils.create_or_update_skill_map",
										args: {
											employee: employee_name,
											skills: values,
										},
										callback: function (r) {
											if (!r.exc) {
												frappe.msgprint({
													title: __("Success"),
													message: __(
														"Personnel Skill Map updated successfully."
													),
													indicator: "green",
												});
												if (r.message) {
													frappe.set_route(
														"Form",
														"Employee Skill Map",
														r.message
													);
												}
											}
										},
									});
								},
							});

							d.show();
						});
					}
				});
		}

		if (
			frm.doc.docstatus === 1 &&
			frm.doc.status === "Rejected" &&
			frm.doc.applicant_notified_of_application_status === 0
		) {
			frm.add_custom_button(
				__("Send Rejection Email"),
				() => {
					frappe.call({
						method: "onerc_vmms.volunteer_and_member_management.overrides.server.job_opening.send_rejection_email",
						args: {
							name: frm.doc.name,
						},
						callback: function (r) {
							if (!r.exc) {
								frappe.msgprint({
									title: __("Success"),
									message: __("Rejection email sent successfully."),
									indicator: "green",
								});
							}
						},
					});
				},
				__("Actions")
			);
		}
	},
	after_save: function (frm) {
		frm.update_primary_actions();

		if (frm.doc.status === "Accepted" && frm.doc.is_volunteer == 1) {
			frappe.db.get_value("Employee", { job_applicant: frm.doc.name }, "name").then((r) => {
				if (r && !r.message.name) {
					frappe.confirm(
						__("Do you want to create a Personnel record for this volunteer?"),
						() => {
							let new_employee = frappe.model.get_new_doc("Employee");
							new_employee.job_applicant = frm.doc.name;
							new_employee.company = frm.doc.company;
							new_employee.date_of_joining = frappe.datetime.get_today();

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
							};

							same_fields.forEach((field) => {
								if (frm.doc[field]) new_employee[field] = frm.doc[field];
							});

							Object.entries(field_mapping).forEach(
								([applicant_field, employee_field]) => {
									if (frm.doc[applicant_field])
										new_employee[employee_field] = frm.doc[applicant_field];
								}
							);

							if (frm.doc.applicant_name) {
								const parts = frm.doc.applicant_name.trim().split(" ");
								if (parts.length > 1) {
									new_employee.first_name = parts.slice(0, -1).join(" ");
									new_employee.last_name = parts.slice(-1).join(" ");
								} else {
									new_employee.first_name = parts[0];
								}
							}

							frappe.db.insert(new_employee).then((doc) => {
								frappe.msgprint({
									title: __("Personnel Created"),
									message: __("Personnel {0} has been created", [doc.name]),
									indicator: "green",
								});
								frappe.set_route("Form", "Employee", doc.name);
							});
						}
					);
				}
			});
		}
	},
});
