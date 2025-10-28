<template>
  <div class="space-y-6">
    <div class="grid grid-cols-1 gap-6">
      <Link
        doctype="Profession"
        v-model="form.profession"
        label="Profession"
        class="mt-4"
        :required="true"
      />
      <ChildTable
        v-model="form.education"
        doctype="Employee Education"
        label="Education History"
        required
        :autoEditGrid="false"
      />
      <ChildTable
        v-model="form.courses"
        doctype="User External Course"
        label="Certifications and Trainings"
        :autoEditGrid="false"
      />
      <ChildTable
        v-model="form.additional_skills"
        doctype="Additional Skill"
        label="Skills"
        :autoEditGrid="false"
      />

      <ChildTable
        v-model="form.licences"
        doctype="Personnel Licence"
        label="Professional Licences"
        :autoEditGrid="false"
      />
    </div>
  </div>
</template>

<script setup>
import ChildTable from "@/components/Controls/ChildTable.vue";
import Link from "@/components/Controls/Link.vue";

const props = defineProps({
  form: {
    type: Object,
    required: true,
  },
});

const form = props.form;
</script>
