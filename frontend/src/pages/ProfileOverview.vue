<template>
	<NoPermission v-if="!isLoggedIn" :page="__('Profile')" />
	<div v-if="loading" class="text-center py-20 bg-surface-white rounded-xl">
		<ProgressSpinner size="sm" :message="__('Loading user details...')" />
	</div>

	<div v-else class="bg-surface-white rounded-xl p-4 sm:p-6 lg:p-8">
		<ProfileHeader :allow-edit="false" :form="form" class="mb-6 md:mb-10" />
		<div class="flex justify-between items-center mb-6">
			<h2 class="text-2xl font-bold text-ink-gray-8">
				{{ __("Profile Overview") }}
			</h2>

			<router-link
				:to="{ name: 'Profile' }"
				class="flex items-center gap-2 px-5 py-2 bg-red-600 text-ink-white rounded-lg hover:bg-red-700 transition-colors font-semibold"
			>
				<LogIn class="w-5 h-5" />
				{{ __("Edit Profile") }}
			</router-link>
		</div>

		<div class="space-y-6">
			<div v-if="loading" class="flex items-center justify-center py-20">
				<ProgressSpinner size="md" />
			</div>

			<template v-else>
				<StatCards :stats="stats" />

				<HeatmapPanel v-model:year="selectedYear" :user-id="user" />

				<PieChartPanel v-model:field="percentageChartField" :user-id="user" />

				<LineChartPanel
					v-model:filter="lineChartFilter"
					v-model:timespan="timespan"
					:user-id="user"
				/>

				<RecentActivity :user-id="user" :limit="activityLimit" />
			</template>
		</div>
	</div>
</template>

<script setup>
import ProgressSpinner from "../components/Common/ProgressSpinner.vue";
import HeatmapPanel from "@/components/Profile/HeatmapPanel.vue";
import LineChartPanel from "@/components/Profile/LineChartPanel.vue";
import PieChartPanel from "@/components/Profile/PieChartPanel.vue";
import ProfileHeader from "@/components/Profile/ProfileHeader.vue";
import RecentActivity from "@/components/Profile/RecentActivity.vue";
import StatCards from "@/components/Profile/StatCards.vue";
import { createResource } from "frappe-ui";
import { LogIn } from "lucide-vue-next";
import { onMounted, reactive, ref } from "vue";
import NoPermission from "../components/NoPermission.vue";
import { sessionStore } from "../stores/session";

const { isLoggedIn, user } = sessionStore();

const loading = ref(true);
const form = reactive({});
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

function populateForm(data) {
	Object.keys(data).forEach((key) => {
		form[key] = data[key] !== null ? data[key] : "";
	});
}

const userDetailsResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.get_user_details",
	onSuccess(data) {
		if (data) {
			populateForm(data);
		}
		loading.value = false;
	},
	onError(err) {
		loading.value = false;
	},
});

const userPointsResource = createResource({
	url: "frappe.social.doctype.energy_point_log.energy_point_log.get_user_energy_and_review_points",
	makeParams: () => ({ user: user }),
	auto: true,
});

const userRankResource = createResource({
	url: "frappe.desk.page.user_profile.user_profile.get_user_rank",
	makeParams: () => ({ user: user }),
	auto: true,
});

onMounted(async () => {
	if (!isLoggedIn) return;

	loading.value = true;
	try {
		await Promise.all([
			userDetailsResource.fetch(),
			userPointsResource.fetch(),
			userRankResource.fetch(),
		]);

		const points = userPointsResource.data?.[user] || {};
		stats.energyPoints = points.energy_points || 0;
		stats.reviewPoints = points.review_points || 0;

		stats.rank = userRankResource.data?.all_time_rank?.[0] || 0;
		stats.monthRank = userRankResource.data?.monthly_rank?.[0] || 0;
	} catch (err) {
	} finally {
		loading.value = false;
	}
});
</script>
