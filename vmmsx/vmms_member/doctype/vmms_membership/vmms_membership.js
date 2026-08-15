// Copyright (c) 2026, Nigel and contributors
// For license information, please see license.txt

/* ACC-03 at the picker, not only at Submit.
 *
 * `geo_node` is an ordinary Link with no filter in its JSON: which level it
 * may sit at is society configuration that can change at any time, so it does
 * not belong in a fixed `link_filters`. Left unfiltered, somebody could pick a
 * Region a workflow only routes at Branch level, save a perfectly good draft,
 * and have Submit refuse it minutes later — the exact trap this file closes.
 *
 * `vmmsx.api.member.geo_node_levels` reads the same two things
 * `VMMSMembership.validate()` and the approval engine's Submit each enforce
 * independently — National Society Settings' `vmms_membership_anchor_level`
 * and the governing VMMS Approval Workflow's `allowed_anchor_levels` —
 * intersected, so a level this picker offers can never be one either check
 * goes on to reject. Fetched once per form load: the levels are society
 * configuration that does not change while somebody is filling in one
 * membership.
 */
/* Two more papercuts closed on this form, both from the same walk-through.
 *
 * **The heading named nothing.** `VMMS Membership` has no `title_field`, so the
 * page heading was the docname, MSHIP-00013 — a membership record that never
 * says whose it is. The name is read from the status DTO, which reads it from
 * Red Profile, and is set on the page rather than stored: this doctype holds no
 * identity and must not start.
 *
 * **The price was invisible at the moment of choosing.** Somebody picking a
 * membership type was picking between names with nothing to say that one of
 * them charges a fee. The type's own fee is read live and shown as the field's
 * description, so it is beside the choice rather than a page away, and it
 * updates when the choice does. Live, because a fee is configuration a society
 * changes and a stale price on a form is worse than no price at all.
 */
frappe.ui.form.on("VMMS Membership", {
	onload(frm) {
		vmmsx_membership.apply_anchor_filter(frm);
	},

	refresh(frm) {
		vmmsx_membership.show_price(frm);

		if (!frm.is_new()) {
			vmmsx_membership.load(frm);
		}
	},

	membership_type(frm) {
		vmmsx_membership.show_price(frm);
	},
});

const vmmsx_membership = {
	apply_anchor_filter(frm) {
		frappe.xcall("vmmsx.api.member.geo_node_levels").then((dto) => {
			frm.set_query("geo_node", () =>
				dto.unconstrained ? {} : { filters: { geo_level: ["in", dto.levels] } }
			);
		});
	},

	/** What this type costs, under the field that chose it. */
	show_price(frm) {
		const field = frm.get_field("membership_type");

		if (!field) {
			return;
		}

		frappe
			.xcall("vmmsx.api.member.membership_type_pricing", {
				membership_type: frm.doc.membership_type,
			})
			.then((dto) => {
				field.set_description(dto.known ? vmmsx_membership.price_line(dto) : "");
			})
			.catch(() => field.set_description(""));
	},

	/** The fee in words a person reads, and what else the choice commits them to.
	 *
	 * Free is said as a word rather than as a zero beside a currency symbol: a
	 * society that charges nothing should not have its forms implying it might.
	 * `format_currency` is Frappe's own, so the currency the society configured
	 * is rendered the way the rest of the desk renders it.
	 */
	price_line(dto) {
		const price = dto.free ? __("Free") : frappe.format(dto.amount, {
			fieldtype: "Currency",
			options: "currency",
		}, { currency: dto.currency });

		// A lifetime type has no duration, and "0 days" beside a fee would be
		// the form contradicting the record. The server says which it is.
		const parts = [price, dto.is_lifetime ? __("Lifetime") : __("{0} days", [dto.duration_days])];

		if (dto.requires_approver) {
			parts.push(__("needs an approver"));
		}

		return parts.join(" &middot; ");
	},

	/** The member's name where the docname was, with the docname kept beneath it.
	 *
	 * Read through `get_membership`, whose DTO takes the name from Red Profile.
	 * Nothing is written, and reloading asks again.
	 */
	/** One read, two jobs: name the page, and offer what may be done to it.
	 *
	 * Both come from `get_membership`, so a form that could not be resolved
	 * shows the docname and no buttons rather than half a page.
	 */
	load(frm) {
		frappe
			.xcall("vmmsx.api.member.get_membership", { name: frm.doc.name })
			.then((dto) => {
				vmmsx_membership.name_the_page(frm, dto);
				vmmsx_membership.actions(frm, dto);
			})
			.catch(() => {
				// A membership the reader may not fully resolve still renders as
				// the desk's ordinary form. The heading simply stays the docname
				// and no act is offered, which is the safe direction to fail in.
			});
	},

	name_the_page(frm, dto) {
		if (!dto.member_name) {
			return;
		}

		frm.page.set_title(dto.member_name);
		// The opaque docname stays visible and copyable: it is what an audit
		// trail, a report and a support conversation refer to.
		frm.page.set_title_sub(frm.doc.name);
		frappe.utils.set_title(`${dto.member_name} - ${frm.doc.name}`);
	},

	/* --- the acts -------------------------------------------------------- */

	/** What may be done to this membership's standing, from where it stands now.
	 *
	 * **Cancel and expire are not two spellings of the same act.** Cancel ends a
	 * membership early and records why; expire closes one whose validity has
	 * already run out and carries no reason, because the date is the reason. So
	 * expire is offered only when `is_lapsed` says the window has actually
	 * closed — the same predicate `api/member.py::expire_membership` checks
	 * before it will act, derived once server-side so the button and the
	 * endpoint cannot disagree. A current membership offers cancel alone, which
	 * is the honest answer to "I need this one to stop".
	 *
	 * **Activation is deliberately absent**, and the endpoint's docstring says
	 * why: it is a predicate re-evaluated from `on_update`, not a verb somebody
	 * performs. A button forcing it would be a way around approval and payment
	 * both.
	 *
	 * `can_act` is the server's answer — `frappe.has_permission(..., "write")`,
	 * the same check the endpoints make — so no role name appears here.
	 */
	actions(frm, dto) {
		frm.clear_custom_buttons();

		if (!dto.can_act) {
			return;
		}

		if (dto.membership_status !== "Cancelled") {
			frm.add_custom_button(
				__("Cancel membership"),
				() => vmmsx_membership.ask_to_cancel(frm),
				__("Standing")
			);
		}

		if (dto.membership_status === "Active" && dto.is_lapsed) {
			frm.add_custom_button(
				__("Expire"),
				() => vmmsx_membership.ask_to_expire(frm),
				__("Standing")
			);
		}
	},

	/** Cancelling asks for a reason, because nothing else will record one.
	 *
	 * The service adds a comment only when a reason is given, which makes it the
	 * entire record of why a membership ended early: `membership_status` itself
	 * remembers neither who decided nor why.
	 */
	ask_to_cancel(frm) {
		frappe.prompt(
			[
				{
					fieldname: "reason",
					fieldtype: "Small Text",
					label: __("Why is this membership being cancelled?"),
					reqd: 1,
				},
			],
			(values) => vmmsx_membership.act(frm, "vmmsx.api.member.cancel_membership", values),
			__("Cancel membership"),
			__("Cancel membership")
		);
	},

	/** Expiring asks only for confirmation. There is nothing to say that the
	 * dates do not already say, and the server refuses it anyway unless the
	 * validity window has closed.
	 */
	ask_to_expire(frm) {
		frappe.confirm(
			__("Close this membership? Its validity has already run out."),
			() => vmmsx_membership.act(frm, "vmmsx.api.member.expire_membership", {})
		);
	},

	/** Perform an act and reload.
	 *
	 * `frm.reload_doc()` rather than repainting from the response: these verbs
	 * move derived state that the rest of the form reads off the document, and
	 * one reload is the only way the whole page agrees with itself afterwards.
	 */
	act(frm, method, values) {
		frappe
			.xcall(method, { name: frm.doc.name, ...values })
			.then(() => frm.reload_doc())
			.catch(() => {
				// Frappe has already shown the server's message. Nothing is
				// reloaded, so the form still shows the state that failed to move
				// rather than a guess about where it ended up.
			});
	},
};
