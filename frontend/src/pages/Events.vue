<template>
	<div class="p-5">
		<header class="flex justify-between items-center mt-5 md:max-w-7xl md:mx-auto">
			<h1 class="text-3xl font-bold">{{ __("Events") }}</h1>
		</header>
	</div>
	<div class="md:mx-auto" :aria-busy="events.loading">
		<div
			class="md:w-1/2 mx-auto flex flex-col md:flex-row items-center gap-2 justify-start mb-2 px-4"
		>
			<TextInput
				type="search"
				size="lg"
				variant="outline"
				placeholder="Search by event name or location"
				:disabled="false"
				:modelValue="searchTerm"
				@update:modelValue="(val) => (searchTerm = val)"
				class="w-full md:w-1/2"
			/>
			<TabButtons
				:buttons="[
					{
						label: 'Upcoming',
						value: 'upcoming',
					},
					{
						label: 'All Events',
						value: 'all',
					},
				]"
				v-model="currentTab"
				class="w-1/4"
			/>
		</div>
		<ProgressSpinner v-if="events.loading" />
		<ErrorMessage
			v-else-if="events.error"
			class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm my-auto mt-20 w-3/4 mx-auto"
			message="Failed to load Events"
		/>

		<div v-else-if="events.data && events.data.length > 0">
			<div
				class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 w-3/4 mx-auto gap-6 m-10"
			>
				<EventCard v-for="event in events.data" :event="event" />
			</div>
		</div>
		<EmptyState v-else="!events.data || events.data.length === 0" type="Events" />
	</div>
	<div class="px-8">
		<EventCalendar v-if="toggleEventView" :event="events.data" />
	</div>
</template>

<script setup>
import { watchDebounced } from "@vueuse/core";
import { useHead } from "@vueuse/head";
import { createResource, TabButtons, TextInput } from "frappe-ui";
import { ref, watch } from "vue";
import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import EmptyState from "../components/EmptyState.vue";
import EventCard from "../components/EventCard.vue";

const searchTerm = ref("");
const currentTab = ref("upcoming");

watch(currentTab, (newTab) => {
	if (newTab) {
		events.reload();
	}
});

const events = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.events.get_events",
	auto: true,
	cache: searchTerm.value,
	makeParams() {
		return {
			search: searchTerm.value,
			event_type: currentTab.value,
		};
	},
});

watchDebounced(
	searchTerm,
	() => {
		events.reload();
	},
	{ debounce: 500, maxWait: 1000 }
);

useHead({
	title: "Upcoming Events | Kenya Red Cross VMMS",
	meta: [
		{
			name: "description",
			content:
				"Discover and register for upcoming Kenya Red Cross events, activities, and training sessions in your area. Search by name or location.",
		},
	],
});
</script>
