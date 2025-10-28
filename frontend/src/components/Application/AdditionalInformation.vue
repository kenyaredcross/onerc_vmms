<template>
  <div class="space-y-8">
    <div
      v-if="!props.job?.screening_questions?.length"
      class="text-center py-10 px-6 rounded-lg bg-emerald-50 border-2 border-emerald-200 text-emerald-800"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-12 w-12 mx-auto mb-3"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="1.5"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <h3 class="text-xl font-semibold mb-1">
        No Additional Information Required
      </h3>
      <p class="text-sm">
        This opportunity does not require any supplementary information at this
        time. Click 'Save & Continue' to proceed to the review step.
      </p>
    </div>

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
        />

        <FormControl
          v-else-if="q.question_type === 'Text'"
          v-model="responses[q.question_id].answer"
          type="textarea"
          :rows="12"
        />

        <FormControl
          v-else-if="q.question_type === 'Date'"
          v-model="responses[q.question_id].answer"
          type="date"
        />

        <FormControl
          v-else-if="q.question_type === 'Email'"
          v-model="responses[q.question_id].answer"
          type="email"
        />

        <FormControl
          v-else-if="q.question_type === 'Phone'"
          v-model="responses[q.question_id].answer"
          type="text"
          inputmode="tel"
        />

        <div v-else-if="q.question_type === 'Rating'" class="flex gap-3 mt-1">
          <template v-for="n in q.max_score" :key="n">
            <button
              type="button"
              class="px-3 py-1.5 border rounded-full text-sm"
              :class="{
                'bg-blue-600 text-white': responses[q.question_id].answer >= n,
                'hover:bg-blue-50': true,
              }"
              @click="responses[q.question_id].answer = n"
            >
              {{ n }}
            </button>
          </template>
        </div>

        <CheckableListSelect
          v-else-if="q.question_type === 'MultiSelect'"
          v-model="responses[q.question_id].answer"
          :options="parseOptions(q.options)"
        />

        <div v-else-if="q.question_type === 'Upload'">
          <Uploader
            v-model="responses[q.question_id].attachment"
            label="Upload File"
          />
        </div>

        <FormControl
          v-else
          v-model="responses[q.question_id].answer"
          type="text"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import CheckableListSelect from "@/components/Controls/CheckableListSelect.vue";
import Uploader from "@/components/Controls/Uploader.vue";
import { FormControl } from "frappe-ui";
import { computed, ref, watch } from "vue";

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

if (props.job?.screening_questions?.length) {
  props.job.screening_questions.forEach((q) => {
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
}

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

if (props.job?.screening_questions?.length) {
  props.job.screening_questions.forEach((q) => {
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
}
</script>
