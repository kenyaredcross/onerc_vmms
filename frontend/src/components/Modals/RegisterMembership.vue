<template>
	<Dialog v-model="registerDialog">
		<template #body-title>
			<h3 class="text-2xl font-bold text-ink-gray-8" id="modal-title">
				{{ props.is_renew ? "Renew" : "Register" }} as a Member
			</h3>
		</template>

		<template #body-content>
			<ProgressSpinner
				v-if="membershipEligibility.loading"
				:message="'Processing membership validity'"
			/>
			<ErrorMessage
				v-else-if="membershipEligibility.error"
				:message="membershipEligibility.error"
			/>
			<div v-else-if="!membershipEligibility.data.eligible">
				<div class="p-6 rounded-lg shadow-sm">
					<div class="flex items-start space-x-3">
						<div class="flex-shrink-0">
							<AlertTriangle class="w-6 h-6 text-yellow-600" />
						</div>
						<div>
							<h4 class="text-lg font-semibold text-yellow-800 mb-2">
								Profile Incomplete
							</h4>
							<p class="text-yellow-700 mb-3">
								To become a member, please complete your profile with all required
								information. This ensures we can properly process your membership
								application.
							</p>
							<div class="mb-2">
								<p class="text-base font-semibold text-yellow-800">
									Missing Fields:
								</p>
								<ul class="list-disc list-inside text-yellow-700">
									<li
										v-for="field in membershipEligibility.data.missing_fields"
										:key="field"
									>
										{{
											__(field).charAt(0).toUpperCase() + __(field).slice(1)
										}}
									</li>
								</ul>
							</div>
							<Button
								variant="solid"
								theme="red"
								@click="router.push({ name: 'Profile' })"
							>
								Complete Profile
							</Button>
						</div>
					</div>
				</div>
			</div>
			<div v-else>
				<div class="py-4">
					<form action="" @submit.prevent="submit">
						<div
							class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6 p-4 bg-surface-red-4 border border-outline-red-1 rounded-2xl shadow-sm"
						>
							<div class="space-y-1">
								<FormControl
									type="text"
									label="Membership Type"
									placeholder="Select membership type"
									class="w-full text-sm text-ink-gray-8"
									v-model="membershipForm.membership_type"
									:value="props.membership_type"
									readonly
								/>
							</div>

							<div class="space-y-1">
								<FormControl
									type="number"
									label="Amount"
									placeholder="Enter amount"
									class="w-full text-sm"
									v-model="membershipForm.amount"
									:value="props.amount"
									readonly
								/>
							</div>
						</div>

						<FormControl
							v-if="!is_renew"
							type="autocomplete"
							label="Branch / County"
							placeholder="Select branch or county to register with"
							class="w-full mb-4"
							:options="branches.data"
							v-model="branch"
						/>

						<FormControl
							v-if="is_renew"
							type="text"
							label="Branch / County"
							placeholder="Select branch or county to register with"
							class="w-full mb-4"
							:value="props.renew_branch"
							v-model="branch"
							readonly
							required
						/>

						<div>
							<ProgressSpinner
								v-if="validateBranchPGW.loading"
								:message="'Validating payment for branch selection...'"
							/>
							<ErrorMessage
								v-else-if="validateBranchPGW.error"
								:message="validateBranchPGW.error"
							/>
						</div>

						<div v-show="showPaymentOptions">
							<ProgressSpinner
								v-if="paymentGateways.loading"
								:message="'Fetching Payment Methods'"
							/>
							<ErrorMessage
								v-else-if="paymentGateways.error"
								:message="paymentGateways.error"
							/>
							<div v-else-if="paymentGateways.data">
								<p class="mt-4 mb-2 text-sm font-medium text-ink-gray-5">
									{{ __("Select a Payment Method:") }}
								</p>
								<ul class="space-y-2">
									<li
										v-for="pgw in paymentGateways.data"
										:key="pgw"
										@click="membershipForm.payment_gateway = pgw"
										class="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all duration-200"
										:class="
											membershipForm.payment_gateway === pgw
												? 'border-outline-red-3 bg-surface-red-1 text-ink-red-3 font-semibold'
												: 'border-outline-gray-2 bg-surface-white text-ink-gray-7 hover:border-outline-red-2 hover:bg-surface-red-1'
										"
									>
										<span
											class="w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors"
											:class="
												membershipForm.payment_gateway === pgw
													? 'border-outline-red-3'
													: 'border-outline-gray-3'
											"
										>
											<span
												v-if="membershipForm.payment_gateway === pgw"
												class="w-2 h-2 rounded-full bg-surface-red-4"
											></span>
										</span>
										{{ __(pgw) }}
									</li>
								</ul>
							</div>
						</div>

						<div class="mt-4 gap-2 flex items-end justify-end">
							<Button
								type="button"
								variant="solid"
								theme="red"
								:loading="createMembership.loading"
								class="rounded-lg px-6"
								@click="submit"
							>
								Proceed
							</Button>
						</div>
						<ErrorMessage v-if="formError" class="mt-2" :message="formError" />
						<ErrorMessage
							v-else-if="createMembership.error"
							class="mt-2"
							:message="createMembership.error"
						/>
					</form>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Dialog,
	FormControl,
	Button,
	createResource,
	ErrorMessage,
	toast,
	Toast,
} from "frappe-ui";
import { reactive, ref, toRaw, watch, watchEffect } from "vue";
import { AlertTriangle } from "lucide-vue-next";
import router from "../../router";
import ProgressSpinner from "../Common/ProgressSpinner.vue";

const registerDialog = defineModel();
const branch = ref("");
const close = defineEmits(["close"]);
const formError = ref("");
const showPaymentOptions = ref(false);

const membershipForm = reactive({
	amount: 0,
	membership_type: "",
	branch: "",
	payment_gateway: "",
});

const props = defineProps({
	membership_type: String,
	amount: Number,
	renew_branch: String,
	is_renew: {
		type: Boolean,
		default: false,
	},
});

watchEffect(() => {
	membershipForm.membership_type = props.membership_type;
	membershipForm.amount = props.amount;
	membershipForm.branch = props.renew_branch || "";
});

watch(branch, (newValue) => {
	const selectedBranch = toRaw(newValue);

	if (selectedBranch) {
		validateBranchPGW.submit(
			{ company: selectedBranch.value },
			{
				onSuccess: () => {
					showPaymentOptions.value = true;
				},
				onError: () => {
					showPaymentOptions.value = false;
				},
			},
		);
		membershipForm.branch = selectedBranch.value;
	} else {
		membershipForm.branch = "";
	}
});

const validateBranchPGW = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.get_pgw_for_company",
});

const branches = createResource({
	url: "onerc_vmms.volunteer_and_member_management.utils.get_companies",
	auto: true,
	cache: "branches",
	transform: (data) => data.map((item) => ({ label: item.name, value: item.name })),
});

const createMembership = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.initiate_membership_registration",
	makeParams() {
		return { ...membershipForm };
	},
});

function submit() {
	if (!props.is_renew && !branch.value) {
		return;
	}

	if (!validateForm()) return;

	createMembership.submit(
		{},
		{
			onSuccess: (data) => {
				if (data) {
					toast.success("Redirecting you to the payment page...");
					setTimeout(() => {
						window.location.href = data;
					}, 3000);
				}
			},
		},
	);
}

watch(registerDialog, (isOpen) => {
	if (!isOpen) {
		branch.value = "";
		formError.value = "";
		props.is_renew = false;
	} else {
		membershipEligibility.fetch();
		getPaymentGateways();
		createMembership.error = "";
		formError.value = "";
	}
});

function getPaymentGateways() {
	if (!props.membership_type) {
		toast.error("Membership type is required to fetch payment gateways.");
		return;
	}
	paymentGateways.submit(
		{},
		{
			onError(error) {
				console.error("Failed to fetch payment gateways:", error);
			},
		},
	);
}

const paymentGateways = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.get_membership_type_pgws",
	makeParams() {
		return { membership_type: props.membership_type };
	},
});

const membershipEligibility = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.validate_membership_eligibility",
	cache: "membership_eligibility",
});

function validateForm() {
	formError.value = "";
	const labels = {
		amount: "Amount",
		membership_type: "Membership Type",
		branch: "Branch / County",
		payment_gateway: "Payment Method",
	};
	for (const [key, value] of Object.entries(membershipForm)) {
		if (!value) {
			formError.value = `${labels[key] ?? key} is required.`;
			return false;
		}
	}
	formError.value = "";
	return true;
}
</script>
