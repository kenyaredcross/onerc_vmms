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

    <div class="border rounded-lg shadow-sm">
      <div
        class="flex justify-between items-center p-4 cursor-pointer"
        @click="toggleCollapse('docs')"
      >
        <h2 class="text-lg font-semibold">
          Supporting Documents & Attachments
        </h2>
        <svg
          :class="{ 'rotate-180': !isCollapsed.docs }"
          class="w-5 h-5 text-gray-500 transition-transform duration-200"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </div>
      <div v-show="!isCollapsed.docs" class="p-4 pt-0 space-y-4">
        <ChildTable
          v-model="localForm.supporting_documents"
          doctype="Supporting Document"
          label="Supporting Documents"
          :autoEditGrid="false"
          :readOnly="!editing"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from "vue";
import { Button, createResource, toast } from "frappe-ui";
import ChildTable from "@/components/Controls/ChildTable.vue";

const props = defineProps({
  form: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["saved"]);

const editing = ref(false);
const saveInProgress = ref(false);
const originalFormData = ref({});

const isCollapsed = reactive({
  docs: false,
});

const localForm = reactive({
  supporting_documents: [],
  attachments: [],
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
  return JSON.stringify(localForm) !== JSON.stringify(originalFormData.value);
}

function toggleCollapse(section) {
  isCollapsed[section] = !isCollapsed[section];
}

const saveDocsResource = createResource({
  url: "non_profit.non_profit.api.update_user_details",
  makeParams() {
    return JSON.parse(JSON.stringify(localForm));
  },
  onSuccess() {
    toast.success("Documents saved successfully");
    originalFormData.value = JSON.parse(JSON.stringify(localForm));
    editing.value = false;
    saveInProgress.value = false;
    emit("saved", localForm);
  },
  onError(err) {
    console.error("Save error:", err);
    toast.error(err.message || "Failed to save documents");
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
    await saveDocsResource.submit();
  } else {
    editing.value = true;
    originalFormData.value = JSON.parse(JSON.stringify(localForm));
  }
}
</script>
