// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Deployment Request Tool", {
	setup: function (frm) {
		frm.trigger("set_query");
	},

	validate(frm) {
		if (frm.doc.expected_end_date && frm.doc.expected_start_date) {
			if (frm.doc.expected_end_date < frm.doc.expected_start_date) {
				frappe.msgprint(__("Expected End Date cannot be before Expected Start Date"));
				frappe.validated = false;
			}
		}
	},

	refresh: function (frm) {
		frm.page.clear_indicator();
		!frm.doc.__islocal ? addActionsButtons(frm) : null;
		frm.employees_datatable?.destroy();

		frm.trigger("set_primary_action");

		frm.events.set_task_filter(frm);

		frm.events.set_sub_county_filter(frm);
		frm.events.set_ward_filter(frm);
		frm.events.set_location_filter(frm);

		frm.events.set_tor_filter(frm);

		frm.set_query("region", function () {
			return {
				filters: [["organisation_type", "=", "Region"]],
			};
		});

		frm.set_query("branch", function () {
			const filters = [["organisation_type", "=", "Branch"]];
			const regions = [];
			if (frm.doc.region && frm.doc.region.length) {
				for (let i = 0; i < frm.doc.region.length; i++) {
					const company = frm.doc.region[i].company;
					if (company) {
						regions.push(company);
					}
				}
			}

			if (regions.length > 0) {
				filters.push(["parent_company", "in", regions]);
			}
			return { filters };
		});

		frm.set_query("branch", function () {
			const filters = [["organisation_type", "=", "Branch"]];
			const regions = [];
			if (frm.doc.region && frm.doc.region.length) {
				for (let i = 0; i < frm.doc.region.length; i++) {
					const company = frm.doc.region[i].company;
					if (company) {
						regions.push(company);
					}
				}
			}

			if (regions.length > 0) {
				filters.push(["parent_company", "in", regions]);
			}
			return { filters };
		});

		render_tor_preview(frm);
	},

	region(frm) {
		frm.set_value("branch", "");
	},

	county(frm) {
		frm.set_value("administrative_location", "");
		frm.set_value("sub_county", "");
		frm.set_value("ward", "");
		frm.events.set_sub_county_filter(frm);
		frm.events.set_ward_filter(frm);
		frm.events.set_location_filter(frm);
	},

	sub_county(frm) {
		frm.events.set_ward_filter(frm);
		frm.events.set_location_filter(frm);
	},

	terms_of_reference: function (frm) {
		frm.events.set_tor_filter(frm);
		frappe.db
			.get_value("Personnel Terms of Reference", frm.doc.terms_of_reference, [
				"company",
				"expected_start_date",
				"expected_end_date",
				"mission_background",
				"project",
				"title_of_mission",
			])
			.then((r) => {
				if (r && r.message) {
					if (r.message.company) frm.set_value("company", r.message.company);
					if (r.message.expected_start_date)
						frm.set_value("expected_start_date", r.message.expected_start_date);
					if (r.message.expected_end_date)
						frm.set_value("expected_end_date", r.message.expected_end_date);
					if (r.message.mission_background)
						frm.set_value("notes", r.message.mission_background);
					if (r.message.project) frm.set_value("project", r.message.project);
					if (r.message.title_of_mission)
						frm.set_value("title", r.message.title_of_mission);
				}
			});
		render_tor_preview(frm);
	},

	company: function (frm) {
		frm.events.set_tor_filter(frm);
	},

	project(frm) {
		if (!frm.doc.project) return;
		frm.events.set_task_filter(frm);
		// frappe.db
		// 	.get_value("Project", frm.doc.project, [
		// 		"company",
		// 		"expected_start_date",
		// 		"expected_end_date",
		// 		"notes",
		// 	])
		// 	.then((r) => {
		// 		if (r && r.message) {
		// 			if (r.message.company) frm.set_value("company", r.message.company);
		// 			if (r.message.expected_start_date)
		// 				frm.set_value("expected_start_date", r.message.expected_start_date);
		// 			if (r.message.expected_end_date)
		// 				frm.set_value("expected_end_date", r.message.expected_end_date);
		// 			if (r.message.notes) frm.set_value("notes", r.message.notes);
		// 		}
		// 	});
	},

	task(frm) {
		if (!frm.doc.task) return;

		frappe.db
			.get_value("Task", frm.doc.task, [
				"company",
				"exp_start_date",
				"exp_end_date",
				"description",
				"project",
			])
			.then((r) => {
				if (r && r.message) {
					if (r.message.company) frm.set_value("company", r.message.company);
					if (r.message.exp_start_date)
						frm.set_value("expected_start_date", r.message.exp_start_date);
					if (r.message.exp_end_date)
						frm.set_value("expected_end_date", r.message.exp_end_date);
					if (r.message.description) frm.set_value("notes", r.message.description);
					if (r.message.project) frm.set_value("project", r.message.project);
				}
			});
	},

	set_task_filter(frm) {
		frm.set_query("task", function () {
			return {
				filters: {
					project: frm.doc.project || "",
				},
			};
		});
	},

	set_sub_county_filter(frm) {
		const counties = [];
		if (frm.doc.county && frm.doc.county.length) {
			for (let i = 0; i < frm.doc.county.length; i++) {
				const county = frm.doc.county[i].county;
				if (county) {
					counties.push(county);
				}
			}
		}

		if (counties.length > 0) {
			frm.set_query("sub_county", function () {
				const filters = [["county", "in", counties]];
				return { filters };
			});
		} else {
			frm.set_query("sub_county", function () {
				return {};
			});
		}
	},

	set_location_filter(frm) {
		const counties = [];
		const sub_counties = [];

		if (frm.doc.county?.length) {
			for (let i = 0; i < frm.doc.county.length; i++) {
				const county = frm.doc.county[i].county;
				if (county) counties.push(county);
			}
		}

		if (frm.doc.sub_county?.length) {
			for (let i = 0; i < frm.doc.sub_county.length; i++) {
				const sub_county = frm.doc.sub_county[i].sub_county;
				if (sub_county) sub_counties.push(sub_county);
			}
		}

		frm.set_query("administrative_location", function () {
			const filters = [];

			if (counties.length > 0) {
				filters.push(["county", "in", counties]);
			}

			if (sub_counties.length > 0) {
				filters.push(["sub_county", "in", sub_counties]);
			}

			if (filters.length > 0) {
				return { filters };
			} else {
				return {};
			}
		});
	},

	set_ward_filter(frm) {
		const counties = [];
		if (frm.doc.county && frm.doc.county.length) {
			for (let i = 0; i < frm.doc.county.length; i++) {
				const county = frm.doc.county[i].county;
				if (county) {
					counties.push(county);
				}
			}
		}

		if (counties.length > 0) {
			frm.set_query("ward", function () {
				const filters = [["county", "in", counties]];
				return { filters };
			});
		} else {
			frm.set_query("ward", function () {
				return {};
			});
		}
	},

	set_tor_filter(frm) {
		frm.set_query("terms_of_reference", function () {
			return [];
		});
		frm.refresh_field("terms_of_reference");

		frm.call({
			method: "onerc_vmms.volunteer_and_member_management.utils.utils.get_company_descendants",
			args: {
				company: frm.doc.company,
			},
		}).then((r) => {
			const companies = r.message || [];
			if (frm.doc.company) companies.push(frm.doc.company);

			frm.set_query("terms_of_reference", function () {
				return {
					filters: {
						company: ["in", companies],
						project: frm.doc.project || "",
						expected_end_date: [">=", frappe.datetime.get_today()],
						docstatus: 1,
					},
				};
			});
		});
	},

	get_employees: function (frm) {
		if (!frm.doc.project || !frm.doc.expected_start_date) {
			frm.events.render_employees_datatable(frm, []);
			return;
		}

		frm.call({
			method: "_get_employees",
			args: {
				advanced_filters: frm.advanced_filters || [],
			},
			freeze: true,
			freeze_message: __("Fetching eligible personnel..."),
			doc: frm.doc,
		}).then((r) => {
			const columns = frm.events.get_employees_datatable_columns();
			frm.events.render_employees_datatable(frm, r.message || []);

			if (r.message) {
				// no additional handling required
			}
		});
	},

	render_employees_datatable: function (frm, employees) {
		const columns = frm.events.get_employees_datatable_columns();

		if (frm.employees_datatable) {
			frm.employees_datatable.destroy();
		}

		const wrapper = frm.get_field("employee_list").$wrapper;
		wrapper.empty();

		if (employees && employees.length > 0) {
			frm.employees_datatable = new frappe.DataTable(wrapper[0], {
				columns: columns,
				data: employees,
				checkboxColumn: true,
				layout: "fluid",
				cellHeight: 40,
				noDataMessage: __("No personnel found matching the criteria"),
			});
		} else {
			wrapper.html(`
        <div class="text-muted text-center" style="padding: 40px;">
          <i class="fa fa-users fa-3x" style="opacity: 0.3; margin-bottom: 15px;"></i>
          <p>${__("No personnel found matching the criteria")}</p>
          <small>${__("Adjust your filters to find eligible personnel")}</small>
        </div>
      `);
		}
	},

	get_employees_datatable_columns: function () {
		return [
			{
				name: "employee",
				id: "employee",
				content: __("Personnel ID"),
				width: 120,
				format: (value, row, column, data) => {
					return value
						? `<a href="/app/employee/${data.employee}" target="_blank">${value}</a>`
						: "";
				},
			},
			{
				name: "employee_name",
				id: "employee_name",
				content: __("Personnel Name"),
				width: 180,
				format: (value, row, column, data) => {
					return value
						? `<a href="/app/employee/${data.employee}" target="_blank">${value}</a>`
						: "";
				},
			},
			{
				name: "user_id",
				id: "user_id",
				content: __("Email"),
				width: 250,
				format: (value, row, column, data) => {
					return value
						? `<a href="/app/user/${value}" target="_blank">${value}</a>`
						: "";
				},
			},
			{
				name: "company",
				id: "company",
				content: __("Company"),
				width: 150,
				format: (value, row, column, data) => {
					return value
						? `<a href="/app/company/${value}" target="_blank">${value}</a>`
						: "";
				},
			},
			// {
			// 	name: "department",
			// 	id: "department",
			// 	content: __("Department"),
			// 	width: 150,
			// 	format: (value, row, column, data) => {
			// 		return value
			// 			? `<a href="/app/department/${value}" target="_blank">${value}</a>`
			// 			: "";
			// 	},
			// },
			{
				name: "designation",
				id: "designation",
				content: __("Designation"),
				width: 150,
				format: (value, row, column, data) => {
					return value
						? `<a href="/app/designation/${value}" target="_blank">${value}</a>`
						: "";
				},
			},
			// {
			// 	name: "employment_type",
			// 	id: "employment_type",
			// 	content: __("Personnel Type"),
			// 	width: 130,
			// 	format: (value) => {
			// 		return value || "";
			// 	},
			// },
		].map((x) => ({
			...x,
			editable: false,
			focusable: false,
			dropdown: false,
			align: "left",
		}));
	},

	deploy_employees: function (frm) {
		if (!frm.employees_datatable || !frm.employees_datatable.rowmanager.checkMap) {
			frappe.msgprint(__("Please select personnel to deploy"));
			return;
		}

		const check_map = frm.employees_datatable.rowmanager.checkMap;
		const selected_employees = [];

		check_map.forEach((is_checked, idx) => {
			if (is_checked && frm.employees_datatable.datamanager.data[idx]) {
				selected_employees.push(frm.employees_datatable.datamanager.data[idx].employee);
			}
		});

		if (selected_employees.length === 0) {
			frappe.msgprint(__("Please select at least one personnel to deploy"));
			return;
		}

		hrms.validate_mandatory_fields(frm, selected_employees);

		if (frm.is_dirty()) {
			frm.save().then(() => {
				frm.events.confirm_deployment(frm, selected_employees);
			});
		} else {
			frm.events.confirm_deployment(frm, selected_employees);
		}
	},

	confirm_deployment: function (frm, selected_employees) {
		frappe.confirm(
			__("Send request to {0} personnel(s) for this project?", [selected_employees.length]),
			() => frm.events.bulk_deploy_employees(frm, selected_employees)
		);
	},

	bulk_deploy_employees: function (frm, employees) {
		frm.call({
			method: "deploy_employees",
			doc: frm.doc,
			args: {
				employees: employees,
			},
			freeze: true,
			freeze_message: __("Sending Requests..."),
		}).then((r) => {
			if (r.message) {
				const { success, failure } = r.message;

				let message = "";

				if (success && success.length > 0) {
					message += __("Successfully sent {0} request(s)", [success.length]);
				}

				if (failure && failure.length > 0) {
					if (message) message += "<br>";
					message += __("Failed to create {0} request(s):", [failure.length]);
					message += "<ul>";
					failure.forEach((f) => {
						const employeeData = frm.employees_datatable.datamanager.data.find(
							(d) => d.employee === f.employee
						);
						const employeeName =
							(employeeData && employeeData.employee_name) || f.employee_name || "";
						message += `<li><a href="/app/employee/${f.employee}" target="_blank">${
							employeeName || f.employee
						}</a>: ${f.reason || "Unknown reason"}</li>`;
					});
					message += "</ul>";
				}

				if (message) {
					frappe.msgprint({
						title: __("Deployment Status"),
						message: message,
						indicator: success && success.length > 0 ? "green" : "red",
					});
				}

				frm.refresh();
			}
		});
	},
});

async function render_tor_preview(frm) {
	if (!frm.doc.tor_url) return;

	const tor_name = frm.doc.terms_of_reference;
	const doctype = "Personnel Terms of Reference";
	const base_url = window.location.origin;

	let pdf_url = `${base_url}/api/method/onerc_vmms.volunteer_and_member_management.utils.utils.download_pdf?doctype=${encodeURIComponent(
		doctype
	)}&name=${encodeURIComponent(tor_name)}`;

	pdf_url += "&settings=%7B%7D&_lang=en";

	const preview_html = `
		<div style="text-align: right; margin-bottom: 10px;">
			<a href="${pdf_url}" target="_blank" class="btn btn-primary btn-sm" style="margin-right: 5px;">View Full</a>
			<a href="${pdf_url}" download class="btn btn-secondary btn-sm">Download</a>
		</div>
		<iframe src="${pdf_url}" style="width: 100%; height: 600px; border: 1px solid #ccc; border-radius: 8px;"></iframe>
	`;

	frm.set_df_property("tor", "options", preview_html);
	frm.refresh_field("tor");
}

function addActionsButtons(frm) {
	const buttonRegistry = {
		"Fetch Volunteers": { method: "get_employees", type: "info", condition: false },
		"Send Deployment Request": {
			method: "deploy_employees",
			type: "danger",
			condition: frm.doc.future_deployment,
		},
	};

	Object.keys(buttonRegistry).forEach((action) => {
		const { method, type, condition } = buttonRegistry[action];

		if (condition) return;
		frm.add_custom_button(action, () => {
			frm.trigger(method);
		});
		frm.change_custom_button_type(action, null, type);
	});
}
