// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Personnel Deployment Request", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.require_contract_before_deployment) {
			frappe.db.get_value(
				"Contract",
				{
					personnel_deployment_assignment: frm.doc.name,
					docstatus: ["!=", 2],
				},
				["name"],
				(r) => {
					if (r && !r.name) {
						frm.add_custom_button(__("Create Contract"), () => {
							frappe.model.with_doctype("Contract", () => {
								let contract = frappe.model.get_new_doc("Contract");
								contract.party_type = "Employee";
								contract.party_name = frm.doc.employee;
								contract.start_date = frm.doc.expected_start_date;
								contract.end_date = frm.doc.expected_end_date;
								contract.project = frm.doc.project;
								contract.task = frm.doc.task;
								contract.personnel_deployment_assignment = frm.doc.name;
								contract.personnel_deployment_request = frm.doc.deployment;

								frappe.set_route("Form", "Contract", contract.name);
							});
						}).addClass("btn-primary");
					}
				}
			);
		}

		render_tor_preview(frm);
	},

	terms_of_reference: function (frm) {
		render_tor_preview(frm);
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
		frm.trigger("get_employees");
	},

	project(frm) {
		if (!frm.doc.project) return;
		frm.events.set_task_filter(frm);
		frappe.db
			.get_value("Project", frm.doc.project, [
				"company",
				"expected_start_date",
				"expected_end_date",
				"notes",
				"terms_of_reference",
			])
			.then((r) => {
				if (r && r.message) {
					if (r.message.company) frm.set_value("company", r.message.company);
					if (r.message.expected_start_date)
						frm.set_value("expected_start_date", r.message.expected_start_date);
					if (r.message.expected_end_date)
						frm.set_value("expected_end_date", r.message.expected_end_date);
					if (r.message.notes) frm.set_value("notes", r.message.notes);
					if (r.message.terms_of_reference)
						frm.set_value("terms_of_reference", r.message.terms_of_reference);
				}
			});
		frm.trigger("get_employees");
	},

	deployment(frm) {
		if (!frm.doc.deployment) return;
		frappe.db
			.get_value("Deployment Request Tool", frm.doc.deployment, [
				"project",
				"terms_of_reference",
				"tor_url",
				"expected_start_date",
				"expected_end_date",
				"notes",
			])
			.then((r) => {
				if (r && r.message) {
					if (r.message.project) frm.set_value("project", r.message.project);
					if (r.message.tor_url) frm.set_value("tor_url", r.message.tor_url);
					if (r.message.terms_of_reference)
						frm.set_value("terms_of_reference", r.message.terms_of_reference);

					if (r.message.expected_start_date)
						frm.set_value("expected_start_date", r.message.expected_start_date);
					if (r.message.expected_end_date)
						frm.set_value("expected_end_date", r.message.expected_end_date);
					if (r.message.notes) frm.set_value("notes", r.message.notes);
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
});

async function render_tor_preview(frm) {
	if (!frm.doc.terms_of_reference) {
		frm.set_df_property("tor", "options", "");
		frm.refresh_field("tor");
		return;
	}

	const tor_name = frm.doc.terms_of_reference;
	const doctype = "Personnel Terms of Reference";
	const base_url = window.location.origin;

	let pdf_url = `${base_url}/api/method/frappe.utils.print_format.download_pdf?doctype=${encodeURIComponent(
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
	if (frm.doc.tor_url !== pdf_url) {
		frm.doc.tor_url = pdf_url;
		frm.save();
	}
	frm.refresh_field("tor");
}
