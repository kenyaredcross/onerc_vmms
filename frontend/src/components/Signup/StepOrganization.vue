<template>
  <section>
    <h2 class="text-xl font-bold text-red-700 mb-4">
      {{ __("Organization & Personal Info") }}
    </h2>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="space-y-6">
        <div>
          <Link
            v-model="localModel.company"
            :label="__('Branch / County')"
            doctype="Company"
            :required="true"
            :filters="{ is_group: 0 }"
          />
          <p
            v-if="errors[0]?.['Branch / County']"
            class="text-sm text-red-600 mt-1"
          >
            {{ errors[0]?.["Branch / County"] }}
          </p>
        </div>

        <div v-if="localModel.company">
          <Link
            v-model="localModel.sub_county"
            :label="__('Sub County')"
            doctype="Sub County"
            :required="true"
            :filters="{ county: localModel.company }"
          />
          <p v-if="errors[0]?.['Sub County']" class="text-sm text-red-600 mt-1">
            {{ errors[0]?.["Sub County"] }}
          </p>
        </div>

        <div v-if="localModel.sub_county">
          <Link
            v-model="localModel.administrative_location"
            :label="__('Location')"
            doctype="Administrative Location"
            :required="true"
            :filters="{ sub_county: localModel.sub_county }"
          />
          <p v-if="errors[0]?.['Location']" class="text-sm text-red-600 mt-1">
            {{ errors[0]?.["Location"] }}
          </p>
        </div>

        <div>
          <FormControl
            v-model="localModel.ward"
            :label="__('Ward')"
            type="text"
          />
          <p v-if="errors[0]?.['Ward']" class="text-sm text-red-600 mt-1">
            {{ errors[0]?.["Ward"] }}
          </p>
        </div>

        <div>
          <FormControl
            v-model="localModel.citizenship"
            :label="__('Citizenship')"
            type="select"
            :options="citizenshipOptions"
            :required="true"
          />
          <p
            v-if="errors[0]?.['Citizenship']"
            class="text-sm text-red-600 mt-1"
          >
            {{ errors[0]?.["Citizenship"] }}
          </p>
        </div>

        <div v-if="localModel.citizenship === 'Citizen'">
          <FormControl
            v-model="localModel.id_number"
            :label="__('National ID')"
            type="text"
          />
          <p
            v-if="errors[0]?.['National ID']"
            class="text-sm text-red-600 mt-1"
          >
            {{ errors[0]?.["National ID"] }}
          </p>
        </div>

        <div v-if="localModel.citizenship !== 'Citizen'">
          <Link
            doctype="Country"
            v-model="localModel.country_of_citizenship"
            :label="__('Country of Citizenship')"
          />
          <p
            v-if="errors[0]?.['Country of Citizenship']"
            class="text-sm text-red-600 mt-1"
          >
            {{ errors[0]?.["Country of Citizenship"] }}
          </p>
        </div>
        <div v-if="localModel.citizenship !== 'Citizen'">
          <FormControl
            v-model="localModel.passport_number"
            :label="__('Passport Number')"
            type="text"
          />
          <p
            v-if="errors[0]?.['Passport Number']"
            class="text-sm text-red-600 mt-1"
          >
            {{ errors[0]?.["Passport Number"] }}
          </p>
        </div>
      </div>

      <div class="space-y-6">
        <FormControl
          v-model="localModel.date_of_birth"
          :label="__('Date of Birth')"
          type="date"
        />
        <p
          v-if="errors[0]?.['Date of Birth']"
          class="text-sm text-red-600 mt-1"
        >
          {{ errors[0]?.["Date of Birth"] }}
        </p>

        <FormControl
          v-model="localModel.marital_status"
          :label="__('Marital Status')"
          type="select"
          :options="maritalOptions"
        />
        <p
          v-if="errors[0]?.['Marital Status']"
          class="text-sm text-red-600 mt-1"
        >
          {{ errors[0]?.["Marital Status"] }}
        </p>

        <FormControl
          v-model="localModel.number_of_dependants"
          :label="__('Number of Dependants')"
          type="number"
        />
        <p
          v-if="errors[0]?.['Number of Dependants']"
          class="text-sm text-red-600 mt-1"
        >
          {{ errors[0]?.["Number of Dependants"] }}
        </p>

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

        <FormControl
          v-model="localModel.blood_group"
          :label="__('Blood Group')"
          type="select"
          :options="bloodGroupOptions"
        />
        <p v-if="errors[0]?.['Blood Group']" class="text-sm text-red-600 mt-1">
          {{ errors[0]?.["Blood Group"] }}
        </p>

        <FormControl
          v-model="localModel.has_insurance"
          :label="__('KRCS Insurance')"
          type="select"
          :options="yesNoOptions"
        />
        <p
          v-if="errors[0]?.['KRCS Insurance']"
          class="text-sm text-red-600 mt-1"
        >
          {{ errors[0]?.["KRCS Insurance"] }}
        </p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { FormControl } from "frappe-ui";
import Link from "@/components/Controls/Link.vue";
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

  if (!form.company) stepErrors[0]["Branch / County"] = "Branch is required";
  if (!form.sub_county) stepErrors[0]["Sub County"] = "This field is required";
  if (!form.administrative_location)
    stepErrors[0]["Location"] = "This field is required";
  if (!form.citizenship)
    stepErrors[0]["Citizenship"] = "This field is required";

  if (!form.date_of_birth) {
    stepErrors[0]["Date of Birth"] = "Date of birth is required";
  } else {
    const dob = new Date(form.date_of_birth);
    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();
    const m = today.getMonth() - dob.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) age--;
    if (age < 7 || age > 100)
      stepErrors[0]["Date of Birth"] = "Age must be between 7 and 100 years";
  }

  if (!form.id_number && !form.passport_number)
    stepErrors[0]["National ID"] = "Passport or ID number is required";
  if (form.id_number && !/^\d{7,9}$/.test(form.id_number))
    stepErrors[0]["National ID"] = "ID number must be 7–9 digits";
  if (form.passport_number && !/^[A-Z0-9]{6,9}$/i.test(form.passport_number))
    stepErrors[0]["Passport Number"] = "Invalid passport number format";

  if (form.mpesa_mobile_phone) {
    const phone = form.mpesa_mobile_phone.toString().replace(/\s+/g, "");
    const phoneRegex = /^(?:\+254|0)(7\d{8}|1\d{8})$/;
    if (!phoneRegex.test(phone))
      stepErrors[0]["Mobile Money (M-Pesa) phone if different"] =
        "Enter a valid phone number";
  }

  emit("update:errors", stepErrors);

  return Object.keys(stepErrors[0]).length === 0;
}

watch(localModel, validateForm, { deep: true, immediate: true });
</script>
