import { defineStore } from "pinia";
import { ref } from "vue";

export const useSidebar = defineStore("sidebar", () => {
  const sidebarCollapsed = ref(false);
  const webpagesCollapsed = ref(true);

  if (localStorage.getItem("sidebarCollapsed")) {
    sidebarCollapsed.value = JSON.parse(
      localStorage.getItem("sidebarCollapsed")
    );
  }

  if (localStorage.getItem("webpagesCollapsed")) {
    webpagesCollapsed.value = JSON.parse(
      localStorage.getItem("webpagesCollapsed")
    );
  }

  return {
    sidebarCollapsed,
    webpagesCollapsed,
  };
});
