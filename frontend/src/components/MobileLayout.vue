<template>
	<div class="flex h-full flex-col gap-2 relative">
		<div class="h-full pb-10 mb-5" id="scrollContainer">
			<slot />
		</div>

		<div class="relative z-20">
			<div
				class="fixed bottom-16 right-2 w-[80%] rounded-md bg-surface-white text-base p-5 space-y-4 shadow-md"
				v-if="showMenu"
				ref="menu"
			>
				<div
					v-for="link in otherLinks"
					:key="link.label"
					class="flex items-center space-x-2 cursor-pointer hover:underline"
					@click="handleClick(link)"
				>
					<component :is="icons[link.icon]" class="h-4 w-4 stroke-1.5 text-red-600" />
					<component
						v-if="link.logo"
						:is="`img`"
						:src="link.logo"
						class="h-4 w-4 object-contain"
					/>
					<div class="">{{ __(link.name) }}</div>
				</div>
			</div>

			<div
				class="fixed bottom-0 left-0 w-full flex items-center justify-between border-t border-outline-gray-2 bg-surface-white standalone:pb-4 z-10"
			>
				<button
					v-for="tab in sidebarLinks.filter(
						(link) => link.label !== 'Profile' && link.label !== 'Events',
					)"
					:key="tab.label"
					:class="isVisible(tab) ? 'block' : 'hidden'"
					class="flex-1 flex flex-col items-center justify-center py-4 transition active:scale-95"
					@click="handleClick(tab)"
				>
					<component
						:is="icons[tab.icon]"
						class="h-6 w-6 stroke-1.5"
						:class="[isActive(tab) ? 'text-ink-red-4' : 'text-ink-gray-5']"
					/>
					<span class="text-xs">{{ __(tab.label) }}</span>
				</button>

				<button
					@click="toggleMenu"
					class="py-4 px-3 flex flex-col items-center justify-center"
				>
					<component :is="icons['List']" class="h-6 w-6 stroke-1.5 text-ink-gray-5" />
					<span class="text-xs">{{ __("More") }}</span>
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { sessionStore } from "@/stores/session";
import { usersStore } from "@/stores/user";
import { getSidebarLinks } from "@/utils";
import { createResource } from "frappe-ui";
import * as icons from "lucide-vue-next";
import { ref, toRaw, watch } from "vue";
import { useRouter } from "vue-router";
import { sideBarApps } from "../utils/appsNavigate";

const { logout, user } = sessionStore();
let { isLoggedIn } = sessionStore();
const router = useRouter();
let { userResource } = usersStore();
const sidebarLinks = ref(getSidebarLinks());
const otherLinks = ref([]);
const showMenu = ref(false);
const menu = ref(null);
let appsLoaded = false;

const handleOutsideClick = (e) => {
	if (menu.value && !menu.value.contains(e.target)) {
		showMenu.value = false;
	}
};

watch(showMenu, (val) => {
	if (val) {
		setTimeout(() => {
			document.addEventListener("click", handleOutsideClick);
		}, 0);
	} else {
		document.removeEventListener("click", handleOutsideClick);
	}
});

const addOtherLinks = () => {
	if (user) {
		otherLinks.value.push(
			...sideBarApps(),
			{
				name: "Events",
				icon: "CalendarDays",
				to: "Events",
			},
			{
				name: "Profile",
				icon: "User",
				to: "Profile",
			},
			{
				name: "Log out",
				icon: "LogOut",
			},
		);
	} else {
		otherLinks.value.push(
			{
				name: "Events",
				icon: "CalendarDays",
				to: "Events",
			},
			{
				name: "Log in",
				icon: "LogIn",
			},
		);
	}
};

let isActive = (tab) => {
	return tab.activeFor?.includes(router.currentRoute.value.name);
};

const handleClick = (tabLink) => {
	let tab = toRaw(tabLink);

	if (tab.name === "Log in") {
		window.location.href = "/vmms/login";
	} else if (tab.name === "Log out") {
		logout.submit().then(() => {
			isLoggedIn = false;
		});
	} else if (tab.route) {
		window.location.href = tab.route;
	} else if (tab.to) {
		router.push({ name: tab.to });
	}
};

const isVisible = (tab) => {
	if (tab.name == "Log in") return !isLoggedIn;
	else if (tab.name == "Log out") return isLoggedIn;
	else return true;
};

const toggleMenu = () => {
	showMenu.value = !showMenu.value;
};

watch(showMenu, (newVal) => {
	if (newVal) {
		if (otherLinks.value.length == 0) addOtherLinks();
	}
});
</script>
