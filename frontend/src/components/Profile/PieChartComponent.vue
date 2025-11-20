<template>
	<div class="w-full h-full flex items-center justify-center">
		<canvas ref="chartCanvas"></canvas>
	</div>
</template>

<script>
export default {
	name: "PieChartComponent",
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
				"#8B5CF6", // purple
				"#3B82F6", // blue
				"#06B6D4", // cyan
				"#14B8A6", // teal
				"#EC4899", // pink
				"#EF4444", // red
				"#F97316", // orange
				"#EAB308", // yellow
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
		async initChart() {
			// Load Chart.js if not already loaded
			if (!window.Chart) {
				await this.loadChartJS();
			}

			const ctx = this.$refs.chartCanvas.getContext("2d");

			// Extract data from the datasets
			const data =
				this.chartData.datasets && this.chartData.datasets[0]
					? this.chartData.datasets[0].values || this.chartData.datasets[0].data || []
					: [];

			this.chartInstance = new Chart(ctx, {
				type: "doughnut",
				data: {
					labels: this.chartData.labels || [],
					datasets: [
						{
							data: data,
							backgroundColor: this.colors,
							borderColor: "#ffffff",
							borderWidth: 2,
						},
					],
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: {
						legend: {
							display: true,
							position: "bottom",
							labels: {
								padding: 15,
								usePointStyle: true,
								font: {
									size: 12,
								},
							},
						},
						tooltip: {
							callbacks: {
								label: function (context) {
									const label = context.label || "";
									const value = context.parsed || 0;
									const total = context.dataset.data.reduce((a, b) => a + b, 0);
									const percentage =
										total > 0 ? ((value / total) * 100).toFixed(1) : 0;
									return `${label}: ${value} (${percentage}%)`;
								},
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

			const data =
				this.chartData.datasets && this.chartData.datasets[0]
					? this.chartData.datasets[0].values || this.chartData.datasets[0].data || []
					: [];

			this.chartInstance.data.labels = this.chartData.labels || [];
			this.chartInstance.data.datasets[0].data = data;
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
