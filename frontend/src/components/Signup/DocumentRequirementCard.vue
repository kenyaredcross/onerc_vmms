<template>
	<!-- bare = state area only (used inside the "add another document" wrapper) -->
	<div
		:class="
			bare
				? ''
				: 'rounded-lg border border-outline-gray-2 bg-surface-white px-4 py-4 shadow-sm transition-colors'
		"
	>
		<!-- Header (hidden in bare mode) -->
		<div v-if="!bare" class="flex items-start gap-3 mb-3">
			<div
				class="flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-full"
				:class="hasFile ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'"
			>
				<component :is="hasFile ? FileCheck : FileText" class="w-5 h-5" />
			</div>

			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2">
					<div class="flex-1 min-w-0 flex items-center gap-0.5">
						<span class="text-sm font-semibold text-ink-gray-1-800 truncate">
							{{ __(title) }}
						</span>
						<span
							v-if="required"
							class="text-red-500 font-semibold flex-shrink-0"
							:title="__('Required')"
							aria-hidden="true"
							>*</span
						>
					</div>
					<Badge
						:theme="required ? 'red' : 'gray'"
						variant="subtle"
						size="sm"
						class="flex-shrink-0"
					>
						{{ required ? __("Required") : __("Optional") }}
					</Badge>
				</div>
				<p class="text-xs text-ink-gray-1-500 mt-0.5">
					{{ supportHint }}
				</p>
			</div>
		</div>

		<!-- Optional per-card content (e.g. the document name field for "Other") -->
		<slot name="beforeState" />

		<!-- State area -->
		<!-- 1) uploading -->
		<div
			v-if="uploading"
			class="rounded-md border border-outline-gray-2 bg-surface-gray-50 px-3 py-3"
		>
			<div class="flex items-center justify-between text-sm mb-2">
				<span class="flex items-center gap-2 text-ink-gray-1-700 min-w-0">
					<Loader2 class="w-4 h-4 text-red-600 animate-spin flex-shrink-0" />
					<span class="truncate min-w-0">{{ uploadingName }}</span>
				</span>
				<span class="text-xs text-ink-gray-1-500 flex-shrink-0">{{ progress }}%</span>
			</div>
			<div class="w-full h-1 bg-surface-gray-200 rounded-full overflow-hidden">
				<div
					class="h-1 bg-red-600 rounded-full transition-all duration-200"
					:style="{ width: `${progress}%` }"
				></div>
			</div>
		</div>

		<!-- 2) validation / upload error (client-side only; no review-rejection status exists) -->
		<div v-else-if="localError" class="rounded-md border border-red-200 bg-red-50 px-3 py-3">
			<div class="flex items-start gap-2">
				<AlertCircle class="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
				<div class="flex-1 min-w-0">
					<p class="text-sm font-medium text-red-700">
						{{ __("File not accepted") }}
					</p>
					<p class="text-xs text-red-600 mt-0.5 break-words">{{ localError }}</p>
					<button
						type="button"
						class="mt-2 text-xs font-medium text-red-700 hover:text-red-800 underline"
						@click="reset"
					>
						{{ __("Choose another file") }}
					</button>
				</div>
			</div>
		</div>

		<!-- 3) uploaded -->
		<div
			v-else-if="hasFile"
			class="rounded-md border border-outline-gray-2 bg-surface-gray-50 px-3 py-2.5 flex items-center gap-3"
		>
			<div
				class="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded bg-surface-white border border-outline-gray-2 text-red-600"
			>
				<FileText class="w-4 h-4" />
			</div>
			<div class="flex-1 min-w-0">
				<a
					:href="fileUrl"
					target="_blank"
					rel="noopener"
					class="block text-sm font-medium text-ink-gray-1-800 hover:text-red-700 truncate"
				>
					{{ fileName }}
				</a>
				<p class="text-xs text-ink-gray-1-500 truncate">{{ metaLine }}</p>
			</div>
			<div class="flex items-center gap-1 flex-shrink-0">
				<Button
					variant="ghost"
					size="sm"
					class="!p-1.5"
					:title="__('Replace')"
					@click="browse"
				>
					<RefreshCw class="w-4 h-4 text-ink-gray-1-500" />
				</Button>
				<Button
					variant="ghost"
					size="sm"
					class="!p-1.5"
					:title="__('Remove')"
					@click="remove"
				>
					<Trash2 class="w-4 h-4 text-red-500" />
				</Button>
			</div>
		</div>

		<!-- 4) empty -->
		<div
			v-else
			role="button"
			tabindex="0"
			class="rounded-md border-2 border-dashed px-4 py-6 text-center cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-red-200"
			:class="[
				dragOver
					? 'border-red-400 bg-red-50'
					: 'border-outline-gray-300 bg-surface-gray-50 hover:border-red-300 hover:bg-red-50/40',
				disabled ? 'opacity-50 cursor-not-allowed pointer-events-none' : '',
			]"
			@click="browse"
			@keydown.enter.prevent="browse"
			@keydown.space.prevent="browse"
			@dragover.prevent="dragOver = true"
			@dragleave.prevent="dragOver = false"
			@drop.prevent="onDrop"
		>
			<UploadCloud class="mx-auto h-7 w-7 text-ink-gray-1-400 pointer-events-none" />
			<p class="mt-2 text-sm text-ink-gray-1-600 pointer-events-none">
				<span class="font-medium text-red-600">{{ __("Drop a file here") }}</span>
				{{ __("or") }}
				<span class="font-medium text-red-600">{{ __("browse") }}</span>
			</p>
		</div>

		<input
			ref="fileInput"
			type="file"
			:accept="acceptAttribute"
			class="hidden"
			@change="onFileSelect"
		/>
	</div>
</template>

<script setup>
import { toast } from "frappe-ui";
import {
	AlertCircle,
	FileCheck,
	FileText,
	Loader2,
	RefreshCw,
	Trash2,
	UploadCloud,
} from "lucide-vue-next";
import { computed, ref } from "vue";

const props = defineProps({
	title: { type: String, default: "" },
	required: { type: Boolean, default: true },
	// The attachment currently stored for this document: a file object
	// ({ file_url, file_name, file_size, name }), a plain file_url string, or null.
	modelValue: { type: [Object, String, null], default: null },
	disabled: { type: Boolean, default: false },
	bare: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

// Client-side constraints — match the current grid exactly. Server-side
// validation (files.py::upload_file) is authoritative and untouched.
const ALLOWED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png"];
const MAX_FILE_SIZE_MB = 10;
const UPLOAD_URL = "/api/method/onerc_vmms.volunteer_and_member_management.api.files.upload_file";

const fileInput = ref(null);
const uploading = ref(false);
const uploadingName = ref("");
const progress = ref(0);
const localError = ref("");
const dragOver = ref(false);

// Extensions gate validation; the image MIME types make mobile browsers offer
// the camera ("Take Photo") alongside the file picker. Validation still enforces
// the extension list below, so this widens the picker options only, not what's accepted.
const acceptAttribute = computed(() =>
	[...ALLOWED_EXTENSIONS, "image/jpeg", "image/png"].join(",")
);
const supportHint = computed(() => `PDF, JPG or PNG · ${__("up to")} ${MAX_FILE_SIZE_MB} MB`);

const hasFile = computed(() => {
	const v = props.modelValue;
	if (!v) return false;
	if (typeof v === "string") return !!v.trim();
	return !!(v.file_url || v.url);
});

const fileUrl = computed(() => {
	const v = props.modelValue;
	if (!v) return "";
	return typeof v === "string" ? v : v.file_url || v.url || "";
});

const fileName = computed(() => {
	const v = props.modelValue;
	if (!v) return "";
	if (typeof v === "string") return v.split("/").pop();
	return v.file_name || v.name || (v.file_url || v.url || "").split("/").pop();
});

const fileSize = computed(() => {
	const v = props.modelValue;
	if (!v || typeof v === "string") return null;
	return v.file_size || v.size || null;
});

const metaLine = computed(() => {
	const parts = [];
	if (props.title) parts.push(__(props.title));
	if (fileSize.value) parts.push(formatBytes(fileSize.value));
	return parts.join(" · ");
});

function browse() {
	if (props.disabled) return;
	localError.value = "";
	fileInput.value?.click();
}

function reset() {
	localError.value = "";
	uploadingName.value = "";
	progress.value = 0;
}

function onFileSelect(e) {
	const target = e.target;
	const file = target.files?.[0];
	target.value = "";
	if (file) handleFile(file);
}

function onDrop(e) {
	dragOver.value = false;
	if (props.disabled) return;
	const file = e.dataTransfer?.files?.[0];
	if (file) handleFile(file);
}

function validate(file) {
	const lower = file.name.toLowerCase();
	const okExt = ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext));
	if (!okExt) {
		return __("Unsupported file type. Allowed: {0}").format(
			ALLOWED_EXTENSIONS.map((e) => e.replace(".", "").toUpperCase()).join(", ")
		);
	}
	if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
		return __("File is too large. Maximum size is {0} MB.").format(MAX_FILE_SIZE_MB);
	}
	return null;
}

async function handleFile(file) {
	const error = validate(file);
	if (error) {
		localError.value = error;
		return;
	}

	localError.value = "";
	uploadingName.value = file.name;
	uploading.value = true;
	progress.value = 0;

	// Lightweight determinate feedback while the request is in flight.
	const timer = setInterval(() => {
		progress.value = Math.min(90, progress.value + 12);
	}, 120);

	try {
		const formData = new FormData();
		formData.append("file", file);

		const response = await fetch(UPLOAD_URL, {
			method: "POST",
			body: formData,
			credentials: "include",
			headers: {
				"X-Frappe-CSRF-Token": window.csrf_token,
			},
		});

		if (!response.ok) {
			const text = await response.text();
			throw new Error(parseServerError(text));
		}

		const data = await response.json();
		const msg = data?.message || {};

		// Same object shape the grid produced; the server normalises `attachment`
		// to its file_url string on save, so file_size here is display-only.
		const fileObj = {
			file_url: msg.file_url,
			file_name: msg.file_name || file.name,
			file_size: file.size,
			name: msg.name,
		};

		progress.value = 100;
		emit("update:modelValue", fileObj);
		toast.success(__("{0} uploaded").format(fileObj.file_name));
	} catch (err) {
		localError.value = err?.message || __("Upload failed. Please try again.");
	} finally {
		clearInterval(timer);
		uploading.value = false;
	}
}

function remove() {
	emit("update:modelValue", null);
	reset();
	toast.success(__("File removed"));
}

function parseServerError(text) {
	try {
		const json = JSON.parse(text);
		const messages = json._server_messages ? JSON.parse(json._server_messages) : null;
		if (Array.isArray(messages) && messages.length) {
			const first = JSON.parse(messages[0]);
			if (first?.message) return stripHtml(first.message);
		}
		if (json.message) return stripHtml(json.message);
		if (json.exc_type) return json.exc_type;
	} catch (e) {
		// fall through
	}
	return __("Upload failed. Please try again.");
}

function stripHtml(s) {
	return String(s)
		.replace(/<[^>]*>/g, "")
		.trim();
}

function formatBytes(bytes, decimals = 1) {
	if (!bytes) return "";
	const k = 1024;
	const sizes = ["Bytes", "KB", "MB", "GB"];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return `${Number.parseFloat((bytes / k ** i).toFixed(decimals))} ${sizes[i]}`;
}
</script>
