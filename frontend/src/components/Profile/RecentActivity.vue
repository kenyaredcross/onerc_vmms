<template>
	<div class="bg-surface-white rounded-lg border border-outline-gray-2 p-6">
		<h3 class="text-lg font-semibold text-ink-gray-8 mb-4">Recent Activity</h3>

		<div v-if="activities.length === 0" class="text-center py-8 text-ink-gray-8">
			No activities to show
		</div>

		<div v-else class="space-y-4">
			<div
				v-for="activity in activities"
				:key="activity.name"
				class="border-l-4 border-purple-500 pl-4 py-3 hover:bg-surface-gray-5 transition-colors rounded-r"
			>
				<div class="flex justify-between items-start">
					<div class="flex-1">
						<div class="flex items-center gap-2 mb-1">
							<span :class="getBadgeClass(activity.type)">{{ activity.type }}</span>
							<span class="text-sm font-semibold text-purple-600"
								>{{ activity.points > 0 ? "+" : ""
								}}{{ activity.points }} pts</span
							>
						</div>
						<p
							class="text-ink-gray-1-700 text-sm"
							v-html="sanitizeHtml(activity.formatted_message)"
						></p>
						<p v-if="activity.user" class="text-xs text-ink-gray-1-500 mt-1">
							From: {{ activity.user }}
						</p>
					</div>
					<span class="text-xs text-ink-gray-1-500 whitespace-nowrap ml-4">{{
						formatDate(activity.creation)
					}}</span>
				</div>
			</div>
		</div>

		<button
			v-if="hasMore"
			@click="loadMore"
			:disabled="loadingMore"
			class="mt-4 w-full py-2 text-purple-600 hover:text-purple-700 font-medium hover:bg-purple-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
		>
			{{ loadingMore ? "Loading..." : "Show More Activity" }}
		</button>
	</div>
</template>

<script setup>
import { createResource } from "frappe-ui";
import { onMounted, ref } from "vue";
import { sanitizeHtml } from "../../utils/sanitizeHtml";

const props = defineProps({
	userId: { type: String, required: true },
	limit: { type: Number, default: 20 },
});

const activityStart = ref(0);
const activities = ref([]);
const hasMore = ref(false);
const loadingMore = ref(false);

const resource = createResource({
	url: "frappe.desk.page.user_profile.user_profile.get_energy_points_list",
	makeParams: () => ({ start: activityStart.value, limit: props.limit, user: props.userId }),
	auto: false,
});

function escapeHtml(value) {
	return String(value ?? "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;");
}

function formatActivityMessage(activity) {
	let msg = escapeHtml(activity.reason || "");
	if (activity.reference_doctype && activity.reference_name) {
		const href = `/app/${encodeURIComponent(activity.reference_doctype)}/${encodeURIComponent(
			activity.reference_name
		)}`;
		const link = `<a href="${href}" class="text-blue-600 hover:underline">${escapeHtml(
			activity.reference_name
		)}</a>`;
		msg = msg.replace(escapeHtml(activity.reference_name), () => link);
	}
	return msg || `${escapeHtml(activity.type)} points awarded`;
}

function fetchActivities() {
	resource
		.fetch()
		.then(() => {
			const data = resource.data || [];
			activities.value.push(
				...data.map((a) => ({ ...a, formatted_message: formatActivityMessage(a) }))
			);
			hasMore.value = data.length === props.limit;
			loadingMore.value = false;
		})
		.catch(() => {
			loadingMore.value = false;
		});
}

function loadMore() {
	loadingMore.value = true;
	activityStart.value += props.limit;
	fetchActivities();
}

function getBadgeClass(type) {
	const classes = {
		Appreciation: "bg-green-100 text-green-800",
		Criticism: "bg-red-100 text-red-800",
		Auto: "bg-blue-100 text-blue-800",
		Revert: "bg-orange-100 text-orange-800",
		Review: "bg-purple-100 text-purple-800",
	};
	return `px-2 py-1 text-xs font-semibold rounded ${
		classes[type] || "bg-surface-gray-100 text-ink-gray-1-800"
	}`;
}

function formatDate(date) {
	const d = new Date(date);
	return d.toLocaleDateString("en-US", {
		month: "short",
		day: "numeric",
		hour: "2-digit",
		minute: "2-digit",
	});
}

onMounted(() => {
	fetchActivities();
});
</script>
