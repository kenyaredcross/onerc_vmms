<template>
	<section>
		<div class="mb-5">
			<div class="flex items-center justify-between gap-4">
				<h2 class="text-xl font-bold text-red-700">
					{{ __("Supporting Documents") }}
				</h2>
				<span
					v-if="requiredTypes.length"
					class="text-sm font-medium flex items-center gap-1.5"
					:class="allRequiredDone ? 'text-green-700' : 'text-ink-gray-1-600'"
				>
					<CheckCircle2 v-if="allRequiredDone" class="w-4 h-4" />
					{{ uploadedRequiredCount }} {{ __("of") }} {{ requiredTypes.length }}
					{{ __("required uploaded") }}
				</span>
			</div>

			<div
				v-if="requiredTypes.length"
				class="mt-2 w-full h-1 bg-surface-gray-200 rounded-full overflow-hidden"
			>
				<div
					class="h-1 rounded-full transition-all duration-300"
					:class="allRequiredDone ? 'bg-green-600' : 'bg-red-600'"
					:style="{ width: `${requiredProgress}%` }"
				></div>
			</div>
		</div>

		<div v-if="displayTypes.length">
			<div class="space-y-3">
				<DocumentRequirementCard
					v-for="type in pagedTypes"
					:key="`doc-${type}`"
					:title="type"
					:required="requiredSet.has(type)"
					:model-value="attachmentByType[type] || null"
					@update:model-value="(v) => setAttachment(type, v)"
				>
					<template v-if="type === 'Other'" #beforeState>
						<FormControl
							type="text"
							:label="__('Document name')"
							:model-value="docNameByType[type] || ''"
							:placeholder="__('e.g. Reference letter')"
							class="mb-3"
							@update:model-value="(v) => setDocName(type, v)"
						/>
					</template>
				</DocumentRequirementCard>
			</div>

			<div v-if="totalPages > 1" class="mt-4 flex items-center justify-center gap-3">
				<Button
					variant="ghost"
					size="sm"
					:disabled="currentPage === 1"
					@click="currentPage--"
				>
					<ChevronLeft class="w-4 h-4 mr-1" />
					{{ __("Previous") }}
				</Button>
				<span class="text-xs text-ink-gray-1-600">
					{{ __("Page {0} of {1}").format(currentPage, totalPages) }}
				</span>
				<Button
					variant="ghost"
					size="sm"
					:disabled="currentPage === totalPages"
					@click="currentPage++"
				>
					{{ __("Next") }}
					<ChevronRight class="w-4 h-4 ml-1" />
				</Button>
			</div>
		</div>

		<div
			v-else
			class="rounded-lg border border-dashed border-outline-gray-300 bg-surface-gray-50 px-4 py-6 text-center"
		>
			<FileText class="mx-auto h-7 w-7 text-ink-gray-1-400" />
			<p class="mt-2 text-sm font-medium text-ink-gray-1-700">
				{{ __("No documents required") }}
			</p>
			<p class="mt-0.5 text-xs text-ink-gray-1-500">
				{{ __("There are no supporting documents to upload for your application.") }}
			</p>
		</div>

		<div class="mt-6 flex items-center justify-between gap-4 border-t pt-4">
			<p class="text-xs text-ink-gray-1-500">
				{{ __("Files upload immediately. Your application is saved when you continue.") }}
			</p>
			<span
				v-if="requiredTypes.length"
				class="text-xs font-medium flex items-center gap-1.5"
				:class="allRequiredDone ? 'text-green-700' : 'text-amber-700'"
			>
				<component
					:is="allRequiredDone ? CheckCircle2 : AlertCircle"
					class="w-3.5 h-3.5"
				/>
				{{
					allRequiredDone
						? __("All required documents uploaded")
						: __("{0} of {1} required uploaded").format(
								uploadedRequiredCount,
								requiredTypes.length
						  )
				}}
			</span>
		</div>
	</section>
</template>

<script setup>
import { Button, FormControl, createResource } from "frappe-ui";
import { AlertCircle, CheckCircle2, ChevronLeft, ChevronRight, FileText } from "lucide-vue-next";
import { computed, ref, watch } from "vue";
import DocumentRequirementCard from "./DocumentRequirementCard.vue";

const PAGE_SIZE = 5;

const props = defineProps({
	modelValue: { type: Object, required: true },
	// Kept for interface compatibility with the wizard (unused here).
	errors: { type: Object, default: () => ({}) },
	documents: { type: Array, default: () => [] },
	requiredTypes: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue"]);

const localModel = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const allTypesResource = createResource({
	url: "onerc_vmms.volunteer_and_member_management.api.doc.custom_search_link",
	method: "POST",
	auto: true,
	params: { doctype: "Supporting Document Type", txt: "", page_length: 500 },
	transform: (data) => (data || []).map((o) => o.value).filter(Boolean),
});

const requiredSet = computed(() => new Set(props.requiredTypes));

function currentRows() {
	return Array.isArray(localModel.value?.supporting_documents)
		? localModel.value.supporting_documents
		: [];
}

const displayTypes = computed(() => {
	const fetched = allTypesResource.data || [];
	const fromRows = currentRows()
		.map((r) => r?.type)
		.filter(Boolean);

	const seen = new Set();
	const out = [];
	for (const t of [...props.requiredTypes, ...fetched, ...fromRows]) {
		if (t && !seen.has(t)) {
			seen.add(t);
			out.push(t);
		}
	}
	return out;
});

const currentPage = ref(1);
const totalPages = computed(() => Math.max(1, Math.ceil(displayTypes.value.length / PAGE_SIZE)));
const pagedTypes = computed(() => {
	const start = (currentPage.value - 1) * PAGE_SIZE;
	return displayTypes.value.slice(start, start + PAGE_SIZE);
});

watch(totalPages, (pages) => {
	if (currentPage.value > pages) currentPage.value = pages;
});

const attachmentByType = ref({});
const docNameByType = ref({});
let selfUpdate = false;

function seedFromModel() {
	const rows = currentRows();
	const aMap = {};
	const nMap = {};
	for (const type of displayTypes.value) {
		const withFile = rows.find((r) => r?.type === type && r?.attachment);
		aMap[type] = withFile ? withFile.attachment : null;
		const anyRow = rows.find((r) => r?.type === type);
		nMap[type] = anyRow?.document_name || "";
	}
	attachmentByType.value = aMap;
	docNameByType.value = nMap;
}

function buildRows() {
	const rows = [];
	for (const type of displayTypes.value) {
		const attachment = attachmentByType.value[type];
		if (!attachment) continue;
		const row = { type, attachment };
		if (type === "Other" && docNameByType.value[type]) {
			row.document_name = docNameByType.value[type];
		}
		rows.push(row);
	}
	return rows;
}

function syncModel() {
	const rows = buildRows();
	if (JSON.stringify(rows) === JSON.stringify(currentRows())) return;
	selfUpdate = true;

	localModel.value.supporting_documents = rows;
}

function setAttachment(type, value) {
	attachmentByType.value = { ...attachmentByType.value, [type]: value || null };
}

function setDocName(type, value) {
	docNameByType.value = { ...docNameByType.value, [type]: value || "" };
}

const uploadedRequiredCount = computed(
	() => props.requiredTypes.filter((type) => !!attachmentByType.value[type]).length
);
const requiredProgress = computed(() => {
	const total = props.requiredTypes.length;
	if (!total) return 0;
	return Math.round((uploadedRequiredCount.value / total) * 100);
});
const allRequiredDone = computed(
	() =>
		props.requiredTypes.length > 0 &&
		uploadedRequiredCount.value === props.requiredTypes.length
);

seedFromModel();

watch([attachmentByType, docNameByType], syncModel, { deep: true });

watch([() => allTypesResource.data, () => props.requiredTypes], seedFromModel, {
	deep: true,
});

watch(
	() => localModel.value?.supporting_documents,
	() => {
		if (selfUpdate) {
			selfUpdate = false;
			return;
		}
		seedFromModel();
	},
	{ deep: true }
);
</script>
