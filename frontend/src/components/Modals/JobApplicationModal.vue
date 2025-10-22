<template>
  <div v-if="alreadyApplied" class="text-center py-10">
    <PendingApproval />
  </div>
  <div v-else class="min-h-screen flex flex-col">
    <main class="flex-1 container mx-auto px-6 py-10">
      <div class="bg-white shadow-lg rounded-2xl p-8">
        <div v-if="loading" class="text-center py-10">
          <p>{{ __("Loading application...") }}</p>
        </div>

        <div v-else>
          <section class="mb-8">
            <h1
              class="text-xl uppercase font-bold mb-4 text-center text-red-700"
            >
              Volunteer Signup
            </h1>
            <h2 class="text-xl font-bold text-red-700 mb-4">
              {{ __("Organization") }}
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Link
                v-model="form.company"
                :label="__('Branch')"
                doctype="Company"
                :required="true"
                :filters="{ is_group: 0 }"
              />
            </div>
          </section>

          <section
            v-if="!showOnlyDocsProfile && !props.showOnlyDocs"
            class="mb-10"
          >
            <h2 class="text-xl font-bold text-red-700 mb-4">
              {{ __("Personal Information") }}
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <FormControl
                v-model="form.surname"
                :label="__('Surname')"
                type="text"
                :required="isPersonalInfoRequired"
                v-if="!hidePersonalInfo"
              />
              <FormControl
                v-model="form.other_names"
                :label="__('Other Names')"
                type="text"
                :required="isPersonalInfoRequired"
                v-if="!hidePersonalInfo"
              />
              <FormControl
                v-model="form.email_id"
                :label="__('Email Address')"
                type="email"
                :disabled="true"
                :required="isPersonalInfoRequired"
                v-if="!hidePersonalInfo"
              />
              <FormControl
                v-model="form.phone"
                :label="__('Phone Number')"
                type="tel"
                :required="isPersonalInfoRequired"
                v-if="!hidePersonalInfo"
              />
              <Link
                v-model="form.gender"
                :label="__('Gender')"
                doctype="Gender"
                :required="isPersonalInfoRequired"
              />
              <FormControl
                v-model="form.date_of_birth"
                :label="__('Date of Birth')"
                type="date"
                :required="isPersonalInfoRequired"
              />
              <FormControl
                v-model="form.idpassport_number"
                :label="__('ID/Passport Number')"
                type="text"
                :required="isPersonalInfoRequired"
              />
              <FormControl
                v-model="form.mpesa_mobile_phone"
                :label="__('MPESA Mobile Phone (if different)')"
                type="tel"
              />
            </div>
          </section>

          <section v-if="!props.showOnlyDocsProfile" class="mb-10">
            <h2 class="text-xl font-bold text-red-700 mb-4">
              {{ __("Additional Information") }}
            </h2>
            <div
              class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-4"
            >
              <FormControl
                v-model="form.marital_status"
                :label="__('Marital Status')"
                type="select"
                :options="maritalOptions"
              />
              <FormControl
                v-model="form.highest_level_of_education"
                :label="__('Highest Level of Education')"
                type="select"
                :options="educationOptions"
              />
              <FormControl
                v-model="form.profession"
                :label="__('Profession')"
                type="text"
              />
              <FormControl
                v-model="form.place_of_work"
                :label="__('Place of Work')"
                type="text"
              />
              <FormControl
                v-model="form.ward"
                :label="__('Region & Ward')"
                type="text"
              />
              <FormControl
                v-model="form.blood_group"
                :label="__('Blood Group')"
                type="select"
                :options="bloodGroupOptions"
              />
            </div>

            <div
              class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-gray-300"
            >
              <MultiSelect
                doctype="LMS Course"
                v-model="form.trainings"
                :label="__('Trainings')"
              />
              <MultiSelect
                doctype="Language"
                v-model="form.languages"
                :label="__('Languages')"
              />
              <FormControl
                v-model="form.other_languages"
                :label="__('Other Languages')"
                type="textarea"
                :rows="6"
              />
              <FormControl
                v-model="form.reason_to_join"
                :label="__('Reason for Joining')"
                type="textarea"
                :rows="6"
              />
              <FormControl
                v-model="form.allergies"
                :label="__('Allergies')"
                type="textarea"
                :rows="6"
              />
              <FormControl
                v-model="form.disabilities"
                :label="__('Disabilities')"
                type="textarea"
                :rows="6"
              />
              <!-- <FormControl
                v-model="form.additional_skills"
                :label="__('Additional Skills')"
                type="textarea"
                :rows="6"
              /> -->
            </div>
          </section>

          <section class="mb-10">
            <h2 class="text-xl font-bold text-red-700 mb-4">
              {{ __("Documents & Profile Photo") }}
            </h2>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <label class="block mb-2 font-semibold text-gray-800">{{
                  __("Profile Photo")
                }}</label>
                <Uploader
                  label="Upload Profile Photo"
                  :fileTypes="['.jpg', '.jpeg', '.png']"
                  :onSuccess="(data) => (profilePhoto = data)"
                />
              </div>

              <div>
                <label class="block mb-2 font-semibold text-gray-800">{{
                  __("Upload Resume")
                }}</label>
                <Uploader
                  label="Upload Resume"
                  :fileTypes="['.pdf', '.docx', '.doc']"
                  :onSuccess="(file) => (resume = file)"
                />
              </div>
            </div>
          </section>

          <section class="mb-10">
            <div>
              <label class="block mb-2 font-semibold text-gray-800">
                {{ __("Supporting Documents") }}
              </label>
              <Uploader
                label="Upload Documents"
                :fileTypes="['.pdf', '.docx', '.doc', '.jpg', '.png']"
                :multi="true"
                :onSuccess="handleDocumentUpload"
              />
            </div>

            <span class="mb-2 !pt-4 text-lg font-semibold text-gray-800">
              {{ __("Cover Letter") }}
            </span>
            <div
              class="mt-6 mb-2 font-semibold text-gray-800 border border-gray-300 rounded-lg"
            >
              <TextEditor
                editor-class="min-h-[20rem] w-full rounded-b-lg border-t-0 p-2"
                :content="form.cover_letter"
                @change="(val) => (form.cover_letter = val)"
                :bubbleMenu="true"
                :fixed-menu="true"
              />
            </div>
          </section>

          <div class="flex justify-end">
            <Button
              variant="solid"
              class="bg-red-700 hover:bg-red-800 text-white px-6 py-3 rounded-lg"
              @click="submitResume"
            >
              {{
                applicationId ? __("Save Changes") : __("Submit Application")
              }}
            </Button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, inject, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { usersStore } from "../../stores/user";
import {
  FormControl,
  TextEditor,
  toast,
  createResource,
  Button,
} from "frappe-ui";
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import Uploader from "@/components/Controls/Uploader.vue";
import PendingApproval from "../PendingApproval.vue";

const router = useRouter();
const user = inject("$user");
const { roleResource } = usersStore();

const props = defineProps({
  job: { type: String, required: false, default: "" },
  showOnlyDocs: { type: Boolean, default: false },
});

const loading = ref(true);
const resume = ref(null);
const profilePhoto = ref(null);
const applicationId = ref(null);
const documents = ref([]);

const form = ref({
  company: "",
  surname: "",
  other_names: "",
  email_id: "",
  phone: "",
  mpesa_mobile_phone: "",
  gender: "",
  date_of_birth: "",
  idpassport_number: "",
  marital_status: "",
  highest_level_of_education: "",
  profession: "",
  place_of_work: "",
  reason_to_join: "",
  allergies: "",
  disabilities: "",
  languages: "",
  other_languages: "",
  trainings: "",
  blood_group: "",
  additional_skills: "",
  ward: "",
  cover_letter: "",
});

const maritalOptions = [
  { label: "Single", value: "Single" },
  { label: "Married", value: "Married" },
  { label: "Divorced", value: "Divorced" },
  { label: "Widowed", value: "Widowed" },
];

const educationOptions = [
  { label: "Nursery", value: "Nursery" },
  { label: "Primary", value: "Primary" },
  { label: "Secondary", value: "Secondary" },
  { label: "Vocational", value: "Vocational" },
  { label: "Tertiary/University", value: "Tertiary/University" },
  { label: "None", value: "None" },
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
];

const hidePersonalInfo = computed(() => roleResource.data?.name);
const showOnlyDocsProfile = computed(() => roleResource.data?.employee);
const isPersonalInfoRequired = computed(() => !showOnlyDocsProfile.value);
const alreadyApplied = ref(false);

const jobApplication = createResource({
  url: "non_profit.non_profit.api.get_list",
  makeParams() {
    return {
      doctype: "Job Applicant",
      filters: {
        email_id: user.data?.email,
        is_volunteer: true,
      },
      fields: ["*"],
    };
  },
  auto: true,
  reloadOn: () => !!user.data?.email,
  onSuccess(data) {
    if (data?.length) {
      loading.value = false;
      alreadyApplied.value = true;
    } else {
      loading.value = false;
      form.value.email_id = user.data?.email || "";
    }
  },
});
const opportunityApplication = createResource({
  url: "non_profit.non_profit.api.create_job_application",
  makeParams() {
    const params = {
      ...form.value,
      resume: resume.value,
      profile_photo: profilePhoto.value,
      is_volunteer: true,
      documents: documents.value,
    };

    if (applicationId.value) {
      params.id = applicationId.value;
    }

    return params;
  },
});
const handleDocumentUpload = (file) => {
  const newDocument = {
    file_name: file.file_name,
    file_url: file.file_url,
    file_size: file.file_size,
    uploaded_on: new Date().toISOString(),
  };
  documents.value.push(newDocument);
  toast.success(`Document "${file.file_name}" uploaded successfully`);
};

function submitResume() {
  opportunityApplication.submit(
    {},
    {
      validate() {
        if (!form.value.company) return "Company is required";
        if (!hidePersonalInfo.value) {
          if (!form.value.surname) return "Surname is required";
          if (!form.value.other_names) return "Other names are required";
          if (!form.value.email_id) return "Email is required";
          if (!form.value.phone) return "Phone number is required";
          if (!form.value.idpassport_number)
            return "ID/Passport number is required";
        }
      },
      onSuccess() {
        toast.success(
          applicationId.value
            ? "Application updated successfully"
            : "Application submitted successfully"
        );
        router.push({ name: "Dashboard" });
      },

      onError(err) {
        toast.error(err.messages?.[0] || err);
      },
    }
  );
}

watch(
  () => user.data,
  (newVal) => {
    if (!newVal?.name) {
      router.push({
        name: "Login",
        query: { "redirect-to": router.currentRoute.value.fullPath },
      });
    }
  },
  { immediate: true }
);
</script>
