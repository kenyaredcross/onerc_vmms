<template>
	<div class="bg-surface-base rounded-lg border border-outline-gray-2 p-6">
		<div class="flex justify-between items-center mb-4">
			<h3 class="text-lg-semibold text-ink-gray-1-800">Type Distribution</h3>
			<select
				v-model="field"
				:aria-label="__('Group distribution by')"
				@change="updateChart"
				class="text-sm border border-outline-gray-300 rounded pl-2 pr-6 py-1 focus:ring-2 focus:ring-red-500 focus:border-transparent"
			>
				<option value="type">Type</option>
				<option value="reference_doctype">Reference Doctype</option>
				<option value="rule">Rule</option>
			</select>
		</div>
		<div class="">
			<PieChartComponent :chart-data="chartData" v-if="!loading" />
			<div v-else class="flex items-center justify-center h-full">
				<ProgressSpinner size="md" />
			</div>
		</div>
	</div>
</template>

<script setup>
import ProgressSpinner from "../Common/ProgressSpinner.vue";
import { createResource } from "frappe-ui";
import { onMounted, ref } from "vue";
import PieChartComponent from "./PieChartComponent.vue";

const props = defineProps({
	userId: { type: String, required: true },
});

const field = ref("type");
const chartData = ref({ labels: [], datasets: [] });
const loading = ref(true);

const chartResource = createResource({
	url: "frappe.desk.page.user_profile.user_profile.get_energy_points_percentage_chart_data",
	auto: false,
});

function updateChart() {
	loading.value = true;
	chartResource.params = { user: props.userId, field: field.value };
	chartResource
		.fetch()
		.then(() => {
			const r = chartResource.data;
			console.log(r);

			chartData.value = r
				? { labels: r.labels || [], datasets: r.datasets || [] }
				: { labels: [], datasets: [] };
			loading.value = false;
		})
		.catch(() => (loading.value = false));
}

onMounted(updateChart);
</script>
