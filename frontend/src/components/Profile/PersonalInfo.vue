<template>
	<div class="space-y-8">
		<!-- Save Button -->
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

		<!-- Responsive Grid Layout -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
			<!-- Column 1: Personal Information -->
			<div>
				<h2 class="text-lg font-semibold mb-4 border-b pb-2">
					{{ __("Personal Information") }}
				</h2>
				<div class="space-y-4">
					<FormControl v-model="localForm.first_name" :label="__('First Name')" />
					<FormControl v-model="localForm.middle_name" :label="__('Other Names')" />
					<FormControl v-model="localForm.last_name" :label="__('Last Name')" />
					<FormControl v-model="localForm.full_name" :label="__('Full Name')" />
					<FormControl v-model="localForm.email" :label="__('Email')" />
					<FormControl
						v-model="localForm.birth_date"
						:label="__('Date of Birth')"
						type="date"
					/>
					<FormControl v-model="localForm.phone" :label="__('Phone')" />
					<FormControl
						v-model="localForm.mpesa_mobile_phone"
						:label="__('Mobile Money (M-Pesa) phone if different')"
					/>
				</div>
			</div>

			<!-- Column 2: Identification -->
			<div>
				<h2 class="text-lg font-semibold mb-4 border-b pb-2">
					{{ __("Identification") }}
				</h2>
				<div class="space-y-4">
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
								? [['name', '=', 'Kenya']]
								: [['name', '!=', 'Kenya']]
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

			<!-- Column 3: Contact & Location -->
			<div>
				<h2 class="text-lg font-semibold mb-4 border-b pb-2">
					{{ __("Contact & Location") }}
				</h2>
				<div class="space-y-4">
					<Link doctype="County" v-model="localForm.county" :label="__('County')" />
					<Link
						v-if="localForm.county"
						doctype="Sub County"
						v-model="localForm.sub_county"
						:label="__('Sub County')"
						:filters="{ county: localForm.county }"
					/>
					<Link doctype="Ward" v-model="localForm.ward" :label="__('Ward')" />
					<Link
						v-if="localForm.sub_county"
						doctype="Administrative Location"
						v-model="localForm.administrative_location"
						:label="__('Location')"
						:filters="{ sub_county: localForm.sub_county }"
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

		<ErrorModal v-model="showErrorDialog" :errors="flatErrors" />
	</div>
</template>

<script setup>
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import { FormControl, createResource, toast } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";
import ErrorModal from "../Modals/ErrorModal.vue";

import { isEmailValid, isPastDate } from "@/utils/validationUtils.js";

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
	full_name: "",
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
	access_to_internet: "",
	mpesa_mobile_phone: "",
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

const isKenyanPhoneNumberValid = (phone) => {
	if (!phone) return true;
	const cleanPhone = phone.toString().replace(/\s+/g, "");

	const phoneRegex = /^(?:\+254|0)(7\d{8}|1\d{8})$/;
	return phoneRegex.test(cleanPhone);
};

function validateForm(form) {
	const errors = {};

	const requiredFields = [
		{ field: "first_name", label: "First Name" },
		{ field: "last_name", label: "Last Name" },
		{
			field: "birth_date",
			label: "Date of Birth",
			check: (val) => isPastDate(val) || "must be a date in the past.",
		},
		{ field: "email", label: "Email" },
		{ field: "phone", label: "Phone" },
		{ field: "citizenship", label: "Citizenship" },
	];

	requiredFields.forEach((item) => {
		if (!form[item.field]) {
			errors[item.label] = `${item.label} is required.`;
		} else if (item.check) {
			const checkResult = item.check(form[item.field]);
			if (typeof checkResult === "string") {
				errors[item.label] = `${item.label} ${checkResult}`;
			}
		}
	});

	if (form.identification_type && form.id_number) {
		const id = form.id_number.toString().trim();

		switch (form.identification_type.toLowerCase()) {
			case "national id":
			case "national identity card":
				if (!/^\d{7,9}$/.test(id))
					errors["Identification Number"] = "National ID must be 7–9 digits";
				break;
			case "passport":
				if (!/^[A-Z]\d{7}$/.test(id))
					errors["Identification Number"] =
						"Passport must start with a letter followed by 7 digits";
				break;
			case "military id":
				if (!/^MIL\d{5,7}$/.test(id))
					errors["Identification Number"] =
						"Military ID must start with 'MIL' followed by 5–7 digits";
				break;
			case "alien id":
				if (!/^A\d{7,9}$/.test(id))
					errors["Identification Number"] =
						"Alien ID must start with 'A' followed by 7–9 digits";
				break;
			case "birth certificate":
				if (!/^\d{8,12}$/.test(id))
					errors["Identification Number"] = "Birth Certificate must be 8–12 digits";
				break;
			case "nemis number":
				if (!/^\d{10,12}$/.test(id))
					errors["Identification Number"] = "NEMIS Number must be 10–12 digits";
				break;
			case "hospital card":
			case "health id":
				if (!/^[A-Z0-9]{5,15}$/i.test(id))
					errors["Identification Number"] =
						"Health/Hospital ID must be 5–15 alphanumeric characters";
				break;
			default:
				if (!id) errors["Identification Number"] = "ID number cannot be empty";
				break;
		}
	} else if (form.identification_type || form.id_number) {
		if (!form.identification_type)
			errors["Identification Document Type"] =
				"Identification Document Type is required if ID Number is provided.";
		if (!form.id_number)
			errors["ID Number"] =
				"ID Number is required if Identification Document Type is provided.";
	}

	if (form.mpesa_mobile_phone && !isKenyanPhoneNumberValid(form.mpesa_mobile_phone)) {
		errors["Mobile Money (M-Pesa) Phone"] =
			"Enter a valid Kenyan phone number (e.g., 07xx/01xx or +254).";
	}

	if (form.phone && !isKenyanPhoneNumberValid(form.phone)) {
		errors["Phone"] = "Enter a valid Kenyan phone number (e.g., 07xx/01xx or +254).";
	}

	if (form.email) {
		const email = form.email.toString().trim();
		if (!isEmailValid(email)) errors["Email"] = "Enter a valid email address";
	}

	return errors;
}

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

	const validationErrors = validateForm(localForm);
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
	},
);

watch(
	() => localForm.sub_county,
	() => {
		localForm.administrative_location = null;
	},
);

watch(
	() => localForm.citizenship,
	() => {
		localForm.country_of_citizenship = null;
	},
);
</script>
