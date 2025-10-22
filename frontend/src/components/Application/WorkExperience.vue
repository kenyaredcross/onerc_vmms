<template>
  <div class="space-y-6">
    <div class="grid grid-cols-1 gap-6">
      <ChildTable
        v-model="form.work_experience"
        doctype="Work Experience"
        label="Work Experience"
        :autoEditGrid="false"
      />
      <ChildTable
        v-model="form.work_references"
        doctype="Professional Reference"
        label="Work References"
        :autoEditGrid="false"
      />
    </div>
  </div>
</template>

<script setup>
import ChildTable from "@/components/Controls/ChildTable.vue";

const props = defineProps({
  form: {
    type: Object,
    required: true,
  },
});

const form = props.form;
</script>
