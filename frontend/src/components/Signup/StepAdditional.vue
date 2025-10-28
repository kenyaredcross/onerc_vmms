<template>
  <section>
    <h2 class="text-xl font-bold text-red-700 mb-4">
      {{ __("Additional Information") }}
    </h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <FormControl
          v-model="localModel.access_to_internet"
          :label="__('Access to Internet')"
          type="select"
          :required="true"
          :options="internetOptions"
        />
        <p
          v-if="errors[1]?.['Access To Internet']"
          class="text-sm text-red-600 mt-1"
        >
          {{ errors[1]?.["Access To Internet"] }}
        </p>
      </div>
      <div>
        <Link
          v-model="localModel.profession"
          :label="__('Profession')"
          :required="true"
          doctype="Profession"
        />
        <p v-if="errors[1]?.['Profession']" class="text-sm text-red-600 mt-1">
          {{ errors[1]?.["Profession"] }}
        </p>
      </div>
      <div>
        <FormControl
          v-model="localModel.reason_to_join_krcs"
          :label="__('Reason for Joining')"
          type="select"
          :required="true"
          :options="reasonsOptions"
        />
        <p
          v-if="errors[1]?.['Reason To Join Krcs']"
          class="text-sm text-red-600 mt-1"
        >
          {{ errors[1]?.["Reason To Join Krcs"] }}
        </p>
      </div>
      <div>
        <MultiSelect
          v-model="localModel.languages"
          doctype="Volunteer Language"
          :label="__('Languages')"
        />
        <p v-if="errors[1]?.['Languages']" class="text-sm text-red-600 mt-1">
          {{ errors[1]?.["Languages"] }}
        </p>
      </div>
      <div>
        <MultiSelect
          v-model="localModel.driving_licence"
          :label="__('Driving Licence')"
          doctype="Driving Licences"
        />
        <p
          v-if="errors[1]?.['Driving Licence']"
          class="text-sm text-red-600 mt-1"
        >
          {{ errors[1]?.["Driving Licence"] }}
        </p>
      </div>

      <div class="w-full md:col-span-2 space-y-6">
        <ChildTable
          v-model="localModel.disabilities"
          doctype="Employee Disability"
          label="Disabilities"
          :autoEditGrid="true"
          :field-queries="disabilityQueries"
          :form-data="localModel"
          @validationErrors="onChildErrors('Disabilities', $event)"
        />
        <ChildTable
          v-model="localModel.allergies"
          doctype="Allergy Table"
          label="Allergies"
          :autoEditGrid="true"
          :form-data="localModel"
          @validationErrors="onChildErrors('Allergies', $event)"
        />

        <ChildTable
          v-model="localModel.education"
          doctype="Employee Education"
          label="Education"
          :autoEditGrid="true"
          @validationErrors="onChildErrors('Education', $event)"
        />

        <ChildTable
          v-model="localModel.courses"
          doctype="User External Course"
          label="Trainings & Certifications"
          :autoEditGrid="true"
          @validationErrors="onChildErrors('Courses', $event)"
        />

        <ChildTable
          v-model="localModel.additional_skills"
          doctype="Additional Skill"
          label="Additional Skills"
          :autoEditGrid="true"
          @validationErrors="onChildErrors('Additional Skills', $event)"
        />

        <ChildTable
          v-model="localModel.licences"
          doctype="Personnel Licence"
          label="Licences"
          :autoEditGrid="true"
          @validationErrors="onChildErrors('Licences', $event)"
        />
      </div>
    </div>
  </section>
</template>

<script setup>
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import { FormControl } from "frappe-ui";
import { computed, onMounted, watch } from "vue";
import ChildTable from "../Controls/ChildTable.vue";

const props = defineProps({
  modelValue: { type: Object, required: true },
  errors: { type: Object, default: () => ({}) },
});

const emit = defineEmits(["update:modelValue", "update:errors"]);

const localModel = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

const requiredFields = [
  "access_to_internet",
  "profession",
  "reason_to_join_krcs",
];

const disabilityQueries = {
  disability: (row, allRows, formData) => {
    return {
      disability_category: row.disability_category || null,
    };
  },
};

function formatLabel(key) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

function validateField(fieldName) {
  const newErrors = { ...props.errors };
  if (!newErrors[1]) newErrors[1] = {};
  const label = formatLabel(fieldName);

  if (
    !localModel.value[fieldName] ||
    localModel.value[fieldName].length === 0
  ) {
    newErrors[1][label] = `${label} is required.`;
  } else {
    delete newErrors[1][label];
    if (Object.keys(newErrors[1]).length === 0) delete newErrors[1];
  }

  emit("update:errors", newErrors);
}

function onChildErrors(tableName, errMap) {
  const newErrors = { ...props.errors };
  if (!newErrors[1]) newErrors[1] = {};

  const hasErrors =
    errMap &&
    ((errMap instanceof Map && errMap.size > 0) ||
      (errMap.constructor === Object && Object.keys(errMap).length > 0));

  if (hasErrors) {
    const errObj = errMap instanceof Map ? Object.fromEntries(errMap) : errMap;
    newErrors[1][tableName] = errObj;
  } else {
    delete newErrors[1][tableName];
    if (Object.keys(newErrors[1]).length === 0) delete newErrors[1];
  }

  emit("update:errors", newErrors);
}

function validateComponentFields() {
  const clearedErrors = { ...props.errors };
  if (!clearedErrors[1]) clearedErrors[1] = {};

  requiredFields.forEach((field) => {
    const label = formatLabel(field);
    delete clearedErrors[1][label];
  });

  emit("update:errors", clearedErrors);

  requiredFields.forEach(validateField);
}

onMounted(() => {
  validateComponentFields();
});

watch(
  localModel,
  () => {
    requiredFields.forEach(validateField);
  },
  { deep: true }
);

const reasonsOptions = [
  { label: "Humanitarian", value: "Humanitarian" },
  { label: "Social Cohesion", value: "Social Cohesion" },
  { label: "Personal", value: "Personal" },
];

const internetOptions = [
  { label: "Yes", value: "Yes" },
  { label: "No", value: "No" },
  { label: "Sometimes", value: "Sometimes" },
];
</script>
