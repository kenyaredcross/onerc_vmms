import { defineStore } from "pinia";
import { ref } from "vue";
import { sessionStore } from "./session";

export const useSettings = defineStore("settings", () => {
	const { isLoggedIn } = sessionStore();
	const isSettingsOpen = ref(false);
	const activeTab = ref(null);

	return {
		isSettingsOpen,
		activeTab,
		isLoggedIn,
	};
});
