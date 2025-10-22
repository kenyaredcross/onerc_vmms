// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Onboarding", {
  refresh(frm) {},

  employee_onboarding_template: function (frm) {
    if (frm.doc.employee_onboarding_template) {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "Employee Onboarding Template",
          name: frm.doc.employee_onboarding_template,
        },
        callback: function (r) {
          if (r.message) {
            let template = r.message;

            frm.clear_table("activities");

            const skipped_fields = [
              "name",
              "parent",
              "parentfield",
              "parenttype",
              "idx",
              "creation",
              "modified",
              "modified_by",
              "owner",
              "docstatus",
            ];

            (template.activities || []).forEach((row) => {
              let child = frm.add_child("activities");
              for (let field in row) {
                if (!skipped_fields.includes(field)) {
                  child[field] = row[field];
                }
              }
            });

            frm.refresh_field("activities");
          }
        },
      });
    } else {
      frm.clear_table("activities");
      frm.refresh_field("activities");
    }
  },
});
