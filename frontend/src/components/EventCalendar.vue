<template>
  <div class="flex h-screen flex-col overflow-hidden p-5">
    <Calendar
      :config="{
        defaultMode: 'Month',
        eventIcons: {},
        allowCustomClickEvents: true,
        enableShortcuts: false,
      }"
      :events="calendarEvents"
      :onClick="handleEventClick"
    />
  </div>

  <div v-if="event && selectedEvent">
    <AttendEventModal
      v-model="attendModal"
      :event="selectedEvent"
      @confirmed="handleConfirmed"
    />
  </div>
</template>

<script lang="ts" setup>
import { Calendar, toast } from "frappe-ui";
import { computed, inject, ref } from "vue";
import AttendEventModal from "./Modals/AttendEventModal.vue";

const props = defineProps<{
  event: Array<any>;
}>();
const reloadConfirmStatus = inject<() => void>("reloadConfirmStatus");

const selectedEvent = ref<any>();
const attendModal = ref(false);

const calendarEvents = computed(() =>
  props.event.map((ev) => ({
    title: ev.title,
    participant: ev.event_category,
    id: ev.name,
    venue: ev.venue,
    fromDate: ev.start_date,
    toDate: ev.end_date,
    fromTime: ev.start_time,
    toTime: ev.end_time,
    originalEvent: ev,
  }))
);

function handleEventClick({ e, calendarEvent }: any) {
  if (calendarEvent.originalEvent) {
    selectedEvent.value = calendarEvent.originalEvent;
  } else {
    const originalEvent = props.event.find(
      (ev) => ev.name === calendarEvent.id
    );
    selectedEvent.value = originalEvent || {
      description: "",
      status: "",
      subject: calendarEvent.title,
      event_category: calendarEvent.participant,
      name: calendarEvent.id,
      event_type: calendarEvent.venue,
      starts_on: calendarEvent.fromDate,
      ends_on: calendarEvent.toDate,
      color: calendarEvent.color,
    };
  }

  attendModal.value = true;
}

function handleConfirmed() {
  if (reloadConfirmStatus) {
    reloadConfirmStatus();
  }
  toast.success("You successfully registered for the event");
}
</script>
