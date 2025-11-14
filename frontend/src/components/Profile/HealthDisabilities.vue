<template>
	<div class="space-y-6">
		<FormControl
			v-model="localForm.blood_group"
			:label="__('Blood Group')"
			type="select"
			:options="bloodGroupOptions"
		/>

		<ChildTable
			v-model="localForm.allergies"
			doctype="Allergy Table"
			:label="__('Allergies')"
			:autoEditGrid="false"
		/>

		<ChildTable
			v-model="localForm.disabilities"
			doctype="Employee Disability"
			:label="__('Disabilities')"
			:autoEditGrid="false"
		/>
		<div class="flex justify-end">
			<button
				v-if="hasChanges"
				@click="handleSave"
				variant="solid"
				class="flex items-center gap-1 px-8 py-2 text-sm font-bold bg-red-600 hover:bg-red-700 text-white rounded-lg shadow-md transition-all active:scale-95"
				:loading="saveInProgress"
			>
				<span>{{ __("Save") }}</span>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-4 h-4"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
					stroke-width="2"
					aria-hidden="true"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M5 5v14a2 2 0 002 2h10a2 2 0 002-2V7l-4-4H7a2 2 0 00-2 2z"
					/>
					<path stroke-linecap="round" stroke-linejoin="round" d="M9 9h6v6H9z" />
				</svg>
			</button>
		</div>
	</div>
	<ErrorModal v-model="showErrorDialog" :errors="flatErrors" />
</template>

<script setup>
import ChildTable from "@/components/Controls/ChildTable.vue";
import { FormControl, createResource, toast } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";
import ErrorModal from "../Modals/ErrorModal.vue";

import { validateForm } from "@/utils/validationUtils.js";

const props = defineProps({
	form: {
		type: Object,
		required: true,
	},
});

const emit = defineEmits(["saved"]);

const bloodGroupOptions = [
	{ label: "A+", value: "A+" },
	{ label: "A-", value: "A-" },
	{ label: "B+", value: "B+" },
	{ label: "B-", value: "B-" },
	{ label: "AB+", value: "AB+" },
	{ label: "AB-", value: "AB-" },
	{ label: "O+", value: "O+" },
	{ label: "O-", value: "O-" },
	{ label: "Don't Know", value: "Don't Know" },
];

const saveInProgress = ref(false);
const originalFormData = ref({});
const showErrorDialog = ref(false);
const flatErrors = ref([]);

const localForm = reactive({
	blood_group: "",
	allergies: [],
	disabilities: [],
	health_information: "",
});

const healthValidationConfig = [
	{
		field: "allergies",
		label: "Allergies",
		requiredFields: ["allergy"],
	},
	{
		field: "disabilities",
		label: "Disabilities",
		requiredFields: ["disability"],
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
	{ immediate: true, deep: true },
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

const saveUserResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.user.update_user_details",
	makeParams() {
		return getChangedFields();
	},
	onSuccess(data) {
		toast.success("Health and disability information saved successfully");

		originalFormData.value = JSON.parse(JSON.stringify(localForm));
		saveInProgress.value = false;
		showErrorDialog.value = false;

		emit("saved", localForm);
	},
	onError(err) {
		console.error("Save error:", err);
		flatErrors.value = [err.message || "Failed to save health and disability information"];
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

	const validationErrors = validateForm(localForm, healthValidationConfig);

	if (validationErrors.length > 0) {
		flatErrors.value = validationErrors;
		showErrorDialog.value = true;
		return;
	}

	saveInProgress.value = true;
	await saveUserResource.submit();
}
</script>
