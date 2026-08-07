<template>
	<SettingsHeader :title="__('Profile')" class="!px-4 !pt-6 sm:!px-[4.4rem] sm:!pt-10 mb-2" />
	<PanelBody>
		<div class="flex flex-col gap-6">
			<div class="flex items-center gap-3 rounded-lg border p-3">
				<Avatar
					size="2xl"
					:label="userResource.data?.full_name"
					:image="userResource.data?.user_image"
				/>
				<div class="min-w-0">
					<div class="text-base-medium text-ink-gray-9 truncate">
						{{ convertToTitleCase(userResource.data?.full_name || "") }}
					</div>
					<div class="text-sm text-ink-gray-6 truncate">
						{{ userResource.data?.email }}
					</div>
				</div>
			</div>

			<div class="divide-y divide-outline-gray-1">
				<SettingsRow
					:title="__('Edit Profile')"
					:description="__('Update your personal details, skills, and documents.')"
				>
					<Button variant="outline" theme="red" @click="go('Profile')">
						{{ __("Open") }}
					</Button>
				</SettingsRow>
				<SettingsRow
					:title="__('Profile Overview')"
					:description="__('See how your profile appears to coordinators.')"
				>
					<Button variant="outline" theme="red" @click="go('ProfileOverview')">
						{{ __("Open") }}
					</Button>
				</SettingsRow>
			</div>
		</div>
	</PanelBody>
</template>

<script setup>
import { useSettings } from "@/stores/settings";
import { usersStore } from "@/stores/user";
import { convertToTitleCase } from "@/utils";
import { Avatar, Button, SettingsHeader, SettingsRow } from "frappe-ui";
import { useRouter } from "vue-router";
import PanelBody from "./PanelBody.vue";

const router = useRouter();
const { userResource } = usersStore();
const settings = useSettings();

function go(name) {
	settings.closeSettings();
	router.push({ name });
}
</script>
