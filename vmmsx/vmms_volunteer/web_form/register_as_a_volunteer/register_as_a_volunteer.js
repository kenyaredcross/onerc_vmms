// Copyright (c) 2026, Nigel and contributors
// For license information, please see license.txt

/* The two-doctype write is a server-side hook on the document, not a client
 * script: see vmmsx/registration/services/intake.py. What lives here is a
 * guided, cascading alternative to typing a Geo Node by hand — Home Area and
 * Serving Branch both are one, and most applicants know the name of the place
 * they mean far better than its opaque docname.
 *
 * The same shape as `vmms_volunteer_application.js`'s picker, adjusted for a
 * Web Form's field API (`frappe.web_form.get_field`) rather than a desk
 * form's (`frm.get_field`) — the two are otherwise the same
 * `frappe.ui.FieldGroup` control interface, so the cascading logic itself does
 * not change. Kept as its own copy rather than a shared import: a public
 * registration page and a desk client script load differently, and a small
 * duplicated helper is simpler than a new cross-context asset to get right.
 *
 * ONE RULE THIS FILE CANNOT BREAK: nothing in it, code or comment, may contain
 * a full stop followed by two underscores. A Web Form's client script is not
 * served as a static asset — `web_form.py::add_custom_context_and_script` reads
 * this file and runs it through `frappe.render_template`, whose sandbox guard
 * tests for exactly that character sequence anywhere in the source. So a
 * dunder-prefixed property on an object is not a runtime problem in the
 * browser: it fails while *rendering the page*, and the whole registration form
 * becomes a 417 "Illegal template" that names no file. The picker's state below
 * is namespaced `vmmsx_` instead, which is what the underscores were doing
 * anyway. Translation calls are unaffected, because the guard wants the stop in
 * front.
 */
frappe.ready(function () {
	const vmmsx_geo_picker = {
		MAX_DEPTH: 8,

		setup() {
			vmmsx_geo_picker.add_button("geo_node", __("Choose Serving Branch"));
		},

		add_button(fieldname, label) {
			const field = frappe.web_form.get_field(fieldname);

			if (!field || field.$wrapper.find(".vmmsx-geo-picker-btn").length) {
				return;
			}

			const $btn = $(
				`<button type="button" class="btn btn-xs btn-default vmmsx-geo-picker-btn" style="margin-top: 4px;">${label}</button>`
			);
			$btn.on("click", () => vmmsx_geo_picker.open(fieldname, label));
			field.$wrapper.append($btn);
		},

		open(fieldname, title) {
			const fields = [];

			for (let depth = 0; depth < vmmsx_geo_picker.MAX_DEPTH; depth++) {
				fields.push({
					fieldname: `level_${depth}`,
					fieldtype: "Select",
					label: __("Level {0}", [depth + 1]),
					options: [],
					hidden: 1,
				});
			}

			const dialog = new frappe.ui.Dialog({
				title,
				fields,
				primary_action_label: __("Use This Location"),
				primary_action: () => {
					if (!dialog.vmmsx_chosen) {
						frappe.msgprint(__("Choose a location first."));
						return;
					}

					frappe.web_form.set_value(fieldname, dialog.vmmsx_chosen);
					dialog.hide();
				},
			});

			dialog.vmmsx_nodes = {};
			dialog.vmmsx_chosen = null;

			for (let depth = 0; depth < vmmsx_geo_picker.MAX_DEPTH; depth++) {
				dialog.get_field(`level_${depth}`).toggle_display(false);
			}

			dialog.show();

			const current = frappe.web_form.get_value(fieldname);

			if (current) {
				vmmsx_geo_picker.restore(dialog, current);
			} else {
				vmmsx_geo_picker.load(dialog, null, 0);
			}
		},

		load(dialog, parent, depth) {
			if (depth >= vmmsx_geo_picker.MAX_DEPTH) {
				return Promise.resolve();
			}

			return frappe.xcall("vmmsx.api.geo.browse", { parent }).then((result) => {
				if (!result.nodes.length) {
					return;
				}

				dialog.vmmsx_nodes[depth] = result.nodes;

				const field = dialog.get_field(`level_${depth}`);
				field.df.label = result.nodes[0].level_name;
				field.df.options = ["", ...result.nodes.map((node) => node.label)];
				field.refresh();
				field.toggle_display(true);

				field.$input.off("change.vmmsx").on("change.vmmsx", () => {
					vmmsx_geo_picker.on_change(dialog, depth);
				});
			});
		},

		on_change(dialog, depth) {
			const label = dialog.get_value(`level_${depth}`);
			const nodes = dialog.vmmsx_nodes[depth] || [];
			const node = nodes.find((candidate) => candidate.label === label);

			for (let deeper = depth + 1; deeper < vmmsx_geo_picker.MAX_DEPTH; deeper++) {
				const field = dialog.get_field(`level_${deeper}`);
				field.set_value("");
				field.toggle_display(false);
				delete dialog.vmmsx_nodes[deeper];
			}

			dialog.vmmsx_chosen = node ? node.name : null;

			if (node) {
				vmmsx_geo_picker.load(dialog, node.name, depth + 1);
			}
		},

		async restore(dialog, node) {
			let chain;

			try {
				({ chain } = await frappe.xcall("vmmsx.api.geo.path", { node }));
			} catch {
				vmmsx_geo_picker.load(dialog, null, 0);
				return;
			}

			for (let depth = 0; depth < chain.length; depth++) {
				const parent = depth === 0 ? null : chain[depth - 1].name;
				await vmmsx_geo_picker.load(dialog, parent, depth);

				const field = dialog.get_field(`level_${depth}`);
				field.set_value(chain[depth].label);
				dialog.vmmsx_chosen = chain[depth].name;
			}

			await vmmsx_geo_picker.load(dialog, node, chain.length);
		},
	};

	vmmsx_geo_picker.setup();

	/* Cross-registration: somebody who already has a Red Profile — a member
	 * registering as a volunteer too — is not re-asked who they are. Prefilled
	 * fields are locked, because typing over them would change nothing anyway:
	 * vmmsx/registration/services/intake.py never overwrites what core already
	 * knows. A field core does not have yet (commonly phone or date of birth)
	 * is left blank and editable, exactly as a first-time registrant sees it.
	 */
	frappe.xcall("vmmsx.api.volunteer.my_registration_prefill").then((prefill) => {
		if (!prefill) {
			return;
		}

		Object.keys(prefill).forEach((fieldname) => {
			const value = prefill[fieldname];

			if (!value) {
				return;
			}

			const field = frappe.web_form.get_field(fieldname);

			if (!field) {
				return;
			}

			frappe.web_form.set_value(fieldname, value);
			field.df.read_only = 1;
			field.refresh();
		});
	});
});
