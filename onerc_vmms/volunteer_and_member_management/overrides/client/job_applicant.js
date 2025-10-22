frappe.ui.form.on("Job Applicant", {
  refresh: function (frm) {
    if (frm.doc.status === "Accepted" && frm.doc.is_volunteer == 1) {
      frappe.db
        .get_value("Employee", { job_applicant: frm.doc.name }, "name")
        .then((r) => {
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
  },

  after_save: function (frm) {
    if (frm.doc.status === "Accepted" && frm.doc.is_volunteer == 1) {
      frappe.db
        .get_value("Employee", { job_applicant: frm.doc.name }, "name")
        .then((r) => {
          if (r && !r.message.name) {
            frappe.confirm(
              __(
                "Do you want to create a Personnel record for this volunteer?"
              ),
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
                  // profile_photo: "image",
                };

                same_fields.forEach((field) => {
                  if (frm.doc[field]) {
                    new_employee[field] = frm.doc[field];
                  }
                });

                Object.entries(field_mapping).forEach(
                  ([applicant_field, employee_field]) => {
                    if (frm.doc[applicant_field]) {
                      new_employee[employee_field] = frm.doc[applicant_field];
                    }
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
                    title: __("Employee Created"),
                    message: __("Employee {0} has been created", [doc.name]),
                    indicator: "green",
                  });
                  frappe.set_route("Form", "Employee", doc.name);
                });
              },
              () => {}
            );
          }
        });
    }
  },
});
