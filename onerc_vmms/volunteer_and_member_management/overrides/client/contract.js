frappe.ui.form.on("Contract", {
  refresh(frm) {
    frm.events.set_task_filter(frm);
    frm.events.set_party_user(frm);
  },

  project(frm) {
    frm.events.set_task_filter(frm);

    if (!frm.doc.project) {
      frm.set_value("task", null);
    }
  },

  task(frm) {
    if (frm.doc.task && !frm.doc.project) {
      frappe.db.get_value("Task", frm.doc.task, "project", (r) => {
        if (r && r.project) {
          frm.set_value("project", r.project);
        }
      });
    }
  },

  party_name(frm) {
    frm.events.set_party_user(frm);
  },

  personnel_deployment_assignment(frm) {
    if (frm.doc.personnel_deployment_assignment) {
      frappe.db.get_value(
        "Personnel Deployment Request",
        frm.doc.personnel_deployment_assignment,
        ["project", "task"],
        (r) => {
          if (r) {
            if (r.project) {
              frm.set_value("project", r.project);
            }
            if (r.task) {
              frm.set_value("task", r.task);
            }
            if (r.task) {
              frm.set_value(
                "personnel_deployment_request",
                r.personnel_deployment_request
              );
            }
          }
        }
      );
    }
  },

  set_task_filter(frm) {
    frm.set_query("task", () => {
      const filters = {};
      if (frm.doc.project) {
        filters.project = frm.doc.project;
      }
      return { filters };
    });
  },

  set_party_user(frm) {
    if (frm.doc.party_name && frm.doc.party_type === "Employee") {
      frappe.db.get_value("Employee", frm.doc.party_name, "user_id", (r) => {
        if (r && r.user_id) {
          frm.set_value("party_user", r.user_id);
        }
      });
    }
  },
});
