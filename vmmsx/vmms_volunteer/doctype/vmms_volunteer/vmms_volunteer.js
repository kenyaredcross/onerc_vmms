// Copyright (c) 2026, Nigel and contributors
// For license information, please see license.txt

/* The volunteer page as one working surface: the complete coordinator's view.
 *
 * This is the app's first client-side script, and it is an in-repo file rather
 * than a desk Client Script record on purpose: a Client Script is a row in one
 * site's database, invisible to review, absent from every other site, and gone
 * the day somebody deletes it. This ships, migrates and diffs with the code it
 * belongs to.
 *
 * **Everything painted below is read at display time and stored nowhere.** The
 * volunteer record holds a Red Profile link, what it can currently do, and its
 * own derived state. It holds no identity at all — no name, no email, not even
 * a `fetch_from`, which would be a stored copy wearing a different hat. So the
 * page asks the server who this person is each time it opens, and renders the
 * answer into HTML fields that no column backs. Correct somebody's phone number
 * on their Red Profile and every volunteer page in the society is correct on
 * next open, because there is nothing anywhere to go and update.
 *
 * **One call, not six.** `get_dossier` returns every block below, resolved as at
 * one instant. Six calls would have been six instants, and a page that showed a
 * certification as current beside a deployability indicator computed a second
 * later, after midnight passed, would be wrong in the way that is hardest to
 * notice. The endpoint's docstring states the same argument from the other side.
 *
 * The blocks, and the question each answers:
 *
 *   identity_card             who is this person, and where do they live and serve
 *   deployability_indicator   may they be sent, right now
 *   certifications_held       what do they hold, and has any of it lapsed
 *   deployment_history        what have they been sent on
 *   time_served               what have they given
 *   verification_outcome      how were they verified
 *   declared_at_application   what did they say on the day, which is not what
 *                             they can do now
 *
 * What is *not* an HTML block here is as deliberate as what is. Skills,
 * languages and availability are real editable fields on the record, painted by
 * Frappe's own grid, because they are the volunteer's current truth and a
 * coordinator has to be able to change them. A read-only rendering of them
 * would have been a nicer-looking screen and a worse one.
 *
 * The heading is overridden here too. `title_field` is `red_profile`, and
 * Frappe's toolbar reads that field's raw value, so the page heading reads
 * RP-00042 — the least readable thing on the screen. The alternative was a
 * virtual title field holding the name, and it was rejected: it would put an
 * identity value on this doctype's meta, which is precisely what this module
 * refuses, and Frappe's list view adds `title_field` to its query, so a computed
 * one risks selecting a column that does not exist. `refresh_header()` runs
 * before the `refresh` trigger (frappe/public/js/frappe/form/form.js), so
 * setting the title here wins, and it wins with a value that was never stored.
 */

/* Scoped to this script, not hung on `window`. Frappe evaluates a doctype's
 * form script with `new Function(...)()` (frappe/public/js/frappe/form/
 * script_manager.js), so a top-level const lives in that call's scope and the
 * handler below closes over it. Nothing is added to the global namespace, and
 * there is no name for another app to collide with.
 */
const vmmsx_volunteer = {
	/** Which HTML block each part of the dossier is painted into.
	 *
	 * A table rather than seven calls written out, so adding a block is adding a
	 * row and a renderer: the loading state, the paint and the failure message
	 * are then the same for every block by construction rather than by whoever
	 * copied the last one carefully.
	 */
	blocks: [
		["identity_card", "identity_html"],
		["deployability_indicator", "deployability_html"],
		["certifications_held", "certifications_html"],
		["deployment_history", "deployments_html"],
		["time_served", "time_html"],
		["verification_outcome", "verification_html"],
		["declared_at_application", "declared_html"],
	],

	/** The whole page, from one read. */
	render(frm) {
		const painted = vmmsx_volunteer.blocks
			.map(([fieldname, renderer]) => [frm.get_field(fieldname), renderer])
			.filter(([field]) => field);

		if (!painted.length) {
			return;
		}

		painted.forEach(([field]) => field.$wrapper.html(vmmsx_volunteer.loading()));

		frappe
			.xcall("vmmsx.api.volunteer.get_dossier", { name: frm.doc.name })
			.then((dossier) => {
				painted.forEach(([field, renderer]) => {
					field.$wrapper.html(vmmsx_volunteer[renderer](dossier));
				});

				vmmsx_volunteer.set_heading(frm, (dossier.identity || {}).full_name);
				vmmsx_volunteer.actions(frm, dossier);
			})
			.catch(() => {
				painted.forEach(([field]) =>
					field.$wrapper.html(
						vmmsx_volunteer.muted(__("This volunteer's record could not be read just now."))
					)
				);
			});
	},

	/* --- the heading ---------------------------------------------------- */

	/** The person's name where the docname was, with the docname kept beneath it.
	 *
	 * The name is the one the DTO just read from Red Profile. Nothing is written,
	 * and reloading the page asks again.
	 */
	set_heading(frm, full_name) {
		if (!full_name) {
			return;
		}

		frm.page.set_title(full_name);
		// The opaque docname stays visible and copyable: it is what an audit
		// trail, a report and a support conversation refer to.
		frm.page.set_title_sub(frm.doc.name);
		frappe.utils.set_title(`${full_name} - ${frm.doc.name}`);
	},

	/* --- the acts -------------------------------------------------------- */

	/** What may be done to this volunteer's standing, from where it stands now.
	 *
	 * A table rather than a chain of comparisons, the same shape
	 * `announce._URGENCY` and `member.approval._BEGIN` use on the Python side.
	 * **Branching on `status` is allowed and branching on a stage label is not**:
	 * a stage is a society's word and this is a closed Select this app owns, four
	 * values, the same category as `states.py`. A status this file does not know
	 * offers nothing, which is the direction a dispatch table should fail in.
	 *
	 * Every verb is idempotent server-side, so a double-click costs a round trip
	 * and changes nothing twice.
	 */
	verbs: {
		Prospective: ["suspend", "exit"],
		Active: ["suspend", "exit"],
		Suspended: ["reinstate", "exit"],
		Exited: ["reinstate"],
	},

	/** One definition per verb: what it is called, what it asks for, what it calls.
	 *
	 * `reason` is required on all three. The service only adds a comment when one
	 * is given, which makes the reason the *entire* record of why somebody's
	 * standing changed — the status field itself remembers nothing about who
	 * decided or why. Asking for it here is what stops that trail having holes in
	 * it, and the endpoint still accepts None for callers that are not a person.
	 */
	acts: {
		suspend: {
			label: __("Suspend"),
			method: "vmmsx.api.volunteer.suspend_volunteer",
			fields: [
				{
					fieldname: "reason",
					fieldtype: "Small Text",
					label: __("Why is this volunteer being suspended?"),
					reqd: 1,
				},
			],
		},
		reinstate: {
			label: __("Reinstate"),
			method: "vmmsx.api.volunteer.reinstate_volunteer",
			fields: [
				{
					fieldname: "reason",
					fieldtype: "Small Text",
					label: __("Why is this volunteer being reinstated?"),
					reqd: 1,
				},
			],
			// Said out loud because it surprises people: reinstating does not make
			// somebody Active, it hands the question back to their applications.
			note: __(
				"Standing returns to whatever this volunteer's applications support, which may be Prospective rather than Active."
			),
		},
		exit: {
			label: __("Record exit"),
			method: "vmmsx.api.volunteer.record_volunteer_exit",
			fields: [
				{
					fieldname: "on_date",
					fieldtype: "Date",
					label: __("Date they stopped volunteering"),
					// A function, resolved when the dialog opens rather than when
					// this file loads: a desk tab left open overnight would
					// otherwise default to yesterday.
					default: () => frappe.datetime.get_today(),
					reqd: 1,
				},
				{
					fieldname: "reason",
					fieldtype: "Small Text",
					label: __("Why are they leaving?"),
					reqd: 1,
				},
			],
		},
	},

	/** Draw the buttons this person may actually press.
	 *
	 * **`can_act` is the server's answer, not this file's.** It is
	 * `frappe.has_permission(..., "write")` — the same check the endpoint makes
	 * when the button is pressed — so no role name appears here and the desk
	 * cannot offer an act the server would refuse. A volunteer opening their own
	 * record through the holder bypass gets `false` and no buttons.
	 *
	 * Cleared first because `refresh` runs on every reload, and Frappe keeps
	 * custom buttons across one.
	 */
	actions(frm, dossier) {
		frm.clear_custom_buttons();

		if (!dossier.can_act) {
			return;
		}

		(vmmsx_volunteer.verbs[frm.doc.status] || []).forEach((verb) => {
			const act = vmmsx_volunteer.acts[verb];

			frm.add_custom_button(act.label, () => vmmsx_volunteer.ask(frm, act), __("Standing"));
		});
	},

	/** Ask for the act's arguments, then perform it and reload.
	 *
	 * `frm.reload_doc()` rather than repainting from the response: the verbs move
	 * derived state that other parts of this page read off the document, and one
	 * reload is the only way the whole form agrees with itself afterwards.
	 */
	ask(frm, act) {
		// The note is a field in the dialog rather than something set on it
		// afterwards: `prompt` returns before its dialog is reliably reachable,
		// and a declarative field cannot be missed by a timing change.
		// A `default` may be a function, resolved here so it is answered when the
		// dialog opens rather than when this file loaded.
		const asked = act.fields.map((field) =>
			typeof field.default === "function" ? { ...field, default: field.default() } : field
		);

		const fields = act.note
			? [{ fieldtype: "HTML", options: vmmsx_volunteer.muted(act.note) }, ...asked]
			: asked;

		frappe.prompt(
			fields,
			(values) => {
				frappe
					.xcall(act.method, { name: frm.doc.name, ...values })
					.then(() => frm.reload_doc())
					.catch(() => {
						// Frappe has already shown the server's message. Nothing is
						// reloaded, so the form still shows the state that failed to
						// move rather than a guess about where it ended up.
					});
			},
			act.label,
			act.label
		);
	},

	/* --- rendering ------------------------------------------------------ */

	identity_html(dossier) {
		const person = dossier.identity || {};
		const rows = [
			[__("Email"), person.email],
			[__("Phone"), person.phone],
			[__("Gender"), person.gender],
			[__("Date of Birth"), vmmsx_volunteer.date(person.date_of_birth)],
			[__("Preferred Language"), person.preferred_language],
			[__("Citizenship"), person.country_of_citizenship],
			[__("Residency"), person.residency_type],
			// Two Geo Nodes, two labels, and never the bare word "location".
			// Where somebody lives and where they serve are different questions,
			// and a coordinator who confuses them sends the right person to the
			// wrong branch.
			[__("Home Area"), person.home_geo_path],
			[__("Serving Branch"), person.geo_path],
			[__("Country of Residence"), person.country_of_residence],
			[__("Address Abroad"), person.residence_address],
		];

		return `
			<div class="vmms-card">
				<div class="vmms-card-media">${vmmsx_volunteer.photo(person)}</div>
				<div class="vmms-card-body">
					<div class="vmms-card-title">${vmmsx_volunteer.text(person.full_name)}</div>
					<div class="vmms-card-subtitle">
						${vmmsx_volunteer.profile_link(person.red_profile)}
					</div>
					${vmmsx_volunteer.definitions(rows.filter(([, value]) => value))}
				</div>
			</div>
			${vmmsx_volunteer.footnote(
				__(
					"Name, contact, gender, date of birth and Home Area are read from this person's Red Profile when the page opens. None of them is stored on the volunteer record."
				)
			)}
		`;
	},

	/** May this person be sent, right now. Derived; no flag backs it. */
	deployability_html(dossier) {
		const dto = dossier.deployability || {};
		const reasons = dto.reasons || [];
		// Frappe's own indicator pill, not a class this app would then have to
		// ship a stylesheet for. The desk already styles these, so the flag is
		// visible on every site without a bundle, and it looks like the rest of
		// the desk rather than like something bolted on.
		const state = vmmsx_volunteer.pill(
			dto.deployable ? "green" : "red",
			dto.deployable ? __("Deployable") : __("Not deployable")
		);

		const why = reasons.length
			? `<ul class="vmms-reasons">${reasons
					.map((reason) => `<li>${vmmsx_volunteer.text(reason)}</li>`)
					.join("")}</ul>`
			: "";

		return `
			${state}
			${why}
			${vmmsx_volunteer.footnote(
				__(
					"Worked out when this page opened, from this volunteer's status and the certifications they hold as at {0}. No field anywhere records it, so it cannot be stale and no job has to have run for it to be right.",
					[vmmsx_volunteer.date(dossier.as_of)]
				)
			)}
		`;
	},

	certifications_html(dossier) {
		const rows = dossier.certifications || [];

		if (!rows.length) {
			return vmmsx_volunteer.muted(__("No certifications are recorded for this volunteer."));
		}

		const cells = rows
			.map((row) => {
				// A lapse that blocks deployment is the one a coordinator has to
				// see from across the room; a lapse the society keeps only as a
				// record is a reminder. Both are read from the type's own
				// configuration, so which is which is a society's answer.
				const flag = !row.lapsed
					? vmmsx_volunteer.pill("green", __("Current"))
					: row.blocks_deployment
						? vmmsx_volunteer.pill("red", __("Lapsed, blocks deployment"))
						: vmmsx_volunteer.pill("orange", __("Lapsed"));

				return `
					<tr>
						<td>${vmmsx_volunteer.text(row.certification_type_name)}</td>
						<td>${vmmsx_volunteer.text(vmmsx_volunteer.date(row.completion_date))}</td>
						<td>${vmmsx_volunteer.text(
							vmmsx_volunteer.date(row.expiry_date) || __("Does not expire")
						)}</td>
						<td>${flag}</td>
					</tr>
				`;
			})
			.join("");

		return `
			<table class="table table-sm vmms-table">
				<thead>
					<tr>
						<th>${__("Certification")}</th>
						<th>${__("Completed")}</th>
						<th>${__("Expires")}</th>
						<th>${__("Status")}</th>
					</tr>
				</thead>
				<tbody>${cells}</tbody>
			</table>
			${vmmsx_volunteer.footnote(
				__(
					"Whether a certification has lapsed is a comparison against {0}, made when this page opened. There is no lapsed field on any record.",
					[vmmsx_volunteer.date(dossier.as_of)]
				)
			)}
		`;
	},

	deployments_html(dossier) {
		const rows = dossier.deployments || [];

		if (!rows.length) {
			return vmmsx_volunteer.muted(__("This volunteer has not been on a deployment."));
		}

		const cells = rows
			.map(
				(row) => `
					<tr>
						<td>${vmmsx_volunteer.deployment_link(row.deployment)}</td>
						<td>${vmmsx_volunteer.text(row.tor_name || row.terms_of_reference)}</td>
						<td>${vmmsx_volunteer.text(vmmsx_volunteer.date(row.start_date))}</td>
						<td>${vmmsx_volunteer.text(vmmsx_volunteer.date(row.end_date))}</td>
						<td>${vmmsx_volunteer.text(row.status)}</td>
						<td>${vmmsx_volunteer.text(vmmsx_volunteer.date(row.left_on))}</td>
					</tr>
				`
			)
			.join("");

		return `
			<table class="table table-sm vmms-table">
				<thead>
					<tr>
						<th>${__("Deployment")}</th>
						<th>${__("Terms of Reference")}</th>
						<th>${__("From")}</th>
						<th>${__("To")}</th>
						<th>${__("Status")}</th>
						<th>${__("Left On")}</th>
					</tr>
				</thead>
				<tbody>${cells}</tbody>
			</table>
			${vmmsx_volunteer.footnote(
				__(
					"Read from each deployment's own roster. Somebody who left early is shown as having left rather than removed, because the time they served still has to be filable."
				)
			)}
		`;
	},

	time_html(dossier) {
		const dto = dossier.time || {};
		const byType = dto.hours_by_type || {};
		const totals = Object.keys(byType)
			.sort()
			.map((kind) => [vmmsx_volunteer.text(kind), byType[kind]]);

		const recent = (dto.recent || [])
			.map(
				(row) => `
					<tr>
						<td>${vmmsx_volunteer.text(vmmsx_volunteer.date(row.activity_date))}</td>
						<td>${vmmsx_volunteer.text(row.log_type)}</td>
						<td>${vmmsx_volunteer.text(row.log_category)}</td>
						<td>${vmmsx_volunteer.deployment_link(row.deployment)}</td>
						<td>${vmmsx_volunteer.text(row.hours)}</td>
					</tr>
				`
			)
			.join("");

		if (!dto.log_count) {
			return vmmsx_volunteer.muted(__("This volunteer has not logged any time."));
		}

		return `
			${vmmsx_volunteer.definitions([
				[__("Total Hours"), dto.total_hours],
				[__("Logs Filed"), dto.log_count],
				...totals,
			])}
			<div class="vmms-card-title-small">${__("Most Recent")}</div>
			<table class="table table-sm vmms-table">
				<thead>
					<tr>
						<th>${__("Date")}</th>
						<th>${__("Kind")}</th>
						<th>${__("Category")}</th>
						<th>${__("Deployment")}</th>
						<th>${__("Hours")}</th>
					</tr>
				</thead>
				<tbody>${recent}</tbody>
			</table>
		`;
	},

	verification_html(dossier) {
		const dto = dossier.application || {};
		if (!dto.application) {
			return vmmsx_volunteer.muted(
				__(
					"No application on file. This volunteer was recorded directly rather than through an application."
				)
			);
		}

		const decisions = (dto.decisions || []).map((row) => {
			const who = vmmsx_volunteer.text(row.approver);
			const when = vmmsx_volunteer.text(vmmsx_volunteer.date(row.decided_on));
			const what = vmmsx_volunteer.text(row.decision);
			const stage = row.stage_label
				? `<span class="text-muted"> &middot; ${vmmsx_volunteer.text(row.stage_label)}</span>`
				: "";
			const why = row.reason
				? `<div class="vmms-reason">${vmmsx_volunteer.text(row.reason)}</div>`
				: "";

			return `<li><strong>${what}</strong> ${__("by")} ${who} ${__("on")} ${when}${stage}${why}</li>`;
		});

		const others =
			dto.application_count > 1
				? vmmsx_volunteer.footnote(
						__("This person has {0} approved applications. The most recent is shown.", [
							dto.application_count,
						])
					)
				: "";

		return `
			${vmmsx_volunteer.definitions([
				[__("Approval State"), dto.approval_state],
				[__("Application"), vmmsx_volunteer.application_link(dto.application)],
				[__("Applied On"), vmmsx_volunteer.date(dto.applied_on)],
			])}
			<div class="vmms-card-title-small">${__("Decisions")}</div>
			${
				decisions.length
					? `<ul class="vmms-decisions">${decisions.join("")}</ul>`
					: vmmsx_volunteer.muted(
							__("No decision was recorded, so no approver acted on this application.")
						)
			}
			${others}
			${vmmsx_volunteer.footnote(
				__(
					"Read from the application every time this page opens. The volunteer record holds no approval state of its own."
				)
			)}
		`;
	},

	declared_html(dossier) {
		const dto = dossier.application || {};
		const declared = dto.declared || {};
		const identification = declared.identification || {};
		const rows = [
			// Motivation, prior experience and the identification are here and
			// nowhere else: they are facts about the applying rather than about
			// the volunteer, so there is no current-state copy of them to edit.
			[__("Motivation"), vmmsx_volunteer.selector_labels(declared.motivation)],
			[__("Prior Experience"), declared.prior_experience],
			[__("Identification"), identification.id_type_name],
			[__("ID Number"), identification.id_number],
			// These three appear on the record above as well, as current truth.
			// Showing both is the point: the difference between them is what a
			// volunteer has learned since, and it is only visible side by side.
			[__("Skills declared"), vmmsx_volunteer.selector_labels(declared.skills)],
			[__("Languages declared"), vmmsx_volunteer.selector_labels(declared.languages)],
			[__("Availability declared"), vmmsx_volunteer.selector_labels(declared.availability)],
		].filter(([, value]) => value);

		if (!dto.application) {
			return vmmsx_volunteer.muted(__("There is no application, so nothing was declared."));
		}

		const body = rows.length
			? rows
					.map(
						([label, value]) => `
							<div class="vmms-declared">
								<div class="vmms-declared-label">${label}</div>
								<div class="vmms-declared-value">${vmmsx_volunteer.text(value)}</div>
							</div>
						`
					)
					.join("")
			: vmmsx_volunteer.muted(__("Nothing was declared on this application."));

		return `
			${vmmsx_volunteer.warning(
				__(
					"Declared by the applicant on {0}. This is what they said about themselves that day, not what this volunteer is currently able to do.",
					[vmmsx_volunteer.date(dto.applied_on) || __("the day they applied")]
				)
			)}
			${body}
			${vmmsx_volunteer.footnote(
				__(
					"Certifications are the record of what this volunteer is qualified to do, and once structured skills arrive they supersede everything above."
				)
			)}
		`;
	},

	/* --- small pieces --------------------------------------------------- */

	/** Every value that reaches the DOM goes through here. */
	text(value) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
	},

	date(value) {
		return value ? frappe.datetime.str_to_user(value) : "";
	},

	/** A `[{key, label}, ...]` structured declaration, joined for display. */
	selector_labels(rows) {
		return (rows || []).map((row) => row.label).join(", ");
	},

	photo(person) {
		if (person.profile_photo) {
			return `<img class="vmms-photo" src="${vmmsx_volunteer.text(
				person.profile_photo
			)}" alt="${vmmsx_volunteer.text(person.full_name)}">`;
		}

		return `<div class="vmms-photo vmms-photo-empty">${vmmsx_volunteer.text(
			frappe.get_abbr(person.full_name || "")
		)}</div>`;
	},

	profile_link(red_profile) {
		if (!red_profile) {
			return "";
		}

		const name = vmmsx_volunteer.text(red_profile);

		return `<a href="/app/red-profile/${encodeURIComponent(red_profile)}">${name}</a>`;
	},

	application_link(application) {
		return vmmsx_volunteer.desk_link("vmms-volunteer-application", application);
	},

	deployment_link(deployment) {
		return vmmsx_volunteer.desk_link("vmms-deployment", deployment);
	},

	/** A link into the desk, or nothing at all. The docname is escaped twice over:
	 * once for the URL and once for the text, because the two need different
	 * escaping and using either for both is a hole.
	 */
	desk_link(route, name) {
		if (!name) {
			return "";
		}

		return `<a href="/app/${route}/${encodeURIComponent(name)}">${vmmsx_volunteer.text(name)}</a>`;
	},

	/** Label/value pairs. Values are pre-escaped or already markup this file built. */
	definitions(rows) {
		const cells = rows
			.map(
				([label, value]) => `
					<div class="vmms-pair">
						<div class="vmms-pair-label">${label}</div>
						<div class="vmms-pair-value">${
							value
								? vmmsx_volunteer.maybe_markup(value)
								: `<span class="text-muted">${__("Not recorded")}</span>`
						}</div>
					</div>
				`
			)
			.join("");

		return `<div class="vmms-pairs">${cells}</div>`;
	},

	/** Anchors this file built are passed through; everything else is escaped. */
	maybe_markup(value) {
		return String(value).startsWith("<a ") ? value : vmmsx_volunteer.text(value);
	},

	/** A desk indicator pill. The colour is this file's; the label is escaped.
	 *
	 * `indicator-pill` is Frappe's own, so these read as part of the desk and
	 * need no stylesheet from this app. The colour is chosen from a fixed set in
	 * the callers above and never comes from data.
	 */
	pill(colour, label) {
		return `<span class="indicator-pill ${colour}">${vmmsx_volunteer.text(label)}</span>`;
	},

	loading() {
		return vmmsx_volunteer.muted(__("Reading..."));
	},

	muted(message) {
		return `<div class="text-muted vmms-note">${message}</div>`;
	},

	warning(message) {
		return `<div class="vmms-snapshot">${message}</div>`;
	},

	footnote(message) {
		return `<div class="text-muted vmms-footnote">${message}</div>`;
	},
};

frappe.ui.form.on("VMMS Volunteer", {
	refresh(frm) {
		// A record being created has no name to ask the server about, and nobody
		// to show: the person is chosen on this form, not read from it.
		if (frm.is_new()) {
			return;
		}

		vmmsx_volunteer.render(frm);
	},
});
