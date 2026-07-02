<template>
	<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
		<div class="flex items-start justify-between">
			<div class="flex-1">
				<div class="flex items-center gap-3 mb-3">
					<h1 class="text-3xl font-bold text-gray-900">
						{{ project.project.project_name }}
					</h1>
					<Badge :theme="getStatusTheme(project.project.status)" class="px-3 py-1">
						{{ project.project.status }}
					</Badge>
				</div>
				<p
					class="text-sm text-gray-500 font-mono bg-gray-50 px-2 py-1 rounded inline-block mb-4"
				>
					{{ project.project.name }}
				</p>
				<div class="flex items-center gap-6 text-sm text-gray-600">
					<span class="flex items-center gap-2">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
							/>
						</svg>
						{{ project.project.project_type }}
					</span>
					<span class="flex items-center gap-2">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						{{ formatDate(project.expected_start_date) }}
						{{ __("-") }}
						{{ formatDate(project.expected_end_date) }}
					</span>

					<Badge
						v-if="project.deployment_status"
						variant="subtle"
						:theme="
							project.deployment_status === 'Pending'
								? 'orange'
								: project.deployment_status === 'Rejected'
								? 'red'
								: 'green'
						"
						class="px-3 py-1"
						size="lg"
					>
						{{ __("Assignment") }} {{ project.deployment_status }}
					</Badge>
				</div>
			</div>
			<div class="flex items-center gap-3">
				<Badge :theme="getPriorityTheme(project.project.priority)" class="px-3 py-1">
					{{ project.project.priority }} {{ __("Priority") }}
				</Badge>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Badge } from "frappe-ui";

const props = defineProps({
	project: {
		type: Object,
		required: true,
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

const formatDate = (dateString) => {
	if (!dateString) return "Not set";
	return new Date(dateString).toLocaleDateString("en-US", {
		year: "numeric",
		month: "short",
		day: "numeric",
	});
};
</script>
