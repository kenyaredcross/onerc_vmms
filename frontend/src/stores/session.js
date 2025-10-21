import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { usersStore } from "./user";
import router from "@/router";
import { computed, reactive, ref } from "vue";
import { useRoute } from "vue-router";

export const sessionStore = defineStore("vmms-session", () => {
	let { userResource } = usersStore();
	const brand = reactive({});

	function sessionUser() {
		let cookies = new URLSearchParams(document.cookie.split("; ").join("&"));
		let _sessionUser = cookies.get("user_id");
		if (_sessionUser === "Guest") {
			_sessionUser = null;
		}
		return _sessionUser;
	}

	let user = ref(sessionUser());
	const isLoggedIn = computed(() => !!user.value);
  const route = useRoute();

	const login = createResource({
		url: "login",
		onError() {
			throw new Error("Invalid email or password");
		},
		onSuccess() {
			userResource.reload();
			user.value = sessionUser();
			login.reset();

			const redirectTo = route.query["redirect-to"];
			if (redirectTo) {
				router.push(redirectTo);
			} else {
				router.push({ name: "Dashboard" });
			}
		},
	});

	const logout = createResource({
		url: "logout",
		onSuccess() {
			userResource.reset();
			user.value = null;
			window.location.reload();
		},
	});

	return {
		user,
		isLoggedIn,
		login,
		logout,
		brand,
	};
});
