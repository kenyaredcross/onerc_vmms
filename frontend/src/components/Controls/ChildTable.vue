<template>
	<div ref="tableRef" class="w-full">
		<div v-if="label" class="text-xs text-ink-gray-5 mb-2">{{ __(label) }}</div>

		<div class="block lg:hidden">
			<div class="flex items-center justify-between mb-3 p-2 bg-surface-gray-1 rounded-lg">
				<div class="flex items-center gap-2">
					<input
						type="checkbox"
						:aria-label="__('Select all rows')"
						@change="toggleSelectAll"
						:checked="allSelected"
						:disabled="rowsRef.length === 0"
						class="cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
					/>
					<span class="text-sm font-medium text-ink-gray-6">
						{{
							selectedRows.size > 0
								? `${selectedRows.size} ${__("selected")}`
								: __("Select All")
						}}
					</span>
				</div>

				<div class="flex items-center gap-1">
					<Button
						v-if="selectedRows.size > 0"
						@click="duplicateSelected"
						variant="ghost"
						size="sm"
						class="!p-1"
						:title="__('Duplicate')"
					>
						<Copy class="size-3" />
					</Button>
					<Button
						v-if="selectedRows.size > 0"
						@click="deleteSelected"
						variant="ghost"
						size="sm"
						class="!p-1"
						:title="__('Delete')"
					>
						<Trash2 class="size-3 text-red-600" />
					</Button>
					<Button
						@click="addRow"
						variant="solid"
						size="sm"
						class="inline-flex items-center !px-2 !py-1 text-xs gap-1"
					>
						+ {{ __("Add") }}
					</Button>
				</div>
			</div>

			<div class="space-y-2">
				<div
					v-for="(row, rowIndex) in rowsRef"
					:key="`mobile-row-${rowIndex}`"
					class="border rounded-lg p-3 transition-all"
					:class="[
						selectedRows.has(rowIndex)
							? 'bg-blue-50 border-blue-200'
							: 'bg-surface-white',
						editingRow === rowIndex ? 'ring-2 ring-blue-300' : '',
						validationErrors.has(rowIndex) &&
						Object.keys(validationErrors.get(rowIndex) || {}).length > 0
							? 'border-red-500'
							: '',
					]"
				>
					<div class="flex items-center justify-between mb-3">
						<div class="flex items-center gap-2">
							<input
								type="checkbox"
								:aria-label="`${__('Select row')} ${rowIndex + 1}`"
								:checked="selectedRows.has(rowIndex)"
								@change="toggleRowSelection(rowIndex)"
								class="cursor-pointer"
							/>
							<span class="text-xs font-medium text-ink-gray-6">
								{{ __("Row") }} {{ rowIndex + 1 }}
							</span>
						</div>
						<Button
							variant="ghost"
							size="sm"
							:aria-label="`${__('Edit row')} ${rowIndex + 1}`"
							@click.stop="openEditModal(rowIndex)"
							class="!p-1"
						>
							<Edit class="size-3 text-ink-gray-7 stroke-1.5" />
						</Button>
					</div>

					<div
						v-if="
							validationErrors.has(rowIndex) &&
							Object.keys(validationErrors.get(rowIndex) || {}).length > 0
						"
						class="top-2 right-2 p-1 bg-red-500 rounded-full"
					>
						<X class="size-3 text-white" />
					</div>

					<div class="space-y-2">
						<div
							v-for="field in getVisibleFieldsForRow(row, rowIndex).slice(0, 3)"
							:key="field.fieldname"
							v-show="!isFieldHidden(field, row)"
							class="flex flex-col gap-1"
						>
							<label class="text-xs text-ink-gray-5 font-medium">
								{{ __(field.label) }}
								<span v-if="isFieldRequired(field, row)" class="text-red-500"
									>*</span
								>
							</label>

							<div
								class="w-full cursor-pointer min-h-[32px] flex items-center"
								:role="field.read_only ? null : 'button'"
								:tabindex="field.read_only ? null : 0"
								@click="
									field.read_only
										? null
										: startEditing(rowIndex, field.fieldname)
								"
								@keydown.enter.prevent="
									field.read_only
										? null
										: startEditing(rowIndex, field.fieldname)
								"
								@keydown.space.prevent="
									field.read_only
										? null
										: startEditing(rowIndex, field.fieldname)
								"
							>
								<component
									v-if="
										editingRow === rowIndex && editingField === field.fieldname
									"
									:is="getFieldComponent(field)"
									v-model="row[field.fieldname]"
									v-bind="getFieldProps(field, rowIndex)"
									@blur="stopEditingAndValidate(rowIndex, field.fieldname)"
									ref="editInputRef"
									class="w-full text-sm"
									:readonly="!!field.read_only"
									@update:model-value="handleLinkedFieldChange(rowIndex, field)"
								/>

								<div v-else class="text-sm text-ink-gray-7 truncate">
									<template v-if="field.fieldtype === 'Check'">
										<input
											type="checkbox"
											:aria-label="__(field.label)"
											:checked="row[field.fieldname]"
											disabled
											class="cursor-pointer"
										/>
									</template>

									<template
										v-else-if="
											['Attach', 'Attach Image', 'Image'].includes(
												field.fieldtype
											)
										"
									>
										<span class="text-blue-600 truncate text-xs">
											{{
												__(row[field.fieldname]?.file_name) ||
												__(row[field.fieldname]?.name) ||
												__(row[field.fieldname]) ||
												"-"
											}}
										</span>
									</template>

									<template v-else>
										{{
											__(formatFieldValue(row[field.fieldname], field)) ||
											"-"
										}}
									</template>
								</div>
							</div>
							<p
								v-if="validationErrors.get(rowIndex)?.[field.fieldname]"
								class="text-xs text-red-500 mt-1"
							>
								{{ __(validationErrors.get(rowIndex)?.[field.fieldname]) }}
							</p>
						</div>

						<div v-if="getVisibleFieldsForRow(row, rowIndex).length > 3" class="pt-1">
							<button
								@click="openEditModal(rowIndex)"
								class="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
							>
								<span
									>{{ __("View all") }}
									{{ getVisibleFieldsForRow(row, rowIndex).length }}
									{{ __("fields") }}</span
								>
								<svg
									class="size-3"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M9 5l7 7-7 7"
									/>
								</svg>
							</button>
						</div>
					</div>
				</div>
			</div>

			<div
				v-if="rowsRef.length === 0"
				class="p-8 text-center text-ink-gray-5 border rounded-lg"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="mx-auto h-8 w-8 mb-2 text-ink-gray-4"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
					stroke-width="1.5"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M12 3c-4.97 0-9 1.343-9 3v12c0 1.657 4.03 3 9 3s9-1.343 9-3V6c0-1.657-4.03-3-9-3z"
					/>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M3 9c0 1.657 4.03 3 9 3s9-1.343 9-3"
					/>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M3 15c0 1.657 4.03 3 9 3s9-1.343 9-3"
					/>
				</svg>
				<div class="text-sm">{{ __("No Data") }}</div>
				<Button @click="addRow" variant="solid" size="sm" class="mt-3">
					<template #prefix><Plus class="size-3" /></template>
					{{ __("Add First Row") }}
				</Button>
			</div>
		</div>

		<div class="hidden lg:block">
			<div class="overflow-x-auto border rounded-md">
				<div
					class="grid items-center gap-4 p-3 bg-surface-gray-1 border-b text-xs sticky top-0"
					:style="{ gridTemplateColumns: gridColumnsStyle }"
				>
					<div class="w-8 flex items-center justify-center">
						<input
							type="checkbox"
							:aria-label="__('Select all rows')"
							@change="toggleSelectAll"
							:checked="allSelected"
							:disabled="rowsRef.length === 0"
							class="cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
						/>
					</div>
					<div
						v-for="field in visibleFields"
						:key="field.fieldname"
						class="font-medium text-ink-gray-6 truncate"
						:title="field.label"
					>
						{{ __(field.label) }}
						<span v-if="field.reqd" class="text-red-500">*</span>
					</div>
					<div class="w-8"></div>
				</div>

				<div
					v-for="(row, rowIndex) in rowsRef"
					:key="`desktop-row-${rowIndex}`"
					class="grid items-center gap-4 p-3 transition-all group"
					:class="[
						rowIndex % 2 === 0 ? 'bg-surface-white' : 'bg-surface-white',
						selectedRows.has(rowIndex) ? 'bg-blue-50' : '',
						editingRow === rowIndex ? 'ring-2 ring-blue-300' : '',
						validationErrors.has(rowIndex) &&
						Object.keys(validationErrors.get(rowIndex) || {}).length > 0
							? 'border-l-4 border-red-500'
							: '',
					]"
					:style="{ gridTemplateColumns: gridColumnsStyle }"
				>
					<div class="w-8 flex items-center justify-center">
						<input
							type="checkbox"
							:aria-label="`${__('Select row')} ${rowIndex + 1}`"
							:checked="selectedRows.has(rowIndex)"
							@change="toggleRowSelection(rowIndex)"
							class="cursor-pointer"
						/>
					</div>

					<template v-for="field in visibleFields" :key="field.fieldname">
						<div
							v-show="!isFieldHidden(field, row)"
							class="w-full"
							:class="{ 'cursor-pointer': !field.read_only }"
							:role="field.read_only ? null : 'button'"
							:tabindex="field.read_only ? null : 0"
							@click="
								field.read_only ? null : startEditing(rowIndex, field.fieldname)
							"
							@keydown.enter.prevent="
								field.read_only ? null : startEditing(rowIndex, field.fieldname)
							"
							@keydown.space.prevent="
								field.read_only ? null : startEditing(rowIndex, field.fieldname)
							"
						>
							<component
								v-if="editingRow === rowIndex && editingField === field.fieldname"
								:is="getFieldComponent(field)"
								v-model="row[field.fieldname]"
								v-bind="getFieldProps(field, rowIndex)"
								@blur="stopEditingAndValidate(rowIndex, field.fieldname)"
								ref="editInputRef"
								:readonly="!!field.read_only"
								:required="isFieldRequired(field, row)"
								@update:model-value="handleLinkedFieldChange(rowIndex, field)"
								:class="{
									'border-red-500':
										validationErrors.get(rowIndex)?.[field.fieldname],
								}"
							/>

							<div
								v-else
								class="text-sm text-ink-gray-7 truncate min-h-[32px] flex items-center"
								:title="formatFieldValue(row[field.fieldname], field) || '-'"
								:class="{
									'border-2 border-red-500 rounded-md p-1':
										validationErrors.get(rowIndex)?.[field.fieldname],
								}"
							>
								<template v-if="field.fieldtype === 'Check'">
									<input
										type="checkbox"
										:aria-label="__(field.label)"
										:checked="row[field.fieldname]"
										disabled
										class="cursor-pointer"
									/>
								</template>

								<template
									v-else-if="
										['Attach', 'Attach Image', 'Image'].includes(
											field.fieldtype
										)
									"
								>
									<span class="text-blue-600 truncate">
										{{
											__(row[field.fieldname]?.file_name) ||
											__(row[field.fieldname]?.name) ||
											__(row[field.fieldname]) ||
											"-"
										}}
									</span>
								</template>

								<template v-else>
									{{ __(formatFieldValue(row[field.fieldname], field)) || "-" }}
								</template>
							</div>
							<p
								v-if="validationErrors.get(rowIndex)?.[field.fieldname]"
								class="text-xs text-red-500 mt-1"
							>
								{{ __(validationErrors.get(rowIndex)?.[field.fieldname]) }}
							</p>
						</div>
					</template>

					<div
						class="flex items-center justify-end opacity-90 group-hover:opacity-100 transition-opacity"
					>
						<Button
							variant="ghost"
							size="sm"
							:aria-label="`${__('Edit row')} ${rowIndex + 1}`"
							@click.stop="openEditModal(rowIndex)"
						>
							<Edit class="size-4 text-ink-gray-7 stroke-1.5" />
						</Button>
					</div>
				</div>

				<div v-if="rowsRef.length === 0" class="p-8 text-center text-ink-gray-5">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="mx-auto h-10 w-10 mb-2 text-ink-gray-4"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
						stroke-width="1.5"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M12 3c-4.97 0-9 1.343-9 3v12c0 1.657 4.03 3 9 3s9-1.343 9-3V6c0-1.657-4.03-3-9-3z"
						/>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M3 9c0 1.657 4.03 3 9 3s9-1.343 9-3"
						/>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M3 15c0 1.657 4.03 3 9 3s9-1.343 9-3"
						/>
					</svg>
					<div class="text-sm">{{ __("No Data") }}</div>
				</div>
			</div>

			<div class="mt-3 flex items-center justify-between">
				<Button v-if="!props.readOnly" @click="addRow" variant="solid" size="sm">
					<template #prefix><Plus class="size-4" /></template>
					{{ __("Add Row") }}
				</Button>

				<div v-if="selectedRows.size > 0" class="flex items-center gap-2">
					<span class="text-xs text-ink-gray-6"
						>{{ selectedRows.size }} {{ __("selected") }}</span
					>
					<Button
						v-if="!props.readOnly && selectedRows.size > 0"
						@click="duplicateSelected"
						variant="ghost"
						size="sm"
						:title="__('Duplicate')"
					>
						<Copy class="size-4 text-ink-gray-7" />
					</Button>

					<Button
						v-if="!props.readOnly && selectedRows.size > 0"
						@click="deleteSelected"
						variant="ghost"
						size="sm"
						:title="__('Delete')"
					>
						<Trash2 class="size-4 text-red-600" />
					</Button>
				</div>
			</div>
		</div>

		<Dialog v-model="editModalOpenModel" :options="{ size: '4xl' }">
			<template #body-title>
				<h3 class="text-base sm:text-lg font-semibold text-ink-gray-7">
					{{ __("Edit Row") }} {{ (editModalRowIndex || 0) + 1 }}
				</h3>
			</template>

			<template #body-content>
				<div class="max-h-[70vh] overflow-y-auto">
					<template
						v-for="(section, sIndex) in getModalLayoutForRow(editModalData)"
						:key="sIndex"
					>
						<div
							class="border-t pt-4 sm:pt-6 mt-4 sm:mt-6 first:border-t-0 first:pt-0 first:mt-0"
						>
							<h4
								v-if="section.label"
								class="text-sm sm:text-base font-semibold text-ink-gray-7 mb-3 sm:mb-4"
							>
								{{ __(section.label) }}
							</h4>

							<div class="flex flex-col md:flex-row -mx-1 sm:-mx-2">
								<div
									v-for="(col, cIndex) in section.columns"
									:key="cIndex"
									class="flex-1 px-1 sm:px-2"
								>
									<div
										v-for="field in col"
										:key="field.fieldname"
										v-show="!isFieldHidden(field, editModalData)"
										class="mb-3 sm:mb-4"
									>
										<template v-if="field.fieldtype === 'Check'">
											<div class="flex items-center gap-2">
												<FormControl
													:type="'checkbox'"
													v-model="editModalData[field.fieldname]"
													v-bind="getFieldProps(field)"
													:readonly="!!field.read_only"
													@update:model-value="
														handleLinkedFieldChange(
															editModalRowIndex,
															field,
															editModalData
														)
													"
												/>
												<label class="text-sm text-ink-gray-7">
													{{ __(field.label) }}
													<span
														v-if="
															isFieldRequired(field, editModalData)
														"
														class="text-red-500"
														>*</span
													>
												</label>
											</div>
										</template>

										<template v-else>
											<label class="block text-sm text-ink-gray-7 mb-1">
												{{ __(field.label) }}
												<span
													v-if="isFieldRequired(field, editModalData)"
													class="text-red-500"
													>*</span
												>
											</label>

											<component
												:is="getFieldComponent(field)"
												v-model="editModalData[field.fieldname]"
												v-bind="getFieldProps(field)"
												:rows="field.fieldtype === 'Long Text' ? 8 : 4"
												:required="isFieldRequired(field, editModalData)"
												:readonly="!!field.read_only"
												class="text-sm"
												@update:model-value="
													handleLinkedFieldChange(
														editModalRowIndex,
														field,
														editModalData
													)
												"
												:class="{
													'border-red-500': validationErrors.get(
														editModalRowIndex || -1
													)?.[field.fieldname],
												}"
											/>
											<p
												v-if="
													editModalRowIndex !== null &&
													validationErrors.get(editModalRowIndex)?.[
														field.fieldname
													]
												"
												class="text-xs text-red-500 mt-1"
											>
												{{
													__(
														validationErrors.get(editModalRowIndex)?.[
															field.fieldname
														]
													)
												}}
											</p>
										</template>
									</div>
								</div>
							</div>
						</div>
					</template>
				</div>
			</template>

			<template #actions>
				<div class="flex items-center justify-end gap-2 flex-wrap">
					<Button
						@click="cancelEditModal"
						variant="ghost"
						size="sm"
						class="flex-1 sm:flex-none"
					>
						{{ __("Cancel") }}
					</Button>
					<Button
						v-if="!props.readOnly"
						@click="saveEditModal"
						variant="solid"
						size="sm"
					>
						{{ __("Save Changes") }}
					</Button>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import {
	Button,
	createResource,
	Dialog,
	FormControl,
	Textarea,
	TextEditor,
	TextInput,
} from "frappe-ui";
import { Copy, Edit, Plus, Trash2, X } from "lucide-vue-next";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import LinkControl from "./Link.vue";
import Uploader from "./Uploader.vue";

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	doctype: { type: String, required: true },
	label: { type: String, default: "" },
	fieldQueries: { type: Object, default: () => ({}) },
	formData: { type: Object, default: () => ({}) },
	autoEditGrid: { type: Boolean, default: false },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "validationErrors"]);

const rowsRef = ref([]);
const tableRef = ref(null);
const selectedRows = ref(new Set());
const editingRow = ref(null);
const editingField = ref(null);
const editInputRef = ref(null);
const editModalOpen = ref(false);
const editModalOpenModel = computed({
	get: () => editModalOpen.value,
	set: (val) => {
		if (val) editModalOpen.value = true;
		else closeEditModal();
	},
});
const editModalRowIndex = ref(null);
const editModalData = ref({});
const isUpdating = ref(false);
const editableGrid = ref(false);

const validationErrors = ref(new Map());

defineExpose({
	validateBeforeSave,
});

const fieldComponentMap = {
	Attach: Uploader,
	"Attach Image": Uploader,
	Image: Uploader,
	Autocomplete: TextInput,
	Barcode: TextInput,
	Button: Button,
	Check: "checkbox",
	Code: TextEditor,
	Color: "color",
	Currency: "number",
	Data: TextInput,
	Date: "date",
	Datetime: "datetime-local",
	Duration: TextInput,
	"Dynamic Link": LinkControl,
	Float: "number",
	Geolocation: "map",
	Heading: "heading",
	HTML: "html",
	"HTML Editor": TextEditor,
	Icon: "icon",
	Int: "number",
	JSON: Textarea,
	Link: LinkControl,
	"Long Text": Textarea,
	"Markdown Editor": TextEditor,
	Password: "password",
	Percent: "number",
	Phone: "tel",
	Rating: "rating",
	"Read Only": TextInput,
	Select: "select",
	Signature: "signature",
	"Small Text": Textarea,
	Table: "childtable",
	"Table MultiSelect": "multiselecttable",
	Text: TextInput,
	"Text Editor": TextEditor,
	Time: "time",
};

function getFieldComponent(field) {
	const comp = fieldComponentMap[field.fieldtype];

	const formControlTypes = [
		"Int",
		"Float",
		"Currency",
		"Data",
		"Date",
		"Datetime",
		"Time",
		"Email",
		"Password",
		"Tel",
		"Search",
		"Check",
		"Select",
	];

	if (comp && typeof comp !== "string") return comp;
	if (formControlTypes.includes(field.fieldtype)) return FormControl;

	return comp || FormControl;
}

function evaluateExpression(expression, doc) {
	if (!expression) return false;

	try {
		let cleanExpression = expression.trim();
		if (cleanExpression.startsWith("eval:")) {
			cleanExpression = cleanExpression.substring(5).trim();
		}

		const evalFunc = new Function("doc", `with(doc) { return ${cleanExpression}; }`);
		return evalFunc(doc);
	} catch (error) {
		console.error("Error evaluating expression:", expression, error);
		return false;
	}
}

function isFieldHidden(field, rowData) {
	if (field.hidden) return true;

	if (field.depends_on) {
		return !evaluateExpression(field.depends_on, rowData);
	}

	return false;
}

function isFieldRequired(field, rowData) {
	if (field.reqd) return true;

	if (field.mandatory_depends_on) {
		return evaluateExpression(field.mandatory_depends_on, rowData);
	}

	return false;
}

function getVisibleFieldsForRow(rowData, rowIndex) {
	return visibleFields.value.filter((field) => !isFieldHidden(field, rowData));
}

function getModalLayoutForRow(rowData) {
	const layout = [];
	let currentSection = { type: "section", columns: [[]] };

	for (const field of doctypeFields.value) {
		if (field.fieldtype === "Section Break") {
			if (currentSection.columns.some((col) => col.length > 0)) {
				layout.push(currentSection);
			}

			currentSection = { type: "section", label: field.label, columns: [[]] };
		} else if (field.fieldtype === "Column Break") {
			currentSection.columns.push([]);
		} else if (!isFieldHidden(field, rowData)) {
			currentSection.columns[currentSection.columns.length - 1].push(field);
		}
	}

	if (currentSection.columns.some((col) => col.length > 0)) {
		layout.push(currentSection);
	}

	return layout;
}

function getFieldProps(field, rowIndex) {
	const props = {
		readonly: !!field.read_only,
		required: false,
	};

	if (rowIndex !== undefined && rowsRef.value[rowIndex]) {
		props.required = isFieldRequired(field, rowsRef.value[rowIndex]);
	}

	switch (field.fieldtype) {
		case "Data":
			props.type = "text";
			break;
		case "Check":
			props.type = "checkbox";
			break;

		case "Int":
		case "Float":
		case "Currency":
			props.type = "number";
			break;

		case "Date":
			props.type = "date";
			break;

		case "Datetime":
			props.type = "datetime-local";
			break;

		case "Time":
			props.type = "time";
			break;

		case "Email":
			props.type = "email";
			break;

		case "Password":
			props.type = "password";
			break;

		case "Tel":
			props.type = "tel";
			break;

		case "Search":
			props.type = "search";
			break;

		case "Select":
			props.type = "select";
			props.options = getSelectOptions(field);
			break;

		case "Link":
		case "Dynamic Link":
			props.doctype = field.options;
			props.description = field.description || "";

			let baseFilters =
				typeof field.get_query === "function" ? field.get_query() : field.get_query || {};

			if (props.fieldQueries && props.fieldQueries[field.fieldname]) {
				const row = rowIndex !== undefined ? rowsRef.value[rowIndex] : {};
				const dynamicFilters = props.fieldQueries[field.fieldname](
					row,
					rowsRef.value,
					props.formData
				);
				baseFilters = { ...baseFilters, ...dynamicFilters };
			}

			props.filters = baseFilters;

			break;

		case "Attach":
		case "Attach Image":
		case "Image":
			props.fileTypes = [".pdf", ".jpg", ".jpeg", ".png"];
			props.multi = false;
			props.maxFileSize = 10;
			props.success = (file) => {
				if (rowIndex !== undefined) handleUploadSuccess(rowIndex, field.fieldname, file);
			};
			break;
	}

	return props;
}

function getSelectOptions(field) {
	if (field.options) {
		return field.options
			.split("\n")
			.map((o) => o.trim())
			.filter((o) => o);
	}
	return [];
}

function formatFieldValue(value, field) {
	if (field.fieldtype === "Check") return value ? "Yes" : "No";
	return value;
}

function handleUploadSuccess(rowIndex, fieldname, file) {
	if (rowIndex !== undefined && rowsRef.value[rowIndex]) {
		rowsRef.value[rowIndex][fieldname] = file;
		validateRow(rowIndex);
	}
}

async function fetchLinkedFieldData(linkDoctype, linkName, targetField) {
	if (!linkName) return null;

	const linkedDoc = createResource({
		url: "frappe.client.get_value",
		params: {
			doctype: linkDoctype,
			filters: linkName,
			fieldname: targetField,
		},
		auto: false,
	});

	try {
		const response = await linkedDoc.fetch();

		if (response && !Array.isArray(response)) {
			return response?.[targetField] ?? null;
		}

		if (Array.isArray(response) && response.length > 0) {
			return response[0]?.[targetField] ?? null;
		}

		return null;
	} catch (error) {
		console.error(
			`Error fetching linked field: ${linkDoctype}/${linkName}.${targetField}`,
			error
		);
		return null;
	}
}

async function handleLinkedFieldChange(rowIndex, changedField, dataRef) {
	if (rowIndex === null) return;

	const currentRow = dataRef || rowsRef.value[rowIndex];

	const fieldsToUpdate = doctypeFields.value.filter(
		(f) => f.fetch_from && f.fetch_from.startsWith(`${changedField.fieldname}.`)
	);

	for (const field of fieldsToUpdate) {
		const [sourceLinkField, targetField] = field.fetch_from.split(".");

		if (sourceLinkField === changedField.fieldname && currentRow[changedField.fieldname]) {
			const linkDoctype = changedField.options;
			const linkName = currentRow[changedField.fieldname];

			if (linkDoctype && linkName) {
				const fetchedValue = await fetchLinkedFieldData(
					linkDoctype,
					linkName,
					targetField
				);

				if (dataRef) {
					dataRef[field.fieldname] = fetchedValue;
				} else {
					rowsRef.value[rowIndex][field.fieldname] = fetchedValue;
				}
			} else {
				if (dataRef) {
					dataRef[field.fieldname] = getDefaultValue(field);
				} else {
					rowsRef.value[rowIndex][field.fieldname] = getDefaultValue(field);
				}
			}
		}
	}

	if (changedField.fetch_from && changedField.fieldtype === "Link") {
		const [sourceLinkField, targetField] = changedField.fetch_from.split(".");
		if (sourceLinkField === changedField.fieldname) {
			const linkDoctype = changedField.options;
			const linkName = currentRow[changedField.fieldname];

			if (linkDoctype && linkName) {
				const fetchedValue = await fetchLinkedFieldData(
					linkDoctype,
					linkName,
					targetField
				);
				if (dataRef) {
					dataRef[changedField.fieldname] = fetchedValue;
				} else {
					rowsRef.value[rowIndex][changedField.fieldname] = fetchedValue;
				}
			}
		}
	}
}

const doctypeMeta = createResource({
	url: "frappe.desk.form.load.getdoctype",
	params: { doctype: props.doctype, with_parent: 1, ignore_permissions: 1 },
	auto: true,
});

const doctypeFields = computed(() => {
	if (!doctypeMeta.data?.docs) return [];

	const targetDoc = doctypeMeta.data.docs.find((d) => d.name === props.doctype);
	if (!targetDoc?.fields) return [];

	const fields = targetDoc.fields.map((f) => ({
		...f,
		read_only: f.read_only == 1,
		hidden: f.hidden == 1,
		reqd: f.reqd == 1,
	}));

	const fieldsToShow = fields.filter((f) => !f.hidden);

	const editableGridVal = targetDoc.editable_grid;
	editableGrid.value = editableGridVal === 1 || editableGridVal === "1";

	const fieldOrder = targetDoc.field_order
		? targetDoc.field_order.split("\n").map((f) => f.trim())
		: [];

	if (fieldOrder.length > 0) {
		return fieldsToShow.sort((a, b) => {
			const posA = fieldOrder.indexOf(a.fieldname);
			const posB = fieldOrder.indexOf(b.fieldname);

			if (posA !== -1 && posB !== -1) {
				return posA - posB;
			}

			if (posA !== -1) return -1;
			if (posB !== -1) return 1;

			return (a.idx || 0) - (b.idx || 0);
		});
	}

	return fieldsToShow.sort((a, b) => (a.idx || 0) - (b.idx || 0));
});

const visibleFields = computed(() => {
	const baseFields = doctypeFields.value.filter(
		(f) => !["Section Break", "Column Break"].includes(f.fieldtype)
	);

	const listViewFields = baseFields.filter((field) => {
		if (!field.depends_on) return true;

		const simpleConditions = [/^eval:\s*["']?[^"']*["']?\s*$/, /^["']?[^"']*["']?\s*$/];

		return simpleConditions.some((pattern) => pattern.test(field.depends_on.trim()));
	});

	const vf = listViewFields.filter((f) => f.in_list_view);
	return vf.length > 0 ? vf : listViewFields.slice(0, 5);
});

const modalLayout = computed(() => {
	const layout = [];
	let currentSection = { type: "section", columns: [[]] };

	for (const field of doctypeFields.value) {
		if (field.fieldtype === "Section Break") {
			if (currentSection.columns.some((col) => col.length > 0)) {
				layout.push(currentSection);
			}

			currentSection = { type: "section", label: field.label, columns: [[]] };
		} else if (field.fieldtype === "Column Break") {
			currentSection.columns.push([]);
		} else {
			currentSection.columns[currentSection.columns.length - 1].push(field);
		}
	}

	if (currentSection.columns.some((col) => col.length > 0)) {
		layout.push(currentSection);
	}

	return layout;
});

const gridColumnsStyle = computed(() => {
	const cols = visibleFields.value.length;
	return ["40px", ...Array(cols).fill("1fr"), "40px"].join(" ");
});

function initializeRows() {
	if (isUpdating.value) return;
	rowsRef.value = (props.modelValue || []).map((r) => ensureRowShape(r));

	validateAllRows();
}

function ensureRowShape(row) {
	const shaped = { ...(row || {}) };
	doctypeFields.value.forEach((field) => {
		if (
			!["Section Break", "Column Break"].includes(field.fieldtype) &&
			!(field.fieldname in shaped)
		) {
			shaped[field.fieldname] = getDefaultValue(field);
		}
	});
	return shaped;
}

function getDefaultValue(field) {
	if (field.fieldtype === "Check") return 0;
	if (["Int", "Float", "Currency"].includes(field.fieldtype)) return 0;

	return field.default || "";
}

onMounted(() => {
	watch(
		() => doctypeMeta.data,
		() => {
			if (doctypeMeta.data) initializeRows();
		},
		{ immediate: true }
	);
});

watch(
	() => rowsRef.value.map((row) => ({ ...row })),
	() => {
		rowsRef.value.forEach((_, idx) => {
			validateRow(idx);
		});
		emit("validationErrors", validationErrors.value);
	},
	{ deep: true, immediate: true }
);

watch(
	() => props.modelValue,
	(nv) => {
		if (isUpdating.value) return;
		if (nv && Array.isArray(nv) && doctypeFields.value.length > 0) {
			const newRows = nv.map((r) => ensureRowShape(r));
			if (JSON.stringify(newRows) !== JSON.stringify(rowsRef.value)) {
				rowsRef.value = newRows;
				validateAllRows();
			}
		}
	},
	{ deep: true }
);

watch(
	rowsRef,
	(nv) => {
		if (isUpdating.value) return;
		isUpdating.value = true;
		nextTick(() => {
			const cleanedRows = nv.map((r) => {
				const cleaned = { ...r };
				delete cleaned.__is_editing;
				return cleaned;
			});

			emit("update:modelValue", cleanedRows);
			nextTick(() => {
				isUpdating.value = false;
			});
		});
	},
	{ deep: true }
);

function validateRow(rowIndex) {
	const row = rowsRef.value[rowIndex];
	if (!row) return {};

	const errors = {};

	for (const field of doctypeFields.value) {
		if (isFieldHidden(field, row)) {
			continue;
		}

		if (isFieldRequired(field, row)) {
			const value = row[field.fieldname];
			const isEmpty = value === null || value === undefined || value === "";

			if (
				isEmpty ||
				(field.fieldtype === "Link" && value === "") ||
				(field.fieldtype === "Check" && value === 0)
			) {
				errors[field.fieldname] = `${field.label} is required.`;
			}
		}
	}

	if (Object.keys(errors).length > 0) {
		validationErrors.value.set(rowIndex, errors);
	} else {
		validationErrors.value.delete(rowIndex);
	}

	emit("validationErrors", new Map(validationErrors.value));

	return errors;
}

function validateAllRows() {
	validationErrors.value.clear();
	let allValid = true;

	rowsRef.value.forEach((_, rowIndex) => {
		const errors = validateRow(rowIndex);
		if (Object.keys(errors).length > 0) {
			allValid = false;
		}
	});

	validationErrors.value = new Map(validationErrors.value);

	emit("validationErrors", new Map(validationErrors.value));

	return allValid;
}

function validateBeforeSave() {
	const result = validateAllRows();
	emit("validationErrors", new Map(validationErrors.value));
	return result;
}

function stopEditingAndValidate(rowIndex, fieldname) {
	setTimeout(() => {
		editingRow.value = null;
		editingField.value = null;

		validateRow(rowIndex);
	}, 150);
}

function addRow() {
	const newRow = {};
	doctypeFields.value.forEach((field) => {
		if (!["Section Break", "Column Break"].includes(field.fieldtype)) {
			newRow[field.fieldname] = getDefaultValue(field);
		}
	});

	rowsRef.value.push(newRow);
	const newIndex = rowsRef.value.length - 1;

	validateRow(newIndex);
	openEditModal(newIndex);
}

function duplicateSelected() {
	const indices = Array.from(selectedRows.value).sort((a, b) => b - a);
	const newIndices = [];

	indices.forEach((idx) => {
		const duplicate = { ...rowsRef.value[idx] };
		rowsRef.value.splice(idx + 1, 0, duplicate);
		newIndices.push(idx + 1);
	});

	selectedRows.value.clear();

	newIndices.forEach(validateRow);
}

function deleteSelected() {
	const indices = Array.from(selectedRows.value).sort((a, b) => b - a);
	indices.forEach((idx) => {
		rowsRef.value.splice(idx, 1);
		validationErrors.value.delete(idx);
	});
	selectedRows.value.clear();

	validateAllRows();
}

function toggleRowSelection(idx) {
	if (selectedRows.value.has(idx)) {
		selectedRows.value.delete(idx);
	} else {
		selectedRows.value.add(idx);
	}
}

const allSelected = computed(() => {
	return rowsRef.value.length > 0 && selectedRows.value.size === rowsRef.value.length;
});

function toggleSelectAll() {
	if (allSelected.value) {
		selectedRows.value.clear();
	} else {
		rowsRef.value.forEach((_, idx) => selectedRows.value.add(idx));
	}
}

function startEditing(rowIndex, fieldname) {
	const field = doctypeFields.value.find((f) => f.fieldname === fieldname);
	if (field?.read_only) return;

	editingRow.value = rowIndex;
	editingField.value = fieldname;
	nextTick(() => {
		if (editInputRef.value?.el) {
			editInputRef.value.el.focus();
		}
	});
}

function openEditModal(idx) {
	editModalRowIndex.value = idx;

	editModalData.value = JSON.parse(JSON.stringify(rowsRef.value[idx]));
	editModalOpen.value = true;
}

function closeEditModal() {
	editModalOpen.value = false;
	editModalRowIndex.value = null;
	editModalData.value = {};
}

function cancelEditModal() {
	const rowIndex = editModalRowIndex.value;
	if (rowIndex === null) return;

	validateModalData(rowIndex, editModalData.value);

	rowsRef.value[rowIndex] = {
		...rowsRef.value[rowIndex],
		...editModalData.value,
	};

	closeEditModal();
}

function saveEditModal() {
	const rowIndex = editModalRowIndex.value;
	if (rowIndex === null) return;

	const errors = validateModalData(rowIndex, editModalData.value);

	if (Object.keys(errors).length > 0) {
		return;
	}

	rowsRef.value[rowIndex] = {
		...rowsRef.value[rowIndex],
		...editModalData.value,
	};

	validationErrors.value.delete(rowIndex);

	closeEditModal();
}

function validateModalData(rowIndex, data) {
	const errors = {};

	for (const field of doctypeFields.value) {
		if (isFieldHidden(field, data)) {
			continue;
		}

		if (isFieldRequired(field, data)) {
			const value = data[field.fieldname];
			const isEmpty = value === null || value === undefined || value === "";

			if (
				isEmpty ||
				(field.fieldtype === "Link" && value === "") ||
				(field.fieldtype === "Check" && value === 0)
			) {
				errors[field.fieldname] = `${field.label} is required.`;
			}
		}
	}

	if (Object.keys(errors).length > 0) {
		validationErrors.value.set(rowIndex, errors);
	} else {
		validationErrors.value.delete(rowIndex);
	}
	validationErrors.value = new Map(validationErrors.value);

	return errors;
}

// Add this watch after the existing watches
watch(
	() => rowsRef.value.map((row) => ({ ...row })),
	(newRows, oldRows) => {
		// Re-evaluate depends_on and mandatory_depends_on for all rows
		newRows.forEach((row, rowIndex) => {
			// Trigger re-validation to update required fields
			validateRow(rowIndex);

			// Force reactivity update for modal if it's open
			if (editModalOpen.value && editModalRowIndex.value === rowIndex) {
				editModalData.value = { ...editModalData.value };
			}
		});
	},
	{ deep: true }
);

// Add this watch specifically for modal data changes
watch(
	() => ({ ...editModalData.value }),
	(newData) => {
		if (editModalOpen.value && editModalRowIndex.value !== null) {
			// Re-validate modal data when any field changes
			validateModalData(editModalRowIndex.value, newData);
		}
	},
	{ deep: true }
);
</script>
