<template>
	<NoPermission v-if="!isLoggedIn" :page="__('Membership')" />
	<div v-else class="space-y-4 mx-auto px-4">
		<ErrorMessage
			v-if="currentMembership.error || membershipTypes.error"
			class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm my-auto mt-20"
			:message="__('Failed to get Membership Details')"
		/>

		<div v-else-if="currentMembership.data" class="w-full flex flex-col items-center md:mt-10">
			<Member
				v-if="currentMembership.data.length > 0"
				:membershipStatus="currentMembership.data"
			/>
		</div>

		<div
			v-if="currentMembership.data"
			class="p-2 pt-2 md:p-8 bg-gray-50 rounded-2xl shadow-md text-center mb-20 max-w-7xl mx-auto"
		>
			<h1
				class="flex flex-col md:flex-row justify-center items-center gap-2 text-xl md:text-3xl font-semibold text-red-600"
			>
				<span>{{ __("Select a New Plan") }}</span>
				<span v-if="!currentMembership.data.length">
					{{ __("to become a member") }}
				</span>
			</h1>

			<div v-if="membershipTypes.data?.length" class="mt-10">
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
					<VmmsPortalCard
						v-for="membershipType in membershipTypes.data"
						class="w-full max-w-sm transition hover:shadow-lg cursor-pointer"
						:membershipType="membershipType"
						@click="selectMembershipType(membershipType)"
					/>
				</div>
			</div>

			<EmptyState v-else :type="__('Membership Type')" class="mt-10" />
		</div>
	</div>

	<RegisterMembership
		v-model="registerDialog"
		:membership_type="membershipForm.membership_type"
		:amount="membershipForm.amount"
		@close="cleanUpMembershipForm"
	/>
</template>

<script setup>
import { useHead } from "@vueuse/head";
import { createResource, ErrorMessage, toast } from "frappe-ui";
import { reactive, ref, watch } from "vue";
import EmptyState from "../components/EmptyState.vue";
import Member from "../components/MemberPlan.vue";
import RegisterMembership from "../components/Modals/RegisterMembership.vue";
import NoPermission from "../components/NoPermission.vue";
import VmmsPortalCard from "../components/VmmsPortalCard.vue";
import { membershipStore } from "../stores/membership";
import { sessionStore } from "../stores/session";

const { membershipTypes, currentMembership } = membershipStore();
const { isLoggedIn } = sessionStore();
const membershipId = ref("");

const registerDialog = ref(false);
const payNow = ref(false);
const membershipForm = reactive({
	membership_type: "",
	amount: 0,
});

const renewMembership = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.renew_membership",
	makeParams() {
		return {
			id: membershipId.value,
			phone_number: membershipForm.phone_number,
		};
	},
	onSuccess() {
		toast.success("Membership payment initiated successfully! Check your phone for a prompt.");
	},
	onError(error) {
		toast.error(error.message || "Failed to initiate membership payment.");
	},
});

function cleanUpMembershipForm() {
	registerDialog.value = false;
	membershipForm.membership_type = "";
	membershipForm.amount = 0;
}

function selectMembershipType(membershipType) {
	membershipForm.membership_type = membershipType.membership_type;
	membershipForm.amount = membershipType.amount;
	registerDialog.value = true;
}

function submit() {
	if (!membershipForm.branch) {
		createMembership.error = "Please select a branch";
		return;
	}
	createMembership.submit({ ...membershipForm });
}

watch(registerDialog, (newValue) => {
	if (newValue === false) {
		cleanUpMembershipForm();
	}
});

useHead({
	title: "Manage Membership | Kenya Red Cross VMMS",
	meta: [
		{
			name: "description",
			content:
				"View your current Kenya Red Cross membership status, renew your existing plan, or select a new membership type to join the organization.",
		},
	],
});
</script>
