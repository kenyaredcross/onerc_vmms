<template>
  <div class="space-y-1.5 relative">
    <label class="block" :class="labelClasses" v-if="attrs.label">
      {{ attrs.label }}
      <span class="text-ink-red-3" v-if="attrs.required">*</span>
    </label>

    <div class="relative">
      <Autocomplete
        ref="autocomplete"
        :options="options.data"
        v-model="value"
        :size="attrs.size || 'sm'"
        :variant="attrs.variant"
        :placeholder="attrs.placeholder"
        :filterable="false"
        :readonly="attrs.readonly || props.readOnly"
        class="relative !z-100"
      >
        <template #target="{ open, togglePopover }">
          <slot name="target" v-bind="{ open, togglePopover }" />
        </template>

        <template #prefix>
          <slot name="prefix" />
        </template>

        <template #item-prefix="{ active, selected, option }">
          <slot name="item-prefix" v-bind="{ active, selected, option }" />
        </template>

        <template #item-label="{ active, selected, option }">
          <slot name="item-label" v-bind="{ active, selected, option }" />
        </template>

        <template #footer="{ value, close }">
          <div v-if="attrs.onCreate">
            <Button
              variant="ghost"
              class="w-full !justify-start"
              :label="__('Create New')"
              @click="attrs.onCreate(value, close)"
            >
              <template #prefix>
                <Plus class="h-4 w-4 stroke-1.5" />
              </template>
            </Button>
          </div>
          <div>
            <Button
              variant="ghost"
              class="w-full !justify-start"
              :label="__('Clear')"
              @click="() => clearValue(close)"
            >
              <template #prefix>
                <X class="h-4 w-4 stroke-1.5" />
              </template>
            </Button>
          </div>
        </template>
      </Autocomplete>
    </div>

    <p v-if="description" class="text-sm text-ink-gray-5">{{ description }}</p>
  </div>
</template>

<script setup>
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import { watchDebounced } from "@vueuse/core";
import { createResource, Button } from "frappe-ui";
import { Plus, X } from "lucide-vue-next";
import { useAttrs, computed, ref, watch } from "vue";

const props = defineProps({
  doctype: {
    type: String,
    required: true,
  },
  filters: {
    type: Object,
    default: () => ({}),
  },
  modelValue: {
    type: String,
    default: "",
  },
  description: {
    type: String,
    default: "",
  },
  readOnly: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:modelValue", "change"]);
const attrs = useAttrs();
const valuePropPassed = computed(() => "value" in attrs);

const value = computed({
  get: () => (valuePropPassed.value ? attrs.value : props.modelValue),
  set: (val) => {
    return (
      val?.value &&
      emit(valuePropPassed.value ? "change" : "update:modelValue", val?.value)
    );
  },
});

const autocomplete = ref(null);
const text = ref("");

watchDebounced(
  () => autocomplete.value?.query,
  (val) => {
    val = val || "";
    if (text.value === val) return;
    text.value = val;
    reload(val);
  },
  { debounce: 300, immediate: true }
);

watchDebounced(
  () => props.doctype,
  () => reload(""),
  { debounce: 300, immediate: true }
);

const serializeFilters = (f) => {
  if (!f) return "{}";
  return typeof f === "string" ? f : JSON.stringify(f);
};

const options = createResource({
  url: "non_profit.non_profit.api.custom_search_link",
  cache: [props.doctype, text.value, serializeFilters(props.filters)],
  method: "POST",
  auto: true,
  params: {
    doctype: props.doctype,
    txt: text.value,
    filters: serializeFilters(props.filters),
  },
  transform: (data) => {
    return data.map((option) => ({
      label: option.label || option.value,
      value: option.value,
      description: option.description,
    }));
  },
});

const reload = (val = autocomplete.value?.query || "") => {
  options.update({
    params: {
      doctype: props.doctype,
      txt: val,
      filters: serializeFilters(props.filters),
    },
  });
  options.reload();
};

const clearValue = (close) => {
  emit(valuePropPassed.value ? "change" : "update:modelValue", "");
  close();
};

const labelClasses = computed(() => [
  { sm: "text-xs", md: "text-base" }[attrs.size || "sm"],
  "text-ink-gray-5",
]);

watch(
  () => props.filters,
  () => reload(autocomplete.value?.query || ""),
  { immediate: true, deep: true }
);
</script>

<style scoped>
.frappeui-popper-root {
  z-index: 9999 !important;
}
</style>
