<template>
	<div class="text-center py-8">
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
		<h3 class="text-xl font-semibold text-gray-900 mb-2">Membership Successful!</h3>
		<p class="text-gray-600 mb-6">
			Your membership has been processed successfully. Thank you for your continued support!
			Welcome to our community!
		</p>
		<Button variant="solid" theme="green" class="rounded-lg px-6" @click="emit('close')">
			Close
		</Button>
	</div>
</template>

<script setup>
import { Button } from "frappe-ui";

const emit = defineEmits(["close"]);
</script>
