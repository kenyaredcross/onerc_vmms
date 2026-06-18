<template>
	<div class="space-y-6">
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
			<FormControl
				v-model="form.phone_number"
				:label="__('Phone Number')"
				type="tel"
				required
			/>

			<FormControl v-model="form.email_id" :label="__('Email Address')" required />

			<FormControl
				v-model="form.citizenship"
				:label="__('Citizenship')"
				type="select"
				:options="citizenshipOptions.map((opt) => ({ ...opt, label: __(opt.label) }))"
				required
			/>

			<Link
				doctype="Country"
				v-model="form.country_of_citizenship"
				:label="__('Country of Citizenship')"
				:filters="
					form.citizenship === 'Citizen'
						? [['name', '=', 'Gambia']]
						: [['name', '!=', 'Gambia']]
				"
				:required="true"
			/>
			<Link
				doctype="Identification Document Type"
				v-model="form.identification_type"
				:label="__('Identification Document Type')"
				:required="true"
			/>

			<FormControl v-model="form.id_number" :label="__('ID Number')" />
			<Link v-model="form.gender" :label="__('Gender')" doctype="Gender" :required="true" />
		</div>

		<h2 class="text-xl font-semibold border-t pt-6 mt-6">{{ __("Contact & Location") }}</h2>

		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			<Link doctype="County" v-model="form.county" :label="__('LGA')" />
			<Link
				v-if="form.county"
				doctype="Sub County"
				v-model="form.sub_county"
				:label="__('District')"
				:filters="{ county: form.county }"
			/>
			<Link
				doctype="Ward"
				v-model="form.ward"
				:label="__('Ward')"
				:filters="{ county: form.county }"
			/>
			<Link
				v-if="form.sub_county"
				doctype="Administrative Location"
				v-model="form.administrative_location"
				:label="__('Location')"
				:filters="{ sub_county: form.sub_county }"
			/>
			<FormControl
				v-model="form.access_to_internet"
				:label="__('Access to Internet')"
				type="select"
				:options="internetOptions.map((opt) => ({ ...opt, label: __(opt.label) }))"
			/>
		</div>
	</div>
</template>

<script setup>
import Link from "@/components/Controls/Link.vue";
import { FormControl } from "frappe-ui";

import { nextTick, onMounted, watch } from "vue";

const props = defineProps({
	form: {
		type: Object,
		required: true,
	},
});

const form = props.form;

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

watch(
	() => form.county,
	() => {
		form.sub_county = null;
		form.administrative_location = null;
		form.ward = null;
	},
);

watch(
	() => form.sub_county,
	() => {
		form.administrative_location = null;
	},
);

watch(
	() => form.citizenship,
	() => {
		form.country_of_citizenship = null;
	},
);

onMounted(async () => {
	await nextTick();
	if (form.county) form.county = form.county;
	if (form.sub_county) form.sub_county = form.sub_county;
	if (form.ward) form.ward = form.ward;
	if (form.country_of_citizenship) form.country_of_citizenship = form.country_of_citizenship;
	if (form.identification_type) form.identification_type = form.identification_type;
	if (form.gender) form.gender = form.gender;
});
</script>
