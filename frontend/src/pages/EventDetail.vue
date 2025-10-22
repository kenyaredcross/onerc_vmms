<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
    <ProgressSpinner v-if="eventDetail.loading" />
    <ErrorMessage
      v-else-if="eventDetail.error"
      class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm my-auto mt-20"
      message="Failed to load Event Details"
    />
    <div v-else-if="eventDetail.data">
      <div class="relative overflow-hidden bg-white">
        <div
          class="absolute inset-0 bg-gradient-to-r from-red-300 to-transparent"
        ></div>
        <div
          class="max-w-7xl mx-auto px-4 sm:px-2 lg:px-8 py-8 lg:py-10 relative flex flex-col md:flex-row items-center gap-4 md:gap-10"
        >
          <div class="flex-1">
            <h1
              class="text-3xl sm:text-4xl md:text-5xl lg:text-[3.5rem] font-bold text-gray-800 mb-4 leading-tight"
            >
              {{ eventDetail.data?.title }}
            </h1>

            <div
              class="flex flex-wrap gap-4 sm:gap-6 text-gray-700 mb-4 sm:mb-6"
            >
              <div class="flex items-center gap-2 text-sm sm:text-base">
                <CalendarDays class="w-5 h-5 text-red-500" />
                <span
                  >{{ formatDate(eventDetail.data?.start_date) }} -
                  {{ formatDate(eventDetail.data?.end_date) }}</span
                >
              </div>
              <div class="flex items-center gap-2 text-sm sm:text-base">
                <Clock class="w-5 h-5 text-red-500" />
                <span>{{ eventDetail.data?.start_time }}</span>
              </div>
              <div class="flex items-center gap-2 text-sm sm:text-base">
                <MapPin class="w-5 h-5 text-red-500" />
                <span>{{ eventDetail.data?.venue }}</span>
              </div>
            </div>

            <div class="mb-6 sm:mb-8">
              <div v-if="eventDetail.data?.is_ticketed">
                <Button
                  v-if="!hasBookedTickets"
                  theme="red"
                  variant="solid"
                  size="lg"
                  @click="handleRegister(true)"
                >
                  Get Ticket
                </Button>
              </div>
              <div v-else>
                <Button
                  theme="red"
                  variant="solid"
                  size="lg"
                  @click="handleRegister(false)"
                >
                  Register Event
                </Button>
              </div>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div
                v-for="(value, key) in timeRemaining"
                :key="key"
                class="bg-red-50 border border-red-100 rounded-lg py-3 px-1 sm:py-4 text-center"
              >
                <div class="text-xl sm:text-3xl font-bold text-gray-800">
                  {{ value }}
                </div>
                <div class="text-xs sm:text-sm text-gray-600 uppercase mt-1">
                  {{ key }}
                </div>
              </div>
            </div>
          </div>

          <div class="">
            <img
              :src="eventDetail.data?.banner_image"
              alt="Event Image"
              class="w-full rounded-lg"
            />
          </div>
        </div>
      </div>

      <BookedTickets
        v-if="eventDetail.data?.booked_tickets?.length"
        :tickets="eventDetail.data.booked_tickets"
      />

      <div class="max-w-7xl mx-auto md:px-4 px-1 lg:px-8 py-6 lg:py-8">
        <div
          class="bg-white border border-gray-200 rounded-2xl p-6 sm:p-12 shadow-sm"
        >
          <h2 class="text-xl md:text-3xl font-extrabold text-red-500 mb-3">
            Why attend?
          </h2>
          <p class="text-base sm:text-lg text-gray-700 leading-relaxed mb-6">
            {{ eventDetail.data?.short_description }}
          </p>
          <hr class="my-4" />
          <p class="text-base sm:text-lg text-gray-700 leading-relaxed mb-6">
            {{ eventDetail.data?.about }}
          </p>
        </div>
      </div>

      <div class="max-w-7xl mx-auto md:px-4 px-2 lg:px-8 py-4 lg:py-8">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div
            v-if="speakerProfiles.data?.length"
            class="md:col-span-2 bg-white rounded-xl p-6 border border-gray-200 shadow-sm"
          >
            <div class="mb-6 flex items-center gap-3">
              <div
                class="w-10 h-10 flex items-center justify-center rounded-lg bg-red-50 border border-red-100"
              >
                <Users class="w-5 h-5 text-red-500" />
              </div>
              <h3 class="text-xl md:text-3xl font-extrabold text-gray-900">
                Featured Speakers
              </h3>
            </div>

            <ul class="space-y-4">
              <li
                v-for="speaker in speakerProfiles.data"
                :key="speaker.name"
                class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gray-50 border border-gray-200 rounded-lg p-4"
              >
                <div class="flex items-center gap-4">
                  <img
                    :src="speaker.display_image"
                    alt="Speaker Image"
                    class="w-16 h-16 sm:w-20 sm:h-20 rounded-full object-cover border border-gray-200"
                  />
                  <div>
                    <h4 class="text-lg font-semibold text-gray-800">
                      {{ speaker.full_name }}
                    </h4>
                    <p class="text-sm text-gray-600">
                      {{ speaker.designation }}
                    </p>
                    <p class="text-red-500 font-bold" v-if="speaker.company">
                      {{ speaker.company }}
                    </p>
                  </div>
                </div>

                <div>
                  <span class="">Social Links:</span>
                  <div class="flex items-center gap-3 sm:justify-end">
                    <a
                      v-for="link in speaker.social_media_links"
                      :key="link.name"
                      :href="link.url"
                      target="_blank"
                      class="text-gray-500 hover:text-red-500 transition"
                    >
                      <component
                        :is="getSocialMediaIcon(link.platform)"
                        class="w-5 h-5"
                      />
                    </a>
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div class="max-w-7xl mx-auto px-1 lg:px-8 pb-8 lg:pb-12">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div
            class="bg-white border border-gray-200 rounded-2xl p-6 sm:p-8 shadow-sm"
          >
            <h3
              class="text-xl md:text-2xl font-bold text-gray-800 mb-6 border-b border-gray-200 pb-3"
            >
              Event Details
            </h3>

            <div class="space-y-4 divide-y divide-gray-100">
              <div
                class="flex items-start gap-3 pt-1 first:pt-0"
                v-for="detail in [
                  {
                    icon: CalendarDays,
                    label: 'Date',
                    value:
                      formatDate(eventDetail.data?.start_date) +
                      ' - ' +
                      formatDate(eventDetail.data?.end_date),
                  },
                  {
                    icon: Clock,
                    label: 'Time',
                    value:
                      eventDetail.data?.start_time +
                      ' - ' +
                      eventDetail.data?.end_time,
                  },
                  {
                    icon: MapPin,
                    label: 'Venue',
                    value: eventDetail.data?.venue,
                  },
                  { icon: Users, label: 'Host', value: eventDetail.data?.host },
                ]"
                :key="detail.label"
              >
                <div
                  class="w-10 h-10 flex items-center justify-center rounded-lg bg-red-50 border border-red-100"
                >
                  <component :is="detail.icon" class="w-5 h-5 text-red-500" />
                </div>
                <div>
                  <div class="text-sm text-gray-500">{{ detail.label }}</div>
                  <div class="text-base font-medium text-gray-800">
                    {{ detail.value }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <AttendEventModal
    :eventId="eventDetail.data?.name"
    :dialogStatus="isOpen"
    @close="isOpen = false"
    v-model="isOpen"
  />
  <Ticket
    v-model="openTicketModal"
    :tickets="eventDetail.data?.tickets"
    :event="eventDetail.data?.name"
  />
</template>
<script setup>
import { Button, createResource, toast } from "frappe-ui";
import { CalendarDays, Clock, MapPin, Users } from "lucide-vue-next";
import { ref, onMounted, onUnmounted, inject, watch, computed } from "vue";
import { useRoute } from "vue-router";
import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import ErrorMessage from "frappe-ui/src/components/ErrorMessage/ErrorMessage.vue";
import {
  Twitter,
  Linkedin,
  Facebook,
  Instagram,
  Github,
  Globe,
  Youtube,
} from "lucide-vue-next";
import router from "../router";
import AttendEventModal from "../components/Modals/AttendEventModal.vue";
import Ticket from "../components/Modals/Ticket.vue";
import BookedTickets from "../components/BookedTickets.vue";

const showTickets = ref(false);
const toggleTickets = () => {
  showTickets.value = !showTickets.value;
};

const hasBookedTickets = computed(() => {
  return (
    eventDetail.data?.booked_tickets &&
    eventDetail.data.booked_tickets.length > 0
  );
});

const route = useRoute();
const eventName = ref(route.params.id);
const user = inject("$user");
const isOpen = ref(false);
const openTicketModal = ref(false);

const eventDetail = createResource({
  url: "non_profit.non_profit.api.get_event_details",
  makeParams() {
    return {
      event_name: eventName.value,
    };
  },
  auto: true,
  cache: ["event", eventName.value],
  onSuccess(data) {
    if (
      user?.data == "Guest" &&
      (eventDetail.data?.event_access === "Private" ||
        eventDetail.data?.event_access === "Members Only")
    ) {
      toast.error(
        "This is a private event. Please log in  to view event details."
      );
      setTimeout(() => {
        router.push({ name: "Login" });
      }, 3000);
    }
    speakerProfiles.reload();
  },
});

const timeRemaining = ref({
  days: 0,
  hours: 0,
  minutes: 0,
  seconds: 0,
});

let timerInterval = null;

const start_date = computed(() => {
  return eventDetail.data?.start_date || "";
});
const start_time = computed(() => {
  return eventDetail.data?.start_time || "";
});

watch([start_date, start_time], () => {
  if (start_date.value && start_time.value) {
    calculateTimeRemaining();
    if (timerInterval) {
      clearInterval(timerInterval);
    }
    timerInterval = setInterval(calculateTimeRemaining, 1000);
  }
});

const calculateTimeRemaining = () => {
  if (!start_date.value || !start_time.value) {
    return;
  }

  let timeStr = start_time.value.trim();
  if (!timeStr.includes(":")) {
    return;
  }

  let timeParts = timeStr.split(":");
  timeParts = timeParts.map((part) => part.padStart(2, "0"));

  if (timeParts.length === 2) {
    timeParts.push("00");
  }

  timeStr = timeParts.join(":");

  const dateTimeStr = `${start_date.value}T${timeStr}`;
  const startDateTime = new Date(dateTimeStr);

  if (isNaN(startDateTime.getTime())) {
    return;
  }

  const now = new Date();
  const difference = startDateTime - now;

  if (difference > 0) {
    timeRemaining.value = {
      days: Math.floor(difference / (1000 * 60 * 60 * 24)),
      hours: Math.floor((difference / (1000 * 60 * 60)) % 24),
      minutes: Math.floor((difference / 1000 / 60) % 60),
      seconds: Math.floor((difference / 1000) % 60),
    };
  } else {
    timeRemaining.value = {
      days: 0,
      hours: 0,
      minutes: 0,
      seconds: 0,
    };
  }
};

const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const handleRegister = (status) => {
  if (status) {
    openTicketModal.value = true;
  } else {
    isOpen.value = true;
  }
};

onMounted(() => {
  calculateTimeRemaining();
  timerInterval = setInterval(calculateTimeRemaining, 1000);
});

onUnmounted(() => {
  if (timerInterval) {
    clearInterval(timerInterval);
  }
});

const speakerProfiles = createResource({
  url: "non_profit.non_profit.api.get_speaker_profiles",
  auto: true,
  cache: ["speakers", eventName.value],
  makeParams() {
    const speakers = eventDetail.data?.featured_speakers || [];
    return {
      event_speakers: JSON.stringify(speakers),
    };
  },
});

function getSocialMediaIcon(platform) {
  switch (platform.toLowerCase()) {
    case "instagram":
      return Instagram;
    case "twitter":
    case "x":
      return Twitter;
    case "linkedin":
      return Linkedin;
    case "github":
      return Github;
    case "facebook":
      return Facebook;

    case "youtube":
      return Youtube;
    case "website":
      return Globe;
    default:
      return Globe;
  }
}
</script>
