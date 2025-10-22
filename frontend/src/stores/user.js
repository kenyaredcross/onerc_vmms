import { createResource } from "frappe-ui";
import { defineStore } from "pinia";
import { useRouter } from "vue-router";

const router = useRouter();

export const userStore = defineStore("vmms-user", () => {
	let userResource = createResource({
		url: "onerc_vmms.volunteer_and_member_management.api.get_user_info",
		onError(error) {
			router.push("/login");
		},
	});

	const roleResource = createResource({
		url: "onerc_vmms.volunteer_and_member_management.api.get_user_info",
		auto: true,
		cache: ["roles"],
	});

	const presentSlots = createResource({
		url: "onerc_vmms.volunteer_and_member_management.api.get_present_slots",
		cache: "presentSlots",
	});

  return {
    userResource,
    roleResource,
    presentSlots,
  };
});
