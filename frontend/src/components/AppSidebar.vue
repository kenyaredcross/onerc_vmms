<template>
  <div
    class="flex h-full flex-col justify-between transition-all duration-300 ease-in-out border-r bg-surface-menu-bar"
    :class="sidebarStore.sidebarCollapsed ? 'w-14' : 'w-56'"
  >
    <div
      class="flex flex-col overflow-hidden"
      :class="sidebarStore.sidebarCollapsed ? 'items-center' : ''"
    >
      <UserDropdown :isCollapsed="sidebarStore.sidebarCollapsed" />
      <div class="flex flex-col">
        <SidebarLink
          v-for="link in sidebarLinks"
          :link="link"
          :isCollapsed="sidebarStore.sidebarCollapsed"
          class="mx-2 my-0.5"
        />
      </div>
    </div>
    <div class="m-2 flex flex-col gap-1">
      <div
        v-if="readOnlyMode && !sidebarStore.sidebarCollapsed"
        class="z-10 m-2 bg-surface-modal py-2.5 px-3 text-xs text-ink-gray-7 leading-5 rounded-md"
      >
        {{
          __(
            "This site is being updated. You will not be able to make any changes. Full access will be restored shortly."
          )
        }}
      </div>

      <div
        class="flex items-center mt-4"
        :class="
          sidebarStore.sidebarCollapsed ? 'flex-col space-y-3' : 'flex-row'
        "
      >
        <div
          class="flex items-center flex-1"
          :class="
            sidebarStore.sidebarCollapsed
              ? 'flex-col space-y-3'
              : 'flex-row space-x-3'
          "
        >
          <Tooltip v-if="readOnlyMode && sidebarStore.sidebarCollapsed">
            <CircleAlert
              class="size-4 stroke-1.5 text-ink-gray-7 cursor-pointer"
            />
            <template #body>
              <div
                class="max-w-[30ch] rounded bg-surface-gray-7 px-2 py-1 text-center text-p-xs text-ink-white shadow-xl"
              >
                {{
                  __(
                    "This site is being updated. You will not be able to make any changes. Full access will be restored shortly."
                  )
                }}
              </div>
            </template>
          </Tooltip>
          <Tooltip :text="__('Powered by VMMS Portal')">
            <Zap
              class="size-4 stroke-1.5 text-ink-gray-7 cursor-pointer"
              @click="redirectToWebsite()"
            />
          </Tooltip>
        </div>
        <Tooltip
          :text="sidebarStore.sidebarCollapsed ? __('Expand') : __('Collapse')"
        >
          <CollapseSidebar
            class="size-4 text-ink-gray-7 duration-300 stroke-1.5 ease-in-out cursor-pointer"
            :class="{
              '[transform:rotateY(180deg)]': sidebarStore.sidebarCollapsed,
            }"
            @click="toggleSidebar()"
          />
        </Tooltip>
      </div>
    </div>
  </div>
</template>

<script setup>
import UserDropdown from "@/components/UserDropdown.vue";
import CollapseSidebar from "@/components/Icons/CollapseSidebar.vue";
import SidebarLink from "@/components/SidebarLink.vue";
import { ref, onMounted, inject, onUnmounted } from "vue";
import { getSidebarLinks } from "@/utils";
import { useSidebar } from "@/stores/sidebar";
import { Tooltip } from "frappe-ui";
import { CircleAlert, Zap } from "lucide-vue-next";

let sidebarStore = useSidebar();
const sidebarLinks = ref(getSidebarLinks());
const readOnlyMode = window.read_only_mode;

const toggleSidebar = () => {
  sidebarStore.sidebarCollapsed = !sidebarStore.sidebarCollapsed;
  localStorage.setItem(
    "sidebarCollapsed",
    JSON.stringify(sidebarStore.sidebarCollapsed)
  );
};

const redirectToWebsite = () => {
  window.open(
    "https://github.com/navariltd/non_profit/tree/ft/volunteer-member-portal",
    "_blank"
  );
};
</script>
