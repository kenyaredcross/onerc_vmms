<template>
	<div class="space-y-6">
		<div class="flex justify-between items-center">
			<h2 class="text-2xl font-bold text-gray-800">{{ __("Energy Points Dashboard") }}</h2>
			<button
				@click="$emit('edit-profile')"
				class="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium shadow-md hover:shadow-lg"
			>
				{{ __("Edit Profile") }}
			</button>
		</div>

		<div v-if="loading" class="flex items-center justify-center py-20">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600"></div>
		</div>

		<template v-else>
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
				<StatCard
					icon="star"
					:value="energyPoints"
					:label="__('Energy Points')"
					color="bg-purple-500"
				/>
				<StatCard
					icon="users"
					:value="reviewPoints"
					:label="__('Review Points')"
					color="bg-blue-500"
				/>
				<StatCard
					icon="trending-up"
					:value="`#${rank}`"
					:label="__('All-Time Rank')"
					color="bg-teal-500"
				/>
				<StatCard
					icon="calendar"
					:value="`#${monthRank}`"
					:label="__('Monthly Rank')"
					color="bg-pink-500"
				/>
			</div>

			<div class="grid grid-cols-1 gap-6">
				<div class="bg-white rounded-lg shadow-md p-6">
					<div
						class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-3"
					>
						<h3 class="text-lg font-semibold text-gray-800">
							{{ __("Energy Points Trend") }}
						</h3>
						<div class="flex flex-wrap gap-2">
							<select
								v-model="lineChartFilter"
								@change="updateLineChartData"
								class="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
							>
								<option value="All">{{ __("All") }}</option>
								<option value="Auto">{{ __("Auto") }}</option>
								<option value="Appreciation">{{ __("Appreciation") }}</option>
								<option value="Criticism">{{ __("Criticism") }}</option>
								<option value="Revert">{{ __("Revert") }}</option>
							</select>
							<select
								v-model="timespan"
								@change="updateLineChartData"
								class="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
							>
								<option value="Last Week">{{ __("Last Week") }}</option>
								<option value="Last Month">{{ __("Last Month") }}</option>
								<option value="Last Quarter">{{ __("Last Quarter") }}</option>
								<option value="Last Year">{{ __("Last Year") }}</option>
							</select>
						</div>
					</div>
					<div class="h-64">
						<LineChartComponent :chart-data="lineChartData" />
					</div>
				</div>

				<div class="bg-white rounded-lg shadow-md p-6">
					<div class="flex justify-between items-center mb-4">
						<h3 class="text-lg font-semibold text-gray-800">
							{{ __("Type Distribution") }}
						</h3>
						<select
							v-model="percentageChartField"
							@change="updatePercentageChart"
							class="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
						>
							<option value="type">{{ __("Type") }}</option>
							<option value="reference_doctype">
								{{ __("Reference Doctype") }}
							</option>
							<option value="rule">{{ __("Rule") }}</option>
						</select>
					</div>
					<div class="h-64">
						<PieChartComponent :chart-data="pieChartData" />
					</div>
				</div>
			</div>

			<div class="bg-white rounded-lg shadow-md p-6">
				<div class="flex justify-between items-center mb-4">
					<h3 class="text-lg font-semibold text-gray-800">
						{{ __("Activity Heatmap") }}
					</h3>
					<select
						v-model="selectedYear"
						@change="updateHeatmapData"
						class="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
					>
						<option v-for="year in availableYears" :key="year" :value="year">
							{{ year }}
						</option>
					</select>
				</div>
				<div class="overflow-x-auto">
					<HeatmapComponent :heatmap-data="heatmapData" />
				</div>
			</div>

			<div class="bg-white rounded-lg shadow-md p-6">
				<h3 class="text-lg font-semibold text-gray-800 mb-4">
					{{ __("Recent Activity") }}
				</h3>
				<div v-if="activities.length === 0" class="text-center py-8 text-gray-500">
					{{ __("No activities to show") }}
				</div>
				<div v-else class="space-y-4">
					<div
						v-for="activity in activities"
						:key="activity.name"
						class="border-l-4 border-purple-500 pl-4 py-3 hover:bg-gray-50 transition-colors rounded-r"
					>
						<div class="flex justify-between items-start">
							<div class="flex-1">
								<div class="flex items-center gap-2 mb-1">
									<span :class="getActivityBadgeClass(activity.type)">
										{{ __(activity.type) }}
									</span>
									<span class="text-sm font-semibold text-purple-600">
										{{ activity.points > 0 ? "+" : "" }}{{ activity.points }}
										{{ __("pts") }}
									</span>
								</div>
								<p
									class="text-gray-700 text-sm"
									v-html="activity.formatted_message"
								></p>
								<p v-if="activity.user" class="text-xs text-gray-500 mt-1">
									{{ __("From") }}: {{ activity.user }}
								</p>
							</div>
							<span class="text-xs text-gray-500 whitespace-nowrap ml-4">
								{{ formatDate(activity.creation) }}
							</span>
						</div>
					</div>
				</div>
				<button
					v-if="hasMoreActivities"
					@click="loadMoreActivities"
					:disabled="loadingMore"
					class="mt-4 w-full py-2 text-purple-600 hover:text-purple-700 font-medium hover:bg-purple-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{{ loadingMore ? __("Loading...") : __("Show More Activity") }}
				</button>
			</div>
		</template>
	</div>
</template>

<script>
import { createResource } from "frappe-ui";
import { ref } from "vue";
import HeatmapComponent from "./HeatmapComponent.vue";
import LineChartComponent from "./LineChartComponent.vue";
import PieChartComponent from "./PieChartComponent.vue";
import StatCard from "./StatCard.vue";

export default {
	name: "EnergyPointsDashboard",
	components: {
		StatCard,
		LineChartComponent,
		PieChartComponent,
		HeatmapComponent,
	},
	props: {
		userId: {
			type: String,
			required: true,
		},
	},
	emits: ["edit-profile"],
	data() {
		return {
			activityLimit: 20,
			lineChartFilter: "All",
			timespan: "Last Month",
			interval: "Daily",
			selectedYear: new Date().getFullYear(),
			percentageChartField: "type",
			availableYears: [],
			lineChartData: { labels: [], datasets: [] },
			pieChartData: { labels: [], datasets: [] },
			heatmapData: [],

			activities: [],
			hasMoreActivities: false,
		};
	},

	setup(props) {
		const activityStart = ref(0);

		const activities = ref([]);
		const hasMoreActivities = ref(false);
		const activityLimit = 20;

		const formatActivityMessage = (activity) => {
			let message = activity.reason || "";
			if (activity.reference_doctype && activity.reference_name) {
				const link = `<a href="/app/${activity.reference_doctype}/${activity.reference_name}" class="text-blue-600 hover:underline">${activity.reference_name}</a>`;
				message = message.replace(activity.reference_name, link);
			}
			return message || `${activity.type} points awarded`;
		};

		const formatActivities = (activitiesData) => {
			return activitiesData.map((activity) => ({
				...activity,
				formatted_message: formatActivityMessage(activity),
			}));
		};

		const userPointsResource = createResource({
			url: "frappe.social.doctype.energy_point_log.energy_point_log.get_user_energy_and_review_points",
			makeParams() {
				return { user: props.userId };
			},
			auto: true,
		});

		const userRankResource = createResource({
			url: "frappe.desk.page.user_profile.user_profile.get_user_rank",
			makeParams() {
				return { user: props.userId };
			},
			auto: true,
		});

		const lineChartResource = createResource({
			url: "frappe.desk.doctype.dashboard_chart.dashboard_chart.get",
			auto: false,
		});

		const percentageChartResource = createResource({
			url: "frappe.desk.page.user_profile.user_profile.get_energy_points_percentage_chart_data",
			auto: false,
		});

		const heatmapResource = createResource({
			url: "frappe.desk.page.user_profile.user_profile.get_energy_points_heatmap_data",
			auto: false,
		});

		const initialActivitiesResource = createResource({
			url: "frappe.desk.page.user_profile.user_profile.get_energy_points_list",
			makeParams() {
				return {
					start: 0,
					limit: activityLimit,
					user: props.userId,
				};
			},

			onSuccess(data) {
				activities.value = formatActivities(data);
				hasMoreActivities.value = data.length === activityLimit;
			},
			auto: true,
		});

		const moreActivitiesResource = createResource({
			url: "frappe.desk.page.user_profile.user_profile.get_energy_points_list",
			makeParams() {
				return {
					start: activityStart.value,
					limit: activityLimit,
					user: props.userId,
				};
			},
			auto: false,
		});

		return {
			activityStart,
			activities,
			hasMoreActivities,
			userPointsResource,
			userRankResource,
			lineChartResource,
			percentageChartResource,
			heatmapResource,
			initialActivitiesResource,
			moreActivitiesResource,
		};
	},

	computed: {
		loading() {
			return (
				this.userPointsResource.loading ||
				this.userRankResource.loading ||
				this.lineChartResource.loading ||
				this.percentageChartResource.loading ||
				this.heatmapResource.loading ||
				this.initialActivitiesResource.loading
			);
		},
		loadingMore() {
			return this.moreActivitiesResource.loading;
		},
		energyPoints() {
			const data = this.userPointsResource.data?.[this.userId];
			return data?.energy_points || 0;
		},
		reviewPoints() {
			const data = this.userPointsResource.data?.[this.userId];
			return data?.review_points || 0;
		},
		rank() {
			return this.userRankResource.data?.all_time_rank?.[0] || 0;
		},
		monthRank() {
			return this.userRankResource.data?.monthly_rank?.[0] || 0;
		},
	},

	watch: {
		lineChartFilter: {
			handler() {
				this.updateLineChartData();
			},
			immediate: false,
		},
		timespan: {
			handler() {
				this.updateLineChartData();
			},
			immediate: false,
		},
		percentageChartField: {
			handler() {
				this.updatePercentageChart();
			},
			immediate: false,
		},
		selectedYear: {
			handler() {
				this.updateHeatmapData();
			},
			immediate: false,
		},
	},

	mounted() {
		this.generateAvailableYears();
		this.updateLineChartData();
		this.updatePercentageChart();
		this.updateHeatmapData();
	},

	methods: {
		loadMoreActivities() {
			this.activityStart = this.activityStart + this.activityLimit;

			this.moreActivitiesResource
				.fetch()
				.then(() => {
					const newActivities = this.moreActivitiesResource.data || [];
					if (newActivities.length) {
						this.activities.push(...this.formatActivities(newActivities));
						this.hasMoreActivities = newActivities.length === this.activityLimit;
					} else {
						this.hasMoreActivities = false;
					}
				})
				.catch(() => {});
		},

		formatActivities(activities) {
			return activities.map((activity) => ({
				...activity,
				formatted_message: this.formatActivityMessage(activity),
			}));
		},

		formatActivityMessage(activity) {
			let message = activity.reason || "";

			if (activity.reference_doctype && activity.reference_name) {
				const link = `<a href="/app/${activity.reference_doctype}/${activity.reference_name}" class="text-blue-600 hover:underline">${activity.reference_name}</a>`;
				message = message.replace(activity.reference_name, link);
			}

			return message || `${activity.type} points awarded`;
		},

		updateLineChartData() {
			const filters = [["Energy Point Log", "user", "=", this.userId, false]];

			if (this.lineChartFilter !== "All") {
				filters.push(["Energy Point Log", "type", "=", this.lineChartFilter, false]);
			} else {
				filters.push(["Energy Point Log", "type", "!=", "Review", false]);
			}

			const chartConfig = {
				timespan: this.timespan,
				time_interval: this.interval,
				type: "Line",
				value_based_on: "points",
				chart_type: "Sum",
				document_type: "Energy Point Log",
				name: "Energy Points",
				based_on: "creation",
				filters_json: JSON.stringify(filters),
			};

			this.lineChartResource.params = {
				chart: chartConfig,
				no_cache: 1,
			};

			this.lineChartResource.fetch().then(() => {
				const r = this.lineChartResource.data;
				if (r) {
					this.lineChartData = {
						labels: r.labels || [],
						datasets: r.datasets || [],
					};
				}
			});
		},

		updatePercentageChart() {
			this.percentageChartResource.params = {
				user: this.userId,
				field: this.percentageChartField,
			};

			this.percentageChartResource.fetch().then(() => {
				const r = this.percentageChartResource.data;
				if (r) {
					this.pieChartData = {
						labels: r.labels || [],
						datasets: r.datasets || [],
					};
				}
			});
		},

		updateHeatmapData() {
			const dateFrom = `${this.selectedYear}-01-01`;

			this.heatmapResource.params = {
				user: this.userId,
				date: dateFrom,
			};

			this.heatmapResource.fetch().then(() => {
				const r = this.heatmapResource.data;
				if (r) {
					this.heatmapData = r;
				}
			});
		},

		generateAvailableYears() {
			const currentYear = new Date().getFullYear();
			const years = [];
			for (let i = currentYear; i >= currentYear - 5; i--) {
				years.push(i);
			}
			this.availableYears = years;
		},

		formatDate(dateString) {
			const date = new Date(dateString);
			return date.toLocaleDateString("en-US", {
				month: "short",
				day: "numeric",
				hour: "2-digit",
				minute: "2-digit",
			});
		},

		getActivityBadgeClass(type) {
			const baseClasses = "px-2 py-1 text-xs font-semibold rounded";
			const typeClasses = {
				Appreciation: "bg-green-100 text-green-800",
				Criticism: "bg-red-100 text-red-800",
				Auto: "bg-blue-100 text-blue-800",
				Revert: "bg-orange-100 text-orange-800",
				Review: "bg-purple-100 text-purple-800",
			};
			return `${baseClasses} ${typeClasses[type] || "bg-gray-100 text-gray-800"}`;
		},

		__(text) {
			return window.__ ? window.__(text) : text;
		},
	},
	errorCaptured(err, vm, info) {
		console.error("Resource Error:", err, info);
		this.$toast.error("An error occurred while loading dashboard data.");
		return false;
	},
};
</script>
