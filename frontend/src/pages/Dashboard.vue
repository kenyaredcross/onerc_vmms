<template>
	<NoPermission v-if="user?.data == 'Guest'" :page="__('Dashboard')" />

	<div
		v-if="user?.data && user?.data !== 'Guest'"
		class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2 lg:py-8"
	>
		<header
			class="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 sm:p-6 bg-surface-white rounded-xl border border-outline-gray-2"
		>
			<!-- Title -->
			<h1
				class="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-extrabold text-ink-gray-1-900 tracking-tight mb-3 sm:mb-0 w-full truncate text-left sm:text-left"
			>
				{{ __("Welcome back, ") }}
				<span class="ml-1 text-red-600 font-black">{{ user?.data?.full_name }}</span>
			</h1>

			<div v-show="isMobile" class="p-2 cursor-pointer" @click="changeTheme">
				<Sun v-if="currentTheme == 'dark'" class="w-5 h-5 text-ink-gray-6" />
				<Moon v-else class="w-5 h-5 text-ink-gray-6" />
			</div>

			<!-- Action Buttons & Notifications -->
			<div
				class="flex flex-wrap sm:flex-nowrap items-center gap-2 md:gap-4 w-full sm:w-auto justify-end"
			>
				<!-- Volunteer Action -->
				<div
					v-if="roleResource?.data?.is_volunteer"
					class="flex flex-wrap sm:flex-nowrap items-center gap-2 justify-end"
				>
					<div
						v-if="!presentSlots?.data"
						class="hidden sm:block text-xs border border-blue-600 px-2 py-1 bg-blue-100 rounded-lg text-blue-600 font-medium whitespace-nowrap"
					>
						{{ __("Action Required") }}
					</div>

					<button
						class="px-3 py-1.5 sm:px-4 sm:py-2 text-sm font-semibold text-white bg-red-600 rounded-xl hover:bg-red-700 shadow-lg transition duration-150 ease-in-out transform hover:scale-[1.02] active:scale-95 whitespace-nowrap"
						@click="setAvailability = true"
					>
						{{ __("Set Availability") }}
					</button>

					<!-- Notifications -->
					<div class="relative cursor-pointer" @click="showNotificationDialog = true">
						<div
							class="relative transition duration-200"
							:class="{ 'animate-wiggle': hasNotification }"
						>
							<Bell
								class="h-6 w-6 text-ink-gray-1-700 hover:text-red-600 transition duration-150"
							/>
							<span
								v-if="hasNotification"
								class="absolute -top-1 -right-1 block h-3 w-3 rounded-full bg-red-600 ring-2 ring-white animate-ping-once"
								style="animation-iteration-count: 1"
							></span>
						</div>
					</div>
				</div>

				<!-- Profile Menu -->
				<div class="relative flex-shrink-0">
					<button
						@click="isOpen = !isOpen"
						:class="[
							'flex items-center justify-center w-11 h-11 rounded-full border border-outline-gray-2 transition-all duration-300 ease-in-out',
							isOpen
								? 'bg-red-600 ring-4 ring-red-300/50 text-white'
								: 'bg-surface-gray-200 hover:bg-red-500 hover:text-white text-ink-gray-1-700',
						]"
						aria-label="Toggle profile menu"
						aria-expanded="[isOpen ? 'true' : 'false']"
					>
						<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
							<path
								d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"
							/>
						</svg>
					</button>

					<transition
						enter-active-class="transition ease-out duration-200"
						enter-from-class="transform opacity-0 scale-95 translate-y-2"
						enter-to-class="transform opacity-100 scale-100 translate-y-0"
						leave-active-class="transition ease-in duration-150"
						leave-from-class="transform opacity-100 scale-100 translate-y-0"
						leave-to-class="transform opacity-0 scale-95 translate-y-2"
					>
						<div
							v-show="isOpen"
							class="absolute right-0 mt-4 w-56 bg-surface-white rounded-xl border border-outline-gray-100 shadow-2xl py-2 z-50 origin-top-right ring-1 ring-black ring-opacity-5"
							role="menu"
							aria-orientation="vertical"
						>
							<router-link
								:to="{ name: 'Profile' }"
								class="flex items-center gap-2 px-4 py-3 text-sm font-medium text-ink-gray-1-700 hover:bg-red-50 hover:text-red-600 transition duration-150 ease-in-out"
								role="menuitem"
								@click="isOpen = false"
							>
								<LogIn class="w-5 h-5" />{{ __("Edit Profile") }}
							</router-link>

							<div class="border-t my-1"></div>

							<router-link
								:to="{ name: 'ProfileOverview' }"
								class="flex items-center gap-2 px-4 py-3 text-sm font-medium text-ink-gray-1-700 hover:bg-red-50 hover:text-red-600 transition duration-150 ease-in-out"
								role="menuitem"
								@click="isOpen = false"
							>
								<User class="w-5 h-5" />{{ __("Profile Overview") }}
							</router-link>
						</div>
					</transition>
				</div>
			</div>
		</header>

		<main>
			<div v-if="roleResource?.loading" class="py-20 text-center">
				<ProgressSpinner :message="'Setting up Dashboard...'" />
			</div>

			<div v-else-if="roleResource?.data" class="grid grid-cols-1 gap-6">
				<Welcome v-if="!isVolunteer && !isMember" />

				<Volunteer v-if="isVolunteer" v-bind="dashboardStats?.data" />

				<Member v-if="isMember" :membership-status="currentMembership?.data" />

				<section
					v-if="roleResource?.data && (isVolunteer || isMember)"
					class="bg-surface-white p-6 rounded-xl border border-outline-gray-2"
				>
					<div class="flex justify-between mb-4">
						<h2 class="text-xl font-bold">{{ __("Upcoming Events") }}</h2>
						<router-link
							to="/events"
							v-if="events.data && events.data.length > 3"
							class="text-sm text-red-600 font-semibold"
						>
							{{ __("View All") }}
						</router-link>
					</div>

					<div
						class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
						v-if="events?.data?.length"
					>
						<EventCard
							v-for="event in events?.data.slice(0, 3)"
							:key="event.name"
							:event="event"
						/>
					</div>

					<EmptyState
						v-if="events?.data && events.data.length === 0"
						:type="__('Events')"
					/>
				</section>
			</div>
		</main>

		<Availability
			v-model="setAvailability"
			@success="updateAvailability"
			@cancel="updateAvailability"
		/>

		<Dialog :options="{ size: 'lg' }" v-model="showNotificationDialog">
			<template #body-title>
				<div class="flex gap-2 justify-between">
					<h3 class="text-xl font-bold flex items-center text-ink-gray-8 gap-2">
						<Bell class="w-5 h-5 text-ink-red-4" />
						{{ __("Assignments") }}
					</h3>
					<Badge theme="red">{{ assignedProjects.length }}</Badge>
				</div>
			</template>

			<template #body-content>
				<div v-if="assignedProjects.length" class="space-y-3">
					<div v-for="p in assignedProjects" :key="p.name" class="p-4 border rounded-lg">
						<div class="flex justify-between">
							<div>
								<h4 class="font-semibold text-ink-gray-8">{{ p.project_name }}</h4>
								<p class="text-xs text-ink-gray-5">{{ p.name }}</p>
							</div>
							<router-link
								:to="{
									name: 'DeploymentDetail',
									params: { id: p.deployment_name },
								}"
							>
								<Button variant="solid" theme="red">{{ __("View") }}</Button>
							</router-link>
						</div>
					</div>
				</div>

				<div v-else class="text-center py-12 text-ink-gray-1-500">
					{{ __("No new assignments") }}
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { useHead } from "@vueuse/head";
import { Badge, Button, createResource, Dialog } from "frappe-ui";
import { Bell, LogIn, User, Sun, Moon } from "lucide-vue-next";

import { onMounted, ref, computed } from "vue";

import { membershipStore } from "../stores/membership";
import { sessionStore } from "../stores/session";
import { usersStore } from "../stores/user";

import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import EmptyState from "../components/EmptyState.vue";
import EventCard from "../components/EventCard.vue";
import Member from "../components/MemberPlan.vue";
import Availability from "../components/Modals/Availability.vue";
import NoPermission from "../components/NoPermission.vue";
import Volunteer from "../components/Volunteer.vue";
import Welcome from "../components/Welcome.vue";
import { useScreenSize } from "@/utils/composables";
import { useTheme } from "frappe-ui";

const { isMobile } = useScreenSize();
const { currentTheme, setTheme } = useTheme();
const theme = computed({
	get() {
		if (currentTheme.value === "light") return "light";
		if (currentTheme.value === "dark") return "dark";
		return "system";
	},
	set(value) {
		setTheme(value);
	},
});

function changeTheme() {
	theme.value = theme.value === "light" ? "dark" : "light";
}
const isOpen = ref(false);
const showNotificationDialog = ref(false);
const setAvailability = ref(false);
const hasNotification = ref(false);
const assignedProjects = ref([]);

const { roleResource, userResource, presentSlots, isVolunteer, isMember } = usersStore();
const { events, currentMembership } = membershipStore();
const { isLoggedIn } = sessionStore();

const user = userResource;

const fecthAssignments = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.projects.fetch_assigned_projects",
	auto: true,
	onSuccess(data) {
		assignedProjects.value = data || [];
		hasNotification.value = assignedProjects.value.length > 0;
	},
});

const dashboardStats = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.volunteer.get_dashboard_stats",
	auto: true,
});

function updateAvailability() {
	presentSlots.reload();
	setAvailability.value = false;
}

onMounted(() => {
	if (isLoggedIn) {
		roleResource.reload();
		currentMembership.reload();
		events.reload();
	}
});

useHead({
	title: "VMMS",
});
</script>
