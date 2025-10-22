<template>
  <section>
    <h2 class="text-xl font-bold text-red-700 mb-4">
      {{ __("Other Details") }}
    </h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <FormControl
        v-model="localForm.additional_skills"
        :label="__('Additional Skills')"
        type="textarea"
        :rows="4"
      />
      <FormControl v-model="localForm.ward" :label="__('Ward')" type="text" />
    </div>
  </section>
</template>

<script setup>
import { reactive, watch } from "vue";
import { FormControl } from "frappe-ui";

const props = defineProps({ modelValue: Object });
const emit = defineEmits(["update:modelValue"]);

const bloodGroups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map(
  (v) => ({ label: v, value: v })
);

const localForm = reactive({ ...props.modelValue });
watch(localForm, (val) => emit("update:modelValue", val), { deep: true });
</script>
