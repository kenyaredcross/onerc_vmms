<template>
  <div class="p-5"></div>

  <div class="md:p-6 mx-auto w-3/4">
    <h1 class="text-3xl font-semibold">Projects</h1>
    <Badge></Badge>
  </div>

  <div class="md:p-6 mx-auto border rounded-lg shadow-sm bg-white w-3/4">
    <ListView
      class="h-[250px]"
      :columns="columns"
      :rows="rows"
      :options="options"
      row-key="id"
    >
      <template #cell="{ item, row, column }">
        <span class="font-medium text-ink-gray-7">
          {{ item }}
        </span>
      </template>
    </ListView>
  </div>
</template>

<script lang="ts" setup>
import { computed, inject, onMounted } from "vue";
import { createResource, ListView, Badge, toast } from "frappe-ui";
import { useRoute } from "vue-router";

const route = useRoute();
const user = inject<any>("$user");

onMounted(() => {
  if (!user.data) {
    toast.warning("You must be logged in to view this page");
    setTimeout(() => {
      window.location.href = "/login";
    }, 500);
  }
});

const projectParams = computed(() => {
  const status = route.params.status;
  if (status === "accepted") {
    return { accepted: 1 };
  }
  if (status === "rejected") {
    return { rejected: 1 };
  }
  return {};
});

const projects = createResource({
  url: "non_profit.non_profit.api.get_all_deployed_projects",
  auto: true,
  cache: ["projects"],
  makeParams(value) {
    return projectParams.value;
  },
});

const columns = [
  {
    label: "Project",
    key: "project_name",
    getLabel: ({ row }) => row.name,
    width: "200px",
  },
  {
    label: "Start Date",
    key: "expected_start_date",
    width: "200px",
  },
  {
    label: "End Date",
    key: "expected_end_date",
    width: "200px",
  },
  {
    label: "Project Type",
    key: "project_type",
    width: "200px",
  },
  {
    label: "Status",
    key: "status",
  },
];

const rows = computed(() => projects.data || []);

const options = {
  selectable: false,
  showTooltip: true,
  resizeColumn: true,
  emptyState: {
    title: "No projects found",
    description:
      "Be checking on notifications for a new project to get started",
  },
};
</script>
