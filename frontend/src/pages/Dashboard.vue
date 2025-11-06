<template>
	<NoPermission v-if="user?.data == 'Guest'" :page="__('Dashboard')" />
	<div v-if="user?.data && user?.data !== 'Guest'" class="max-w-7xl mx-auto">
		<div class="flex flex-col gap-2 my-6">
			<h1 class="text-lg md:text-4xl font-bold text-gray-900 ml-7">
				Welcome back, {{ user?.data?.full_name }}!
			</h1>
		</div>

		<div v-if="roleResource?.loading" class="text-center py-20">
			<p>{{ __("Setting Up Dashboard...") }}</p>
			<ProgressSpinner />
		</div>

		<div v-else-if="roleResource?.data">
			<Welcome v-if="!roleResource?.data?.is_volunteer && !roleResource?.data?.is_member" />
			<div v-if="roleResource?.data" class="mb-8 h-full">
				<Volunteer v-if="roleResource?.data?.is_volunteer" v-bind="dashboardStats?.data" />

				<Member
					:membership-status="currentMembership?.data"
					v-else-if="roleResource?.data?.is_member"
				/>
			</div>

			<section
				v-if="
					roleResource?.data &&
					(roleResource?.data?.is_volunteer || roleResource?.data?.is_member)
				"
				class="flex flex-col gap-4 md:p-6 bg-white shadow"
			>
				<div class="flex items-center justify-between">
					<h2 class="text-2xl font-semibold text-gray-900">
						{{ __("Upcoming Events") }}
					</h2>
					<router-link to="/events">
						<button
							class="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
						>
							{{ __("View All") }}
							<ChevronRight class="w-4 h-4" />
						</button>
					</router-link>
				</div>

				<div
					v-if="events?.data && events?.data.length > 0 && !toggleEventView"
					class="grid md:grid-cols-3 gap-4"
				>
					<EventCard
						v-for="event in events?.data.slice(0, 3)"
						:key="event.name"
						:event="event"
					/>
				</div>

				<EventCalendar v-if="toggleEventView" :event="events?.data" />

				<EmptyState
					v-if="events?.data && events?.data.length === 0"
					:type="__('Events')"
				/>
			</section>
		</div>
	</div>
</template>

<script setup>
import { useHead } from "@vueuse/head";
import { createResource } from "frappe-ui";
import { ChevronRight } from "lucide-vue-next";
import { onMounted, ref } from "vue";

import EmptyState from "../components/EmptyState.vue";
import EventCalendar from "../components/EventCalendar.vue";
import EventCard from "../components/EventCard.vue";
import Member from "../components/MemberPlan.vue";
import Volunteer from "../components/Volunteer.vue";
import Welcome from "../components/Welcome.vue";

import { membershipStore } from "../stores/membership";
import { sessionStore } from "../stores/session";
import { usersStore } from "../stores/user";

import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import NoPermission from "../components/NoPermission.vue";

const { roleResource, userResource } = usersStore();
const { events, currentMembership } = membershipStore();
const { isLoggedIn } = sessionStore();

const toggleEventView = ref(false);
const user = userResource;

onMounted(() => {
	if (isLoggedIn) {
		roleResource.reload();
		currentMembership.reload();
		events.reload();
	}
});

const dashboardStats = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.volunteer.get_dashboard_stats",
	auto: true,
});

function toggleEventViews() {
	toggleEventView.value = !toggleEventView.value;
}

useHead({
	title: "Volunteer/Member Dashboard | Kenya Red Cross VMMS",
	meta: [
		{
			name: "description",
			content:
				"Access your personal Kenya Red Cross dashboard. View project statistics, membership status, and upcoming events.",
		},
	],
});
</script>

<style scoped>
.max-h-screen::-webkit-scrollbar {
	width: 8px;
}
.max-h-screen::-webkit-scrollbar-thumb {
	background-color: rgba(0, 0, 0, 0.2);
	border-radius: 4px;
}
</style>
