<template>
  <div
    class="flex flex-col bg-gradient-to-br from-white via-red-50 to-red-100 border border-red-200 rounded-2xl p-6 h-full shadow-md hover:shadow-lg transition-all duration-300"
  >
    <div class="mb-4">
      <span class="text-lg font-semibold text-red-700">{{ job.company }}</span>
      <h2 class="text-2xl font-extrabold text-gray-900 leading-snug pt-4">
        {{ job.job_title }}
      </h2>
      <div class="mt-2 flex flex-col gap-1">
        <div v-if="job.department" class="flex items-center gap-1">
          <span
            class="text-sm text-gray-700 bg-gray-100 px-3 py-1 rounded-full border border-gray-200"
          >
            {{ job.department }}
          </span>
        </div>
      </div>
    </div>

    <div class="flex flex-wrap gap-3 mb-4">
      <div
        v-if="job.designation"
        class="px-3 py-1 rounded-full text-xs font-semibold bg-red-200 text-red-900 border border-red-300"
      >
        {{ job.designation }}
      </div>
      <div
        v-if="job.location || job.country"
        class="flex items-center gap-1 text-sm text-gray-700"
      >
        <MapPin class="w-4 h-4 text-red-500" />
        <span
          >{{ job.location }}{{ job.country ? `, ${job.country}` : "" }}</span
        >
      </div>
    </div>

    <p
      v-if="job.description"
      class="description text-sm text-gray-800 leading-relaxed mb-5"
    >
      {{ job.description }}
    </p>

    <div class="grid grid-cols-2 gap-y-3 text-sm mb-5">
      <div v-if="job.vacancies" class="flex items-center gap-1">
        <span class="font-semibold text-gray-900 text-base">{{
          job.vacancies
        }}</span>
        <span class="text-gray-700">
          {{ job.vacancies > 1 ? __("vacancies") : __("vacancy") }}
        </span>
      </div>
      <div v-if="job.applicants" class="flex items-center gap-1">
        <span class="font-semibold text-gray-900 text-base">{{
          job.applicants
        }}</span>
        <span class="text-gray-700">
          {{ job.applicants > 1 ? __("applicants") : __("applicant") }}
        </span>
      </div>
      <div v-if="job.posted_on">
        <span class="text-gray-600">Posted:</span>
        <span class="font-medium text-gray-900">
          {{ dayjs(job.posted_on).fromNow() }}
        </span>
      </div>
      <div v-if="job.closes_on">
        <span class="text-gray-600">Closes:</span>
        <span class="font-semibold text-red-700">
          {{ dayjs(job.closes_on).format("MMM D, YYYY") }}
        </span>
      </div>
      <div v-if="job.closed_on">
        <span class="text-gray-600">Closed:</span>
        <span class="font-medium text-gray-900">
          {{ dayjs(job.closed_on).format("MMM D, YYYY") }}
        </span>
      </div>
    </div>

    <div class="flex flex-wrap gap-2 mt-auto">
      <Badge
        v-if="job.employment_type"
        class="bg-red-200 text-red-900 border border-red-300"
      >
        {{ job.employment_type }}
      </Badge>
      <Badge
        v-if="job.computed_status"
        :class="{
          'bg-green-200 text-green-900 border border-green-300':
            job.computed_status === 'Open',
          'bg-gray-200 text-gray-800 border border-gray-300':
            job.computed_status === 'Closed',
          'bg-yellow-200 text-yellow-900 border border-yellow-300':
            job.computed_status === 'Upcoming' ||
            job.computed_status === 'Ending Soon',
          'bg-red-300 text-red-900 border border-red-400':
            job.computed_status === 'Expired',
        }"
      >
        {{ job.computed_status }}
      </Badge>
      <Badge class="bg-white/70 text-gray-700 border border-gray-300">
        {{ dayjs(job.creation).fromNow() }}
      </Badge>
    </div>
  </div>
</template>

<script setup>
import { inject } from "vue";
import { Badge } from "frappe-ui";
import { MapPin } from "lucide-vue-next";

const dayjs = inject("$dayjs");
const props = defineProps({
  job: {
    type: Object,
    default: null,
  },
});
</script>

<style>
.description {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.5;
}
</style>
