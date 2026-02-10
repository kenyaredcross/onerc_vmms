// Copyright (c) 2026, Kenya Red Cross Society and contributors

frappe.provide("onerc_vmms.data_import");

onerc_vmms.data_import.ImportPreview = class ImportPreview {
	constructor({ wrapper, preview_data, frm, events = {} }) {
		this.wrapper = wrapper;
		this.preview_data = preview_data;
		this.events = events;
		this.frm = frm;

		frappe.model.with_doctype("Employee", () => {
			frappe.model.with_doctype("User", () => {
				this.refresh();
			});
		});
	}

	refresh() {
		this.data = this.preview_data.data || [];
		this.make_wrapper();
		this.prepare_columns();
		this.render_datatable();
		this.add_actions();
	}

	make_wrapper() {
		this.wrapper.html(`
            <div class="import-preview-wrapper" style="margin-top: 15px;">
                <div class="preview-header d-flex justify-content-between align-items-center mb-2">
                    <h6 class="uppercase p-2 text-muted" style="margin:0;">${__("File Data Preview")}</h6>
                    <div class="table-actions d-flex" style="gap: 5px;"></div>
                </div>
                <div class="table-preview border rounded shadow-sm" style="overflow: hidden;"></div>
            </div>
        `);
		frappe.utils.bind_actions_with_object(this.wrapper, this);
		this.$table_preview = this.wrapper.find(".table-preview");
	}

	prepare_columns() {
		this.columns = this.preview_data.columns.map((col, i) => {
			let header = col.header_title || __("Untitled");
			if (header === "Sr. No") return { id: "srno", name: "Sr. No", width: 70 };
			return {
				id: `col_${i}`,
				name: header,
				content: `<span class="indicator ${col.df ? "green" : "red"}">${header}</span>`,
				width: 160,
			};
		});
	}

	render_datatable() {
		if (this.datatable) this.datatable.destroy();
		this.datatable = new DataTable(this.$table_preview.get(0), {
			data: this.data.slice(0, 5),
			columns: this.columns,
			layout: "fixed",
		});
	}

	add_actions() {
		this.wrapper.find(".table-actions").html(`
            <button class="btn btn-xs btn-default" data-action="show_column_mapper">
                <i class="fa fa-exchange text-muted"></i> ${__("Map Columns")}
            </button>
        `);
	}

	show_column_mapper() {
		const emp_opts = this.get_doctype_options("Employee");
		const user_opts = this.get_doctype_options("User");
		const SKIP_VAL = "Don't Import";
		const skip_option = { label: __(SKIP_VAL), value: SKIP_VAL };

		let emp_saved = {},
			user_saved = {};
		try {
			emp_saved =
				JSON.parse(this.frm.doc.employee_template_options || "{}").column_to_field_map ||
				{};
			user_saved =
				JSON.parse(this.frm.doc.user_template_options || "{}").column_to_field_map || {};
		} catch (e) {}

		let fields = [
			{
				fieldtype: "HTML",
				options: `<div class="row fw-bold text-muted small uppercase px-2 mb-2" style="border-bottom: 2px solid var(--border-color); padding-bottom: 10px;">
                        <div class="col-4">${__("File Column")}</div>
                        <div class="col-4">${__("User Mapping")}</div>
                        <div class="col-4">${__("Employee Mapping")}</div>
                      </div>`,
			},
		];

		this.preview_data.columns.forEach((col, i) => {
			const header = col.header_title;
			if (header === "Sr. No") return;

			const current_user =
				user_saved[header] || this.find_best_match(header, user_opts) || SKIP_VAL;
			const current_emp =
				emp_saved[header] || this.find_best_match(header, emp_opts) || SKIP_VAL;

			fields.push(
				{ fieldtype: "Section Break", fieldname: `sb_${i}` },
				{ fieldtype: "Column Break", width: "33%" },
				{
					fieldtype: "HTML",
					options: `<div style="padding-top: 8px; font-weight: bold; font-size: 12px;">${header}</div>`,
				},
				{ fieldtype: "Column Break", width: "33%" },
				{
					fieldname: `user_map_${i}`,
					fieldtype: "Autocomplete",
					options: [skip_option].concat(user_opts),
					default: current_user,
				},
				{ fieldtype: "Column Break", width: "33%" },
				{
					fieldname: `emp_map_${i}`,
					fieldtype: "Autocomplete",
					options: [skip_option].concat(emp_opts),
					default: current_emp,
				},
			);
		});

		let dialog = new frappe.ui.Dialog({
			title: __("Map Personnel Data Fields"),
			fields: fields,
			size: "large",
			primary_action: (values) => {
				let e_map = {},
					u_map = {};
				this.preview_data.columns.forEach((col, i) => {
					const header = col.header_title;
					if (header === "Sr. No") return;
					u_map[header] = values[`user_map_${i}`] || SKIP_VAL;
					e_map[header] = values[`emp_map_${i}`] || SKIP_VAL;
				});
				this.events.remap_columns(e_map, u_map);
				dialog.hide();
			},
		});

		dialog.on_page_render = () => {
			dialog.wrapper.find(".section-break").css({
				"margin-top": "0px",
				"border-bottom": "1px solid var(--border-color)",
				padding: "5px 0",
			});
			dialog.wrapper.find(".modal-body").css({ "overflow-y": "auto", "max-height": "60vh" });
			dialog.wrapper.find(".section-head").hide();
		};
		dialog.show();
	}

	find_best_match(header, options) {
		if (!header) return null;
		let h = header.toLowerCase().replace(/[^a-z0-9]/g, "");
		let match = options.find((o) => {
			let l = o.label.toLowerCase().replace(/[^a-z0-9]/g, "");
			return l.includes(h) || h.includes(o.value.toLowerCase());
		});
		return match ? match.value : null;
	}

	get_doctype_options(dt) {
		let meta = frappe.get_meta(dt);
		return meta.fields
			.filter((df) => frappe.model.is_value_type(df.fieldtype) && !df.hidden)
			.map((df) => ({ label: `${__(df.label)} (${df.fieldname})`, value: df.fieldname }));
	}
};

frappe.ui.form.on("Personnel Data Import", {
	refresh(frm) {
		frm.trigger("update_indicators");
		frm.trigger("import_file");
		frm.trigger("update_primary_action");
		frm.trigger("show_import_log");
		frm.trigger("show_import_warnings");
		frappe.realtime.on("data_import_refresh", function (data) {
			if (data.data_import === frm.doc.name) {
				frm.reload_doc();
			}
		});

		frappe.realtime.on("data_import_progress", function (data) {
			if (data.data_import === frm.doc.name) {
				frappe.show_progress(
					__("Importing"),
					data.current,
					data.total,
					__("Processing row {0} of {1}").format(data.current, data.total),
				);
			}
		});
	},

	update_primary_action(frm) {
		if (frm.is_dirty()) {
			frm.enable_save();
			return;
		}
		// frm.disable_save();

		if (frm.doc.status === "In Progress") {
			frm.page.clear_primary_action();
			return;
		}

		if (frm.doc.import_file && frm.doc.status !== "Success") {
			let label =
				frm.doc.status === "Pending" || !frm.doc.status
					? __("Start Import")
					: __("Retry Import");
			frm.page.set_primary_action(label, () => frm.trigger("start_import"));
		} else if (!frm.doc.import_file) {
			frm.page.set_primary_action(__("Save"), () => frm.save());
		}
	},

	start_import(frm) {
		frm.call({
			method: "form_start_import",
			args: { data_import: frm.doc.name },
			btn: frm.page.btn_primary,
		}).then((r) => {
			if (r.message) frm.reload_doc();
		});
	},

	import_file(frm) {
		if (!frm.doc.import_file) return;
		frm.call({
			method: "get_preview_from_template",
			doc: frm.doc,
		}).then((r) => {
			if (r.message) {
				frm.get_field("import_preview").$wrapper.empty();
				let $container = $('<div class="unified-preview-container"></div>').appendTo(
					frm.get_field("import_preview").$wrapper,
				);
				frm.import_preview = new onerc_vmms.data_import.ImportPreview({
					wrapper: $container,
					preview_data: r.message,
					frm: frm,
					events: {
						remap_columns: (emp_map, user_map) => {
							frm.set_value(
								"employee_template_options",
								JSON.stringify({ column_to_field_map: emp_map }),
							);
							frm.set_value(
								"user_template_options",
								JSON.stringify({ column_to_field_map: user_map }),
							);
							frm.save().then(() => frm.trigger("import_file"));
						},
					},
				});
			}
		});
	},

	update_indicators(frm) {
		const indicator = frappe.get_indicator(frm.doc);
		if (indicator) frm.page.set_indicator(indicator[0], indicator[1]);
	},

	show_import_warnings(frm, preview_data) {
		let columns = preview_data.columns;
		let warnings = JSON.parse(frm.doc.template_warnings || "[]");
		warnings = warnings.concat(preview_data.warnings || []);

		frm.toggle_display("import_warnings_section", warnings.length > 0);
		if (warnings.length === 0) {
			frm.get_field("import_warnings").$wrapper.html("");
			return;
		}

		let warnings_by_row = {};
		let other_warnings = [];
		for (let warning of warnings) {
			if (warning.row) {
				warnings_by_row[warning.row] = warnings_by_row[warning.row] || [];
				warnings_by_row[warning.row].push(warning);
			} else {
				other_warnings.push(warning);
			}
		}

		let html = "";
		html += Object.keys(warnings_by_row)
			.map((row_number) => {
				let message = warnings_by_row[row_number]
					.map((w) => {
						if (w.field) {
							let label =
								w.field.label +
								(w.field.parent !== frm.doc.reference_doctype
									? ` (${w.field.parent})`
									: "");
							return `<li>${label}: ${w.message}</li>`;
						}
						return `<li>${w.message}</li>`;
					})
					.join("");
				return `
                <div class="warning" data-row="${row_number}">
                    <h5 class="text-uppercase">${__("Row {0}", [row_number])}</h5>
                    <div class="body"><ul>${message}</ul></div>
                </div>
            `;
			})
			.join("");

		html += other_warnings
			.map((warning) => {
				let header = "";
				if (columns && warning.col) {
					let column_number = `<span class="text-uppercase">${__("Column {0}", [
						warning.col,
					])}</span>`;
					let column_header = columns[warning.col].header_title;
					header = `${column_number} (${column_header})`;
				}
				return `
                    <div class="warning" data-col="${warning.col}">
                        <h5>${header}</h5>
                        <div class="body">${warning.message}</div>
                    </div>
                `;
			})
			.join("");
		frm.get_field("import_warnings").$wrapper.html(`
            <div class="row">
                <div class="col-sm-10 warnings">${html}</div>
            </div>
        `);
	},

	show_failed_logs(frm) {
		frm.trigger("show_import_log");
	},

	render_import_log(frm) {
		frappe.call({
			method: "onerc_vmms.volunteer_and_member_management.doctype.personnel_data_import.personnel_data_import.get_import_logs",
			args: {
				data_import: frm.doc.name,
			},
			callback: function (r) {
				let logs = r.message;

				if (logs.length === 0) return;

				frm.toggle_display("import_log_preview", true);

				let rows = logs
					.map((log) => {
						let html = "";
						if (log.success) {
							const ref_dt = frm.doc.reference_doctype;
							const link =
								ref_dt && log.docname
									? frappe.utils.get_form_link(ref_dt, log.docname, true)
									: log.docname || __("Unknown Record");

							if (frm.doc.import_type === "Insert New Records") {
								html = __("Successfully imported {0}", [
									`<span class="underline">${link}</span>`,
								]);
							} else {
								html = __("Successfully updated {0}", [
									`<span class="underline">${link}</span>`,
								]);
							}
						} else {
							let messages = JSON.parse(log.messages || "[]")
								.map((m) => {
									let title = m.title ? `<strong>${m.title}</strong>` : "";
									let message = m.message ? `<div>${m.message}</div>` : "";
									return title + message;
								})
								.join("");
							let id = frappe.dom.get_unique_id();
							html = `${messages}
                                <button class="btn btn-default btn-xs" type="button" data-toggle="collapse" data-target="#${id}" aria-expanded="false" aria-controls="${id}" style="margin-top: 15px;">
                                    ${__("Show Traceback")}
                                </button>
                                <div class="collapse" id="${id}" style="margin-top: 15px;">
                                    <div class="well">
                                        <pre>${log.exception}</pre>
                                    </div>
                                </div>`;
						}
						let indicator_color = log.success ? "green" : "red";
						let title = log.success ? __("Success") : __("Failure");

						if (frm.doc.show_failed_logs && log.success) {
							return "";
						}

						return `<tr>
                            <td>${JSON.parse(log.row_indexes).join(", ")}</td>
                            <td>
                                <div class="indicator ${indicator_color}">${title}</div>
                            </td>
                            <td>
                                ${html}
                            </td>
                        </tr>`;
					})
					.join("");

				if (!rows && frm.doc.show_failed_logs) {
					rows = `<tr><td class="text-center text-muted" colspan=3>
                        ${__("No failed logs")}
                    </td></tr>`;
				}

				frm.get_field("import_log_preview").$wrapper.html(`
                    <table class="table table-bordered">
                        <tr class="text-muted">
                            <th width="10%">${__("Row Number")}</th>
                            <th width="10%">${__("Status")}</th>
                            <th width="80%">${__("Message")}</th>
                        </tr>
                        ${rows}
                    </table>
                `);
			},
		});
	},

	show_import_log(frm) {
		frm.toggle_display("import_log_preview", false);

		if (frm.is_new() || frm.import_in_progress) {
			return;
		}

		frappe.call({
			method: "frappe.client.get_count",
			args: {
				doctype: "Data Import Log",
				filters: {
					data_import: frm.doc.name,
				},
			},
			callback: function (r) {
				let count = r.message;

				if (count < 50000) {
					frm.trigger("render_import_log");
				} else {
					frm.toggle_display("import_log_preview", false);
					frm.add_custom_button(__("Export Import Log"), () =>
						frm.trigger("export_import_log"),
					);
				}
			},
		});
	},
});
