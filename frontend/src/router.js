import { createRouter, createWebHistory } from "vue-router";
import { sessionStore } from "./stores/session";
import { usersStore } from "./stores/user";

const routes = [
	{
		path: "/",
		redirect: {
			name: "Dashboard",
		},
	},

	{
		path: "/dashboard",
		name: "Dashboard",
		component: () => import("@/pages/Dashboard.vue"),
	},
	{
		path: "/opportunities",
		name: "Jobs",
		component: () => import("@/pages/Jobs.vue"),
	},
	{
		path: "/opportunities/:job",
		name: "JobDetail",
		component: () => import("@/pages/JobDetail.vue"),
		props: true,
	},
	{
		name: "Login",
		path: "/login",
		component: () => import("@/pages/Login.vue"),
	},

	{
		path: "/user/profile",
		name: "Profile",
		component: () => import("@/pages/Profile.vue"),
		props: true,
	},
	{
		name: "Welcome",
		path: "/welcome",
		component: () => import("@/pages/VmmsPortal.vue"),
		meta: { requiresAuth: false },
	},
	{
		name: "Events",
		path: "/events",
		component: () => import("@/pages/Events.vue"),
	},
	{
		name: "Deployments",
		path: "/deployments",
		component: () => import("@/pages/Deployments.vue"),
		meta: { requiresVolunteer: true },
	},
	{
		name: "DeploymentDetail",
		path: "/deployments/:id",
		component: () => import("@/pages/DeploymentDetail.vue"),
		meta: { requiresAuth: true, requiresVolunteer: true },
	},
	{
		name: "Membership",
		path: "/membership",
		component: () => import("@/pages/Membership.vue"),
	},
	{
		name: "VolunteerSignup",
		path: "/volunteer/signup",
		component: () => import("@/pages/VolunteerSignup.vue"),
		meta: { requiresAuth: true },
	},
	{
		name: "JobApplication",
		path: "/applications",
		component: () => import("@/pages/JobApplication.vue"),
		props: true,
	},
	{
		name: "JobApplicationDetail",
		path: "/applications/:id",
		component: () => import("@/pages/JobApplicationDetail.vue"),
		props: true,
	},
	{
		name: "AssignmentDetail",
		path: "/assignment/:id",
		component: () => import("@/pages/AssignmentDetail.vue"),
		props: true,
		meta: { requiresAuth: true },
	},
	{
		name: "EventDetail",
		path: "/event/:id",
		component: () => import("@/pages/EventDetail.vue"),
		props: true,
	},
	{
		name: "EventRegistration",
		path: "/event/registration/:eventRoute",
		component: () => import("@/pages/EventRegistration.vue"),
		props: true,
	},
	{
		name: "CheckoutSummary",
		path: "/checkout-summary",
		component: () => import("@/pages/CheckoutSummary.vue"),
	},
];

let router = createRouter({
	history: createWebHistory("/vmms"),
	routes,
});

router.beforeEach(async (to, from, next) => {
	const { userResource } = usersStore();
	let { isLoggedIn } = sessionStore();

	if (to.meta.requiresAuth === false) {
		return next();
	}

	try {
		if (isLoggedIn) {
			await userResource.promise;
		}
	} catch (error) {
		isLoggedIn = false;
	}

	if (!isLoggedIn) {
		if (to.meta.requiresAuth) {
			return next({ name: "Login" });
		} else {
			return next();
		}
	}

	router.beforeEach(async (to, from, next) => {
		const { userResource } = usersStore();
		let { isLoggedIn } = sessionStore();

		if (to.meta.requiresAuth === false) {
			return next();
		}

		try {
			if (isLoggedIn) {
				await userResource.promise;
			}
		} catch (error) {
			isLoggedIn = false;
		}

		if (!isLoggedIn) {
			if (to.meta.requiresAuth) {
				return next({ name: "Login" });
			} else {
				return next();
			}
		}

		if (to.meta.requiresVolunteer) {
			if (!userResource?.data?.is_volunteer) {
				return next({ name: "Dashboard" });
			}
		}

		return next();
	});

	return next();
});

export default router;
