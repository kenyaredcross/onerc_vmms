<template>
  <div
    class="group relative flex flex-col bg-white border border-gray-200 rounded-xl p-4 h-full shadow-sm hover:shadow-xl hover:border-red-300 transition-all duration-300 overflow-hidden"
  >
    <div
      class="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-500 via-red-400 to-orange-400"
    ></div>

    <div class="mb-3 flex flex-wrap gap-2">
      <div
        v-if="job.designation"
        class="inline-flex items-center gap-1 px-2 py-0.5 bg-red-50 border border-red-200 rounded-full text-xs font-medium text-red-700"
      >
        <User class="w-3 h-3" />
        <span>{{ job.designation }}</span>
      </div>
    </div>
    <h2
      class="text-lg font-bold text-gray-900 leading-tight mb-2 group-hover:text-red-600 transition-colors duration-200"
    >
      {{ job.job_title }}
    </h2>

    <div
      v-if="job.job_location"
      class="flex items-center gap-2 px-3 py-1 bg-red-100 border-l-4 border-red-500 rounded text-sm font-semibold text-red-800 mb-3"
    >
      <MapPin class="w-4 h-4 text-red-600 flex-shrink-0" />
      <span>{{ job.job_location }}</span>
    </div>

    <div
      class="h-px bg-gradient-to-r from-transparent via-gray-200 to-transparent mb-3"
    ></div>

    <div class="space-y-3 mb-4 flex-grow">
      <div class="grid grid-cols-2 gap-3">
        <div v-if="job.posted_on" class="flex items-center gap-2 min-w-0">
          <div
            class="flex-shrink-0 w-7 h-7 bg-green-50 rounded-md flex items-center justify-center"
          >
            <Calendar class="w-4 h-4 text-green-600" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs text-gray-500">
              Posted On:
              <span class="font-semibold text-gray-900">{{
                dayjs(job.posted_on).format("MMM D")
              }}</span>
            </p>
          </div>
        </div>

        <div v-if="job.closes_on" class="flex items-center gap-2 min-w-0">
          <div
            class="flex-shrink-0 w-7 h-7 bg-red-50 rounded-md flex items-center justify-center"
          >
            <CalendarX class="w-4 h-4 text-red-600" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs text-gray-500">
              Closes On:
              <span class="font-semibold text-gray-900">{{
                dayjs(job.closes_on).format("MMM D")
              }}</span>
            </p>
          </div>
        </div>
      </div>

      <div v-if="job.duration" class="flex items-center gap-2">
        <div
          class="flex-shrink-0 w-7 h-7 bg-blue-50 rounded-md flex items-center justify-center"
        >
          <Clock class="w-4 h-4 text-blue-600" />
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs text-gray-500">
            Open For:
            <span class="text-sm font-semibold text-gray-900">{{
              formatDuration(job.duration)
            }}</span>
          </p>
        </div>
      </div>
    </div>

    <div class="pt-3 border-t border-gray-100 mt-auto">
      <div class="flex items-center justify-between gap-4">
        <div
          v-if="job.creation"
          class="flex items-center gap-1.5 text-xs text-gray-500"
        >
          <History class="w-3 h-3" />
          <span>{{ dayjs().diff(dayjs(job.creation), "day") }}d ago</span>
        </div>

        <div
          v-if="job?.publish_applications_received && job.applicants"
          class="flex items-center gap-1.5 px-2 py-1 bg-gradient-to-r from-red-500 to-orange-500 rounded-md text-white shadow-sm"
        >
          <Users class="w-3.5 h-3.5" />
          <span class="text-sm font-bold leading-none">{{
            job.applicants
          }}</span>
          <span class="text-xs opacity-90 leading-none">applicants</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {
  Calendar,
  CalendarX,
  Clock,
  History,
  MapPin,
  User,
  Users,
} from "lucide-vue-next";
import { inject } from "vue";

const dayjs = inject("$dayjs");
const settings = inject("jobSettings", { showApplicants: true });

const props = defineProps({
  job: {
    type: Object,
    default: null,
  },
});

const formatDuration = (seconds) => {
  const SECONDS_IN_HOUR = 3600;
  const SECONDS_IN_DAY = SECONDS_IN_HOUR * 24;
  const SECONDS_IN_MONTH = SECONDS_IN_DAY * 30.437;

  const months = Math.floor(seconds / SECONDS_IN_MONTH);
  let remainingSeconds = seconds % SECONDS_IN_MONTH;

  const days = Math.floor(remainingSeconds / SECONDS_IN_DAY);
  remainingSeconds %= SECONDS_IN_DAY;

  const hours = Math.ceil(remainingSeconds / SECONDS_IN_HOUR);

  let parts = [];
  if (months > 0) {
    parts.push(`${months}m`);
  }
  if (days > 0) {
    parts.push(`${days}d`);
  }
  if (hours > 0 && months === 0) {
    parts.push(`${hours}h`);
  }

  return parts.join(" ");
};
</script>
