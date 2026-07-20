<template>
	<div class="w-full h-24 flex items-center justify-center">
		<canvas ref="chartCanvas"></canvas>
	</div>
</template>

<script>
import Chart from "chart.js/auto";

export default {
	name: "HorizontalBarChart",
	props: {
		chartData: {
			type: Object,
			required: true,
			default: () => ({
				labels: [],
				datasets: [],
			}),
		},
	},
	data() {
		return {
			chartInstance: null,
			colors: [
				"#8B5CF6",
				"#3B82F6",
				"#06B6D4",
				"#14B8A6",
				"#EC4899",
				"#EF4444",
				"#F97316",
				"#EAB308",
			],
		};
	},
	watch: {
		chartData: {
			deep: true,
			handler() {
				this.updateChart();
			},
		},
	},
	mounted() {
		this.initChart();
	},
	beforeUnmount() {
		if (this.chartInstance) {
			this.chartInstance.destroy();
		}
	},
	methods: {
		initChart() {
			const ctx = this.$refs.chartCanvas.getContext("2d");

			const dataset =
				this.chartData.datasets?.[0]?.values || this.chartData.datasets?.[0]?.data || [];
			const labels = this.chartData.labels || [];
			const combined = labels.map((label, idx) => ({ label, value: dataset[idx] }));
			combined.sort((a, b) => b.value - a.value);

			const datasets = combined.map((c, idx) => ({
				label: c.label,
				data: [c.value],
				backgroundColor: this.colors[idx % this.colors.length],
				borderWidth: 0,
			}));

			this.chartInstance = new Chart(ctx, {
				type: "bar",
				data: {
					labels: [""],
					datasets: datasets,
				},
				options: {
					indexAxis: "y",
					responsive: true,
					maintainAspectRatio: false,
					plugins: {
						legend: { display: true, position: "bottom" },
						tooltip: {
							callbacks: {
								label: function (context) {
									const value = context.raw;
									const total = context.chart.data.datasets.reduce(
										(sum, d) => sum + d.data[0],
										0
									);
									const percentage =
										total > 0 ? ((value / total) * 100).toFixed(1) : 0;
									return `${context.dataset.label}: ${value} (${percentage}%)`;
								},
							},
						},
					},
					scales: {
						x: {
							stacked: true,
							beginAtZero: true,
						},
						y: {
							stacked: true,
						},
					},
				},
			});
		},

		updateChart() {
			if (!this.chartInstance) {
				this.initChart();
				return;
			}

			const dataset =
				this.chartData.datasets?.[0]?.values || this.chartData.datasets?.[0]?.data || [];
			const labels = this.chartData.labels || [];
			const combined = labels.map((label, idx) => ({ label, value: dataset[idx] }));
			combined.sort((a, b) => b.value - a.value);

			this.chartInstance.data.datasets = combined.map((c, idx) => ({
				label: c.label,
				data: [c.value],
				backgroundColor: this.colors[idx % this.colors.length],
				borderWidth: 0,
			}));

			this.chartInstance.update();
		},
	},
};
</script>
