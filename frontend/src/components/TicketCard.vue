<template>
	<div
		class="group relative overflow-hidden p-5 border rounded-2xl bg-white cursor-pointer transition-all duration-300"
	>
		<div class="relative flex items-start justify-between gap-4">
			<div class="flex-1">
				<div class="flex items-center gap-2 mb-2">
					<h4 class="text-lg font-semibold text-gray-900">
						{{ ticket.title }}
					</h4>
					<ChevronRight
						class="w-5 h-5 text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
					/>
				</div>
			</div>

			<div class="flex flex-col items-end justify-between h-full">
				<div class="text-right">
					<div class="text-2xl font-bold text-gray-900">
						{{ ticket.price }}
					</div>
					<div class="text-xs text-gray-400 font-medium">
						{{ ticket.currency }}
					</div>
				</div>
			</div>
		</div>

		<div class="flex justify-end mt-4">
			<Button class="w-1/2 flex items-center gap-2" theme="red" variant="solid">
				<ChevronRight />
			</Button>
		</div>
	</div>
</template>
<script setup>
import { Button } from "frappe-ui";
import { ChevronRight } from "lucide-vue-next";

const props = defineProps({
	ticket: {
		type: Object,
		required: true,
	},
});
</script>
