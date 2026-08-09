<template>
	<div class="relative z-1 bg-surface-gray-1 rounded-2xl overflow-hidden">
		<div class="relative z-1 w-full h-48 sm:h-64 bg-surface-gray-100">
			<img
				v-if="form?.cover_image"
				:src="form.cover_image"
				:alt="__('Cover Image')"
				class="object-cover w-full h-full"
			/>
			<div
				v-else
				class="flex flex-col items-center justify-center w-full h-full text-ink-gray-1-600 border-2 border-dashed border-outline-gray-300"
			>
				<svg class="w-10 h-10 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
				<span class="text-sm-medium">{{ __("No Cover Image") }}</span>
			</div>

			<button
				@click="openCoverUploader"
				class="absolute top-3 right-3 bg-surface-base/90 hover:bg-surface-base text-ink-gray-1-700 p-2 rounded-full shadow transition"
				:aria-label="__('Edit cover image')"
				v-if="allowEdit"
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
			class="flex flex-col sm:flex-row items-center sm:items-end justify-between px-4 sm:px-6 pb-6 -mt-12 sm:-mt-20 relative z-1"
		>
			<div class="flex items-center sm:items-end space-x-3 sm:space-x-4 w-full">
				<div class="relative">
					<div
						class="w-20 h-20 sm:w-32 sm:h-32 rounded-full border-3 sm:border-4 border-white shadow-md bg-surface-gray-100 overflow-hidden"
					>
						<img
							v-if="form?.user_image"
							:src="form.user_image"
							:alt="__('Profile Image')"
							class="object-cover w-full h-full"
						/>
						<div
							v-else
							class="flex items-center justify-center w-full h-full text-ink-gray-1-600"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="w-8 h-8 sm:w-10 sm:h-10"
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
						v-if="allowEdit"
						:aria-label="__('Edit profile image')"
						class="absolute bottom-1 right-1 bg-surface-base p-1 sm:p-1.5 rounded-full shadow hover:bg-surface-gray-50 text-ink-gray-1-700 transition"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="w-3.5 h-3.5 sm:w-4 sm:h-4"
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
					class="flex flex-col sm:flex-row items-center sm:items-end justify-between w-full"
				>
					<div class="text-center sm:text-left">
						<h1 class="text-2xl-bold sm:text-4xl text-red-600 leading-tight">
							{{ __(form?.full_name || "Volunteer Name") }}
						</h1>
						<p class="text-xs-medium sm:text-base text-ink-gray-1-500">
							{{ __(form?.email) }}
						</p>
					</div>

					<!-- <div class="mt-3 sm:mt-0 flex-shrink-0">
						<a
							href="/app/user-profile"
							target="_blank"
							class="inline-flex items-center px-3 py-1.5 sm:px-4 sm:py-2 border border-red-700 shadow text-xs-medium sm:text-sm rounded-md text-white bg-red-600 hover:bg-red-700 transition"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="h-4 w-4 sm:h-5 sm:w-5 mr-1.5 sm:mr-2"
								viewBox="0 0 20 20"
								fill="currentColor"
							>
								<path
									d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.195 1.328L10 17.5l6.705 1.381a1 1 0 001.195-1.328l-7-14z"
								/>
							</svg>
							<span class="font-semibold sm:font-bold">
								{{ __("View More") }}
							</span>
						</a>
					</div> -->
				</div>
			</div>
		</div>

		<Dialog
			v-model="showCoverUploader"
			:options="{ size: '4xl' }"
			:disable-outside-click-to-close="saveInProgress"
		>
			<template #body-title>
				<h2 class="text-lg-semibold text-ink-gray-1-900">
					{{ __("Edit Cover Image") }}
				</h2>
			</template>

			<template #body-content>
				<div class="max-h-[70vh] overflow-y-auto">
					<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
						<div>
							<div class="flex items-center justify-between mb-3">
								<label class="block text-sm-medium text-ink-gray-1-700">
									{{ __("Current Cover Image") }}
								</label>
							</div>
							<div
								class="relative bg-surface-gray-100 rounded-lg overflow-hidden w-full h-48"
							>
								<img
									v-if="form?.cover_image"
									:src="form.cover_image"
									:alt="__('Current Cover')"
									class="w-full h-full object-cover"
								/>
								<div
									v-else
									class="flex flex-col items-center justify-center w-full h-full text-ink-gray-1-600"
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
									<span class="text-sm">{{ __("No current image") }}</span>
								</div>
							</div>
						</div>

						<div>
							<label class="block text-sm-medium text-ink-gray-1-700 mb-3">
								{{ __("New Cover Image") }}
							</label>
							<div
								class="relative bg-surface-gray-100 rounded-lg overflow-hidden w-full h-48"
							>
								<img
									v-if="coverImageModel"
									:src="getCoverPreviewUrl()"
									:alt="__('New Cover Preview')"
									class="w-full h-full object-cover"
								/>
								<div
									v-else
									class="flex flex-col items-center justify-center w-full h-full text-ink-gray-1-600"
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
									<span class="text-sm">{{ __("Upload to preview") }}</span>
								</div>
							</div>
						</div>
					</div>
					<div class="mt-6">
						<Uploader
							:model-value="coverImageModel"
							@update:model-value="handleCoverImageUpdate"
							:file-types="['.pdf', '.jpg', '.jpeg', '.png']"
							:multi="false"
							:show-file-name="false"
							:show-length="false"
							:label="__('Upload New Cover Image')"
							:description="
								__('Recommended size: 1200x300 pixels. PNG, JPG, GIF up to 10MB')
							"
						/>
					</div>
				</div>
			</template>

			<template #actions>
				<div class="flex items-center justify-between gap-3">
					<button
						v-if="form?.cover_image"
						@click="deleteCoverImage"
						:disabled="saveInProgress"
						class="px-4 py-2 text-sm-medium text-red-600 bg-surface-base border border-red-300 rounded-lg hover:bg-red-50 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
							></path>
						</svg>
						{{ __("Delete Current Image") }}
					</button>
					<div v-else></div>

					<div class="flex items-center gap-3">
						<button
							@click="closeCoverUploader"
							:disabled="saveInProgress"
							class="px-4 py-2 text-sm-medium text-ink-gray-1-700 bg-surface-base border border-outline-gray-300 rounded-lg hover:bg-surface-gray-50 transition disabled:opacity-50 disabled:cursor-not-allowed"
						>
							{{ __("Cancel") }}
						</button>
						<button
							@click="saveCoverImage"
							:disabled="!coverImageModel || saveInProgress"
							class="px-4 py-2 text-sm-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
						>
							<template v-if="saveInProgress">
								<div
									class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
								></div>
								{{ __("Saving...") }}
							</template>
							<template v-else> {{ __("Save Cover Image") }} </template>
						</button>
					</div>
				</div>
			</template>
		</Dialog>

		<Dialog
			v-model="showProfileUploader"
			:options="{ size: '4xl' }"
			:disable-outside-click-to-close="saveInProgress"
		>
			<template #body-title>
				<h2 class="text-lg-semibold text-ink-gray-1-900">
					{{ __("Edit Profile Image") }}
				</h2>
			</template>

			<template #body-content>
				<div class="max-h-[70vh] overflow-y-auto">
					<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
						<div class="flex flex-col items-center">
							<div class="flex items-center justify-between w-full mb-3">
								<label class="block text-sm-medium text-ink-gray-1-700">
									{{ __("Current Profile Image") }}
								</label>
							</div>
							<div
								class="w-48 h-48 rounded-full border-4 border-white shadow-lg bg-surface-gray-100 overflow-hidden"
							>
								<img
									v-if="form?.user_image"
									:src="form.user_image"
									:alt="__('Current Profile')"
									class="object-cover w-full h-full"
								/>
								<div
									v-else
									class="flex items-center justify-center w-full h-full text-ink-gray-1-600"
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
							<label class="block text-sm-medium text-ink-gray-1-700 mb-3 w-full">
								{{ __("New Profile Image") }}
							</label>
							<div
								class="w-48 h-48 rounded-full border-4 border-white shadow-lg bg-surface-gray-100 overflow-hidden"
							>
								<img
									v-if="profileImageModel"
									:src="getProfilePreviewUrl()"
									:alt="__('New Profile Preview')"
									class="object-cover w-full h-full"
								/>
								<div
									v-else
									class="flex flex-col items-center justify-center w-full h-full text-ink-gray-1-600"
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
									<span class="text-sm text-center">{{
										__("Upload to preview")
									}}</span>
								</div>
							</div>
						</div>
					</div>

					<div class="mt-6">
						<Uploader
							:model-value="profileImageModel"
							@update:model-value="handleProfileImageUpdate"
							:file-types="['.pdf', '.jpg', '.jpeg', '.png']"
							:multi="false"
							:show-file-name="false"
							:show-length="false"
							:label="__('Upload New Profile Image')"
							:description="
								__(
									'Recommended: Square image, minimum 200x200 pixels. PNG, JPG, GIF up to 10MB'
								)
							"
						/>
					</div>
				</div>
			</template>

			<template #actions>
				<div class="flex items-center justify-between gap-3">
					<button
						v-if="form?.user_image"
						@click="deleteProfileImage"
						:disabled="saveInProgress"
						class="px-4 py-2 text-sm-medium text-red-600 bg-surface-base border border-red-300 rounded-lg hover:bg-red-50 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
							></path>
						</svg>
						{{ __("Delete Current Image") }}
					</button>
					<div v-else></div>

					<div class="flex items-center gap-3">
						<button
							@click="closeProfileUploader"
							:disabled="saveInProgress"
							class="px-4 py-2 text-sm-medium text-ink-gray-1-700 bg-surface-base border border-outline-gray-300 rounded-lg hover:bg-surface-gray-50 transition disabled:opacity-50 disabled:cursor-not-allowed"
						>
							{{ __("Cancel") }}
						</button>
						<button
							@click="saveProfileImage"
							:disabled="!profileImageModel || saveInProgress"
							class="px-4 py-2 text-sm-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
						>
							<template v-if="saveInProgress">
								<div
									class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
								></div>
								{{ __("Saving...") }}
							</template>
							<template v-else> {{ __("Save Profile Image") }} </template>
						</button>
					</div>
				</div>
			</template>
		</Dialog>

		<Dialog
			v-model="deleteConfirmOpen"
			:options="{ size: 'sm' }"
			:disable-outside-click-to-close="saveInProgress"
		>
			<template #body-title>
				<h3 class="text-lg-medium text-ink-gray-1-900">
					{{ __("Confirm Deletion") }}
				</h3>
			</template>

			<template #body-content>
				<div class="text-center">
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
					<p class="mt-4 text-sm text-ink-gray-1-500">
						{{ __("Are you sure you want to delete your") }}
						<span class="font-semibold">{{ __(deleteConfirm.type) }}</span>
						{{ __("image? This action cannot be undone.") }}
					</p>
				</div>
			</template>

			<template #actions>
				<div class="flex justify-end gap-3">
					<button
						@click="closeDeleteConfirm"
						:disabled="saveInProgress"
						class="px-4 py-2 text-sm-medium text-ink-gray-1-700 bg-surface-base border border-outline-gray-300 rounded-lg hover:bg-surface-gray-50 transition disabled:opacity-50"
					>
						{{ __("Cancel") }}
					</button>
					<button
						@click="executeDelete"
						:disabled="saveInProgress"
						class="px-4 py-2 text-sm-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition disabled:opacity-50 flex items-center gap-2"
					>
						<template v-if="saveInProgress">
							<div
								class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
							></div>
							{{ __("Deleting...") }}
						</template>
						<template v-else> {{ __("Delete") }} </template>
					</button>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import Uploader from "@/components/Controls/Uploader.vue";
import { createResource, Dialog, toast } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";

const props = defineProps({
	form: {
		type: Object,
		required: true,
	},
	allowEdit: {
		type: Boolean,
		default: false,
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

const deleteConfirmOpen = computed({
	get: () => deleteConfirm.open,
	set: (val) => {
		if (val) deleteConfirm.open = true;
		else closeDeleteConfirm();
	},
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
	url: "onerc_vmms.volunteer_and_member_management.api.user.update_user_details",
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
	localForm.cover_image = coverImageModel.value.file_url || coverImageModel.value;

	await saveDocsResource.submit();
	closeCoverUploader();
}

async function saveProfileImage() {
	if (!profileImageModel.value) {
		toast.error("Please select a profile image first");
		return;
	}

	saveInProgress.value = true;
	localForm.user_image = profileImageModel.value.file_url || profileImageModel.value;

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
