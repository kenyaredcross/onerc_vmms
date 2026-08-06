<template>
	<div class="min-h-screen bg-surface-gray-1">
		<ProjectLoading v-if="DeploymentDetail.loading" />
		<ProjectError v-else-if="DeploymentDetail.error" @reload="DeploymentDetail.reload()" />
		<ProjectContent
			v-else-if="DeploymentDetail.data"
			:project="DeploymentDetail.data"
			:decision-loading="assignmentDecision.loading"
			:decision-error="decisionError"
			@accept="acceptAssignment"
			@reject="rejectAssignment"
			@download-contract="downloadContract"
		/>
	</div>
</template>

<script setup>
import ProjectContent from "@/components/Project/ProjectContent.vue";
import ProjectError from "@/components/Project/ProjectError.vue";
import ProjectLoading from "@/components/Project/ProjectLoading.vue";
import { useAssignmentDetail } from "@/composables/useAssignmentDetail";
import { useHead } from "@vueuse/head";

const {
	DeploymentDetail,
	assignmentDecision,
	decisionError,
	acceptAssignment,
	rejectAssignment,
	downloadContract,
} = useAssignmentDetail();

useHead({
	title: "Deployment Assignment Details | Kenya Red Cross",
	meta: [
		{
			name: "description",
			content:
				"View details for your assigned Kenya Red Cross deployment, including progress, timeline, and assignment decision (Accept/Reject).",
		},
	],
});
</script>
