<template>
  <div class="space-y-6">
    <CollapsibleSection title="Personal Details">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <FormControl
          v-model="form.citizenship"
          :label="__('Citizenship')"
          type="text"
          :readonly="true"
          required
        />

        <FormControl
          v-if="form.citizenship === 'Citizen'"
          v-model="form.id_number"
          label="ID Number"
          :readonly="true"
        />
        <Link
          v-if="form.citizenship !== 'Citizen'"
          doctype="Country"
          v-model="form.country_of_citizenship"
          :label="__('Country of Citizenship')"
          :readOnly="true"
        />
        <FormControl
          v-if="form.citizenship !== 'Citizen'"
          v-model="form.passport_number"
          label="Passport Number"
          :readonly="true"
        />

        <FormControl
          v-model="form.birth_date"
          label="Date of Birth"
          type="date"
          :readonly="true"
        />
        <FormControl
          v-model="form.marital_status"
          label="Marital Status"
          type="text"
          :readonly="true"
        />
        <FormControl
          v-model="form.number_of_dependants"
          label="Number of Dependants"
          :readonly="true"
        />

        <MultiSelect
          v-model="form.languages"
          doctype="Volunteer Language"
          label="Languages"
          :readOnly="true"
        />
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="Contact & Location">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Link
          doctype="County"
          v-model="form.county"
          label="County"
          :readOnly="true"
        />
        <Link
          v-if="form.county"
          doctype="Sub County"
          v-model="form.sub_county"
          label="Sub County"
          :filters="{ county: form.county }"
          :readOnly="true"
        />
        <FormControl
          v-model="form.ward"
          label="Ward"
          type="text"
          :readonly="true"
        />
        <Link
          v-if="form.sub_county"
          doctype="Administrative Location"
          v-model="form.administrative_location"
          label="Location"
          :filters="{ sub_county: form.sub_county }"
          :readOnly="true"
        />
        <FormControl
          v-model="form.access_to_internet"
          label="Access to Internet"
          type="text"
          :readonly="true"
        />
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="Education & Qualifications">
      <div class="grid grid-cols-1 gap-6">
        <Link
          doctype="Profession"
          v-model="form.profession"
          label="Profession"
          class="mt-4"
          :readOnly="true"
        />
        <ChildTable
          v-model="form.education"
          doctype="Employee Education"
          label="Education History"
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
        <ChildTable
          v-model="form.additional_skills"
          doctype="Additional Skill"
          label="Skills"
          :autoEditGrid="false"
          :readOnly="true"
        />
        <ChildTable
          v-model="form.courses"
          doctype="User External Course"
          label="Courses"
          :autoEditGrid="false"
          :readOnly="true"
        />

        <ChildTable
          v-model="form.licences"
          doctype="Personnel Licence"
          label="Professional Licences"
          :autoEditGrid="false"
          :readOnly="true"
        />
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="Work Experience & References">
      <div class="grid grid-cols-1 gap-6">
        <ChildTable
          v-model="form.work_experience"
          doctype="Work Experience"
          label="Work Experience"
          :autoEditGrid="false"
          :readOnly="true"
        />
        <ChildTable
          v-model="form.work_references"
          doctype="Professional Reference"
          label="Work References"
          :autoEditGrid="false"
          :readOnly="true"
        />
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="Additional Questions">
      <div class="space-y-8">
        <div
          v-for="(q, index) in visibleQuestions"
          :key="q.question_id"
          class="rounded-xl border p-5 bg-white shadow-sm transition-all"
          :class="{
            'ml-8 border-blue-300 bg-blue-50': q.depends_on_question,
          }"
        >
          <div class="flex justify-between items-start mb-2">
            <label class="font-medium text-gray-800">
              {{ index + 1 }}. {{ q.question }}
              <span v-if="q.is_required" class="text-red-500">*</span>
            </label>
          </div>

          <p v-if="q.help_text" class="text-sm text-gray-500 mb-2">
            {{ q.help_text }}
          </p>

          <div class="mt-2">
            <FormControl
              v-if="q.question_type === 'Yes/No'"
              v-model="responses[q.question_id].answer"
              type="select"
              :options="[
                { label: 'Yes', value: 'Yes' },
                { label: 'No', value: 'No' },
              ]"
              :readonly="true"
            />

            <FormControl
              v-else-if="q.question_type === 'Text'"
              v-model="responses[q.question_id].answer"
              type="textarea"
              :rows="12"
              :readonly="true"
            />

            <FormControl
              v-else-if="q.question_type === 'Date'"
              v-model="responses[q.question_id].answer"
              type="date"
              :readonly="true"
            />

            <FormControl
              v-else-if="q.question_type === 'Email'"
              v-model="responses[q.question_id].answer"
              type="email"
              :readonly="true"
            />

            <FormControl
              v-else-if="q.question_type === 'Phone'"
              v-model="responses[q.question_id].answer"
              type="text"
              inputmode="tel"
              :readonly="true"
            />

            <div
              v-else-if="q.question_type === 'Rating'"
              class="flex gap-3 mt-1"
            >
              <span class="text-lg font-bold">
                {{ responses[q.question_id].answer || "N/A" }}
              </span>
              <span
                v-if="responses[q.question_id].answer"
                class="text-gray-500"
              >
                / {{ q.max_score }}
              </span>
            </div>

            <CheckableListSelect
              v-else-if="q.question_type === 'MultiSelect'"
              v-model="responses[q.question_id].answer"
              :options="parseOptions(q.options)"
              :readOnly="true"
            />

            <div v-else-if="q.question_type === 'Upload'">
              <a
                v-if="responses[q.question_id].attachment"
                :href="responses[q.question_id].attachment"
                target="_blank"
                class="text-blue-600 hover:underline font-medium"
              >
                View Uploaded File
              </a>
              <span v-else class="text-gray-500">No file uploaded</span>
            </div>

            <FormControl
              v-else
              v-model="responses[q.question_id].answer"
              type="text"
              :readonly="true"
            />
          </div>
        </div>
      </div>
    </CollapsibleSection>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { FormControl } from "frappe-ui";
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import ChildTable from "@/components/Controls/ChildTable.vue";

import CheckableListSelect from "@/components/Controls/CheckableListSelect.vue";

import CollapsibleSection from "@/components/CollapsibleSection.vue";

const props = defineProps({
  form: { type: Object, required: true },
  job: { type: Object, required: true },
});

const responses = ref({});

function parseOptions(optStr) {
  if (!optStr) return [];
  return optStr
    .split(/\r?\n|,/)
    .map((o) => o.trim())
    .filter((o) => o);
}

props.job?.screening_questions?.forEach((q) => {
  const existing = props.form.screening_question_responses?.find(
    (r) => r.question_id === q.question_id
  );

  responses.value[q.question_id] = {
    question_id: q.question_id,
    question: q.question,
    answer: existing?.answer || "",
    attachment: existing?.attachment || null,
  };
});

watch(
  responses,
  (newVal) => {
    props.form.screening_question_responses = Object.values(newVal)
      .map((r) => {
        let ans = r.answer;
        if (Array.isArray(ans)) {
          ans = ans.join("\n");
        }
        return {
          question_id: r.question_id,
          question: r.question,
          answer: ans || "",
          attachment: r.attachment || null,
        };
      })
      .filter((r) => r.answer || r.attachment);
  },
  { deep: true, immediate: true }
);

const visibleQuestions = computed(() =>
  props.job?.screening_questions?.filter((q) => {
    if (!q.depends_on_question || !q.show_if_answer_is) return true;
    const dep = responses.value[q.depends_on_question];
    if (!dep) return false;
    return Array.isArray(dep.answer)
      ? dep.answer.includes(q.show_if_answer_is)
      : dep.answer === q.show_if_answer_is;
  })
);

props.job?.screening_questions?.forEach((q) => {
  if (q.depends_on_question) {
    watch(
      () => responses.value[q.depends_on_question]?.answer,
      () => {
        const shouldShow = visibleQuestions.value.includes(q);
        if (!shouldShow) {
          responses.value[q.question_id].answer = "";
          responses.value[q.question_id].attachment = null;
        }
      }
    );
  }
});

const form = props.form;
</script>
