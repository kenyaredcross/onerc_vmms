<template>
	<div class="min-h-screen bg-gray-50">
		<div v-if="projectDetail.loading" class="flex items-center justify-center min-h-screen">
			<div class="flex flex-col justify-center items-center text-center text-red-800">
				<Spinner class="w-12" />
				<p class="text-gray-600">{{ __("Loading project details...") }}</p>
			</div>
		</div>

		<div v-else-if="projectDetail.error" class="flex items-center justify-center min-h-screen">
			<div class="text-center">
				<div
					class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4"
				>
					<svg
						class="w-8 h-8 text-red-600"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
						/>
					</svg>
				</div>
				<h3 class="text-lg font-medium text-gray-900 mb-2">
					{{ __("Error loading project") }}
				</h3>
				<Button theme="red" @click="projectDetail.reload()">{{ __("Try Again") }}</Button>
			</div>
		</div>

		<div v-else-if="projectDetail.data" class="max-w-6xl mx-auto px-6 py-8">
			<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
				<div class="flex items-start justify-between">
					<div class="flex-1">
						<div class="flex items-center gap-3 mb-3">
							<h1 class="text-3xl font-bold text-gray-900">
								{{ projectDetail.data.project.project_name }}
							</h1>
							<Badge
								:theme="getStatusTheme(projectDetail.data.project.status)"
								class="px-3 py-1"
							>
								{{ projectDetail.data.project.status }}
							</Badge>
						</div>
						<p
							class="text-sm text-gray-500 font-mono bg-gray-50 px-2 py-1 rounded inline-block mb-4"
						>
							{{ projectDetail.data.project.name }}
						</p>
						<div class="flex items-center gap-6 text-sm text-gray-600">
							<span class="flex items-center gap-2">
								<svg
									class="w-4 h-4"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
									/>
								</svg>
								{{ projectDetail.data.project.project_type }}
							</span>
							<span class="flex items-center gap-2">
								<svg
									class="w-4 h-4"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
									/>
								</svg>
								{{ formatDate(projectDetail.data.expected_start_date) }}
								{{ __("-") }}
								{{ formatDate(projectDetail.data.expected_end_date) }}
							</span>

							<Badge
								v-if="projectDetail.data.status"
								variant="subtle"
								:theme="
									projectDetail.data.status === 'Pending'
										? 'orange'
										: projectDetail.data.status === 'Rejected'
											? 'red'
											: 'green'
								"
								class="px-3 py-1"
								size="lg"
							>
								{{ __("Assignment") }} {{ projectDetail.data.status }}
							</Badge>
						</div>
					</div>
					<div class="flex items-center gap-3">
						<Badge
							:theme="getPriorityTheme(projectDetail.data.project.priority)"
							class="px-3 py-1"
						>
							{{ projectDetail.data.project.priority }} {{ __("Priority") }}
						</Badge>
					</div>
				</div>
			</div>

			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<div class="lg:col-span-2 space-y-6">
					<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
						<h2 class="text-lg font-semibold text-gray-900 mb-4">
							{{ __("Project Progress") }}
						</h2>
						<div class="space-y-4">
							<div class="flex items-center justify-between text-sm">
								<span class="text-gray-600">{{ __("Completion") }}</span>
								<span class="font-medium text-gray-900"
									>{{ projectDetail.data.project.percent_complete }}%</span
								>
							</div>
							<div class="w-full bg-gray-200 rounded-full h-3">
								<div
									class="bg-red-600 h-3 rounded-full transition-all duration-500"
									:style="{
										width: `${projectDetail.data.project.percent_complete}%`,
									}"
								></div>
							</div>
						</div>
					</div>

					<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
						<h2 class="text-lg font-semibold text-gray-900 mb-4">{{ __("Notes") }}</h2>
						<div
							v-if="projectDetail.data.notes"
							class="prose prose-sm max-w-none text-gray-700"
						>
							{{ projectDetail.data.project.notes }}
						</div>
						<div v-else class="text-gray-500 italic">
							{{ __("No notes available for this project.") }}
						</div>
					</div>
					<TORDetails
						:term-details="projectDetail.data.term_details"
						:tor-url="projectDetail.data.tor_url"
					/>
				</div>
				<div class="space-y-6">
					<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
						<h2 class="text-lg font-semibold text-gray-900 mb-4">
							{{ __("Project Information") }}
						</h2>
						<div class="space-y-4">
							<div>
								<label class="text-sm font-medium text-gray-600">{{
									__("Status")
								}}</label>
								<p class="text-sm text-gray-900 mt-1 flex items-center gap-2">
									<span
										class="w-2 h-2 rounded-full"
										:class="getStatusColor(projectDetail.data.project.status)"
									></span>
									{{ projectDetail.data.project.status }}
								</p>
							</div>
							<div>
								<label class="text-sm font-medium text-gray-600">{{
									__("Active")
								}}</label>
								<p class="text-sm text-gray-900 mt-1">
									{{ projectDetail.data.project.is_active }}
								</p>
							</div>
							<div>
								<label class="text-sm font-medium text-gray-600">{{
									__("Location")
								}}</label>
								<p class="text-sm text-gray-900 mt-1">
									{{ projectDetail.data.location }}
								</p>
							</div>
						</div>
					</div>
					<div
						v-if="
							projectDetail?.data?.status === 'Pending' &&
							projectDetail?.data?.require_contract_before_deployment &&
							!projectDetail?.data?.contract?.name
						"
						class="w-full flex items-center justify-center rounded-lg border border-yellow-300 bg-yellow-50 px-8 py-4 text-sm font-medium text-yellow-700 shadow-sm"
					>
						<svg
							class="h-4 w-4 mr-2 text-yellow-500"
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 9v2m0 4h.01M12 5.5a7.5 7.5 0 100 15 7.5 7.5 0 000-15z"
							/>
						</svg>
						<div class="flex-1">
							<h3 class="text-sm font-semibold text-yellow-800 mb-1">
								{{ __("Contract Pending") }}
							</h3>
							<p class="text-sm text-yellow-700">
								{{
									__(
										"A signed contract is required before you can accept this project. Please wait, or contact the project manager for assistance.",
									)
								}}
							</p>
						</div>
					</div>

					<div
						v-else-if="projectDetail?.data?.status === 'Pending'"
						class="bg-white rounded-xl shadow-lg border border-red-300 p-8"
					>
						<h2
							class="flex flex-row items-center gap-2 text-2xl font-bold text-red-700 mb-4"
						>
							<Badge variant="subtle" theme="red">{{
								__("Action Required:")
							}}</Badge>
							<span>{{ __("Project Decision") }}</span>
						</h2>

						<div class="mb-6">
							<p class="text-sm text-gray-700 font-medium mb-2">
								{{
									__(
										"Important: Please review the official project information before you decide.",
									)
								}}
							</p>

							<div
								class="flex justify-center"
								v-if="projectDetail?.data?.contract?.name"
							>
								<Button
									@click="downloadContract(projectDetail?.data?.contract?.name)"
									:loading="loading"
									theme="red"
									variant="solid"
								>
									{{ __("Download Contract") }}
								</Button>
							</div>
						</div>

						<p class="text-sm text-gray-500 italic mb-6">
							{{
								__(
									"Your decision to accept this project confirms your agreement to the terms outlined.",
								)
							}}
						</p>

						<div class="flex gap-3">
							<Button theme="green" class="flex-1" @click="acceptDialog = true">
								{{ __("Accept Project") }}
							</Button>
							<Button
								theme="red"
								variant="outline"
								class="flex-1"
								@click="rejectAssignment(projectDetail.data.name)"
								:loading="assignmentDecision.loading"
							>
								{{ __("Reject Project") }}
							</Button>
						</div>

						<ErrorMessage :message="assignmentDecision.error" class="mt-4" />
						<ErrorMessage :message="downloadError" class="mt-4" />
					</div>
				</div>
			</div>
		</div>
	</div>

	<Dialog v-model="acceptDialog">
		<template #body-title>
			<h3 class="text-2xl font-semibold text-gray-900">{{ __("Confirm Action") }}</h3>
		</template>

		<template #body-content>
			<div class="space-y-4 text-gray-700">
				<p>
					{{
						__(
							"By confirming, you acknowledge that you have read the contract details and terms of reference, and that you accept the project.",
						)
					}}
				</p>
				<p class="text-sm text-gray-500 italic">
					{{ __("Accepting means you agree to the documents provided.") }}
				</p>
			</div>
		</template>

		<template #actions="{ close }">
			<div class="flex space-x-2">
				<Button
					theme="red"
					variant="solid"
					:loading="assignmentDecision.loading"
					@click="
						acceptAssignment(
							projectDetail?.data?.name,
							projectDetail?.data?.contract?.name,
						)
					"
				>
					{{ __("Confirm") }}
				</Button>
				<Button variant="outline" @click="close()">{{ __("Cancel") }}</Button>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import TORDetails from "@/components/TORDetails.vue";
import { useHead } from "@vueuse/head";
import { Badge, Button, createResource, Dialog, ErrorMessage, Spinner, toast } from "frappe-ui";
import { computed, inject, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import router from "../router";

const route = useRoute();
const user = inject("$user");
const acceptDialog = ref(false);
const downloadError = ref("");
const loading = ref(false);

onMounted(() => {
	if (!user.data) {
		toast.warning("You must be logged in to view this page");
		setTimeout(() => {
			router.push("/login");
		}, 500);
	}
});

const projectParams = computed(() => {
	return route.params.id;
});

const projectDetail = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.projects.get_assignment_details",
	auto: true,
	cache: ["project_detail", projectParams.value],
	makeParams() {
		return { assignment_name: projectParams.value };
	},
});

const getStatusTheme = (status) => {
	const statusMap = {
		Open: "blue",
		Working: "orange",
		Completed: "green",
		Cancelled: "red",
	};
	return statusMap[status] || "gray";
};

const getPriorityTheme = (priority) => {
	const priorityMap = {
		High: "red",
		Medium: "orange",
		Low: "green",
	};
	return priorityMap[priority] || "gray";
};

const getStatusColor = (status) => {
	const colorMap = {
		Open: "bg-blue-500",
		Working: "bg-orange-500",
		Completed: "bg-green-500",
		Cancelled: "bg-red-500",
		"On Hold": "bg-yellow-500",
	};
	return colorMap[status] || "bg-gray-500";
};

const formatDate = (dateString) => {
	if (!dateString) return "Not set";
	return new Date(dateString).toLocaleDateString("en-US", {
		year: "numeric",
		month: "short",
		day: "numeric",
	});
};

const acceptAssignment = (deploymentAssignment, contractName) => {
	assignmentDecision.submit({
		name: deploymentAssignment,
		accepted: true,
		contract_name: contractName,
	});
};

const rejectAssignment = (deploymentAssignment) => {
	assignmentDecision.submit({ name: deploymentAssignment, accepted: false });
};

const assignmentDecision = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.projects.accept_assignment",
	makeParams(values) {
		return values;
	},
	onSuccess() {
		acceptDialog.value = false;
		toast.success("Your decision has been recorded.");
		projectDetail.reload();
	},
});

const downloadContract = (contractName) => {
	loading.value = true;

	let headers = { "X-Frappe-Site-Name": window.location.hostname };
	if (window.csrf_token) {
		headers["X-Frappe-CSRF-Token"] = window.csrf_token;
	}

	fetch("/api/method/frappe.utils.print_format.download_pdf", {
		method: "POST",
		headers,
		body: new URLSearchParams({
			doctype: "Contract",
			name: contractName,
		}),
	})
		.then((response) => {
			if (response.ok) {
				return response.blob();
			} else {
				downloadError.value = "Failed to download PDF";
			}
		})
		.then((blob) => {
			if (!blob) return;
			const blobUrl = window.URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = blobUrl;
			link.download = `${contractName}.pdf`;
			link.click();

			setTimeout(() => {
				window.URL.revokeObjectURL(blobUrl);
			}, 3000);
		})
		.catch((error) => {
			downloadError.value = `Failed to download PDF: ${error.message}`;
		})
		.finally(() => {
			loading.value = false;
		});
};

useHead({
	title: "Project Assignment Details | Kenya Red Cross",
	meta: [
		{
			name: "description",
			content:
				"View details for your assigned Kenya Red Cross project, including progress, timeline, and assignment decision (Accept/Reject).",
		},
	],
});
</script>
