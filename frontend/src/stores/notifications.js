import { createResource } from "frappe-ui";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

export const useNotifications = defineStore("notifications", () => {
	const isPanelOpen = ref(false);
	const assignments = ref([]);

	const assignmentsResource = createResource({
		url: "onerc_vmms.volunteer_and_member_management.api.projects.fetch_assigned_projects",
		auto: true,
		onSuccess(data) {
			assignments.value = data || [];
		},
	});

	const unreadCount = computed(() => assignments.value.length);
	const hasUnread = computed(() => unreadCount.value > 0);

	function togglePanel() {
		isPanelOpen.value = !isPanelOpen.value;
	}

	function closePanel() {
		isPanelOpen.value = false;
	}

	return {
		assignments,
		assignmentsResource,
		unreadCount,
		hasUnread,
		isPanelOpen,
		togglePanel,
		closePanel,
	};
});
