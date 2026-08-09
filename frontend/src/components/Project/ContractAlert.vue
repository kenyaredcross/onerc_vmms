<template>
	<div
		class="w-full flex items-center justify-center rounded-lg border border-outline-yellow-3 bg-surface-yellow-1 px-8 py-4 text-sm-medium text-ink-yellow-7"
	>
		<svg
			class="h-4 w-4 mr-2 text-ink-yellow-5"
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M12 9v2m0 4h.01M12 5.5a7.5 7.5 0 100 15 7.5 7.5 0 000-15z"
			/>
		</svg>
		<div class="flex-1">
			<h3 class="text-sm-semibold text-ink-yellow-8 mb-1">
				{{ __("Contract Pending") }}
			</h3>
			<p class="text-sm text-ink-yellow-7">
				{{
					__(
						"A signed contract is required before you can accept this deployment. Please wait, or contact the deployment manager for assistance."
					)
				}}
			</p>
		</div>
	</div>
</template>

<script setup>
defineProps({
	project: {
		type: Object,
		required: true,
	},
});
</script>
