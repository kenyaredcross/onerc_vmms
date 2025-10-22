<template>
  <div class="p-5">
    <header
      class="flex justify-between items-center mt-5 md:max-w-7xl md:mx-auto"
    >
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
      <div class="flex justify-center mb-2">
        <TextInput
          type="search"
          size="sm"
          variant="outline"
          placeholder="Search by event name, location, or date"
          :disabled="false"
          :modelValue="searchTerm"
          @update:modelValue="(val) => (searchTerm = val)"
        />
      </div>

      <EventCard
        v-if="events.data && events.data.length > 0"
        v-for="event in events.data"
        :event="event"
      />
      <EmptyState
        v-if="!events.data || events.data.length === 0"
        type="Events"
      />
    </div>
  </div>
  <div class="px-8">
    <EventCalendar v-if="toggleEventView" :event="events.data" />
  </div>
</template>

<script lang="ts" setup>
import { onMounted, provide, ref, watch } from "vue";
import EventCard from "../components/EventCard.vue";
import { membershipStore } from "../stores/membership";
import { createResource, TextInput } from "frappe-ui";
import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import EmptyState from "../components/EmptyState.vue";
import ErrorMessage from "frappe-ui/src/components/ErrorMessage/ErrorMessage.vue";

const searchTerm = ref("");

const events = createResource({
  url: "non_profit.non_profit.api.get_events",
  auto: true,
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
