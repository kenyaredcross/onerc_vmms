<template>
  <div>
    <div
      class="flex flex-col md:flex-row md:justify-end md:items-center gap-3 md:gap-4 p-4 md:m-6"
    >
      <div
        v-if="!presentSlots.data"
        class="flex items-center justify-center order-2 md:order-1"
      >
        <p
          class="text-sm text-center border border-blue-600 px-2 py-1 bg-blue-100 rounded-lg text-blue-600 font-medium"
        >
          Action Required: Please set your availability.
        </p>
      </div>

      <div
        class="flex flex-row justify-between md:justify-end items-center gap-3 md:gap-4 order-1 md:order-2"
      >
        <Button
          variant="solid"
          size="md"
          theme="red"
          @click="setAvailability = true"
          class="rounded-xl shadow-md w-full sm:w-auto"
        >
          Set Availability
        </Button>

        <div
          class="relative cursor-pointer"
          @click="showNotificationDialog = true"
        >
          <div
            class="relative inline-block"
            :class="{ 'animate-bounce': hasNotification }"
          >
            <Bell class="h-7 w-7 text-gray-700" />
            <span
              v-if="hasNotification"
              class="absolute -top-1 -right-1 block h-3 w-3 rounded-full bg-red-600 ring-2 ring-white"
            ></span>
          </div>
        </div>
      </div>
    </div>

    <Dialog :options="{ size: 'lg' }" v-model="showNotificationDialog">
      <template #body-title>
        <div class="flex items-center justify-between">
          <h3 class="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <div
              class="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center"
            >
              <Bell class="h-5 w-5 text-red-600" />
            </div>
            New  Assignment
          </h3>

          <Badge variant="outline" theme="red" class="ml-2">
            {{ assignedProjects.length }} new
          </Badge>
        </div>
      </template>

      <template #body-content>
        <div v-if="assignedProjects.length" class="space-y-3">
          <div
            v-for="project in assignedProjects"
            :key="project.name"
            class="bg-gradient-to-r from-white to-gray-50 rounded-xl shadow-sm border border-gray-100 p-6"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <div class="flex items-center gap-3 mb-2">
                  <h4 class="text-lg font-semibold text-gray-900">
                    {{ project.project_name }}
                  </h4>
                  <Badge
                    :theme="priorityTheme(project.priority)"
                    class="px-2.5 py-0.5 text-xs rounded-full font-medium"
                  >
                    {{ project.priority }}
                  </Badge>
                </div>
                <p
                  class="text-sm text-gray-500 font-mono bg-gray-50 px-2 py-1 rounded inline-block"
                >
                  {{ project.name }}
                </p>
              </div>

              <router-link
                :to="{
                  name: 'AssignmentDetail',
                  params: { id: project.deployment_name },
                }"
                class="ml-4"
              >
                <Button variant="solid" theme="red"> View Details </Button>
              </router-link>
            </div>
          </div>
        </div>

        <div
          v-else
          class="flex flex-col items-center justify-center text-center py-16"
        >
          <div
            class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4"
          >
            <Bell class="h-8 w-8 text-gray-400" />
          </div>
          <h4 class="text-lg font-medium text-gray-900 mb-2">All caught up!</h4>
          <p class="text-sm text-gray-500 max-w-sm">
            No new project assignments at the moment. We'll notify you when new
            ones arrive.
          </p>
        </div>
      </template>
    </Dialog>
  </div>

  <div class="px-10">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 my-8">
      <div
        class="cursor-pointer p-6 flex flex-col w-full bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200"
      >
        <h4
          class="text-sm font-medium text-gray-600 uppercase tracking-wide mb-3"
        >
          Total Assignments
        </h4>
        <div class="text-3xl font-bold text-gray-900 mb-1">
          {{ props.total_projects_deployed || 0 }}
        </div>
        <div class="text-xs text-gray-500">All assignments</div>
      </div>

      <div
        @click="showNotificationDialog = true"
        class="cursor-pointer p-6 flex flex-col w-full bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200"
      >
        <h4
          class="text-sm font-medium text-gray-600 uppercase tracking-wide mb-3"
        >
          Pending
        </h4>
        <div class="text-3xl font-bold text-amber-600 mb-1">
          {{ props.pending_projects || 0 }}
        </div>
        <div class="text-xs text-gray-500">Awaiting response</div>
      </div>

      <div
        class="cursor-pointer p-6 flex flex-col w-full bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200"
      >
        <h4
          class="text-sm font-medium text-gray-600 uppercase tracking-wide mb-3"
        >
          Accepted
        </h4>
        <div class="text-3xl font-bold text-green-600 mb-1">
          {{ props.accepted_projects || 0 }}
        </div>
        <div class="text-xs text-gray-500">Ongoing assignments</div>
      </div>

      <div
        class="cursor-pointer p-6 flex flex-col w-full bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200"
      >
        <h4
          class="text-sm font-medium text-gray-600 uppercase tracking-wide mb-3"
        >
          Rejected
        </h4>
        <div class="text-3xl font-bold text-red-600 mb-1">
          {{ props.rejected_projects || 0 }}
        </div>
        <div class="text-xs text-gray-500">Declined assignments</div>
      </div>
    </div>
  </div>

  <Availability
    @success="updateAvailability"
    v-model="setAvailability"
    @cancel="updateAvailability(true)"
  />
</template>

<script lang="ts" setup>
import { ref } from "vue";
import { Dialog, Button, createResource, Badge, toast } from "frappe-ui";
import { Bell, LucideCalendar } from "lucide-vue-next";
import Availability from "./Modals/Availability.vue";
import { usersStore } from "../stores/user";

interface Task {
  name: string;
  subject: string;
  description: string;
  exp_start_date: string | null;
  exp_end_date: string | null;
  priority: string;
  status: string;
  project: string;
}

interface Project {
  deployment_name: string;
  expected_end_date: string;
  expected_start_date: string;
  is_active: string;
  name: string;
  notes: string;
  percent_complete: number;
  priority: string;
  project_name: string;
  project_type: string;
  status: string;
  task?: Task;
}

const props = defineProps<{
  total_projects_deployed: number;
  pending_projects: number;
  accepted_projects: number;
  rejected_projects: number;
}>();

const hasNotification = ref(false);
const showNotificationDialog = ref(false);
const setAvailability = ref(false);

const assignedProjects = ref<Project[]>([]);

const fecthAssignments = createResource({
  url: "non_profit.non_profit.api.fetch_assigned_projects",
  auto: true,
  onSuccess(data) {
    assignedProjects.value = data || [];
    hasNotification.value = assignedProjects.value.length > 0;
  },
});

const { presentSlots } = usersStore();

// Priority theme
function priorityTheme(priority: string) {
  switch (priority) {
    case "High":
      return "red";
    case "Medium":
      return "orange";
    case "Low":
      return "green";
    default:
      return "gray";
  }
}

function updateAvailability(cancelled = false) {
  presentSlots.reload();
  toast.success("Availability updated successfully");

  setAvailability.value = false;
}
</script>
