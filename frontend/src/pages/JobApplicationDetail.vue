<template>
  <div class="max-w-5xl mx-auto py-10 space-y-8">
    <div
      v-if="job.data"
      class="p-6 rounded-xl shadow-sm border border-gray-200 bg-gradient-to-r from-red-50 to-white"
    >
      <div class="flex items-start gap-4">
        <div>
          <img
            v-if="job.data.company_logo"
            :src="job.data.company_logo"
            class="w-16 h-16 rounded-lg object-contain cursor-pointer bg-gray-50 border"
            :alt="job.data.company"
            @click="redirectToWebsite(job.data.company_website)"
          />
          <div
            v-else
            class="w-16 h-16 flex items-center justify-center rounded-lg bg-red-100 text-red-700 font-semibold text-xl cursor-default"
          >
            {{ getCompanyAbbr(job.data.company) }}
          </div>
        </div>
        <div>
          <h1 class="text-3xl font-bold text-gray-900 mb-1">
            {{ job.data.job_title }}
          </h1>
          <div class="text-lg font-medium text-red-600">
            {{ job.data.company }}
          </div>
          <div
            v-if="job.data.location || job.data.country"
            class="text-sm text-gray-500 mt-1"
          >
            {{ job.data.location
            }}<span v-if="job.data.country">, {{ job.data.country }}</span>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="!loading"
      class="bg-white rounded-xl shadow-sm p-6 border border-gray-200"
    >
      <h2 class="text-2xl font-bold text-red-700 mb-6">
        Apply for this Opportunity
      </h2>

      <div
        class="flex overflow-x-auto border-b border-gray-200 whitespace-nowrap mb-8 -mx-6 px-6 sm:mx-0 sm:px-0"
      >
        <button
          v-for="(step, index) in filteredSteps"
          :key="index"
          @click="goToStep(step.originalIndex)"
          :disabled="step.originalIndex > maxCompletedStep + 1 && !isSubmitted"
          :class="[
            'py-3 px-3 sm:px-5 text-sm sm:text-base font-semibold transition-all duration-200 ease-in-out flex-shrink-0 flex items-center gap-2',
            currentStep === step.originalIndex
              ? 'border-b-4 border-red-600 text-red-700 bg-red-50/50'
              : step.originalIndex <= maxCompletedStep && !isSubmitted
                ? 'text-green-600 hover:text-red-500 hover:border-b-4 hover:border-red-100'
                : isSubmitted
                  ? 'text-red-700'
                  : 'text-gray-400 cursor-not-allowed',
          ]"
        >
          <svg
            v-if="step.originalIndex <= maxCompletedStep && !isSubmitted"
            class="w-4 h-4 text-green-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M5 13l4 4L19 7"
            ></path>
          </svg>
          {{ step.title }}
        </button>
      </div>

      <div
        class="space-y-10 min-h-[300px] bg-gray-50 rounded-xl p-6 border border-gray-200"
      >
        <component
          :is="steps[currentStep].component"
          v-bind="{
            form,
            job: job.data,
            user: userDetails,

            isReadonly: isSubmitted,
          }"
        />
      </div>

      <div
        v-if="!isSubmitted"
        class="flex justify-between mt-6 pt-4 border-t border-gray-100"
      >
        <Button
          v-if="currentStep > 0"
          variant="subtle"
          @click="prevStep"
          class="text-gray-700 hover:bg-gray-100"
        >
          &larr; Back
        </Button>

        <div class="flex-grow"></div>

        <Button
          variant="solid"
          :loading="isSaving"
          @click="handleStepAction"
          class="!bg-red-700 hover:bg-red-800 text-white px-6 py-3 rounded-lg ml-auto"
        >
          {{
            currentStep < steps.length - 1
              ? "Save & Continue"
              : "Submit Application"
          }}
        </Button>
      </div>

      <div
        v-else
        class="mt-6 pt-4 border-t border-gray-100 text-lg font-medium text-gray-700"
      >
        <div class="text-center py-4">
          <div
            class="mb-2 text-emerald-600 font-semibold flex items-center justify-center"
          >
            <svg
              class="w-5 h-5 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              ></path>
            </svg>
            Application Successfully Submitted
          </div>
          <p class="text-gray-600">
            Thank you for your application. You can review your submitted
            details here.
          </p>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-20 text-gray-500">
      Loading application details...
    </div>
  </div>
</template>

<script setup>
import { ref, inject, markRaw, watch, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, toast, createResource } from "frappe-ui";

import PersonalInfo from "@/components/Application/PersonalInfo.vue";
import EducationBackground from "@/components/Application/EducationBackground.vue";
import WorkExperience from "@/components/Application/WorkExperience.vue";
import AdditionalInformation from "@/components/Application/AdditionalInformation.vue";
import ApplicationReview from "@/components/Application/ApplicationReview.vue";

const route = useRoute();
const router = useRouter();
const user = inject("$user");

const jobId = route.params?.id || "";
const loading = ref(true);
const currentStep = ref(0);
const maxCompletedStep = ref(-1);
const isSaving = ref(false);

const steps = [
  {
    hash: "#info",
    title: "Personal Info",
    component: markRaw(PersonalInfo),
    validate: (f) => true,
  },
  {
    hash: "#education",
    title: "Education & Qualifications",
    component: markRaw(EducationBackground),
    validate: () => true,
  },
  {
    hash: "#experience",
    title: "Work Experience",
    component: markRaw(WorkExperience),
    validate: () => true,
  },
  {
    hash: "#additional",
    title: "Additional Information",
    component: markRaw(AdditionalInformation),
    validate: () => true,
  },
  {
    hash: "#review",
    title: "Review & Submit",
    component: markRaw(ApplicationReview),
    validate: () => true,
  },
];

const form = ref({});
const resume = ref(null);
const documents = ref([]);
const userDetails = ref({});

const isSubmitted = computed(() => {
  return (
    opportunityApplication.data?.status &&
    opportunityApplication.data.status !== "Draft"
  );
});

const filteredSteps = computed(() => {
  if (isSubmitted.value) {
    const reviewStepIndex = steps.findIndex((s) => s.hash === "#review");
    const reviewStep = steps[reviewStepIndex];
    return [{ ...reviewStep, originalIndex: reviewStepIndex }];
  }

  return steps.map((s, index) => ({ ...s, originalIndex: index }));
});

const userDetailsResource = createResource({
  url: "non_profit.non_profit.api.get_user_details",
  auto: true,
  onSuccess(data) {
    if (data) {
      userDetails.value = data;
      populateForm(data);
    }
    loading.value = false;
  },
  onError(err) {
    toast.error(err.message || "Failed to fetch user details");
    loading.value = false;
  },
});

const opportunityApplication = createResource({
  url: "non_profit.non_profit.api.get_job_application",
  params: { name: jobId },
  auto: true,
  onSuccess(data) {
    if (data) {
      populateForm(data, true);
      form.value.job_application_id = data.name;
      resume.value = data.resume || null;
      documents.value = data.documents || [];

      if (data.job_title) {
        job.update({ params: { job: data.job_title } });
      }

      if (data.status && data.status !== "Draft") {
        const reviewIndex = steps.findIndex((s) => s.hash === "#review");
        if (reviewIndex !== -1) {
          currentStep.value = reviewIndex;
          router.replace({ hash: steps[reviewIndex].hash });
        }
      }
    }
  },
  onError(err) {
    toast.error(err.message || "Failed to fetch application details");
    loading.value = false;
  },
});

const job = createResource({
  url: "non_profit.non_profit.api.get_job_details",
  params: { job: jobId },
  cache: ["job", jobId],
  onSuccess(data) {
    if (!data) {
      toast.error("Job not found");
      router.replace({ name: "JobListings" });
    }
  },
  onError(err) {
    toast.error(err.message || "Failed to fetch job details");
    router.replace({ name: "JobListings" });
  },
  auto: false,
});

const applicationSave = createResource({
  url: "non_profit.non_profit.api.update_job_application",
});

const submitApplicationResource = createResource({
  url: "non_profit.non_profit.api.submit_job_application",
  makeParams() {
    return {
      id: jobId,
    };
  },
});

function populateForm(data = {}, isApplication = false) {
  const src = isApplication ? "application" : "user";
  const user = userDetails.value || {};

  const fieldMap = {
    surname: ["surname", "last_name"],
    other_names: ["other_names", "first_name"],
    email_id: ["email_id", "email"],
    phone: ["phone", "mobile", "contact"],
    cover_letter: ["cover_letter"],
  };

  for (const key in fieldMap) {
    let value =
      data[key] ||
      fieldMap[key]
        .map((alt) => data[alt])
        .find((v) => v !== undefined && v !== null) ||
      form.value[key];

    if (
      (value === undefined || value === null || value === "") &&
      src === "user"
    ) {
      value =
        user[key] ||
        fieldMap[key]
          .map((alt) => user[alt])
          .find((v) => v !== undefined && v !== null) ||
        "";
    }

    form.value[key] = Array.isArray(value) ? [...value] : value;
  }

  const source = src === "user" ? user : data;
  for (const key in source) {
    const value = source[key];

    if (
      form.value[key] === undefined ||
      form.value[key] === null ||
      form.value[key] === "" ||
      (Array.isArray(form.value[key]) && form.value[key].length === 0)
    ) {
      form.value[key] = Array.isArray(value) ? [...value] : value;
    }
  }

  if (src === "user") {
    for (const key in data) {
      if (fieldMap[key]) continue;
      if (
        form.value[key] === undefined ||
        form.value[key] === null ||
        form.value[key] === "" ||
        (Array.isArray(form.value[key]) && form.value[key].length === 0)
      ) {
        form.value[key] = Array.isArray(data[key]) ? [...data[key]] : data[key];
      }
    }
  }
}

const goToStep = (index) => {
  if (isSubmitted.value) {
    const reviewIndex = steps.findIndex((s) => s.hash === "#review");
    if (index === reviewIndex) {
      currentStep.value = index;
      router.replace({ hash: steps[index].hash });
    } else {
      toast.error(
        "This submitted application is read-only and can only view the Review tab."
      );
    }
    return;
  }

  if (index <= maxCompletedStep.value + 1) {
    currentStep.value = index;
    router.replace({ hash: steps[index].hash });
    isSaving.value = false;
  } else {
    toast.error("Please complete the previous step first.");
  }
};

const prevStep = () => {
  if (currentStep.value > 0) goToStep(currentStep.value - 1);
};

onMounted(() => {
  const initialHash = route.hash || "#info";

  const index = steps.findIndex((s) => s.hash === initialHash);
  currentStep.value = index >= 0 ? index : 0;

  if (!route.hash || route.hash !== steps[currentStep.value].hash) {
    router.replace({ hash: steps[currentStep.value].hash });
  }
});

watch(
  () => route.hash,
  (newHash) => {
    const index = steps.findIndex((s) => s.hash === newHash);
    if (index >= 0) currentStep.value = index;
  }
);

watch(
  () => opportunityApplication.data,
  (newData) => {
    if (newData && newData.job_title) {
      job.update({ params: { job: newData.job_title } });
      job.reload();
    }
  },
  { deep: true }
);

const handleStepAction = () => {
  const step = steps[currentStep.value];
  const valid = step.validate(form.value, resume.value, userDetails.value);

  if (!valid) {
    toast.error("Please complete required fields before continuing.");
    return;
  }

  if (currentStep.value < steps.length - 1) {
    saveApplicationDraft();
  } else {
    submitApplication();
  }
};

const saveApplicationDraft = () => {
  isSaving.value = true;
  applicationSave.submit(
    {
      id: jobId,
      ...form.value,
      resume: resume.value,
      documents: documents.value,
    },
    {
      onSuccess: (response) => {
        form.value.job_application_id =
          response?.name || response?.application_id;
        maxCompletedStep.value = Math.max(
          maxCompletedStep.value,
          currentStep.value
        );
        toast.success("Application stage saved successfully.");
        goToStep(currentStep.value + 1);
      },
      onError: (err) =>
        toast.error(err.messages?.[0] || "Failed to save application stage."),
      onSettled: () => (isSaving.value = false),
    }
  );
};

const submitApplication = () => {
  isSaving.value = true;
  submitApplicationResource.submit(
    {
      id: jobId,
    },
    {
      onSuccess: (response) => {
        const id = response?.name || response?.application_id;
        toast.success("Application submitted successfully.");
        router.push({ name: "JobApplicationDetail", params: { id } });
      },
      onError: (err) =>
        toast.error(err.messages?.[0] || "Failed to submit application."),
      onSettled: () => (isSaving.value = false),
    }
  );
};

const redirectToWebsite = (url) => window.open(url, "_blank");
const getCompanyAbbr = (name) =>
  name
    ? name
        .split(" ")
        .map((w) => w[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "NA";
</script>
