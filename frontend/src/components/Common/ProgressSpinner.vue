<template>
	<div
		role="status"
		aria-live="polite"
		class="flex flex-col justify-center items-center my-auto text-center text-3xl"
	>
		<LoaderCircle aria-hidden="true" class="animate-spin text-red-500" :class="sizeClass" />
		<span v-if="message" class="text-base"> {{ __(message) }}</span>
		<span v-else class="sr-only">{{ __("Loading") }}</span>
	</div>
</template>
<script setup>
import { LoaderCircle } from "lucide-vue-next";
import { computed } from "vue";

const SIZES = {
	sm: "h-8 w-8",
	md: "h-12 w-12",
	lg: "h-16 w-16",
};

const props = defineProps({
	message: String,
	size: {
		type: String,
		default: "lg",
		validator: (value) => ["sm", "md", "lg"].includes(value),
	},
});

const sizeClass = computed(() => SIZES[props.size] || SIZES.lg);
</script>
