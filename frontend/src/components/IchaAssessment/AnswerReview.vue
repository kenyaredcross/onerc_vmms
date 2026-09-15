<template>
	<div class="space-y-4">
		<h3 class="text-xl font-bold text-gray-900">{{ __("Question Review") }}</h3>
		<p class="text-sm text-gray-500">
			{{ __("Green = correct answer. Red highlight = your incorrect selection.") }}
		</p>

		<div
			v-for="(ans, idx) in answers"
			:key="ans.question"
			class="bg-white rounded-xl border p-5 shadow-sm"
			:class="ans.is_correct ? 'border-green-200' : 'border-red-200'"
		>
			<div class="flex items-center gap-2 mb-1">
				<span class="text-xs font-semibold uppercase tracking-wide text-gray-400">
					{{ ans.course }}
				</span>
				<span
					class="text-xs font-semibold px-2 py-0.5 rounded-full"
					:class="ans.is_correct ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
				>
					{{ ans.is_correct ? __("Correct") : __("Incorrect") }}
				</span>
			</div>
			<p class="font-medium text-gray-900 mb-3 leading-snug">
				{{ idx + 1 }}. {{ ans.question_text }}
			</p>
			<div class="space-y-1.5">
				<div
					v-for="opt in ['A', 'B', 'C', 'D']"
					:key="opt"
					class="flex items-start gap-2 px-3 py-2 rounded-lg text-sm"
					:class="getOptionClass(ans, opt)"
				>
					<span class="font-semibold shrink-0 w-5">{{ opt }}.</span>
					<span>{{ ans.options[opt] }}</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	answers: {
		type: Array,
		required: true,
	},
});

function getOptionClass(ans, opt) {
	if (opt === ans.correct_answer) {
		return "bg-green-50 border border-green-300 text-green-900 font-medium";
	}
	if (opt === ans.selected_answer && !ans.is_correct) {
		return "bg-red-50 border border-red-300 text-red-900";
	}
	return "bg-gray-50 text-gray-700";
}
</script>
