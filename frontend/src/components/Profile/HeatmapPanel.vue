<template>
	<div class="bg-white rounded-lg shadow-md p-6">
		<div class="flex justify-between items-center mb-4">
			<h3 class="text-lg font-semibold text-gray-800">Activity Overview</h3>
			<select
				v-model="year"
				@change="updateHeatmap"
				class="text-sm border border-gray-300 rounded pl-2 pr-6 py-1 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
			>
				<option v-for="y in availableYears" :key="y" :value="y">
					{{ y }}
				</option>
			</select>
		</div>

		<div>
			<HeatmapComponent :heatmap-data="heatmapData" :year="year" v-if="!loading" />
			<div v-else class="flex items-center justify-center h-64">
				<div
					class="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-500"
				></div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { format } from "date-fns";
import { createResource } from "frappe-ui";
import { onMounted, ref } from "vue";
import HeatmapComponent from "./HeatmapComponent.vue";

const props = defineProps({
	userId: { type: String, required: true },
});

const currentYear = new Date().getFullYear();
const year = ref(currentYear);
const availableYears = ref([]);
const heatmapData = ref({});
const loading = ref(true);

const heatmapResource = createResource({
	url: "frappe.desk.page.user_profile.user_profile.get_energy_points_heatmap_data",
	auto: false,
});

function generateYears() {
	const years = [];
	for (let i = currentYear; i >= currentYear - 5; i--) years.push(i);
	availableYears.value = years;
} 

function updateHeatmap() {
	loading.value = true;

	heatmapResource.params = { user: props.userId, date: `${year.value}-01-01` };

	heatmapResource
		.fetch()
		.then(() => {
			const rawData = heatmapResource.data || {};
			const formattedData = {};

			for (const timestamp in rawData) {
				const date = new Date(parseInt(timestamp) * 1000);
				const dateString = format(date, "yyyy-MM-dd");
				formattedData[dateString] = rawData[timestamp];
			}

			heatmapData.value = formattedData;
			loading.value = false;
		})
		.catch((e) => {
			console.error("Heatmap fetch error:", e);
			loading.value = false;
		});
}

onMounted(() => {
	generateYears();
	updateHeatmap();
});
</script>
