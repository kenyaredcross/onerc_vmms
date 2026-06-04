<template>
	<div class="bg-surface-white rounded-lg shadow-md p-4 sm:p-6">
		<div
			class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-3"
		>
			<h3 class="text-lg font-semibold text-ink-gray-1-800">Energy Points Trend</h3>

			<div class="flex flex-wrap gap-2">
				<select
					v-model="filter"
					@change="updateChart"
					class="text-sm border border-outline-gray-300 rounded pl-2 pr-6 py-1 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
				>
					<option value="All">All</option>
					<option value="Auto">Auto</option>
					<option value="Appreciation">Appreciation</option>
					<option value="Criticism">Criticism</option>
					<option value="Revert">Revert</option>
				</select>

				<select
					v-model="timespan"
					@change="updateChart"
					class="text-sm border border-outline-gray-300 rounded pl-2 pr-6 py-1 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
				>
					<option value="Last Week">Last Week</option>
					<option value="Last Month">Last Month</option>
					<option value="Last Quarter">Last Quarter</option>
					<option value="Last Year">Last Year</option>
				</select>
			</div>
		</div>

		<div class="h-60 sm:h-64 w-full">
			<LineChartComponent :chart-data="chartData" v-if="!loading" />
			<div v-else class="flex items-center justify-center h-full">
				<div
					class="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-500"
				></div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { createResource } from "frappe-ui";
import { onMounted, ref } from "vue";
import LineChartComponent from "./LineChartComponent.vue";

const props = defineProps({ userId: { type: String, required: true } });

const filter = ref("All");
const timespan = ref("Last Month");
const chartData = ref({ labels: [], datasets: [] });
const loading = ref(true);

const chartResource = createResource({
	url: "frappe.desk.doctype.dashboard_chart.dashboard_chart.get",
	auto: false,
});

function updateChart() {
	loading.value = true;
	const filters = [["Energy Point Log", "user", "=", props.userId, false]];
	if (filter.value !== "All") {
		filters.push(["Energy Point Log", "type", "=", filter.value, false]);
	} else {
		filters.push(["Energy Point Log", "type", "!=", "Review", false]);
	}

	const chartConfig = {
		timespan: timespan.value,
		time_interval: "Daily",
		type: "Line",
		value_based_on: "points",
		chart_type: "Sum",
		document_type: "Energy Point Log",
		name: "Energy Points",
		based_on: "creation",
		filters_json: JSON.stringify(filters),
	};

	chartResource.params = { chart: chartConfig, no_cache: 1 };
	chartResource
		.fetch()
		.then(() => {
			chartData.value = chartResource.data
				? {
						labels: chartResource.data.labels || [],
						datasets: chartResource.data.datasets || [],
					}
				: { labels: [], datasets: [] };
			loading.value = false;
		})
		.catch(() => (loading.value = false));
}

onMounted(updateChart);
</script>
