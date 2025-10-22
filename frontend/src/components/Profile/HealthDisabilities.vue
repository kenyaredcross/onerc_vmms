<template>
  <div class="space-y-6">
    <div class="flex justify-end">
      <Button
        @click="handleEditToggle"
        variant="solid"
        class="px-8"
        :loading="saveInProgress"
      >
        {{ editing ? "Save" : "Edit" }}
      </Button>
    </div>

    <FormControl
      v-if="!editing"
      v-model="localForm.blood_group"
      label="Blood Group"
      type="text"
      :readOnly="true"
    />
    <FormControl
      v-if="editing"
      v-model="localForm.blood_group"
      label="Blood Group"
      :readOnly="!editing"
      type="select"
      :options="bloodGroupOptions"
    />

    <ChildTable
      v-model="localForm.allergies"
      doctype="Allergy Table"
      label="Allergies"
      :autoEditGrid="false"
      :readOnly="!editing"
    />

    <ChildTable
      v-model="localForm.disabilities"
      doctype="Employee Disability"
      label="Disabilities"
      :autoEditGrid="false"
      :readOnly="!editing"
    />
  </div>
</template>

<script setup>
import { ref, reactive, watch } from "vue";
import { Button, FormControl, createResource, toast } from "frappe-ui";
import ChildTable from "@/components/Controls/ChildTable.vue";

const props = defineProps({
  form: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["saved"]);

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

const editing = ref(false);
const saveInProgress = ref(false);
const originalFormData = ref({});

const localForm = reactive({
  blood_group: "",
  allergies: [],
  disabilities: [],
  health_information: "",
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
  { immediate: true, deep: true }
);

function hasChanges() {
  const current = JSON.stringify(localForm);
  const original = JSON.stringify(originalFormData.value);
  return current !== original;
}

const saveUserResource = createResource({
  url: "non_profit.non_profit.api.update_user_details",
  makeParams() {
    const payload = JSON.parse(JSON.stringify(localForm));

    return payload;
  },
  onSuccess(data) {
    toast.success("Health and disability information saved successfully");

    originalFormData.value = JSON.parse(JSON.stringify(localForm));
    editing.value = false;
    saveInProgress.value = false;

    emit("saved", localForm);
  },
  onError(err) {
    console.error("Save error:", err);
    toast.error(
      err.message || "Failed to save health and disability information"
    );
    saveInProgress.value = false;
  },
});

async function handleEditToggle() {
  if (editing.value) {
    if (!hasChanges()) {
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
