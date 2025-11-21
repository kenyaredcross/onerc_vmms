<template>
	<div class="text-center py-8 border rounded-lg shadow-sm bg-white">
		<div class="mb-4">
			<svg
				class="mx-auto h-16 w-16 text-green-500"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
				/>
			</svg>
		</div>
		<h3 class="text-xl font-semibold text-gray-900 mb-2">{{ title }} Successful!</h3>
		<p class="text-gray-600 mb-6">{{ message }}. Thank you for your support!</p>
	</div>
</template>

<script setup>
import { Button } from "frappe-ui";

const emit = defineEmits(["close"]);

const props = defineProps({
	title: String,
	message: String,
});
</script>
