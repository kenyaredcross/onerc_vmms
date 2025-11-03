<template>
	<div class="p-5">
		<header class="flex justify-between items-center mt-5 md:max-w-7xl md:mx-auto">
			<h1 class="text-3xl font-bold">Events</h1>
		</header>
	</div>
	<div class="md:max-w- md:mx-auto">
		<div class="flex justify-center mb-2 px-4">
			<TextInput
				type="search"
				size="lg"
				variant="outline"
				placeholder="Search by event name or location"
				:disabled="false"
				:modelValue="searchTerm"
				@update:modelValue="(val) => (searchTerm = val)"
				class="w-full md:w-1/3"
			/>
		</div>
		<ProgressSpinner v-if="events.loading" />
		<ErrorMessage
			v-else-if="events.error"
			class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm my-auto mt-20 w-3/4 mx-auto"
			message="Failed to load Events"
		/>

		<div v-else-if="events.data && events.data.length > 0">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 w-3/4 mx-auto gap-6 m-10">
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
import { createResource, TextInput } from "frappe-ui";
import { ref, watch } from "vue";
import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import EmptyState from "../components/EmptyState.vue";
import EventCard from "../components/EventCard.vue";
import { watchDebounced } from "@vueuse/core";

const searchTerm = ref("");

const events = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.events.get_events",
	auto: true,
	cache: searchTerm.value,
	makeParams() {
		return {
			search: searchTerm.value,
		};
	},
});

watchDebounced(
	searchTerm,
	() => {
		events.reload();
	},
	{ debounce: 500, maxWait: 1000 },
);

const toggleEventView = ref(false);

function toggleEventViews() {
	toggleEventView.value = !toggleEventView.value;
}
</script>
