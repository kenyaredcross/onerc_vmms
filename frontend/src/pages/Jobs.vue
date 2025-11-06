<template>
	<div class="flex flex-col min-h-screen bg-gray-50">
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 sm:px-6 shadow-sm"
		>
			<div class="flex items-center space-x-4">
				<Breadcrumbs
					class="h-7 text-sm sm:text-base text-gray-600"
					:items="[{ label: __('Opportunities'), route: { name: 'Jobs' } }]"
				/>
				<div class="hidden sm:block text-xl font-bold text-red-600">
					{{
						__(currentTab) === __("Open")
							? __("{0} Open Opportunities").format(jobCount)
							: __("{0} My Applications").format(jobCount)
					}}
				</div>
			</div>
		</header>

		<main class="flex-1 min-w-0 p-4 sm:p-6 lg:p-8">
			<div class="flex justify-start mb-6 lg:mb-8">
				<TabButtons
					:buttons="jobTabs"
					v-model="currentTab"
					class="w-full sm:w-auto"
					active-class="bg-red-600 text-white"
					inactive-class="text-gray-700 hover:bg-gray-100"
				/>
			</div>

			<div v-if="currentTab === 'Open'">
				<div
					v-if="currentTab === 'Open'"
					class="bg-white rounded-xl shadow-sm p-4 sm:p-6 mb-6 space-y-6"
				>
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
						<FormControl
							type="text"
							:placeholder="__('Search opportunities...')"
							v-model="searchQuery"
							class="w-full"
							@input="updateJobs"
						>
							<template #prefix>
								<Search class="w-5 h-5 text-gray-400" />
							</template>
						</FormControl>
						<Link
							doctype="Designation"
							v-model="designation"
							:placeholder="__('Designation')"
							class="w-full"
							@change="updateJobs"
						/>
						<Link
							doctype="Profession"
							v-model="profession"
							:placeholder="__('Profession')"
							class="w-full"
							@change="updateJobs"
						/>
						<Link
							doctype="Location"
							v-model="job_location"
							:placeholder="__('Location')"
							class="w-full"
							@change="updateJobs"
						/>
						<MultiSelect
							doctype="Company Item"
							v-model="selectedRegions"
							:label="__('Region')"
							:mainField="'company'"
							:filters="{ organisation_type: 'Region' }"
							class="w-full"
							@change="onRegionChange"
						/>
						<MultiSelect
							doctype="Company Item"
							v-model="selectedBranches"
							:mainField="'company'"
							:label="__('Branch')"
							:filters="branchFilters"
							class="w-full"
							@change="updateJobs"
						/>

						<Button
							variant="ghost"
							class="justify-center text-red-600 hover:bg-red-50 border border-red-200"
							@click="clearFilters"
						>
							<span class="text-sm font-medium">{{ __("Clear All") }}</span>
						</Button>
					</div>
				</div>

				<div
					v-if="jobs.data?.length"
					class="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
				>
					<router-link
						v-for="job in jobs.data"
						:key="job.name"
						:to="{ name: 'JobDetail', params: { job: job.name } }"
						class="transition-transform duration-300 hover:scale-[1.02] transform"
					>
						<JobCard :job="job" />
					</router-link>
				</div>
				<EmptyState v-else :type="__('Job Openings')" />
			</div>

			<div v-else-if="currentTab === 'My Applications'">
				<JobApplication />
			</div>
		</main>
	</div>
</template>

<script setup>
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import EmptyState from "@/components/EmptyState.vue";
import JobCard from "@/components/JobCard.vue";
import { useHead } from "@vueuse/head";
import { Breadcrumbs, Button, createResource, FormControl, TabButtons } from "frappe-ui";
import { Search } from "lucide-vue-next";
import { computed, inject, onMounted, ref, watch } from "vue";
import { sessionStore } from "../stores/session";
import JobApplication from "./JobApplication.vue";

const user = inject("$user");
const { brand } = sessionStore();

const job_location = ref(null);
const designation = ref(null);
const profession = ref(null);
const searchQuery = ref("");
const selectedRegions = ref([]);
const selectedBranches = ref([]);
const showFilters = ref(false);
const filters = ref({});
const orFilters = ref({});
const jobCount = ref(0);
const readOnlyMode = window.read_only_mode;
const currentTab = ref("Open");

const jobTabs = computed(() => [
	{ label: __("Open"), value: "Open" },
	{ label: __("My Applications"), value: "My Applications" },
]);

const branchFilters = computed(() => {
	const baseFilter = { organisation_type: "Branch" };

	if (selectedRegions.value?.length) {
		const companyNames = selectedRegions.value.map((item) =>
			typeof item === "string" ? item : item.company,
		);

		baseFilter.parent_company = ["in", companyNames];
	}

	return baseFilter;
});

onMounted(() => {
	const queries = new URLSearchParams(location.search);
	if (queries.has("type")) job_location.value = queries.get("type");
	updateContent();
});

const jobs = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.get_job_openings",
	cache: ["jobs"],
});

const updateContent = () => {
	if (currentTab.value === "Open") {
		updateJobs();
	}
};

const updateJobs = () => {
	updateFilters();
	jobs.update({
		params: { filters: filters.value, orFilters: orFilters.value },
	});
	jobs.reload();
};

const updateFilters = () => {
	filters.value.status = "Open";

	if (job_location.value) filters.value.job_location = job_location.value;
	else delete filters.value.job_location;

	if (designation.value) filters.value.designation = designation.value;
	else delete filters.value.designation;

	if (profession.value) filters.value.profession = profession.value;
	else delete filters.value.profession;

	if (selectedRegions.value?.length) {
		const regionNames = selectedRegions.value.map((item) =>
			typeof item === "string" ? item : item.company,
		);
		filters.value.region = regionNames;
	} else {
		delete filters.value.region;
	}

	if (selectedBranches.value?.length) {
		const companyNames = selectedBranches.value.map((item) =>
			typeof item === "string" ? item : item.company,
		);
		filters.value.company = companyNames;
	} else {
		delete filters.value.company;
	}

	if (searchQuery.value) {
		orFilters.value = {
			job_title: ["like", `%${searchQuery.value}%`],
			company: ["like", `%${searchQuery.value}%`],
			location: ["like", `%${searchQuery.value}%`],
		};
	} else orFilters.value = {};
};

const onRegionChange = () => {
	selectedBranches.value = [];
	updateJobs();
};

const clearFilters = () => {
	selectedRegions.value = [];
	selectedBranches.value = [];
	job_location.value = null;
	designation.value = null;
	profession.value = null;
	searchQuery.value = "";
	updateJobs();
};

watch(currentTab, () => {
	updateContent();
	jobCount.value = 0;
});

watch([job_location, designation, profession, selectedBranches], () => {
	if (currentTab.value === "Open") {
		updateJobs();
	}
});

watch(selectedRegions, () => {
	if (currentTab.value === "Open") {
		onRegionChange();
	}
});

watch(jobs, () => {
	if (currentTab.value === "Open") {
		jobCount.value = jobs.data?.length || 0;
	}
});
useHead({
	title: "Opportunities | Kenya Red Cross",
	meta: [
		{
			name: "description",
			content:
				"Explore open opportunities with the Kenya Red Cross. Filter by location, profession, and designation, or manage your applications.",
		},
	],
});
</script>
