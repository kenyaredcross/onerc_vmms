<template>
	<div class="overflow-x-auto">
		<div class="relative w-full min-w-min heatmap-container">
			<div v-if="!heatmapData || Object.keys(heatmapData).length === 0" class="empty-state">
				<svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
					/>
				</svg>
				<p class="empty-text">{{ __("No activity data available") }}</p>
				<p class="empty-subtext">{{ __("Start contributing to see your heatmap") }}</p>
			</div>

			<div v-else class="heatmap-wrapper">
				<div class="heatmap-scroll-container">
					<div class="heatmap-main-grid">
						<!-- Day Labels Column -->
						<div class="day-labels-column">
							<div class="day-labels-spacer"></div>
							<div class="day-labels-list">
								<div
									v-for="day in dayLabels"
									:key="day.index"
									class="day-label-wrapper"
								>
									<span v-if="day.visible" class="day-label">{{
										day.abbr
									}}</span>
									<span v-else class="day-label day-label-hidden">{{
										day.abbr
									}}</span>
								</div>
							</div>
						</div>

						<!-- Months Grid -->
						<div class="months-grid">
							<div
								v-for="(monthData, index) in monthlyData"
								:key="index"
								class="month-column"
							>
								<div class="month-header">{{ monthData.name }}</div>
								<div class="month-days-wrapper">
									<div
										v-for="(weekdayRow, rowIndex) in monthData.daysByWeekday"
										:key="rowIndex"
										class="weekday-row"
									>
										<div
											v-for="(dataPoint, colIndex) in weekdayRow"
											:key="colIndex"
											:title="dataPoint.isEmpty ? '' : getTooltip(dataPoint)"
											:class="[
												'heatmap-cell',
												{ 'empty-cell': dataPoint.isEmpty },
												!dataPoint.isEmpty &&
													getIntensityClass(dataPoint.count),
											]"
											:data-count="dataPoint.count"
											:data-day="
												dataPoint.date
													? getDayOfWeek(dataPoint.date)
													: null
											"
											@mouseenter="
												!dataPoint.isEmpty &&
												showTooltip(dataPoint, $event)
											"
											@mouseleave="hideTooltip"
											@click="
												!dataPoint.isEmpty && handleCellClick(dataPoint)
											"
										>
											<div v-if="!dataPoint.isEmpty" class="cell-glow"></div>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div class="legend-container">
					<span class="legend-text">{{ __("Less") }}</span>
					<div class="legend-squares">
						<div class="legend-square intensity-0">
							<div class="square-glow"></div>
						</div>
						<div class="legend-square intensity-1">
							<div class="square-glow"></div>
						</div>
						<div class="legend-square intensity-2">
							<div class="square-glow"></div>
						</div>
						<div class="legend-square intensity-3">
							<div class="square-glow"></div>
						</div>
						<div class="legend-square intensity-4">
							<div class="square-glow"></div>
						</div>
					</div>
					<span class="legend-text">{{ __("More") }}</span>
				</div>
			</div>

			<div
				v-if="tooltip.show"
				class="heatmap-tooltip"
				:style="{ top: tooltip.y + 'px', left: tooltip.x + 'px' }"
			>
				<div class="tooltip-inner">
					<div class="tooltip-count">{{ tooltip.count }} {{ __("points") }}</div>
					<div class="tooltip-date">{{ tooltip.date }}</div>
				</div>
				<div class="tooltip-arrow"></div>
			</div>
		</div>
	</div>

	<div class="stats-panel">
		<div class="stat-item">
			<div class="stat-value">{{ totalContributions }}</div>
			<div class="stat-label">{{ __("Total Points") }}</div>
		</div>
		<div class="stat-divider"></div>
		<div class="stat-item">
			<div class="stat-value">{{ longestStreak }}</div>
			<div class="stat-label">{{ __("Longest Streak") }}</div>
		</div>
		<div class="stat-divider"></div>
		<div class="stat-item">
			<div class="stat-value">{{ currentStreak }}</div>
			<div class="stat-label">{{ __("Current Streak") }}</div>
		</div>
	</div>
</template>

<script>
import { format } from "date-fns";
import { computed, ref, watch } from "vue";

export default {
	name: "HeatmapComponent",
	props: {
		heatmapData: {
			type: [Object],
			default: () => ({}),
		},
		year: {
			type: [Number, String],
			required: true,
		},
	},
	setup(props) {
		const monthLabels = [
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
		];

		const dayLabels = [
			{ index: 0, abbr: "Sun", visible: false },
			{ index: 1, abbr: "Mon", visible: true },
			{ index: 2, abbr: "Tue", visible: false },
			{ index: 3, abbr: "Wed", visible: true },
			{ index: 4, abbr: "Thu", visible: false },
			{ index: 5, abbr: "Fri", visible: true },
			{ index: 6, abbr: "Sat", visible: false },
		];

		const tooltip = ref({
			show: false,
			x: 0,
			y: 0,
			count: 0,
			date: "",
		});

		const startDate = computed(() => format(new Date(props.year, 0, 1), "yyyy-MM-dd"));
		const endDate = computed(() => format(new Date(props.year, 11, 31), "yyyy-MM-dd"));

		const processedData = computed(() => {
			const data = {};
			const start = new Date(startDate.value);
			const end = new Date(endDate.value);
			let currentDate = new Date(start);

			while (currentDate <= end) {
				const dateString = format(currentDate, "yyyy-MM-dd");
				data[dateString] = props.heatmapData[dateString] || 0;
				currentDate.setDate(currentDate.getDate() + 1);
			}

			const dataArray = Object.entries(data).map(([date, count]) => ({
				date,
				count: count || 0,
			}));
			return dataArray.sort((a, b) => new Date(a.date) - new Date(b.date));
		});

		const monthlyData = computed(() => {
			const months = [];

			for (let monthIndex = 0; monthIndex < 12; monthIndex++) {
				const monthStart = new Date(props.year, monthIndex, 1);
				const monthEnd = new Date(props.year, monthIndex + 1, 0);
				const daysInMonth = monthEnd.getDate();

				const daysByWeekday = Array.from({ length: 7 }, () => []);

				for (let day = 1; day <= daysInMonth; day++) {
					const date = new Date(props.year, monthIndex, day);
					const dateString = format(date, "yyyy-MM-dd");
					const dayOfWeek = date.getDay();

					daysByWeekday[dayOfWeek].push({
						date: dateString,
						count: props.heatmapData[dateString] || 0,
						isEmpty: false,
					});
				}

				const maxWeeks = Math.max(...daysByWeekday.map((row) => row.length));
				daysByWeekday.forEach((row) => {
					while (row.length < maxWeeks) {
						row.push({
							date: null,
							count: 0,
							isEmpty: true,
						});
					}
				});

				months.push({
					name: monthLabels[monthIndex],
					daysByWeekday: daysByWeekday,
					maxWeeks: maxWeeks,
				});
			}

			return months;
		});

		const maxCount = computed(() => {
			if (processedData.value.length === 0) return 1;
			return Math.max(...processedData.value.map((d) => d.count || 0), 1);
		});

		const totalContributions = computed(() => {
			return processedData.value.reduce((sum, d) => sum + (d.count || 0), 0);
		});

		const longestStreak = computed(() => {
			let maxStreak = 0;
			let currentStreakCount = 0;

			processedData.value.forEach((d) => {
				if (d.count > 0) {
					currentStreakCount++;
					maxStreak = Math.max(maxStreak, currentStreakCount);
				} else {
					currentStreakCount = 0;
				}
			});

			return maxStreak;
		});

		const currentStreak = computed(() => {
			let streak = 0;
			for (let i = processedData.value.length - 1; i >= 0; i--) {
				if (processedData.value[i].count > 0) {
					streak++;
				} else {
					break;
				}
			}
			return streak;
		});

		function getDayOfWeek(dateString) {
			return new Date(dateString).getDay();
		}

		function getIntensityClass(count) {
			if (!count || count === 0) return "intensity-0";

			const percentage = (count / maxCount.value) * 100;

			if (percentage < 20) return "intensity-1";
			if (percentage < 40) return "intensity-2";
			if (percentage < 60) return "intensity-3";
			return "intensity-4";
		}

		function getTooltip(dataPoint) {
			const date = new Date(dataPoint.date);
			const formattedDate = format(date, "MMM dd, yyyy");
			return `${dataPoint.count || 0} points on ${formattedDate}`;
		}

		function showTooltip(dataPoint, event) {
			const date = new Date(dataPoint.date);
			const formattedDate = format(date, "MMM dd, yyyy");

			const rect = event.target.getBoundingClientRect();
			const scrollX = window.scrollX || window.pageXOffset;
			const scrollY = window.scrollY || window.pageYOffset;

			tooltip.value = {
				show: true,
				x: rect.left + rect.width / 2 + scrollX,
				y: rect.top + scrollY - 10,
				count: dataPoint.count || 0,
				date: formattedDate,
			};
		}

		function hideTooltip() {
			tooltip.value.show = false;
		}

		function handleCellClick(dataPoint) {
			console.log("Clicked:", dataPoint);
		}

		function __(text) {
			return window.__ ? window.__(text) : text;
		}

		watch(
			() => props.heatmapData,
			() => processedData.value,
			{ deep: true },
		);

		return {
			dayLabels,
			tooltip,
			processedData,
			monthlyData,
			maxCount,
			totalContributions,
			longestStreak,
			currentStreak,
			getDayOfWeek,
			getIntensityClass,
			getTooltip,
			showTooltip,
			hideTooltip,
			handleCellClick,
			__,
		};
	},
};
</script>

<style scoped>
.heatmap-container {
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif;
	--color-primary: #10b981;
	--color-bg: #ffffff;
	--color-text-primary: #111827;
	--color-text-secondary: #6b7280;
	--color-border: #e5e7eb;
	--color-shadow: rgba(0, 0, 0, 0.05);
	--cell-size: 14px;
	--cell-gap: 3px;
	--transition-smooth: cubic-bezier(0.4, 0, 0.2, 1);
}

.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 4rem 2rem;
	background: var(--color-bg);
	border-radius: 16px;
	box-shadow: 0 1px 3px var(--color-shadow);
	border: 1px solid var(--color-border);
}

.empty-icon {
	width: 64px;
	height: 64px;
	color: #d1d5db;
	margin-bottom: 1rem;
	animation: float 3s ease-in-out infinite;
}

.empty-text {
	font-size: 1.125rem;
	font-weight: 600;
	color: var(--color-text-primary);
	margin-bottom: 0.5rem;
}

.empty-subtext {
	font-size: 0.875rem;
	color: var(--color-text-secondary);
}

.heatmap-wrapper {
	background: var(--color-bg);
	border-radius: 16px;
	padding: 1.5rem;
	box-shadow: 0 1px 3px var(--color-shadow);
	border: 1px solid var(--color-border);
	display: flex;
	flex-direction: column;
	gap: 1.5rem;
	overflow: hidden;
}

.heatmap-scroll-container {
	overflow-x: auto;
	overflow-y: hidden;
	-webkit-overflow-scrolling: touch;
	scrollbar-width: thin;
	scrollbar-color: var(--color-border) transparent;
}

.heatmap-scroll-container::-webkit-scrollbar {
	height: 8px;
}

.heatmap-scroll-container::-webkit-scrollbar-track {
	background: transparent;
	border-radius: 4px;
}

.heatmap-scroll-container::-webkit-scrollbar-thumb {
	background: var(--color-border);
	border-radius: 4px;
}

.heatmap-scroll-container::-webkit-scrollbar-thumb:hover {
	background: var(--color-text-secondary);
}

.heatmap-main-grid {
	display: flex;
	gap: 0.75rem;
	min-width: min-content;
}

.day-labels-column {
	display: flex;
	flex-direction: column;
	flex-shrink: 0;
}

.day-labels-spacer {
	height: calc(1.5rem + 0.5rem + 0.25rem);
	flex-shrink: 0;
}

.day-labels-list {
	display: flex;
	flex-direction: column;
	gap: var(--cell-gap);
}

.day-label-wrapper {
	display: flex;
	align-items: center;
	height: var(--cell-size);
}

.day-label {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	font-size: 0.7rem;
	font-weight: 500;
	color: var(--color-text-secondary);
	user-select: none;
	padding-right: 0.5rem;
	white-space: nowrap;
}

.day-label-hidden {
	opacity: 0;
	visibility: hidden;
}

.months-grid {
	display: grid;
	grid-template-columns: repeat(12, minmax(60px, 1fr));
	gap: 0.75rem;
	width: 100%;
	min-width: min-content;
}

.month-column {
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
	min-width: 0;
}

.month-header {
	font-size: 0.75rem;
	font-weight: 600;
	color: var(--color-text-secondary);
	text-transform: uppercase;
	letter-spacing: 0.025em;
	text-align: center;
	padding-bottom: 0.25rem;
	border-bottom: 2px solid var(--color-border);
}

.month-days-wrapper {
	display: flex;
	flex-direction: column;
	gap: var(--cell-gap);
}

.weekday-row {
	display: flex;
	gap: var(--cell-gap);
	justify-content: center;
}

.heatmap-cell {
	width: var(--cell-size);
	height: var(--cell-size);
	border-radius: 3px;
	cursor: pointer;
	transition: all 0.25s var(--transition-smooth);
	position: relative;
	border: 1px solid transparent;
}

.heatmap-cell.empty-cell {
	background: transparent;
	border: none;
	cursor: default;
	pointer-events: none;
}

.heatmap-cell:not(.empty-cell):hover {
	transform: scale(1.25);
	z-index: 10;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.heatmap-cell:not(.empty-cell):active {
	transform: scale(1.15);
}

.cell-glow {
	position: absolute;
	inset: -3px;
	border-radius: 4px;
	opacity: 0;
	transition: opacity 0.25s ease;
	pointer-events: none;
}

.heatmap-cell:hover .cell-glow {
	opacity: 1;
	animation: pulse 1.5s ease-in-out infinite;
}

.intensity-0 {
	background: #f3f4f6;
	border-color: #e5e7eb;
}

.intensity-0:hover {
	background: #e5e7eb;
	border-color: #d1d5db;
}

.intensity-1 {
	background: #d1fae5;
	border-color: #a7f3d0;
}

.intensity-1:hover {
	background: #a7f3d0;
	border-color: #6ee7b7;
}

.intensity-1 .cell-glow {
	background: radial-gradient(circle, rgba(16, 185, 129, 0.3) 0%, transparent 70%);
}

.intensity-2 {
	background: #6ee7b7;
	border-color: #34d399;
}

.intensity-2:hover {
	background: #34d399;
	border-color: #10b981;
}

.intensity-2 .cell-glow {
	background: radial-gradient(circle, rgba(16, 185, 129, 0.4) 0%, transparent 70%);
}

.intensity-3 {
	background: #10b981;
	border-color: #059669;
}

.intensity-3:hover {
	background: #059669;
	border-color: #047857;
}

.intensity-3 .cell-glow {
	background: radial-gradient(circle, rgba(16, 185, 129, 0.5) 0%, transparent 70%);
}

.intensity-4 {
	background: #047857;
	border-color: #065f46;
}

.intensity-4:hover {
	background: #065f46;
	border-color: #064e3b;
}

.intensity-4 .cell-glow {
	background: radial-gradient(circle, rgba(16, 185, 129, 0.6) 0%, transparent 70%);
}

.legend-container {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 0.75rem;
	margin-top: 1.5rem;
	padding-top: 1.5rem;
	border-top: 1px solid var(--color-border);
}

.legend-text {
	font-size: 0.75rem;
	font-weight: 500;
	color: var(--color-text-secondary);
	user-select: none;
}

.legend-squares {
	display: flex;
	gap: var(--cell-gap);
}

.legend-square {
	width: var(--cell-size);
	height: var(--cell-size);
	border-radius: 3px;
	cursor: pointer;
	transition: all 0.25s var(--transition-smooth);
	position: relative;
	border: 1px solid transparent;
}

.legend-square:hover {
	transform: scale(1.2);
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.square-glow {
	position: absolute;
	inset: -2px;
	border-radius: 3px;
	opacity: 0;
	transition: opacity 0.25s ease;
	pointer-events: none;
}

.legend-square:hover .square-glow {
	opacity: 1;
}

.stats-panel {
	display: flex;
	justify-content: space-around;
	align-items: center;
	margin-top: 1.5rem;
	padding: 1.25rem;
	background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
	border-radius: 12px;
	border: 1px solid #d1fae5;
}

.stat-item {
	text-align: center;
	flex: 1;
}

.stat-value {
	font-size: 1.875rem;
	font-weight: 700;
	color: var(--color-primary);
	margin-bottom: 0.25rem;
}

.stat-label {
	font-size: 0.8125rem;
	font-weight: 500;
	color: var(--color-text-secondary);
	text-transform: uppercase;
	letter-spacing: 0.025em;
}

.stat-divider {
	width: 1px;
	height: 2.5rem;
	background: linear-gradient(
		to bottom,
		transparent 0%,
		var(--color-border) 50%,
		transparent 100%
	);
}

.heatmap-tooltip {
	position: fixed;
	transform: translate(-50%, -100%);
	z-index: 1000;
	pointer-events: none;
	animation: tooltipFadeIn 0.2s ease-out;
}

.tooltip-inner {
	background: rgba(17, 24, 39, 0.95);
	backdrop-filter: blur(8px);
	color: white;
	padding: 0.625rem 0.875rem;
	border-radius: 8px;
	box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
	border: 1px solid rgba(255, 255, 255, 0.1);
	white-space: nowrap;
}

.tooltip-count {
	font-size: 0.8125rem;
	font-weight: 600;
	margin-bottom: 0.125rem;
}

.tooltip-date {
	font-size: 0.6875rem;
	opacity: 0.8;
}

.tooltip-arrow {
	width: 0;
	height: 0;
	border-left: 5px solid transparent;
	border-right: 5px solid transparent;
	border-top: 5px solid rgba(17, 24, 39, 0.95);
	position: absolute;
	bottom: -5px;
	left: 50%;
	transform: translateX(-50%);
}

@keyframes float {
	0%,
	100% {
		transform: translateY(0);
	}
	50% {
		transform: translateY(-10px);
	}
}

@keyframes pulse {
	0%,
	100% {
		opacity: 0.5;
		transform: scale(1);
	}
	50% {
		opacity: 1;
		transform: scale(1.05);
	}
}

@keyframes tooltipFadeIn {
	from {
		opacity: 0;
		transform: translate(-50%, calc(-100% - 5px));
	}
	to {
		opacity: 1;
		transform: translate(-50%, -100%);
	}
}

@media (max-width: 1536px) {
	.heatmap-container {
		--cell-size: 13px;
	}
}

@media (max-width: 1280px) {
	.heatmap-container {
		--cell-size: 12px;
	}
}

@media (max-width: 1024px) {
	.heatmap-container {
		--cell-size: 11px;
		--cell-gap: 2.5px;
	}

	.heatmap-wrapper {
		padding: 1.25rem;
	}

	.day-label {
		font-size: 0.65rem;
		padding-right: 0.375rem;
	}

	.month-header {
		font-size: 0.7rem;
	}

	.stat-value {
		font-size: 1.5rem;
	}

	.stat-label {
		font-size: 0.75rem;
	}
}

@media (max-width: 768px) {
	.heatmap-container {
		--cell-size: 10px;
		--cell-gap: 2px;
	}

	.heatmap-wrapper {
		padding: 1rem;
		border-radius: 12px;
	}

	.heatmap-main-grid {
		gap: 0.5rem;
	}

	.months-grid {
		gap: 0.5rem;
	}

	.day-label {
		font-size: 0.625rem;
		padding-right: 0.25rem;
	}

	.month-header {
		font-size: 0.65rem;
		padding-bottom: 0.2rem;
	}

	.stat-divider {
		width: 100%;
		height: 1px;
		background: linear-gradient(
			to right,
			transparent 0%,
			var(--color-border) 50%,
			transparent 100%
		);
	}

	.stat-value {
		font-size: 1.375rem;
	}
}

@media (max-width: 640px) {
	.heatmap-container {
		--cell-size: 9px;
	}

	.day-label {
		font-size: 0.6rem;
	}

	.month-header {
		font-size: 0.625rem;
	}

	.legend-container {
		flex-wrap: wrap;
		gap: 0.5rem;
	}
}

@media (max-width: 480px) {
	.heatmap-container {
		--cell-size: 8px;
		--cell-gap: 1.5px;
	}

	.heatmap-wrapper {
		padding: 0.875rem;
	}

	.empty-state {
		padding: 2.5rem 1.25rem;
	}

	.empty-icon {
		width: 48px;
		height: 48px;
	}

	.empty-text {
		font-size: 1rem;
	}

	.empty-subtext {
		font-size: 0.8125rem;
	}

	.months-grid {
		gap: 0.375rem;
	}

	.month-header {
		font-size: 0.6rem;
	}

	.day-label {
		font-size: 0.55rem;
		padding-right: 0.2rem;
	}

	.stats-panel {
		padding: 1rem;
	}

	.stat-value {
		font-size: 1.25rem;
	}

	.stat-label {
		font-size: 0.7rem;
	}
}

@media print {
	.heatmap-wrapper {
		box-shadow: none;
		border: 1px solid #000;
	}

	.heatmap-cell:hover {
		transform: none;
		box-shadow: none;
	}

	.stats-panel {
		break-inside: avoid;
	}
}
</style>
