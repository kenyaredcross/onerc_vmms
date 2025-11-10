<template>
	<div class="">
		<h1 class="text-3xl font-bold text-center text-red-700 py-3">
			{{ __("Volunteer Signup") }}
		</h1>
	</div>

	<div v-if="!isLoggedIn" class="text-center py-20">
		<LogIn class="w-16 h-16 text-gray-400 mx-auto mb-4" />
		<h2 class="text-3xl font-bold text-gray-900 mb-4">{{ __("Login Required") }}</h2>
		<p class="text-gray-600 mb-8">
			{{ __("Please log in to submit your volunteer application.") }}
		</p>
		<Button
			variant="solid"
			class="bg-red-600 hover:bg-red-700 text-white"
			@click="redirectToLogin"
		>
			<template #prefix>
				<LogIn class="w-4 h-4" />
			</template>
			{{ __("Login to Continue") }}
		</Button>
	</div>

	<div v-else-if="alreadyApplied && applicationStatus !== 'Draft'" class="text-center py-10">
		<PendingApproval />
	</div>

	<div
		v-else-if="!alreadyApplied || (alreadyApplied && applicationStatus === 'Draft')"
		class="min-h-screen flex flex-col"
	>
		<main class="flex-1 container mx-auto px-4 py-4">
			<div class="bg-white shadow-lg rounded p-6">
				<div class="w-full mb-10">
					<div
						v-if="alreadyApplied && applicationStatus === 'Draft'"
						class="text-center mb-6"
					>
						<h2 class="text-xl font-semibold text-orange-600">
							{{ __("Continue Your Draft Application") }}
						</h2>
						<p class="text-gray-600 text-sm">
							{{ __("Complete and submit your volunteer application") }}
						</p>
					</div>

					<div class="flex items-center justify-between relative">
						<div
							v-for="(step, i) in steps"
							:key="i"
							class="flex-1 flex flex-col items-center text-center relative group cursor-pointer"
						>
							<div
								v-if="i < steps.length"
								class="absolute top-6 w-full h-1 -translate-y-1/2"
								:class="i < currentStep ? 'bg-red-600' : 'bg-gray-300'"
							></div>

							<div
								class="relative flex items-center justify-center w-12 h-12 rounded-full border-2 transition-all duration-300 ease-in-out"
								:class="[
									i < currentStep
										? 'bg-red-600 border-red-600 text-white shadow-md hover:shadow-lg'
										: i === currentStep
											? 'bg-white border-red-600 text-red-600 font-bold shadow-lg scale-110 ring-4 ring-red-100'
											: 'bg-gray-200 border-gray-300 text-gray-500 hover:border-gray-400 hover:bg-gray-300',
								]"
							>
								<span class="text-lg">{{ i + 1 }}</span>
							</div>
						</div>
					</div>
				</div>

				<section v-if="currentStep === 0">
					<StepOrganization
						v-model="form"
						:errors="errors"
						@update:errors="handleErrorsUpdate"
						@change="trackChanges"
					/>
				</section>
				<section v-if="currentStep === 1">
					<StepAdditional
						v-model="form"
						:errors="errors"
						@update:errors="handleErrorsUpdate"
						@change="trackChanges"
					/>
				</section>
				<section v-if="currentStep === 2">
					<StepDocuments
						v-model="form"
						:documents="documents"
						:errors="errors"
						@change="trackChanges"
					/>
				</section>
				<section v-if="currentStep === 3">
					<ReviewApplication :form="form" />
				</section>

				<div class="flex justify-between items-center gap-4 mt-10">
					<div>
						<span v-if="hasUnsavedChanges" class="text-sm text-orange-600 font-medium">
						</span>
					</div>
					<div class="flex gap-4">
						<Button v-if="currentStep > 0" @click="prevStep">
							{{ __("Back") }}
						</Button>
						<Button
							v-if="currentStep < steps.length - 1"
							@click="nextStep"
							variant="solid"
							:loading="saveInProgress"
						>
							{{ __("Save & Continue") }}
						</Button>
						<Button
							v-if="currentStep === steps.length - 1"
							class="bg-red-700 text-white"
							variant="solid"
							:loading="saveInProgress"
							@click="showSubmitDialog = true"
						>
							{{ __("Submit Application") }}
						</Button>
					</div>
				</div>
			</div>
		</main>
	</div>

	<Dialog v-model="showSubmitDialog">
		<template #body-title>
			<h2 class="text-lg font-bold text-gray-900">
				{{ __("Confirm Submission") }}
			</h2>
		</template>

		<template #body-content>
			<p class="text-gray-700 leading-relaxed">
				{{ __("Are you sure you want to submit this application?") }}
			</p>
			<p class="mt-2 text-sm text-red-600 font-medium">
				{{ __("You won't be able to make further edits after submission.") }}
			</p>
		</template>

		<template #actions>
			<div class="flex flex-col gap-3 sm:flex-row sm:justify-end">
				<Button
					variant="outline"
					class="w-full sm:w-auto py-3"
					@click="showSubmitDialog = false"
				>
					{{ __("Cancel") }}
				</Button>
				<Button
					variant="solid"
					class="w-full sm:w-auto bg-red-700 hover:bg-red-800 text-white py-3"
					:loading="submitInProgress"
					:disabled="submitInProgress"
					@click="confirmSubmit"
				>
					<template #prefix>
						<FeatherIcon name="check-circle" class="w-4" />
					</template>
					{{ submitInProgress ? __("Submitting...") : __("Submit") }}
				</Button>
			</div>
		</template>
	</Dialog>

	<ErrorModal v-model="showErrorDialog" :errors="flatErrors" />
</template>

<script setup>
import PendingApproval from "@/components/PendingApproval.vue";
import StepAdditional from "@/components/Signup/StepAdditional.vue";
import StepDocuments from "@/components/Signup/StepDocuments.vue";
import StepOrganization from "@/components/Signup/StepOrganization.vue";
import { useHead } from "@vueuse/head";
import { Button, createResource, Dialog, toast } from "frappe-ui";
import { FeatherIcon, LogIn } from "lucide-vue-next";
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import ErrorModal from "../components/Modals/ErrorModal.vue";
import ReviewApplication from "../components/Signup/ReviewApplication.vue";
import { sessionStore } from "../stores/session";
import { usersStore } from "../stores/user";

const FIELD_MAP = {
	date_of_birth: "birth_date",
	mpesa_mobile_phone: "mobile_no",
	surname: "last_name",
	other_names: "middle_name",
	phone_number: "phone",
};

const NORMAL_FIELDS = [
	"ward",
	"first_name",
	"identification_type",
	"id_number",
	"passport_number",
	"number_of_dependants",
	"marital_status",
	"blood_group",
	"citizenship",
	"country_of_citizenship",
	"administrative_location",
	"sub_county",
	"county",
	"access_to_internet",
	"profession",
	"reason_to_join_krcs",
	"gender",
	"email_id",
];

const TABLE_FIELDS = [
	"languages",
	"education",
	"disabilities",
	"driving_licence",
	"courses",
	"licences",
	"additional_skills",
	"allergies",
	"work_references",
	"work_experience",
	"supporting_documents",
];

const { userResource } = usersStore();
const { isLoggedIn } = sessionStore();
const user = userResource;
const router = useRouter();
const submitInProgress = ref(false);

const currentStep = ref(0);
const steps = [
	{ title: "Organization & Personal Info" },
	{ title: "Additional Info" },
	{ title: "Documents" },
	{ title: "Review & Submit" },
];

const applicationId = ref(null);
const alreadyApplied = ref(false);
const applicationStatus = ref(null);
const documents = ref([]);
const saveInProgress = ref(false);
const showSubmitDialog = ref(false);
const showErrorDialog = ref(false);
const loading = ref(true);

const originalFormData = ref({});
const hasUnsavedChanges = ref(false);
const changedFields = ref(new Set());
const flatErrors = ref("");

const form = reactive({
	email_id: "",
	phone_number: "",
	company: "",
	mpesa_mobile_phone: "",
	date_of_birth: "",
	id_number: "",
	passport_number: "",
	administrative_location: "",
	sub_county: "",
	citizenship: "",
	country_of_citizenship: "",
	marital_status: "",
	education: "",
	profession: "",
	allergies: [],
	access_to_internet: "",
	identification_type: "",
	number_of_dependants: null,
	reason_to_join_krcs: "",
	disabilities: "",
	has_insurance: "",
	languages: [],
	driving_licence: [],
	licences: [],
	blood_group: "",
	courses: [],
	supporting_documents: [],
	courses: [],
	additional_skills: "",
	county: "",
	ward: "",
	gender: "",
	consent_to_use_of_bio_data: false,
	profile_photo: null,
	_current_step: 0,
	_current_progress: 0,
});

const errors = reactive({});

const stepFields = {
	0: [
		"email_id",
		"phone_number",
		"company",
		"ward",
		"date_of_birth",
		"id_number",
		"passport_number",
		"mpesa_mobile_phone",
		"number_of_dependants",
		"marital_status",
		"blood_group",
		"has_insurance",
		"citizenship",
		"country_of_citizenship",
		"identification_type",
		"administrative_location",
		"sub_county",
		"county",
		"gender",
		"consent_to_use_of_bio_data",
	],
	1: [
		"access_to_internet",
		"profession",
		"allergies",
		"languages",
		"education",
		"disabilities",
		"reason_to_join_krcs",
		"driving_licence",
		"courses",
		"licences",
		"additional_skills",
	],
	2: ["profile_photo", "supporting_documents"],
};

const progressPercentage = computed(() => {
	const totalSteps = steps.length;
	const baseProgress = (currentStep.value / totalSteps) * 100;

	const currentStepFields = stepFields[currentStep.value] || [];
	let filledFields = 0;

	currentStepFields.forEach((field) => {
		const value = form[field];
		if (value && (Array.isArray(value) ? value.length > 0 : value !== "")) {
			filledFields++;
		}
	});

	const currentStepProgress =
		currentStepFields.length > 0
			? (filledFields / currentStepFields.length) * (100 / totalSteps)
			: 0;

	return Math.min(baseProgress + currentStepProgress, 100);
});

function trackChanges(field) {
	const currentValue = JSON.stringify(form[field]);
	const originalValue = JSON.stringify(originalFormData.value[field]);

	if (currentValue !== originalValue) {
		changedFields.value.add(field);
		hasUnsavedChanges.value = true;
	} else {
		changedFields.value.delete(field);
		hasUnsavedChanges.value = changedFields.value.size > 0;
	}
}

watch(
	form,
	() => {
		Object.keys(form).forEach((key) => {
			if (!key.startsWith("_")) {
				trackChanges(key);
			}
		});
	},
	{ deep: true },
);

function populateFormFromUser(userData) {
	const allFields = [...new Set([...NORMAL_FIELDS, ...Object.keys(FIELD_MAP)])];
	TABLE_FIELDS.forEach((tableField) => {
		const userValue = userData[tableField];
		if (Array.isArray(userValue) && userValue.length > 0) {
			form[tableField] = JSON.parse(JSON.stringify(userValue));
		}
	});

	allFields.forEach((formField) => {
		const userField = FIELD_MAP[formField] || formField;
		let userValue = userData[userField];

		if (formField === "email_id" && user.data?.email) {
			userValue = user.data.email;
		} else if (formField === "phone_number" && user.data?.phone) {
			userValue = user.data.phone;
		}

		const formValue = form[formField];
		const formIsEmpty =
			formValue === null ||
			formValue === undefined ||
			formValue === "" ||
			(Array.isArray(formValue) && formValue.length === 0);

		const userValueExists =
			userValue !== null &&
			userValue !== undefined &&
			userValue !== "" &&
			(!Array.isArray(userValue) || userValue.length > 0);

		if (formIsEmpty && userValueExists) {
			if (form[formField] !== userValue) {
				form[formField] = userValue;
			}
		}
	});

	updateOriginalData();
	hasUnsavedChanges.value = false;
	changedFields.value.clear();
}

const userDetailsResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.get_user_details",
	onSuccess(data) {
		if (data) populateFormFromUser(data);
		loading.value = false;
	},
	onError(err) {
		toast.error(err.message || "Failed to fetch user details");
		loading.value = false;
	},
});

function getCurrentStepData(onlyChanges = false) {
	const currentStepData = {};
	const currentStepFieldList = stepFields[currentStep.value] || [];

	currentStepFieldList.forEach((field) => {
		if (onlyChanges && !changedFields.value.has(field)) {
			return;
		}

		if (field === "documents") {
			currentStepData.documents = documents.value;
		} else {
			currentStepData[field] = form[field];
		}
	});

	if (form.company) {
		currentStepData.county = form.company;
	}

	currentStepData.is_volunteer = true;
	currentStepData._current_step = currentStep.value;
	currentStepData._current_progress = Math.round(progressPercentage.value);

	if (user.data?.email) {
		currentStepData.email_id = user.data.email;
	}
	if (user.data?.phone) {
		currentStepData.phone_number = user.data.phone;
	}

	return currentStepData;
}

const jobApplication = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.doc.search_doctype",
	makeParams() {
		return {
			doctype: "Job Applicant",
			filters: {
				email_id: user.data?.email,
				is_volunteer: true,
			},
			first: true,
		};
	},
	auto: true,
	reloadOn: () => !!user.data?.email,
	onSuccess(data) {
		if (data?.name) {
			const application = data;

			alreadyApplied.value = true;
			applicationStatus.value = application.docstatus == 0 ? "Draft" : application.name;
			applicationId.value = application.name;

			if (applicationStatus.value === "Draft") {
				populateForm(application);
			}
		} else {
			form.email_id = user.data?.email || "";
		}

		// Fetch user details to fill missing fields
		userDetailsResource.submit();
	},
});

const submitApplicationResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.submit_job_application",
	makeParams() {
		return {
			id: applicationId.value,
		};
	},
});

const confirmSubmit = async () => {
	submitInProgress.value = true;
	submitApplicationResource.submit(
		{},
		{
			onSuccess: () => {
				// toast.success("Application submitted successfully");
				showSubmitDialog.value = false;
				alreadyApplied.value = true;
				hasUnsavedChanges.value = false;
				changedFields.value.clear();
				submitInProgress.value = false;
				window.location.reload();
			},
			onError: (err) => {
				submitInProgress.value = false;
				toast.error(err.messages?.[0] || "Submission failed");
			},
		},
	);
};

const createApplication = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.create_job_application",
	makeParams() {
		return getCurrentStepData(false);
	},
	onSuccess(data) {
		applicationId.value = data.name;
		toast.success("Application saved successfully");
		saveInProgress.value = false;

		updateOriginalData();
		hasUnsavedChanges.value = false;
		changedFields.value.clear();
	},
	onError(error) {
		console.error("Create application error:", error);
		toast.error("Failed to save application");
		saveInProgress.value = false;
	},
});

const updateApplication = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.update_job_application",
	makeParams() {
		const stepData = getCurrentStepData(true);
		return {
			id: applicationId.value,
			...stepData,
		};
	},
	onSuccess(data) {
		toast.success("Application updated successfully");
		saveInProgress.value = false;

		updateOriginalData();
		hasUnsavedChanges.value = false;
		changedFields.value.clear();
	},
	onError(error) {
		console.error("Update application error:", error);
		toast.error("Failed to update application");
		saveInProgress.value = false;
	},
});

function populateForm(data) {
	Object.keys(form).forEach((key) => {
		if (data[key] !== undefined && data[key] !== null) {
			form[key] = data[key];
		}
	});

	if (data.languages && Array.isArray(data.languages)) {
		form.languages = data.languages;
	}
	if (data.driving_licence && Array.isArray(data.driving_licence)) {
		form.driving_licence = data.driving_licence;
	}
	if (data.licences && Array.isArray(data.licences)) {
		form.licences = data.licences;
	}
	if (data.courses && Array.isArray(data.courses)) {
		form.courses = data.courses;
	}
	if (data.allergies && Array.isArray(data.allergies)) {
		form.allergies = data.allergies;
	}
	if (data.disabilities && Array.isArray(data.disabilities)) {
		form.disabilities = data.disabilities;
	}
	if (data.supporting_documents && Array.isArray(data.supporting_documents)) {
		form.supporting_documents = data.supporting_documents;
	}
	if (data.education) {
		form.education = data.education;
	}
	if (data.additional_skills) {
		form.additional_skills = data.additional_skills;
	}
	if (data.work_references) {
		form.work_references = data.work_references;
	}
	if (data.work_experience) {
		form.work_experience = data.work_experience;
	}

	if (data.documents && Array.isArray(data.documents)) {
		documents.value = data.documents;
	}

	updateOriginalData();
}

function updateOriginalData() {
	originalFormData.value = JSON.parse(JSON.stringify(form));
}

function redirectToLogin() {
	router.push("/login");
}

function handleErrorsUpdate(newErrors = {}) {
	Object.keys(errors).forEach((k) => delete errors[k]);

	Object.entries(newErrors || {}).forEach(([k, v]) => {
		let normalized;

		if (v instanceof Map) {
			normalized = Object.fromEntries(v);
		} else if (typeof v === "object" && v !== null) {
			normalized = JSON.parse(JSON.stringify(v));
		} else {
			normalized = v;
		}

		if (normalized && (typeof normalized !== "object" || Object.keys(normalized).length > 0)) {
			errors[k] = normalized;
		}
	});
}

function validateStep(stepIndex) {
	let valid = true;

	if (flatErrors.value) {
		return false;
	}

	return valid;
}

async function saveApplication() {
	if (!hasUnsavedChanges.value && applicationId.value) {
		return;
	}

	saveInProgress.value = true;

	try {
		if (!applicationId.value) {
			await createApplication.submit();
		} else {
			await updateApplication.submit();
		}
	} catch (error) {
		saveInProgress.value = false;
	}
}

function updateHash(step) {
	window.location.hash = `step-${step + 1}`;
}

function readHashAndNavigate() {
	const hash = window.location.hash.slice(1);
	const match = hash.match(/step-(\d+)/);

	if (match) {
		const step = parseInt(match[1]) - 1;
		if (step >= 0 && step < steps.length) {
			currentStep.value = step;
		}
	}
}

function goToStep(stepIndex) {
	if (stepIndex === currentStep.value) return;

	if (stepIndex < currentStep.value) {
		currentStep.value = stepIndex;
		updateHash(stepIndex);
		return;
	}

	if (!validateStep(currentStep.value)) {
		showErrorDialog.value = true;
		return;
	}

	let canProceed = true;
	for (let i = currentStep.value; i < stepIndex; i++) {
		if (!validateStep(i)) {
			canProceed = false;
			showErrorDialog.value = true;
			break;
		}
	}

	if (canProceed) {
		currentStep.value = stepIndex;
		updateHash(stepIndex);
	}
}

async function nextStep() {
	if (!validateStep(currentStep.value)) {
		showErrorDialog.value = true;
		return;
	}

	await saveApplication();

	if (!saveInProgress.value && currentStep.value < steps.length - 1) {
		currentStep.value++;
		updateHash(currentStep.value);
	}
}

function prevStep() {
	if (currentStep.value > 0) {
		currentStep.value--;
		updateHash(currentStep.value);
	}
}

function handleHashChange() {
	readHashAndNavigate();
}

onMounted(() => {
	readHashAndNavigate();
	window.addEventListener("hashchange", handleHashChange);
	updateOriginalData();
});

onUnmounted(() => {
	window.removeEventListener("hashchange", handleHashChange);
});

watch(currentStep, (newStep) => {
	form._current_step = newStep;
	form._current_progress = Math.round(progressPercentage.value);
});
watch(
	[errors, currentStep],
	([newErrors, newStep]) => {
		const stepErrors = newErrors[newStep] || {};

		flatErrors.value = Object.keys(stepErrors).length > 0 ? stepErrors : null;
	},
	{ deep: true, immediate: true },
);

useHead({
	title: "Volunteer Signup | Kenya Red Cross",
	meta: [
		{
			name: "description",
			content:
				"Join the Kenya Red Cross as a volunteer and make a difference in your community. Sign up to contribute your skills, time, and compassion.",
		},
	],
});
</script>
