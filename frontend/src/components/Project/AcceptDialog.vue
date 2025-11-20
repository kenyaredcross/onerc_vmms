<template>
	<Dialog :modelValue="modelValue" @update:modelValue="$emit('update:modelValue', $event)">
		<template #body-title>
			<h3 class="text-2xl font-semibold text-gray-900">{{ __("Confirm Action") }}</h3>
		</template>

		<template #body-content>
			<div class="space-y-4 text-gray-700">
				<p>
					{{
						__(
							"By confirming, you acknowledge that you have read the contract details and terms of reference, and that you accept the deployment.",
						)
					}}
				</p>
				<p class="text-sm text-gray-500 italic">
					{{ __("Accepting means you agree to the documents provided.") }}
				</p>
			</div>
		</template>

		<template #actions="{ close }">
			<div class="flex space-x-2">
				<Button
					theme="red"
					variant="solid"
					:loading="loading"
					@click="handleConfirm(close)"
				>
					{{ __("Confirm") }}
				</Button>
				<Button variant="outline" @click="close()">{{ __("Cancel") }}</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, Dialog } from "frappe-ui";

const props = defineProps({
	modelValue: {
		type: Boolean,
		required: true,
	},
	loading: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["update:modelValue", "confirm"]);

const handleConfirm = (close) => {
	emit("confirm");
	close();
};
</script>
