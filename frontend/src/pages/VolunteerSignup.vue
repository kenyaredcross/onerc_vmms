<template>
  <div class="">
    <h1 class="text-3xl font-bold text-center text-red-700 py-3">
      {{ __("Volunteer Signup") }}
    </h1>
  </div>

  <div v-if="!isLoggedIn" class="text-center py-20">
    <LogIn class="w-16 h-16 text-gray-400 mx-auto mb-4" />
    <h2 class="text-3xl font-bold text-gray-900 mb-4">Login Required</h2>
    <p class="text-gray-600 mb-8">
      Please log in to submit your volunteer application.
    </p>
    <Button
      variant="solid"
      class="bg-red-600 hover:bg-red-700 text-white"
      @click="redirectToLogin"
    >
      <template #prefix>
        <LogIn class="w-4 h-4" />
      </template>
      {{ __("Login to Continue") }}
    </Button>
  </div>

  <div
    v-else-if="alreadyApplied && applicationStatus !== 'Draft'"
    class="text-center py-10"
  >
    <PendingApproval />
  </div>

  <div
    v-else-if="
      !alreadyApplied || (alreadyApplied && applicationStatus === 'Draft')
    "
    class="min-h-screen flex flex-col"
  >
    <main class="flex-1 container mx-auto px-4 py-4">
      <div class="bg-white shadow-lg rounded p-6">
        <div class="w-full mb-10">
          <div
            v-if="alreadyApplied && applicationStatus === 'Draft'"
            class="text-center mb-6"
          >
            <h2 class="text-xl font-semibold text-orange-600">
              Continue Your Draft Application
            </h2>
            <p class="text-gray-600 text-sm">
              Complete and submit your volunteer application
            </p>
          </div>

          <div class="flex items-center justify-between relative">
            <div
              v-for="(step, i) in steps"
              :key="i"
              class="flex-1 flex flex-col items-center text-center relative group cursor-pointer"
            >
              <div
                v-if="i < steps.length"
                class="absolute top-6 w-full h-1 -translate-y-1/2"
                :class="i < currentStep ? 'bg-red-600' : 'bg-gray-300'"
              ></div>

              <div
                class="relative flex items-center justify-center w-12 h-12 rounded-full border-2 transition-all duration-300 ease-in-out"
                :class="[
                  i < currentStep
                    ? 'bg-red-600 border-red-600 text-white shadow-md hover:shadow-lg'
                    : i === currentStep
                      ? 'bg-white border-red-600 text-red-600 font-bold shadow-lg scale-110 ring-4 ring-red-100'
                      : 'bg-gray-200 border-gray-300 text-gray-500 hover:border-gray-400 hover:bg-gray-300',
                ]"
              >
                <span class="text-lg">{{ i + 1 }}</span>
              </div>
            </div>
          </div>
        </div>

        <section v-if="currentStep === 0">
          <StepOrganization
            v-model="form"
            :errors="errors"
            @update:errors="handleErrorsUpdate"
            @change="trackChanges"
          />
        </section>
        <section v-if="currentStep === 1">
          <StepAdditional
            v-model="form"
            :errors="errors"
            @update:errors="handleErrorsUpdate"
            @change="trackChanges"
          />
        </section>
        <section v-if="currentStep === 2">
          <StepDocuments
            v-model="form"
            :documents="documents"
            :errors="errors"
            @change="trackChanges"
          />
        </section>
        <section v-if="currentStep === 3">
          <ReviewApplication :form="form" />
        </section>

        <div class="flex justify-between items-center gap-4 mt-10">
          <div>
            <span
              v-if="hasUnsavedChanges"
              class="text-sm text-orange-600 font-medium"
            >
            </span>
          </div>
          <div class="flex gap-4">
            <Button v-if="currentStep > 0" @click="prevStep">
              {{ __("Back") }}
            </Button>
            <Button
              v-if="currentStep < steps.length - 1"
              @click="nextStep"
              variant="solid"
              :loading="saveInProgress"
            >
              {{ __("Save & Continue") }}
            </Button>
            <Button
              v-if="currentStep === steps.length - 1"
              class="bg-red-700 text-white"
              variant="solid"
              :loading="saveInProgress"
              @click="showSubmitDialog = true"
            >
              {{ __("Submit Application") }}
            </Button>
          </div>
        </div>
      </div>
    </main>
  </div>

  <!-- Submit Confirmation Dialog -->
  <Dialog v-model="showSubmitDialog">
    <template #body-title>
      <h2 class="text-lg font-bold text-gray-900">
        {{ __("Confirm Submission") }}
      </h2>
    </template>

    <template #body-content>
      <p class="text-gray-700 leading-relaxed">
        {{ __("Are you sure you want to submit this application?") }}
      </p>
      <p class="mt-2 text-sm text-red-600 font-medium">
        {{ __("You won't be able to make further edits after submission.") }}
      </p>
    </template>

    <template #actions>
      <div class="flex flex-col gap-3 sm:flex-row sm:justify-end">
        <Button
          variant="outline"
          class="w-full sm:w-auto py-3"
          @click="showSubmitDialog = false"
        >
          {{ __("Cancel") }}
        </Button>
        <Button
          variant="solid"
          class="w-full sm:w-auto bg-red-700 hover:bg-red-800 text-white py-3"
          @click="confirmSubmit"
        >
          <template #prefix>
            <FeatherIcon name="check-circle" class="w-4" />
          </template>
          {{ __("Submit") }}
        </Button>
      </div>
    </template>
  </Dialog>

  <ErrorModal v-model="showErrorDialog" :errors="flatErrors" />
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from "vue";
import { Button, toast, createResource, Dialog } from "frappe-ui";
import { LogIn, FeatherIcon } from "lucide-vue-next";
import PendingApproval from "@/components/PendingApproval.vue";
import StepOrganization from "@/components/Signup/StepOrganization.vue";
import StepAdditional from "@/components/Signup/StepAdditional.vue";
import StepDocuments from "@/components/Signup/StepDocuments.vue";
import { usersStore } from "../stores/user";
import { sessionStore } from "../stores/session";
import { useRouter } from "vue-router";
import ReviewApplication from "../components/Signup/ReviewApplication.vue";
import ErrorModal from "../components/Modals/ErrorModal.vue";

const { userResource } = usersStore();
const { isLoggedIn } = sessionStore();
const user = userResource;
const router = useRouter();

const currentStep = ref(0);
const steps = [
  { title: "Organization & Personal Info" },
  { title: "Additional Info" },
  { title: "Documents" },
  { title: "Review & Submit" },
];

const applicationId = ref(null);
const alreadyApplied = ref(false);
const applicationStatus = ref(null);
const documents = ref([]);
const saveInProgress = ref(false);
const showSubmitDialog = ref(false);
const showErrorDialog = ref(false);

const originalFormData = ref({});
const hasUnsavedChanges = ref(false);
const changedFields = ref(new Set());
const flatErrors = ref("");

const form = reactive({
  company: "",
  mpesa_mobile_phone: "",
  date_of_birth: "",
  id_number: "",
  passport_number: "",
  administrative_location: "",
  sub_county: "",
  citizenship: "",
  marital_status: "",
  education: "",
  profession: "",
  access_to_internet: "",
  citizenship: "",
  number_of_dependants: null,
  reason_to_join_krcs: "",
  disabilities: "",
  has_insurance: "",
  languages: [],
  driving_licence: [],
  licences: [],
  blood_group: "",
  certification: [],
  supporting_documents: [],
  courses: [],
  additional_skills: "",
  county: "",
  ward: "",
  profile_photo: null,
  _current_step: 0,
  _current_progress: 0,
});

const errors = reactive({});

const stepFields = {
  0: [
    "company",
    "ward",
    "date_of_birth",
    "id_number",
    "passport_number",
    "mpesa_mobile_phone",
    "number_of_dependants",
    "marital_status",
    "blood_group",
    "has_insurance",
    "citizenship",
    "administrative_location",
    "sub_county",
    "county",
  ],
  1: [
    "access_to_internet",
    "profession",
    "languages",
    "education",
    "disabilities",
    "reason_to_join_krcs",
    "driving_licence",
    "certification",
    "licences",
    "additional_skills",
    "courses",
  ],
  2: ["profile_photo", "supporting_documents"],
};

const progressPercentage = computed(() => {
  const totalSteps = steps.length;
  const baseProgress = (currentStep.value / totalSteps) * 100;

  const currentStepFields = stepFields[currentStep.value] || [];
  let filledFields = 0;

  currentStepFields.forEach((field) => {
    const value = form[field];
    if (value && (Array.isArray(value) ? value.length > 0 : value !== "")) {
      filledFields++;
    }
  });

  const currentStepProgress =
    currentStepFields.length > 0
      ? (filledFields / currentStepFields.length) * (100 / totalSteps)
      : 0;

  return Math.min(baseProgress + currentStepProgress, 100);
});

function trackChanges(field) {
  const currentValue = JSON.stringify(form[field]);
  const originalValue = JSON.stringify(originalFormData.value[field]);

  if (currentValue !== originalValue) {
    changedFields.value.add(field);
    hasUnsavedChanges.value = true;
  } else {
    changedFields.value.delete(field);
    hasUnsavedChanges.value = changedFields.value.size > 0;
  }
}

watch(
  form,
  () => {
    Object.keys(form).forEach((key) => {
      if (!key.startsWith("_")) {
        trackChanges(key);
      }
    });
  },
  { deep: true }
);

function getCurrentStepData(onlyChanges = false) {
  const currentStepData = {};
  const currentStepFieldList = stepFields[currentStep.value] || [];

  currentStepFieldList.forEach((field) => {
    if (onlyChanges && !changedFields.value.has(field)) {
      return;
    }

    if (field === "documents") {
      currentStepData.documents = documents.value;
    } else {
      currentStepData[field] = form[field];
    }
  });

  currentStepData.is_volunteer = true;
  currentStepData._current_step = currentStep.value;
  currentStepData._current_progress = Math.round(progressPercentage.value);

  if (user.data?.email) {
    currentStepData.email_id = user.data.email;
  }

  return currentStepData;
}

const jobApplication = createResource({
  url: "non_profit.non_profit.api.search_doctype",
  makeParams() {
    return {
      doctype: "Job Applicant",
      filters: {
        email_id: user.data?.email,
        is_volunteer: true,
      },
      first: true,
    };
  },
  auto: true,
  reloadOn: () => !!user.data?.email,
  onSuccess(data) {
    if (data?.name) {
      const application = data;

      alreadyApplied.value = true;
      applicationStatus.value =
        application.status || application.workflow_state;
      applicationId.value = application.name;

      if (applicationStatus.value === "Draft") {
        populateForm(application);
      }
    } else {
      form.email_id = user.data?.email || "";
    }
  },
});

const submitApplicationResource = createResource({
  url: "non_profit.non_profit.api.submit_job_application",
  makeParams() {
    return {
      id: applicationId.value,
    };
  },
});

const confirmSubmit = async () => {
  submitApplicationResource.submit(
    {},
    {
      onSuccess: () => {
        toast.success("Application submitted successfully");
        showSubmitDialog.value = false;
        alreadyApplied.value = true;
        hasUnsavedChanges.value = false;
        changedFields.value.clear();
        window.location.hash = "";
      },
      onError: (err) => {
        toast.error(err.messages?.[0] || "Submission failed");
      },
    }
  );
};

const createApplication = createResource({
  url: "non_profit.non_profit.api.create_job_application",
  makeParams() {
    return getCurrentStepData(false);
  },
  onSuccess(data) {
    applicationId.value = data.name;
    toast.success("Application saved successfully");
    saveInProgress.value = false;

    updateOriginalData();
    hasUnsavedChanges.value = false;
    changedFields.value.clear();
  },
  onError(error) {
    console.error("Create application error:", error);
    toast.error("Failed to save application");
    saveInProgress.value = false;
  },
});

const updateApplication = createResource({
  url: "non_profit.non_profit.api.update_job_application",
  makeParams() {
    const stepData = getCurrentStepData(true);
    return {
      id: applicationId.value,
      ...stepData,
    };
  },
  onSuccess(data) {
    toast.success("Application updated successfully");
    saveInProgress.value = false;

    updateOriginalData();
    hasUnsavedChanges.value = false;
    changedFields.value.clear();
  },
  onError(error) {
    console.error("Update application error:", error);
    toast.error("Failed to update application");
    saveInProgress.value = false;
  },
});

function populateForm(data) {
  Object.keys(form).forEach((key) => {
    if (data[key] !== undefined && data[key] !== null) {
      form[key] = data[key];
    }
  });

  if (data.languages && Array.isArray(data.languages)) {
    form.languages = data.languages;
  }
  if (data.driving_licence && Array.isArray(data.driving_licence)) {
    form.driving_licence = data.driving_licence;
  }
  if (data.licences && Array.isArray(data.licences)) {
    form.licences = data.licences;
  }

  if (data.documents && Array.isArray(data.documents)) {
    documents.value = data.documents;
  }

  updateOriginalData();
}

function updateOriginalData() {
  originalFormData.value = JSON.parse(JSON.stringify(form));
}

function redirectToLogin() {
  router.push("/login");
}

function handleErrorsUpdate(newErrors = {}) {
  Object.keys(errors).forEach((k) => delete errors[k]);

  Object.entries(newErrors || {}).forEach(([k, v]) => {
    let normalized;

    if (v instanceof Map) {
      normalized = Object.fromEntries(v);
    } else if (typeof v === "object" && v !== null) {
      normalized = JSON.parse(JSON.stringify(v));
    } else {
      normalized = v;
    }

    if (
      normalized &&
      (typeof normalized !== "object" || Object.keys(normalized).length > 0)
    ) {
      errors[k] = normalized;
    }
  });
}

function validateStep(stepIndex) {
  let valid = true;

  if (flatErrors.value) {
    console.log("Validation failed due to existing errors:", flatErrors.value);

    return false;
  }

  // Object.keys(errors).forEach((k) => (errors[k] = ""));

  // if (stepIndex === 0) {
  //   if (!form.company) {
  //     errors.company = __("Branch is required");
  //     valid = false;
  //   }

  //   if (form.mpesa_mobile_phone) {
  //     const phone = form.mpesa_mobile_phone.toString().replace(/\s+/g, "");
  //     const phoneRegex = /^(?:\+254|0)(7\d{8}|1\d{8})$/;
  //     if (!phoneRegex.test(phone)) {
  //       errors.mpesa_mobile_phone = __("Enter a valid phone number");
  //       valid = false;
  //     }
  //   }

  //   if (!form.administrative_location) {
  //     errors.administrative_location = __("This field is required");
  //     valid = false;
  //   }
  //   if (!form.sub_county) {
  //     errors.sub_county = __("This field is required");
  //     valid = false;
  //   }
  //   if (!form.citizenship) {
  //     errors.citizenship = __("This field is required");
  //     valid = false;
  //   }

  //   if (!form.date_of_birth) {
  //     errors.date_of_birth = __("Date of birth is required");
  //     valid = false;
  //   } else {
  //     const dob = new Date(form.date_of_birth);
  //     const today = new Date();
  //     let age = today.getFullYear() - dob.getFullYear();
  //     const m = today.getMonth() - dob.getMonth();
  //     if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) {
  //       age--;
  //     }

  //     if (age < 7 || age > 100) {
  //       errors.date_of_birth = __("Age must be between 7 and 100 years");
  //       valid = false;
  //     }
  //   }

  //   if (!form.id_number && !form.passport_number) {
  //     errors.id_number = __("Passport or ID number is required");
  //     valid = false;
  //   }

  //   if (form.id_number && !/^\d{7,9}$/.test(form.id_number)) {
  //     errors.id_number = __("ID number must be 7–9 digits");
  //     valid = false;
  //   }

  //   if (
  //     form.passport_number &&
  //     !/^[A-Z0-9]{6,9}$/i.test(form.passport_number)
  //   ) {
  //     errors.passport_number = __("Invalid passport number format");
  //     valid = false;
  //   }
  // }

  // if (stepIndex === 1) {
  //   if (!form.reason_to_join_krcs) {
  //     errors.reason_to_join_krcs = __("This field is required");
  //     valid = false;
  //   }
  //   if (!form.profession) {
  //     errors.profession = __("This field is required");
  //     valid = false;
  //   }
  //   if (!form.access_to_internet) {
  //     errors.access_to_internet = __("This field is required");
  //     valid = false;
  //   }
  // }

  return valid;
}

async function saveApplication() {
  if (!hasUnsavedChanges.value && applicationId.value) {
    return;
  }

  saveInProgress.value = true;

  try {
    if (!applicationId.value) {
      await createApplication.submit();
    } else {
      await updateApplication.submit();
    }
  } catch (error) {
    console.error("Save error:", error);
    saveInProgress.value = false;
  }
}

function updateHash(step) {
  window.location.hash = `step-${step + 1}`;
}

function readHashAndNavigate() {
  const hash = window.location.hash.slice(1);
  const match = hash.match(/step-(\d+)/);

  if (match) {
    const step = parseInt(match[1]) - 1;
    if (step >= 0 && step < steps.length) {
      currentStep.value = step;
    }
  }
}

function goToStep(stepIndex) {
  if (stepIndex === currentStep.value) return;

  if (stepIndex < currentStep.value) {
    currentStep.value = stepIndex;
    updateHash(stepIndex);
    return;
  }

  if (!validateStep(currentStep.value)) {
    showErrorDialog.value = true;
    return;
  }

  let canProceed = true;
  for (let i = currentStep.value; i < stepIndex; i++) {
    if (!validateStep(i)) {
      canProceed = false;
      showErrorDialog.value = true;
      break;
    }
  }

  if (canProceed) {
    currentStep.value = stepIndex;
    updateHash(stepIndex);
  }
}

async function nextStep() {
  if (!validateStep(currentStep.value)) {
    showErrorDialog.value = true;
    return;
  }

  await saveApplication();

  if (!saveInProgress.value && currentStep.value < steps.length - 1) {
    currentStep.value++;
    updateHash(currentStep.value);
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--;
    updateHash(currentStep.value);
  }
}

function handleHashChange() {
  readHashAndNavigate();
}

onMounted(() => {
  readHashAndNavigate();
  window.addEventListener("hashchange", handleHashChange);
  updateOriginalData();
});

onUnmounted(() => {
  window.removeEventListener("hashchange", handleHashChange);
});

watch(currentStep, (newStep) => {
  form._current_step = newStep;
  form._current_progress = Math.round(progressPercentage.value);
});

watch(
  errors,
  (newErrors) => {
    const stepErrors = newErrors[currentStep.value] || {};
    flatErrors.value = Object.keys(stepErrors).length > 0 ? stepErrors : null;
  },
  { deep: true, immediate: true }
);
</script>
