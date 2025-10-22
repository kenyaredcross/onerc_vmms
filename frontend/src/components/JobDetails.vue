<template>
  <div v-if="job.data" class="mx-auto px-4 sm:px-6 pt-8 max-w-4xl">
    <div class="p-8 bg-white rounded-2xl shadow-sm border border-gray-100">
      <div
        class="flex flex-col sm:flex-row items-start sm:items-center gap-6 mb-8"
      >
        <img
          v-if="job.data.company_logo"
          :src="job.data.company_logo"
          class="w-20 h-20 sm:w-24 sm:h-24 rounded-xl object-contain bg-gray-50 border cursor-pointer"
          alt="Company Logo"
          @click="redirectToWebsite(job.data.website)"
        />
        <div
          v-else
          class="w-20 h-20 flex items-center justify-center rounded-xl bg-red-100 text-red-700 font-bold text-2xl"
        >
          {{ getCompanyAbbr(job.data.company) }}
        </div>

        <div class="flex-1">
          <h1 class="text-3xl font-bold text-gray-900">
            {{ job.data.job_title }}
          </h1>
          <p class="text-lg font-semibold text-red-600">
            {{ job.data.company }}
          </p>
          <p v-if="job.data.profession" class="text-sm text-gray-500 mt-1">
            Profession:
            <span class="font-medium text-gray-800">{{
              job.data.profession
            }}</span>
          </p>
          <p v-if="job.data.department" class="text-sm text-gray-500">
            Department:
            <span class="font-medium text-gray-800">{{
              job.data.department
            }}</span>
          </p>
        </div>
      </div>

      <div class="flex flex-wrap gap-3 mb-10">
        <Badge
          size="lg"
          class="bg-gray-50 text-gray-700 border border-gray-200"
        >
          <template #prefix
            ><CalendarDays class="w-4 h-4 stroke-2 text-gray-500"
          /></template>
          Posted {{ dayjs(job.data.creation).fromNow() }}
        </Badge>

        <Badge size="lg" class="bg-red-50 text-red-700 border border-red-200">
          <template #prefix
            ><ClipboardType class="w-4 h-4 stroke-2 text-red-600"
          /></template>
          {{ job.data.employment_type }}
        </Badge>

        <Badge
          size="lg"
          class="bg-blue-50 text-blue-700 border border-blue-200"
        >
          <template #prefix
            ><Briefcase class="w-4 h-4 stroke-2 text-blue-600"
          /></template>
          {{
            job.data.designation?.designation_name || job.data.designation?.name
          }}
        </Badge>

        <Badge
          v-if="job.data.minimum_years_of_experience"
          size="lg"
          class="bg-green-50 text-green-700 border border-green-200"
        >
          <template #prefix
            ><Award class="w-4 h-4 stroke-2 text-green-600"
          /></template>
          {{ job.data.minimum_years_of_experience }}+ Years
        </Badge>
      </div>

      <section v-if="job.data.required_skills?.length" class="mb-10">
        <h2 class="section-title"><CheckCircle class="icon" /> Core Skills</h2>
        <div class="section-card flex flex-wrap gap-2">
          <span
            v-for="(skill, idx) in job.data.required_skills"
            :key="idx"
            class="skill-badge"
          >
            <Check class="w-3 h-3 text-red-600" /> {{ skill?.skill }}
          </span>
        </div>
      </section>

      <section v-if="hasQualification(job.data)" class="mb-10">
        <h2 class="section-title"><FileText class="icon" /> Qualifications</h2>
        <div class="section-card grid sm:grid-cols-2 gap-6">
          <div>
            <p class="section-label">Minimum Qualification</p>
            <p class="section-value">
              {{ job.data.minimum_qualification_level }}
            </p>
          </div>
          <div>
            <p class="section-label">Field of Study</p>
            <p class="section-value">{{ job.data.preferred_field_of_study }}</p>
          </div>
          <div>
            <p class="section-label">Minimum GPA / Grade</p>
            <p class="section-value">{{ job.data.required_gpa__grade }}</p>
          </div>
          <div>
            <p class="section-label">Equivalent Experience</p>
            <p class="section-value">
              {{ job.data.allow_equivalent_experience ? "Yes" : "No" }}
            </p>
          </div>
        </div>
      </section>

      <section v-if="job.data.required_licences?.length" class="mb-10">
        <h2 class="section-title"><Award class="icon" /> Required Licenses</h2>
        <div class="section-card flex flex-wrap gap-2">
          <span
            v-for="(lic, idx) in job.data.required_licences"
            :key="idx"
            class="skill-badge"
          >
            <Check class="w-3 h-3 text-red-600" /> {{ lic?.license_type }}
          </span>
        </div>
      </section>

      <section v-if="job.data.description">
        <h2 class="section-title"><FileText class="icon" /> Job Description</h2>
        <div
          v-html="job.data.description"
          class="prose prose-sm max-w-none text-gray-700 mt-6 prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-gray-200 prose-th:border-gray-200 prose-th:bg-gray-50"
        ></div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { Badge } from "frappe-ui";
import {
  Check,
  CalendarDays,
  FileText,
  ClipboardType,
  Briefcase,
  Award,
  CheckCircle,
} from "lucide-vue-next";
import { inject } from "vue";

const props = defineProps({
  job: Object,
});

const dayjs = inject("$dayjs");

const redirectToWebsite = (url) => {
  if (url) window.open(url, "_blank");
};

const getCompanyAbbr = (name) =>
  name
    ? name
        .split(" ")
        .map((word) => word[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "NA";

const hasQualification = (job) =>
  job.minimum_qualification_level ||
  job.preferred_field_of_study ||
  job.required_gpa__grade ||
  job.allow_equivalent_experience;
</script>

<style scoped>
.section-title {
  @apply text-xl font-bold text-gray-900 mb-4 flex items-center gap-2;
}
.icon {
  @apply w-5 h-5 text-red-600;
}
.section-card {
  @apply p-6 bg-white rounded-xl border border-gray-100 shadow-sm;
}
.section-label {
  @apply text-xs font-semibold text-gray-500 uppercase tracking-wide;
}
.section-value {
  @apply mt-1 text-base font-medium text-gray-900;
}
.skill-badge {
  @apply px-3 py-1 rounded-full text-sm font-medium bg-red-50 text-red-700 border border-red-200 flex items-center gap-1 hover:bg-red-100 transition;
}
</style>
