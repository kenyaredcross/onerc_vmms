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

    <Link
      doctype="Profession"
      v-model="localForm.profession"
      label="Profession"
      :readOnly="!editing"
      class="mt-4"
    />

    <div class="border rounded-lg shadow-sm">
      <div
        class="flex justify-between items-center p-4 cursor-pointer"
        @click="toggleCollapse('education')"
      >
        <h2 class="text-lg font-semibold">Education & Work History</h2>
        <svg
          :class="{ 'rotate-180': !isCollapsed.education }"
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
          ></path>
        </svg>
      </div>
      <div v-show="!isCollapsed.education" class="p-4 pt-0 space-y-4">
        <ChildTable
          v-model="localForm.education"
          doctype="Employee Education"
          label="Education History"
          :autoEditGrid="false"
          :readOnly="!editing"
        />
        <ChildTable
          v-model="localForm.work_experience"
          doctype="Work Experience"
          label="Work Experience"
          :autoEditGrid="false"
          :readOnly="!editing"
        />
        <ChildTable
          v-model="localForm.work_references"
          doctype="Professional Reference"
          label="Work References"
          :autoEditGrid="false"
          :readOnly="!editing"
        />
        <ChildTable
          v-model="localForm.certification"
          doctype="Certification"
          label="Certifications"
          :autoEditGrid="false"
          :readOnly="!editing"
        />
      </div>
    </div>

    <div class="border rounded-lg shadow-sm">
      <div
        class="flex justify-between items-center p-4 cursor-pointer"
        @click="toggleCollapse('skills')"
      >
        <h2 class="text-lg font-semibold">Skills & Courses</h2>
        <svg
          :class="{ 'rotate-180': !isCollapsed.skills }"
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
          ></path>
        </svg>
      </div>
      <div
        v-show="!isCollapsed.skills"
        class="p-4 pt-0 space-y-4 grid grid-cols-1 gap-4"
      >
        <ChildTable
          v-model="localForm.additional_skills"
          doctype="Additional Skill"
          label="Skills"
          :autoEditGrid="false"
          :readOnly="!editing"
        />
        <ChildTable
          v-model="localForm.courses"
          doctype="User External Course"
          label="Courses"
          :autoEditGrid="false"
          :readOnly="!editing"
        />
      </div>
    </div>

    <div class="border rounded-lg shadow-sm">
      <div
        class="flex justify-between items-center p-4 cursor-pointer"
        @click="toggleCollapse('licences')"
      >
        <h2 class="text-lg font-semibold">Licences & Driving</h2>
        <svg
          :class="{ 'rotate-180': !isCollapsed.licences }"
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
          ></path>
        </svg>
      </div>
      <div
        v-show="!isCollapsed.licences"
        class="p-4 pt-0 space-y-4 grid grid-cols-1 gap-4"
      >
        <MultiSelect
          v-model="localForm.driving_licence"
          doctype="Driving Licences"
          label="Driving Licence Classes"
          :readOnly="!editing"
        />
        <ChildTable
          v-model="localForm.licences"
          doctype="Personnel Licence"
          label="Professional Licences"
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
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";

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
  education: false,
  skills: true,
  licences: true,
});

const localForm = reactive({
  profession: null,
  education: [],
  work_experience: [],
  work_references: [],
  certification: [],
  additional_skills: [],
  courses: [],
  languages: [],
  licences: [],
  driving_licence: [],
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

function toggleCollapse(section) {
  isCollapsed[section] = !isCollapsed[section];
}

const saveUserResource = createResource({
  url: "non_profit.non_profit.api.update_user_details",
  makeParams() {
    const payload = JSON.parse(JSON.stringify(localForm));
    return payload;
  },
  onSuccess(data) {
    toast.success("education and skills saved successfully");

    originalFormData.value = JSON.parse(JSON.stringify(localForm));
    editing.value = false;
    saveInProgress.value = false;

    emit("saved", localForm);
  },
  onError(err) {
    console.error("Save error:", err);
    toast.error(err.message || "Failed to save education and skills");
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
