<template>
  <div class="space-y-8">
    <h2 class="text-2xl font-bold text-red-700">
      {{ __("Review Your Application") }}
    </h2>

    <div>
      <h3 class="text-lg font-semibold text-gray-800 mb-4">
        {{ __("Organization & Personal Info") }}
      </h3>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <ReviewField label="Company / Branch" :value="form.company" />
        <ReviewField label="Mpesa Phone" :value="form.mpesa_mobile_phone" />
        <ReviewField label="Date of Birth" :value="form.date_of_birth" />
        <ReviewField label="ID Number" :value="form.id_number" />
        <ReviewField label="Passport Number" :value="form.passport_number" />
        <ReviewField label="Marital Status" :value="form.marital_status" />
        <ReviewField label="Blood Group" :value="form.blood_group" />
        <ReviewField label="Dependants" :value="form.number_of_dependants" />
        <ReviewField label="Citizenship" :value="form.citizenship" />
        <ReviewField label="County" :value="form.county" />
        <ReviewField label="Sub County" :value="form.sub_county" />
        <ReviewField label="Ward" :value="form.ward" />
        <ReviewField
          label="Administrative Location"
          :value="form.administrative_location"
        />
      </div>
    </div>

    <div>
      <h3 class="text-lg font-semibold text-gray-800 mb-4">
        {{ __("Additional Info") }}
      </h3>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <ReviewField label="Profession" :value="form.profession" />
        <ReviewField
          label="Access to Internet"
          :value="form.access_to_internet"
        />
        <ReviewField
          label="Reason to Join KRCS"
          :value="form.reason_to_join_krcs"
        />
        <ReviewField label="Has Insurance" :value="form.has_insurance" />

        <MultiSelect
          v-model="form.languages"
          doctype="Volunteer Language"
          :label="__('Languages')"
          :disabled="true"
          :readOnly="true"
        />
        <MultiSelect
          v-model="form.driving_licence"
          doctype="Driving Licences"
          :label="__('Driving Licence')"
          :disabled="true"
          :readOnly="true"
        />

        <div class="w-full md:col-span-3 space-y-6">
          <ChildTable
            v-model="form.disabilities"
            doctype="Employee Disability"
            label="Disabilities"
            :autoEditGrid="false"
            :readOnly="true"
          />
          <ChildTable
            v-model="form.education"
            doctype="Employee Education"
            label="Education"
            :autoEditGrid="false"
            :readOnly="true"
          />
          <ChildTable
            v-model="form.licences"
            doctype="Personnel Licence"
            label="Licences"
            :autoEditGrid="false"
            :readOnly="true"
          />
          <ChildTable
            v-model="form.certification"
            doctype="Certification"
            label="Certifications"
            :autoEditGrid="false"
            :readOnly="true"
          />
        </div>
      </div>
    </div>

    <div>
      <h3 class="text-lg font-semibold text-gray-800 mb-4">
        {{ __("Documents") }}
      </h3>
      <ChildTable
        v-model="form.supporting_documents"
        doctype="Supporting Document"
        label="Supporting Documents"
        :autoEditGrid="false"
        :readOnly="true"
      />
    </div>
  </div>
</template>

<script setup>
import ReviewField from "./ReviewField.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import ChildTable from "@/components/Controls/ChildTable.vue";

const props = defineProps({
  form: { type: Object, required: true },
});
</script>
