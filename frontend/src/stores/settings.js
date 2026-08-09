import { defineStore } from "pinia";
import { ref } from "vue";
import { sessionStore } from "./session";

export const useSettings = defineStore("settings", () => {
	const { isLoggedIn } = sessionStore();
	const isSettingsOpen = ref(false);
	const activeTab = ref("profile");

	function openSettings(tab = "profile") {
		activeTab.value = tab;
		isSettingsOpen.value = true;
	}

	function closeSettings() {
		isSettingsOpen.value = false;
	}

	return {
		isSettingsOpen,
		activeTab,
		isLoggedIn,
		openSettings,
		closeSettings,
	};
});
