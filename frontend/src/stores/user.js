import { createResource } from "frappe-ui";
import { defineStore } from "pinia";
import { useRouter } from "vue-router";

const router = useRouter();

export const usersStore = defineStore("vmms-users", () => {
	let userResource = createResource({
		url: "onerc_vmms.volunteer_and_member_management.api.user.get_user_info",
		onError(error) {
			if (error && error.exc_type === "AuthenticationError") {
				router.push("/login");
			}
		},
		auto: true,
	});

	const roleResource = createResource({
		url: "onerc_vmms.volunteer_and_member_management.api.user.get_user_info",
		auto: true,
		cache: ["roles"],
	});

	const presentSlots = createResource({
		url: "onerc_vmms.volunteer_and_member_management.api.volunteer.get_present_slots",
		cache: "presentSlots",
		auto: true,
	});

  return {
    userResource,
    roleResource,
    presentSlots,
  };
});
