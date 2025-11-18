<template>
	<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
		<h2 class="text-lg font-semibold text-gray-900 mb-4">{{ __("Notes") }}</h2>
		<div v-if="notes" class="prose prose-sm max-w-none text-gray-700">
			{{ notes }}
		</div>
		<div v-else class="text-gray-500 italic">
			{{ __("No notes available for this project.") }}
		</div>
	</div>
</template>

<script setup>
defineProps({
	notes: {
		type: String,
		default: "",
	},
});
</script>
