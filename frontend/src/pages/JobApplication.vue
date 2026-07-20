<template>
	<div class="w-full mx-auto py-2 px-1">
		<div v-if="!isLoggedIn" class="text-center py-20">
			<LogIn class="w-16 h-16 text-gray-400 mx-auto mb-4" />
			<h2 class="text-3xl font-bold text-gray-900 mb-4">
				{{ __("Authentication Required") }}
			</h2>
			<p class="text-gray-600 mb-8">
				{{
					__(
						"Please log in to access your opportunity application details. Your application information is protected and only available to authenticated users."
					)
				}}
			</p>
			<Button
				variant="solid"
				class="bg-red-700 hover:bg-red-800 text-white px-6 py-3 rounded-lg"
				@click="redirectToLogin"
			>
				{{ __("Log In") }}
			</Button>
		</div>

		<div v-else>
			<h1 class="text-3xl font-bold text-gray-900 mb-8">{{ __("My Applications") }}</h1>

			<div v-if="applications.loading" class="text-center py-20">
				<p class="text-gray-500">{{ __("Loading applications...") }}</p>
			</div>

			<div v-else-if="!applications.data?.length" class="text-center py-20">
				<p class="text-gray-500">
					{{ __("You haven't applied for any opportunities yet.") }}
				</p>
			</div>

			<div v-else>
				<div v-if="jobTabs.length" class="mb-6">
					<TabButtons
						v-model="currentTab"
						:buttons="jobTabs"
						class="w-full sm:w-auto"
						active-class="bg-red-600 text-white"
						inactive-class="text-gray-700 hover:bg-gray-100"
					/>
				</div>

				<div
					v-if="filteredApplications.length"
					class="grid grid-cols-1 md:grid-cols-2 gap-6"
				>
					<router-link
						v-for="app in filteredApplications"
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
									{{ __(getCompanyAbbr(app.company)) }}
								</div>
							</div>

							<div class="flex-1">
								<div class="flex justify-between items-start">
									<h2 class="text-xl font-bold text-gray-900">
										{{
											__(
												app?.job_opening_details?.job_title ||
													app.job_title
											)
										}}
									</h2>
									<span
										class="px-3 py-1 text-xs font-semibold rounded-full"
										:class="statusClass(app.status, app.docstatus)"
									>
										{{
											app.docstatus === 2
												? __("Cancelled")
												: app.docstatus === 0
												? __("Draft")
												: __(app.status)
										}}
									</span>
								</div>
								<p class="text-red-700 font-medium">{{ __(app.company) }}</p>
								<p v-if="app.designation" class="text-gray-500 text-sm">
									<strong>{{ __("Designation") }}:</strong>
									{{ __(app.designation) }}
								</p>
							</div>
						</div>

						<div class="mt-4 text-sm text-gray-600">
							{{ __("Applied") }}
							{{ formatDistanceToNow(parseISO(app.creation), { addSuffix: true }) }}
						</div>
						<div class="mt-1 text-sm text-gray-600">
							{{ __("Modified") }}
							{{ formatDistanceToNow(parseISO(app.modified), { addSuffix: true }) }}
						</div>

						<div
							v-if="app.cover_letter"
							class="mt-4 p-3 bg-gray-50 rounded-lg text-sm text-gray-700"
						>
							<strong>{{ __("Cover Letter") }}:</strong>
							<div v-html="coverLetterPreview(app.cover_letter)"></div>
						</div>

						<div
							v-if="app.job_opening_details"
							class="mt-4 border-t pt-4 text-sm text-gray-700"
						>
							<p v-if="app.job_opening_details.job_status">
								<strong>{{ __("Opportunity Status") }}:</strong>
								{{ __(app.job_opening_details.job_status) }}
							</p>
							<p v-if="app.job_opening_details.posted_on">
								<strong>{{ __("Posted On") }}:</strong>
								{{ formatDate(app.job_opening_details.posted_on) }}
							</p>
							<p v-if="app.job_opening_details.closes_on">
								<strong>{{ __("Closes On") }}:</strong>
								{{ formatDate(app.job_opening_details.closes_on) }}
							</p>
							<p v-if="app.job_opening_details.job_description" class="mt-2">
								<strong>{{ __("Description") }}:</strong>
								{{ __(app.job_opening_details.job_description) }}
							</p>
						</div>
					</router-link>
				</div>

				<div v-else class="text-center py-20 text-gray-500">
					{{ __("No applications found under") }} "{{ __(currentTab) }}"
					{{ __("status.") }}
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { useHead } from "@vueuse/head";
import { format, formatDistanceToNow, parseISO } from "date-fns";
import { Button, createResource, TabButtons } from "frappe-ui";
import { LogIn } from "lucide-vue-next";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { sessionStore } from "../stores/session";
import { usersStore } from "../stores/user";
import NoPermission from "../components/NoPermission.vue";
import { sanitizeHtml } from "../utils/sanitizeHtml";

const coverLetterPreview = (text) => {
	if (!text) return "";
	const truncated = text.substring(0, 150) + (text.length > 150 ? "..." : "");
	return sanitizeHtml(truncated);
};

const { userResource } = usersStore();
const { isLoggedIn } = sessionStore();
const user = userResource;
const router = useRouter();

const applications = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.fetch_applications",
	makeParams() {
		return { email: user.data?.email };
	},
	auto: false,
});

watch(
	() => user.data?.email,
	(email) => {
		if (email) applications.reload();
	},
	{ immediate: true }
);

const redirectToLogin = () => router.push({ name: "Login" });

const getCompanyAbbr = (name) =>
	name
		? name
				.split(" ")
				.map((word) => word[0])
				.join("")
				.slice(0, 2)
				.toUpperCase()
		: "NA";

const statusClass = (status, docstatus) => {
	if (docstatus === 0) {
		return "bg-gray-200 text-gray-800";
	}
	if (docstatus === 2) {
		return "bg-red-200 text-red-800";
	}
	switch (status?.toLowerCase()) {
		case "open":
			return "bg-green-100 text-green-700";
		case "accepted":
			return "bg-blue-100 text-blue-700";
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

const currentTab = ref(null);

const jobTabs = computed(() => {
	if (!applications.data) return [];

	const tabs = [];

	if (applications.data.some((a) => a.docstatus === 0)) {
		tabs.push({ label: "Draft", value: "Draft" });
	}

	const submittedApplications = applications.data.filter((a) => a.docstatus === 1);
	const statuses = [...new Set(submittedApplications.map((a) => a.status).filter(Boolean))];

	const priority = {
		open: 1,
		"in progress": 2,
		"under review": 3,
		accepted: 4,
		closed: 5,
	};

	const orderedStatuses = statuses.sort((a, b) => {
		const aLower = a?.toLowerCase();
		const bLower = b?.toLowerCase();
		return (priority[aLower] || 99) - (priority[bLower] || 99);
	});

	orderedStatuses.forEach((status) => {
		tabs.push({
			label: status.charAt(0).toUpperCase() + status.slice(1),
			value: status,
		});
	});

	if (applications.data.some((a) => a.docstatus === 2)) {
		tabs.push({ label: "Cancelled", value: "Cancelled" });
	}

	if (!currentTab.value && tabs.length) currentTab.value = tabs[0].value;
	return tabs;
});

const filteredApplications = computed(() => {
	if (!applications.data || !currentTab.value) return [];

	const tabValue = currentTab.value.toLowerCase();

	if (tabValue === "draft") {
		return applications.data.filter((app) => app.docstatus === 0);
	} else if (tabValue === "cancelled") {
		return applications.data.filter((app) => app.docstatus === 2);
	} else {
		return applications.data.filter(
			(app) => app.docstatus === 1 && app.status?.toLowerCase() === tabValue
		);
	}
});

useHead({
	title: "My Applications | Kenya Red Cross VMMS",
	meta: [
		{
			name: "description",
			content:
				"Track and manage all your applications for Kenya Red Cross job and volunteer opportunities. View application status, details, and history.",
		},
	],
});
</script>
