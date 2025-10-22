<template>
  <div
    class="container mx-auto px-4 md:px-8 py-4 md:py-8 min-h-screen bg-gray-50"
  >
    <ProfileHeader :form="form" class="mb-6 md:mb-10" />

    <div v-if="loading" class="text-center py-20 bg-white rounded-xl shadow-lg">
      <div class="flex flex-col items-center justify-center">
        <svg
          class="animate-spin h-8 w-8 text-red-600 mb-3"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          ></circle>
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
        <p class="text-gray-600 font-medium">Loading user details...</p>
      </div>
    </div>

    <div v-else class="bg-white shadow-xl rounded-xl p-4 sm:p-6 lg:p-8">
      <div
        class="flex overflow-x-auto border-b border-gray-200 whitespace-nowrap mb-6 -mx-4 sm:mx-0 px-4 sm:px-0"
      >
        <button
          v-for="(tab, i) in tabs"
          :key="i"
          @click="goToTab(i)"
          :class="[
            'py-3 px-3 sm:px-5 text-sm sm:text-base font-semibold transition-all duration-200 ease-in-out flex-shrink-0',
            currentTab === i
              ? 'border-b-4 border-red-600 text-red-700 bg-red-50/50' // Active Tab Styles
              : 'text-gray-600 hover:text-red-500 hover:border-b-4 hover:border-red-100', // Inactive Tab Styles
          ]"
        >
          {{ tab.title }}
        </button>
      </div>

      <div class="min-h-[400px] py-4">
        <component
          :is="tabs[currentTab].component"
          :form="form"
          @saved="handleSaved"
        />
      </div>

      <div class="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-100">
        <button
          v-if="currentTab > 0"
          class="flex items-center gap-1 px-4 py-2 text-sm font-medium bg-gray-100 text-gray-700 rounded-lg transition-colors hover:bg-gray-200 active:scale-95"
          @click="prevTab"
        >
          <svg
            class="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10 19l-7-7m0 0l7-7m-7 7h18"
            ></path>
          </svg>
          Back
        </button>
        <button
          v-if="currentTab < tabs.length - 1"
          class="flex items-center gap-1 px-4 py-2 text-sm font-bold bg-red-600 hover:bg-red-700 text-white rounded-lg shadow-md transition-all active:scale-95"
          @click="nextTab"
        >
          Next
          <svg
            class="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M14 5l7 7m0 0l-7 7m7-7H3"
            ></path>
          </svg>
        </button>
      </div>
    </div>

    <ErrorModal v-model="showErrorDialog" :errors="flatErrors" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { createResource, toast } from "frappe-ui";

// Component Imports
import PersonalInfo from "@/components/Profile/PersonalInfo.vue";
import CitizenshipDocuments from "@/components/Profile/CitizenshipDocuments.vue";
import QualificationsSkills from "@/components/Profile/QualificationsSkills.vue";
import HealthDisabilities from "@/components/Profile/HealthDisabilities.vue";
import ErrorModal from "@/components/Modals/ErrorModal.vue";
import ProfileHeader from "@/components/Profile/ProfileHeader.vue";

const loading = ref(true);
const showErrorDialog = ref(false);
const currentTab = ref(0);
const flatErrors = ref("");

const tabs = [
  { title: "Personal Info", component: PersonalInfo },
  { title: "Health & Disabilities", component: HealthDisabilities },
  { title: "Qualifications & Skills", component: QualificationsSkills },
  { title: "Documents", component: CitizenshipDocuments },
];

const form = reactive({});

function populateForm(data) {
  Object.keys(data).forEach((key) => {
    form[key] = data[key] !== null ? data[key] : "";
  });
}

const userDetailsResource = createResource({
  url: "non_profit.non_profit.api.get_user_details",
  auto: true,
  onSuccess(data) {
    if (data) populateForm(data);
    loading.value = false;
  },
  onError(err) {
    toast.error(err.message || "Failed to fetch user details");
    loading.value = false;
  },
});

function handleSaved(updatedData) {
  Object.assign(form, updatedData);
}

function updateTabFromHash() {
  if (typeof window !== "undefined") {
    const hash = window.location.hash.substring(1);
    const index = parseInt(hash.replace("tab-", ""), 10);
    if (!isNaN(index) && index >= 0 && index < tabs.length) {
      currentTab.value = index;
    } else {
      currentTab.value = 0;
      updateHash(0);
    }
  }
}

function updateHash(index) {
  if (typeof window !== "undefined") {
    window.location.hash = `tab-${index}`;
  }
}

function goToTab(i) {
  currentTab.value = i;
  updateHash(i);
}

function nextTab() {
  goToTab(Math.min(currentTab.value + 1, tabs.length - 1));
}

function prevTab() {
  goToTab(Math.max(currentTab.value - 1, 0));
}

onMounted(() => {
  updateTabFromHash();

  if (typeof window !== "undefined") {
    window.addEventListener("hashchange", updateTabFromHash);
  }

  if (!userDetailsResource.data) userDetailsResource.reload();
});
</script>
