<template>
  <div class="flex h-full flex-col gap-2 relative">
    <div class="h-full pb-10 mb-5" id="scrollContainer">
      <slot />
    </div>

    <div class="relative z-20">
      <div
        class="fixed bottom-16 right-2 w-[80%] rounded-md bg-surface-white text-base p-5 space-y-4 shadow-md"
        v-if="showMenu"
        ref="menu"
      >
        <div
          v-for="link in otherLinks"
          :key="link.label"
          class="flex items-center space-x-2 cursor-pointer hover:underline"
          @click="handleClick(link)"
        >
          <component
            :is="icons[link.icon]"
            class="h-4 w-4 stroke-1.5 text-red-600"
          />
          <component
            v-if="link.logo"
            :is="`img`"
            :src="link.logo"
            class="h-4 w-4 object-contain"
          />
          <div class="">{{ link.label }}</div>
        </div>
      </div>

      <div
        v-if="sidebarSettings.data"
        class="fixed bottom-0 left-0 w-full flex items-center justify-between border-t border-outline-gray-2 bg-surface-white standalone:pb-4 z-10"
      >
        <button
          v-for="tab in sidebarLinks.filter(
            (link) => link.label !== 'Learning'
          )"
          :key="tab.label"
          :class="isVisible(tab) ? 'block' : 'hidden'"
          class="flex-1 flex flex-col items-center justify-center py-4 transition active:scale-95"
          @click="handleClick(tab)"
        >
          <component
            :is="icons[tab.icon]"
            class="h-6 w-6 stroke-1.5"
            :class="[isActive(tab) ? 'text-ink-red-4' : 'text-ink-gray-5']"
          />
          <span class="text-xs">{{ tab.label }}</span>
        </button>

        <button
          @click="toggleMenu"
          class="py-4 px-3 flex flex-col items-center justify-center"
        >
          <component
            :is="icons['List']"
            class="h-6 w-6 stroke-1.5 text-ink-gray-5"
          />
          <span class="text-xs">More</span>
        </button>
      </div>
    </div>
  </div>
</template>
<script setup>
import { getSidebarLinks } from "@/utils";
import { useRouter } from "vue-router";
import { watch, ref, onMounted, toRaw } from "vue";
import { sessionStore } from "@/stores/session";
import { useSettings } from "@/stores/settings";
import { usersStore } from "@/stores/user";
import * as icons from "lucide-vue-next";
import { createResource, Spinner } from "frappe-ui";

const { logout, user } = sessionStore();
let { isLoggedIn } = sessionStore();
const { sidebarSettings } = useSettings();
const router = useRouter();
let { userResource } = usersStore();
const sidebarLinks = ref(getSidebarLinks());
const otherLinks = ref([]);
const showMenu = ref(false);
const menu = ref(null);

onMounted(() => {
  sidebarSettings.reload(
    {},
    {
      onSuccess(data) {
        filterLinksToShow(data);
        addOtherLinks();
      },
    }
  );
});

const handleOutsideClick = (e) => {
  if (menu.value && !menu.value.contains(e.target)) {
    showMenu.value = false;
  }
};

watch(showMenu, (val) => {
  if (val) {
    setTimeout(() => {
      document.addEventListener("click", handleOutsideClick);
    }, 0);
  } else {
    document.removeEventListener("click", handleOutsideClick);
  }
});

const filterLinksToShow = (data) => {
  Object.keys(data).forEach((key) => {
    if (!parseInt(data[key])) {
      sidebarLinks.value = sidebarLinks.value.filter(
        (link) => link.label.toLowerCase().split(" ").join("_") !== key
      );
    }
  });
};

const addOtherLinks = () => {
  if (user) {
    apps.data.forEach((app) => {
      if (app.name === "non_profit") return;
      otherLinks.value.push({
        label: app.title,
        logo: app.logo,
        to: app.route,
      });
    });
    otherLinks.value.push({
      label: "Log out",
      icon: "LogOut",
    });
  } else {
    otherLinks.value.push({
      label: "Log in",
      icon: "LogIn",
    });
  }
};

const apps = createResource({
  url: "frappe.apps.get_apps",
  cache: "apps",
  auto: true,
  transform: (data) => {
    let _apps = [
      {
        name: "frappe",
        logo: "/assets/lms/images/desk.png",
        title: __("Desk"),
        route: "/app",
      },
    ];
    data.map((app) => {
      if (app.name === "non_profit") return;
      _apps.push({
        name: app.name,
        logo: app.logo,
        title: __(app.title),
        route: app.route,
      });
    });
    return _apps;
  },
});

let isActive = (tab) => {
  return tab.activeFor?.includes(router.currentRoute.value.name);
};

const handleClick = (tabLink) => {
  let tab = toRaw(tabLink);

  if (tab.label === "Log in") {
    window.location.href = "/login";
  } else if (tab.label === "Log out") {
    logout.submit().then(() => {
      isLoggedIn = false;
    });
  } else if (tab.logo) {
    window.location.href = tab.to;
  } else if (tab.to) {
    router.push({ name: tab.to });
  }
};

const isVisible = (tab) => {
  if (tab.label == "Log in") return !isLoggedIn;
  else if (tab.label == "Log out") return isLoggedIn;
  else return true;
};

const toggleMenu = () => {
  showMenu.value = !showMenu.value;
};
</script>
