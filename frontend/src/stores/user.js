import { defineStore } from "pinia";
import { createResource, createListResource } from "frappe-ui";
import { useRouter } from "vue-router";

const router = useRouter();

export const usersStore = defineStore("vmms-user", () => {
	let userResource = createResource({
		url: "non_profit.non_profit.api.get_user_info",
		onError(error) {
			router.push("/login");
		},
	});

	const roleResource = createResource({
		url: "non_profit.non_profit.api.get_user_info",
		auto: true,
		cache: ["roles"],
	});

	const presentSlots = createResource({
		url: "non_profit.non_profit.api.get_present_slots",
		cache: "presentSlots",
	});

	return {
		userResource,
		roleResource,
		presentSlots,
	};
});
