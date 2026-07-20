<template>
	<div class="bg-white rounded-xl shadow-lg border border-red-300 p-8">
		<h2 class="flex flex-row items-center gap-2 text-2xl font-bold text-red-700 mb-4">
			<Badge variant="subtle" theme="red">{{ __("Action Required:") }}</Badge>
			<span>{{ __("Deployment Decision") }}</span>
		</h2>
		<p class="text-sm text-gray-700 font-medium mb-2">
			{{
				__(
					"Important: Please review the official deployment information before you decide."
				)
			}}
		</p>
		<div class="flex gap-3">
			<Button theme="green" class="flex-1" @click="$emit('accept')">{{
				__("Accept Deployment")
			}}</Button>
			<Button theme="red" variant="outline" class="flex-1" @click="$emit('reject')">{{
				__("Reject Deployment")
			}}</Button>
		</div>
	</div>
</template>

<script setup>
import { Badge, Button } from "frappe-ui";
const props = defineProps({ projectData: Object });
</script>
