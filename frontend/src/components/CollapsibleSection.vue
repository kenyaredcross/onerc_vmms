<template>
	<div class="border rounded-lg bg-surface-white shadow-sm">
		<button
			@click="toggle"
			class="flex justify-between items-center w-full p-4 text-left font-semibold text-ink-gray-1-700 hover:bg-surface-gray-50 transition duration-150"
		>
			<h2 class="text-xl font-semibold">{{ __(title) }}</h2>
			<svg
				class="w-5 h-5 transition-transform duration-300"
				:class="{ 'rotate-180': isOpen }"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M19 9l-7 7-7-7"
				></path>
			</svg>
		</button>
		<div v-show="isOpen" class="p-6 border-t">
			<slot></slot>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue";

const props = defineProps({
	title: {
		type: String,
		required: true,
	},
	defaultOpen: {
		type: Boolean,
		default: false,
	},
});

const isOpen = ref(props.defaultOpen);

function toggle() {
	isOpen.value = !isOpen.value;
}
</script>
