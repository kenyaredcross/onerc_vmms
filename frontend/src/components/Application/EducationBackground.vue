<template>
  <div class="space-y-6">
    <div class="grid grid-cols-1 gap-6">
      <Link
        doctype="Profession"
        v-model="form.profession"
        label="Profession"
        class="mt-4"
      />
      <ChildTable
        v-model="form.education"
        doctype="Employee Education"
        label="Education History"
        :autoEditGrid="false"
      />
      <ChildTable
        v-model="form.certification"
        doctype="Certification"
        label="Certifications"
        :autoEditGrid="false"
      />
      <ChildTable
        v-model="form.additional_skills"
        doctype="Additional Skill"
        label="Skills"
        :autoEditGrid="false"
      />
      <ChildTable
        v-model="form.courses"
        doctype="User External Course"
        label="Courses"
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
import Link from "@/components/Controls/Link.vue";
import ChildTable from "@/components/Controls/ChildTable.vue";

const props = defineProps({
  form: {
    type: Object,
    required: true,
  },
});

const form = props.form;
</script>
