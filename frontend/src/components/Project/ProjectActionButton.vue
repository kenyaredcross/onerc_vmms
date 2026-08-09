<template>
	<button
		@click="openDoctype"
		class="flex items-center justify-start w-full p-4 text-sm-semibold text-ink-gray-8 transition-all duration-300 bg-surface-base border border-outline-gray-2 rounded-lg hover:shadow-md hover:border-outline-red-5 hover:bg-surface-red-1 focus:outline-none focus:ring-2 focus:ring-outline-green-4 focus:ring-offset-2"
	>
		<component
			:is="iconComponent"
			:size="18"
			class="mr-4 text-ink-red-6 transition-colors duration-300 group-hover:text-ink-red-8"
		/>
		{{ label }}
	</button>
</template>

<script setup>
import * as LucideIcons from "lucide-vue-next";
import { computed } from "vue";

const props = defineProps({
	label: String,
	doctype: String,
	project: Object,
	icon: String,
});

const iconComponent = computed(() => {
	return LucideIcons[props.icon] || LucideIcons.HeartPulse;
});

const openDoctype = () => {
	const url = `/app/${props.doctype
		.toLowerCase()
		.replace(/ /g, "-")}/new?personnel_deployment_request=${props.project.name}`;
	window.open(url, "_blank");
};
</script>
