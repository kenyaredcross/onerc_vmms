<template>
	<div class="max-w-5xl mx-auto py-10 space-y-8">
		<div
			v-if="job.data"
			class="p-6 rounded-xl shadow-sm border border-gray-200 bg-gradient-to-r from-red-50 to-white"
		>
			<div class="flex items-start gap-4">
				<div>
					<img
						v-if="job.data.company_logo"
						:src="job.data.company_logo"
						class="w-16 h-16 rounded-lg object-contain cursor-pointer bg-gray-50 border"
						:alt="__(job.data.company)"
						@click="redirectToWebsite(job.data.company_website)"
					/>
					<div
						v-else
						class="w-16 h-16 flex items-center justify-center rounded-lg bg-red-100 text-red-700 font-semibold text-xl cursor-default"
					>
						{{ __(getCompanyAbbr(job.data.company)) }}
					</div>
				</div>
				<div>
					<h1 class="text-3xl font-bold text-gray-900 mb-1">
						{{ __(job.data.job_title) }}
					</h1>
					<div class="text-lg font-medium text-red-600">
						{{ __(job.data.company) }}
					</div>
					<div
						v-if="job.data.location || job.data.country"
						class="text-sm text-gray-500 mt-1"
					>
						{{ __(job.data.location)
						}}<span v-if="job.data.country"
							>{{ __(", ") }}{{ __(job.data.country) }}</span
						>
					</div>
				</div>
			</div>
		</div>

		<div v-if="!loading" class="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
			<h2 class="text-2xl font-bold text-red-700 mb-6">
				{{ __("Apply for this Opportunity") }}
			</h2>

			<div
				class="flex overflow-x-auto border-b border-gray-200 whitespace-nowrap mb-8 -mx-6 px-6 sm:mx-0 sm:px-0"
			>
				<button
					v-for="(step, index) in filteredSteps"
					:key="index"
					@click="goToStep(step.originalIndex)"
					:disabled="
						step.originalIndex > maxCompletedStep + 1 &&
						step.originalIndex > currentStep &&
						!isSubmitted
					"
					:class="[
						'py-3 px-3 sm:px-5 text-sm sm:text-base font-semibold transition-all duration-200 ease-in-out flex-shrink-0 flex items-center gap-2 border-b-4',
						currentStep === step.originalIndex
							? 'border-red-600 text-red-700 bg-red-50/50'
							: step.originalIndex < currentStep
								? 'border-green-600 text-green-600 hover:text-red-500 hover:border-red-200'
								: step.originalIndex <= maxCompletedStep + 1
									? 'border-gray-200 text-gray-600 hover:text-red-600 hover:border-red-300'
									: 'border-gray-100 text-gray-400 cursor-not-allowed',
					]"
				>
					<svg
						v-if="step.originalIndex < currentStep && !isSubmitted"
						class="w-4 h-4 text-green-500"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M5 13l4 4L19 7"
						></path>
					</svg>
					{{ __(step.title) }}
				</button>
			</div>

			<div class="space-y-10 min-h-[300px] bg-gray-50 rounded-xl p-6 border border-gray-200">
				<component
					:is="steps[currentStep].component"
					v-bind="{
						form,
						job: job.data,
						user: userDetails,

						isReadonly: isSubmitted,
					}"
				/>
			</div>

			<div
				v-if="!isSubmitted"
				class="flex justify-between mt-6 pt-4 border-t border-gray-100"
			>
				<Button
					v-if="currentStep > 0"
					variant="subtle"
					@click="prevStep"
					class="text-gray-700 hover:bg-gray-100"
				>
					{{ __("&larr; Back") }}
				</Button>

				<div class="flex-grow"></div>

				<Button
					variant="solid"
					:loading="isSaving"
					@click="handleStepAction"
					class="!bg-red-700 hover:bg-red-800 text-white px-6 py-3 rounded-lg ml-auto"
				>
					{{
						currentStep < steps.length - 1
							? __("Save & Continue")
							: __("Submit Application")
					}}
				</Button>
			</div>

			<div
				v-else
				class="mt-6 pt-4 border-t border-gray-100 text-lg font-medium text-gray-700"
			>
				<div class="text-center py-4">
					<div
						class="mb-2 text-emerald-600 font-semibold flex items-center justify-center"
					>
						<svg
							class="w-5 h-5 mr-2"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M5 13l4 4L19 7"
							></path>
						</svg>
						{{ __("Application Successfully Submitted") }}
					</div>
					<p class="text-gray-600">
						{{
							__(
								"Thank you for your application. You can review your submitted details here.",
							)
						}}
					</p>
				</div>
			</div>
		</div>

		<div v-else class="text-center py-20 text-gray-500">
			{{ __("Loading application details...") }}
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
						:loading="isSaving"
						@click="submitApplication"
					>
						<template #prefix>
							<FeatherIcon name="check-circle" class="w-4" />
						</template>
						{{ isSaving ? __("Submitting...") : __("Submit") }}
					</Button>
				</div>
			</template>
		</Dialog>
		<ErrorModal v-model="showErrorDialog" :errors="flatErrors" />
	</div>
</template>

<script setup>
import { useHead } from "@vueuse/head";
import { Button, createResource, Dialog, toast } from "frappe-ui";
import { FeatherIcon } from "lucide-vue-next";
import { computed, inject, markRaw, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import AdditionalInformation from "@/components/Application/AdditionalInformation.vue";
import ApplicationReview from "@/components/Application/ApplicationReview.vue";
import EducationBackground from "@/components/Application/EducationBackground.vue";
import PersonalInfo from "@/components/Application/PersonalInfo.vue";
import WorkExperience from "@/components/Application/WorkExperience.vue";

import ErrorModal from "../components/Modals/ErrorModal.vue";

import { isDateValid, isPastDate, validateForm } from "@/utils/validationUtils.js";

const route = useRoute();
const router = useRouter();
const user = inject("$user");

const jobId = route.params?.id || "";
const loading = ref(true);
const currentStep = ref(0);
const maxCompletedStep = ref(-1);
const isSaving = ref(false);

const showErrorDialog = ref(false);
const showSubmitDialog = ref(false);
const validationErrors = ref([]);

const flatErrors = computed(() => {
	if (!validationErrors.value.length) return [];
	return validationErrors.value.flatMap((err) =>
		typeof err === "string" ? [err] : Object.values(err).flat(),
	);
});

const applicationValidationConfig = [
	{
		step: 0,
		fields: ["surname", "other_names"],
		customChecks: [
			(form) => {
				const errors = [];
				if (form.identification_type && !form.id_number) {
					errors.push("ID Number is required when Identification Type is selected.");
				}
				if (!form.surname || !form.other_names) {
					errors.push("Surname and Other Names are required.");
				}
				return errors;
			},
		],
	},
	{
		step: 1,
		customChecks: [
			(form) => {
				const errors = [];
				if (!form.profession) {
					errors.push("Profession is required.");
				}
				if (!form.education || form.education.length === 0) {
					errors.push("Education History is required.");
				}
				return errors;
			},
		],
	},
	{
		step: 1,
		field: "education",
		label: "Education History",
		requiredFields: ["school_univ", "level", "year_of_passing"],
		dateChecks: [
			{
				field: "year_of_passing",
				validation: (date) => isPastDate(date),
				error: "must be a past date.",
			},
		],
	},
	{
		step: 1,
		field: "additional_skills",
		label: "Skills",
		requiredFields: ["additional_skill"],
	},
	{
		step: 1,
		field: "courses",
		label: "Certifications and Trainings",
		requiredFields: ["course_name", "institution", "start_date", "date_completed"],
		dateChecks: [
			{
				field: "start_date",
				validation: (date) => isPastDate(date),
				error: "must be a past date.",
			},
			{
				field: "date_completed",
				validation: (date) => isPastDate(date),
				error: "must be a past date.",
				condition: (row) => row.date_completed,
			},
			{
				field: "date_completed",
				validation: (date, row) => new Date(date) >= new Date(row.start_date),
				error: (row) => `cannot be before Start Date (${row.start_date}).`,
				condition: (row) => row.start_date && row.date_completed,
			},
		],
	},
	{
		step: 1,
		field: "licences",
		label: "Professional Licences",
		requiredFields: [
			"license_type",
			"institution",
			"qualification",
			"valid_from",
			{ field: "license_name", condition: (row) => row.license_type === "Other" },
			{ field: "valid_to", condition: (row) => !row.does_not_expire },
		],
		dateChecks: [
			{
				field: "valid_from",
				validation: (date) => isDateValid(date),
				error: "is not a valid date.",
			},
			{
				field: "valid_to",
				validation: (date) => isDateValid(date),
				error: "is not a valid date.",
				condition: (row) => row.valid_to && row.does_not_expire !== 1,
			},
			{
				field: "valid_to",
				validation: (date, row) => new Date(date) > new Date(row.valid_from),
				error: (row) => `must be after Valid From (${row.valid_from}).`,
				condition: (row) => row.valid_from && row.valid_to && row.does_not_expire !== 1,
			},
		],
	},
	{
		step: 2,
		field: "work_experience",
		label: "Work Experience",
		requiredFields: [
			"title",
			"company",
			"location",
			"from_date",
			{ field: "to_date", condition: (row) => !row.current },
		],
		dateChecks: [
			{
				field: "from_date",
				validation: (date) => isPastDate(date),
				error: "must be a past date.",
			},
			{
				field: "to_date",
				validation: (date) => isPastDate(date),
				error: "must be a past date.",
				condition: (row) => row.to_date && !row.current,
			},
			{
				field: "to_date",
				validation: (date, row) => new Date(date) >= new Date(row.from_date),
				error: (row) => `cannot be before From Date (${row.from_date}).`,
				condition: (row) => row.from_date && row.to_date && !row.current,
			},
		],
	},
	{
		step: 2,
		field: "work_references",
		label: "Work References",
		requiredFields: ["reference_name", "position", "organization", "email", "phone_number"],
		emailChecks: [{ field: "email", error: "is not a valid email address." }],
		phoneChecks: [{ field: "phone_number", error: "is not a valid phone number." }],
	},
	{ step: 3, validate: (form) => true },
];

const getStepValidationConfig = (stepIndex) => {
	return applicationValidationConfig.filter((config) => config.step === stepIndex);
};

const steps = [
	{
		hash: "#info",
		title: "Personal Info",
		component: markRaw(PersonalInfo),
		validate: (form) => {
			const config = getStepValidationConfig(0);
			const validationErrors = validateForm(form, config);
			return validationErrors.length ? validationErrors : true;
		},
	},
	{
		hash: "#education",
		title: "Education & Qualifications",
		component: markRaw(EducationBackground),
		validate: (form) => {
			const config = getStepValidationConfig(1);
			const validationErrors = validateForm(form, config);
			return validationErrors.length ? validationErrors : true;
		},
	},
	{
		hash: "#experience",
		title: "Work Experience",
		component: markRaw(WorkExperience),
		validate: (form) => {
			const config = getStepValidationConfig(2);
			const validationErrors = validateForm(form, config);
			return validationErrors.length ? validationErrors : true;
		},
	},
	{
		hash: "#additional",
		title: "Additional Information",
		component: markRaw(AdditionalInformation),
		validate: (form) => validateAdditionalInformation(form),
	},
	{
		hash: "#review",
		title: "Review & Submit",
		component: markRaw(ApplicationReview),
		validate: (form) => {
			const allErrors = [];
			for (let i = 0; i < steps.length - 1; i++) {
				const stepErrors = steps[i].validate(form);
				if (Array.isArray(stepErrors)) {
					allErrors.push(...stepErrors.map((err) => `[${steps[i].title}] ${err}`));
				}
			}
			return allErrors.length ? allErrors : true;
		},
	},
];

function validateAdditionalInformation(form) {
	const responses = form.screening_question_responses || {};
	const questions = job.data?.screening_questions || [];
	const errors = [];

	if (questions.length) {
		questions.forEach((q) => {
			const response = Object.values(responses).find((r) => r.question === q.question);
			const answer = response?.answer ?? "";
			if (q.is_required && !answer.trim()) {
				errors.push(`"${q.question}" is required.`);
			}
		});
	}

	if (form.linkedin) {
		const linkedinPattern = /^https?:\/\/(www\.)?linkedin\.com\/.*$/i;
		if (!linkedinPattern.test(form.linkedin)) {
			errors.push("LinkedIn URL is invalid.");
		}
	}

	if (form.github) {
		const githubPattern = /^https?:\/\/(www\.)?github\.com\/.*$/i;
		if (!githubPattern.test(form.github)) {
			errors.push("GitHub URL is invalid.");
		}
	}

	return errors.length ? errors : true;
}

const form = ref({});
const resume = ref(null);
const documents = ref([]);
const userDetails = ref({});

const isSubmitted = computed(() => {
	return opportunityApplication.data?.docstatus && opportunityApplication.data.docstatus !== 0;
});

const filteredSteps = computed(() => {
	if (isSubmitted.value) {
		const reviewStepIndex = steps.findIndex((s) => s.hash === "#review");
		const reviewStep = steps[reviewStepIndex];
		return [{ ...reviewStep, originalIndex: reviewStepIndex }];
	}

	return steps.map((s, index) => ({ ...s, originalIndex: index }));
});

const userDetailsResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.get_user_details",
	auto: true,
	onSuccess(data) {
		if (data) {
			userDetails.value = data;
			populateForm(data);
		}
		loading.value = false;
	},
	onError(err) {
		toast.error(err.message || "Failed to fetch user details");
		loading.value = false;
	},
});

const opportunityApplication = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.get_job_application",
	params: { name: jobId },
	auto: true,
	onSuccess(data) {
		if (data) {
			populateForm(data, true);
			form.value.job_application_id = data.name;
			resume.value = data.resume || null;
			documents.value = data.documents || [];

			if (data.job_title) {
				job.update({ params: { job: data.job_title } });
			}

			if (data.docstatus && data.docstatus !== 0) {
				const reviewIndex = steps.findIndex((s) => s.hash === "#review");
				if (reviewIndex !== -1) {
					currentStep.value = reviewIndex;
					router.replace({ hash: steps[reviewIndex].hash });
				}
			}
		}
	},
	onError(err) {
		toast.error(err.message || "Failed to fetch application details");
		loading.value = false;
	},
});

const job = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.get_job_details",
	params: { job: jobId },
	cache: ["job", jobId],
	onSuccess(data) {
		if (!data) {
			toast.error("Job not found");
			router.replace({ name: "JobListings" });
		}
	},
	onError(err) {
		toast.error(err.message || "Failed to fetch job details");
		router.replace({ name: "JobListings" });
	},
	auto: false,
});

const applicationSave = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.update_job_application",
});

const submitApplicationResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.application.submit_job_application",
	makeParams() {
		return {
			id: jobId,
		};
	},
});

function populateForm(data = {}, isApplication = false) {
	const src = isApplication ? "application" : "user";
	const user = userDetails.value || {};

	const fieldMap = {
		surname: ["surname", "last_name"],
		other_names: ["other_names", "first_name"],
		email_id: ["email_id", "email"],
		phone: ["phone", "mobile", "contact"],
		cover_letter: ["cover_letter"],
	};

	const renameMap = {
		date_of_birth: ["birth_date"],
		phone_number: ["phone", "mobile_no", "mobile", "contact"],
	};

	for (const key in fieldMap) {
		let value =
			data[key] ||
			fieldMap[key].map((alt) => data[alt]).find((v) => v !== undefined && v !== null) ||
			form.value[key];

		if ((value === undefined || value === null || value === "") && src === "user") {
			value =
				user[key] ||
				fieldMap[key].map((alt) => user[alt]).find((v) => v !== undefined && v !== null) ||
				"";
		}

		form.value[key] = Array.isArray(value) ? [...value] : value;
	}

	const source = src === "user" ? user : data;

	for (const formKey in renameMap) {
		if (
			form.value[formKey] !== undefined &&
			form.value[formKey] !== null &&
			form.value[formKey] !== "" &&
			!(Array.isArray(form.value[formKey]) && form.value[formKey].length === 0)
		) {
			continue;
		}

		const sourceKeys = renameMap[formKey];
		let mappedValue = null;

		mappedValue = sourceKeys
			.map((sourceKey) => source[sourceKey])
			.find((v) => v !== undefined && v !== null && v !== "");

		if (
			(mappedValue === undefined || mappedValue === null || mappedValue === "") &&
			isApplication
		) {
			mappedValue = sourceKeys
				.map((sourceKey) => user[sourceKey])
				.find((v) => v !== undefined && v !== null && v !== "");
		}

		if (mappedValue !== undefined && mappedValue !== null) {
			form.value[formKey] = mappedValue;
		}
	}

	const sourceToCopy = src === "user" ? user : data;
	for (const key in sourceToCopy) {
		const value = sourceToCopy[key];

		if (
			fieldMap[key] ||
			renameMap[key] ||
			form.value[key] === undefined ||
			form.value[key] === null ||
			form.value[key] === "" ||
			(Array.isArray(form.value[key]) && form.value[key].length === 0)
		) {
			if (!fieldMap[key] && !renameMap[key]) {
				form.value[key] = Array.isArray(value) ? [...value] : value;
			}
		}
	}
}

const goToStep = (index) => {
	if (isSubmitted.value) {
		const reviewIndex = steps.findIndex((s) => s.hash === "#review");
		if (index === reviewIndex) {
			currentStep.value = index;
			router.replace({ hash: steps[index].hash });
		} else {
			toast.error(
				"This submitted application is read-only and can only view the Review tab.",
			);
		}
		return;
	}

	if (index <= currentStep.value) {
		currentStep.value = index;
		router.replace({ hash: steps[index].hash });
		isSaving.value = false;
		return;
	}

	if (index > maxCompletedStep.value + 1) {
		toast.error("Please complete the previous step first.");
		return;
	}

	currentStep.value = index;
	router.replace({ hash: steps[index].hash });
	isSaving.value = false;
};

const prevStep = () => {
	if (currentStep.value > 0) goToStep(currentStep.value - 1);
};

onMounted(() => {
	const initialHash = route.hash || "#info";

	const index = steps.findIndex((s) => s.hash === initialHash);
	currentStep.value = index >= 0 ? index : 0;

	if (!route.hash || route.hash !== steps[currentStep.value].hash) {
		router.replace({ hash: steps[currentStep.value].hash });
	}
});

watch(
	() => route.hash,
	(newHash) => {
		const index = steps.findIndex((s) => s.hash === newHash);
		if (index >= 0) currentStep.value = index;
	},
);

watch(
	() => opportunityApplication.data,
	(newData) => {
		if (newData && newData.job_title) {
			job.update({ params: { job: newData.job_title } });
			job.reload();
		}
	},
	{ deep: true },
);

const handleStepAction = () => {
	const step = steps[currentStep.value];
	const result = step.validate(form.value, resume.value, userDetails.value);

	if (result !== true) {
		validationErrors.value = Array.isArray(result) ? result : [result];
		showErrorDialog.value = true;
		return;
	}

	if (currentStep.value < steps.length - 1) {
		saveApplicationDraft();
	} else {
		showSubmitDialog.value = true;
	}
};

const saveApplicationDraft = () => {
	isSaving.value = true;
	applicationSave.submit(
		{
			id: jobId,
			...form.value,
			resume: resume.value,
			documents: documents.value,
		},
		{
			onSuccess: (response) => {
				form.value.job_application_id = response?.name || response?.application_id;
				maxCompletedStep.value = Math.max(maxCompletedStep.value, currentStep.value);
				toast.success("Application stage saved successfully.");
				goToStep(currentStep.value + 1);
			},
			onError: (err) =>
				toast.error(err.messages?.[0] || "Failed to save application stage."),
			onSettled: () => (isSaving.value = false),
		},
	);
};

const submitApplication = () => {
	isSaving.value = true;
	submitApplicationResource.submit(
		{
			id: jobId,
		},
		{
			onSuccess: (response) => {
				if (response?.error) {
					window.location.reload();
				} else {
					window.location.reload();
				}
			},
			onError: (err) => {
				(toast.error(err.messages?.[0] || "Failed to submit application."),
					window.location.reload());
			},
			onSettled: () => (isSaving.value = false),
		},
	);
};

const redirectToWebsite = (url) => window.open(url, "_blank");
const getCompanyAbbr = (name) =>
	name
		? name
				.split(" ")
				.map((w) => w[0])
				.join("")
				.slice(0, 2)
				.toUpperCase()
		: "NA";

useHead({
	title: "Job Application Details | Kenya Red Cross ",
	meta: [
		{
			name: "description",
			content:
				"View and manage your job application details for Kenya Red Cross opportunities. Track your application status and updates.",
		},
	],
});
</script>
