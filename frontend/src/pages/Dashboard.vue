<template>
	<NoPermission v-if="user?.data == 'Guest'" :page="__('Dashboard')" />

	<div v-if="isLoggedIn" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2 lg:py-8">
		<div :aria-busy="roleResource?.loading">
			<div v-if="roleResource?.loading" class="py-20 text-center">
				<ProgressSpinner :message="'Setting up Dashboard...'" />
			</div>

			<div v-else-if="roleResource?.data" class="grid grid-cols-1 gap-6">
				<Welcome v-if="!isVolunteer && !isMember" />

				<Member v-if="isMember" :membership-status="currentMembership?.data" />

				<section
					v-if="roleResource?.data && (isVolunteer || isMember)"
					class="bg-surface-base p-6 rounded-xl border border-outline-gray-2"
				>
					<div class="flex justify-between mb-4">
						<h2 class="text-2xl-bold">{{ __("Upcoming Events") }}</h2>
						<router-link
							to="/events"
							v-if="events.data && events.data.length > 3"
							class="text-sm-semibold text-red-600"
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
		</div>
	</div>
</template>

<script setup>
import { useHead } from "@vueuse/head";
import { storeToRefs } from "pinia";
import { onMounted } from "vue";

import { membershipStore } from "../stores/membership";
import { sessionStore } from "../stores/session";
import { usersStore } from "../stores/user";

import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import EmptyState from "../components/EmptyState.vue";
import EventCard from "../components/EventCard.vue";
import Member from "../components/MemberPlan.vue";
import NoPermission from "../components/NoPermission.vue";
import Welcome from "../components/Welcome.vue";

const userStore = usersStore();
const { roleResource, userResource } = userStore;
const { isVolunteer, isMember } = storeToRefs(userStore);
const { events, currentMembership } = membershipStore();
const { isLoggedIn } = sessionStore();

const user = userResource;

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
