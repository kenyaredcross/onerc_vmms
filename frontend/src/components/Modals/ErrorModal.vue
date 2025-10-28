<template>
  <Dialog v-model="show">
    <template #body-title>
      <div class="flex items-center gap-3">
        <div
          class="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center"
        >
          <FeatherIcon name="alert-circle" class="w-5 h-5 text-red-600" />
        </div>
        <h2 class="text-lg font-bold text-gray-900">{{ title }}</h2>
      </div>
    </template>

    <template #body-content>
      <div class="space-y-4 max-h-96 overflow-y-auto">
        <div
          v-for="(errorValue, fieldName) in errors"
          :key="fieldName"
          class="bg-red-50 border border-red-200 rounded-lg p-4"
        >
          <h3 class="font-semibold text-red-900 mb-2 capitalize">
            {{ formatFieldName(fieldName) }}
          </h3>
          <ErrorRenderer :value="errorValue" :level="0" />
        </div>
      </div>
    </template>

    <template #actions>
      <Button
        variant="solid"
        class="w-full bg-red-700 hover:bg-red-800 text-white"
        @click="show = false"
      >
        {{ buttonText }}
      </Button>
    </template>
  </Dialog>
</template>

<script setup>
import { Button, Dialog } from "frappe-ui";
import { FeatherIcon } from "lucide-vue-next";
import { computed, defineComponent, h } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  errors: { type: Object, default: () => ({}) },
  title: { type: String, default: "Please Fix the Following Errors" },
  buttonText: { type: String, default: "Close" },
});

const emit = defineEmits(["update:modelValue"]);

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

function formatFieldName(fieldName) {
  if (typeof fieldName === "number" && Number.isInteger(fieldName)) {
    return String(fieldName + 1);
  }

  return String(fieldName)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function isPlainObject(value) {
  return (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.prototype.toString.call(value) === "[object Object]"
  );
}

const ErrorRenderer = defineComponent({
  name: "ErrorRenderer",
  props: {
    value: { type: [String, Object, Array], default: null },
    level: { type: Number, default: 0 },
    fieldName: { type: String, default: "" },
  },
  setup(props) {
    return () => {
      const { value, level, fieldName } = props;

      if (typeof value === "string") {
        return h(
          "div",
          {
            class: "text-sm text-red-700 flex items-start gap-2",
            style: { marginLeft: `${level * 12}px` },
          },
          [h("span", { class: "text-red-500 mt-0.5" }, "•"), h("span", value)]
        );
      }

      if (Array.isArray(value)) {
        return h(
          "div",
          {
            class: "space-y-2",
            style: { marginLeft: `${level * 12}px` },
          },
          value.map((item, index) => {
            if (typeof item === "string") {
              return h("div", { class: "flex items-start gap-2", key: index }, [
                h("span", { class: "text-red-500 mt-0.5" }, "•"),
                h("span", { class: "text-sm text-red-700" }, item),
              ]);
            }

            if (isPlainObject(item)) {
              return h(
                "div",
                {
                  class: "bg-white rounded p-3 border border-red-200 mb-2",
                  key: index,
                },
                [
                  h(
                    "div",
                    { class: "font-medium text-red-800 mb-2" },
                    `Row ${index + 1}`
                  ),
                  h(
                    "div",
                    { class: "space-y-1" },
                    Object.entries(item).map(([subField, subValue]) =>
                      h(
                        "div",
                        { class: "flex items-start gap-2", key: subField },
                        [
                          h("span", { class: "text-red-500 mt-0.5" }, "→"),
                          h("div", { class: "flex-1 text-sm" }, [
                            h(
                              "strong",
                              { class: "text-red-800" },
                              `${formatFieldName(subField)}: `
                            ),
                            h(ErrorRenderer, {
                              value: subValue,
                              level: level + 1,
                              fieldName: subField,
                            }),
                          ]),
                        ]
                      )
                    )
                  ),
                ]
              );
            }

            return h("div", { class: "flex items-start gap-2", key: index }, [
              h("span", { class: "text-red-500 mt-0.5" }, "•"),
              h("span", { class: "text-sm text-red-700" }, String(item)),
            ]);
          })
        );
      }

      if (isPlainObject(value)) {
        return h(
          "div",
          {
            class: "space-y-2",
            style: { marginLeft: `${level * 12}px` },
          },
          Object.entries(value).map(([key, val]) =>
            h(
              "div",
              { class: "text-sm text-red-700", key },
              h("div", { class: "flex items-start gap-2 mb-1" }, [
                h("span", { class: "text-red-500 mt-0.5" }, "→"),
                h("div", { class: "flex-1" }, [
                  h(
                    "strong",
                    { class: "text-red-800" },
                    `${formatFieldName(key)}: `
                  ),
                  h("div", { class: "ml-2 mt-1" }, [
                    h(ErrorRenderer, {
                      value: val,
                      level: level + 1,
                      fieldName: key,
                    }),
                  ]),
                ]),
              ])
            )
          )
        );
      }

      return h(
        "div",
        {
          class: "text-sm text-red-700 flex items-start gap-2",
          style: { marginLeft: `${level * 12}px` },
        },
        [
          h("span", { class: "text-red-500 mt-0.5" }, "•"),
          h("span", String(value)),
        ]
      );
    };
  },
});
</script>
