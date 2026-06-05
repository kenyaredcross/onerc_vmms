<template>
	<button
		@click="openDoctype"
		class="flex items-center justify-start w-full p-4 text-sm font-semibold text-ink-gray-1-800 transition-all duration-300 bg-surface-white border border-outline-gray-2 rounded-lg hover:shadow-md hover:border-red-500 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-offset-2"
	>
		<component
			:is="iconComponent"
			:size="18"
			class="mr-4 text-red-600 transition-colors duration-300 group-hover:text-red-800"
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
	const url = `/app/${props.doctype.toLowerCase().replace(/ /g, "-")}/new?personnel_deployment_request=${props.project.name}`;
	window.open(url, "_blank");
};
</script>
