<template>
  <div class="w-full mx-auto py-2 px-1">
    <div v-if="!isLoggedIn" class="text-center py-20">
      <LogIn class="w-16 h-16 text-gray-400 mx-auto mb-4" />
      <h2 class="text-3xl font-bold text-gray-900 mb-4">
        Authentication Required
      </h2>
      <p class="text-gray-600 mb-8">
        Please log in to access your job application details. Your application
        information is protected and only available to authenticated users.
      </p>
      <Button
        variant="solid"
        class="bg-red-700 hover:bg-red-800 text-white px-6 py-3 rounded-lg"
        @click="redirectToLogin"
      >
        Log In
      </Button>
    </div>

    <div v-else>
      <h1 class="text-3xl font-bold text-gray-900 mb-8">My Applications</h1>

      <div v-if="applications.loading" class="text-center py-20">
        <p class="text-gray-500">Loading applications...</p>
      </div>

      <div v-else-if="!applications.data?.length" class="text-center py-20">
        <p class="text-gray-500">You haven’t applied for any jobs yet.</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <router-link
          v-for="app in applications.data"
          :key="app.name"
          :to="{ name: 'JobApplicationDetail', params: { id: app.name } }"
          class="flex flex-col bg-gradient-to-br from-white via-red-50 to-red-100 border border-red-200 rounded-2xl p-6 h-full shadow-md hover:shadow-lg transition-all duration-300"
        >
          <div class="flex items-start gap-4">
            <div>
              <img
                v-if="app.job_opening_details?.company_logo"
                :src="app.job_opening_details.company_logo"
                class="w-14 h-14 rounded-lg object-contain bg-gray-50 border"
              />
              <div
                v-else
                class="w-14 h-14 flex items-center justify-center rounded-lg bg-red-100 text-red-700 font-bold"
              >
                {{ getCompanyAbbr(app.company) }}
              </div>
            </div>

            <div class="flex-1">
              <div class="flex justify-between items-start">
                <h2 class="text-xl font-bold text-gray-900">
                  {{ app?.job_opening_details?.job_title || app.job_title }}
                </h2>
                <span
                  class="px-3 py-1 text-xs font-semibold rounded-full"
                  :class="statusClass(app.status)"
                >
                  {{ app.status || "Unknown" }}
                </span>
              </div>
              <p class="text-red-700 font-medium">{{ app.company }}</p>

              <p v-if="app.designation" class="text-gray-500 text-sm">
                <strong>Designation:</strong> {{ app.designation }}
              </p>
            </div>
          </div>

          <div class="mt-4 text-sm text-gray-600">
            Applied
            {{
              formatDistanceToNow(parseISO(app.creation), { addSuffix: true })
            }}
          </div>
          <div class="mt-1 text-sm text-gray-600">
            Modified
            {{
              formatDistanceToNow(parseISO(app.modified), { addSuffix: true })
            }}
          </div>

          <div
            v-if="app.cover_letter"
            class="mt-4 p-3 bg-gray-50 rounded-lg text-sm text-gray-700"
          >
            <strong>Cover Letter:</strong>
            <div
              v-html="
                app.cover_letter.substring(0, 150) +
                (app.cover_letter.length > 150 ? '...' : '')
              "
            ></div>
          </div>

          <div
            v-if="app.job_opening_details"
            class="mt-4 border-t pt-4 text-sm text-gray-700"
          >
            <p v-if="app.job_opening_details.job_status">
              <strong>Job Status:</strong>
              {{ app.job_opening_details.job_status }}
            </p>
            <p v-if="app.job_opening_details.posted_on">
              <strong>Posted On:</strong>
              {{ formatDate(app.job_opening_details.posted_on) }}
            </p>
            <p v-if="app.job_opening_details.closes_on">
              <strong>Closes On:</strong>
              {{ formatDate(app.job_opening_details.closes_on) }}
            </p>
            <p v-if="app.job_opening_details.job_description" class="mt-2">
              <strong>Description:</strong>
              {{ app.job_opening_details.job_description }}
            </p>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject } from "vue";
import { useRouter } from "vue-router";
import { createResource, Button } from "frappe-ui";
import { LogIn } from "lucide-vue-next";
import { formatDistanceToNow, parseISO, format } from "date-fns";
import { usersStore } from "../stores/user";
import { sessionStore } from "../stores/session";

const { userResource } = usersStore();
const { isLoggedIn } = sessionStore();
const user = userResource;

const router = useRouter();

const applications = createResource({
  url: "non_profit.non_profit.api.fetch_applications",
  makeParams() {
    return { email: user.data?.email };
  },
  auto: true,
  reloadOn: () => !!user.data?.email,
});

const redirectToLogin = () => {
  router.push({ name: "Login" });
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

const statusClass = (status) => {
  switch (status?.toLowerCase()) {
    case "open":
      return "bg-green-100 text-green-700";
    case "closed":
      return "bg-red-100 text-red-700";
    case "in progress":
    case "under review":
      return "bg-yellow-100 text-yellow-700";
    default:
      return "bg-gray-100 text-gray-700";
  }
};

const formatDate = (date) => {
  try {
    return format(parseISO(date), "PPP");
  } catch {
    return date;
  }
};
</script>
