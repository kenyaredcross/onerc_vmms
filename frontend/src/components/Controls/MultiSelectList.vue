<template>
  <div class="space-y-2">
    <!-- <label
      v-if="label"
      :class="labelClasses"
      class="block font-medium text-gray-700"
    >
      {{ label }} <span v-if="required" class="text-red-600">*</span>
    </label> -->

    <input
      v-model="query"
      type="text"
      :placeholder="props.label || 'Select...'"
      autocomplete="off"
      class="form-input w-full rounded-md border-gray-300 px-3 py-2 text-sm focus:border-red-500 focus:ring focus:ring-red-200"
    />

    <div
      :class="`grid gap-1 grid-cols-${cols}`"
      class="border rounded-md bg-white p-1"
    >
      <div
        v-for="option in filteredOptions"
        :key="option.value"
        :class="[
          'flex items-center gap-2 rounded-md p-2 transition cursor-pointer',
          values.includes(option.value)
            ? 'bg-red-50 border border-red-200'
            : 'hover:bg-gray-50',
        ]"
      >
        <input
          type="checkbox"
          :id="option.value"
          :value="option.value"
          :checked="values.includes(option.value)"
          @change="toggleValue(option.value)"
          class="h-4 w-4 text-red-600 border-gray-300 rounded focus:ring-red-500 cursor-pointer"
        />
        <label
          :for="option.value"
          class="flex-1 text-sm font-medium text-gray-800 cursor-pointer"
        >
          {{ option.label || option.value }}
        </label>
      </div>
    </div>

    <div v-if="allowCreate" class="pt-1">
      <Button
        variant="outline"
        class="w-full justify-center text-sm"
        :label="`+ Add New`"
        @click="showCreateDialog = true"
      />
    </div>

    <CreateNewEntryDialog
      v-model="showCreateDialog"
      :doctype="doctype"
      @created="addValue"
    />
  </div>
</template>

<script setup>
import { createResource, Button } from "frappe-ui";
import { ref, computed, watch, onMounted } from "vue";
import CreateNewEntryDialog from "../Modals/CreateNewEntryDialog.vue";

const props = defineProps({
  label: String,
  size: { type: String, default: "sm" },
  doctype: { type: String, required: true },
  filters: { type: Object, default: () => ({}) },
  validate: { type: Function, default: null },
  errorMessage: {
    type: Function,
    default: (value) => `${value} is an Invalid value`,
  },
  required: Boolean,
  allowCreate: { type: Boolean, default: false },
  cols: { type: Number, default: 2 },
});

const emit = defineEmits(["change"]);
const values = defineModel();
const query = ref("");
const showCreateDialog = ref(false);
const error = ref(null);

const filterOptions = createResource({
  url: "non_profit.non_profit.api.custom_search_link",
  method: "POST",
  cache: false,
  auto: false,
  params: {
    txt: "",
    doctype: props.doctype,
    filters: props.filters,
    page_length: 100,
  },
});

const reload = () => {
  filterOptions.update({
    params: {
      txt: query.value,
      doctype: props.doctype,
      filters: props.filters,
      page_length: 100,
    },
  });
  filterOptions.reload();
};

onMounted(reload);

watch(query, reload, { immediate: false });
watch(() => props.filters, reload, { deep: true });

const options = computed(() => filterOptions.data || []);
const filteredOptions = computed(() =>
  query.value
    ? options.value.filter((o) =>
        o.label?.toLowerCase().includes(query.value.toLowerCase())
      )
    : options.value
);

function toggleValue(value) {
  error.value = null;
  if (!values.value) values.value = [];
  if (values.value.includes(value)) {
    values.value = values.value.filter((v) => v !== value);
  } else {
    if (props.validate && !props.validate(value)) {
      error.value = props.errorMessage(value);
      return;
    }
    values.value.push(value);
  }
  emit("change", values.value);
}

function addValue(value) {
  if (!values.value) values.value = [];
  if (!values.value.includes(value)) {
    values.value.push(value);
    emit("change", values.value);
  }
}

const labelClasses = computed(() => [
  { sm: "text-sm", md: "text-base" }[props.size || "sm"],
  "text-gray-600",
]);
</script>
