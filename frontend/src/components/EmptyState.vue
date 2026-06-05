<template>
	<div class="flex items-center justify-center px-4">
		<div
			class="bg-surface-white rounded-2xl p-8 max-w-lg w-full text-center border border-red-200"
		>
			<div
				class="flex items-center justify-center w-16 h-16 mx-auto rounded-full bg-red-50 mb-4"
			>
				<FileX class="size-8 text-red-500" />
			</div>

			<h2 class="text-xl font-semibold text-red-600 mb-2">
				{{ __("No {0}").format(type?.toLowerCase()) }}
			</h2>

			<p class="text-ink-gray-1-700 leading-6">
				{{ __("There are no {0} currently.").format(type?.toLowerCase()) }}
				<span v-if="type === 'Membership'" class="block mt-2 text-red-600 font-medium">
					{{ __("Please select a membership plan to continue.") }}
				</span>
			</p>
		</div>
	</div>
</template>

<script setup>
import { FileX } from "lucide-vue-next";

const props = defineProps({
	type: String,
});
</script>
