<template>
	<Teleport to="body">
		<Transition
			enter-active-class="transition duration-150 ease-out"
			enter-from-class="opacity-0"
			enter-to-class="opacity-100"
			leave-active-class="transition duration-100 ease-in"
			leave-from-class="opacity-100"
			leave-to-class="opacity-0"
		>
			<div
				v-if="modelValue"
				class="fixed inset-0 z-[200] flex items-center justify-center p-4"
			>
				<div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close" />

				<div class="relative z-10 w-full max-w-lg bg-surface-white rounded-xl shadow-2xl">
					<div
						class="flex items-center justify-between px-6 pt-5 pb-4 border-b border-outline-gray-100"
					>
						<h3 class="text-lg font-semibold text-ink-gray-8">
							{{ __("Create New") }} {{ doctype }}
						</h3>
						<button
							class="rounded-md p-1 text-ink-gray-5 hover:text-ink-gray-8 hover:bg-surface-gray-2 transition-colors"
							@click="close"
						>
							<X class="h-4 w-4" />
						</button>
					</div>

					<div class="px-6 pt-5 pb-2 space-y-4">
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

					<div
						class="flex justify-end gap-3 px-6 py-4 border-t border-outline-gray-100 mt-4"
					>
						<Button variant="subtle" @click="close">{{ __("Cancel") }}</Button>
						<Button variant="solid" theme="red" :loading="submitting" @click="submit">
							{{ __("Create") }}
						</Button>
					</div>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup>
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import { Button, Checkbox, createResource, FileUploader, FormControl, toast } from "frappe-ui";
import { X } from "lucide-vue-next";
import { ref, watch } from "vue";

const props = defineProps({
	doctype: { type: String, required: true },
	modelValue: { type: Boolean, default: false },
	initialData: { type: Object, default: () => ({}) },
});

const emit = defineEmits(["update:modelValue", "created"]);

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
	},
);

async function loadFields() {
	loading.value = true;
	try {
		const res = await getDoctypeInfoResource.submit({ doctype: props.doctype });
		doctypeFields.value = res.fields.filter(
			(f) => !f.hidden && !f.read_only && f.fieldtype !== "Column Break",
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
