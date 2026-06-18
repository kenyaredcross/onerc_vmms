<template>
	<div class="space-y-8">
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
			<div>
				<h2 class="text-lg font-semibold mb-4 border-b pb-2">
					{{ __("Personal Information") }}
				</h2>
				<div class="space-y-4">
					<FormControl
						v-model="localForm.first_name"
						:label="__('First Name')"
						:required="true"
					/>
					<FormControl v-model="localForm.middle_name" :label="__('Other Names')" />
					<FormControl
						v-model="localForm.last_name"
						:label="__('Last Name')"
						:required="true"
					/>

					<FormControl v-model="localForm.email" :label="__('Email')" :required="true" />
					<FormControl
						v-model="localForm.birth_date"
						:label="__('Date of Birth')"
						type="date"
						:required="true"
					/>
					<FormControl v-model="localForm.phone" :label="__('Phone')" />
					<FormControl
						v-model="localForm.mobile_no"
						:label="__('Mobile Money (M-Pesa) phone if different')"
					/>
				</div>
			</div>

			<div>
				<h2 class="text-lg font-semibold mb-4 border-b pb-2">
					{{ __("Identification") }}
				</h2>
				<div class="space-y-4">
					<Link
						doctype="Gender"
						v-model="localForm.gender"
						:label="__('Gender')"
						:required="true"
					/>
					<FormControl
						v-model="localForm.marital_status"
						:label="__('Marital Status')"
						type="select"
						:options="maritalOptions"
					/>
					<FormControl
						v-model="localForm.citizenship"
						:label="__('Citizenship')"
						type="select"
						:options="citizenshipOptions"
						:required="true"
					/>
					<Link
						doctype="Country"
						v-model="localForm.country_of_citizenship"
						:label="__('Country of Citizenship')"
						:filters="
							localForm.citizenship === 'Citizen'
								? [['name', '=', 'Gambia']]
								: [['name', '!=', 'Gambia']]
						"
					/>
					<Link
						doctype="Identification Document Type"
						v-model="localForm.identification_type"
						:label="__('Identification Document Type')"
						:required="true"
					/>
					<FormControl v-model="localForm.id_number" :label="__('ID Number')" />
					<FormControl
						v-model="localForm.number_of_dependants"
						:label="__('Number of Dependants')"
					/>
					<MultiSelect
						v-model="localForm.languages"
						doctype="Volunteer Language"
						:label="__('Languages')"
					/>
				</div>
			</div>

			<div>
				<h2 class="text-lg font-semibold mb-4 border-b pb-2">
					{{ __("Contact & Location") }}
				</h2>
				<div class="space-y-4">
					<Link doctype="County" v-model="localForm.county" :label="__('LGA')" />
					<Link
						v-if="localForm.county"
						doctype="Sub County"
						v-model="localForm.sub_county"
						:label="__('District')"
						:filters="{ county: localForm.county }"
					/>
					<Link
						doctype="Ward"
						v-model="localForm.ward"
						:label="__('Ward')"
						:filters="{ sub_county: localForm.sub_county }"
					/>
					<Link
						v-if="localForm.sub_county"
						doctype="Administrative Location"
						v-model="localForm.administrative_location"
						:label="__('Location')"
						:filters="{ sub_county: localForm.sub_county }"
					/>
					<Link
						v-if="localForm.administrative_location"
						doctype="Sub Location"
						v-model="localForm.sub_location"
						:label="__('Sub Location')"
						:filters="{ location: localForm.administrative_location }"
					/>
					<FormControl
						v-model="localForm.access_to_internet"
						:label="__('Access to Internet')"
						type="select"
						:options="internetOptions"
					/>
				</div>
			</div>
		</div>
		<div class="mb-40 mt-8">
			<FormControl
				v-model="localForm.consent_to_use_of_bio_data"
				:label="__('Consent to Use of Bio Data')"
				type="checkbox"
				:required="true"
			/>
			<p class="italic text-sm">
				{{
					__(
						"I consent to the use of my bio data for identification and verification purposes as per the organization's data protection policy.",
					)
				}}
			</p>
		</div>
		<div class="flex justify-end">
			<button
				v-if="hasChanges"
				@click="handleSave"
				variant="solid"
				class="flex items-center gap-1 px-8 py-2 text-sm font-bold bg-red-600 hover:bg-red-700 text-white rounded-lg shadow-md transition-all active:scale-95"
				:loading="saveInProgress"
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
		<ErrorModal v-model="showErrorDialog" :errors="flatErrors" />
	</div>
</template>

<script setup>
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import { FormControl, createResource, toast } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";
import ErrorModal from "../Modals/ErrorModal.vue";

import { validateForm } from "@/utils/validationUtils.js";

const props = defineProps({
	form: {
		type: Object,
		required: true,
	},
});

const emit = defineEmits(["saved"]);

const citizenshipOptions = [
	{ label: "Citizen", value: "Citizen" },
	{ label: "Non-citizen", value: "Non-citizen" },
	{ label: "Refugee", value: "Refugee" },
	{ label: "Migrant", value: "Migrant" },
	{ label: "Other", value: "Other" },
];

const maritalOptions = [
	{ label: "Single", value: "Single" },
	{ label: "Married", value: "Married" },
	{ label: "Divorced", value: "Divorced" },
	{ label: "Widowed", value: "Widowed" },
];

const internetOptions = [
	{ label: "Yes", value: "Yes" },
	{ label: "No", value: "No" },
	{ label: "Sometimes", value: "Sometimes" },
];

const saveInProgress = ref(false);
const originalFormData = ref({});
const showErrorDialog = ref(false);
const flatErrors = ref([]);

const localForm = reactive({
	first_name: "",
	middle_name: "",
	last_name: "",
	email: "",
	phone: "",
	id_number: "",
	identification_type: "",
	birth_date: "",
	marital_status: "",
	number_of_dependants: "",
	blood_group: "",
	professional_summary: "",
	citizenship: "",
	country_of_citizenship: "",
	languages: [],

	county: "",
	sub_county: "",
	ward: "",
	administrative_location: "",
	sub_location: "",
	access_to_internet: "",
	mobile_no: "",
	gender: "",
	consent_to_use_of_bio_data: false,
});

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
	{ immediate: true, deep: true },
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

const formConfig = {
	formChecks: {
		requiredFields: [
			"first_name",
			"last_name",
			"birth_date",
			"email",
			"phone",
			"identification_type",
			"citizenship",
			"country_of_citizenship",
			"id_number",
			"gender",
		],
		emailChecks: [
			{
				field: "email",
			},
		],
		phoneChecks: [
			{
				field: "phone",
			},
			{
				field: "mobile_no",
			},
		],
		dateChecks: [
			{
				field: "birth_date",
				maxDate: new Date(),
				errorMessage: "Date of Birth cannot be in the future.",
			},
		],
		customChecks: [
			(form) => {
				const errors = [];
				if (!form.identification_type || !form.id_number) return errors;

				const id = String(form.id_number).trim();
				const type = form.identification_type.toLowerCase();

				const rules = {
					"national id": {
						pattern: /^\d{7,9}$/,
						error: "National Identity Card must be 7–9 digits.",
					},
					passport: {
						pattern: /^[A-Z0-9]{6,9}$/i,
						error: "Passport number must be 6–9 characters (letters and numbers).",
					},
					"military id": {
						pattern: /^[A-Z0-9\-]{5,20}$/i,
						error: "Military ID must be 5–20 characters (letters, numbers, hyphens allowed).",
					},
					"alien id": {
						pattern: /^[A-Z0-9\-]{5,20}$/i,
						error: "Alien ID must be 5–20 characters (letters, numbers, hyphens allowed).",
					},
					"birth certificate": {
						pattern: /^[A-Z0-9\-]{6,20}$/i,
						error: "Birth Certificate number must be 6–20 characters.",
					},
					"nemis number": {
						pattern: /^\d{8,14}$/,
						error: "NEMIS Number must be 8–14 digits.",
					},
				};

				const rule = rules[type] || {
					pattern: /^[A-Z0-9\-]{5,20}$/i,
					error: "Identification Number must be 5–20 characters (letters, numbers, hyphens allowed).",
				};

				if (!rule.pattern.test(id)) {
					errors.push(rule.error);
				}

				return errors;
			},
		],
	},
};
const saveUserResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.update_user_details",
	makeParams() {
		return getChangedFields();
	},
	onSuccess(data) {
		toast.success("Personal information saved successfully");
		originalFormData.value = JSON.parse(JSON.stringify(localForm));
		saveInProgress.value = false;
		emit("saved", localForm);
	},
	onError(err) {
		console.error("Save error:", err);
		flatErrors.value = [err.message || "Failed to save personal information"];
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

	const validationErrors = validateForm(localForm, formConfig);
	if (Object.keys(validationErrors).length > 0) {
		flatErrors.value = Object.entries(validationErrors).map(
			([field, message]) => `${field}: ${message}`,
		);
		showErrorDialog.value = true;
		return;
	}

	saveInProgress.value = true;
	await saveUserResource.submit();
}

watch(
	() => localForm.county,
	() => {
		localForm.sub_county = null;
		localForm.administrative_location = null;
		localForm.ward = null;
		localForm.sub_location = null;
	},
);

watch(
	() => localForm.sub_county,
	() => {
		localForm.administrative_location = null;
		localForm.ward = null;
		localForm.sub_location = null;
	},
);

watch(
	() => localForm.administrative_location,
	() => {
		localForm.sub_location = null;
	},
);

watch(
	() => localForm.citizenship,
	() => {
		localForm.country_of_citizenship = null;
	},
);
</script>
