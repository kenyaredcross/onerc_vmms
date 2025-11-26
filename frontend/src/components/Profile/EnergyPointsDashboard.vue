<template>
	<div class="space-y-6">
		<div v-if="loading" class="flex items-center justify-center py-20">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600"></div>
		</div>

		<template v-else>
			<StatCards :stats="stats" />

			<LineChartPanel
				v-model:filter="lineChartFilter"
				v-model:timespan="timespan"
				:user-id="userId"
			/>

			<PieChartPanel v-model:field="percentageChartField" :user-id="userId" />

			<HeatmapPanel v-model:year="selectedYear" :user-id="userId" />

			<RecentActivity :user-id="userId" :limit="activityLimit" />
		</template>
	</div>
</template>

<script setup>
import { createResource } from "frappe-ui";
import { reactive, ref, watchEffect } from "vue";
import HeatmapPanel from "./HeatmapPanel.vue";
import LineChartPanel from "./LineChartPanel.vue";
import PieChartPanel from "./PieChartPanel.vue";
import RecentActivity from "./RecentActivity.vue";
import StatCards from "./StatCards.vue";

const props = defineProps({
	userId: { type: String, required: true },
});

const loading = ref(true);
const stats = reactive({
	energyPoints: 0,
	reviewPoints: 0,
	rank: 0,
	monthRank: 0,
});

const lineChartFilter = ref("All");
const timespan = ref("Last Month");
const percentageChartField = ref("type");
const selectedYear = ref(new Date().getFullYear());
const activityLimit = ref(20);

// Resources
const userPointsResource = createResource({
	url: "frappe.social.doctype.energy_point_log.energy_point_log.get_user_energy_and_review_points",
	makeParams: () => ({ user: props.userId }),
	auto: true,
});

const userRankResource = createResource({
	url: "frappe.desk.page.user_profile.user_profile.get_user_rank",
	makeParams: () => ({ user: props.userId }),
	auto: true,
});

watchEffect(() => {
	if (userPointsResource.data) {
		const data = userPointsResource.data?.[props.userId] || {};
		stats.energyPoints = data.energy_points || 0;
		stats.reviewPoints = data.review_points || 0;
	}
	if (userRankResource.data) {
		stats.rank = userRankResource.data?.all_time_rank?.[0] || 0;
		stats.monthRank = userRankResource.data?.monthly_rank?.[0] || 0;
	}

	loading.value = userPointsResource.loading || userRankResource.loading;
});
</script>
