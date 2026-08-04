<template>
	<NoPermission v-if="!isLoggedIn" :page="__('Deployments')" />
	<div v-else class="flex flex-col min-h-screen bg-gray-50">
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 sm:px-6 shadow-md"
		>
			<div class="flex items-center space-x-4">
				<h1 class="text-2xl sm:text-3xl font-bold text-gray-800">
					{{ __("Deployments") }}
				</h1>
				<div class="text-lg font-bold text-red-600">
					<span class="hidden sm:inline-block text-xl">
						{{ __("{0} Deployments").format(filteredProjects.length) }}
					</span>
					<span class="sm:hidden text-base"> ({{ filteredProjects.length }}) </span>
				</div>
			</div>
		</header>

		<div class="flex-1 min-w-0 p-4 sm:p-6 lg:p-8">
			<div
				class="flex justify-start mb-6 lg:mb-8 overflow-x-auto whitespace-nowrap -mx-4 sm:mx-0 p-2 sm:p-0"
			>
				<TabButtons
					:buttons="projectTabs"
					:model-value="currentTab"
					@update:model-value="updateTabAndHash"
					class="min-w-max sm:w-auto"
					active-class="bg-red-600 text-white"
					inactive-class="text-gray-700 hover:bg-gray-100"
				/>
			</div>

			<div v-if="projects.loading" class="text-center py-10">
				<p class="text-gray-500 text-lg">{{ __("Loading deployments...") }}</p>
			</div>

			<div v-else-if="filteredProjects.length">
				<div class="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
					<router-link
						v-for="project in filteredProjects"
						:key="project.name"
						:to="{ name: 'DeploymentDetail', params: { id: project.name } }"
						class="transition-transform duration-300 hover:scale-[1.02] transform block"
					>
						<ProjectCard
							:project="project"
							:current-status="getProjectStatus(project)"
						/>
					</router-link>
				</div>
			</div>

			<EmptyState v-else :type="__('Deployments')" />
		</div>
	</div>
</template>

<script setup>
import EmptyState from "@/components/EmptyState.vue";
import ProjectCard from "@/components/Project/ProjectCard.vue";
import { useHead } from "@vueuse/head";
import { createResource, TabButtons, toast } from "frappe-ui";
import { computed, inject, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { sessionStore } from "../stores/session";
import NoPermission from "@/components/NoPermission.vue";

const route = useRoute();
const router = useRouter();
const defaultTab = "All";
const { isLoggedIn } = sessionStore();

const baseProjectTabs = [
	{ label: __("All"), value: "All" },
	{ label: __("Active"), value: "Active" },
	{ label: __("Pending Response"), value: "Pending Response" },
	{ label: __("Awaiting Deployment"), value: "Awaiting Deployment" },
	{ label: __("Declined Deployment"), value: "Declined Deployment" },
	{ label: __("Closed"), value: "Closed" },
];

const projectTabs = computed(() => baseProjectTabs);

const normalizeTabToHash = (tabName) => {
	return tabName.toLowerCase().replace(/\s+/g, "-");
};

const denormalizeHashToTab = (hash) => {
	const normalizedHash = hash.startsWith("#") ? hash.substring(1) : hash;

	const tab = projectTabs.value.find((t) => normalizeTabToHash(t.value) === normalizedHash);
	return tab ? tab.value : defaultTab;
};

const currentTab = ref(defaultTab);

watch(
	() => route.hash,
	(newHash) => {
		currentTab.value = denormalizeHashToTab(newHash);
	},
	{ immediate: true }
);

const updateTabAndHash = (newTabValue) => {
	currentTab.value = newTabValue;
	const hash = `#${normalizeTabToHash(newTabValue)}`;
	if (route.hash !== hash) {
		router.replace({ hash: hash });
	}
};

const projects = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.projects.get_all_deployed_projects",
	auto: true,
});

const allProjects = computed(() => projects.data || []);

const getProjectStatus = (project) => {
	if (project.deployment_status === "Rejected") return "Declined Deployment";
	if (project.docstatus === 0) {
		if (project.deployment_status === "Pending") return "Pending Response";
		if (project.deployment_status === "Accepted") return "Awaiting Deployment";
	}
	if (project.docstatus === 1 && project.deployment_status === "Accepted") {
		return project.project.status === "Open" ? "Active" : "Closed";
	}
	return "All";
};

const filteredProjects = computed(() => {
	if (currentTab.value === "All") return allProjects.value;

	return allProjects.value.filter((project) => getProjectStatus(project) === currentTab.value);
});

useHead({
	title: "My Deployments | Kenya Red Cross VMMS",
	meta: [
		{
			name: "description",
			content:
				"View the list of deployments you are currently involved in with the Kenya Red Cross. Track deployment dates, types, and your participation status.",
		},
	],
});
</script>
