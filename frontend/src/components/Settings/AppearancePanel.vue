<template>
	<SettingsHeader :title="__('Appearance')" class="!px-4 !pt-6 sm:!px-[4.4rem] sm:!pt-10" />
	<PanelBody>
		<ThemeSwitcher
			:label="__('Theme')"
			:description="__('Switch between light, dark, or system theme')"
			:name="brandName"
			:logo="logo"
			:theme-labels="{
				light: __('Light'),
				dark: __('Dark'),
				system: __('System'),
			}"
		/>
	</PanelBody>
</template>

<script setup>
import VMMSLogo from "@/components/Icons/VMMSLogo.vue";
import { sessionStore } from "@/stores/session";
import { SettingsHeader, ThemeSwitcher } from "frappe-ui";
import { computed, markRaw } from "vue";
import PanelBody from "./PanelBody.vue";

const { branding } = sessionStore();

const brandName = computed(() => {
	const name = branding.data?.brand_name;
	return name && branding.data?.app_name !== "Frappe" ? name : __("VMMS Portal");
});

const logo = computed(() => branding.data?.logo || markRaw(VMMSLogo));
</script>
