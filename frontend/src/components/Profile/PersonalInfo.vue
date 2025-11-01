<template>
	<div class="space-y-6">
		<div class="flex justify-end">
			<button
				@click="handleEditToggle"
				variant="solid"
				class="flex items-center gap-1 px-8 py-2 text-sm font-bold bg-red-600 hover:bg-red-700 text-white rounded-lg shadow-md transition-all active:scale-95"
				:loading="saveInProgress"
			>
				{{ editing ? __("Save") : __("Edit") }}
			</button>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			<FormControl
				v-model="localForm.first_name"
				:label="__('First Name')"
				:readOnly="!editing"
			/>
			<FormControl
				v-model="localForm.middle_name"
				:label="__('Other Names')"
				:readOnly="!editing"
			/>
			<FormControl
				v-model="localForm.last_name"
				:label="__('Last Name')"
				:readOnly="!editing"
			/>
			<FormControl
				v-model="localForm.full_name"
				:label="__('Full Name')"
				:readOnly="!editing"
			/>
			<FormControl v-model="localForm.email" :label="__('Email')" :readOnly="!editing" />
			<FormControl v-model="localForm.phone" :label="__('Phone')" :readOnly="!editing" />

			<FormControl
				v-if="!editing"
				v-model="localForm.citizenship"
				:label="__('Citizenship')"
				type="text"
				:readOnly="true"
			/>
			<FormControl
				v-if="editing"
				v-model="localForm.citizenship"
				:label="__('Citizenship')"
				type="select"
				:options="citizenshipOptions"
				:readOnly="!editing"
				:required="true"
			/>

			<FormControl
				v-if="localForm.citizenship === 'Citizen'"
				v-model="localForm.id_number"
				:label="__('ID Number')"
				:readOnly="!editing"
			/>
			<Link
				v-if="localForm.citizenship !== 'Citizen'"
				doctype="Country"
				v-model="localForm.country_of_citizenship"
				:label="__('Country of Citizenship')"
				:readOnly="!editing"
			/>
			<FormControl
				v-if="localForm.citizenship !== 'Citizen'"
				v-model="localForm.passport_number"
				:label="__('Passport Number')"
				:readOnly="!editing"
			/>

			<FormControl
				v-model="localForm.birth_date"
				:label="__('Date of Birth')"
				type="date"
				:readOnly="!editing"
			/>
			<FormControl
				v-if="!editing"
				v-model="localForm.marital_status"
				:label="__('Marital Status')"
				type="text"
				:readOnly="true"
			/>
			<FormControl
				v-if="editing"
				v-model="localForm.marital_status"
				:label="__('Marital Status')"
				:readOnly="!editing"
				type="select"
				:options="maritalOptions"
			/>
			<FormControl
				v-model="localForm.number_of_dependants"
				:label="__('Number of Dependants')"
				:readOnly="!editing"
			/>

			<MultiSelect
				v-model="localForm.languages"
				doctype="Volunteer Language"
				:label="__('Languages')"
				:readOnly="!editing"
			/>
		</div>

		<h2 class="text-xl font-semibold border-t pt-6 mt-6">{{ __("Contact & Location") }}</h2>
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			<Link
				doctype="County"
				v-model="localForm.county"
				:label="__('County')"
				:readOnly="!editing"
			/>
			<Link
				v-if="localForm.county"
				doctype="Sub County"
				v-model="localForm.sub_county"
				:label="__('Sub County')"
				:readOnly="!editing"
				:filters="{ county: localForm.county }"
			/>
			<FormControl
				v-model="localForm.ward"
				:label="__('Ward')"
				:readOnly="!editing"
				type="text"
			/>
			<Link
				v-if="localForm.sub_county"
				doctype="Administrative Location"
				v-model="localForm.administrative_location"
				:label="__('Location')"
				:readOnly="!editing"
				:filters="{ sub_county: localForm.sub_county }"
			/>
			<FormControl
				v-if="!editing"
				v-model="localForm.access_to_internet"
				:label="__('Access to Internet')"
				type="text"
				:readOnly="true"
			/>
			<FormControl
				v-if="editing"
				v-model="localForm.access_to_internet"
				:label="__('Access to Internet')"
				type="select"
				:options="internetOptions"
				:readOnly="!editing"
			/>
		</div>
	</div>
</template>

<script setup>
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import { FormControl, createResource, toast } from "frappe-ui";
import { reactive, ref, watch } from "vue";

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

const editing = ref(false);
const saveInProgress = ref(false);
const originalFormData = ref({});

const localForm = reactive({
	first_name: "",
	middle_name: "",
	last_name: "",
	full_name: "",
	email: "",
	phone: "",
	id_number: "",
	passport_number: "",
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
});

watch(
	() => props.form,
	(newForm) => {
		Object.keys(localForm).forEach((key) => {
			if (newForm[key] !== undefined) {
				localForm[key] = newForm[key];
			}
		});

		if (!editing.value) {
			originalFormData.value = JSON.parse(JSON.stringify(localForm));
		}
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

const saveUserResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.update_user_details",
	makeParams() {
		const payload = getChangedFields();
		return payload;
	},
	onSuccess(data) {
		toast.success("Personal information saved successfully");

		originalFormData.value = JSON.parse(JSON.stringify(localForm));
		editing.value = false;
		saveInProgress.value = false;

		emit("saved", localForm);
	},
	onError(err) {
		console.error("Save error:", err);
		toast.error(err.message || "Failed to save personal information");
		saveInProgress.value = false;
	},
});

async function handleEditToggle() {
	if (editing.value) {
		const changes = getChangedFields();

		if (Object.keys(changes).length === 0) {
			toast.info("No changes to save");
			editing.value = false;
			return;
		}

		saveInProgress.value = true;
		await saveUserResource.submit();
	} else {
		editing.value = true;

		originalFormData.value = JSON.parse(JSON.stringify(localForm));
	}
}
</script>
