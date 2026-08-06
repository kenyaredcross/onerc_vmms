<template>
	<div class="flex h-full flex-col gap-2 relative">
		<main
			id="scrollContainer"
			tabindex="-1"
			class="h-full pb-10 mb-8 bg-surface-base focus:outline-none"
		>
			<slot />
		</main>

		<div class="relative z-20">
			<div
				v-if="showMenu"
				ref="menu"
				class="fixed bottom-16 right-2 w-[80%] rounded-xl bg-surface-base border border-outline-gray-1 shadow-lg p-4 space-y-3"
			>
				<button
					v-for="link in otherLinks"
					:key="link.label"
					type="button"
					class="w-full text-left flex items-center space-x-2 cursor-pointer hover:underline"
					@click="handleClick(link)"
				>
					<component :is="icons[link.icon]" class="h-4 w-4 shrink-0 text-ink-red-6" />
					<component
						v-if="link.logo"
						:is="`img`"
						:src="link.logo"
						class="h-4 w-4 object-contain"
					/>
					<span>{{ __(link.name) }}</span>
				</button>
			</div>

			<nav
				:aria-label="__('Main')"
				class="fixed bottom-0 left-0 w-full flex items-center justify-between border-t border-outline-gray-2 bg-surface-base standalone:pb-4 z-10"
			>
				<button
					v-for="tab in sidebarLinks.filter(
						(link) => !['Profile', 'Events'].includes(link.label)
					)"
					:key="tab.label"
					:class="isVisible(tab) ? 'flex' : 'hidden'"
					class="flex-1 flex-col items-center justify-center py-4 transition active:scale-95"
					@click="handleClick(tab)"
				>
					<component
						:is="icons[tab.icon]"
						class="h-6 w-6 stroke-1.5"
						:class="isActive(tab) ? 'text-ink-red-8' : 'text-ink-gray-5'"
					/>
					<span class="text-2xs text-ink-gray-6">{{ __(tab.label) }}</span>
				</button>

				<button
					v-if="isLoggedIn"
					id="notifications-btn"
					class="relative flex-1 flex flex-col items-center justify-center py-4 transition active:scale-95"
					:aria-label="__('Notifications')"
					@click="notifications.togglePanel()"
				>
					<span class="relative">
						<component
							:is="icons['Bell']"
							class="h-6 w-6 stroke-1.5"
							:class="
								notifications.isPanelOpen ? 'text-ink-red-8' : 'text-ink-gray-5'
							"
						/>
						<span
							v-if="notifications.hasUnread"
							class="absolute -top-1 -right-1 size-2 rounded-full bg-surface-red-5"
						/>
					</span>
					<span class="text-2xs text-ink-gray-6">{{ __("Alerts") }}</span>
				</button>

				<button
					@click="toggleMenu"
					class="py-4 px-3 flex flex-col items-center justify-center"
				>
					<component :is="icons['List']" class="h-6 w-6 stroke-1.5 text-ink-gray-5" />
					<span class="text-xs text-ink-gray-6">{{ __("More") }}</span>
				</button>
			</nav>
		</div>

		<NotificationPanel v-if="isLoggedIn" />
	</div>
</template>

<script setup>
import NotificationPanel from "@/components/NotificationPanel.vue";
import { useNotifications } from "@/stores/notifications";
import { sessionStore } from "@/stores/session";
import { useSettings } from "@/stores/settings";
import { usersStore } from "@/stores/user";
import { getSidebarLinks } from "@/utils";
import * as icons from "lucide-vue-next";
import { computed, ref, toRaw, watch } from "vue";
import { useRouter } from "vue-router";
import { sideBarApps } from "../utils/appsNavigate";

const notifications = useNotifications();
const settings = useSettings();

const { logout, user } = sessionStore();
let { isLoggedIn } = sessionStore();
const router = useRouter();
const userStore = usersStore();
let { userResource } = userStore;
const otherLinks = ref([]);
const showMenu = ref(false);
const menu = ref(null);

const sidebarLinks = computed(() => getSidebarLinks(userStore.isVolunteer));

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
				name: "Settings",
				icon: "Settings",
				onClick: () => settings.openSettings(),
			},

			{
				name: "Log out",
				icon: "LogOut",
			}
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
			}
		);
	}
};

let isActive = (tab) => {
	return tab.activeFor?.includes(router.currentRoute.value.name);
};

const handleClick = (tabLink) => {
	let tab = toRaw(tabLink);

	showMenu.value = false;

	if (tab.onClick) {
		tab.onClick();
	} else if (tab.name === "Log in") {
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
