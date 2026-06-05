<template>
	<NoPermission v-if="!isLoggedIn" :page="__('Profile')" />
	<div
		v-else
		class="container mx-auto px-4 md:px-8 py-4 md:py-8 min-h-screen bg-surface-gray-50"
	>
		<ProfileHeader :allow-edit="true" :form="form" class="mb-6 md:mb-10" />

		<div v-if="loading" class="text-center py-20 bg-surface-white rounded-xl shadow-lg">
			<div class="flex flex-col items-center justify-center">
				<svg
					class="animate-spin h-8 w-8 text-red-600 mb-3"
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
				>
					<circle
						class="opacity-25"
						cx="12"
						cy="12"
						r="10"
						stroke="currentColor"
						stroke-width="4"
					></circle>
					<path
						class="opacity-75"
						fill="currentColor"
						d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
					></path>
				</svg>
				<p class="text-ink-gray-1-600 font-medium">{{ __("Loading user details...") }}</p>
			</div>
		</div>

		<div v-else class="bg-surface-white shadow-xl rounded-xl p-4 sm:p-6 lg:p-8">
			<div class="flex justify-between items-center mb-6">
				<h2 class="text-2xl font-bold text-ink-gray-1-900 dark:text-ink-gray-5">
					{{ __("Edit Profile") }}
				</h2>

				<router-link
					:to="{ name: 'ProfileOverview' }"
					class="flex items-center gap-2 px-5 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-semibold shadow-md"
				>
					<Grid class="w-5 h-5" />
					{{ __("Profile Overview") }}
				</router-link>
			</div>

			<div>
				<div
					class="flex overflow-x-auto border-b border-outline-gray-2 whitespace-nowrap mb-6 -mx-4 sm:mx-0 px-4 sm:px-0"
				>
					<button
						v-for="(tab, i) in tabs"
						:key="i"
						@click="goToTab(i)"
						:class="[
							'py-3 px-3 sm:px-5 text-sm sm:text-base font-semibold transition-all duration-200 ease-in-out flex-shrink-0',
							currentTab === i
								? 'border-b-4 border-red-600 text-red-700 bg-red-50/50'
								: 'text-ink-gray-8 hover:text-red-500 hover:border-b-4 hover:border-red-100',
						]"
					>
						{{ __(tab.title) }}
					</button>
				</div>

				<div class="min-h-[400px] py-4">
					<component
						:is="tabs[currentTab].component"
						:form="form"
						@saved="handleSaved"
					/>
				</div>
			</div>
		</div>

		<ErrorModal v-model="showErrorDialog" :errors="flatErrors" />
	</div>
</template>

<script setup>
import { useHead } from "@vueuse/head";
import { createResource, toast } from "frappe-ui";
import { Grid } from "lucide-vue-next";
import { onMounted, reactive, ref } from "vue";

import ErrorModal from "@/components/Modals/ErrorModal.vue";
import CitizenshipDocuments from "@/components/Profile/CitizenshipDocuments.vue";
import HealthDisabilities from "@/components/Profile/HealthDisabilities.vue";
import PersonalInfo from "@/components/Profile/PersonalInfo.vue";
import ProfileHeader from "@/components/Profile/ProfileHeader.vue";
import QualificationsSkills from "@/components/Profile/QualificationsSkills.vue";
import NoPermission from "../components/NoPermission.vue";
import { sessionStore } from "../stores/session";

const loading = ref(true);
const showErrorDialog = ref(false);
const currentTab = ref(0);
const flatErrors = ref("");
const userId = ref(null);
const { isLoggedIn, user } = sessionStore();

const tabs = [
	{ title: "Personal Info", component: PersonalInfo },
	{ title: "Health & Disabilities", component: HealthDisabilities },
	{ title: "Qualifications & Skills", component: QualificationsSkills },
	{ title: "Documents", component: CitizenshipDocuments },
];

const form = reactive({});

function populateForm(data) {
	Object.keys(data).forEach((key) => {
		form[key] = data[key] !== null ? data[key] : "";
	});
}

const userDetailsResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.get_user_details",
	onSuccess(data) {
		if (data) {
			populateForm(data);
			userId.value = data.name || user;
		}
		loading.value = false;
	},
	onError(err) {
		toast.error(err.message || "Failed to fetch user details");
		loading.value = false;
	},
});

function handleSaved(updatedData) {
	Object.assign(form, updatedData);
	toast.success("Profile updated successfully");
}

function updateTabFromHash() {
	if (typeof window !== "undefined") {
		const hash = window.location.hash.substring(1);
		const index = parseInt(hash.replace("tab-", ""), 10);
		if (!isNaN(index) && index >= 0 && index < tabs.length) {
			currentTab.value = index;
		} else {
			currentTab.value = 0;
			updateHash(0);
		}
	}
}

function updateHash(index) {
	if (typeof window !== "undefined") {
		window.location.hash = `tab-${index}`;
	}
}

function goToTab(i) {
	currentTab.value = i;
	updateHash(i);
}

onMounted(() => {
	updateTabFromHash();
	if (!isLoggedIn) return;
	userDetailsResource.fetch();
	if (typeof window !== "undefined") {
		window.addEventListener("hashchange", updateTabFromHash);
	}
});

useHead({
	title: "Edit Profile | Kenya Red Cross VMMS",
	meta: [
		{
			name: "description",
			content:
				"Manage your personal information, health details, qualifications, skills, and important documents within the Kenya Red Cross VMMS.",
		},
	],
});
</script>
