<template>
  <div class="relative bg-white rounded-2xl shadow-lg overflow-hidden">
    <div class="relative w-full h-48 sm:h-64 bg-gray-100">
      <img
        v-if="form?.cover_image"
        :src="form.cover_image"
        alt="Cover Image"
        class="object-cover w-full h-full"
      />
      <div
        v-else
        class="flex flex-col items-center justify-center w-full h-full text-gray-400 border-2 border-dashed border-gray-300"
      >
        <svg
          class="w-10 h-10 mb-2"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
          ></path>
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
          ></path>
        </svg>
        <span class="text-sm font-medium">No Cover Image</span>
      </div>

      <button
        @click="openCoverUploader"
        class="absolute top-3 right-3 bg-white/90 hover:bg-white text-gray-700 p-2 rounded-full shadow transition"
        aria-label="Edit cover image"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
          />
        </svg>
      </button>
    </div>

    <div
      class="flex flex-col sm:flex-row items-center sm:items-end justify-between px-6 pb-6 -mt-16 sm:-mt-20 relative z-10"
    >
      <div class="flex items-end space-x-4">
        <div class="relative">
          <div
            class="w-28 h-28 sm:w-36 sm:h-36 rounded-full border-4 border-white shadow-lg bg-gray-100 overflow-hidden"
          >
            <img
              v-if="form?.user_image"
              :src="form.user_image"
              alt="Profile Image"
              class="object-cover w-full h-full"
            />
            <div
              v-else
              class="flex items-center justify-center w-full h-full text-gray-400"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="w-10 h-10"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fill-rule="evenodd"
                  d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                  clip-rule="evenodd"
                ></path>
              </svg>
            </div>
          </div>

          <button
            @click="openProfileUploader"
            class="absolute bottom-1 right-1 bg-white p-1.5 rounded-full shadow-md hover:bg-gray-50 text-gray-700 transition"
            aria-label="Edit profile photo"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
              />
            </svg>
          </button>
        </div>

        <div>
          <h1 class="text-2xl sm:text-3xl font-bold text-red-600 leading-tight">
            {{ form?.full_name || "Volunteer Name" }}
          </h1>
          <p class="text-sm sm:text-base text-gray-500 font-medium">
            {{ form?.email }}
          </p>
        </div>
      </div>
    </div>

    <div
      v-if="showCoverUploader"
      class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      @click.self="closeCoverUploader"
    >
      <div
        class="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col"
      >
        <div class="flex items-center justify-between p-4 border-b">
          <h2 class="text-lg font-semibold text-gray-900">Edit Cover Image</h2>
          <button
            @click="closeCoverUploader"
            class="text-gray-400 hover:text-gray-600 transition"
            :disabled="saveInProgress"
          >
            <svg
              class="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div class="flex items-center justify-between mb-3">
                <label class="block text-sm font-medium text-gray-700">
                  Current Cover Image
                </label>
              </div>
              <div
                class="relative bg-gray-100 rounded-lg overflow-hidden w-full h-48"
              >
                <img
                  v-if="form?.cover_image"
                  :src="form.cover_image"
                  alt="Current Cover"
                  class="w-full h-full object-cover"
                />
                <div
                  v-else
                  class="flex flex-col items-center justify-center w-full h-full text-gray-400"
                >
                  <svg
                    class="w-12 h-12 mb-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
                    ></path>
                  </svg>
                  <span class="text-sm">No current image</span>
                </div>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-3">
                New Cover Image
              </label>
              <div
                class="relative bg-gray-100 rounded-lg overflow-hidden w-full h-48"
              >
                <img
                  v-if="coverImageModel"
                  :src="getCoverPreviewUrl()"
                  alt="New Cover Preview"
                  class="w-full h-full object-cover"
                />
                <div
                  v-else
                  class="flex flex-col items-center justify-center w-full h-full text-gray-400"
                >
                  <svg
                    class="w-12 h-12 mb-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
                    ></path>
                  </svg>
                  <span class="text-sm">Upload to preview</span>
                </div>
              </div>
            </div>
          </div>
          <div class="mt-6">
            <Uploader
              :model-value="coverImageModel"
              @update:model-value="handleCoverImageUpdate"
              :file-types="['image/*']"
              :multi="false"
              :show-file-name="false"
              :show-length="false"
              label="Upload New Cover Image"
              description="Recommended size: 1200x300 pixels. PNG, JPG, GIF up to 10MB"
            />
          </div>
        </div>

        <div
          class="flex items-center justify-between gap-3 p-4 border-t bg-gray-50"
        >
          <button
            v-if="form?.cover_image"
            @click="deleteCoverImage"
            :disabled="saveInProgress"
            class="px-4 py-2 text-sm font-medium text-red-600 bg-white border border-red-300 rounded-lg hover:bg-red-50 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              ></path>
            </svg>
            Delete Current Image
          </button>
          <div v-else></div>

          <div class="flex items-center gap-3">
            <button
              @click="closeCoverUploader"
              :disabled="saveInProgress"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              @click="saveCoverImage"
              :disabled="!coverImageModel || saveInProgress"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <template v-if="saveInProgress">
                <div
                  class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
                ></div>
                Saving...
              </template>
              <template v-else> Save Cover Image </template>
            </button>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="showProfileUploader"
      class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      @click.self="closeProfileUploader"
    >
      <div
        class="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col"
      >
        <div class="flex items-center justify-between p-4 border-b">
          <h2 class="text-lg font-semibold text-gray-900">
            Edit Profile Image
          </h2>
          <button
            @click="closeProfileUploader"
            class="text-gray-400 hover:text-gray-600 transition"
            :disabled="saveInProgress"
          >
            <svg
              class="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="flex flex-col items-center">
              <div class="flex items-center justify-between w-full mb-3">
                <label class="block text-sm font-medium text-gray-700">
                  Current Profile Image
                </label>
              </div>
              <div
                class="w-48 h-48 rounded-full border-4 border-white shadow-lg bg-gray-100 overflow-hidden"
              >
                <img
                  v-if="form?.user_image"
                  :src="form.user_image"
                  alt="Current Profile"
                  class="object-cover w-full h-full"
                />
                <div
                  v-else
                  class="flex items-center justify-center w-full h-full text-gray-400"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="w-12 h-12"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                      clip-rule="evenodd"
                    ></path>
                  </svg>
                </div>
              </div>
            </div>

            <div class="flex flex-col items-center">
              <label
                class="block text-sm font-medium text-gray-700 mb-3 w-full"
              >
                New Profile Image
              </label>
              <div
                class="w-48 h-48 rounded-full border-4 border-white shadow-lg bg-gray-100 overflow-hidden"
              >
                <img
                  v-if="profileImageModel"
                  :src="getProfilePreviewUrl()"
                  alt="New Profile Preview"
                  class="object-cover w-full h-full"
                />
                <div
                  v-else
                  class="flex flex-col items-center justify-center w-full h-full text-gray-400"
                >
                  <svg
                    class="w-12 h-12 mb-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
                    ></path>
                  </svg>
                  <span class="text-sm text-center">Upload to preview</span>
                </div>
              </div>
            </div>
          </div>

          <div class="mt-6">
            <Uploader
              :model-value="profileImageModel"
              @update:model-value="handleProfileImageUpdate"
              :file-types="['image/*']"
              :multi="false"
              :show-file-name="false"
              :show-length="false"
              label="Upload New Profile Image"
              description="Recommended: Square image, minimum 200x200 pixels. PNG, JPG, GIF up to 10MB"
            />
          </div>
        </div>

        <div
          class="flex items-center justify-between gap-3 p-4 border-t bg-gray-50"
        >
          <button
            v-if="form?.user_image"
            @click="deleteProfileImage"
            :disabled="saveInProgress"
            class="px-4 py-2 text-sm font-medium text-red-600 bg-white border border-red-300 rounded-lg hover:bg-red-50 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              ></path>
            </svg>
            Delete Current Image
          </button>
          <div v-else></div>

          <div class="flex items-center gap-3">
            <button
              @click="closeProfileUploader"
              :disabled="saveInProgress"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              @click="saveProfileImage"
              :disabled="!profileImageModel || saveInProgress"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <template v-if="saveInProgress">
                <div
                  class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
                ></div>
                Saving...
              </template>
              <template v-else> Save Profile Image </template>
            </button>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="deleteConfirm.open"
      class="fixed inset-0 bg-black bg-opacity-50 z-[60] flex items-center justify-center p-4"
      @click.self="closeDeleteConfirm"
    >
      <div
        class="bg-white rounded-xl shadow-2xl w-full max-w-sm overflow-hidden"
      >
        <div class="p-6 text-center">
          <svg
            class="w-16 h-16 mx-auto text-red-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856a2 2 0 001.995-1.858L21 5H3l.012 13.142A2 2 0 004.062 19z"
            ></path>
          </svg>
          <h3 class="mt-4 text-lg font-medium text-gray-900">
            Confirm Deletion
          </h3>
          <p class="mt-2 text-sm text-gray-500">
            Are you sure you want to delete your
            <span class="font-semibold">{{ deleteConfirm.type }}</span> image?
            This action cannot be undone.
          </p>
        </div>

        <div
          class="flex justify-end gap-3 p-4 border-t border-gray-200 bg-gray-50"
        >
          <button
            @click="closeDeleteConfirm"
            :disabled="saveInProgress"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            @click="executeDelete"
            :disabled="saveInProgress"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition disabled:opacity-50 flex items-center gap-2"
          >
            <template v-if="saveInProgress">
              <div
                class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
              ></div>
              Deleting...
            </template>
            <template v-else> Delete </template>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from "vue";
import { createResource, toast } from "frappe-ui";
import { useRouter } from "vue-router";
import Uploader from "@/components/Controls/Uploader.vue";

const props = defineProps({
  form: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["saved"]);

const router = useRouter();

const showCoverUploader = ref(false);
const showProfileUploader = ref(false);

const coverImageModel = ref(null);
const profileImageModel = ref(null);
const saveInProgress = ref(false);

const deleteConfirm = reactive({
  open: false,
  type: null,
});

const localForm = reactive({
  user_image: props.form.user_image || null,
  cover_image: props.form.cover_image || null,
  full_name: props.form.full_name || "",
  title: props.form.title || "",
});

watch(
  () => props.form,
  (newForm) => {
    localForm.user_image = newForm.user_image || null;
    localForm.cover_image = newForm.cover_image || null;
    localForm.full_name = newForm.full_name || "";
    localForm.title = newForm.title || "";
  },
  { immediate: true, deep: true }
);

function openCoverUploader() {
  coverImageModel.value = null;
  showCoverUploader.value = true;
}

function closeCoverUploader() {
  showCoverUploader.value = false;
  coverImageModel.value = null;
}

function handleCoverImageUpdate(newValue) {
  coverImageModel.value = newValue;
}

function getCoverPreviewUrl() {
  if (!coverImageModel.value) return null;
  return coverImageModel.value.file_url || coverImageModel.value;
}

function openProfileUploader() {
  profileImageModel.value = null;
  showProfileUploader.value = true;
}

function closeProfileUploader() {
  showProfileUploader.value = false;
  profileImageModel.value = null;
}

function handleProfileImageUpdate(newValue) {
  profileImageModel.value = newValue;
}

function getProfilePreviewUrl() {
  if (!profileImageModel.value) return null;
  return profileImageModel.value.file_url || profileImageModel.value;
}

function openDeleteConfirm(type) {
  if (type === "cover") closeCoverUploader();
  if (type === "profile") closeProfileUploader();

  deleteConfirm.type = type;
  deleteConfirm.open = true;
}

function closeDeleteConfirm() {
  deleteConfirm.open = false;
  deleteConfirm.type = null;
}

function deleteCoverImage() {
  openDeleteConfirm("cover");
}

function deleteProfileImage() {
  openDeleteConfirm("profile");
}

async function executeDelete() {
  if (!deleteConfirm.type) return;

  saveInProgress.value = true;
  const typeToDelete = deleteConfirm.type;

  if (typeToDelete === "cover") {
    localForm.cover_image = null;
  } else if (typeToDelete === "profile") {
    localForm.user_image = null;
  }

  await saveDocsResource.submit();
}

const saveDocsResource = createResource({
  url: "non_profit.non_profit.api.update_user_details",
  makeParams() {
    return {
      user_image: localForm.user_image,
      cover_image: localForm.cover_image,
    };
  },
  onSuccess() {
    toast.success("Profile images saved successfully");
    saveInProgress.value = false;

    closeDeleteConfirm();

    emit("saved", {
      user_image: localForm.user_image,
      cover_image: localForm.cover_image,
    });

    router.go(0);
  },
  onError(err) {
    console.error("Save error:", err);
    toast.error(err.message || "Failed to save profile images");
    saveInProgress.value = false;

    closeDeleteConfirm();

    if (localForm.cover_image === null) openCoverUploader();
    if (localForm.user_image === null) openProfileUploader();
  },
});

async function saveCoverImage() {
  if (!coverImageModel.value) {
    toast.error("Please select a cover image first");
    return;
  }

  saveInProgress.value = true;
  localForm.cover_image =
    coverImageModel.value.file_url || coverImageModel.value;

  await saveDocsResource.submit();
  closeCoverUploader();
}

async function saveProfileImage() {
  if (!profileImageModel.value) {
    toast.error("Please select a profile image first");
    return;
  }

  saveInProgress.value = true;
  localForm.user_image =
    profileImageModel.value.file_url || profileImageModel.value;

  await saveDocsResource.submit();
  closeProfileUploader();
}
</script>

<style scoped>
@media (max-width: 640px) {
  .-mt-16 {
    margin-top: -4rem;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
