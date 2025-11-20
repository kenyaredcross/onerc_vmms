<template>
	<div class="w-full h-full">
		<canvas ref="chartCanvas"></canvas>
	</div>
</template>

<script>
export default {
	name: "LineChartComponent",
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
		async initChart() {
			// Load Chart.js if not already loaded
			if (!window.Chart) {
				await this.loadChartJS();
			}

			const ctx = this.$refs.chartCanvas.getContext("2d");

			this.chartInstance = new Chart(ctx, {
				type: "line",
				data: {
					labels: this.chartData.labels || [],
					datasets: (this.chartData.datasets || []).map((dataset, index) => ({
						label: dataset.name || `Dataset ${index + 1}`,
						data: dataset.values || dataset.data || [],
						borderColor: "#8B5CF6",
						backgroundColor: "rgba(139, 92, 246, 0.1)",
						tension: 0.4,
						fill: true,
						pointRadius: 4,
						pointHoverRadius: 6,
						borderWidth: 2,
					})),
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: {
						legend: {
							display: true,
							position: "top",
						},
						tooltip: {
							mode: "index",
							intersect: false,
						},
					},
					scales: {
						x: {
							display: true,
							grid: {
								display: false,
							},
						},
						y: {
							display: true,
							beginAtZero: true,
							grid: {
								color: "rgba(0, 0, 0, 0.05)",
							},
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

			this.chartInstance.data.labels = this.chartData.labels || [];
			this.chartInstance.data.datasets = (this.chartData.datasets || []).map(
				(dataset, index) => ({
					label: dataset.name || `Dataset ${index + 1}`,
					data: dataset.values || dataset.data || [],
					borderColor: "#8B5CF6",
					backgroundColor: "rgba(139, 92, 246, 0.1)",
					tension: 0.4,
					fill: true,
					pointRadius: 4,
					pointHoverRadius: 6,
					borderWidth: 2,
				}),
			);

			this.chartInstance.update();
		},

		loadChartJS() {
			return new Promise((resolve, reject) => {
				if (window.Chart) {
					resolve();
					return;
				}

				const script = document.createElement("script");
				script.src = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js";
				script.onload = resolve;
				script.onerror = reject;
				document.head.appendChild(script);
			});
		},
	},
};
</script>
