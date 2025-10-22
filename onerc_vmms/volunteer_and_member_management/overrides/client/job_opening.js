frappe.ui.form.on("Job Opening", {
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
  },

  designation: function (frm) {
    if (frm.doc.designation) {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "Designation",
          name: frm.doc.designation,
        },
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

        frappe.show_alert(__("Fields copied from Job Opening Template"));
      },
    });
  },
});

frappe.ui.form.on("Job Application Screening Questions", {
  screening_questions_add: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);

    let table = frm.doc.screening_questions || [];

    let last_seq = 0;
    if (table.length > 1) {
      table.slice(0, -1).forEach((r) => {
        if (r.question_id && r.question_id.startsWith("Q")) {
          let num = parseInt(r.question_id.replace("Q", ""));
          if (!isNaN(num) && num > last_seq) last_seq = num;
        }
      });
    }

    row.question_id = "Q" + (last_seq + 1);

    frm.refresh_field("screening_questions");
  },
});
