<template>
	<SettingsDialog v-model="settings.isSettingsOpen" v-model:tab="settings.activeTab">
		<SettingsSidebar>
			<SettingsNavGroup :label="__('Account')">
				<SettingsNavItem
					v-for="tab in tabs"
					:key="tab.value"
					:value="tab.value"
					class="data-[state=active]:!bg-surface-red-2 data-[state=active]:!text-ink-red-8 data-[state=active]:!shadow-none"
				>
					<template #prefix>
						<span
							:class="[
								tab.icon,
								'size-4 shrink-0',
								settings.activeTab === tab.value
									? 'text-ink-red-7'
									: 'text-ink-gray-6',
							]"
						/>
					</template>
					{{ __(tab.label) }}
				</SettingsNavItem>
			</SettingsNavGroup>
		</SettingsSidebar>

		<SettingsContent>
			<SettingsPanel v-for="tab in tabs" :key="tab.value" :value="tab.value">
				<component :is="tab.component" />
			</SettingsPanel>
		</SettingsContent>
	</SettingsDialog>
</template>

<script setup>
import { useSettings } from "@/stores/settings";
import { usersStore } from "@/stores/user";
import {
	SettingsContent,
	SettingsDialog,
	SettingsNavGroup,
	SettingsNavItem,
	SettingsPanel,
	SettingsSidebar,
} from "frappe-ui";
import { computed, markRaw } from "vue";
import AppearancePanel from "./AppearancePanel.vue";
import AvailabilityPanel from "./AvailabilityPanel.vue";
import ProfilePanel from "./ProfilePanel.vue";

const settings = useSettings();
const userStore = usersStore();

const tabs = computed(() =>
	[
		{
			label: "Profile",
			value: "profile",
			icon: "lucide-user",
			component: markRaw(ProfilePanel),
		},
		userStore.isVolunteer && {
			label: "Availability",
			value: "availability",
			icon: "lucide-calendar-clock",
			component: markRaw(AvailabilityPanel),
		},
		{
			label: "Appearance",
			value: "appearance",
			icon: "lucide-sun-moon",
			component: markRaw(AppearancePanel),
		},
	].filter(Boolean)
);
</script>
