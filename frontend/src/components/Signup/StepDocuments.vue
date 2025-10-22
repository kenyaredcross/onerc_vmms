<template>
  <section>
    <h2 class="text-xl font-bold text-red-700 mb-4">
      {{ __("Documents ") }}
    </h2>
    <!-- <div class="grid grid-cols-1 gap-6">
      <div class="space-y-2">
        <span class="text-gray-700"> Profile Photo </span>
        <Uploader
          label="Upload Profile Photo"
          :fileTypes="['.jpg', '.png']"
          :onSuccess="(f) => (localModel.profile_photo = f)"
        />
      </div>
    </div> -->

    <div class="mt-6">
      <ChildTable
        v-model="localModel.supporting_documents"
        doctype="Supporting Document"
        :autoEditGrid="true"
        label="Supporting Documents"
        @validationErrors="onChildErrors('supporting_documents', $event)"
      />
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";
import Uploader from "@/components/Controls/Uploader.vue";
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

function onChildErrors(tableName, errMap) {
  const tableErrors = Object.fromEntries(errMap);
  const newErrors = { ...props.errors };
  if (Object.keys(tableErrors).length > 0) {
    newErrors[tableName] = tableErrors;
  } else {
    delete newErrors[tableName];
  }
  emit("update:errors", newErrors);
}
</script>
