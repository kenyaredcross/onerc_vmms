<template>
	<section>
		<h2 class="text-xl font-bold text-red-700 mb-4">
			{{ __("Additional Information") }}
		</h2>
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<div>
				<FormControl
					v-model="localModel.access_to_internet"
					:label="__('Access to Internet')"
					type="select"
					:required="true"
					:options="internetOptions"
				/>
				<p v-if="errors[1]?.['Access To Internet']" class="text-sm text-red-600 mt-1">
					{{ errors[1]?.["Access To Internet"] }}
				</p>
			</div>
			<div>
				<Link
					v-model="localModel.profession"
					:label="__('Profession')"
					:required="true"
					doctype="Profession"
				/>
				<p v-if="errors[1]?.['Profession']" class="text-sm text-red-600 mt-1">
					{{ errors[1]?.["Profession"] }}
				</p>
			</div>
			<div>
				<FormControl
					v-model="localModel.reason_to_join_krcs"
					:label="__('Reason for Joining')"
					type="select"
					:required="true"
					:options="reasonsOptions"
				/>
				<p v-if="errors[1]?.['Reason To Join Krcs']" class="text-sm text-red-600 mt-1">
					{{ errors[1]?.["Reason To Join Krcs"] }}
				</p>
			</div>
			<div>
				<MultiSelect
					v-model="localModel.languages"
					doctype="Volunteer Language"
					:label="__('Languages')"
				/>
				<p v-if="errors[1]?.['Languages']" class="text-sm text-red-600 mt-1">
					{{ errors[1]?.["Languages"] }}
				</p>
			</div>
			<div>
				<MultiSelect
					v-model="localModel.driving_licence"
					:label="__('Driving Licence')"
					doctype="Driving Licences"
				/>
				<p v-if="errors[1]?.['Driving Licence']" class="text-sm text-red-600 mt-1">
					{{ errors[1]?.["Driving Licence"] }}
				</p>
			</div>

			<div class="w-full md:col-span-2 space-y-6">
				<ChildTable
					v-model="localModel.disabilities"
					doctype="Employee Disability"
					label="Disabilities"
					:autoEditGrid="true"
					:field-queries="disabilityQueries"
					:form-data="localModel"
					@validationErrors="onChildErrors('Disabilities', $event)"
				/>
				<ChildTable
					v-model="localModel.allergies"
					doctype="Allergy Table"
					label="Allergies"
					:autoEditGrid="true"
					:form-data="localModel"
					@validationErrors="onChildErrors('Allergies', $event)"
				/>

				<ChildTable
					v-model="localModel.education"
					doctype="Employee Education"
					label="Education"
					:autoEditGrid="true"
					@validationErrors="onChildErrors('Education', $event)"
				/>

				<ChildTable
					v-model="localModel.courses"
					doctype="User External Course"
					label="Trainings & Certifications"
					:autoEditGrid="true"
					@validationErrors="onChildErrors('Courses', $event)"
				/>

				<ChildTable
					v-model="localModel.additional_skills"
					doctype="Additional Skill"
					label="Additional Skills"
					:autoEditGrid="true"
					@validationErrors="onChildErrors('Additional Skills', $event)"
				/>

				<ChildTable
					v-model="localModel.licences"
					doctype="Personnel Licence"
					label="Licences"
					:autoEditGrid="true"
					@validationErrors="onChildErrors('Licences', $event)"
				/>
			</div>
		</div>
	</section>
</template>

<script setup>
import Link from "@/components/Controls/Link.vue";
import MultiSelect from "@/components/Controls/MultiSelect.vue";
import {
	isDateValid,
	isEmailValid,
	isPastDate,
	isPhoneNumberValid,
} from "@/utils/validationUtils.js";
import { FormControl } from "frappe-ui";
import { computed, onMounted, watch } from "vue";
import ChildTable from "../Controls/ChildTable.vue";

const props = defineProps({
	modelValue: { type: Object, required: true },
	errors: { type: Object, default: () => ({}) },
});

const emit = defineEmits(["update:modelValue", "update:errors"]);

const localModel = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const requiredSimpleFields = ["access_to_internet", "profession", "reason_to_join_krcs"];

const disabilityQueries = {
	disability: (row, allRows, formData) => {
		return {
			disability_category: row.disability_category || null,
		};
	},
};

const reasonsOptions = [
	{ label: "Humanitarian", value: "Humanitarian" },
	{ label: "Social Cohesion", value: "Social Cohesion" },
	{ label: "Personal", value: "Personal" },
];

const internetOptions = [
	{ label: "Yes", value: "Yes" },
	{ label: "No", value: "No" },
	{ label: "Sometimes", value: "Sometimes" },
];

function formatLabel(key) {
	return key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

function validateChildTableRows(rows, config, tableLabel) {
	const tableErrors = new Map();
	if (!Array.isArray(rows)) return tableErrors;

	rows.forEach((row, rowIndex) => {
		const rowErrors = new Map();

		if (config.requiredFields) {
			config.requiredFields.forEach((req) => {
				const fieldName = typeof req === "string" ? req : req.field;
				const condition =
					typeof req === "string" ? true : req.condition ? req.condition(row) : true;

				if (
					condition &&
					(!row[fieldName] ||
						(typeof row[fieldName] === "string" && row[fieldName].trim() === ""))
				) {
					rowErrors.set(fieldName, `${formatLabel(fieldName)} is required.`);
				}
			});
		}

		if (config.dateChecks) {
			config.dateChecks.forEach((check) => {
				const condition = check.condition ? check.condition(row) : true;
				if (condition) {
					const value = row[check.field];
					let errorMsg =
						typeof check.error === "function" ? check.error(row) : check.error;

					if (value && !check.validation(value, row)) {
						rowErrors.set(check.field, `${formatLabel(check.field)} ${errorMsg}`);
					}
				}
			});
		}

		if (config.emailChecks) {
			config.emailChecks.forEach((check) => {
				if (row[check.field] && !isEmailValid(row[check.field])) {
					rowErrors.set(check.field, `${formatLabel(check.field)} ${check.error}`);
				}
			});
		}

		if (config.phoneChecks) {
			config.phoneChecks.forEach((check) => {
				if (row[check.field] && !isPhoneNumberValid(row[check.field])) {
					rowErrors.set(check.field, `${formatLabel(check.field)} ${check.error}`);
				}
			});
		}

		if (rowErrors.size > 0) {
			tableErrors.set(rowIndex, Object.fromEntries(rowErrors));
		}
	});

	return tableErrors;
}

const componentValidationConfig = [
	{ field: "access_to_internet", label: "Access To Internet", type: "simple" },
	{ field: "profession", label: "Profession", type: "simple" },
	{ field: "reason_to_join_krcs", label: "Reason To Join Krcs", type: "simple" },
	{ field: "languages", label: "Languages", type: "multiselect" },
	{ field: "driving_licence", label: "Driving Licence", type: "multiselect" },

	{
		field: "education",
		label: "Education",
		type: "child",
		requiredFields: ["school_univ", "level", "year_of_passing"],
		dateChecks: [
			{
				field: "year_of_passing",
				validation: (date) => isPastDate(date),
				error: "must be a past date.",
			},
		],
	},
	{
		field: "courses",
		label: "Trainings & Certifications",
		type: "child",
		requiredFields: ["course_name", "institution", "start_date", "date_completed"],
		dateChecks: [
			{
				field: "start_date",
				validation: (date) => isPastDate(date),
				error: "must be a past date.",
			},
			{
				field: "date_completed",
				validation: (date) => isPastDate(date),
				error: "must be a past date.",
				condition: (row) => row.date_completed,
			},
			{
				field: "date_completed",
				validation: (date, row) => new Date(date) >= new Date(row.start_date),
				error: (row) => `cannot be before Start Date (${row.start_date}).`,
				condition: (row) => row.start_date && row.date_completed,
			},
		],
	},
	{
		field: "additional_skills",
		label: "Additional Skills",
		type: "child",
		requiredFields: ["additional_skill"],
	},
	{
		field: "licences",
		label: "Licences",
		type: "child",
		requiredFields: [
			"license_type",
			"institution",
			"qualification",
			"valid_from",
			{ field: "license_name", condition: (row) => row.license_type === "Other" },
			{ field: "valid_to", condition: (row) => !row.does_not_expire },
		],
		dateChecks: [
			{
				field: "valid_from",
				validation: (date) => isDateValid(date),
				error: "is not a valid date.",
			},
			{
				field: "valid_to",
				validation: (date) => isDateValid(date),
				error: "is not a valid date.",
				condition: (row) => row.valid_to && row.does_not_expire !== 1,
			},
			{
				field: "valid_to",
				validation: (date, row) => new Date(date) > new Date(row.valid_from),
				error: (row) => `must be after Valid From (${row.valid_from}).`,
				condition: (row) => row.valid_from && row.valid_to && row.does_not_expire !== 1,
			},
		],
	},
];

function onChildErrors(tableName, errMap) {
	const newErrors = { ...props.errors };
	if (!newErrors[1]) newErrors[1] = {};

	const hasErrors =
		errMap &&
		((errMap instanceof Map && errMap.size > 0) ||
			(errMap.constructor === Object && Object.keys(errMap).length > 0));

	if (hasErrors) {
		const errObj = errMap instanceof Map ? Object.fromEntries(errMap) : errMap;
		newErrors[1][tableName] = errObj;
	} else {
		delete newErrors[1][tableName];
		if (Object.keys(newErrors[1]).length === 0) delete newErrors[1];
	}

	emit("update:errors", newErrors);
}

function validateComponentFields() {
	let newErrors = { ...props.errors };
	if (!newErrors[1]) newErrors[1] = {};

	componentValidationConfig.forEach((config) => {
		delete newErrors[1][config.label];
	});

	componentValidationConfig.forEach((config) => {
		const value = localModel.value[config.field];
		const label = config.label;

		if (config.type === "simple" || config.type === "multiselect") {
			if (
				requiredSimpleFields.includes(config.field) &&
				(!value ||
					(Array.isArray(value) && value.length === 0) ||
					(typeof value === "string" && value.length === 0))
			) {
				newErrors[1][label] = `${label} is required.`;
			}
		} else if (config.type === "child") {
			const tableErrors = validateChildTableRows(value, config, label);
			if (tableErrors.size > 0) {
				newErrors[1][label] = Object.fromEntries(tableErrors);
			}
		}
	});

	if (newErrors[1] && Object.keys(newErrors[1]).length === 0) {
		delete newErrors[1];
	}

	emit("update:errors", newErrors);
}

onMounted(() => {
	validateComponentFields();
});

watch(
	localModel,
	() => {
		validateComponentFields();
	},
	{ deep: true },
);
</script>
