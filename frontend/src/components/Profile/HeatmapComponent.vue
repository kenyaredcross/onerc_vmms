<template>
	<div class="heatmap-container">
		<div
			v-if="!heatmapData || heatmapData.length === 0"
			class="text-center py-8 text-gray-500"
		>
			{{ __("No activity data available") }}
		</div>
		<div v-else class="heatmap-wrapper">
			<div class="flex">
				<!-- Month Labels -->
				<div class="flex-1">
					<div class="flex justify-between text-xs text-gray-500 mb-2">
						<span v-for="month in monthLabels" :key="month">{{ month }}</span>
					</div>

					<!-- Heatmap Grid -->
					<div class="grid grid-flow-col gap-1" :style="gridStyle">
						<div
							v-for="(dataPoint, index) in processedData"
							:key="index"
							:title="getTooltip(dataPoint)"
							:class="['heatmap-cell', getIntensityClass(dataPoint.count)]"
							@mouseenter="showTooltip(dataPoint, $event)"
							@mouseleave="hideTooltip"
						></div>
					</div>

					<!-- Legend -->
					<div class="flex items-center justify-end gap-2 mt-3 text-xs text-gray-600">
						<span>{{ __("Less") }}</span>
						<div class="flex gap-1">
							<div class="heatmap-cell intensity-0"></div>
							<div class="heatmap-cell intensity-1"></div>
							<div class="heatmap-cell intensity-2"></div>
							<div class="heatmap-cell intensity-3"></div>
							<div class="heatmap-cell intensity-4"></div>
						</div>
						<span>{{ __("More") }}</span>
					</div>
				</div>
			</div>
		</div>

		<!-- Tooltip -->
		<div
			v-if="tooltip.show"
			class="heatmap-tooltip"
			:style="{ top: tooltip.y + 'px', left: tooltip.x + 'px' }"
		>
			<div class="font-semibold">{{ tooltip.count }} {{ __("points") }}</div>
			<div class="text-xs">{{ tooltip.date }}</div>
		</div>
	</div>
</template>

<script>
export default {
	name: "HeatmapComponent",
	props: {
		heatmapData: {
			type: [Object, Array],
			default: () => [],
		},
	},
	data() {
		return {
			monthLabels: [
				"Jan",
				"Feb",
				"Mar",
				"Apr",
				"May",
				"Jun",
				"Jul",
				"Aug",
				"Sep",
				"Oct",
				"Nov",
				"Dec",
			],
			tooltip: {
				show: false,
				x: 0,
				y: 0,
				count: 0,
				date: "",
			},
		};
	},
	computed: {
		processedData() {
			if (!this.heatmapData) return [];

			// Convert object to array if necessary
			const dataArray = Array.isArray(this.heatmapData)
				? this.heatmapData
				: Object.entries(this.heatmapData).map(([date, count]) => ({
						date,
						count: count || 0,
					}));

			// Sort by date
			return dataArray.sort((a, b) => new Date(a.date) - new Date(b.date));
		},

		maxCount() {
			if (this.processedData.length === 0) return 1;
			return Math.max(...this.processedData.map((d) => d.count || 0), 1);
		},

		gridStyle() {
			// Calculate number of weeks (columns)
			const weeks = Math.ceil(this.processedData.length / 7);
			return {
				gridTemplateRows: "repeat(7, minmax(0, 1fr))",
				gridTemplateColumns: `repeat(${weeks}, minmax(0, 1fr))`,
			};
		},
	},
	methods: {
		getIntensityClass(count) {
			if (!count || count === 0) return "intensity-0";

			const percentage = (count / this.maxCount) * 100;

			if (percentage < 20) return "intensity-1";
			if (percentage < 40) return "intensity-2";
			if (percentage < 60) return "intensity-3";
			return "intensity-4";
		},

		getTooltip(dataPoint) {
			const date = new Date(dataPoint.date);
			const formattedDate = date.toLocaleDateString("en-US", {
				year: "numeric",
				month: "short",
				day: "numeric",
			});
			return `${dataPoint.count || 0} points on ${formattedDate}`;
		},

		showTooltip(dataPoint, event) {
			const date = new Date(dataPoint.date);
			const formattedDate = date.toLocaleDateString("en-US", {
				year: "numeric",
				month: "short",
				day: "numeric",
			});

			this.tooltip = {
				show: true,
				x: event.pageX + 10,
				y: event.pageY - 40,
				count: dataPoint.count || 0,
				date: formattedDate,
			};
		},

		hideTooltip() {
			this.tooltip.show = false;
		},

		__(text) {
			return window.__ ? window.__(text) : text;
		},
	},
};
</script>

<style scoped>
.heatmap-container {
	position: relative;
	min-width: 800px;
}

.heatmap-wrapper {
	background: #f9fafb;
	border-radius: 0.5rem;
	padding: 1rem;
}

.heatmap-cell {
	width: 12px;
	height: 12px;
	border-radius: 2px;
	transition: all 0.2s ease;
	cursor: pointer;
}

.heatmap-cell:hover {
	transform: scale(1.2);
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.intensity-0 {
	background-color: #ebedf0;
}

.intensity-1 {
	background-color: #c6e48b;
}

.intensity-2 {
	background-color: #7bc96f;
}

.intensity-3 {
	background-color: #239a3b;
}

.intensity-4 {
	background-color: #196127;
}

.heatmap-tooltip {
	position: fixed;
	background: rgba(0, 0, 0, 0.9);
	color: white;
	padding: 0.5rem 0.75rem;
	border-radius: 0.375rem;
	font-size: 0.875rem;
	pointer-events: none;
	z-index: 1000;
	box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
</style>
