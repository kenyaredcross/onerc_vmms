import { createResource } from "frappe-ui";
import { defineStore } from "pinia";

export const membershipStore = defineStore("membership", () => {
	const membershipTypes = createResource({
		url: "onerc_vmms.volunteer_and_member_management.api.membership.get_membership_types",
		cache: "MembershipTypes",
		auto: true,
	});

	const events = createResource({
		url: "onerc_vmms.volunteer_and_member_management.api.events.get_events",
		auto: true,
		cache: ["events"],
	});

	const currentMembership = createResource({
		url: "onerc_vmms.volunteer_and_member_management.api.membership.get_current_membership",
		auto: true,
		cache: ["currentMembership"],
	});

	return {
		membershipTypes,
		events,
		currentMembership,
	};
});
