<template>
	<div
		class="group relative flex flex-col bg-surface-base border border-outline-gray-2 rounded-xl p-4 h-full hover:shadow-xl hover:border-outline-red-3 transition-all duration-300 overflow-hidden"
	>
		<div
			class="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-500 via-red-400 to-orange-400"
		></div>

		<div class="mb-3 flex flex-wrap gap-2">
			<div
				v-if="job.designation"
				class="inline-flex items-center gap-1 px-2 py-0.5 bg-surface-red-1 border border-outline-red-3 rounded-full text-xs-medium text-ink-red-7"
			>
				<User class="w-3 h-3" />
				<span>{{ __(job.designation) }}</span>
			</div>
		</div>
		<h2
			class="text-lg-bold text-ink-gray-9 leading-tight mb-2 group-hover:text-ink-red-6 transition-colors duration-200"
		>
			{{ __(job.job_title) }}
		</h2>

		<div
			v-if="job.company"
			class="flex items-center gap-2 px-3 py-1 bg-surface-red-2 border-l-4 border-outline-red-5 rounded text-sm-semibold text-ink-red-8 mb-3"
		>
			<MapPin class="w-4 h-4 text-ink-red-6 flex-shrink-0" />
			<span>{{ __(job.company) }}</span>
		</div>

		<div
			class="h-px bg-gradient-to-r from-transparent via-outline-gray-3 to-transparent mb-3"
		></div>

		<div class="space-y-3 mb-4 flex-grow">
			<div class="grid grid-cols-2 gap-3">
				<div v-if="job.posted_on" class="flex items-center gap-2 min-w-0">
					<div
						class="flex-shrink-0 w-7 h-7 bg-surface-green-1 rounded-md flex items-center justify-center"
					>
						<Calendar class="w-4 h-4 text-ink-green-6" />
					</div>
					<div class="flex-1 min-w-0">
						<p class="text-xs text-ink-gray-5">
							{{ __("Posted On:") }}
							<span class="font-semibold text-ink-gray-9">{{
								__(dayjs(job.posted_on).format("MMM D"))
							}}</span>
						</p>
					</div>
				</div>

				<div v-if="job.closes_on" class="flex items-center gap-2 min-w-0">
					<div
						class="flex-shrink-0 w-7 h-7 bg-surface-red-1 rounded-md flex items-center justify-center"
					>
						<CalendarX class="w-4 h-4 text-ink-red-6" />
					</div>
					<div class="flex-1 min-w-0">
						<p class="text-xs text-ink-gray-5">
							{{ __("Closes On:") }}
							<span class="font-semibold text-ink-gray-9">{{
								__(dayjs(job.closes_on).format("MMM D"))
							}}</span>
						</p>
					</div>
				</div>
			</div>

			<div v-if="job.duration" class="flex items-center gap-2">
				<div
					class="flex-shrink-0 w-7 h-7 bg-surface-blue-1 rounded-md flex items-center justify-center"
				>
					<Clock class="w-4 h-4 text-ink-blue-6" />
				</div>
				<div class="flex-1 min-w-0">
					<p class="text-xs text-ink-gray-5">
						{{ __("Open For:") }}
						<span class="text-sm-semibold text-ink-gray-9">{{
							__(formatDuration(job.duration))
						}}</span>
					</p>
				</div>
			</div>
		</div>

		<div class="pt-3 border-t border-outline-gray-1 mt-auto">
			<div class="flex items-center justify-between gap-4">
				<div v-if="job.creation" class="flex items-center gap-1.5 text-xs text-ink-gray-5">
					<History class="w-3 h-3" />
					<span>{{ dayjs().diff(dayjs(job.creation), "day") }}{{ __("d ago") }}</span>
				</div>

				<div
					v-if="job?.publish_applications_received && job.applicants"
					class="flex items-center gap-1.5 px-2 py-1 bg-gradient-to-r from-red-500 to-orange-500 rounded-md text-white shadow-sm"
				>
					<Users class="w-3.5 h-3.5" />
					<span class="text-sm-bold leading-none">{{ __(job.applicants) }}</span>
					<span class="text-xs opacity-90 leading-none">{{ __("applicants") }}</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Calendar, CalendarX, Clock, History, MapPin, User, Users } from "lucide-vue-next";
import { inject } from "vue";

const dayjs = inject("$dayjs");
const settings = inject("jobSettings", { showApplicants: true });

const props = defineProps({
	job: {
		type: Object,
		default: null,
	},
});

const formatDuration = (seconds) => {
	const SECONDS_IN_HOUR = 3600;
	const SECONDS_IN_DAY = SECONDS_IN_HOUR * 24;
	const SECONDS_IN_MONTH = SECONDS_IN_DAY * 30.437;

	const months = Math.floor(seconds / SECONDS_IN_MONTH);
	let remainingSeconds = seconds % SECONDS_IN_MONTH;

	const days = Math.floor(remainingSeconds / SECONDS_IN_DAY);
	remainingSeconds %= SECONDS_IN_DAY;

	const hours = Math.ceil(remainingSeconds / SECONDS_IN_HOUR);

	let parts = [];
	if (months > 0) {
		parts.push(`${months}m`);
	}
	if (days > 0) {
		parts.push(`${days}d`);
	}
	if (hours > 0 && months === 0) {
		parts.push(`${hours}h`);
	}

	return parts.join(" ");
};
</script>
