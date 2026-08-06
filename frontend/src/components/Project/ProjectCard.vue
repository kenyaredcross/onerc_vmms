<template>
	<div
		class="group relative flex flex-col bg-surface-base border border-outline-gray-2 rounded-lg p-4 h-full shadow-md hover:shadow-xl hover:border-outline-red-4 transition-all duration-300 overflow-hidden"
	>
		<div
			class="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-red-500 via-red-400 to-orange-400"
		></div>

		<div class="mb-1">
			<h2
				class="text-lg-bold text-ink-gray-9 leading-tight group-hover:text-ink-red-7 transition-colors duration-200"
			>
				{{ __(project?.deployment?.title || project.name) }}
			</h2>

			<div
				v-if="project?.project?.project_name || project.project_name"
				class="flex items-center gap-2 mt-1"
			>
				<span
					class="text-xs-semibold text-ink-red-6 bg-surface-red-2 px-2 py-1 rounded-md"
				>
					{{ __("Project: ") + __(project?.project?.project_name) }}
				</span>
			</div>
		</div>

		<div class="my-3 flex flex-wrap gap-1.5">
			<div
				v-if="project.project?.project_type || project.project_type"
				class="inline-flex items-center gap-1 px-2.5 py-0.5 bg-surface-red-2 border border-outline-red-3 rounded-full text-xs-semibold text-ink-red-8"
			>
				<Briefcase class="w-3 h-3" />
				<span>{{ __(project.project?.project_type || project.project_type) }}</span>
			</div>

			<div
				v-if="currentStatus"
				:class="getStatusBadgeClass(currentStatus)"
				class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs-semibold"
			>
				<component :is="getStatusIcon(currentStatus)" class="w-3 h-3" />
				<span>{{ __(currentStatus) }}</span>
			</div>

			<div
				v-if="project.project?.priority"
				:class="getPriorityBadgeClass(project.project.priority)"
				class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs-semibold"
			>
				<Flag class="w-3 h-3" />
				<span>{{ __(project.project.priority) }}</span>
			</div>
		</div>

		<div class="space-y-2 mb-3">
			<div
				v-if="project.location || project.project?.company"
				class="flex items-center gap-2 px-3 py-1 bg-surface-red-1 border-l-2 border-outline-red-5 rounded text-sm-medium text-ink-red-8"
			>
				<MapPin class="w-4 h-4 text-ink-red-6 flex-shrink-0" />
				<span class="truncate">{{
					__(project.location || project.project?.company)
				}}</span>
			</div>
		</div>

		<div class="h-px bg-surface-gray-2 mb-3"></div>

		<div class="flex-grow space-y-3 mb-4">
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<div
					v-if="project.expected_start_date || project.project?.expected_start_date"
					class="flex items-center gap-2 p-2 bg-surface-green-1 rounded-md"
				>
					<div
						class="flex-shrink-0 w-6 h-6 bg-surface-base rounded-full flex items-center justify-center"
					>
						<Calendar class="w-4 h-4 text-ink-green-6" />
					</div>
					<div>
						<p class="text-xs text-ink-gray-6">Start:</p>
						<p class="text-sm-semibold text-ink-gray-9">
							{{
								__(
									dayjs(
										project.expected_start_date ||
											project.project?.expected_start_date
									).format("MMM D, YYYY")
								)
							}}
						</p>
					</div>
				</div>

				<div
					v-if="project.expected_end_date || project.project?.expected_end_date"
					class="flex items-center gap-2 p-2 bg-surface-red-1 rounded-md"
				>
					<div
						class="flex-shrink-0 w-6 h-6 bg-surface-base rounded-full flex items-center justify-center"
					>
						<CalendarX class="w-4 h-4 text-ink-red-6" />
					</div>
					<div>
						<p class="text-xs text-ink-gray-6">End:</p>
						<p class="text-sm-semibold text-ink-gray-9">
							{{
								__(
									dayjs(
										project.expected_end_date ||
											project.project?.expected_end_date
									).format("MMM D, YYYY")
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
				class="flex items-center gap-2 p-2 bg-surface-blue-1 rounded-md w-full"
			>
				<div
					class="flex-shrink-0 w-6 h-6 bg-surface-base rounded-full flex items-center justify-center"
				>
					<Clock class="w-4 h-4 text-ink-blue-6" />
				</div>
				<div>
					<p class="text-xs text-ink-gray-6">Duration:</p>
					<p class="text-sm-semibold text-ink-gray-9">
						{{
							__(
								calculateDuration(
									project.expected_start_date ||
										project.project?.expected_start_date,
									project.expected_end_date || project.project?.expected_end_date
								)
							)
						}}
					</p>
				</div>
			</div>
		</div>

		<div
			class="pt-3 border-t border-outline-gray-1 flex items-center justify-end gap-3 mt-auto"
		>
			<div v-if="project.creation" class="flex items-center gap-1 text-xs text-ink-gray-5">
				<History class="w-3.5 h-3.5" />
				<span>
					{{ __("Created") }} {{ dayjs().diff(dayjs(project.creation), "day")
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
		"Pending Response": "bg-surface-yellow-2 border border-outline-yellow-3 text-ink-yellow-8",
		"Awaiting Deployment": "bg-surface-green-2 border border-outline-green-3 text-ink-green-8",
		"Declined Deployment": "bg-surface-red-2 border border-outline-red-3 text-ink-red-8",
		Active: "bg-surface-blue-2 border border-outline-blue-3 text-ink-blue-8",
		Closed: "bg-surface-gray-2 border border-outline-gray-3 text-ink-gray-8",
	};
	return classes[status] || "bg-surface-gray-2 border border-outline-gray-3 text-ink-gray-8";
};

const getPriorityBadgeClass = (priority) => {
	const classes = {
		Low: "bg-surface-blue-2 border border-outline-blue-3 text-ink-blue-8",
		Medium: "bg-surface-yellow-2 border border-outline-yellow-3 text-ink-yellow-8",
		High: "bg-surface-orange-2 border border-outline-orange-3 text-ink-orange-8",
		Urgent: "bg-surface-red-2 border border-outline-red-3 text-ink-red-8",
	};
	return classes[priority] || "bg-surface-gray-2 border border-outline-gray-3 text-ink-gray-8";
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
