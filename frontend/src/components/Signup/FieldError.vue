<template>
	<p v-if="message" :id="id" role="alert" class="text-sm text-red-600 mt-1">
		{{ message }}
	</p>
</template>

<script setup>
defineProps({
	id: { type: String, required: true },
	message: { type: String, default: null },
});
</script>
