<template>
	<div class="space-y-6">
		<div class="rounded-xl border p-5 bg-white shadow-sm">
			<h3 class="font-semibold text-gray-800 mb-3">
				{{ __("Professional Profiles") }}
			</h3>

			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-5">
				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">
						{{ __("LinkedIn Profile") }}
					</label>
					<FormControl
						v-model="localForm.linkedin"
						type="url"
						placeholder="https://linkedin.com/in/your-profile"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">
						{{ __("GitHub Profile") }}
					</label>
					<FormControl
						v-model="localForm.github"
						type="url"
						placeholder="https://github.com/username"
					/>
				</div>
				<Link
					doctype="Profession"
					v-model="localForm.profession"
					:label="__('Profession')"
					class="mt-4"
				/>
			</div>
		</div>

		<CollapsibleSection
			:title="__('Education & Work History')"
			:default-open="true"
			body-class="p-4 pt-0 space-y-4"
		>
			<ChildTable
				v-model="localForm.education"
				doctype="Employee Education"
				:label="__('Education History')"
				:autoEditGrid="false"
			/>
			<ChildTable
				v-model="localForm.work_experience"
				doctype="Work Experience"
				:label="__('Work Experience')"
				:autoEditGrid="false"
			/>
			<ChildTable
				v-model="localForm.work_references"
				doctype="Professional Reference"
				:label="__('Work References')"
				:autoEditGrid="false"
			/>
		</CollapsibleSection>

		<CollapsibleSection
			:title="__('Skills, Licences & Courses')"
			body-class="p-4 pt-0 space-y-4 grid grid-cols-1 gap-4"
		>
			<MultiSelect
				v-model="localForm.driving_licence"
				doctype="Driving Licences"
				:label="__('Driving Licence Classes')"
			/>
			<ChildTable
				v-model="localForm.additional_skills"
				doctype="Additional Skill"
				:label="__('Skills')"
				:autoEditGrid="false"
			/>
			<ChildTable
				v-model="localForm.courses"
				doctype="User External Course"
				:label="__('Certifications and Trainings')"
				:autoEditGrid="false"
			/>
			<ChildTable
				v-model="localForm.licences"
				doctype="Personnel Licence"
				:label="__('Professional Licences')"
				:autoEditGrid="false"
			/>
		</CollapsibleSection>
		<div class="flex justify-end">
			<button
				v-if="hasChanges"
				type="button"
				@click="handleSave"
				class="flex items-center gap-1 px-8 py-2 text-sm font-bold bg-red-600 hover:bg-red-700 text-white rounded-lg shadow-md transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-red-600 disabled:active:scale-100"
				:disabled="saveInProgress"
				:aria-busy="saveInProgress"
			>
				<span>{{ __("Save") }}</span>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-4 h-4"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
					stroke-width="2"
					aria-hidden="true"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M5 5v14a2 2 0 002 2h10a2 2 0 002-2V7l-4-4H7a2 2 0 00-2 2z"
					/>
					<path stroke-linecap="round" stroke-linejoin="round" d="M9 9h6v6H9z" />
				</svg>
			</button>
		</div>
	</div>
	<ErrorModal v-model="showErrorDialog" :errors="flatErrors" />
</template>

<script setup>
import CollapsibleSection from "@/components/CollapsibleSection.vue";
import ChildTable from "@/components/Controls/ChildTable.vue";
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import { createResource, FormControl, toast } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";
import ErrorModal from "../Modals/ErrorModal.vue";

import { isDateValid, isPastDate, validateForm } from "@/utils/validationUtils.js";

const props = defineProps({
	form: {
		type: Object,
		required: true,
	},
});

const emit = defineEmits(["saved"]);

const saveInProgress = ref(false);
const originalFormData = ref({});
const showErrorDialog = ref(false);
const flatErrors = ref([]);

const localForm = reactive({
	profession: null,
	linkedin: "",
	github: "",
	education: [],
	work_experience: [],
	work_references: [],
	additional_skills: [],
	courses: [],
	languages: [],
	licences: [],
	driving_licence: [],
});

const userProfileValidationConfig = [
	{
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
		field: "additional_skills",
		label: "Skills",
		requiredFields: ["additional_skill"],
	},
	{
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
		field: "work_references",
		label: "Work References",
		requiredFields: ["reference_name", "position", "organization", "email", "phone_number"],
		emailChecks: [{ field: "email", error: "is not a valid email address." }],
		phoneChecks: [{ field: "phone_number", error: "is not a valid phone number." }],
	},
];

function syncLocalForm(newForm) {
	Object.keys(localForm).forEach((key) => {
		if (newForm[key] !== undefined) {
			localForm[key] = newForm[key];
		}
	});
	originalFormData.value = JSON.parse(JSON.stringify(localForm));
}

watch(
	() => props.form,
	(newForm) => {
		syncLocalForm(newForm);
	},
	{ immediate: true, deep: true }
);

function getChangedFields() {
	const changed = {};
	for (const key in localForm) {
		const currentValue = JSON.stringify(localForm[key]);
		const originalValue = JSON.stringify(originalFormData.value[key]);
		if (currentValue !== originalValue) {
			changed[key] = localForm[key];
		}
	}
	return changed;
}

const hasChanges = computed(() => {
	return Object.keys(getChangedFields()).length > 0;
});

const saveUserResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.update_user_details",
	makeParams() {
		return getChangedFields();
	},
	onSuccess(data) {
		toast.success("Education and skills saved successfully");
		originalFormData.value = JSON.parse(JSON.stringify(localForm));
		saveInProgress.value = false;
		showErrorDialog.value = false;
		emit("saved", localForm);
	},
	onError(err) {
		console.error("Save error:", err);
		flatErrors.value = [err.message || "Failed to save education and skills"];
		showErrorDialog.value = true;
		saveInProgress.value = false;
	},
});

async function handleSave() {
	const changes = getChangedFields();

	if (Object.keys(changes).length === 0) {
		toast.info("No changes to save");
		return;
	}

	const validationErrors = validateForm(localForm, userProfileValidationConfig);

	if (validationErrors.length > 0) {
		flatErrors.value = validationErrors;
		showErrorDialog.value = true;
		return;
	}

	saveInProgress.value = true;
	await saveUserResource.submit();
}
</script>
