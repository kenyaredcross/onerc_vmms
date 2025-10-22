<template>
  <Dialog v-model="show" class="rounded-lg shadow-xl p-4 w-full mx-auto">
    <template #title>
      <h3 class="text-xl font-semibold text-gray-800">
        {{ __("Create New") }} {{ doctype }}
      </h3>
    </template>

    <template #body>
      <div class="space-y-4 p-4">
        <div
          v-for="field in doctypeFields"
          :key="field.fieldname"
          class="flex flex-col gap-1"
        >
          <label class="block text-sm font-medium text-gray-700">
            {{ field.label }}
            <span v-if="field.reqd" class="text-red-500">*</span>
          </label>

          <component
            :is="getComponent(field)"
            v-model="formData[field.fieldname]"
            v-bind="getComponentProps(field)"
            class="w-full"
          />
        </div>
      </div>

      <div class="flex justify-end gap-3 p-4 border-t border-gray-100">
        <Button variant="subtle" @click="close">{{ __("Cancel") }}</Button>
        <Button variant="solid" @click="submit">{{ __("Create") }}</Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import {
  Dialog,
  FileUploader,
  Button,
  createResource,
  toast,
  FormControl,
  Checkbox,
} from "frappe-ui";
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";

const props = defineProps({
  doctype: { type: String, required: true },
  modelValue: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "created"]);

const show = ref(props.modelValue);
const doctypeFields = ref([]);
const formData = ref({});

const getDoctypeInfoResource = createResource({
  url: "non_profit.non_profit.api.get_doc_info",
  method: "POST",
});

const createEntryResource = createResource({
  url: "non_profit.non_profit.api.create_link_doc",
  method: "POST",
});

watch(
  () => props.modelValue,
  async (val) => {
    show.value = val;
    if (val) await loadFields();
  }
);

async function loadFields() {
  try {
    const res = await getDoctypeInfoResource.submit({ doctype: props.doctype });
    doctypeFields.value = res.fields.filter(
      (f) => !f.hidden && !f.read_only && f.fieldtype !== "Column Break"
    );
    formData.value = {};
    doctypeFields.value.forEach((f) => (formData.value[f.fieldname] = ""));
  } catch (e) {
    toast({ title: "Error", text: "Could not load fields", variant: "error" });
    console.error(e);
  }
}

async function submit() {
  try {
    const payload = { doctype: props.doctype, ...formData.value };
    const res = await createEntryResource.submit({ data: payload });
    toast({
      title: "Success",
      text: `${res.name} created`,
      variant: "success",
    });
    emit("created", res.name);
    close();
  } catch (e) {
    toast({ title: "Error", text: "Could not create entry", variant: "error" });
    console.error(e);
  }
}

function close() {
  emit("update:modelValue", false);
}

function getComponent(field) {
  switch (field.fieldtype) {
    case "Data":
    case "Small Text":
    case "Long Text":
    case "Text Editor":
      return FormControl;
    case "Select":
      return FormControl;
    case "Check":
      return Checkbox;
    case "Link":
      return Link;
    case "Table MultiSelect":
      return MultiSelect;
    case "Attach":
    case "Attach Image":
      return FileUploader;
    default:
      return FormControl;
  }
}

function getComponentProps(field) {
  const props = {};

  if (field.fieldtype === "Select" && field.options) {
    props.options = field.options.split("\n").filter((o) => o);
  }

  if (field.fieldtype === "Link") {
    props.doctype = field.options;
  }

  if (field.fieldtype === "Attach" || field.fieldtype === "Attach Image") {
    props.upload = { doctype: props.doctype };
  }

  return props;
}
</script>
