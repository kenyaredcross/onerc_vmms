<template>
	<div class="p-5">
		<header class="flex justify-between items-center mt-5 md:max-w-7xl md:mx-auto">
			<h1 class="text-3xl font-bold">Events</h1>
			<!-- <Button variant="solid" theme="red" @click="toggleEventViews">
        {{ toggleEventView ? "List" : "Calendar" }} View</Button
      > -->
		</header>
	</div>
	<div class="md:max-w- md:mx-auto">
		<ProgressSpinner v-if="events.loading" />
		<ErrorMessage
			v-if="events.error"
			class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm my-auto mt-20"
			message="Failed to load Events"
		/>
		<div>
			<div class="flex justify-center mb-2 px-2">
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

			<EventCard
				v-if="events.data && events.data.length > 0"
				v-for="event in events.data"
				:event="event"
			/>
			<EmptyState v-if="!events.data || events.data.length === 0" type="Events" />
		</div>
	</div>
	<div class="px-8">
		<EventCalendar v-if="toggleEventView" :event="events.data" />
	</div>
</template>

<script lang="ts" setup>
import { createResource, TextInput } from "frappe-ui";
import ErrorMessage from "frappe-ui/src/components/ErrorMessage/ErrorMessage.vue";
import { ref, watch } from "vue";
import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import EmptyState from "../components/EmptyState.vue";
import EventCard from "../components/EventCard.vue";

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

const toggleEventView = ref(false);

function toggleEventViews() {
	toggleEventView.value = !toggleEventView.value;
}

watch(searchTerm, () => {
	events.reload();
});
</script>
