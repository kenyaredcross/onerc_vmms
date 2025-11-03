<template>
	<button
		v-if="app"
		class="flex h-7 cursor-pointer hover:bg-surface-gray-2 items-center rounded text-ink-gray-8 duration-300 ease-in-out focus:outline-none focus:transition-none focus-visible:rounded focus-visible:ring-2 focus-visible:ring-outline-gray-3"
		@click="navigate(app)"
	>
		<div
			class="flex items-center w-full duration-300 ease-in-out group"
			:class="isCollapsed ? 'p-1 relative' : 'px-2 py-1'"
		>
			<Tooltip :text="app.title" placement="right">
				<slot name="icon">
					<span class="grid h-5 w-6 flex-shrink-0 place-items-center">
						<img :src="app.logo" class="h-4 w-4 stroke-1.5 text-ink-gray-8" alt="" />
					</span>
				</slot>
			</Tooltip>

			<span
				class="flex-shrink-0 text-sm duration-300 ease-in-out"
				:class="
					isCollapsed ? 'ml-0 w-0 overflow-hidden opacity-0' : 'ml-2 w-auto opacity-100'
				"
			>
				{{ __(app.title) }}
			</span>
		</div>
	</button>
</template>

<script setup>
import { Tooltip } from "frappe-ui";
import * as icons from "lucide-vue-next";

const props = defineProps({
	app: Object,
	isCollapsed: Boolean,
});

const navigate = (app) => {
	window.open(app.route, "_blank");
};
</script>
