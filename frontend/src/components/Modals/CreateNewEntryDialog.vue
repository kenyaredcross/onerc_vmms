<template>
	<Dialog v-model="show" :options="{ size: 'lg' }">
		<template #body-title>
			<h3 class="text-lg font-semibold text-ink-gray-8">
				{{ __("Create New") }} {{ doctype }}
			</h3>
		</template>

		<template #body-content>
			<div class="space-y-4 max-h-[60vh] overflow-y-auto">
				<div v-if="loading" class="py-6 text-center text-sm text-ink-gray-5">
					{{ __("Loading...") }}
				</div>
				<template v-else>
					<div v-for="field in doctypeFields" :key="field.fieldname">
						<label class="block text-xs font-medium text-ink-gray-5 mb-1.5">
							{{ field.label }}
							<span v-if="field.reqd" class="text-red-500 ml-0.5">*</span>
						</label>
						<component
							:is="getComponent(field)"
							v-model="formData[field.fieldname]"
							v-bind="getComponentProps(field)"
							class="w-full"
						/>
					</div>
				</template>
			</div>
		</template>

		<template #actions>
			<div class="flex justify-end gap-3">
				<Button variant="subtle" @click="close">{{ __("Cancel") }}</Button>
				<Button variant="solid" theme="red" :loading="submitting" @click="submit">
					{{ __("Create") }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import {
	Button,
	Checkbox,
	createResource,
	Dialog,
	FileUploader,
	FormControl,
	toast,
} from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = defineProps({
	doctype: { type: String, required: true },
	modelValue: { type: Boolean, default: false },
	initialData: { type: Object, default: () => ({}) },
});

const emit = defineEmits(["update:modelValue", "created"]);

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const doctypeFields = ref([]);
const formData = ref({});
const loading = ref(false);
const submitting = ref(false);

const getDoctypeInfoResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.doc.get_doc_info",
	method: "POST",
});

const createEntryResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.doc.create_link_doc",
	method: "POST",
});

watch(
	() => props.modelValue,
	async (val) => {
		if (val) await loadFields();
	}
);

async function loadFields() {
	loading.value = true;
	try {
		const res = await getDoctypeInfoResource.submit({ doctype: props.doctype });
		doctypeFields.value = res.fields.filter(
			(f) => !f.hidden && !f.read_only && f.fieldtype !== "Column Break"
		);
		formData.value = {};
		doctypeFields.value.forEach((f) => (formData.value[f.fieldname] = ""));
		Object.assign(formData.value, props.initialData);
	} catch (e) {
		console.log(e.message.message);

		toast.error("Could not load fields for doctype");
	} finally {
		loading.value = false;
	}
}

async function submit() {
	submitting.value = true;
	try {
		const payload = { doctype: props.doctype, ...props.initialData, ...formData.value };

		const res = await createEntryResource.submit({ data: payload });

		if (res?.status === "error") {
			toast.error(res.message || "Could not create entry");
			return;
		}

		toast.success(`${res.name} created`);
		emit("created", res.name);
		close();
	} catch (e) {
		const msg = e?.message || "Could not create entry";
		toast.error(msg);
	} finally {
		submitting.value = false;
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
	const fieldProps = {};

	if (field.fieldtype === "Select" && field.options) {
		fieldProps.options = field.options.split("\n").filter((o) => o);
	}

	if (field.fieldtype === "Link") {
		fieldProps.doctype = field.options;
	}

	if (field.fieldtype === "Attach" || field.fieldtype === "Attach Image") {
		fieldProps.upload = { doctype: props.doctype };
	}

	return fieldProps;
}
</script>
