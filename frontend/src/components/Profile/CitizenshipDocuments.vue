<template>
	<div class="space-y-6">
		<CollapsibleSection
			:title="__('Supporting Documents & Attachments')"
			:default-open="true"
			body-class="p-4 pt-0 space-y-4"
		>
			<ChildTable
				v-model="localForm.supporting_documents"
				doctype="Supporting Document"
				:label="__('Supporting Documents')"
				:autoEditGrid="false"
			/>
		</CollapsibleSection>
		<div class="flex justify-end">
			<button
				v-if="hasChanges"
				type="button"
				@click="handleSave"
				class="flex items-center gap-1 px-8 py-2 text-sm font-bold bg-red-600 hover:bg-red-700 text-white rounded-lg shadow-md transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-red-600 disabled:active:scale-100"
				:disabled="saveInProgress"
				:aria-busy="saveInProgress"
			>
				{{ __("Save") }}
			</button>
		</div>
	</div>
	<ErrorModal v-model="showErrorDialog" :errors="flatErrors" />
</template>

<script setup>
import CollapsibleSection from "@/components/CollapsibleSection.vue";
import ChildTable from "@/components/Controls/ChildTable.vue";
import { validateForm } from "@/utils/validationUtils.js";
import { createResource, toast } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";
import ErrorModal from "../Modals/ErrorModal.vue";

const props = defineProps({
	form: {
		type: Object,
		required: true,
	},
});

const emit = defineEmits(["saved"]);

const saveInProgress = ref(false);
const originalFormData = ref({});
const showErrorDialog = ref(false);
const flatErrors = ref([]);

const localForm = reactive({
	supporting_documents: [],
	attachments: [],
});

const documentValidationConfig = [
	{
		field: "supporting_documents",
		label: "Supporting Documents",
		requiredFields: [
			"type",
			"attachment",

			{ field: "document_name", condition: (row) => row.type === "Other" },
		],
	},
];

function syncLocalForm(newForm) {
	Object.keys(localForm).forEach((key) => {
		if (newForm[key] !== undefined) {
			localForm[key] = newForm[key];
		}
	});
	originalFormData.value = JSON.parse(JSON.stringify(localForm));
}

watch(
	() => props.form,
	(newForm) => {
		syncLocalForm(newForm);
	},
	{ immediate: true, deep: true }
);

function getChangedFields() {
	const changed = {};
	for (const key in localForm) {
		const currentValue = JSON.stringify(localForm[key]);
		const originalValue = JSON.stringify(originalFormData.value[key]);
		if (currentValue !== originalValue) {
			changed[key] = localForm[key];
		}
	}
	return changed;
}

const hasChanges = computed(() => {
	return Object.keys(getChangedFields()).length > 0;
});

const saveDocsResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.update_user_details",
	makeParams() {
		return getChangedFields();
	},
	onSuccess() {
		toast.success("Documents saved successfully");
		originalFormData.value = JSON.parse(JSON.stringify(localForm));
		saveInProgress.value = false;
		showErrorDialog.value = false;
		emit("saved", localForm);
	},
	onError(err) {
		console.error("Save error:", err);
		flatErrors.value = [err.message || "Failed to save documents"];
		showErrorDialog.value = true;
		saveInProgress.value = false;
	},
});

async function handleSave() {
	const changes = getChangedFields();

	if (Object.keys(changes).length === 0) {
		toast.info("No changes to save");
		return;
	}

	const validationErrors = validateForm(localForm, documentValidationConfig);

	if (validationErrors.length > 0) {
		flatErrors.value = validationErrors;
		showErrorDialog.value = true;
		return;
	}

	saveInProgress.value = true;
	await saveDocsResource.submit();
}
</script>
