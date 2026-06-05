<template>
	<div class="bg-surface-red-1 border border-outline-red-3 rounded-xl p-6 space-y-6 max-w-sm">
		<!-- Header with Aid Theme Icon -->
		<div class="flex items-center space-x-3 border-b border-outline-red-3 pb-4">
			<HeartPulse :size="24" class="text-red-600" />
			<h3 class="text-xl font-bold text-ink-gray-1-800">Deployment Operations</h3>
		</div>

		<!-- Action Buttons (Strictly 1 per line) -->
		<div class="grid grid-cols-1 gap-4">
			<ActionButton
				label="Expense Claim"
				doctype="Expense Claim"
				:project="project"
				icon="Wallet"
			/>

			<ActionButton
				label="Attendance"
				doctype="Attendance"
				:project="project"
				icon="CalendarCheck"
			/>

			<ActionButton
				label="Timesheet"
				doctype="Timesheet"
				:project="project"
				icon="CalendarCheck"
			/>

			<ActionButton
				label="Material Request"
				doctype="Material Request"
				:project="project"
				icon="Package"
			/>

			<ActionButton
				label="Personnel Advance"
				doctype="Employee Advance"
				:project="project"
				icon="DollarSign"
			/>
		</div>

		<p class="text-xs text-red-700 pt-2 border-t border-red-200">
			Select an operational item to initiate a new request for this deployment.
		</p>
	</div>
</template>

<script setup>
import { HeartPulse } from "lucide-vue-next";
import ActionButton from "./ProjectActionButton.vue";

const props = defineProps({
	project: {
		type: Object,
		required: true,
	},
});
</script>
