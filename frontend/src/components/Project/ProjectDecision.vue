<template>
	<div class="bg-surface-base rounded-xl border border-outline-red-1 p-8">
		<h2 class="flex flex-row items-center gap-2 text-3xl-bold text-ink-red-7 mb-4">
			<Badge variant="subtle" theme="red">{{ __("Required") }}</Badge>
			<span>{{ __("Deployment Decision") }}</span>
		</h2>

		<div class="mb-6">
			<p class="text-sm-medium text-ink-gray-7 mb-2">
				{{
					__(
						"Important: Please review the official deployment information before you decide."
					)
				}}
			</p>

			<div class="flex justify-center" v-if="project?.contract?.name">
				<Button
					@click="$emit('download-contract', project.contract.name)"
					:loading="loading"
					theme="red"
					variant="solid"
				>
					{{ __("Download Contract") }}
				</Button>
			</div>
		</div>

		<p class="text-sm text-ink-gray-5 italic mb-6">
			{{
				__(
					"Your decision to accept this deployment confirms your agreement to the terms outlined."
				)
			}}
		</p>

		<div class="flex gap-3">
			<Button theme="green" variant="solid" class="flex-1" @click="$emit('accept')">
				{{ __("Accept") }}
			</Button>
			<Button
				theme="red"
				variant="solid"
				class="flex-1"
				@click="$emit('reject')"
				:loading="loading"
			>
				{{ __("Reject") }}
			</Button>
		</div>

		<ErrorMessage :message="error" class="mt-4" />
	</div>
</template>

<script setup>
import { Badge, Button, ErrorMessage } from "frappe-ui";

defineProps({
	project: {
		type: Object,
		required: true,
	},
	loading: {
		type: Boolean,
		default: false,
	},
	error: {
		type: String,
		default: "",
	},
});

defineEmits(["accept", "reject", "download-contract"]);
</script>
