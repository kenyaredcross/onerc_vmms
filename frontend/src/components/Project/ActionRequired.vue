<template>
	<div class="bg-surface-base rounded-xl shadow-lg border border-outline-red-3 p-8">
		<h2 class="flex flex-row items-center gap-2 text-3xl-bold text-ink-red-7 mb-4">
			<Badge variant="subtle" theme="red">{{ __("Action Required:") }}</Badge>
			<span>{{ __("Deployment Decision") }}</span>
		</h2>
		<p class="text-sm-medium text-ink-gray-7 mb-2">
			{{
				__(
					"Important: Please review the official deployment information before you decide."
				)
			}}
		</p>
		<div class="flex gap-3">
			<Button theme="green" class="flex-1" @click="$emit('accept')">{{
				__("Accept")
			}}</Button>
			<Button theme="red" variant="outline" class="flex-1" @click="$emit('reject')">{{
				__("Reject")
			}}</Button>
		</div>
	</div>
</template>

<script setup>
import { Badge, Button } from "frappe-ui";
const props = defineProps({ projectData: Object });
</script>
