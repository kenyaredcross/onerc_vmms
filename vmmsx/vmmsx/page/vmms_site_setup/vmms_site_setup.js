// Copyright (c) 2026, Nigel and contributors
// For license information, please see license.txt

// Site Setup: the VMMS-Kenya setup scripts as a Desk page, for a site with no
// shell (Frappe Cloud). Temporary: see steps.py.

const SITE_SETUP = "vmmsx.vmmsx.page.vmms_site_setup.vmms_site_setup";

frappe.pages["vmms-site-setup"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Site Setup"),
		single_column: true,
	});
	wrapper.site_setup = new VmmsSiteSetup(page);
};

frappe.pages["vmms-site-setup"].on_page_show = function (wrapper) {
	wrapper.site_setup && wrapper.site_setup.refresh();
};

class VmmsSiteSetup {
	constructor(page) {
		this.page = page;
		this.timer = null;
		this.open = new Set();
		this.$body = $(`
			<div class="vmms-site-setup" style="max-width: 980px; margin: 0 auto; padding-bottom: 48px;">
				<p class="text-muted" style="margin: 4px 0 20px;">
					${__(
						"Set up this site in order, top to bottom. Check shows what a step would change and changes nothing. Run makes the change. Every step can be run again: it only adds what is missing."
					)}
				</p>
				<div class="setup-settings frappe-card" style="padding: 20px; margin-bottom: 24px;"></div>
				<h5 style="margin: 0 0 12px;">${__("Steps")}</h5>
				<div class="setup-steps"></div>
			</div>
		`).appendTo(page.main);

		this.make_form();
		page.set_primary_action(__("Save settings"), () =>
			this.save().then(() => frappe.show_alert({ message: __("Saved"), indicator: "green" }))
		);
		page.set_secondary_action(__("Refresh"), () => this.refresh());
		this.refresh();
	}

	make_form() {
		this.form = new frappe.ui.FieldGroup({
			parent: this.$body.find(".setup-settings"),
			fields: [
				{
					fieldtype: "HTML",
					options: `<h5 style="margin-top:0">${__(
						"Settings the steps read"
					)}</h5><p class="text-muted small">${__(
						"Saved on this site. Fill in what a step needs before you run it."
					)}</p>`,
				},
				{ fieldtype: "Section Break", label: __("Society") },
				{ fieldname: "society_name", fieldtype: "Data", label: __("Society name") },
				{ fieldname: "society_short_name", fieldtype: "Data", label: __("Short name") },
				{
					fieldname: "society_country",
					fieldtype: "Link",
					options: "Country",
					label: __("Country"),
				},
				{ fieldtype: "Column Break" },
				{ fieldname: "society_language", fieldtype: "Data", label: __("Language") },
				{
					fieldname: "society_logo",
					fieldtype: "Attach Image",
					label: __("Logo"),
					description: __("Empty uses the Kenya Red Cross logo shipped with the app."),
				},
				{ fieldtype: "Section Break", label: __("Roles") },
				{
					fieldname: "nsd_emails",
					fieldtype: "Small Text",
					label: __("NSD Coordinators"),
					description: __(
						"Email addresses of existing users to make NSD Coordinator, one per line. Can be left empty."
					),
				},
				{ fieldtype: "Section Break", label: __("County map") },
				{
					fieldname: "boundary_credit",
					fieldtype: "Data",
					label: __("Source line under the maps"),
				},
				{ fieldtype: "Section Break", label: __("Payments (M-Pesa)") },
				{
					fieldname: "mpesa_environment",
					fieldtype: "Select",
					label: __("Environment"),
					options: "Sandbox\nProduction",
				},
				{
					fieldname: "mpesa_shortcode",
					fieldtype: "Data",
					label: __("Shortcode (paybill or till)"),
				},
				{
					fieldname: "mpesa_callback_base_url",
					fieldtype: "Data",
					label: __("Callback address"),
					description: __(
						"This site's public https address. Safaricom sends payment results here."
					),
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "mpesa_initiator_name",
					fieldtype: "Data",
					label: __("Initiator name"),
					description: __("For looking up receipts. Can be left empty."),
				},
				{ fieldname: "currency", fieldtype: "Data", label: __("Currency") },
				{
					fieldtype: "HTML",
					options: `<p class="text-muted small">${__(
						"The consumer key, consumer secret, passkey and security credential are typed into {0}, never on this page.",
						[
							`<a href="/app/onerc-payment-settings">${__(
								"OneRC Payment Settings"
							)}</a>`,
						]
					)}</p>`,
				},
				{ fieldtype: "Section Break", label: __("Accounting") },
				{
					fieldname: "accounting_company",
					fieldtype: "Link",
					options: "Company",
					label: __("Company"),
					description: __("Empty means the default company."),
				},
				{
					fieldname: "mpesa_account",
					fieldtype: "Data",
					label: __("M-Pesa bank account"),
					description: __("An existing account's name, or empty to create “M-Pesa”."),
				},
				{
					fieldname: "income_account",
					fieldtype: "Data",
					label: __("Membership income account"),
					description: __(
						"An existing account's name, or empty to create “Membership Fees”."
					),
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "posting_starts_on",
					fieldtype: "Date",
					label: __("Post fees paid from"),
					description: __(
						"Empty keeps the date already set, or today if there is none."
					),
				},
				{
					fieldname: "posting_enabled",
					fieldtype: "Check",
					label: __("Switch posting on"),
					description: __(
						"Off, fees are kept and posted by the daily job once it is switched on."
					),
				},
				{ fieldtype: "Section Break", label: __("Numbering") },
				{
					fieldname: "old_volunteer_counter",
					fieldtype: "Int",
					label: __("Old site's last volunteer number"),
					description: __("Empty keeps 31709, read from the old site on 3 Nov 2026."),
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "old_series",
					fieldtype: "Small Text",
					label: __("Old member and membership counters"),
					description: __(
						"One per line, such as VM-MEM-2026-=1500. Empty keeps the counters read on 3 Nov 2026."
					),
				},
			],
		});
		this.form.make();
	}

	values() {
		return this.form.get_values(true) || {};
	}

	save() {
		return frappe.xcall(`${SITE_SETUP}.save_settings`, { values: this.values() });
	}

	refresh() {
		return frappe.xcall(`${SITE_SETUP}.state`).then((state) => {
			if (!this.loaded) {
				this.form.set_values(state.settings);
				this.loaded = true;
			}
			this.render(state);
			clearTimeout(this.timer);
			if (state.running) this.timer = setTimeout(() => this.refresh(), 3000);
		});
	}

	start(step, apply) {
		const go = () =>
			this.save()
				.then(() =>
					frappe.xcall(`${SITE_SETUP}.start`, { step: step.key, apply: apply ? 1 : 0 })
				)
				.then((state) => {
					this.open.add(step.key);
					this.render(state);
					clearTimeout(this.timer);
					this.timer = setTimeout(() => this.refresh(), 2000);
				});
		if (!apply) return go();
		frappe.confirm(
			__("Run {0} on this site? It makes the changes a Check reports.", [
				`<b>${frappe.utils.escape_html(step.title)}</b>`,
			]),
			go
		);
	}

	render(state) {
		const $steps = this.$body.find(".setup-steps").empty();
		state.steps.forEach((step, index) => {
			const last = state.results[step.key];
			const busy = Boolean(state.running);
			const $card = $(`
				<div class="frappe-card" style="padding: 16px 20px; margin-bottom: 12px;">
					<div style="display:flex; gap:16px; align-items:flex-start; justify-content:space-between; flex-wrap:wrap;">
						<div style="min-width:0; flex:1 1 420px;">
							<div style="font-weight:600;">${index + 1}. ${frappe.utils.escape_html(step.title)}</div>
							<div class="text-muted small" style="margin-top:4px;">${frappe.utils.escape_html(
								step.summary
							)}</div>
							<div class="setup-status small" style="margin-top:8px;">${this.status(last)}</div>
						</div>
						<div class="setup-actions" style="display:flex; gap:8px; flex:none;"></div>
					</div>
					<div class="setup-result" style="margin-top:12px; display:none;"></div>
				</div>
			`).appendTo($steps);

			const $actions = $card.find(".setup-actions");
			$(`<button class="btn btn-default btn-sm">${__("Check")}</button>`)
				.prop("disabled", busy)
				.on("click", () => this.start(step, false))
				.appendTo($actions);
			if (!step.check_only) {
				$(`<button class="btn btn-primary btn-sm">${__("Run")}</button>`)
					.prop("disabled", busy)
					.on("click", () => this.start(step, true))
					.appendTo($actions);
			}

			if (last && last.status !== "running") {
				const $result = $card.find(".setup-result").html(this.result(last));
				const $toggle = $(`<a class="small" style="cursor:pointer;"></a>`);
				const show = (open) => {
					$result.toggle(open);
					$toggle.text(open ? __("Hide result") : __("Show result"));
				};
				$toggle.on("click", () => {
					const open = !this.open.has(step.key);
					open ? this.open.add(step.key) : this.open.delete(step.key);
					show(open);
				});
				$card.find(".setup-status").append(" · ").append($toggle);
				show(this.open.has(step.key));
			}
		});
	}

	status(last) {
		if (!last) return `<span class="text-muted">${__("Not run yet")}</span>`;
		const when = last.at ? frappe.datetime.str_to_user(last.at) : "";
		const who = last.by ? frappe.utils.escape_html(last.by) : "";
		if (last.status === "running") {
			return `<span class="indicator-pill blue">${
				last.mode === "run" ? __("Running…") : __("Checking…")
			}</span>`;
		}
		if (last.status === "failed") {
			return `<span class="indicator-pill red">${__(
				"Failed"
			)}</span> <span class="text-muted">${when} · ${who}</span>`;
		}
		const label = last.mode === "run" ? __("Done") : __("Checked");
		const problems = (last.result && (last.result.problems || last.result.blocking)) || [];
		const tone = problems.length ? "orange" : "green";
		return `<span class="indicator-pill ${tone}">${label}</span> <span class="text-muted">${when} · ${who}</span>`;
	}

	result(last) {
		if (last.status === "failed") {
			return `<div class="alert alert-danger" style="margin:0;">${frappe.utils.escape_html(
				last.error || __("Failed")
			)}</div>`;
		}
		const result = last.result || {};
		const list = (title, rows, tone) =>
			rows && rows.length
				? `<div style="margin-bottom:10px;"><div class="small" style="font-weight:600; color:var(--${tone}-600, inherit);">${title}</div><ul class="small" style="margin:4px 0 0 18px; padding:0;">${rows
						.map((row) => `<li>${frappe.utils.escape_html(row)}</li>`)
						.join("")}</ul></div>`
				: "";
		if ("blocking" in result) {
			return (
				list(__("Must be fixed"), result.blocking, "red") +
				list(__("Before real people use the site"), result.before_go_live, "orange") +
				list(__("Passed"), result.ok, "green")
			);
		}
		const problems = result.problems || (result.after && result.after.problems) || [];
		return (
			list(__("Still to do"), problems, "orange") +
			`<pre class="small" style="max-height:420px; overflow:auto; margin:0; white-space:pre-wrap;">${frappe.utils.escape_html(
				JSON.stringify(result, null, 2)
			)}</pre>`
		);
	}
}
