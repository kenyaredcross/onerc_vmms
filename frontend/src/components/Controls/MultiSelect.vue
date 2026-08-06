<template>
	<div>
		<MultiSelect
			v-model="selectedLinkValues"
			v-bind="attrs"
			:options="options"
			:filterable="false"
			:loading="filterOptions.loading"
			:disabled="props.readOnly"
			:required="props.required"
			:label="props.label ? __(props.label) : undefined"
			:placeholder="__(props.label) || __('Select...')"
			:size="props.size"
			:empty-text="__('No results')"
			:error="error"
			@update:query="onQuery"
		>
			<template v-if="props.allowCreate" #footer="{ close }">
				<Button
					variant="ghost"
					class="w-full !justify-start"
					:label="__('Add New')"
					@click="
						() => {
							close();
							showCreateDialog = true;
						}
					"
				>
					<template #prefix>
						<Plus class="h-4 w-4 stroke-1.5" />
					</template>
				</Button>
			</template>
		</MultiSelect>

		<div v-if="displayValues.length" class="grid grid-cols-1 gap-2 mt-1">
			<div
				v-for="(item, index) in displayValues"
				:key="`${props.label}-${item[linkFieldName] || index}`"
				class="flex items-center justify-between break-all bg-surface-gray-2 text-ink-gray-7 word-wrap p-2 rounded-md mr-2"
			>
				<span class="break-all">{{ __(item.__label) || __(item.label) }}</span>
				<X
					v-if="!props.readOnly"
					class="size-4 stroke-1.5 cursor-pointer"
					@click="removeValue(index)"
				/>
			</div>
		</div>

		<CreateNewEntryDialog
			v-model="showCreateDialog"
			:doctype="linkDoctype"
			@created="(newName) => addValue({ value: newName, label: newName })"
		/>
	</div>
</template>

<script setup>
import { Button, createResource, debounce, MultiSelect } from "frappe-ui";
import { Plus, X } from "lucide-vue-next";
import { computed, onBeforeUnmount, onMounted, ref, useAttrs, watch } from "vue";
import CreateNewEntryDialog from "../Modals/CreateNewEntryDialog.vue";

defineOptions({ inheritAttrs: false });

const attrs = useAttrs();

const props = defineProps({
	label: String,
	size: { type: String, default: "sm" },
	doctype: { type: String, required: true },
	mainField: { type: String, default: null },
	filters: { type: Object, default: () => ({}) },
	validate: { type: Function, default: null },
	errorMessage: {
		type: Function,
		default: (value) => `${value} is an Invalid value`,
	},
	required: Boolean,
	allowCreate: { type: Boolean, default: false },
	readOnly: { type: Boolean, default: false },
});

const values = defineModel();
const emit = defineEmits(["change"]);

const error = ref(null);
const showCreateDialog = ref(false);
const linkFieldName = ref(props.mainField);
const linkDoctype = ref(null);
const titleField = ref(null);
const displayValues = ref([]);
let resolving = false;

const childtableMeta = createResource({
	url: "frappe.desk.form.load.getdoctype",
	params: {
		doctype: props.doctype,
		with_parent: 0,
	},
	cache: [props.doctype],
	auto: true,
	onSuccess(data) {
		const doc = data.docs.find((d) => d.name === props.doctype) || data.docs[0];
		if (!linkFieldName.value) {
			const linkField = doc.fields.find((f) => f.fieldtype === "Link");
			if (linkField) {
				linkFieldName.value = linkField.fieldname;
				linkDoctype.value = linkField.options;
			} else {
				console.error("[MultiSelect] No link field found in childtable:", props.doctype);
			}
		} else {
			const field = doc.fields.find((f) => f.fieldname === linkFieldName.value);

			if (field && field.fieldtype === "Link") {
				linkDoctype.value = field.options;
			} else {
				console.error("[MultiSelect] Field not found or not a Link field:", {
					fieldname: linkFieldName.value,
					field: field,
					doctype: props.doctype,
				});
			}
		}
	},
});

const linkDoctypeMeta = createResource({
	url: "frappe.desk.form.load.getdoctype",
	makeParams() {
		return linkDoctype.value
			? {
					doctype: linkDoctype.value,
					with_parent: 0,
			  }
			: null;
	},
	cache: () => [linkDoctype.value],
	auto: false,
	onSuccess(data) {
		titleField.value = data.docs[0].title_field || "name";
	},
});

watch(
	linkDoctype,
	(newVal) => {
		if (newVal) {
			linkDoctypeMeta.reload();
			reload("");
		}
	},
	{ immediate: true }
);

const childtableEntries = createResource({
	url: "frappe.client.get_list",
	makeParams() {
		if (!values.value?.length) {
			return null;
		}

		const childIds = values.value.filter((v) => typeof v === "string");

		if (!childIds.length) {
			return null;
		}

		return {
			doctype: props.doctype,
			fields: ["name", linkFieldName.value],
			filters: [["name", "in", childIds]],
		};
	},
	auto: false,
});

const linkLabelsResource = createResource({
	url: "frappe.client.get_list",
	makeParams() {
		const linkValues = displayValues.value.map((v) => v[linkFieldName.value]).filter(Boolean);

		if (!linkValues.length || !linkDoctype.value || !titleField.value) {
			return null;
		}

		return {
			doctype: linkDoctype.value,
			fields: ["name", titleField.value],
			filters: [["name", "in", linkValues]],
		};
	},
	auto: false,
});

const resolveValues = async () => {
	if (resolving || !values.value?.length || !linkFieldName.value) {
		displayValues.value = [];
		return;
	}

	resolving = true;
	try {
		const resolved = [];

		const hasStringValues = values.value.some((v) => typeof v === "string");

		if (hasStringValues) {
			await childtableEntries.reload();

			if (childtableEntries.data) {
				for (const entry of childtableEntries.data) {
					resolved.push({
						name: entry.name,
						[linkFieldName.value]: entry[linkFieldName.value],
						__label: entry[linkFieldName.value],
					});
				}
			}
		} else {
			for (const val of values.value) {
				resolved.push({
					...val,
					__label: val[linkFieldName.value] || val.name,
				});
			}
		}

		displayValues.value = resolved;

		if (
			resolved.length &&
			linkDoctype.value &&
			titleField.value &&
			resolved.every((item) => item[linkFieldName.value])
		) {
			await linkLabelsResource.reload();

			if (linkLabelsResource.data?.length) {
				displayValues.value = resolved.map((item) => {
					const match = linkLabelsResource.data.find(
						(opt) => opt.name === item[linkFieldName.value]
					);
					return {
						...item,
						__label: match
							? match[titleField.value] || match.name
							: item[linkFieldName.value],
					};
				});
			}
		}
	} finally {
		resolving = false;
	}
};

watch(
	[() => values.value, linkFieldName, titleField],
	() => {
		if (linkFieldName.value && titleField.value) {
			resolveValues();
		}
	},
	{ deep: true }
);

onMounted(() => {
	if (values.value?.length) {
		resolveValues();
	}
});

const filterOptions = createResource({
	url: "frappe.desk.search.search_link",
	method: "POST",
	auto: false,
	makeParams() {
		if (!linkDoctype.value) {
			return null;
		}

		return {
			txt: "",
			doctype: linkDoctype.value,
			filters: props.filters,
		};
	},
	transform: (data) =>
		(data || []).map((option) => ({
			label: option.label || option.value,
			value: option.value,
			description: option.description,
		})),
});

const options = computed(() => {
	if (!filterOptions.data) {
		return [];
	}

	const currentLinkValues = displayValues.value.map((v) => v[linkFieldName.value]);

	return filterOptions.data.filter((option) => !currentLinkValues.includes(option.value));
});

function reload(val) {
	if (!linkDoctype.value) {
		return;
	}

	filterOptions.update({
		params: {
			txt: val,
			doctype: linkDoctype.value,
			filters: props.filters,
		},
	});
	filterOptions.reload();
}

const onQuery = debounce((val) => reload(val || ""), 300);

onBeforeUnmount(() => onQuery.cancel?.());

const selectedLinkValues = computed({
	get: () => displayValues.value.map((v) => v[linkFieldName.value]).filter(Boolean),
	set: (next) => {
		const current = displayValues.value.map((v) => v[linkFieldName.value]);

		for (const linkValue of next) {
			if (!current.includes(linkValue)) {
				const option = (filterOptions.data || []).find((o) => o.value === linkValue);
				addValue(option || { value: linkValue, label: linkValue });
			}
		}

		for (let i = current.length - 1; i >= 0; i--) {
			if (!next.includes(current[i])) {
				removeValue(i);
			}
		}
	},
});

const addValue = (option) => {
	error.value = null;
	if (!option) return;

	let linkValue, labelValue;

	if (typeof option === "string") {
		linkValue = option.trim();
		labelValue = option.trim();
	} else {
		linkValue = option.value;
		labelValue = option.label || option.value;
	}

	if (displayValues.value.some((item) => item[linkFieldName.value] === linkValue)) {
		return;
	}

	if (props.validate && !props.validate(linkValue)) {
		error.value = props.errorMessage(linkValue);
		return;
	}

	const newRow = {
		[linkFieldName.value]: linkValue,
		__label: labelValue,
	};

	displayValues.value.push(newRow);

	if (!values.value) {
		values.value = [];
	}

	values.value = [...values.value, newRow];

	emit("change", values.value);
};

watch(
	() => props.filters,
	() => {
		if (linkDoctype.value) {
			reload("");
		}
	},
	{ deep: true }
);

const removeValue = (index) => {
	displayValues.value.splice(index, 1);
	values.value.splice(index, 1);

	emit("change", values.value);
};
</script>
