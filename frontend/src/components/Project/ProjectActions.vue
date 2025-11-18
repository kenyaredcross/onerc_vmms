<template>
	<div class="bg-red-50 border border-red-200 rounded-xl shadow-lg p-6 space-y-6 max-w-sm">
		<!-- Header with Aid Theme Icon -->
		<div class="flex items-center space-x-3 border-b border-red-200 pb-4">
			<HeartPulse :size="24" class="text-red-600" />
			<h3 class="text-xl font-bold text-gray-800">Project Operations</h3>
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
			Select an operational item to initiate a new request for this project.
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
