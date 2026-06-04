<template>
	<div class="bg-surface-white rounded-xl shadow-lg border border-red-300 p-8">
		<h2 class="flex flex-row items-center gap-2 text-2xl font-bold text-red-700 mb-4">
			<Badge variant="subtle" theme="red">{{ __("Action Required:") }}</Badge>
			<span>{{ __("Deployment Decision") }}</span>
		</h2>

		<div class="mb-6">
			<p class="text-sm text-ink-gray-1-700 font-medium mb-2">
				{{
					__(
						"Important: Please review the official deployment information before you decide.",
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

		<p class="text-sm text-ink-gray-1-500 italic mb-6">
			{{
				__(
					"Your decision to accept this deployment confirms your agreement to the terms outlined.",
				)
			}}
		</p>

		<div class="flex gap-3">
			<Button theme="green" class="flex-1" @click="$emit('accept')">
				{{ __("Accept Deployment") }}
			</Button>
			<Button
				theme="red"
				variant="outline"
				class="flex-1"
				@click="$emit('reject')"
				:loading="loading"
			>
				{{ __("Reject Deployment") }}
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
