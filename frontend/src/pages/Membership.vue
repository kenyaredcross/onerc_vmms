<template>
	<NoPermission v-if="user?.data == 'Guest'" :page="__('Membership')" />
	<div class="space-y-4 mx-auto px-4" v-if="user?.data && user?.data !== 'Guest'">
		<ErrorMessage
			v-if="currentMembership.error || membershipTypes.error"
			class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm my-auto mt-20"
			:message="__('Failed to get Membership Details')"
		/>

		<div v-else-if="currentMembership.data" class="w-full flex flex-col items-center">
			<Member
				v-if="currentMembership.data.length > 0"
				:membershipStatus="currentMembership.data"
			/>
			<EmptyState v-else :type="__('Membership')" class="mt-6" />
		</div>

		<div
			v-if="currentMembership.data"
			class="p-2 pt-2 md:p-8 bg-gray-50 rounded-2xl shadow-md text-center mb-20 max-w-7xl mx-auto"
		>
			<h1 class="text-lg md:text-3xl text-gray-900">{{ __("Select a New Plan") }}</h1>

			<div v-if="membershipTypes.data?.length > 0" class="mt-10">
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
					<div
						v-for="membershipType in membershipTypes.data"
						:key="membershipType.name"
						class="flex justify-center"
					>
						<VmmsPortalCard
							class="w-full max-w-sm transition hover:scale-105 hover:shadow-lg cursor-pointer"
							:membershipType="membershipType"
							@click="selectMembershipType(membershipType)"
						/>
					</div>
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
import { inject, reactive, ref, watch } from "vue";
import EmptyState from "../components/EmptyState.vue";
import Member from "../components/MemberPlan.vue";
import RegisterMembership from "../components/Modals/RegisterMembership.vue";
import NoPermission from "../components/NoPermission.vue";
import VmmsPortalCard from "../components/VmmsPortalCard.vue";
import { membershipStore } from "../stores/membership";
import { isValidPhone } from "../utils/volunteer";

const { membershipTypes, currentMembership } = membershipStore();
const user = inject("$user");
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
	payNow.value = false;
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

function payMembership() {
	if (!membershipForm.phone_number) {
		createMembership.error = "Please enter your phone number";
		return;
	}

	if (!isValidPhone(membershipForm.phone_number)) {
		createMembership.error = "Please enter a valid Kenyan phone number.eg. (+254123456789)";
		return;
	}
	createMembership.error = "";

	const membershipId = currentMembership.data?.[0]?.name;

	if (membershipId) {
		renewMembership.submit({
			membership: membershipId,
			phone_number: membershipForm.phone_number,
		});
	} else {
		toast.info("Payment can only be initiated after a membership document has been created.");
	}
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
