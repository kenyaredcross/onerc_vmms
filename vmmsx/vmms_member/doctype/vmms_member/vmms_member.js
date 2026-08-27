// Copyright (c) 2026, Nigel and contributors
// For license information, please see license.txt

/* The member page as one working surface: the complete coordinator's view.
 *
 * An in-repo file rather than a desk Client Script record, for the reason
 * `vmms_volunteer.js` gives: a Client Script is a row in one site's database,
 * invisible to review, absent from every other site, and gone the day somebody
 * deletes it. This ships, migrates and diffs with the code it belongs to.
 *
 * **Everything painted below is read at display time and stored nowhere.** The
 * member record holds a Red Profile link, a derived status and a joining date.
 * It holds no identity at all, and it holds nothing about the memberships
 * beneath it, because a member *is* their memberships and a copy here would be
 * a second answer. So the page asks the server each time it opens, and renders
 * the answer into HTML fields that no column backs. Correct somebody's phone
 * number on their Red Profile, or a branch's name in the geo tree, and every
 * member page in the society is right on next open.
 *
 * **One call, not four.** `get_dossier` returns every block below, resolved as
 * at one instant. Four calls would have been four instants, and lapse,
 * effective status and renewability are all comparisons against a date: a page
 * showing a membership as lapsed beside a renew button that said "not yet",
 * because the two asked either side of midnight, would be wrong in the way that
 * is hardest to notice. The endpoint's docstring states the same argument from
 * the other side.
 *
 * The blocks, and the question each answers:
 *
 *   identity_card          who is this person, and where do they live
 *   standing_indicator     what are they to the society, right now
 *   memberships_held       what do they hold, where, until when, and paid how
 *   verification_history   who checked, and when
 *
 * The heading is overridden here too. `title_field` is `red_profile`, and
 * Frappe's toolbar reads that field's raw value, so the page heading read
 * RP-00042 beside a docname of MEM-00007 and named the person nowhere at all.
 * The alternative was a virtual title field holding the name, and it was
 * rejected for the reason the volunteer page rejects it: it would put an
 * identity value on this doctype's meta, which is precisely what this module
 * refuses, and Frappe's list view adds `title_field` to its query, so a computed
 * one risks selecting a column that does not exist. `refresh_header()` runs
 * before the `refresh` trigger (frappe/public/js/frappe/form/form.js), so
 * setting the title here wins, and it wins with a value that was never stored.
 */

/* Scoped to this script, not hung on `window`. Frappe evaluates a doctype's
 * form script with `new Function(...)()`, so a top-level const lives in that
 * call's scope and the handler below closes over it.
 */
const vmmsx_member = {
	/** Which HTML block each part of the dossier is painted into. */
	blocks: [
		["identity_card", "identity_html"],
		["standing_indicator", "standing_html"],
		["memberships_held", "memberships_html"],
		["verification_history", "history_html"],
	],

	/** The whole page, from one read. */
	render(frm) {
		const painted = vmmsx_member.blocks
			.map(([fieldname, renderer]) => [frm.get_field(fieldname), renderer])
			.filter(([field]) => field);

		if (!painted.length) {
			return;
		}

		painted.forEach(([field]) => field.$wrapper.html(vmmsx_member.loading()));

		frappe
			.xcall("vmmsx.api.member.get_dossier", { name: frm.doc.name })
			.then((dossier) => {
				painted.forEach(([field, renderer]) => {
					field.$wrapper.html(vmmsx_member[renderer](dossier));
				});

				vmmsx_member.set_heading(frm, (dossier.identity || {}).full_name);
			})
			.catch(() => {
				painted.forEach(([field]) =>
					field.$wrapper.html(
						vmmsx_member.muted(__("This member's record could not be read just now."))
					)
				);
			});
	},

	/* --- the heading ---------------------------------------------------- */

	/** The person's name where the docname was, with the docname kept beneath it. */
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

	/* --- rendering ------------------------------------------------------ */

	identity_html(dossier) {
		const person = dossier.identity || {};
		const residence =
			person.residency_type === "Abroad"
				? [person.country_of_residence, person.residence_address].filter(Boolean).join(" · ")
				: person.home_geo_path;
		const rows = [
			[__("Email"), person.email],
			[__("Phone"), person.phone],
			[__("Gender"), person.gender],
			[__("Date of Birth"), vmmsx_member.date(person.date_of_birth)],
			[__("Preferred Language"), person.preferred_language],
			[__("Country of Citizenship"), person.country_of_citizenship],
			[__("Citizenship"), person.citizenship_status],
			[__("Residency"), person.residency_type],
			// Where somebody lives. Never labelled simply "location": a branch
			// they are a member at is a different question, answered per
			// membership below, and a coordinator who confuses the two writes to
			// the wrong branch.
			[__("Residence"), residence],
		];

		return `
			<div class="vmms-card">
				<div class="vmms-card-media">${vmmsx_member.photo(person)}</div>
				<div class="vmms-card-body">
					<div class="vmms-card-title">${vmmsx_member.text(person.full_name)}</div>
					<div class="vmms-card-subtitle">
						${vmmsx_member.profile_link(person.red_profile)}
					</div>
					${vmmsx_member.definitions(rows.filter(([, value]) => value))}
				</div>
			</div>
			${vmmsx_member.footnote(
				__(
					"Name, contact, gender, date of birth, country of citizenship and Home Area are read from this person's Red Profile when the page opens. None of them is stored on the member record."
				)
			)}
		`;
	},

	/** What this person is to the society. Derived; the stored field mirrors it. */
	standing_html(dossier) {
		const dto = dossier.standing || {};
		// Frappe's own indicator pill, not a class this app would then have to
		// ship a stylesheet for. The colour is chosen from a fixed map here and
		// never comes from data; an unrecognised status falls back to grey
		// rather than rendering an unstyled pill.
		const colours = { Active: "green", Lapsed: "orange", Terminated: "red", Prospective: "blue" };
		const state = vmmsx_member.pill(colours[dto.status] || "gray", dto.status || __("Unknown"));

		const branches = (dto.current_geo_paths || []).length
			? `<ul class="vmms-reasons">${dto.current_geo_paths
					.map((path) => `<li>${vmmsx_member.text(path)}</li>`)
					.join("")}</ul>`
			: "";

		return `
			${state}
			${vmmsx_member.definitions(
				[
					[__("Joined On"), vmmsx_member.date(dto.joined_on)],
					[__("Memberships Held"), dto.visible_count],
					[__("Currently Active"), dto.current_count],
					[__("Lapsed"), dto.lapsed_count],
				].filter(([, value]) => value || value === 0)
			)}
			${
				branches
					? `<div class="vmms-card-title-small">${__("Currently a member at")}</div>${branches}`
					: ""
			}
			${vmmsx_member.footnote(
				__(
					"Worked out when this page opened, from the memberships below, as at {0}. Somebody active at one branch and expired at another is active: holding a current membership anywhere makes a person a current member.",
					[vmmsx_member.date(dossier.as_of)]
				)
			)}
		`;
	},

	memberships_html(dossier) {
		const rows = dossier.memberships || [];

		if (!rows.length) {
			return vmmsx_member.muted(
				__(
					"No memberships. Either this person has never been enrolled, or none of their branches is within your scope."
				)
			);
		}

		const cells = rows
			.map((row) => {
				const flag = row.is_current
					? vmmsx_member.pill("green", __("Current"))
					: row.lapsed
						? vmmsx_member.pill("orange", __("Lapsed"))
						: vmmsx_member.pill("gray", row.membership_status);

				return `
					<tr>
						<td>${vmmsx_member.membership_link(row.name)}</td>
						<td>${vmmsx_member.text(row.membership_geo_path)}</td>
						<td>${vmmsx_member.text(row.membership_type_name)}</td>
						<td>${vmmsx_member.validity(row)}</td>
						<td>${flag}</td>
						<td>${vmmsx_member.payment(row.payment)}</td>
						<td>${vmmsx_member.certificate(row)}</td>
					</tr>
				`;
			})
			.join("");

		return `
			<table class="table table-sm vmms-table">
				<thead>
					<tr>
						<th>${__("Membership")}</th>
						<th>${__("Branch")}</th>
						<th>${__("Type")}</th>
						<th>${__("Valid")}</th>
						<th>${__("Status")}</th>
						<th>${__("Paid")}</th>
						<th>${__("Certificate")}</th>
					</tr>
				</thead>
				<tbody>${cells}</tbody>
			</table>
			${vmmsx_member.footnote(
				__(
					"Every branch is listed separately, because a membership belongs to a branch and somebody may hold several at once. Whether one has lapsed is a comparison against {0}, made when this page opened; no record carries a lapsed field.",
					[vmmsx_member.date(dossier.as_of)]
				)
			)}
		`;
	},

	/** The validity window, or what is standing in for one. */
	validity(row) {
		if (row.valid_from && row.valid_to) {
			return `${vmmsx_member.text(vmmsx_member.date(row.valid_from))} &ndash; ${vmmsx_member.text(
				vmmsx_member.date(row.valid_to)
			)}`;
		}

		if (row.valid_from) {
			// Activated with no end date. A lifetime membership is the
			// configured way to get here and says so; anything else with no
			// valid_to is rendered rather than assumed away.
			const end = row.is_lifetime ? __("Lifetime") : __("No expiry");

			return `${vmmsx_member.text(vmmsx_member.date(row.valid_from))} &ndash; ${end}`;
		}

		return `<span class="text-muted">${__("Not yet active")}</span>`;
	},

	/** How this membership was paid for. Read live; nothing here is stored. */
	payment(dto) {
		if (!dto) {
			return "";
		}

		if (dto.is_proof) {
			const who = dto.verified_by
				? __("verified by {0}", [dto.verified_by])
				: __("awaiting verification");

			return `${vmmsx_member.pill("blue", __("Proof"))} <div class="vmms-reason">${vmmsx_member.text(
				who
			)}</div>${
				dto.proof_attachment
					? `<a href="${vmmsx_member.text(dto.proof_attachment)}">${__("Attachment")}</a>`
					: ""
			}`;
		}

		if (!dto.payable) {
			return vmmsx_member.pill("gray", __("Free"));
		}

		if (!dto.settled) {
			return vmmsx_member.pill("orange", __("Unpaid"));
		}

		// The gateway and its receipt come from the payments app on every read,
		// never from a copy on the membership. A site with no payments app
		// installed simply has no live half to show, and says the fee is
		// settled without claiming to know how.
		const how = dto.live
			? __("via {0}", [dto.gateway || __("gateway")])
			: __("recorded on this membership");
		const receipt = dto.gateway_receipt || dto.receipt;

		return `${vmmsx_member.pill("green", __("Paid"))} <div class="vmms-reason">${vmmsx_member.text(
			how
		)}${receipt ? ` &middot; ${vmmsx_member.text(receipt)}` : ""}</div>`;
	},

	/** Whether a certificate exists, and whether this reader may have it. */
	certificate(row) {
		const dto = row.certificate || {};

		if (!dto.available) {
			return `<span class="text-muted">${__("Not active")}</span>`;
		}

		if (!dto.configured) {
			return `<span class="text-muted">${__("No template")}</span>`;
		}

		if (!dto.may_print) {
			return `<span class="text-muted">${__("Not yours to print")}</span>`;
		}

		return `<a href="/api/method/vmmsx.api.member.download_certificate?membership=${encodeURIComponent(
			row.name
		)}">${__("Download")}</a>`;
	},

	history_html(dossier) {
		const rows = dossier.history || [];

		if (!rows.length) {
			return vmmsx_member.muted(
				__(
					"Nobody has recorded a decision on this person's memberships. A membership that activates on payment has no approver, so this is ordinary."
				)
			);
		}

		const items = rows.map((row) => {
			const who = vmmsx_member.text(row.approver);
			const when = vmmsx_member.text(vmmsx_member.date(row.decided_on));
			const what = vmmsx_member.text(row.decision);
			const stage = row.stage_label
				? `<span class="text-muted"> &middot; ${vmmsx_member.text(row.stage_label)}</span>`
				: "";
			const where = `<span class="text-muted"> &middot; ${vmmsx_member.text(
				row.membership_type_name
			)}, ${vmmsx_member.text(row.geo_path)}</span>`;
			const why = row.reason ? `<div class="vmms-reason">${vmmsx_member.text(row.reason)}</div>` : "";

			return `<li><strong>${what}</strong> ${__("by")} ${who} ${__(
				"on"
			)} ${when}${stage}${where}${why}</li>`;
		});

		return `
			<ul class="vmms-decisions">${items.join("")}</ul>
			${vmmsx_member.footnote(
				__(
					"Read from each membership's own approval decisions every time this page opens. The member record holds no approval state of its own."
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

	photo(person) {
		if (person.profile_photo) {
			return `<img class="vmms-photo" src="${vmmsx_member.text(
				person.profile_photo
			)}" alt="${vmmsx_member.text(person.full_name)}">`;
		}

		return `<div class="vmms-photo vmms-photo-empty">${vmmsx_member.text(
			frappe.get_abbr(person.full_name || "")
		)}</div>`;
	},

	profile_link(red_profile) {
		if (!red_profile) {
			return "";
		}

		return `<a href="/app/red-profile/${encodeURIComponent(red_profile)}">${vmmsx_member.text(
			red_profile
		)}</a>`;
	},

	membership_link(name) {
		if (!name) {
			return "";
		}

		return `<a href="/app/vmms-membership/${encodeURIComponent(name)}">${vmmsx_member.text(
			name
		)}</a>`;
	},

	/** Label/value pairs. Values are pre-escaped or already markup this file built. */
	definitions(rows) {
		const cells = rows
			.map(
				([label, value]) => `
					<div class="vmms-pair">
						<div class="vmms-pair-label">${label}</div>
						<div class="vmms-pair-value">${
							value || value === 0
								? vmmsx_member.maybe_markup(value)
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
		return String(value).startsWith("<a ") ? value : vmmsx_member.text(value);
	},

	/** A desk indicator pill. The colour is this file's; the label is escaped. */
	pill(colour, label) {
		return `<span class="indicator-pill ${colour}">${vmmsx_member.text(label)}</span>`;
	},

	loading() {
		return vmmsx_member.muted(__("Reading..."));
	},

	muted(message) {
		return `<div class="text-muted vmms-note">${message}</div>`;
	},

	footnote(message) {
		return `<div class="text-muted vmms-footnote">${message}</div>`;
	},
};

frappe.ui.form.on("VMMS Member", {
	refresh(frm) {
		// A record being created has no name to ask the server about, and nobody
		// to show: the person is chosen on this form, not read from it.
		if (frm.is_new()) {
			return;
		}

		vmmsx_member.render(frm);
	},
});
