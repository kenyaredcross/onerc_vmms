// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Personnel Details Update", {
	setup(frm) {
		frm.set_query("employee", () => ({
			filters: { status: "Active" },
		}));
	},

	onload(frm) {
		if (frm.doc.__islocal && !frm.doc.amended_from) {
			frm.clear_table("update_details");
			frm.refresh_field("update_details");
		}
	},

	employee(frm) {
		frm.clear_table("update_details");
		frm.refresh_field("update_details");
	},

	refresh(frm) {
		if (!frm.doc.date) {
			frm.set_value("date", frappe.datetime.get_today());
		}
		frm.fields_dict.update_details.grid.wrapper.find(".grid-add-row").hide();
		frm.events.setup_employee_property_button(frm);
	},

	setup_employee_property_button(frm) {
		frm.fields_dict.update_details.grid.add_custom_button(__("Add Employee Property"), () => {
			if (!frm.doc.employee) {
				frappe.msgprint(__("Please select Employee first."));
				return;
			}

			const allowed_fields = [];
			const exclude_fields = [
				"naming_series",
				"employee",
				"employee_name",
				"status",
				"image",
				"lft",
				"rgt",
				"old_parent",
			];

			const exclude_field_types = [
				"HTML",
				"Section Break",
				"Column Break",
				"Button",
				"Read Only",
				"Tab Break",
			];

			frappe.model.with_doctype("Employee", () => {
				const field_label_map = {};
				frappe.get_meta("Employee").fields.forEach((d) => {
					field_label_map[d.fieldname] =
						__(d.label, null, d.parent) + ` (${d.fieldname})`;

					if (d.fieldtype === "Table") {
						allowed_fields.push({
							label: field_label_map[d.fieldname],
							value: d.fieldname,
							fieldtype: "Table",
							options: d.options,
						});
					} else if (
						!exclude_field_types.includes(d.fieldtype) &&
						!exclude_fields.includes(d.fieldname) &&
						!d.hidden
					) {
						allowed_fields.push({
							label: field_label_map[d.fieldname],
							value: d.fieldname,
							fieldtype: d.fieldtype,
							options: d.options || "",
						});
					}
				});

				show_dialog(frm, allowed_fields);
			});
		});
	},
});

var show_dialog = function (frm, allowed_fields) {
	var d = new frappe.ui.Dialog({
		title: __("Update Property"),
		fields: [
			{
				fieldname: "property",
				label: __("Select Property"),
				fieldtype: "Autocomplete",
				options: allowed_fields,
				reqd: 1,
			},
			{
				fieldname: "current",
				fieldtype: "Data",
				label: __("Current"),
				read_only: 1,
			},
			{ fieldname: "new_value", fieldtype: "Data", label: __("New") },
		],
		primary_action_label: __("Add to Details"),
		primary_action: () => {
			d.get_primary_btn().attr("disabled", true);
			if (d.data) {
				d.data.new = d.get_values().new_value;
				add_to_details(frm, d);
			}
		},
	});

	d.fields_dict["property"].df.onchange = () => {
		let selected = d.fields_dict["property"].get_value();
		if (!selected) return;

		let fielddef = (allowed_fields || []).find((f) => f.value === selected);
		if (!fielddef) return;

		d.data.fieldname = fielddef.value;
		d.data.property = fielddef.label;

		if (fielddef.fieldtype === "Table") {
			d.hide();
			show_child_table_dialog(frm, fielddef);
			return;
		}

		frappe.call({
			method: "hrms.hr.utils.get_employee_field_property",
			args: { employee: frm.doc.employee, fieldname: selected },
			callback: function (r) {
				if (r.message) {
					d.data.current = r.message.value;
					d.set_value("current", r.message.value);

					render_dynamic_field(d, r.message.datatype, r.message.options, selected);
					d.get_primary_btn().attr("disabled", false);
				}
			},
		});
	};

	d.get_primary_btn().attr("disabled", true);
	d.data = {};
	d.show();
};

var render_dynamic_field = function (d, fieldtype, options, fieldname) {
	d.data.new = null;
	var dynamic_field = frappe.ui.form.make_control({
		df: {
			fieldtype: fieldtype,
			fieldname: fieldname,
			options: options || "",
			label: __("New"),
		},
		parent: d.fields_dict.new_value.wrapper,
		only_input: false,
	});
	dynamic_field.make_input();
	d.replace_field("new_value", dynamic_field.df);
};

var add_to_details = function (frm, d) {
	let data = d.data;
	if (data.fieldname) {
		if (validate_duplicate(frm, "update_details", data.fieldname)) {
			frappe.show_alert({
				message: __("Property already added"),
				indicator: "orange",
			});
			return false;
		}
		if (data.current == data.new) {
			frappe.show_alert({
				message: __("Nothing to change"),
				indicator: "orange",
			});
			d.get_primary_btn().attr("disabled", false);
			return false;
		}

		frm.add_child("update_details", {
			fieldname: data.fieldname,
			property: data.property,
			current: data.current,
			new: data.new,
		});
		frm.refresh_field("update_details");

		frm.fields_dict.update_details.grid.wrapper.find(".grid-add-row").hide();

		frappe.show_alert({ message: __("Added to details"), indicator: "green" });

		d.hide();
		d.data = {};
	} else {
		frappe.show_alert({ message: __("Value missing"), indicator: "red" });
	}
};

var validate_duplicate = function (frm, table, fieldname) {
	return frm.doc[table].some((detail) => detail.fieldname === fieldname);
};

var show_child_table_dialog = function (frm, fielddef) {
	var d = new frappe.ui.Dialog({
		title: __("Update Child Table - " + fielddef.label),
		fields: [
			{
				fieldname: "action",
				label: __("Action"),
				fieldtype: "Select",
				options: ["Add Row", "Update Row", "Delete Row"],
				reqd: 1,
			},
			{
				fieldname: "row_data",
				label: __("Row Data (JSON)"),
				fieldtype: "Code",
				options: "json",
				depends_on: "eval:doc.action!='Delete Row'",
			},
		],
		primary_action_label: __("Add to Details"),
		primary_action: () => {
			const values = d.get_values();
			if (!values.action) {
				frappe.msgprint(__("Please select an action."));
				return;
			}
			frm.add_child("update_details", {
				fieldname: fielddef.value,
				property: fielddef.label,
				current: "",
				new: JSON.stringify(values),
			});
			frm.refresh_field("update_details");
			frappe.show_alert({
				message: __("Child Table Change Added"),
				indicator: "green",
			});
			d.hide();
		},
	});
	d.show();
};
