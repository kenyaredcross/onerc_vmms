<<<<<<< HEAD
=======
import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { usersStore } from "./user";
>>>>>>> origin/develop
import router from "@/router";
import { createResource } from "frappe-ui";
import { defineStore } from "pinia";
import { computed, reactive, ref } from "vue";
<<<<<<< HEAD
import { usersStore } from "./user";

export const sessionStore = defineStore("vmms-session", () => {
	let { userResource } = usersStore();
	const brand = reactive({});
=======

export const sessionStore = defineStore("vmms-session", () => {
  let { userResource } = usersStore();
  const brand = reactive({});
>>>>>>> origin/develop

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

	const login = createResource({
		url: "login",
		onError() {
			throw new Error("Invalid email or password");
		},
		onSuccess() {
			userResource.reload();
			user.value = sessionUser();
			login.reset();
			router.replace({ path: "/" });
		},
	});


	const branding = createResource({
		url: "onerc_vmms.volunteer_and_member_management.utils.get_branding",
		cache: "brand",
		auto: true,
		onSuccess(data) {
			brand.name = data.app_name;
			brand.logo = data.app_logo;
			brand.favicon = data.favicon?.file_url || "/assets/non_profit/frontend/favicon.png";
		},
	});

	return {
		user,
		isLoggedIn,
		login,
		logout,
		brand,
		branding,
	};
});
