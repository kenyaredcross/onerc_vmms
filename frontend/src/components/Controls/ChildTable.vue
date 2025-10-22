<template>
  <div ref="tableRef" class="w-full">
    <div v-if="label" class="text-xs text-ink-gray-5 mb-2">{{ label }}</div>

    <div class="block lg:hidden">
      <div
        class="flex items-center justify-between mb-3 p-2 bg-surface-gray-1 rounded-lg"
      >
        <div class="flex items-center gap-2">
          <input
            type="checkbox"
            @change="toggleSelectAll"
            :checked="allSelected"
            :disabled="rowsRef.length === 0"
            class="cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
          />
          <span class="text-sm font-medium text-ink-gray-6">
            {{
              selectedRows.size > 0
                ? `${selectedRows.size} selected`
                : "Select All"
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
            title="Duplicate"
          >
            <Copy class="size-3" />
          </Button>
          <Button
            v-if="selectedRows.size > 0"
            @click="deleteSelected"
            variant="ghost"
            size="sm"
            class="!p-1"
            title="Delete"
          >
            <Trash2 class="size-3 text-red-600" />
          </Button>
          <Button
            @click="addRow"
            variant="solid"
            size="sm"
            class="inline-flex items-center !px-2 !py-1 text-xs gap-1"
          >
            + Add
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
              : 'bg-white',
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
                :checked="selectedRows.has(rowIndex)"
                @change="toggleRowSelection(rowIndex)"
                class="cursor-pointer"
              />
              <span class="text-xs font-medium text-ink-gray-6">
                Row {{ rowIndex + 1 }}
              </span>
            </div>
            <Button
              variant="ghost"
              size="sm"
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
              v-for="field in visibleFields.slice(0, 3)"
              :key="field.fieldname"
              v-show="!field.hidden"
              class="flex flex-col gap-1"
            >
              <label class="text-xs text-ink-gray-5 font-medium">
                {{ field.label }}
                <span v-if="field.reqd" class="text-red-500">*</span>
              </label>

              <div
                class="w-full cursor-pointer min-h-[32px] flex items-center"
                @click="
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
                        row[field.fieldname]?.file_name ||
                        row[field.fieldname]?.name ||
                        row[field.fieldname] ||
                        "-"
                      }}
                    </span>
                  </template>

                  <template v-else>
                    {{ formatFieldValue(row[field.fieldname], field) || "-" }}
                  </template>
                </div>
              </div>
              <p
                v-if="validationErrors.get(rowIndex)?.[field.fieldname]"
                class="text-xs text-red-500 mt-1"
              >
                {{ validationErrors.get(rowIndex)?.[field.fieldname] }}
              </p>
            </div>

            <div v-if="visibleFields.length > 3" class="pt-1">
              <button
                @click="openEditModal(rowIndex)"
                class="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                <span>View all {{ visibleFields.length }} fields</span>
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
        <div class="text-sm">No Data</div>
        <Button @click="addRow" variant="solid" size="sm" class="mt-3">
          <template #prefix><Plus class="size-3" /></template>
          Add First Row
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
            {{ field.label }}
            <span v-if="field.reqd" class="text-red-500">*</span>
          </div>
          <div class="w-8"></div>
        </div>

        <div
          v-for="(row, rowIndex) in rowsRef"
          :key="`desktop-row-${rowIndex}`"
          class="grid items-center gap-4 p-3 transition-all group"
          :class="[
            rowIndex % 2 === 0 ? 'bg-white' : 'bg-surface-white',
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
              :checked="selectedRows.has(rowIndex)"
              @change="toggleRowSelection(rowIndex)"
              class="cursor-pointer"
            />
          </div>

          <template v-for="field in visibleFields" :key="field.fieldname">
            <div
              class="w-full"
              :class="{ 'cursor-pointer': !field.read_only }"
              @click="
                field.read_only ? null : startEditing(rowIndex, field.fieldname)
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
                :readonly="!!field.read_only"
                :required="!!field.reqd"
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
                      row[field.fieldname]?.file_name ||
                      row[field.fieldname]?.name ||
                      row[field.fieldname] ||
                      "-"
                    }}
                  </span>
                </template>

                <template v-else>
                  {{ formatFieldValue(row[field.fieldname], field) || "-" }}
                </template>
              </div>
              <p
                v-if="validationErrors.get(rowIndex)?.[field.fieldname]"
                class="text-xs text-red-500 mt-1"
              >
                {{ validationErrors.get(rowIndex)?.[field.fieldname] }}
              </p>
            </div>
          </template>

          <div
            class="flex items-center justify-end opacity-90 group-hover:opacity-100 transition-opacity"
          >
            <Button
              variant="ghost"
              size="sm"
              @click.stop="openEditModal(rowIndex)"
            >
              <Edit class="size-4 text-ink-gray-7 stroke-1.5" />
            </Button>
          </div>
        </div>

        <div
          v-if="rowsRef.length === 0"
          class="p-8 text-center text-ink-gray-5"
        >
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
          <div class="text-sm">No Data</div>
        </div>
      </div>

      <div class="mt-3 flex items-center justify-between">
        <Button
          v-if="!props.readOnly"
          @click="addRow"
          variant="solid"
          size="sm"
        >
          <template #prefix><Plus class="size-4" /></template>
          Add Row
        </Button>

        <div v-if="selectedRows.size > 0" class="flex items-center gap-2">
          <span class="text-xs text-ink-gray-6"
            >{{ selectedRows.size }} selected</span
          >
          <Button
            v-if="!props.readOnly && selectedRows.size > 0"
            @click="duplicateSelected"
            variant="ghost"
            size="sm"
            title="Duplicate"
          >
            <Copy class="size-4 text-ink-gray-7" />
          </Button>

          <Button
            v-if="!props.readOnly && selectedRows.size > 0"
            @click="deleteSelected"
            variant="ghost"
            size="sm"
            title="Delete"
          >
            <Trash2 class="size-4 text-red-600" />
          </Button>
        </div>
      </div>
    </div>

    <div
      v-if="editModalOpen"
      class="fixed inset-0 z-10 bg-black bg-opacity-50 flex items-center justify-center p-2 sm:p-4"
      @click.self="closeEditModal"
    >
      <div
        class="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[95vh] overflow-hidden flex flex-col m-2"
      >
        <div
          class="flex items-center justify-between p-3 sm:p-4 border-b bg-surface-gray-1"
        >
          <h3 class="text-base sm:text-lg font-semibold text-ink-gray-7">
            Edit Row {{ (editModalRowIndex || 0) + 1 }}
          </h3>
          <button
            @click="cancelEditModal"
            class="text-ink-gray-5 hover:text-ink-gray-7 transition-colors p-1"
          >
            <X class="size-4 sm:size-5" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6">
          <template v-for="(section, sIndex) in modalLayout" :key="sIndex">
            <div
              class="border-t pt-4 sm:pt-6 mt-4 sm:mt-6 first:border-t-0 first:pt-0 first:mt-0"
            >
              <h4
                v-if="section.label"
                class="text-sm sm:text-base font-semibold text-ink-gray-7 mb-3 sm:mb-4"
              >
                {{ section.label }}
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
                    v-show="!field.hidden"
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
                          {{ field.label }}
                          <span v-if="field.reqd" class="text-red-500">*</span>
                        </label>
                      </div>
                    </template>

                    <template v-else>
                      <label class="block text-sm text-ink-gray-7 mb-1">
                        {{ field.label }}
                        <span v-if="field.reqd" class="text-red-500">*</span>
                      </label>

                      <component
                        :is="getFieldComponent(field)"
                        v-model="editModalData[field.fieldname]"
                        v-bind="getFieldProps(field)"
                        :rows="field.fieldtype === 'Long Text' ? 8 : 4"
                        :required="field.reqd"
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
                          validationErrors.get(editModalRowIndex || -1)?.[
                            field.fieldname
                          ]
                        "
                        class="text-xs text-red-500 mt-1"
                      >
                        {{
                          validationErrors.get(editModalRowIndex || -1)?.[
                            field.fieldname
                          ]
                        }}
                      </p>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <div
          class="flex items-center justify-end gap-2 p-3 sm:p-4 border-t bg-surface-gray-1 flex-wrap"
        >
          <Button
            @click="cancelEditModal"
            variant="ghost"
            size="sm"
            class="flex-1 sm:flex-none"
          >
            Cancel
          </Button>
          <Button
            v-if="!props.readOnly"
            @click="saveEditModal"
            variant="solid"
            size="sm"
          >
            Save Changes
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from "vue";
import {
  Button,
  FormControl,
  createResource,
  Textarea,
  TextEditor,
  TextInput,
} from "frappe-ui";
import Uploader from "./Uploader.vue";
import LinkControl from "./Link.vue";
import { Plus, Trash2, Copy, Edit, X } from "lucide-vue-next";

interface DocField {
  fieldname: string;
  fieldtype: string;
  label: string;
  options?: string;
  description?: string;
  get_query?: any;
  in_list_view: number | boolean;
  idx: number;

  read_only?: number | boolean;
  hidden?: number | boolean;
  reqd?: number | boolean;
  fetch_from?: string;
  default?: any;
}

type RowData = Record<string, any>;

const props = withDefaults(
  defineProps<{
    modelValue?: RowData[];
    doctype: string;
    label?: string;
    fieldQueries?: Record<
      string,
      (row: RowData, allRows: RowData[], formData?: any) => any
    >;
    formData?: RowData;
    autoEditGrid?: boolean;
    readOnly?: boolean;
  }>(),
  { modelValue: () => [], label: "", fieldQueries: () => ({}), readOnly: false }
);

const emit = defineEmits<{
  (e: "update:modelValue", value: RowData[]): void;
  (e: "validationErrors", errors: Map<number, Record<string, string>>): void;
}>();

const rowsRef = ref<RowData[]>([]);
const tableRef = ref<HTMLElement | null>(null);
const selectedRows = ref(new Set<number>());
const editingRow = ref<number | null>(null);
const editingField = ref<string | null>(null);
const editInputRef = ref<any>(null);
const editModalOpen = ref(false);
const editModalRowIndex = ref<number | null>(null);
const editModalData = ref<RowData>({});
const isUpdating = ref(false);
const editableGrid = ref(false);

const validationErrors = ref(new Map<number, Record<string, string>>());

defineExpose({
  validateBeforeSave,
});

const fieldComponentMap: Record<string, any> = {
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

function getFieldComponent(field: DocField) {
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

function getFieldProps(field: DocField, rowIndex?: number) {
  const props: Record<string, any> = {
    readonly: !!field.read_only,
    required: !!field.reqd,
  };

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
        typeof field.get_query === "function"
          ? field.get_query()
          : field.get_query || {};

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
      props.fileTypes = [".pdf", ".jpg", ".png", ".doc", ".docx"];
      props.multi = false;
      props.maxFileSize = 10;
      props.success = (file: any) => {
        if (rowIndex !== undefined)
          handleUploadSuccess(rowIndex, field.fieldname, file);
      };
      break;
  }

  return props;
}

function getSelectOptions(field: DocField) {
  if (field.options) {
    return field.options
      .split("\n")
      .map((o) => o.trim())
      .filter((o) => o);
  }
  return [];
}

function formatFieldValue(value: any, field: DocField) {
  if (field.fieldtype === "Check") return value ? "Yes" : "No";
  return value;
}
function handleUploadSuccess(rowIndex: number, fieldname: string, file: any) {
  if (rowIndex !== undefined && rowsRef.value[rowIndex]) {
    rowsRef.value[rowIndex][fieldname] = file;

    validateRow(rowIndex);
  }
}

async function fetchLinkedFieldData(
  linkDoctype: string,
  linkName: string,
  targetField: string
): Promise<any> {
  if (!linkName) return null;

  const linkedDoc = createResource({
    url: "non_profit.non_profit.api.search_doctype",
    params: {
      doctype: linkDoctype,
      name: linkName,
      fields: [targetField],
      ignore_permissions: 1,
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

async function handleLinkedFieldChange(
  rowIndex: number | null,
  changedField: DocField,
  dataRef?: RowData
) {
  if (rowIndex === null) return;

  const currentRow = dataRef || rowsRef.value[rowIndex];

  const fieldsToUpdate = doctypeFields.value.filter(
    (f) => f.fetch_from && f.fetch_from.startsWith(`${changedField.fieldname}.`)
  );

  for (const field of fieldsToUpdate) {
    const [sourceLinkField, targetField] = field.fetch_from!.split(".");

    if (
      sourceLinkField === changedField.fieldname &&
      currentRow[changedField.fieldname]
    ) {
      const linkDoctype = changedField.options as string;
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
    const [sourceLinkField, targetField] = changedField.fetch_from!.split(".");
    if (sourceLinkField === changedField.fieldname) {
      const linkDoctype = changedField.options as string;
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

const doctypeFields = computed<DocField[]>(() => {
  if (!doctypeMeta.data?.docs) return [];

  const targetDoc = doctypeMeta.data.docs.find(
    (d: any) => d.name === props.doctype
  );
  if (!targetDoc?.fields) return [];

  const fields: DocField[] = targetDoc.fields.map((f: any) => ({
    ...f,

    read_only: f.read_only == 1,
    hidden: f.hidden == 1,
    reqd: f.reqd == 1,
  }));

  const fieldsToShow = fields.filter((f) => !f.hidden);

  const editableGridVal = targetDoc.editable_grid;
  editableGrid.value = editableGridVal === 1 || editableGridVal === "1";

  const fieldOrder = targetDoc.field_order
    ? targetDoc.field_order.split("\n").map((f: string) => f.trim())
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
  const vf = doctypeFields.value.filter(
    (f) =>
      f.in_list_view && !["Section Break", "Column Break"].includes(f.fieldtype)
  );
  return vf.length > 0
    ? vf
    : doctypeFields.value
        .filter((f) => !["Section Break", "Column Break"].includes(f.fieldtype))
        .slice(0, 5);
});

const modalLayout = computed(() => {
  const layout: any[] = [];
  let currentSection: any = { type: "section", columns: [[]] };

  for (const field of doctypeFields.value) {
    if (field.fieldtype === "Section Break") {
      if (currentSection.columns.some((col: any) => col.length > 0)) {
        layout.push(currentSection);
      }

      currentSection = { type: "section", label: field.label, columns: [[]] };
    } else if (field.fieldtype === "Column Break") {
      currentSection.columns.push([]);
    } else {
      currentSection.columns[currentSection.columns.length - 1].push(field);
    }
  }

  if (currentSection.columns.some((col: any) => col.length > 0)) {
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

function ensureRowShape(row: RowData): RowData {
  const shaped: RowData = { ...(row || {}) };
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

function getDefaultValue(field: DocField) {
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
      const newRows = nv.map((r: any) => ensureRowShape(r));
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
        const cleaned: RowData = { ...r };
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

function validateRow(rowIndex: number): Record<string, string> {
  const row = rowsRef.value[rowIndex];
  if (!row) return {};

  const errors: Record<string, string> = {};

  for (const field of doctypeFields.value) {
    if (field.reqd) {
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

function validateAllRows(): boolean {
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

function validateBeforeSave(): boolean {
  const result = validateAllRows();
  emit("validationErrors", new Map(validationErrors.value));
  return result;
}

function stopEditingAndValidate(rowIndex: number, fieldname: string) {
  setTimeout(() => {
    editingRow.value = null;
    editingField.value = null;

    validateRow(rowIndex);
  }, 150);
}

function addRow() {
  const newRow: RowData = {};
  doctypeFields.value.forEach((field) => {
    if (!["Section Break", "Column Break"].includes(field.fieldtype)) {
      newRow[field.fieldname] = getDefaultValue(field);
    }
  });

  rowsRef.value.push(newRow);
  const newIndex = rowsRef.value.length - 1;

  validateRow(newIndex);

  if (!editableGrid.value || props.autoEditGrid) {
    openEditModal(newIndex);
  }
}

function duplicateSelected() {
  const indices = Array.from(selectedRows.value).sort((a, b) => b - a);
  const newIndices: number[] = [];

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

function toggleRowSelection(idx: number) {
  if (selectedRows.value.has(idx)) {
    selectedRows.value.delete(idx);
  } else {
    selectedRows.value.add(idx);
  }
}

const allSelected = computed(() => {
  return (
    rowsRef.value.length > 0 && selectedRows.value.size === rowsRef.value.length
  );
});

function toggleSelectAll() {
  if (allSelected.value) {
    selectedRows.value.clear();
  } else {
    rowsRef.value.forEach((_, idx) => selectedRows.value.add(idx));
  }
}

function startEditing(rowIndex: number, fieldname: string) {
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

function openEditModal(idx: number) {
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

  const errors = validateModalData(rowIndex, editModalData.value);

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

function validateModalData(
  rowIndex: number,
  data: RowData
): Record<string, string> {
  const errors: Record<string, string> = {};

  for (const field of doctypeFields.value) {
    if (field.reqd) {
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
</script>
