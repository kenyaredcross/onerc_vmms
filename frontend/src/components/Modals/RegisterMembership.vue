<template>
	<Dialog v-model="registerDialog">
		<template #body-title>
			<h3 class="text-3xl-bold text-ink-gray-8" id="modal-title">
				{{ props.is_renew ? "Renew" : "Register" }} as a Member
			</h3>
		</template>

		<template #body-content>
			<div :aria-busy="membershipEligibility.loading">
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
								<h4 class="text-lg-semibold text-yellow-800 mb-2">
									Profile Incomplete
								</h4>
								<p class="text-yellow-700 mb-3">
									To become a member, please complete your profile with all
									required information. This ensures we can properly process your
									membership application.
								</p>
								<div class="mb-2">
									<p class="text-base-semibold text-yellow-800">
										Missing Fields:
									</p>
									<ul class="list-disc list-inside text-yellow-700">
										<li
											v-for="field in membershipEligibility.data
												.missing_fields"
											:key="field"
										>
											{{
												__(field).charAt(0).toUpperCase() +
												__(field).slice(1)
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
					<div v-if="applicationSubmitted" class="py-4">
						<PaymentStatus
							title="Membership Application"
							message="Your application has been submitted for verification"
							returnUrl="/vmms/membership"
							urlName="Membership"
							@close="registerDialog = false"
						/>
					</div>
					<div v-else class="py-4">
						<form action="" @submit.prevent="submit">
							<div
								class="grid grid-cols-1 gap-4 mb-6 p-4 border rounded-2xl"
								:class="{ 'sm:grid-cols-2': !isExistingMember }"
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

								<div v-if="!isExistingMember" class="space-y-1">
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
							<div
								v-if="noPaymentMethods"
								class="mb-4 flex items-start gap-3 p-4 rounded-xl border border-outline-amber-2 bg-surface-amber-1"
								role="status"
							>
								<AlertTriangle
									class="w-5 h-5 text-ink-amber-3 shrink-0 mt-0.5"
									aria-hidden="true"
								/>
								<div>
									<p class="text-sm-medium text-ink-gray-8">
										{{ __("Online payment is unavailable") }}
									</p>
									<p class="mt-1 text-sm text-ink-gray-6">
										{{ paymentBlockedMessage }}
									</p>
								</div>
							</div>

							<div
								v-if="paymentLookupFailed"
								class="mb-4 flex items-start gap-3 p-4 rounded-xl border border-outline-red-2 bg-surface-red-1"
								role="alert"
							>
								<AlertTriangle
									class="w-5 h-5 text-ink-red-4 shrink-0 mt-0.5"
									aria-hidden="true"
								/>
								<div class="flex-1">
									<p class="text-sm-medium text-ink-gray-8">
										{{ __("Could not load payment methods") }}
									</p>
									<p class="mt-1 text-sm text-ink-gray-6">
										{{
											__(
												"We could not check which payment methods are available. Check your connection and try again."
											)
										}}
									</p>
									<Button
										type="button"
										variant="subtle"
										class="mt-3"
										:loading="paymentGateways.loading"
										@click="getPaymentGateways"
									>
										{{ __("Try again") }}
									</Button>
								</div>
							</div>

							<div v-if="!props.is_renew" class="mb-4 flex items-center gap-2">
								<input
									id="is_existing_member"
									type="checkbox"
									v-model="isExistingMember"
									class="h-4 w-4 rounded border-outline-gray-3 text-ink-red-6 focus:ring-outline-red-4"
								/>
								<label
									for="is_existing_member"
									class="text-sm-medium text-ink-gray-7"
								>
									{{ __("I am an existing member (Not registered on portal)") }}
								</label>
							</div>

							<FormControl
								v-if="!is_renew && !paymentUnavailable"
								type="autocomplete"
								label="Branch / County"
								placeholder="Select branch or county to register with"
								class="w-full mb-4"
								:options="branches.data"
								v-model="branch"
							/>

							<FormControl
								v-if="is_renew && !paymentUnavailable"
								type="text"
								label="Branch / County"
								placeholder="Select branch or county to register with"
								class="w-full mb-4"
								:value="props.renew_branch"
								v-model="branch"
								readonly
								required
							/>

							<div v-if="isExistingMember" class="space-y-2">
								<p class="text-sm-medium text-ink-gray-5">
									{{ __("Proof of Membership (Receipt / Certificate / Card)") }}
								</p>
								<FileUploader
									:fileTypes="['.jpg', '.jpeg', '.png', '.pdf']"
									:uploadArgs="{
										private: true,
										upload_endpoint: PROOF_UPLOAD_ENDPOINT,
									}"
									:validateFile="validateProofFile"
									@success="onProofUploaded"
								>
									<template
										v-slot="{
											file,
											uploading,
											progress,
											error,
											openFileSelector,
										}"
									>
										<div class="flex items-center gap-3">
											<Button
												type="button"
												variant="subtle"
												:loading="uploading"
												@click="openFileSelector"
											>
												{{
													uploading
														? `${__("Uploading")} ${progress}%`
														: membershipForm.proof_attachment
														? __("Replace File")
														: __("Upload File")
												}}
											</Button>
											<span
												v-if="
													membershipForm.proof_attachment && !uploading
												"
												class="text-sm text-ink-gray-6 truncate"
											>
												{{
													membershipForm.proof_attachment.file_name ||
													file?.name
												}}
											</span>
										</div>
										<ErrorMessage v-if="error" class="mt-2" :message="error" />
									</template>
								</FileUploader>
								<p class="text-xs text-ink-gray-5">
									{{
										__(
											"No payment is required. Your application will be reviewed and activated once your proof of membership is verified."
										)
									}}
								</p>
							</div>

							<div v-else>
								<ProgressSpinner
									v-if="validateBranchPGW.loading"
									:message="'Validating payment for branch selection...'"
								/>
								<ErrorMessage
									v-else-if="validateBranchPGW.error"
									:message="validateBranchPGW.error"
								/>
							</div>

							<div v-show="showPaymentOptions && !isExistingMember">
								<ProgressSpinner
									v-if="paymentGateways.loading"
									:message="'Fetching Payment Methods'"
								/>
								<ErrorMessage
									v-else-if="paymentGateways.error"
									:message="paymentGateways.error"
								/>
								<div v-else-if="paymentGateways.data?.length">
									<p class="mt-4 mb-2 text-sm-medium text-ink-gray-5">
										{{ __("Select a Payment Method:") }}
									</p>
									<ul class="space-y-2">
										<li
											v-for="pgw in paymentGateways.data"
											:key="pgw"
											@click="selectPaymentGateway(pgw)"
											class="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all duration-200"
											:class="
												membershipForm.payment_gateway === pgw
													? 'border-outline-red-4 bg-surface-red-1 text-ink-red-6 font-semibold'
													: 'border-outline-gray-2 bg-surface-base text-ink-gray-7 hover:border-outline-red-3 hover:bg-surface-red-1'
											"
										>
											<span
												class="w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors"
												:class="
													membershipForm.payment_gateway === pgw
														? 'border-outline-red-4'
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

							<div
								v-if="!paymentUnavailable"
								class="mt-4 gap-2 flex items-end justify-end"
							>
								<Button
									type="button"
									variant="solid"
									theme="red"
									:loading="createMembership.loading"
									class="rounded-lg px-6"
									@click="submit"
								>
									{{ isExistingMember ? __("Apply") : __("Proceed") }}
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
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Dialog,
	FileUploader,
	FormControl,
	Button,
	createResource,
	ErrorMessage,
	toast,
} from "frappe-ui";
import { computed, reactive, ref, toRaw, watch } from "vue";
import { AlertTriangle } from "lucide-vue-next";
import router from "../../router";
import { membershipStore } from "../../stores/membership";
import ProgressSpinner from "../Common/ProgressSpinner.vue";
import PaymentStatus from "../PaymentStatus.vue";

const PROOF_UPLOAD_ENDPOINT =
	"/api/method/onerc_vmms.volunteer_and_member_management.api.files.upload_file";

const registerDialog = defineModel();
const branch = ref("");
const close = defineEmits(["close"]);
const formError = ref("");
const validatedBranch = ref("");
const isExistingMember = ref(false);
const applicationSubmitted = ref(false);

const { currentMembership } = membershipStore();

const membershipForm = reactive({
	amount: 0,
	membership_type: "",
	branch: "",
	payment_gateway: "",
	is_existing_member: false,
	proof_attachment: null,
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

watch(
	() => [props.membership_type, props.amount],
	([membershipType, amount]) => {
		membershipForm.membership_type = membershipType;
		membershipForm.amount = amount;
	},
	{ immediate: true }
);

watch(
	() => [props.is_renew, props.renew_branch],
	([isRenew, renewBranch]) => {
		if (isRenew && renewBranch) {
			membershipForm.branch = renewBranch;
			branch.value = renewBranch;
		}
	},
	{ immediate: true }
);

function toBranchName(raw) {
	const selected = toRaw(raw);
	if (!selected) return "";
	if (typeof selected === "string") return selected;
	return selected.value || selected.name || selected.label || "";
}

watch(branch, (newValue) => {
	const branchName = toBranchName(newValue);

	if (membershipForm.branch === branchName) return;

	membershipForm.branch = branchName;
	clearErrors();
	checkBranchPaymentSupport();
});

watch(isExistingMember, (newValue) => {
	membershipForm.is_existing_member = newValue;
	clearErrors();

	if (newValue) {
		membershipForm.payment_gateway = "";
		validatedBranch.value = "";
		validateBranchPGW.error = null;
	} else {
		membershipForm.proof_attachment = null;
		checkBranchPaymentSupport();
	}
});

const showPaymentOptions = computed(
	() =>
		!isExistingMember.value &&
		!!membershipForm.branch &&
		validatedBranch.value === membershipForm.branch
);

function checkBranchPaymentSupport() {
	const target = membershipForm.branch;

	validatedBranch.value = "";
	membershipForm.payment_gateway = "";

	if (isExistingMember.value || !target) return;

	validateBranchPGW.submit(
		{ company: target },
		{
			onSuccess: () => {
				if (membershipForm.branch === target) validatedBranch.value = target;
			},
			onError: () => {
				if (membershipForm.branch === target) validatedBranch.value = "";
			},
		}
	);
}

function selectPaymentGateway(gateway) {
	membershipForm.payment_gateway = gateway;
	clearErrors();
}

function validateProofFile(file) {
	const extension = file.name.split(".").pop().toLowerCase();
	if (!["jpg", "jpeg", "png", "pdf"].includes(extension)) {
		return __("Only JPG, PNG or PDF files are allowed.");
	}
}

function onProofUploaded(file) {
	membershipForm.proof_attachment = file;
	formError.value = "";
	createMembership.error = "";
}

const validateBranchPGW = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.get_pgw_for_company",
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
	if (!validateForm()) return;

	createMembership.submit(
		{},
		{
			onSuccess(data) {
				if (isExistingMember.value) {
					toast.success(__("Application submitted successfully for verification."));
					applicationSubmitted.value = true;
					currentMembership.reload();
					return;
				}

				if (data) {
					toast.success(__("Redirecting you to the payment page..."));
					setTimeout(() => {
						window.location.href = data;
					}, 3000);
				}
			},
		}
	);
}

function clearErrors() {
	formError.value = "";
	createMembership.error = null;
	validateBranchPGW.error = null;
	paymentGateways.error = null;
}

function resetState() {
	branch.value = "";
	isExistingMember.value = false;
	applicationSubmitted.value = false;
	validatedBranch.value = "";

	membershipForm.branch = "";
	membershipForm.payment_gateway = "";
	membershipForm.is_existing_member = false;
	membershipForm.proof_attachment = null;

	validateBranchPGW.data = null;
	paymentGateways.data = null;
	clearErrors();
}

watch(registerDialog, (isOpen) => {
	resetState();

	if (!isOpen) return;

	if (props.is_renew && props.renew_branch) {
		membershipForm.branch = props.renew_branch;
		branch.value = props.renew_branch;
		checkBranchPaymentSupport();
	}

	membershipEligibility.fetch();
	getPaymentGateways();
});

function getPaymentGateways() {
	if (!props.membership_type) {
		toast.error("Membership type is required to fetch payment gateways.");
		return;
	}
	paymentGateways.submit(
		{},
		{
			onSuccess(gateways) {
				if (
					membershipForm.payment_gateway &&
					!(gateways || []).includes(membershipForm.payment_gateway)
				) {
					membershipForm.payment_gateway = "";
				}
			},
		}
	);
}

const paymentGateways = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.membership.get_membership_type_pgws",
	makeParams() {
		return { membership_type: props.membership_type };
	},
});

const noPaymentMethods = computed(() => {
	if (isExistingMember.value || paymentGateways.loading) return false;
	if (paymentGateways.error) return false;
	return Array.isArray(paymentGateways.data) && paymentGateways.data.length === 0;
});

const paymentLookupFailed = computed(
	() => !isExistingMember.value && !paymentGateways.loading && !!paymentGateways.error
);

const paymentUnavailable = computed(
	() => (noPaymentMethods.value || paymentLookupFailed.value) && !isExistingMember.value
);

const paymentBlockedMessage = computed(() =>
	props.is_renew
		? __(
				"Online payment is not set up for this membership type, so it cannot be renewed here yet. Please contact support to renew."
		  )
		: __(
				"Online payment is not set up for this membership type yet. If you are already a member, tick the box below and apply with your proof of membership instead. Otherwise please contact support."
		  )
);

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
		proof_attachment: "Proof of Membership",
	};

	const requiredFields = isExistingMember.value
		? ["membership_type", "branch", "proof_attachment"]
		: ["amount", "membership_type", "branch", "payment_gateway"];

	for (const key of requiredFields) {
		if (!membershipForm[key]) {
			formError.value = `${labels[key] ?? key} is required.`;
			return false;
		}
	}

	if (!isExistingMember.value) {
		const offered = paymentGateways.data || [];
		if (!offered.includes(membershipForm.payment_gateway)) {
			formError.value = __("Please choose one of the available payment methods.");
			return false;
		}
	}

	return true;
}
</script>
