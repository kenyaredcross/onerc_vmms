<template>
	<div
		class="group relative flex flex-col bg-white border border-gray-200 rounded-lg p-4 h-full shadow-md hover:shadow-xl hover:border-red-400 transition-all duration-300 overflow-hidden"
	>
		<div
			class="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-red-500 via-red-400 to-orange-400"
		></div>

		<div class="mb-1">
			<h2
				class="text-lg font-bold text-gray-900 leading-tight group-hover:text-red-700 transition-colors duration-200"
			>
				{{ __(project?.deployment?.title || project.name) }}
			</h2>

			<div
				v-if="project?.project?.project_name || project.project_name"
				class="flex items-center gap-2 mt-1"
			>
				<span class="text-xs font-semibold text-red-600 bg-red-100 px-2 py-1 rounded-md">
					{{ __("Project: ") + __(project?.project?.project_name) }}
				</span>
			</div>
		</div>

		<div class="my-3 flex flex-wrap gap-1.5">
			<div
				v-if="project.project?.project_type || project.project_type"
				class="inline-flex items-center gap-1 px-2.5 py-0.5 bg-red-100 border border-red-300 rounded-full text-xs font-semibold text-red-800"
			>
				<Briefcase class="w-3 h-3" />
				<span>{{ __(project.project?.project_type || project.project_type) }}</span>
			</div>

			<div
				v-if="currentStatus"
				:class="getStatusBadgeClass(currentStatus)"
				class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold"
			>
				<component :is="getStatusIcon(currentStatus)" class="w-3 h-3" />
				<span>{{ __(currentStatus) }}</span>
			</div>

			<div
				v-if="project.project?.priority"
				:class="getPriorityBadgeClass(project.project.priority)"
				class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold"
			>
				<Flag class="w-3 h-3" />
				<span>{{ __(project.project.priority) }}</span>
			</div>
		</div>

		<div class="space-y-2 mb-3">
			<div
				v-if="project.location || project.project?.company"
				class="flex items-center gap-2 px-3 py-1 bg-red-50 border-l-2 border-red-500 rounded text-sm font-medium text-red-800"
			>
				<MapPin class="w-4 h-4 text-red-600 flex-shrink-0" />
				<span class="truncate">{{
					__(project.location || project.project?.company)
				}}</span>
			</div>
		</div>

		<div class="h-px bg-gray-100 mb-3"></div>

		<div class="flex-grow space-y-3 mb-4">
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<div
					v-if="project.expected_start_date || project.project?.expected_start_date"
					class="flex items-center gap-2 p-2 bg-green-50 rounded-md"
				>
					<div
						class="flex-shrink-0 w-6 h-6 bg-white rounded-full flex items-center justify-center"
					>
						<Calendar class="w-4 h-4 text-green-600" />
					</div>
					<div>
						<p class="text-xs text-gray-600">Start:</p>
						<p class="text-sm font-semibold text-gray-900">
							{{
								__(
									dayjs(
										project.expected_start_date ||
											project.project?.expected_start_date,
									).format("MMM D, YYYY"),
								)
							}}
						</p>
					</div>
				</div>

				<div
					v-if="project.expected_end_date || project.project?.expected_end_date"
					class="flex items-center gap-2 p-2 bg-red-50 rounded-md"
				>
					<div
						class="flex-shrink-0 w-6 h-6 bg-white rounded-full flex items-center justify-center"
					>
						<CalendarX class="w-4 h-4 text-red-600" />
					</div>
					<div>
						<p class="text-xs text-gray-600">End:</p>
						<p class="text-sm font-semibold text-gray-900">
							{{
								__(
									dayjs(
										project.expected_end_date ||
											project.project?.expected_end_date,
									).format("MMM D, YYYY"),
								)
							}}
						</p>
					</div>
				</div>
			</div>

			<div
				v-if="
					(project.expected_start_date || project.project?.expected_start_date) &&
					(project.expected_end_date || project.project?.expected_end_date)
				"
				class="flex items-center gap-2 p-2 bg-blue-50 rounded-md w-full"
			>
				<div
					class="flex-shrink-0 w-6 h-6 bg-white rounded-full flex items-center justify-center"
				>
					<Clock class="w-4 h-4 text-blue-600" />
				</div>
				<div>
					<p class="text-xs text-gray-600">Duration:</p>
					<p class="text-sm font-semibold text-gray-900">
						{{
							__(
								calculateDuration(
									project.expected_start_date ||
										project.project?.expected_start_date,
									project.expected_end_date ||
										project.project?.expected_end_date,
								),
							)
						}}
					</p>
				</div>
			</div>
		</div>

		<div class="pt-3 border-t border-gray-100 flex items-center justify-end gap-3 mt-auto">
			<div v-if="project.creation" class="flex items-center gap-1 text-xs text-gray-500">
				<History class="w-3.5 h-3.5" />
				<span>
					{{ __("Created") }} {{ __(dayjs().diff(dayjs(project.creation), "day"))
					}}{{ __("d ago") }}
				</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import {
	Activity,
	Briefcase,
	Calendar,
	CalendarX,
	CheckCircle,
	Clock,
	Flag,
	History,
	HourglassIcon,
	MapPin,
	XCircle,
} from "lucide-vue-next";
import { inject } from "vue";

const dayjs = inject("$dayjs");

const props = defineProps({
	project: { type: Object, default: null },
	currentStatus: { type: String, default: "All" },
});

const getStatusBadgeClass = (status) => {
	const classes = {
		"Pending Response": "bg-yellow-100 border border-yellow-300 text-yellow-800",
		"Awaiting Deployment": "bg-green-100 border border-green-300 text-green-800",
		"Declined Deployment": "bg-red-100 border border-red-300 text-red-800",
		Active: "bg-blue-100 border border-blue-300 text-blue-800",
		Closed: "bg-gray-100 border border-gray-300 text-gray-800",
	};
	return classes[status] || "bg-gray-100 border border-gray-300 text-gray-800";
};

const getPriorityBadgeClass = (priority) => {
	const classes = {
		Low: "bg-blue-100 border border-blue-300 text-blue-800",
		Medium: "bg-yellow-100 border border-yellow-300 text-yellow-800",
		High: "bg-orange-100 border border-orange-300 text-orange-800",
		Urgent: "bg-red-100 border border-red-300 text-red-800",
	};
	return classes[priority] || "bg-gray-100 border border-gray-300 text-gray-800";
};

const getStatusIcon = (status) => {
	const icons = {
		"Pending Response": HourglassIcon,
		"Awaiting Deployment": CheckCircle,
		"Declined Deployment": XCircle,
		Active: CheckCircle,
		Closed: XCircle,
	};
	return icons[status] || Activity;
};

const calculateDuration = (startDate, endDate) => {
	const start = dayjs(startDate);
	const end = dayjs(endDate);
	const days = end.diff(start, "day");

	if (days < 30) return `${days}d`;
	else if (days < 365) {
		const months = Math.floor(days / 30);
		const remainingDays = days % 30;
		return remainingDays > 0 ? `${months}m ${remainingDays}d` : `${months}m`;
	} else {
		const years = Math.floor(days / 365);
		const months = Math.floor((days % 365) / 30);
		return months > 0 ? `${years}y ${months}m` : `${years}y`;
	}
};
</script>
