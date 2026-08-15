// Copyright (c) 2026, Nigel and contributors
// For license information, please see license.txt

/* The coordinator's working surface for one application.
 *
 * Two jobs, neither of them approval logic — there are no desk workflow
 * buttons on this doctype, and there never will be; see vmmsx/api/approvals.py.
 *
 * 1. **The identity card.** Red Profile is a Link on this record and nothing
 *    else about the applicant is stored here, so a coordinator otherwise sees a
 *    docname and has to click through to find out who they are looking at.
 *    `applicant_identity` renders the resolved name/email/phone instead, read
 *    live through `vmmsx.api.volunteer.get_decision` and stored nowhere.
 *
 * 2. **The cascading geo picker**, on Home Area and Serving Branch alike. Both
 *    are ordinary Link fields — typing still works — and this adds a guided
 *    "walk the tree" alternative next to each, because a coordinator entering a
 *    paper application often knows "the ward called Mweiga" and not its opaque
 *    Geo Node name. Every level shown comes from `vmmsx.api.geo.browse`, which
 *    reads onerc_core's own adapter; nothing here assumes a level name or a
 *    tree depth.
 */
const vmmsx_application = {
	MAX_GEO_DEPTH: 8,

	/* --- the identity card ------------------------------------------------ */

	render_identity(frm) {
		const field = frm.get_field("applicant_identity");

		if (!field) {
			return;
		}

		field.$wrapper.html(vmmsx_application.muted(__("Reading...")));

		frappe
			.xcall("vmmsx.api.volunteer.get_decision", { name: frm.doc.name })
			.then((decision) => {
				field.$wrapper.html(vmmsx_application.identity_html(decision));
			})
			.catch(() => {
				field.$wrapper.html(
					vmmsx_application.muted(__("This applicant's details could not be read just now."))
				);
			});
	},

	identity_html(decision) {
		const rows = [
			[__("Red Profile"), vmmsx_application.profile_link(decision.red_profile)],
			[__("Email"), decision.email],
			[__("Phone"), decision.phone],
		];

		const cells = rows
			.map(
				([label, value]) => `
					<div class="vmms-pair">
						<div class="vmms-pair-label">${label}</div>
						<div class="vmms-pair-value">${
							value
								? vmmsx_application.maybe_markup(value)
								: `<span class="text-muted">${__("Not recorded")}</span>`
						}</div>
					</div>
				`
			)
			.join("");

		return `
			<div class="vmms-card-title">${vmmsx_application.text(decision.full_name)}</div>
			<div class="vmms-pairs">${cells}</div>
		`;
	},

	text(value) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
	},

	profile_link(red_profile) {
		if (!red_profile) {
			return "";
		}

		return `<a href="/app/red-profile/${encodeURIComponent(red_profile)}">${vmmsx_application.text(
			red_profile
		)}</a>`;
	},

	maybe_markup(value) {
		return String(value).startsWith("<a ") ? value : vmmsx_application.text(value);
	},

	muted(message) {
		return `<div class="text-muted vmms-note">${message}</div>`;
	},

	/* --- the cascading geo picker ------------------------------------------ */

	setup_geo_pickers(frm) {
		vmmsx_application.add_picker_button(frm, "home_geo_node", __("Choose Home Area"));
		vmmsx_application.add_picker_button(frm, "geo_node", __("Choose Serving Branch"));
	},

	add_picker_button(frm, fieldname, label) {
		const field = frm.get_field(fieldname);

		if (!field || field.$wrapper.find(".vmmsx-geo-picker-btn").length) {
			return;
		}

		const $btn = $(
			`<button type="button" class="btn btn-xs btn-default vmmsx-geo-picker-btn" style="margin-top: 4px;">${label}</button>`
		);
		$btn.on("click", () => vmmsx_application.open_geo_picker(frm, fieldname, label));
		field.$wrapper.append($btn);
	},

	open_geo_picker(frm, fieldname, title) {
		const fields = [];

		for (let depth = 0; depth < vmmsx_application.MAX_GEO_DEPTH; depth++) {
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

				frm.set_value(fieldname, dialog.vmmsx_chosen);
				dialog.hide();
			},
		});

		dialog.vmmsx_nodes = {};
		dialog.vmmsx_chosen = null;

		for (let depth = 0; depth < vmmsx_application.MAX_GEO_DEPTH; depth++) {
			dialog.get_field(`level_${depth}`).toggle_display(false);
		}

		dialog.show();

		const current = frm.doc[fieldname];

		if (current) {
			vmmsx_application.restore_geo_path(dialog, current);
		} else {
			vmmsx_application.load_geo_level(dialog, null, 0);
		}
	},

	load_geo_level(dialog, parent, depth) {
		if (depth >= vmmsx_application.MAX_GEO_DEPTH) {
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
				vmmsx_application.on_geo_level_change(dialog, depth);
			});
		});
	},

	on_geo_level_change(dialog, depth) {
		const label = dialog.get_value(`level_${depth}`);
		const nodes = dialog.vmmsx_nodes[depth] || [];
		const node = nodes.find((candidate) => candidate.label === label);

		// A change here invalidates every level chosen below it.
		for (let deeper = depth + 1; deeper < vmmsx_application.MAX_GEO_DEPTH; deeper++) {
			const field = dialog.get_field(`level_${deeper}`);
			field.set_value("");
			field.toggle_display(false);
			delete dialog.vmmsx_nodes[deeper];
		}

		dialog.vmmsx_chosen = node ? node.name : null;

		if (node) {
			vmmsx_application.load_geo_level(dialog, node.name, depth + 1);
		}
	},

	async restore_geo_path(dialog, node) {
		let chain;

		try {
			({ chain } = await frappe.xcall("vmmsx.api.geo.path", { node }));
		} catch {
			// The stored value no longer resolves (deleted, or from a different
			// tree). Fall back to an empty picker rather than leaving the dialog
			// stuck on a spinner.
			vmmsx_application.load_geo_level(dialog, null, 0);
			return;
		}

		for (let depth = 0; depth < chain.length; depth++) {
			const parent = depth === 0 ? null : chain[depth - 1].name;
			await vmmsx_application.load_geo_level(dialog, parent, depth);

			const field = dialog.get_field(`level_${depth}`);
			field.set_value(chain[depth].label);
			dialog.vmmsx_chosen = chain[depth].name;
		}

		// The node itself may have children the applicant did not drill into;
		// offer the next level too, exactly as a fresh picker would.
		await vmmsx_application.load_geo_level(dialog, node, chain.length);
	},
};

frappe.ui.form.on("VMMS Volunteer Application", {
	refresh(frm) {
		vmmsx_application.setup_geo_pickers(frm);

		// A record being created has no applicant to read yet.
		if (frm.is_new()) {
			return;
		}

		vmmsx_application.render_identity(frm);
	},

	residency_type(frm) {
		// The desk form's own depends_on already shows and hides the right
		// fields; nothing else changes when the toggle flips.
		frm.refresh_field("home_geo_node");
		frm.refresh_field("country_of_residence");
		frm.refresh_field("residence_address");
	},
});
