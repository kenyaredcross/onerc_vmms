<template>
	<div class="bg-surface-base rounded-xl border border-outline-gray-2 p-6">
		<h2 class="text-lg-semibold text-ink-gray-9 mb-4">{{ __("Notes") }}</h2>
		<div v-if="notes" class="prose prose-sm max-w-none text-ink-gray-7">
			{{ notes }}
		</div>
		<div v-else class="text-ink-gray-5 italic">
			{{ __("No notes available for this deployment.") }}
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
