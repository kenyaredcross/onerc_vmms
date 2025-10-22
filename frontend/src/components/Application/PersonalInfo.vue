<template>
  <div class="space-y-6">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <FormControl
        v-model="form.citizenship"
        :label="__('Citizenship')"
        type="select"
        :options="citizenshipOptions"
        required
      />

      <FormControl
        v-if="form.citizenship === 'Citizen'"
        v-model="form.id_number"
        label="ID Number"
      />
      <Link
        v-if="form.citizenship !== 'Citizen'"
        doctype="Country"
        v-model="form.country_of_citizenship"
        :label="__('Country of Citizenship')"
      />
      <FormControl
        v-if="form.citizenship !== 'Citizen'"
        v-model="form.passport_number"
        label="Passport Number"
      />

      <FormControl
        v-model="form.birth_date"
        label="Date of Birth"
        type="date"
      />
      <FormControl
        v-model="form.marital_status"
        label="Marital Status"
        type="select"
        :options="maritalOptions"
      />
      <FormControl
        v-model="form.number_of_dependants"
        label="Number of Dependants"
      />

      <MultiSelect
        v-model="form.languages"
        doctype="Volunteer Language"
        label="Languages"
      />
    </div>

    <h2 class="text-xl font-semibold border-t pt-6 mt-6">Contact & Location</h2>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <Link doctype="County" v-model="form.county" label="County" />
      <Link
        v-if="form.county"
        doctype="Sub County"
        v-model="form.sub_county"
        label="Sub County"
        :filters="{ county: form.county }"
      />
      <FormControl v-model="form.ward" label="Ward" type="text" />
      <Link
        v-if="form.sub_county"
        doctype="Administrative Location"
        v-model="form.administrative_location"
        label="Location"
        :filters="{ sub_county: form.sub_county }"
      />
      <FormControl
        v-model="form.access_to_internet"
        label="Access to Internet"
        type="select"
        :options="internetOptions"
      />
    </div>
  </div>
</template>

<script setup>
import { FormControl } from "frappe-ui";
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";

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
</script>
