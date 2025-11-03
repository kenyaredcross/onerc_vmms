<template>
	<Dropdown class="p-2" :options="userDropdownOptions">
		<template v-slot="{ open }">
			<button
				class="flex h-12 py-2 items-center rounded-md duration-300 ease-in-out"
				:class="
					isCollapsed
						? 'px-0 w-auto'
						: open
							? 'bg-surface-white shadow-sm px-2 w-52'
							: 'hover:bg-surface-gray-3 px-2 w-52'
				"
			>
				<img
					v-if="branding.data?.banner_image"
					:src="branding.data?.banner_image.file_url"
					class="w-8 h-8 rounded flex-shrink-0"
				/>
				<VMMSLogo v-else class="w-8 h-8 rounded flex-shrink-0" />
				<div
					class="flex flex-1 flex-col text-left duration-300 ease-in-out"
					:class="
						isCollapsed
							? 'opacity-0 ml-0 w-0 overflow-hidden'
							: 'opacity-100 ml-2 w-auto'
					"
				>
					<div class="text-base font-medium text-ink-gray-9 leading-none">
						<span
							v-if="branding.data?.app_name && branding.data?.app_name != 'Frappe'"
						>
							{{ branding.data?.app_name }}
						</span>
						<span v-else> {{ "VMMS Portal" }} </span>
					</div>
					<div
						v-if="userResource.data"
						class="mt-1 text-sm text-ink-gray-7 leading-none"
					>
						{{ convertToTitleCase(userResource.data?.full_name) }}
					</div>
				</div>
				<div
					class="duration-300 ease-in-out"
					:class="
						isCollapsed
							? 'opacity-0 ml-0 w-0 overflow-hidden'
							: 'opacity-100 ml-2 w-auto'
					"
				>
					<ChevronDown class="h-4 w-4 text-ink-gray-7" />
				</div>
			</button>
		</template>
	</Dropdown>
</template>

<script setup>
import Apps from "@/components/Apps.vue";
import FrappeCloudIcon from "@/components/Icons/FrappeCloudIcon.vue";
import VMMSLogo from "@/components/Icons/VMMSLogo.vue";
import { sessionStore } from "@/stores/session";
import { usersStore } from "@/stores/user";
import { convertToTitleCase } from "@/utils";
import { createDialog } from "@/utils/dialogs";
import { Dropdown } from "frappe-ui";
import { ChevronDown, LogIn, LogOut, User } from "lucide-vue-next";
import { computed, markRaw, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const { logout, branding } = sessionStore();
let { userResource } = usersStore();
let { isLoggedIn } = sessionStore();
const frappeCloudBaseEndpoint = "https://frappecloud.com";
const $dialog = createDialog;

const props = defineProps({
	isCollapsed: {
		type: Boolean,
		default: false,
	},
});

const userDropdownOptions = computed(() => {
	return [
		{
			group: "",
			items: [
				{
					icon: User,
					label: "My Profile",
					onClick: () => {
						router.push(`/user/profile`);
					},
					condition: () => {
						return isLoggedIn;
					},
				},
				{
					component: markRaw(Apps),
					condition: () => {
						let cookies = new URLSearchParams(document.cookie.split("; ").join("&"));
						let system_user = cookies.get("system_user");
						if (system_user === "yes") return true;
						else return false;
					},
				},
				{
					icon: FrappeCloudIcon,
					label: "Login to Frappe Cloud",
					onClick: () => {
						$dialog({
							title: __("Login to Frappe Cloud?"),
							message: __(
								"Are you sure you want to login to your Frappe Cloud dashboard?",
							),
							actions: [
								{
									label: __("Confirm"),
									variant: "solid",
									onClick(close) {
										loginToFrappeCloud();
										close();
									},
								},
							],
						});
					},
					condition: () => {
						return (
							userResource.data?.is_system_manager && userResource.data?.is_fc_site
						);
					},
				},
				{
					icon: LogOut,
					label: "Log out",
					onClick: () => {
						logout.submit().then(() => {
							isLoggedIn = false;
						});
					},
					condition: () => {
						return isLoggedIn;
					},
				},
				{
					icon: LogIn,
					label: "Log in",
					onClick: () => {
						window.location.href = "/login";
					},
					condition: () => {
						return !isLoggedIn;
					},
				},
			],
		},
	];
});

const loginToFrappeCloud = () => {
	let redirect_to = "/dashboard/sites/" + userResource.data.sitename;
	window.open(`${frappeCloudBaseEndpoint}${redirect_to}`, "_blank");
};
</script>
