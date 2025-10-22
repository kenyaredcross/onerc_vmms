<template>
  <div class="border-0">
    <label v-if="label" class="block text-sm font-medium text-gray-700 mb-1"
      >{{ label }} <span v-if="required" class="text-red-500">*</span></label
    >
    <p v-if="description" class="text-xs text-gray-500 mb-2">
      {{ description }}
    </p>

    <component
      v-if="
        !readOnly && (multi || !uploadedFiles.length) && customUploadComponent
      "
      :is="customUploadComponent"
      :accept="acceptAttribute"
      :multiple="multi"
      :supported-formats="supportedFormatsText"
      @files-selected="handleFiles"
      @click="triggerFileInput"
    />

    <button
      v-else-if="!readOnly && (multi || !uploadedFiles.length)"
      type="button"
      class="flex flex-col items-center justify-center p-6 border-2 border-dashed border-gray-300 rounded-md bg-gray-50 hover:border-blue-400 transition-colors duration-300 w-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 mb-4"
      @dragover.prevent
      @drop.prevent="onDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        :accept="acceptAttribute"
        :multiple="multi"
        @change="onFileSelect"
        class="hidden"
      />
      <div class="text-center mb-4 pointer-events-none">
        <Cloud class="mx-auto h-12 w-12 text-gray-400" />
        <div class="mt-4 text-sm text-gray-600">
          <span class="font-medium text-blue-600">Click to upload</span>
          or drag and drop
        </div>
        <p class="text-xs text-gray-500 mt-1">
          Supported formats: {{ supportedFormatsText }}
        </p>
        <p v-if="multi" class="text-xs text-blue-500 mt-1 font-medium">
          Multiple files can be selected
        </p>
      </div>
    </button>

    <div
      v-if="readOnly && !uploadedFiles.length"
      class="p-6 border-2 border-solid border-gray-200 rounded-md bg-gray-50 text-center text-gray-500"
    >
      No files uploaded.
    </div>

    <div v-if="uploadedFiles.length" class="space-y-3">
      <div class="text-sm font-medium text-gray-700 mb-2" v-if="showLength">
        {{ uploadedFiles.length }} file(s)
        {{ readOnly ? "attached" : "uploaded" }}
      </div>
      <div class="grid grid-cols-1 gap-4">
        <div
          v-for="(file, index) in uploadedFiles"
          :key="(file.file_name || file.name || file.file_url) + index"
          class="bg-white p-4 rounded-md border space-y-2"
        >
          <component
            v-if="customPreviewComponent"
            :is="customPreviewComponent"
            :file="file"
            :index="index"
            :read-only="readOnly"
            @remove="removeFile"
          />

          <div v-else class="relative w-full max-w-32">
            <img
              v-if="isImage(file.file_url || file.url || file.file_url)"
              :src="file.file_url || file.url || file"
              alt="Uploaded preview"
              class="w-full h-fit p-2 rounded-lg border object-cover"
            />

            <iframe
              v-else-if="isPDF(file.file_url || file.url || file)"
              :src="file.file_url || file.url || file"
              class="w-fit h-64 border rounded-lg"
            ></iframe>

            <div
              v-else
              class="flex items-center justify-center w-32 h-32 border rounded-lg bg-gray-100 text-gray-500"
            >
              <FileText class="w-10 h-10" />
            </div>

            <button
              v-if="!uploading && !readOnly"
              @click="removeFile(index)"
              class="absolute -top-2 -right-2 bg-gray-200 border rounded-full shadow h-6 w-6 text-red-500 hover:bg-red-100 flex items-center justify-center text-xs"
              title="Remove File"
            >
              ✕
            </button>
          </div>

          <div>
            <a
              :href="file.file_url || file.url || file"
              target="_blank"
              class="block font-medium text-blue-600 hover:underline truncate"
              v-if="showFileName"
            >
              {{ file.file_name || file.name || file }}
            </a>
            <p v-if="file.file_size" class="text-xs text-gray-500 mt-1">
              {{ formatBytes(file.file_size) }}
            </p>
          </div>
        </div>
      </div>

      <button
        v-if="multi && uploadedFiles.length > 1 && !uploading && !readOnly"
        @click="clearAllFiles"
        type="button"
        class="mt-4 px-4 py-2 text-sm text-red-600 border border-red-300 rounded-md hover:bg-red-50 transition-colors"
      >
        Clear All Files
      </button>
    </div>

    <component
      v-if="uploading && customProgressComponent"
      :is="customProgressComponent"
      :upload-queue="uploadQueue"
      @cancel="cancelUpload"
    />

    <div
      v-else-if="uploading"
      class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
    >
      <div class="bg-white p-6 rounded-xl shadow-2xl w-full max-w-lg">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">
          Uploading Files
        </h2>

        <div class="space-y-4 max-h-80 overflow-y-auto pr-2">
          <div
            v-for="(item, index) in uploadQueue"
            :key="item.file.name + index"
            class="space-y-1"
          >
            <div class="flex justify-between text-sm font-medium text-gray-700">
              <span class="truncate w-40">{{ item.file.name }}</span>
              <span>{{ item.progress }}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
              <div
                class="bg-gradient-to-r from-blue-400 to-blue-600 h-2 rounded-full transition-all duration-300"
                :style="{ width: `${item.progress}%` }"
              ></div>
            </div>
          </div>
        </div>

        <div class="mt-6 text-center">
          <p class="text-xs text-gray-500">
            {{ uploadQueue.length }} file(s) uploading...
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { toast } from "frappe-ui";
import { Cloud, FileText } from "lucide-vue-next";

const emit = defineEmits<{
  (e: "success", data: any): void;
  (e: "update:modelValue", value: any): void;
  (e: "filesChanged", files: any[]): void;
}>();

const props = withDefaults(
  defineProps<{
    modelValue?: any;
    label?: string;
    description?: string;
    fileTypes?: string[];
    validateFile?: (file: File) => string | void;
    required?: boolean;
    uploadArgs?: { [key: string]: any };
    multi?: boolean;
    maxFiles?: number;
    maxFileSize?: number;
    readOnly?: boolean;

    showFileName?: boolean;
    showLength?: boolean;

    customUploadComponent?: any;
    customPreviewComponent?: any;
    customProgressComponent?: any;

    customUploadHandler?: (file: File) => Promise<any>;
  }>(),
  {
    modelValue: "",
    label: "",
    description: "",
    fileTypes: () => ["*/*"],
    required: false,
    uploadArgs: () => ({}),
    multi: false,
    maxFiles: 10,
    maxFileSize: 10,
    readOnly: false,
    showFileName: true,
    showLength: false,
    customUploadComponent: null,
    customPreviewComponent: null,
    customProgressComponent: null,
  }
);

const fileInput = ref<HTMLInputElement | null>(null);
const uploading = ref(false);
const uploadedFiles = ref<any[]>([]);
const uploadQueue = ref<{ file: File; progress: number }[]>([]);

const triggerFileInput = () => {
  if (props.readOnly) return;
  fileInput.value?.click();
};

async function uploadFile(file: File) {
  if (props.customUploadHandler) {
    return await props.customUploadHandler(file);
  }

  const formData = new FormData();
  formData.append("file", file);

  for (const [key, value] of Object.entries(props.uploadArgs)) {
    formData.append(key, value as string);
  }

  const response = await fetch(
    "/api/method/non_profit.non_profit.api.upload_file",
    {
      method: "POST",
      body: formData,
      credentials: "include",
      headers: {
        "X-Frappe-CSRF-Token": (window as any).csrf_token,
      },
    }
  );

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text);
  }

  const data = await response.json();

  return data.message;
}

const simulateProgress = (update: (p: number) => void) => {
  return new Promise<void>((resolve) => {
    const start = Date.now();
    const tick = () => {
      const elapsed = Date.now() - start;
      const target = Math.min(90, Math.floor((elapsed / 1500) * 90));
      update(target);
      if (elapsed >= 1000) return resolve();
      requestAnimationFrame(tick);
    };
    tick();
  });
};

const normalizeFileTypes = computed(() =>
  (props.fileTypes || ["*/*"]).map((t) => t.trim().toLowerCase())
);

const acceptAttribute = computed(() =>
  normalizeFileTypes.value.includes("*/*")
    ? undefined
    : normalizeFileTypes.value.join(",")
);

const supportedFormatsText = computed(() =>
  props.fileTypes?.length
    ? props.fileTypes
        .map((t) => t.replace(".", ""))
        .join(", ")
        .toUpperCase()
    : "ANY"
);

function fileMatchesAllowed(file: File) {
  if (normalizeFileTypes.value.includes("*/*")) return true;

  const lowerName = file.name.toLowerCase();
  const mime = file.type.toLowerCase();

  for (const pattern of normalizeFileTypes.value) {
    if (pattern.startsWith(".")) {
      if (lowerName.endsWith(pattern)) return true;
    } else if (pattern.endsWith("/*")) {
      const major = pattern.split("/")[0];
      if (mime.startsWith(major + "/")) return true;
    } else if (pattern.includes("/")) {
      if (mime === pattern) return true;
    } else {
      if (lowerName.endsWith("." + pattern)) return true;
    }
  }

  return false;
}

const validateFiles = (files: File[]): File[] => {
  const validFiles: File[] = [];

  for (const file of files) {
    if (
      props.multi &&
      props.maxFiles &&
      uploadedFiles.value.length + validFiles.length >= props.maxFiles
    ) {
      toast.error(`Maximum ${props.maxFiles} files allowed`);
      break;
    }

    if (file.size > props.maxFileSize * 1024 * 1024) {
      toast.error(
        `File ${file.name} is too large. Maximum size is ${props.maxFileSize}MB`
      );
      continue;
    }

    if (props.validateFile) {
      const errorMessage = props.validateFile(file);
      if (errorMessage) {
        toast.error(errorMessage);
        continue;
      }
    }

    if (!fileMatchesAllowed(file)) {
      toast.error(
        `File ${file.name} is not an allowed type. Supported: ${supportedFormatsText.value}`
      );
      continue;
    }

    const isDuplicate = uploadedFiles.value.some(
      (uploadedFile) =>
        (uploadedFile.file_name || uploadedFile.name || uploadedFile) ===
        file.name
    );

    if (isDuplicate) {
      toast.error(`File ${file.name} is already uploaded`);
      continue;
    }

    validFiles.push(file);
  }

  return validFiles;
};

const onFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (!target.files?.length) return;

  const files = Array.from(target.files);
  handleFiles(files);

  target.value = "";
};

const onDrop = (e: DragEvent) => {
  if (props.readOnly) return;
  if (!e.dataTransfer?.files?.length) return;
  const files = Array.from(e.dataTransfer.files);
  handleFiles(files);
};

const handleFiles = async (files: File[]) => {
  if (props.readOnly) return;

  const validFiles = validateFiles(files);
  if (!validFiles.length) return;

  if (!props.multi && uploadedFiles.value.length > 0) {
    uploadedFiles.value = [];
  }

  uploadQueue.value = validFiles.map((f) => ({ file: f, progress: 0 }));
  uploading.value = true;

  for (const item of uploadQueue.value) {
    const file = item.file;
    item.progress = 0;

    try {
      await simulateProgress((p) => (item.progress = p));
      const data = await uploadFile(file);

      const fileObj =
        data && typeof data === "object"
          ? data
          : {
              file_name: file.name,
              file_url: data || "",
              file_size: file.size,
            };

      uploadedFiles.value.push(fileObj);
      item.progress = 100;

      if (props.multi) {
        emit("update:modelValue", uploadedFiles.value.slice());
        emit("filesChanged", uploadedFiles.value.slice());
      } else {
        emit("update:modelValue", fileObj);
      }

      emit("success", fileObj);
      toast.success(`${file.name} uploaded successfully.`);
    } catch (err: any) {
      item.progress = 0;
      toast.error(`Failed to upload ${file.name}: ${err?.message || err}`);
    }
  }

  uploading.value = false;
};

const removeFile = (index: number) => {
  if (props.readOnly) return;
  const removedFile = uploadedFiles.value[index];
  uploadedFiles.value.splice(index, 1);

  if (props.multi) {
    emit("update:modelValue", uploadedFiles.value.slice());
    emit("filesChanged", uploadedFiles.value.slice());
  } else {
    emit("update:modelValue", "");
  }
  toast.success(
    `${removedFile.file_name || removedFile.name || "File"} removed successfully.`
  );
};

const clearAllFiles = () => {
  if (props.readOnly) return;
  if (
    confirm(
      `Are you sure you want to remove all ${uploadedFiles.value.length} files?`
    )
  ) {
    uploadedFiles.value = [];
    if (fileInput.value) fileInput.value.value = "";

    if (!props.multi) {
      emit("update:modelValue", "");
    } else {
      emit("update:modelValue", []);
      emit("filesChanged", []);
    }

    toast.success("All files removed successfully.");
  }
};

const cancelUpload = () => {
  uploading.value = false;
  uploadQueue.value = [];
};

const formatBytes = (bytes: number, decimals = 2) => {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
};

const isImage = (url: string) => /\.(jpg|jpeg|png|gif|webp)$/i.test(url);
const isPDF = (url: string) => /\.pdf$/i.test(url);

function initFromModelValue() {
  uploadedFiles.value = [];

  if (props.multi) {
    if (Array.isArray(props.modelValue)) {
      uploadedFiles.value = props.modelValue.map((v: any) =>
        normalizeIncomingFileObj(v)
      );
    }
  } else {
    if (!props.modelValue) {
      uploadedFiles.value = [];
    } else {
      uploadedFiles.value = [normalizeIncomingFileObj(props.modelValue)];
    }
  }
}

function normalizeIncomingFileObj(v: any) {
  if (typeof v === "string") {
    return { file_name: v.split("/").pop(), file_url: v, file_size: null };
  }
  if (v && typeof v === "object") {
    return {
      file_name:
        v.file_name || v.name || (v.file_url || v.url || "").split("/").pop(),
      file_url: v.file_url || v.url || v.file_url || v,
      file_size: v.file_size || v.size || null,
      ...v,
    };
  }
  return v;
}

onMounted(() => {
  initFromModelValue();
});

watch(
  () => props.modelValue,
  () => {
    initFromModelValue();
  },
  { deep: true }
);

defineExpose({
  triggerFileInput,
  handleFiles,
  removeFile,
  clearAllFiles,
});
</script>

<style scoped>
.group:hover {
  background-color: #f8fafb;
}
</style>
