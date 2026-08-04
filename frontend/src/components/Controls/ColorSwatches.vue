<template>
	<div>
		<div class="text-xs text-ink-gray-5 mb-1">
			{{ __(label) }}
		</div>
		<Popover placement="bottom" class="!block">
			<template #target="{ togglePopover, isOpen }">
				<div class="space-y-2">
					<FormControl
						type="text"
						autocomplete="off"
						class="w-full"
						:placeholder="__('Set Color')"
						@focus="togglePopover"
						:modelValue="modelValue"
						@update:modelValue="(val: string) => emit('update:modelValue', val)"
					>
						<template #prefix>
							<div
								class="size-4 rounded-full"
								:style="
									modelValue
										? {
												backgroundColor:
													theme.backgroundColor[
														modelValue.toLowerCase()
													][400],
										  }
										: {}
								"
							>
								<Palette
									v-if="!modelValue"
									class="size-4 stroke-1.5 text-ink-gray-5"
								/>
							</div>
						</template>
						<template #suffix>
							<Button
								variant="ghost"
								:aria-label="__('Clear colour')"
								@click="emit('update:modelValue', null)"
							>
								<X class="size-3 text-ink-gray-5" />
							</Button>
						</template>
					</FormControl>
				</div>
			</template>
			<template #body="{ close }">
				<div class="rounded-lg bg-surface-white p-3 border w-fit mt-2">
					<div class="text-xs text-ink-gray-5 mb-1.5">
						{{ __("Swatches") }}
					</div>
					<div class="grid grid-cols-7 gap-2">
						<button
							v-for="color in colors"
							:key="color"
							type="button"
							class="size-5 rounded-full cursor-pointer"
							:aria-label="__(color)"
							:aria-pressed="modelValue === color"
							:style="{
								backgroundColor: theme.backgroundColor[color.toLowerCase()][400],
							}"
							@click="
								() => {
									emit('update:modelValue', color);
									close();
									emit('change', color);
								}
							"
						></button>
					</div>
				</div>
			</template>
		</Popover>
		<div class="text-sm text-ink-gray-5 mt-2">
			{{ description }}
		</div>
	</div>
</template>
<script setup lang="ts">
import { Button, FormControl, Popover } from "frappe-ui";
import { computed } from "vue";
import { Palette, X } from "lucide-vue-next";
import { theme } from "@/utils/theme";

const emit = defineEmits(["update:modelValue", "change"]);

const props = defineProps<{
	modelValue: string;
	label: string;
	description?: string;
}>();

const colors = computed(() => {
	return [
		"Red",
		"Blue",
		"Green",
		"Amber",
		"Purple",
		"Cyan",
		"Orange",
		"Violet",
		"Pink",
		"Teal",
		"Gray",
		"Yellow",
	];
});
</script>
