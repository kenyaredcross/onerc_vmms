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
			default: () => ({ labels: [], datasets: [] }),
		},
	},
	data() {
		return { chartInstance: null };
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
		if (this.chartInstance) this.chartInstance.destroy();
	},
	methods: {
		async initChart() {
			if (!window.Chart) await this.loadChartJS();

			const ctx = this.$refs.chartCanvas.getContext("2d");

			const colors = [
				"#8B5CF6",
				"#3B82F6",
				"#06B6D4",
				"#14B8A6",
				"#EC4899",
				"#F97316",
				"#EAB308",
				"#FBBF24",
			];

			this.chartInstance = new Chart(ctx, {
				type: "line",
				data: {
					labels: this.chartData.labels || [],
					datasets: (this.chartData.datasets || []).map((d, idx) => ({
						label: d.name || `Dataset ${idx + 1}`,
						data: d.values || d.data || [],
						borderColor: colors[idx % colors.length],
						backgroundColor: colors[idx % colors.length] + "33",
						tension: 0.3,
						fill: true,
						pointRadius: 3,
						pointHoverRadius: 5,
						borderWidth: 2,
					})),
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					interaction: { mode: "index", intersect: false },
					plugins: {
						legend: {
							display: true,
							position: "top",
							labels: { boxWidth: 12, padding: 15, font: { size: 12 } },
						},
						tooltip: {
							backgroundColor: "#fff",
							titleColor: "#111",
							bodyColor: "#111",
							borderColor: "#ddd",
							borderWidth: 1,
							padding: 8,
							cornerRadius: 6,
							displayColors: true,
						},
					},
					scales: {
						x: {
							display: true,
							grid: { display: false },
							ticks: { color: "#4B5563", maxRotation: 0, minRotation: 0 },
						},
						y: {
							beginAtZero: true,
							grid: { color: "rgba(0,0,0,0.05)" },
							ticks: { color: "#4B5563", stepSize: 10 },
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

			const colors = [
				"#8B5CF6",
				"#3B82F6",
				"#06B6D4",
				"#14B8A6",
				"#EC4899",
				"#F97316",
				"#EAB308",
				"#FBBF24",
			];

			this.chartInstance.data.labels = this.chartData.labels || [];
			this.chartInstance.data.datasets = (this.chartData.datasets || []).map((d, idx) => ({
				label: d.name || `Dataset ${idx + 1}`,
				data: d.values || d.data || [],
				borderColor: colors[idx % colors.length],
				backgroundColor: colors[idx % colors.length] + "33",
				tension: 0.3,
				fill: true,
				pointRadius: 3,
				pointHoverRadius: 5,
				borderWidth: 2,
			}));

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
