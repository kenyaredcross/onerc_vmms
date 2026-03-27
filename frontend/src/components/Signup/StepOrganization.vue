<template>
	<section>
		<h2 class="text-xl font-bold text-red-700 mb-4">
			{{ __("Personal Info") }}
		</h2>
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
			<div>
				<Link
					v-model="localModel.company"
					:label="__('Branch / Wilaya')"
					doctype="Company"
					:required="true"
					:filters="{ is_group: 0 }"
				/>
				<p v-if="errors[0]?.['Branch / Wilaya']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Branch / Wilaya"] }}
				</p>
			</div>
			<div>
				<FormControl
					v-model="localModel.phone_number"
					label="Phone Number"
					type="tel"
					required
				/>
				<p v-if="errors[0]?.['Phone Number']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Phone Number"] }}
				</p>
			</div>
			<div>
				<FormControl v-model="localModel.email_id" label="Email Address" required />
				<p v-if="errors[0]?.['Email Address']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Email Address"] }}
				</p>
			</div>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
			<div>
				<FormControl
					v-model="localModel.date_of_birth"
					:label="__('Date of Birth')"
					type="date"
				/>
				<p v-if="errors[0]?.['Date of Birth']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Date of Birth"] }}
				</p>
			</div>

			<div>
				<Link
					v-model="localModel.gender"
					:label="__('Gender')"
					doctype="Gender"
					:required="true"
				/>
				<p v-if="errors[0]?.['Gender']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Gender"] }}
				</p>
			</div>
			<div>
				<FormControl
					v-model="localModel.marital_status"
					:label="__('Marital Status')"
					type="select"
					:options="maritalOptions"
				/>
				<p v-if="errors[0]?.['Marital Status']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Marital Status"] }}
				</p>
			</div>
			<div>
				<FormControl
					v-model="localModel.number_of_dependants"
					:label="__('Number of Dependants')"
					type="number"
				/>
				<p v-if="errors[0]?.['Number of Dependants']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Number of Dependants"] }}
				</p>
			</div>
			<div>
				<FormControl
					v-model="localModel.mpesa_mobile_phone"
					:label="__('Mobile Money (M-Pesa) phone if different')"
					type="tel"
				/>
				<p
					v-if="errors[0]?.['Mobile Money (M-Pesa) phone if different']"
					class="text-sm text-red-600 mt-1"
				>
					{{ errors[0]?.["Mobile Money (M-Pesa) phone if different"] }}
				</p>
			</div>
			<div>
				<FormControl
					v-model="localModel.blood_group"
					:label="__('Blood Group')"
					type="select"
					:options="bloodGroupOptions"
				/>
				<p v-if="errors[0]?.['Blood Group']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Blood Group"] }}
				</p>
			</div>
			<div>
				<FormControl
					v-model="localModel.has_insurance"
					:label="__('TRCS Insurance')"
					type="select"
					:options="yesNoOptions"
					title="Select 'Yes' if you are insured through TRCS"
					aria-describedby="krcs-insurance-desc"
				/>
				<p id="krcs-insurance-desc" class="text-sm text-gray-600 mt-1">
					<span title="KRCS = Tanzania Red Cross Society" class="mr-2 text-xs">ⓘ</span>
					{{
						__(
							"Indicate whether you have insurance with the Tanzania Red Cross Society (TRCS).",
						)
					}}
				</p>
				<p v-if="errors[0]?.['TRCS Insurance']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["TRCS Insurance"] }}
				</p>
			</div>
		</div>

		<h2 class="text-xl font-bold text-red-700 mb-4">
			{{ __("Location Info") }}
		</h2>
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
			<div>
				<Link
					v-model="localModel.county"
					:label="__('Wilaya')"
					doctype="County"
					:required="true"
				/>
				<p v-if="errors[0]?.['Wilaya']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Wilaya"] }}
				</p>
			</div>
			<div>
				<Link
					v-model="localModel.sub_county"
					:label="__('Kata')"
					doctype="Sub County"
					:required="true"
					:filters="localModel.county ? { county: localModel.county } : {}"
				/>
				<p v-if="errors[0]?.['Kata']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Kata"] }}
				</p>
			</div>

			<div>
				<Link
					v-model="localModel.ward"
					:label="__('Mtaa')"
					doctype="Ward"
					:required="true"
					:filters="localModel.sub_county ? { sub_county: localModel.sub_county } : {}"
				/>
				<p v-if="errors[0]?.['Mtaa']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Mtaa"] }}
				</p>
			</div>

			<div>
				<Link
					v-model="localModel.administrative_location"
					:label="__('Location')"
					doctype="Administrative Location"
					:required="true"
					:filters="localModel.sub_county ? { sub_county: localModel.sub_county } : {}"
				/>
				<p v-if="errors[0]?.['Location']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Location"] }}
				</p>
			</div>

			<div>
				<Link
					v-model="localModel.sub_location"
					:label="__('Sub Location')"
					doctype="Sub Location"
					:required="true"
					:filters="
						localModel.administrative_location
							? { location: localModel.administrative_location }
							: {}
					"
				/>
				<p v-if="errors[0]?.['Sub Location']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Sub Location"] }}
				</p>
			</div>
		</div>
		<h2 class="text-xl font-bold text-red-700 mb-4">
			{{ __("Identification") }}
		</h2>
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			<div>
				<FormControl
					v-model="localModel.citizenship"
					:label="__('Citizenship')"
					type="select"
					:options="citizenshipOptions"
					:required="true"
				/>
				<p v-if="errors[0]?.['Citizenship']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Citizenship"] }}
				</p>
			</div>

			<div>
				<Link
					doctype="Identification Document Type"
					v-model="localModel.identification_type"
					:label="__('Identification Document Type')"
					:required="true"
				/>
				<p
					v-if="errors[0]?.['Identification Document Type']"
					class="text-sm text-red-600 mt-1"
				>
					{{ errors[0]?.["Identification Document Type"] }}
				</p>
			</div>
			<div>
				<FormControl
					v-model="localModel.id_number"
					:label="__('Identification Number')"
					type="text"
					:required="true"
				/>
				<p v-if="errors[0]?.['Identification Number']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Identification Number"] }}
				</p>
			</div>

			<div>
				<Link
					doctype="Country"
					v-model="localModel.country_of_citizenship"
					:label="__('Country of Citizenship')"
					:required="true"
					:filters="
						localModel.citizenship === 'Citizen'
							? [['name', '=', 'Tanzania']]
							: [['name', '!=', 'Tanzania']]
					"
				/>
				<p v-if="errors[0]?.['Country of Citizenship']" class="text-sm text-red-600 mt-1">
					{{ errors[0]?.["Country of Citizenship"] }}
				</p>
			</div>
		</div>

		<div class="mb-40 mt-8">
			<FormControl
				v-model="localModel.consent_to_use_of_bio_data"
				:label="__('Consent to Use of Bio Data')"
				type="checkbox"
				:required="true"
				:options="reasonsOptions"
			/>
			<p class="italic text-sm">
				{{
					__(
						"I consent to the use of my bio data for identification and verification purposes as per the organization's data protection policy.",
					)
				}}
			</p>
		</div>
	</section>
</template>

<script setup>
import Link from "@/components/Controls/Link.vue";
import { FormControl } from "frappe-ui";
import { computed, watch } from "vue";

const props = defineProps({
	modelValue: { type: Object, required: true },
	errors: { type: Object, default: () => ({}) },
});

const emit = defineEmits(["update:modelValue", "update:errors"]);

const localModel = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const maritalOptions = [
	{ label: "Single", value: "Single" },
	{ label: "Married", value: "Married" },
	{ label: "Divorced", value: "Divorced" },
	{ label: "Widowed", value: "Widowed" },
];

const bloodGroupOptions = [
	{ label: "A+", value: "A+" },
	{ label: "A-", value: "A-" },
	{ label: "B+", value: "B+" },
	{ label: "B-", value: "B-" },
	{ label: "AB+", value: "AB+" },
	{ label: "AB-", value: "AB-" },
	{ label: "O+", value: "O+" },
	{ label: "O-", value: "O-" },
	{ label: "Don't Know", value: "Don't Know" },
];

const yesNoOptions = [
	{ label: "Yes", value: "Yes" },
	{ label: "No", value: "No" },
];

const citizenshipOptions = [
	{ label: "Citizen", value: "Citizen" },
	{ label: "Non-citizen", value: "Non-citizen" },
	{ label: "Refugee", value: "Refugee" },
	{ label: "Migrant", value: "Migrant" },
	{ label: "Other", value: "Other" },
];

function validateForm() {
	const stepErrors = { 0: {} };
	const form = localModel.value;

	if (!form.company) stepErrors[0]["Branch / Wilaya"] = "Branch is required";
	if (!form.county) stepErrors[0]["Wilaya"] = "Wilaya is required";
	if (!form.phone_number) stepErrors[0]["Phone Number"] = "Phone number is required";
	if (!form.email_id) stepErrors[0]["Email Address"] = "Email address is required";
	if (!form.gender) stepErrors[0]["Gender"] = "Gender is required";
	if (!form.sub_county) stepErrors[0]["Kata"] = "This field is required";
	if (!form.administrative_location) stepErrors[0]["Location"] = "This field is required";
	if (!form.sub_location) stepErrors[0]["Sub Location"] = "This field is required";
	if (!form.ward) stepErrors[0]["Mtaa"] = "Mtaa is required";
	if (!form.citizenship) stepErrors[0]["Citizenship"] = "This field is required";
	if (!form.identification_type)
		stepErrors[0]["Identification Document Type"] = "This field is required";
	if (!form.id_number) stepErrors[0]["Identification Number"] = "This field is required";
	if (!form.country_of_citizenship)
		stepErrors[0]["Country of Citizenship"] = "This field is required";
	if (!form.date_of_birth) stepErrors[0]["Date of Birth"] = "Date of birth is required";

	if (form.date_of_birth) {
		const dob = new Date(form.date_of_birth);
		const today = new Date();
		let age = today.getFullYear() - dob.getFullYear();
		const m = today.getMonth() - dob.getMonth();
		if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) age--;
		if (age < 7 || age > 100)
			stepErrors[0]["Date of Birth"] = "Age must be between 7 and 100 years";
	}

	if (form.identification_type && form.id_number) {
		const id = form.id_number.toString().trim();

		switch (form.identification_type.toLowerCase()) {
			case "national id":
			case "national identity card":
				if (!/^\d{7,9}$/.test(id))
					stepErrors[0]["Identification Number"] = "National ID must be 7–9 digits";
				break;
			case "passport":
				if (!/^[A-Z0-9]{6,9}$/i.test(id))
					stepErrors[0]["Identification Number"] =
						"Passport number must be 6–9 characters (letters and numbers)";
				break;

			case "military id":
				if (!/^[A-Z0-9\-]{5,20}$/i.test(id))
					stepErrors[0]["Identification Number"] =
						"Military ID must be 5–20 characters (letters, numbers, hyphens allowed)";
				break;

			case "alien id":
				if (!/^[A-Z0-9\-]{5,20}$/i.test(id))
					stepErrors[0]["Identification Number"] =
						"Alien ID must be 5–20 characters (letters, numbers, hyphens allowed)";
				break;

			case "birth certificate":
				if (!/^[A-Z0-9\-]{6,20}$/i.test(id))
					stepErrors[0]["Identification Number"] =
						"Birth Certificate number must be 6–20 characters";
				break;

			case "nemis number":
				if (!/^\d{8,14}$/.test(id))
					stepErrors[0]["Identification Number"] = "NEMIS Number must be 8–14 digits";
				break;
			default:
				if (!/^[A-Z0-9\-]{5,20}$/i.test(id))
					stepErrors[0]["Identification Number"] =
						"Identification Number must be 5–20 characters (letters, numbers, hyphens allowed)";
		}
	}
	const phoneRegex = /^(?:\+254|0)(?:7\d{8}|1\d{8})$/;

	if (form.mpesa_mobile_phone) {
		const phone = form.mpesa_mobile_phone.toString().replace(/\s+/g, "");
		if (!phoneRegex.test(phone))
			stepErrors[0]["Mobile Money (M-Pesa) phone if different"] =
				"Enter a valid phone number";
	}

	if (form.phone_number) {
		const phone = form.phone_number.toString().replace(/\s+/g, "");
		if (!phoneRegex.test(phone)) stepErrors[0]["Phone Number"] = "Enter a valid phone number";
	}

	emit("update:errors", stepErrors);
	return Object.keys(stepErrors[0]).length === 0;
}

import { onMounted, ref } from "vue";

const ready = ref(false);

onMounted(() => {
	setTimeout(() => {
		ready.value = true;
	}, 500);
});

watch(
	() => localModel.value.company,
	(newVal, oldVal) => {
		if (ready.value && oldVal !== newVal) {
			if (!localModel.value.county && newVal) {
				localModel.value.county = newVal;
			}
		}
	},
);

watch(
	() => localModel.value.county,
	(newVal, oldVal) => {
		if (ready.value && oldVal !== newVal) {
			localModel.value.sub_county = "";
			localModel.value.ward = "";
			localModel.value.administrative_location = "";
			localModel.value.sub_location = "";
		}
	},
);

watch(
	() => localModel.value.sub_county,
	(newVal, oldVal) => {
		if (ready.value && oldVal !== newVal) {
			localModel.value.administrative_location = "";
			localModel.value.sub_location = "";
			localModel.value.ward = "";
		}
	},
);

watch(
	() => localModel.value.administrative_location,
	(newVal, oldVal) => {
		if (ready.value && oldVal !== newVal) {
			localModel.value.sub_location = "";
		}
	},
);

watch(
	() => localModel.value.citizenship,
	(newVal, oldVal) => {
		if (ready.value && oldVal !== newVal) {
			localModel.value.country_of_citizenship = newVal === "Citizen" ? "Tanzania" : "";
		}
	},
);

watch(localModel, validateForm, { deep: true, immediate: true });
</script>
