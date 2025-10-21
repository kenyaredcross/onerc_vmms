import { usersStore } from "./stores/user";
import { sessionStore } from "./stores/session";
import { createRouter, createWebHistory } from "vue-router";

const routes = [
	{
		path: "/",
		name: "Dashboard",
		component: () => import("@/pages/Dashboard.vue"),
	},
	{
		name: "Login",
		path: "/account/login",
		component: () => import("@/pages/Login.vue"),
	},
];

const router = createRouter({
	history: createWebHistory("/vmms"),
	routes,
});

router.beforeEach(async (to, from, next) => {
	const { isLoggedIn } = sessionStore();
	const { userResource } = usersStore();
	try {
		await userResource.promise;
	} catch (error) {
		isLoggedIn = false;
	}

	if (to.name === "Login" && isLoggedIn) {
		next({ name: "Dashboard" });
	} else if (to.name !== "Login" && !isLoggedIn) {
		next({ name: "Login" });
	} else {
		next();
	}
});

export default router;
