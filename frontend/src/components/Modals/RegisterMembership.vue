<template>
	<Dialog v-model="registerDialog">
		<template #body-title>
			<h3 class="text-2xl font-bold text-gray-900" id="modal-title">
				{{ props.is_renew ? "Renew" : "Register" }} as a
				<span class="text-red-600">Member</span>
			</h3>
		</template>

		<template #body-content>
			<div v-if="!paymentStatus" class="py-4">
				<form action="" @submit.prevent="submit">
					<div
						class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6 p-4 bg-red-200 border border-red-100 rounded-2xl shadow-sm"
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
					/>

					<FormControl
						type="text"
						label="Phone Number (MPesa Phone Number to be used for payment)"
						placeholder="eg. 0712345678"
						class="w-full"
						v-model="membershipForm.phone"
					/>

					<ErrorMessage
						v-if="createMembership.error"
						class="text-center border rounded-md p-2 border-red-500 bg-red-50 text-sm my-3"
						:message="createMembership.error"
					/>
					<div class="mt-4 gap-2 flex items-end justify-end">
						<Button
							v-if="!confirmPayment"
							type="submit"
							variant="solid"
							theme="green"
							:loading="createMembership.loading"
							class="rounded-lg px-6"
						>
							{{ props.is_renew ? "Renew" : "Register" }}
						</Button>
					</div>
				</form>
				<div class="flex items-end justify-end">
					<Button
						v-if="confirmPayment"
						variant="solid"
						theme="red"
						class="rounded-lg px-6"
						@click="checkPayment"
						:loading="confirmPaymentStatus.loading"
					>
						Confirm Payment
					</Button>
				</div>
			</div>

			<PaymentStatus v-if="paymentStatus" @close="registerDialog = false" />
		</template>
	</Dialog>
</template>
<script setup>
import { Dialog, FormControl, Button, createResource, ErrorMessage, toast } from "frappe-ui";
import { reactive, ref, toRaw, watch, watchEffect } from "vue";
import { isValidPhone } from "../../utils/volunteer";
import { membershipStore } from "../../stores/membership";
import PaymentStatus from "../PaymentStatus.vue";

const registerDialog = defineModel();
const branch = ref("");
const close = defineEmits(["close"]);
const confirmPayment = ref(false);
const invoice = ref("");
const paymentStatus = ref(false);

const membershipForm = reactive({
	phone: "",
	amount: 0,
	membership_type: "",
	branch: "",
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
});

const branches = createResource({
	url: "onerc_vmms.volunteer_and_member_management.utils.get_companies",
	auto: true,
	cache: "branches",
	transform: (data) => data.map((item) => ({ label: item.name, value: item.name })),
});

const createMembership = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.create_membership",
	makeParams() {
		return { ...membershipForm };
	},
});

function submit() {
	if ((!props.is_renew && !branch.value) || !membershipForm.phone) {
		createMembership.error = "Please fill in all required fields before submitting.";
		return;
	}
	if (!isValidPhone(membershipForm.phone)) {
		createMembership.error = "Please enter a valid phone number.";
		return;
	}

	createMembership.error = "";
	createMembership.submit(
		{},
		{
			onSuccess(data) {
				toast.success(
					"Payment initiated Successfully! You will receive a payment prompt shortly on your phone.",
				);
				currentMembership.reload();
				createMembership.error = "";
				invoice.value = data;
				confirmPayment.value = true;
			},
			onError(error) {},
		},
	);
}

watch(registerDialog, (isOpen) => {
	if (!isOpen) {
		branch.value = "";
		membershipForm.phone = "";
		createMembership.error = "";
		confirmPayment.value = false;
		paymentStatus.value = false;
		invoice.value = "";
		props.is_renew = false;
	}
});

const confirmPaymentStatus = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.confirm_payment",
	makeParams() {
		return {
			invoice_name: invoice.value,
		};
	},
});

const checkPayment = () => {
	if (!invoice.value) {
		toast.error("Error confirming payment. Please try again.");

		return;
	}

	confirmPaymentStatus.submit(
		{},
		{
			onSuccess(data) {
				data === "paid"
					? handlePaymentStatus()
					: toast.info(
							"Payment confirmation pending. Please click 'Confirm Payment' again to verify your transaction status.",
						);
			},
			onError(error) {
				toast.error("Error confirming payment. Please try again.");
			},
		},
	);
};

const handlePaymentStatus = () => {
	toast.success("Payment confirmed! Thank you for your membership.");
	currentMembership.reload();
	confirmPayment.value = false;
	paymentStatus.value = true;
};
</script>
