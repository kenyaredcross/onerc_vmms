<template>
	<Dialog v-model="registerDialog">
		<template #body-title>
			<h3 class="text-2xl font-bold text-gray-900" id="modal-title">
				{{ props.is_renew ? "Renew" : "Register" }} as a
				<span class="text-red-600">Member</span>
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
				<div
					class="p-6 bg-gradient-to-r from-yellow-50 to-orange-50 border border-yellow-200 rounded-lg shadow-sm"
				>
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
				<div v-if="!paymentStatus && !applicationSubmitted" class="py-4">
					<form action="" @submit.prevent="submit">
						<div
							class="grid grid-cols-1 gap-4 mb-4 p-4 bg-red-200 border border-red-100 rounded-2xl shadow-sm"
							:class="{ 'sm:grid-cols-2': !isExistingMember || props.is_renew }"
						>
							<div class="space-y-1">
								<FormControl
									type="text"
									label="Membership Type"
									placeholder="Select membership type"
									class="w-full text-sm"
									v-model="membershipForm.membership_type"
									:value="props.membership_type"
									readonly
								/>
							</div>

							<div v-if="!isExistingMember || props.is_renew" class="space-y-1">
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

						<div v-if="!props.is_renew" class="mb-4 flex items-center gap-2">
							<input
								id="is_existing_member"
								type="checkbox"
								v-model="isExistingMember"
								class="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
							/>
							<label
								for="is_existing_member"
								class="text-sm font-medium text-gray-700"
							>
								I am an existing member (Not registered on portal)
							</label>
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
						/>

						<div v-if="isExistingMember && !props.is_renew" class="space-y-1 mb-4">
							<Uploader
								label="Proof of Membership (Receipt / Certificate / Card)"
								:fileTypes="['.jpg', '.jpeg', '.png', '.pdf']"
								:onSuccess="(data) => (membershipForm.proof_attachment = data)"
							/>
						</div>

						<div v-else class="space-y-4">
							<div>
								<FormControl
									type="text"
									label="Phone Number (MPesa Phone Number to be used for payment)"
									placeholder="eg. 0712345678"
									class="w-full"
									v-model="membershipForm.phone"
									required
								/>
								<PaymentInfoAlert class="mt-2" v-if="checkSTK" />
							</div>
						</div>

						<ErrorMessage
							v-if="createMembership.error"
							class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm my-3"
							:message="createMembership.error"
						/>
						<div class="mt-4 gap-2 flex items-end justify-end">
							<Button
								type="submit"
								variant="solid"
								theme="green"
								:loading="createMembership.loading || confirmPayment"
								class="rounded-lg px-6"
							>
								{{
									props.is_renew
										? "Renew"
										: isExistingMember
										? "Apply"
										: confirmPayment
										? "Processing Payment...."
										: "Register"
								}}
							</Button>
						</div>
					</form>
				</div>

				<PaymentStatus
					v-else
					@close="registerDialog = false"
					:message="
						isExistingMember
							? 'Membership application submitted successfully for verification'
							: 'Membership processed successfully'
					"
					title="Membership"
					returnUrl="/vmms/membership"
					urlName="Membership"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, createResource, Dialog, ErrorMessage, FormControl, toast } from "frappe-ui";
import { AlertTriangle } from "lucide-vue-next";
import { reactive, ref, toRaw, watch, watchEffect } from "vue";
import router from "../../router";
import { membershipStore } from "../../stores/membership";
import { paymentListener } from "../../utils/payment";
import { isValidPhone } from "../../utils/volunteer";
import ProgressSpinner from "../Common/ProgressSpinner.vue";
import PaymentInfoAlert from "../PaymentInfoAlert.vue";
import PaymentStatus from "../PaymentStatus.vue";

const registerDialog = defineModel();
const branch = ref("");
const close = defineEmits(["close"]);
const confirmPayment = ref(false);
const invoice = ref("");
const paymentStatus = ref(false);
const applicationSubmitted = ref(false);
const checkSTK = ref(false);
const isExistingMember = ref(false);

const membershipForm = reactive({
	phone: "",
	amount: 0,
	membership_type: "",
	branch: "",
	is_existing_member: false,
	proof_attachment: null,
});

const { currentMembership } = membershipStore();

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
		membershipForm.branch = selectedBranch.value;
	} else {
		membershipForm.branch = "";
	}
	if (createMembership.error && membershipForm.branch) {
		createMembership.error = "";
	}
});

watch(isExistingMember, (newValue) => {
	membershipForm.is_existing_member = newValue;
	createMembership.error = "";

	if (newValue) {
		membershipForm.phone = "";
		checkSTK.value = false;
	} else {
		membershipForm.proof_attachment = null;
		if (userDetails.data) {
			membershipForm.phone = userDetails.data.mobile_no || "";
		}
	}
});

const branches = createResource({
	url: "onerc_vmms.volunteer_and_member_management.utils.utils.get_companies",
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
	if (!props.is_renew && !membershipForm.branch) {
		createMembership.error = "Please select a branch or county.";
		return;
	}

	if (isExistingMember.value && !props.is_renew) {
		if (
			!membershipForm.proof_attachment ||
			(Array.isArray(membershipForm.proof_attachment) &&
				membershipForm.proof_attachment.length === 0)
		) {
			createMembership.error = "Please upload a proof of membership.";
			return;
		}
	} else {
		if (!membershipForm.phone) {
			createMembership.error = "Please enter your phone number.";
			return;
		}
		if (!isValidPhone(membershipForm.phone)) {
			createMembership.error = "Please enter a valid phone number.";
			return;
		}
	}

	createMembership.error = "";

	createMembership.submit(
		{},
		{
			onSuccess(data) {
				if (isExistingMember.value && !props.is_renew) {
					toast.success("Application submitted successfully for verification.");
					applicationSubmitted.value = true;
					paymentStatus.value = true;
					currentMembership.reload();
				} else {
					checkSTK.value = true;
					toast.success(
						"Payment initiated Successfully! You will receive a payment prompt shortly on your phone."
					);
					createMembership.error = "";
					confirmPayment.value = true;
					initiatePaymentListener(data);
				}
			},
		}
	);
}

function initiatePaymentListener(data) {
	paymentListener.saveToken(data);
	paymentListener.listenForPayment().then((status) => {
		if (status === "Completed") {
			handlePaymentStatus();
		} else {
			checkSTK.value = false;
			toast.error("Payment failed or was cancelled. Please try again.");
		}

		confirmPayment.value = false;
	});
}

watch(registerDialog, (isOpen) => {
	if (!isOpen) {
		branch.value = "";
		membershipForm.branch = "";
		membershipForm.phone = "";
		membershipForm.is_existing_member = false;
		membershipForm.proof_attachment = null;
		isExistingMember.value = false;
		createMembership.error = "";
		confirmPayment.value = false;
		paymentStatus.value = false;
		applicationSubmitted.value = false;
		invoice.value = "";
		props.is_renew = false;
		checkSTK.value = false;
	} else {
		membershipEligibility.fetch();
		userDetails.fetch();
	}
});

const handlePaymentStatus = () => {
	toast.success("Payment confirmed! Thank you for your membership.");
	currentMembership.reload();
	paymentStatus.value = true;
};

const membershipEligibility = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.validate_membership_eligibility",
	cache: "membership_eligibility",
});

const userDetails = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.get_user_details",
	cache: "user_details",
	onSuccess(data) {
		if (!isExistingMember.value) {
			membershipForm.phone = data.mobile_no || "";
		}
	},
});
</script>
