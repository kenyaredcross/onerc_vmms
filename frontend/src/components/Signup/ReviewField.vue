<template>
	<div class="p-3 border rounded-md bg-surface-gray-50">
		<p class="text-xs font-semibold text-ink-gray-1-500">{{ label }}</p>
		<p class="mt-1 text-ink-gray-1-800">
			{{ value ? value : "—" }}
		</p>
	</div>
</template>

<script setup>
defineProps({ label: String, value: [String, Number, Object] });
</script>
