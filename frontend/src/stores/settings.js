import { defineStore } from "pinia";
import { ref } from "vue";
import { sessionStore } from "./session";
import { createResource } from "frappe-ui";

export const useSettings = defineStore("settings", () => {
  const { isLoggedIn } = sessionStore();
  const isSettingsOpen = ref(false);
  const activeTab = ref(null);

  const sidebarSettings = createResource({
    url: "lms.lms.api.get_sidebar_settings",
    cache: "Sidebar Settings",
    auto: false,
  });

  return {
    isSettingsOpen,
    activeTab,
    isLoggedIn,
    sidebarSettings,
  };
});
