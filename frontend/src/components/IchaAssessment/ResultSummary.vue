<template>
	<div
		class="p-6 rounded-xl border shadow-sm"
		:class="result.passed ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'"
	>
		<div class="flex items-center gap-3 mb-4">
			<div
				class="flex items-center justify-center size-12 rounded-full shrink-0"
				:class="result.passed ? 'bg-green-100' : 'bg-red-100'"
			>
				<CheckCircle v-if="result.passed" class="size-7 text-green-600" />
				<XCircle v-else class="size-7 text-red-600" />
			</div>
			<div>
				<h2 class="text-2xl font-bold" :class="result.passed ? 'text-green-800' : 'text-red-800'">
					{{ result.passed ? __("Congratulations! You Passed") : __("Assessment Not Passed") }}
				</h2>
				<p class="text-sm text-gray-500 mt-0.5">
					{{ __("Submitted on {0}", [formatDate(result.submitted_on)]) }}
				</p>
			</div>
		</div>

		<div class="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-4">
			<div
				class="text-center p-4 rounded-lg"
				:class="result.passed ? 'bg-green-100' : 'bg-red-100'"
			>
				<p
					class="text-3xl font-black"
					:class="result.passed ? 'text-green-700' : 'text-red-700'"
				>
					{{ result.score }}/{{ result.total_questions }}
				</p>
				<p class="text-xs text-gray-500 mt-1 font-medium">{{ __("Score") }}</p>
			</div>
			<div class="text-center p-4 rounded-lg bg-gray-100">
				<p class="text-3xl font-black text-gray-800">{{ result.percentage.toFixed(1) }}%</p>
				<p class="text-xs text-gray-500 mt-1 font-medium">{{ __("Percentage") }}</p>
			</div>
			<div
				class="text-center p-4 rounded-lg col-span-2 sm:col-span-1"
				:class="result.passed ? 'bg-green-100' : 'bg-red-100'"
			>
				<p
					class="text-3xl font-black"
					:class="result.passed ? 'text-green-700' : 'text-red-700'"
				>
					{{ result.passed ? __("PASS") : __("FAIL") }}
				</p>
				<p class="text-xs text-gray-500 mt-1 font-medium">{{ __("Result") }}</p>
			</div>
		</div>

		<p class="mt-4 text-sm text-gray-600">
			<span v-if="result.passed">
				{{ __("You scored {0}% and have successfully completed the ICHA Research Assistant Assessment.", [result.percentage.toFixed(1)]) }}
			</span>
			<span v-else>
				{{ __("You scored {0}%. A minimum of 70% is required to pass. Your attempt has been recorded.", [result.percentage.toFixed(1)]) }}
			</span>
		</p>
	</div>
</template>

<script setup>
import { CheckCircle, XCircle } from "lucide-vue-next";
import dayjs from "dayjs";

const props = defineProps({
	result: {
		type: Object,
		required: true,
	},
});

function formatDate(d) {
	return dayjs(d).format("DD MMM YYYY HH:mm");
}
</script>
